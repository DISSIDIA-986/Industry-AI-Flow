from __future__ import annotations

import json

from scripts.testing import run_observability_replay as replay


def test_observability_replay_pass_with_fixture_data(capsys):
    code = replay.main(
        [
            "--audit-log",
            "tests/evaluation/fixtures/audit_sample.jsonl",
            "--evaluation-json",
            "tests/evaluation/fixtures/ragas_sample_metrics.json",
            "--ab-json",
            "tests/evaluation/fixtures/prompt_ab_sample_metrics.json",
            "--monthly-cost-cad",
            "360",
            "--min-workflow-events",
            "5",
            "--max-workflow-error-rate",
            "0.10",
            "--max-workflow-p95-ms",
            "3000",
            "--min-dispatch-events",
            "2",
        ]
    )
    payload = json.loads(capsys.readouterr().out)

    assert code == 0
    assert payload["passed"] is True
    assert payload["summary"]["workflow_total"] == 8
    assert payload["summary"]["dispatch_total"] == 2


def test_observability_replay_fail_with_sparse_log(tmp_path, capsys):
    log_path = tmp_path / "audit_sparse.jsonl"
    log_path.write_text(
        json.dumps(
            {
                "ts": "2026-02-10T08:00:00Z",
                "action": "workflow.query",
                "tenant_id": "public",
                "status": "error",
                "detail": {"latency_ms": 5200},
            }
        )
        + "\n",
        encoding="utf-8",
    )

    code = replay.main(
        [
            "--audit-log",
            str(log_path),
            "--min-workflow-events",
            "3",
            "--max-workflow-error-rate",
            "0.01",
            "--max-workflow-p95-ms",
            "500",
            "--min-dispatch-events",
            "1",
        ]
    )
    payload = json.loads(capsys.readouterr().out)

    assert code == 1
    assert payload["passed"] is False
    assert payload["failed_count"] > 0
    names = {item["name"] for item in payload["checks"] if not item["passed"]}
    assert "workflow_events_min_count" in names
    assert "workflow_error_rate" in names
