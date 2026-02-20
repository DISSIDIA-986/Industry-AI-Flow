"""数据分析工具 - 自动化 EDA 和数据分析功能"""

import logging
from pathlib import Path
from typing import Annotated, Any, Dict, List, Optional

from langchain_core.tools import tool

logger = logging.getLogger(__name__)


def _resolve_container_data_path(data_file: str) -> str:
    """Map host file path to the mounted path visible in the sandbox container."""
    raw_path = str(data_file or "").strip()
    if not raw_path:
        return raw_path
    if raw_path.startswith("/workspace/"):
        return raw_path
    return f"/workspace/{Path(raw_path).name}"


@tool
def data_analysis_tool(
    data_file: Annotated[str, "数据文件路径"],
    analysis_type: Annotated[
        str, "分析类型：'eda', 'correlation', 'summary', 'distribution'"
    ] = "eda",
    target_column: Annotated[Optional[str], "目标列名（用于监督学习分析）"] = None,
    columns: Annotated[Optional[List[str]], "要分析的列名列表"] = None,
) -> Dict[str, Any]:
    """
    数据分析工具 - 自动化探索性数据分析（EDA）

    这个工具提供全面的数据分析功能，包括：
    1. 基础统计：数据概览、描述性统计
    2. 缺失值分析：缺失值检测和处理建议
    3. 相关性分析：特征间相关性矩阵和热力图
    4. 分布分析：数据分布特征和异常值检测
    5. 数据质量：数据类型、重复值、异常值检查

    支持的分析类型：
    - 'eda': 完整的探索性数据分析
    - 'correlation': 相关性分析
    - 'summary': 基础统计摘要
    - 'distribution': 分布分析

    Args:
        data_file: 数据文件路径（CSV、Excel等）
        analysis_type: 分析类型
        target_column: 目标列名（可选）
        columns: 要分析的列名列表（可选）

    Returns:
        分析结果字典，包含：
        - success: 是否成功
        - analysis_type: 执行的分析类型
        - data_info: 数据基本信息
        - statistics: 统计结果
        - insights: 数据洞察
        - recommendations: 数据处理建议
        - visualizations: 生成的可视化代码
        - error: 错误信息（如果失败）

    Example:
        >>> result = data_analysis_tool.invoke({
        ...     "data_file": "/path/to/data.csv",
        ...     "analysis_type": "eda",
        ...     "target_column": "price"
        ... })
        >>> print(f"分析成功: {result['success']}")
        >>> print(f"数据行数: {result['data_info']['rows']}")
    """

    # 生成分析代码
    analysis_code = _generate_analysis_code(
        data_file, analysis_type, target_column, columns
    )

    # 使用代码执行工具运行分析
    from backend.tools.code_execution import code_execution_tool

    try:
        result = code_execution_tool.invoke(
            {"code": analysis_code, "data_files": [data_file] if data_file else None}
        )

        if result["success"]:
            # 解析分析结果
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
            }

    except Exception as e:
        logger.error(f"Data analysis tool error: {e}")
        return {
            "success": False,
            "error": f"Tool error: {str(e)}",
            "analysis_type": analysis_type,
        }


@tool
def data_preprocessing_tool(
    data_file: Annotated[str, "数据文件路径"],
    operations: Annotated[
        List[str],
        "预处理操作列表：'clean_missing', 'remove_duplicates', 'normalize', 'encode_categorical'",
    ] = ["clean_missing"],
    output_format: Annotated[str, "输出格式：'csv', 'excel', 'json'"] = "csv",
) -> Dict[str, Any]:
    """
    数据预处理工具 - 自动化数据清洗和预处理

    这个工具提供常见的数据预处理功能：
    1. 缺失值处理：删除、填充、插值
    2. 重复值处理：检测和删除重复行
    3. 数据标准化：数值特征标准化和归一化
    4. 分类编码：标签编码、独热编码
    5. 异常值处理：检测和处理异常值

    支持的预处理操作：
    - 'clean_missing': 缺失值处理
    - 'remove_duplicates': 删除重复值
    - 'normalize': 数值标准化
    - 'encode_categorical': 分类变量编码

    Args:
        data_file: 数据文件路径
        operations: 预处理操作列表
        output_format: 输出格式

    Returns:
        预处理结果字典，包含：
        - success: 是否成功
        - processed_data_info: 处理后数据信息
        - operations_applied: 应用的操作
        - data_quality_metrics: 数据质量指标
        - output_file: 输出文件路径
        - preprocessing_summary: 预处理摘要

    Example:
        >>> result = data_preprocessing_tool.invoke({
        ...     "data_file": "/path/to/data.csv",
        ...     "operations": ["clean_missing", "remove_duplicates"]
        ... })
    """

    # 生成预处理代码
    preprocessing_code = _generate_preprocessing_code(
        data_file, operations, output_format
    )

    # 使用代码执行工具运行预处理
    from backend.tools.code_execution import code_execution_tool

    try:
        result = code_execution_tool.invoke(
            {
                "code": preprocessing_code,
                "data_files": [data_file] if data_file else None,
            }
        )

        if result["success"]:
            # 解析预处理结果
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
    """生成数据分析代码"""

    # 确定文件读取方式
    container_data_file = _resolve_container_data_path(data_file)
    if data_file.endswith(".csv"):
        read_code = f"df = pd.read_csv('{container_data_file}')"
    elif data_file.endswith((".xlsx", ".xls")):
        read_code = f"df = pd.read_excel('{container_data_file}')"
    else:
        read_code = f"# 请手动读取数据文件: {container_data_file}"

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

# 读取数据
{read_code}

print("=== 数据基本信息 ===")
print(f"数据形状: {{df.shape}}")
print(f"列名: {{list(df.columns)}}")
print(f"数据类型:\\n{{df.dtypes}}")

# 选择分析的列
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
print("\\n=== 描述性统计 ===")
print(df_analysis.describe())

print("\\n=== 缺失值分析 ===")
missing_info = df_analysis.isnull().sum()
missing_percentage = (missing_info / len(df_analysis)) * 100
missing_df = pd.DataFrame({
    'missing_count': missing_info,
    'missing_percentage': missing_percentage
})
print(missing_df[missing_df['missing_count'] > 0])

print("\\n=== 数据类型分析 ===")
numeric_columns = df_analysis.select_dtypes(include=[np.number]).columns.tolist()
categorical_columns = df_analysis.select_dtypes(include=['object']).columns.tolist()
print(f"数值列: {{numeric_columns}}")
print(f"分类列: {{categorical_columns}}")

# 相关性分析（仅数值列）
if len(numeric_columns) > 1:
    print("\\n=== 相关性分析 ===")
    correlation_matrix = df_analysis[numeric_columns].corr()
    print(correlation_matrix)

    # 生成相关性热力图
    plt.figure(figsize=(10, 8))
    sns.heatmap(correlation_matrix, annot=True, cmap='coolwarm', center=0)
    plt.title('特征相关性热力图')
    plt.tight_layout()
    plt.savefig('/workspace/correlation_heatmap.png', dpi=300, bbox_inches='tight')
    plt.close()
    print("相关性热力图已保存: correlation_heatmap.png")

# 分布分析
print("\\n=== 分布分析 ===")
for col in numeric_columns[:5]:  # 限制前5个数值列
    plt.figure(figsize=(12, 4))

    # 直方图
    plt.subplot(1, 2, 1)
    plt.hist(df_analysis[col].dropna(), bins=30, alpha=0.7)
    plt.title(f'{{col}} 分布直方图')
    plt.xlabel(col)
    plt.ylabel('频次')

    # 箱线图
    plt.subplot(1, 2, 2)
    plt.boxplot(df_analysis[col].dropna())
    plt.title(f'{{col}} 箱线图')
    plt.ylabel(col)

    plt.tight_layout()
    plt.savefig(f'/workspace/{{col}}_distribution.png', dpi=300, bbox_inches='tight')
    plt.close()
    print(f"{{col}} 分布图已保存: {{col}}_distribution.png")

# 分类变量分析
for col in categorical_columns[:5]:  # 限制前5个分类列
    if df_analysis[col].nunique() <= 20:  # 只分析唯一值较少的分类变量
        plt.figure(figsize=(10, 6))
        value_counts = df_analysis[col].value_counts()
        plt.bar(range(len(value_counts)), value_counts.values)
        plt.xticks(range(len(value_counts)), value_counts.index, rotation=45)
        plt.title(f'{{col}} 分布')
        plt.xlabel(col)
        plt.ylabel('频次')
        plt.tight_layout()
        plt.savefig(f'/workspace/{{col}}_barplot.png', dpi=300, bbox_inches='tight')
        plt.close()
        print(f"{{col}} 柱状图已保存: {{col}}_barplot.png")

print("\\n=== 数据质量评估 ===")
print(f"重复行数: {{df_analysis.duplicated().sum()}}")
print(f"完全重复的行数: {{df_analysis.duplicated().sum()}}")

# 输出分析摘要
analysis_summary = {
    'total_rows': len(df_analysis),
    'total_columns': len(df_analysis.columns),
    'numeric_columns': len(numeric_columns),
    'categorical_columns': len(categorical_columns),
    'missing_values': missing_info.sum(),
    'duplicate_rows': df_analysis.duplicated().sum()
}

print("\\n=== 分析摘要 ===")
print(json.dumps(analysis_summary, indent=2, ensure_ascii=False))
"""

    elif analysis_type == "correlation":
        base_code += """
numeric_columns = df_analysis.select_dtypes(include=[np.number]).columns.tolist()
if len(numeric_columns) > 1:
    correlation_matrix = df_analysis[numeric_columns].corr()
    print("相关性矩阵:")
    print(correlation_matrix)

    # 找出高相关性特征对
    high_corr_pairs = []
    for i in range(len(correlation_matrix.columns)):
        for j in range(i+1, len(correlation_matrix.columns)):
            corr_value = correlation_matrix.iloc[i, j]
            if abs(corr_value) > 0.7:  # 高相关性阈值
                high_corr_pairs.append({
                    'feature1': correlation_matrix.columns[i],
                    'feature2': correlation_matrix.columns[j],
                    'correlation': corr_value
                })

    print("\\n高相关性特征对:")
    for pair in high_corr_pairs:
        print(f"{{pair['feature1']}} - {{pair['feature2']}}: {{pair['correlation']:.3f}}")
else:
    print("数值列不足，无法进行相关性分析")
"""

    elif analysis_type == "summary":
        base_code += """
print("=== 数据摘要 ===")
print(f"数据集大小: {{df_analysis.shape}}")
print("\\n数据类型:")
print(df_analysis.dtypes)

print("\\n数值列统计:")
numeric_cols = df_analysis.select_dtypes(include=[np.number])
if not numeric_cols.empty:
    print(numeric_cols.describe())

print("\\n分类列统计:")
categorical_cols = df_analysis.select_dtypes(include=['object'])
if not categorical_cols.empty:
    for col in categorical_cols.columns:
        print(f"\\n{{col}}:")
        print(f"  唯一值数量: {{df_analysis[col].nunique()}}")
        print(f"  最频繁值: {{df_analysis[col].mode().iloc[0] if not df_analysis[col].mode().empty else 'N/A'}}")
        print(f"  缺失值数量: {{df_analysis[col].isnull().sum()}}")
"""

    elif analysis_type == "distribution":
        base_code += """
numeric_columns = df_analysis.select_dtypes(include=[np.number]).columns.tolist()

print("=== 分布分析 ===")
for col in numeric_columns:
    data = df_analysis[col].dropna()

    # 基础统计
    print(f"\\n{{col}} 分布统计:")
    print(f"  均值: {{data.mean():.3f}}")
    print(f"  中位数: {{data.median():.3f}}")
    print(f"  标准差: {{data.std():.3f}}")
    print(f"  偏度: {{data.skew():.3f}}")
    print(f"  峰度: {{data.kurtosis():.3f}}")

    # 异常值检测（IQR方法）
    Q1 = data.quantile(0.25)
    Q3 = data.quantile(0.75)
    IQR = Q3 - Q1
    lower_bound = Q1 - 1.5 * IQR
    upper_bound = Q3 + 1.5 * IQR
    outliers = data[(data < lower_bound) | (data > upper_bound)]

    print(f"  异常值数量: {{len(outliers)}} ({{len(outliers)/len(data)*100:.1f}}%)")

    # 生成分布图
    plt.figure(figsize=(15, 5))

    # 直方图
    plt.subplot(1, 3, 1)
    plt.hist(data, bins=30, alpha=0.7, density=True)
    plt.title(f'{{col}} 直方图')
    plt.xlabel(col)
    plt.ylabel('密度')

    # 箱线图
    plt.subplot(1, 3, 2)
    plt.boxplot(data)
    plt.title(f'{{col}} 箱线图')
    plt.ylabel(col)

    # Q-Q图
    plt.subplot(1, 3, 3)
    from scipy import stats
    stats.probplot(data, dist="norm", plot=plt)
    plt.title(f'{{col}} Q-Q图')

    plt.tight_layout()
    plt.savefig(f'/workspace/{{col}}_distribution_analysis.png', dpi=300, bbox_inches='tight')
    plt.close()
    print(f"  分布分析图已保存: {{col}}_distribution_analysis.png")
"""

    return base_code


def _generate_preprocessing_code(
    data_file: str, operations: List[str], output_format: str
) -> str:
    """生成数据预处理代码"""

    # 确定文件读取方式
    container_data_file = _resolve_container_data_path(data_file)
    if data_file.endswith(".csv"):
        read_code = f"df = pd.read_csv('{container_data_file}')"
    elif data_file.endswith((".xlsx", ".xls")):
        read_code = f"df = pd.read_excel('{container_data_file}')"
    else:
        read_code = f"# 请手动读取数据文件: {container_data_file}"

    base_code = f"""
import pandas as pd
import numpy as np
from sklearn.preprocessing import StandardScaler, LabelEncoder, MinMaxScaler
import json
import warnings
warnings.filterwarnings('ignore')

# 读取原始数据
{read_code}
original_shape = df.shape
print(f"原始数据形状: {{original_shape}}")

df_processed = df.copy()
preprocessing_log = []

"""

    if "clean_missing" in operations:
        base_code += """
# 缺失值处理
print("\\n=== 缺失值处理 ===")
missing_info = df_processed.isnull().sum()
print("缺失值统计:")
print(missing_info[missing_info > 0])

# 数值列缺失值用中位数填充
numeric_columns = df_processed.select_dtypes(include=[np.number]).columns
for col in numeric_columns:
    if df_processed[col].isnull().sum() > 0:
        median_val = df_processed[col].median()
        df_processed[col].fillna(median_val, inplace=True)
        preprocessing_log.append(f"数值列 {{col}} 缺失值用中位数 {{median_val}} 填充")

# 分类列缺失值用众数填充
categorical_columns = df_processed.select_dtypes(include=['object']).columns
for col in categorical_columns:
    if df_processed[col].isnull().sum() > 0:
        mode_val = df_processed[col].mode().iloc[0] if not df_processed[col].mode().empty else 'Unknown'
        df_processed[col].fillna(mode_val, inplace=True)
        preprocessing_log.append(f"分类列 {{col}} 缺失值用众数 {{mode_val}} 填充")

print("缺失值处理完成")
"""

    if "remove_duplicates" in operations:
        base_code += """
# 重复值处理
print("\\n=== 重复值处理 ===")
duplicate_count = df_processed.duplicated().sum()
print(f"重复行数: {{duplicate_count}}")

if duplicate_count > 0:
    df_processed.drop_duplicates(inplace=True)
    preprocessing_log.append(f"删除了 {{duplicate_count}} 行重复数据")

print("重复值处理完成")
"""

    if "normalize" in operations:
        base_code += """
# 数值标准化
print("\\n=== 数值标准化 ===")
numeric_columns = df_processed.select_dtypes(include=[np.number]).columns.tolist()

if numeric_columns:
    scaler = StandardScaler()
    df_processed[numeric_columns] = scaler.fit_transform(df_processed[numeric_columns])
    preprocessing_log.append(f"对 {{len(numeric_columns)}} 个数值列进行了标准化")
    print(f"标准化列: {{numeric_columns}}")
else:
    print("没有数值列需要标准化")
"""

    if "encode_categorical" in operations:
        base_code += """
# 分类变量编码
print("\\n=== 分类变量编码 ===")
categorical_columns = df_processed.select_dtypes(include=['object']).columns.tolist()

for col in categorical_columns:
    if df_processed[col].nunique() <= 10:  # 对唯一值较少的分类变量进行独热编码
        dummies = pd.get_dummies(df_processed[col], prefix=col)
        df_processed = pd.concat([df_processed.drop(col, axis=1), dummies], axis=1)
        preprocessing_log.append(f"分类列 {{col}} 进行了独热编码")
    else:  # 对唯一值较多的分类变量进行标签编码
        le = LabelEncoder()
        df_processed[col] = le.fit_transform(df_processed[col])
        preprocessing_log.append(f"分类列 {{col}} 进行了标签编码")

print("分类变量编码完成")
"""

    # 输出处理后的数据
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
# 保存处理后的数据
{save_code}

# 生成预处理报告
final_shape = df_processed.shape
preprocessing_summary = {{
    'original_shape': original_shape,
    'final_shape': final_shape,
    'rows_removed': original_shape[0] - final_shape[0],
    'columns_added': final_shape[1] - original_shape[1],
    'preprocessing_steps': preprocessing_log
}}

print("\\n=== 预处理摘要 ===")
print(f"原始形状: {{original_shape}}")
print(f"处理后形状: {{final_shape}}")
print(f"删除行数: {{original_shape[0] - final_shape[0]}}")
print(f"新增列数: {{final_shape[1] - original_shape[1]}}")
print(f"输出文件: {{output_file}}")

print("\\n预处理步骤:")
for step in preprocessing_log:
    print(f"  - {{step}}")

print("\\n预处理摘要JSON:")
print(json.dumps(preprocessing_summary, indent=2, ensure_ascii=False))
"""

    return base_code


def _parse_analysis_output(stdout: str) -> Dict[str, Any]:
    """解析分析输出"""
    try:
        # 尝试从输出中提取JSON格式的摘要
        lines = stdout.split("\n")
        json_start = None
        json_end = None

        for i, line in enumerate(lines):
            if "分析摘要" in line or "预处理摘要" in line:
                # 查找JSON开始
                for j in range(i, len(lines)):
                    if lines[j].strip().startswith("{"):
                        json_start = j
                        break
                # 查找JSON结束
                for j in range(json_start or i, len(lines)):
                    if lines[j].strip().endswith("}"):
                        json_end = j
                        break
                break

        if json_start is not None and json_end is not None:
            json_str = "\n".join(lines[json_start : json_end + 1])
            summary = eval(json_str)  # 简单的JSON解析
        else:
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
        logger.warning(f"解析分析输出失败: {e}")
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
            f"分析完成（{analysis_type}）。数据集共有 {rows} 行、{cols} 列，"
            f"其中数值列 {numeric_cols or 0} 个，分类列 {categorical_cols or 0} 个。"
        )

    condensed_lines = [line.strip() for line in raw_output.splitlines() if line.strip()]
    if condensed_lines:
        return condensed_lines[0][:240]
    return "分析完成。"


def _parse_preprocessing_output(stdout: str) -> Dict[str, Any]:
    """解析预处理输出"""
    try:
        # 尝试从输出中提取预处理摘要
        lines = stdout.split("\n")
        json_start = None
        json_end = None

        for i, line in enumerate(lines):
            if "预处理摘要JSON:" in line:
                # 下一行应该是JSON
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
        logger.warning(f"解析预处理输出失败: {e}")
        return {
            "processed_data_info": {},
            "preprocessing_summary": {},
            "raw_output": stdout,
        }
