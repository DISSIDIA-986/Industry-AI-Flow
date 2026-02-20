"""RAG Agent - EN Agent EN."""

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
    ENLLMEN

    EN:
    - ollama: ENOllamaEN(Qwen2.5EN)
    - zhipu: ENAIEN(GLM-4EN,ENAnthropicEN)

    Returns:
        ENLLMEN
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

        # ENAI(ENAnthropicEN)
        return ChatAnthropic(
            model=settings.zhipu_model,
            api_key=settings.zhipu_api_key,
            base_url=settings.zhipu_base_url,
            timeout=settings.api_timeout_ms / 1000,  # EN
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

        # ENOllama(EN)
        return ChatOllama(
            model=settings.ollama_model, base_url=settings.ollama_host, temperature=0
        )


def build_rag_agent():
    """
    ENRAG Agent - ENLangChain 1.0EN

    EN:
    1. ENcreate_agent API:ENAgentEN
    2. TypedDict-basedEN:EN1.0EN
    3. EN:LLMEN
    4. EN:EN → EN → EN
    5. ENLLMEN:OllamaEN + ENAIEN

    Returns:
        ENRAG AgentEN

    Example:
        >>> agent = build_rag_agent()
        >>> result = agent.invoke({
        ...     "messages": [],
        ...     "question": "ENLangChain 1.0EN?"
        ... })
        >>> print(result["final_answer"])
    """

    # 1. ENLLM(EN)
    llm = _get_llm()

    # 2. EN(ENAgentEN)
    system_prompt = """ENRAGEN,EN.

**EN**:
1. EN,EN`hybrid_retrieval_tool`EN(ENtop_k=10)
2. EN`rerank_tool`EN,ENtop-5EN
3. EN,EN,EN

**EN**:
- EN
- EN,EN"EN,EN"
- EN,ENID(doc_id)
- EN,EN,EN
- EN

**EN**:
EN:
1. EN
2. EN(EN:ENdoc-123ENdoc-456)
3. EN(EN,EN)
"""

    # 3. ENAgent(ENLangChain 1.0ENAPI)
    agent = create_agent_compat(
        model=llm,
        tools=[hybrid_retrieval_tool, rerank_tool],
        system_prompt=system_prompt,
        # state_schema=RAGAgentState,  # EN,EN
    )

    return agent


# ENAgentEN(EN)
rag_agent = build_rag_agent()
