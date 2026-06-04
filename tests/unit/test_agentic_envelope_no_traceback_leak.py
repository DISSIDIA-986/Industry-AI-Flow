"""Regression: the agentic envelope must never leak a raw traceback to the user.

Bug (found 2026-06-04 extreme-coverage sweep, cases 03_two_rows_predict and
09_inf_extremes): when the agentic path exhausted its rounds on a sandbox runtime
error, both the user-facing ``answer`` AND the structured ``code_generation.
fallback_reason`` were set to ``result.error_message`` — which is the raw sandbox
stderr, a full multi-line Python traceback. On the demo this would show evaluators
an ugly traceback instead of a friendly message (CLAUDE.md: no stack traces leaked).

Fix: ``_build_answer`` distills the error to one safe line; ``_fallback_reason``
returns a clean enum (the last repair trigger). The full trace stays in ``stderr``.
"""

from __future__ import annotations

import pytest

from backend.services.data_analysis.agentic_loop import PlanExecutionResult
from backend.services.data_analysis.agentic_envelope import (
    _build_answer,
    _fallback_reason,
    _distill_error,
)

pytestmark = pytest.mark.unit

_TRACEBACK = (
    "---------------------------------------------------------------------------\n"
    "ValueError                                Traceback (most recent call last)\n"
    "Cell In[1], line 60\n"
    "     58 fig, axes = plt.subplots(1, 2, figsize=(12, 5))\n"
    "---> 60 sns.histplot(col_huge, kde=True, ax=axes[0])\n"
    "File /usr/local/lib/python3.13/site-packages/seaborn/distributions.py:1416\n"
    "ValueError: array must not contain infs or NaNs\n"
)


def _failed_result(error_message: str, trigger: str = "sandbox_runtime_error") -> PlanExecutionResult:
    return PlanExecutionResult(
        success=False,
        status="error",
        repair_triggered=True,
        repair_trigger_type=trigger,
        error_message=error_message,
    )


def test_answer_does_not_leak_traceback():
    res = _failed_result(_TRACEBACK)
    answer = _build_answer(res, plan={}, summary={})
    assert "Traceback (most recent call last)" not in answer
    assert "Cell In[" not in answer
    assert "site-packages" not in answer
    assert "\n" not in answer, "answer must be a single user-facing line"
    # The distilled one-line cause is allowed and helpful.
    assert "array must not contain infs or NaNs" in answer


def test_fallback_reason_is_single_safe_line_not_traceback():
    res = _failed_result(_TRACEBACK, trigger="sandbox_runtime_error")
    fr = _fallback_reason(res) or ""
    # distilled to the final exception line — informative but never a traceback
    assert fr == "ValueError: array must not contain infs or NaNs"
    assert "Traceback" not in fr
    assert "\n" not in fr
    assert "Cell In[" not in fr
    # the clean machine enum still lives in repair_trigger_type (set on the result)
    assert res.repair_trigger_type == "sandbox_runtime_error"


def test_fallback_reason_preserves_timeout_and_unanswerable():
    timed_out = PlanExecutionResult(success=False, status="error", time_budget_exhausted=True)
    assert _fallback_reason(timed_out) == "time_budget_exhausted"
    unans = PlanExecutionResult(success=False, status="unanswerable", error_message="no")
    assert _fallback_reason(unans) == "model_declared_unanswerable"


def test_distill_error_picks_final_exception_line():
    assert _distill_error(_TRACEBACK) == "ValueError: array must not contain infs or NaNs"
    assert _distill_error("") == ""
    assert _distill_error(None) == ""
    # No exception line -> last non-empty line, single line, capped.
    multi = "step one\nstep two\nsomething went wrong here"
    assert _distill_error(multi) == "something went wrong here"
    long = "X" * 500
    assert len(_distill_error(long)) <= 200


def test_distill_error_prefers_exception_over_trailing_warning():
    # A warning appended after the real exception must not be picked as the cause.
    text = (
        "Traceback (most recent call last)\n"
        "ValueError: the real cause here\n"
        "DeprecationWarning: some library noise emitted afterwards\n"
    )
    assert _distill_error(text) == "ValueError: the real cause here"
    # When there is ONLY a warning, fall back to it rather than a random line.
    only_warn = "doing work\nUserWarning: heads up about something"
    assert _distill_error(only_warn) == "UserWarning: heads up about something"


def test_two_row_single_class_degrades_gracefully():
    # case 03: 2-row classification -> sklearn "only one class" -> clean message.
    tb = (
        "Traceback (most recent call last)\n"
        "ValueError: This solver needs samples of at least 2 classes in the data, "
        "but the data contains only one class: 'a'\n"
    )
    res = _failed_result(tb)
    answer = _build_answer(res, plan={"produces_chart": True}, summary={})
    assert "Traceback" not in answer
    assert "couldn't complete" in answer.lower()
