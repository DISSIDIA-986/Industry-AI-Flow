"""
ENAgent - ENCSV/ExcelEN
ENCodeExecutorEN,EN
"""

import json
import logging
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from backend.config import settings
from backend.services.code_executor import code_executor, get_code_execution_manager
from backend.services.llm_integration.llm_client import LLMClientFactory

logger = logging.getLogger(__name__)


class DataAnalysisAgent:
    """ENAgent - EN"""

    def __init__(self, llm_client: Optional[Any] = None):
        """
        ENAgent

        Args:
            llm_client: LLMEN,EN
        """
        self.llm_client = llm_client or LLMClientFactory.create_client(
            backend=settings.resolved_local_backend
        )
        self.code_execution_manager = get_code_execution_manager()
        self.code_executor = code_executor

        if not self.code_execution_manager and not self.code_executor:
            logger.warning("Code execution provider unavailable, data analysis is degraded")

    def analyze_query(
        self,
        question: str,
        data_file_path: str,
        dataset_metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        EN

        Args:
            question: EN
            data_file_path: EN
            dataset_metadata: EN(EN,EN)

        Returns:
            DictENanswer,code,visualizationsEN
        """
        try:
            # 1. EN
            if not os.path.exists(data_file_path):
                return {
                    "success": False,
                    "error": f"Data file not found: {data_file_path}",
                    "answer": "The dataset could not be located. Please verify the file path and retry.",
                }

            # 2. EN
            if not dataset_metadata:
                dataset_metadata = self._extract_dataset_info(data_file_path)

            # 3. EN
            analysis_code = self._generate_analysis_code(
                question, data_file_path, dataset_metadata
            )

            if not analysis_code:
                return {
                    "success": False,
                    "error": "Failed to generate analysis code.",
                    "answer": "The analysis code could not be generated for this request.",
                }

            # 4. EN
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

            # 5. EN
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
                # EN,EN
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
        EN

        Args:
            file_path: EN

        Returns:
            EN
        """
        try:
            # EN
            if file_path.endswith(".csv"):
                df = None
                for enc in ("utf-8", "utf-8-sig", "latin-1"):
                    try:
                        df = pd.read_csv(file_path, encoding=enc)
                        break
                    except UnicodeDecodeError:
                        continue
                if df is None:
                    return {"error": "Unable to decode CSV with any supported encoding (utf-8, utf-8-sig, latin-1)."}
            elif file_path.endswith((".xlsx", ".xls")):
                df = pd.read_excel(file_path)
            else:
                return {"error": "Unsupported data file format."}

            # EN
            columns_info = []
            for col in df.columns:
                col_type = str(df[col].dtype)
                col_info = {
                    "name": col,
                    "type": col_type,
                    "non_null_count": int(df[col].count()),
                    "null_count": int(df[col].isnull().sum()),
                }

                # EN
                if df[col].dtype in ["int64", "float64"]:
                    col_info.update(
                        {
                            "mean": float(df[col].mean()) if not df[col].empty else 0,
                            "min": float(df[col].min()) if not df[col].empty else 0,
                            "max": float(df[col].max()) if not df[col].empty else 0,
                            "std": float(df[col].std()) if not df[col].empty else 0,
                        }
                    )

                # EN
                elif df[col].dtype == "object":
                    unique_count = df[col].nunique()
                    if unique_count <= 20:  # EN
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
            logger.error(f"EN: {e}")
            return {"error": str(e)}

    def _generate_analysis_code(
        self, question: str, data_file_path: str, dataset_metadata: Dict[str, Any]
    ) -> Optional[str]:
        """
        ENLLMEN

        Args:
            question: EN
            data_file_path: EN
            dataset_metadata: EN

        Returns:
            ENPythonEN
        """
        # ENPrompt
        prompt = self._build_code_generation_prompt(
            question, data_file_path, dataset_metadata
        )

        try:
            # ENLLMEN
            llm_response = self.llm_client.generate(
                prompt, temperature=0.1, max_tokens=1000  # EN
            )

            # EN
            code = self._extract_code_from_response(llm_response)

            return code

        except Exception as e:
            logger.error(f"EN: {e}")
            # EN:EN
            return self._generate_template_code(
                question, data_file_path, dataset_metadata
            )

    def _build_code_generation_prompt(
        self, question: str, data_file_path: str, dataset_metadata: Dict[str, Any]
    ) -> str:
        """ENPrompt"""
        columns_desc = "\n".join(
            [
                f"  - {col['name']} ({col['type']})"
                for col in dataset_metadata.get("columns_info", [])
            ]
        )

        return f"""EN.ENPythonEN.

**EN**:
- EN: {os.path.basename(data_file_path)}
- EN: {dataset_metadata.get('rows', 'unknown')}
- EN: {dataset_metadata.get('columns', 'unknown')}
- EN:
{columns_desc}

**EN**: {question}

**EN**:
1. ENpandasEN: pd.read_csv() EN pd.read_excel()
2. EN /workspace/{os.path.basename(data_file_path)}
3. EN,EN print() EN
4. EN,EN
5. EN,EN /workspace/ EN
6. EN
7. EN30EN

**EN**:
```python
import pandas as pd
import numpy as np

# EN
df = pd.read_csv('/workspace/{os.path.basename(data_file_path)}')

# EN
# ... your analysis code ...

# EN
print("EN: ...")
```

ENPythonEN,EN.EN```python EN ```EN."""

    def _extract_code_from_response(self, response: str) -> Optional[str]:
        """ENLLMEN"""
        # EN
        code_pattern = r"```python\n(.*?)```"
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
        """EN"""
        filename = os.path.basename(data_file_path)

        # EN
        question_lower = question.lower()

        # EN
        if any(keyword in question_lower for keyword in ["average", "EN", "mean"]):
            return self._template_average(filename, dataset_metadata, question)

        elif any(
            keyword in question_lower for keyword in ["max", "EN", "EN", "highest"]
        ):
            return self._template_max(filename, dataset_metadata)

        elif any(
            keyword in question_lower for keyword in ["min", "EN", "EN", "lowest"]
        ):
            return self._template_min(filename, dataset_metadata)

        elif any(
            keyword in question_lower for keyword in ["count", "EN", "EN", "how many"]
        ):
            return self._template_count(filename, dataset_metadata)

        elif any(
            keyword in question_lower for keyword in ["percentage", "EN", "EN", "%"]
        ):
            return self._template_percentage(filename, dataset_metadata)

        else:
            # EN:EN
            return self._template_describe(filename, dataset_metadata)

    def _template_describe(self, filename: str, metadata: Dict) -> str:
        """EN"""
        return f"""import pandas as pd

df = pd.read_csv('/workspace/{filename}')
print("EN:")
print(f"EN: {{len(df)}}")
print(f"EN: {{len(df.columns)}}")
print("\\nEN:")
print(df.dtypes)
print("\\nEN:")
print(df.describe())
"""

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
        priority_keywords = ["cost", "price", "amount", "total", "value", "salary", "revenue"]
        for keyword in priority_keywords:
            for col in numeric_cols:
                if keyword in col.lower():
                    return col
        return numeric_cols[0]

    def _template_average(self, filename: str, metadata: Dict, question: str = "") -> str:
        """EN"""
        numeric_cols = [
            col["name"] for col in metadata.get("columns_info", []) if "mean" in col
        ]

        if numeric_cols:
            target_col = self._pick_relevant_column(numeric_cols, question)
            return f"""import pandas as pd

df = pd.read_csv('/workspace/{filename}')
avg_value = df['{target_col}'].mean()
print(f"'{target_col}'EN: {{avg_value:.2f}}")
"""
        else:
            return self._template_describe(filename, metadata)

    def _template_max(self, filename: str, metadata: Dict, question: str = "") -> str:
        """EN"""
        numeric_cols = [
            col["name"] for col in metadata.get("columns_info", []) if "max" in col
        ]

        if numeric_cols:
            target_col = self._pick_relevant_column(numeric_cols, question)
            return f"""import pandas as pd

df = pd.read_csv('/workspace/{filename}')
max_value = df['{target_col}'].max()
max_row = df[df['{target_col}'] == max_value].iloc[0]
print(f"EN'{target_col}': {{max_value}}")
print(f"EN: {{max_row.to_dict()}}")
"""
        else:
            return self._template_describe(filename, metadata)

    def _template_min(self, filename: str, metadata: Dict, question: str = "") -> str:
        """EN"""
        numeric_cols = [
            col["name"] for col in metadata.get("columns_info", []) if "min" in col
        ]

        if numeric_cols:
            target_col = self._pick_relevant_column(numeric_cols, question)
            return f"""import pandas as pd

df = pd.read_csv('/workspace/{filename}')
min_value = df['{target_col}'].min()
min_row = df[df['{target_col}'] == min_value].iloc[0]
print(f"EN'{target_col}': {{min_value}}")
print(f"EN: {{min_row.to_dict()}}")
"""
        else:
            return self._template_describe(filename, metadata)

    def _template_count(self, filename: str, metadata: Dict) -> str:
        """EN"""
        categorical_cols = [
            col["name"]
            for col in metadata.get("columns_info", [])
            if col.get("unique_values", 0) > 0 and col.get("unique_values", 0) < 100
        ]

        if categorical_cols:
            target_col = categorical_cols[0]
            return f"""import pandas as pd

df = pd.read_csv('/workspace/{filename}')
value_counts = df['{target_col}'].value_counts()
print(f"'{target_col}'EN:")
print(value_counts)
"""
        else:
            return f"""import pandas as pd

df = pd.read_csv('/workspace/{filename}')
print(f"EN: {{len(df)}}")
"""

    def _template_percentage(self, filename: str, metadata: Dict) -> str:
        """EN"""
        categorical_cols = [
            col["name"]
            for col in metadata.get("columns_info", [])
            if col.get("unique_values", 0) > 0 and col.get("unique_values", 0) < 50
        ]

        if categorical_cols:
            target_col = categorical_cols[0]
            return f"""import pandas as pd

df = pd.read_csv('/workspace/{filename}')
value_counts = df['{target_col}'].value_counts()
percentages = (value_counts / len(df) * 100).round(2)
print(f"'{target_col}'EN:")
for val, pct in percentages.items():
    print(f"  {{val}}: {{pct}}%")
"""
        else:
            return self._template_describe(filename, metadata)

    def _parse_execution_output(
        self, stdout: str, question: str, dataset_metadata: Dict[str, Any]
    ) -> str:
        """
        EN

        Args:
            stdout: EN
            question: EN
            dataset_metadata: EN

        Returns:
            EN
        """
        if not stdout.strip():
            return "EN,EN."

        # EN
        cleaned_output = stdout.strip()

        # EN,EN
        if cleaned_output.endswith((".", ".", "!", "!")):
            return cleaned_output

        # EN,EN
        return f"EN:\n{cleaned_output}"

    def _generate_fallback_answer(
        self, question: str, dataset_metadata: Dict[str, Any], error_message: str
    ) -> str:
        """
        EN(EN)

        Args:
            question: EN
            dataset_metadata: EN
            error_message: EN

        Returns:
            EN
        """
        # EN
        question_lower = question.lower()

        # EN
        if (
            "feature" in question_lower
            or "column" in question_lower
            or "EN" in question_lower
            or "EN" in question_lower
        ):
            columns = dataset_metadata.get("column_names", [])
            if columns:
                return f"EN: {', '.join(columns)}"

        # EN
        if (
            "how many" in question_lower
            or "EN" in question_lower
            or "row" in question_lower
            or "EN" in question_lower
        ):
            rows = dataset_metadata.get("rows")
            if rows:
                return f"EN {rows} EN."

        # EN
        return f"EN,EN.EN {dataset_metadata.get('rows', 'unknown')} EN {dataset_metadata.get('columns', 'unknown')} EN."


# Lazy singleton — avoids import-time side effects (LLM client, Docker init).
_data_analysis_agent: Optional[DataAnalysisAgent] = None


def get_data_analysis_agent() -> DataAnalysisAgent:
    global _data_analysis_agent
    if _data_analysis_agent is None:
        _data_analysis_agent = DataAnalysisAgent()
    return _data_analysis_agent


# Keep backward-compatible attribute name but as None — callers should use
# get_data_analysis_agent() instead.
data_analysis_agent = None
