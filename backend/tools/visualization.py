"""可视化工具 - 自动化图表生成和可视化功能"""

import json
import logging
from pathlib import Path
import re
from typing import Annotated, Any, Dict, List, Optional

from backend.config import settings
from backend.tools.dataset_metadata import (
    build_metadata_audit_report,
    build_prompt_metadata,
    extract_dataset_metadata,
)
from langchain_core.tools import tool

logger = logging.getLogger(__name__)

_ALLOWED_VIZ_EXTENSIONS = {
    ".png",
    ".jpg",
    ".jpeg",
    ".svg",
    ".html",
    ".pdf",
    ".gif",
    ".webp",
}


def _next_available_path(directory: Path, base_name: str) -> Path:
    candidate = directory / base_name
    if not candidate.exists():
        return candidate
    stem = Path(base_name).stem or "artifact"
    suffix = Path(base_name).suffix
    index = 1
    while True:
        next_candidate = directory / f"{stem}_{index}{suffix}"
        if not next_candidate.exists():
            return next_candidate
        index += 1


def _persist_visualization_artifacts(output_files: Dict[str, Any]) -> List[Dict[str, str]]:
    if not isinstance(output_files, dict) or not output_files:
        return []

    output_dir = Path(getattr(settings, "temp_data_dir", "/tmp/luncheon_data")).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    persisted: List[Dict[str, str]] = []

    for raw_name, raw_content in output_files.items():
        safe_name = Path(str(raw_name)).name
        suffix = Path(safe_name).suffix.lower()
        if suffix not in _ALLOWED_VIZ_EXTENSIONS:
            continue

        if isinstance(raw_content, (bytes, bytearray)):
            content = bytes(raw_content)
        elif isinstance(raw_content, str):
            content = raw_content.encode("utf-8")
        else:
            continue

        if not content:
            continue

        target = _next_available_path(output_dir, safe_name)
        target.write_bytes(content)
        persisted.append({"filename": target.name, "path": str(target)})

    return persisted


def _resolve_container_data_path(data_file: str) -> str:
    raw_path = str(data_file or "").strip()
    if not raw_path:
        return raw_path
    if raw_path.startswith("/workspace/"):
        return raw_path
    return f"/workspace/{Path(raw_path).name}"


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
    if "pd.read_" not in lowered and "read_csv(" not in lowered and "read_excel(" not in lowered:
        return False
    blocked_patterns = (
        "locals(",
        "globals(",
        "eval(",
        "exec(",
        "__import__(",
        "subprocess.",
        "os.system(",
        "open(",
    )
    return not any(pattern in lowered for pattern in blocked_patterns)


def _generate_visualization_code_with_llm(
    data_file: str,
    chart_type: str,
    x_column: Optional[str] = None,
    y_column: Optional[str] = None,
    color_column: Optional[str] = None,
    title: Optional[str] = None,
    save_format: str = "png",
    interactive: bool = False,
    instruction: Optional[str] = None,
    dataset_metadata: Optional[Dict[str, Any]] = None,
) -> tuple[str, str, str]:
    fallback_code = _generate_visualization_code(
        data_file=data_file,
        chart_type=chart_type,
        x_column=x_column,
        y_column=y_column,
        color_column=color_column,
        title=title,
        save_format=save_format,
        interactive=interactive,
    )

    container_data_file = _resolve_container_data_path(data_file)
    output_format = "html" if interactive else save_format
    output_path = f"/workspace/{chart_type}_chart.{output_format}"
    prompt_title = title or f"{chart_type.title()} Chart"
    user_instruction = instruction or f"Create a {chart_type} chart for key insights."
    metadata_payload = build_prompt_metadata(dataset_metadata or {})

    prompt = f"""
Generate executable Python code for data visualization.

Task:
- instruction: {user_instruction}
- chart_type: {chart_type}
- x_column: {x_column or "auto-detect"}
- y_column: {y_column or "auto-detect if needed"}
- color_column: {color_column or "none"}
- chart_title: {prompt_title}
- data_file: {container_data_file}
- output_file: {output_path}
- dataset_metadata_json: {metadata_payload}

Hard requirements:
1. Use pandas as pd and numpy as np.
2. You only receive dataset metadata above (not raw rows); infer column types from metadata_json.
3. Use matplotlib/seaborn for static charts, and plotly.express only when interactive=True.
4. Read data from "{container_data_file}".
5. Save exactly one chart to "{output_path}".
6. Build dict variable chart_info with keys:
   chart_type, x_column, y_column, color_column, title, output_file, data_points, interactive
7. Print exactly one final marker line:
   CHART_INFO_JSON=<json>
   where <json> is json.dumps(chart_info, ensure_ascii=False)
8. Do NOT use locals(), globals(), eval(), exec(), __import__(), open(), subprocess, os.system.
9. Never raise exceptions when columns are missing; auto-fallback to available columns or frequency counts so one chart is still produced.
10. Ensure chart_info values are JSON-serializable Python types.
11. Return Python code only, no markdown fences or explanations.
"""

    try:
        from backend.services.llm_integration.llm_client import get_llm_client

        client = get_llm_client()
        raw_response = client.generate(
            prompt,
            temperature=0.1,
            max_tokens=1000,
            top_p=0.9,
        )
        generated_code = _extract_python_code(raw_response)
        if not generated_code:
            raise ValueError("empty_code")
        if not _is_generated_code_allowed(generated_code):
            raise ValueError("generated_code_failed_safety_or_quality_gate")
        return generated_code, "llm", ""
    except Exception as exc:
        logger.warning("LLM visualization code generation failed; using template fallback: %s", exc)
        return fallback_code, "template_fallback", str(exc)


@tool
def visualization_tool(
    data_file: Annotated[str, "Data file path"],
    chart_type: Annotated[
        str,
        "Chart type: 'line', 'bar', 'scatter', 'histogram', 'heatmap', 'box', 'violin', 'pie'",
    ] = "line",
    x_column: Annotated[Optional[str], "X-axis column name"] = None,
    y_column: Annotated[Optional[str], "Y-axis column name"] = None,
    color_column: Annotated[Optional[str], "Color grouping column name"] = None,
    title: Annotated[Optional[str], "Chart title"] = None,
    instruction: Annotated[Optional[str], "Natural-language visualization instruction"] = None,
    save_format: Annotated[str, "Save format: 'png', 'jpg', 'svg', 'html'"] = "png",
    interactive: Annotated[bool, "Whether to generate interactive charts"] = False,
) -> Dict[str, Any]:
    """
    可视化工具 - 自动化生成各类数据可视化图表

    这个工具提供全面的数据可视化功能，支持：
    1. 基础图表：折线图、柱状图、散点图、直方图
    2. Statistical charts: box plots, violin plots, heatmaps
    3. 分布图表：饼图、环形图、雷达图
    4. 高级可视化：3D图表、地理图表、网络图
    5. 交互式图表：基于 Plotly 的动态可视化

    支持的图表类型：
    - 'line': 折线图
    - 'bar': 柱状图
    - 'scatter': 散点图
    - 'histogram': 直方图
    - 'heatmap': 热力图
    - 'box': Box Plot
    - 'violin': 小提琴图
    - 'pie': 饼图

    Args:
        data_file: Data file path
        chart_type: 图表类型
        x_column: X-axis column name
        y_column: Y-axis column name
        color_column: Color grouping column name
        title: Chart title
        save_format: 保存格式
        interactive: Whether to generate interactive charts

    Returns:
        可视化结果字典，包含：
        - success: 是否成功
        - chart_type: 生成的图表类型
        - chart_info: 图表信息
        - file_path: 图表文件路径
        - chart_data: 图表数据摘要
        - insights: 图表洞察
        - error: 错误信息（如果失败）

    Example:
        >>> result = visualization_tool.invoke({
        ...     "data_file": "/path/to/data.csv",
        ...     "chart_type": "scatter",
        ...     "x_column": "age",
        ...     "y_column": "income",
        ...     "color_column": "gender"
        ... })
        >>> print(f"图表生成成功: {result['success']}")
        >>> print(f"图表路径: {result['file_path']}")
    """

    # 先尝试由 LLM 动态生成代码，失败时回退模板。
    dataset_metadata = extract_dataset_metadata(data_file)
    metadata_report = build_metadata_audit_report(dataset_metadata)
    llm_input_policy = {
        "mode": "metadata_only",
        "raw_data_sent_to_llm": False,
        "metadata_status": metadata_report.get("status"),
        "redaction_mode": metadata_report.get("redaction_mode"),
    }
    viz_code, generation_mode, generation_error = _generate_visualization_code_with_llm(
        data_file=data_file,
        chart_type=chart_type,
        x_column=x_column,
        y_column=y_column,
        color_column=color_column,
        title=title,
        save_format=save_format,
        interactive=interactive,
        instruction=instruction,
        dataset_metadata=dataset_metadata,
    )

    # 使用代码执行工具运行可视化
    from backend.tools.code_execution import code_execution_tool

    try:
        execution_mode = generation_mode
        execution_reason = generation_error
        result = code_execution_tool.invoke(
            {"code": viz_code, "data_files": [data_file] if data_file else None}
        )
        if not result.get("success") and generation_mode == "llm":
            runtime_error = str(result.get("error") or "").strip()
            fallback_code = _generate_visualization_code(
                data_file=data_file,
                chart_type=chart_type,
                x_column=x_column,
                y_column=y_column,
                color_column=color_column,
                title=title,
                save_format=save_format,
                interactive=interactive,
            )
            fallback_result = code_execution_tool.invoke(
                {
                    "code": fallback_code,
                    "data_files": [data_file] if data_file else None,
                }
            )
            if fallback_result.get("success"):
                viz_code = fallback_code
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
            # 解析可视化结果
            viz_result = _parse_visualization_output(result["stdout"])
            persisted_visualizations = _persist_visualization_artifacts(
                result.get("output_files", {})
            )

            if persisted_visualizations:
                first_path = persisted_visualizations[0]["path"]
                chart_info = viz_result.get("chart_info")
                if not isinstance(chart_info, dict):
                    chart_info = {}
                chart_info["output_file"] = first_path
                viz_result["chart_info"] = chart_info
                viz_result["file_path"] = first_path

            viz_result.update(
                {
                    "success": True,
                    "chart_type": chart_type,
                    "visualizations": (
                        persisted_visualizations
                        if persisted_visualizations
                        else result.get("visualizations", [])
                    ),
                    "code_generation": {
                        "mode": execution_mode,
                        "fallback_reason": execution_reason or None,
                    },
                    "generated_code_preview": viz_code[:1200],
                    "metadata_extraction": metadata_report,
                    "llm_input_policy": llm_input_policy,
                }
            )

            logger.info(f"Visualization complete, type: {chart_type}")
            return viz_result
        else:
            return {
                "success": False,
                "error": f"Visualization generation failed: {result.get('error', 'Unknown error')}",
                "chart_type": chart_type,
                "stdout": result.get("stdout", ""),
                "stderr": result.get("stderr", ""),
                "code_generation": {
                    "mode": execution_mode,
                    "fallback_reason": execution_reason or None,
                },
                "generated_code_preview": viz_code[:1200],
                "metadata_extraction": metadata_report,
                "llm_input_policy": llm_input_policy,
            }

    except Exception as e:
        logger.error(f"Visualization tool error: {e}")
        return {
            "success": False,
            "error": f"Tool error: {str(e)}",
            "chart_type": chart_type,
            "metadata_extraction": metadata_report,
            "llm_input_policy": llm_input_policy,
        }


@tool
def advanced_visualization_tool(
    data_file: Annotated[str, "Data file path"],
    viz_type: Annotated[
        str,
        "Advanced visualization type: '3d_scatter', 'parallel_coordinates', 'andrews_curves', 'radar', 'treemap', 'sunburst'",
    ] = "3d_scatter",
    columns: Annotated[List[str], "List of column names to use"] = None,
    group_column: Annotated[Optional[str], "Group column name"] = None,
    title: Annotated[Optional[str], "Chart title"] = None,
    save_format: Annotated[str, "Save format: 'png', 'jpg', 'svg', 'html'"] = "png",
) -> Dict[str, Any]:
    """
    高级可视化工具 - 生成复杂的数据可视化图表

    这个工具提供高级的数据可视化功能：
    1. 3D可视化：3D散点图、3D曲面图
    2. 多维可视化：平行坐标图、安德鲁斯曲线
    3. 层次可视化：树状图、旭日图
    4. 特殊图表：雷达图、词云图、网络图
    5. 统计图表：Q-Q图、概率密度图

    支持的高级可视化类型：
    - '3d_scatter': 3D散点图
    - 'parallel_coordinates': 平行坐标图
    - 'andrews_curves': 安德鲁斯曲线
    - 'radar': 雷达图
    - 'treemap': 树状图
    - 'sunburst': 旭日图

    Args:
        data_file: Data file path
        viz_type: 高级可视化类型
        columns: List of column names to use
        group_column: Group column name
        title: Chart title
        save_format: 保存格式

    Returns:
        高级可视化结果字典

    Example:
        >>> result = advanced_visualization_tool.invoke({
        ...     "data_file": "/path/to/data.csv",
        ...     "viz_type": "parallel_coordinates",
        ...     "columns": ["feature1", "feature2", "feature3"],
        ...     "group_column": "category"
        ... })
    """

    # Generate advanced visualization code
    adv_viz_code = _generate_advanced_viz_code(
        data_file, viz_type, columns, group_column, title, save_format
    )

    # 使用代码执行工具运行可视化
    from backend.tools.code_execution import code_execution_tool

    try:
        result = code_execution_tool.invoke(
            {"code": adv_viz_code, "data_files": [data_file] if data_file else None}
        )

        if result["success"]:
            # 解析可视化结果
            viz_result = _parse_visualization_output(result["stdout"])
            viz_result.update(
                {
                    "success": True,
                    "chart_type": viz_type,
                    "visualizations": result.get("visualizations", []),
                }
            )

            logger.info(f"Advanced visualization complete, type: {viz_type}")
            return viz_result
        else:
            return {
                "success": False,
                "error": f"Advanced visualization generation failed: {result.get('error', 'Unknown error')}",
                "chart_type": viz_type,
                "stdout": result.get("stdout", ""),
                "stderr": result.get("stderr", ""),
            }

    except Exception as e:
        logger.error(f"Advanced visualization tool error: {e}")
        return {"success": False, "error": f"Tool error: {str(e)}", "chart_type": viz_type}


@tool
def dashboard_generation_tool(
    data_file: Annotated[str, "Data file path"],
    dashboard_type: Annotated[
        str, "Dashboard type: 'eda', 'ml_monitoring', 'business_kpi', 'time_series'"
    ] = "eda",
    key_metrics: Annotated[List[str], "List of key metric column names"] = None,
    time_column: Annotated[Optional[str], "Time column name"] = None,
    output_format: Annotated[str, "Output format: 'html', 'pdf'"] = "html",
) -> Dict[str, Any]:
    """
    仪表板生成工具 - 自动化生成数据仪表板

    这个工具提供完整的仪表板生成功能：
    1. EDA仪表板：探索性数据分析仪表板
    2. ML监控仪表板：机器学习模型监控
    3. 业务KPI仪表板：关键业务指标展示
    4. 时间序列仪表板：时序数据分析

    支持的仪表板类型：
    - 'eda': 探索性数据分析仪表板
    - 'ml_monitoring': 机器学习监控仪表板
    - 'business_kpi': 业务KPI仪表板
    - 'time_series': 时间序列仪表板

    Args:
        data_file: Data file path
        dashboard_type: 仪表板类型
        key_metrics: List of key metric column names
        time_column: Time column name
        output_format: 输出格式

    Returns:
        仪表板生成结果字典

    Example:
        >>> result = dashboard_generation_tool.invoke({
        ...     "data_file": "/path/to/data.csv",
        ...     "dashboard_type": "eda",
        ...     "key_metrics": ["sales", "profit", "customers"]
        ... })
    """

    # Generate dashboard code
    dashboard_code = _generate_dashboard_code(
        data_file, dashboard_type, key_metrics, time_column, output_format
    )

    # 使用代码执行工具运行仪表板生成
    from backend.tools.code_execution import code_execution_tool

    try:
        result = code_execution_tool.invoke(
            {"code": dashboard_code, "data_files": [data_file] if data_file else None}
        )

        if result["success"]:
            # 解析仪表板结果
            dashboard_result = _parse_dashboard_output(result["stdout"])
            dashboard_result.update(
                {
                    "success": True,
                    "dashboard_type": dashboard_type,
                    "visualizations": result.get("visualizations", []),
                }
            )

            logger.info(f"Dashboard generation complete, type: {dashboard_type}")
            return dashboard_result
        else:
            return {
                "success": False,
                "error": f"Dashboard generation failed: {result.get('error', 'Unknown error')}",
                "dashboard_type": dashboard_type,
                "stdout": result.get("stdout", ""),
                "stderr": result.get("stderr", ""),
            }

    except Exception as e:
        logger.error(f"Dashboard generation tool error: {e}")
        return {
            "success": False,
            "error": f"Tool error: {str(e)}",
            "dashboard_type": dashboard_type,
        }


def _generate_visualization_code(
    data_file: str,
    chart_type: str,
    x_column: Optional[str] = None,
    y_column: Optional[str] = None,
    color_column: Optional[str] = None,
    title: Optional[str] = None,
    save_format: str = "png",
    interactive: bool = False,
) -> str:
    """Generate visualization code"""

    # 确定文件读取方式
    container_data_file = _resolve_container_data_path(data_file)
    if data_file.endswith(".csv"):
        read_code = f"df = pd.read_csv('{container_data_file}')"
    elif data_file.endswith((".xlsx", ".xls")):
        read_code = f"df = pd.read_excel('{container_data_file}')"
    else:
        read_code = f"# Please read data file manually: {container_data_file}"

    # 选择可视化库
    if interactive:
        viz_lib = "plotly.express as px"
        save_method = "fig.write_html"
    else:
        viz_lib = "matplotlib.pyplot as plt\nimport seaborn as sns"
        save_method = "plt.savefig"

    base_code = f"""
import pandas as pd
import numpy as np
import json
import {viz_lib}
import warnings
warnings.filterwarnings('ignore')

# Set up fonts if available
if not {interactive}:
    plt.rcParams['font.sans-serif'] = ['SimHei', 'Arial Unicode MS', 'DejaVu Sans']
    plt.rcParams['axes.unicode_minus'] = False

# 读取数据
{read_code}

print("=== Data Info ===")
print(f"Data Shape: {{df.shape}}")
print(f"列名: {{list(df.columns)}}")

# 自动检测列（如果未指定）
numeric_columns = df.select_dtypes(include=[np.number]).columns.tolist()
"""

    if not x_column:
        base_code += """
x_col = numeric_columns[0] if len(numeric_columns) > 0 else df.columns[0]
"""
    else:
        base_code += f"x_col = '{x_column}'\n"

    if not y_column and chart_type in ["line", "bar", "scatter"]:
        base_code += """
if len(numeric_columns) > 1:
    y_col = numeric_columns[1]
elif len(numeric_columns) == 1:
    y_col = numeric_columns[0]
else:
    # Fallback: build a frequency table so charts can still be rendered.
    source_col = str(df.columns[0])
    freq_df = df[source_col].astype(str).value_counts().reset_index()
    freq_df.columns = [source_col, 'value_count']
    df = freq_df
    x_col = source_col
    y_col = 'value_count'
"""
    elif y_column:
        base_code += f"y_col = '{y_column}'\n"
    else:
        base_code += "y_col = None\n"

    if not color_column:
        base_code += "color_col = None\n"
    else:
        base_code += f"color_col = '{color_column}'\n"

    if not title:
        base_code += f"chart_title = '{chart_type.title()} Chart'\n"
    else:
        base_code += f"chart_title = '{title}'\n"

    # 根据图表类型生成代码
    if interactive:
        # Plotly 交互式图表
        if chart_type == "line":
            base_code += """
fig = px.line(df, x=x_col, y=y_col, color=color_col, title=chart_title)
"""
        elif chart_type == "bar":
            base_code += """
fig = px.bar(df, x=x_col, y=y_col, color=color_col, title=chart_title)
"""
        elif chart_type == "scatter":
            base_code += """
fig = px.scatter(df, x=x_col, y=y_col, color=color_col, title=chart_title)
"""
        elif chart_type == "histogram":
            base_code += """
fig = px.histogram(df, x=x_col, color=color_col, title=chart_title)
"""
        elif chart_type == "box":
            base_code += """
fig = px.box(df, x=x_col, y=y_col, color=color_col, title=chart_title)
"""
        elif chart_type == "pie":
            base_code += """
fig = px.pie(df, names=x_col, values=y_col, title=chart_title)
"""

        base_code += f"""
fig.update_layout(title_font_size=16, showlegend=True)
output_file = '/workspace/{chart_type}_chart.html'
fig.write_html(output_file)
print(f"交互式图表已保存: {{output_file}}")
"""

    else:
        # Matplotlib/Seaborn 静态图表
        if chart_type == "line":
            base_code += """
plt.figure(figsize=(12, 6))
if color_col and df[color_col].nunique() <= 10:
    for group in df[color_col].unique():
        group_data = df[df[color_col] == group]
        plt.plot(group_data[x_col], group_data[y_col], label=str(group), marker='o')
    plt.legend()
else:
    plt.plot(df[x_col], df[y_col], marker='o')
plt.xlabel(x_col)
plt.ylabel(y_col)
plt.title(chart_title)
plt.grid(True, alpha=0.3)
"""

        elif chart_type == "bar":
            base_code += """
plt.figure(figsize=(12, 6))
if color_col and df[color_col].nunique() <= 10:
    # 分组柱状图
    pivot_data = df.pivot_table(values=y_col, index=x_col, columns=color_col, aggfunc='mean')
    pivot_data.plot(kind='bar', figsize=(12, 6))
else:
    plt.bar(df[x_col], df[y_col])
plt.xlabel(x_col)
plt.ylabel(y_col)
plt.title(chart_title)
plt.xticks(rotation=45)
"""

        elif chart_type == "scatter":
            base_code += """
plt.figure(figsize=(10, 8))
if color_col and df[color_col].nunique() <= 10:
    for group in df[color_col].unique():
        group_data = df[df[color_col] == group]
        plt.scatter(group_data[x_col], group_data[y_col], label=str(group), alpha=0.7)
    plt.legend()
else:
    plt.scatter(df[x_col], df[y_col], alpha=0.7)
plt.xlabel(x_col)
plt.ylabel(y_col)
plt.title(chart_title)
plt.grid(True, alpha=0.3)
"""

        elif chart_type == "histogram":
            base_code += """
plt.figure(figsize=(10, 6))
is_numeric_hist = pd.api.types.is_numeric_dtype(df[x_col])
if not is_numeric_hist:
    hist_counts = df[x_col].astype(str).value_counts()
    plt.bar(hist_counts.index, hist_counts.values)
    plt.xticks(rotation=45)
elif color_col and df[color_col].nunique() <= 5:
    for group in df[color_col].unique():
        group_data = df[df[color_col] == group]
        plt.hist(group_data[x_col], alpha=0.7, label=str(group), bins=30)
    plt.legend()
else:
    plt.hist(df[x_col], bins=30, alpha=0.7)
plt.xlabel(x_col)
plt.ylabel('频次')
plt.title(chart_title)
plt.grid(True, alpha=0.3)
"""

        elif chart_type == "box":
            base_code += """
plt.figure(figsize=(10, 6))
if color_col and df[color_col].nunique() <= 10:
    sns.boxplot(data=df, x=x_col, y=y_col, hue=color_col)
else:
    sns.boxplot(data=df, x=x_col, y=y_col)
plt.title(chart_title)
plt.xticks(rotation=45)
"""

        elif chart_type == "heatmap":
            base_code += """
# 热力图需要数值数据
numeric_df = df.select_dtypes(include=[np.number])
plt.figure(figsize=(12, 8))
correlation_matrix = numeric_df.corr()
sns.heatmap(correlation_matrix, annot=True, cmap='coolwarm', center=0,
            square=True, linewidths=0.5)
plt.title(chart_title)
plt.tight_layout()
"""

        elif chart_type == "violin":
            base_code += """
plt.figure(figsize=(10, 6))
if color_col and df[color_col].nunique() <= 10:
    sns.violinplot(data=df, x=x_col, y=y_col, hue=color_col)
else:
    sns.violinplot(data=df, x=x_col, y=y_col)
plt.title(chart_title)
plt.xticks(rotation=45)
"""

        elif chart_type == "pie":
            base_code += """
plt.figure(figsize=(10, 8))
if y_col:
    pie_data = df.groupby(x_col)[y_col].sum()
else:
    pie_data = df[x_col].value_counts()
plt.pie(pie_data.values, labels=pie_data.index, autopct='%1.1f%%', startangle=90)
plt.title(chart_title)
plt.axis('equal')
"""

        base_code += f"""
plt.tight_layout()
output_file = '/workspace/{chart_type}_chart.{save_format}'
plt.savefig(output_file, dpi=300, bbox_inches='tight')
plt.close()
print(f"图表已保存: {{output_file}}")
"""

    # 添加图表信息输出
    base_code += f"""
# 输出图表信息
chart_info = {{
    'chart_type': '{chart_type}',
    'x_column': x_col,
    'y_column': y_col,
    'color_column': color_col,
    'title': chart_title,
    'output_file': output_file,
    'data_points': len(df),
    'interactive': {repr(interactive)}
}}

print("\\n=== 图表信息 ===")
for key, value in chart_info.items():
    print(f"{{key}}: {{value}}")
print("CHART_INFO_JSON=" + json.dumps(chart_info, ensure_ascii=False))
"""

    return base_code


def _generate_advanced_viz_code(
    data_file: str,
    viz_type: str,
    columns: Optional[List[str]] = None,
    group_column: Optional[str] = None,
    title: Optional[str] = None,
    save_format: str = "png",
) -> str:
    """Generate advanced visualization code"""

    # 确定文件读取方式
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
from mpl_toolkits.mplot3d import Axes3D
import seaborn as sns
from pandas.plotting import parallel_coordinates, andrews_curves, radviz
import warnings
warnings.filterwarnings('ignore')

# 设置中文字体
plt.rcParams['font.sans-serif'] = ['SimHei', 'Arial Unicode MS', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

# 读取数据
{read_code}

print("=== Data Info ===")
print(f"Data Shape: {{df.shape}}")
print(f"列名: {{list(df.columns)}}")

# 选择列
"""

    if columns:
        base_code += f"selected_columns = {columns}\n"
    else:
        base_code += "selected_columns = df.select_dtypes(include=[np.number]).columns.tolist()[:5]\n"
    base_code += "output_file = None\n"

    if not title:
        base_code += (
            f"chart_title = '{viz_type.replace('_', ' ').title()} Visualization'\n"
        )
    else:
        base_code += f"chart_title = '{title}'\n"

    # 根据高级可视化类型生成代码
    if viz_type == "3d_scatter":
        base_code += """
fig = plt.figure(figsize=(12, 8))
ax = fig.add_subplot(111, projection='3d')

if len(selected_columns) >= 3:
    x, y, z = selected_columns[0], selected_columns[1], selected_columns[2]

    if group_column and group_column in df.columns:
        for group in df[group_column].unique():
            group_data = df[df[group_column] == group]
            ax.scatter(group_data[x], group_data[y], group_data[z], label=str(group))
        ax.legend()
    else:
        ax.scatter(df[x], df[y], df[z])

    ax.set_xlabel(x)
    ax.set_ylabel(y)
    ax.set_zlabel(z)
else:
    print("需要至少3个数值列来生成3D散点图")

ax.set_title(chart_title)
"""

    elif viz_type == "parallel_coordinates":
        base_code += f"""
if len(selected_columns) >= 2 and group_column and group_column in df.columns:
    plt.figure(figsize=(14, 8))
    parallel_coordinates(df[selected_columns + [group_column]], group_column)
    plt.title(chart_title)
    plt.xticks(rotation=45)
else:
    print("平行坐标图需要分组列和至少2个数值列")
"""

    elif viz_type == "andrews_curves":
        base_code += f"""
if len(selected_columns) >= 2 and group_column and group_column in df.columns:
    plt.figure(figsize=(12, 8))
    andrews_curves(df[selected_columns + [group_column]], group_column)
    plt.title(chart_title)
else:
    print("安德鲁斯曲线需要分组列和至少2个数值列")
"""

    elif viz_type == "radar":
        base_code += f"""
if len(selected_columns) >= 3 and group_column and group_column in df.columns:
    # 雷达图需要标准化数据
    from sklearn.preprocessing import MinMaxScaler

    numeric_data = df[selected_columns].copy()
    scaler = MinMaxScaler()
    numeric_data_scaled = scaler.fit_transform(numeric_data)

    # 计算每个组的平均值
    if group_column in df.columns:
        grouped_data = df.groupby(group_column)[selected_columns].mean()

        # 创建雷达图
        angles = np.linspace(0, 2*np.pi, len(selected_columns), endpoint=False).tolist()
        angles += angles[:1]  # 闭合图形

        fig, ax = plt.subplots(figsize=(10, 10), subplot_kw=dict(projection='polar'))

        for i, (group_name, group_data) in enumerate(grouped_data.iterrows()):
            values = group_data.values.tolist()
            values += values[:1]  # 闭合图形
            ax.plot(angles, values, 'o-', linewidth=2, label=str(group_name))
            ax.fill(angles, values, alpha=0.25)

        ax.set_xticks(angles[:-1])
        ax.set_xticklabels(selected_columns)
        ax.set_title(chart_title)
        ax.legend()
else:
    print("雷达图需要分组列和至少3个数值列")
"""

    elif viz_type == "treemap":
        base_code += """
# 树状图需要 plotly
try:
    import plotly.express as px

    if len(selected_columns) >= 2:
        # 使用前两列作为父级和子级
        parent_col = selected_columns[0]
        child_col = selected_columns[1]

        # 计算每个子级的值
        treemap_data = df.groupby([parent_col, child_col]).size().reset_index(name='count')

        fig = px.treemap(treemap_data, path=[parent_col, child_col], values='count', title=chart_title)
        output_file = f'/workspace/treemap.html'
        fig.write_html(output_file)
        print(f"树状图已保存: {output_file}")
    else:
        print("树状图需要至少2个列")
except ImportError:
    print("树状图需要安装 plotly: pip install plotly")
"""

    elif viz_type == "sunburst":
        base_code += """
# 旭日图需要 plotly
try:
    import plotly.express as px

    if len(selected_columns) >= 2:
        # 使用前两列作为层级
        level1_col = selected_columns[0]
        level2_col = selected_columns[1]

        # 计算每个层级的值
        sunburst_data = df.groupby([level1_col, level2_col]).size().reset_index(name='count')

        fig = px.sunburst(sunburst_data, path=[level1_col, level2_col], values='count', title=chart_title)
        output_file = f'/workspace/sunburst.html'
        fig.write_html(output_file)
        print(f"旭日图已保存: {output_file}")
    else:
        print("旭日图需要至少2个列")
except ImportError:
    print("旭日图需要安装 plotly: pip install plotly")
"""

    base_code += f"""
# 保存图表
if not '{viz_type}' in ['treemap', 'sunburst']:  # 这些已经保存为HTML
    plt.tight_layout()
    output_file = f'/workspace/{viz_type}_visualization.{save_format}'
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"高级可视化已保存: {{output_file}}")

# 输出图表信息
viz_info = {{
    'viz_type': '{viz_type}',
    'columns_used': selected_columns,
    'group_column': '{group_column}' if '{group_column}' else None,
    'title': chart_title,
    'output_file': output_file,
    'data_points': len(df)
}}

print("\\n=== 高级可视化信息 ===")
for key, value in viz_info.items():
    print(f"{{key}}: {{value}}")
"""

    return base_code


def _generate_dashboard_code(
    data_file: str,
    dashboard_type: str,
    key_metrics: Optional[List[str]] = None,
    time_column: Optional[str] = None,
    output_format: str = "html",
) -> str:
    """Generate dashboard code"""

    # 确定文件读取方式
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
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

# 设置中文字体
plt.rcParams['font.sans-serif'] = ['SimHei', 'Arial Unicode MS', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

# 读取数据
{read_code}

print("=== Data Info ===")
print(f"Data Shape: {{df.shape}}")
print(f"列名: {{list(df.columns)}}")

# 选择关键指标
"""

    if key_metrics:
        base_code += f"metrics = {key_metrics}\n"
    else:
        base_code += (
            "metrics = df.select_dtypes(include=[np.number]).columns.tolist()[:5]\n"
        )

    if time_column:
        base_code += f"time_col = '{time_column}'\n"
    else:
        base_code += "time_col = None\n"

    # 根据仪表板类型生成代码
    if dashboard_type == "eda":
        base_code += """
# EDA 仪表板
fig, axes = plt.subplots(2, 3, figsize=(18, 12))
fig.suptitle('探索性数据分析仪表板', fontsize=16)

# 1. Data Overview
axes[0, 0].text(0.1, 0.5, f'数据集形状: {df.shape}\\n数值列: {len(df.select_dtypes(include=[np.number]).columns)}\\n分类列: {len(df.select_dtypes(include=[object]).columns)}',
                transform=axes[0, 0].transAxes, fontsize=12, verticalalignment='center')
axes[0, 0].set_title('Data Overview')
axes[0, 0].axis('off')

# 2. Missing Values分析
missing_data = df.isnull().sum()
missing_data = missing_data[missing_data > 0].sort_values(ascending=False)
if len(missing_data) > 0:
    axes[0, 1].bar(range(len(missing_data)), missing_data.values)
    axes[0, 1].set_xticks(range(len(missing_data)))
    axes[0, 1].set_xticklabels(missing_data.index, rotation=45)
    axes[0, 1].set_title('Missing Values分析')
else:
    axes[0, 1].text(0.5, 0.5, '无Missing Values', transform=axes[0, 1].transAxes,
                    ha='center', va='center')
    axes[0, 1].set_title('Missing Values分析')

# 3. 数值Variable分布
if len(metrics) > 0:
    df[metrics[0]].hist(bins=30, ax=axes[0, 2])
    axes[0, 2].set_title(f'{metrics[0]} 分布')
else:
    axes[0, 2].text(0.5, 0.5, '无数值列', transform=axes[0, 2].transAxes,
                    ha='center', va='center')
    axes[0, 2].set_title('数值Variable分布')

# 4. 相关性热力图
numeric_df = df.select_dtypes(include=[np.number])
if len(numeric_df.columns) > 1:
    correlation_matrix = numeric_df.corr()
    sns.heatmap(correlation_matrix, annot=True, cmap='coolwarm', center=0,
                ax=axes[1, 0], square=True)
    axes[1, 0].set_title('相关性热力图')
else:
    axes[1, 0].text(0.5, 0.5, '数值列不足', transform=axes[1, 0].transAxes,
                    ha='center', va='center')
    axes[1, 0].set_title('相关性热力图')

# 5. Box Plot
if len(metrics) >= 2:
    df[metrics[:2]].boxplot(ax=axes[1, 1])
    axes[1, 1].set_title('Box Plot')
    axes[1, 1].tick_params(axis='x', rotation=45)
else:
    axes[1, 1].text(0.5, 0.5, '数值列不足', transform=axes[1, 1].transAxes,
                    ha='center', va='center')
    axes[1, 1].set_title('Box Plot')

# 6. 数据质量评分
quality_score = 100
quality_score -= (df.isnull().sum().sum() / (df.shape[0] * df.shape[1])) * 50
quality_score -= (df.duplicated().sum() / df.shape[0]) * 30

axes[1, 2].bar(['数据质量'], [quality_score])
axes[1, 2].set_ylim(0, 100)
axes[1, 2].set_title(f'数据质量评分: {quality_score:.1f}')
axes[1, 2].set_ylabel('分数')

plt.tight_layout()
"""

    elif dashboard_type == "business_kpi":
        base_code += """
# 业务KPI仪表板
fig, axes = plt.subplots(2, 3, figsize=(18, 12))
fig.suptitle('业务KPI仪表板', fontsize=16)

# 1. KPI概览
if len(metrics) > 0:
    for i, metric in enumerate(metrics[:3]):
        if i < 3:
            value = df[metric].sum() if df[metric].dtype in ['int64', 'float64'] else df[metric].nunique()
            axes[0, i].text(0.5, 0.5, f'{metric}\\n{value:,.0f}',
                           transform=axes[0, i].transAxes, ha='center', va='center',
                           fontsize=14, fontweight='bold')
            axes[0, i].set_title(metric)
            axes[0, i].axis('off')

# 4. 趋势图
if len(metrics) >= 2 and time_col and time_col in df.columns:
    df_sorted = df.sort_values(time_col)
    axes[1, 0].plot(df_sorted[time_col], df_sorted[metrics[0]])
    axes[1, 0].set_title(f'{metrics[0]} 趋势')
    axes[1, 0].tick_params(axis='x', rotation=45)

# 5. 对比图
if len(metrics) >= 2:
    axes[1, 1].bar(metrics[:2], [df[metric].sum() for metric in metrics[:2]])
    axes[1, 1].set_title('指标对比')
    axes[1, 1].tick_params(axis='x', rotation=45)

# 6. 分布图
if len(metrics) > 0:
    df[metrics[0]].hist(bins=30, ax=axes[1, 2])
    axes[1, 2].set_title(f'{metrics[0]} 分布')

plt.tight_layout()
"""

    base_code += f"""
# 保存仪表板
output_file = f'/workspace/{dashboard_type}_dashboard.{output_format}'
if output_format == 'html':
    # 保存为HTML需要特殊处理
    import io
    import base64

    img_buffer = io.BytesIO()
    plt.savefig(img_buffer, format='png', dpi=300, bbox_inches='tight')
    img_buffer.seek(0)
    img_str = base64.b64encode(img_buffer.read()).decode()

    html_content = f'''
    <!DOCTYPE html>
    <html>
    <head>
        <title>{dashboard_type} Dashboard</title>
        <style>
            body {{ font-family: Arial, sans-serif; margin: 20px; }}
            .dashboard {{ text-align: center; }}
            img {{ max-width: 100%; height: auto; }}
        </style>
    </head>
    <body>
        <div class="dashboard">
            <h1>{dashboard_type} Dashboard</h1>
            <img src="data:image/png;base64,{img_str}" alt="Dashboard">
        </div>
    </body>
    </html>
    '''

    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(html_content)
else:
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    plt.close()

print(f"仪表板已保存: {{output_file}}")

# 输出仪表板信息
dashboard_info = {{
    'dashboard_type': '{dashboard_type}',
    'metrics': metrics,
    'time_column': time_col,
    'output_file': output_file,
    'data_points': len(df)
}}

print("\\n=== 仪表板信息 ===")
for key, value in dashboard_info.items():
    print(f"{{key}}: {{value}}")
"""

    return base_code


def _parse_visualization_output(stdout: str) -> Dict[str, Any]:
    """Parse visualization output"""
    try:
        lines = stdout.split("\n")
        chart_info: Dict[str, Any] = {}

        marker = "CHART_INFO_JSON="
        marker_line = next(
            (line for line in lines if line.strip().startswith(marker)),
            None,
        )
        if marker_line:
            raw_json = marker_line.split(marker, 1)[1].strip()
            try:
                parsed = json.loads(raw_json)
                if isinstance(parsed, dict):
                    chart_info = parsed
            except Exception:
                chart_info = {}

        if not chart_info:
            for line in lines:
                if ":" in line and not line.startswith("==="):
                    key, value = line.split(":", 1)
                    chart_info[key.strip()] = value.strip()

        return {
            "chart_info": chart_info,
            "file_path": chart_info.get("output_file", ""),
            "chart_data": {
                "data_points": chart_info.get("data_points", "0"),
                "x_column": chart_info.get("x_column", ""),
                "y_column": chart_info.get("y_column", ""),
                "color_column": chart_info.get("color_column", ""),
            },
            "insights": [],
            "raw_output": stdout,
        }

    except Exception as e:
        logger.warning(f"Parse visualization output failed: {e}")
        return {
            "chart_info": {},
            "file_path": "",
            "chart_data": {},
            "insights": [],
            "raw_output": stdout,
        }


def _parse_dashboard_output(stdout: str) -> Dict[str, Any]:
    """Parse dashboard output"""
    try:
        # 尝试从输出中提取仪表板信息
        lines = stdout.split("\n")
        dashboard_info = {}

        for line in lines:
            if ":" in line and not line.startswith("==="):
                key, value = line.split(":", 1)
                dashboard_info[key.strip()] = value.strip()

        return {
            "dashboard_info": dashboard_info,
            "file_path": dashboard_info.get("output_file", ""),
            "metrics": dashboard_info.get("metrics", "").strip("[]").split(", ")
            if dashboard_info.get("metrics")
            else [],
            "raw_output": stdout,
        }

    except Exception as e:
        logger.warning(f"Parse dashboard output failed: {e}")
        return {
            "dashboard_info": {},
            "file_path": "",
            "metrics": [],
            "raw_output": stdout,
        }
