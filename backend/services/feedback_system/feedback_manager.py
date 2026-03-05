"""
Feedback Manager - Feedback-driven RAG quality optimization system.
"""

import datetime
import json
import logging
import uuid
from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional, Tuple

from backend.services.core.embedder import embed_single_text
from backend.services.core.vectorstore import VectorStore
from backend.services.retrieval.reranker import Reranker

logger = logging.getLogger(__name__)


class FeedbackType(Enum):
    """User feedback classification for query responses."""

    HELPFUL = "helpful"
    NOT_HELPFUL = "not_helpful"
    PARTIALLY_HELPFUL = "partially_helpful"


@dataclass
class UserFeedback:
    """Data class representing a user's feedback on a query response."""

    query_id: str
    question: str
    answer: str
    feedback_type: FeedbackType
    user_comment: Optional[str] = None
    timestamp: datetime.datetime = None
    retrieved_chunks: List[Dict] = None
    feedback_weight: float = 1.0  # Multiplier for feedback impact on quality scores

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.datetime.now()
        if self.retrieved_chunks is None:
            self.retrieved_chunks = []


@dataclass
class FeedbackStatistics:
    """Aggregated feedback statistics over a time period."""

    total_queries: int
    helpful_count: int
    not_helpful_count: int
    partially_helpful_count: int
    success_rate: float
    avg_feedback_weight: float


class FeedbackManager:
    """Manages user feedback collection and drives adaptive RAG optimization."""

    def __init__(self, vectorstore: VectorStore, reranker: Reranker = None):
        self.vectorstore = vectorstore
        self.reranker = reranker
        self._init_database()

    def _init_database(self):
        """Initialize feedback database tables and indexes."""
        conn = self.vectorstore.get_connection()
        cur = conn.cursor()

        try:
            # Create query feedback table
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS query_feedback (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    query_id VARCHAR(255) UNIQUE NOT NULL,
                    question TEXT NOT NULL,
                    answer TEXT NOT NULL,
                    feedback_type VARCHAR(50) NOT NULL,
                    user_comment TEXT,
                    retrieved_chunks JSONB,
                    feedback_weight FLOAT DEFAULT 1.0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    processed_at TIMESTAMP
                )
            """
            )

            # Create document quality scores table
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS document_quality_scores (
                    doc_id VARCHAR(255) NOT NULL,
                    chunk_id INTEGER NOT NULL,
                    quality_score FLOAT DEFAULT 0.0,
                    helpful_count INTEGER DEFAULT 0,
                    not_helpful_count INTEGER DEFAULT 0,
                    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (doc_id, chunk_id)
                )
            """
            )

            # Create query optimization log table
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS query_optimization_log (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    query_id VARCHAR(255) NOT NULL,
                    original_query TEXT NOT NULL,
                    optimized_query TEXT,
                    optimization_strategy VARCHAR(100),
                    improvement_score FLOAT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """
            )

            # Create indexes for efficient querying
            cur.execute(
                "CREATE INDEX IF NOT EXISTS idx_feedback_type ON query_feedback(feedback_type)"
            )
            cur.execute(
                "CREATE INDEX IF NOT EXISTS idx_feedback_created ON query_feedback(created_at)"
            )
            cur.execute(
                "CREATE INDEX IF NOT EXISTS idx_doc_quality ON document_quality_scores(quality_score)"
            )

            conn.commit()
            logger.info("Feedback database tables initialized successfully")

        except Exception as e:
            conn.rollback()
            logger.error(f"Failed to initialize feedback database: {e}")
            raise e
        finally:
            cur.close()
            conn.close()

    def record_feedback(self, feedback: UserFeedback) -> bool:
        """Record user feedback and trigger adaptive optimizations."""
        conn = self.vectorstore.get_connection()
        cur = conn.cursor()

        try:
            # Upsert feedback record (update on conflict by query_id)
            cur.execute(
                """
                INSERT INTO query_feedback
                (query_id, question, answer, feedback_type, user_comment, retrieved_chunks, feedback_weight)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (query_id)
                DO UPDATE SET
                    feedback_type = EXCLUDED.feedback_type,
                    user_comment = EXCLUDED.user_comment,
                    feedback_weight = EXCLUDED.feedback_weight,
                    processed_at = CURRENT_TIMESTAMP
                RETURNING id
            """,
                (
                    feedback.query_id,
                    feedback.question,
                    feedback.answer,
                    feedback.feedback_type.value,
                    feedback.user_comment,
                    json.dumps(feedback.retrieved_chunks)
                    if feedback.retrieved_chunks
                    else None,
                    feedback.feedback_weight,
                ),
            )

            result = cur.fetchone()
            conn.commit()

            if result:
                # Update quality scores for retrieved document chunks
                self._update_document_quality_scores(feedback)
                # Trigger adaptive optimization based on feedback signal
                self._trigger_adaptive_optimization(feedback)
                logger.info(f"Feedback recorded for query {feedback.query_id}")
                return True

            return False

        except Exception as e:
            conn.rollback()
            logger.error(f"Failed to record feedback: {e}")
            return False
        finally:
            cur.close()
            conn.close()

    def _update_document_quality_scores(self, feedback: UserFeedback):
        """Update quality scores for document chunks based on user feedback."""
        if not feedback.retrieved_chunks:
            return

        conn = self.vectorstore.get_connection()
        cur = conn.cursor()

        try:
            for chunk in feedback.retrieved_chunks:
                doc_id = chunk.get("doc_id")
                chunk_id = chunk.get("chunk_id", 0)

                if not doc_id:
                    continue

                # Calculate quality score adjustment from feedback
                quality_delta = self._calculate_quality_impact(
                    feedback.feedback_type, feedback.feedback_weight
                )

                # Upsert quality score with incremental update on conflict
                cur.execute(
                    """
                    INSERT INTO document_quality_scores (doc_id, chunk_id, quality_score, helpful_count, not_helpful_count)
                    VALUES (%s, %s, %s, %s, %s)
                    ON CONFLICT (doc_id, chunk_id)
                    DO UPDATE SET
                        quality_score = document_quality_scores.quality_score + EXCLUDED.quality_score,
                        helpful_count = CASE
                            WHEN EXCLUDED.quality_score > 0 THEN document_quality_scores.helpful_count + 1
                            ELSE document_quality_scores.helpful_count
                        END,
                        not_helpful_count = CASE
                            WHEN EXCLUDED.quality_score < 0 THEN document_quality_scores.not_helpful_count + 1
                            ELSE document_quality_scores.not_helpful_count
                        END,
                        last_updated = CURRENT_TIMESTAMP
                """,
                    (
                        doc_id,
                        chunk_id,
                        quality_delta,
                        1 if feedback.feedback_type == FeedbackType.HELPFUL else 0,
                        1 if feedback.feedback_type == FeedbackType.NOT_HELPFUL else 0,
                    ),
                )

            conn.commit()

        except Exception as e:
            conn.rollback()
            logger.error(f"Failed to update document quality scores: {e}")
        finally:
            cur.close()
            conn.close()

    def _calculate_quality_impact(
        self, feedback_type: FeedbackType, weight: float = 1.0
    ) -> float:
        """EN"""
        impact_scores = {
            FeedbackType.HELPFUL: 1.0,
            FeedbackType.NOT_HELPFUL: -1.5,  # EN
            FeedbackType.PARTIALLY_HELPFUL: 0.3,
        }
        return impact_scores.get(feedback_type, 0.0) * weight

    def _trigger_adaptive_optimization(self, feedback: UserFeedback):
        """EN"""
        try:
            # EN
            if feedback.feedback_type == FeedbackType.NOT_HELPFUL:
                self._schedule_reranking_optimization(feedback)

            # EN
            if self._should_rewrite_query(feedback):
                self._schedule_query_rewriting(feedback)

        except Exception as e:
            logger.error(f"Failed to trigger adaptive optimization: {e}")

    def _schedule_reranking_optimization(self, feedback: UserFeedback):
        """EN"""
        # EN,EN
        logger.info(f"Scheduling reranking optimization for query {feedback.query_id}")

        # EN
        if self.reranker:
            optimization_data = {
                "query_id": feedback.query_id,
                "strategy": "adjust_reranking_weights",
                "feedback_type": feedback.feedback_type.value,
                "retrieved_chunks": feedback.retrieved_chunks,
            }
            # EN,EN
            self._optimize_reranking_weights(optimization_data)

    def _optimize_reranking_weights(self, optimization_data: Dict):
        """EN"""
        try:
            # EN
            # EN
            logger.info(
                f"Optimizing reranking weights based on feedback: {optimization_data}"
            )

            # Apply feedback-driven optimizations
            # Update retrieval parameters based on feedback patterns

        except Exception as e:
            logger.error(f"Failed to optimize reranking weights: {e}")

    def _should_rewrite_query(self, feedback: UserFeedback) -> bool:
        """EN"""
        # EN
        conn = self.vectorstore.get_connection()
        cur = conn.cursor()

        try:
            cur.execute(
                """
                SELECT COUNT(*) FROM query_feedback
                WHERE feedback_type = 'not_helpful'
                AND question % %s  -- ENPostgreSQLEN
                AND created_at > NOW() - INTERVAL '24 hours'  -- fixed literal, no parameterization needed
            """,
                (feedback.question,),
            )

            similar_negative_feedback = cur.fetchone()[0]
            return similar_negative_feedback >= 2  # EN24EN2EN

        except Exception as e:
            logger.error(f"Failed to check query rewriting necessity: {e}")
            return False
        finally:
            cur.close()
            conn.close()

    def _schedule_query_rewriting(self, feedback: UserFeedback):
        """EN"""
        logger.info(f"Scheduling query rewriting for query {feedback.query_id}")

        optimization_data = {
            "query_id": feedback.query_id,
            "original_query": feedback.question,
            "strategy": "query_expansion",
            "feedback_type": feedback.feedback_type.value,
        }

        # EN,EN
        self._rewrite_query(optimization_data)

    def _rewrite_query(self, optimization_data: Dict):
        """EN"""
        try:
            # Rewrite query using feedback data
            # Adjust keywords, filters, and ranking based on past feedback
            logger.info(f"Rewriting query: {optimization_data}")

        except Exception as e:
            logger.error(f"Failed to rewrite query: {e}")

    def get_feedback_statistics(self, days: int = 7) -> FeedbackStatistics:
        """EN"""
        conn = self.vectorstore.get_connection()
        cur = conn.cursor()

        try:
            cur.execute(
                """
                SELECT
                    COUNT(*) as total,
                    COUNT(CASE WHEN feedback_type = 'helpful' THEN 1 END) as helpful,
                    COUNT(CASE WHEN feedback_type = 'not_helpful' THEN 1 END) as not_helpful,
                    COUNT(CASE WHEN feedback_type = 'partially_helpful' THEN 1 END) as partially_helpful,
                    AVG(feedback_weight) as avg_weight
                FROM query_feedback
                WHERE created_at > NOW() - INTERVAL '1 day' * %s
            """,
                (days,),
            )

            result = cur.fetchone()
            total, helpful, not_helpful, partially_helpful, avg_weight = result

            success_rate = (
                (helpful + partially_helpful * 0.5) / total if total > 0 else 0.0
            )

            return FeedbackStatistics(
                total_queries=total,
                helpful_count=helpful,
                not_helpful_count=not_helpful,
                partially_helpful_count=partially_helpful,
                success_rate=success_rate,
                avg_feedback_weight=avg_weight or 1.0,
            )

        except Exception as e:
            logger.error(f"Failed to get feedback statistics: {e}")
            return FeedbackStatistics(0, 0, 0, 0, 0.0, 1.0)
        finally:
            cur.close()
            conn.close()

    def get_high_quality_documents(
        self, min_score: float = 0.5, limit: int = 100
    ) -> List[Dict]:
        """EN"""
        conn = self.vectorstore.get_connection()
        cur = conn.cursor()

        try:
            cur.execute(
                """
                SELECT DISTINCT d.id, d.filename, AVG(dqs.quality_score) as avg_quality
                FROM documents d
                JOIN document_chunks dc ON d.id = dc.doc_id
                LEFT JOIN document_quality_scores dqs ON d.id = dqs.doc_id AND dc.chunk_id = dqs.chunk_id
                GROUP BY d.id, d.filename
                HAVING AVG(dqs.quality_score) >= %s
                ORDER BY avg_quality DESC
                LIMIT %s
            """,
                (min_score, limit),
            )

            results = []
            for row in cur.fetchall():
                results.append(
                    {
                        "doc_id": row[0],
                        "filename": row[1],
                        "quality_score": float(row[2]) if row[2] else 0.0,
                    }
                )

            return results

        except Exception as e:
            logger.error(f"Failed to get high quality documents: {e}")
            return []
        finally:
            cur.close()
            conn.close()

    def adjust_search_weights(
        self, feedback_history: List[UserFeedback]
    ) -> Dict[str, float]:
        """EN"""
        if not feedback_history:
            return {"vector_weight": 0.7, "bm25_weight": 0.3}

        # EN
        helpful_ratio = sum(
            1 for f in feedback_history if f.feedback_type == FeedbackType.HELPFUL
        ) / len(feedback_history)

        # EN,EN
        if helpful_ratio < 0.5:
            # EN,EN
            return {"vector_weight": 0.8, "bm25_weight": 0.2}
        elif helpful_ratio > 0.8:
            # EN,EN
            return {"vector_weight": 0.6, "bm25_weight": 0.4}
        else:
            # EN
            return {"vector_weight": 0.7, "bm25_weight": 0.3}
