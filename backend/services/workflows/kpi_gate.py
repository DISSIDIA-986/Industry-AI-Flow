"""Workflow KPI gate evaluation utilities."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Iterable, List


@dataclass(frozen=True)
class KPIGateThresholds:
    min_faithfulness: float = 0.80
    min_answer_relevancy: float = 0.75
    min_prompt_ab_lift: float = 0.05
    max_p95_latency_increase_ratio: float = 0.10
    max_sensitive_egress_hits: int = 0
    max_monthly_cost_cad: float = 500.0


@dataclass(frozen=True)
class KPIGateInput:
    faithfulness: float
    answer_relevancy: float
    prompt_ab_lift: float
    baseline_p95_latency_ms: float
    current_p95_latency_ms: float
    sensitive_egress_hits: int
    monthly_cost_cad: float


@dataclass(frozen=True)
class KPICheckResult:
    name: str
    passed: bool
    actual: float | int
    expected: str
    message: str


@dataclass
class KPIGateResult:
    passed: bool
    checks: List[KPICheckResult] = field(default_factory=list)

    @property
    def failed_checks(self) -> List[KPICheckResult]:
        return [item for item in self.checks if not item.passed]

    def to_dict(self) -> dict:
        return {
            "passed": self.passed,
            "checks": [asdict(check) for check in self.checks],
            "failed_count": len(self.failed_checks),
        }


def compute_p95(values: Iterable[float | int]) -> float:
    points = sorted(float(value) for value in values)
    if not points:
        return 0.0

    # Inclusive nearest-rank percentile.
    index = int(round(0.95 * (len(points) - 1)))
    index = max(0, min(index, len(points) - 1))
    return points[index]


def evaluate_kpi_gate(
    payload: KPIGateInput,
    thresholds: KPIGateThresholds | None = None,
) -> KPIGateResult:
    rules = thresholds or KPIGateThresholds()

    baseline_latency = max(float(payload.baseline_p95_latency_ms), 0.0)
    current_latency = max(float(payload.current_p95_latency_ms), 0.0)
    if baseline_latency > 0:
        latency_increase_ratio = (current_latency - baseline_latency) / baseline_latency
    else:
        latency_increase_ratio = 0.0 if current_latency == 0 else 1.0

    checks = [
        KPICheckResult(
            name="faithfulness",
            passed=float(payload.faithfulness) >= rules.min_faithfulness,
            actual=float(payload.faithfulness),
            expected=f">= {rules.min_faithfulness:.2f}",
            message="Faithfulness threshold",
        ),
        KPICheckResult(
            name="answer_relevancy",
            passed=float(payload.answer_relevancy) >= rules.min_answer_relevancy,
            actual=float(payload.answer_relevancy),
            expected=f">= {rules.min_answer_relevancy:.2f}",
            message="Answer relevancy threshold",
        ),
        KPICheckResult(
            name="prompt_ab_lift",
            passed=float(payload.prompt_ab_lift) >= rules.min_prompt_ab_lift,
            actual=float(payload.prompt_ab_lift),
            expected=f">= {rules.min_prompt_ab_lift:.2f}",
            message="Prompt A/B quality lift threshold",
        ),
        KPICheckResult(
            name="p95_latency_increase_ratio",
            passed=latency_increase_ratio <= rules.max_p95_latency_increase_ratio,
            actual=round(latency_increase_ratio, 4),
            expected=f"<= {rules.max_p95_latency_increase_ratio:.2f}",
            message="P95 latency increase ratio threshold",
        ),
        KPICheckResult(
            name="sensitive_egress_hits",
            passed=int(payload.sensitive_egress_hits)
            <= rules.max_sensitive_egress_hits,
            actual=int(payload.sensitive_egress_hits),
            expected=f"<= {rules.max_sensitive_egress_hits}",
            message="Sensitive egress must be zero",
        ),
        KPICheckResult(
            name="monthly_cost_cad",
            passed=float(payload.monthly_cost_cad) <= rules.max_monthly_cost_cad,
            actual=round(float(payload.monthly_cost_cad), 4),
            expected=f"<= {rules.max_monthly_cost_cad:.2f}",
            message="Monthly cost threshold",
        ),
    ]

    return KPIGateResult(
        passed=all(item.passed for item in checks),
        checks=checks,
    )


def payload_from_dict(raw: dict) -> KPIGateInput:
    return KPIGateInput(
        faithfulness=float(raw.get("faithfulness", 0.0)),
        answer_relevancy=float(raw.get("answer_relevancy", 0.0)),
        prompt_ab_lift=float(raw.get("prompt_ab_lift", 0.0)),
        baseline_p95_latency_ms=float(raw.get("baseline_p95_latency_ms", 0.0)),
        current_p95_latency_ms=float(raw.get("current_p95_latency_ms", 0.0)),
        sensitive_egress_hits=int(raw.get("sensitive_egress_hits", 0)),
        monthly_cost_cad=float(raw.get("monthly_cost_cad", 0.0)),
    )


def thresholds_from_dict(raw: dict) -> KPIGateThresholds:
    return KPIGateThresholds(
        min_faithfulness=float(raw.get("min_faithfulness", 0.80)),
        min_answer_relevancy=float(raw.get("min_answer_relevancy", 0.75)),
        min_prompt_ab_lift=float(raw.get("min_prompt_ab_lift", 0.05)),
        max_p95_latency_increase_ratio=float(
            raw.get("max_p95_latency_increase_ratio", 0.10)
        ),
        max_sensitive_egress_hits=int(raw.get("max_sensitive_egress_hits", 0)),
        max_monthly_cost_cad=float(raw.get("max_monthly_cost_cad", 500.0)),
    )
