"""Regression tests: non-finite (inf / overflow) hardening in chart_executor.

Bug (found 2026-06-04 extreme-coverage sweep, case 09_inf_extremes):
  - `pd.to_numeric(...).dropna()` does NOT drop +/-inf (inf is a valid float),
    so matplotlib's `hist()` raised "supplied range of [-inf, inf] is not finite"
    and the histogram chart failed.
  - Summary stats (mean/std) over inf / 1e308 magnitudes produced NaN / inf,
    which `json.dumps` serializes as the literal tokens NaN / Infinity — accepted
    by Python's json.loads but INVALID JSON that breaks a browser JSON.parse.

Fix: `_finite_series()` strips inf before plotting; `_san()` + `allow_nan=False`
guarantee every emitted CHART_*_JSON marker is spec-valid JSON.

These exec the generated snippet locally (Agg backend), redirecting /workspace/
to a temp dir — no sandbox required.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from backend.services.data_analysis.chart_executor import _build_combined_snippet

pytestmark = pytest.mark.unit

_OK = re.compile(r"^CHART_OK_JSON=(.+)$", re.MULTILINE)
_FAILED = re.compile(r"^CHART_FAILED_JSON=(.+)$", re.MULTILINE)


def _chart(idx: int, ctype: str, params: dict) -> dict:
    return {"id": f"chart_{idx:02d}_{ctype}", "type": ctype, "params": params,
            "source_columns": [v for v in params.values() if isinstance(v, str)]}


def _exec_snippet(charts: list[dict], csv_text: str, tmp_path: Path) -> str:
    """Build the combined snippet, redirect /workspace -> tmp_path, exec, return stdout."""
    (tmp_path / "data.csv").write_text(csv_text)
    snippet = _build_combined_snippet(charts, str(tmp_path / "data.csv"))
    snippet = snippet.replace("/workspace/", f"{tmp_path}/")
    import io
    from contextlib import redirect_stdout

    buf = io.StringIO()
    glb: dict = {}
    with redirect_stdout(buf):
        exec(compile(snippet, "<snippet>", "exec"), glb)  # noqa: S102 - trusted, locally built
    return buf.getvalue()


def _assert_strict_json(line_payload: str) -> dict:
    """Parse rejecting NaN/Infinity — proves the marker is spec-valid JSON."""
    def _reject(_):  # parse_constant fires only on NaN/Infinity/-Infinity
        raise AssertionError("emitted summary is not spec-valid JSON (NaN/Infinity present)")

    return json.loads(line_payload, parse_constant=_reject)


def test_histogram_survives_inf_column(tmp_path):
    csv = "huge\ninf\n-inf\n1.5\n2.0\n3.0\n4.0\n5.0\n"
    out = _exec_snippet([_chart(0, "histogram", {"column": "huge"})], csv, tmp_path)
    ok = _OK.search(out)
    assert ok, f"histogram failed on inf column; stdout={out!r}"
    payload = _assert_strict_json(ok.group(1))
    assert payload["status"] == "ok"
    summary = payload["summary"]
    # inf rows dropped -> mean over {1.5..5.0} is finite and ~3.2
    assert summary["mean"] is not None and 1.5 <= summary["mean"] <= 5.0
    assert summary["count"] == 5


def test_summary_with_overflow_magnitudes_stays_valid_json(tmp_path):
    # 1e308 magnitudes: variance overflows to inf; bin width can overflow too.
    # Either outcome is acceptable as long as it degrades gracefully and the
    # emitted marker is ALWAYS spec-valid JSON (never the token Infinity/NaN).
    csv = "huge\n1e308\n-1e308\n1e308\n-1e308\n5.0\n"
    out = _exec_snippet([_chart(0, "histogram", {"column": "huge"})], csv, tmp_path)
    ok, failed = _OK.search(out), _FAILED.search(out)
    assert ok or failed, f"no marker emitted; stdout={out!r}"
    payload = _assert_strict_json((ok or failed).group(1))  # raises if Infinity/NaN leaked
    if ok:
        # std may overflow -> sanitized to JSON null, never the invalid token Infinity
        assert "std" in payload["summary"]
    else:
        # graceful failure carries a clean, JSON-safe error string (no traceback)
        assert "Traceback" not in payload.get("error", "")


def test_scatter_survives_inf(tmp_path):
    csv = "x,y\ninf,1\n2,2\n3,inf\n4,4\n5,5\n"
    out = _exec_snippet([_chart(0, "scatter", {"x": "x", "y": "y"})], csv, tmp_path)
    ok = _OK.search(out)
    assert ok, f"scatter failed on inf; stdout={out!r}"
    _assert_strict_json(ok.group(1))


def test_model_comparison_emitter_guards_non_finite():
    """The model-comparison snippet must sanitize non-finite metrics (R^2 on a
    constant target, overflowed scores) so MODEL_*_JSON is always valid JSON."""
    from backend.services.data_analysis.chart_executor import _build_model_snippet

    mc = {
        "enabled": True,
        "target_column": "y",
        "task": "regression",
        "models": ["RandomForest", "Ridge"],
    }
    snippet = _build_model_snippet(mc, "/tmp/data.csv")
    # The emitter must run values through _san and forbid NaN/Infinity tokens.
    assert "_san(payload)" in snippet
    assert "allow_nan=False" in snippet
    assert "def _san(o):" in snippet


def test_emit_summary_helper_sanitizes_non_finite():
    """The injected agentic emit_summary() must turn inf/nan into JSON null."""
    import io
    from contextlib import redirect_stdout
    from backend.services.data_analysis.agentic_loop import _EMIT_SUMMARY_HELPER

    ns: dict = {}
    exec(compile(_EMIT_SUMMARY_HELPER, "<helper>", "exec"), ns)  # noqa: S102
    buf = io.StringIO()
    with redirect_stdout(buf):
        ns["emit_summary"]({"key_findings": ["x"], "r2": float("inf"),
                            "auc": float("nan"), "n": 5, "nested": {"v": float("-inf")}})
    payload = buf.getvalue().strip().split("ANALYSIS_SUMMARY_JSON=", 1)[1]
    parsed = _assert_strict_json(payload)
    assert parsed["r2"] is None and parsed["auc"] is None
    assert parsed["nested"]["v"] is None
    assert parsed["n"] == 5


def test_all_inf_column_degrades_gracefully(tmp_path):
    # Entirely non-finite -> empty after stripping -> clean CHART_FAILED, not a crash.
    csv = "huge\ninf\n-inf\ninf\n"
    out = _exec_snippet([_chart(0, "histogram", {"column": "huge"})], csv, tmp_path)
    failed = _FAILED.search(out)
    assert failed, f"expected graceful CHART_FAILED for all-inf column; stdout={out!r}"
    payload = _assert_strict_json(failed.group(1))
    assert "finite numeric values" in payload.get("error", "")
