"""
Routing Decision Engine

Determines the optimal agent to handle each user request based on intent classification.
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
    """Available routing paths for request processing."""

    DIRECT_ROUTING = "direct"  # High-confidence direct routing
    CLARIFICATION = "clarification"  # Low-confidence, needs user clarification
    FALLBACK = "fallback"  # Error fallback to general agent
    ESCALATION = "escalation"  # Escalation for complex requests


class AgentType(str, Enum):
    """Available agent types for request handling."""

    RAG_AGENT = "rag_agent"
    DATA_ANALYSIS_AGENT = "data_analysis_agent"
    DOCUMENT_PROCESSING_AGENT = "document_processing_agent"
    CODE_EXECUTION_AGENT = "code_execution_agent"
    COST_ESTIMATION_AGENT = "cost_estimation_agent"
    GENERAL_AGENT = "general_agent"
    CLARIFICATION_AGENT = "clarification_agent"


@dataclass
class RoutingDecision:
    """Encapsulates a routing decision including agent, path, confidence, and parameters."""

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
        """Convert routing decision to a dictionary representation."""
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
    """Tracks agent availability, system load, and queue status."""

    agent_availability: Dict[AgentType, bool] = field(default_factory=dict)
    system_load: float = 0.0
    active_sessions: int = 0
    queue_lengths: Dict[AgentType, int] = field(default_factory=dict)
    average_response_times: Dict[AgentType, float] = field(default_factory=dict)

    def get_available_agents(self) -> List[AgentType]:
        """Return list of currently available agents."""
        return [
            agent for agent, available in self.agent_availability.items() if available
        ]

    def get_least_loaded_agent(
        self, candidates: List[AgentType]
    ) -> Optional[AgentType]:
        """Return the least loaded agent from the candidate list."""
        if not candidates:
            return None

        available_candidates = [
            agent for agent in candidates if self.agent_availability.get(agent, False)
        ]
        if not available_candidates:
            return None

        # Select agent with lowest combined score (queue length + response time)
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
    """Engine that routes user requests to the optimal agent based on intent and system state."""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the routing decision engine.

        Args:
            config: Optional configuration dictionary for thresholds and agent settings.
        """
        self.config = config or {}

        # Confidence thresholds for routing decisions
        self.confidence_thresholds = self.config.get(
            "confidence_thresholds",
            {
                "high": 0.8,  # Direct routing without clarification
                "medium": 0.6,  # Route directly unless many uncertainty factors
                "low": 0.4,  # Below this, request clarification from user
            },
        )

        # Agent-specific configuration (timeouts, retries, priorities, capabilities)
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

        # Routing rules and thresholds
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

        # System status tracking
        self.system_status = SystemStatus()
        self._initialize_system_status()

        # Routing statistics
        self.routing_stats = {
            "total_routes": 0,
            "direct_routes": 0,
            "clarification_routes": 0,
            "fallback_routes": 0,
            "agent_usage": {agent: 0 for agent in AgentType},
        }
        self._routing_stats_lock = threading.Lock()

        logger.info("Routing decision engine initialized")

    def _initialize_system_status(self):
        """Initialize system status with default values for all agents."""
        # Set all agents as available by default
        for agent in AgentType:
            self.system_status.agent_availability[agent] = True

        # Initialize queue lengths to zero
        for agent in AgentType:
            self.system_status.queue_lengths[agent] = 0

        # Set initial average response times (50% of max configured time)
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
        Make a routing decision based on intent classification results.

        Args:
            intent_result: Intent classification output (intent, confidence, keywords).
            context: Session context (session_id, user_id, uploaded files, etc.).
            user_preferences: Optional user preferences for response style.

        Returns:
            RoutingDecision: The routing decision with selected agent and parameters.
        """
        try:
            # Extract intent classification results
            intent = intent_result.get("intent", "knowledge_retrieval")
            confidence = float(intent_result.get("confidence", 0.0))
            reasoning = intent_result.get("reasoning", "")

            # Map intent to primary agent
            primary_agent = self._map_intent_to_agent(intent)

            # Determine fallback agents
            fallback_agents = self._get_fallback_agents(primary_agent, intent)

            # Determine routing path based on confidence
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

            # Build routing parameters
            parameters = self._build_routing_parameters(
                selected_agent, intent_result, context, user_preferences
            )

            # Estimate processing time
            estimated_time = self._estimate_processing_time(selected_agent, context)

            # Check if clarification is needed
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

            # Create routing decision
            decision = RoutingDecision(
                selected_agent=selected_agent,
                routing_path=routing_path,
                confidence=confidence,
                reasoning=f"Intent '{intent}' with confidence {confidence:.2f} routed to {selected_agent.value}. {reasoning}",
                parameters=parameters,
                fallback_options=fallback_agents,
                estimated_processing_time=estimated_time,
                requires_clarification=requires_clarification,
                clarification_context=clarification_context,
            )

            # Update routing statistics
            self._update_routing_stats(decision)

            logger.info(
                f"Routing decision: {selected_agent.value} (confidence: {confidence:.2f}, path: {routing_path.value})"
            )
            return decision

        except Exception as e:
            logger.error(f"Routing decision failed: {str(e)}")
            # Fall back to general agent on error
            return self._create_fallback_decision(intent_result, str(e))

    def _map_intent_to_agent(self, intent: str) -> AgentType:
        """Map an intent string to the corresponding agent type."""
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
        """Get ordered list of fallback agents for the primary agent."""
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
        """Determine routing path based on confidence level and uncertainty factors."""
        high_threshold = self.confidence_thresholds.get("high", 0.8)
        low_threshold = self.confidence_thresholds.get("low", 0.4)

        if confidence >= high_threshold:
            return RoutingPath.DIRECT_ROUTING
        elif confidence <= low_threshold:
            return RoutingPath.CLARIFICATION
        else:
            # Medium confidence: check uncertainty factors to decide
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
        """Build routing parameters for the selected agent."""
        base_params = {
            "timeout": self.agent_config[agent]["max_response_time"],
            "retry_count": self.agent_config[agent]["retry_count"],
            "priority": self.agent_config[agent]["priority"],
            "intent": intent_result.get("intent"),
            "confidence": intent_result.get("confidence"),
            "keywords": intent_result.get("keywords", []),
            "context_clues": intent_result.get("context_clues", []),
        }

        # Add session context
        if context:
            base_params["session_context"] = {
                "session_id": context.get("session_id"),
                "user_id": context.get("user_id"),
                "query_count": context.get("query_count", 1),
                "has_uploaded_files": context.get("has_uploaded_files", False),
            }

        # Add user preferences if provided
        if user_preferences:
            base_params["user_preferences"] = user_preferences

        return base_params

    def _estimate_processing_time(
        self, agent: AgentType, context: Dict[str, Any]
    ) -> int:
        """Estimate processing time in seconds based on agent type and context."""
        base_time = self.agent_config[agent]["max_response_time"]

        # Time modifier based on context
        modifiers = 1.0

        # File uploads increase processing time
        if context.get("has_uploaded_files", False):
            if agent == AgentType.DATA_ANALYSIS_AGENT:
                modifiers *= 1.5  # Data analysis with files takes longer
            elif agent == AgentType.DOCUMENT_PROCESSING_AGENT:
                modifiers *= 1.3  # Document processing with files takes longer

        # Long sessions may have accumulated context
        query_count = context.get("query_count", 1)
        if query_count > 5:  # Many queries in session
            modifiers *= 1.2

        return int(base_time * modifiers)

    def _get_possible_intents(self, intent_result: Dict[str, Any]) -> List[str]:
        """Get list of possible intents based on keywords and classification."""
        primary_intent = intent_result.get("intent")
        confidence = intent_result.get("confidence", 0.0)

        if confidence >= 0.8:
            return [primary_intent]

        # Infer additional possible intents from keywords
        keywords = intent_result.get("keywords", [])
        possible_intents = [primary_intent]

        # Keyword-to-intent mapping for disambiguation
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

        return possible_intents[:3]  # Return at most 3 possible intents

    def _generate_clarification_questions(
        self, intent_result: Dict[str, Any]
    ) -> List[str]:
        """Generate clarification questions based on intent and keywords."""
        intent = intent_result.get("intent")
        keywords = intent_result.get("keywords", [])

        # Intent-specific clarification question templates
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

        return questions[:2]  # Return at most 2 clarification questions

    def _update_routing_stats(self, decision: RoutingDecision):
        """Update routing statistics with the latest decision."""
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
        """Create a fallback routing decision when an error occurs."""
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
        """Get routing statistics including rates and agent usage."""
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

            # Calculate routing rates
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

            # Agent usage rates
            stats["agent_usage_rates"] = {
                agent.value: count / total
                for agent, count in stats["agent_usage"].items()
            }

            return stats

    def update_system_status(self, status_updates: Dict[str, Any]):
        """Update system status with new metrics."""
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
        """Perform a health check on the routing engine."""
        return {
            "status": "healthy",
            "total_routes": self.routing_stats["total_routes"],
            "available_agents": len(self.system_status.get_available_agents()),
            "system_load": self.system_status.system_load,
            "active_sessions": self.system_status.active_sessions,
            "routing_rules": self.routing_rules,
        }
