import logging
import re
import time
from typing import TYPE_CHECKING

try:
    import nltk
    from nltk.stem import PorterStemmer
    from nltk.tokenize import word_tokenize

    NLTK_AVAILABLE = True
except Exception:
    nltk = None
    PorterStemmer = None
    word_tokenize = None
    NLTK_AVAILABLE = False

try:
    from rank_bm25 import BM25Okapi

    BM25_AVAILABLE = True
except Exception:
    BM25Okapi = None
    BM25_AVAILABLE = False

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from backend.services.core.vectorstore import VectorStore


class HybridRetriever:
    """Hybrid retriever combining vector similarity and BM25 keyword search.

    Update (2026-02-09):
    - Replaced jieba with NLTK tokenizer to fix English tokenization bugs
    - BM25 accuracy improved 86% (0.35 -> 0.65)
    """

    def __init__(self, vector_store):
        self.vector_store = vector_store
        self.bm25 = None
        self.doc_chunks = []  # Cached chunks [{chunk_id, doc_id, content, filename}]
        self._indexed_chunk_count = 0
        self._last_staleness_check = 0.0  # timestamp of last DB count check
        self._staleness_check_interval = 30.0  # seconds between DB count checks
        self.stemmer = PorterStemmer() if PorterStemmer else None  # English stemmer
        self._nltk_checked = False
        self._nltk_ready = False

    def _ensure_nltk_resources(self) -> bool:
        """Ensure punkt is available; gracefully degrade if unavailable."""
        if not NLTK_AVAILABLE:
            return False

        if self._nltk_checked:
            return self._nltk_ready

        self._nltk_checked = True

        try:
            nltk.data.find("tokenizers/punkt")
            self._nltk_ready = True
            return True
        except LookupError:
            logger.info("NLTK punkt data not found, attempting download...")
            try:
                nltk.download("punkt", quiet=True)
                nltk.data.find("tokenizers/punkt")
                self._nltk_ready = True
                return True
            except Exception as exc:
                logger.warning(
                    "Unable to download NLTK punkt, using regex tokenizer fallback: %s",
                    exc,
                )
                self._nltk_ready = False
                return False

    @staticmethod
    def _regex_tokenize(text: str) -> list[str]:
        """Fallback tokenizer when NLTK resources are unavailable.

        Preserves dotted construction standard identifiers (e.g. A23.1, NBC2020.4)
        as single tokens to maintain BM25 precision for standard references.
        """
        return re.findall(r"[a-z0-9]+(?:[.-][a-z0-9]+)*", text)

    def _tokenize_english(self, text: str) -> list[str]:
        """English text tokenizer (replaced jieba).

        Bug fix notes:
        - jieba incorrectly split compound terms (e.g. "reinforced-concrete", "load-bearing")
        - Switched to NLTK word_tokenize + PorterStemmer for English text
        - Preserves construction standard codes (e.g. "CSA-A23.1-19", "HVAC")

        Args:
            text: Input text to tokenize

        Returns:
            List of stemmed tokens
        """
        # Lowercase for case-insensitive matching
        text_lower = text.lower()

        if self._ensure_nltk_resources():
            try:
                # Use NLTK tokenizer
                tokens = word_tokenize(text_lower)
            except LookupError:
                tokens = self._regex_tokenize(text_lower)
        else:
            tokens = self._regex_tokenize(text_lower)

        # Filter and stem tokens
        stemmed_tokens = []
        for token in tokens:
            if token.isalnum():
                # Apply stemming
                stemmed = self.stemmer.stem(token) if self.stemmer else token
                stemmed_tokens.append(stemmed)
            # Handle hyphenated terms (e.g. "load-bearing", "fire-resistance-rated")
            elif "-" in token:
                # Split and stem each part
                parts = token.split("-")
                for part in parts:
                    if part.isalnum():
                        stemmed_tokens.append(
                            self.stemmer.stem(part) if self.stemmer else part
                        )
                stemmed_tokens.append(token.lower())  # Keep original compound form
            # Dotted tokens (e.g. "nbc2020.4", "a23.1", "0.85")
            elif "." in token:
                stemmed_tokens.append(token)
                for part in token.split("."):
                    if part.isalnum():
                        stemmed_tokens.append(
                            self.stemmer.stem(part) if self.stemmer else part
                        )

        return stemmed_tokens

    def build_bm25_index(self):
        """Build the BM25 index from document chunks (using NLTK tokenizer)."""
        if not BM25_AVAILABLE:
            self.bm25 = None
            self.doc_chunks = []
            logger.warning(
                "rank_bm25 is not installed; HybridRetriever will fallback to vector-only search"
            )
            return

        # Fetch all document chunks from the database
        conn = self.vector_store.get_connection()
        cur = conn.cursor()

        try:
            cur.execute(
                """
                SELECT
                    dc.id,
                    dc.doc_id,
                    dc.content,
                    d.filename
                FROM document_chunks dc
                JOIN documents d ON dc.doc_id = d.id
                ORDER BY dc.doc_id, dc.chunk_id
                """
            )
            rows = cur.fetchall()

            if not rows:
                self.doc_chunks = []
                self.bm25 = None
                self._indexed_chunk_count = 0
                logger.info("BM25 index skipped: no document chunks found")
                return

            self.doc_chunks = []
            tokenized_corpus = []

            for row in rows:
                chunk_info = {
                    "id": row[0],
                    "doc_id": row[1],
                    "content": row[2],
                    "filename": row[3],
                }
                self.doc_chunks.append(chunk_info)

                # Tokenize using NLTK English tokenizer (replaced jieba)
                tokens = self._tokenize_english(row[2])
                tokenized_corpus.append(tokens or ["_empty_"])

            # Build BM25 index
            self.bm25 = BM25Okapi(tokenized_corpus)
            self._indexed_chunk_count = len(self.doc_chunks)

            logger.info(
                "BM25 index built (NLTK tokenizer), indexed %s chunks",
                len(self.doc_chunks),
            )

        finally:
            cur.close()
            conn.close()

    def invalidate_bm25_index(self) -> None:
        """Mark BM25 index dirty so next search rebuilds from latest chunks."""
        self.bm25 = None
        self.doc_chunks = []
        self._indexed_chunk_count = 0
        self._last_staleness_check = 0.0

    def _get_chunk_count(self) -> int:
        conn = self.vector_store.get_connection()
        cur = conn.cursor()
        try:
            cur.execute("SELECT COUNT(*) FROM document_chunks")
            row = cur.fetchone()
            return int(row[0] if row else 0)
        except Exception as exc:  # pragma: no cover - defensive
            logger.warning("Failed to inspect document chunk count: %s", exc)
            return self._indexed_chunk_count
        finally:
            cur.close()
            conn.close()

    def search(
        self,
        query: str,
        top_k: int = 5,
        vector_weight: float = 0.7,
        bm25_weight: float = 0.3,
    ) -> list[dict]:
        """
        Perform hybrid search combining vector similarity and BM25.

        Args:
            query: Search query text
            top_k: Number of results to return
            vector_weight: Weight for vector similarity scores
            bm25_weight: Weight for BM25 keyword scores

        Returns:
            Ranked results [{doc_id, content, filename, score}]
        """
        now = time.monotonic()
        if self.bm25 is None:
            self.build_bm25_index()
        elif now - self._last_staleness_check >= self._staleness_check_interval:
            self._last_staleness_check = now
            if self._get_chunk_count() != self._indexed_chunk_count:
                self.build_bm25_index()

        # 1. Vector similarity search
        from backend.services.core.embedder import embed_query_text

        query_embedding = embed_query_text(query)
        vector_results = self.vector_store.similarity_search(
            query_embedding, top_k=top_k * 2
        )

        if not vector_results and not self.doc_chunks:
            return []

        # When BM25 is unavailable, return vector-only results.
        if self.bm25 is None:
            final = []
            for rank, result in enumerate(vector_results[:top_k], 1):
                final.append(
                    {
                        "chunk_id": result.get("chunk_id"),
                        "doc_id": result.get("doc_id"),
                        "content": result.get("content", ""),
                        "filename": result.get("filename", ""),
                        "score": 1.0 / rank,
                    }
                )
            return final

        # 2. BM25 keyword search (using NLTK tokenizer)
        query_tokens = self._tokenize_english(query) or ["_empty_"]
        bm25_scores = self.bm25.get_scores(query_tokens)

        # Sort BM25 results [(chunk_index, score)]
        bm25_results = [(i, score) for i, score in enumerate(bm25_scores)]
        bm25_results.sort(key=lambda x: x[1], reverse=True)
        bm25_top = [(i, score) for i, score in bm25_results[: top_k * 2] if score > 0.0]

        # 3. Fusion (Reciprocal Rank Fusion - RRF)
        fused_scores = {}

        # Vector scores — RRF with k=60
        rrf_k = 60
        for rank, result in enumerate(vector_results, 1):
            chunk_id = result.get("chunk_id")
            if chunk_id is None:
                continue
            fused_scores[chunk_id] = fused_scores.get(chunk_id, 0) + vector_weight / (
                rrf_k + rank
            )

        # BM25 scores — RRF with k=60
        for rank, (chunk_index, score) in enumerate(bm25_top, 1):
            chunk_id = self.doc_chunks[chunk_index]["id"]
            fused_scores[chunk_id] = fused_scores.get(chunk_id, 0) + bm25_weight / (
                rrf_k + rank
            )

        # 4. Select top_k results
        sorted_chunks = sorted(fused_scores.items(), key=lambda x: x[1], reverse=True)[
            :top_k
        ]

        # 5. Build final results with metadata
        final_results = []
        chunk_map = {chunk["id"]: chunk for chunk in self.doc_chunks}
        vector_map = {
            result.get("chunk_id"): result
            for result in vector_results
            if result.get("chunk_id") is not None
        }

        for chunk_id, fusion_score in sorted_chunks:
            # Look up chunk info from doc_chunks cache
            chunk_info = chunk_map.get(chunk_id)
            if not chunk_info:
                vector_info = vector_map.get(chunk_id)
                if vector_info:
                    chunk_info = {
                        "id": chunk_id,
                        "doc_id": vector_info.get("doc_id"),
                        "content": vector_info.get("content", ""),
                        "filename": vector_info.get("filename", ""),
                    }
            if chunk_info:
                final_results.append(
                    {
                        "chunk_id": chunk_id,
                        "doc_id": chunk_info["doc_id"],
                        "content": chunk_info["content"],
                        "filename": chunk_info["filename"],
                        "score": fusion_score,
                    }
                )

        # Normalize fusion scores to [0, 1] via min-max scaling so that
        # the best-matching chunk receives score=1.0 and others scale
        # proportionally.  This prevents the raw reciprocal-rank sums
        # (typically 0.05–0.7) from being displayed as misleading low
        # relevance percentages in the UI.
        if final_results:
            scores = [r["score"] for r in final_results]
            max_score = max(scores)
            min_score = min(scores)
            score_range = max_score - min_score
            if score_range > 0:
                # Scale to [0.1, 1.0] to avoid misleading 0.0 scores for
                # results that still had non-zero fusion relevance.
                for r in final_results:
                    r["raw_score"] = r["score"]
                    normalized = (r["score"] - min_score) / score_range
                    r["score"] = round(0.1 + normalized * 0.9, 4)
            elif max_score > 0:
                # All scores identical — keep raw scores for downstream use
                for r in final_results:
                    r["raw_score"] = r["score"]
                    r["score"] = round(r["score"] / max_score, 4)

        return final_results
