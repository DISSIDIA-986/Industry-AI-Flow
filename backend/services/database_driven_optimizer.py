"""
数据库驱动的RAG优化引擎 - 基于持久化数据的智能优化
"""

import datetime
import json
import logging
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
import numpy as np
from backend.services.session_manager import SessionManager
from backend.services.core.vectorstore import VectorStore
from backend.services.feedback_system.feedback_manager import FeedbackManager
from backend.config import settings

logger = logging.getLogger(__name__)


@dataclass
class OptimizationRecommendation:
    """优化建议"""
    optimization_type: str
    target_config: Dict[str, Any]
    expected_improvement: float
    confidence: float
    reasoning: str
    affected_queries: List[str]


class DatabaseDrivenOptimizer:
    """数据库驱动的RAG优化引擎"""

    def __init__(self, vectorstore: VectorStore):
        self.vectorstore = vectorstore
        self.session_manager = SessionManager(vectorstore)
        self.feedback_manager = FeedbackManager(vectorstore)

    def analyze_and_optimize(self, optimization_scope: str = "global") -> List[OptimizationRecommendation]:
        """
        分析并生成优化建议

        Args:
            optimization_scope: 优化范围 ("global", "session", "document_type")

        Returns:
            优化建议列表
        """
        recommendations = []

        try:
            # 1. 分析查询性能模式
            performance_recommendations = self._analyze_query_performance_patterns(optimization_scope)
            recommendations.extend(performance_recommendations)

            # 2. 分析反馈驱动的优化机会
            feedback_recommendations = self._analyze_feedback_driven_optimizations(optimization_scope)
            recommendations.extend(feedback_recommendations)

            # 3. 分析配置使用效率
            config_recommendations = self._analyze_configuration_efficiency(optimization_scope)
            recommendations.extend(config_recommendations)

            # 4. 分析文档质量和检索相关性
            doc_recommendations = self._analyze_document_quality_patterns(optimization_scope)
            recommendations.extend(doc_recommendations)

            # 按预期改善程度排序
            recommendations.sort(key=lambda x: x.expected_improvement, reverse=True)

            logger.info(f"Generated {len(recommendations)} optimization recommendations for scope: {optimization_scope}")
            return recommendations

        except Exception as e:
            logger.error(f"Error during optimization analysis: {e}")
            return []

    def _analyze_query_performance_patterns(self, scope: str) -> List[OptimizationRecommendation]:
        """分析查询性能模式"""
        recommendations = []

        try:
            # 获取性能分析数据
            analytics = self.session_manager.get_rag_performance_analytics(days=7)

            if not analytics.get('performance_summary'):
                return recommendations

            perf_summary = analytics['performance_summary']
            config_usage = analytics.get('configuration_usage', [])

            # 分析响应时间模式
            avg_response_time = perf_summary.get('avg_response_time')
            if avg_response_time and avg_response_time > 3.0:  # 超过3秒
                recommendations.append(OptimizationRecommendation(
                    optimization_type="response_time_optimization",
                    target_config={
                        "reduce_retrieval_k": True,
                        "enable_caching": True,
                        "optimize_embedding_cache": True
                    },
                    expected_improvement=min(0.3, (avg_response_time - 3.0) / avg_response_time),
                    confidence=0.8,
                    reasoning=f"Average response time {avg_response_time:.2f}s exceeds 3s threshold",
                    affected_queries=[]
                ))

            # 分析检索分数模式
            avg_retrieval_score = perf_summary.get('avg_retrieval_score')
            if avg_retrieval_score and avg_retrieval_score < 0.6:  # 检索分数过低
                # 分析最佳配置
                best_config = self._find_best_performing_config(config_usage)
                if best_config:
                    recommendations.append(OptimizationRecommendation(
                        optimization_type="retrieval_weight_adjustment",
                        target_config={
                            "vector_weight": best_config['vector_weight'],
                            "bm25_weight": best_config['bm25_weight']
                        },
                        expected_improvement=0.2,
                        confidence=0.7,
                        reasoning=f"Low retrieval score {avg_retrieval_score:.2f}, suggesting weight adjustment",
                        affected_queries=[]
                    ))

            # 分析重排序效果
            avg_reranking_score = perf_summary.get('avg_reranking_score')
            if avg_reranking_score and avg_reranking_score < 0.5:  # 重排序效果不佳
                recommendations.append(OptimizationRecommendation(
                    optimization_type="reranking_optimization",
                    target_config={
                        "reranking_model_tuning": True,
                        "increase_reranking_candidates": True,
                        "adjust_reranking_threshold": True
                    },
                    expected_improvement=0.15,
                    confidence=0.6,
                    reasoning=f"Low reranking score {avg_reranking_score:.2f} indicates model tuning needed",
                    affected_queries=[]
                ))

        except Exception as e:
            logger.error(f"Error analyzing query performance patterns: {e}")

        return recommendations

    def _analyze_feedback_driven_optimizations(self, scope: str) -> List[OptimizationRecommendation]:
        """分析反馈驱动的优化机会"""
        recommendations = []

        try:
            # 获取反馈统计
            feedback_stats = self.feedback_manager.get_feedback_statistics(days=7)

            if feedback_stats.total_queries < settings.min_feedback_for_optimization:
                return recommendations

            success_rate = feedback_stats.success_rate

            # 分析成功率模式
            if success_rate < 0.6:  # 成功率过低
                recommendations.append(OptimizationRecommendation(
                    optimization_type="comprehensive_retrieval_enhancement",
                    target_config={
                        "enable_query_expansion": True,
                        "increase_retrieval_depth": True,
                        "boost_high_quality_docs": True,
                        "adjust_semantic_threshold": True
                    },
                    expected_improvement=0.25,
                    confidence=0.8,
                    reasoning=f"Low success rate {success_rate:.2f} indicates need for comprehensive enhancement",
                    affected_queries=[]
                ))

            # 分析部分有帮助的反馈
            if feedback_stats.partially_helpful_count > feedback_stats.helpful_count:
                recommendations.append(OptimizationRecommendation(
                    optimization_type="answer_quality_refinement",
                    target_config={
                        "improve_context_compression": True,
                        "enhance_prompt_engineering": True,
                        "adjust_llm_temperature": 0.3
                    },
                    expected_improvement=0.2,
                    confidence=0.7,
                    reasoning="High partially_helpful count suggests answer refinement needed",
                    affected_queries=[]
                ))

            # 分析无帮助反馈的具体模式
            if feedback_stats.not_helpful_count > 0:
                # 获取具体的负面反馈查询
                negative_queries = self._get_negative_feedback_patterns()
                if negative_queries:
                    recommendations.append(OptimizationRecommendation(
                        optimization_type="targeted_query_optimization",
                        target_config={
                            "domain_specific_tuning": True,
                            "custom_embedding_fine_tuning": True,
                            "specialized_reranking": True
                        },
                        expected_improvement=0.3,
                        confidence=0.75,
                        reasoning=f"Identified {len(negative_queries)} problematic query patterns",
                        affected_queries=negative_queries
                    ))

        except Exception as e:
            logger.error(f"Error analyzing feedback-driven optimizations: {e}")

        return recommendations

    def _analyze_configuration_efficiency(self, scope: str) -> List[OptimizationRecommendation]:
        """分析配置使用效率"""
        recommendations = []

        try:
            # 获取自适应配置使用情况
            conn = self.vectorstore.get_connection()
            cur = conn.cursor()

            cur.execute("""
                SELECT
                    config_type,
                    config_key,
                    AVG(CAST(config_value->>'performance_score' AS FLOAT)) as avg_score,
                    COUNT(*) as usage_count,
                    MAX(CAST(config_value->>'performance_score' AS FLOAT)) as max_score
                FROM adaptive_configurations
                WHERE is_active = TRUE
                AND CAST(config_value->>'performance_score' AS FLOAT) IS NOT NULL
                GROUP BY config_type, config_key
                HAVING COUNT(*) > 5
                ORDER BY avg_score DESC
            """)

            config_analysis = cur.fetchall()
            cur.close()
            conn.close()

            if not config_analysis:
                return recommendations

            # 找出表现最好和最差的配置
            best_configs = [row for row in config_analysis if row[2] > 0.7]
            worst_configs = [row for row in config_analysis if row[2] < 0.4]

            # 为表现差的配置提供建议
            for config_type, config_key, avg_score, usage_count, max_score in worst_configs:
                # 找到对应类型的最佳配置
                best_match = next((row for row in best_configs if row[0] == config_type), None)
                if best_match:
                    recommendations.append(OptimizationRecommendation(
                        optimization_type=f"config_replacement_{config_type}",
                        target_config={
                            "replace_config": config_key,
                            "with_config": best_match[1],
                            "expected_score_improvement": best_match[2] - avg_score
                        },
                        expected_improvement=min(0.4, best_match[2] - avg_score),
                        confidence=0.8,
                        reasoning=f"Config {config_key} underperforming with score {avg_score:.2f}",
                        affected_queries=[]
                    ))

        except Exception as e:
            logger.error(f"Error analyzing configuration efficiency: {e}")

        return recommendations

    def _analyze_document_quality_patterns(self, scope: str) -> List[OptimizationRecommendation]:
        """分析文档质量模式"""
        recommendations = []

        try:
            # 获取低质量文档
            conn = self.vectorstore.get_connection()
            cur = conn.cursor()

            cur.execute("""
                SELECT
                    dqs.doc_id,
                    d.filename,
                    AVG(dqs.quality_score) as avg_quality,
                    SUM(dqs.not_helpful_count) as total_negative,
                    SUM(dqs.helpful_count) as total_positive
                FROM document_quality_scores dqs
                JOIN documents d ON dqs.doc_id = d.id
                GROUP BY dqs.doc_id, d.filename
                HAVING AVG(dqs.quality_score) < 0.3 AND SUM(dqs.not_helpful_count + dqs.helpful_count) > 5
                ORDER BY avg_quality ASC
                LIMIT 10
            """)

            low_quality_docs = cur.fetchall()
            cur.close()
            conn.close()

            if low_quality_docs:
                doc_ids = [row[0] for row in low_quality_docs]
                recommendations.append(OptimizationRecommendation(
                    optimization_type="document_quality_improvement",
                    target_config={
                        "document_ids": doc_ids,
                        "action": "reprocess_or_remove",
                        "quality_threshold": 0.3
                    },
                    expected_improvement=0.2,
                    confidence=0.75,
                    reasoning=f"Found {len(doc_ids)} consistently low-quality documents",
                    affected_queries=[]
                ))

            # 分析高质量文档模式
            cur = self.vectorstore.get_connection()
            cur = conn.cursor()

            cur.execute("""
                SELECT
                    dqs.doc_id,
                    d.filename,
                    AVG(dqs.quality_score) as avg_quality,
                    d.chunk_count
                FROM document_quality_scores dqs
                JOIN documents d ON dqs.doc_id = d.id
                GROUP BY dqs.doc_id, d.filename, d.chunk_count
                HAVING AVG(dqs.quality_score) > 0.8 AND d.chunk_count > 10
                ORDER BY avg_quality DESC
                LIMIT 20
            """)

            high_quality_docs = cur.fetchall()
            cur.close()
            conn.close()

            if high_quality_docs:
                high_quality_ids = [row[0] for row in high_quality_docs]
                recommendations.append(OptimizationRecommendation(
                    optimization_type="high_quality_document_boosting",
                    target_config={
                        "document_ids": high_quality_ids,
                        "action": "boost_retrieval_weight",
                        "boost_factor": 1.5
                    },
                    expected_improvement=0.15,
                    confidence=0.7,
                    reasoning=f"Found {len(high_quality_ids)} high-quality documents to boost",
                    affected_queries=[]
                ))

        except Exception as e:
            logger.error(f"Error analyzing document quality patterns: {e}")

        return recommendations

    def _find_best_performing_config(self, config_usage: List[Dict]) -> Optional[Dict]:
        """找出表现最佳的配置"""
        if not config_usage:
            return None

        # 按平均响应时间和使用次数找最佳配置
        best_config = None
        best_score = -1

        for config in config_usage:
            if config['avg_response_time'] and config['usage_count'] >= 3:
                # 综合评分：响应时间越低越好，使用次数越高越好
                score = config['usage_count'] / (config['avg_response_time'] + 1)
                if score > best_score:
                    best_score = score
                    best_config = config

        return best_config

    def _get_negative_feedback_patterns(self) -> List[str]:
        """获取负面反馈的查询模式"""
        try:
            conn = self.vectorstore.get_connection()
            cur = conn.cursor()

            cur.execute("""
                SELECT DISTINCT qf.question
                FROM query_feedback qf
                WHERE qf.feedback_type = 'not_helpful'
                AND qf.created_at > NOW() - INTERVAL '7 days'
                LIMIT 20
            """)

            negative_queries = [row[0] for row in cur.fetchall()]
            cur.close()
            conn.close()

            return negative_queries

        except Exception as e:
            logger.error(f"Error getting negative feedback patterns: {e}")
            return []

    def apply_optimization(self, recommendation: OptimizationRecommendation) -> bool:
        """应用优化建议"""
        try:
            logger.info(f"Applying optimization: {recommendation.optimization_type}")

            # 根据优化类型应用不同的优化策略
            if recommendation.optimization_type == "retrieval_weight_adjustment":
                return self._apply_retrieval_weight_optimization(recommendation)
            elif recommendation.optimization_type == "response_time_optimization":
                return self._apply_response_time_optimization(recommendation)
            elif recommendation.optimization_type == "reranking_optimization":
                return self._apply_reranking_optimization(recommendation)
            elif recommendation.optimization_type == "document_quality_improvement":
                return self._apply_document_quality_optimization(recommendation)
            elif recommendation.optimization_type == "high_quality_document_boosting":
                return self._apply_document_boosting_optimization(recommendation)
            else:
                logger.warning(f"Unknown optimization type: {recommendation.optimization_type}")
                return False

        except Exception as e:
            logger.error(f"Error applying optimization: {e}")
            return False

    def _apply_retrieval_weight_optimization(self, recommendation: OptimizationRecommendation) -> bool:
        """应用检索权重优化"""
        try:
            # 保存新的自适应配置
            config_value = recommendation.target_config
            self.session_manager.save_adaptive_config(
                config_type="retrieval_weights",
                config_key="vector_bm25_balance",
                config_value=config_value,
                performance_score=recommendation.expected_improvement
            )

            logger.info(f"Applied retrieval weight optimization: {config_value}")
            return True

        except Exception as e:
            logger.error(f"Error applying retrieval weight optimization: {e}")
            return False

    def _apply_response_time_optimization(self, recommendation: OptimizationRecommendation) -> bool:
        """应用响应时间优化"""
        try:
            config_value = recommendation.target_config
            self.session_manager.save_adaptive_config(
                config_type="performance_optimization",
                config_key="response_time_tuning",
                config_value=config_value,
                performance_score=recommendation.expected_improvement
            )

            logger.info(f"Applied response time optimization: {config_value}")
            return True

        except Exception as e:
            logger.error(f"Error applying response time optimization: {e}")
            return False

    def _apply_reranking_optimization(self, recommendation: OptimizationRecommendation) -> bool:
        """应用重排序优化"""
        try:
            config_value = recommendation.target_config
            self.session_manager.save_adaptive_config(
                config_type="reranking_optimization",
                config_key="model_tuning",
                config_value=config_value,
                performance_score=recommendation.expected_improvement
            )

            logger.info(f"Applied reranking optimization: {config_value}")
            return True

        except Exception as e:
            logger.error(f"Error applying reranking optimization: {e}")
            return False

    def _apply_document_quality_optimization(self, recommendation: OptimizationRecommendation) -> bool:
        """应用文档质量优化"""
        try:
            # 这里可以实现文档重新处理或删除的逻辑
            doc_ids = recommendation.target_config.get('document_ids', [])
            logger.info(f"Marked {len(doc_ids)} documents for quality improvement")

            # 触发文档重新处理任务
            for doc_id in doc_ids:
                self.session_manager.trigger_optimization(
                    trigger_type="document_reprocessing",
                    trigger_data={"doc_id": doc_id, "reason": "low_quality"}
                )

            return True

        except Exception as e:
            logger.error(f"Error applying document quality optimization: {e}")
            return False

    def _apply_document_boosting_optimization(self, recommendation: OptimizationRecommendation) -> bool:
        """应用文档提升优化"""
        try:
            doc_ids = recommendation.target_config.get('document_ids', [])
            boost_factor = recommendation.target_config.get('boost_factor', 1.5)

            # 保存文档提升配置
            config_value = {
                "document_ids": doc_ids,
                "boost_factor": boost_factor
            }

            self.session_manager.save_adaptive_config(
                config_type="document_boosting",
                config_key="high_quality_docs",
                config_value=config_value,
                performance_score=recommendation.expected_improvement
            )

            logger.info(f"Applied document boosting for {len(doc_ids)} documents with factor {boost_factor}")
            return True

        except Exception as e:
            logger.error(f"Error applying document boosting optimization: {e}")
            return False

    def process_pending_optimizations(self) -> int:
        """处理待处理的优化任务"""
        processed_count = 0

        try:
            pending_optimizations = self.session_manager.get_pending_optimizations(limit=20)

            for optimization in pending_optimizations:
                try:
                    trigger_id = optimization['id']
                    trigger_type = optimization['trigger_type']
                    trigger_data = optimization['trigger_data']

                    # 处理优化任务
                    if trigger_type == "document_reprocessing":
                        success = self._process_document_reprocessing(trigger_data)
                    elif trigger_type == "query_rewrite":
                        success = self._process_query_rewrite(trigger_data)
                    elif trigger_type == "config_update":
                        success = self._process_config_update(trigger_data)
                    else:
                        logger.warning(f"Unknown optimization trigger type: {trigger_type}")
                        continue

                    # 更新处理状态
                    status = "completed" if success else "failed"
                    result = {"processed": True, "trigger_type": trigger_type}
                    error_message = None if success else "Processing failed"

                    self.session_manager.update_optimization_status(
                        trigger_id, status, result, error_message
                    )

                    if success:
                        processed_count += 1

                except Exception as e:
                    logger.error(f"Error processing optimization {optimization['id']}: {e}")
                    self.session_manager.update_optimization_status(
                        optimization['id'], "failed", None, str(e)
                    )

        except Exception as e:
            logger.error(f"Error processing pending optimizations: {e}")

        return processed_count

    def _process_document_reprocessing(self, trigger_data: Dict) -> bool:
        """处理文档重新处理任务"""
        try:
            doc_id = trigger_data.get('doc_id')
            reason = trigger_data.get('reason', 'unknown')

            # 这里可以实现文档重新处理逻辑
            logger.info(f"Reprocessing document {doc_id} due to: {reason}")

            # 实际实现中，这里应该调用文档处理管道重新处理文档
            return True

        except Exception as e:
            logger.error(f"Error processing document reprocessing: {e}")
            return False

    def _process_query_rewrite(self, trigger_data: Dict) -> bool:
        """处理查询重写任务"""
        try:
            original_query = trigger_data.get('original_query')
            query_id = trigger_data.get('query_id')

            # 这里可以实现查询重写逻辑
            logger.info(f"Rewriting query {query_id}: {original_query}")

            return True

        except Exception as e:
            logger.error(f"Error processing query rewrite: {e}")
            return False

    def _process_config_update(self, trigger_data: Dict) -> bool:
        """处理配置更新任务"""
        try:
            config_type = trigger_data.get('config_type')
            config_updates = trigger_data.get('updates', {})

            # 应用配置更新
            for key, value in config_updates.items():
                self.session_manager.save_adaptive_config(
                    config_type=config_type,
                    config_key=key,
                    config_value=value
                )

            logger.info(f"Updated {config_type} configuration: {config_updates}")
            return True

        except Exception as e:
            logger.error(f"Error processing config update: {e}")
            return False