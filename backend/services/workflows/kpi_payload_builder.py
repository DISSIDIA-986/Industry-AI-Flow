"""Build KPI gate payloads from runtime artifacts."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

from backend.services.workflows.kpi_gate import compute_p95

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class KPIPayloadBuildConfig:
    audit_log_path: str = "logs/audit.log"
    evaluation_json_path: Optional[str] = None
    ab_json_path: Optional[str] = None
    tenant_id: str = "public"
    monthly_cost_cad: Optional[float] = None
    cad_per_usd: float = 1.35


def build_kpi_payload(config: KPIPayloadBuildConfig) -> Dict[str, float | int]:
    audit_events = _load_jsonl(Path(config.audit_log_path))
    evaluation_data = _load_optional_json(config.evaluation_json_path)
    ab_data = _load_optional_json(config.ab_json_path)

    workflow_latencies = _extract_workflow_latencies_ms(
        audit_events,
        tenant_id=config.tenant_id,
    )
    baseline_p95, current_p95 = _split_latency_baseline_current(workflow_latencies)
    sensitive_egress_hits = _extract_sensitive_egress_hits(
        audit_events,
        tenant_id=config.tenant_id,
    )

    faithfulness = _extract_metric(evaluation_data, "faithfulness", default=0.0)
    answer_relevancy = _extract_metric(
        evaluation_data,
        "answer_relevancy",
        default=0.0,
    )
    prompt_ab_lift = _extract_metric(ab_data, "prompt_ab_lift", default=0.0)

    monthly_cost_cad = config.monthly_cost_cad
    if monthly_cost_cad is None:
        monthly_cost_cad = _load_monthly_cost_cad(
            tenant_id=config.tenant_id,
            cad_per_usd=config.cad_per_usd,
        )

    return {
        "faithfulness": round(float(faithfulness), 6),
        "answer_relevancy": round(float(answer_relevancy), 6),
        "prompt_ab_lift": round(float(prompt_ab_lift), 6),
        "baseline_p95_latency_ms": round(float(baseline_p95), 3),
        "current_p95_latency_ms": round(float(current_p95), 3),
        "sensitive_egress_hits": int(sensitive_egress_hits),
        "monthly_cost_cad": round(float(monthly_cost_cad), 6),
    }


def _load_jsonl(path: Path) -> List[dict]:
    if not path.exists():
        return []

    rows: List[dict] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            try:
                item = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(item, dict):
                rows.append(item)
    return rows


def _load_optional_json(path: Optional[str]) -> Dict[str, Any]:
    if not path:
        return {}
    file_path = Path(path)
    if not file_path.exists():
        return {}
    try:
        with file_path.open("r", encoding="utf-8") as handle:
            payload = json.load(handle)
    except Exception as exc:
        logger.warning("Unable to load JSON %s: %s", file_path, exc)
        return {}
    return payload if isinstance(payload, dict) else {}


def _extract_workflow_latencies_ms(
    events: Iterable[dict], tenant_id: str
) -> List[float]:
    values: List[float] = []
    for event in events:
        if event.get("action") != "workflow.query":
            continue
        if str(event.get("tenant_id") or "") != tenant_id:
            continue
        detail = event.get("detail")
        if not isinstance(detail, dict):
            continue
        latency = detail.get("latency_ms")
        if latency is None:
            continue
        try:
            values.append(float(latency))
        except Exception:
            continue
    return values


def _split_latency_baseline_current(latencies_ms: List[float]) -> tuple[float, float]:
    if not latencies_ms:
        return 0.0, 0.0

    if len(latencies_ms) < 4:
        p95 = compute_p95(latencies_ms)
        return p95, p95

    mid = len(latencies_ms) // 2
    baseline = latencies_ms[:mid]
    current = latencies_ms[mid:]
    return compute_p95(baseline), compute_p95(current)


def _extract_sensitive_egress_hits(events: Iterable[dict], tenant_id: str) -> int:
    total = 0
    for event in events:
        if event.get("action") != "llm.dispatch":
            continue
        if str(event.get("tenant_id") or "") != tenant_id:
            continue
        detail = event.get("detail")
        if not isinstance(detail, dict):
            continue
        value = detail.get("sensitive_hit_count")
        if value is None:
            continue
        try:
            total += int(value)
        except Exception:
            continue
    return total


def _extract_metric(payload: Dict[str, Any], key: str, default: float) -> float:
    if key in payload:
        try:
            return float(payload[key])
        except Exception:
            return default

    nested_keys = ("current_metrics", "metrics", "summary", "result")
    for nested_key in nested_keys:
        nested = payload.get(nested_key)
        if isinstance(nested, dict) and key in nested:
            try:
                return float(nested[key])
            except Exception:
                return default
    return default


def _load_monthly_cost_cad(*, tenant_id: str, cad_per_usd: float) -> float:
    try:
        from backend.services.llm_integration.cost_tracker import cost_tracker

        usd = float(cost_tracker.get_monthly_spend(tenant_id))
        return max(0.0, usd * float(cad_per_usd))
    except Exception as exc:
        logger.warning("Unable to load monthly cost from DB: %s", exc)
        return 0.0
