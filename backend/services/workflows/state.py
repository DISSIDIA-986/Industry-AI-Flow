"""Core workflow state contracts for the new RAG workflow pipeline."""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional, TypedDict


class ErrorCode(str, Enum):
    """Structured error codes for pipeline node failures.

    Each node sets an appropriate code before breaking the pipeline,
    enabling downstream consumers (API responses, frontend) to show
    specific error messages instead of generic "something went wrong".
    """

    SAFETY_BLOCKED = "SAFETY_BLOCKED"
    RETRIEVER_TIMEOUT = "RETRIEVER_TIMEOUT"
    RETRIEVER_EMPTY = "RETRIEVER_EMPTY"
    RERANKER_FAILURE = "RERANKER_FAILURE"
    LLM_TIMEOUT = "LLM_TIMEOUT"
    LLM_GENERATION_ERROR = "LLM_GENERATION_ERROR"
    CODE_VALIDATION_FAILED = "CODE_VALIDATION_FAILED"
    SANDBOX_TIMEOUT = "SANDBOX_TIMEOUT"
    COST_ESTIMATION_ERROR = "COST_ESTIMATION_ERROR"
    SERVICE_UNAVAILABLE = "SERVICE_UNAVAILABLE"
    NODE_TIMEOUT = "NODE_TIMEOUT"
    UNKNOWN_ERROR = "UNKNOWN_ERROR"


class WorkflowState(TypedDict, total=False):
    trace_id: str
    tenant_id: str
    query: str
    intent: Optional[str]
    retrieved_context: List[Dict[str, Any]]
    system_prompt: Optional[str]
    prompt_meta: Optional[Dict[str, Any]]
    route_mode: str
    provider_used: Optional[str]
    response: Optional[str]
    metrics: Dict[str, Any]
    error: Optional[str]
    metadata: Dict[str, Any]


class WorkflowServices(TypedDict, total=False):
    intent_classifier: Any
    retriever: Any
    reranker: Any
    prompt_manager: Any
    template_selector: Any
    cost_estimation_service: Any
    code_execution_manager: Any
    response_builder: Any
