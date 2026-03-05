"""
EN
EN,ENAgent
"""

import asyncio
import json
import logging
import threading
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple, Union

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class RoutingPath(str, Enum):
    """EN"""

    DIRECT_ROUTING = "direct"  # EN
    CLARIFICATION = "clarification"  # EN
    FALLBACK = "fallback"  # EN
    ESCALATION = "escalation"  # EN


class AgentType(str, Enum):
    """AgentEN"""

    RAG_AGENT = "rag_agent"
    DATA_ANALYSIS_AGENT = "data_analysis_agent"
    DOCUMENT_PROCESSING_AGENT = "document_processing_agent"
    CODE_EXECUTION_AGENT = "code_execution_agent"
    COST_ESTIMATION_AGENT = "cost_estimation_agent"
    GENERAL_AGENT = "general_agent"
    CLARIFICATION_AGENT = "clarification_agent"


@dataclass
class RoutingDecision:
    """EN"""

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
        """EN"""
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
    """EN"""

    agent_availability: Dict[AgentType, bool] = field(default_factory=dict)
    system_load: float = 0.0
    active_sessions: int = 0
    queue_lengths: Dict[AgentType, int] = field(default_factory=dict)
    average_response_times: Dict[AgentType, float] = field(default_factory=dict)

    def get_available_agents(self) -> List[AgentType]:
        """ENAgentEN"""
        return [
            agent for agent, available in self.agent_availability.items() if available
        ]

    def get_least_loaded_agent(
        self, candidates: List[AgentType]
    ) -> Optional[AgentType]:
        """ENAgentEN"""
        if not candidates:
            return None

        available_candidates = [
            agent for agent in candidates if self.agent_availability.get(agent, False)
        ]
        if not available_candidates:
            return None

        # ENAgent
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
    """EN"""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        EN

        Args:
            config: EN
        """
        self.config = config or {}

        # EN
        self.confidence_thresholds = self.config.get(
            "confidence_thresholds",
            {
                "high": 0.8,  # EN,EN
                "medium": 0.6,  # EN,EN
                "low": 0.4,  # EN,EN
            },
        )

        # AgentEN
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
                AgentType.COST_ESTIMATION_AGENT: {
                    "max_response_time": 30,
                    "retry_count": 2,
                    "priority": 2,
                    "capabilities": ["cost_estimation", "budget_forecasting"],
                },
                AgentType.GENERAL_AGENT: {
                    "max_response_time": 45,
                    "retry_count": 3,
                    "priority": 4,
                    "capabilities": ["general_qa", "fallback_handling"],
                },
            },
        )

        # EN
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

        # EN
        self.system_status = SystemStatus()
        self._initialize_system_status()

        # EN
        self.routing_stats = {
            "total_routes": 0,
            "direct_routes": 0,
            "clarification_routes": 0,
            "fallback_routes": 0,
            "agent_usage": {agent: 0 for agent in AgentType},
        }
        self._routing_stats_lock = threading.Lock()

        logger.info("EN")

    def _initialize_system_status(self):
        """EN"""
        # ENAgentEN
        for agent in AgentType:
            self.system_status.agent_availability[agent] = True

        # EN(EN)
        for agent in AgentType:
            self.system_status.queue_lengths[agent] = 0

        # EN
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
        EN

        Args:
            intent_result: EN
            context: EN
            user_preferences: EN

        Returns:
            RoutingDecision: EN
        """
        try:
            # EN
            intent = intent_result.get("intent", "knowledge_retrieval")
            confidence = float(intent_result.get("confidence", 0.0))
            reasoning = intent_result.get("reasoning", "")

            # ENAgent
            primary_agent = self._map_intent_to_agent(intent)

            # ENAgent
            fallback_agents = self._get_fallback_agents(primary_agent, intent)

            # EN
            routing_path = self._determine_routing_path(confidence, intent_result)

            # Load balancing: only apply when confidence is below high threshold
            # to avoid overriding high-confidence intent routing decisions.
            high_threshold = self.confidence_thresholds.get("high", 0.8)
            if (
                self.routing_rules.get("enable_load_balancing", True)
                and confidence < high_threshold
            ):
                candidates = [primary_agent] + fallback_agents
                selected_agent = (
                    self.system_status.get_least_loaded_agent(candidates)
                    or primary_agent
                )
            else:
                selected_agent = primary_agent

            # EN
            parameters = self._build_routing_parameters(
                selected_agent, intent_result, context, user_preferences
            )

            # EN
            estimated_time = self._estimate_processing_time(selected_agent, context)

            # EN
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

            # EN
            decision = RoutingDecision(
                selected_agent=selected_agent,
                routing_path=routing_path,
                confidence=confidence,
                reasoning=f"EN'{intent}'EN{confidence:.2f}EN{selected_agent.value}.{reasoning}",
                parameters=parameters,
                fallback_options=fallback_agents,
                estimated_processing_time=estimated_time,
                requires_clarification=requires_clarification,
                clarification_context=clarification_context,
            )

            # EN
            self._update_routing_stats(decision)

            logger.info(
                f"EN: {selected_agent.value} (EN: {confidence:.2f}, EN: {routing_path.value})"
            )
            return decision

        except Exception as e:
            logger.error(f"EN: {str(e)}")
            # ENAgent
            return self._create_fallback_decision(intent_result, str(e))

    def _map_intent_to_agent(self, intent: str) -> AgentType:
        """ENAgent"""
        intent_mapping = {
            "knowledge_retrieval": AgentType.RAG_AGENT,
            "data_analysis": AgentType.DATA_ANALYSIS_AGENT,
            "cost_estimation": AgentType.COST_ESTIMATION_AGENT,
            "document_processing": AgentType.DOCUMENT_PROCESSING_AGENT,
            "code_execution": AgentType.CODE_EXECUTION_AGENT,
        }
        return intent_mapping.get(intent, AgentType.GENERAL_AGENT)

    def _get_fallback_agents(
        self, primary_agent: AgentType, intent: str
    ) -> List[AgentType]:
        """ENAgentEN"""
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
            AgentType.COST_ESTIMATION_AGENT: [
                AgentType.RAG_AGENT,
                AgentType.GENERAL_AGENT,
            ],
            AgentType.GENERAL_AGENT: [],
        }
        return fallback_mapping.get(primary_agent, [AgentType.GENERAL_AGENT])

    def _determine_routing_path(
        self, confidence: float, intent_result: Dict[str, Any]
    ) -> RoutingPath:
        """EN"""
        high_threshold = self.confidence_thresholds.get("high", 0.8)
        low_threshold = self.confidence_thresholds.get("low", 0.4)

        if confidence >= high_threshold:
            return RoutingPath.DIRECT_ROUTING
        elif confidence <= low_threshold:
            return RoutingPath.CLARIFICATION
        else:
            # EN,EN
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
        """EN"""
        base_params = {
            "timeout": self.agent_config[agent]["max_response_time"],
            "retry_count": self.agent_config[agent]["retry_count"],
            "priority": self.agent_config[agent]["priority"],
            "intent": intent_result.get("intent"),
            "confidence": intent_result.get("confidence"),
            "keywords": intent_result.get("keywords", []),
            "context_clues": intent_result.get("context_clues", []),
        }

        # EN
        if context:
            base_params["session_context"] = {
                "session_id": context.get("session_id"),
                "user_id": context.get("user_id"),
                "query_count": context.get("query_count", 1),
                "has_uploaded_files": context.get("has_uploaded_files", False),
            }

        # EN
        if user_preferences:
            base_params["user_preferences"] = user_preferences

        return base_params

    def _estimate_processing_time(
        self, agent: AgentType, context: Dict[str, Any]
    ) -> int:
        """EN"""
        base_time = self.agent_config[agent]["max_response_time"]

        # EN
        modifiers = 1.0

        # EN,EN
        if context.get("has_uploaded_files", False):
            if agent == AgentType.DATA_ANALYSIS_AGENT:
                modifiers *= 1.5  # EN
            elif agent == AgentType.DOCUMENT_PROCESSING_AGENT:
                modifiers *= 1.3  # EN

        # EN
        query_count = context.get("query_count", 1)
        if query_count > 5:  # EN
            modifiers *= 1.2

        return int(base_time * modifiers)

    def _get_possible_intents(self, intent_result: Dict[str, Any]) -> List[str]:
        """EN"""
        primary_intent = intent_result.get("intent")
        confidence = intent_result.get("confidence", 0.0)

        if confidence >= 0.8:
            return [primary_intent]

        # EN
        keywords = intent_result.get("keywords", [])
        possible_intents = [primary_intent]

        # EN
        keyword_intent_mapping = {
            "analyze": "data_analysis",
            "dataset": "data_analysis",
            "chart": "data_analysis",
            "cost": "cost_estimation",
            "budget": "cost_estimation",
            "estimate": "cost_estimation",
            "price": "cost_estimation",
            "document": "document_processing",
            "PDF": "document_processing",
            "upload": "document_processing",
            "code": "code_execution",
            "script": "code_execution",
            "execute": "code_execution",
        }

        for keyword in keywords:
            mapped_intent = keyword_intent_mapping.get(keyword)
            if mapped_intent and mapped_intent not in possible_intents:
                possible_intents.append(mapped_intent)

        return possible_intents[:3]  # EN3EN

    def _generate_clarification_questions(
        self, intent_result: Dict[str, Any]
    ) -> List[str]:
        """EN"""
        intent = intent_result.get("intent")
        keywords = intent_result.get("keywords", [])

        # EN
        clarification_templates = {
            "knowledge_retrieval": [
                "Could you be more specific about what information you're looking for?",
                "Are you asking about a specific standard or regulation?",
                "Would you like to search within a particular document?",
            ],
            "data_analysis": [
                "Do you have a dataset to analyze? If so, what format is it in?",
                "What specific analysis would you like to perform?",
                "Are you looking for summary statistics or a specific visualization?",
            ],
            "document_processing": [
                "What type of document would you like to process? For example, PDF, image, or spreadsheet?",
                "Would you like to extract text, data, or both from the document?",
                "Do you need OCR for scanned documents?",
            ],
            "code_execution": [
                "What programming task would you like to accomplish?",
                "Do you have existing code to run, or do you need code generated?",
                "What programming language should the code be in?",
            ],
        }

        questions = clarification_templates.get(
            intent, ["Could you clarify your request?", "What would you like me to help you with?"]
        )

        if "dataset" in keywords and intent == "data_analysis":
            questions.insert(0, "What analysis would you like to perform on your dataset?")
        elif "PDF" in keywords and intent == "document_processing":
            questions.insert(0, "Would you like to extract text from the PDF or process it another way?")

        return questions[:2]  # EN2EN

    def _update_routing_stats(self, decision: RoutingDecision):
        """EN"""
        with self._routing_stats_lock:
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
        """EN"""
        return RoutingDecision(
            selected_agent=AgentType.GENERAL_AGENT,
            routing_path=RoutingPath.FALLBACK,
            confidence=0.5,
            reasoning=f"Routing error, falling back to General Agent. Error: {error}",
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
        """EN"""
        with self._routing_stats_lock:
            total = self.routing_stats["total_routes"]
            if total == 0:
                return {
                    "total_routes": 0,
                    "direct_routes": 0,
                    "clarification_routes": 0,
                    "fallback_routes": 0,
                    "agent_usage": dict(self.routing_stats["agent_usage"]),
                }

            # EN
            stats = {
                "total_routes": total,
                "direct_routes": self.routing_stats["direct_routes"],
                "clarification_routes": self.routing_stats["clarification_routes"],
                "fallback_routes": self.routing_stats["fallback_routes"],
                "agent_usage": dict(self.routing_stats["agent_usage"]),
            }
            stats["direct_routing_rate"] = stats["direct_routes"] / total
            stats["clarification_rate"] = stats["clarification_routes"] / total
            stats["fallback_rate"] = stats["fallback_routes"] / total

            # AgentEN
            stats["agent_usage_rates"] = {
                agent.value: count / total
                for agent, count in stats["agent_usage"].items()
            }

            return stats

    def update_system_status(self, status_updates: Dict[str, Any]):
        """EN"""
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
        """EN"""
        return {
            "status": "healthy",
            "total_routes": self.routing_stats["total_routes"],
            "available_agents": len(self.system_status.get_available_agents()),
            "system_load": self.system_status.system_load,
            "active_sessions": self.system_status.active_sessions,
            "routing_rules": self.routing_rules,
        }
