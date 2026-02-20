"""代码执行工具 - LangChain 工具接口"""

import logging
from typing import Annotated, Any, Dict, List, Optional

from langchain_core.tools import tool

from backend.config import settings
from backend.services.code_executor import (
    CodeExecutionError,
    code_executor,
    get_code_execution_manager,
    validate_code,
)

logger = logging.getLogger(__name__)


def _validation_failure_payload(validation_error: str, warnings: list[str]) -> Dict[str, Any]:
    return {
        "success": False,
        "error": "代码安全检查失败",
        "validation_errors": [validation_error] if validation_error else [],
        "warnings": warnings,
        "stdout": "",
        "stderr": validation_error or "",
        "exit_code": -1,
        "execution_time": 0,
        "visualizations": [],
        "output_files": {},
    }


@tool
def code_execution_tool(
    code: Annotated[str, "要执行的 Python 代码"],
    data_files: Annotated[Optional[List[str]], "数据文件路径列表"] = None,
    timeout: Annotated[Optional[int], "执行超时时间（秒）"] = None,
) -> Dict[str, Any]:
    """
    代码执行工具 - 在安全的 Docker 沙箱环境中执行 Python 代码

    这个工具提供了一个安全的 Python 代码执行环境，支持：
    1. 数据分析：pandas、numpy 数据处理
    2. 可视化：matplotlib、seaborn、plotly 图表生成
    3. 机器学习：scikit-learn、xgboost 模型训练
    4. 安全沙箱：Docker 容器隔离，资源限制

    安全特性：
    - 禁止危险的系统调用（os.system、subprocess 等）
    - 网络访问禁用
    - 资源限制（CPU、内存、时间）
    - 非root用户执行
    - 临时文件系统隔离

    Args:
        code: 要执行的 Python 代码
        data_files: 数据文件路径列表（CSV、Excel等）
        timeout: 执行超时时间（秒），默认使用配置值

    Returns:
        执行结果字典，包含：
        - success: 是否成功执行
        - stdout: 标准输出内容
        - stderr: 错误输出内容
        - exit_code: 退出码
        - execution_time: 执行时间（秒）
        - visualizations: 生成的可视化文件列表
        - error: 错误信息（如果失败）
        - validation_errors: 代码安全检查错误

    Example:
        >>> result = code_execution_tool.invoke({
        ...     "code": "import pandas as pd\\nprint('Hello, Data Analysis!')",
        ...     "data_files": ["/path/to/data.csv"]
        ... })
        >>> print(f"执行成功: {result['success']}")
        >>> print(f"输出: {result['stdout']}")
    """

    manager = get_code_execution_manager()

    # 检查代码执行器是否可用
    if code_executor is None and manager is None:
        return {
            "success": False,
            "error": "代码执行器不可用，请检查 Docker 环境",
            "stdout": "",
            "stderr": "Code executor not available",
            "exit_code": -1,
            "execution_time": 0,
            "visualizations": [],
        }

    # 一律先做静态安全校验，防止 manager 路径绕过校验。
    validation = validate_code(code, strict_mode=True)
    if not validation.is_valid:
        return _validation_failure_payload(
            validation_error=validation.error or "Unknown validation error",
            warnings=validation.warnings,
        )

    try:
        if manager is not None:
            result = manager.execute_code(
                code=code,
                data_files=data_files,
                timeout=timeout,
                mode=settings.code_execution_provider,
            )
        else:
            # 回退到历史执行器实现（仅docker）
            result = code_executor.execute_code(
                code=code, data_files=data_files, timeout=timeout
            )

        # 记录执行日志
        if result["success"]:
            logger.info(f"代码执行成功，耗时 {result['execution_time']:.2f} 秒")
            if result["visualizations"]:
                logger.info(f"生成了 {len(result['visualizations'])} 个可视化文件")
        else:
            logger.warning(f"代码执行失败: {result.get('error', 'Unknown error')}")

        return result

    except Exception as e:
        logger.error(f"代码执行工具异常: {e}")
        return {
            "success": False,
            "error": f"工具执行异常: {str(e)}",
            "stdout": "",
            "stderr": str(e),
            "exit_code": -1,
            "execution_time": 0,
            "visualizations": [],
        }


@tool
def code_validation_tool(code: Annotated[str, "要验证的 Python 代码"]) -> Dict[str, Any]:
    """
    代码验证工具 - 检查 Python 代码的安全性和语法正确性

    这个工具在实际执行前对代码进行安全检查，包括：
    1. 语法检查：确保代码语法正确
    2. 安全检查：检测危险操作和禁用函数
    3. 导入检查：验证导入的模块是否允许
    4. 结构检查：分析代码结构复杂度

    Args:
        code: 要验证的 Python 代码

    Returns:
        验证结果字典，包含：
        - valid: 是否通过验证
        - syntax_errors: 语法错误列表
        - security_errors: 安全错误列表
        - warnings: 警告信息列表
        - suggestions: 改进建议

    Example:
        >>> result = code_validation_tool.invoke({
        ...     "code": "import pandas as pd\\nprint('Hello')"
        ... })
        >>> print(f"代码有效: {result['valid']}")
    """

    if code_executor is None:
        from backend.services.code_executor import validate_code

        validation_result = validate_code(code, strict_mode=True)
        syntax_errors = []
        security_errors = []
        if validation_result.error:
            if "syntax" in validation_result.error.lower() or "语法" in validation_result.error:
                syntax_errors.append(validation_result.error)
            else:
                security_errors.append(validation_result.error)
        return {
            "valid": validation_result.is_valid,
            "syntax_errors": syntax_errors,
            "security_errors": security_errors,
            "warnings": validation_result.warnings,
            "suggestions": ["可在启用 Docker 后进行完整执行前校验"],
        }

    try:
        # 使用执行器的验证功能
        validation_errors = code_executor._validate_code(code)

        # 分类错误
        syntax_errors = []
        security_errors = []

        for error in validation_errors:
            if "语法错误" in error:
                syntax_errors.append(error)
            else:
                security_errors.append(error)

        # 生成建议
        suggestions = []
        if security_errors:
            suggestions.append("移除危险操作，如 os.system、subprocess 等")
        if syntax_errors:
            suggestions.append("修复语法错误")

        return {
            "valid": len(validation_errors) == 0,
            "syntax_errors": syntax_errors,
            "security_errors": security_errors,
            "warnings": [],
            "suggestions": suggestions,
        }

    except Exception as e:
        logger.error(f"代码验证工具异常: {e}")
        return {
            "valid": False,
            "syntax_errors": [f"验证异常: {str(e)}"],
            "security_errors": [],
            "warnings": [],
            "suggestions": [],
        }


@tool
def get_execution_environment_info() -> Dict[str, Any]:
    """
    获取执行环境信息工具 - 返回代码执行环境的详细信息

    这个工具提供当前代码执行环境的配置信息，包括：
    1. Docker 状态：容器运行状态
    2. 资源限制：CPU、内存、时间限制
    3. 可用库：预装的数据分析库列表
    4. 安全配置：安全策略和限制

    Returns:
        环境信息字典，包含：
        - docker_available: Docker 是否可用
        - resource_limits: 资源限制配置
        - available_libraries: 可用库列表
        - security_features: 安全特性列表
        - configuration: 当前配置信息

    Example:
        >>> info = get_execution_environment_info.invoke({})
        >>> print(f"Docker 可用: {info['docker_available']}")
    """

    # 基础配置信息
    config_info = {
        "timeout": settings.code_execution_timeout,
        "memory_limit": settings.code_execution_memory_limit,
        "cpu_limit": settings.code_execution_cpu_limit,
        "docker_image": settings.docker_image_name,
        "temp_dir": settings.temp_data_dir,
        "provider_mode": settings.code_execution_provider,
        "ppio_enabled": settings.enable_ppio_code_execution,
    }

    # 安全特性
    security_features = [
        "Docker 容器隔离",
        "非root用户执行",
        "网络访问禁用",
        "资源限制（CPU/内存/时间）",
        "临时文件系统",
        "代码安全检查",
        "危险操作黑名单",
    ]

    # 可用库列表（基于Docker镜像）
    available_libraries = [
        "pandas",
        "numpy",
        "matplotlib",
        "seaborn",
        "plotly",
        "scikit-learn",
        "xgboost",
        "lightgbm",
        "openpyxl",
        "xlrd",
        "psycopg2-binary",
    ]

    manager = get_code_execution_manager()
    if manager is not None and hasattr(manager, "health_snapshot"):
        health_snapshot = manager.health_snapshot(mode=settings.code_execution_provider)
        docker_state = (
            health_snapshot.get("providers", {}).get("docker") or {}
            if isinstance(health_snapshot.get("providers"), dict)
            else {}
        )
        docker_available = bool(docker_state.get("healthy", False))
        code_execution_available = bool(health_snapshot.get("healthy", False))
    else:
        health_snapshot = {
            "healthy": bool(code_executor is not None),
            "mode": settings.code_execution_provider,
            "selected_provider": "docker",
            "providers": {"docker": {"healthy": bool(code_executor is not None)}},
        }
        docker_available = bool(code_executor is not None)
        code_execution_available = bool(code_executor is not None)

    return {
        "docker_available": docker_available,
        "code_execution_available": code_execution_available,
        "execution_health": health_snapshot,
        "resource_limits": config_info,
        "available_libraries": available_libraries,
        "security_features": security_features,
        "configuration": {
            "enable_docker_sandbox": settings.enable_docker_sandbox,
            "max_iterations": 3,  # Agent 最大迭代次数
            "supported_file_types": [".csv", ".xlsx", ".xls", ".json", ".txt"],
            "visualization_formats": [".png", ".jpg", ".svg", ".html", ".pdf"],
        },
    }
