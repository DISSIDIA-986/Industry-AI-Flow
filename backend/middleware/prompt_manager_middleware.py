"""
LangChain 1.0 Prompt Manager Middleware
ENPromptEN,EN,A/BEN
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
    """PromptEN"""

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
    """PromptEN"""

    def __init__(self, prompt_manager: PromptManager):
        self.prompt_manager = prompt_manager
        self.usage_logs: List[Dict[str, Any]] = []

    async def on_llm_start(
        self, serialized: Dict[str, Any], prompts: List[str], **kwargs: Any
    ) -> None:
        """LLMEN"""
        # ENPromptEN
        pass

    async def on_llm_end(self, response, **kwargs: Any) -> None:
        """LLMEN"""
        # EN
        pass


class PromptManagerMiddleware:
    """
    PromptEN

    EN:
    1. ENPromptEN
    2. EN
    3. A/BEN
    4. EN
    5. EN
    """

    def __init__(
        self,
        prompt_manager: PromptManager,
        enable_experiments: bool = True,
        enable_monitoring: bool = True,
        context_enrichers: Optional[List[Callable]] = None,
    ):
        """
        EN

        Args:
            prompt_manager: PromptEN
            enable_experiments: ENA/BEN
            enable_monitoring: EN
            context_enrichers: EN
        """
        self.prompt_manager = prompt_manager
        self.enable_experiments = enable_experiments
        self.enable_monitoring = enable_monitoring
        self.context_enrichers = context_enrichers or []

        logger.info("PromptEN")

    def create_prompt_chain(
        self,
        prompt_name: str,
        category: str,
        context_builder: Optional[Callable[[Dict[str, Any]], PromptContext]] = None,
    ) -> Runnable:
        """
        ENPromptEN

        Args:
            prompt_name: PromptEN
            category: PromptEN
            context_builder: EN

        Returns:
            Runnable: EN
        """

        async def process_input(inputs: Dict[str, Any]) -> Dict[str, Any]:
            """EN,ENPrompt"""
            try:
                # EN
                prompt_context = self._build_context(inputs, context_builder)

                # ENPrompt
                prompt_info, rendered_content = await self.prompt_manager.get_prompt(
                    name=prompt_name,
                    category=category,
                    context=prompt_context.metadata,
                    variables=prompt_context.variables,
                    enable_experiments=self.enable_experiments,
                )

                # ENPromptEN
                enriched_inputs = inputs.copy()
                enriched_inputs.update(
                    {
                        "system_prompt": rendered_content,
                        "prompt_info": prompt_info,
                        "prompt_context": prompt_context,
                        "usage_start_time": datetime.now(),
                    }
                )

                # EN
                if self.enable_monitoring:
                    self._record_usage_start(prompt_info.id, prompt_context)

                logger.debug(f"PromptEN: {category}/{prompt_name}")
                return enriched_inputs

            except Exception as e:
                logger.error(f"PromptEN: {e}")
                # EN:EN
                return inputs

        async def process_output(
            outputs: Dict[str, Any], inputs: Dict[str, Any]
        ) -> Dict[str, Any]:
            """EN,EN"""
            try:
                if "prompt_info" in inputs and "usage_start_time" in inputs:
                    prompt_info = inputs["prompt_info"]
                    usage_start_time = inputs["usage_start_time"]

                    # EN
                    execution_time_ms = int(
                        (datetime.now() - usage_start_time).total_seconds() * 1000
                    )

                    # EN
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

                    # EN
                    if self.enable_monitoring:
                        asyncio.create_task(
                            self.prompt_manager.record_usage_log(usage_log)
                        )

                    # EN
                    outputs["prompt_performance"] = {
                        "prompt_id": str(prompt_info.id),
                        "prompt_name": prompt_info.name,
                        "prompt_version": prompt_info.version,
                        "execution_time_ms": execution_time_ms,
                        "performance_score": prompt_info.performance_score,
                    }

                return outputs

            except Exception as e:
                logger.error(f"EN: {e}")
                return outputs

        # EN
        chain = (
            RunnableLambda(process_input)
            | RunnablePassthrough()
            | RunnableLambda(lambda outputs: outputs)  # EN
            | RunnableLambda(process_output)
        )

        return chain

    def create_adaptive_prompt_chain(
        self,
        prompt_categories: List[str],
        context_analyzer: Callable[[Dict[str, Any]], str],
    ) -> Runnable:
        """
        ENPromptEN,EN

        Args:
            prompt_categories: ENPromptEN
            context_analyzer: EN,EN

        Returns:
            Runnable: EN
        """

        async def adaptive_prompt_selection(inputs: Dict[str, Any]) -> Dict[str, Any]:
            """ENPromptEN"""
            try:
                # EN,EN
                selected_category = context_analyzer(inputs)

                if selected_category not in prompt_categories:
                    logger.warning(f"EN: {selected_category}")
                    selected_category = prompt_categories[0]  # EN

                # EN
                prompt_context = self._build_context(inputs)

                # ENPrompt
                prompt_info, rendered_content = await self.prompt_manager.get_prompt(
                    name=inputs.get("task_name", "default"),  # EN
                    category=selected_category,
                    context=prompt_context.metadata,
                    variables=prompt_context.variables,
                    enable_experiments=self.enable_experiments,
                )

                # ENPrompt
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
                logger.error(f"ENPromptEN: {e}")
                return inputs

        # EN
        chain = (
            RunnableLambda(adaptive_prompt_selection)
            | RunnablePassthrough()
            | RunnableLambda(lambda x: x)  # EN
        )

        return chain

    def create_experiment_chain(
        self, experiment_name: str, fallback_prompt_name: str, fallback_category: str
    ) -> Runnable:
        """
        ENA/BEN

        Args:
            experiment_name: EN
            fallback_prompt_name: ENPromptEN
            fallback_category: ENPromptEN

        Returns:
            Runnable: EN
        """

        async def experiment_prompt_selection(inputs: Dict[str, Any]) -> Dict[str, Any]:
            """ENPromptEN"""
            try:
                # ENPrompt
                # EN
                prompt_context = self._build_context(inputs)

                # ENPrompt(EN)
                try:
                    (
                        prompt_info,
                        rendered_content,
                    ) = await self.prompt_manager.get_prompt(
                        name=f"{experiment_name}_control",  # EN
                        category="experiments",
                        context=prompt_context.metadata,
                        variables=prompt_context.variables,
                        enable_experiments=True,
                    )
                except ValueError:
                    # ENPrompt
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
                logger.error(f"ENPromptEN: {e}")
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
        """ENPromptEN"""
        if context_builder:
            return context_builder(inputs)

        # EN
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
        """EN(EN)"""
        # EN
        pass

    def create_rag_prompt_chain(self) -> Runnable:
        """ENRAGENPromptEN"""
        return self.create_prompt_chain(
            prompt_name="rag_response",
            category="RAG",
            context_builder=self._rag_context_builder,
        )

    def create_code_execution_prompt_chain(self) -> Runnable:
        """ENPromptEN"""
        return self.create_prompt_chain(
            prompt_name="code_execution",
            category="Code-Execution",
            context_builder=self._code_execution_context_builder,
        )

    def create_data_analysis_prompt_chain(self) -> Runnable:
        """ENPromptEN"""
        return self.create_prompt_chain(
            prompt_name="data_analysis",
            category="Data-Analysis",
            context_builder=self._data_analysis_context_builder,
        )

    def _rag_context_builder(self, inputs: Dict[str, Any]) -> PromptContext:
        """RAGEN"""
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
        """EN"""
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
        """EN"""
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
    """PromptEN"""

    @staticmethod
    def integrate_with_langgraph(
        workflow, prompt_manager: PromptManager, node_configs: Dict[str, Dict[str, Any]]
    ) -> None:
        """
        ENPromptENLangGraphEN

        Args:
            workflow: LangGraphEN
            prompt_manager: PromptEN
            node_configs: EN
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
            # ENPromptEN
            prompt_chain = middleware.create_prompt_chain(
                prompt_name=config["prompt_name"],
                category=config["category"],
                context_builder=config.get("context_builder"),
            )

            # EN
            workflow.add_node(
                node_name, lambda state, chain=prompt_chain: chain.invoke(state)
            )

    @staticmethod
    def create_prompt_enhanced_agent(
        llm, prompt_manager: PromptManager, system_prompt_category: str = "System"
    ):
        """
        ENPromptENAgent

        Args:
            llm: EN
            prompt_manager: PromptEN
            system_prompt_category: ENPromptEN

        Returns:
            PromptENAgent
        """
        middleware = PromptManagerMiddleware(prompt_manager)

        async def prompt_enhanced_call(messages: List[BaseMessage]) -> BaseMessage:
            """PromptEN"""
            # EN
            last_message = messages[-1] if messages else HumanMessage(content="")

            inputs = {
                "input": last_message.content,
                "messages": messages,
                "session_id": str(uuid.uuid4()),
            }

            # ENPrompt
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

                # EN
                enhanced_messages = [
                    AIMessage(content=system_prompt_content)
                ] + messages

                # ENLLM
                response = await llm.ainvoke(enhanced_messages)

                # EN
                usage_log = UsageLog(
                    prompt_id=system_prompt_info.id,
                    session_id=inputs["session_id"],
                    context={"message_count": len(messages)},
                    variables_used={},
                    execution_time_ms=0,  # EN
                    success=True,
                    tokens_used=response.usage_metadata.get("total_tokens", 0)
                    if hasattr(response, "usage_metadata")
                    else 0,
                )

                asyncio.create_task(prompt_manager.record_usage_log(usage_log))

                return response

            except Exception as e:
                logger.error(f"PromptEN: {e}")
                # EN
                return await llm.ainvoke(messages)

        return prompt_enhanced_call
