"""W2 unit tests for agentic_loop.py (Plan Appendix E W5, 4 tests).

Each test uses dependency injection via `llm_caller=` to stub GLM-4.7, and
monkeypatches `run_sandbox` to avoid hitting E2B. Real-provider tests
live in env-gated tests/integration/test_agentic_real_provider.py (W5).
"""
from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any, Dict, List

import pandas as pd
import pytest

from backend.services.code_executor.providers.base import ExecutionResult
from backend.services.data_analysis import agentic_loop
from backend.services.data_analysis.agentic_loop import (
    PlanExecutionResult,
    run_agentic_analysis,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def sample_csv(tmp_path: Path) -> Path:
    """Write a minimal valid CSV so load_dataframe + extract_profile work."""
    df = pd.DataFrame({"tip": [1.0, 2.0, 3.0, 4.5], "size": [1, 2, 3, 4]})
    path = tmp_path / "sample.csv"
    df.to_csv(path, index=False)
    return path


def _make_valid_llm_response(code: str = "df = pd.read_csv('/workspace/sample.csv')\nprint(df.head())\nprint('ANALYSIS_SUMMARY_JSON={\"n\": 4}')") -> str:
    return json.dumps(
        {
            "status": "ok",
            "business_goal": "Test goal",
            "analysis_plan": "Load and print head",
            "assumptions": [],
            "python_code": code,
            "produces_chart": False,
        }
    )


def _make_blocked_method_response() -> str:
    """Response that will fail the validator (uses .agg)."""
    return json.dumps(
        {
            "status": "ok",
            "business_goal": "Group by size",
            "analysis_plan": "Aggregate tips",
            "assumptions": [],
            "python_code": "df = pd.read_csv('/workspace/sample.csv')\nr = df.groupby('size').agg({'tip': 'mean'})\nprint(r)",
            "produces_chart": False,
        }
    )


def _make_successful_sandbox_result(stdout: str = 'df head\nANALYSIS_SUMMARY_JSON={"n": 4}\n') -> ExecutionResult:
    return ExecutionResult(
        success=True,
        stdout=stdout,
        stderr="",
        error=None,
        execution_time_s=2.5,
        output_files={},
    )


def _make_failed_sandbox_result(error: str = "NameError: x") -> ExecutionResult:
    return ExecutionResult(
        success=False,
        stdout="",
        stderr=error,
        error=error,
        execution_time_s=1.0,
        output_files={},
    )


# ---------------------------------------------------------------------------
# Tests (Plan E.3 W5: 4 unit tests for agentic_loop)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_round1_success_no_repair(sample_csv, monkeypatch):
    """Test 1: round 1 fully passes → no repair triggered, success=True."""
    calls: List[str] = []

    async def _fake_llm(prompt: str) -> str:
        calls.append(prompt)
        return _make_valid_llm_response()

    async def _fake_sandbox(code, csv_files, timeout_s, bootstrap_packages=None):
        return _make_successful_sandbox_result()

    monkeypatch.setattr(agentic_loop, "run_sandbox", _fake_sandbox)

    result: PlanExecutionResult = await run_agentic_analysis(
        question="How many tips?",
        data_file_path=str(sample_csv),
        llm_caller=_fake_llm,
    )

    assert result.success is True
    assert result.status == "ok"
    assert len(result.rounds) == 1
    assert result.repair_triggered is False
    assert result.repair_recovered is None
    assert result.time_budget_exhausted is False
    assert len(calls) == 1  # LLM called exactly once


@pytest.mark.asyncio
async def test_repair_triggers_on_validator_fail(sample_csv, monkeypatch):
    """Test 2: round 1 uses .agg (validator fails) → round 2 repairs →
    repair_triggered=True, repair_recovered=True."""
    call_count = {"n": 0}

    async def _fake_llm(prompt: str) -> str:
        call_count["n"] += 1
        if call_count["n"] == 1:
            return _make_blocked_method_response()  # uses .agg → validator rejects
        return _make_valid_llm_response()  # repair uses allowed methods

    async def _fake_sandbox(code, csv_files, timeout_s, bootstrap_packages=None):
        return _make_successful_sandbox_result()

    monkeypatch.setattr(agentic_loop, "run_sandbox", _fake_sandbox)

    result = await run_agentic_analysis(
        question="Mean tip by size",
        data_file_path=str(sample_csv),
        llm_caller=_fake_llm,
    )

    assert result.success is True
    assert result.status == "ok"
    assert len(result.rounds) == 2
    assert result.repair_triggered is True
    assert result.repair_trigger_type == "validator_rejection"
    assert result.repair_recovered is True
    assert call_count["n"] == 2  # two LLM calls, one per round


@pytest.mark.asyncio
async def test_time_budget_exhaustion_graceful(sample_csv, monkeypatch):
    """Test 3: total budget tiny → round 1 succeeds within budget → success,
    no repair attempted even if round 1 had a soft issue. Verifies the
    budget-exhaustion return path is a first-class outcome (not an exception)."""

    # Slow LLM (2s) but valid — tiny budget forces repair skip if it failed
    async def _slow_but_ok(prompt: str) -> str:
        await asyncio.sleep(0.05)
        return _make_valid_llm_response()

    async def _fake_sandbox(code, csv_files, timeout_s, bootstrap_packages=None):
        return _make_successful_sandbox_result()

    monkeypatch.setattr(agentic_loop, "run_sandbox", _fake_sandbox)

    # Budget well below REPAIR_DECISION_CUTOFF_S (25s) — round 1 still fits,
    # the test verifies the function returns cleanly without hanging.
    result = await run_agentic_analysis(
        question="Q",
        data_file_path=str(sample_csv),
        llm_caller=_slow_but_ok,
        total_budget_s=5.0,
    )
    assert result.success is True
    assert result.total_elapsed_s < 5.0


@pytest.mark.asyncio
async def test_budget_exhausted_mid_round2(sample_csv, monkeypatch):
    """Test 4: round 1 fails with repair trigger, round 2 has no time left →
    skip repair (elapsed ≥ 25s cutoff)."""

    async def _fake_llm(prompt: str) -> str:
        # Slow first call to push elapsed past the repair cutoff (simulated via monkeypatch)
        return _make_blocked_method_response()

    async def _fake_sandbox(code, csv_files, timeout_s, bootstrap_packages=None):
        return _make_failed_sandbox_result()

    monkeypatch.setattr(agentic_loop, "run_sandbox", _fake_sandbox)
    # Force the repair-decision cutoff to 0 so repair is always skipped
    monkeypatch.setattr(agentic_loop, "REPAIR_DECISION_CUTOFF_S", 0.0)

    result = await run_agentic_analysis(
        question="Q",
        data_file_path=str(sample_csv),
        llm_caller=_fake_llm,
        total_budget_s=10.0,
    )

    assert result.success is False
    assert result.status == "error"
    assert result.repair_triggered is False  # skipped due to cutoff
    assert len(result.rounds) == 1


# ---------------------------------------------------------------------------
# Bonus: unanswerable status should not trigger repair
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_round1_user_prompt_accepts_brace_literals_in_sample_data(
    sample_csv, monkeypatch, tmp_path
):
    """Codex review P2 — a CSV cell like `hello {foo}` must NOT crash
    round 1. Before the fix, `_build_user_prompt` used format_map whose
    leftover-placeholder guard rejected the substituted text. Now the
    builder uses .replace() substitution, symmetric with the repair
    builder, and any literal {word} text in sample values survives
    through to the LLM verbatim.
    """
    import pandas as pd

    csv = tmp_path / "with_braces.csv"
    # First sample value is f-string-looking literal text the model
    # might legitimately see in user-uploaded marketing copy or paths.
    pd.DataFrame(
        {
            "name": ["hello {foo}", "ok {bar}", "fine"],
            "count": [1, 2, 3],
        }
    ).to_csv(csv, index=False)

    async def _fake_llm(prompt: str) -> str:
        assert "{foo}" in prompt, "slot value should round-trip literal braces"
        return _make_valid_llm_response()

    async def _fake_sandbox(code, csv_files, timeout_s, bootstrap_packages=None):
        return _make_successful_sandbox_result()

    monkeypatch.setattr(agentic_loop, "run_sandbox", _fake_sandbox)

    result = await run_agentic_analysis(
        question="Count rows",
        data_file_path=str(csv),
        llm_caller=_fake_llm,
    )
    assert result.success is True


@pytest.mark.asyncio
async def test_malformed_summary_json_is_soft_success_not_failure(
    sample_csv, monkeypatch
):
    """Refinement after v4 gate rerun: if the model EMITTED the
    ANALYSIS_SUMMARY_JSON line but the JSON inside is malformed, treat
    the round as soft success (keep the chart) — don't throw away a
    working output over a JSON parse nit. Only a completely MISSING
    summary line fires repair (see the next test).
    """
    async def _fake_llm(prompt: str) -> str:
        return _make_valid_llm_response()

    async def _fake_sandbox(code, csv_files, timeout_s, bootstrap_packages=None):
        # Emitted BUT the JSON payload is malformed (trailing garbage).
        return ExecutionResult(
            success=True,
            stdout='ANALYSIS_SUMMARY_JSON={"n": 4,,}\n',
            stderr="",
            error=None,
            execution_time_s=0.5,
            output_files={},
        )

    monkeypatch.setattr(agentic_loop, "run_sandbox", _fake_sandbox)

    result = await run_agentic_analysis(
        question="Q",
        data_file_path=str(sample_csv),
        llm_caller=_fake_llm,
    )
    # Soft success — no repair fires, round count stays at 1.
    assert result.success is True
    assert result.repair_triggered is False
    assert len(result.rounds) == 1
    # summary_emitted True, summary_parsed None — both surfaced on the
    # terminal round so callers can telemetry the degradation.
    assert result.rounds[-1].summary_emitted is True
    assert result.rounds[-1].summary_parsed is None


@pytest.mark.asyncio
async def test_completely_missing_summary_triggers_repair(
    sample_csv, monkeypatch
):
    """Codex review P2 — a round that passes validation + sandbox but
    forgot the ANALYSIS_SUMMARY_JSON line entirely must fire repair.
    Different from the malformed case above: "forgot" means the marker
    string isn't even in stdout.
    """
    call_count = {"n": 0}

    async def _fake_llm(prompt: str) -> str:
        call_count["n"] += 1
        if call_count["n"] == 1:
            # Valid code, no summary marker.
            return json.dumps(
                {
                    "status": "ok",
                    "business_goal": "Count",
                    "analysis_plan": "Count rows",
                    "assumptions": [],
                    "python_code": "df = pd.read_csv('/workspace/sample.csv')\nprint(len(df))\n",
                    "produces_chart": False,
                }
            )
        # Round 2: now includes the summary line.
        return _make_valid_llm_response()

    async def _fake_sandbox(code, csv_files, timeout_s, bootstrap_packages=None):
        # First call: no summary marker in stdout.
        # Second call: summary present (matches _make_successful_sandbox_result default).
        # NB: agentic_loop injects the emit_summary() helper (which contains the
        # literal "ANALYSIS_SUMMARY_JSON=' + _payload") into EVERY code block, so
        # we key on the model's own literal marker print ("={") to tell the
        # rounds apart — the injected helper never emits that exact substring.
        if "ANALYSIS_SUMMARY_JSON={" in code:
            return _make_successful_sandbox_result()
        # Round 1 code prints len only, no summary.
        return ExecutionResult(
            success=True,
            stdout="42\n",  # no ANALYSIS_SUMMARY_JSON line
            stderr="",
            error=None,
            execution_time_s=0.5,
            output_files={},
        )

    monkeypatch.setattr(agentic_loop, "run_sandbox", _fake_sandbox)

    result = await run_agentic_analysis(
        question="Count rows",
        data_file_path=str(sample_csv),
        llm_caller=_fake_llm,
    )

    assert call_count["n"] == 2, "round 2 must fire when summary JSON missing"
    assert result.repair_triggered is True
    assert result.repair_trigger_type == "summary_json_parse_error"


def test_load_once_reads_file_exactly_one_time(tmp_path, monkeypatch):
    """Codex review P2 — _load_once must not re-read the file. Counts
    Path.read_bytes calls against a real temp file."""
    import pandas as pd

    from backend.services.data_analysis import agentic_loop as al

    csv = tmp_path / "tiny.csv"
    pd.DataFrame({"a": [1, 2], "b": [3, 4]}).to_csv(csv, index=False)

    read_count = {"n": 0}
    real_read_bytes = Path.read_bytes

    def _counting_read(self):  # type: ignore[no-untyped-def]
        read_count["n"] += 1
        return real_read_bytes(self)

    monkeypatch.setattr(Path, "read_bytes", _counting_read)

    df, raw = al._load_once(str(csv))
    assert read_count["n"] == 1, f"expected 1 read, got {read_count['n']}"
    assert len(df) == 2
    assert isinstance(raw, bytes) and len(raw) > 0


def test_load_once_rejects_oversized_files(tmp_path):
    """Codex review P2 — MAX_DATASET_BYTES guard should raise rather
    than let a 500MB CSV OOM the API worker."""
    from backend.services.data_analysis import agentic_loop as al

    big = tmp_path / "big.csv"
    # Write one byte over the cap via truncate (sparse file, cheap).
    with big.open("wb") as f:
        f.truncate(al.MAX_DATASET_BYTES + 1)

    with pytest.raises(ValueError, match="size cap"):
        al._load_once(str(big))


@pytest.mark.asyncio
async def test_token_usage_flows_into_plan_result_when_caller_populates_slot(
    sample_csv, monkeypatch
):
    """Cost observability (post-Codex-review): the default Zhipu caller
    writes per-call usage into `_last_call_usage`, `_run_one_round` reads
    it into `RoundRecord.llm_tokens_in/out`, and `_finalize` aggregates
    across rounds into `PlanExecutionResult.total_tokens_in/out`. Stub
    the caller to simulate that write so test doesn't need a live API.
    """
    async def _fake_llm(prompt: str) -> str:
        # Simulate what _default_glm5_caller does after client.generate.
        agentic_loop._last_call_usage["input"] = 1500
        agentic_loop._last_call_usage["output"] = 220
        return _make_valid_llm_response()

    async def _fake_sandbox(code, csv_files, timeout_s, bootstrap_packages=None):
        return _make_successful_sandbox_result()

    monkeypatch.setattr(agentic_loop, "run_sandbox", _fake_sandbox)

    result = await run_agentic_analysis(
        question="Q",
        data_file_path=str(sample_csv),
        llm_caller=_fake_llm,
    )

    assert result.success is True
    # Round-level fields populated.
    r1 = result.rounds[0]
    assert r1.llm_tokens_in == 1500
    assert r1.llm_tokens_out == 220
    # Aggregated at plan level (one round, so equal).
    assert result.total_tokens_in == 1500
    assert result.total_tokens_out == 220


@pytest.mark.asyncio
async def test_token_usage_absent_when_caller_does_not_populate_slot(
    sample_csv, monkeypatch
):
    """Injected test callers that don't touch the usage slot leave tokens
    as None — no accidental bleed from prior tests in the module."""
    # Preemptively clear in case some earlier test in this module left residue.
    agentic_loop._last_call_usage["input"] = None
    agentic_loop._last_call_usage["output"] = None

    async def _fake_llm(prompt: str) -> str:
        return _make_valid_llm_response()

    async def _fake_sandbox(code, csv_files, timeout_s, bootstrap_packages=None):
        return _make_successful_sandbox_result()

    monkeypatch.setattr(agentic_loop, "run_sandbox", _fake_sandbox)

    result = await run_agentic_analysis(
        question="Q",
        data_file_path=str(sample_csv),
        llm_caller=_fake_llm,
    )

    assert result.rounds[0].llm_tokens_in is None
    assert result.rounds[0].llm_tokens_out is None
    assert result.total_tokens_in is None
    assert result.total_tokens_out is None


@pytest.mark.asyncio
async def test_bootstrap_packages_constant_includes_statsmodels():
    """Smoke test: BOOTSTRAP_PACKAGES stays in sync with the W1 probe's
    EXTRA_SANDBOX_PACKAGES. Any drift between the two lists breaks the
    W6 remediation contract (probe says missing → loop installs at
    request time). Cheap guard against accidental divergence."""
    from backend.services.code_executor.sandbox_runtime import (
        EXTRA_SANDBOX_PACKAGES,
    )

    assert set(agentic_loop.BOOTSTRAP_PACKAGES) == set(EXTRA_SANDBOX_PACKAGES), (
        f"BOOTSTRAP_PACKAGES {agentic_loop.BOOTSTRAP_PACKAGES} drifted from "
        f"sandbox_runtime.EXTRA_SANDBOX_PACKAGES {EXTRA_SANDBOX_PACKAGES}"
    )


@pytest.mark.asyncio
async def test_repair_prompt_handles_fstring_braces_in_previous_output(
    sample_csv, monkeypatch
):
    """Regression guard for the W6 airline-Q1 bug.

    If round-1 code contains a Python f-string like ``f"Peak: {peak_month}"``,
    that literal {peak_month} ends up inside the ``previous_json`` slot of
    the repair prompt. The old ``render_prompt(format_map)`` path raised
    ``ValueError: Prompt rendered with leftover placeholders: ['{peak_month}']``
    before round 2 could even start, so the case failed with rounds=0.
    Fix: ``_build_repair_prompt`` now substitutes via ``.replace()``,
    which does not scan slot *values* for unfilled placeholders.
    """
    call_count = {"n": 0}

    async def _fake_llm(prompt: str) -> str:
        call_count["n"] += 1
        if call_count["n"] == 1:
            # Valid JSON but the code inside contains an f-string that looks
            # like a template placeholder. Validator will reject it (uses .agg)
            # so repair fires — that's how we exercise _build_repair_prompt.
            return json.dumps(
                {
                    "status": "ok",
                    "business_goal": "Monthly trend",
                    "analysis_plan": "Decompose and print peak",
                    "assumptions": [],
                    "python_code": (
                        "peak_month = 'Jul'\n"
                        "print(f'Peak month: {peak_month}')\n"
                        "df.groupby('size').agg({'tip': 'mean'})\n"
                    ),
                    "produces_chart": False,
                }
            )
        # Round 2: return a clean, validator-passing response.
        return _make_valid_llm_response()

    async def _fake_sandbox(code, csv_files, timeout_s, bootstrap_packages=None):
        return _make_successful_sandbox_result()

    monkeypatch.setattr(agentic_loop, "run_sandbox", _fake_sandbox)

    # This call used to raise ValueError before the fix.
    result = await run_agentic_analysis(
        question="Describe trend",
        data_file_path=str(sample_csv),
        llm_caller=_fake_llm,
    )

    assert call_count["n"] == 2, "repair round should have fired"
    assert result.success is True
    assert result.repair_triggered is True
    assert result.repair_recovered is True
    # Most importantly: no exception — the {peak_month} literal survived
    # the substitution path without being mistaken for an unfilled slot.


@pytest.mark.asyncio
async def test_unanswerable_is_terminal_success_no_repair(sample_csv, monkeypatch):
    """Model claims the question can't be answered → no repair, success=True
    with status='unanswerable'."""
    async def _fake_llm(prompt: str) -> str:
        return json.dumps(
            {
                "status": "unanswerable",
                "business_goal": None,
                "analysis_plan": None,
                "assumptions": [],
                "python_code": None,
                "produces_chart": False,
                "reason": "No numeric columns suitable for this question.",
                "suggestion": "Upload a dataset with numeric fields.",
            }
        )

    async def _fake_sandbox(code, csv_files, timeout_s, bootstrap_packages=None):
        # Should never be called
        raise AssertionError("sandbox should not run for unanswerable")

    monkeypatch.setattr(agentic_loop, "run_sandbox", _fake_sandbox)

    result = await run_agentic_analysis(
        question="impossible question",
        data_file_path=str(sample_csv),
        llm_caller=_fake_llm,
    )

    assert result.success is True
    assert result.status == "unanswerable"
    assert result.repair_triggered is False
    assert len(result.rounds) == 1
    assert result.error_message == "No numeric columns suitable for this question."


# ---------------------------------------------------------------------------
# A3 (emit_summary helper injection) + A2 (best/salvageable-round) — 2026-06-04
# ---------------------------------------------------------------------------


def test_inject_summary_helper_prepends_and_is_callable():
    """A3: helper is prepended and defines emit_summary in the exec namespace."""
    code = "df = pd.read_csv('/workspace/x.csv')\nemit_summary({'key_findings': ['ok']})\n"
    injected = agentic_loop._inject_summary_helper(code)
    assert injected.startswith("import json as _ds_json")
    assert "def emit_summary(" in injected
    assert injected.rstrip().endswith(code.rstrip())
    # The helper itself must be valid Python and define emit_summary.
    ns: Dict[str, Any] = {}
    exec(agentic_loop._EMIT_SUMMARY_HELPER, ns)
    assert callable(ns["emit_summary"])


def test_inject_summary_helper_emits_numpy_safe(capsys):
    """A3: emit_summary serializes NumPy scalars that bare json.dumps rejects."""
    import numpy as np

    ns: Dict[str, Any] = {}
    exec(agentic_loop._EMIT_SUMMARY_HELPER, ns)
    ns["emit_summary"](
        {"key_findings": ["f1"], "p_sig": np.bool_(True), "mean": np.float64(3.14)}
    )
    out = capsys.readouterr().out
    assert out.startswith("ANALYSIS_SUMMARY_JSON=")
    payload = out.split("ANALYSIS_SUMMARY_JSON=", 1)[1].strip()
    obj = json.loads(payload)
    assert obj["p_sig"] is True
    assert abs(obj["mean"] - 3.14) < 1e-9


def test_inject_summary_helper_hoists_future_import():
    """A3: a leading `from __future__` import must stay first after injection."""
    code = "from __future__ import annotations\nimport pandas as pd\nprint(1)\n"
    injected = agentic_loop._inject_summary_helper(code)
    assert injected.startswith("from __future__ import annotations")
    assert "import json as _ds_json" in injected
    # Whole thing still parses.
    import ast

    ast.parse(injected)


def _round(*, validator_pass, sandbox_success, chart, summary_emitted, parsed=True):
    """Build a RoundRecord for _pick_best_round tests."""
    rec = agentic_loop.RoundRecord(round_num=1)
    rec.parsed = {"status": "ok", "python_code": "x=1"} if parsed else None
    rec.json_schema_valid = parsed
    rec.validator_pass = validator_pass
    rec.sandbox_success = sandbox_success
    rec.chart_exists = chart
    rec.chart_bytes = b"PNGDATA" if chart else None
    rec.summary_emitted = summary_emitted
    return rec


def test_pick_best_round_prefers_clean():
    clean = _round(validator_pass=True, sandbox_success=True, chart=True, summary_emitted=True)
    broken = _round(validator_pass=True, sandbox_success=False, chart=True, summary_emitted=False)
    best, quality = agentic_loop._pick_best_round([broken, clean])
    assert quality == "clean"
    assert best is clean


def test_pick_best_round_salvages_clean_chart_missing_summary_as_degraded():
    """A2: a CLEAN sandbox run (no crash) that produced a chart but forgot the
    summary line → degraded salvage."""
    salvage = _round(validator_pass=True, sandbox_success=True, chart=True, summary_emitted=False)
    worse = _round(validator_pass=True, sandbox_success=False, chart=False, summary_emitted=False)
    best, quality = agentic_loop._pick_best_round([salvage, worse])
    assert quality == "degraded"
    assert best is salvage


def test_pick_best_round_does_not_salvage_crashed_chart():
    """A2 honesty guard (Codex final review): a round whose code RAISED is NOT
    upgraded even if a chart file was written before the crash — the chart may
    not reflect the real (failed) computation."""
    crashed = _round(validator_pass=True, sandbox_success=False, chart=True, summary_emitted=False)
    best, quality = agentic_loop._pick_best_round([crashed])
    assert quality == "terminal"


def test_pick_best_round_never_salvages_validator_reject():
    """A2 honesty guard: a security/validator rejection is never upgraded."""
    rejected = _round(validator_pass=False, sandbox_success=True, chart=True, summary_emitted=False)
    best, quality = agentic_loop._pick_best_round([rejected])
    assert quality == "terminal"


@pytest.mark.asyncio
async def test_degraded_success_when_clean_run_omits_summary(sample_csv, monkeypatch):
    """A2 end-to-end (honest contract): the sandbox runs CLEANLY and produces a
    chart, but the model never prints the ANALYSIS_SUMMARY_JSON line. Repair
    also omits it → the loop returns success=True + degraded=True with the
    chart preserved (instead of a hard 'Analysis failed' over a good chart).
    """
    def _make_valid_chart_response() -> str:
        return json.dumps(
            {
                "status": "ok",
                "business_goal": "Classify",
                "analysis_plan": "Train + confusion matrix",
                "assumptions": [],
                "python_code": "df = pd.read_csv('/workspace/sample.csv')\nprint('done')\n",
                "produces_chart": True,
            }
        )

    async def _fake_llm(prompt: str) -> str:
        return _make_valid_chart_response()

    async def _fake_sandbox(code, csv_files, timeout_s, bootstrap_packages=None):
        # Clean run, chart saved, but NO ANALYSIS_SUMMARY_JSON marker printed.
        return ExecutionResult(
            success=True,
            stdout="training done\n",  # no marker line
            stderr="",
            error=None,
            execution_time_s=2.0,
            output_files={"analysis_chart.png": b"\x89PNG_realbytes"},
        )

    monkeypatch.setattr(agentic_loop, "run_sandbox", _fake_sandbox)

    result = await run_agentic_analysis(
        question="Classify species and show a confusion matrix.",
        data_file_path=str(sample_csv),
        llm_caller=_fake_llm,
    )

    assert result.success is True, "chart must be salvaged, not reported as failure"
    assert result.degraded is True
    assert result.degraded_reason
    assert result.final_chart_bytes == b"\x89PNG_realbytes"
    assert result.repair_triggered is True
    assert result.repair_recovered is True


# ---------------------------------------------------------------------------
# A1 (Groq fallback in the default agentic caller) — 2026-06-04
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_default_caller_falls_back_to_groq_on_zhipu_error(monkeypatch):
    """A1: when the Zhipu client errors, the caller transparently retries via
    Groq and records the answering provider."""
    import backend.services.llm_integration.llm_client as llm_mod

    class _Boom:
        def generate(self, *a, **k):
            raise RuntimeError("zhipu 503")

    class _Groq:
        last_usage = {"input_tokens": 11, "output_tokens": 7}

        def generate(self, *a, **k):
            return "groq answer"

    def _fake_factory(backend=None):
        return _Boom() if backend == "zhipu" else _Groq()

    monkeypatch.setattr(llm_mod.LLMClientFactory, "create_client", staticmethod(_fake_factory))
    agentic_loop.reset_cache()

    caller = agentic_loop._default_glm5_caller()
    text = await caller("some prompt")

    assert text == "groq answer"
    assert agentic_loop._last_call_provider["provider"] == "groq"
    assert agentic_loop._last_call_usage["input"] == 11


@pytest.mark.asyncio
async def test_default_caller_raises_when_all_providers_fail(monkeypatch):
    """A1: if both providers fail the caller raises (the round records an LLM
    error and the loop falls through to its failure/ salvage handling)."""
    import backend.services.llm_integration.llm_client as llm_mod

    class _Boom:
        def generate(self, *a, **k):
            raise RuntimeError("down")

    monkeypatch.setattr(
        llm_mod.LLMClientFactory, "create_client", staticmethod(lambda backend=None: _Boom())
    )
    agentic_loop.reset_cache()

    caller = agentic_loop._default_glm5_caller()
    with pytest.raises(RuntimeError, match="all LLM providers failed"):
        await caller("p")


# ---------------------------------------------------------------------------
# A5a (strip reflexive unused blocked imports) — 2026-06-04
# ---------------------------------------------------------------------------


def test_strip_unused_import_os_is_removed():
    code = "import os\nimport pandas as pd\ndf = pd.read_csv('/workspace/x.csv')\nprint(df.head())\n"
    out = agentic_loop._strip_unused_blocked_imports(code)
    assert "import os" not in out
    assert "import pandas as pd" in out


def test_strip_keeps_used_os_import():
    """If os is actually referenced, keep the import so the validator still
    blocks it (no security bypass)."""
    code = "import os\np = os.environ.get('X')\nprint(p)\n"
    out = agentic_loop._strip_unused_blocked_imports(code)
    assert "import os" in out


def test_strip_leaves_allowed_imports_untouched():
    code = "import numpy as np\nimport pandas as pd\nimport json\nprint(1)\n"
    out = agentic_loop._strip_unused_blocked_imports(code)
    assert out == code


# ---------------------------------------------------------------------------
# Conditional bootstrap (latency fix) — 2026-06-04
# ---------------------------------------------------------------------------


def test_needed_bootstrap_only_for_statsmodels():
    assert agentic_loop._needed_bootstrap("import pandas as pd\nfrom sklearn import svm\n") == []
    assert agentic_loop._needed_bootstrap(
        "import statsmodels.api as sm\nm = sm.tsa.ARIMA(y, order=(1,1,1))\n"
    ) == ["statsmodels"]


# ---------------------------------------------------------------------------
# Codex final-review fixes — 2026-06-04
# ---------------------------------------------------------------------------


def test_inject_helper_hoists_future_after_docstring():
    """Future import after a module docstring must still be lifted to the top
    so the injected helper doesn't push it out of first position."""
    import ast

    code = '"""module doc"""\nfrom __future__ import annotations\nimport pandas as pd\nprint(1)\n'
    injected = agentic_loop._inject_summary_helper(code)
    assert injected.startswith("from __future__ import annotations")
    ast.parse(injected)  # must compile


def test_strip_leaves_indented_blocked_import():
    """An indented `import os` is NOT stripped (removing the only statement of
    a block would break indentation); validator handles it instead."""
    code = "if True:\n    import os\n    print(os.getcwd())\n"
    out = agentic_loop._strip_unused_blocked_imports(code)
    assert "import os" in out  # untouched


def test_strip_only_top_level_unused():
    code = "import os\nimport pandas as pd\nprint(pd.__version__)\n"
    out = agentic_loop._strip_unused_blocked_imports(code)
    assert "import os" not in out
    assert "import pandas as pd" in out


@pytest.mark.asyncio
async def test_default_caller_falls_back_to_groq_on_unparseable_zhipu(monkeypatch):
    """A1+ (browser QA 2026-06-04): Zhipu returns non-JSON garbage (the
    single-column edge) → caller falls over to Groq's parseable response and
    does NOT cache the garbage."""
    import backend.services.llm_integration.llm_client as llm_mod

    valid_json = json.dumps({"status": "ok", "python_code": "print(1)", "produces_chart": False})

    class _Garbage:
        last_usage = {"input_tokens": 5, "output_tokens": 2}

        def generate(self, *a, **k):
            return "Sure! Here is the analysis: (no JSON at all)"

    class _Groq:
        last_usage = {"input_tokens": 9, "output_tokens": 4}

        def generate(self, *a, **k):
            return valid_json

    monkeypatch.setattr(
        llm_mod.LLMClientFactory, "create_client",
        staticmethod(lambda backend=None: _Garbage() if backend == "zhipu" else _Groq()),
    )
    agentic_loop.reset_cache()

    caller = agentic_loop._default_glm5_caller()
    text = await caller("p")

    assert text == valid_json
    assert agentic_loop._last_call_provider["provider"] == "groq"
    # Garbage must not have been cached; the parseable Groq response is cached.
    stats = agentic_loop.cache_stats()
    assert stats["stores"] == 1
