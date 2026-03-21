"""
Intent Classification API
RESTful endpoints for intent classification workflows.
"""

import asyncio
import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from backend.security.dependencies import get_current_tenant, secure_endpoint
from backend.services.context_manager import ContextManager
from backend.services.intent_classification.intent_classifier import IntentClassifier
from backend.services.intent_classification.intent_workflow import (
    IntentClassificationWorkflow,
)
from backend.services.prompt_manager import PromptManager
from backend.services.routing_decision import RoutingDecisionEngine

logger = logging.getLogger(__name__)

# Router
router = APIRouter(
    prefix="/api/intent",
    tags=["Intent Classification"],
    dependencies=[Depends(secure_endpoint)],
)

# Singleton workflow instance
_intent_workflow: Optional[IntentClassificationWorkflow] = None


# Request/response schemas
class ClassifyRequest(BaseModel):
    """API schema."""

    query: str = Field(..., description="Description", min_length=1, max_length=2000)
    session_id: str = Field(..., description="Session ID", min_length=1, max_length=100)
    user_id: Optional[str] = Field(None, description="User ID", max_length=100)
    context: Optional[Dict[str, Any]] = Field(None, description="Description")
    thread_id: Optional[str] = Field(None, description="Thread ID")


class ClassifyResponse(BaseModel):
    """API schema."""

    success: bool = Field(..., description="Description")
    intent: Optional[str] = Field(None, description="Description")
    confidence: Optional[float] = Field(None, description="Description")
    reasoning: Optional[str] = Field(None, description="Description")
    routing_decision: Optional[Dict[str, Any]] = Field(None, description="Description")
    agent_response: Optional[str] = Field(None, description="Agent response text")
    clarification_needed: bool = Field(False, description="Description")
    clarification_message: Optional[str] = Field(None, description="Description")
    processing_time_ms: Optional[int] = Field(
        None, description="Processing time in milliseconds"
    )
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Description")
    node_trace: List[Dict[str, Any]] = Field(
        default_factory=list, description="Per-node execution trace"
    )
    capability_scores: Optional[Dict[str, Any]] = Field(
        None, description="Score breakdown per capability"
    )
    matched_keywords: Optional[List] = Field(
        None, description="Keywords that matched during classification"
    )
    error: Optional[str] = Field(None, description="Description")


class ContinueWorkflowRequest(BaseModel):
    """API schema."""

    user_response: str = Field(
        ..., description="Description", min_length=1, max_length=2000
    )
    session_id: str = Field(..., description="Session ID", min_length=1, max_length=100)
    thread_id: Optional[str] = Field(None, description="Thread ID")


class SessionContextResponse(BaseModel):
    """API schema."""

    session_id: str
    user_id: Optional[str]
    query_count: int
    session_topic: str
    session_stage: str
    uploaded_files_count: int
    recent_intents: List[str]
    context_keywords: List[str]
    completion_rate: float
    session_duration_minutes: float


class WorkflowStatsResponse(BaseModel):
    """API schema."""

    total_routes: int
    direct_routing_rate: float
    clarification_rate: float
    fallback_rate: float
    agent_usage_rates: Dict[str, float]
    available_agents: int
    system_load: float


def get_intent_workflow() -> IntentClassificationWorkflow:
    """API schema."""
    global _intent_workflow
    if _intent_workflow is None:
        raise HTTPException(
            status_code=500, detail="Intent workflow is not initialized."
        )
    return _intent_workflow


async def initialize_intent_workflow():
    """API schema."""
    global _intent_workflow

    try:
        # EN
        # EN,EN
        from backend.config import get_database_pool
        from backend.services.llm_integration.llm_client import get_llm_client

        pool = await get_database_pool()
        from backend.services.llm_integration.llm_client import LLMClientFactory

        try:
            intent_llm_client = LLMClientFactory.create_client("zhipu")
        except Exception:
            intent_llm_client = get_llm_client()

        # EN
        prompt_manager = PromptManager(pool)
        context_manager = ContextManager(storage_backend="memory")
        intent_classifier = IntentClassifier(
            prompt_manager=prompt_manager,
            llm_client=intent_llm_client,
        )
        routing_engine = RoutingDecisionEngine()

        # EN
        _intent_workflow = IntentClassificationWorkflow(
            intent_classifier=intent_classifier,
            context_manager=context_manager,
            routing_engine=routing_engine,
            prompt_manager=prompt_manager,
        )

        logger.info("Intent workflow initialized successfully.")

    except Exception as e:
        logger.error(f"Failed to initialize intent workflow: {str(e)}")
        raise


@router.get("/capabilities")
async def get_capabilities():
    """Return the system capability catalog (MCP-like tools/list)."""
    from backend.services.intent_classification.capability_registry import (
        get_capability_registry,
    )

    registry = get_capability_registry()
    return {
        "capabilities": registry.to_catalog(),
        "version": "1.0",
        "total": len(registry.list_all()),
    }


@router.post("/classify", response_model=ClassifyResponse)
async def classify_intent(
    request: ClassifyRequest,
    background_tasks: BackgroundTasks,
    workflow: IntentClassificationWorkflow = Depends(get_intent_workflow),
):
    """Classify user intent and return routing decision metadata."""
    try:
        start_time = datetime.now()

        logger.info(
            f"Classify request received. session_id={request.session_id}, "
            f"query_preview={request.query[:100]}..."
        )

        # EN
        result = await workflow.run_workflow(
            query=request.query,
            session_id=request.session_id,
            user_id=request.user_id,
            thread_id=request.thread_id,
        )

        # EN
        processing_time = int((datetime.now() - start_time).total_seconds() * 1000)

        # Extract capability_scores and matched_keywords from workflow metadata
        metadata = result.get("metadata", {})
        intent_result_data = result.get("intent_result") or {}
        cap_scores = metadata.get("capability_scores")
        matched_kw = metadata.get("matched_keywords")

        # EN
        response = ClassifyResponse(
            success=result["success"],
            intent=intent_result_data.get("intent"),
            confidence=intent_result_data.get("confidence"),
            reasoning=intent_result_data.get("reasoning"),
            routing_decision=result.get("routing_decision"),
            agent_response=result.get("agent_response"),
            clarification_needed=result.get("clarification_needed", False),
            clarification_message=result.get("clarification_response"),
            processing_time_ms=processing_time,
            metadata=metadata,
            node_trace=result.get("node_trace", []),
            capability_scores=cap_scores,
            matched_keywords=matched_kw,
            error=result.get("error"),
        )

        # EN
        background_tasks.add_task(
            log_classification_usage,
            request.session_id,
            request.user_id,
            request.query,
            result,
        )

        logger.info(f"Classification completed. success={result['success']}")
        return response

    except Exception as e:
        logger.error(f"Intent classification API error: {str(e)}")
        return ClassifyResponse(
            success=False,
            error="Internal classification error",
            agent_response="An internal error occurred while classifying the request.",
        )


@router.post("/continue", response_model=ClassifyResponse)
async def continue_workflow(
    request: ContinueWorkflowRequest,
    background_tasks: BackgroundTasks,
    workflow: IntentClassificationWorkflow = Depends(get_intent_workflow),
):
    """Continue a pending clarification workflow using user follow-up input."""
    try:
        logger.info(f"Continue request received. session_id={request.session_id}")

        # EN
        result = await workflow.continue_workflow(
            user_response=request.user_response,
            session_id=request.session_id,
            thread_id=request.thread_id,
        )

        # EN
        response = ClassifyResponse(
            success=result["success"],
            intent=result.get("intent_result", {}).get("intent")
            if result.get("intent_result")
            else None,
            confidence=result.get("intent_result", {}).get("confidence")
            if result.get("intent_result")
            else None,
            reasoning=result.get("intent_result", {}).get("reasoning")
            if result.get("intent_result")
            else None,
            routing_decision=result.get("routing_decision"),
            agent_response=result.get("agent_response"),
            clarification_needed=result.get("clarification_needed", False),
            clarification_message=result.get("clarification_response"),
            metadata=result.get("metadata", {}),
            error=result.get("error"),
        )

        # EN
        background_tasks.add_task(
            log_continuation_usage, request.session_id, request.user_response, result
        )

        logger.info(f"Continuation completed. success={result['success']}")
        return response

    except Exception as e:
        logger.error(f"Intent continuation API error: {str(e)}")
        return ClassifyResponse(
            success=False,
            error="Internal continuation error",
            agent_response="An internal error occurred while continuing the workflow.",
        )


@router.get("/session/{session_id}/context", response_model=SessionContextResponse)
async def get_session_context(
    session_id: str,
    workflow: IntentClassificationWorkflow = Depends(get_intent_workflow),
):
    """Get aggregated session context information for a workflow session."""
    try:
        logger.info(f"Session context requested. session_id={session_id}")

        # EN
        session_context = await workflow.context_manager.get_session_context(session_id)

        # EN
        enhanced_context = await workflow.context_manager.get_enhanced_context(
            session_id=session_id, max_history=10, include_files=True
        )

        # EN
        response = SessionContextResponse(
            session_id=session_context.session_id,
            user_id=session_context.user_id,
            query_count=session_context.query_count,
            session_topic=session_context.session_topic,
            session_stage=session_context.session_stage,
            uploaded_files_count=len(session_context.uploaded_files),
            recent_intents=session_context.get_recent_intents(5),
            context_keywords=enhanced_context.get("context_keywords", []),
            completion_rate=session_context.completion_rate,
            session_duration_minutes=session_context.get_session_duration() / 60,
        )

        logger.info(f"Session context loaded. query_count={response.query_count}")
        return response

    except Exception as e:
        logger.error(f"Failed to get session context: {str(e)}")
        raise HTTPException(status_code=500, detail="Session context error")


@router.get("/session/{session_id}/patterns")
async def analyze_session_patterns(
    session_id: str,
    workflow: IntentClassificationWorkflow = Depends(get_intent_workflow),
):
    """Analyze interaction patterns and context evolution for one session."""
    try:
        logger.info(f"Session pattern analysis requested. session_id={session_id}")

        # EN
        patterns = await workflow.context_manager.analyze_session_patterns(session_id)

        return {
            "success": True,
            "session_id": session_id,
            "patterns": patterns,
            "analysis_timestamp": datetime.now().isoformat(),
        }

    except Exception as e:
        logger.error(f"Failed to analyze session patterns: {str(e)}")
        raise HTTPException(status_code=500, detail="Session pattern analysis error")


@router.get("/stats/workflow", response_model=WorkflowStatsResponse)
async def get_workflow_statistics(
    workflow: IntentClassificationWorkflow = Depends(get_intent_workflow),
):
    """Return workflow-level routing and utilization statistics."""
    try:
        logger.info("Workflow statistics requested.")

        # EN
        stats = workflow.get_workflow_stats()

        # EN
        routing_stats = workflow.routing_engine.get_routing_statistics()

        # EN
        response = WorkflowStatsResponse(
            total_routes=routing_stats.get("total_routes", 0),
            direct_routing_rate=routing_stats.get("direct_routing_rate", 0.0),
            clarification_rate=routing_stats.get("clarification_rate", 0.0),
            fallback_rate=routing_stats.get("fallback_rate", 0.0),
            agent_usage_rates=routing_stats.get("agent_usage_rates", {}),
            available_agents=len(
                workflow.routing_engine.system_status.get_available_agents()
            ),
            system_load=workflow.routing_engine.system_status.system_load,
        )

        logger.info(f"Workflow statistics ready. total_routes={response.total_routes}")
        return response

    except Exception as e:
        logger.error(f"Failed to get workflow statistics: {str(e)}")
        raise HTTPException(status_code=500, detail="Workflow statistics error")


@router.post("/test/classification")
async def test_intent_classification(
    query: str,
    session_id: str = "test_session",
    user_id: Optional[str] = None,
    workflow: IntentClassificationWorkflow = Depends(get_intent_workflow),
):
    """Run a direct classifier test endpoint for diagnostics."""
    try:
        logger.info(
            f"Classification test request received. query_preview={query[:50]}..."
        )

        # EN
        test_context = QueryContext(
            session_id=session_id,
            user_id=user_id,
            current_query=query,
            session_history=[],
            recent_intents=[],
            uploaded_files=[],
            user_preferences={},
            context_keywords=[],
        )

        # EN
        intent_result = await workflow.intent_classifier.classify_intent(
            query=query, context=test_context
        )

        return {
            "success": True,
            "intent_result": intent_result.to_dict(),
            "test_timestamp": datetime.now().isoformat(),
        }

    except Exception as e:
        logger.error(f"Classification test failed: {str(e)}")
        return {
            "success": False,
            "error": "Classification test failed",
            "test_timestamp": datetime.now().isoformat(),
        }


@router.get("/health")
async def health_check(
    workflow: IntentClassificationWorkflow = Depends(get_intent_workflow),
):
    """Return health status for intent workflow components."""
    try:
        # EN
        classifier_health = await workflow.intent_classifier.health_check()
        context_health = await workflow.context_manager.health_check()
        routing_health = await workflow.routing_engine.health_check()

        overall_health = all(
            [
                classifier_health.get("status") == "healthy",
                context_health.get("status") == "healthy",
                routing_health.get("status") == "healthy",
            ]
        )

        return {
            "status": "healthy" if overall_health else "degraded",
            "timestamp": datetime.now().isoformat(),
            "components": {
                "intent_classifier": classifier_health,
                "context_manager": context_health,
                "routing_engine": routing_health,
                "prompt_manager": "enabled" if workflow.prompt_manager else "disabled",
            },
            "workflow": workflow.get_workflow_stats(),
        }

    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        return {
            "status": "unhealthy",
            "timestamp": datetime.now().isoformat(),
            "error": "Health check failed",
        }


# EN
async def log_classification_usage(
    session_id: str, user_id: Optional[str], query: str, result: Dict[str, Any]
):
    """API schema."""
    try:
        # EN
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "session_id": session_id,
            "user_id": user_id,
            "query": query,
            "success": result["success"],
            "intent": result.get("intent_result", {}).get("intent"),
            "confidence": result.get("intent_result", {}).get("confidence"),
            "selected_agent": result.get("routing_decision", {}).get("selected_agent"),
            "clarification_needed": result.get("clarification_needed", False),
        }

        logger.info(
            f"Classification usage log: {json.dumps(log_entry, ensure_ascii=False)}"
        )

    except Exception as e:
        logger.error(f"Failed to write classification usage log: {str(e)}")


async def log_continuation_usage(
    session_id: str, user_response: str, result: Dict[str, Any]
):
    """API schema."""
    try:
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "session_id": session_id,
            "user_response": user_response,
            "success": result["success"],
            "clarification_needed": result.get("clarification_needed", False),
        }

        logger.info(
            f"Continuation usage log: {json.dumps(log_entry, ensure_ascii=False)}"
        )

    except Exception as e:
        logger.error(f"Failed to write continuation usage log: {str(e)}")


# EN
async def initialize_intent_routes():
    """API schema."""
    await initialize_intent_workflow()
    logger.info("Intent classification API routes initialized.")
