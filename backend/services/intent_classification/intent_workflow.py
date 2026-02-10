"""
意图分类工作流
集成LangChain 1.0 State Graph，实现完整的意图识别和路由流程
"""

import asyncio
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from types import SimpleNamespace
from typing import Annotated, Any, Dict, List, Literal, Optional, TypedDict

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableLambda, RunnablePassthrough
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, StateGraph
from langgraph.graph.message import add_messages

from backend.config import settings

from .context_manager import ContextManager, SessionContext
from .intent_classifier import IntentClassifier, IntentResult, QueryContext
from .prompt_manager import PromptManager
from .routing_decision import AgentType, RoutingDecision, RoutingDecisionEngine
from backend.services.workflows.nodes.prompt_node import prompt_node
from backend.services.workflows.prompting.template_selector import TemplateSelector

logger = logging.getLogger(__name__)


class WorkflowState(TypedDict):
    """工作流状态定义"""

    messages: Annotated[List, add_messages]  # 消息历史
    session_id: str  # 会话ID
    user_id: Optional[str]  # 用户ID
    current_query: str  # 当前用户查询
    query_context: QueryContext  # 查询上下文
    session_context: SessionContext  # 会话上下文
    intent_result: Optional[IntentResult]  # 意图分类结果
    routing_decision: Optional[RoutingDecision]  # 路由决策
    clarification_needed: bool  # 是否需要澄清
    clarification_response: Optional[str]  # 澄清回应
    agent_response: Optional[str]  # Agent响应
    workflow_complete: bool  # 工作流是否完成
    error: Optional[str]  # 错误信息
    system_prompt: Optional[str]  # Prompt模板渲染结果
    prompt_meta: Optional[Dict[str, Any]]  # Prompt元信息
    metadata: Dict[str, Any]  # 元数据


class IntentClassificationWorkflow:
    """意图分类工作流"""

    def __init__(
        self,
        intent_classifier: IntentClassifier,
        context_manager: ContextManager,
        routing_engine: RoutingDecisionEngine,
        prompt_manager: Optional[PromptManager] = None,
    ):
        """
        初始化工作流

        Args:
            intent_classifier: 意图分类器
            context_manager: 上下文管理器
            routing_engine: 路由决策引擎
            prompt_manager: Prompt管理器（可选）
        """
        self.intent_classifier = intent_classifier
        self.context_manager = context_manager
        self.routing_engine = routing_engine
        self.prompt_manager = prompt_manager
        self.template_selector = TemplateSelector()

        # 创建工作流图
        self.workflow = self._create_workflow()

        # 内存检查点保存器（用于会话状态管理）
        self.memory = MemorySaver()

        logger.info("意图分类工作流初始化完成")

    def _create_workflow(self) -> StateGraph:
        """创建工作流图"""
        # 创建状态图
        workflow = StateGraph(WorkflowState)

        # 添加节点
        workflow.add_node("input_preprocessing", self._input_preprocessing_node)
        workflow.add_node("context_enrichment", self._context_enrichment_node)
        workflow.add_node("intent_classification", self._intent_classification_node)
        workflow.add_node("confidence_evaluation", self._confidence_evaluation_node)
        workflow.add_node("routing_decision", self._routing_decision_node)
        workflow.add_node("prompt_preparation", self._prompt_preparation_node)
        workflow.add_node("clarification_needed", self._clarification_needed_node)
        workflow.add_node(
            "clarification_processing", self._clarification_processing_node
        )
        workflow.add_node("agent_dispatch", self._agent_dispatch_node)
        workflow.add_node("response_processing", self._response_processing_node)
        workflow.add_node("error_handling", self._error_handling_node)

        # 设置入口点
        workflow.set_entry_point("input_preprocessing")

        # 添加边
        workflow.add_edge("input_preprocessing", "context_enrichment")
        workflow.add_edge("context_enrichment", "intent_classification")
        workflow.add_edge("intent_classification", "confidence_evaluation")

        # 条件路由
        workflow.add_conditional_edges(
            "confidence_evaluation",
            self._route_based_on_confidence,
            {
                "high_confidence": "routing_decision",
                "low_confidence": "clarification_needed",
                "error": "error_handling",
            },
        )

        workflow.add_edge("routing_decision", "prompt_preparation")
        workflow.add_edge("prompt_preparation", "agent_dispatch")
        workflow.add_edge("clarification_needed", "clarification_processing")

        # 澄清处理后的路由
        workflow.add_conditional_edges(
            "clarification_processing",
            self._route_after_clarification,
            {
                "retry_classification": "intent_classification",
                "proceed_with_fallback": "routing_decision",
                "await_user_input": END,
            },
        )

        workflow.add_edge("agent_dispatch", "response_processing")
        workflow.add_edge("response_processing", END)
        workflow.add_edge("error_handling", END)

        return workflow

    async def _input_preprocessing_node(self, state: WorkflowState) -> WorkflowState:
        """输入预处理节点"""
        try:
            logger.info(f"开始输入预处理，会话ID: {state['session_id']}")

            # 清理和预处理用户查询
            current_query = state.get("current_query", "")

            # 基本清理
            cleaned_query = current_query.strip()

            # 更新状态
            state["current_query"] = cleaned_query
            state["messages"].append(HumanMessage(content=cleaned_query))

            # 更新元数据
            state["metadata"]["preprocessing_timestamp"] = datetime.now().isoformat()
            state["metadata"]["query_length"] = len(cleaned_query)

            logger.debug(f"输入预处理完成: {cleaned_query[:100]}...")
            return state

        except Exception as e:
            logger.error(f"输入预处理失败: {str(e)}")
            state["error"] = f"输入预处理失败: {str(e)}"
            return state

    async def _context_enrichment_node(self, state: WorkflowState) -> WorkflowState:
        """上下文增强节点"""
        try:
            logger.info("开始上下文增强")

            session_id = state["session_id"]

            # 获取会话上下文
            session_context = await self.context_manager.get_session_context(
                session_id=session_id, user_id=state.get("user_id")
            )
            state["session_context"] = session_context

            # 获取增强的上下文信息
            enhanced_context = await self.context_manager.get_enhanced_context(
                session_id=session_id, max_history=5, include_files=True
            )

            # 构建查询上下文
            query_context = QueryContext(
                session_id=session_id,
                user_id=state.get("user_id"),
                current_query=state["current_query"],
                session_history=enhanced_context.get("interaction_history", []),
                recent_intents=session_context.get_recent_intents(3),
                uploaded_files=session_context.uploaded_files,
                user_preferences=session_context.user_preferences,
                context_keywords=enhanced_context.get("context_keywords", []),
            )
            state["query_context"] = query_context

            # 更新元数据
            state["metadata"][
                "context_enrichment_timestamp"
            ] = datetime.now().isoformat()
            state["metadata"]["context_quality"] = enhanced_context.get(
                "context_quality", "medium"
            )

            logger.debug(f"上下文增强完成，上下文质量: {state['metadata']['context_quality']}")
            return state

        except Exception as e:
            logger.error(f"上下文增强失败: {str(e)}")
            state["error"] = f"上下文增强失败: {str(e)}"
            return state

    async def _intent_classification_node(self, state: WorkflowState) -> WorkflowState:
        """意图分类节点"""
        try:
            logger.info("开始意图分类")

            # 执行意图分类
            intent_result = await self.intent_classifier.classify_intent(
                query=state["current_query"], context=state["query_context"]
            )
            state["intent_result"] = intent_result

            # 记录交互
            await self.context_manager.add_interaction_record(
                session_id=state["session_id"],
                user_query=state["current_query"],
                classified_intent=intent_result.intent,
                agent_response="",  # 待Agent响应后填充
                confidence=intent_result.confidence,
                processing_time_ms=intent_result.processing_time_ms,
                success=True,
            )

            # 更新元数据
            state["metadata"]["classification_timestamp"] = datetime.now().isoformat()
            state["metadata"]["intent"] = intent_result.intent
            state["metadata"]["confidence"] = intent_result.confidence

            logger.info(
                f"意图分类完成: {intent_result.intent} (置信度: {intent_result.confidence:.2f})"
            )
            return state

        except Exception as e:
            logger.error(f"意图分类失败: {str(e)}")
            state["error"] = f"意图分类失败: {str(e)}"
            return state

    async def _confidence_evaluation_node(self, state: WorkflowState) -> WorkflowState:
        """置信度评估节点"""
        try:
            logger.info("开始置信度评估")

            intent_result = state.get("intent_result")
            if not intent_result:
                state["error"] = "缺少意图分类结果"
                return state

            confidence = intent_result.confidence

            # 置信度评估
            high_threshold = 0.8
            low_threshold = 0.5

            if confidence >= high_threshold:
                state["clarification_needed"] = False
                evaluation_result = "high_confidence"
                logger.info("高置信度，直接路由")
            elif confidence <= low_threshold:
                state["clarification_needed"] = True
                evaluation_result = "low_confidence"
                logger.info("低置信度，需要澄清")
            else:
                # 中等置信度，考虑其他因素
                uncertainty_factors = intent_result.uncertainty_factors
                if len(uncertainty_factors) > 2:
                    state["clarification_needed"] = True
                    evaluation_result = "low_confidence"
                    logger.info("中置信度但不确定因素多，需要澄清")
                else:
                    state["clarification_needed"] = False
                    evaluation_result = "high_confidence"
                    logger.info("中置信度但风险可控，直接路由")

            # 更新元数据
            state["metadata"]["confidence_evaluation"] = evaluation_result
            state["metadata"]["uncertainty_factors"] = intent_result.uncertainty_factors

            return state

        except Exception as e:
            logger.error(f"置信度评估失败: {str(e)}")
            state["error"] = f"置信度评估失败: {str(e)}"
            return {"evaluation_result": "error"}

    async def _routing_decision_node(self, state: WorkflowState) -> WorkflowState:
        """路由决策节点"""
        try:
            logger.info("开始路由决策")

            intent_result = state["intent_result"]

            # 构建路由上下文
            routing_context = {
                "session_id": state["session_id"],
                "user_id": state.get("user_id"),
                "query_count": state["session_context"].query_count,
                "has_uploaded_files": len(state["session_context"].uploaded_files) > 0,
                "session_stage": state["session_context"].session_stage,
            }

            # 执行路由决策
            routing_decision = await self.routing_engine.make_routing_decision(
                intent_result=intent_result.to_dict(),
                context=routing_context,
                user_preferences=state["session_context"].user_preferences,
            )
            state["routing_decision"] = routing_decision

            # 更新元数据
            state["metadata"]["routing_timestamp"] = datetime.now().isoformat()
            state["metadata"]["selected_agent"] = routing_decision.selected_agent.value
            state["metadata"]["routing_path"] = routing_decision.routing_path.value

            logger.info(f"路由决策完成: {routing_decision.selected_agent.value}")
            return state

        except Exception as e:
            logger.error(f"路由决策失败: {str(e)}")
            state["error"] = f"路由决策失败: {str(e)}"
            return state

    async def _prompt_preparation_node(self, state: WorkflowState) -> WorkflowState:
        """Prompt准备节点（将模板选择前置到Agent执行前）"""
        if not self.prompt_manager:
            state["metadata"]["prompt_status"] = "disabled"
            return state

        try:
            intent_value = None
            if state.get("intent_result") is not None:
                intent = state["intent_result"].intent
                intent_value = intent.value if hasattr(intent, "value") else str(intent)

            prompt_state = {
                "query": state.get("current_query", ""),
                "intent": intent_value,
                "retrieved_context": state.get("query_context").interaction_history
                if state.get("query_context")
                else [],
                "metadata": {
                    **state.get("metadata", {}),
                    "session_id": state.get("session_id"),
                    "user_id": state.get("user_id"),
                    "prompt_experiments_enabled": False,
                },
            }
            services = SimpleNamespace(
                prompt_manager=self.prompt_manager,
                template_selector=self.template_selector,
            )
            prompt_state = await prompt_node(prompt_state, services)
            if prompt_state.get("error"):
                state["metadata"]["prompt_status"] = "error"
                state["metadata"]["prompt_error"] = prompt_state["error"]
                return state

            state["system_prompt"] = prompt_state.get("system_prompt")
            state["prompt_meta"] = prompt_state.get("prompt_meta")
            state["metadata"]["prompt_status"] = "ok"
            if state.get("prompt_meta"):
                state["metadata"]["prompt_meta"] = state["prompt_meta"]
            return state
        except Exception as e:
            logger.warning(f"Prompt准备失败，降级到默认执行: {e}")
            state["metadata"]["prompt_status"] = "error"
            state["metadata"]["prompt_error"] = str(e)
            return state

    async def _clarification_needed_node(self, state: WorkflowState) -> WorkflowState:
        """澄清需求节点"""
        try:
            logger.info("生成澄清问题")

            intent_result = state["intent_result"]
            routing_decision = state.get("routing_decision")

            if routing_decision and routing_decision.clarification_context:
                clarification_context = routing_decision.clarification_context
            else:
                # 生成基本的澄清上下文
                clarification_context = {
                    "possible_intents": [intent_result.intent],
                    "clarification_questions": [
                        f"关于'{intent_result.intent}'，您能提供更多细节吗？",
                        "您的具体需求是什么？",
                    ],
                    "user_context": {
                        "current_query": state["current_query"],
                        "confidence": intent_result.confidence,
                    },
                }

            # 如果有Prompt管理器，使用澄清Prompt
            if self.prompt_manager:
                try:
                    prompt_info, prompt_content = await self.prompt_manager.get_prompt(
                        name="intent_clarification",
                        category="Intent",
                        context={
                            "user_query": state["current_query"],
                            "possible_intents": clarification_context[
                                "possible_intents"
                            ],
                            "classification_result": intent_result.reasoning,
                        },
                        variables={
                            "user_query": state["current_query"],
                            "possible_intents": json.dumps(
                                clarification_context["possible_intents"],
                                ensure_ascii=False,
                            ),
                            "classification_result": intent_result.reasoning,
                            "language": "zh-CN",
                        },
                    )

                    # 使用LLM生成澄清消息
                    clarification_message = (
                        await self._generate_clarification_with_prompt(
                            prompt_content, clarification_context
                        )
                    )
                except Exception as e:
                    logger.warning(f"使用Prompt管理器生成澄清失败，使用默认方法: {str(e)}")
                    clarification_message = self._generate_default_clarification(
                        clarification_context
                    )
            else:
                clarification_message = self._generate_default_clarification(
                    clarification_context
                )

            state["clarification_response"] = clarification_message
            state["metadata"]["clarification_timestamp"] = datetime.now().isoformat()
            state["metadata"]["clarification_generated"] = True

            logger.info("澄清问题生成完成")
            return state

        except Exception as e:
            logger.error(f"澄清需求处理失败: {str(e)}")
            state["error"] = f"澄清需求处理失败: {str(e)}"
            return state

    async def _clarification_processing_node(
        self, state: WorkflowState
    ) -> WorkflowState:
        """澄清处理节点"""
        try:
            logger.info("处理澄清回应")

            # 在实际应用中，这里会等待用户的澄清回应
            # 对于演示目的，我们模拟几种情况

            # 检查是否有用户的澄清回应
            clarification_response = state.get("clarification_response")
            if not clarification_response:
                # 如果没有澄清回应，等待用户输入
                state["metadata"]["awaiting_user_clarification"] = True
                return state

            # 这里可以添加澄清回应的处理逻辑
            # 例如重新分类、更新上下文等

            # 简化处理：基于澄清情况决定下一步
            routing_decision = state.get("routing_decision")
            if routing_decision and routing_decision.confidence < 0.7:
                # 如果原路由决策置信度较低，尝试使用备选方案
                state["metadata"]["clarification_handled"] = True
                return state  # 继续到路由决策节点
            else:
                # 重新进行意图分类
                state["metadata"]["clarification_handled"] = True
                return state

        except Exception as e:
            logger.error(f"澄清处理失败: {str(e)}")
            state["error"] = f"澄清处理失败: {str(e)}"
            return state

    async def _agent_dispatch_node(self, state: WorkflowState) -> WorkflowState:
        """Agent调度节点"""
        try:
            logger.info("调度Agent处理请求")

            routing_decision = state["routing_decision"]

            # 模拟Agent处理
            agent_type = routing_decision.selected_agent
            agent_response = await self._dispatch_to_agent(
                agent_type=agent_type,
                query=state["current_query"],
                context=state["query_context"],
                parameters=routing_decision.parameters,
                system_prompt=state.get("system_prompt"),
                prompt_meta=state.get("prompt_meta"),
            )

            state["agent_response"] = agent_response
            state["metadata"]["agent_dispatch_timestamp"] = datetime.now().isoformat()
            state["metadata"]["agent_type"] = agent_type.value

            # 更新会话上下文中的交互记录
            intent_result = state["intent_result"]
            await self.context_manager.add_interaction_record(
                session_id=state["session_id"],
                user_query=state["current_query"],
                classified_intent=intent_result.intent,
                agent_response=agent_response,
                confidence=intent_result.confidence,
                processing_time_ms=intent_result.processing_time_ms,
                success=True,
            )

            logger.info(f"Agent处理完成: {agent_type.value}")
            return state

        except Exception as e:
            logger.error(f"Agent调度失败: {str(e)}")
            state["error"] = f"Agent调度失败: {str(e)}"
            return state

    async def _response_processing_node(self, state: WorkflowState) -> WorkflowState:
        """响应处理节点"""
        try:
            logger.info("处理最终响应")

            agent_response = state.get("agent_response", "")

            # 添加AI消息到历史
            state["messages"].append(AIMessage(content=agent_response))

            # 标记工作流完成
            state["workflow_complete"] = True
            state["metadata"]["completion_timestamp"] = datetime.now().isoformat()

            logger.info("工作流完成")
            return state

        except Exception as e:
            logger.error(f"响应处理失败: {str(e)}")
            state["error"] = f"响应处理失败: {str(e)}"
            return state

    async def _error_handling_node(self, state: WorkflowState) -> WorkflowState:
        """错误处理节点"""
        logger.error(f"工作流错误: {state.get('error', '未知错误')}")

        # 设置错误响应
        error_message = "抱歉，处理您的请求时遇到了问题。请稍后重试或重新描述您的需求。"
        state["agent_response"] = error_message
        state["messages"].append(AIMessage(content=error_message))
        state["workflow_complete"] = True
        state["metadata"]["error_timestamp"] = datetime.now().isoformat()

        return state

    def _route_based_on_confidence(self, state: WorkflowState) -> str:
        """基于置信度的路由逻辑"""
        if state.get("error"):
            return "error"

        if state.get("clarification_needed", False):
            return "low_confidence"
        else:
            return "high_confidence"

    def _route_after_clarification(self, state: WorkflowState) -> str:
        """澄清后的路由逻辑"""
        if state.get("metadata", {}).get("awaiting_user_clarification", False):
            return "await_user_input"

        # 简化逻辑：回到路由决策
        return "proceed_with_fallback"

    async def _generate_clarification_with_prompt(
        self, prompt_content: str, context: Dict[str, Any]
    ) -> str:
        """使用Prompt生成澄清消息"""
        try:
            # 这里应该调用LLM生成澄清消息
            # 简化实现，返回模板化消息
            questions = context.get("clarification_questions", [])
            possible_intents = context.get("possible_intents", [])

            if questions:
                clarification = f"我需要进一步了解您的需求。您希望：\n\n"
                for i, question in enumerate(questions, 1):
                    clarification += f"{i}. {question}\n"
                clarification += "\n请选择最符合您需求的选项，或者提供更多详细信息。"
            else:
                clarification = "请提供更多关于您需求的信息，以便我更好地为您服务。"

            return clarification
        except Exception as e:
            logger.error(f"生成澄清消息失败: {str(e)}")
            return "请提供更多详细信息，以便我更好地理解您的需求。"

    def _generate_default_clarification(self, context: Dict[str, Any]) -> str:
        """生成默认澄清消息"""
        questions = context.get("clarification_questions", [])
        possible_intents = context.get("possible_intents", [])

        if questions:
            clarification = f"我需要进一步了解您的需求。您希望：\n\n"
            for i, question in enumerate(questions, 1):
                clarification += f"{i}. {question}\n"
            clarification += "\n请选择最符合您需求的选项，或者提供更多详细信息。"
        else:
            clarification = "请提供更多关于您需求的信息，以便我更好地为您服务。"

        return clarification

    async def _dispatch_to_agent(
        self,
        agent_type: AgentType,
        query: str,
        context: QueryContext,
        parameters: Dict[str, Any],
        system_prompt: Optional[str] = None,
        prompt_meta: Optional[Dict[str, Any]] = None,
    ) -> str:
        """调度到具体的Agent"""
        # 这里是模拟的Agent调用
        # 在实际应用中，会调用真实的Agent服务

        agent_responses = {
            AgentType.RAG_AGENT: f"根据您的查询'{query}'，我为您检索到相关知识：这是一个关于{context.context_keywords[0] if context.context_keywords else '相关主题'}的详细解释...",
            AgentType.DATA_ANALYSIS_AGENT: f"针对您提到的数据分析需求，我建议采用以下方法：首先进行探索性数据分析，然后根据数据特征选择合适的分析方法...",
            AgentType.DOCUMENT_PROCESSING_AGENT: f"关于文档处理，我可以帮您提取文本内容、识别表格数据或进行OCR处理。请提供具体的文档信息...",
            AgentType.CODE_EXECUTION_AGENT: f"我将帮您执行相关代码任务。基于您的需求，建议使用Python来实现相应的计算或算法...",
            AgentType.GENERAL_AGENT: f"我理解您的需求是'{query}'。让我为您提供一些有用的建议和信息...",
        }

        response = agent_responses.get(agent_type, "我正在处理您的请求，请稍候...")
        if system_prompt:
            prompt_name = (prompt_meta or {}).get("name", "unknown_prompt")
            response = f"{response}\n\n[模板已应用: {prompt_name}]"
        return response

    async def run_workflow(
        self,
        query: str,
        session_id: str,
        user_id: Optional[str] = None,
        thread_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        运行完整的工作流

        Args:
            query: 用户查询
            session_id: 会话ID
            user_id: 用户ID
            thread_id: 线程ID（用于LangGraph）

        Returns:
            Dict[str, Any]: 工作流执行结果
        """
        try:
            # 初始化状态
            initial_state = WorkflowState(
                messages=[],
                session_id=session_id,
                user_id=user_id,
                current_query=query,
                query_context=QueryContext(session_id=session_id, user_id=user_id),
                session_context=SessionContext(session_id=session_id),
                intent_result=None,
                routing_decision=None,
                clarification_needed=False,
                clarification_response=None,
                agent_response=None,
                workflow_complete=False,
                error=None,
                system_prompt=None,
                prompt_meta=None,
                metadata={
                    "start_timestamp": datetime.now().isoformat(),
                    "prompt_experiments_enabled": bool(
                        settings.prompt_experiments_enabled
                    ),
                },
            )

            # 创建可运行的工作流
            runnable_workflow = self.workflow.compile(checkpointer=self.memory)

            # 执行工作流
            config = {"configurable": {"thread_id": thread_id or session_id}}
            result = await runnable_workflow.ainvoke(initial_state, config=config)

            # 构建返回结果
            return {
                "success": not bool(result.get("error")),
                "agent_response": result.get("agent_response"),
                "intent_result": result["intent_result"].to_dict()
                if result.get("intent_result")
                else None,
                "routing_decision": result["routing_decision"].to_dict()
                if result.get("routing_decision")
                else None,
                "clarification_needed": result.get("clarification_needed", False),
                "clarification_response": result.get("clarification_response"),
                "messages": [
                    {"type": type(msg).__name__, "content": msg.content}
                    for msg in result.get("messages", [])
                ],
                "metadata": result.get("metadata", {}),
                "error": result.get("error"),
            }

        except Exception as e:
            logger.error(f"工作流执行失败: {str(e)}")
            return {
                "success": False,
                "error": f"工作流执行失败: {str(e)}",
                "agent_response": "抱歉，处理您的请求时遇到了系统错误。请稍后重试。",
            }

    async def continue_workflow(
        self, user_response: str, session_id: str, thread_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        继续工作流（例如在澄清后）

        Args:
            user_response: 用户回应
            session_id: 会话ID
            thread_id: 线程ID

        Returns:
            Dict[str, Any]: 工作流执行结果
        """
        try:
            # 获取之前的状态
            runnable_workflow = self.workflow.compile(checkpointer=self.memory)
            config = {"configurable": {"thread_id": thread_id or session_id}}

            # 创建新的状态更新
            state_update = WorkflowState(
                messages=[HumanMessage(content=user_response)],
                current_query=user_response,
                metadata={
                    "continuation_timestamp": datetime.now().isoformat(),
                    "prompt_experiments_enabled": bool(
                        settings.prompt_experiments_enabled
                    ),
                },
            )

            # 继续执行工作流
            result = await runnable_workflow.ainvoke(state_update, config=config)

            return {
                "success": not bool(result.get("error")),
                "agent_response": result.get("agent_response"),
                "clarification_needed": result.get("clarification_needed", False),
                "clarification_response": result.get("clarification_response"),
                "messages": [
                    {"type": type(msg).__name__, "content": msg.content}
                    for msg in result.get("messages", [])
                ],
                "metadata": result.get("metadata", {}),
                "error": result.get("error"),
            }

        except Exception as e:
            logger.error(f"工作流继续执行失败: {str(e)}")
            return {
                "success": False,
                "error": f"工作流继续执行失败: {str(e)}",
                "agent_response": "抱歉，处理您的回应时遇到了错误。请重新描述您的需求。",
            }

    def get_workflow_stats(self) -> Dict[str, Any]:
        """获取工作流统计信息"""
        routing_stats = self.routing_engine.get_routing_statistics()

        return {
            "workflow_status": "active",
            "routing_statistics": routing_stats,
            "components": {
                "intent_classifier": "enabled",
                "context_manager": "enabled",
                "routing_engine": "enabled",
                "prompt_manager": "enabled" if self.prompt_manager else "disabled",
            },
            "memory_checkpoints": "enabled",
        }
