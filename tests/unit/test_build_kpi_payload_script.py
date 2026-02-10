from __future__ import annotations

import json

from scripts.testing.build_kpi_payload import main


def test_build_kpi_payload_script_writes_output_file(tmp_path):
    output_path = tmp_path / "kpi_payload.json"

    code = main(
        [
            "--audit-log",
            "tests/evaluation/fixtures/audit_sample.jsonl",
            "--evaluation-json",
            "tests/evaluation/fixtures/ragas_sample_metrics.json",
            "--ab-json",
            "tests/evaluation/fixtures/prompt_ab_sample_metrics.json",
            "--tenant-id",
            "public",
            "--monthly-cost-cad",
            "360",
            "--output",
            str(output_path),
            "--pretty",
        ]
    )

    assert code == 0
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload["faithfulness"] == 0.84
    assert payload["answer_relevancy"] == 0.79
    assert payload["prompt_ab_lift"] == 0.07
    assert payload["monthly_cost_cad"] == 360.0


def test_build_kpi_payload_script_prints_json(capsys):
    code = main(
        [
            "--audit-log",
            "tests/evaluation/fixtures/audit_sample.jsonl",
            "--monthly-cost-cad",
            "88",
        ]
    )
    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert code == 0
    assert payload["baseline_p95_latency_ms"] == 940.0
    assert payload["current_p95_latency_ms"] == 1010.0
    assert payload["monthly_cost_cad"] == 88.0
