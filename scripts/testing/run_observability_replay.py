#!/usr/bin/env python3
"""Replay workflow audit logs and run observability quality gates."""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Dict, Iterable, List, Optional

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.services.workflows.kpi_gate import (
    KPIGateInput,
    KPIGateThresholds,
    compute_p95,
    evaluate_kpi_gate,
    thresholds_from_dict,
)
from backend.services.workflows.kpi_payload_builder import (
    KPIPayloadBuildConfig,
    build_kpi_payload,
)


@dataclass(frozen=True)
class ReplayCheck:
    name: str
    passed: bool
    expected: str
    actual: str
    message: str


@dataclass
class ReplayResult:
    passed: bool
    checks: List[ReplayCheck] = field(default_factory=list)
    summary: Dict[str, float | int] = field(default_factory=dict)
    kpi_payload: Dict[str, float | int] = field(default_factory=dict)

    @property
    def failed_checks(self) -> List[ReplayCheck]:
        return [item for item in self.checks if not item.passed]

    def to_dict(self) -> dict:
        return {
            "passed": self.passed,
            "failed_count": len(self.failed_checks),
            "summary": self.summary,
            "kpi_payload": self.kpi_payload,
            "checks": [asdict(item) for item in self.checks],
        }


def _load_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise ValueError(f"JSON payload must be an object: {path}")
    return data


def _load_jsonl(path: Path) -> List[dict]:
    if not path.exists():
        return []

    rows: List[dict] = []
    with path.open("r", encoding="utf-8") as handle:
        for raw in handle:
            line = raw.strip()
            if not line:
                continue
            try:
                item = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(item, dict):
                rows.append(item)
    return rows


def _filter_tenant_events(events: Iterable[dict], tenant_id: str) -> List[dict]:
    return [item for item in events if str(item.get("tenant_id") or "") == tenant_id]


def _extract_workflow_stats(events: Iterable[dict]) -> Dict[str, float | int]:
    workflow_events = [
        item for item in events if item.get("action") == "workflow.query"
    ]
    total = len(workflow_events)
    errors = sum(1 for item in workflow_events if str(item.get("status")) != "success")
    latencies: List[float] = []
    for event in workflow_events:
        detail = event.get("detail")
        if not isinstance(detail, dict):
            continue
        latency_ms = detail.get("latency_ms")
        if latency_ms is None:
            continue
        try:
            latencies.append(float(latency_ms))
        except Exception:
            continue

    error_rate = (errors / total) if total else 1.0
    p95_latency_ms = compute_p95(latencies) if latencies else 0.0

    return {
        "workflow_total": total,
        "workflow_errors": errors,
        "workflow_error_rate": round(error_rate, 6),
        "workflow_p95_latency_ms": round(float(p95_latency_ms), 3),
    }


def _extract_dispatch_stats(events: Iterable[dict]) -> Dict[str, float | int]:
    dispatch_events = [item for item in events if item.get("action") == "llm.dispatch"]
    sensitive_hits = 0
    for event in dispatch_events:
        detail = event.get("detail")
        if not isinstance(detail, dict):
            continue
        value = detail.get("sensitive_hit_count")
        if value is None:
            continue
        try:
            sensitive_hits += int(value)
        except Exception:
            continue
    return {
        "dispatch_total": len(dispatch_events),
        "dispatch_sensitive_hits": sensitive_hits,
    }


def evaluate_replay(
    *,
    audit_log: str,
    evaluation_json: Optional[str],
    ab_json: Optional[str],
    tenant_id: str,
    monthly_cost_cad: Optional[float],
    cad_per_usd: float,
    min_workflow_events: int,
    max_workflow_error_rate: float,
    max_workflow_p95_ms: float,
    min_dispatch_events: int,
    thresholds_path: Optional[str],
) -> ReplayResult:
    tenant_events = _filter_tenant_events(_load_jsonl(Path(audit_log)), tenant_id)
    workflow_stats = _extract_workflow_stats(tenant_events)
    dispatch_stats = _extract_dispatch_stats(tenant_events)
    summary = {**workflow_stats, **dispatch_stats}

    checks: List[ReplayCheck] = []
    workflow_total = int(summary["workflow_total"])
    workflow_error_rate = float(summary["workflow_error_rate"])
    workflow_p95_latency_ms = float(summary["workflow_p95_latency_ms"])
    dispatch_total = int(summary["dispatch_total"])

    checks.append(
        ReplayCheck(
            name="workflow_events_min_count",
            passed=workflow_total >= min_workflow_events,
            expected=f">= {min_workflow_events}",
            actual=str(workflow_total),
            message="Workflow replay must include enough samples to be representative.",
        )
    )
    checks.append(
        ReplayCheck(
            name="workflow_error_rate",
            passed=workflow_error_rate <= max_workflow_error_rate,
            expected=f"<= {max_workflow_error_rate:.4f}",
            actual=f"{workflow_error_rate:.4f}",
            message="Workflow replay error rate exceeds configured threshold.",
        )
    )
    checks.append(
        ReplayCheck(
            name="workflow_p95_latency_ms",
            passed=workflow_p95_latency_ms <= max_workflow_p95_ms,
            expected=f"<= {max_workflow_p95_ms:.2f}",
            actual=f"{workflow_p95_latency_ms:.2f}",
            message="Workflow replay p95 latency exceeds configured threshold.",
        )
    )
    checks.append(
        ReplayCheck(
            name="dispatch_events_min_count",
            passed=dispatch_total >= min_dispatch_events,
            expected=f">= {min_dispatch_events}",
            actual=str(dispatch_total),
            message="Replay should include llm.dispatch events for egress/safety checks.",
        )
    )

    kpi_payload = build_kpi_payload(
        KPIPayloadBuildConfig(
            audit_log_path=audit_log,
            evaluation_json_path=evaluation_json,
            ab_json_path=ab_json,
            tenant_id=tenant_id,
            monthly_cost_cad=monthly_cost_cad,
            cad_per_usd=cad_per_usd,
        )
    )
    thresholds: Optional[KPIGateThresholds] = None
    if thresholds_path:
        thresholds = thresholds_from_dict(_load_json(Path(thresholds_path)))
    kpi_result = evaluate_kpi_gate(KPIGateInput(**kpi_payload), thresholds=thresholds)

    for check in kpi_result.checks:
        checks.append(
            ReplayCheck(
                name=f"kpi.{check.name}",
                passed=check.passed,
                expected=check.expected,
                actual=str(check.actual),
                message=check.message,
            )
        )

    return ReplayResult(
        passed=all(item.passed for item in checks),
        checks=checks,
        summary=summary,
        kpi_payload=kpi_payload,
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Replay workflow observability logs and evaluate release gates"
    )
    parser.add_argument(
        "--audit-log",
        default="logs/audit.log",
        help="Path to audit JSONL log (default: logs/audit.log)",
    )
    parser.add_argument(
        "--evaluation-json",
        help="Optional path to faithfulness/relevancy metrics JSON",
    )
    parser.add_argument(
        "--ab-json",
        help="Optional path to prompt A/B metrics JSON",
    )
    parser.add_argument(
        "--tenant-id",
        default="public",
        help="Tenant id filter (default: public)",
    )
    parser.add_argument(
        "--monthly-cost-cad",
        type=float,
        help="Optional explicit monthly CAD cost; overrides DB lookup",
    )
    parser.add_argument(
        "--cad-per-usd",
        type=float,
        default=1.35,
        help="CAD conversion rate for DB-derived monthly cost (default: 1.35)",
    )
    parser.add_argument(
        "--min-workflow-events",
        type=int,
        default=5,
        help="Minimum workflow.query event count required (default: 5)",
    )
    parser.add_argument(
        "--max-workflow-error-rate",
        type=float,
        default=0.05,
        help="Maximum allowed workflow error rate [0,1] (default: 0.05)",
    )
    parser.add_argument(
        "--max-workflow-p95-ms",
        type=float,
        default=3000.0,
        help="Maximum allowed workflow p95 latency in ms (default: 3000)",
    )
    parser.add_argument(
        "--min-dispatch-events",
        type=int,
        default=1,
        help="Minimum llm.dispatch event count required (default: 1)",
    )
    parser.add_argument(
        "--thresholds",
        help="Optional path to KPI threshold overrides JSON",
    )
    parser.add_argument(
        "--pretty",
        action="store_true",
        help="Pretty-print JSON output",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    result = evaluate_replay(
        audit_log=args.audit_log,
        evaluation_json=args.evaluation_json,
        ab_json=args.ab_json,
        tenant_id=args.tenant_id,
        monthly_cost_cad=args.monthly_cost_cad,
        cad_per_usd=args.cad_per_usd,
        min_workflow_events=max(0, int(args.min_workflow_events)),
        max_workflow_error_rate=max(0.0, float(args.max_workflow_error_rate)),
        max_workflow_p95_ms=max(0.0, float(args.max_workflow_p95_ms)),
        min_dispatch_events=max(0, int(args.min_dispatch_events)),
        thresholds_path=args.thresholds,
    )

    payload = result.to_dict()
    if args.pretty:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(json.dumps(payload, ensure_ascii=False))
    return 0 if result.passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
