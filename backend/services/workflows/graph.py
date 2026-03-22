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

    try:
        updated = await asyncio.wait_for(
            handler(state, services), timeout=timeout
        )
        node_latency[node_name] = int((time.perf_counter() - started) * 1000)
        if node_name not in completed_nodes:
            completed_nodes.append(node_name)
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
        return state
    except Exception as exc:  # pragma: no cover - safety net
        node_latency[node_name] = int((time.perf_counter() - started) * 1000)
        logger.exception("Workflow node '%s' failed: %s", node_name, exc)
        metadata["failed_node"] = node_name
        metadata["error_code"] = ErrorCode.UNKNOWN_ERROR.value
        state["error"] = (
            "I encountered an issue processing your request. Please try again."
        )
        return state


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

        if state.get("error") or not state.get("response"):
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

    try:
        return await asyncio.wait_for(_execute_pipeline(), timeout=300.0)
    except asyncio.TimeoutError:
        state["error"] = "Request timed out. Please try again."
        state["response"] = "Request timed out. Please try again."
        return state
