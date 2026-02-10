"""Shared request/response types for LLM dispatch."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Dict, List, Literal, Optional

RouteMode = Literal["local_only", "hybrid_auto", "cloud_only"]


@dataclass
class DispatchRequest:
    prompt: str
    tenant_id: str
    trace_id: str
    route_mode: RouteMode = "local_only"
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None
    top_p: Optional[float] = None
    local_conf_threshold: Optional[float] = None


@dataclass
class UsageStats:
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0

    def to_dict(self) -> Dict[str, int]:
        return asdict(self)


@dataclass
class CostStats:
    estimated_cost_usd: float = 0.0

    def to_dict(self) -> Dict[str, float]:
        return {"estimated_cost_usd": round(float(self.estimated_cost_usd), 6)}


@dataclass
class DispatchResponse:
    success: bool
    text: str
    provider: str
    model: str
    route_mode: RouteMode
    trace_id: str
    latency_ms: int
    confidence: float = 0.0
    usage: UsageStats = field(default_factory=UsageStats)
    cost: CostStats = field(default_factory=CostStats)
    redaction_applied: bool = False
    sensitive_hit_count: int = 0
    redaction_categories: List[str] = field(default_factory=list)
    policy_decision: str = "allow"
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, object]:
        payload = asdict(self)
        payload["usage"] = self.usage.to_dict()
        payload["cost"] = self.cost.to_dict()
        return payload
