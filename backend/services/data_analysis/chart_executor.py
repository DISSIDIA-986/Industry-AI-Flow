"""Deterministic chart executor for EDA plans.

Takes a plan from ``chart_plan.eda_plan_from_metadata`` and materializes it
into PNG files by concatenating per-chart scaffolds into ONE combined
Python snippet, which is then run in a single sandbox execution. This is
the structural fix for the first-run flakiness: we previously spun a new
sandbox per chart (2x Sandbox.create per request with the health-check
bug, even worse with N charts). One execution, N charts.

Design contract (see niuyp-main-design-20260417-183703.md):
- Planner emits raw column names in ``source_columns``; executor is the
  sanitization layer. We use ``repr()`` to interpolate column names as
  Python string literals — that's bulletproof for quotes, backslashes,
  newlines, unicode. No f-string concatenation of raw names into code.
- Partial failures are recoverable: each chart is wrapped in try/except,
  emits ``CHART_OK_JSON={...}`` or ``CHART_FAILED_JSON={...}`` on stdout.
  One failing histogram does not take down the other four charts.
- Column validation happens at runtime inside the sandbox (``if col not in
  df.columns: raise``) rather than pre-flight on the host, because the
  sandbox is the source of truth for what the loaded df actually contains
  (encoding, dtype inference can differ from the metadata pass).
- Output images are saved to ``/workspace/<chart_id>.png`` so the chart_id
  is the stable correlation key across stdout markers, plan entries, and
  the executor's output_files dict.

Returns a dict shaped for ``report_composer.py`` to consume directly —
does not re-download files, does not re-read stdout.
"""

from __future__ import annotations

import json
import logging
import os
import re
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# Per-chart render budget in the combined snippet. Matplotlib + pandas
# warm-up dominates the first chart (~1-2s); subsequent charts are fast.
# Total sandbox timeout is the agent's concern; this constant is only used
# to size the default when the caller doesn't specify one.
DEFAULT_CHART_TIMEOUT_S = 60


_SUPPORTED_CHART_TYPES = {
    "histogram",
    "scatter",
    "heatmap",
    "bar",
    "boxplot",
}


def execute_eda(
    plan: Dict[str, Any],
    data_file_path: str,
    code_execution_manager: Any,
    mode: Optional[str] = None,
    timeout_s: int = DEFAULT_CHART_TIMEOUT_S,
) -> Dict[str, Any]:
    """Render every chart in ``plan`` as a single sandbox execution.

    Args:
        plan: Output from ``chart_plan.eda_plan_from_metadata``.
        data_file_path: Host path to the data file (CSV/XLSX/JSON). The
            sandbox sees it at ``/workspace/<basename>``.
        code_execution_manager: A ``CodeExecutionManager`` instance (from
            ``backend.services.code_executor``). Required — the executor
            does not fall back to the legacy single-provider executor;
            the manager's mode routing is what gives us the e2b bypass.
        mode: Execution mode override. Defaults to
            ``settings.code_execution_provider`` when None.
        timeout_s: Sandbox timeout for the combined snippet.

    Returns:
        {
          "success": bool,                # True if sandbox ran without
                                          # raising; individual charts can
                                          # still be "failed" status
          "charts": [                     # one entry per plan chart
            {
              "id": "chart_00_histogram",
              "type": "histogram",
              "status": "ok" | "failed" | "missing",
              "params": {...},
              "image_filename": "chart_00_histogram.png" | None,
              "summary": {...} | None,
              "error": str | None,
            },
            ...
          ],
          "stdout": str,
          "stderr": str,
          "execution_time": float,
          "output_files": {filename: bytes, ...},
        }
    """
    charts_spec: List[Dict[str, Any]] = (plan.get("eda") or {}).get("charts") or []
    if not charts_spec:
        return {
            "success": True,
            "charts": [],
            "stdout": "",
            "stderr": "",
            "execution_time": 0.0,
            "output_files": {},
            "code": "",
        }

    if code_execution_manager is None:
        return _degraded_result(
            charts_spec,
            error="code execution manager unavailable",
        )

    snippet = _build_combined_snippet(charts_spec, data_file_path)

    from backend.config import settings

    effective_mode = (mode or settings.code_execution_provider or "docker").strip().lower()

    execution = code_execution_manager.execute_code(
        code=snippet,
        data_files=[data_file_path],
        timeout=timeout_s,
        mode=effective_mode,
    )

    stdout = execution.get("stdout", "") or ""
    stderr = execution.get("stderr", "") or ""
    output_files = execution.get("output_files", {}) or {}

    per_chart = _parse_chart_markers(stdout)

    charts: List[Dict[str, Any]] = []
    for spec in charts_spec:
        idx = _extract_chart_idx(spec["id"])
        marker = per_chart.get(idx)
        if marker is None:
            # Sandbox crashed before this chart ran, or stdout was truncated.
            charts.append(
                {
                    "id": spec["id"],
                    "type": spec["type"],
                    "status": "missing",
                    "params": spec.get("params", {}),
                    "image_filename": None,
                    "summary": None,
                    "error": (
                        execution.get("error")
                        or stderr.strip()
                        or "chart did not emit a completion marker"
                    ),
                }
            )
            continue

        status = marker.get("status", "failed")
        image_filename = marker.get("image_filename")
        # Only claim an image if it actually exists in output_files. Belt
        # and suspenders: the sandbox might savefig-succeed but the
        # download pass could miss it, in which case the frontend would
        # render a broken <img>.
        if image_filename and image_filename not in output_files:
            status = "failed"
            error = (
                marker.get("error")
                or f"image '{image_filename}' was not downloaded from sandbox"
            )
            image_filename = None
        else:
            error = marker.get("error")

        charts.append(
            {
                "id": spec["id"],
                "type": spec["type"],
                "status": status,
                "params": spec.get("params", {}),
                "image_filename": image_filename,
                "summary": marker.get("summary"),
                "error": error,
            }
        )

    return {
        "success": bool(execution.get("success")),
        "charts": charts,
        "stdout": stdout,
        "stderr": stderr,
        "execution_time": float(execution.get("execution_time") or 0.0),
        "output_files": output_files,
        # Expose the assembled snippet so the agent can thread it into the
        # response's legacy `code` field without re-building it.
        "code": snippet,
    }


# ---------------------------------------------------------------------------
# snippet assembly
# ---------------------------------------------------------------------------


def _build_combined_snippet(
    charts_spec: List[Dict[str, Any]], data_file_path: str
) -> str:
    """Concatenate chart scaffolds into one Python script.

    Layout:
      - header: imports, df load, _emit helper
      - per-chart blocks (try/except around _render_<type>)
      - no footer: each chart self-reports via stdout markers
    """
    basename = os.path.basename(data_file_path)
    ext = basename.rsplit(".", 1)[-1].lower() if "." in basename else ""
    # Same escaping contract as column names: interpolate the sandbox path
    # via repr() so filenames with quotes / backslashes / newlines produce
    # valid Python. Dataset upload naming (e.g., "customer's-data.csv")
    # would otherwise break snippet compilation before any chart runs.
    sandbox_path = f"/workspace/{basename}"

    lines: List[str] = [
        "# Auto-generated EDA snippet (chart_executor.py)",
        "import json as _json",
        # No `import traceback` — CodeValidator strict-mode whitelist
        # rejects it. We surface the exception message only; sandbox
        # stderr still carries the full traceback for post-mortem debug.
        "import pandas as _pd",
        "import numpy as _np",
        "import matplotlib",
        "matplotlib.use('Agg')",
        "import matplotlib.pyplot as plt",
        "",
        f"_DATA_PATH = {sandbox_path!r}",
        _loader_block(ext),
        "",
        "def _emit(status, idx, chart_type, **extra):",
        "    marker = 'CHART_OK_JSON' if status == 'ok' else 'CHART_FAILED_JSON'",
        "    payload = {'idx': idx, 'type': chart_type, 'status': status}",
        "    payload.update(extra)",
        "    print(f'{marker}=' + _json.dumps(payload, default=str))",
        "",
        "def _require_columns(df, cols):",
        "    missing = [c for c in cols if c not in df.columns]",
        "    if missing:",
        "        raise ValueError(f'columns not in dataset: {missing}')",
        "",
    ]

    for spec in charts_spec:
        idx = _extract_chart_idx(spec["id"])
        chart_type = spec["type"]
        if chart_type not in _SUPPORTED_CHART_TYPES:
            lines.extend(_unsupported_block(idx, chart_type))
            continue
        lines.extend(_chart_block(idx, spec))

    return "\n".join(lines) + "\n"


def _loader_block(ext: str) -> str:
    if ext == "csv":
        # Pandas-only delimiter sniff: try each candidate sep with nrows=0
        # to read just the header, pick first sep yielding >1 column, fall
        # back to default comma. open() is BLOCKED by the validator (strict
        # mode), so we can't use a file-read helper here. This mirrors the
        # agentic prompt's pattern so deterministic + agentic produce
        # column-shape-compatible output. Falls back to comma for
        # single-column files (sep=None+engine='python' would corrupt
        # those — splits 'value\n0.24' into ['Unnamed: 0', 'alue']).
        return (
            "_df = None\n"
            "for _try_sep in (',', ';', '\\t', '|'):\n"
            "    try:\n"
            "        _hdr = _pd.read_csv(_DATA_PATH, sep=_try_sep, nrows=0)\n"
            "        if len(_hdr.columns) > 1:\n"
            "            _df = _pd.read_csv(_DATA_PATH, sep=_try_sep)\n"
            "            break\n"
            "    except Exception:\n"
            "        continue\n"
            "if _df is None:\n"
            "    try:\n"
            "        _df = _pd.read_csv(_DATA_PATH)\n"
            "    except UnicodeDecodeError:\n"
            "        _df = _pd.read_csv(_DATA_PATH, encoding='latin-1')\n"
        )
    if ext in {"xlsx", "xls"}:
        return "_df = _pd.read_excel(_DATA_PATH)\n"
    if ext == "json":
        return "_df = _pd.read_json(_DATA_PATH)\n"
    # Default: try CSV with same smart sniff.
    return (
        "_df = None\n"
        "for _try_sep in (',', ';', '\\t', '|'):\n"
        "    try:\n"
        "        _hdr = _pd.read_csv(_DATA_PATH, sep=_try_sep, nrows=0)\n"
        "        if len(_hdr.columns) > 1:\n"
        "            _df = _pd.read_csv(_DATA_PATH, sep=_try_sep)\n"
        "            break\n"
        "    except Exception:\n"
        "        continue\n"
        "if _df is None:\n"
        "    _df = _pd.read_csv(_DATA_PATH)\n"
    )


def _chart_block(idx: int, spec: Dict[str, Any]) -> List[str]:
    chart_type = spec["type"]
    chart_id = spec["id"]
    params = spec.get("params", {})
    image_filename = f"{chart_id}.png"

    body = _render_body(chart_type, idx, params, image_filename)

    return [
        f"# --- chart {idx:02d} {chart_type} ---",
        "try:",
        *[f"    {line}" for line in body],
        "    plt.close('all')",
        f"    _emit('ok', {idx}, {chart_type!r}, image_filename={image_filename!r}, summary=_summary)",
        "except Exception as _exc:",
        "    plt.close('all')",
        f"    _emit('failed', {idx}, {chart_type!r}, error=f'{{type(_exc).__name__}}: {{_exc}}')",
        "",
    ]


def _unsupported_block(idx: int, chart_type: str) -> List[str]:
    return [
        f"# --- chart {idx:02d} {chart_type} (unsupported) ---",
        f"_emit('failed', {idx}, {chart_type!r}, error='unsupported chart type')",
        "",
    ]


# ---------------------------------------------------------------------------
# per-type render bodies — return a list of source lines (no indent prefix;
# _chart_block indents them). Each body MUST assign ``_summary`` and call
# ``fig.savefig(f"/workspace/{image_filename}")``.
# ---------------------------------------------------------------------------


def _render_body(
    chart_type: str, idx: int, params: Dict[str, Any], image_filename: str
) -> List[str]:
    if chart_type == "histogram":
        return _render_histogram(params, image_filename)
    if chart_type == "scatter":
        return _render_scatter(params, image_filename)
    if chart_type == "heatmap":
        return _render_heatmap(params, image_filename)
    if chart_type == "bar":
        return _render_bar(params, image_filename)
    if chart_type == "boxplot":
        return _render_boxplot(params, image_filename)
    raise ValueError(f"unsupported chart type: {chart_type}")


def _render_histogram(params: Dict[str, Any], image_filename: str) -> List[str]:
    col = params["column"]
    return [
        f"_col = {col!r}",
        "_require_columns(_df, [_col])",
        "_series = _pd.to_numeric(_df[_col], errors='coerce').dropna()",
        "if _series.empty:",
        "    raise ValueError(f'column {_col!r} has no numeric values')",
        "_fig, _ax = plt.subplots(figsize=(8, 5))",
        "_ax.hist(_series, bins=20, color='#3b82f6', edgecolor='white')",
        "_ax.set_title(f'Distribution of {_col}')",
        "_ax.set_xlabel(_col)",
        "_ax.set_ylabel('Frequency')",
        "_fig.tight_layout()",
        f"_fig.savefig('/workspace/{image_filename}', dpi=100)",
        "_summary = {",
        "    'column': _col,",
        "    'count': int(_series.shape[0]),",
        "    'mean': float(_series.mean()),",
        "    'median': float(_series.median()),",
        "    'std': float(_series.std()),",
        "}",
    ]


def _render_scatter(params: Dict[str, Any], image_filename: str) -> List[str]:
    x = params["x"]
    y = params["y"]
    return [
        f"_x_col = {x!r}",
        f"_y_col = {y!r}",
        "_require_columns(_df, [_x_col, _y_col])",
        "_x = _pd.to_numeric(_df[_x_col], errors='coerce')",
        "_y = _pd.to_numeric(_df[_y_col], errors='coerce')",
        "_valid = _x.notna() & _y.notna()",
        "_x = _x[_valid]; _y = _y[_valid]",
        "if _x.empty:",
        "    raise ValueError('no overlapping numeric values between x and y')",
        "_fig, _ax = plt.subplots(figsize=(8, 5))",
        "_ax.scatter(_x, _y, alpha=0.6, s=20, color='#3b82f6')",
        "_ax.set_xlabel(_x_col); _ax.set_ylabel(_y_col)",
        "_ax.set_title(f'{_y_col} vs {_x_col}')",
        "_fig.tight_layout()",
        f"_fig.savefig('/workspace/{image_filename}', dpi=100)",
        "try:",
        "    _rho = float(_x.corr(_y))",
        "except Exception:",
        "    _rho = None",
        "_summary = {",
        "    'x': _x_col, 'y': _y_col,",
        "    'n': int(_x.shape[0]),",
        "    'pearson_r': _rho,",
        "}",
    ]


def _render_heatmap(params: Dict[str, Any], image_filename: str) -> List[str]:
    cols = params.get("columns") or []
    return [
        f"_cols = {list(cols)!r}",
        "_require_columns(_df, _cols)",
        # NOTE: build the numeric frame via dict comprehension, NOT
        # DataFrame.apply(). CodeValidator.BLOCKED_METHOD_NAMES rejects
        # .apply() because it runs arbitrary callables per element.
        "_num = _pd.DataFrame({_c: _pd.to_numeric(_df[_c], errors='coerce') for _c in _cols})",
        "_corr = _num.corr(method='pearson').fillna(0.0)",
        "if _corr.empty:",
        "    raise ValueError('correlation matrix is empty')",
        "_fig, _ax = plt.subplots(figsize=(max(6, len(_cols) * 0.6), max(5, len(_cols) * 0.6)))",
        "_im = _ax.imshow(_corr.values, cmap='RdBu_r', vmin=-1, vmax=1)",
        "_ax.set_xticks(range(len(_cols))); _ax.set_yticks(range(len(_cols)))",
        "_ax.set_xticklabels(_cols, rotation=45, ha='right'); _ax.set_yticklabels(_cols)",
        "for _i in range(len(_cols)):",
        "    for _j in range(len(_cols)):",
        "        _ax.text(_j, _i, f'{_corr.iloc[_i, _j]:.2f}', ha='center', va='center', fontsize=8, color='black')",
        "_ax.set_title('Correlation heatmap (Pearson)')",
        "_fig.colorbar(_im, ax=_ax, fraction=0.046, pad=0.04)",
        "_fig.tight_layout()",
        f"_fig.savefig('/workspace/{image_filename}', dpi=100)",
        "_summary = {",
        "    'columns': _cols,",
        "    'n_columns': len(_cols),",
        "}",
    ]


def _render_bar(params: Dict[str, Any], image_filename: str) -> List[str]:
    col = params["column"]
    return [
        f"_col = {col!r}",
        "_require_columns(_df, [_col])",
        "_counts = _df[_col].dropna().astype(str).value_counts().head(20)",
        "if _counts.empty:",
        "    raise ValueError(f'column {_col!r} has no non-null values')",
        "_fig, _ax = plt.subplots(figsize=(8, 5))",
        "_ax.bar(_counts.index.astype(str), _counts.values, color='#3b82f6')",
        "_ax.set_title(f'Counts by {_col}')",
        "_ax.set_xlabel(_col); _ax.set_ylabel('Count')",
        "for _label in _ax.get_xticklabels():",
        "    _label.set_rotation(45); _label.set_horizontalalignment('right')",
        "_fig.tight_layout()",
        f"_fig.savefig('/workspace/{image_filename}', dpi=100)",
        "_summary = {",
        "    'column': _col,",
        "    'categories': [str(_k) for _k in _counts.index.tolist()],",
        "    'counts': [int(_v) for _v in _counts.values.tolist()],",
        "}",
    ]


def _render_boxplot(params: Dict[str, Any], image_filename: str) -> List[str]:
    col = params["column"]
    by = params["by"]
    return [
        f"_col = {col!r}",
        f"_by = {by!r}",
        "_require_columns(_df, [_col, _by])",
        "_plot = _df[[_col, _by]].copy()",
        "_plot[_col] = _pd.to_numeric(_plot[_col], errors='coerce')",
        "_plot = _plot.dropna(subset=[_col, _by])",
        "if _plot.empty:",
        "    raise ValueError('no overlapping values for boxplot')",
        "_groups = [g[_col].values for _name, g in _plot.groupby(_by)]",
        "_labels = [str(_name) for _name, _g in _plot.groupby(_by)]",
        "if not _groups:",
        "    raise ValueError('no groups to plot')",
        "_fig, _ax = plt.subplots(figsize=(max(6, len(_groups) * 0.8), 5))",
        "_ax.boxplot(_groups, labels=_labels, showfliers=True)",
        "_ax.set_title(f'{_col} by {_by}')",
        "_ax.set_xlabel(_by); _ax.set_ylabel(_col)",
        "for _label in _ax.get_xticklabels():",
        "    _label.set_rotation(45); _label.set_horizontalalignment('right')",
        "_fig.tight_layout()",
        f"_fig.savefig('/workspace/{image_filename}', dpi=100)",
        "_summary = {",
        "    'column': _col,",
        "    'by': _by,",
        "    'n_groups': len(_groups),",
        "    'group_labels': _labels,",
        "}",
    ]


# ---------------------------------------------------------------------------
# stdout marker parsing
# ---------------------------------------------------------------------------


_MARKER_RE = re.compile(
    r"^(CHART_OK_JSON|CHART_FAILED_JSON)=(\{.*\})\s*$",
    re.MULTILINE,
)


def _parse_chart_markers(stdout: str) -> Dict[int, Dict[str, Any]]:
    out: Dict[int, Dict[str, Any]] = {}
    if not stdout:
        return out
    for match in _MARKER_RE.finditer(stdout):
        try:
            payload = json.loads(match.group(2))
        except json.JSONDecodeError:
            continue
        idx = payload.get("idx")
        if not isinstance(idx, int):
            continue
        # Last marker wins if a chart somehow emitted twice (shouldn't,
        # but try/except on re-emission would be silent).
        out[idx] = payload
    return out


def _extract_chart_idx(chart_id: str) -> int:
    # chart_id format: "chart_{idx:02d}_{type}"
    match = re.match(r"^chart_(\d+)_", chart_id or "")
    if not match:
        raise ValueError(f"malformed chart id: {chart_id!r}")
    return int(match.group(1))


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------


def _degraded_result(
    charts_spec: List[Dict[str, Any]], error: str
) -> Dict[str, Any]:
    charts = [
        {
            "id": spec["id"],
            "type": spec["type"],
            "status": "failed",
            "params": spec.get("params", {}),
            "image_filename": None,
            "summary": None,
            "error": error,
        }
        for spec in charts_spec
    ]
    return {
        "success": False,
        "charts": charts,
        "stdout": "",
        "stderr": error,
        "execution_time": 0.0,
        "output_files": {},
        "code": "",
    }


# ===========================================================================
# Model comparison (stretch)
# ===========================================================================

_MODEL_IMAGE_FILENAME = "model_comparison.png"

_MODEL_MARKER_RE = re.compile(
    r"^(MODEL_OK_JSON|MODEL_FAILED_JSON)=(\{.*\})\s*$",
    re.MULTILINE,
)


def execute_model_comparison(
    plan: Dict[str, Any],
    data_file_path: str,
    code_execution_manager: Any,
    mode: Optional[str] = None,
    timeout_s: int = 18,
) -> Dict[str, Any]:
    """Run the stretch-goal model comparison stage.

    Trains two models side-by-side (from ``plan.model_comparison.models``)
    on the uploaded dataset in a single E2B sandbox, renders a comparison
    visualization (confusion matrices for classification, predicted-vs-
    actual scatters for regression), and returns a metrics table.

    Reads the same dataset the EDA stage reads. Runs in its own sandbox
    invocation (separate from ``execute_eda``) so the 12s model budget
    is isolated from the EDA budget.

    Returns:
        {
          "success": bool,
          "enabled": bool,          # False if plan had it gated off
          "reason": str,            # why it ran or didn't
          "target_column": str | None,
          "task": "classification" | "regression" | None,
          "metrics": {model_name: {metric: value, ...}, ...},
          "image_filename": str | None,
          "output_files": dict,     # for report_composer persistence
          "stdout": str,
          "stderr": str,
          "execution_time": float,
          "code": str,
        }
    """
    mc = plan.get("model_comparison") or {}
    if not mc.get("enabled"):
        return {
            "success": False,
            "enabled": False,
            "reason": mc.get("reason") or "model comparison disabled",
            "target_column": None,
            "task": None,
            "metrics": {},
            "image_filename": None,
            "output_files": {},
            "stdout": "",
            "stderr": "",
            "execution_time": 0.0,
            "code": "",
        }

    if code_execution_manager is None:
        return {
            "success": False,
            "enabled": True,
            "reason": "code execution manager unavailable",
            "target_column": mc.get("target_column"),
            "task": mc.get("task"),
            "metrics": {},
            "image_filename": None,
            "output_files": {},
            "stdout": "",
            "stderr": "code execution manager unavailable",
            "execution_time": 0.0,
            "code": "",
        }

    snippet = _build_model_snippet(mc, data_file_path)

    from backend.config import settings

    effective_mode = (
        mode or settings.code_execution_provider or "docker"
    ).strip().lower()

    execution = code_execution_manager.execute_code(
        code=snippet,
        data_files=[data_file_path],
        timeout=timeout_s,
        mode=effective_mode,
    )

    stdout = execution.get("stdout", "") or ""
    stderr = execution.get("stderr", "") or ""
    output_files = execution.get("output_files", {}) or {}
    marker = _parse_model_marker(stdout)

    # Image only counts if it actually came back from the sandbox.
    image_filename = None
    if marker and marker.get("status") == "ok":
        emitted = marker.get("image_filename")
        if emitted and emitted in output_files:
            image_filename = emitted

    success = bool(
        execution.get("success")
        and marker
        and marker.get("status") == "ok"
        and image_filename
    )

    if success:
        reason = (
            f"trained {len(marker.get('metrics') or {})} model(s) "
            f"on target={mc.get('target_column')!r}, "
            f"task={mc.get('task')}"
        )
    else:
        reason = (
            (marker or {}).get("error")
            or stderr.strip().splitlines()[-1] if stderr.strip()
            else "model comparison failed — no completion marker"
        )

    return {
        "success": success,
        "enabled": True,
        "reason": reason,
        "target_column": mc.get("target_column"),
        "task": mc.get("task"),
        "metrics": (marker or {}).get("metrics") or {},
        "image_filename": image_filename,
        "output_files": output_files,
        "stdout": stdout,
        "stderr": stderr,
        "execution_time": float(execution.get("execution_time") or 0.0),
        "code": snippet,
    }


def _parse_model_marker(stdout: str) -> Optional[Dict[str, Any]]:
    """Return the last MODEL_*_JSON marker from stdout, or None.

    Last marker wins so a retry inside the snippet can override an
    earlier failure without cluttering the output.
    """
    if not stdout:
        return None
    last: Optional[Dict[str, Any]] = None
    for match in _MODEL_MARKER_RE.finditer(stdout):
        try:
            payload = json.loads(match.group(2))
        except json.JSONDecodeError:
            continue
        status = "ok" if match.group(1) == "MODEL_OK_JSON" else "failed"
        payload["status"] = status
        last = payload
    return last


def _build_model_snippet(mc: Dict[str, Any], data_file_path: str) -> str:
    """Assemble the single-sandbox model comparison snippet.

    Strategy:
      1. Load data (same loader as EDA).
      2. Isolate target + features, drop rows with missing target.
      3. Fill missing feature values (median for numeric, mode for cat).
      4. One-hot encode small-cardinality categoricals. Drop high-
         cardinality columns (would blow feature space on demo data).
      5. Encode target if classification.
      6. Train/test split with stratify fallback.
      7. Fit + predict each model, compute metrics.
      8. Render 1x2 subplot figure (confusion matrices / pred-vs-actual).
      9. Emit MODEL_OK_JSON / MODEL_FAILED_JSON marker.

    Robustness: every non-trivial step lives inside a try/except that,
    on failure, emits MODEL_FAILED_JSON and exits cleanly. The sandbox
    should never raise an unhandled exception.
    """
    basename = os.path.basename(data_file_path)
    ext = basename.rsplit(".", 1)[-1].lower() if "." in basename else ""
    sandbox_path = f"/workspace/{basename}"
    target = mc["target_column"]
    task = mc["task"]
    models = mc.get("models") or []

    # Hard-coded model imports: matching names declared by analysis_planner.
    # Any new model must be added here AND in _fit_block below.
    lines: List[str] = [
        "# Auto-generated model comparison snippet (chart_executor.py)",
        "import json as _json",
        "import numpy as _np",
        "import pandas as _pd",
        "import matplotlib",
        "matplotlib.use('Agg')",
        "import matplotlib.pyplot as plt",
        "from sklearn.model_selection import train_test_split",
        "from sklearn.preprocessing import LabelEncoder",
        "from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor",
        "from sklearn.linear_model import LogisticRegression, Ridge",
        "from sklearn.metrics import (",
        "    accuracy_score, precision_score, recall_score, f1_score,",
        "    confusion_matrix,",
        "    r2_score, mean_squared_error, mean_absolute_error,",
        ")",
        "",
        f"_DATA_PATH = {sandbox_path!r}",
        f"_TARGET = {target!r}",
        f"_TASK = {task!r}",
        f"_MODELS = {list(models)!r}",
        f"_IMAGE = '/workspace/{_MODEL_IMAGE_FILENAME}'",
        "",
        "def _emit(status, **extra):",
        "    marker = 'MODEL_OK_JSON' if status == 'ok' else 'MODEL_FAILED_JSON'",
        "    payload = {'task': _TASK, 'target': _TARGET}",
        "    payload.update(extra)",
        "    print(f'{marker}=' + _json.dumps(payload, default=str))",
        "",
        "try:",
        "    " + _loader_block(ext).replace("\n", "\n    ").rstrip(),
        "",
        "    if _TARGET not in _df.columns:",
        "        _emit('failed', error=f'target column {_TARGET!r} not found in data')",
        "        raise SystemExit(0)",
        "",
        "    # Drop rows with missing target; degenerate otherwise.",
        "    _df = _df[_df[_TARGET].notna()].copy()",
        "    if len(_df) < 20:",
        "        _emit('failed', error=f'only {len(_df)} rows after dropping NaN targets')",
        "        raise SystemExit(0)",
        "",
        "    # Cap at 10k rows for training speed.",
        "    if len(_df) > 10000:",
        "        _df = _df.sample(n=10000, random_state=42).reset_index(drop=True)",
        "",
        "    _y = _df[_TARGET]",
        "    _X = _df.drop(columns=[_TARGET])",
        "",
        "    # Fill numeric NaN with median, object NaN with mode (or 'missing').",
        "    for _col in _X.columns:",
        "        if _pd.api.types.is_numeric_dtype(_X[_col]):",
        "            _X[_col] = _X[_col].fillna(_X[_col].median())",
        "        else:",
        "            try:",
        "                _mode = _X[_col].mode(dropna=True)",
        "                _fill = _mode.iloc[0] if not _mode.empty else 'missing'",
        "            except Exception:",
        "                _fill = 'missing'",
        "            _X[_col] = _X[_col].fillna(_fill)",
        "",
        "    # One-hot encode object columns with <=10 unique values.",
        "    # Drop higher-cardinality object columns (would blow feature space).",
        "    _dropped_cols = []",
        "    _encode_cols = []",
        "    for _col in list(_X.columns):",
        "        if _pd.api.types.is_numeric_dtype(_X[_col]):",
        "            continue",
        "        if _X[_col].nunique(dropna=False) <= 10:",
        "            _encode_cols.append(_col)",
        "        else:",
        "            _dropped_cols.append(_col)",
        "    if _dropped_cols:",
        "        _X = _X.drop(columns=_dropped_cols)",
        "    if _encode_cols:",
        "        _X = _pd.get_dummies(_X, columns=_encode_cols, drop_first=True)",
        "",
        "    if _X.shape[1] == 0:",
        "        _emit('failed', error='no usable features after preprocessing')",
        "        raise SystemExit(0)",
        "",
        "    # Encode target for classification.",
        "    _target_classes = None",
        "    if _TASK == 'classification':",
        "        _le = LabelEncoder()",
        "        _y_enc = _le.fit_transform(_y.astype(str))",
        "        _target_classes = list(_le.classes_)",
        "    else:",
        "        _y_enc = _pd.to_numeric(_y, errors='coerce')",
        "        _mask = ~_np.isnan(_y_enc)",
        "        _y_enc = _y_enc[_mask]",
        "        _X = _X.loc[_mask.values].reset_index(drop=True)",
        "",
        "    # Train/test split — stratify for classification with fallback.",
        "    _stratify = _y_enc if _TASK == 'classification' else None",
        "    try:",
        "        _Xtr, _Xte, _ytr, _yte = train_test_split(",
        "            _X, _y_enc, test_size=0.2, random_state=42, stratify=_stratify",
        "        )",
        "    except ValueError:",
        "        # Stratify failed (rare class with <2 samples). Retry without.",
        "        _Xtr, _Xte, _ytr, _yte = train_test_split(",
        "            _X, _y_enc, test_size=0.2, random_state=42",
        "        )",
        "",
        "    _results = {}",
        "    _preds = {}",
        "",
        "    for _model_name in _MODELS:",
        "        try:",
        _fit_block_indent(),
        "        except Exception as _exc:",
        "            _results[_model_name] = {'error': str(_exc)[:200]}",
        "",
        "    # Render comparison figure — 1x2 subplots, one per model.",
        "    _n_models = max(1, len(_preds))",
        "    _fig, _axes = plt.subplots(1, _n_models, figsize=(6 * _n_models, 5))",
        "    if _n_models == 1:",
        "        _axes = [_axes]",
        "    _ax_idx = 0",
        "    for _mname, _yhat in _preds.items():",
        "        _ax = _axes[_ax_idx]",
        "        if _TASK == 'classification':",
        "            _cm = confusion_matrix(_yte, _yhat)",
        "            _im = _ax.imshow(_cm, cmap='Blues', aspect='auto')",
        "            _ax.set_title(f'{_mname}\\nConfusion Matrix')",
        "            _ax.set_xlabel('Predicted')",
        "            _ax.set_ylabel('Actual')",
        "            if _target_classes and len(_target_classes) <= 10:",
        "                _ticks = list(range(len(_target_classes)))",
        "                _ax.set_xticks(_ticks)",
        "                _ax.set_yticks(_ticks)",
        "                _ax.set_xticklabels(_target_classes, rotation=45, ha='right', fontsize=8)",
        "                _ax.set_yticklabels(_target_classes, fontsize=8)",
        "            for _i in range(_cm.shape[0]):",
        "                for _j in range(_cm.shape[1]):",
        "                    _ax.text(_j, _i, str(int(_cm[_i, _j])), ha='center', va='center', fontsize=9, color='black')",
        "        else:",
        "            _ax.scatter(_yte, _yhat, alpha=0.5, s=20, color='#3b82f6')",
        "            _lo = float(min(_np.min(_yte), _np.min(_yhat)))",
        "            _hi = float(max(_np.max(_yte), _np.max(_yhat)))",
        "            _ax.plot([_lo, _hi], [_lo, _hi], 'r--', linewidth=1)",
        "            _ax.set_xlabel('Actual')",
        "            _ax.set_ylabel('Predicted')",
        "            _ax.set_title(f'{_mname}\\nPredicted vs Actual')",
        "        _ax_idx += 1",
        "    _fig.tight_layout()",
        "    _fig.savefig(_IMAGE, dpi=100)",
        "    plt.close('all')",
        "",
        "    _emit(",
        "        'ok',",
        "        image_filename=_IMAGE.rsplit('/', 1)[-1],",
        "        metrics=_results,",
        "        n_train=int(len(_ytr)),",
        "        n_test=int(len(_yte)),",
        "        n_features=int(_X.shape[1]),",
        "        dropped_columns=_dropped_cols,",
        "        encoded_columns=_encode_cols,",
        "    )",
        "except SystemExit:",
        "    raise",
        "except Exception as _exc:",
        "    _emit('failed', error=str(_exc)[:300])",
        "",
    ]
    return "\n".join(lines) + "\n"


def _fit_block_indent() -> str:
    """Return the indented fit+score block for the model loop.

    Separate function because nested indent inside the big list is
    unreadable. Uses if/elif on the model name string (from planner)
    so we stay on the CodeValidator whitelist (no eval/getattr on
    module-level classes).
    """
    lines = [
        "            _lower = _model_name.lower()",
        "            if _lower == 'randomforestclassifier':",
        "                _m = RandomForestClassifier(n_estimators=100, random_state=42, n_jobs=1)",
        "            elif _lower == 'logisticregression':",
        "                _m = LogisticRegression(max_iter=1000, random_state=42)",
        "            elif _lower == 'randomforestregressor':",
        "                _m = RandomForestRegressor(n_estimators=100, random_state=42, n_jobs=1)",
        "            elif _lower == 'ridge':",
        "                _m = Ridge(random_state=42)",
        "            else:",
        "                _results[_model_name] = {'error': f'unknown model {_model_name!r}'}",
        "                continue",
        "            _m.fit(_Xtr, _ytr)",
        "            _yhat = _m.predict(_Xte)",
        "            _preds[_model_name] = _yhat",
        "            if _TASK == 'classification':",
        "                _results[_model_name] = {",
        "                    'accuracy': round(float(accuracy_score(_yte, _yhat)), 4),",
        "                    'precision': round(float(precision_score(_yte, _yhat, average='weighted', zero_division=0)), 4),",
        "                    'recall': round(float(recall_score(_yte, _yhat, average='weighted', zero_division=0)), 4),",
        "                    'f1': round(float(f1_score(_yte, _yhat, average='weighted', zero_division=0)), 4),",
        "                }",
        "            else:",
        "                _rmse = float(_np.sqrt(mean_squared_error(_yte, _yhat)))",
        "                _results[_model_name] = {",
        "                    'r2': round(float(r2_score(_yte, _yhat)), 4),",
        "                    'rmse': round(_rmse, 4),",
        "                    'mae': round(float(mean_absolute_error(_yte, _yhat)), 4),",
        "                }",
    ]
    return "\n".join(lines)
