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
        # sep=None + engine="python" matches the metadata reader so
        # semicolon/tab-delimited files (e.g. UCI wine-quality) parse
        # into the same column shape the planner saw. Without this,
        # the sandbox would see one giant string column and every
        # chart template would fail on "column not found".
        return (
            "try:\n"
            "    _df = _pd.read_csv(_DATA_PATH, sep=None, engine='python')\n"
            "except UnicodeDecodeError:\n"
            "    _df = _pd.read_csv(_DATA_PATH, sep=None, engine='python', encoding='latin-1')\n"
            "except Exception:\n"
            "    # Sniff failure — fall back to comma default.\n"
            "    _df = _pd.read_csv(_DATA_PATH)\n"
        )
    if ext in {"xlsx", "xls"}:
        return "_df = _pd.read_excel(_DATA_PATH)\n"
    if ext == "json":
        return "_df = _pd.read_json(_DATA_PATH)\n"
    # Default: try CSV — matches extract_dataset_info's treatment of
    # unknown extensions (it errors out up there, so we should rarely
    # hit this).
    return "_df = _pd.read_csv(_DATA_PATH, sep=None, engine='python')\n"


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
