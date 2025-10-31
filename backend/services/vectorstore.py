import psycopg2
from pgvector.psycopg2 import register_vector
import uuid
from backend.config import settings


class VectorStore:
    def __init__(self):
        self.database_url = settings.database_url

    def get_connection(self):
        """获取数据库连接"""
        conn = psycopg2.connect(self.database_url)
        register_vector(conn)
        return conn

    def store_document_with_chunks(
        self,
        filename: str,
        filepath: str,
        chunks: list[str],
        embeddings: list[list[float]]
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
                (doc_id, filename, filepath, len(chunks))
            )

            # 2. 插入所有文档块和向量
            for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
                cur.execute(
                    """
                    INSERT INTO document_chunks (doc_id, chunk_id, content, embedding)
                    VALUES (%s, %s, %s, %s)
                    """,
                    (doc_id, i, chunk, embedding)
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
        self,
        query_embedding: list[float],
        top_k: int = 3
    ) -> list[dict]:
        """向量相似度搜索"""
        conn = self.get_connection()
        cur = conn.cursor()

        try:
            # 使用余弦相似度搜索
            cur.execute(
                """
                SELECT
                    dc.doc_id,
                    dc.content,
                    dc.embedding <=> %s AS distance,
                    d.filename
                FROM document_chunks dc
                JOIN documents d ON dc.doc_id = d.id
                ORDER BY distance
                LIMIT %s
                """,
                (query_embedding, top_k)
            )

            results = []
            for row in cur.fetchall():
                results.append({
                    "doc_id": row[0],
                    "content": row[1],
                    "distance": float(row[2]),
                    "filename": row[3]
                })

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
