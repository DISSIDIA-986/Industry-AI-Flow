"""High-level orchestrator for workflow stages."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from types import SimpleNamespace
from typing import Any, Dict, Optional
from uuid import uuid4

from backend.config import settings
from backend.services.workflows.graph import run_prompt_stage, run_workflow_pipeline
from backend.services.workflows.state import WorkflowState


@dataclass
class WorkflowOrchestrator:
    services: Any = field(default_factory=SimpleNamespace)
    default_route_mode: str = "local_only"

    async def run_prompt(self, state: WorkflowState) -> WorkflowState:
        return await run_prompt_stage(state, self.services)

    async def run(self, state: WorkflowState) -> WorkflowState:
        started = time.perf_counter()
        state.setdefault("metadata", {})
        metrics = state.setdefault("metrics", {})

        if not state.get("route_mode"):
            state["route_mode"] = self.default_route_mode
        state = await run_workflow_pipeline(state, self.services)
        if not state.get("response"):
            state["response"] = self._build_response(state)

        metrics["orchestrator_latency_ms"] = int(
            (time.perf_counter() - started) * 1000
        )
        return state

    @staticmethod
    def _build_response(state: WorkflowState) -> str:
        query = (state.get("query") or "").strip()
        prompt_name = ((state.get("prompt_meta") or {}).get("name")) or "default"
        provider = state.get("provider_used") or "local"
        return f"[{provider}] {query}\n\n[prompt={prompt_name}]"


@dataclass
class DefaultWorkflowRunner:
    orchestrator: WorkflowOrchestrator

    async def run_workflow(
        self,
        query: str,
        session_id: str,
        user_id: Optional[str] = None,
        thread_id: Optional[str] = None,
        route_mode: Optional[str] = None,
    ) -> Dict[str, Any]:
        resolved_route_mode = route_mode or "local_only"
        state: WorkflowState = {
            "trace_id": str(uuid4()),
            "tenant_id": "public",
            "query": query,
            "intent": None,
            "retrieved_context": [],
            "system_prompt": None,
            "prompt_meta": None,
            "route_mode": resolved_route_mode,
            "provider_used": None,
            "response": None,
            "metrics": {},
            "error": None,
            "metadata": {
                "session_id": session_id,
                "user_id": user_id,
                "thread_id": thread_id or session_id,
                "requested_route_mode": resolved_route_mode,
                "tenant_id": "public",
                "workflow_runner": "fallback_orchestrator",
                "prompt_experiments_enabled": bool(
                    settings.prompt_experiments_enabled
                ),
            },
        }
        state = await self.orchestrator.run(state)

        return {
            "success": state.get("error") is None,
            "agent_response": state.get("response"),
            "intent_result": {"intent": state.get("intent")},
            "routing_decision": None,
            "clarification_needed": False,
            "clarification_response": None,
            "messages": [],
            "metrics": state.get("metrics", {}),
            "metadata": state.get("metadata", {}),
            "error": state.get("error"),
        }
