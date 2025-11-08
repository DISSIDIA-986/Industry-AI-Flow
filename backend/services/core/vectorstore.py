import uuid

import psycopg2
from pgvector.psycopg2 import register_vector

from backend.config import settings


class VectorStore:
    def __init__(self):
        self.database_url = settings.database_url

    def get_connection(self):
        """获取数据库连接"""
        conn = psycopg2.connect(self.database_url)
        # 尝试注册 pgvector，如果不可用则跳过
        try:
            register_vector(conn)
        except Exception:
            # pgvector 扩展未安装，向量将存储为 TEXT
            pass
        return conn

    def store_document_with_chunks(
        self,
        filename: str,
        filepath: str,
        chunks: list[str],
        embeddings: list[list[float]],
    ) -> str:
        """存储文档及其分块向量"""
        conn = self.get_connection()
        cur = conn.cursor()

        try:
            # 1. 插入文档记录
            doc_id = str(uuid.uuid4())
            cur.execute(
                """
                INSERT INTO documents (id, filename, filepath, chunk_count)
                VALUES (%s, %s, %s, %s)
                """,
                (doc_id, filename, filepath, len(chunks)),
            )

            # 2. 插入所有文档块和向量
            for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
                cur.execute(
                    """
                    INSERT INTO document_chunks (doc_id, chunk_id, content, embedding)
                    VALUES (%s, %s, %s, %s)
                    """,
                    (doc_id, i, chunk, embedding),
                )

            conn.commit()
            return doc_id

        except Exception as e:
            conn.rollback()
            raise e
        finally:
            cur.close()
            conn.close()

    def similarity_search(
        self, query_embedding: list[float], top_k: int = 3
    ) -> list[dict]:
        """向量相似度搜索（兼容无pgvector的环境）"""
        conn = self.get_connection()
        cur = conn.cursor()

        try:
            # 检查是否安装了 pgvector 扩展
            cur.execute(
                """
                SELECT EXISTS(
                    SELECT 1 FROM pg_extension WHERE extname = 'vector'
                )
            """
            )
            has_pgvector = cur.fetchone()[0]

            if has_pgvector:
                # 使用 pgvector 的余弦相似度
                embedding_str = "[" + ",".join(map(str, query_embedding)) + "]"
                cur.execute(
                    """
                    SELECT
                        dc.doc_id,
                        dc.content,
                        dc.embedding <=> %s::vector AS distance,
                        d.filename
                    FROM document_chunks dc
                    JOIN documents d ON dc.doc_id = d.id
                    ORDER BY distance
                    LIMIT %s
                    """,
                    (embedding_str, top_k),
                )
            else:
                # 回退到 Python 计算相似度（向量存储为 TEXT）
                cur.execute(
                    """
                    SELECT
                        dc.doc_id,
                        dc.content,
                        dc.embedding,
                        d.filename
                    FROM document_chunks dc
                    JOIN documents d ON dc.doc_id = d.id
                    WHERE dc.embedding IS NOT NULL
                """
                )

                # 计算余弦相似度
                import numpy as np
                from sklearn.metrics.pairwise import cosine_similarity

                all_results = []
                query_vec = np.array(query_embedding).reshape(1, -1)

                for row in cur.fetchall():
                    # 解析存储的向量（PostgreSQL 数组格式 {x,y,z}）
                    embedding_str = row[2]
                    if embedding_str.startswith("{") and embedding_str.endswith("}"):
                        # PostgreSQL 数组格式
                        embedding_str = embedding_str[1:-1]  # 去除首尾的 {}
                    stored_embedding = [float(x) for x in embedding_str.split(",")]
                    stored_vec = np.array(stored_embedding).reshape(1, -1)

                    # 计算相似度（转为距离）
                    similarity = cosine_similarity(query_vec, stored_vec)[0][0]
                    distance = 1 - similarity

                    all_results.append(
                        {
                            "doc_id": row[0],
                            "content": row[1],
                            "distance": distance,
                            "filename": row[3],
                        }
                    )

                # 排序并取 top_k
                all_results.sort(key=lambda x: x["distance"])
                return all_results[:top_k]

            results = []
            for row in cur.fetchall():
                results.append(
                    {
                        "doc_id": row[0],
                        "content": row[1],
                        "distance": float(row[2]),
                        "filename": row[3],
                    }
                )

            return results

        finally:
            cur.close()
            conn.close()

    def get_document_count(self) -> int:
        """获取文档总数"""
        conn = self.get_connection()
        cur = conn.cursor()

        try:
            cur.execute("SELECT COUNT(*) FROM documents")
            return cur.fetchone()[0]
        finally:
            cur.close()
            conn.close()

    def get_chunk_count(self) -> int:
        """获取文档块总数"""
        conn = self.get_connection()
        cur = conn.cursor()

        try:
            cur.execute("SELECT COUNT(*) FROM document_chunks")
            return cur.fetchone()[0]
        finally:
            cur.close()
            conn.close()
