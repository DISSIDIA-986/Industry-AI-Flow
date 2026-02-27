"""Workflow graph entrypoints."""

from __future__ import annotations

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)

from backend.services.workflows.nodes.code_exec_node import code_exec_node
from backend.services.workflows.nodes.cost_estimation_node import cost_estimation_node
from backend.services.workflows.nodes.groundedness_node import groundedness_node
from backend.services.workflows.nodes.intent_node import intent_node
from backend.services.workflows.nodes.prompt_node import prompt_node
from backend.services.workflows.nodes.response_node import response_node
from backend.services.workflows.nodes.retrieval_node import retrieval_node
from backend.services.workflows.nodes.rerank_node import rerank_node
from backend.services.workflows.nodes.route_node import route_node
from backend.services.workflows.nodes.safety_node import safety_node
from backend.services.workflows.state import WorkflowState


async def run_prompt_stage(state: WorkflowState, services: Any) -> WorkflowState:
    """Run the prompt selection/render stage."""
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

    try:
        updated = await handler(state, services)
        node_latency[node_name] = int((time.perf_counter() - started) * 1000)
        if node_name not in completed_nodes:
            completed_nodes.append(node_name)
        return updated
    except Exception as exc:  # pragma: no cover - safety net
        node_latency[node_name] = int((time.perf_counter() - started) * 1000)
        logger.exception("Workflow node '%s' failed: %s", node_name, exc)
        metadata["failed_node"] = node_name
        state["error"] = "I encountered an issue processing your request. Please try again."
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
        ("groundedness_node", groundedness_node),
        ("route_node", route_node),
        ("code_exec_node", code_exec_node),
        ("response_node", response_node),
    ]

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
            continue

        if node_name == "prompt_node" and getattr(services, "prompt_manager", None) is None:
            continue

        state = await _run_node(node_name=node_name, handler=handler, state=state, services=services)

    if not state.get("response"):
        state = await response_node(state, services)
    if state.get("error") and not state.get("response"):
        state["response"] = "An error occurred while processing your request. Please try again."
    return state
