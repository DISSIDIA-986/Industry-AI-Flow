"""
EN
ENLangChain 1.0 State Graph,EN
"""

import asyncio
import json
import logging
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace
from typing import Annotated, Any, Dict, List, Literal, Optional, TypedDict

from langchain_core.messages import AIMessage, HumanMessage
from langgraph.checkpoint.memory import MemorySaver
from langgraph.errors import GraphRecursionError  # P0 修复: 捕获递归异常
from langgraph.graph import END, StateGraph
from langgraph.graph.message import add_messages

from backend.config import settings
from backend.services.context_manager import ContextManager, SessionContext
from backend.services.intent_classification.intent_classifier import (
    IntentClassifier,
    IntentResult,
    QueryContext,
)
from backend.services.prompt_manager import PromptManager
from backend.services.retrieval.document_profile import DocumentProfileService
from backend.services.routing_decision import (
    AgentType,
    RoutingDecision,
    RoutingDecisionEngine,
)
from backend.services.workflows.nodes.prompt_node import prompt_node
from backend.services.workflows.prompting.template_selector import TemplateSelector

logger = logging.getLogger(__name__)


class WorkflowState(TypedDict):
    """EN"""

    messages: Annotated[List, add_messages]  # EN
    session_id: str  # ENID
    user_id: Optional[str]  # ENID
    current_query: str  # EN
    query_context: QueryContext  # EN
    session_context: SessionContext  # EN
    intent_result: Optional[IntentResult]  # EN
    routing_decision: Optional[RoutingDecision]  # EN
    clarification_needed: bool  # EN
    clarification_response: Optional[str]  # EN
    clarification_round: int  # P0: Track clarification iterations to prevent infinite loops
    agent_response: Optional[str]  # AgentEN
    workflow_complete: bool  # EN
    error: Optional[str]  # EN
    system_prompt: Optional[str]  # PromptEN
    prompt_meta: Optional[Dict[str, Any]]  # PromptEN
    metadata: Dict[str, Any]  # EN


class IntentClassificationWorkflow:
    """EN"""

    def __init__(
        self,
        intent_classifier: IntentClassifier,
        context_manager: ContextManager,
        routing_engine: RoutingDecisionEngine,
        prompt_manager: Optional[PromptManager] = None,
    ):
        """
        EN

        Args:
            intent_classifier: EN
            context_manager: EN
            routing_engine: EN
            prompt_manager: PromptEN(EN)
        """
        self.intent_classifier = intent_classifier
        self.context_manager = context_manager
        self.routing_engine = routing_engine
        self.prompt_manager = prompt_manager
        self.template_selector = TemplateSelector()
        self._rag_service = None
        self._document_profile_service: Optional[DocumentProfileService] = None
        self._data_analysis_agent = None
        self._document_extractor = None
        self._code_execution_manager = None

        # EN
        self.workflow = self._create_workflow()

        # EN(EN)
        self.memory = MemorySaver()

        logger.info("EN")

    def _create_workflow(self) -> StateGraph:
        """EN"""
        # EN
        workflow = StateGraph(WorkflowState)

        # EN
        workflow.add_node("input_preprocessing", self._input_preprocessing_node)
        workflow.add_node("context_enrichment", self._context_enrichment_node)
        workflow.add_node("intent_classification", self._intent_classification_node)
        workflow.add_node("confidence_evaluation", self._confidence_evaluation_node)
        workflow.add_node("routing_decision_step", self._routing_decision_node)
        workflow.add_node("prompt_preparation", self._prompt_preparation_node)
        workflow.add_node("clarification_step", self._clarification_needed_node)
        workflow.add_node(
            "clarification_processing", self._clarification_processing_node
        )
        workflow.add_node("agent_dispatch", self._agent_dispatch_node)
        workflow.add_node("response_processing", self._response_processing_node)
        workflow.add_node("error_handling", self._error_handling_node)

        # EN
        workflow.set_entry_point("input_preprocessing")

        # Route preprocessing/enrichment failures to the dedicated error handler.
        workflow.add_conditional_edges(
            "input_preprocessing",
            self._route_after_preprocessing,
            {
                "continue": "context_enrichment",
                "error": "error_handling",
            },
        )
        workflow.add_conditional_edges(
            "context_enrichment",
            self._route_after_context_enrichment,
            {
                "continue": "intent_classification",
                "error": "error_handling",
            },
        )
        workflow.add_edge("intent_classification", "confidence_evaluation")

        # EN
        workflow.add_conditional_edges(
            "confidence_evaluation",
            self._route_based_on_confidence,
            {
                "high_confidence": "routing_decision_step",
                "low_confidence": "clarification_step",
                "error": "error_handling",
            },
        )

        workflow.add_edge("routing_decision_step", "prompt_preparation")
        workflow.add_edge("prompt_preparation", "agent_dispatch")
        workflow.add_edge("clarification_step", "clarification_processing")

        # EN
        workflow.add_conditional_edges(
            "clarification_processing",
            self._route_after_clarification,
            {
                "retry_classification": "intent_classification",
                "proceed_with_fallback": "routing_decision_step",
                "await_user_input": END,
            },
        )

        workflow.add_edge("agent_dispatch", "response_processing")
        workflow.add_edge("response_processing", END)
        workflow.add_edge("error_handling", END)

        return workflow

    async def _input_preprocessing_node(self, state: WorkflowState) -> WorkflowState:
        """EN"""
        try:
            logger.info(f"EN,ENID: {state['session_id']}")

            # EN
            current_query = state.get("current_query", "")

            # EN
            cleaned_query = current_query.strip()

            # EN
            state["current_query"] = cleaned_query
            state["messages"].append(HumanMessage(content=cleaned_query))

            # EN
            state["metadata"]["preprocessing_timestamp"] = datetime.now().isoformat()
            state["metadata"]["query_length"] = len(cleaned_query)

            logger.debug(f"EN: {cleaned_query[:100]}...")
            return state

        except Exception as e:
            logger.error(f"EN: {str(e)}")
            state["error"] = f"EN: {str(e)}"
            return state

    async def _context_enrichment_node(self, state: WorkflowState) -> WorkflowState:
        """EN"""
        try:
            logger.info("EN")

            session_id = state["session_id"]

            # EN
            session_context = await self.context_manager.get_session_context(
                session_id=session_id, user_id=state.get("user_id")
            )
            state["session_context"] = session_context

            # EN
            enhanced_context = await self.context_manager.get_enhanced_context(
                session_id=session_id, max_history=5, include_files=True
            )

            recent_intents = [
                item.value if hasattr(item, "value") else str(item)
                for item in session_context.get_recent_intents(3)
            ]
            uploaded_files = [
                {
                    "name": file_ctx.file_name,
                    "type": file_ctx.file_type,
                    "size": file_ctx.file_size,
                    "file_path": file_ctx.file_path,
                    "metadata": file_ctx.metadata or {},
                }
                for file_ctx in session_context.uploaded_files
            ]

            # EN
            query_context = QueryContext(
                session_id=session_id,
                user_id=state.get("user_id"),
                session_topic=session_context.session_topic,
                recent_intents=recent_intents,
                uploaded_files=uploaded_files,
                user_preferences=session_context.user_preferences or {},
                interaction_history=enhanced_context.get("interaction_history", []) or [],
                time_of_day=datetime.now().strftime("%H:%M"),
                query_count_in_session=int(session_context.query_count),
            )
            state["query_context"] = query_context

            # EN
            state["metadata"][
                "context_enrichment_timestamp"
            ] = datetime.now().isoformat()
            state["metadata"]["context_quality"] = enhanced_context.get(
                "context_quality", "medium"
            )

            logger.debug(f"EN,EN: {state['metadata']['context_quality']}")
            return state

        except Exception as e:
            logger.error(f"EN: {str(e)}")
            state["error"] = f"EN: {str(e)}"
            return state

    async def _intent_classification_node(self, state: WorkflowState) -> WorkflowState:
        """EN"""
        try:
            logger.info("EN")

            # EN
            intent_result = await self.intent_classifier.classify_intent(
                query=state["current_query"], context=state["query_context"]
            )
            state["intent_result"] = intent_result

            # EN(EN,EN)
            await self._record_interaction(
                session_id=state["session_id"],
                user_query=state["current_query"],
                classified_intent=(
                    intent_result.intent.value
                    if hasattr(intent_result.intent, "value")
                    else str(intent_result.intent)
                ),
                agent_response="",  # ENAgentEN
                confidence=intent_result.confidence,
                processing_time_ms=intent_result.processing_time_ms,
                success=True,
            )

            # EN
            state["metadata"]["classification_timestamp"] = datetime.now().isoformat()
            state["metadata"]["intent"] = (
                intent_result.intent.value
                if hasattr(intent_result.intent, "value")
                else str(intent_result.intent)
            )
            state["metadata"]["confidence"] = intent_result.confidence

            logger.info(
                f"EN: {intent_result.intent} (EN: {intent_result.confidence:.2f})"
            )
            return state

        except Exception as e:
            logger.error(f"EN: {str(e)}")
            state["error"] = f"EN: {str(e)}"
            return state

    async def _confidence_evaluation_node(self, state: WorkflowState) -> WorkflowState:
        """P0: Evaluate intent confidence and track clarification rounds."""
        try:
            logger.info("EN")

            # P0: CRITICAL - Check max rounds BEFORE anything else to prevent recursion
            clarification_round = state.get("clarification_round", 0)
            MAX_CLARIFICATION_ROUNDS = 2  # P0: Reduced from 3 to prevent hitting 12-step limit

            if clarification_round >= MAX_CLARIFICATION_ROUNDS:
                logger.warning(
                    "P0: Max clarification rounds (%d) reached in confidence_evaluation! Forcing high confidence. Session: %s",
                    MAX_CLARIFICATION_ROUNDS,
                    state.get("session_id", "unknown"),
                )
                # Force high confidence to exit clarification loop
                state["clarification_needed"] = False
                state["metadata"]["max_clarification_reached"] = True
                state["metadata"]["confidence_evaluation"] = "high_confidence"
                return state

            intent_result = state.get("intent_result")
            if not intent_result:
                state["error"] = "EN"
                return state

            confidence = intent_result.confidence

            # EN
            high_threshold = 0.8
            low_threshold = 0.5

            if confidence >= high_threshold:
                state["clarification_needed"] = False
                evaluation_result = "high_confidence"
                logger.info("EN,EN")
            elif confidence <= low_threshold:
                # P0: Increment clarification round counter when entering clarification
                state["clarification_round"] = clarification_round + 1
                state["clarification_needed"] = True
                evaluation_result = "low_confidence"
                logger.info(
                    "P0: Setting clarification_needed=True, round %d/%d",
                    clarification_round + 1,
                    MAX_CLARIFICATION_ROUNDS
                )
            else:
                # EN,EN
                uncertainty_factors = intent_result.uncertainty_factors
                if len(uncertainty_factors) > 2:
                    # P0: Increment clarification round counter when entering clarification
                    state["clarification_round"] = clarification_round + 1
                    state["clarification_needed"] = True
                    evaluation_result = "low_confidence"
                    logger.info("EN,EN")
                else:
                    state["clarification_needed"] = False
                    evaluation_result = "high_confidence"
                    logger.info("EN,EN")

            # EN
            state["metadata"]["confidence_evaluation"] = evaluation_result
            state["metadata"]["uncertainty_factors"] = intent_result.uncertainty_factors

            return state

        except Exception as e:
            logger.error(f"EN: {str(e)}")
            state["error"] = f"EN: {str(e)}"
            return state

    async def _routing_decision_node(self, state: WorkflowState) -> WorkflowState:
        """EN"""
        try:
            logger.info("EN")

            intent_result = state["intent_result"]

            # EN
            routing_context = {
                "session_id": state["session_id"],
                "user_id": state.get("user_id"),
                "query_count": state["session_context"].query_count,
                "has_uploaded_files": len(state["session_context"].uploaded_files) > 0,
                "session_stage": state["session_context"].session_stage,
            }

            # EN
            routing_decision = await self.routing_engine.make_routing_decision(
                intent_result=intent_result.to_dict(),
                context=routing_context,
                user_preferences=state["session_context"].user_preferences,
            )
            state["routing_decision"] = routing_decision

            # EN
            state["metadata"]["routing_timestamp"] = datetime.now().isoformat()
            state["metadata"]["selected_agent"] = routing_decision.selected_agent.value
            state["metadata"]["routing_path"] = routing_decision.routing_path.value

            logger.info(f"EN: {routing_decision.selected_agent.value}")
            return state

        except Exception as e:
            logger.error(f"EN: {str(e)}")
            state["error"] = f"EN: {str(e)}"
            return state

    async def _prompt_preparation_node(self, state: WorkflowState) -> WorkflowState:
        """PromptEN(ENAgentEN)"""
        if not self.prompt_manager:
            state["metadata"]["prompt_status"] = "disabled"
            return state

        try:
            intent_value = None
            if state.get("intent_result") is not None:
                intent = state["intent_result"].intent
                intent_value = intent.value if hasattr(intent, "value") else str(intent)

            prompt_state = {
                "query": state.get("current_query", ""),
                "intent": intent_value,
                "retrieved_context": state.get("query_context").interaction_history
                if state.get("query_context")
                else [],
                "metadata": {
                    **state.get("metadata", {}),
                    "session_id": state.get("session_id"),
                    "user_id": state.get("user_id"),
                    "prompt_experiments_enabled": False,
                },
            }
            services = SimpleNamespace(
                prompt_manager=self.prompt_manager,
                template_selector=self.template_selector,
            )
            prompt_state = await prompt_node(prompt_state, services)
            if prompt_state.get("error"):
                state["metadata"]["prompt_status"] = "error"
                state["metadata"]["prompt_error"] = prompt_state["error"]
                return state

            state["system_prompt"] = prompt_state.get("system_prompt")
            state["prompt_meta"] = prompt_state.get("prompt_meta")
            state["metadata"]["prompt_status"] = "ok"
            if state.get("prompt_meta"):
                state["metadata"]["prompt_meta"] = state["prompt_meta"]
            return state
        except Exception as e:
            logger.warning(f"PromptEN,EN: {e}")
            state["metadata"]["prompt_status"] = "error"
            state["metadata"]["prompt_error"] = str(e)
            return state

    async def _clarification_needed_node(self, state: WorkflowState) -> WorkflowState:
        """EN"""
        try:
            logger.info("EN")

            intent_result = state["intent_result"]
            routing_decision = state.get("routing_decision")

            if routing_decision and routing_decision.clarification_context:
                clarification_context = routing_decision.clarification_context
            else:
                # EN
                clarification_context = {
                    "possible_intents": [
                        intent_result.intent.value
                        if hasattr(intent_result.intent, "value")
                        else str(intent_result.intent)
                    ],
                    "clarification_questions": [
                        f"It seems like you may want '{intent_result.intent}'. Could you provide more details?",
                        "Could you clarify what you'd like help with?",
                    ],
                    "user_context": {
                        "current_query": state["current_query"],
                        "confidence": intent_result.confidence,
                    },
                }

            # ENPromptEN,ENPrompt
            if self.prompt_manager:
                try:
                    prompt_info, prompt_content = await self.prompt_manager.get_prompt(
                        name="intent_clarification",
                        category="Intent",
                        context={
                            "user_query": state["current_query"],
                            "possible_intents": clarification_context[
                                "possible_intents"
                            ],
                            "classification_result": intent_result.reasoning,
                        },
                        variables={
                            "user_query": state["current_query"],
                            "possible_intents": json.dumps(
                                clarification_context["possible_intents"],
                                ensure_ascii=False,
                            ),
                            "classification_result": intent_result.reasoning,
                            "language": "zh-CN",
                        },
                    )

                    # ENLLMEN
                    clarification_message = (
                        await self._generate_clarification_with_prompt(
                            prompt_content, clarification_context
                        )
                    )
                except Exception as e:
                    logger.warning(f"ENPromptEN,EN: {str(e)}")
                    clarification_message = self._generate_default_clarification(
                        clarification_context
                    )
            else:
                clarification_message = self._generate_default_clarification(
                    clarification_context
                )

            state["clarification_response"] = clarification_message
            state["metadata"]["clarification_timestamp"] = datetime.now().isoformat()
            state["metadata"]["clarification_generated"] = True

            logger.info("EN")
            return state

        except Exception as e:
            logger.error(f"EN: {str(e)}")
            state["error"] = f"EN: {str(e)}"
            return state

    async def _clarification_processing_node(
        self, state: WorkflowState
    ) -> WorkflowState:
        """P0: Process clarification with max rounds escape hatch."""
        try:
            logger.info("EN")

            # P0: CRITICAL CHECK - If max rounds reached, immediately force proceed
            clarification_round = state.get("clarification_round", 0)
            MAX_CLARIFICATION_ROUNDS = 2  # P0: Max 2 rounds to stay under 12-step LangGraph limit

            if clarification_round >= MAX_CLARIFICATION_ROUNDS:
                logger.warning(
                    "P0: Max clarification rounds (%d) reached in clarification_processing_node! Forcing proceed. Session: %s",
                    clarification_round,
                    state.get("session_id", "unknown"),
                )
                # Don't set clarification_handled - just end the workflow
                # This will cause _route_after_clarification to return "proceed_with_fallback"
                state["clarification_needed"] = False
                state["metadata"]["max_clarification_reached"] = True
                state["metadata"]["awaiting_user_clarification"] = False
                state["metadata"]["clarification_handled"] = False
                return state

            # EN,EN
            # EN,EN

            # EN
            clarification_response = state.get("clarification_response")
            if not clarification_response:
                # EN,EN
                state["metadata"]["awaiting_user_clarification"] = True
                return state

            # EN
            # EN,EN

            # Check if the user actually provided new clarification input.
            # If so, enrich the current query and run a best-effort reclassification.
            user_clarification = str(state.get("user_clarification_input") or "").strip()
            routing_decision = state.get("routing_decision")
            if user_clarification:
                base_query = str(state.get("current_query") or "").strip()
                if base_query:
                    combined_query = f"{base_query}\nUser clarification: {user_clarification}"
                else:
                    combined_query = user_clarification
                state["current_query"] = combined_query
                state["metadata"]["clarification_input"] = user_clarification

                # Reclassify immediately so retry routing has updated intent signal.
                try:
                    query_context = state.get("query_context")
                    if query_context is not None:
                        refreshed_intent = await self.intent_classifier.classify_intent(
                            query=combined_query,
                            context=query_context,
                        )
                        state["intent_result"] = refreshed_intent
                        state["metadata"]["clarification_reclassified"] = True
                        state["metadata"]["clarification_reclass_confidence"] = (
                            refreshed_intent.confidence
                        )
                except Exception as exc:
                    logger.warning("Clarification reclassification failed: %s", exc)
                    state["metadata"]["clarification_reclassified"] = False

                # User provided new input — retry classification on updated query
                state["metadata"]["clarification_handled"] = True
                state["metadata"]["awaiting_user_clarification"] = False
                return state
            elif routing_decision and routing_decision.confidence < 0.7:
                # Low confidence and no new user input — do NOT retry
                # (retrying on the same unchanged query causes an infinite loop)
                state["metadata"]["awaiting_user_clarification"] = True
                return state
            else:
                # Sufficient confidence — proceed with fallback routing
                state["metadata"]["clarification_handled"] = True
                return state

        except Exception as e:
            logger.error(f"EN: {str(e)}")
            state["error"] = f"EN: {str(e)}"
            return state

    async def _agent_dispatch_node(self, state: WorkflowState) -> WorkflowState:
        """AgentEN"""
        try:
            logger.info("ENAgentEN")

            routing_decision = state["routing_decision"]

            # EN:EN,EN
            agent_type = routing_decision.selected_agent
            dispatch_result = await self._dispatch_to_agent(
                agent_type=agent_type,
                query=state["current_query"],
                context=state["query_context"],
                parameters=routing_decision.parameters,
                system_prompt=state.get("system_prompt"),
                prompt_meta=state.get("prompt_meta"),
                route_mode=state.get("metadata", {}).get("requested_route_mode"),
            )
            agent_response = str(dispatch_result.get("response", "")).strip()
            if not agent_response:
                raise RuntimeError("Agent returned empty response")

            state["agent_response"] = agent_response
            state["metadata"]["agent_dispatch_timestamp"] = datetime.now().isoformat()
            state["metadata"]["agent_type"] = agent_type.value
            state["metadata"]["agent_execution_status"] = "ok"
            state["metadata"]["agent_execution"] = dispatch_result.get("metadata", {})

            # EN(EN,EN)
            intent_result = state["intent_result"]
            await self._record_interaction(
                session_id=state["session_id"],
                user_query=state["current_query"],
                classified_intent=(
                    intent_result.intent.value
                    if hasattr(intent_result.intent, "value")
                    else str(intent_result.intent)
                ),
                agent_response=agent_response,
                confidence=intent_result.confidence,
                processing_time_ms=intent_result.processing_time_ms,
                success=True,
            )

            logger.info(f"AgentEN: {agent_type.value}")
            return state

        except Exception as e:
            logger.error(f"AgentEN: {str(e)}")
            state["error"] = f"AgentEN: {str(e)}"
            state["metadata"]["agent_execution_status"] = "error"
            state["metadata"]["agent_execution_error"] = str(e)
            return state

    async def _response_processing_node(self, state: WorkflowState) -> WorkflowState:
        """EN"""
        try:
            logger.info("EN")

            if state.get("error"):
                # EN:EN.
                error_response = (
                    "EN,EN."
                    "EN,EN."
                )
                if not str(state.get("agent_response") or "").strip():
                    state["agent_response"] = error_response
                state["messages"].append(AIMessage(content=state["agent_response"]))
                state["workflow_complete"] = True
                state["metadata"]["error_timestamp"] = datetime.now().isoformat()
                return state

            agent_response = state.get("agent_response", "")
            if agent_response is None or not str(agent_response).strip():
                state["error"] = "Agent returned empty response"
                return state

            # ENAIEN
            state["messages"].append(AIMessage(content=agent_response))

            # EN
            state["workflow_complete"] = True
            state["metadata"]["completion_timestamp"] = datetime.now().isoformat()

            logger.info("EN")
            return state

        except Exception as e:
            logger.error(f"EN: {str(e)}")
            state["error"] = f"EN: {str(e)}"
            return state

    async def _error_handling_node(self, state: WorkflowState) -> WorkflowState:
        """EN"""
        logger.error(f"EN: {state.get('error', 'EN')}")

        # EN
        error_message = (
            "The workflow encountered an internal error and could not complete your request."
        )
        state["agent_response"] = error_message
        state["messages"].append(AIMessage(content=error_message))
        state["workflow_complete"] = True
        state["metadata"]["error_timestamp"] = datetime.now().isoformat()

        return state

    async def _record_interaction(
        self,
        *,
        session_id: str,
        user_query: str,
        classified_intent: str,
        agent_response: str,
        confidence: float,
        processing_time_ms: int,
        success: bool,
    ) -> None:
        """P0: Best-effort interaction recording with timeout protection (increased to 5s)."""
        try:
            await asyncio.wait_for(
                self.context_manager.add_interaction_record(
                    session_id=session_id,
                    user_query=user_query,
                    classified_intent=classified_intent,
                    agent_response=agent_response,
                    confidence=confidence,
                    processing_time_ms=processing_time_ms,
                    success=success,
                ),
                timeout=5.0,  # P0: Increased from 2.0 to 5.0 to reduce timeout warnings
            )
        except asyncio.TimeoutError:
            logger.warning(
                "Interaction recording timed out for session %s; continue without blocking",
                session_id,
            )
        except Exception as exc:
            logger.warning(
                "Interaction recording failed for session %s: %s",
                session_id,
                exc,
            )

    def _route_based_on_confidence(self, state: WorkflowState) -> str:
        """P0: Route based on confidence, with escape hatch after max clarification rounds.

        NOTE: In LangGraph, routing functions must NOT modify state - they only return
        the next node name. State modifications happen in the nodes themselves.
        """
        if state.get("error"):
            return "error"

        # P0: Prevent infinite clarification loops - force proceed after 3 rounds
        clarification_round = state.get("clarification_round", 0)
        MAX_CLARIFICATION_ROUNDS = 2  # P0: Max 2 rounds to stay under 12-step LangGraph limit

        if clarification_round >= MAX_CLARIFICATION_ROUNDS:
            logger.warning(
                "P0: Max clarification rounds (%d) reached, forcing proceed to agent. "
                "Session: %s, Query: %s",
                MAX_CLARIFICATION_ROUNDS,
                state.get("session_id", "unknown"),
                state.get("current_query", "")[:50],
            )
            # Force routing to high_confidence (proceeds to routing_decision_step)
            # The routing_decision_node will handle fallback routing
            return "high_confidence"

        if state.get("clarification_needed", False):
            logger.info(
                "P0: Routing to clarification (round %d/%d) for session %s",
                clarification_round,
                MAX_CLARIFICATION_ROUNDS,
                state.get("session_id", "unknown"),
            )
            return "low_confidence"
        else:
            return "high_confidence"

    def _route_after_preprocessing(self, state: WorkflowState) -> str:
        if state.get("error"):
            return "error"
        return "continue"

    def _route_after_context_enrichment(self, state: WorkflowState) -> str:
        if state.get("error"):
            return "error"
        return "continue"

    def _route_after_clarification(self, state: WorkflowState) -> str:
        """P0: Route after clarification processing, with max rounds check."""
        # P0: IMPORTANT: Check if max clarification rounds reached BEFORE any retry logic
        clarification_round = state.get("clarification_round", 0)
        MAX_CLARIFICATION_ROUNDS = 2  # P0: Max 2 rounds to stay under 12-step LangGraph limit

        logger.info(
            "P0: _route_after_clarification called with clarification_round=%d, awaiting_user_clarification=%s",
            clarification_round,
            state.get("metadata", {}).get("awaiting_user_clarification", False),
        )

        # P0: CRITICAL: If max rounds reached, ALWAYS proceed to fallback, never retry
        if clarification_round >= MAX_CLARIFICATION_ROUNDS:
            logger.warning(
                "P0: Max clarification rounds (%d) reached in _route_after_clarification! Forcing proceed_with_fallback. Session: %s",
                clarification_round,
                state.get("session_id", "unknown"),
            )
            # Force proceed to routing_decision instead of retrying
            return "proceed_with_fallback"

        if state.get("metadata", {}).get("awaiting_user_clarification", False):
            logger.info("P0: Awaiting user clarification, ending workflow")
            return "await_user_input"

        # If clarification was handled (user provided a response), re-run
        # intent classification on the updated query so the new input is used.
        if state.get("metadata", {}).get("clarification_handled", False):
            logger.info(
                "P0: Clarification handled, retrying classification (round %d/%d)",
                clarification_round + 1,
                MAX_CLARIFICATION_ROUNDS,
            )
            return "retry_classification"

        logger.info("P0: No clarification input, proceeding with fallback")
        return "proceed_with_fallback"

    async def _generate_clarification_with_prompt(
        self, prompt_content: str, context: Dict[str, Any]
    ) -> str:
        """Generate a clarification message using prompt content."""
        try:
            questions = context.get("clarification_questions", [])
            possible_intents = context.get("possible_intents", [])

            if questions:
                clarification = "I'd like to better understand your request. Here are some clarifying questions:\n\n"
                for i, question in enumerate(questions, 1):
                    clarification += f"{i}. {question}\n"
                clarification += "\nPlease provide more details so I can assist you better."
            else:
                clarification = "Could you please provide more details about your request?"

            return clarification
        except Exception as e:
            logger.error(f"Failed to generate clarification with prompt: {str(e)}")
            return "Could you please provide more details about your request?"

    def _generate_default_clarification(self, context: Dict[str, Any]) -> str:
        """Generate a default clarification message."""
        questions = context.get("clarification_questions", [])
        possible_intents = context.get("possible_intents", [])

        if questions:
            clarification = "I'd like to better understand your request. Here are some clarifying questions:\n\n"
            for i, question in enumerate(questions, 1):
                clarification += f"{i}. {question}\n"
            clarification += "\nPlease provide more details so I can assist you better."
        else:
            clarification = "Could you please provide more details about your request?"

        return clarification

    def _get_rag_service(self):
        if self._rag_service is None:
            from backend.services.rag_engine import SimpleRAG

            self._rag_service = SimpleRAG(
                use_hybrid_search=True,
                use_reranker=True,
                enable_feedback=settings.enable_feedback_system,
            )
        return self._rag_service

    def _get_document_profile_service(
        self, rag: Any
    ) -> Optional[DocumentProfileService]:
        if not settings.enable_document_profiles:
            return None

        if self._document_profile_service is not None:
            return self._document_profile_service

        vectorstore = getattr(rag, "vectorstore", None)
        if vectorstore is None:
            return None

        self._document_profile_service = DocumentProfileService(vectorstore)
        return self._document_profile_service

    def _get_data_analysis_agent(self):
        if self._data_analysis_agent is None:
            from backend.services.data_analysis.data_analysis_agent import (
                DataAnalysisAgent,
            )

            self._data_analysis_agent = DataAnalysisAgent()
        return self._data_analysis_agent

    def _get_document_extractor(self):
        if self._document_extractor is None:
            from backend.services.document_processing.document_extractor import (
                DocumentExtractor,
            )

            self._document_extractor = DocumentExtractor(use_ocr=True)
        return self._document_extractor

    def _get_code_execution_manager(self):
        if self._code_execution_manager is None:
            from backend.services.code_executor import get_code_execution_manager

            self._code_execution_manager = get_code_execution_manager()
        return self._code_execution_manager

    @staticmethod
    def _unique_sources(chunks: List[Dict[str, Any]], limit: int = 5) -> List[str]:
        sources: List[str] = []
        seen: set[str] = set()
        for item in chunks:
            source = str(
                item.get("filename")
                or item.get("source")
                or (item.get("metadata") or {}).get("filename")
                or item.get("doc_id")
                or ""
            ).strip()
            if not source or source in seen:
                continue
            seen.add(source)
            sources.append(source)
            if len(sources) >= limit:
                break
        return sources

    @staticmethod
    def _extract_code_from_query(query: str) -> Optional[str]:
        import re

        match = re.search(r"```(?:python)?\s*(.*?)```", query, flags=re.DOTALL | re.IGNORECASE)
        if match:
            code = match.group(1).strip()
            return code if code else None
        return None

    def _resolve_uploaded_file_path(
        self,
        context: QueryContext,
        *,
        allowed_suffixes: Optional[set[str]] = None,
    ) -> Optional[str]:
        uploaded_files = context.uploaded_files or []
        for item in uploaded_files:
            file_path = str(item.get("file_path") or item.get("path") or "").strip()
            if not file_path:
                continue
            path_obj = Path(file_path)
            if not path_obj.exists() or not path_obj.is_file():
                continue
            if allowed_suffixes is None:
                return str(path_obj)
            if path_obj.suffix.lower() in allowed_suffixes:
                return str(path_obj)
        return None

    @staticmethod
    def _chunk_identity(chunk: Dict[str, Any]) -> str:
        chunk_id = str(chunk.get("chunk_id") or chunk.get("id") or "").strip()
        if chunk_id:
            return chunk_id

        doc_id = str(chunk.get("doc_id") or "").strip()
        filename = str(chunk.get("filename") or "").strip()
        content = str(chunk.get("content") or "").strip()
        return f"{doc_id}|{filename}|{content[:120]}"

    @staticmethod
    def _chunk_doc_id(chunk: Dict[str, Any]) -> str:
        metadata = chunk.get("metadata") or {}
        if not isinstance(metadata, dict):
            metadata = {}
        doc_id = str(
            chunk.get("doc_id")
            or metadata.get("doc_id")
            or chunk.get("filename")
            or metadata.get("filename")
            or metadata.get("source")
            or ""
        ).strip()
        return doc_id

    async def _boost_chunks_with_profiles(
        self,
        *,
        rag: Any,
        query: str,
        chunks: List[Dict[str, Any]],
        top_k: int,
    ) -> tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        service = self._get_document_profile_service(rag)
        if service is None or not chunks:
            return chunks, []

        candidate_doc_ids = [
            doc_id
            for doc_id in (self._chunk_doc_id(chunk) for chunk in chunks)
            if doc_id
        ]
        if not candidate_doc_ids:
            return chunks, []

        profile_top_k = max(
            1,
            min(
                max(int(settings.document_profile_context_limit), int(top_k)),
                8,
            ),
        )
        profiles = await asyncio.to_thread(
            service.get_ranked_profiles,
            query,
            top_k=profile_top_k,
            candidate_doc_ids=candidate_doc_ids,
            auto_refresh_stale=True,
        )
        if not profiles:
            return chunks, []

        profile_map = {
            str(item.get("doc_id") or "").strip(): float(item.get("profile_score") or 0.0)
            for item in profiles
        }

        boosted_chunks: List[Dict[str, Any]] = []
        for chunk in chunks:
            payload = dict(chunk)
            doc_id = self._chunk_doc_id(payload)
            base_score = 0.0
            try:
                base_score = float(payload.get("score") or 0.0)
            except Exception:
                base_score = 0.0
            if base_score <= 0.0 and payload.get("distance") is not None:
                try:
                    base_score = max(0.0, 1.0 - float(payload.get("distance")))
                except Exception:
                    base_score = 0.0

            profile_score = float(profile_map.get(doc_id, 0.0))
            payload["profile_score"] = round(profile_score, 6)
            payload["score"] = round(base_score + (0.25 * profile_score), 6)
            boosted_chunks.append(payload)

        boosted_chunks.sort(
            key=lambda item: float(item.get("score") or 0.0),
            reverse=True,
        )
        return boosted_chunks[: max(top_k, 1)], profiles

    def _build_suggested_questions(
        self,
        *,
        query: str,
        source_items: List[Dict[str, Any]],
        profiles: List[Dict[str, Any]],
    ) -> List[str]:
        max_questions = max(
            1,
            min(int(settings.workflow_suggested_questions_count), 5),
        )
        query_norm = str(query or "").strip().lower()

        candidates: List[str] = []
        top_profile = profiles[0] if profiles else {}
        profile_name = str(
            top_profile.get("filename")
            or top_profile.get("doc_id")
            or (source_items[0].get("document_name") if source_items else "this source")
        ).strip()
        outline = top_profile.get("outline")
        if isinstance(outline, list):
            for item in outline[:2]:
                heading = str(item or "").strip()
                if not heading:
                    continue
                candidates.append(
                    f'In {profile_name}, what are the requirements for "{heading}"?'
                )

        keywords = top_profile.get("keywords")
        if isinstance(keywords, list):
            filtered_keywords = [str(item).strip() for item in keywords if str(item).strip()]
            if len(filtered_keywords) >= 2:
                candidates.append(
                    f"Can you summarize compliance checks for {filtered_keywords[0]} and {filtered_keywords[1]} in {profile_name}?"
                )

        if source_items:
            primary_source = str(
                source_items[0].get("document_name")
                or source_items[0].get("document_id")
                or profile_name
            ).strip()
            candidates.append(
                f"What evidence from {primary_source} directly supports this answer?"
            )
            candidates.append(
                f"What are the key exceptions or risk points in {primary_source}?"
            )

        candidates.append("What details should I provide next for a more precise answer?")

        suggestions: List[str] = []
        seen: set[str] = set()
        for question in candidates:
            value = str(question or "").strip()
            if not value:
                continue
            lowered = value.lower()
            if lowered in seen or lowered == query_norm:
                continue
            seen.add(lowered)
            suggestions.append(value)
            if len(suggestions) >= max_questions:
                break
        return suggestions

    @staticmethod
    def _parse_json_object(text: str) -> Optional[Dict[str, Any]]:
        raw = str(text or "").strip()
        if not raw:
            return None
        try:
            payload = json.loads(raw)
            return payload if isinstance(payload, dict) else None
        except Exception:
            pass

        start = raw.find("{")
        end = raw.rfind("}")
        if start >= 0 and end > start:
            try:
                payload = json.loads(raw[start : end + 1])
                return payload if isinstance(payload, dict) else None
            except Exception:
                return None
        return None

    @staticmethod
    def _normalize_rewrites(raw: Any) -> List[str]:
        candidates: List[str] = []
        if isinstance(raw, str):
            value = raw.strip()
            if value:
                candidates.append(value)
        elif isinstance(raw, list):
            for item in raw:
                if isinstance(item, str):
                    value = item.strip()
                    if value:
                        candidates.append(value)
        elif isinstance(raw, dict):
            for key in ("rewrites", "queries", "variants", "paraphrases"):
                if key in raw:
                    candidates.extend(IntentClassificationWorkflow._normalize_rewrites(raw.get(key)))
        return candidates

    async def _build_retrieval_queries(
        self,
        *,
        query: str,
        context: QueryContext,
        parameters: Dict[str, Any],
        rag: Any,
    ) -> List[str]:
        enable_rewrite = bool(
            parameters.get("enable_query_rewrite", settings.enable_rag_query_rewrite)
        )
        rewrite_count_raw = parameters.get(
            "query_rewrite_count", settings.rag_query_rewrite_count
        )
        try:
            rewrite_count = int(rewrite_count_raw)
        except Exception:
            rewrite_count = int(settings.rag_query_rewrite_count)
        rewrite_count = max(0, min(rewrite_count, 3))

        retrieval_queries: List[str] = [query]
        if not enable_rewrite or rewrite_count <= 0:
            return retrieval_queries

        history_lines: List[str] = []
        for record in (context.interaction_history or [])[-2:]:
            if not isinstance(record, dict):
                continue
            user_query = str(record.get("user_query") or "").strip()
            if user_query:
                history_lines.append(user_query[:180])

        keyword_values = parameters.get("keywords")
        keywords: List[str] = []
        if isinstance(keyword_values, list):
            for item in keyword_values:
                if isinstance(item, str) and item.strip():
                    keywords.append(item.strip())

        prompt = (
            "Rewrite the user query for document retrieval.\n"
            "Do not change intent. Keep domain terms, standard names, and identifiers.\n"
            "Return strict JSON only: {\"rewrites\": [\"...\"]}\n"
            f"Generate at most {rewrite_count} rewrites.\n\n"
            f"Original query:\n{query}\n\n"
            f"Recent conversation hints:\n{chr(10).join(history_lines) if history_lines else '(none)'}\n"
            f"Intent keywords: {', '.join(keywords) if keywords else '(none)'}\n"
        )

        raw_response = ""
        try:
            raw_response = await asyncio.to_thread(
                rag.llm_client.generate,
                prompt,
                temperature=0.0,
                max_tokens=220,
            )
        except Exception as exc:
            logger.warning("Query rewrite generation failed, fallback to original query: %s", exc)

        rewrite_candidates: List[str] = []
        parsed = self._parse_json_object(raw_response)
        if parsed is not None:
            rewrite_candidates.extend(self._normalize_rewrites(parsed.get("rewrites", parsed)))

        # Deterministic fallback: add keyword-enriched retrieval query
        if not rewrite_candidates and keywords:
            rewrite_candidates.append(f"{query} {' '.join(keywords[:4])}".strip())

        for item in rewrite_candidates:
            value = item.strip()
            if not value:
                continue
            if value.lower() == query.lower():
                continue
            if value not in retrieval_queries:
                retrieval_queries.append(value)
            if len(retrieval_queries) >= 1 + rewrite_count:
                break
        return retrieval_queries

    async def _retrieve_chunks_for_query(
        self,
        *,
        rag: Any,
        query: str,
        top_k: int,
    ) -> List[Dict[str, Any]]:
        if rag.use_hybrid_search and rag.hybrid_retriever:
            chunks = await asyncio.to_thread(
                rag.hybrid_retriever.search,
                query=query,
                top_k=max(top_k, 1),
                vector_weight=0.7,
                bm25_weight=0.3,
            )
        else:
            from backend.services.core.embedder import embed_query_text

            query_embedding = await asyncio.to_thread(embed_query_text, query)
            chunks = await asyncio.to_thread(
                rag.vectorstore.similarity_search, query_embedding, max(top_k, 1)
            )
        return chunks if isinstance(chunks, list) else []

    def _fuse_retrieval_chunks(
        self,
        *,
        retrieval_runs: List[Dict[str, Any]],
        top_k: int,
    ) -> List[Dict[str, Any]]:
        fused_scores: Dict[str, float] = {}
        chunk_payloads: Dict[str, Dict[str, Any]] = {}

        for run_index, run in enumerate(retrieval_runs):
            chunks = run.get("chunks")
            if not isinstance(chunks, list):
                continue
            query_weight = 1.0 if run_index == 0 else 0.85
            for rank, chunk in enumerate(chunks, 1):
                if not isinstance(chunk, dict):
                    continue
                chunk_key = self._chunk_identity(chunk)
                if not chunk_key:
                    continue
                fused_scores[chunk_key] = fused_scores.get(chunk_key, 0.0) + (
                    query_weight / (60.0 + float(rank))
                )
                if chunk_key not in chunk_payloads:
                    chunk_payloads[chunk_key] = dict(chunk)

        sorted_keys = sorted(fused_scores.keys(), key=lambda key: fused_scores[key], reverse=True)
        fused_chunks: List[Dict[str, Any]] = []
        for key in sorted_keys[: max(top_k, 1)]:
            payload = dict(chunk_payloads[key])
            payload["score"] = round(float(fused_scores[key]), 6)
            fused_chunks.append(payload)
        return fused_chunks

    async def _dispatch_rag_query(
        self,
        *,
        query: str,
        context: QueryContext,
        parameters: Dict[str, Any],
    ) -> Dict[str, Any]:
        top_k_raw = parameters.get("top_k")
        try:
            top_k = int(top_k_raw) if top_k_raw is not None else int(settings.top_k)
        except Exception:
            top_k = int(settings.top_k)

        rag = self._get_rag_service()
        retrieval_queries = await self._build_retrieval_queries(
            query=query,
            context=context,
            parameters=parameters,
            rag=rag,
        )
        retrieval_runs: List[Dict[str, Any]] = []
        retrieval_depth = max(top_k * 2, top_k)
        for retrieval_query in retrieval_queries:
            chunks_for_query = await self._retrieve_chunks_for_query(
                rag=rag,
                query=retrieval_query,
                top_k=retrieval_depth,
            )
            retrieval_runs.append(
                {
                    "query": retrieval_query,
                    "chunks": chunks_for_query,
                }
            )

        chunks = self._fuse_retrieval_chunks(
            retrieval_runs=retrieval_runs,
            top_k=max(top_k, 1),
        )
        if rag.use_reranker and rag.reranker and chunks:
            chunks = await asyncio.to_thread(
                rag.reranker.rerank,
                query=query,
                documents=chunks,
                top_k=max(top_k, 1),
            )
        document_profiles: List[Dict[str, Any]] = []
        if chunks:
            chunks, document_profiles = await self._boost_chunks_with_profiles(
                rag=rag,
                query=query,
                chunks=chunks,
                top_k=max(top_k, 1),
            )

        if not chunks:
            raise RuntimeError("RAG retrieval returned empty context")

        normalized_chunks: List[Dict[str, Any]] = []
        max_relevance_raw = 0.0
        for chunk in chunks:
            payload = dict(chunk) if isinstance(chunk, dict) else {}
            raw_score = payload.get("score")
            if raw_score is None and payload.get("distance") is not None:
                try:
                    raw_score = max(0.0, 1.0 - float(payload.get("distance")))
                except Exception:
                    raw_score = 0.0
            try:
                relevance_raw = max(0.0, float(raw_score or 0.0))
            except Exception:
                relevance_raw = 0.0
            payload["relevance_raw"] = relevance_raw
            max_relevance_raw = max(max_relevance_raw, relevance_raw)
            normalized_chunks.append(payload)

        source_items: List[Dict[str, Any]] = []
        seen_sources: set[str] = set()
        for chunk in normalized_chunks:
            metadata = chunk.get("metadata") or {}
            if not isinstance(metadata, dict):
                metadata = {}
            doc_id = str(
                chunk.get("doc_id") or metadata.get("doc_id") or chunk.get("filename") or ""
            ).strip()
            doc_name = str(
                chunk.get("filename")
                or metadata.get("filename")
                or metadata.get("source")
                or doc_id
            ).strip()
            chunk_id = str(chunk.get("chunk_id") or chunk.get("id") or "").strip()
            content_hash = str(chunk.get("content", ""))[:120]
            source_key = f"{doc_id}:{doc_name}:{chunk_id or content_hash}"
            if not doc_name and not doc_id:
                continue
            if source_key in seen_sources:
                continue
            seen_sources.add(source_key)

            relevance_raw = float(chunk.get("relevance_raw") or 0.0)
            if max_relevance_raw > 0.0:
                relevance = relevance_raw / max_relevance_raw
            else:
                relevance = relevance_raw
            relevance = max(0.0, min(1.0, relevance))

            content = str(chunk.get("content") or "").strip()
            source_items.append(
                {
                    "document_id": doc_id or doc_name,
                    "document_name": doc_name or doc_id,
                    "relevance": round(relevance, 6),
                    "relevance_raw": round(relevance_raw, 6),
                    "profile_score": float(chunk.get("profile_score") or 0.0),
                    "content": content[:400],
                }
            )

        if not source_items:
            raise RuntimeError("RAG returned no grounded sources")

        context_blocks: List[str] = []
        for idx, item in enumerate(source_items[: max(top_k, 3)], 1):
            if not item["content"]:
                continue
            context_blocks.append(
                f"[{idx}] source={item['document_name']}\n{item['content']}"
            )
        if not context_blocks:
            raise RuntimeError("RAG contexts are empty after retrieval")

        profile_context_limit = max(1, int(settings.document_profile_context_limit))
        profile_snippets = DocumentProfileService.to_prompt_snippets(
            document_profiles,
            max_items=profile_context_limit,
        )
        document_profile_text = "\n\n".join(profile_snippets) if profile_snippets else "(none)"

        history_lines: List[str] = []
        for record in (context.interaction_history or [])[-3:]:
            if not isinstance(record, dict):
                continue
            user_query = str(record.get("user_query") or "").strip()
            agent_response = str(record.get("agent_response") or "").strip()
            if user_query:
                history_lines.append(f"User: {user_query[:220]}")
            if agent_response:
                history_lines.append(f"Assistant: {agent_response[:220]}")
        history_text = "\n".join(history_lines) if history_lines else "(none)"
        retrieved_chunks_text = "\n\n".join(context_blocks)
        suggested_questions = self._build_suggested_questions(
            query=query,
            source_items=source_items,
            profiles=document_profiles,
        )

        prompt = (
            "You are a construction-domain RAG assistant.\n"
            "Use only the retrieved context to answer the user.\n"
            "Rules:\n"
            "1. Answer directly and do not restate the question.\n"
            "2. If context is insufficient, state what is missing.\n"
            "3. Cite evidence with [1], [2], ... based on retrieved chunks.\n"
            "4. Keep the answer concise and factual.\n\n"
            f"Conversation history:\n{history_text}\n\n"
            f"Document profiles:\n{document_profile_text}\n\n"
            f"User question:\n{query}\n\n"
            f"Retrieved chunks:\n{retrieved_chunks_text}\n\n"
            "Final answer:"
        )

        temperature_raw = parameters.get("temperature")
        max_tokens_raw = parameters.get("max_tokens")
        try:
            temperature = float(temperature_raw) if temperature_raw is not None else 0.2
        except Exception:
            temperature = 0.2
        try:
            max_tokens = int(max_tokens_raw) if max_tokens_raw is not None else 900
        except Exception:
            max_tokens = 900

        llm_answer = ""
        try:
            llm_answer = await asyncio.to_thread(
                rag.llm_client.generate,
                prompt,
                temperature=temperature,
                max_tokens=max_tokens,
            )
        except Exception as exc:
            logger.warning("RAG generation failed, falling back to extractive answer: %s", exc)

        cited_answer = str(llm_answer or "").strip()
        if not cited_answer:
            highlight_lines: List[str] = []
            for idx, block in enumerate(context_blocks[:3], 1):
                preview = block.split("\n", 1)[-1].replace("\n", " ").strip()
                if preview:
                    highlight_lines.append(f"{idx}. {preview[:260]}")
            cited_answer = (
                "Retrieved evidence was found, but generation degraded. "
                "Key evidence:\n"
                + "\n".join(highlight_lines)
            ).strip()

        return {
            "response": cited_answer,
            "metadata": {
                "source_count": len(source_items),
                "sources": source_items[:5],
                "retrieved_count": len(chunks),
                "generation_mode": "rag_grounded_llm",
                "retrieval_queries": retrieval_queries,
                "retrieval_query_count": len(retrieval_queries),
                "query_rewrite_used": len(retrieval_queries) > 1,
                "profile_boost_used": bool(document_profiles),
                "document_profiles": document_profiles[:profile_context_limit],
                "suggested_questions": suggested_questions,
            },
        }

    async def _dispatch_data_analysis_query(
        self,
        *,
        query: str,
        context: QueryContext,
    ) -> Dict[str, Any]:
        data_file = self._resolve_uploaded_file_path(
            context,
            allowed_suffixes={".csv", ".xlsx", ".xls", ".json"},
        )
        if not data_file:
            raise RuntimeError("Data analysis requires an uploaded dataset file path")

        agent = self._get_data_analysis_agent()
        result = await asyncio.to_thread(
            agent.analyze_query,
            question=query,
            data_file_path=data_file,
            dataset_metadata=None,
        )
        if not isinstance(result, dict):
            raise RuntimeError("Data analysis returned an invalid payload")
        if not result.get("success"):
            raise RuntimeError(str(result.get("error") or "data analysis failed"))

        answer = str(result.get("answer") or "").strip()
        if not answer:
            raise RuntimeError("Data analysis returned empty answer")

        return {
            "response": answer,
            "metadata": {
                "data_file": data_file,
                "execution_time": result.get("execution_time"),
                "visualizations": result.get("visualizations", []),
            },
        }

    async def _dispatch_document_query(
        self,
        *,
        query: str,
        context: QueryContext,
    ) -> Dict[str, Any]:
        file_path = self._resolve_uploaded_file_path(context)
        if not file_path:
            raise RuntimeError("Document processing requires an uploaded document path")

        extractor = self._get_document_extractor()
        extracted = await asyncio.to_thread(extractor.extract, file_path)
        text = str(getattr(extracted, "text", "") or "").strip()
        if not text:
            raise RuntimeError("Document extraction produced empty text")

        preview = text[:1200]
        answer = (
            f"Document extracted successfully for query: {query}\n\n"
            f"Source: {Path(file_path).name}\n"
            f"Preview:\n{preview}"
        )
        return {
            "response": answer,
            "metadata": {
                "document_path": file_path,
                "file_type": getattr(extracted, "file_type", ""),
                "method": getattr(extracted, "method", ""),
                "source_count": 1,
                "sources": [Path(file_path).name],
            },
        }

    async def _dispatch_code_execution_query(
        self,
        *,
        query: str,
        parameters: Dict[str, Any],
    ) -> Dict[str, Any]:
        code = str(parameters.get("code") or "").strip() or self._extract_code_from_query(query)
        if not code:
            raise RuntimeError("Code execution requires Python code snippet in query")

        manager = self._get_code_execution_manager()
        if manager is None:
            raise RuntimeError("Code execution provider is unavailable")

        mode = str(parameters.get("mode") or settings.code_execution_provider)
        timeout = parameters.get("timeout")
        result = await asyncio.to_thread(
            manager.execute_code,
            code=code,
            data_files=None,
            timeout=timeout,
            mode=mode,
        )
        if not isinstance(result, dict):
            raise RuntimeError("Code execution returned an invalid payload")
        if not result.get("success"):
            raise RuntimeError(str(result.get("error") or result.get("stderr") or "code execution failed"))

        stdout = str(result.get("stdout") or "").strip()
        response = stdout or "Code executed successfully with no stdout output."
        return {
            "response": response,
            "metadata": {
                "mode": mode,
                "execution_time": result.get("execution_time"),
            },
        }

    async def _dispatch_to_agent(
        self,
        agent_type: AgentType,
        query: str,
        context: QueryContext,
        parameters: Dict[str, Any],
        system_prompt: Optional[str] = None,
        prompt_meta: Optional[Dict[str, Any]] = None,
        route_mode: Optional[str] = None,
    ) -> Dict[str, Any]:
        """ENAgentEN,EN."""
        normalized_params = parameters if isinstance(parameters, dict) else {}
        if system_prompt:
            normalized_params["system_prompt"] = system_prompt
        if prompt_meta:
            normalized_params["prompt_meta"] = prompt_meta
        if route_mode:
            normalized_params["route_mode"] = route_mode

        if agent_type in {AgentType.RAG_AGENT, AgentType.GENERAL_AGENT}:
            return await self._dispatch_rag_query(
                query=query,
                context=context,
                parameters=normalized_params,
            )
        if agent_type == AgentType.COST_ESTIMATION_AGENT:
            # Cost estimation is handled by the dedicated cost_estimation_node
            # in the workflow pipeline. Return a non-empty marker so the caller
            # does not treat this as an empty-response error.
            return {
                "response": "Routing to cost estimation service...",
                "metadata": {"routed_to": "cost_estimation_node"},
            }
        if agent_type == AgentType.DATA_ANALYSIS_AGENT:
            return await self._dispatch_data_analysis_query(query=query, context=context)
        if agent_type == AgentType.DOCUMENT_PROCESSING_AGENT:
            return await self._dispatch_document_query(query=query, context=context)
        if agent_type == AgentType.CODE_EXECUTION_AGENT:
            return await self._dispatch_code_execution_query(
                query=query,
                parameters=normalized_params,
            )

        raise RuntimeError(f"Unsupported agent type: {agent_type.value}")

    async def run_workflow(
        self,
        query: str,
        session_id: str,
        user_id: Optional[str] = None,
        thread_id: Optional[str] = None,
        route_mode: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        EN

        Args:
            query: EN
            session_id: ENID
            user_id: ENID
            thread_id: ENID(ENLangGraph)

        Returns:
            Dict[str, Any]: EN
        """
        try:
            # P0: Initialize clarification_round counter to prevent infinite loops
            initial_state = WorkflowState(
                messages=[],
                session_id=session_id,
                user_id=user_id,
                current_query=query,
                query_context=QueryContext(session_id=session_id, user_id=user_id),
                session_context=SessionContext(session_id=session_id),
                intent_result=None,
                routing_decision=None,
                clarification_needed=False,
                clarification_response=None,
                clarification_round=0,  # P0: Start at round 0
                agent_response=None,
                workflow_complete=False,
                error=None,
                system_prompt=None,
                prompt_meta=None,
                metadata={
                    "start_timestamp": datetime.now().isoformat(),
                    "workflow_runner": "intent_workflow",
                    "prompt_experiments_enabled": bool(
                        settings.prompt_experiments_enabled
                    ),
                    "requested_route_mode": route_mode,
                },
            )

            # EN
            runnable_workflow = self.workflow.compile(checkpointer=self.memory)

            # EN
            config = {
                "configurable": {"thread_id": thread_id or session_id},
                "recursion_limit": settings.workflow_recursion_limit,  # P0 修复: 设置递归限制
            }
            result = await runnable_workflow.ainvoke(initial_state, config=config)

            # EN
            metadata = result.get("metadata") or {}
            if not isinstance(metadata, dict):
                metadata = {}
            agent_response = str(result.get("agent_response") or "").strip()
            success = bool(
                not result.get("error")
                and bool(agent_response)
                and metadata.get("agent_execution_status", "ok") == "ok"
            )
            return {
                "success": success,
                "agent_response": result.get("agent_response"),
                "intent_result": result["intent_result"].to_dict()
                if result.get("intent_result")
                else None,
                "routing_decision": result["routing_decision"].to_dict()
                if result.get("routing_decision")
                else None,
                "clarification_needed": result.get("clarification_needed", False),
                "clarification_response": result.get("clarification_response"),
                "messages": [
                    {"type": type(msg).__name__, "content": msg.content}
                    for msg in result.get("messages", [])
                ],
                "metadata": metadata,
                "error": result.get("error"),
            }

        except GraphRecursionError as e:
            # P0 修复: 捕获递归异常，返回受控错误
            logger.error(f"Workflow recursion limit exceeded: {str(e)}")
            return {
                "success": False,
                "error": "The workflow exceeded maximum processing steps. Please rephrase your query or provide more specific details.",
                "agent_response": "I need more information to help you. Could you please rephrase your question or provide additional context?",
                "clarification_needed": True,
                "clarification_response": "Your request requires clarification. Please provide more specific details.",
            }
        except Exception as e:
            logger.error(f"Intent workflow execution failed: {str(e)}")
            return {
                "success": False,
                "error": f"Intent workflow error: {str(e)}",
                "agent_response": "The request could not be completed due to an internal workflow error.",
            }

    async def continue_workflow(
        self, user_response: str, session_id: str, thread_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        EN(EN)

        Args:
            user_response: EN
            session_id: ENID
            thread_id: ENID

        Returns:
            Dict[str, Any]: EN
        """
        try:
            # EN
            runnable_workflow = self.workflow.compile(checkpointer=self.memory)
            config = {
                "configurable": {"thread_id": thread_id or session_id},
                "recursion_limit": settings.workflow_recursion_limit,  # P0 修复: 设置递归限制
            }

            existing_metadata: Dict[str, Any] = {}
            existing_query_context: QueryContext = QueryContext(session_id=session_id)
            existing_session_context: SessionContext = SessionContext(
                session_id=session_id
            )
            try:
                checkpoint = None
                if hasattr(runnable_workflow, "aget_state"):
                    checkpoint = await runnable_workflow.aget_state(config=config)
                elif hasattr(runnable_workflow, "get_state"):
                    checkpoint = runnable_workflow.get_state(config=config)

                checkpoint_values = getattr(checkpoint, "values", None)
                if checkpoint_values is None and isinstance(checkpoint, dict):
                    checkpoint_values = checkpoint.get("values") or checkpoint

                if isinstance(checkpoint_values, dict):
                    metadata = checkpoint_values.get("metadata")
                    if isinstance(metadata, dict):
                        existing_metadata = dict(metadata)
                    checkpoint_query_context = checkpoint_values.get("query_context")
                    if isinstance(checkpoint_query_context, QueryContext):
                        existing_query_context = checkpoint_query_context
                    checkpoint_session_context = checkpoint_values.get(
                        "session_context"
                    )
                    if isinstance(checkpoint_session_context, SessionContext):
                        existing_session_context = checkpoint_session_context
            except Exception as exc:
                logger.debug(
                    "Failed to fetch checkpoint state for workflow continuation: %s",
                    exc,
                )

            merged_metadata: Dict[str, Any] = dict(existing_metadata)
            merged_metadata.update(
                {
                    "continuation_timestamp": datetime.now().isoformat(),
                    "workflow_runner": "intent_workflow",
                    "prompt_experiments_enabled": bool(
                        settings.prompt_experiments_enabled
                    ),
                }
            )

            # EN
            state_update = WorkflowState(
                messages=[HumanMessage(content=user_response)],
                session_id=session_id,
                user_id=None,
                current_query=user_response,
                query_context=existing_query_context,
                session_context=existing_session_context,
                intent_result=None,
                routing_decision=None,
                clarification_needed=False,
                clarification_response=None,
                agent_response=None,
                workflow_complete=False,
                error=None,
                system_prompt=None,
                prompt_meta=None,
                metadata=merged_metadata,
            )

            # EN
            result = await runnable_workflow.ainvoke(state_update, config=config)

            return {
                "success": not bool(result.get("error")),
                "agent_response": result.get("agent_response"),
                "clarification_needed": result.get("clarification_needed", False),
                "clarification_response": result.get("clarification_response"),
                "messages": [
                    {"type": type(msg).__name__, "content": msg.content}
                    for msg in result.get("messages", [])
                ],
                "metadata": result.get("metadata", {}),
                "error": result.get("error"),
            }

        except GraphRecursionError as e:
            # P0 修复: 捕获递归异常，返回受控错误
            logger.error(f"Workflow recursion limit exceeded during continuation: {str(e)}")
            return {
                "success": False,
                "error": "The workflow exceeded maximum processing steps. Please rephrase your query or provide more specific details.",
                "agent_response": "I need more information to help you. Could you please rephrase your question or provide additional context?",
                "clarification_needed": True,
                "clarification_response": "Your request requires clarification. Please provide more specific details.",
            }
        except Exception as e:
            logger.error(f"Intent workflow continuation failed: {str(e)}")
            return {
                "success": False,
                "error": f"Intent workflow continuation error: {str(e)}",
                "agent_response": "The workflow continuation failed due to an internal error.",
            }

    def get_workflow_stats(self) -> Dict[str, Any]:
        """EN"""
        routing_stats = self.routing_engine.get_routing_statistics()

        return {
            "workflow_status": "active",
            "routing_statistics": routing_stats,
            "components": {
                "intent_classifier": "enabled",
                "context_manager": "enabled",
                "routing_engine": "enabled",
                "prompt_manager": "enabled" if self.prompt_manager else "disabled",
            },
            "memory_checkpoints": "enabled",
        }
