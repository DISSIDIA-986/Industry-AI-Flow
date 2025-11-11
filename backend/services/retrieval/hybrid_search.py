import logging

import jieba
from rank_bm25 import BM25Okapi

from backend.services.core.embedder import embed_single_text
from backend.services.core.vectorstore import VectorStore

logger = logging.getLogger(__name__)


class HybridRetriever:
    """混合检索器：结合 BM25 关键词检索和向量语义检索"""

    def __init__(self, vector_store: VectorStore):
        self.vector_store = vector_store
        self.bm25 = None
        self.doc_chunks = []  # 存储文档块信息 [{chunk_id, doc_id, content, filename}]

    def build_bm25_index(self):
        """构建 BM25 索引"""
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

                # 使用 jieba 分词（支持中文）
                tokens = list(jieba.cut_for_search(row[2]))
                tokenized_corpus.append(tokens)

            # 构建 BM25 索引
            self.bm25 = BM25Okapi(tokenized_corpus)

            logger.info("BM25 索引构建完成，共 %s 个文档块", len(self.doc_chunks))

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

        # 2. BM25 检索
        query_tokens = list(jieba.cut_for_search(query))
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
