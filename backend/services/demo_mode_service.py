"""Demo mode control-plane for Capstone operation profiles."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from threading import Lock
from typing import Any, Dict, List, Optional

from backend.config import settings
from backend.services.workflows.policies.routing_policy import resolve_route_mode

DEMO_MODE_LIVE_HYBRID = "live_hybrid"
DEMO_MODE_LOCAL_SAFE = "local_safe"
DEMO_MODE_SCRIPTED_REPLAY = "scripted_replay"

ALLOWED_DEMO_MODES = {
    DEMO_MODE_LIVE_HYBRID,
    DEMO_MODE_LOCAL_SAFE,
    DEMO_MODE_SCRIPTED_REPLAY,
}


@dataclass(frozen=True)
class DemoModeProfile:
    mode: str
    label: str
    description: str
    default_route_mode: str
    cloud_allowed: bool
    scripted_replay_enabled: bool


DEMO_MODE_PROFILES: Dict[str, DemoModeProfile] = {
    DEMO_MODE_LIVE_HYBRID: DemoModeProfile(
        mode=DEMO_MODE_LIVE_HYBRID,
        label="Live Hybrid",
        description="Local-first hybrid flow with cloud fallback for quality.",
        default_route_mode="hybrid_auto",
        cloud_allowed=True,
        scripted_replay_enabled=False,
    ),
    DEMO_MODE_LOCAL_SAFE: DemoModeProfile(
        mode=DEMO_MODE_LOCAL_SAFE,
        label="Local Safe",
        description="Force local inference path to guarantee offline fallback.",
        default_route_mode="local_only",
        cloud_allowed=False,
        scripted_replay_enabled=False,
    ),
    DEMO_MODE_SCRIPTED_REPLAY: DemoModeProfile(
        mode=DEMO_MODE_SCRIPTED_REPLAY,
        label="Scripted Replay",
        description="Return curated replay responses for deterministic demo flow.",
        default_route_mode="local_only",
        cloud_allowed=False,
        scripted_replay_enabled=True,
    ),
}


SCRIPTED_REPLAY_SCENARIOS: List[Dict[str, Any]] = [
    {
        "id": "cost_estimation_showcase",
        "keywords": ["cost", "estimate"],
        "intent": "cost_estimation",
        "response": (
            "[Scripted Replay] Estimated project actual cost: CAD 78,540,000. "
            "Predicted overrun: 9.1%. Suggested mitigation: freeze high-volatility "
            "materials early and tighten change-order governance."
        ),
    },
    {
        "id": "hybrid_dispatch_showcase",
        "keywords": ["hybrid", "route"],
        "intent": "knowledge_retrieval",
        "response": (
            "[Scripted Replay] Routing decision: local model attempted first, "
            "confidence under threshold, cloud fallback applied, grounded answer returned."
        ),
    },
    {
        "id": "document_rag_showcase",
        "keywords": ["document", "rag"],
        "intent": "knowledge_retrieval",
        "response": (
            "[Scripted Replay] Retrieved 3 grounded chunks from the uploaded document set "
            "and composed a source-backed summary for construction compliance review."
        ),
    },
]


class DemoModeService:
    """Runtime mutable demo mode service."""

    def __init__(self) -> None:
        self._lock = Lock()
        self._mode = self._normalize_mode(settings.resolved_demo_mode)
        self._allow_cloud_override = bool(settings.demo_allow_cloud_override)

    @staticmethod
    def _normalize_mode(value: str) -> str:
        normalized = (value or "").strip().lower()
        if normalized in ALLOWED_DEMO_MODES:
            return normalized
        return DEMO_MODE_LIVE_HYBRID

    @property
    def mode(self) -> str:
        with self._lock:
            return self._mode

    def get_profile(self, mode: Optional[str] = None) -> DemoModeProfile:
        target = self._normalize_mode(mode or self.mode)
        return DEMO_MODE_PROFILES[target]

    def get_state(self) -> Dict[str, Any]:
        with self._lock:
            profile = self.get_profile(self._mode)
            return {
                "mode": self._mode,
                "allow_cloud_override": self._allow_cloud_override,
                "profile": asdict(profile),
                "available_modes": [
                    asdict(DEMO_MODE_PROFILES[key])
                    for key in sorted(DEMO_MODE_PROFILES.keys())
                ],
                "replay_scenarios": len(SCRIPTED_REPLAY_SCENARIOS),
            }

    def set_mode(self, mode: str) -> Dict[str, Any]:
        with self._lock:
            self._mode = self._normalize_mode(mode)
        return self.get_state()

    def set_cloud_override(self, enabled: bool) -> Dict[str, Any]:
        with self._lock:
            self._allow_cloud_override = bool(enabled)
        return self.get_state()

    def resolve_route_mode(self, requested_mode: Optional[str]) -> str:
        profile = self.get_profile()
        # Local-safe and scripted-replay always pin to local route mode.
        if profile.mode in {DEMO_MODE_LOCAL_SAFE, DEMO_MODE_SCRIPTED_REPLAY}:
            return "local_only"

        if requested_mode:
            return resolve_route_mode(
                requested_mode, default_mode=profile.default_route_mode
            )

        return resolve_route_mode(
            profile.default_route_mode, default_mode="hybrid_auto"
        )

    def cloud_calls_allowed(self) -> bool:
        state = self.get_state()
        profile = state["profile"]
        return bool(profile["cloud_allowed"] or state["allow_cloud_override"])

    def replay_response(self, query: str) -> Optional[Dict[str, Any]]:
        profile = self.get_profile()
        if not profile.scripted_replay_enabled:
            return None

        normalized_query = (query or "").strip().lower()
        if not normalized_query:
            return None

        for scenario in SCRIPTED_REPLAY_SCENARIOS:
            keywords = [
                str(item).lower().strip() for item in scenario.get("keywords", [])
            ]
            if keywords and all(keyword in normalized_query for keyword in keywords):
                return scenario

        # Generic fallback to keep scripted replay resilient in live demo.
        return {
            "id": "generic_fallback",
            "keywords": [],
            "intent": "knowledge_retrieval",
            "response": (
                "[Scripted Replay] This response is served from replay mode to ensure "
                "deterministic Capstone demo continuity under network/API uncertainty."
            ),
        }

    def reset_for_tests(
        self,
        *,
        mode: Optional[str] = None,
        allow_cloud_override: Optional[bool] = None,
    ) -> None:
        with self._lock:
            self._mode = self._normalize_mode(mode or settings.resolved_demo_mode)
            self._allow_cloud_override = (
                bool(allow_cloud_override)
                if allow_cloud_override is not None
                else bool(settings.demo_allow_cloud_override)
            )


_demo_mode_service: Optional[DemoModeService] = None


def get_demo_mode_service() -> DemoModeService:
    global _demo_mode_service
    if _demo_mode_service is None:
        _demo_mode_service = DemoModeService()
    return _demo_mode_service
