"""Persistence layer for long-term memories stored in PostgreSQL + pgvector."""

from __future__ import annotations

import json
import logging
import uuid
from typing import Any, Dict, List, Optional

import psycopg2
from pgvector.psycopg2 import register_vector

from backend.config import settings
from backend.services.core.embedder import embed_single_text

logger = logging.getLogger(__name__)


class LongTermMemoryStore:
    """Handles persistence and retrieval of conversation memories."""

    TABLE_NAME = "conversation_memories"

    def __init__(self) -> None:
        self.database_url = settings.database_url
        self.embedding_dim = settings.embedding_dim
        self._ensure_table()

    def _ensure_table(self) -> None:
        try:
            conn = psycopg2.connect(self.database_url)
            cur = conn.cursor()
            register_vector(conn)
            cur.execute(
                f"""
                CREATE TABLE IF NOT EXISTS {self.TABLE_NAME} (
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
                f"CREATE INDEX IF NOT EXISTS idx_{self.TABLE_NAME}_session ON {self.TABLE_NAME} (session_id);"
            )
            cur.execute(
                f"CREATE INDEX IF NOT EXISTS idx_{self.TABLE_NAME}_memory_type ON {self.TABLE_NAME} (memory_type);"
            )
            conn.commit()
        except Exception as exc:
            logger.warning("无法初始化对话记忆表: %s", exc)
        finally:
            if "cur" in locals():
                cur.close()
            if "conn" in locals():
                conn.close()

    def _get_connection(self):
        conn = psycopg2.connect(self.database_url)
        try:
            register_vector(conn)
        except Exception:
            pass
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
                INSERT INTO {self.TABLE_NAME}
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
            logger.error("写入长期记忆失败: %s", exc)
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

        embedding = embed_single_text(query)
        embedding_str = "[" + ",".join(map(str, embedding)) + "]"

        conn = self._get_connection()
        cur = conn.cursor()

        try:
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
                FROM {self.TABLE_NAME}
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
            logger.error("搜索长期记忆失败: %s", exc)
            return []
        finally:
            cur.close()
            conn.close()
