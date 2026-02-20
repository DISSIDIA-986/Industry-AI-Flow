"""Code Analysis Agent - EN Python EN"""

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
    ENLLMEN

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
    EN Agent - EN

    EN:
    1. EN:Docker EN
    2. EN:EDA,EN,EN
    3. EN:EN
    4. EN:EN
    5. EN:EN

    Returns:
        EN Code Analysis Agent EN
    """

    # 1. ENLLM
    llm = _get_llm()

    # 2. EN
    system_prompt = """EN Python EN,EN,EN.

**EN**:
1. **EN**:EN pandas,numpy EN,EN
2. **EN**:EN matplotlib,seaborn,plotly EN
3. **EN**:EN scikit-learn,xgboost EN
4. **EN**:EN

**EN**:
1. EN,EN
2. EN Python EN
3. EN
4. EN,EN
5. EN(3EN)
6. EN

**EN**:
- EN pandas EN
- EN
- EN
- EN

**EN**:
- EN:EN
- EN:EN
- EN:EN
- EN:EN,EN

**EN**:
- EN
- EN
- EN
- EN

**EN**:
- EN Docker EN
- EN {code_execution_timeout} EN
- EN {code_execution_memory_limit}
- EN3EN,EN
""".format(
        code_execution_timeout=getattr(settings, "code_execution_timeout", 300),
        code_execution_memory_limit=getattr(
            settings, "code_execution_memory_limit", "1G"
        ),
    )

    # 3. EN Agent
    agent = create_agent_compat(
        model=llm,
        tools=[code_execution_tool, data_analysis_tool, visualization_tool],
        system_prompt=system_prompt,
        # state_schema=CodeAnalysisAgentState,  # EN,EN
        max_iterations=3,  # EN
    )

    return agent


# EN Agent EN
code_analysis_agent = build_code_analysis_agent()
