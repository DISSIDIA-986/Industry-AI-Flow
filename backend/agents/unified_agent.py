"""Unified Agent - combines RAG retrieval with data analysis capabilities."""

import logging
import threading
from typing import Any, Dict, List, Optional

from backend.agents.langchain_compat import (
    build_legacy_llm_invoke_adapter,
    create_agent_compat,
)
from backend.agents.state import CodeAnalysisAgentState, RAGAgentState
from backend.config import settings
from backend.tools.code_execution import (
    code_execution_tool,
    code_validation_tool,
    get_execution_environment_info,
)
from backend.tools.data_analysis import data_analysis_tool, data_preprocessing_tool
from backend.tools.iterative_code_execution import (
    iterative_code_analysis_tool,
    self_healing_code_execution_tool,
)
from backend.tools.reranker import rerank_tool
from backend.tools.retrieval import hybrid_retrieval_tool
from backend.tools.visualization import (
    advanced_visualization_tool,
    dashboard_generation_tool,
    visualization_tool,
)

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


def _classify_user_intent(question: str) -> str:
    """Classify user intent for the unified agent.

    Args:
        question: The user's question text.

    Returns:
        One of: 'knowledge', 'data_analysis', 'mixed'
    """
    question_lower = question.lower()

    data_analysis_keywords = [
        "analyze",
        "analysis",
        "statistics",
        "chart",
        "graph",
        "plot",
        "visualize",
        "visualization",
        "dataset",
        "data",
        "trend",
        "compare",
        "correlation",
        "eda",
        "distribution",
        "histogram",
        "scatter",
        "regression",
        "average",
        "mean",
        "summary",
    ]

    knowledge_keywords = [
        "what is",
        "how to",
        "explain",
        "define",
        "describe",
        "properties",
        "requirements",
        "standard",
        "regulation",
        "specification",
        "code requirement",
        "building code",
        "construction",
    ]

    data_score = sum(
        1 for keyword in data_analysis_keywords if keyword in question_lower
    )
    knowledge_score = sum(
        1 for keyword in knowledge_keywords if keyword in question_lower
    )

    if data_score > knowledge_score and data_score > 0:
        return "data_analysis"
    elif knowledge_score > data_score and knowledge_score > 0:
        return "knowledge"
    elif data_score == knowledge_score and data_score > 0:
        return "mixed"
    else:
        return "knowledge"  # Default to knowledge retrieval


def build_unified_agent():
    """
    Build the unified agent combining RAG retrieval and data analysis.

    Steps:
    1. Initialize the LLM backend
    2. Define the system prompt with tool descriptions
    3. Register all available tools
    4. Optionally enable iterative execution tools
    5. Create and return the agent

    Returns:
        A configured unified agent instance.
    """

    # 1. Initialize LLM
    llm = _get_llm()

    # 2. System prompt
    system_prompt = """You are a construction industry AI assistant with access to specialized tools.

**Core Capabilities**:
1. **Knowledge Retrieval**: Answer questions about construction standards, regulations, and best practices using RAG.
2. **Data Analysis**: Analyze construction datasets, generate statistics, charts, and insights.
3. **Code Execution**: Run Python code for calculations, data processing, and analysis.
4. **Visualization**: Create charts, graphs, and dashboards from construction data.

**Workflow**:
1. **Understand the request**: Classify what the user needs:
   - Knowledge question → Use RAG retrieval tools
   - Data analysis → Use analysis and visualization tools
   - Calculation → Use code execution tools

2. **Knowledge retrieval**:
   - Use `hybrid_retrieval_tool` to search the document database (default top_k=10)
   - Use `rerank_tool` to select the top-5 most relevant results
   - Always cite sources in your response

3. **Data analysis**:
   - Use `iterative_code_analysis_tool` for multi-step analysis (preferred)
   - Use `self_healing_code_execution_tool` for error-resilient code execution
   - Use `data_analysis_tool` for standard statistical analysis
   - Use `visualization_tool` for creating charts
   - For data quality issues, use `data_preprocessing_tool` first
   - For simple scripts, use `code_execution_tool` directly

4. **Response quality**:
   - Always provide clear, well-structured answers
   - Include relevant citations and data sources
   - If unsure, say so rather than guessing

**Available Tools**:

**RAG Retrieval**:
- `hybrid_retrieval_tool`: Search construction document database using hybrid BM25+vector retrieval
- `rerank_tool`: Re-rank retrieved documents for relevance

**Code Execution**:
- `code_execution_tool`: Execute Python code in a sandboxed environment
- `code_validation_tool`: Validate code before execution
- `get_execution_environment_info`: Check available execution environment

**Iterative Analysis (LangChain 1.0 Tools)**:
- `iterative_code_analysis_tool`: Multi-step data analysis with automatic iteration
  - Analyzes datasets, generates EDA reports, statistical summaries, and insights
  - Automatically retries on errors with corrected code
  - Runs up to 5 iterations for convergence
- `self_healing_code_execution_tool`: Error-resilient code execution
  - Executes Python code with automatic error detection
  - On failure, analyzes the error, generates a fix, and retries
  - Suitable for complex calculations

**Data Processing**:
- `data_analysis_tool`: Statistical analysis on uploaded datasets
- `data_preprocessing_tool`: Clean and transform data before analysis

**Visualization**:
- `visualization_tool`: Create standard charts and plots
- `advanced_visualization_tool`: Create complex multi-panel visualizations
- `dashboard_generation_tool`: Generate interactive data dashboards

**Important Guidelines**:
1. Always understand the user's intent before selecting tools
2. For knowledge questions, always cite sources — never fabricate answers
3. For data analysis, validate data quality before running complex analyses
4. Handle errors gracefully and explain what went wrong
5. Provide results in a clear, professional format
6. When uncertain about the question, ask for clarification

**Security Constraints**:
- Code runs in a Docker sandbox
- Maximum execution time: {code_execution_timeout} seconds
- Memory limit: {code_execution_memory_limit}
- Network access is restricted
- Only approved Python libraries are available
""".format(
        code_execution_timeout=getattr(settings, "code_execution_timeout", 300),
        code_execution_memory_limit=getattr(
            settings, "code_execution_memory_limit", "1G"
        ),
    )

    # 3. Register tools
    tools = [
        # RAG retrieval tools
        hybrid_retrieval_tool,
        rerank_tool,
        # Code execution tools
        code_execution_tool,
        code_validation_tool,
        get_execution_environment_info,
        # Data analysis tools
        data_analysis_tool,
        data_preprocessing_tool,
        # Visualization tools
        visualization_tool,
        advanced_visualization_tool,
        dashboard_generation_tool,
    ]

    # Add iterative execution tools if enabled
    if getattr(settings, "enable_iterative_execution", True):
        tools.extend([iterative_code_analysis_tool, self_healing_code_execution_tool])

    # 4. Create the unified agent
    agent = create_agent_compat(
        model=llm,
        tools=tools,
        system_prompt=system_prompt,
        # state_schema=RAGAgentState,  # Disabled; using default state schema
        max_iterations=getattr(settings, "max_code_fix_attempts", 5),  # Max tool iterations
    )

    return agent


class UnifiedAgentOrchestrator:
    """Unified Agent Orchestrator - routes requests to the appropriate agent pipeline."""

    def __init__(self):
        """Initialize the orchestrator with a shared unified agent instance."""
        self.agent = get_unified_agent()
        self.logger = logging.getLogger(__name__)

    def process_request(self, question: str, **kwargs) -> Dict[str, Any]:
        """
        Process a user request through the unified agent pipeline.

        Args:
            question: The user's question text.
            **kwargs: Additional parameters (e.g., data_file path).

        Returns:
            A dict with success status, intent, question, and result.
        """
        try:
            # 1. Classify intent
            intent = _classify_user_intent(question)
            self.logger.info(f"Classified intent: {intent}")

            # 2. Enhance input based on intent
            enhanced_input = self._enhance_input_by_intent(question, intent, **kwargs)

            # 3. Invoke the unified agent
            result = self.agent.invoke(enhanced_input)

            # 4. Process result based on intent
            processed_result = self._process_result_by_intent(result, intent)

            return {
                "success": True,
                "intent": intent,
                "question": question,
                "result": processed_result,
                "raw_response": result,
            }

        except Exception as e:
            self.logger.error(f"Unified agent processing failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "intent": "unknown",
                "question": question,
            }

    def _enhance_input_by_intent(
        self, question: str, intent: str, **kwargs
    ) -> Dict[str, Any]:
        """Enhance the agent input with intent-specific context."""
        base_input = {"messages": [], "question": question}

        if intent == "data_analysis":
            # Attach data file path if provided
            if "data_file" in kwargs:
                base_input["data_file"] = kwargs["data_file"]
                base_input["question"] += f"\n\nData file: {kwargs['data_file']}"

            # Add data analysis instructions
            base_input["question"] += "\n\nPlease analyze this data, generate statistics, and provide visualizations."

        elif intent == "knowledge":
            # Add knowledge retrieval instructions
            base_input["question"] += "\n\nPlease search the knowledge base and cite your sources."

        elif intent == "mixed":
            # Attach data file and combine both instruction sets
            if "data_file" in kwargs:
                base_input["data_file"] = kwargs["data_file"]
                base_input["question"] += f"\n\nData file: {kwargs['data_file']}"

            base_input["question"] += "\n\nPlease combine knowledge retrieval with data analysis."

        return base_input

    def _process_result_by_intent(
        self, result: Dict[str, Any], intent: str
    ) -> Dict[str, Any]:
        """Process the agent result based on the classified intent."""
        processed = {
            "answer": "",
            "sources": [],
            "visualizations": [],
            "data_analysis": {},
            "code_execution": {},
            "confidence": "medium",
        }

        # Extract the answer from messages
        if "messages" in result:
            messages = result["messages"]
            if messages:
                # Get the last message as the final answer
                last_message = messages[-1]
                if hasattr(last_message, "content"):
                    processed["answer"] = last_message.content
                else:
                    processed["answer"] = str(last_message)

        # Extract intent-specific results
        if intent in ["knowledge", "mixed"]:
            # Extract document sources from retrieval steps
            processed["sources"] = self._extract_sources(result)

        if intent in ["data_analysis", "mixed"]:
            # Extract analysis results and visualizations
            processed["data_analysis"] = self._extract_analysis_results(result)
            processed["visualizations"] = self._extract_visualizations(result)
            processed["code_execution"] = self._extract_code_execution_results(result)

        return processed

    def _extract_sources(self, result: Dict[str, Any]) -> List[str]:
        """Extract document source IDs from retrieval tool results."""
        sources = []

        # Search intermediate steps for retrieval tool outputs
        if "intermediate_steps" in result:
            for step in result["intermediate_steps"]:
                if len(step) >= 2:
                    tool_call, tool_result = step[0], step[1]
                    if hasattr(tool_call, "tool") and "retrieval" in tool_call.tool:
                        if isinstance(tool_result, list):
                            for doc in tool_result:
                                if isinstance(doc, dict) and "doc_id" in doc:
                                    sources.append(doc["doc_id"])

        return sources

    def _extract_analysis_results(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """Extract data analysis results from tool execution steps."""
        analysis_results = {}

        if "intermediate_steps" in result:
            for step in result["intermediate_steps"]:
                if len(step) >= 2:
                    tool_call, tool_result = step[0], step[1]
                    if hasattr(tool_call, "tool"):
                        if "data_analysis" in tool_call.tool:
                            analysis_results["data_analysis"] = tool_result
                        elif "preprocessing" in tool_call.tool:
                            analysis_results["preprocessing"] = tool_result

        return analysis_results

    def _extract_visualizations(self, result: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract generated visualizations from tool execution steps."""
        visualizations = []

        if "intermediate_steps" in result:
            for step in result["intermediate_steps"]:
                if len(step) >= 2:
                    tool_call, tool_result = step[0], step[1]
                    if hasattr(tool_call, "tool") and "visualization" in tool_call.tool:
                        if (
                            isinstance(tool_result, dict)
                            and "visualizations" in tool_result
                        ):
                            visualizations.extend(tool_result["visualizations"])

        return visualizations

    def _extract_code_execution_results(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """Extract code execution results from tool execution steps."""
        code_results = {}

        if "intermediate_steps" in result:
            for step in result["intermediate_steps"]:
                if len(step) >= 2:
                    tool_call, tool_result = step[0], step[1]
                    if (
                        hasattr(tool_call, "tool")
                        and "code_execution" in tool_call.tool
                    ):
                        if isinstance(tool_result, dict):
                            code_results = tool_result
                            break

        return code_results


_unified_agent: Optional[Any] = None
_unified_orchestrator: Optional[UnifiedAgentOrchestrator] = None
_unified_lock = threading.Lock()


def get_unified_agent():
    """Lazily build unified agent to avoid import-time startup failures."""
    global _unified_agent
    if _unified_agent is None:
        with _unified_lock:
            if _unified_agent is None:
                _unified_agent = build_unified_agent()
    return _unified_agent


def get_unified_orchestrator() -> UnifiedAgentOrchestrator:
    """Lazily build orchestrator and share singleton across requests."""
    global _unified_orchestrator
    if _unified_orchestrator is None:
        with _unified_lock:
            if _unified_orchestrator is None:
                _unified_orchestrator = UnifiedAgentOrchestrator()
    return _unified_orchestrator
