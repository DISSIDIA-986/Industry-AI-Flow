from __future__ import annotations

import json

from scripts.testing import run_schema_migration_rehearsal as rehearsal


def test_schema_migration_rehearsal_default_pass(capsys):
    code = rehearsal.main(["--scenario", "both"])
    payload = json.loads(capsys.readouterr().out)

    assert code == 0
    assert payload["passed"] is True
    assert payload["failed_scenarios"] == 0
    assert len(payload["scenarios"]) == 2


def test_schema_migration_rehearsal_single_scenario_pretty(capsys):
    code = rehearsal.main(["--scenario", "legacy", "--pretty"])
    payload = json.loads(capsys.readouterr().out)

    assert code == 0
    assert payload["passed"] is True
    assert payload["failed_scenarios"] == 0
    assert len(payload["scenarios"]) == 1
    assert payload["scenarios"][0]["scenario"] == "legacy"


def test_schema_migration_rehearsal_can_fail_on_forbidden_token(monkeypatch, capsys):
    monkeypatch.setattr(
        rehearsal,
        "FORBIDDEN_SQL_TOKENS",
        rehearsal.FORBIDDEN_SQL_TOKENS + ("CREATE TABLE IF NOT EXISTS PROMPTS",),
    )

    code = rehearsal.main(["--scenario", "empty"])
    payload = json.loads(capsys.readouterr().out)

    assert code == 1
    assert payload["passed"] is False
    assert payload["failed_scenarios"] == 1
