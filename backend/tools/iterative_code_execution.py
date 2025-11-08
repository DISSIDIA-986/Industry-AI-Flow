"""可迭代代码执行工具 - 集成自我修复机制的智能代码执行"""

import asyncio
import logging
from typing import Annotated, Any, Dict, List, Optional

from langchain_core.tools import tool

from backend.agents.code_execution_agent import iterative_code_agent
from backend.services.data_transfer import data_transfer

logger = logging.getLogger(__name__)


@tool
def iterative_code_analysis_tool(
    request: Annotated[str, "数据分析请求描述"],
    data_file: Annotated[Optional[str], "数据文件路径（可选）"] = None,
    analysis_type: Annotated[
        str, "分析类型：'eda', 'ml_model', 'visualization', 'statistical'"
    ] = "eda",
    max_attempts: Annotated[int, "最大修复尝试次数"] = 5,
    transfer_method: Annotated[
        str, "数据传递方式：'auto', 'file_mapping', 'database'"
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
        data_file: 数据文件路径（可选）
        analysis_type: 分析类型
        max_attempts: 最大修复尝试次数
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
        ...     print(f"分析成功，执行了 {result['attempts']} 次尝试")
        ...     print(f"生成了 {len(result['visualizations'])} 个可视化图表")
    """

    try:
        # 准备数据文件（如果提供）
        transferred_data = None
        context = {"analysis_type": analysis_type}

        if data_file:
            logger.info(f"处理数据文件: {data_file}")

            # 传递数据文件
            transfer_result = data_transfer.transfer_file_for_docker(
                data_file, transfer_method
            )

            if not transfer_result["success"]:
                return {
                    "success": False,
                    "error": f"数据文件传递失败: {transfer_result.get('error', 'Unknown error')}",
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

            # 为代码执行准备数据文件路径
            if transfer_result["method"] == "file_mapping":
                data_file_for_execution = transfer_result["transferred_path"]
            else:
                # 数据库方式，使用配置文件
                data_file_for_execution = transfer_result.get("config_file")

        # 构建增强的分析请求
        enhanced_request = _build_enhanced_request(
            request, analysis_type, transferred_data
        )

        # 异步执行可迭代分析
        try:
            # 在同步环境中运行异步代码
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
            logger.error(f"可迭代执行异常: {e}")
            return {
                "success": False,
                "error": f"代码执行异常: {str(e)}",
                "analysis_type": analysis_type,
                "attempts": 0,
            }

        # 后处理结果
        processed_result = _process_analysis_result(
            result, analysis_type, transferred_data
        )

        # 清理传递的数据
        if transferred_data:
            cleanup_success = data_transfer.cleanup_transferred_data(transferred_data)
            processed_result["cleanup_success"] = cleanup_success

        return processed_result

    except Exception as e:
        logger.error(f"可迭代代码分析工具异常: {e}")
        return {
            "success": False,
            "error": f"工具异常: {str(e)}",
            "analysis_type": analysis_type,
            "attempts": 0,
        }


@tool
def self_healing_code_execution_tool(
    code: Annotated[str, "要执行的 Python 代码"],
    description: Annotated[str, "代码描述和预期结果"],
    data_files: Annotated[Optional[List[str]], "依赖的数据文件列表"] = None,
    max_attempts: Annotated[int, "最大自我修复尝试次数"] = 5,
    auto_fix_imports: Annotated[bool, "是否自动修复导入错误"] = True,
) -> Dict[str, Any]:
    """
    自我修复代码执行工具 - 智能修复执行错误的代码运行器

    这个工具专门用于执行可能有问题的 Python 代码，并在遇到错误时自动修复：
    1. **导入错误自动修复**: 检测缺失的导入并自动添加
    2. **语法错误修正**: 修复常见的语法问题
    3. **变量未定义**: 自动定义常用的变量
    4. **文件路径修复**: 修正文件访问路径
    5. **类型错误处理**: 添加必要的类型转换
    6. **索引边界检查**: 修复数组/列表越界问题

    修复策略：
    - 第一次尝试：执行原始代码
    - 第二次尝试：添加缺失的导入
    - 第三次尝试：修复语法错误
    - 第四次尝试：定义未使用的变量
    - 第五次尝试：修复文件路径和类型转换

    Args:
        code: 要执行的 Python 代码
        description: 代码描述和预期结果
        data_files: 依赖的数据文件列表
        max_attempts: 最大自我修复尝试次数
        auto_fix_imports: 是否自动修复导入错误

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
        df = read_csv('data.csv')  # 缺少 pandas 导入
        print(df.head())
        '''
        >>> result = self_healing_code_execution_tool.invoke({
        ...     "code": code,
        ...     "description": "读取并显示数据前几行"
        ... })
        >>> print(f"修复成功: {result['success']}")
        >>> print(f"应用修复: {result['fixes_applied']}")
    """

    try:
        # 准备数据文件
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

        # 构建执行请求
        execution_request = f"""
执行以下 Python 代码：

描述: {description}

要求:
1. 执行代码并返回结果
2. 如果遇到错误，自动修复并重试
3. 最多尝试 {max_attempts} 次
4. 保持代码的核心逻辑不变

代码:
```python
{code}
```
"""

        # 异步执行自我修复
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
            logger.error(f"自我修复执行异常: {e}")
            return {
                "success": False,
                "error": f"执行异常: {str(e)}",
                "final_code": code,
                "attempts": 0,
                "fixes_applied": [],
            }

        # 提取修复信息
        fixes_applied = []
        if "attempts" in result and len(result["attempts"]) > 1:
            for attempt in result["attempts"][1:]:  # 跳过第一次原始尝试
                if attempt.fixes_applied:
                    fixes_applied.extend(attempt.fixes_applied)

        # 清理数据文件
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
        logger.error(f"自我修复工具异常: {e}")
        return {
            "success": False,
            "error": f"工具异常: {str(e)}",
            "final_code": code,
            "attempts": 0,
            "fixes_applied": [],
        }


def _build_enhanced_request(
    request: str, analysis_type: str, transferred_data: Optional[Dict[str, Any]] = None
) -> str:
    """构建增强的分析请求"""

    # 根据分析类型添加特定要求
    type_requirements = {
        "eda": """
探索性数据分析要求：
1. 数据概览：形状、类型、缺失值
2. 描述性统计：均值、中位数、标准差等
3. 分布分析：直方图、箱线图、密度图
4. 相关性分析：相关性矩阵和热力图
5. 异常值检测：识别和可视化异常值
6. 数据质量：重复值、缺失值模式分析
""",
        "ml_model": """
机器学习模型要求：
1. 数据预处理：特征工程、数据清洗
2. 特征选择：相关性分析、重要性排序
3. 模型选择：至少尝试2-3种算法
4. 模型训练：交叉验证、超参数调优
5. 模型评估：准确率、精确率、召回率、F1分数
6. 结果解释：特征重要性、模型可解释性
""",
        "visualization": """
数据可视化要求：
1. 基础图表：柱状图、折线图、散点图
2. 统计图表：箱线图、小提琴图、热力图
3. 交互式图表：使用 plotly 创建可交互图表
4. 多维可视化：3D图表、平行坐标图
5. 美化图表：设置标题、标签、颜色主题
6. 保存图片：高清输出多种格式
""",
        "statistical": """
统计分析要求：
1. 描述性统计：完整的数据摘要
2. 假设检验：t检验、卡方检验等
3. 相关性分析：Pearson、Spearman相关系数
4. 方差分析：单因素、多因素方差分析
5. 回归分析：线性回归、多项式回归
6. 置信区间：参数估计的置信区间
""",
    }

    requirements = type_requirements.get(analysis_type, "")

    enhanced_request = f"""
用户请求: {request}

分析类型: {analysis_type}

{requirements}

代码要求：
1. 使用 pandas, numpy, matplotlib, seaborn 等库
2. 设置中文字体支持，确保中文标签和标题正确显示
3. 代码要有详细的注释
4. 生成高清可视化图表
5. 输出结构化的分析结果
6. 包含错误处理机制
7. 保存所有图表文件到 /workspace/output/

中文字体支持代码（请在代码开头添加）：
```python
import sys
try:
    if '/app/utils' not in sys.path:
        sys.path.insert(0, '/app/utils')
    import matplotlib_chinese_support
    matplotlib_chinese_support.setup_chinese_matplotlib()
    print("✓ 已启用中文字体支持")
except ImportError:
    plt.rcParams['font.sans-serif'] = ['SimHei', 'WenQuanYi Zen Hei', 'Arial Unicode MS', 'DejaVu Sans']
    plt.rcParams['axes.unicode_minus'] = False
    print("✓ 使用备用中文字体配置")
```
"""

    if transferred_data:
        enhanced_request += f"""

数据文件信息：
- 文件名: {transferred_data['file_info']['name']}
- 文件大小: {transferred_data['file_info']['size_mb']} MB
- 传递方式: {transferred_data['method']}
- 数据路径: {transferred_data.get('container_path', transferred_data.get('transferred_path'))}
"""

    return enhanced_request


def _process_analysis_result(
    result: Dict[str, Any],
    analysis_type: str,
    transferred_data: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """处理分析结果"""

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
        # 成功时的额外信息
        processed["summary"] = result.get("summary", {})
        processed["performance_metrics"] = {
            "total_attempts": result.get("attempts", 0),
            "successful_attempt": result.get("successful_attempt"),
            "execution_time": result.get("execution_time", 0.0),
            "visualizations_generated": len(result.get("visualizations", [])),
        }

        # 数据传递信息
        if transferred_data:
            processed["data_transfer"] = {
                "method": transferred_data["method"],
                "original_size": transferred_data["file_info"]["size_mb"],
                "transfer_success": True,
            }
    else:
        # 失败时的错误分析
        processed["error_analysis"] = {
            "error_message": result.get("error_message", "Unknown error"),
            "failed_attempts": result.get("failed_attempts", []),
            "error_patterns": result.get("summary", {}).get("error_patterns", {}),
            "suggestions": _generate_error_suggestions(result),
        }

    return processed


def _generate_error_suggestions(result: Dict[str, Any]) -> List[str]:
    """根据错误生成修复建议"""
    suggestions = []

    error_message = result.get("error_message", "").lower()

    if "import" in error_message and "no module" in error_message:
        suggestions.append("检查并安装缺失的 Python 库")
        suggestions.append("添加正确的 import 语句")

    if "file" in error_message and (
        "not found" in error_message or "no such file" in error_message
    ):
        suggestions.append("检查文件路径是否正确")
        suggestions.append("确认文件权限和可访问性")

    if "memory" in error_message or "out of memory" in error_message:
        suggestions.append("减少数据集大小或使用数据采样")
        suggestions.append("优化内存使用，避免大对象")

    if "timeout" in error_message:
        suggestions.append("优化算法复杂度")
        suggestions.append("增加执行时间限制")

    if "syntax" in error_message:
        suggestions.append("检查代码语法错误")
        suggestions.append("验证括号、引号等配对")

    if suggestions == []:
        suggestions.append("检查代码逻辑和数据兼容性")
        suggestions.append("尝试简化分析步骤")

    return suggestions
