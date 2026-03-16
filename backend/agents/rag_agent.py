"""RAG Agent - retrieval-augmented generation agent for knowledge queries."""

import logging

from backend.agents.langchain_compat import (
    build_legacy_llm_invoke_adapter,
    create_agent_compat,
)
from backend.agents.state import RAGAgentState
from backend.config import settings
from backend.tools.reranker import rerank_tool
from backend.tools.retrieval import hybrid_retrieval_tool

logger = logging.getLogger(__name__)


def _get_llm():
    """
    Get the LLM instance based on the configured provider.

    Supported providers:
    - ollama: Local Ollama backend (Qwen3.5 models)
    - zhipu: Cloud AI API (GLM-4, via Anthropic-compatible SDK)

    Returns:
        A LangChain-compatible LLM instance.
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

        # Cloud AI via Anthropic-compatible SDK
        return ChatAnthropic(
            model=settings.zhipu_model,
            api_key=settings.zhipu_api_key,
            base_url=settings.zhipu_base_url,
            timeout=settings.api_timeout_ms / 1000,  # Convert ms to seconds
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

        # Local Ollama backend (default)
        return ChatOllama(
            model=settings.ollama_model, base_url=settings.ollama_host, temperature=0
        )


def build_rag_agent():
    """
    Build the RAG Agent using LangChain 1.0 compatible APIs.

    Architecture:
    1. Uses create_agent_compat API to build a tool-calling agent
    2. TypedDict-based state for LangChain 1.0 compatibility
    3. Provider-agnostic LLM initialization
    4. Pipeline: retrieve → rerank → generate answer
    5. Multi-backend LLM support: local Ollama + cloud AI fallback

    Returns:
        A configured RAG Agent instance.

    Example:
        >>> agent = build_rag_agent()
        >>> result = agent.invoke({
        ...     "messages": [],
        ...     "question": "What are the fire safety requirements for high-rise buildings?"
        ... })
        >>> print(result["final_answer"])
    """

    # 1. Initialize LLM (provider-agnostic)
    llm = _get_llm()

    # 2. Define the system prompt (guides agent behavior)
    system_prompt = """You are a RAG-powered construction knowledge assistant. Answer questions accurately based on retrieved documents.

**Workflow**:
1. When a user asks a question, use `hybrid_retrieval_tool` to search the document database (default top_k=10)
2. Use `rerank_tool` to select the top-5 most relevant results
3. Generate a comprehensive answer based on the retrieved documents, citing your sources

**Guidelines**:
- Always base your answers on retrieved documents
- If no relevant documents are found, say "I don't have enough information to answer this question"
- Always cite document IDs (doc_id) in your response
- If the question is ambiguous, ask for clarification before searching
- Respond in clear, professional English

**Response Format**:
Your answer should include:
1. A direct answer to the question
2. Source citations (e.g., Sources: doc-123, doc-456)
3. Confidence note (high, medium, or low based on source relevance)
"""

    # 3. Create the agent (using LangChain 1.0 compatible API)
    agent = create_agent_compat(
        model=llm,
        tools=[hybrid_retrieval_tool, rerank_tool],
        system_prompt=system_prompt,
        # state_schema=RAGAgentState,  # Disabled; using default state schema
    )

    return agent


# Build the RAG agent singleton (initialized at import time)
rag_agent = build_rag_agent()
