"""EN Agent - EN RAG EN"""

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


def _classify_user_intent(question: str) -> str:
    """
    EN

    Args:
        question: EN

    Returns:
        EN:'knowledge', 'data_analysis', 'mixed'
    """
    question_lower = question.lower()

    # EN
    data_analysis_keywords = [
        "EN",
        "EN",
        "EN",
        "EN",
        "EN",
        "EN",
        "EN",
        "EN",
        "EN",
        "EN",
        "EN",
        "EN",
        "EN",
        "eda",
        "EN",
        "EN",
        "EN",
        "EN",
        "EN",
        "EN",
        "EN",
    ]

    # EN
    knowledge_keywords = [
        "EN",
        "EN",
        "EN",
        "EN",
        "EN",
        "EN",
        "EN",
        "EN",
        "EN",
        "EN",
        "EN",
        "EN",
        "EN",
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
        return "knowledge"  # EN


def build_unified_agent():
    """
    EN Agent - EN RAG EN

    EN:
    1. EN:EN
    2. EN:EN
    3. EN:EN
    4. EN:EN
    5. EN:EN

    Returns:
        EN Agent EN
    """

    # 1. ENLLM
    llm = _get_llm()

    # 2. EN
    system_prompt = """EN,EN.

**EN**:
1. **EN**:EN
2. **EN**:EN,EN
3. **EN**:EN Python EN
4. **EN**:EN

**EN**:
1. **EN**:EN,EN
   - EN → EN RAG EN
   - EN → EN
   - EN → EN

2. **EN**:
   - EN `hybrid_retrieval_tool` EN(EN top_k=10)
   - EN `rerank_tool` EN top-5 EN
   - EN

3. **EN**:
   - EN `iterative_code_analysis_tool` EN(EN)
   - EN `self_healing_code_execution_tool` EN
   - EN `data_analysis_tool` EN
   - EN `visualization_tool` EN
   - EN,EN `data_preprocessing_tool` EN
   - EN,EN `code_execution_tool` EN

4. **EN**:
   - EN
   - EN
   - EN

**EN**:

**RAG EN**:
- `hybrid_retrieval_tool`: EN
- `rerank_tool`: EN

**EN**:
- `code_execution_tool`: EN Python EN
- `code_validation_tool`: EN
- `get_execution_environment_info`: EN

**EN(LangChain 1.0 EN)**:
- `iterative_code_analysis_tool`: EN,EN
  - EN,ENEDA,EN,EN
  - EN,EN
  - EN5EN,EN
- `self_healing_code_execution_tool`: EN
  - EN Python EN
  - EN,EN,EN
  - EN

**EN**:
- `data_analysis_tool`: EN
- `data_preprocessing_tool`: EN

**EN**:
- `visualization_tool`: EN
- `advanced_visualization_tool`: EN
- `dashboard_generation_tool`: EN

**EN**:
1. EN
2. EN,EN"EN,EN"
3. EN,EN,EN
4. EN,EN
5. EN,EN
6. EN,EN,EN

**EN**:
EN:
1. EN
2. EN(EN)
3. EN
4. EN(EN)
5. EN

**EN(LangChain 1.0 EN)**:
- **EN**: EN
- **EN**: EN,EN
- **EN**: EN5EN,EN
- **EN**: EN
- **EN**: EN

**EN**:
- EN Docker EN
- EN {code_execution_timeout} EN
- EN {code_execution_memory_limit}
- EN
- EN,EN
""".format(
        code_execution_timeout=getattr(settings, "code_execution_timeout", 300),
        code_execution_memory_limit=getattr(
            settings, "code_execution_memory_limit", "1G"
        ),
    )

    # 3. EN
    tools = [
        # RAG EN
        hybrid_retrieval_tool,
        rerank_tool,
        # EN
        code_execution_tool,
        code_validation_tool,
        get_execution_environment_info,
        # EN
        data_analysis_tool,
        data_preprocessing_tool,
        # EN
        visualization_tool,
        advanced_visualization_tool,
        dashboard_generation_tool,
    ]

    # EN,EN
    if getattr(settings, "enable_iterative_execution", True):
        tools.extend([iterative_code_analysis_tool, self_healing_code_execution_tool])

    # 4. EN Agent
    agent = create_agent_compat(
        model=llm,
        tools=tools,
        system_prompt=system_prompt,
        # state_schema=RAGAgentState,  # EN,EN
        max_iterations=getattr(settings, "max_code_fix_attempts", 5),  # EN
    )

    return agent


class UnifiedAgentOrchestrator:
    """EN Agent EN - EN"""

    def __init__(self):
        """EN"""
        self.agent = get_unified_agent()
        self.logger = logging.getLogger(__name__)

    def process_request(self, question: str, **kwargs) -> Dict[str, Any]:
        """
        EN

        Args:
            question: EN
            **kwargs: EN(EN)

        Returns:
            EN
        """
        try:
            # 1. EN
            intent = _classify_user_intent(question)
            self.logger.info(f"EN: {intent}")

            # 2. EN
            enhanced_input = self._enhance_input_by_intent(question, intent, **kwargs)

            # 3. EN Agent
            result = self.agent.invoke(enhanced_input)

            # 4. EN
            processed_result = self._process_result_by_intent(result, intent)

            return {
                "success": True,
                "intent": intent,
                "question": question,
                "result": processed_result,
                "raw_response": result,
            }

        except Exception as e:
            self.logger.error(f"EN Agent EN: {e}")
            return {
                "success": False,
                "error": str(e),
                "intent": "unknown",
                "question": question,
            }

    def _enhance_input_by_intent(
        self, question: str, intent: str, **kwargs
    ) -> Dict[str, Any]:
        """EN"""
        base_input = {"messages": [], "question": question}

        if intent == "data_analysis":
            # EN,EN
            if "data_file" in kwargs:
                base_input["data_file"] = kwargs["data_file"]
                base_input["question"] += f"\n\nEN: {kwargs['data_file']}"

            # EN
            base_input["question"] += "\n\nEN,EN,EN."

        elif intent == "knowledge":
            # EN,EN
            base_input["question"] += "\n\nEN,EN."

        elif intent == "mixed":
            # EN,EN
            if "data_file" in kwargs:
                base_input["data_file"] = kwargs["data_file"]
                base_input["question"] += f"\n\nEN: {kwargs['data_file']}"

            base_input["question"] += "\n\nEN,EN."

        return base_input

    def _process_result_by_intent(
        self, result: Dict[str, Any], intent: str
    ) -> Dict[str, Any]:
        """EN"""
        processed = {
            "answer": "",
            "sources": [],
            "visualizations": [],
            "data_analysis": {},
            "code_execution": {},
            "confidence": "medium",
        }

        # EN
        if "messages" in result:
            messages = result["messages"]
            if messages:
                # EN
                last_message = messages[-1]
                if hasattr(last_message, "content"):
                    processed["answer"] = last_message.content
                else:
                    processed["answer"] = str(last_message)

        # EN
        if intent in ["knowledge", "mixed"]:
            # EN
            processed["sources"] = self._extract_sources(result)

        if intent in ["data_analysis", "mixed"]:
            # EN
            processed["data_analysis"] = self._extract_analysis_results(result)
            processed["visualizations"] = self._extract_visualizations(result)
            processed["code_execution"] = self._extract_code_execution_results(result)

        return processed

    def _extract_sources(self, result: Dict[str, Any]) -> List[str]:
        """EN"""
        sources = []

        # EN
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
        """EN"""
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
        """EN"""
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
        """EN"""
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
