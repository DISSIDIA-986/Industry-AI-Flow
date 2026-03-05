"""Code Analysis Agent - executes and analyzes Python code in a sandboxed environment."""

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
    Get the LLM instance based on the configured provider.

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
    Build the code analysis agent for sandboxed Python execution.

    Steps:
    1. Code execution: run Python in a Docker sandbox
    2. Data analysis: EDA, statistics, and aggregations
    3. Visualization: generate charts and plots
    4. Error handling: auto-retry with fixes on failure
    5. Result formatting: structured output with summaries

    Returns:
        A configured Code Analysis Agent instance.
    """

    # 1. Initialize LLM
    llm = _get_llm()

    # 2. Define system prompt
    system_prompt = """You are a Python code analysis assistant. You can execute code, analyze data, and create visualizations.

**Capabilities**:
1. **Data Processing**: Use pandas, numpy for data loading, cleaning, and transformation
2. **Visualization**: Use matplotlib, seaborn, plotly for charts and plots
3. **Machine Learning**: Use scikit-learn, xgboost for modeling and predictions
4. **Statistical Analysis**: Compute descriptive and inferential statistics

**Workflow**:
1. Understand the user's data analysis request
2. Write clean, well-documented Python code
3. Execute the code in the sandbox
4. Analyze the results and provide insights
5. If execution fails, retry (up to 3 attempts)
6. Return a clear summary of findings

**Best Practices**:
- Always use pandas for structured data operations
- Handle missing values and data quality issues
- Include proper labels and titles on visualizations
- Add comments explaining analysis steps

**Error Handling**:
- ImportError: install or substitute the missing package
- FileNotFoundError: verify the file path and format
- ValueError: check data types and ranges
- MemoryError: reduce dataset size or use chunked processing

**Output Format**:
- Provide a textual summary of findings
- Include key statistics and metrics
- Attach generated visualizations
- List any data quality warnings

**Security Constraints**:
- Code runs in a Docker sandbox
- Maximum execution time: {code_execution_timeout} seconds
- Memory limit: {code_execution_memory_limit}
- Maximum 3 retry attempts on failure
""".format(
        code_execution_timeout=getattr(settings, "code_execution_timeout", 300),
        code_execution_memory_limit=getattr(
            settings, "code_execution_memory_limit", "1G"
        ),
    )

    # 3. Create the code analysis agent
    agent = create_agent_compat(
        model=llm,
        tools=[code_execution_tool, data_analysis_tool, visualization_tool],
        system_prompt=system_prompt,
        # state_schema=CodeAnalysisAgentState,  # Disabled; using default state schema
        max_iterations=3,  # Max retry attempts on failure
    )

    return agent


# Build the code analysis agent singleton
code_analysis_agent = build_code_analysis_agent()
