"""
Data Analysis Agent - Analyzes CSV/Excel datasets via LLM-generated code.
Uses CodeExecutor for sandboxed execution and returns results with visualizations.
"""

import json
import logging
import math
import os
import re
import threading
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from backend.config import settings
from backend.services.code_executor import get_code_execution_manager, get_code_executor
from backend.services.llm_integration.llm_client import LLMClientFactory

logger = logging.getLogger(__name__)

# Backward-compatibility hook for legacy tests/callers that monkeypatch
# backend.services.data_analysis.data_analysis_agent.code_executor directly.
code_executor: Any | None = None


class _LegacyExecutorAdapter:
    """Shim that exposes a ``CodeExecutionManager``-style ``execute_code``
    signature on top of the legacy single-provider executor.

    The legacy executor (``DockerCodeExecutor`` / ``get_code_executor()``)
    has ``execute_code(code, data_files=None, timeout=None)`` with no
    ``mode`` argument. ``chart_executor.execute_eda`` calls through with
    ``mode=`` so we swallow it here. Keeps the legacy fallback path
    working when ``get_code_execution_manager()`` returns ``None``.
    """

    def __init__(self, legacy_executor: Any) -> None:
        self._exec = legacy_executor

    def execute_code(
        self,
        code: str,
        data_files: Optional[List[str]] = None,
        timeout: Optional[int] = None,
        mode: Optional[str] = None,  # ignored; legacy executor has a fixed backend
    ) -> Dict[str, Any]:
        return self._exec.execute_code(
            code=code, data_files=data_files, timeout=timeout
        )


class DataAnalysisAgent:
    """Data Analysis Agent - generates and executes code to analyze datasets."""

    def __init__(self, llm_client: Optional[Any] = None):
        """
        Initialize the Data Analysis Agent.

        Args:
            llm_client: LLM client instance, auto-created if not provided
        """
        if llm_client is not None:
            self.llm_client = llm_client
        else:
            try:
                self.llm_client = LLMClientFactory.create_client(
                    backend=settings.resolved_cloud_provider
                )
            except Exception as exc:
                logger.warning(
                    "LLM client creation failed: %s; data analysis LLM features disabled",
                    exc,
                )
                self.llm_client = None

        self.code_execution_manager = get_code_execution_manager()
        self.code_executor = (
            code_executor if code_executor is not None else get_code_executor()
        )

        if not self.code_execution_manager and not self.code_executor:
            logger.warning(
                "Code execution provider unavailable, data analysis is degraded"
            )

    def analyze_query(
        self,
        question: str,
        data_file_path: str,
        dataset_metadata: Optional[Dict[str, Any]] = None,
        on_progress: Optional[Any] = None,
    ) -> Dict[str, Any]:
        """
        Analyze a dataset to answer the user's question.

        Args:
            question: User's analysis question
            data_file_path: Path to the data file
            dataset_metadata: Pre-extracted metadata (optional, extracted automatically if missing)
            on_progress: Optional callback (stage, status, progress, detail) for SSE progress

        Returns:
            Dict containing answer, code, visualizations, and execution details
        """

        def _progress(stage: str, status: str, progress: float, detail: str) -> None:
            if on_progress is not None:
                try:
                    on_progress(stage, status, progress, detail)
                except Exception as exc:
                    logger.warning("on_progress callback failed: %s", exc)

        try:
            # 1. Validate file exists
            _progress("file_parse", "running", 0.05, "Validating data file...")
            if not os.path.exists(data_file_path):
                _progress("file_parse", "failed", 0.05, "File not found")
                return {
                    "success": False,
                    "error": f"Data file not found: {data_file_path}",
                    "answer": "The dataset could not be located. Please verify the file path and retry.",
                }
            _progress("file_parse", "completed", 0.10, f"File: {os.path.basename(data_file_path)}")

            # 2. Extract dataset metadata
            _progress("metadata_extract", "running", 0.12, "Extracting column info and statistics...")
            if not dataset_metadata:
                dataset_metadata = self._extract_dataset_info(data_file_path)
            if isinstance(dataset_metadata, dict) and dataset_metadata.get("error"):
                _progress("metadata_extract", "failed", 0.15, dataset_metadata["error"])
                return {
                    "success": False,
                    "error": dataset_metadata["error"],
                    "answer": dataset_metadata.get(
                        "error", "Failed to extract dataset metadata."
                    ),
                }
            _progress(
                "metadata_extract", "completed", 0.20,
                f"{dataset_metadata.get('rows', '?')} rows × {dataset_metadata.get('columns', '?')} cols",
            )

            # 3. Build deterministic EDA plan from metadata
            #
            # Replaces the former LLM code-gen path. The plan is a pure
            # function of dataset metadata (chart_plan.py), so this stage
            # cannot hit a cloud API failure, JSON parse retry, or
            # prompt-regression flake. Critical for demo stability.
            _progress("code_generation", "running", 0.25, "Planning charts from dataset shape...")
            from backend.services.data_analysis.chart_plan import (
                eda_plan_from_metadata,
            )

            plan = eda_plan_from_metadata(dataset_metadata, user_question=question)
            chart_count = len((plan.get("eda") or {}).get("charts") or [])
            code_gen_mode = "deterministic_planner"
            _progress(
                "code_generation",
                "completed",
                0.40,
                f"Planned {chart_count} chart(s)",
            )

            # 4. Validate generated code (security check)
            #
            # The deterministic snippet is built from frozen templates we
            # own. We still run CodeValidator in strict mode as belt-and-
            # suspenders: if a future render helper slips in a blocked
            # method (.apply/.agg/.map), this catches it before the
            # sandbox ever sees the code. Covered by
            # test_combined_snippet_passes_strict_validator.
            _progress("security_check", "running", 0.42, "Validating snippet...")
            from backend.services.code_executor.validator import validate_code
            from backend.services.data_analysis.chart_executor import (
                _build_combined_snippet,
                execute_eda,
            )

            charts_spec = (plan.get("eda") or {}).get("charts") or []
            snippet_for_validation = (
                _build_combined_snippet(charts_spec, data_file_path)
                if charts_spec
                else ""
            )
            if snippet_for_validation:
                validation = validate_code(snippet_for_validation, strict_mode=True)
                if not validation.is_valid:
                    _progress(
                        "security_check",
                        "failed",
                        0.50,
                        f"Validation failed: {validation.error}",
                    )
                    return {
                        "success": False,
                        "error": f"Deterministic snippet failed validation: {validation.error}",
                        "answer": "The analysis snippet did not pass security validation. This is a bug in the chart templates.",
                        "dataset_info": dataset_metadata,
                        "code_generation": {
                            "mode": code_gen_mode,
                            "fallback_reason": validation.error,
                        },
                    }
            _progress("security_check", "completed", 0.50, f"Validated ({code_gen_mode})")

            # 5. Execute combined snippet in a SINGLE sandbox invocation.
            #
            # This is the structural fix for first-run flakiness: the
            # old path would spin one Sandbox.create() per chart. Now all
            # N charts share one sandbox; partial failures are isolated
            # via CHART_OK_JSON / CHART_FAILED_JSON stdout markers.
            _progress("sandbox_execution", "running", 0.55, "Rendering charts in sandbox...")
            execution_runner = self.code_execution_manager
            if execution_runner is None and self.code_executor is not None:
                # Legacy executor path: older deployments/tests inject
                # ``data_analysis_agent.code_executor`` directly (or only have
                # Docker wired). Wrap it so ``execute_eda`` can call
                # ``.execute_code(code, data_files, timeout, mode=...)`` even
                # though the legacy executor's signature lacks ``mode``.
                execution_runner = _LegacyExecutorAdapter(self.code_executor)
            if execution_runner is None:
                _progress("sandbox_execution", "failed", 0.55, "No execution provider")
                return {
                    "success": False,
                    "error": "Code execution provider is unavailable",
                    "answer": "Data analysis is temporarily unavailable because the execution provider is offline.",
                    "dataset_info": dataset_metadata,
                    "code_generation": {
                        "mode": code_gen_mode,
                        "fallback_reason": "no code_execution_manager",
                    },
                }

            execution_result = execute_eda(
                plan=plan,
                data_file_path=data_file_path,
                code_execution_manager=execution_runner,
                mode=settings.code_execution_provider,
                timeout_s=60,
            )

            # 6. Compose the legacy-shaped response envelope.
            _progress("result_render", "running", 0.85, "Composing charts and findings...")
            from backend.services.data_analysis.report_composer import (
                compose_eda_response,
            )

            composed = compose_eda_response(
                plan=plan,
                execution=execution_result,
                question=question,
                dataset_metadata=dataset_metadata,
                generated_code=execution_result.get("code") or "",
            )

            if composed.get("success"):
                _progress("result_render", "completed", 1.0, "Analysis complete")
            else:
                _progress(
                    "result_render",
                    "failed",
                    1.0,
                    composed.get("stderr") or "no charts rendered",
                )

            return composed

        except Exception as e:
            logger.error(f"Data analysis agent error: {e}")
            return {
                "success": False,
                "error": str(e),
                "answer": "Data analysis failed due to an internal error.",
            }

    @staticmethod
    def _parse_analysis_summary(stdout: str) -> Optional[Dict[str, Any]]:
        """Parse ANALYSIS_SUMMARY_JSON marker from execution output."""
        if not stdout:
            return None
        match = re.search(r"ANALYSIS_SUMMARY_JSON=(.+)$", stdout, re.MULTILINE)
        if not match:
            return None
        try:
            return json.loads(match.group(1))
        except (json.JSONDecodeError, ValueError):
            return None

    def _extract_dataset_info(self, file_path: str) -> Dict[str, Any]:
        """
        Extract metadata from a dataset file (columns, types, statistics).

        Privacy by design: This function extracts structural metadata only.
        Raw data values (top_values, sample_rows) are kept in the metadata dict
        for local use (frontend preview) but are NEVER included in the LLM prompt
        built by _build_code_generation_prompt(). The prompt only uses column
        names and types — see that method for the privacy boundary.

        Args:
            file_path: Path to the data file

        Returns:
            Dict with dataset metadata (columns, rows, statistics)
        """
        # Large file guard: cap rows read to prevent OOM on huge files.
        # total_rows is counted separately so metadata reports the real dataset size.
        _NROWS_GUARD = 10_000

        try:
            # Load data file
            if file_path.endswith(".csv"):
                df = None
                # sep=None + engine="python" triggers csv.Sniffer so files that
                # use ';' or '\t' as delimiter (e.g. UCI wine-quality) parse
                # into proper columns instead of a single 500-char string.
                # Falls back to sep="," on sniff failure so standard comma
                # CSVs keep the faster C engine path where possible.
                for enc in ("utf-8", "utf-8-sig", "latin-1"):
                    try:
                        df = pd.read_csv(
                            file_path,
                            encoding=enc,
                            nrows=_NROWS_GUARD,
                            sep=None,
                            engine="python",
                        )
                        break
                    except UnicodeDecodeError:
                        continue
                    except pd.errors.ParserError:
                        try:
                            df = pd.read_csv(
                                file_path, encoding=enc, nrows=_NROWS_GUARD
                            )
                            break
                        except UnicodeDecodeError:
                            continue
                if df is None:
                    return {
                        "error": "Unable to decode CSV with any supported encoding (utf-8, utf-8-sig, latin-1)."
                    }
                # Count real total rows using csv.reader so quoted multiline
                # fields are counted correctly (raw line count would overcount).
                import csv as _csv

                try:
                    with open(file_path, newline="", encoding="utf-8") as f:
                        reader = _csv.reader(f)
                        next(reader, None)  # skip header
                        total_rows = sum(1 for _ in reader)
                except Exception:
                    total_rows = len(df)
            elif file_path.endswith((".xlsx", ".xls")):
                df = pd.read_excel(file_path)
                total_rows = len(df)
            elif file_path.endswith(".json"):
                df = pd.read_json(file_path)
                total_rows = len(df)
            else:
                return {"error": "Unsupported data file format."}

            # PII column name detection (warning only — column names are structural
            # metadata required for correct code generation, not aliased)
            from backend.services.data_analysis.pii_detector import detect_pii_columns

            pii_warnings = detect_pii_columns(df.columns.tolist())
            if pii_warnings:
                logger.warning(
                    "Detected potentially sensitive column names: %s. "
                    "Column names (not data) will be sent to cloud LLM for code generation.",
                    pii_warnings,
                )

            # Build column metadata.
            #
            # Each column gets a semantic `role` so chart_plan.py does not have
            # to reverse-engineer pandas dtype strings. Roles:
            #   "numeric"     — int/float/uint/nullable Int/Float, NOT bool
            #   "categorical" — object or pandas CategoricalDtype
            #   "boolean"     — bool
            #   "datetime"    — datetime64[ns] etc
            #   "unknown"     — anything else (timedelta, period, extension types)
            #
            # Also tags `is_id_like`: unique count approaches row count, so the
            # column is probably an ID/timestamp-as-int/ZIP and should not be
            # plotted by heuristic. Threshold 0.9 to allow small duplicates.
            columns_info = []

            def _safe_float(val, default=0.0):
                try:
                    f = float(val)
                    if not math.isfinite(f):
                        return default
                    return f
                except (TypeError, ValueError):
                    return default

            for col in df.columns:
                series = df[col]
                col_type = str(series.dtype)
                non_null = int(series.count())
                null_count = int(series.isnull().sum())

                # Role classification — use pandas helpers so nullable / uint /
                # extension types are handled correctly.
                is_bool = pd.api.types.is_bool_dtype(series)
                is_numeric = (
                    pd.api.types.is_numeric_dtype(series) and not is_bool
                )
                is_datetime = pd.api.types.is_datetime64_any_dtype(series)
                is_categorical = isinstance(
                    series.dtype, pd.CategoricalDtype
                ) or series.dtype == object

                if is_bool:
                    role = "boolean"
                elif is_numeric:
                    role = "numeric"
                elif is_datetime:
                    role = "datetime"
                elif is_categorical:
                    role = "categorical"
                else:
                    role = "unknown"

                col_info: Dict[str, Any] = {
                    "name": col,
                    "type": col_type,
                    "role": role,
                    "non_null_count": non_null,
                    "null_count": null_count,
                }

                # ID-like: near-unique values + column name that reads as an
                # identifier. Both conditions must hold, otherwise continuous
                # numeric columns (prices, coordinates, sensor readings) that
                # happen to be mostly unique get excluded from every chart.
                if non_null > 0 and role in {"numeric", "categorical"}:
                    unique_count = int(series.nunique(dropna=True))
                    col_info["unique_values"] = unique_count
                    uniqueness = unique_count / non_null
                    name_lower = str(col).strip().lower()
                    name_is_id = bool(
                        re.match(r"^(id|uuid|guid|row_?(id|num|index))$", name_lower)
                        or re.search(r"(^|_)(id|uuid|guid)$", name_lower)
                        or name_lower.startswith("row_")
                    )
                    col_info["is_id_like"] = (
                        non_null >= 10 and uniqueness >= 0.98 and name_is_id
                    )

                if role == "numeric":
                    col_info.update(
                        {
                            "mean": _safe_float(series.mean()),
                            "min": _safe_float(series.min()),
                            "max": _safe_float(series.max()),
                            "std": _safe_float(series.std()),
                        }
                    )
                elif role == "categorical":
                    unique_count = col_info.get("unique_values", 0)
                    if unique_count <= 20:
                        value_counts = series.value_counts().to_dict()
                        col_info["top_values"] = dict(
                            list(value_counts.items())[:5]
                        )

                columns_info.append(col_info)

            # Precompute top-correlated numeric pair so chart_plan.py can
            # stay pure (no df access). Uses the already-in-memory sample.
            # Excludes ID-like columns (monotonic sequences, timestamps-as-int,
            # ZIP codes) because correlations between them are noise.
            top_corr_pair: Optional[Dict[str, Any]] = None
            try:
                numeric_cols = [
                    c["name"]
                    for c in columns_info
                    if c.get("role") == "numeric"
                    and float(c.get("std") or 0.0) > 0.0
                    and not c.get("is_id_like", False)
                ]
                if len(numeric_cols) >= 2:
                    corr = df[numeric_cols].corr(method="pearson").abs()
                    best_rho = -1.0
                    best_pair = None
                    for i, a in enumerate(numeric_cols):
                        for b in numeric_cols[i + 1 :]:
                            rho = float(corr.at[a, b])
                            if math.isfinite(rho) and rho > best_rho:
                                best_rho = rho
                                best_pair = (a, b)
                    if best_pair is not None:
                        top_corr_pair = {
                            "col_a": best_pair[0],
                            "col_b": best_pair[1],
                            "abs_rho": best_rho,
                        }
            except Exception as exc:
                logger.debug("top_corr_pair computation skipped: %s", exc)

            truncated = total_rows > len(df)
            metadata: Dict[str, Any] = {
                "filename": os.path.basename(file_path),
                "rows": total_rows,
                "rows_sampled": len(df) if truncated else total_rows,
                "truncated": truncated,
                "columns": len(df.columns),
                "column_names": df.columns.tolist(),
                "columns_info": columns_info,
                "memory_usage": int(df.memory_usage(deep=True).sum()),
                "has_index": df.index.name is not None,
            }
            if top_corr_pair is not None:
                metadata["top_corr_pair"] = top_corr_pair
            return metadata

        except Exception as e:
            logger.error(f"Failed to extract dataset metadata: {e}")
            return {"error": str(e)}

    def _generate_analysis_code(
        self, question: str, data_file_path: str, dataset_metadata: Dict[str, Any]
    ) -> Optional[str]:
        """
        Use LLM to generate Python analysis code.

        Args:
            question: User's analysis question
            data_file_path: Path to the data file
            dataset_metadata: Extracted dataset metadata

        Returns:
            Generated Python code string
        """
        # Build the code generation prompt
        prompt = self._build_code_generation_prompt(
            question, data_file_path, dataset_metadata
        )

        if self.llm_client is None:
            logger.warning(
                "LLM client unavailable, falling back to template code generation"
            )
            return self._generate_template_code(
                question, data_file_path, dataset_metadata
            )

        try:
            # Call LLM to generate analysis code
            llm_response = self.llm_client.generate(
                prompt,
                temperature=0.1,
                max_tokens=1000,  # Low temperature for deterministic code
            )

            # Extract code block from response
            code = self._extract_code_from_response(llm_response)

            return code

        except Exception as e:
            logger.error(f"LLM code generation failed: {e}")

        # Cloud LLM dual fallback: try alternate cloud providers before template.
        for fallback_backend in ("zhipu", "groq"):
            if (
                self.llm_client is not None
                and getattr(self.llm_client, "backend", None) == fallback_backend
            ):
                continue
            try:
                fallback_client = LLMClientFactory.create_client(
                    backend=fallback_backend
                )
                llm_response = fallback_client.generate(
                    prompt, temperature=0.1, max_tokens=1000
                )
                code = self._extract_code_from_response(llm_response)
                logger.info("Code generation succeeded with fallback: %s", fallback_backend)
                return code
            except Exception as exc:
                logger.warning("Fallback %s also failed: %s", fallback_backend, exc)

        # Final fallback: template-based code generation
        return self._generate_template_code(
            question, data_file_path, dataset_metadata
        )

    @staticmethod
    def _blocked_methods_list() -> str:
        """Build blocked methods list dynamically from CodeValidator source of truth."""
        from backend.services.code_executor.validator import CodeValidator

        return ", ".join(f".{m}()" for m in sorted(CodeValidator.BLOCKED_METHOD_NAMES))

    def _build_code_generation_prompt(
        self, question: str, data_file_path: str, dataset_metadata: Dict[str, Any]
    ) -> str:
        """Build the unified analysis+visualization code generation prompt."""
        clean_question = (
            question.replace("{", "").replace("}", "").replace("```", "").strip()[:500]
        )
        columns_desc = "\n".join(
            [
                f"  - {col['name'].replace('{', '').replace('}', '').replace('`', '')} ({col['type']})"
                for col in dataset_metadata.get("columns_info", [])
            ]
        )
        blocked = self._blocked_methods_list()
        filename = os.path.basename(data_file_path)

        return f"""You are a data analysis assistant. Write Python code that:
1. Analyzes the dataset to answer the user's question
2. Generates an appropriate visualization chart

**Dataset Metadata** (no raw data — privacy by design):
- Filename: {filename}
- Rows: {dataset_metadata.get('rows', 'unknown')}, Columns: {dataset_metadata.get('columns', 'unknown')}
- Column details:
{columns_desc}

**User Question**: {clean_question}

**Hard Requirements**:
1. Use pandas as pd, numpy as np, matplotlib.pyplot as plt, seaborn as sns
2. Read data from "/workspace/{filename}"
3. Print analysis results clearly with print() statements
4. Print a final JSON marker line: ANALYSIS_SUMMARY_JSON={{"analysis_type": "...", "key_findings": ["..."], "chart_type": "..."}}
   Use json.dumps() to serialize the dict.
5. Auto-detect the best chart type based on the data and question:
   - Numeric trend over time → line chart
   - Category comparison → bar chart
   - Two numeric variables correlation → scatter plot
   - Single variable distribution → histogram
   - Proportion / composition → pie chart
6. Save exactly one chart to "/workspace/analysis_chart.png"
   with plt.savefig("/workspace/analysis_chart.png", dpi=150, bbox_inches="tight")
7. try: plt.style.use("seaborn-v0_8-whitegrid")
   except: plt.style.use("ggplot")
8. Set figure size to (10, 6) minimum
9. Include proper title, axis labels, and legend where appropriate

**BLOCKED methods** (code validator will reject these — DO NOT USE):
{blocked}
Use instead: df.groupby(col)[y].mean(), df[col].value_counts(), df.pivot_table(), for-loops, list comprehensions

**BLOCKED modules**: os, subprocess, sys, pathlib, socket, requests, urllib
**BLOCKED functions**: open(), eval(), exec(), __import__(), compile(), input(), getattr(), setattr()

10. Handle missing values gracefully (dropna() or fillna() before plotting)
11. All text in English only
12. Code must complete within 30 seconds

Return ONLY executable Python code, no markdown fences, no explanations."""

    def _extract_code_from_response(self, response: str) -> Optional[str]:
        """Extract Python code block from LLM response."""
        # Try to find fenced code block
        code_pattern = r"```[Pp]ython[ \t]*\r?\n(.*?)```"
        matches = re.findall(code_pattern, response, re.DOTALL)

        if matches:
            return matches[0].strip()

        # Stricter fallback: only accept as raw code if it parses as valid
        # Python and contains import statements (not just prose mentioning
        # the words 'import' and 'print').
        stripped = response.strip()
        if stripped:
            import ast

            try:
                tree = ast.parse(stripped)
                has_import = any(
                    isinstance(node, (ast.Import, ast.ImportFrom))
                    for node in ast.walk(tree)
                )
                if has_import:
                    return stripped
            except SyntaxError:
                pass

        return None

    def _generate_template_code(
        self, question: str, data_file_path: str, dataset_metadata: Dict[str, Any]
    ) -> str:
        """Generate template-based analysis code when LLM code generation fails."""
        filename = os.path.basename(data_file_path)

        # Classify question by keyword matching
        question_lower = question.lower()

        # Average / mean calculation
        if any(keyword in question_lower for keyword in ["average", "avg", "mean"]):
            return self._template_average(filename, dataset_metadata, question)

        elif any(
            keyword in question_lower
            for keyword in ["max", "maximum", "largest", "highest"]
        ):
            return self._template_max(filename, dataset_metadata, question)

        elif any(
            keyword in question_lower
            for keyword in ["min", "minimum", "smallest", "lowest"]
        ):
            return self._template_min(filename, dataset_metadata, question)

        elif any(
            keyword in question_lower
            for keyword in ["count", "total", "number of", "how many"]
        ):
            return self._template_count(filename, dataset_metadata)

        elif any(
            keyword in question_lower
            for keyword in ["percentage", "proportion", "ratio", "%"]
        ):
            return self._template_percentage(filename, dataset_metadata)

        else:
            # Default: descriptive statistics overview
            return self._template_describe(filename, dataset_metadata)

    def _template_describe(self, filename: str, metadata: Dict) -> str:
        """Generate code for descriptive statistics overview."""
        read_call = self._read_data_code(filename)
        return f"""import pandas as pd

df = {read_call}
print("Dataset Overview:")
print(f"Total rows: {{len(df)}}")
print(f"Total columns: {{len(df.columns)}}")
print("\\nColumn types:")
print(df.dtypes)
print("\\nStatistical summary:")
print(df.describe())
"""

    @staticmethod
    def _read_data_code(filename: str) -> str:
        """Return pandas read call appropriate for the file extension."""
        if filename.endswith((".xlsx", ".xls")):
            return f"pd.read_excel('/workspace/{filename}')"
        return f"pd.read_csv('/workspace/{filename}')"

    @staticmethod
    def _sanitize_column_name(col: str) -> str:
        """Sanitize a column name for safe interpolation into generated Python code.

        Escapes single quotes and backslashes to prevent code injection via
        malicious CSV column names.
        """
        return col.replace("\\", "\\\\").replace("'", "\\'")

    @staticmethod
    def _pick_relevant_column(numeric_cols: list[str], question: str) -> str:
        """Pick the most relevant numeric column based on question keywords."""
        question_lower = question.lower() if question else ""
        for col in numeric_cols:
            col_lower = col.lower()
            # Check if any part of the column name appears in the question
            col_parts = re.split(r"[_\-\s]+", col_lower)
            if any(part in question_lower for part in col_parts if len(part) > 2):
                return col
        # Fallback: prefer columns with 'cost', 'price', 'amount', 'total'
        priority_keywords = [
            "cost",
            "price",
            "amount",
            "total",
            "value",
            "salary",
            "revenue",
        ]
        for keyword in priority_keywords:
            for col in numeric_cols:
                if keyword in col.lower():
                    return col
        return numeric_cols[0]

    def _template_average(
        self, filename: str, metadata: Dict, question: str = ""
    ) -> str:
        """Generate code for average/mean value calculations."""
        numeric_cols = [
            col["name"] for col in metadata.get("columns_info", []) if "mean" in col
        ]

        if numeric_cols:
            target_col = self._sanitize_column_name(
                self._pick_relevant_column(numeric_cols, question)
            )
            read_call = self._read_data_code(filename)
            return f"""import pandas as pd

df = {read_call}
avg_value = df['{target_col}'].mean()
print(f"Average of '{target_col}': {{avg_value:.2f}}")
"""
        else:
            return self._template_describe(filename, metadata)

    def _template_max(self, filename: str, metadata: Dict, question: str = "") -> str:
        """Generate code for maximum value queries."""
        numeric_cols = [
            col["name"] for col in metadata.get("columns_info", []) if "max" in col
        ]

        if numeric_cols:
            target_col = self._sanitize_column_name(
                self._pick_relevant_column(numeric_cols, question)
            )
            read_call = self._read_data_code(filename)
            return f"""import pandas as pd

df = {read_call}
col_data = df['{target_col}'].dropna()
if len(col_data) == 0:
    print("No non-null values found in '{target_col}'")
else:
    max_value = col_data.max()
    max_row = df[df['{target_col}'] == max_value].iloc[0]
    print(f"Maximum of '{target_col}': {{max_value}}")
    print(f"Row with max value: {{max_row.to_dict()}}")
"""
        else:
            return self._template_describe(filename, metadata)

    def _template_min(self, filename: str, metadata: Dict, question: str = "") -> str:
        """Template for minimum value queries."""
        numeric_cols = [
            col["name"] for col in metadata.get("columns_info", []) if "min" in col
        ]

        if numeric_cols:
            target_col = self._sanitize_column_name(
                self._pick_relevant_column(numeric_cols, question)
            )
            read_call = self._read_data_code(filename)
            return f"""import pandas as pd

df = {read_call}
col_data = df['{target_col}'].dropna()
if len(col_data) == 0:
    print("No non-null values found in '{target_col}'")
else:
    min_value = col_data.min()
    min_row = df[df['{target_col}'] == min_value].iloc[0]
    print(f"Minimum of '{target_col}': {{min_value}}")
    print(f"Row with min value: {{min_row.to_dict()}}")
"""
        else:
            return self._template_describe(filename, metadata)

    def _pick_relevant_categorical_column(
        self, categorical_cols: list, question: str = ""
    ) -> str:
        """Pick the most relevant categorical column based on the user question."""
        if not question or not categorical_cols:
            return categorical_cols[0] if categorical_cols else ""
        question_lower = question.lower()
        for col in categorical_cols:
            col_lower = col.lower()
            if col_lower in question_lower:
                return col
            col_parts = re.split(r"[_\-\s]+", col_lower)
            if any(part in question_lower for part in col_parts if len(part) > 2):
                return col
        return categorical_cols[0]

    def _template_count(self, filename: str, metadata: Dict, question: str = "") -> str:
        """Generate code to count values in categorical columns."""
        categorical_cols = [
            col["name"]
            for col in metadata.get("columns_info", [])
            if col.get("unique_values", 0) > 0 and col.get("unique_values", 0) < 100
        ]

        read_call = self._read_data_code(filename)
        if categorical_cols:
            target_col = self._sanitize_column_name(
                self._pick_relevant_categorical_column(categorical_cols, question)
            )
            return f"""import pandas as pd

df = {read_call}
value_counts = df['{target_col}'].value_counts()
print(f"Value counts for '{target_col}':")
print(value_counts)
"""
        else:
            return f"""import pandas as pd

df = {read_call}
print(f"Total rows: {{len(df)}}")
"""

    def _template_percentage(
        self, filename: str, metadata: Dict, question: str = ""
    ) -> str:
        """Generate code to calculate percentage distribution of categorical columns."""
        categorical_cols = [
            col["name"]
            for col in metadata.get("columns_info", [])
            if col.get("unique_values", 0) > 0 and col.get("unique_values", 0) < 50
        ]

        if categorical_cols:
            target_col = self._sanitize_column_name(
                self._pick_relevant_categorical_column(categorical_cols, question)
            )
            read_call = self._read_data_code(filename)
            return f"""import pandas as pd

df = {read_call}
value_counts = df['{target_col}'].value_counts()
percentages = (value_counts / len(df) * 100).round(2)
print(f"Percentage distribution for '{target_col}':")
for val, pct in percentages.items():
    print(f"  {{val}}: {{pct}}%")
"""
        else:
            return self._template_describe(filename, metadata)

    def _parse_execution_output(
        self, stdout: str, question: str, dataset_metadata: Dict[str, Any]
    ) -> str:
        """
        Parse and format the execution output from the code sandbox.

        Args:
            stdout: Raw standard output from code execution
            question: The user's original question
            dataset_metadata: Metadata about the dataset being analyzed

        Returns:
            Formatted analysis result string
        """
        if not stdout.strip():
            return "The analysis completed but produced no output."

        # Clean whitespace
        cleaned_output = stdout.strip()

        # If output already ends with punctuation, return as-is
        if cleaned_output.endswith((".", ".", "!", "!")):
            return cleaned_output

        # Wrap raw output with a header
        return f"Analysis result:\n{cleaned_output}"

    def _generate_fallback_answer(
        self, question: str, dataset_metadata: Dict[str, Any], error_message: str
    ) -> str:
        """
        Generate a metadata-based fallback answer when code execution fails.

        Args:
            question: The user's original question
            dataset_metadata: Metadata about the dataset
            error_message: The error that caused the fallback

        Returns:
            A best-effort answer based on dataset metadata
        """
        # Classify question by keywords
        question_lower = question.lower()

        # Questions about columns / features
        if (
            "feature" in question_lower
            or "column" in question_lower
            or "field" in question_lower
            or "variable" in question_lower
        ):
            columns = dataset_metadata.get("column_names", [])
            if columns:
                return (
                    f"The dataset contains the following columns: {', '.join(columns)}"
                )

        # Questions about row count / size
        if (
            "how many" in question_lower
            or "count" in question_lower
            or "row" in question_lower
            or "record" in question_lower
        ):
            rows = dataset_metadata.get("rows")
            if rows:
                return f"The dataset contains {rows} rows."

        # Default fallback
        return f"I was unable to complete the analysis due to an execution error. The dataset has {dataset_metadata.get('rows', 'unknown')} rows and {dataset_metadata.get('columns', 'unknown')} columns."


# Lazy singleton — avoids import-time side effects (LLM client, Docker init).
_data_analysis_agent: Optional[DataAnalysisAgent] = None
_data_analysis_agent_lock = threading.Lock()


def get_data_analysis_agent() -> DataAnalysisAgent:
    """Lazy factory — creates agent on first call, handles missing LLM gracefully."""
    global _data_analysis_agent
    if _data_analysis_agent is None:
        with _data_analysis_agent_lock:
            if _data_analysis_agent is None:
                try:
                    _data_analysis_agent = DataAnalysisAgent()
                except Exception as _exc:
                    logger.warning("DataAnalysisAgent init failed: %s", _exc)
                    _data_analysis_agent = DataAnalysisAgent.__new__(DataAnalysisAgent)
                    _data_analysis_agent.llm_client = None
                    _data_analysis_agent.code_execution_manager = None
                    _data_analysis_agent.code_executor = None
    return _data_analysis_agent


# Keep backward-compatible attribute name but as None — callers should use
# get_data_analysis_agent() instead.
data_analysis_agent = None
