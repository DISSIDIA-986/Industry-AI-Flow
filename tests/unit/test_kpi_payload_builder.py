from __future__ import annotations

from backend.services.workflows.kpi_payload_builder import (
    KPIPayloadBuildConfig,
    build_kpi_payload,
)


def test_build_kpi_payload_from_fixtures():
    payload = build_kpi_payload(
        KPIPayloadBuildConfig(
            audit_log_path="tests/evaluation/fixtures/audit_sample.jsonl",
            evaluation_json_path="tests/evaluation/fixtures/ragas_sample_metrics.json",
            ab_json_path="tests/evaluation/fixtures/prompt_ab_sample_metrics.json",
            tenant_id="public",
            monthly_cost_cad=320.0,
        )
    )

    assert payload["faithfulness"] == 0.84
    assert payload["answer_relevancy"] == 0.79
    assert payload["prompt_ab_lift"] == 0.07
    assert payload["baseline_p95_latency_ms"] == 940.0
    assert payload["current_p95_latency_ms"] == 1010.0
    assert payload["sensitive_egress_hits"] == 0
    assert payload["monthly_cost_cad"] == 320.0


def test_build_kpi_payload_uses_defaults_for_missing_sources():
    payload = build_kpi_payload(
        KPIPayloadBuildConfig(
            audit_log_path="tests/evaluation/fixtures/does_not_exist.jsonl",
            evaluation_json_path="tests/evaluation/fixtures/does_not_exist_eval.json",
            ab_json_path="tests/evaluation/fixtures/does_not_exist_ab.json",
            tenant_id="public",
            monthly_cost_cad=100.0,
        )
    )

    assert payload["faithfulness"] == 0.0
    assert payload["answer_relevancy"] == 0.0
    assert payload["prompt_ab_lift"] == 0.0
    assert payload["baseline_p95_latency_ms"] == 0.0
    assert payload["current_p95_latency_ms"] == 0.0
    assert payload["sensitive_egress_hits"] == 0
    assert payload["monthly_cost_cad"] == 100.0
