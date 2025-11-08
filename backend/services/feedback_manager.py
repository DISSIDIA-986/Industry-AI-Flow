"""
反馈机制模块 - RAG系统的用户反馈和自适应优化
"""

import uuid
import datetime
import json
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import logging
from backend.services.vectorstore import VectorStore
from backend.services.retrieval.reranker import Reranker
from backend.services.embedder import embed_single_text

logger = logging.getLogger(__name__)


class FeedbackType(Enum):
    """反馈类型"""
    HELPFUL = "helpful"
    NOT_HELPFUL = "not_helpful"
    PARTIALLY_HELPFUL = "partially_helpful"


@dataclass
class UserFeedback:
    """用户反馈数据结构"""
    query_id: str
    question: str
    answer: str
    feedback_type: FeedbackType
    user_comment: Optional[str] = None
    timestamp: datetime.datetime = None
    retrieved_chunks: List[Dict] = None
    feedback_weight: float = 1.0  # 反馈权重

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.datetime.now()
        if self.retrieved_chunks is None:
            self.retrieved_chunks = []


@dataclass
class FeedbackStatistics:
    """反馈统计信息"""
    total_queries: int
    helpful_count: int
    not_helpful_count: int
    partially_helpful_count: int
    success_rate: float
    avg_feedback_weight: float


class FeedbackManager:
    """反馈管理器 - 处理用户反馈并触发自适应优化"""

    def __init__(self, vectorstore: VectorStore, reranker: Reranker = None):
        self.vectorstore = vectorstore
        self.reranker = reranker
        self._init_database()

    def _init_database(self):
        """初始化反馈相关的数据库表"""
        conn = self.vectorstore.get_connection()
        cur = conn.cursor()

        try:
            # 创建反馈表
            cur.execute("""
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
            """)

            # 创建文档质量评分表
            cur.execute("""
                CREATE TABLE IF NOT EXISTS document_quality_scores (
                    doc_id VARCHAR(255) NOT NULL,
                    chunk_id INTEGER NOT NULL,
                    quality_score FLOAT DEFAULT 0.0,
                    helpful_count INTEGER DEFAULT 0,
                    not_helpful_count INTEGER DEFAULT 0,
                    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (doc_id, chunk_id)
                )
            """)

            # 创建查询优化记录表
            cur.execute("""
                CREATE TABLE IF NOT EXISTS query_optimization_log (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    query_id VARCHAR(255) NOT NULL,
                    original_query TEXT NOT NULL,
                    optimized_query TEXT,
                    optimization_strategy VARCHAR(100),
                    improvement_score FLOAT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # 创建索引
            cur.execute("CREATE INDEX IF NOT EXISTS idx_feedback_type ON query_feedback(feedback_type)")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_feedback_created ON query_feedback(created_at)")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_doc_quality ON document_quality_scores(quality_score)")

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
        """记录用户反馈"""
        conn = self.vectorstore.get_connection()
        cur = conn.cursor()

        try:
            # 插入反馈记录
            cur.execute("""
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
            """, (
                feedback.query_id,
                feedback.question,
                feedback.answer,
                feedback.feedback_type.value,
                feedback.user_comment,
                json.dumps(feedback.retrieved_chunks) if feedback.retrieved_chunks else None,
                feedback.feedback_weight
            ))

            result = cur.fetchone()
            conn.commit()

            if result:
                # 更新文档质量评分
                self._update_document_quality_scores(feedback)
                # 触发自适应优化
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
        """更新文档质量评分"""
        if not feedback.retrieved_chunks:
            return

        conn = self.vectorstore.get_connection()
        cur = conn.cursor()

        try:
            for chunk in feedback.retrieved_chunks:
                doc_id = chunk.get('doc_id')
                chunk_id = chunk.get('chunk_id', 0)

                if not doc_id:
                    continue

                # 计算反馈对文档质量的影响
                quality_delta = self._calculate_quality_impact(feedback.feedback_type, feedback.feedback_weight)

                # 更新文档质量评分
                cur.execute("""
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
                """, (doc_id, chunk_id, quality_delta,
                      1 if feedback.feedback_type == FeedbackType.HELPFUL else 0,
                      1 if feedback.feedback_type == FeedbackType.NOT_HELPFUL else 0))

            conn.commit()

        except Exception as e:
            conn.rollback()
            logger.error(f"Failed to update document quality scores: {e}")
        finally:
            cur.close()
            conn.close()

    def _calculate_quality_impact(self, feedback_type: FeedbackType, weight: float = 1.0) -> float:
        """计算反馈对文档质量的影响分数"""
        impact_scores = {
            FeedbackType.HELPFUL: 1.0,
            FeedbackType.NOT_HELPFUL: -1.5,  # 负面反馈权重更高
            FeedbackType.PARTIALLY_HELPFUL: 0.3
        }
        return impact_scores.get(feedback_type, 0.0) * weight

    def _trigger_adaptive_optimization(self, feedback: UserFeedback):
        """触发自适应优化"""
        try:
            # 检查是否需要触发重排序优化
            if feedback.feedback_type == FeedbackType.NOT_HELPFUL:
                self._schedule_reranking_optimization(feedback)

            # 检查是否需要查询重写
            if self._should_rewrite_query(feedback):
                self._schedule_query_rewriting(feedback)

        except Exception as e:
            logger.error(f"Failed to trigger adaptive optimization: {e}")

    def _schedule_reranking_optimization(self, feedback: UserFeedback):
        """安排重排序优化"""
        # 这里可以实现异步任务队列，当前简单实现
        logger.info(f"Scheduling reranking optimization for query {feedback.query_id}")

        # 基于负面反馈调整重排序权重
        if self.reranker:
            optimization_data = {
                'query_id': feedback.query_id,
                'strategy': 'adjust_reranking_weights',
                'feedback_type': feedback.feedback_type.value,
                'retrieved_chunks': feedback.retrieved_chunks
            }
            # 在实际应用中，这里应该发送到任务队列
            self._optimize_reranking_weights(optimization_data)

    def _optimize_reranking_weights(self, optimization_data: Dict):
        """优化重排序权重"""
        try:
            # 基于反馈调整重排序模型的权重
            # 这里可以实现更复杂的机器学习优化逻辑
            logger.info(f"Optimizing reranking weights based on feedback: {optimization_data}")

            # 简单实现：调整相似度和相关性权重
            # 实际应用中可以使用更复杂的在线学习算法

        except Exception as e:
            logger.error(f"Failed to optimize reranking weights: {e}")

    def _should_rewrite_query(self, feedback: UserFeedback) -> bool:
        """判断是否需要重写查询"""
        # 检查最近是否有类似的负面反馈
        conn = self.vectorstore.get_connection()
        cur = conn.cursor()

        try:
            cur.execute("""
                SELECT COUNT(*) FROM query_feedback
                WHERE feedback_type = 'not_helpful'
                AND question % %s  -- 使用PostgreSQL的模糊匹配
                AND created_at > NOW() - INTERVAL '24 hours'
            """, (feedback.question,))

            similar_negative_feedback = cur.fetchone()[0]
            return similar_negative_feedback >= 2  # 如果24小时内有2次以上类似负面反馈

        except Exception as e:
            logger.error(f"Failed to check query rewriting necessity: {e}")
            return False
        finally:
            cur.close()
            conn.close()

    def _schedule_query_rewriting(self, feedback: UserFeedback):
        """安排查询重写"""
        logger.info(f"Scheduling query rewriting for query {feedback.query_id}")

        optimization_data = {
            'query_id': feedback.query_id,
            'original_query': feedback.question,
            'strategy': 'query_expansion',
            'feedback_type': feedback.feedback_type.value
        }

        # 在实际应用中，这里应该发送到任务队列
        self._rewrite_query(optimization_data)

    def _rewrite_query(self, optimization_data: Dict):
        """重写查询以提高检索效果"""
        try:
            # 实现查询扩展和重写逻辑
            # 例如：添加同义词、扩展关键词等
            logger.info(f"Rewriting query: {optimization_data}")

        except Exception as e:
            logger.error(f"Failed to rewrite query: {e}")

    def get_feedback_statistics(self, days: int = 7) -> FeedbackStatistics:
        """获取反馈统计信息"""
        conn = self.vectorstore.get_connection()
        cur = conn.cursor()

        try:
            cur.execute("""
                SELECT
                    COUNT(*) as total,
                    COUNT(CASE WHEN feedback_type = 'helpful' THEN 1 END) as helpful,
                    COUNT(CASE WHEN feedback_type = 'not_helpful' THEN 1 END) as not_helpful,
                    COUNT(CASE WHEN feedback_type = 'partially_helpful' THEN 1 END) as partially_helpful,
                    AVG(feedback_weight) as avg_weight
                FROM query_feedback
                WHERE created_at > NOW() - INTERVAL '%s days'
            """, (days,))

            result = cur.fetchone()
            total, helpful, not_helpful, partially_helpful, avg_weight = result

            success_rate = (helpful + partially_helpful * 0.5) / total if total > 0 else 0.0

            return FeedbackStatistics(
                total_queries=total,
                helpful_count=helpful,
                not_helpful_count=not_helpful,
                partially_helpful_count=partially_helpful,
                success_rate=success_rate,
                avg_feedback_weight=avg_weight or 1.0
            )

        except Exception as e:
            logger.error(f"Failed to get feedback statistics: {e}")
            return FeedbackStatistics(0, 0, 0, 0, 0.0, 1.0)
        finally:
            cur.close()
            conn.close()

    def get_high_quality_documents(self, min_score: float = 0.5, limit: int = 100) -> List[Dict]:
        """获取高质量文档列表"""
        conn = self.vectorstore.get_connection()
        cur = conn.cursor()

        try:
            cur.execute("""
                SELECT DISTINCT d.id, d.filename, AVG(dqs.quality_score) as avg_quality
                FROM documents d
                JOIN document_chunks dc ON d.id = dc.doc_id
                LEFT JOIN document_quality_scores dqs ON d.id = dqs.doc_id AND dc.chunk_id = dqs.chunk_id
                GROUP BY d.id, d.filename
                HAVING AVG(dqs.quality_score) >= %s
                ORDER BY avg_quality DESC
                LIMIT %s
            """, (min_score, limit))

            results = []
            for row in cur.fetchall():
                results.append({
                    'doc_id': row[0],
                    'filename': row[1],
                    'quality_score': float(row[2]) if row[2] else 0.0
                })

            return results

        except Exception as e:
            logger.error(f"Failed to get high quality documents: {e}")
            return []
        finally:
            cur.close()
            conn.close()

    def adjust_search_weights(self, feedback_history: List[UserFeedback]) -> Dict[str, float]:
        """基于反馈历史调整搜索权重"""
        if not feedback_history:
            return {'vector_weight': 0.7, 'bm25_weight': 0.3}

        # 分析反馈模式并调整权重
        helpful_ratio = sum(1 for f in feedback_history if f.feedback_type == FeedbackType.HELPFUL) / len(feedback_history)

        # 如果成功率低，可能需要调整检索策略
        if helpful_ratio < 0.5:
            # 增加向量搜索权重，可能语义理解更重要
            return {'vector_weight': 0.8, 'bm25_weight': 0.2}
        elif helpful_ratio > 0.8:
            # 成功率高，可以保持当前策略或略微增加关键词权重
            return {'vector_weight': 0.6, 'bm25_weight': 0.4}
        else:
            # 默认平衡策略
            return {'vector_weight': 0.7, 'bm25_weight': 0.3}