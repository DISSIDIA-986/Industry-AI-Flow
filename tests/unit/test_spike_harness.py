"""Unit tests for spike_harness (B.10 in design doc Appendix B).

7 tests, each catches a specific failure mode that would silently corrupt the
spike results. These MUST pass before the spike script is allowed to run.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from backend.services.data_analysis.spike_harness import (
    JsonParseError,
    extract_profile,
    extract_summary_json,
    parse_json_response,
    render_prompt,
)


@pytest.fixture
def sample_profile_slots(tmp_path):
    """A synthetic 3-column profile matching what the spike would emit."""
    import pandas as pd

    df = pd.DataFrame(
        {
            "age": [25, 30, 35, 40, 45],
            "sex": ["F", "M", "F", "M", "F"],
            "salary": [50000, 60000, 75000, 80000, 90000],
        }
    )
    profile = extract_profile(df, filename="sample.csv", total_rows=5)
    return {
        "filename": "sample.csv",
        "n_rows": 5,
        "n_cols": 3,
        "column_profile_table": profile["column_profile_table"],
        "question": "How does salary vary with age?",
    }


@pytest.fixture
def user_template_path(tmp_path):
    """Writable temp copy of the real user template, for isolation."""
    real = Path("scripts/prompts/spike_v1_user_template.md")
    target = tmp_path / "user_template.md"
    target.write_text(real.read_text(encoding="utf-8"), encoding="utf-8")
    return str(target)


# ---------------------------------------------------------------------------
# Prompt rendering (tests 1-3)
# ---------------------------------------------------------------------------


def test_render_prompt_all_slots_filled(user_template_path, sample_profile_slots):
    """Test 1 — no leftover {slot} after rendering."""
    rendered, _, _ = render_prompt(user_template_path, sample_profile_slots)
    # The template should have no single-brace placeholders left.
    # Double-braces `{{` / `}}` inside the JSON example are OK (they escape to single braces).
    # Search for any `{word}` that is NOT part of rendered content.
    import re

    leftovers = re.findall(r"\{[A-Za-z_][A-Za-z0-9_]*\}", rendered)
    assert leftovers == [], f"unfilled slots present: {leftovers}"


def test_render_prompt_stable_hash(user_template_path, sample_profile_slots):
    """Test 2 — same input renders to same SHA256, every time."""
    _, tpl_sha_1, rendered_sha_1 = render_prompt(user_template_path, sample_profile_slots)
    _, tpl_sha_2, rendered_sha_2 = render_prompt(user_template_path, sample_profile_slots)
    assert tpl_sha_1 == tpl_sha_2
    assert rendered_sha_1 == rendered_sha_2


def test_render_prompt_column_table_correct(user_template_path, sample_profile_slots):
    """Test 3 — profile with 3 columns produces 3 lines in the column table."""
    rendered, _, _ = render_prompt(user_template_path, sample_profile_slots)
    # The sample fixture has 3 columns: age, sex, salary.
    for col in ("age", "sex", "salary"):
        assert col in rendered, f"expected column '{col}' in rendered prompt"
    # And the column_profile_table should have 3 non-empty rows.
    rows = [r for r in sample_profile_slots["column_profile_table"].split("\n") if r.strip()]
    assert len(rows) == 3, f"expected 3 column rows, got {len(rows)}"


# ---------------------------------------------------------------------------
# JSON parsing (tests 4-7)
# ---------------------------------------------------------------------------


def test_parse_json_response_plain():
    """Test 4 — raw JSON dict parses directly."""
    raw = '{"status":"ok","business_goal":"test"}'
    out = parse_json_response(raw)
    assert out == {"status": "ok", "business_goal": "test"}


def test_parse_json_response_markdown_wrapped():
    """Test 5 — markdown fences around JSON still extract correctly."""
    raw = '```json\n{"status":"ok","python_code":"import pandas"}\n```'
    out = parse_json_response(raw)
    assert out is not None
    assert out["status"] == "ok"
    assert out["python_code"] == "import pandas"


def test_parse_json_response_with_prose():
    """Test 6 — leading prose before JSON still extracts via regex fallback."""
    raw = 'Here is the analysis plan:\n{"status":"ok","assumptions":["x"]}\nEnd of response.'
    out = parse_json_response(raw)
    assert out is not None
    assert out["status"] == "ok"
    assert out["assumptions"] == ["x"]


def test_parse_json_response_unparseable():
    """Test 7 — completely non-JSON input returns None (caller flags
    json_schema_valid=false and triggers repair)."""
    raw = "This is completely bogus text with no braces at all."
    out = parse_json_response(raw)
    assert out is None


# ---------------------------------------------------------------------------
# Bonus: summary JSON extraction from sandbox stdout
# ---------------------------------------------------------------------------


def test_extract_summary_json_success():
    stdout = 'Some chart logging\nANALYSIS_SUMMARY_JSON={"tip_mean":2.99,"n":244}\nDone.\n'
    emitted, ok, obj = extract_summary_json(stdout)
    assert emitted is True
    assert ok is True
    assert obj == {"tip_mean": 2.99, "n": 244}


def test_extract_summary_json_missing():
    stdout = "No summary here, just some chart output."
    emitted, ok, obj = extract_summary_json(stdout)
    assert emitted is False
    assert ok is False
    assert obj is None


def test_extract_summary_json_malformed():
    stdout = "ANALYSIS_SUMMARY_JSON=this is not json"
    emitted, ok, obj = extract_summary_json(stdout)
    assert emitted is True  # line was emitted
    assert ok is False  # but JSON parse failed
    assert obj is None


def test_extract_summary_json_accepts_python_repr_with_single_quotes():
    """Regression: GLM-4.7 sometimes emits Python str(dict) output with
    single quotes, which json.loads rejects. ast.literal_eval fallback
    recovers the dict safely (no arbitrary code execution).
    Observed live in a titanic ML-comparison request — the AUC dict was
    parsed as None, blanking the Key Findings panel even though the
    data was right there in stdout.
    """
    stdout = (
        "ANALYSIS_SUMMARY_JSON={'model_comparison': "
        "{'LogisticRegression': {'mean_auc': 0.8521, 'std_auc': 0.0218}, "
        "'RandomForest': {'mean_auc': 0.8735, 'std_auc': 0.0236}}}"
    )
    emitted, ok, obj = extract_summary_json(stdout)
    assert emitted is True
    assert ok is True
    assert isinstance(obj, dict)
    mc = obj["model_comparison"]
    assert mc["RandomForest"]["mean_auc"] == 0.8735
    assert mc["LogisticRegression"]["std_auc"] == 0.0218


def test_extract_summary_json_accepts_python_none_true_false():
    """ast.literal_eval also handles None/True/False which json.loads
    rejects (json requires null/true/false)."""
    stdout = "ANALYSIS_SUMMARY_JSON={'flag': True, 'missing': None, 'count': 3}"
    emitted, ok, obj = extract_summary_json(stdout)
    assert emitted is True
    assert ok is True
    assert obj == {"flag": True, "missing": None, "count": 3}
