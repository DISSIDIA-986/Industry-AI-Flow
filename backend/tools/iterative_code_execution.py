"""Iterative Code Execution Tool - Smart code execution with self-healing"""

import asyncio
import logging
from typing import Annotated, Any, Dict, List, Optional

from langchain_core.tools import tool

from backend.agents.code_execution_agent import iterative_code_agent
from backend.services.code_executor import validate_code
from backend.services.data_transfer import data_transfer

logger = logging.getLogger(__name__)


@tool
def iterative_code_analysis_tool(
    request: Annotated[str, "Data analysis request description"],
    data_file: Annotated[Optional[str], "Data file path (optional)"] = None,
    analysis_type: Annotated[
        str, "Analysis type: 'eda', 'ml_model', 'visualization', 'statistical'"
    ] = "eda",
    max_attempts: Annotated[int, "Maximum repair attempts"] = 5,
    transfer_method: Annotated[
        str, "Data transfer method: 'auto', 'file_mapping', 'database'"
    ] = "auto",
) -> Dict[str, Any]:
    """
    可迭代代码分析工具 - 自动修复的智能数据分析

    这个工具具备以下特性：
    1. **自我修复机制**: 代码执行失败时自动分析错误并修复
    2. **智能数据传递**: 自动选择最优的数据文件传递方式
    3. **多轮迭代**: 支持最多5次修复尝试
    4. **错误学习**: 记录错误模式，提高修复成功率
    5. **上下文保持**: 在迭代过程中保持分析上下文

    支持的分析类型：
    - 'eda': 探索性数据分析（默认）
    - 'ml_model': 机器学习模型训练
    - 'visualization': 数据可视化
    - 'statistical': 统计分析和假设检验

    Args:
        request: 详细的数据分析请求
        data_file: Data file path (optional)
        analysis_type: 分析类型
        max_attempts: Maximum repair attempts
        transfer_method: 数据传递方式

    Returns:
        执行结果字典，包含：
        - success: 是否成功
        - analysis_type: 分析类型
        - final_code: 最终执行的代码
        - attempts: 尝试次数统计
        - execution_result: 执行结果
        - visualizations: 生成的可视化文件
        - error_analysis: 错误分析（如果失败）
        - performance_metrics: 性能指标

    Example:
        >>> result = iterative_code_analysis_tool.invoke({
        ...     "request": "对销售数据进行探索性分析，包括趋势分析和可视化",
        ...     "data_file": "/path/to/sales_data.csv",
        ...     "analysis_type": "eda"
        ... })
        >>> if result["success"]:
        ...     print(f"分析成功，执行了 {result['attempts']} attempts尝试")
        ...     print(f"生成了 {len(result['visualizations'])} 个可视化图表")
    """

    try:
        # Prepare data file (if provided)
        transferred_data = None
        context = {"analysis_type": analysis_type}

        if data_file:
            logger.info(f"Processing data file: {data_file}")

            # 传递数据文件
            transfer_result = data_transfer.transfer_file_for_docker(
                data_file, transfer_method
            )

            if not transfer_result["success"]:
                return {
                    "success": False,
                    "error": f"Data file transfer failed: {transfer_result.get('error', 'Unknown error')}",
                    "analysis_type": analysis_type,
                    "attempts": 0,
                }

            transferred_data = transfer_result
            context.update(
                {
                    "data_file_info": transfer_result["file_info"],
                    "transfer_method": transfer_result["method"],
                    "transferred_path": transfer_result["transferred_path"],
                }
            )

            # Prepare data file path for code execution
            if transfer_result["method"] == "file_mapping":
                data_file_for_execution = transfer_result["transferred_path"]
            else:
                # Database method, use config file
                data_file_for_execution = transfer_result.get("config_file")

        # Build enhanced analysis request
        enhanced_request = _build_enhanced_request(
            request, analysis_type, transferred_data
        )

        # Async iterative analysis execution
        try:
            # Running async code in synchronous context
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            result = loop.run_until_complete(
                iterative_code_agent.execute_code_iteratively(
                    original_request=enhanced_request,
                    data_file=data_file_for_execution if data_file else None,
                    context=context,
                )
            )

            loop.close()

        except Exception as e:
            logger.error(f"Iterative execution error: {e}")
            return {
                "success": False,
                "error": f"Code execution error: {str(e)}",
                "analysis_type": analysis_type,
                "attempts": 0,
            }

        # Post-process results
        processed_result = _process_analysis_result(
            result, analysis_type, transferred_data
        )

        # Clean up transferred data
        if transferred_data:
            cleanup_success = data_transfer.cleanup_transferred_data(transferred_data)
            processed_result["cleanup_success"] = cleanup_success

        return processed_result

    except Exception as e:
        logger.error(f"Iterative code analysis tool error: {e}")
        return {
            "success": False,
            "error": f"Tool error: {str(e)}",
            "analysis_type": analysis_type,
            "attempts": 0,
        }


@tool
def self_healing_code_execution_tool(
    code: Annotated[str, "Python code to execute"],
    description: Annotated[str, "Code description and expected result"],
    data_files: Annotated[Optional[List[str]], "List of data file dependencies"] = None,
    max_attempts: Annotated[int, "Maximum self-healing attempts"] = 5,
    auto_fix_imports: Annotated[bool, "Whether to auto-fix import errors"] = True,
) -> Dict[str, Any]:
    """
    自我修复代码执行工具 - 智能修复执行错误的代码运行器

    这个工具专门用于执行可能有问题的 Python 代码，并在遇到错误时自动修复：
    1. **导入错误自动修复**: 检测缺失的导入并自动添加
    2. **语法错误修正**: 修复常见的语法问题
    3. **Variable未定义**: 自动定义常用的Variable
    4. **文件路径修复**: 修正文件访问路径
    5. **类型错误处理**: 添加必要的类型转换
    6. **索引边界检查**: 修复数组/列表越界问题

    修复策略：
    - 第一次尝试：执行原始代码
    - 第二次尝试：添加缺失的导入
    - 第三次尝试：修复语法错误
    - 第四次尝试：定义未使用的Variable
    - 第五次尝试：修复文件路径和类型转换

    Args:
        code: Python code to execute
        description: Code description and expected result
        data_files: List of data file dependencies
        max_attempts: Maximum self-healing attempts
        auto_fix_imports: Whether to auto-fix import errors

    Returns:
        执行结果字典，包含：
        - success: 是否成功
        - final_code: 最终执行的代码
        - attempts: 尝试次数
        - fixes_applied: 应用的修复列表
        - execution_result: 最终执行结果
        - error_history: 错误历史记录
        - performance_metrics: 执行性能指标

    Example:
        >>> code = '''
        # 可能包含错误的代码
        df = read_csv('data.csv')  # missing pandas import
        print(df.head())
        '''
        >>> result = self_healing_code_execution_tool.invoke({
        ...     "code": code,
        ...     "description": "读取并显示数据前几行"
        ... })
        >>> print(f"修复成功: {result['success']}")
        >>> print(f"Fixes applied: {result['fixes_applied']}")
    """

    try:
        # Validate code safety BEFORE any execution attempt.
        validation = validate_code(code, strict_mode=True)
        if not validation.is_valid:
            return {
                "success": False,
                "error": f"Code safety validation failed: {validation.error}",
                "final_code": code,
                "attempts": 0,
                "fixes_applied": [],
            }

        # Prepare data file
        transferred_files = []
        context = {"description": description, "auto_fix_imports": auto_fix_imports}

        if data_files:
            for file_path in data_files:
                transfer_result = data_transfer.transfer_file_for_docker(
                    file_path, "auto"
                )
                if transfer_result["success"]:
                    transferred_files.append(transfer_result["transferred_path"])
                    context[f"data_file_{len(transferred_files)}"] = transfer_result

        # Build execution request
        execution_request = f"""
Execute the following Python code:

Description: {description}

Requirements:
1. Execute code and return results
2. If errors occur, auto-fix and retry
3. Maximum {max_attempts} attempts
4. Keep the core logic unchanged

Code:
```python
{code}
```
"""

        # Async self-healing execution
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            result = loop.run_until_complete(
                iterative_code_agent.execute_code_iteratively(
                    original_request=execution_request,
                    initial_code=code,
                    data_file=transferred_files[0] if transferred_files else None,
                    context=context,
                )
            )

            loop.close()

        except Exception as e:
            logger.error(f"Self-healing execution error: {e}")
            return {
                "success": False,
                "error": f"Execution error: {str(e)}",
                "final_code": code,
                "attempts": 0,
                "fixes_applied": [],
            }

        # Extract fix information
        fixes_applied = []
        if "attempts" in result and len(result["attempts"]) > 1:
            for attempt in result["attempts"][1:]:  # Skip first original attempt
                if attempt.fixes_applied:
                    fixes_applied.extend(attempt.fixes_applied)

        # Clean up data files
        for transfer_result in [
            tr for tr in context.values() if isinstance(tr, dict) and "success" in tr
        ]:
            try:
                data_transfer.cleanup_transferred_data(transfer_result)
            except:
                pass

        return {
            "success": result.get("success", False),
            "final_code": result.get("final_code", code),
            "attempts": result.get("attempts", 0),
            "fixes_applied": fixes_applied,
            "execution_result": {
                "stdout": result.get("stdout", ""),
                "stderr": result.get("stderr", ""),
                "execution_time": result.get("execution_time", 0.0),
                "visualizations": result.get("visualizations", []),
            },
            "error_history": [
                {
                    "attempt": attempt.attempt_id,
                    "error": attempt.error_message,
                    "success": attempt.success,
                }
                for attempt in result.get("attempts", [])
                if not attempt.success
            ],
            "performance_metrics": {
                "total_execution_time": sum(
                    attempt.execution_time for attempt in result.get("attempts", [])
                ),
                "success_rate": 1.0 if result.get("success", False) else 0.0,
                "fixes_per_attempt": len(fixes_applied)
                / max(1, result.get("attempts", 1) - 1),
            },
        }

    except Exception as e:
        logger.error(f"Self-healing tool error: {e}")
        return {
            "success": False,
            "error": f"Tool error: {str(e)}",
            "final_code": code,
            "attempts": 0,
            "fixes_applied": [],
        }


def _build_enhanced_request(
    request: str, analysis_type: str, transferred_data: Optional[Dict[str, Any]] = None
) -> str:
    """Build enhanced analysis request"""

    # Add type-specific requirements
    type_requirements = {
        "eda": """
Exploratory Data Analysis Requirements:
1. Data overview: shape, types, missing values
2. Descriptive statistics: mean, median, std, etc.
3. Distribution analysis: histograms, box plots, density plots
4. Correlation analysis: correlation matrix and heatmaps
5. Outlier detection: identify and visualize outliers
6. Data quality: duplicates and missing value pattern analysis
""",
        "ml_model": """
Machine Learning Model Requirements:
1. Data preprocessing: feature engineering, data cleaning
2. Feature selection: correlation analysis, importance ranking
3. Model selection: try at least 2-3 algorithms
4. Model training: cross-validation, hyperparameter tuning
5. Model evaluation: accuracy, precision, recall, F1 score
6. Result interpretation: feature importance, model explainability
""",
        "visualization": """
Data Visualization Requirements:
1. Basic charts: bar charts, line charts, scatter plots
2. Statistical charts: box plots, violin plots, heatmaps
3. Interactive charts: create interactive charts with Plotly
4. Multi-dimensional visualization: 3D charts, parallel coordinates
5. Chart styling: set titles, labels, color themes
6. Save images: high-resolution output in multiple formats
""",
        "statistical": """
Statistical Analysis Requirements:
1. Descriptive statistics: complete data summary
2. Hypothesis testing: t-test, chi-square test, etc.
3. Correlation analysis: Pearson, Spearman coefficients
4. ANOVA: one-way, multi-factor analysis of variance
5. Regression analysis: linear regression, polynomial regression
6. Confidence intervals: parameter estimation confidence intervals
""",
    }

    requirements = type_requirements.get(analysis_type, "")

    enhanced_request = f"""
User request: {request}

Analysis type: {analysis_type}

{requirements}

Code requirements:
1. Use pandas, numpy, matplotlib, and seaborn.
2. Configure matplotlib with cross-platform fonts.
3. Include clear comments for key logic.
4. Generate high-resolution visualizations.
5. Return structured analysis results.
6. Include basic error handling.
7. Save all charts to /workspace/output/.

Recommended matplotlib bootstrap:
```python
plt.rcParams['font.sans-serif'] = ['DejaVu Sans', 'Arial Unicode MS', 'Liberation Sans']
plt.rcParams['axes.unicode_minus'] = False
print("✓ Matplotlib font settings initialized")
```
"""

    if transferred_data:
        enhanced_request += f"""

Data file information:
- Filename: {transferred_data['file_info']['name']}
- File size: {transferred_data['file_info']['size_mb']} MB
- Transfer method: {transferred_data['method']}
- Data path: {transferred_data.get('container_path', transferred_data.get('transferred_path'))}
"""

    return enhanced_request


def _process_analysis_result(
    result: Dict[str, Any],
    analysis_type: str,
    transferred_data: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Process analysis result"""

    processed = {
        "success": result.get("success", False),
        "analysis_type": analysis_type,
        "final_code": result.get("final_code", ""),
        "attempts": result.get("attempts", 0),
        "execution_result": {
            "stdout": result.get("stdout", ""),
            "stderr": result.get("stderr", ""),
            "execution_time": result.get("execution_time", 0.0),
            "visualizations": result.get("visualizations", []),
        },
    }

    if result.get("success", False):
        # Additional info on success
        processed["summary"] = result.get("summary", {})
        processed["performance_metrics"] = {
            "total_attempts": result.get("attempts", 0),
            "successful_attempt": result.get("successful_attempt"),
            "execution_time": result.get("execution_time", 0.0),
            "visualizations_generated": len(result.get("visualizations", [])),
        }

        # Data transfer info
        if transferred_data:
            processed["data_transfer"] = {
                "method": transferred_data["method"],
                "original_size": transferred_data["file_info"]["size_mb"],
                "transfer_success": True,
            }
    else:
        # Error analysis on failure
        processed["error_analysis"] = {
            "error_message": result.get("error_message", "Unknown error"),
            "failed_attempts": result.get("failed_attempts", []),
            "error_patterns": result.get("summary", {}).get("error_patterns", {}),
            "suggestions": _generate_error_suggestions(result),
        }

    return processed


def _generate_error_suggestions(result: Dict[str, Any]) -> List[str]:
    """Generate fix suggestions based on errors"""
    suggestions = []

    error_message = result.get("error_message", "").lower()

    if "import" in error_message and "no module" in error_message:
        suggestions.append("Check and install missing Python libraries")
        suggestions.append("Add correct import statements")

    if "file" in error_message and (
        "not found" in error_message or "no such file" in error_message
    ):
        suggestions.append("Check if file path is correct")
        suggestions.append("Verify file permissions and accessibility")

    if "memory" in error_message or "out of memory" in error_message:
        suggestions.append("Reduce dataset size or use data sampling")
        suggestions.append("Optimize memory usage, avoid large objects")

    if "timeout" in error_message:
        suggestions.append("Optimize algorithm complexity")
        suggestions.append("Increase execution time limit")

    if "syntax" in error_message:
        suggestions.append("Check code syntax errors")
        suggestions.append("Verify bracket and quote pairing")

    if suggestions == []:
        suggestions.append("Check code logic and data compatibility")
        suggestions.append("Try to simplify analysis steps")

    return suggestions
