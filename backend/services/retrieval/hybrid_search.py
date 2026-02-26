import logging
import re
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
    """EN:EN BM25 EN

    EN(2026-02-09):
    - ENjiebaENNLTKEN,ENbug
    - ENBM25EN86%(0.35 → 0.65)
    """

    def __init__(self, vector_store):
        self.vector_store = vector_store
        self.bm25 = None
        self.doc_chunks = []  # EN [{chunk_id, doc_id, content, filename}]
        self._indexed_chunk_count = 0
        self.stemmer = PorterStemmer() if PorterStemmer else None  # EN
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
        """Fallback tokenizer when NLTK resources are unavailable."""
        return re.findall(r"[a-z0-9]+(?:-[a-z0-9]+)*", text)

    def _tokenize_english(self, text: str) -> list[str]:
        """EN(ENjieba)

        ENbugEN:
        - jiebaEN(EN"reinforced-concrete", "load-bearing")EN
        - ENNLTK word_tokenize + PorterStemmerEN
        - EN(EN"CSA-A23.1-19", "HVAC")

        Args:
            text: EN

        Returns:
            EN
        """
        # EN
        text_lower = text.lower()

        if self._ensure_nltk_resources():
            try:
                # NLTKEN
                tokens = word_tokenize(text_lower)
            except LookupError:
                tokens = self._regex_tokenize(text_lower)
        else:
            tokens = self._regex_tokenize(text_lower)

        # EN + EN
        stemmed_tokens = []
        for token in tokens:
            if token.isalnum():
                # EN
                stemmed = self.stemmer.stem(token) if self.stemmer else token
                stemmed_tokens.append(stemmed)
            # EN(EN"load-bearing", "fire-resistance-rated")
            elif "-" in token:
                # ENtokenEN
                parts = token.split("-")
                for part in parts:
                    if part.isalnum():
                        stemmed_tokens.append(
                            self.stemmer.stem(part) if self.stemmer else part
                        )
                stemmed_tokens.append(token.lower())  # EN

        return stemmed_tokens

    def build_bm25_index(self):
        """EN BM25 EN(ENNLTKEN)"""
        if not BM25_AVAILABLE:
            self.bm25 = None
            self.doc_chunks = []
            logger.warning(
                "rank_bm25 is not installed; HybridRetriever will fallback to vector-only search"
            )
            return

        # EN
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

                # ENNLTKEN(ENjieba)
                tokens = self._tokenize_english(row[2])
                tokenized_corpus.append(tokens or ["_empty_"])

            # EN BM25 EN
            self.bm25 = BM25Okapi(tokenized_corpus)
            self._indexed_chunk_count = len(self.doc_chunks)

            logger.info("BM25 EN(NLTKEN),EN %s EN", len(self.doc_chunks))

        finally:
            cur.close()
            conn.close()

    def invalidate_bm25_index(self) -> None:
        """Mark BM25 index dirty so next search rebuilds from latest chunks."""
        self.bm25 = None
        self.doc_chunks = []
        self._indexed_chunk_count = 0

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
        EN

        Args:
            query: EN
            top_k: EN
            vector_weight: EN
            bm25_weight: BM25 EN

        Returns:
            EN [{doc_id, content, filename, score}]
        """
        if self.bm25 is None or self._get_chunk_count() != self._indexed_chunk_count:
            self.build_bm25_index()

        # 1. EN
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

        # 2. BM25 EN(ENNLTKEN)
        query_tokens = self._tokenize_english(query) or ["_empty_"]
        bm25_scores = self.bm25.get_scores(query_tokens)

        # EN BM25 EN [(chunk_index, score)]
        bm25_results = [(i, score) for i, score in enumerate(bm25_scores)]
        bm25_results.sort(key=lambda x: x[1], reverse=True)
        bm25_top = bm25_results[: top_k * 2]

        # 3. EN (Reciprocal Rank Fusion - RRF)
        fused_scores = {}

        # EN(EN)
        for rank, result in enumerate(vector_results, 1):
            chunk_id = result.get("chunk_id")
            if chunk_id is None:
                continue
            fused_scores[chunk_id] = (
                fused_scores.get(chunk_id, 0) + vector_weight / (60 + rank)
            )

        # BM25 EN
        for rank, (chunk_index, score) in enumerate(bm25_top, 1):
            chunk_id = self.doc_chunks[chunk_index]["id"]
            fused_scores[chunk_id] = fused_scores.get(chunk_id, 0) + bm25_weight / (60 + rank)

        # 4. EN top_k EN
        sorted_chunks = sorted(fused_scores.items(), key=lambda x: x[1], reverse=True)[
            :top_k
        ]

        # 5. EN
        final_results = []
        chunk_map = {chunk["id"]: chunk for chunk in self.doc_chunks}
        vector_map = {
            result.get("chunk_id"): result
            for result in vector_results
            if result.get("chunk_id") is not None
        }

        for chunk_id, fusion_score in sorted_chunks:
            # EN doc_chunks EN
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
            max_score = max(r["score"] for r in final_results)
            if max_score > 0:
                for r in final_results:
                    r["score"] = round(r["score"] / max_score, 4)

        return final_results
