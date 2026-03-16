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
                    backend=settings.resolved_local_backend
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
    ) -> Dict[str, Any]:
        """
        Analyze a dataset to answer the user's question.

        Args:
            question: User's analysis question
            data_file_path: Path to the data file
            dataset_metadata: Pre-extracted metadata (optional, extracted automatically if missing)

        Returns:
            Dict containing answer, code, visualizations, and execution details
        """
        try:
            # 1. Validate file exists
            if not os.path.exists(data_file_path):
                return {
                    "success": False,
                    "error": f"Data file not found: {data_file_path}",
                    "answer": "The dataset could not be located. Please verify the file path and retry.",
                }

            # 2. Extract dataset metadata
            if not dataset_metadata:
                dataset_metadata = self._extract_dataset_info(data_file_path)
            if isinstance(dataset_metadata, dict) and dataset_metadata.get("error"):
                return {
                    "success": False,
                    "error": dataset_metadata["error"],
                    "answer": dataset_metadata.get(
                        "error", "Failed to extract dataset metadata."
                    ),
                }

            # 3. Generate analysis code
            analysis_code = self._generate_analysis_code(
                question, data_file_path, dataset_metadata
            )

            if not analysis_code:
                return {
                    "success": False,
                    "error": "Failed to generate analysis code.",
                    "answer": "The analysis code could not be generated for this request.",
                }

            # Validate generated code before execution
            from backend.services.code_executor.validator import validate_code

            validation = validate_code(analysis_code, strict_mode=True)
            if not validation.is_valid:
                return {
                    "success": False,
                    "error": f"Generated code failed validation: {validation.error}",
                    "answer": "The generated analysis code did not pass security validation.",
                }

            # 4. Execute code in sandbox
            if not self.code_execution_manager and not self.code_executor:
                return {
                    "success": False,
                    "error": "Code execution provider is unavailable",
                    "answer": "Data analysis is temporarily unavailable because the execution provider is offline.",
                }

            if self.code_execution_manager is not None:
                execution_result = self.code_execution_manager.execute_code(
                    code=analysis_code,
                    data_files=[data_file_path],
                    timeout=30,
                    mode=settings.code_execution_provider,
                )
            else:
                execution_result = self.code_executor.execute_code(
                    code=analysis_code, data_files=[data_file_path], timeout=30
                )

            # 5. Process execution results
            if execution_result["success"]:
                answer = self._parse_execution_output(
                    execution_result["stdout"], question, dataset_metadata
                )

                return {
                    "success": True,
                    "answer": answer,
                    "code": analysis_code,
                    "stdout": execution_result["stdout"],
                    "execution_time": execution_result["execution_time"],
                    "visualizations": execution_result.get("visualizations", []),
                    "dataset_info": dataset_metadata,
                }
            else:
                # Execution failed, generate fallback answer from metadata
                fallback_answer = self._generate_fallback_answer(
                    question, dataset_metadata, execution_result.get("stderr", "")
                )

                return {
                    "success": False,
                    "error": execution_result.get(
                        "error", "Code execution failed during data analysis."
                    ),
                    "stderr": execution_result.get("stderr", ""),
                    "answer": fallback_answer,
                    "code": analysis_code,
                    "dataset_info": dataset_metadata,
                }

        except Exception as e:
            logger.error(f"Data analysis agent error: {e}")
            return {
                "success": False,
                "error": str(e),
                "answer": "Data analysis failed due to an internal error.",
            }

    def _extract_dataset_info(self, file_path: str) -> Dict[str, Any]:
        """
        Extract metadata from a dataset file (columns, types, statistics).

        Args:
            file_path: Path to the data file

        Returns:
            Dict with dataset metadata (columns, rows, statistics)
        """
        try:
            # Load data file
            if file_path.endswith(".csv"):
                df = None
                for enc in ("utf-8", "utf-8-sig", "latin-1"):
                    try:
                        df = pd.read_csv(file_path, encoding=enc)
                        break
                    except UnicodeDecodeError:
                        continue
                if df is None:
                    return {
                        "error": "Unable to decode CSV with any supported encoding (utf-8, utf-8-sig, latin-1)."
                    }
            elif file_path.endswith((".xlsx", ".xls")):
                df = pd.read_excel(file_path)
            elif file_path.endswith(".json"):
                df = pd.read_json(file_path)
            else:
                return {"error": "Unsupported data file format."}

            # Build column metadata
            columns_info = []
            for col in df.columns:
                col_type = str(df[col].dtype)
                col_info = {
                    "name": col,
                    "type": col_type,
                    "non_null_count": int(df[col].count()),
                    "null_count": int(df[col].isnull().sum()),
                }

                if df[col].dtype in ["int64", "float64"]:
                    # Guard against all-NaN columns: mean/min/max/std return NaN
                    # which breaks json.dumps() serialization
                    def _safe_float(val, default=0.0):
                        try:
                            f = float(val)
                            if not math.isfinite(f):
                                return default
                            return f
                        except (TypeError, ValueError):
                            return default

                    col_info.update(
                        {
                            "mean": _safe_float(df[col].mean()),
                            "min": _safe_float(df[col].min()),
                            "max": _safe_float(df[col].max()),
                            "std": _safe_float(df[col].std()),
                        }
                    )

                # Categorical column statistics
                elif df[col].dtype == "object":
                    unique_count = df[col].nunique()
                    if unique_count <= 20:  # Low cardinality - include value counts
                        value_counts = df[col].value_counts().to_dict()
                        col_info.update(
                            {
                                "unique_values": unique_count,
                                "top_values": dict(list(value_counts.items())[:5]),
                            }
                        )
                    else:
                        col_info["unique_values"] = unique_count

                columns_info.append(col_info)

            return {
                "filename": os.path.basename(file_path),
                "rows": len(df),
                "columns": len(df.columns),
                "column_names": df.columns.tolist(),
                "columns_info": columns_info,
                "memory_usage": int(df.memory_usage(deep=True).sum()),
                "has_index": df.index.name is not None,
            }

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
        for fallback_backend in ("zhipu", "gemini"):
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

    def _build_code_generation_prompt(
        self, question: str, data_file_path: str, dataset_metadata: Dict[str, Any]
    ) -> str:
        """Build the code generation prompt for the LLM."""
        clean_question = (
            question.replace("{", "").replace("}", "").replace("```", "").strip()[:500]
        )
        columns_desc = "\n".join(
            [
                f"  - {col['name'].replace('{', '').replace('}', '').replace('`', '')} ({col['type']})"
                for col in dataset_metadata.get("columns_info", [])
            ]
        )

        return f"""You are a data analysis assistant. Write Python code to answer the user's question about the dataset.

**Dataset Information**:
- Filename: {os.path.basename(data_file_path)}
- Rows: {dataset_metadata.get('rows', 'unknown')}
- Columns: {dataset_metadata.get('columns', 'unknown')}
- Column details:
{columns_desc}

**User Question**: {clean_question}

**Requirements**:
1. Use pandas to load the data: pd.read_csv() or pd.read_excel()
2. Data file path: /workspace/{os.path.basename(data_file_path)}
3. Output results using print() statements
4. Include data validation and handle missing values
5. Save any visualizations to /workspace/ directory
6. Keep the code concise and well-commented
7. Code must complete within 30 seconds

**Example**:
```python
import pandas as pd
import numpy as np

# Load the dataset
df = pd.read_csv('/workspace/{os.path.basename(data_file_path)}')

# Perform analysis
# ... your analysis code ...

# Output results
print("Analysis results: ...")
```

Return ONLY Python code. Wrap the code in ```python and ``` markers."""

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
