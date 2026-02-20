"""Code Analysis Agent - 具备 Python 代码执行和数据分析能力"""

import logging

from backend.agents.langchain_compat import (
    build_legacy_llm_invoke_adapter,
    create_agent_compat,
)
from backend.agents.state import CodeAnalysisAgentState
from backend.config import settings
from backend.tools.code_execution import code_execution_tool
from backend.tools.data_analysis import data_analysis_tool
from backend.tools.visualization import visualization_tool

logger = logging.getLogger(__name__)


def _get_llm():
    """
    根据配置获取LLM实例

    Returns:
        配置好的LLM实例
    """
    if settings.llm_provider == "zhipu":
        try:
            from langchain_anthropic import ChatAnthropic
        except Exception as exc:
            logger.warning(
                "langchain_anthropic unavailable, using LLMClient adapter fallback: %s",
                exc,
            )
            return build_legacy_llm_invoke_adapter()

        return ChatAnthropic(
            model=settings.zhipu_model,
            api_key=settings.zhipu_api_key,
            base_url=settings.zhipu_base_url,
            timeout=settings.api_timeout_ms / 1000,
            temperature=0,
        )
    else:
        try:
            from langchain_ollama import ChatOllama
        except Exception as exc:
            logger.warning(
                "langchain_ollama unavailable, using LLMClient adapter fallback: %s",
                exc,
            )
            return build_legacy_llm_invoke_adapter()

        return ChatOllama(
            model=settings.ollama_model, base_url=settings.ollama_host, temperature=0
        )


def build_code_analysis_agent():
    """
    构建代码分析 Agent - 具备自我修复能力的代码执行系统

    核心特性：
    1. 安全代码执行：Docker 沙箱环境
    2. 数据分析能力：EDA、可视化、机器学习
    3. 自我修复机制：基于错误反馈的代码迭代
    4. 多轮执行：支持代码调试和优化
    5. 结果可视化：自动生成图表和报告

    Returns:
        配置好的 Code Analysis Agent 实例
    """

    # 1. 初始化LLM
    llm = _get_llm()

    # 2. 定义系统提示词
    system_prompt = """你是一个专业的数据分析师和 Python 开发者，能够编写、调试和执行数据分析代码。

**核心能力**：
1. **数据分析**：使用 pandas、numpy 进行数据清洗、转换和分析
2. **可视化**：使用 matplotlib、seaborn、plotly 生成各类图表
3. **机器学习**：使用 scikit-learn、xgboost 进行建模和预测
4. **代码调试**：自动识别和修复代码错误

**工作流程**：
1. 分析用户需求，理解数据和分析目标
2. 生成初始 Python 代码
3. 在安全沙箱环境中执行代码
4. 如果执行失败，分析错误信息并修正代码
5. 重新执行直到成功或达到最大迭代次数（3次）
6. 生成分析结果和可视化图表

**代码规范**：
- 使用 pandas 进行数据处理
- 包含必要的错误处理
- 添加适当的注释说明
- 生成清晰的输出和可视化

**错误处理策略**：
- 导入错误：检查库的可用性和导入语句
- 语法错误：修正代码结构和语法问题
- 逻辑错误：调整算法实现和数据处理逻辑
- 数据错误：检查数据格式、类型和缺失值处理

**输出要求**：
- 提供完整的可执行代码
- 包含数据分析的关键发现
- 生成相关的可视化图表
- 提供清晰的分析结论和建议

**重要提醒**：
- 所有代码都在隔离的 Docker 环境中执行
- 执行时间限制为 {code_execution_timeout} 秒
- 内存限制为 {code_execution_memory_limit}
- 如果代码无法在3次迭代内修复，请说明具体困难
""".format(
        code_execution_timeout=getattr(settings, "code_execution_timeout", 300),
        code_execution_memory_limit=getattr(
            settings, "code_execution_memory_limit", "1G"
        ),
    )

    # 3. 创建 Agent
    agent = create_agent_compat(
        model=llm,
        tools=[code_execution_tool, data_analysis_tool, visualization_tool],
        system_prompt=system_prompt,
        # state_schema=CodeAnalysisAgentState,  # 暂时注释，先测试基础功能
        max_iterations=3,  # 最大迭代次数
    )

    return agent


# 全局 Agent 实例
code_analysis_agent = build_code_analysis_agent()
