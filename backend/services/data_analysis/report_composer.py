"""Compose the final Data Analysis response from executor output.

Takes the shape that ``chart_executor.execute_eda`` returns and assembles
the envelope the frontend consumes. Responsibilities:

- Persist each successful chart's PNG bytes to ``settings.temp_data_dir``
  via ``_persist_visualization_artifacts`` so the frontend can fetch them
  through ``/api/v1/files/visualizations/``. Filename collisions are
  resolved by the persister (rename-on-conflict), so the persisted name
  may differ from the in-sandbox name and we must remap it onto the
  matching chart entry.
- Build a compact ``key_findings`` list from per-chart summaries (counts,
  correlations, group cardinalities) so the UI can show bullet points
  without a second LLM call.
- Preserve the legacy response shape that ``analyze_query`` returns today
  (``success``, ``answer``, ``code``, ``visualizations``, ``dataset_info``,
  ``analysis_summary``, ``code_generation``) so frontend code and existing
  tests keep working while the grid rendering is wired up separately.

The composer does NOT download files, call the sandbox, or invoke an LLM —
all of that is upstream. It is a pure transform on executor + plan + metadata.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


def compose_eda_response(
    *,
    plan: Dict[str, Any],
    execution: Dict[str, Any],
    question: str,
    dataset_metadata: Dict[str, Any],
    generated_code: str = "",
) -> Dict[str, Any]:
    """Turn executor output + plan into the final response envelope.

    Args:
        plan: Output from ``chart_plan.eda_plan_from_metadata``. Used for
            rationale text and the model-comparison gate reason.
        execution: Output from ``chart_executor.execute_eda``. Source of
            truth for per-chart status, summaries, and the raw ``output_files``
            bytes dict.
        question: Original user question — echoed in the response for
            traceability and used when building the answer fallback.
        dataset_metadata: Output from ``DataAnalysisAgent._extract_dataset_info``.
            Exposed back to the frontend unchanged so it can render the
            column preview without refetching.

    Returns:
        {
          "success": bool,
          "answer": str,                       # human-readable summary
          "charts": [                           # one per plan chart, grid-order
            {id, type, status, image_filename, summary, error, params},
            ...
          ],
          "visualizations": [filename, ...],   # persisted filenames only,
                                                # matches legacy contract
          "analysis_summary": {                 # parsed for frontend bullets
            "key_findings": [str, ...],
            "rationale": str,
          },
          "code_generation": {
            "mode": "deterministic_planner",
            "fallback_reason": None,
          },
          "dataset_info": {...},
          "execution_time": float,
          "model_comparison": {...},            # gate info, currently disabled
          "stdout": str,                         # preserved for debug UIs
          "stderr": str,
        }
    """
    charts_from_exec: List[Dict[str, Any]] = execution.get("charts") or []
    output_files: Dict[str, Any] = execution.get("output_files") or {}

    persisted_by_original = _persist_charts(charts_from_exec, output_files)

    charts: List[Dict[str, Any]] = []
    # visualizations must preserve the legacy [{filename, path}, ...] shape
    # consumed by frontend firstArtifactPath (data-analysis/page.tsx:91-92).
    # Switching to plain strings silently breaks existing chart rendering.
    ordered_visualizations: List[Dict[str, str]] = []
    for spec in charts_from_exec:
        image_in = spec.get("image_filename")
        persisted_entry = (
            persisted_by_original.get(image_in) if image_in else None
        )
        persisted = persisted_entry["filename"] if persisted_entry else None

        status = spec.get("status", "failed")
        image_out: Optional[str] = None
        error = spec.get("error")
        if persisted_entry is not None:
            image_out = persisted
            ordered_visualizations.append(
                {
                    "filename": persisted_entry["filename"],
                    "path": persisted_entry["path"],
                }
            )
        elif status == "ok":
            # Executor said ok but we failed to persist — degrade so the UI
            # doesn't render a <img> pointing at a missing file.
            status = "failed"
            error = error or "chart image could not be persisted to disk"

        charts.append(
            {
                "id": spec.get("id"),
                "type": spec.get("type"),
                "status": status,
                "image_filename": image_out,
                "summary": spec.get("summary"),
                "error": error,
                "params": spec.get("params", {}),
            }
        )

    ok_count = sum(1 for c in charts if c["status"] == "ok")
    total = len(charts)
    success = bool(execution.get("success")) and ok_count > 0

    key_findings = _build_key_findings(charts, dataset_metadata)
    rationale = plan.get("rationale") or ""

    answer = _build_answer(
        ok_count=ok_count,
        total=total,
        rationale=rationale,
        dataset_metadata=dataset_metadata,
        question=question,
    )

    return {
        "success": success,
        "answer": answer,
        "charts": charts,
        "visualizations": ordered_visualizations,
        # Legacy contract: analyze_query returned both success+failure with
        # a `code` field that the data-analysis page renders in its
        # "Generated Code (Python)" panel. Pass the executor-built snippet
        # through so the panel stays populated on deterministic runs.
        "code": generated_code or "",
        "analysis_summary": {
            "key_findings": key_findings,
            "rationale": rationale,
        },
        "code_generation": {
            "mode": "deterministic_planner",
            "fallback_reason": None,
        },
        "dataset_info": dataset_metadata,
        "execution_time": float(execution.get("execution_time") or 0.0),
        "model_comparison": plan.get("model_comparison")
        or {"enabled": False, "reason": "not available"},
        "stdout": execution.get("stdout", ""),
        "stderr": execution.get("stderr", ""),
    }


# ---------------------------------------------------------------------------
# persistence
# ---------------------------------------------------------------------------


def _persist_charts(
    charts: List[Dict[str, Any]], output_files: Dict[str, Any]
) -> Dict[str, Dict[str, str]]:
    """Persist each chart's PNG one at a time so we keep a stable mapping.

    Calling ``_persist_visualization_artifacts`` with all files at once
    would work, but it returns ``[{filename, path}]`` in iteration order
    without telling us which output_file ended up with which persisted
    entry when collisions trigger ``_next_available_path`` rename. Going
    one chart at a time keeps the mapping trivial.

    Returns a dict of ``{original_filename: {"filename", "path"}}`` so
    callers can rebuild the legacy ``[{filename, path}]`` visualizations
    shape consumed by the frontend.
    """
    mapping: Dict[str, Dict[str, str]] = {}
    if not output_files:
        return mapping

    try:
        from backend.tools.visualization import _persist_visualization_artifacts
    except Exception as exc:  # pragma: no cover — import failure is fatal
        logger.error("visualization persister unavailable: %s", exc)
        return mapping

    for spec in charts:
        image_in = spec.get("image_filename")
        if not image_in or image_in not in output_files:
            continue
        try:
            persisted = _persist_visualization_artifacts(
                {image_in: output_files[image_in]}
            )
        except Exception as exc:
            logger.warning(
                "failed to persist chart %s (%s): %s",
                spec.get("id"),
                image_in,
                exc,
            )
            continue
        if persisted:
            mapping[image_in] = {
                "filename": persisted[0]["filename"],
                "path": persisted[0]["path"],
            }
    return mapping


# ---------------------------------------------------------------------------
# key findings
# ---------------------------------------------------------------------------


def _build_key_findings(
    charts: List[Dict[str, Any]], dataset_metadata: Dict[str, Any]
) -> List[str]:
    """Compose short bullet points from per-chart summaries.

    Kept deterministic on purpose: the UI renders these literally, no
    LLM cleanup pass. Matches the Key Findings contract the
    ``analyze_query`` response already exposes.
    """
    findings: List[str] = []

    rows = dataset_metadata.get("rows")
    cols = dataset_metadata.get("columns")
    if rows is not None and cols is not None:
        findings.append(f"Dataset: {rows:,} rows × {cols} columns.")

    for chart in charts:
        if chart["status"] != "ok":
            continue
        summary = chart.get("summary") or {}
        ctype = chart.get("type")
        try:
            finding = _summary_to_finding(ctype, summary)
        except Exception as exc:  # pragma: no cover — summary shape guard
            logger.debug("finding builder skipped %s: %s", chart.get("id"), exc)
            continue
        if finding:
            findings.append(finding)

    failed = [c for c in charts if c["status"] == "failed"]
    if failed:
        findings.append(
            f"{len(failed)} chart(s) skipped due to errors "
            f"(see details in each card)."
        )

    return findings


def _summary_to_finding(
    chart_type: Optional[str], summary: Dict[str, Any]
) -> Optional[str]:
    if chart_type == "histogram":
        col = summary.get("column")
        mean = summary.get("mean")
        std = summary.get("std")
        median = summary.get("median")
        if col is None or mean is None:
            return None
        parts = [f"'{col}': mean={_fmt(mean)}"]
        if median is not None:
            parts.append(f"median={_fmt(median)}")
        if std is not None:
            parts.append(f"std={_fmt(std)}")
        return ", ".join(parts) + "."

    if chart_type == "scatter":
        x = summary.get("x")
        y = summary.get("y")
        rho = summary.get("pearson_r")
        n = summary.get("n")
        if x is None or y is None:
            return None
        if rho is None:
            return f"'{x}' vs '{y}': n={n}."
        return f"'{x}' vs '{y}': Pearson r={_fmt(rho)} (n={n})."

    if chart_type == "heatmap":
        n = summary.get("n_columns")
        if n is None:
            return None
        return f"Correlation heatmap across {n} numeric columns."

    if chart_type == "bar":
        col = summary.get("column")
        cats = summary.get("categories") or []
        counts = summary.get("counts") or []
        if not col or not cats:
            return None
        top = cats[0]
        top_n = counts[0] if counts else None
        if top_n is not None:
            return (
                f"'{col}': {len(cats)} categories, "
                f"top='{top}' ({top_n})."
            )
        return f"'{col}': {len(cats)} categories."

    if chart_type == "boxplot":
        col = summary.get("column")
        by = summary.get("by")
        n_groups = summary.get("n_groups")
        if not col or not by:
            return None
        return f"'{col}' by '{by}' across {n_groups} group(s)."

    return None


def _fmt(value: Any) -> str:
    try:
        f = float(value)
    except (TypeError, ValueError):
        return str(value)
    if abs(f) >= 1000 or abs(f) < 0.01 and f != 0:
        return f"{f:.2e}"
    return f"{f:.2f}"


# ---------------------------------------------------------------------------
# answer text
# ---------------------------------------------------------------------------


def _build_answer(
    *,
    ok_count: int,
    total: int,
    rationale: str,
    dataset_metadata: Dict[str, Any],
    question: str,
) -> str:
    filename = dataset_metadata.get("filename") or "the dataset"
    rows = dataset_metadata.get("rows")

    if total == 0:
        return (
            f"No charts were produced for {filename}. The dataset does not "
            f"contain numeric or low-cardinality categorical columns that "
            f"the deterministic planner can plot."
        )

    if ok_count == 0:
        return (
            f"Attempted {total} chart(s) for {filename} but all of them "
            f"failed during rendering. Check the per-chart error messages "
            f"below for details."
        )

    header = f"Rendered {ok_count}/{total} charts for {filename}"
    if rows:
        header += f" ({rows:,} rows)"
    header += "."
    if rationale:
        return f"{header} {rationale}"
    return header
