"""Workflow graph entrypoints.

10-node fixed-order execution pipeline:
  intent → safety → cost_estimation → retrieval → rerank →
  prompt → route → code_exec → response → groundedness

Each node has an individual timeout SLA (seconds).  If a node
exceeds its SLA, an ``asyncio.TimeoutError`` is caught and an
``ErrorCode.NODE_TIMEOUT`` is written to ``state["error_code"]``.
The global 300 s timeout remains as a safety net.
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Any

logger = logging.getLogger(__name__)

from backend.observability.langfuse_client import get_langfuse, is_enabled
from backend.services.workflows.nodes.code_exec_node import code_exec_node
from backend.services.workflows.nodes.cost_estimation_node import cost_estimation_node
from backend.services.workflows.nodes.groundedness_node import groundedness_node
from backend.services.workflows.nodes.intent_node import intent_node
from backend.services.workflows.nodes.prompt_node import prompt_node
from backend.services.workflows.nodes.rerank_node import rerank_node
from backend.services.workflows.nodes.response_node import response_node
from backend.services.workflows.nodes.retrieval_node import retrieval_node
from backend.services.workflows.nodes.route_node import route_node
from backend.services.workflows.nodes.safety_node import safety_node
from backend.services.workflows.state import ErrorCode, WorkflowState

# Per-node timeout SLAs (seconds).  Generous for demo stability.
NODE_TIMEOUTS: dict[str, float] = {
    "intent_node": 30,
    "safety_node": 10,
    "cost_estimation_node": 20,
    "retrieval_node": 60,
    "rerank_node": 30,
    "prompt_node": 5,
    "route_node": 5,
    "code_exec_node": 90,
    "response_node": 60,
    "groundedness_node": 15,
}


async def run_prompt_stage(state: WorkflowState, services: Any) -> WorkflowState:
    """Run the prompt selection/render stage."""
    if getattr(services, "prompt_manager", None) is None:
        return state
    return await prompt_node(state, services)


async def _run_node(
    node_name: str,
    handler,
    state: WorkflowState,
    services: Any,
) -> WorkflowState:
    started = time.perf_counter()
    metadata = state.setdefault("metadata", {})
    metrics = state.setdefault("metrics", {})
    node_latency = metrics.setdefault("node_latency_ms", {})
    completed_nodes = metadata.setdefault("completed_nodes", [])
    timeout = NODE_TIMEOUTS.get(node_name, 60)

    lf = get_langfuse() if is_enabled() else None
    span_ctx = (
        lf.start_as_current_observation(
            name=node_name,
            as_type="span",
            metadata={"timeout_sla_s": timeout},
        )
        if lf is not None
        else None
    )

    try:
        if span_ctx is not None:
            span = span_ctx.__enter__()
        try:
            updated = await asyncio.wait_for(
                handler(state, services), timeout=timeout
            )
            elapsed_ms = int((time.perf_counter() - started) * 1000)
            node_latency[node_name] = elapsed_ms
            if node_name not in completed_nodes:
                completed_nodes.append(node_name)
            if span_ctx is not None:
                try:
                    span.update(
                        output={"status": "ok"},
                        metadata={"latency_ms": elapsed_ms, "timeout_sla_s": timeout},
                    )
                except Exception:  # pylint: disable=broad-except
                    pass
            return updated
        except asyncio.TimeoutError:
            elapsed = int((time.perf_counter() - started) * 1000)
            node_latency[node_name] = elapsed
            logger.error(
                "Workflow node '%s' timed out after %ds (SLA: %ds)",
                node_name, elapsed // 1000, int(timeout),
            )
            metadata["failed_node"] = node_name
            metadata["error_code"] = ErrorCode.NODE_TIMEOUT.value
            state["error"] = (
                f"Processing timed out at {node_name.replace('_node', '')} stage. "
                "Please try again."
            )
            if span_ctx is not None:
                try:
                    span.update(
                        output={"status": "timeout"},
                        metadata={"latency_ms": elapsed, "error_code": "NODE_TIMEOUT"},
                        level="ERROR",
                    )
                except Exception:  # pylint: disable=broad-except
                    pass
            return state
        except Exception as exc:  # pragma: no cover - safety net
            elapsed = int((time.perf_counter() - started) * 1000)
            node_latency[node_name] = elapsed
            logger.exception("Workflow node '%s' failed: %s", node_name, exc)
            metadata["failed_node"] = node_name
            metadata["error_code"] = ErrorCode.UNKNOWN_ERROR.value
            state["error"] = (
                "I encountered an issue processing your request. Please try again."
            )
            if span_ctx is not None:
                try:
                    span.update(
                        output={"status": "error", "error": str(exc)[:500]},
                        metadata={"latency_ms": elapsed, "error_code": "UNKNOWN_ERROR"},
                        level="ERROR",
                    )
                except Exception:  # pylint: disable=broad-except
                    pass
            return state
    finally:
        if span_ctx is not None:
            try:
                span_ctx.__exit__(None, None, None)
            except Exception:  # pylint: disable=broad-except
                pass


async def run_workflow_pipeline(state: WorkflowState, services: Any) -> WorkflowState:
    """
    Execute workflow pipeline in fixed order with guarded transitions.
    """
    pipeline = [
        ("intent_node", intent_node),
        ("safety_node", safety_node),
        ("cost_estimation_node", cost_estimation_node),
        ("retrieval_node", retrieval_node),
        ("rerank_node", rerank_node),
        ("prompt_node", prompt_node),
        ("route_node", route_node),
        ("code_exec_node", code_exec_node),
        ("response_node", response_node),
        ("groundedness_node", groundedness_node),
    ]

    async def _execute_pipeline() -> WorkflowState:
        nonlocal state
        # Clear stale shortcut flag from previous turns
        metadata = state.setdefault("metadata", {})
        metadata.pop("shortcut_response", None)

        for node_name, handler in pipeline:
            if state.get("error"):
                break

            metadata = state.setdefault("metadata", {})
            if metadata.get("shortcut_response", False) and node_name not in {
                "safety_node",
                "response_node",
            }:
                # Annotate skipped groundedness node so downstream consumers
                # see a deterministic status instead of a missing key.
                if node_name == "groundedness_node":
                    metadata["groundedness_status"] = "skipped"
                    metadata["groundedness_passed"] = True
                continue

            if (
                node_name == "prompt_node"
                and getattr(services, "prompt_manager", None) is None
            ):
                continue

            state = await _run_node(
                node_name=node_name, handler=handler, state=state, services=services
            )

        failed = (state.get("metadata") or {}).get("failed_node")
        if (state.get("error") or not state.get("response")) and failed != "response_node":
            state = await _run_node("response_node", response_node, state, services)
        if state.get("error") and not state.get("response"):
            state[
                "response"
            ] = "An error occurred while processing your request. Please try again."
        metadata = state.setdefault("metadata", {})
        metadata["pipeline_status"] = "error" if state.get("error") else "completed"
        metrics = state.get("metrics", {})
        metadata["node_latency_ms"] = metrics.get("node_latency_ms", {})
        return state

    lf = get_langfuse() if is_enabled() else None
    query_text = state.get("query") or state.get("user_message") or ""
    tenant_id = (state.get("metadata") or {}).get("tenant_id")

    async def _traced_execute() -> WorkflowState:
        if lf is None:
            return await asyncio.wait_for(_execute_pipeline(), timeout=300.0)
        with lf.start_as_current_observation(
            name="workflow.10_node_pipeline",
            input={"query": query_text[:2000]},
            metadata={"tenant_id": tenant_id, "pipeline": "10_node"},
        ) as root:
            try:
                result = await asyncio.wait_for(_execute_pipeline(), timeout=300.0)
                md = result.get("metadata") or {}
                try:
                    root.update(
                        output={
                            "status": md.get("pipeline_status"),
                            "response_preview": (result.get("response") or "")[:500],
                        },
                        metadata={
                            "completed_nodes": md.get("completed_nodes"),
                            "failed_node": md.get("failed_node"),
                            "error_code": md.get("error_code"),
                            "node_latency_ms": md.get("node_latency_ms"),
                            "intent": md.get("intent"),
                        },
                    )
                except Exception:  # pylint: disable=broad-except
                    pass
                return result
            except asyncio.TimeoutError:
                try:
                    root.update(
                        output={"status": "pipeline_timeout"},
                        metadata={"error_code": "PIPELINE_TIMEOUT"},
                        level="ERROR",
                    )
                except Exception:  # pylint: disable=broad-except
                    pass
                raise

    try:
        return await _traced_execute()
    except asyncio.TimeoutError:
        state["error"] = "Request timed out. Please try again."
        state["response"] = "Request timed out. Please try again."
        return state
