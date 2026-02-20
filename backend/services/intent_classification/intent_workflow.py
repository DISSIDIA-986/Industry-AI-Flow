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

        # EN
        workflow.add_edge("input_preprocessing", "context_enrichment")
        workflow.add_edge("context_enrichment", "intent_classification")
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
        """EN"""
        try:
            logger.info("EN")

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
                state["clarification_needed"] = True
                evaluation_result = "low_confidence"
                logger.info("EN,EN")
            else:
                # EN,EN
                uncertainty_factors = intent_result.uncertainty_factors
                if len(uncertainty_factors) > 2:
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
                        f"EN'{intent_result.intent}',EN?",
                        "EN?",
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
        """EN"""
        try:
            logger.info("EN")

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

            # EN:EN
            routing_decision = state.get("routing_decision")
            if routing_decision and routing_decision.confidence < 0.7:
                # EN,EN
                state["metadata"]["clarification_handled"] = True
                return state  # EN
            else:
                # EN
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
        """Best-effort interaction recording with timeout protection."""
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
                timeout=2.0,
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
        """EN"""
        if state.get("error"):
            return "error"

        if state.get("clarification_needed", False):
            return "low_confidence"
        else:
            return "high_confidence"

    def _route_after_clarification(self, state: WorkflowState) -> str:
        """EN"""
        if state.get("metadata", {}).get("awaiting_user_clarification", False):
            return "await_user_input"

        # EN:EN
        return "proceed_with_fallback"

    async def _generate_clarification_with_prompt(
        self, prompt_content: str, context: Dict[str, Any]
    ) -> str:
        """ENPromptEN"""
        try:
            # ENLLMEN
            # EN,EN
            questions = context.get("clarification_questions", [])
            possible_intents = context.get("possible_intents", [])

            if questions:
                clarification = f"EN.EN:\n\n"
                for i, question in enumerate(questions, 1):
                    clarification += f"{i}. {question}\n"
                clarification += "\nEN,EN."
            else:
                clarification = "EN,EN."

            return clarification
        except Exception as e:
            logger.error(f"EN: {str(e)}")
            return "EN,EN."

    def _generate_default_clarification(self, context: Dict[str, Any]) -> str:
        """EN"""
        questions = context.get("clarification_questions", [])
        possible_intents = context.get("possible_intents", [])

        if questions:
            clarification = f"EN.EN:\n\n"
            for i, question in enumerate(questions, 1):
                clarification += f"{i}. {question}\n"
            clarification += "\nEN,EN."
        else:
            clarification = "EN,EN."

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

    async def _dispatch_rag_query(
        self,
        *,
        query: str,
        parameters: Dict[str, Any],
    ) -> Dict[str, Any]:
        top_k_raw = parameters.get("top_k")
        try:
            top_k = int(top_k_raw) if top_k_raw is not None else int(settings.top_k)
        except Exception:
            top_k = int(settings.top_k)

        rag = self._get_rag_service()
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

        if not isinstance(chunks, list):
            chunks = []
        if rag.use_reranker and rag.reranker and chunks:
            chunks = await asyncio.to_thread(
                rag.reranker.rerank,
                query=query,
                documents=chunks,
                top_k=max(top_k, 1),
            )

        sources = self._unique_sources(chunks)
        if not chunks:
            raise RuntimeError("RAG retrieval returned empty context")
        if not sources:
            raise RuntimeError("RAG returned no grounded sources")

        highlights: List[str] = []
        for idx, chunk in enumerate(chunks[:3], 1):
            text = str(chunk.get("content") or "").strip().replace("\n", " ")
            if not text:
                continue
            highlights.append(f"{idx}. {text[:260]}")
        if not highlights:
            raise RuntimeError("RAG contexts are empty after retrieval")

        cited_answer = (
            "Based on retrieved construction knowledge:\n"
            + "\n".join(highlights)
            + f"\n\n[sources: {', '.join(sources)}]"
        )
        return {
            "response": cited_answer,
            "metadata": {
                "source_count": len(sources),
                "sources": sources,
                "retrieved_count": len(chunks),
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
        del system_prompt, prompt_meta, route_mode
        normalized_params = parameters if isinstance(parameters, dict) else {}

        if agent_type in {AgentType.RAG_AGENT, AgentType.GENERAL_AGENT}:
            return await self._dispatch_rag_query(query=query, parameters=normalized_params)
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
            # EN
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
            config = {"configurable": {"thread_id": thread_id or session_id}}
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
            config = {"configurable": {"thread_id": thread_id or session_id}}

            # EN
            state_update = WorkflowState(
                messages=[HumanMessage(content=user_response)],
                session_id=session_id,
                user_id=None,
                current_query=user_response,
                query_context=QueryContext(session_id=session_id),
                session_context=SessionContext(session_id=session_id),
                intent_result=None,
                routing_decision=None,
                clarification_needed=False,
                clarification_response=None,
                agent_response=None,
                workflow_complete=False,
                error=None,
                system_prompt=None,
                prompt_meta=None,
                metadata={
                    "continuation_timestamp": datetime.now().isoformat(),
                    "workflow_runner": "intent_workflow",
                    "prompt_experiments_enabled": bool(
                        settings.prompt_experiments_enabled
                    ),
                },
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
