"""
LangChain 1.0 Prompt Manager Middleware
提供动态Prompt选择、版本管理、A/B测试等功能的中间件集成
"""

import asyncio
import json
import logging
import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Union

from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage
from langchain_core.runnables import Runnable, RunnableLambda, RunnablePassthrough
from langchain_core.runnables.config import RunnableConfig

from backend.services.prompt_manager import PromptInfo, PromptManager, UsageLog

logger = logging.getLogger(__name__)


@dataclass
class PromptContext:
    """Prompt上下文信息"""

    user_request: str
    session_id: str
    user_id: Optional[str] = None
    request_type: Optional[str] = None
    metadata: Dict[str, Any] = None
    variables: Dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}
        if self.variables is None:
            self.variables = {}


class PromptUsageCallback(BaseCallbackHandler):
    """Prompt使用回调处理器"""

    def __init__(self, prompt_manager: PromptManager):
        self.prompt_manager = prompt_manager
        self.usage_logs: List[Dict[str, Any]] = []

    async def on_llm_start(
        self, serialized: Dict[str, Any], prompts: List[str], **kwargs: Any
    ) -> None:
        """LLM开始时的回调"""
        # 这里可以记录Prompt使用情况
        pass

    async def on_llm_end(self, response, **kwargs: Any) -> None:
        """LLM结束时的回调"""
        # 记录使用结果
        pass


class PromptManagerMiddleware:
    """
    Prompt管理中间件

    功能特性：
    1. 动态Prompt选择
    2. 自动变量注入
    3. A/B测试集成
    4. 性能监控
    5. 使用记录
    """

    def __init__(
        self,
        prompt_manager: PromptManager,
        enable_experiments: bool = True,
        enable_monitoring: bool = True,
        context_enrichers: Optional[List[Callable]] = None,
    ):
        """
        初始化中间件

        Args:
            prompt_manager: Prompt管理器实例
            enable_experiments: 是否启用A/B测试
            enable_monitoring: 是否启用性能监控
            context_enrichers: 上下文增强器列表
        """
        self.prompt_manager = prompt_manager
        self.enable_experiments = enable_experiments
        self.enable_monitoring = enable_monitoring
        self.context_enrichers = context_enrichers or []

        logger.info("Prompt管理中间件初始化完成")

    def create_prompt_chain(
        self,
        prompt_name: str,
        category: str,
        context_builder: Optional[Callable[[Dict[str, Any]], PromptContext]] = None,
    ) -> Runnable:
        """
        创建带有Prompt管理的执行链

        Args:
            prompt_name: Prompt名称
            category: Prompt分类
            context_builder: 上下文构建器

        Returns:
            Runnable: 可执行链
        """

        async def process_input(inputs: Dict[str, Any]) -> Dict[str, Any]:
            """处理输入，注入Prompt"""
            try:
                # 构建上下文
                prompt_context = self._build_context(inputs, context_builder)

                # 获取最优Prompt
                prompt_info, rendered_content = await self.prompt_manager.get_prompt(
                    name=prompt_name,
                    category=category,
                    context=prompt_context.metadata,
                    variables=prompt_context.variables,
                    enable_experiments=self.enable_experiments,
                )

                # 注入Prompt到输入
                enriched_inputs = inputs.copy()
                enriched_inputs.update(
                    {
                        "system_prompt": rendered_content,
                        "prompt_info": prompt_info,
                        "prompt_context": prompt_context,
                        "usage_start_time": datetime.now(),
                    }
                )

                # 记录使用开始
                if self.enable_monitoring:
                    self._record_usage_start(prompt_info.id, prompt_context)

                logger.debug(f"Prompt注入成功: {category}/{prompt_name}")
                return enriched_inputs

            except Exception as e:
                logger.error(f"Prompt注入失败: {e}")
                # 降级处理：返回原始输入
                return inputs

        async def process_output(
            outputs: Dict[str, Any], inputs: Dict[str, Any]
        ) -> Dict[str, Any]:
            """处理输出，记录使用情况"""
            try:
                if "prompt_info" in inputs and "usage_start_time" in inputs:
                    prompt_info = inputs["prompt_info"]
                    usage_start_time = inputs["usage_start_time"]

                    # 计算执行时间
                    execution_time_ms = int(
                        (datetime.now() - usage_start_time).total_seconds() * 1000
                    )

                    # 创建使用日志
                    usage_log = UsageLog(
                        prompt_id=prompt_info.id,
                        session_id=inputs.get("prompt_context", {}).get("session_id"),
                        context=inputs.get("prompt_context", {}).get("metadata", {}),
                        variables_used=inputs.get("prompt_context", {}).get(
                            "variables", {}
                        ),
                        execution_time_ms=execution_time_ms,
                        success=outputs.get("success", True),
                        error_message=outputs.get("error"),
                        user_feedback=outputs.get("user_feedback"),
                        llm_response={"result": outputs.get("result")}
                        if "result" in outputs
                        else None,
                        tokens_used=outputs.get("tokens_used", 0),
                        model_name=outputs.get("model_name"),
                        temperature=outputs.get("temperature"),
                    )

                    # 异步记录使用日志
                    if self.enable_monitoring:
                        asyncio.create_task(
                            self.prompt_manager.record_usage_log(usage_log)
                        )

                    # 添加性能信息到输出
                    outputs["prompt_performance"] = {
                        "prompt_id": str(prompt_info.id),
                        "prompt_name": prompt_info.name,
                        "prompt_version": prompt_info.version,
                        "execution_time_ms": execution_time_ms,
                        "performance_score": prompt_info.performance_score,
                    }

                return outputs

            except Exception as e:
                logger.error(f"输出处理失败: {e}")
                return outputs

        # 构建处理链
        chain = (
            RunnableLambda(process_input)
            | RunnablePassthrough()
            | RunnableLambda(lambda outputs: outputs)  # 实际的处理逻辑在这里插入
            | RunnableLambda(process_output)
        )

        return chain

    def create_adaptive_prompt_chain(
        self,
        prompt_categories: List[str],
        context_analyzer: Callable[[Dict[str, Any]], str],
    ) -> Runnable:
        """
        创建自适应Prompt链，根据上下文自动选择类别

        Args:
            prompt_categories: 可选的Prompt类别列表
            context_analyzer: 上下文分析器，返回选择的类别

        Returns:
            Runnable: 自适应执行链
        """

        async def adaptive_prompt_selection(inputs: Dict[str, Any]) -> Dict[str, Any]:
            """自适应Prompt选择"""
            try:
                # 分析上下文，选择最合适的类别
                selected_category = context_analyzer(inputs)

                if selected_category not in prompt_categories:
                    logger.warning(f"选择的类别不在支持列表中: {selected_category}")
                    selected_category = prompt_categories[0]  # 降级到第一个类别

                # 构建上下文
                prompt_context = self._build_context(inputs)

                # 获取该类别的最佳Prompt
                prompt_info, rendered_content = await self.prompt_manager.get_prompt(
                    name=inputs.get("task_name", "default"),  # 可以从输入中获取任务名称
                    category=selected_category,
                    context=prompt_context.metadata,
                    variables=prompt_context.variables,
                    enable_experiments=self.enable_experiments,
                )

                # 注入Prompt
                enriched_inputs = inputs.copy()
                enriched_inputs.update(
                    {
                        "system_prompt": rendered_content,
                        "prompt_info": prompt_info,
                        "prompt_context": prompt_context,
                        "selected_category": selected_category,
                        "usage_start_time": datetime.now(),
                    }
                )

                return enriched_inputs

            except Exception as e:
                logger.error(f"自适应Prompt选择失败: {e}")
                return inputs

        # 构建自适应链
        chain = (
            RunnableLambda(adaptive_prompt_selection)
            | RunnablePassthrough()
            | RunnableLambda(lambda x: x)  # 实际处理逻辑
        )

        return chain

    def create_experiment_chain(
        self, experiment_name: str, fallback_prompt_name: str, fallback_category: str
    ) -> Runnable:
        """
        创建A/B测试实验链

        Args:
            experiment_name: 实验名称
            fallback_prompt_name: 降级Prompt名称
            fallback_category: 降级Prompt类别

        Returns:
            Runnable: 实验执行链
        """

        async def experiment_prompt_selection(inputs: Dict[str, Any]) -> Dict[str, Any]:
            """实验Prompt选择"""
            try:
                # 首先尝试获取实验Prompt
                # 这里可以实现更复杂的实验逻辑
                prompt_context = self._build_context(inputs)

                # 尝试获取实验Prompt（如果存在）
                try:
                    (
                        prompt_info,
                        rendered_content,
                    ) = await self.prompt_manager.get_prompt(
                        name=f"{experiment_name}_control",  # 控制组
                        category="experiments",
                        context=prompt_context.metadata,
                        variables=prompt_context.variables,
                        enable_experiments=True,
                    )
                except ValueError:
                    # 降级到默认Prompt
                    (
                        prompt_info,
                        rendered_content,
                    ) = await self.prompt_manager.get_prompt(
                        name=fallback_prompt_name,
                        category=fallback_category,
                        context=prompt_context.metadata,
                        variables=prompt_context.variables,
                        enable_experiments=self.enable_experiments,
                    )

                enriched_inputs = inputs.copy()
                enriched_inputs.update(
                    {
                        "system_prompt": rendered_content,
                        "prompt_info": prompt_info,
                        "prompt_context": prompt_context,
                        "experiment_name": experiment_name,
                        "usage_start_time": datetime.now(),
                    }
                )

                return enriched_inputs

            except Exception as e:
                logger.error(f"实验Prompt选择失败: {e}")
                return inputs

        chain = (
            RunnableLambda(experiment_prompt_selection)
            | RunnablePassthrough()
            | RunnableLambda(lambda x: x)
        )

        return chain

    def _build_context(
        self,
        inputs: Dict[str, Any],
        context_builder: Optional[Callable[[Dict[str, Any]], PromptContext]] = None,
    ) -> PromptContext:
        """构建Prompt上下文"""
        if context_builder:
            return context_builder(inputs)

        # 默认上下文构建
        return PromptContext(
            user_request=inputs.get("input", ""),
            session_id=inputs.get("session_id", str(uuid.uuid4())),
            user_id=inputs.get("user_id"),
            request_type=inputs.get("request_type"),
            metadata=inputs.get("metadata", {}),
            variables=inputs.get("variables", {}),
        )

    def _record_usage_start(
        self, prompt_id: uuid.UUID, prompt_context: PromptContext
    ) -> None:
        """记录使用开始（异步）"""
        # 这里可以实现更详细的记录逻辑
        pass

    def create_rag_prompt_chain(self) -> Runnable:
        """创建RAG专用Prompt链"""
        return self.create_prompt_chain(
            prompt_name="rag_response",
            category="RAG",
            context_builder=self._rag_context_builder,
        )

    def create_code_execution_prompt_chain(self) -> Runnable:
        """创建代码执行专用Prompt链"""
        return self.create_prompt_chain(
            prompt_name="code_execution",
            category="Code-Execution",
            context_builder=self._code_execution_context_builder,
        )

    def create_data_analysis_prompt_chain(self) -> Runnable:
        """创建数据分析专用Prompt链"""
        return self.create_prompt_chain(
            prompt_name="data_analysis",
            category="Data-Analysis",
            context_builder=self._data_analysis_context_builder,
        )

    def _rag_context_builder(self, inputs: Dict[str, Any]) -> PromptContext:
        """RAG上下文构建器"""
        return PromptContext(
            user_request=inputs.get("query", ""),
            session_id=inputs.get("session_id", str(uuid.uuid4())),
            request_type="rag",
            metadata={
                "retrieved_docs": inputs.get("retrieved_docs", []),
                "query_type": inputs.get("query_type", "general"),
                "user_history": inputs.get("user_history", []),
            },
            variables={
                "context": "\n\n".join(
                    [doc.get("content", "") for doc in inputs.get("retrieved_docs", [])]
                ),
                "query": inputs.get("query", ""),
                "language": inputs.get("language", "zh-CN"),
            },
        )

    def _code_execution_context_builder(self, inputs: Dict[str, Any]) -> PromptContext:
        """代码执行上下文构建器"""
        return PromptContext(
            user_request=inputs.get("request", ""),
            session_id=inputs.get("session_id", str(uuid.uuid4())),
            request_type="code_execution",
            metadata={
                "language": inputs.get("language", "python"),
                "complexity": inputs.get("complexity", "medium"),
                "environment": inputs.get("environment", "docker"),
            },
            variables={
                "code": inputs.get("code", ""),
                "requirements": inputs.get("requirements", ""),
                "test_cases": inputs.get("test_cases", ""),
                "description": inputs.get("description", ""),
            },
        )

    def _data_analysis_context_builder(self, inputs: Dict[str, Any]) -> PromptContext:
        """数据分析上下文构建器"""
        return PromptContext(
            user_request=inputs.get("request", ""),
            session_id=inputs.get("session_id", str(uuid.uuid4())),
            request_type="data_analysis",
            metadata={
                "data_type": inputs.get("data_type", "tabular"),
                "analysis_type": inputs.get("analysis_type", "eda"),
                "visualization": inputs.get("visualization", True),
            },
            variables={
                "dataset_info": inputs.get("dataset_info", ""),
                "analysis_goals": inputs.get("analysis_goals", ""),
                "data_description": inputs.get("data_description", ""),
                "constraints": inputs.get("constraints", ""),
                "preferred_charts": inputs.get("preferred_charts", ""),
            },
        )


class PromptManagerIntegration:
    """Prompt管理器集成工具类"""

    @staticmethod
    def integrate_with_langgraph(
        workflow, prompt_manager: PromptManager, node_configs: Dict[str, Dict[str, Any]]
    ) -> None:
        """
        将Prompt管理器集成到LangGraph工作流中

        Args:
            workflow: LangGraph工作流
            prompt_manager: Prompt管理器
            node_configs: 节点配置字典
                {
                    'node_name': {
                        'prompt_name': 'prompt_name',
                        'category': 'category',
                        'middleware_config': {}
                    }
                }
        """
        middleware = PromptManagerMiddleware(prompt_manager)

        for node_name, config in node_configs.items():
            # 为每个节点创建Prompt链
            prompt_chain = middleware.create_prompt_chain(
                prompt_name=config["prompt_name"],
                category=config["category"],
                context_builder=config.get("context_builder"),
            )

            # 替换节点逻辑
            workflow.add_node(
                node_name, lambda state, chain=prompt_chain: chain.invoke(state)
            )

    @staticmethod
    def create_prompt_enhanced_agent(
        llm, prompt_manager: PromptManager, system_prompt_category: str = "System"
    ):
        """
        创建Prompt增强的Agent

        Args:
            llm: 语言模型
            prompt_manager: Prompt管理器
            system_prompt_category: 系统Prompt类别

        Returns:
            Prompt增强的Agent
        """
        middleware = PromptManagerMiddleware(prompt_manager)

        async def prompt_enhanced_call(messages: List[BaseMessage]) -> BaseMessage:
            """Prompt增强的调用逻辑"""
            # 构建输入
            last_message = messages[-1] if messages else HumanMessage(content="")

            inputs = {
                "input": last_message.content,
                "messages": messages,
                "session_id": str(uuid.uuid4()),
            }

            # 获取系统Prompt
            try:
                (
                    system_prompt_info,
                    system_prompt_content,
                ) = await prompt_manager.get_prompt(
                    name="agent_system",
                    category=system_prompt_category,
                    context={"message_count": len(messages)},
                    variables={"conversation_history": messages},
                )

                # 构建增强的消息列表
                enhanced_messages = [
                    AIMessage(content=system_prompt_content)
                ] + messages

                # 调用LLM
                response = await llm.ainvoke(enhanced_messages)

                # 记录使用
                usage_log = UsageLog(
                    prompt_id=system_prompt_info.id,
                    session_id=inputs["session_id"],
                    context={"message_count": len(messages)},
                    variables_used={},
                    execution_time_ms=0,  # 这里应该实际计算
                    success=True,
                    tokens_used=response.usage_metadata.get("total_tokens", 0)
                    if hasattr(response, "usage_metadata")
                    else 0,
                )

                asyncio.create_task(prompt_manager.record_usage_log(usage_log))

                return response

            except Exception as e:
                logger.error(f"Prompt增强调用失败: {e}")
                # 降级到直接调用
                return await llm.ainvoke(messages)

        return prompt_enhanced_call
