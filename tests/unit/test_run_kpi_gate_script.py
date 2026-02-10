from __future__ import annotations

import json

from scripts.testing.run_kpi_gate import main


def test_run_kpi_gate_script_pass(tmp_path, capsys):
    payload_path = tmp_path / "payload.json"
    payload_path.write_text(
        json.dumps(
            {
                "faithfulness": 0.85,
                "answer_relevancy": 0.80,
                "prompt_ab_lift": 0.06,
                "baseline_p95_latency_ms": 1000,
                "current_p95_latency_ms": 1050,
                "sensitive_egress_hits": 0,
                "monthly_cost_cad": 450,
            }
        ),
        encoding="utf-8",
    )

    code = main(["--input", str(payload_path), "--pretty"])
    captured = capsys.readouterr()
    output = json.loads(captured.out)

    assert code == 0
    assert output["passed"] is True
    assert output["failed_count"] == 0


def test_run_kpi_gate_script_fail(tmp_path, capsys):
    payload_path = tmp_path / "payload.json"
    payload_path.write_text(
        json.dumps(
            {
                "faithfulness": 0.5,
                "answer_relevancy": 0.6,
                "prompt_ab_lift": 0.01,
                "baseline_p95_latency_ms": 1000,
                "current_p95_latency_ms": 1200,
                "sensitive_egress_hits": 1,
                "monthly_cost_cad": 800,
            }
        ),
        encoding="utf-8",
    )

    code = main(["--input", str(payload_path)])
    captured = capsys.readouterr()
    output = json.loads(captured.out)

    assert code == 1
    assert output["passed"] is False
    assert output["failed_count"] >= 1
