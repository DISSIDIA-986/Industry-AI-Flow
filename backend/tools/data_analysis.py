"""Data Analysis Tools - Automated EDA and data analysis functionality"""

import json
import logging
import math
import re
from pathlib import Path
from typing import Annotated, Any, Dict, List, Optional

from langchain_core.tools import tool

from backend.tools.dataset_metadata import (
    build_metadata_audit_report,
    build_prompt_metadata,
    extract_dataset_metadata,
)

logger = logging.getLogger(__name__)

_FORBIDDEN_CODE_PATTERNS = (
    "locals(",
    "globals(",
    "eval(",
    "exec(",
    "__import__(",
    "subprocess.",
    "os.system(",
    "open(",
    ".apply(",
    ".agg(",
    ".transform(",
    ".map(",
    ".query(",
    ".eval(",
    "lambda ",
)


def _json_safe(value: Any) -> Any:
    """Convert parsed values into JSON-safe Python primitives."""
    if isinstance(value, dict):
        return {str(k): _json_safe(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_json_safe(item) for item in value]
    if isinstance(value, tuple):
        return [_json_safe(item) for item in value]
    if isinstance(value, float):
        if not math.isfinite(value):
            return None
        return value
    if isinstance(value, (int, str, bool)) or value is None:
        return value
    if hasattr(value, "item"):
        try:
            return _json_safe(value.item())
        except Exception:
            return str(value)
    return str(value)


def _extract_python_code(raw_response: str) -> str:
    text = str(raw_response or "").strip()
    if not text:
        return ""
    fence_match = re.search(r"```(?:python)?\s*([\s\S]*?)```", text, re.IGNORECASE)
    if fence_match:
        return fence_match.group(1).strip()
    return text


def _is_generated_code_allowed(code: str) -> bool:
    lowered = code.lower()
    if "import pandas as pd" not in lowered:
        return False
    if (
        "pd.read_" not in lowered
        and "read_csv(" not in lowered
        and "read_excel(" not in lowered
    ):
        return False
    return not any(pattern in lowered for pattern in _FORBIDDEN_CODE_PATTERNS)


def _resolve_container_data_path(data_file: str) -> str:
    """Map host file path to the mounted path visible in the sandbox container."""
    raw_path = str(data_file or "").strip()
    if not raw_path:
        return raw_path
    if raw_path.startswith("/workspace/"):
        return raw_path
    return f"/workspace/{Path(raw_path).name}"


def _generate_analysis_code_with_llm(
    data_file: str,
    analysis_type: str,
    target_column: Optional[str] = None,
    columns: Optional[List[str]] = None,
    instruction: Optional[str] = None,
    dataset_metadata: Optional[Dict[str, Any]] = None,
) -> tuple[str, str, str]:
    fallback_code = _generate_analysis_code(
        data_file=data_file,
        analysis_type=analysis_type,
        target_column=target_column,
        columns=columns,
    )

    container_data_file = _resolve_container_data_path(data_file)
    column_hint = (
        ", ".join(columns or []) if columns else "auto-detect suitable columns"
    )
    user_instruction = instruction or f"Run a concise {analysis_type} analysis."
    metadata_payload = build_prompt_metadata(dataset_metadata or {})

    prompt = f"""
Generate executable Python code for data analysis.

Task:
- analysis_type: {analysis_type}
- instruction: {user_instruction}
- target_column: {target_column or "none"}
- preferred_columns: {column_hint}
- dataset_path: {container_data_file}
- dataset_metadata_json: {metadata_payload}

Hard requirements:
1. Use pandas as pd, numpy as np, matplotlib.pyplot as plt, seaborn as sns, and json.
2. You only receive dataset metadata above (not raw rows); infer structure from metadata_json.
3. Read the dataset from "{container_data_file}" when the generated code runs in sandbox.
4. Keep runtime short; limit heavy loops and avoid expensive operations.
5. Print key findings.
6. Build a dict variable named analysis_summary.
7. Print exactly one final marker line:
   ANALYSIS_SUMMARY_JSON=<json>
   where <json> is json.dumps(analysis_summary, ensure_ascii=False)
8. Do NOT use these APIs: locals(), globals(), eval(), exec(), __import__(), open(), subprocess, os.system.
9. Do NOT use dataframe/series methods blocked by sandbox policy: .apply(), .agg(), .transform(), .map(), .query(), .eval().
10. Ensure analysis_summary values are JSON-serializable Python types. Cast numpy/pandas scalars with int()/float()/str() as needed.
11. Always define analysis_summary before printing it.
12. Return Python code only, no explanations and no markdown fences.
"""

    try:
        from backend.services.llm_integration.llm_client import get_llm_client

        client = get_llm_client()
        raw_response = client.generate(
            prompt,
            temperature=0.1,
            max_tokens=1200,
            top_p=0.9,
        )
        generated_code = _extract_python_code(raw_response)
        if not generated_code:
            raise ValueError("empty_code")
        if not _is_generated_code_allowed(generated_code):
            raise ValueError("generated_code_failed_safety_or_quality_gate")
        return generated_code, "llm", ""
    except Exception as exc:
        logger.warning("LLM code generation failed; using template fallback: %s", exc)
        return fallback_code, "template_fallback", str(exc)


@tool
def data_analysis_tool(
    data_file: Annotated[str, "Data file path"],
    analysis_type: Annotated[
        str, "Analysis type: 'eda', 'correlation', 'summary', 'distribution'"
    ] = "eda",
    target_column: Annotated[
        Optional[str], "Target column name (for supervised learning analysis)"
    ] = None,
    columns: Annotated[Optional[List[str]], "List of column names to analyze"] = None,
    instruction: Annotated[
        Optional[str], "Natural-language analysis instruction"
    ] = None,
) -> Dict[str, Any]:
    """
    Data Analysis Tool - Automated Exploratory Data Analysis (EDA)

    This tool provides comprehensive data analysis capabilities, including:
    1. Basic statistics: Data overview, descriptive statistics
    2. Missing values analysis: Missing value detection and handling suggestions
    3. Correlation analysis: Feature correlation matrix and heatmap
    4. Distribution analysis: Data distribution features and outlier detection
    5. Data quality: Data type, duplicate, and outlier checks

    Supported analysis types:
    - 'eda': Full exploratory data analysis
    - 'correlation': Correlation analysis
    - 'summary': Basic statistical summary
    - 'distribution': Distribution analysis

    Args:
        data_file: Data file path (CSV, Excel, etc.)
        analysis_type: Analysis type
        target_column: Target column name (optional)
        columns: List of column names to analyze (optional)

    Returns:
        Analysis result dictionary containing:
        - success: Whether the analysis succeeded
        - analysis_type: The analysis type performed
        - data_info: Basic data information
        - statistics: Statistical results
        - insights: Data insights
        - recommendations: Data processing suggestions
        - visualizations: Generated visualization code
        - error: Error message (if failed)

    Example:
        >>> result = data_analysis_tool.invoke({
        ...     "data_file": "/path/to/data.csv",
        ...     "analysis_type": "eda",
        ...     "target_column": "price"
        ... })
        >>> print(f"Analysis succeeded: {result['success']}")
        >>> print(f"Row count: {result['data_info']['rows']}")
    """

    # Try LLM dynamic code generation first; fall back to template on failure.
    dataset_metadata = extract_dataset_metadata(data_file)
    metadata_report = build_metadata_audit_report(dataset_metadata)
    llm_input_policy = {
        "mode": "metadata_only",
        "raw_data_sent_to_llm": False,
        "metadata_status": metadata_report.get("status"),
        "redaction_mode": metadata_report.get("redaction_mode"),
    }
    analysis_code, generation_mode, generation_error = _generate_analysis_code_with_llm(
        data_file=data_file,
        analysis_type=analysis_type,
        target_column=target_column,
        columns=columns,
        instruction=instruction,
        dataset_metadata=dataset_metadata,
    )

    # Run analysis via code execution tool
    from backend.tools.code_execution import code_execution_tool

    try:
        execution_mode = generation_mode
        execution_reason = generation_error
        result = code_execution_tool.invoke(
            {"code": analysis_code, "data_files": [data_file] if data_file else None}
        )
        if not result.get("success") and generation_mode == "llm":
            runtime_error = str(result.get("error") or "").strip()
            fallback_code = _generate_analysis_code(
                data_file=data_file,
                analysis_type=analysis_type,
                target_column=target_column,
                columns=columns,
            )
            fallback_result = code_execution_tool.invoke(
                {
                    "code": fallback_code,
                    "data_files": [data_file] if data_file else None,
                }
            )
            if fallback_result.get("success"):
                analysis_code = fallback_code
                result = fallback_result
                execution_mode = "template_fallback_runtime"
                execution_reason = runtime_error or generation_error
            else:
                fallback_error = str(fallback_result.get("error") or "").strip()
                if fallback_error:
                    result["error"] = (
                        f"{runtime_error or 'Runtime error'}; "
                        f"template_retry_error={fallback_error}"
                    )

        if result["success"]:
            # Parse analysis results
            analysis_result = _parse_analysis_output(result["stdout"])
            answer = _build_analysis_answer(
                analysis_type=analysis_type,
                parsed_result=analysis_result,
                raw_output=result.get("stdout", ""),
            )
            analysis_result.update(
                {
                    "success": True,
                    "answer": answer,
                    "analysis_type": analysis_type,
                    "visualizations": result.get("visualizations", []),
                    "code_generation": {
                        "mode": execution_mode,
                        "fallback_reason": execution_reason or None,
                    },
                    "generated_code_preview": analysis_code[:1200],
                    "metadata_extraction": metadata_report,
                    "llm_input_policy": llm_input_policy,
                }
            )

            logger.info(f"Data analysis completed, type: {analysis_type}")
            return analysis_result
        else:
            return {
                "success": False,
                "error": f"Data analysis execution failed: {result.get('error', 'Unknown error')}",
                "analysis_type": analysis_type,
                "stdout": result.get("stdout", ""),
                "stderr": result.get("stderr", ""),
                "code_generation": {
                    "mode": execution_mode,
                    "fallback_reason": execution_reason or None,
                },
                "generated_code_preview": analysis_code[:1200],
                "metadata_extraction": metadata_report,
                "llm_input_policy": llm_input_policy,
            }

    except Exception as e:
        logger.error(f"Data analysis tool error: {e}")
        return {
            "success": False,
            "error": f"Tool error: {str(e)}",
            "analysis_type": analysis_type,
            "metadata_extraction": metadata_report,
            "llm_input_policy": llm_input_policy,
        }


@tool
def data_preprocessing_tool(
    data_file: Annotated[str, "Data file path"],
    operations: Annotated[
        List[str],
        "Preprocessing operations: 'clean_missing', 'remove_duplicates', 'normalize', 'encode_categorical'",
    ] = ["clean_missing"],
    output_format: Annotated[str, "Output format: 'csv', 'excel', 'json'"] = "csv",
) -> Dict[str, Any]:
    """
    Data Preprocessing Tool - Automated data cleaning and preprocessing

    This tool provides common data preprocessing capabilities:
    1. Missing value handling: Deletion, imputation, interpolation
    2. Duplicate handling: Detection and removal of duplicate rows
    3. Data normalization: Numeric feature standardization and normalization
    4. Categorical encoding: Label encoding, one-hot encoding
    5. Outlier handling: Detection and treatment of outliers

    Supported preprocessing operations:
    - 'clean_missing': Missing value handling
    - 'remove_duplicates': Remove duplicate rows
    - 'normalize': Numeric normalization
    - 'encode_categorical': Categorical variable encoding

    Args:
        data_file: Data file path
        operations: List of preprocessing operations
        output_format: Output format

    Returns:
        Preprocessing result dictionary containing:
        - success: Whether the preprocessing succeeded
        - processed_data_info: Processed data information
        - operations_applied: Operations applied
        - data_quality_metrics: Data quality metrics
        - output_file: Output file path
        - preprocessing_summary: Preprocessing summary

    Example:
        >>> result = data_preprocessing_tool.invoke({
        ...     "data_file": "/path/to/data.csv",
        ...     "operations": ["clean_missing", "remove_duplicates"]
        ... })
    """

    # Generate preprocessing code
    preprocessing_code = _generate_preprocessing_code(
        data_file, operations, output_format
    )

    # Run preprocessing via code execution tool
    from backend.tools.code_execution import code_execution_tool

    try:
        result = code_execution_tool.invoke(
            {
                "code": preprocessing_code,
                "data_files": [data_file] if data_file else None,
            }
        )

        if result["success"]:
            # Parse preprocessing results
            preprocessing_result = _parse_preprocessing_output(result["stdout"])
            preprocessing_result.update(
                {
                    "success": True,
                    "operations_applied": operations,
                    "output_format": output_format,
                }
            )

            logger.info(f"Data preprocessing completed, operations: {operations}")
            return preprocessing_result
        else:
            return {
                "success": False,
                "error": f"Data preprocessing failed: {result.get('error', 'Unknown error')}",
                "operations_applied": operations,
                "stdout": result.get("stdout", ""),
                "stderr": result.get("stderr", ""),
            }

    except Exception as e:
        logger.error(f"Data preprocessing tool error: {e}")
        return {
            "success": False,
            "error": f"Tool error: {str(e)}",
            "operations_applied": operations,
        }


def _generate_analysis_code(
    data_file: str,
    analysis_type: str,
    target_column: Optional[str] = None,
    columns: Optional[List[str]] = None,
) -> str:
    """Generate data analysis code"""

    # Determine file read method
    container_data_file = _resolve_container_data_path(data_file)
    if data_file.endswith(".csv"):
        read_code = f"df = pd.read_csv('{container_data_file}')"
    elif data_file.endswith((".xlsx", ".xls")):
        read_code = f"df = pd.read_excel('{container_data_file}')"
    else:
        read_code = f"# Please read data file manually: {container_data_file}"

    base_code = f"""
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import json
import warnings
warnings.filterwarnings('ignore')

# Configure matplotlib defaults for cross-platform rendering
plt.rcParams['font.sans-serif'] = ['DejaVu Sans', 'Arial Unicode MS', 'Liberation Sans']
plt.rcParams['axes.unicode_minus'] = False
print("✓ Matplotlib font settings initialized")

# Read data
{read_code}

print("=== Basic Data Info ===")
print(f"Data Shape: {{df.shape}}")
print(f"Columns: {{list(df.columns)}}")
print(f"Data types:\\n{{df.dtypes}}")

# Select columns for analysis
"""

    if columns:
        base_code += f"""
selected_columns = {columns}
df_analysis = df[selected_columns].copy()
"""
    else:
        base_code += """
df_analysis = df.copy()
"""

    if analysis_type == "eda":
        base_code += """
print("\\n=== Descriptive Statistics ===")
print(df_analysis.describe())

print("\\n=== Missing Values Analysis ===")
missing_info = df_analysis.isnull().sum()
missing_percentage = (missing_info / len(df_analysis)) * 100
missing_df = pd.DataFrame({
    'missing_count': missing_info,
    'missing_percentage': missing_percentage
})
print(missing_df[missing_df['missing_count'] > 0])

print("\\n=== Data Type Analysis ===")
numeric_columns = df_analysis.select_dtypes(include=[np.number]).columns.tolist()
categorical_columns = df_analysis.select_dtypes(include=['object']).columns.tolist()
print(f"Numeric columns: {{numeric_columns}}")
print(f"Categorical columns: {{categorical_columns}}")

# Correlation analysis (numeric columns only)
if len(numeric_columns) > 1:
    print("\\n=== Correlation Analysis ===")
    correlation_matrix = df_analysis[numeric_columns].corr()
    print(correlation_matrix)

    # Generate correlation heatmap
    plt.figure(figsize=(10, 8))
    sns.heatmap(correlation_matrix, annot=True, cmap='coolwarm', center=0)
    plt.title('Correlation Heatmap')
    plt.tight_layout()
    plt.savefig('/workspace/correlation_heatmap.png', dpi=300, bbox_inches='tight')
    plt.close()
    print("Correlation heatmap saved: correlation_heatmap.png")

# Distribution analysis
print("\\n=== Distribution Analysis ===")
for col in numeric_columns[:5]:  # Limit to first 5 numeric columns
    plt.figure(figsize=(12, 4))

    # Histogram
    plt.subplot(1, 2, 1)
    plt.hist(df_analysis[col].dropna(), bins=30, alpha=0.7)
    plt.title(f'{{col}} Distribution Histogram')
    plt.xlabel(col)
    plt.ylabel('Frequency')

    # Box Plot
    plt.subplot(1, 2, 2)
    plt.boxplot(df_analysis[col].dropna())
    plt.title(f'{{col}} Box Plot')
    plt.ylabel(col)

    plt.tight_layout()
    plt.savefig(f'/workspace/{{col}}_distribution.png', dpi=300, bbox_inches='tight')
    plt.close()
    print(f"{{col}} distribution chart saved: {{col}}_distribution.png")

# Categorical variable analysis
for col in categorical_columns[:5]:  # Limit to first 5 categorical columns
    if df_analysis[col].nunique() <= 20:  # Only analyze categorical variables with few unique values
        plt.figure(figsize=(10, 6))
        value_counts = df_analysis[col].value_counts()
        plt.bar(range(len(value_counts)), value_counts.values)
        plt.xticks(range(len(value_counts)), value_counts.index, rotation=45)
        plt.title(f'{{col}} Distribution')
        plt.xlabel(col)
        plt.ylabel('Frequency')
        plt.tight_layout()
        plt.savefig(f'/workspace/{{col}}_barplot.png', dpi=300, bbox_inches='tight')
        plt.close()
        print(f"{{col}} bar chart saved: {{col}}_barplot.png")

print("\\n=== Data Quality Assessment ===")
print(f"Duplicate rows: {{df_analysis.duplicated().sum()}}")
print(f"Fully duplicate rows: {{df_analysis.duplicated().sum()}}")

# Output analysis_summary
analysis_summary = {
    'total_rows': int(len(df_analysis)),
    'total_columns': int(len(df_analysis.columns)),
    'numeric_columns': int(len(numeric_columns)),
    'categorical_columns': int(len(categorical_columns)),
    'missing_values': int(missing_info.sum()),
    'duplicate_rows': int(df_analysis.duplicated().sum())
}

print("\\n=== analysis_summary ===")
print(json.dumps(analysis_summary, indent=2, ensure_ascii=False))
print("ANALYSIS_SUMMARY_JSON=" + json.dumps(analysis_summary, ensure_ascii=False))
"""

    elif analysis_type == "correlation":
        base_code += """
numeric_columns = df_analysis.select_dtypes(include=[np.number]).columns.tolist()
if len(numeric_columns) > 1:
    correlation_matrix = df_analysis[numeric_columns].corr()
    print("Correlation Matrix:")
    print(correlation_matrix)

    # Find highly correlated feature pairs
    high_corr_pairs = []
    for i in range(len(correlation_matrix.columns)):
        for j in range(i+1, len(correlation_matrix.columns)):
            corr_value = correlation_matrix.iloc[i, j]
            if abs(corr_value) > 0.7:  # High correlation threshold
                high_corr_pairs.append({
                    'feature1': correlation_matrix.columns[i],
                    'feature2': correlation_matrix.columns[j],
                    'correlation': corr_value
                })

    print("\\nHighly correlated feature pairs:")
    for pair in high_corr_pairs:
        print(f"{{pair['feature1']}} - {{pair['feature2']}}: {{pair['correlation']:.3f}}")
else:
    print("Not enough numeric columns for correlation analysis")
"""

    elif analysis_type == "summary":
        base_code += """
print("=== Data Summary ===")
print(f"Dataset size: {{df_analysis.shape}}")
print("\\nData types:")
print(df_analysis.dtypes)

print("\\nNumerical Column Statistics:")
numeric_cols = df_analysis.select_dtypes(include=[np.number])
if not numeric_cols.empty:
    print(numeric_cols.describe())

print("\\nCategorical Column Statistics:")
categorical_cols = df_analysis.select_dtypes(include=['object'])
if not categorical_cols.empty:
    for col in categorical_cols.columns:
        print(f"\\n{{col}}:")
        print(f"  Unique values: {{df_analysis[col].nunique()}}")
        print(f"  Most frequent value: {{df_analysis[col].mode().iloc[0] if not df_analysis[col].mode().empty else 'N/A'}}")
        print(f"  Missing value count: {{df_analysis[col].isnull().sum()}}")
"""

    elif analysis_type == "distribution":
        base_code += """
numeric_columns = df_analysis.select_dtypes(include=[np.number]).columns.tolist()

print("=== Distribution Analysis ===")
for col in numeric_columns:
    data = df_analysis[col].dropna()

    # Basic statistics
    print(f"\\n{{col}} distribution statistics:")
    print(f"  Mean: {{data.mean():.3f}}")
    print(f"  Median: {{data.median():.3f}}")
    print(f"  Std Dev: {{data.std():.3f}}")
    print(f"  Skewness: {{data.skew():.3f}}")
    print(f"  Kurtosis: {{data.kurtosis():.3f}}")

    # Outlier detection (IQR method)
    Q1 = data.quantile(0.25)
    Q3 = data.quantile(0.75)
    IQR = Q3 - Q1
    lower_bound = Q1 - 1.5 * IQR
    upper_bound = Q3 + 1.5 * IQR
    outliers = data[(data < lower_bound) | (data > upper_bound)]

    print(f"  Outlier count: {{len(outliers)}} ({{len(outliers)/len(data)*100:.1f}}%)")

    # Generate distribution chart
    plt.figure(figsize=(15, 5))

    # Histogram
    plt.subplot(1, 3, 1)
    plt.hist(data, bins=30, alpha=0.7, density=True)
    plt.title(f'{{col}} Histogram')
    plt.xlabel(col)
    plt.ylabel('Density')

    # Box Plot
    plt.subplot(1, 3, 2)
    plt.boxplot(data)
    plt.title(f'{{col}} Box Plot')
    plt.ylabel(col)

    # Q-Q Plot
    plt.subplot(1, 3, 3)
    from scipy import stats
    stats.probplot(data, dist="norm", plot=plt)
    plt.title(f'{{col}} Q-Q Plot')

    plt.tight_layout()
    plt.savefig(f'/workspace/{{col}}_distribution_analysis.png', dpi=300, bbox_inches='tight')
    plt.close()
    print(f"  Distribution chart saved: {{col}}_distribution_analysis.png")
"""

    return base_code


def _generate_preprocessing_code(
    data_file: str, operations: List[str], output_format: str
) -> str:
    """Generate data preprocessing code"""

    # Determine file read method
    container_data_file = _resolve_container_data_path(data_file)
    if data_file.endswith(".csv"):
        read_code = f"df = pd.read_csv('{container_data_file}')"
    elif data_file.endswith((".xlsx", ".xls")):
        read_code = f"df = pd.read_excel('{container_data_file}')"
    else:
        read_code = f"# Please read data file manually: {container_data_file}"

    base_code = f"""
import pandas as pd
import numpy as np
from sklearn.preprocessing import StandardScaler, LabelEncoder, MinMaxScaler
import json
import warnings
warnings.filterwarnings('ignore')

# Read original data
{read_code}
original_shape = df.shape
print(f"Original data shape: {{original_shape}}")

df_processed = df.copy()
preprocessing_log = []

"""

    if "clean_missing" in operations:
        base_code += """
# Missing value handling
print("\\n=== Missing Value Handling ===")
missing_info = df_processed.isnull().sum()
print("Missing value statistics:")
print(missing_info[missing_info > 0])

# Numeric column missing values filled with median
numeric_columns = df_processed.select_dtypes(include=[np.number]).columns
for col in numeric_columns:
    if df_processed[col].isnull().sum() > 0:
        median_val = df_processed[col].median()
        df_processed[col].fillna(median_val, inplace=True)
        preprocessing_log.append(f"Numeric column {{col}} missing values filled with median {{median_val}}")

# Categorical column missing values filled with mode
categorical_columns = df_processed.select_dtypes(include=['object']).columns
for col in categorical_columns:
    if df_processed[col].isnull().sum() > 0:
        mode_val = df_processed[col].mode().iloc[0] if not df_processed[col].mode().empty else 'Unknown'
        df_processed[col].fillna(mode_val, inplace=True)
        preprocessing_log.append(f"Categorical column {{col}} missing values filled with mode {{mode_val}}")

print("Missing value processing complete")
"""

    if "remove_duplicates" in operations:
        base_code += """
# Duplicate handling
print("\\n=== Duplicate Handling ===")
duplicate_count = df_processed.duplicated().sum()
print(f"Duplicate rows: {{duplicate_count}}")

if duplicate_count > 0:
    df_processed.drop_duplicates(inplace=True)
    preprocessing_log.append(f"Removed {{duplicate_count}} duplicate rows")

print("Duplicate processing complete")
"""

    if "normalize" in operations:
        base_code += """
# Numeric normalization
print("\\n=== Numeric Normalization ===")
numeric_columns = df_processed.select_dtypes(include=[np.number]).columns.tolist()

if numeric_columns:
    scaler = StandardScaler()
    df_processed[numeric_columns] = scaler.fit_transform(df_processed[numeric_columns])
    preprocessing_log.append(f"Standardized {{len(numeric_columns)}} numeric columns")
    print(f"Standardized columns: {{numeric_columns}}")
else:
    print("No numeric columns to standardize")
"""

    if "encode_categorical" in operations:
        base_code += """
# Categorical variable encoding
print("\\n=== Categorical Variable Encoding ===")
categorical_columns = df_processed.select_dtypes(include=['object']).columns.tolist()

for col in categorical_columns:
    if df_processed[col].nunique() <= 10:  # One-hot encode categorical variables with few unique values
        dummies = pd.get_dummies(df_processed[col], prefix=col)
        df_processed = pd.concat([df_processed.drop(col, axis=1), dummies], axis=1)
        preprocessing_log.append(f"Categorical column {{col}} one-hot encoded")
    else:  # Label encode categorical variables with many unique values
        le = LabelEncoder()
        df_processed[col] = le.fit_transform(df_processed[col])
        preprocessing_log.append(f"Categorical column {{col}} label encoded")

print("Categorical variable encoding complete")
"""

    # Output processed data
    output_extension = output_format.lower()
    if output_extension == "csv":
        save_code = "output_file = '/workspace/processed_data.csv'\ndf_processed.to_csv(output_file, index=False)"
    elif output_extension in ["excel", "xlsx"]:
        save_code = "output_file = '/workspace/processed_data.xlsx'\ndf_processed.to_excel(output_file, index=False)"
    elif output_extension == "json":
        save_code = "output_file = '/workspace/processed_data.json'\ndf_processed.to_json(output_file, orient='records', indent=2)"
    else:
        save_code = "output_file = '/workspace/processed_data.csv'\ndf_processed.to_csv(output_file, index=False)"

    base_code += f"""
# Save processed data
{save_code}

# Generate preprocessing report
final_shape = df_processed.shape
preprocessing_summary = {{
    'original_shape': original_shape,
    'final_shape': final_shape,
    'rows_removed': original_shape[0] - final_shape[0],
    'columns_added': final_shape[1] - original_shape[1],
    'preprocessing_steps': preprocessing_log
}}

print("\\n=== Preprocessing Summary ===")
print(f"Original shape: {{original_shape}}")
print(f"Processed shape: {{final_shape}}")
print(f"Rows removed: {{original_shape[0] - final_shape[0]}}")
print(f"Columns added: {{final_shape[1] - original_shape[1]}}")
print(f"Output file: {{output_file}}")

print("\\nPreprocessing steps:")
for step in preprocessing_log:
    print(f"  - {{step}}")

print("\\npreprocessing_summaryJSON:")
print(json.dumps(preprocessing_summary, indent=2, ensure_ascii=False))
"""

    return base_code


def _parse_analysis_output(stdout: str) -> Dict[str, Any]:
    """Parse analysis output"""
    try:
        lines = stdout.split("\n")
        summary: Dict[str, Any] = {}

        marker = "ANALYSIS_SUMMARY_JSON="
        marker_line = next(
            (line for line in lines if line.strip().startswith(marker)),
            None,
        )
        if marker_line:
            raw_json = marker_line.split(marker, 1)[1].strip()
            try:
                parsed = json.loads(raw_json)
                if isinstance(parsed, dict):
                    summary = _json_safe(parsed)
            except Exception:
                summary = {}

        if not summary:
            json_start = None
            json_end = None
            for i, line in enumerate(lines):
                if "analysis_summary" in line or "preprocessing_summary" in line:
                    for j in range(i, len(lines)):
                        if lines[j].strip().startswith("{"):
                            json_start = j
                            break
                    for j in range(json_start or i, len(lines)):
                        if lines[j].strip().endswith("}"):
                            json_end = j
                            break
                    break

            if json_start is not None and json_end is not None:
                json_str = "\n".join(lines[json_start : json_end + 1]).strip()
                try:
                    parsed = json.loads(json_str)
                    if isinstance(parsed, dict):
                        summary = _json_safe(parsed)
                except Exception:
                    summary = {}

        return {
            "data_info": {
                "rows": summary.get("total_rows", 0),
                "columns": summary.get("total_columns", 0),
                "numeric_columns": summary.get("numeric_columns", 0),
                "categorical_columns": summary.get("categorical_columns", 0),
            },
            "statistics": summary,
            "insights": [],
            "recommendations": [],
            "raw_output": stdout,
        }

    except Exception as e:
        logger.warning(f"Parse analysis output failed: {e}")
        return {
            "data_info": {},
            "statistics": {},
            "insights": [],
            "recommendations": [],
            "raw_output": stdout,
        }


def _build_analysis_answer(
    *,
    analysis_type: str,
    parsed_result: Dict[str, Any],
    raw_output: str,
) -> str:
    """Build a concise textual answer for API callers."""
    info = parsed_result.get("data_info") or {}
    rows = info.get("rows")
    cols = info.get("columns")
    numeric_cols = info.get("numeric_columns")
    categorical_cols = info.get("categorical_columns")

    if isinstance(rows, int) and isinstance(cols, int) and (rows > 0 or cols > 0):
        return (
            f"Analysis complete ({analysis_type}). Dataset has {rows} rows, {cols} columns, "
            f"with {numeric_cols or 0} numerical columns and {categorical_cols or 0} categorical columns."
        )

    condensed_lines = [line.strip() for line in raw_output.splitlines() if line.strip()]
    if condensed_lines:
        return condensed_lines[0][:240]
    return "Analysis complete."


def _parse_preprocessing_output(stdout: str) -> Dict[str, Any]:
    """Parse preprocessing output"""
    try:
        # Try to extract preprocessing summary from output
        lines = stdout.split("\n")
        json_start = None
        json_end = None

        for i, line in enumerate(lines):
            if "preprocessing_summaryJSON:" in line:
                # Next line should be JSON
                if i + 1 < len(lines):
                    json_str = lines[i + 1]
                    if json_str.strip().startswith("{"):
                        summary = eval(json_str)
                        return {
                            "processed_data_info": {
                                "original_shape": summary.get("original_shape", [0, 0]),
                                "final_shape": summary.get("final_shape", [0, 0]),
                                "rows_removed": summary.get("rows_removed", 0),
                                "columns_added": summary.get("columns_added", 0),
                            },
                            "preprocessing_summary": summary,
                            "raw_output": stdout,
                        }

        return {
            "processed_data_info": {},
            "preprocessing_summary": {},
            "raw_output": stdout,
        }

    except Exception as e:
        logger.warning(f"Parse preprocessing output failed: {e}")
        return {
            "processed_data_info": {},
            "preprocessing_summary": {},
            "raw_output": stdout,
        }
