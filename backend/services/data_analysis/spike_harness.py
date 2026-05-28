"""
Spike harness for Dynamic Data Analysis GLM-4.7 agentic benchmark.

(Historical note: Plan Appendix E originally called this "GLM-5" as an
internal codename; the actual model was GLM-4.7 throughout. Code,
commit messages, and benchmark filenames containing "glm5" reflect
that codename. Display text / docs say GLM-4.7 to match reality.)

Designed to be reusable: if Stage 2 verdict says "proceed to B", this module
becomes the seed of `agentic_loop.py`. Keep it thin, well-tested, and decoupled
from the 6-node SSE pipeline in data_analysis_agent.py.

Public surface:
    - load_dataframe(path) -> (df, total_rows, role_per_column)
    - extract_profile(df, filename, total_rows) -> ProfileDict
    - render_prompt(template_path, **slots) -> str
    - parse_json_response(text) -> dict | None
    - call_glm(system, user, sampling_config) -> dict (raw GLM-4.7 text parsed)
    - validate_code(code) -> (ok: bool, reason: str | None)
    - run_sandbox(code, csv_files) -> ExecutionResult (async)

The orchestration script in scripts/spike_data_analysis_glm5.py composes these.
"""
from __future__ import annotations

import hashlib
import json
import logging
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd

from backend.services.code_executor.providers.base import ExecutionResult
from backend.services.code_executor.validator import validate_code as _validate_code
from backend.services.data_analysis.data_analysis_agent import DataAnalysisAgent

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data loading + profile extraction
# ---------------------------------------------------------------------------

_PROFILE_COL_ROW_TMPL = (
    "{name} | {dtype} | {role} | {non_null_pct:.1f}% | {n_unique} | {sample_3}"
)


def load_dataframe(path: str) -> pd.DataFrame:
    """Load a CSV/XLSX into a pandas DataFrame.

    Reuses the encoding/sep sniffing already proven in DataAnalysisAgent, but
    returns just the dataframe (total row count is recomputed inside extract_profile).
    """
    agent = DataAnalysisAgent.__new__(DataAnalysisAgent)
    # Bypass __init__ to avoid pulling LLM client etc. We only need the metadata helper.
    info = agent._extract_dataset_info(path)
    if "error" in info:
        raise ValueError(f"load_dataframe failed: {info['error']}")
    # _extract_dataset_info does not return the df itself; re-read it once more
    # for the caller. This is cheap (same file, cached OS page).
    if path.endswith(".csv"):
        # same fallback strategy as the agent
        for enc in ("utf-8", "utf-8-sig", "latin-1"):
            try:
                return pd.read_csv(path, encoding=enc, sep=None, engine="python")
            except UnicodeDecodeError:
                continue
            except pd.errors.ParserError:
                try:
                    return pd.read_csv(path, encoding=enc)
                except UnicodeDecodeError:
                    continue
        raise ValueError(f"Could not decode CSV: {path}")
    if path.endswith((".xlsx", ".xls")):
        return pd.read_excel(path)
    if path.endswith(".json"):
        return pd.read_json(path)
    raise ValueError(f"Unsupported file type: {path}")


def _infer_role(series: pd.Series, name: str) -> str:
    """Infer one of: numeric | categorical | datetime | id | text.

    Datetime detection is intentionally conservative: only strings whose
    parsed dates span multiple years count. This avoids misclassifying
    small integers (ages, counts) as epoch timestamps.
    """
    name_lower = name.lower()
    if name_lower in {"id", "index", "passengerid", "ticket", "row_id"} or name_lower.endswith("_id"):
        return "id"
    if pd.api.types.is_numeric_dtype(series):
        return "numeric"
    if pd.api.types.is_datetime64_any_dtype(series):
        return "datetime"
    # Try parsing as datetime only for object/string columns
    if series.dtype == object:
        try:
            parsed = pd.to_datetime(series.dropna().head(20), errors="raise")
            # Require the parsed range to span > 1 day, else it's likely misparsed
            if len(parsed) > 1 and (parsed.max() - parsed.min()).days >= 1:
                return "datetime"
        except (ValueError, TypeError):
            pass
    n_unique = series.nunique(dropna=True)
    n_total = len(series)
    if n_unique <= 20 or (n_total and n_unique / max(n_total, 1) < 0.1):
        return "categorical"
    return "text"


def _summarize_samples(series: pd.Series, role: str) -> str:
    """Build the `sample_3` slot value for one column.

    Privacy: raw values are only emitted for `categorical` / `datetime`
    columns (where the actual labels carry signal the LLM needs to
    generate correct code — e.g. 'Male'/'Female' vs 'M'/'F'). For
    `numeric` we emit a `min..max` range (more useful than 3 arbitrary
    cells anyway). For `id` / `text` we redact entirely — these are the
    highest-risk PII surfaces (names, emails, free-form notes) and they
    don't help code generation.
    """
    s = series.dropna()
    if s.empty:
        return "<empty>"
    if role in {"id", "text"}:
        return "<redacted>"
    if role == "numeric":
        try:
            lo = s.min()
            hi = s.max()
            return f"range={lo}..{hi}"
        except (TypeError, ValueError):
            return "<numeric>"
    # categorical, datetime — first 3 distinct values are useful signal
    # BUT _infer_role() classifies any low-cardinality column as categorical
    # (n_unique ≤ 20), so short PII columns like 'name' (3 rows, 3 distinct
    # full names) slip through. Guard with a free-form-text heuristic:
    # if a label looks like a sentence (has whitespace) or is long
    # (avg > 25 chars), treat it as PII and redact.
    samples = s.head(3).tolist()
    str_samples = [str(x) for x in samples]
    avg_len = sum(len(x) for x in str_samples) / max(len(str_samples), 1)
    looks_freeform = any(" " in x for x in str_samples) or avg_len > 25
    if looks_freeform:
        return "<redacted:freeform>"
    return ", ".join(repr(x) for x in samples)


def extract_profile(df: pd.DataFrame, filename: str, total_rows: Optional[int] = None) -> Dict[str, Any]:
    """Build the structured profile passed to the LLM. Matches A.1 spec."""
    n_rows = total_rows if total_rows is not None else len(df)
    n_cols = len(df.columns)

    column_rows: List[str] = []
    for col in df.columns:
        series = df[col]
        role = _infer_role(series, col)
        dtype = str(series.dtype)
        non_null_pct = (series.notna().mean() * 100) if len(series) else 0.0
        n_unique = int(series.nunique(dropna=True))
        sample_str = _summarize_samples(series, role)
        column_rows.append(
            _PROFILE_COL_ROW_TMPL.format(
                name=col,
                dtype=dtype,
                role=role,
                non_null_pct=non_null_pct,
                n_unique=n_unique,
                sample_3=sample_str,
            )
        )

    return {
        "filename": filename,
        "n_rows": n_rows,
        "n_cols": n_cols,
        "column_profile_table": "\n".join(column_rows),
    }


# ---------------------------------------------------------------------------
# Prompt rendering + hashing
# ---------------------------------------------------------------------------

_PLACEHOLDER_RE = re.compile(r"\{[A-Za-z_][A-Za-z0-9_]*\}")


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def render_prompt(template_path: str, slots: Dict[str, Any]) -> Tuple[str, str, str]:
    """Render a prompt template. Returns (rendered, template_sha, rendered_sha).

    Uses str.format_map with a SafeDict that raises on missing keys so we never
    ship a prompt with a leftover {slot}. Double-braces in the template
    (e.g. JSON `{{` inside examples) are treated as literals per str.format.
    """
    template_text = Path(template_path).read_text(encoding="utf-8")
    template_sha = _sha256(template_text)

    class _SafeDict(dict):
        def __missing__(self, key: str) -> str:  # type: ignore[override]
            raise KeyError(f"Missing slot in prompt template: {key}")

    rendered = template_text.format_map(_SafeDict(slots))

    # Defense-in-depth: scan for any leftover single-brace placeholders.
    # After str.format, legitimate braces are already stripped/unescaped.
    # If we see a {word} remaining, the template or slot set is wrong.
    leftover = _PLACEHOLDER_RE.findall(rendered)
    if leftover:
        raise ValueError(f"Prompt rendered with leftover placeholders: {leftover}")

    rendered_sha = _sha256(rendered)
    return rendered, template_sha, rendered_sha


# ---------------------------------------------------------------------------
# JSON parsing (two-layer fallback per B.8)
# ---------------------------------------------------------------------------


class JsonParseError(Exception):
    pass


_JSON_BLOCK_RE = re.compile(r"\{[\s\S]*\}")


def parse_json_response(text: str) -> Optional[Dict[str, Any]]:
    """Parse a GLM-4.7 response that should be a JSON object.

    Strategy:
      1. Try json.loads on the stripped text.
      2. If that fails, extract the first {...} block via regex and retry.
      3. If that fails too, return None (caller records json_schema_valid=false).
    """
    if text is None:
        return None
    stripped = text.strip()
    if not stripped:
        return None
    try:
        obj = json.loads(stripped)
        return obj if isinstance(obj, dict) else None
    except json.JSONDecodeError:
        pass
    match = _JSON_BLOCK_RE.search(stripped)
    if not match:
        return None
    try:
        obj = json.loads(match.group(0))
        return obj if isinstance(obj, dict) else None
    except json.JSONDecodeError:
        return None


# ---------------------------------------------------------------------------
# Validator + sandbox wrappers
# ---------------------------------------------------------------------------


@dataclass
class ValidationOutcome:
    ok: bool
    reason: Optional[str] = None


def validate_code(code: str) -> ValidationOutcome:
    """Wrap CodeValidator(strict_mode=True). Returns normalized outcome."""
    result = _validate_code(code, strict_mode=True)
    if result.is_valid:
        return ValidationOutcome(ok=True, reason=None)
    return ValidationOutcome(ok=False, reason=result.error or "validator rejected")


async def run_sandbox(
    code: str,
    csv_files: Dict[str, bytes],
    timeout_s: int = 60,
) -> ExecutionResult:
    """Run `code` in a fresh E2B sandbox with the CSVs pre-uploaded.

    Per B.13, each trial gets a new sandbox — no reuse. The provider's
    Sandbox.create() handles the cold start.
    """
    from backend.config import settings
    from backend.services.code_executor.providers.e2b_provider import E2BExecutionProvider

    provider = E2BExecutionProvider(
        enabled=True,
        api_key=settings.e2b_api_key or None,
        timeout_seconds=settings.e2b_timeout_seconds,
        failure_threshold=settings.e2b_failure_threshold,
        cooldown_seconds=settings.e2b_cooldown_seconds,
    )
    return await provider.execute(code=code, files=csv_files, timeout_s=timeout_s)


# ---------------------------------------------------------------------------
# Summary JSON extraction from sandbox stdout
# ---------------------------------------------------------------------------

_SUMMARY_LINE_RE = re.compile(r"^ANALYSIS_SUMMARY_JSON=(.+)$", re.MULTILINE)


def extract_summary_json(stdout: str) -> Tuple[bool, bool, Optional[Dict[str, Any]]]:
    """Parse the ANALYSIS_SUMMARY_JSON= line out of sandbox stdout.

    Tolerant to two common emission shapes:
      1. Strict JSON (what the prompt asks for via json.dumps)
      2. Python-repr dict with single quotes (what GLM-4.7 emits when it
         does `print('ANALYSIS_SUMMARY_JSON=' + str(result))` by mistake).
    Falling back to ast.literal_eval recovers the dict safely — it only
    accepts literal Python values (dicts, lists, numbers, strings,
    bools, None), so no arbitrary code execution risk.

    Returns (emitted, parse_success, parsed_dict | None).
    """
    import ast

    match = _SUMMARY_LINE_RE.search(stdout or "")
    if not match:
        return False, False, None
    raw = match.group(1).strip()

    # Attempt 1: strict JSON.
    try:
        obj = json.loads(raw)
        if isinstance(obj, dict):
            return True, True, obj
    except json.JSONDecodeError:
        pass

    # Attempt 2: Python literal (handles single-quoted dicts, True/False/None,
    # and numpy scalars stringified as plain numbers). Safe per-docs: does
    # not execute arbitrary code.
    try:
        obj = ast.literal_eval(raw)
        if isinstance(obj, dict):
            return True, True, obj
    except (ValueError, SyntaxError):
        pass

    return True, False, None
