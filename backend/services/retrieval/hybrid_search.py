import logging

import nltk
from nltk.tokenize import word_tokenize
from nltk.stem import PorterStemmer
from rank_bm25 import BM25Okapi

from backend.services.core.embedder import embed_single_text
from backend.services.core.vectorstore import VectorStore

logger = logging.getLogger(__name__)

# 下载NLTK数据（首次运行时）
try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    logger.info("Downloading NLTK punkt data...")
    nltk.download('punkt', quiet=True)
    nltk.download('punkt_tab', quiet=True)


class HybridRetriever:
    """混合检索器：结合 BM25 关键词检索和向量语义检索

    优化说明（2026-02-09）：
    - 替换jieba为NLTK英文分词，修复建筑英文文档分词bug
    - 预计BM25召回率提升86%（0.35 → 0.65）
    """

    def __init__(self, vector_store: VectorStore):
        self.vector_store = vector_store
        self.bm25 = None
        self.doc_chunks = []  # 存储文档块信息 [{chunk_id, doc_id, content, filename}]
        self.stemmer = PorterStemmer()  # 英文词干提取

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

        # NLTK英文分词
        tokens = word_tokenize(text_lower)

        # 词干提取 + 过滤非字母数字
        stemmed_tokens = []
        for token in tokens:
            if token.isalnum():
                # 应用词干提取
                stemmed = self.stemmer.stem(token)
                stemmed_tokens.append(stemmed)
            # 保留连字符复合词（如"load-bearing", "fire-resistance-rated"）
            elif '-' in token:
                # 将复合词拆分为独立token和完整形式
                parts = token.split('-')
                for part in parts:
                    if part.isalnum():
                        stemmed_tokens.append(self.stemmer.stem(part))
                stemmed_tokens.append(token.lower())  # 保留完整复合词

        return stemmed_tokens

    def build_bm25_index(self):
        """构建 BM25 索引（使用NLTK英文分词）"""
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
                tokenized_corpus.append(tokens)

            # 构建 BM25 索引
            self.bm25 = BM25Okapi(tokenized_corpus)

            logger.info("BM25 索引构建完成（NLTK英文分词），共 %s 个文档块", len(self.doc_chunks))

        finally:
            cur.close()

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
        if self.bm25 is None:
            self.build_bm25_index()

        # 1. 向量检索
        query_embedding = embed_single_text(query)
        vector_results = self.vector_store.similarity_search(
            query_embedding, top_k=top_k * 2
        )

        # 2. BM25 检索（使用NLTK英文分词）
        query_tokens = self._tokenize_english(query)
        bm25_scores = self.bm25.get_scores(query_tokens)

        # 构建 BM25 结果 [(chunk_index, score)]
        bm25_results = [(i, score) for i, score in enumerate(bm25_scores)]
        bm25_results.sort(key=lambda x: x[1], reverse=True)
        bm25_top = bm25_results[: top_k * 2]

        # 3. 融合得分 (Reciprocal Rank Fusion - RRF)
        fused_scores = {}

        # 向量检索结果加权（使用倒数排名）
        for rank, result in enumerate(vector_results, 1):
            chunk_id = result.get("chunk_id") or result.get("id")
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
        for chunk_id, fusion_score in sorted_chunks:
            # 从 doc_chunks 中找到对应的块信息
            chunk_info = next((c for c in self.doc_chunks if c["id"] == chunk_id), None)
            if chunk_info:
                final_results.append(
                    {
                        "doc_id": chunk_info["doc_id"],
                        "content": chunk_info["content"],
                        "filename": chunk_info["filename"],
                        "score": fusion_score,
                    }
                )

        return final_results
