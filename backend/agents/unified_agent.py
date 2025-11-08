"""统一 Agent - 融合 RAG 和代码分析能力"""

import logging
from typing import Any, Dict, List

from langchain.agents import create_agent
from langchain_anthropic import ChatAnthropic
from langchain_ollama import ChatOllama

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
    根据配置获取LLM实例

    Returns:
        配置好的LLM实例
    """
    if settings.llm_provider == "zhipu":
        return ChatAnthropic(
            model=settings.zhipu_model,
            api_key=settings.zhipu_api_key,
            base_url=settings.zhipu_base_url,
            timeout=settings.api_timeout_ms / 1000,
            temperature=0,
        )
    else:
        return ChatOllama(
            model=settings.ollama_model, base_url=settings.ollama_host, temperature=0
        )


def _classify_user_intent(question: str) -> str:
    """
    分类用户意图

    Args:
        question: 用户问题

    Returns:
        意图类型：'knowledge', 'data_analysis', 'mixed'
    """
    question_lower = question.lower()

    # 数据分析关键词
    data_analysis_keywords = [
        "分析",
        "数据",
        "图表",
        "可视化",
        "统计",
        "机器学习",
        "预测",
        "模型",
        "训练",
        "回归",
        "分类",
        "聚类",
        "探索性",
        "eda",
        "相关性",
        "分布",
        "趋势",
        "模式",
        "异常",
        "预处理",
        "清洗",
    ]

    # 知识问答关键词
    knowledge_keywords = [
        "什么是",
        "如何",
        "为什么",
        "解释",
        "定义",
        "概念",
        "原理",
        "方法",
        "步骤",
        "教程",
        "文档",
        "说明",
        "介绍",
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
        return "knowledge"  # 默认为知识问答


def build_unified_agent():
    """
    构建统一 Agent - 融合 RAG 和代码分析能力

    核心特性：
    1. 智能意图识别：自动判断用户需求类型
    2. 混合工作流：结合知识检索和数据分析
    3. 工具协调：动态选择合适的工具组合
    4. 结果融合：整合多种分析结果
    5. 上下文保持：维护对话历史和状态

    Returns:
        配置好的统一 Agent 实例
    """

    # 1. 初始化LLM
    llm = _get_llm()

    # 2. 定义系统提示词
    system_prompt = """你是一个智能助手，具备知识问答和数据分析双重能力。

**核心能力**：
1. **知识问答**：基于文档库回答技术问题
2. **数据分析**：处理数据文件，生成分析和可视化
3. **代码执行**：编写和执行 Python 代码
4. **混合任务**：结合知识检索和数据分析

**工作流程**：
1. **意图识别**：分析用户问题，判断需求类型
   - 知识性问题 → 使用 RAG 工具
   - 数据分析问题 → 使用代码分析工具
   - 混合问题 → 结合两种能力

2. **知识问答流程**：
   - 使用 `hybrid_retrieval_tool` 检索相关文档（建议 top_k=10）
   - 使用 `rerank_tool` 重排序获取最相关的 top-5 文档
   - 基于文档生成准确回答

3. **数据分析流程**：
   - 优先使用 `iterative_code_analysis_tool` 进行智能分析（支持自动修复）
   - 使用 `self_healing_code_execution_tool` 执行可能包含错误的代码
   - 使用 `data_analysis_tool` 进行标准探索性分析
   - 使用 `visualization_tool` 生成图表
   - 如有需要，使用 `data_preprocessing_tool` 清洗数据
   - 对于简单任务，使用 `code_execution_tool` 执行代码

4. **混合任务流程**：
   - 先检索相关知识和最佳实践
   - 再进行数据分析
   - 结合知识指导分析过程

**工具使用指南**：

**RAG 工具**：
- `hybrid_retrieval_tool`: 检索相关文档
- `rerank_tool`: 重排序检索结果

**代码分析工具**：
- `code_execution_tool`: 执行 Python 代码
- `code_validation_tool`: 验证代码安全性
- `get_execution_environment_info`: 获取执行环境信息

**智能代码执行工具（LangChain 1.0 增强功能）**：
- `iterative_code_analysis_tool`: 可迭代数据分析，自动修复代码错误
  - 用于复杂数据分析任务，支持EDA、机器学习、可视化等
  - 自动处理文件传递，支持大数据文件的数据库中转
  - 最多5次自我修复尝试，智能错误分析和修复
- `self_healing_code_execution_tool`: 自我修复代码执行器
  - 用于执行可能有问题的 Python 代码
  - 自动修复导入错误、语法错误、变量未定义等常见问题
  - 详细的修复历史和错误分析

**数据分析工具**：
- `data_analysis_tool`: 自动化数据分析
- `data_preprocessing_tool`: 数据预处理

**可视化工具**：
- `visualization_tool`: 基础图表生成
- `advanced_visualization_tool`: 高级可视化
- `dashboard_generation_tool`: 仪表板生成

**重要规则**：
1. 所有回答必须基于检索到的文档或实际数据分析结果
2. 如果文档不足，明确说明"根据现有文档，我无法回答这个问题"
3. 数据分析时，先检查数据质量，再进行分析
4. 生成代码时，确保安全性和可执行性
5. 可视化时，选择合适的图表类型
6. 保持回答简洁、准确、专业

**输出格式**：
你的回答应该包含：
1. 基于问题类型的分析结果
2. 引用的知识来源（如适用）
3. 数据分析的关键发现
4. 可视化图表（如适用）
5. 明确的结论和建议

**智能执行特性（LangChain 1.0 增强）**：
- **自我修复能力**: 代码执行失败时自动分析并修复错误
- **错误学习**: 记录错误模式，提高后续修复成功率
- **多轮迭代**: 支持最多5次修复尝试，逐步优化代码
- **智能数据传递**: 自动选择文件映射或数据库中转方式
- **上下文保持**: 在迭代过程中保持分析上下文和历史

**安全提醒**：
- 所有代码都在安全的 Docker 环境中执行
- 执行时间限制为 {code_execution_timeout} 秒
- 内存限制为 {code_execution_memory_limit}
- 禁止危险的系统操作
- 智能修复仅针对常见错误，不会绕过安全限制
""".format(
        code_execution_timeout=getattr(settings, "code_execution_timeout", 300),
        code_execution_memory_limit=getattr(
            settings, "code_execution_memory_limit", "1G"
        ),
    )

    # 3. 准备工具列表
    tools = [
        # RAG 工具
        hybrid_retrieval_tool,
        rerank_tool,
        # 基础代码执行工具
        code_execution_tool,
        code_validation_tool,
        get_execution_environment_info,
        # 数据分析工具
        data_analysis_tool,
        data_preprocessing_tool,
        # 可视化工具
        visualization_tool,
        advanced_visualization_tool,
        dashboard_generation_tool,
    ]

    # 如果启用可迭代执行，添加高级工具
    if getattr(settings, "enable_iterative_execution", True):
        tools.extend([iterative_code_analysis_tool, self_healing_code_execution_tool])

    # 4. 创建统一 Agent
    agent = create_agent(
        model=llm,
        tools=tools,
        system_prompt=system_prompt,
        # state_schema=RAGAgentState,  # 暂时注释，先测试基础功能
        max_iterations=getattr(settings, "max_code_fix_attempts", 5),  # 支持可迭代执行
    )

    return agent


class UnifiedAgentOrchestrator:
    """统一 Agent 协调器 - 智能路由和结果融合"""

    def __init__(self):
        """初始化协调器"""
        self.agent = build_unified_agent()
        self.logger = logging.getLogger(__name__)

    def process_request(self, question: str, **kwargs) -> Dict[str, Any]:
        """
        处理用户请求

        Args:
            question: 用户问题
            **kwargs: 额外参数（如数据文件路径等）

        Returns:
            处理结果字典
        """
        try:
            # 1. 意图识别
            intent = _classify_user_intent(question)
            self.logger.info(f"用户意图识别: {intent}")

            # 2. 根据意图调整输入
            enhanced_input = self._enhance_input_by_intent(question, intent, **kwargs)

            # 3. 执行 Agent
            result = self.agent.invoke(enhanced_input)

            # 4. 后处理结果
            processed_result = self._process_result_by_intent(result, intent)

            return {
                "success": True,
                "intent": intent,
                "question": question,
                "result": processed_result,
                "raw_response": result,
            }

        except Exception as e:
            self.logger.error(f"统一 Agent 处理失败: {e}")
            return {
                "success": False,
                "error": str(e),
                "intent": "unknown",
                "question": question,
            }

    def _enhance_input_by_intent(
        self, question: str, intent: str, **kwargs
    ) -> Dict[str, Any]:
        """根据意图增强输入"""
        base_input = {"messages": [], "question": question}

        if intent == "data_analysis":
            # 数据分析任务，添加数据文件信息
            if "data_file" in kwargs:
                base_input["data_file"] = kwargs["data_file"]
                base_input["question"] += f"\n\n数据文件: {kwargs['data_file']}"

            # 添加分析建议
            base_input["question"] += "\n\n请进行适当的数据分析，包括数据概览、统计分析和可视化。"

        elif intent == "knowledge":
            # 知识问答任务，添加检索建议
            base_input["question"] += "\n\n请基于文档库提供准确的答案，并引用相关文档。"

        elif intent == "mixed":
            # 混合任务，添加综合建议
            if "data_file" in kwargs:
                base_input["data_file"] = kwargs["data_file"]
                base_input["question"] += f"\n\n数据文件: {kwargs['data_file']}"

            base_input["question"] += "\n\n请结合相关知识和数据分析，提供全面的答案。"

        return base_input

    def _process_result_by_intent(
        self, result: Dict[str, Any], intent: str
    ) -> Dict[str, Any]:
        """根据意图处理结果"""
        processed = {
            "answer": "",
            "sources": [],
            "visualizations": [],
            "data_analysis": {},
            "code_execution": {},
            "confidence": "medium",
        }

        # 提取答案
        if "messages" in result:
            messages = result["messages"]
            if messages:
                # 获取最后一条消息作为答案
                last_message = messages[-1]
                if hasattr(last_message, "content"):
                    processed["answer"] = last_message.content
                else:
                    processed["answer"] = str(last_message)

        # 根据意图提取特定信息
        if intent in ["knowledge", "mixed"]:
            # 提取文档来源
            processed["sources"] = self._extract_sources(result)

        if intent in ["data_analysis", "mixed"]:
            # 提取分析结果
            processed["data_analysis"] = self._extract_analysis_results(result)
            processed["visualizations"] = self._extract_visualizations(result)
            processed["code_execution"] = self._extract_code_execution_results(result)

        return processed

    def _extract_sources(self, result: Dict[str, Any]) -> List[str]:
        """提取文档来源"""
        sources = []

        # 从工具调用中提取来源
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
        """提取数据分析结果"""
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
        """提取可视化结果"""
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
        """提取代码执行结果"""
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


# 全局统一 Agent 实例
unified_agent = build_unified_agent()
unified_orchestrator = UnifiedAgentOrchestrator()
