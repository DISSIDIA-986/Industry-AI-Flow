from __future__ import annotations

import json

from scripts.testing import run_rollback_rehearsal as rehearsal


def test_rollback_rehearsal_pass(monkeypatch, capsys):
    monkeypatch.setattr(rehearsal.settings, "prompt_experiments_enabled", False)
    monkeypatch.setattr(rehearsal.settings, "code_execution_provider", "docker")

    async def _ok_probe():
        return True, "ok"

    monkeypatch.setattr(rehearsal, "_probe_workflow_fallback", _ok_probe)
    code = rehearsal.main([])
    payload = json.loads(capsys.readouterr().out)

    assert code == 0
    assert payload["passed"] is True
    assert payload["failed_count"] == 0


def test_rollback_rehearsal_fail(monkeypatch, capsys):
    monkeypatch.setattr(rehearsal.settings, "prompt_experiments_enabled", True)
    monkeypatch.setattr(rehearsal.settings, "code_execution_provider", "auto")

    async def _fail_probe():
        return False, "fallback broken"

    monkeypatch.setattr(rehearsal, "_probe_workflow_fallback", _fail_probe)
    code = rehearsal.main([])
    payload = json.loads(capsys.readouterr().out)

    assert code == 1
    assert payload["passed"] is False
    assert payload["failed_count"] == 3


def test_rollback_rehearsal_skip_checks(monkeypatch, capsys):
    monkeypatch.setattr(rehearsal.settings, "prompt_experiments_enabled", True)
    monkeypatch.setattr(rehearsal.settings, "code_execution_provider", "auto")

    code = rehearsal.main(
        [
            "--skip-prompt-check",
            "--skip-provider-check",
            "--skip-fallback-check",
            "--pretty",
        ]
    )
    payload = json.loads(capsys.readouterr().out)

    assert code == 0
    assert payload["passed"] is True
    assert payload["checks"] == []
