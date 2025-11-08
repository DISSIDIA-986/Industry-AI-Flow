"""
代码执行服务包初始化

导出核心组件:
- DockerExecutor: Docker容器代码执行器
- CodeValidator: 代码安全验证器
- execute_python_code: 便捷执行函数
- validate_code: 便捷验证函数
"""

from backend.services.code_executor.docker_executor import (
    DockerExecutor,
    ExecutionResult,
    execute_python_code,
)
from backend.services.code_executor.validator import (
    CodeValidator,
    ValidationResult,
    validate_code,
)

# 创建全局执行器实例（延迟初始化）
_global_executor = None


def get_code_executor() -> DockerExecutor:
    """获取全局代码执行器实例（单例模式）"""
    global _global_executor
    if _global_executor is None:
        try:
            _global_executor = DockerExecutor()
        except Exception as e:
            import logging

            logger = logging.getLogger(__name__)
            logger.error(f"无法初始化代码执行器: {e}")
            _global_executor = None
    return _global_executor


# 为向后兼容性提供code_executor别名
code_executor = get_code_executor()


# 自定义异常
class CodeExecutionError(Exception):
    """代码执行异常"""

    pass


__all__ = [
    "DockerExecutor",
    "ExecutionResult",
    "CodeValidator",
    "ValidationResult",
    "execute_python_code",
    "validate_code",
    "get_code_executor",
    "code_executor",
    "CodeExecutionError",
]
