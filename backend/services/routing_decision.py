"""
路由决策服务
基于意图分类结果和置信度，智能路由到对应的Agent
"""

import asyncio
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple, Union

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class RoutingPath(str, Enum):
    """路由路径枚举"""

    DIRECT_ROUTING = "direct"  # 直接路由
    CLARIFICATION = "clarification"  # 澄清流程
    FALLBACK = "fallback"  # 回退方案
    ESCALATION = "escalation"  # 升级处理


class AgentType(str, Enum):
    """Agent类型枚举"""

    RAG_AGENT = "rag_agent"
    DATA_ANALYSIS_AGENT = "data_analysis_agent"
    DOCUMENT_PROCESSING_AGENT = "document_processing_agent"
    CODE_EXECUTION_AGENT = "code_execution_agent"
    GENERAL_AGENT = "general_agent"
    CLARIFICATION_AGENT = "clarification_agent"


@dataclass
class RoutingDecision:
    """路由决策结果"""

    selected_agent: AgentType
    routing_path: RoutingPath
    confidence: float
    reasoning: str
    parameters: Dict[str, Any] = field(default_factory=dict)
    fallback_options: List[AgentType] = field(default_factory=list)
    estimated_processing_time: Optional[int] = None
    requires_clarification: bool = False
    clarification_context: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "selected_agent": self.selected_agent.value,
            "routing_path": self.routing_path.value,
            "confidence": self.confidence,
            "reasoning": self.reasoning,
            "parameters": self.parameters,
            "fallback_options": [agent.value for agent in self.fallback_options],
            "estimated_processing_time": self.estimated_processing_time,
            "requires_clarification": self.requires_clarification,
            "clarification_context": self.clarification_context,
        }


@dataclass
class SystemStatus:
    """系统状态信息"""

    agent_availability: Dict[AgentType, bool] = field(default_factory=dict)
    system_load: float = 0.0
    active_sessions: int = 0
    queue_lengths: Dict[AgentType, int] = field(default_factory=dict)
    average_response_times: Dict[AgentType, float] = field(default_factory=dict)

    def get_available_agents(self) -> List[AgentType]:
        """获取可用的Agent列表"""
        return [
            agent for agent, available in self.agent_availability.items() if available
        ]

    def get_least_loaded_agent(
        self, candidates: List[AgentType]
    ) -> Optional[AgentType]:
        """从候选Agent中选择负载最低的"""
        if not candidates:
            return None

        available_candidates = [
            agent for agent in candidates if self.agent_availability.get(agent, False)
        ]
        if not available_candidates:
            return None

        # 基于队列长度和平均响应时间选择最优Agent
        best_agent = None
        best_score = float("inf")

        for agent in available_candidates:
            queue_score = self.queue_lengths.get(agent, 0)
            response_score = self.average_response_times.get(agent, 0)
            combined_score = queue_score * 0.7 + response_score * 0.3

            if combined_score < best_score:
                best_score = combined_score
                best_agent = agent

        return best_agent


class RoutingDecisionEngine:
    """路由决策引擎"""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        初始化路由决策引擎

        Args:
            config: 配置参数
        """
        self.config = config or {}

        # 置信度阈值
        self.confidence_thresholds = self.config.get(
            "confidence_thresholds",
            {
                "high": 0.8,  # 高置信度，直接路由
                "medium": 0.6,  # 中等置信度，需要验证
                "low": 0.4,  # 低置信度，需要澄清
            },
        )

        # Agent配置
        self.agent_config = self.config.get(
            "agent_config",
            {
                AgentType.RAG_AGENT: {
                    "max_response_time": 30,
                    "retry_count": 2,
                    "priority": 1,
                    "capabilities": ["knowledge_retrieval", "semantic_search"],
                },
                AgentType.DATA_ANALYSIS_AGENT: {
                    "max_response_time": 120,
                    "retry_count": 1,
                    "priority": 2,
                    "capabilities": ["data_analysis", "statistics", "visualization"],
                },
                AgentType.DOCUMENT_PROCESSING_AGENT: {
                    "max_response_time": 60,
                    "retry_count": 2,
                    "priority": 2,
                    "capabilities": ["ocr", "text_extraction", "document_parsing"],
                },
                AgentType.CODE_EXECUTION_AGENT: {
                    "max_response_time": 90,
                    "retry_count": 1,
                    "priority": 3,
                    "capabilities": [
                        "code_execution",
                        "computation",
                        "algorithm_testing",
                    ],
                },
                AgentType.GENERAL_AGENT: {
                    "max_response_time": 45,
                    "retry_count": 3,
                    "priority": 4,
                    "capabilities": ["general_qa", "fallback_handling"],
                },
            },
        )

        # 路由规则
        self.routing_rules = self.config.get(
            "routing_rules",
            {
                "direct_routing_threshold": 0.8,
                "clarification_threshold": 0.5,
                "enable_load_balancing": True,
                "enable_fallback": True,
                "max_fallback_attempts": 3,
            },
        )

        # 系统状态模拟
        self.system_status = SystemStatus()
        self._initialize_system_status()

        # 路由统计
        self.routing_stats = {
            "total_routes": 0,
            "direct_routes": 0,
            "clarification_routes": 0,
            "fallback_routes": 0,
            "agent_usage": {agent: 0 for agent in AgentType},
        }

        logger.info("路由决策引擎初始化完成")

    def _initialize_system_status(self):
        """初始化系统状态"""
        # 所有Agent默认可用
        for agent in AgentType:
            self.system_status.agent_availability[agent] = True

        # 初始化队列长度（模拟）
        for agent in AgentType:
            self.system_status.queue_lengths[agent] = 0

        # 初始化平均响应时间
        for agent in AgentType:
            config = self.agent_config.get(agent, {})
            self.system_status.average_response_times[agent] = (
                config.get("max_response_time", 60) * 0.5
            )

    async def make_routing_decision(
        self,
        intent_result: Dict[str, Any],
        context: Dict[str, Any],
        user_preferences: Optional[Dict[str, Any]] = None,
    ) -> RoutingDecision:
        """
        做出路由决策

        Args:
            intent_result: 意图分类结果
            context: 上下文信息
            user_preferences: 用户偏好

        Returns:
            RoutingDecision: 路由决策结果
        """
        try:
            # 提取关键信息
            intent = intent_result.get("intent", "knowledge_retrieval")
            confidence = float(intent_result.get("confidence", 0.0))
            reasoning = intent_result.get("reasoning", "")

            # 基于意图选择主要Agent
            primary_agent = self._map_intent_to_agent(intent)

            # 获取可用的备选Agent
            fallback_agents = self._get_fallback_agents(primary_agent, intent)

            # 置信度评估
            routing_path = self._determine_routing_path(confidence, intent_result)

            # 负载均衡考虑
            if self.routing_rules.get("enable_load_balancing", True):
                candidates = [primary_agent] + fallback_agents
                selected_agent = (
                    self.system_status.get_least_loaded_agent(candidates)
                    or primary_agent
                )
            else:
                selected_agent = primary_agent

            # 设置路由参数
            parameters = self._build_routing_parameters(
                selected_agent, intent_result, context, user_preferences
            )

            # 估算处理时间
            estimated_time = self._estimate_processing_time(selected_agent, context)

            # 是否需要澄清
            requires_clarification = routing_path == RoutingPath.CLARIFICATION
            clarification_context = None
            if requires_clarification:
                clarification_context = {
                    "possible_intents": self._get_possible_intents(intent_result),
                    "clarification_questions": self._generate_clarification_questions(
                        intent_result
                    ),
                    "user_context": context,
                }

            # 创建路由决策
            decision = RoutingDecision(
                selected_agent=selected_agent,
                routing_path=routing_path,
                confidence=confidence,
                reasoning=f"基于意图'{intent}'和置信度{confidence:.2f}选择{selected_agent.value}。{reasoning}",
                parameters=parameters,
                fallback_options=fallback_agents,
                estimated_processing_time=estimated_time,
                requires_clarification=requires_clarification,
                clarification_context=clarification_context,
            )

            # 更新统计
            self._update_routing_stats(decision)

            logger.info(
                f"路由决策完成: {selected_agent.value} (置信度: {confidence:.2f}, 路径: {routing_path.value})"
            )
            return decision

        except Exception as e:
            logger.error(f"路由决策失败: {str(e)}")
            # 回退到通用Agent
            return self._create_fallback_decision(intent_result, str(e))

    def _map_intent_to_agent(self, intent: str) -> AgentType:
        """将意图映射到Agent"""
        intent_mapping = {
            "knowledge_retrieval": AgentType.RAG_AGENT,
            "data_analysis": AgentType.DATA_ANALYSIS_AGENT,
            "cost_estimation": AgentType.DATA_ANALYSIS_AGENT,
            "document_processing": AgentType.DOCUMENT_PROCESSING_AGENT,
            "code_execution": AgentType.CODE_EXECUTION_AGENT,
        }
        return intent_mapping.get(intent, AgentType.GENERAL_AGENT)

    def _get_fallback_agents(
        self, primary_agent: AgentType, intent: str
    ) -> List[AgentType]:
        """获取备选Agent列表"""
        fallback_mapping = {
            AgentType.RAG_AGENT: [AgentType.GENERAL_AGENT],
            AgentType.DATA_ANALYSIS_AGENT: [
                AgentType.RAG_AGENT,
                AgentType.GENERAL_AGENT,
            ],
            AgentType.DOCUMENT_PROCESSING_AGENT: [
                AgentType.RAG_AGENT,
                AgentType.GENERAL_AGENT,
            ],
            AgentType.CODE_EXECUTION_AGENT: [
                AgentType.DATA_ANALYSIS_AGENT,
                AgentType.GENERAL_AGENT,
            ],
            AgentType.GENERAL_AGENT: [],
        }
        return fallback_mapping.get(primary_agent, [AgentType.GENERAL_AGENT])

    def _determine_routing_path(
        self, confidence: float, intent_result: Dict[str, Any]
    ) -> RoutingPath:
        """确定路由路径"""
        high_threshold = self.confidence_thresholds.get("high", 0.8)
        low_threshold = self.confidence_thresholds.get("low", 0.4)

        if confidence >= high_threshold:
            return RoutingPath.DIRECT_ROUTING
        elif confidence <= low_threshold:
            return RoutingPath.CLARIFICATION
        else:
            # 中等置信度，考虑其他因素
            uncertainty_factors = intent_result.get("uncertainty_factors", [])
            if len(uncertainty_factors) > 2:
                return RoutingPath.CLARIFICATION
            else:
                return RoutingPath.DIRECT_ROUTING

    def _build_routing_parameters(
        self,
        agent: AgentType,
        intent_result: Dict[str, Any],
        context: Dict[str, Any],
        user_preferences: Optional[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """构建路由参数"""
        base_params = {
            "timeout": self.agent_config[agent]["max_response_time"],
            "retry_count": self.agent_config[agent]["retry_count"],
            "priority": self.agent_config[agent]["priority"],
            "intent": intent_result.get("intent"),
            "confidence": intent_result.get("confidence"),
            "keywords": intent_result.get("keywords", []),
            "context_clues": intent_result.get("context_clues", []),
        }

        # 添加上下文信息
        if context:
            base_params["session_context"] = {
                "session_id": context.get("session_id"),
                "user_id": context.get("user_id"),
                "query_count": context.get("query_count", 1),
                "has_uploaded_files": context.get("has_uploaded_files", False),
            }

        # 添加用户偏好
        if user_preferences:
            base_params["user_preferences"] = user_preferences

        return base_params

    def _estimate_processing_time(
        self, agent: AgentType, context: Dict[str, Any]
    ) -> int:
        """估算处理时间"""
        base_time = self.agent_config[agent]["max_response_time"]

        # 根据上下文调整时间估算
        modifiers = 1.0

        # 如果有上传文件，可能需要更多时间
        if context.get("has_uploaded_files", False):
            if agent == AgentType.DATA_ANALYSIS_AGENT:
                modifiers *= 1.5  # 数据分析可能需要更长时间
            elif agent == AgentType.DOCUMENT_PROCESSING_AGENT:
                modifiers *= 1.3  # 文档处理时间适中

        # 会话复杂度
        query_count = context.get("query_count", 1)
        if query_count > 5:  # 复杂会话
            modifiers *= 1.2

        return int(base_time * modifiers)

    def _get_possible_intents(self, intent_result: Dict[str, Any]) -> List[str]:
        """获取可能的意图列表"""
        primary_intent = intent_result.get("intent")
        confidence = intent_result.get("confidence", 0.0)

        if confidence >= 0.8:
            return [primary_intent]

        # 根据关键词获取其他可能的意图
        keywords = intent_result.get("keywords", [])
        possible_intents = [primary_intent]

        # 简单的关键词到意图映射
        keyword_intent_mapping = {
            "数据": "data_analysis",
            "分析": "data_analysis",
            "图表": "data_analysis",
            "成本": "cost_estimation",
            "预算": "cost_estimation",
            "估算": "cost_estimation",
            "超支": "cost_estimation",
            "文档": "document_processing",
            "PDF": "document_processing",
            "图片": "document_processing",
            "代码": "code_execution",
            "运行": "code_execution",
            "计算": "code_execution",
        }

        for keyword in keywords:
            mapped_intent = keyword_intent_mapping.get(keyword)
            if mapped_intent and mapped_intent not in possible_intents:
                possible_intents.append(mapped_intent)

        return possible_intents[:3]  # 最多返回3个可能意图

    def _generate_clarification_questions(
        self, intent_result: Dict[str, Any]
    ) -> List[str]:
        """生成澄清问题"""
        intent = intent_result.get("intent")
        keywords = intent_result.get("keywords", [])

        # 基于意图的澄清问题
        clarification_templates = {
            "knowledge_retrieval": [
                "您是想了解具体的概念解释，还是需要查找特定的信息？",
                "您希望我帮您检索哪个领域的知识？",
                "您的问题更偏向于事实查询还是概念说明？",
            ],
            "data_analysis": [
                "您希望进行哪种类型的数据分析？是统计分析、可视化还是机器学习？",
                "您是否已经上传了需要分析的数据集？",
                "您的分析重点是什么？是探索性分析还是验证特定假设？",
            ],
            "document_processing": [
                "您需要处理什么类型的文档？是PDF文件、图片还是其他格式？",
                "您希望从文档中提取什么类型的内容？是文字、表格还是特定信息？",
                "您的文档是否包含需要OCR识别的扫描内容？",
            ],
            "code_execution": [
                "您希望运行什么类型的代码？是数据处理、算法实现还是特定计算？",
                "您是否有具体的编程语言偏好？",
                "您的代码执行是否需要特定的环境或依赖？",
            ],
        }

        questions = clarification_templates.get(
            intent, ["请您更详细地描述一下您的需求？", "您希望我帮您完成什么具体任务？"]
        )

        # 根据关键词调整问题
        if "图表" in keywords and intent == "data_analysis":
            questions.insert(0, "您是否需要创建数据可视化图表？")
        elif "PDF" in keywords and intent == "document_processing":
            questions.insert(0, "您需要处理PDF文档的什么内容？")

        return questions[:2]  # 最多返回2个问题

    def _update_routing_stats(self, decision: RoutingDecision):
        """更新路由统计"""
        self.routing_stats["total_routes"] += 1
        self.routing_stats["agent_usage"][decision.selected_agent] += 1

        if decision.routing_path == RoutingPath.DIRECT_ROUTING:
            self.routing_stats["direct_routes"] += 1
        elif decision.routing_path == RoutingPath.CLARIFICATION:
            self.routing_stats["clarification_routes"] += 1
        elif decision.routing_path == RoutingPath.FALLBACK:
            self.routing_stats["fallback_routes"] += 1

    def _create_fallback_decision(
        self, intent_result: Dict[str, Any], error: str
    ) -> RoutingDecision:
        """创建回退决策"""
        return RoutingDecision(
            selected_agent=AgentType.GENERAL_AGENT,
            routing_path=RoutingPath.FALLBACK,
            confidence=0.5,
            reasoning=f"路由决策失败，回退到通用Agent。错误信息: {error}",
            parameters={
                "timeout": self.agent_config[AgentType.GENERAL_AGENT][
                    "max_response_time"
                ],
                "retry_count": 3,
                "fallback_reason": error,
            },
            fallback_options=[],
            estimated_processing_time=45,
        )

    def get_routing_statistics(self) -> Dict[str, Any]:
        """获取路由统计信息"""
        total = self.routing_stats["total_routes"]
        if total == 0:
            return self.routing_stats

        # 计算比例
        stats = self.routing_stats.copy()
        stats["direct_routing_rate"] = self.routing_stats["direct_routes"] / total
        stats["clarification_rate"] = self.routing_stats["clarification_routes"] / total
        stats["fallback_rate"] = self.routing_stats["fallback_routes"] / total

        # Agent使用率
        stats["agent_usage_rates"] = {
            agent.value: count / total
            for agent, count in self.routing_stats["agent_usage"].items()
        }

        return stats

    def update_system_status(self, status_updates: Dict[str, Any]):
        """更新系统状态"""
        if "agent_availability" in status_updates:
            self.system_status.agent_availability.update(
                status_updates["agent_availability"]
            )

        if "system_load" in status_updates:
            self.system_status.system_load = status_updates["system_load"]

        if "active_sessions" in status_updates:
            self.system_status.active_sessions = status_updates["active_sessions"]

        if "queue_lengths" in status_updates:
            self.system_status.queue_lengths.update(status_updates["queue_lengths"])

        if "average_response_times" in status_updates:
            self.system_status.average_response_times.update(
                status_updates["average_response_times"]
            )

    async def health_check(self) -> Dict[str, Any]:
        """健康检查"""
        return {
            "status": "healthy",
            "total_routes": self.routing_stats["total_routes"],
            "available_agents": len(self.system_status.get_available_agents()),
            "system_load": self.system_status.system_load,
            "active_sessions": self.system_status.active_sessions,
            "routing_rules": self.routing_rules,
        }
