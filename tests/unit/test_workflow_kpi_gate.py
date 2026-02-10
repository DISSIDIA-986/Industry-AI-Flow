from __future__ import annotations

from backend.services.workflows.kpi_gate import (
    KPIGateInput,
    KPIGateThresholds,
    compute_p95,
    evaluate_kpi_gate,
    payload_from_dict,
    thresholds_from_dict,
)


def test_compute_p95_handles_empty():
    assert compute_p95([]) == 0.0


def test_compute_p95_returns_expected_percentile():
    values = [120, 90, 100, 130, 200, 110, 105, 98, 99, 101]
    assert compute_p95(values) == 200.0


def test_kpi_gate_pass():
    payload = KPIGateInput(
        faithfulness=0.82,
        answer_relevancy=0.79,
        prompt_ab_lift=0.08,
        baseline_p95_latency_ms=1000,
        current_p95_latency_ms=1070,
        sensitive_egress_hits=0,
        monthly_cost_cad=320.0,
    )
    result = evaluate_kpi_gate(payload)

    assert result.passed is True
    assert len(result.failed_checks) == 0


def test_kpi_gate_fail_multiple_checks():
    payload = KPIGateInput(
        faithfulness=0.60,
        answer_relevancy=0.70,
        prompt_ab_lift=0.02,
        baseline_p95_latency_ms=1000,
        current_p95_latency_ms=1300,
        sensitive_egress_hits=2,
        monthly_cost_cad=600.0,
    )
    result = evaluate_kpi_gate(payload)

    assert result.passed is False
    failed = {item.name for item in result.failed_checks}
    assert "faithfulness" in failed
    assert "answer_relevancy" in failed
    assert "prompt_ab_lift" in failed
    assert "p95_latency_increase_ratio" in failed
    assert "sensitive_egress_hits" in failed
    assert "monthly_cost_cad" in failed


def test_kpi_gate_payload_and_threshold_parsers():
    payload = payload_from_dict(
        {
            "faithfulness": 0.9,
            "answer_relevancy": 0.8,
            "prompt_ab_lift": 0.1,
            "baseline_p95_latency_ms": 100,
            "current_p95_latency_ms": 105,
            "sensitive_egress_hits": 0,
            "monthly_cost_cad": 100,
        }
    )
    thresholds = thresholds_from_dict(
        {
            "min_faithfulness": 0.85,
            "min_answer_relevancy": 0.78,
            "min_prompt_ab_lift": 0.06,
            "max_p95_latency_increase_ratio": 0.2,
            "max_sensitive_egress_hits": 0,
            "max_monthly_cost_cad": 500,
        }
    )

    assert isinstance(payload, KPIGateInput)
    assert isinstance(thresholds, KPIGateThresholds)
    result = evaluate_kpi_gate(payload, thresholds)
    assert result.passed is True
