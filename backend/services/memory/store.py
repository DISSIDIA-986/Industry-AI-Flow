"""Persistence layer for long-term memories stored in PostgreSQL + pgvector."""

from __future__ import annotations

import json
import logging
import re
import uuid
from typing import Any, Dict, List, Optional

from backend.config import settings
from backend.services.core.embedder import embed_query_text, embed_single_text
from backend.services.database.driver_compat import (
    connect as connect_db,
    register_pgvector,
)

logger = logging.getLogger(__name__)


class LongTermMemoryStore:
    """Handles persistence and retrieval of conversation memories."""

    TABLE_NAME = "conversation_memories"
    TABLE_NAME_PATTERN = re.compile(r"^[a-z_][a-z0-9_]{0,62}$")

    def __init__(self) -> None:
        self.database_url = settings.database_url
        self.embedding_dim = settings.embedding_dim
        self._table_name = self._validated_table_name()
        self._ensure_table()

    @classmethod
    def _validated_table_name(cls) -> str:
        table_name = str(cls.TABLE_NAME or "").strip()
        if not cls.TABLE_NAME_PATTERN.match(table_name):
            raise ValueError(
                "Invalid TABLE_NAME format; expected lowercase SQL identifier."
            )
        return table_name

    def _ensure_table(self) -> None:
        try:
            conn = connect_db(self.database_url)
            cur = conn.cursor()
            register_pgvector(conn)
            cur.execute(
                f"""
                CREATE TABLE IF NOT EXISTS {self._table_name} (
                    id UUID PRIMARY KEY,
                    session_id TEXT NOT NULL,
                    user_id TEXT,
                    memory_type TEXT NOT NULL,
                    content JSONB NOT NULL,
                    embedding vector({self.embedding_dim}),
                    metadata JSONB,
                    created_at TIMESTAMP DEFAULT (NOW())
                );
                """
            )
            cur.execute(
                f"CREATE INDEX IF NOT EXISTS idx_{self._table_name}_session ON {self._table_name} (session_id);"
            )
            cur.execute(
                f"CREATE INDEX IF NOT EXISTS idx_{self._table_name}_memory_type ON {self._table_name} (memory_type);"
            )
            conn.commit()
            # IVFFlat vector index for cosine similarity searches.
            # Requires at least `lists` rows to exist; wrap in try/except
            # so the table creation succeeds even when the table is empty.
            try:
                cur.execute(
                    f"CREATE INDEX IF NOT EXISTS idx_{self._table_name}_embedding "
                    f"ON {self._table_name} USING ivfflat (embedding vector_cosine_ops) "
                    f"WITH (lists = 10);"
                )
                conn.commit()
            except Exception as idx_exc:
                logger.info(
                    "Skipping IVFFlat index creation (likely too few rows): %s",
                    idx_exc,
                )
                conn.rollback()
        except Exception as exc:
            logger.warning("Memory table initialization failed: %s", exc)
        finally:
            if "cur" in locals():
                cur.close()
            if "conn" in locals():
                conn.close()

    def _get_connection(self):
        conn = connect_db(self.database_url)
        register_pgvector(conn)
        return conn

    def store_memory(
        self,
        session_id: str,
        user_id: Optional[str],
        memory_type: str,
        content: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Persist a structured memory entry."""
        memory_id = str(uuid.uuid4())
        conn = self._get_connection()
        cur = conn.cursor()

        try:
            embedding = embed_single_text(json.dumps(content, ensure_ascii=False))
            embedding_str = "[" + ",".join(map(str, embedding)) + "]"

            cur.execute(
                f"""
                INSERT INTO {self._table_name}
                (id, session_id, user_id, memory_type, content, embedding, metadata)
                VALUES (%s, %s, %s, %s, %s, %s::vector, %s)
                """,
                (
                    memory_id,
                    session_id,
                    user_id,
                    memory_type,
                    json.dumps(content, ensure_ascii=False),
                    embedding_str,
                    json.dumps(metadata or {}, ensure_ascii=False),
                ),
            )
            conn.commit()
            return memory_id
        except Exception as exc:
            conn.rollback()
            logger.error("Failed to store memory: %s", exc)
            raise
        finally:
            cur.close()
            conn.close()

    def search_memories(
        self,
        query: str,
        top_k: int,
        min_similarity: float,
        session_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        if not query:
            return []

        embedding = embed_query_text(query)
        embedding_str = "[" + ",".join(map(str, embedding)) + "]"

        conn = self._get_connection()
        cur = conn.cursor()

        try:
            cur.execute("SET ivfflat.probes = 10")
            session_filter = ""
            params: List[Any] = [embedding_str]
            if session_id:
                session_filter = "AND session_id = %s"
                params.append(session_id)
            params.extend([embedding_str, top_k])

            cur.execute(
                f"""
                SELECT
                    id,
                    session_id,
                    user_id,
                    memory_type,
                    content,
                    metadata,
                    1 - (embedding <=> %s::vector) AS similarity,
                    created_at
                FROM {self._table_name}
                WHERE embedding IS NOT NULL {session_filter}
                ORDER BY embedding <=> %s::vector
                LIMIT %s
                """,
                params,
            )

            rows = cur.fetchall()
            memories: List[Dict[str, Any]] = []
            for row in rows:
                similarity = float(row[6])
                if similarity < min_similarity:
                    continue
                memories.append(
                    {
                        "memory_id": row[0],
                        "session_id": row[1],
                        "user_id": row[2],
                        "memory_type": row[3],
                        "content": row[4],
                        "metadata": row[5] or {},
                        "relevance": similarity,
                        "created_at": row[7].isoformat() if row[7] else None,
                    }
                )
            return memories
        except Exception as exc:
            logger.error("Failed to retrieve memories: %s", exc)
            return []
        finally:
            cur.close()
            conn.close()
