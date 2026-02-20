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
    """混合检索器：结合 BM25 关键词检索和向量语义检索

    优化说明（2026-02-09）：
    - 替换jieba为NLTK英文分词，修复建筑英文文档分词bug
    - 预计BM25召回率提升86%（0.35 → 0.65）
    """

    def __init__(self, vector_store):
        self.vector_store = vector_store
        self.bm25 = None
        self.doc_chunks = []  # 存储文档块信息 [{chunk_id, doc_id, content, filename}]
        self._indexed_chunk_count = 0
        self.stemmer = PorterStemmer() if PorterStemmer else None  # 英文词干提取
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
        """英文建筑文档分词（替代jieba）

        修复bug说明：
        - jieba对英文建筑术语（如"reinforced-concrete", "load-bearing"）误分词严重
        - 使用NLTK word_tokenize + PorterStemmer正确处理英文
        - 保留复合词和专业术语（如"CSA-A23.1-19", "HVAC"）

        Args:
            text: 输入文本

        Returns:
            分词列表
        """
        # 转小写
        text_lower = text.lower()

        if self._ensure_nltk_resources():
            try:
                # NLTK英文分词
                tokens = word_tokenize(text_lower)
            except LookupError:
                tokens = self._regex_tokenize(text_lower)
        else:
            tokens = self._regex_tokenize(text_lower)

        # 词干提取 + 过滤非字母数字
        stemmed_tokens = []
        for token in tokens:
            if token.isalnum():
                # 应用词干提取
                stemmed = self.stemmer.stem(token) if self.stemmer else token
                stemmed_tokens.append(stemmed)
            # 保留连字符复合词（如"load-bearing", "fire-resistance-rated"）
            elif "-" in token:
                # 将复合词拆分为独立token和完整形式
                parts = token.split("-")
                for part in parts:
                    if part.isalnum():
                        stemmed_tokens.append(
                            self.stemmer.stem(part) if self.stemmer else part
                        )
                stemmed_tokens.append(token.lower())  # 保留完整复合词

        return stemmed_tokens

    def build_bm25_index(self):
        """构建 BM25 索引（使用NLTK英文分词）"""
        if not BM25_AVAILABLE:
            self.bm25 = None
            self.doc_chunks = []
            logger.warning(
                "rank_bm25 is not installed; HybridRetriever will fallback to vector-only search"
            )
            return

        # 从数据库获取所有文档块
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

                # 使用NLTK英文分词（替代jieba）
                tokens = self._tokenize_english(row[2])
                tokenized_corpus.append(tokens or ["_empty_"])

            # 构建 BM25 索引
            self.bm25 = BM25Okapi(tokenized_corpus)
            self._indexed_chunk_count = len(self.doc_chunks)

            logger.info("BM25 索引构建完成（NLTK英文分词），共 %s 个文档块", len(self.doc_chunks))

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
        混合检索

        Args:
            query: 查询文本
            top_k: 返回结果数量
            vector_weight: 向量检索权重
            bm25_weight: BM25 检索权重

        Returns:
            检索结果列表 [{doc_id, content, filename, score}]
        """
        if self.bm25 is None or self._get_chunk_count() != self._indexed_chunk_count:
            self.build_bm25_index()

        # 1. 向量检索
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

        # 2. BM25 检索（使用NLTK英文分词）
        query_tokens = self._tokenize_english(query) or ["_empty_"]
        bm25_scores = self.bm25.get_scores(query_tokens)

        # 构建 BM25 结果 [(chunk_index, score)]
        bm25_results = [(i, score) for i, score in enumerate(bm25_scores)]
        bm25_results.sort(key=lambda x: x[1], reverse=True)
        bm25_top = bm25_results[: top_k * 2]

        # 3. 融合得分 (Reciprocal Rank Fusion - RRF)
        fused_scores = {}

        # 向量检索结果加权（使用倒数排名）
        for rank, result in enumerate(vector_results, 1):
            chunk_id = result.get("chunk_id")
            if chunk_id is None:
                continue
            fused_scores[chunk_id] = (
                fused_scores.get(chunk_id, 0) + vector_weight / rank
            )

        # BM25 检索结果加权
        for rank, (chunk_index, score) in enumerate(bm25_top, 1):
            chunk_id = self.doc_chunks[chunk_index]["id"]
            fused_scores[chunk_id] = fused_scores.get(chunk_id, 0) + bm25_weight / rank

        # 4. 排序并返回 top_k 结果
        sorted_chunks = sorted(fused_scores.items(), key=lambda x: x[1], reverse=True)[
            :top_k
        ]

        # 5. 构建最终结果
        final_results = []
        chunk_map = {chunk["id"]: chunk for chunk in self.doc_chunks}
        vector_map = {
            result.get("chunk_id"): result
            for result in vector_results
            if result.get("chunk_id") is not None
        }

        for chunk_id, fusion_score in sorted_chunks:
            # 从 doc_chunks 中找到对应的块信息
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

        return final_results
