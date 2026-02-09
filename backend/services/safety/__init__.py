"""
安全防护层模块

提供RAG系统的安全防护功能：
- 接地度检查
- 置信度阈值
- 免责声明
- 拒绝回答策略
"""

from backend.services.safety.groundedness_checker import (
    GroundednessChecker,
    SafetyGuard,
    SafetyLevel,
    create_safety_guard,
)

__all__ = [
    "GroundednessChecker",
    "SafetyGuard",
    "SafetyLevel",
    "create_safety_guard",
]
