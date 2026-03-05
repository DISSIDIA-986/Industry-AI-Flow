import logging
import time
import uuid

from backend.config import settings
from backend.observability.performance_metrics import record_db_query_duration
from backend.services.database.driver_compat import (
    connect as connect_db,
    register_pgvector,
)


class VectorStore:
    _indexes_ready = False

    def __init__(self):
        self.database_url = settings.database_url
        if not VectorStore._indexes_ready:
            self._ensure_indexes()
            VectorStore._indexes_ready = True

    def get_connection(self):
        """Get a new database connection."""
        conn = connect_db(self.database_url)
        # Register pgvector extension for vector operations
        register_pgvector(conn)
        return conn

    def _ensure_indexes(self) -> None:
        """Create helpful indexes if they do not exist."""
        try:
            conn = connect_db(self.database_url)
            cur = conn.cursor()
            register_pgvector(conn)
            cur.execute(
                "CREATE INDEX IF NOT EXISTS idx_documents_filename ON documents(filename);"
            )
            cur.execute(
                "CREATE INDEX IF NOT EXISTS idx_document_chunks_docid ON document_chunks(doc_id);"
            )
            cur.execute(
                "CREATE INDEX IF NOT EXISTS idx_document_chunks_content_fts ON document_chunks USING gin (to_tsvector('simple', content));"
            )
            try:
                cur.execute(
                    "CREATE INDEX IF NOT EXISTS idx_document_chunks_embedding ON document_chunks USING ivfflat (embedding vector_cosine_ops);"
                )
            except Exception:
                # pgvector not available, skip ivfflat index
                conn.rollback()
            conn.commit()
        except Exception as exc:
            if "conn" in locals():
                conn.rollback()
            # Do not crash app if indexes cannot be created
            import logging

            logging.getLogger(__name__).warning("Failed to create database indexes: %s", exc)
        finally:
            if "cur" in locals():
                cur.close()
            if "conn" in locals():
                conn.close()

    def store_document_with_chunks(
        self,
        filename: str,
        filepath: str,
        chunks: list[str],
        embeddings: list[list[float]],
    ) -> str:
        """Store a document and its chunks with embeddings."""
        conn = self.get_connection()
        cur = conn.cursor()
        start_time = time.monotonic()
        query_type = "store_document"

        try:
            # 1. Insert document record
            doc_id = str(uuid.uuid4())
            cur.execute(
                """
                INSERT INTO documents (id, filename, filepath, chunk_count)
                VALUES (%s, %s, %s, %s)
                """,
                (doc_id, filename, filepath, len(chunks)),
            )

            # 2. Insert chunk records with embeddings
            for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
                cur.execute(
                    """
                    INSERT INTO document_chunks (doc_id, chunk_id, content, embedding)
                    VALUES (%s, %s, %s, %s)
                    """,
                    (doc_id, i, chunk, embedding),
                )

            conn.commit()
            try:
                from backend.services.retrieval.document_profile import (
                    DocumentProfileService,
                )

                DocumentProfileService(self).refresh_profile_for_document(doc_id)
            except Exception as exc:  # pragma: no cover - best effort enrichment
                logging.getLogger(__name__).warning(
                    "Failed to refresh document profile for %s: %s",
                    doc_id,
                    exc,
                )
            return doc_id

        except Exception as e:
            conn.rollback()
            raise e
        finally:
            cur.close()
            conn.close()
            self._record_duration(query_type, start_time)

    def similarity_search(
        self, query_embedding: list[float], top_k: int = 3
    ) -> list[dict]:
        """Perform vector similarity search (using pgvector cosine distance)."""
        conn = self.get_connection()
        cur = conn.cursor()
        start_time = time.monotonic()
        query_type = "similarity_search"

        try:
            # Check if pgvector extension is available
            cur.execute(
                """
                SELECT EXISTS(
                    SELECT 1 FROM pg_extension WHERE extname = 'vector'
                )
            """
            )
            has_pgvector = cur.fetchone()[0]

            if has_pgvector:
                # Set IVFFlat probes for better recall (default=1 misses most vectors)
                cur.execute("SET ivfflat.probes = 10")
                embedding_str = "[" + ",".join(map(str, query_embedding)) + "]"
                cur.execute(
                    """
                    SELECT
                        dc.id,
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
                # Fallback: Python-based cosine similarity (embeddings stored as TEXT)
                cur.execute(
                    """
                    SELECT
                        dc.id,
                        dc.doc_id,
                        dc.content,
                        dc.embedding,
                        d.filename
                    FROM document_chunks dc
                    JOIN documents d ON dc.doc_id = d.id
                    WHERE dc.embedding IS NOT NULL
                """
                )

                # Compute similarity in Python
                import numpy as np
                from sklearn.metrics.pairwise import cosine_similarity

                all_results = []
                query_vec = np.array(query_embedding).reshape(1, -1)

                for row in cur.fetchall():
                    # Parse embedding string (PostgreSQL array format {x,y,z})
                    embedding_str = row[3]
                    if embedding_str.startswith("{") and embedding_str.endswith("}"):
                        # Strip PostgreSQL array braces
                        embedding_str = embedding_str[1:-1]  # Remove {}
                    stored_embedding = [float(x) for x in embedding_str.split(",")]
                    stored_vec = np.array(stored_embedding).reshape(1, -1)

                    # Calculate cosine similarity (convert to distance)
                    similarity = cosine_similarity(query_vec, stored_vec)[0][0]
                    distance = 1 - similarity

                    all_results.append(
                        {
                            "chunk_id": row[0],
                            "doc_id": row[1],
                            "content": row[2],
                            "distance": distance,
                            "filename": row[4],
                        }
                    )

                # Sort by distance and return top_k
                all_results.sort(key=lambda x: x["distance"])
                return all_results[:top_k]

            results = []
            for row in cur.fetchall():
                results.append(
                    {
                        "chunk_id": row[0],
                        "doc_id": row[1],
                        "content": row[2],
                        "distance": float(row[3]),
                        "filename": row[4],
                    }
                )

            return results

        finally:
            cur.close()
            conn.close()
            self._record_duration(query_type, start_time)

    def get_document_count(self) -> int:
        """Get the total number of stored documents."""
        conn = self.get_connection()
        cur = conn.cursor()
        start_time = time.monotonic()

        try:
            cur.execute("SELECT COUNT(*) FROM documents")
            return cur.fetchone()[0]
        finally:
            cur.close()
            conn.close()
            self._record_duration("documents_count", start_time)

    def get_chunk_count(self) -> int:
        """Get the total number of stored document chunks."""
        conn = self.get_connection()
        cur = conn.cursor()
        start_time = time.monotonic()

        try:
            cur.execute("SELECT COUNT(*) FROM document_chunks")
            return cur.fetchone()[0]
        finally:
            cur.close()
            conn.close()
            self._record_duration("chunks_count", start_time)

    def delete_by_doc_id(self, doc_id: str) -> None:
        """Delete a document and its chunks by document ID."""
        conn = self.get_connection()
        cur = conn.cursor()
        start_time = time.monotonic()

        try:
            cur.execute("DELETE FROM document_chunks WHERE doc_id = %s", (doc_id,))
            cur.execute("DELETE FROM documents WHERE id = %s", (doc_id,))
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            cur.close()
            conn.close()
            self._record_duration("delete_document", start_time)

    def _record_duration(self, query_type: str, start_time: float) -> None:
        duration = time.monotonic() - start_time
        record_db_query_duration(query_type, duration)
        threshold = settings.db_query_slow_threshold_ms / 1000
        if duration > threshold:
            import logging

            logging.getLogger(__name__).warning(
                "Slow DB query (%s) %.2fms", query_type, duration * 1000
            )
