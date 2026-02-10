"""Core workflow state contracts for the new RAG workflow pipeline."""

from __future__ import annotations

from typing import Any, Dict, List, Optional, TypedDict


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
    code_execution_manager: Any
    response_builder: Any
