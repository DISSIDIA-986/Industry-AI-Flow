"""Privacy-safe dataset metadata extraction for LLM code generation prompts."""

from __future__ import annotations

import json
import logging
import math
from pathlib import Path
from typing import Any, Dict, List

import pandas as pd

logger = logging.getLogger(__name__)

DEFAULT_MAX_PROFILE_COLUMNS = 60
DEFAULT_MAX_PROMPT_COLUMNS = 30
DEFAULT_MAX_PROMPT_CHARS = 6000


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except Exception:
        return default


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        number = float(value)
    except Exception:
        return default
    if not math.isfinite(number):
        return default
    return number


def _read_dataframe(data_file: str) -> pd.DataFrame:
    path = str(data_file or "").strip()
    suffix = Path(path).suffix.lower()
    if suffix == ".csv":
        last_error: Exception | None = None
        for encoding in ("utf-8", "utf-8-sig", "latin-1"):
            try:
                return pd.read_csv(path, encoding=encoding)
            except UnicodeDecodeError as exc:
                last_error = exc
                continue
        raise ValueError(
            "Unable to decode CSV with supported encodings (utf-8, utf-8-sig, latin-1)."
        ) from last_error
    if suffix in {".xlsx", ".xls"}:
        return pd.read_excel(path)
    if suffix == ".json":
        return pd.read_json(path)
    raise ValueError(f"Unsupported data file format: {suffix or '(unknown)'}")


def extract_dataset_metadata(
    data_file: str,
    *,
    max_profile_columns: int = DEFAULT_MAX_PROFILE_COLUMNS,
) -> Dict[str, Any]:
    """Extract structural dataset metadata without exposing raw row values."""
    source_path = str(data_file or "").strip()
    base = {
        "source_file": Path(source_path).name if source_path else "",
        "redaction_mode": "structural_metadata_only",
        "raw_rows_shared_with_llm": False,
    }
    if not source_path:
        return {**base, "status": "error", "error": "data_file is empty"}

    try:
        df = _read_dataframe(source_path)
    except Exception as exc:
        logger.warning("Dataset metadata extraction failed for %s: %s", source_path, exc)
        return {**base, "status": "error", "error": str(exc)}

    total_rows = _safe_int(len(df))
    total_columns = _safe_int(len(df.columns))
    profiled_columns = max(1, _safe_int(max_profile_columns, DEFAULT_MAX_PROFILE_COLUMNS))

    columns_info: List[Dict[str, Any]] = []
    for column_name in list(df.columns)[:profiled_columns]:
        series = df[column_name]
        non_null_count = _safe_int(series.notna().sum())
        null_count = _safe_int(series.isna().sum())
        column_meta: Dict[str, Any] = {
            "name": str(column_name),
            "dtype": str(series.dtype),
            "non_null_count": non_null_count,
            "null_count": null_count,
            "null_ratio": _safe_float(
                (null_count / total_rows) if total_rows > 0 else 0.0,
                default=0.0,
            ),
            "unique_count": _safe_int(series.nunique(dropna=True)),
        }

        if pd.api.types.is_numeric_dtype(series):
            numeric_series = series.dropna()
            if len(numeric_series) > 0:
                column_meta["numeric_summary"] = {
                    "min": _safe_float(numeric_series.min()),
                    "max": _safe_float(numeric_series.max()),
                    "mean": _safe_float(numeric_series.mean()),
                    "std": _safe_float(numeric_series.std()),
                }

        columns_info.append(column_meta)

    return {
        **base,
        "status": "ok",
        "rows": total_rows,
        "columns": total_columns,
        "column_names": [str(name) for name in list(df.columns)[:profiled_columns]],
        "profiled_columns": len(columns_info),
        "columns_info": columns_info,
    }


def build_prompt_metadata(
    metadata: Dict[str, Any],
    *,
    max_prompt_columns: int = DEFAULT_MAX_PROMPT_COLUMNS,
    max_chars: int = DEFAULT_MAX_PROMPT_CHARS,
) -> str:
    """Return a compact metadata JSON string suitable for LLM prompts."""
    if not isinstance(metadata, dict):
        return "{}"

    if metadata.get("status") != "ok":
        payload = {
            "status": str(metadata.get("status") or "error"),
            "error": str(metadata.get("error") or "unknown"),
            "redaction_mode": "structural_metadata_only",
            "raw_rows_shared_with_llm": False,
        }
        return json.dumps(payload, ensure_ascii=False)

    columns_info = metadata.get("columns_info")
    if not isinstance(columns_info, list):
        columns_info = []
    max_columns = max(1, _safe_int(max_prompt_columns, DEFAULT_MAX_PROMPT_COLUMNS))
    prompt_payload: Dict[str, Any] = {
        "status": "ok",
        "source_file": metadata.get("source_file", ""),
        "rows": _safe_int(metadata.get("rows", 0)),
        "columns": _safe_int(metadata.get("columns", 0)),
        "redaction_mode": "structural_metadata_only",
        "raw_rows_shared_with_llm": False,
        "columns_info": columns_info[:max_columns],
    }

    text = json.dumps(prompt_payload, ensure_ascii=False, separators=(",", ":"))
    if len(text) <= max_chars:
        return text

    trimmed_columns = list(prompt_payload["columns_info"])
    while trimmed_columns and len(text) > max_chars:
        trimmed_columns.pop()
        prompt_payload["columns_info"] = trimmed_columns
        text = json.dumps(prompt_payload, ensure_ascii=False, separators=(",", ":"))

    return text[:max_chars]


def build_metadata_audit_report(metadata: Dict[str, Any]) -> Dict[str, Any]:
    """Build concise metadata extraction report for API responses."""
    if not isinstance(metadata, dict):
        return {
            "status": "error",
            "error": "invalid metadata payload",
            "redaction_mode": "structural_metadata_only",
            "raw_rows_shared_with_llm": False,
        }

    if metadata.get("status") != "ok":
        return {
            "status": str(metadata.get("status") or "error"),
            "error": str(metadata.get("error") or "unknown"),
            "source_file": str(metadata.get("source_file") or ""),
            "redaction_mode": "structural_metadata_only",
            "raw_rows_shared_with_llm": False,
        }

    return {
        "status": "ok",
        "source_file": str(metadata.get("source_file") or ""),
        "rows": _safe_int(metadata.get("rows", 0)),
        "columns": _safe_int(metadata.get("columns", 0)),
        "profiled_columns": _safe_int(metadata.get("profiled_columns", 0)),
        "redaction_mode": "structural_metadata_only",
        "raw_rows_shared_with_llm": False,
    }
