"""Workflow query routes."""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Dict, Optional, Protocol
from uuid import uuid4

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from backend.config import settings
from backend.observability.workflow_metrics import (
    record_workflow_node_latency,
    record_workflow_request,
)
from backend.services.audit_logger import audit_logger
from backend.services.demo_mode_service import get_demo_mode_service

router = APIRouter(prefix="/api/v1/workflow", tags=["workflow"])
logger = logging.getLogger(__name__)

_workflow_service = None
_workflow_lock = asyncio.Lock()


class WorkflowRunner(Protocol):
    async def run_workflow(
        self,
        query: str,
        session_id: str,
        user_id: Optional[str] = None,
        thread_id: Optional[str] = None,
        route_mode: Optional[str] = None,
    ) -> Dict[str, Any]:
        ...


class WorkflowHealth(BaseModel):
    status: str = Field(default="ok")
    component: str = Field(default="workflow")


class WorkflowQueryRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=4000)
    session_id: Optional[str] = Field(default=None, max_length=128)
    user_id: Optional[str] = Field(default=None, max_length=128)
    thread_id: Optional[str] = Field(default=None, max_length=128)
    route_mode: Optional[str] = Field(default=None, max_length=32)


class WorkflowQueryResponse(BaseModel):
    success: bool
    trace_id: str
    session_id: str
    intent: Optional[str] = None
    route_mode: str = Field(default="local_only")
    provider_used: Optional[str] = None
    response: Optional[str] = None
    prompt_meta: Optional[Dict[str, Any]] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    error: Optional[str] = None


async def _initialize_workflow_service() -> WorkflowRunner:
    from backend.config import get_database_pool
    from backend.services.context_manager import ContextManager
    from backend.services.intent_classification.intent_classifier import IntentClassifier
    from backend.services.intent_classification.intent_workflow import (
        IntentClassificationWorkflow,
    )
    from backend.services.llm_integration.llm_client import get_llm_client
    from backend.services.prompt_manager import PromptManager
    from backend.services.routing_decision import RoutingDecisionEngine

    pool = await get_database_pool()
    prompt_manager = PromptManager(pool)
    llm_client = get_llm_client()
    context_manager = ContextManager(storage_backend="memory")
    intent_classifier = IntentClassifier(
        prompt_manager=prompt_manager,
        llm_client=llm_client,
    )
    routing_engine = RoutingDecisionEngine()
    return IntentClassificationWorkflow(
        intent_classifier=intent_classifier,
        context_manager=context_manager,
        routing_engine=routing_engine,
        prompt_manager=prompt_manager,
    )


async def get_workflow_runner() -> WorkflowRunner:
    global _workflow_service
    if _workflow_service is not None:
        return _workflow_service

    async with _workflow_lock:
        if _workflow_service is not None:
            return _workflow_service
        runner_mode = (settings.workflow_runner_mode or "auto").strip().lower()
        if runner_mode == "fallback":
            logger.info("Workflow runner forced to fallback mode")
            _workflow_service = await _initialize_fallback_runner()
            return _workflow_service
        if runner_mode == "intent":
            _workflow_service = await _initialize_workflow_service()
            return _workflow_service
        try:
            _workflow_service = await _initialize_workflow_service()
        except Exception as exc:
            logger.warning(
                "Falling back to lightweight workflow runner due to init error: %s",
                exc,
            )
            _workflow_service = await _initialize_fallback_runner()
    return _workflow_service


async def _initialize_fallback_runner() -> WorkflowRunner:
    from backend.services.workflows.orchestrator import (
        DefaultWorkflowRunner,
        WorkflowOrchestrator,
    )

    services = type("WorkflowServices", (), {})()
    try:
        from backend.config import get_database_pool
        from backend.services.prompt_manager import PromptManager

        pool = await get_database_pool()
        services.prompt_manager = PromptManager(pool)
    except Exception as exc:
        logger.warning("Fallback runner without prompt manager: %s", exc)

    try:
        from backend.services.code_executor import get_code_execution_manager

        services.code_execution_manager = get_code_execution_manager()
    except Exception as exc:
        logger.warning("Fallback runner without code execution manager: %s", exc)

    try:
        from backend.services.rag_engine import SimpleRAG

        rag = SimpleRAG(
            use_hybrid_search=True,
            use_reranker=False,
            enable_feedback=settings.enable_feedback_system,
        )
        services.retriever = _RAGRetrieverAdapter(rag)
    except Exception as exc:
        logger.warning("Fallback runner without RAG retriever: %s", exc)

    try:
        from backend.services.llm_integration.dispatch_service import get_dispatch_service

        services.response_builder = _DispatchResponseBuilder(get_dispatch_service())
    except Exception as exc:
        logger.warning("Fallback runner without dispatch response builder: %s", exc)

    try:
        from backend.services.cost_estimation_service import CostEstimationService

        services.cost_estimation_service = CostEstimationService()
    except Exception as exc:
        logger.warning("Fallback runner without cost estimation service: %s", exc)

    try:
        from backend.services.intent_classification.simple_intent_classifier import (
            SimpleIntentClassifier,
        )

        services.intent_classifier = SimpleIntentClassifier()
    except Exception as exc:
        logger.warning("Fallback runner without intent classifier: %s", exc)

    orchestrator = WorkflowOrchestrator(services=services)
    return DefaultWorkflowRunner(orchestrator=orchestrator)


@router.get("/health", response_model=WorkflowHealth)
async def workflow_health() -> WorkflowHealth:
    return WorkflowHealth()


@router.post("/query", response_model=WorkflowQueryResponse)
async def workflow_query(
    request: WorkflowQueryRequest,
    workflow: WorkflowRunner = Depends(get_workflow_runner),
) -> WorkflowQueryResponse:
    started = asyncio.get_running_loop().time()
    trace_id = str(uuid4())
    session_id = request.session_id or trace_id
    demo_mode_service = get_demo_mode_service()
    demo_state = demo_mode_service.get_state()
    effective_route_mode = demo_mode_service.resolve_route_mode(request.route_mode)

    replay = demo_mode_service.replay_response(request.query)
    if replay is not None:
        metadata: Dict[str, Any] = {
            "trace_id": trace_id,
            "session_id": session_id,
            "tenant_id": settings.default_tenant_id,
            "workflow_runner": "scripted_replay",
            "demo_mode": demo_state["mode"],
            "effective_route_mode": effective_route_mode,
            "replay_scenario": replay["id"],
        }
        response = WorkflowQueryResponse(
            success=True,
            trace_id=trace_id,
            session_id=session_id,
            intent=str(replay.get("intent") or "knowledge_retrieval"),
            route_mode="scripted_replay",
            provider_used="scripted_replay",
            response=str(replay.get("response") or ""),
            prompt_meta=None,
            metadata=metadata,
            error=None,
        )
        record_workflow_request(
            route_mode="scripted_replay",
            provider="scripted_replay",
            status="success",
            latency_seconds=max(0.0, (asyncio.get_running_loop().time() - started)),
        )
        audit_logger.log_event(
            action="workflow.query",
            tenant_id=settings.default_tenant_id,
            status="success",
            user_id=request.user_id,
            detail={
                "trace_id": trace_id,
                "session_id": session_id,
                "intent": response.intent,
                "route_mode": response.route_mode,
                "provider_used": response.provider_used,
                "latency_ms": 0,
                "workflow_runner": "scripted_replay",
                "demo_mode": demo_state["mode"],
            },
        )
        return response

    result = await workflow.run_workflow(
        query=request.query,
        session_id=session_id,
        user_id=request.user_id,
        thread_id=request.thread_id or session_id,
        route_mode=effective_route_mode,
    )

    metadata = result.get("metadata") or {}
    metadata["trace_id"] = trace_id
    metadata["session_id"] = session_id
    metadata["demo_mode"] = demo_state["mode"]
    metadata["effective_route_mode"] = effective_route_mode
    intent_result = result.get("intent_result") or {}
    if not isinstance(intent_result, dict):
        intent_result = {}

    # Fallback runner cannot consume route mode through run_workflow args.
    # Re-apply requested policy here to keep API behavior consistent.
    if metadata.get("workflow_runner") == "fallback_orchestrator":
        from backend.services.workflows.policies.budget_policy import can_use_cloud
        from backend.services.workflows.policies.routing_policy import (
            resolve_route_mode,
            select_provider,
        )

        normalized_mode = resolve_route_mode(effective_route_mode, "local_only")
        budget_eval = metadata.get("budget_evaluation")
        cloud_allowed = can_use_cloud(budget_eval) if isinstance(budget_eval, dict) else False
        metadata["route_mode"] = normalized_mode
        metadata["provider_used"] = select_provider(normalized_mode, cloud_allowed)

    route_mode = (
        effective_route_mode
        or metadata.get("route_mode")
        or metadata.get("routing_path")
        or "local_only"
    )
    provider_used = metadata.get("provider_used")
    prompt_meta = metadata.get("prompt_meta")

    response = WorkflowQueryResponse(
        success=bool(result.get("success")),
        trace_id=trace_id,
        session_id=session_id,
        intent=intent_result.get("intent"),
        route_mode=str(route_mode),
        provider_used=provider_used,
        response=result.get("agent_response"),
        prompt_meta=prompt_meta if isinstance(prompt_meta, dict) else None,
        metadata=metadata,
        error=result.get("error"),
    )

    latency_ms = int((asyncio.get_running_loop().time() - started) * 1000)
    node_timings = (result.get("metrics") or {}).get("node_latency_ms")
    if isinstance(node_timings, dict):
        for node_name, value in node_timings.items():
            try:
                record_workflow_node_latency(str(node_name), float(value) / 1000.0)
            except Exception:
                continue
    record_workflow_request(
        route_mode=str(route_mode),
        provider=response.provider_used or "unknown",
        status="success" if response.success else "error",
        latency_seconds=max(0.0, latency_ms / 1000.0),
    )
    audit_logger.log_event(
        action="workflow.query",
        tenant_id=metadata.get("tenant_id") or settings.default_tenant_id,
        status="success" if response.success else "error",
        user_id=request.user_id,
        detail={
            "trace_id": trace_id,
            "session_id": session_id,
            "intent": response.intent,
            "route_mode": response.route_mode,
            "provider_used": response.provider_used,
            "latency_ms": latency_ms,
            "workflow_runner": metadata.get("workflow_runner", "intent_workflow"),
        },
    )
    return response


class _RAGRetrieverAdapter:
    def __init__(self, rag):
        self.rag = rag

    async def retrieve(self, query: str, top_k: int, metadata: dict):
        del metadata
        if getattr(self.rag, "hybrid_retriever", None) is not None:
            return self.rag.hybrid_retriever.search(query=query, top_k=top_k)
        return []


class _DispatchResponseBuilder:
    def __init__(self, dispatch_service):
        self.dispatch_service = dispatch_service

    def __call__(self, *, state: Dict[str, Any]) -> str:
        try:
            from backend.services.llm_integration.types import DispatchRequest

            metadata = state.get("metadata") or {}
            contexts = state.get("retrieved_context") or []
            context_text = "\n\n".join(
                str(item.get("content") or item.get("text") or "")
                for item in contexts
                if isinstance(item, dict)
            )
            system_prompt = state.get("system_prompt") or ""
            prompt = (
                f"{system_prompt}\n\n"
                f"Context:\n{context_text}\n\n"
                f"User Query:\n{state.get('query', '')}\n"
            ).strip()
            if not prompt:
                prompt = str(state.get("query") or "")

            route_mode = str(state.get("route_mode") or "local_only")
            if route_mode not in {"local_only", "hybrid_auto", "cloud_only"}:
                route_mode = "local_only"

            request = DispatchRequest(
                prompt=prompt,
                tenant_id=str(state.get("tenant_id") or settings.default_tenant_id),
                trace_id=str(state.get("trace_id") or uuid4()),
                route_mode=route_mode,
                temperature=metadata.get("temperature"),
                max_tokens=metadata.get("max_tokens"),
                top_p=metadata.get("top_p"),
            )
            response = self.dispatch_service.generate(request)
            metadata["dispatch"] = response.to_dict()
            state["provider_used"] = response.provider
            state["route_mode"] = response.route_mode
            if response.success and response.text:
                return response.text
            return f"Dispatch failed: {response.error or 'unknown_error'}"
        except Exception as exc:
            logger.warning("Dispatch response builder fallback: %s", exc)
            return "Dispatch unavailable, returning fallback workflow response."
