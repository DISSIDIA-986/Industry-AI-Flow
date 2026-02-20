"""RAG Agent - 使用统一 Agent 构建接口。"""

import logging

from backend.agents.state import RAGAgentState
from backend.agents.langchain_compat import (
    build_legacy_llm_invoke_adapter,
    create_agent_compat,
)
from backend.config import settings
from backend.tools.reranker import rerank_tool
from backend.tools.retrieval import hybrid_retrieval_tool

logger = logging.getLogger(__name__)


def _get_llm():
    """
    根据配置获取LLM实例

    支持的提供商：
    - ollama: 本地Ollama服务（Qwen2.5等）
    - zhipu: 智谱AI云服务（GLM-4系列，通过Anthropic兼容接口）

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

        # 使用智谱AI（通过Anthropic兼容接口）
        return ChatAnthropic(
            model=settings.zhipu_model,
            api_key=settings.zhipu_api_key,
            base_url=settings.zhipu_base_url,
            timeout=settings.api_timeout_ms / 1000,  # 转换为秒
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

        # 使用本地Ollama（默认）
        return ChatOllama(
            model=settings.ollama_model, base_url=settings.ollama_host, temperature=0
        )


def build_rag_agent():
    """
    构建RAG Agent - 使用LangChain 1.0新特性

    核心特性：
    1. 统一create_agent API：简化Agent创建流程
    2. TypedDict-based状态：符合1.0规范
    3. 工具化检索：LLM自主决策何时检索和重排序
    4. 结构化流程：检索 → 重排序 → 生成答案
    5. 多LLM支持：Ollama本地 + 智谱AI云服务

    Returns:
        配置好的RAG Agent实例

    Example:
        >>> agent = build_rag_agent()
        >>> result = agent.invoke({
        ...     "messages": [],
        ...     "question": "什么是LangChain 1.0的主要改进？"
        ... })
        >>> print(result["final_answer"])
    """

    # 1. 初始化LLM（根据配置选择提供商）
    llm = _get_llm()

    # 2. 定义系统提示词（指导Agent工作流程）
    system_prompt = """你是一个专业的RAG助手，帮助用户基于文档库回答问题。

**工作流程**：
1. 收到用户问题后，使用`hybrid_retrieval_tool`检索相关文档（建议top_k=10）
2. 使用`rerank_tool`对检索结果重排序，获取最相关的top-5文档
3. 基于重排序后的文档，生成准确、简洁的回答

**重要规则**：
- 所有回答必须基于检索到的文档内容
- 如果文档不足以回答问题，明确说"根据现有文档，我无法回答这个问题"
- 引用文档时，注明文档ID（doc_id）
- 保持回答简洁、准确、专业
- 不要编造信息或推测

**输出格式**：
你的回答应该包含：
1. 基于文档的答案
2. 引用的文档来源（如：根据文档doc-123和doc-456）
3. 置信度说明（如果文档支持度不足，需说明）
"""

    # 3. 创建Agent（使用LangChain 1.0统一API）
    agent = create_agent_compat(
        model=llm,
        tools=[hybrid_retrieval_tool, rerank_tool],
        system_prompt=system_prompt,
        # state_schema=RAGAgentState,  # 暂时注释，先测试基础功能
    )

    return agent


# 全局Agent实例（避免重复初始化）
rag_agent = build_rag_agent()
