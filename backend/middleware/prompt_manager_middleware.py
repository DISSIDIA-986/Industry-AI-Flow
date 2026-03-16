"""
LangChain 1.0 Prompt Manager Middleware
Integrates prompt management into LangChain pipelines with versioning, monitoring, and A/B testing support.
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
    """Prompt execution context for a single request."""

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
    """Callback handler for tracking prompt usage during LLM calls."""

    def __init__(self, prompt_manager: PromptManager):
        self.prompt_manager = prompt_manager
        self.usage_logs: List[Dict[str, Any]] = []

    async def on_llm_start(
        self, serialized: Dict[str, Any], prompts: List[str], **kwargs: Any
    ) -> None:
        """Called when LLM starts generating."""
        # Record prompt usage start event
        pass

    async def on_llm_end(self, response, **kwargs: Any) -> None:
        """Called when LLM finishes generating."""
        # Record prompt usage end event
        pass


class PromptManagerMiddleware:
    """
    Prompt Manager Middleware for LangChain pipelines.

    Capabilities:
    1. Automatic prompt retrieval and rendering
    2. Variable injection and template processing
    3. A/B experiment prompt selection
    4. Usage monitoring and performance tracking
    5. Context-aware prompt enrichment
    """

    def __init__(
        self,
        prompt_manager: PromptManager,
        enable_experiments: bool = True,
        enable_monitoring: bool = True,
        context_enrichers: Optional[List[Callable]] = None,
    ):
        """
        Initialize the prompt manager middleware.

        Args:
            prompt_manager: Prompt manager instance
            enable_experiments: Enable A/B experiment prompt selection
            enable_monitoring: Enable usage monitoring
            context_enrichers: List of context enrichment functions
        """
        self.prompt_manager = prompt_manager
        self.enable_experiments = enable_experiments
        self.enable_monitoring = enable_monitoring
        self.context_enrichers = context_enrichers or []

        logger.info("Prompt manager middleware initialized")

    def create_prompt_chain(
        self,
        prompt_name: str,
        category: str,
        context_builder: Optional[Callable[[Dict[str, Any]], PromptContext]] = None,
    ) -> Runnable:
        """
        Create a LangChain Runnable chain that manages prompt retrieval and rendering.

        Args:
            prompt_name: Prompt template name
            category: Prompt category
            context_builder: Optional function to build prompt context from inputs

        Returns:
            Runnable: A LangChain Runnable chain with prompt management
        """

        async def process_input(inputs: Dict[str, Any]) -> Dict[str, Any]:
            """Process input and retrieve the managed prompt."""
            try:
                # Build prompt context
                prompt_context = self._build_context(inputs, context_builder)

                # Retrieve and render the prompt
                prompt_info, rendered_content = await self.prompt_manager.get_prompt(
                    name=prompt_name,
                    category=category,
                    context=prompt_context.metadata,
                    variables=prompt_context.variables,
                    enable_experiments=self.enable_experiments,
                )

                # Enrich inputs with prompt information
                enriched_inputs = inputs.copy()
                enriched_inputs.update(
                    {
                        "system_prompt": rendered_content,
                        "prompt_info": prompt_info,
                        "prompt_context": prompt_context,
                        "usage_start_time": datetime.now(),
                    }
                )

                # Start monitoring if enabled
                if self.enable_monitoring:
                    self._record_usage_start(prompt_info.id, prompt_context)

                logger.debug(f"Prompt loaded: {category}/{prompt_name}")
                return enriched_inputs

            except Exception as e:
                logger.error(f"Prompt retrieval failed: {e}")
                # Fallback: return original inputs without prompt enrichment
                return inputs

        async def process_output(
            outputs: Dict[str, Any], inputs: Dict[str, Any]
        ) -> Dict[str, Any]:
            """Process output and record usage metrics."""
            try:
                if "prompt_info" in inputs and "usage_start_time" in inputs:
                    prompt_info = inputs["prompt_info"]
                    usage_start_time = inputs["usage_start_time"]

                    # Calculate execution time
                    execution_time_ms = int(
                        (datetime.now() - usage_start_time).total_seconds() * 1000
                    )

                    # Build usage log entry
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

                    # Record usage log asynchronously
                    if self.enable_monitoring:
                        asyncio.create_task(
                            self.prompt_manager.record_usage_log(usage_log)
                        )

                    # Attach prompt performance metadata to output
                    outputs["prompt_performance"] = {
                        "prompt_id": str(prompt_info.id),
                        "prompt_name": prompt_info.name,
                        "prompt_version": prompt_info.version,
                        "execution_time_ms": execution_time_ms,
                        "performance_score": prompt_info.performance_score,
                    }

                return outputs

            except Exception as e:
                logger.error(f"Output processing failed: {e}")
                return outputs

        # Build the prompt chain
        chain = (
            RunnableLambda(process_input)
            | RunnablePassthrough()
            | RunnableLambda(lambda outputs: outputs)  # Placeholder for LLM call
            | RunnableLambda(process_output)
        )

        return chain

    def create_adaptive_prompt_chain(
        self,
        prompt_categories: List[str],
        context_analyzer: Callable[[Dict[str, Any]], str],
    ) -> Runnable:
        """
        Create an adaptive prompt chain that selects prompt category based on context.

        Args:
            prompt_categories: List of available prompt categories
            context_analyzer: Function to analyze context and select a category

        Returns:
            Runnable: A LangChain Runnable chain with adaptive prompt selection
        """

        async def adaptive_prompt_selection(inputs: Dict[str, Any]) -> Dict[str, Any]:
            """Select and retrieve the best prompt based on context analysis."""
            try:
                # Analyze context to determine the best prompt category
                selected_category = context_analyzer(inputs)

                if selected_category not in prompt_categories:
                    logger.warning(f"Unknown category selected: {selected_category}")
                    selected_category = prompt_categories[
                        0
                    ]  # Fallback to first category

                # Build prompt context
                prompt_context = self._build_context(inputs)

                # Retrieve the prompt for the selected category
                prompt_info, rendered_content = await self.prompt_manager.get_prompt(
                    name=inputs.get("task_name", "default"),  # Use task name or default
                    category=selected_category,
                    context=prompt_context.metadata,
                    variables=prompt_context.variables,
                    enable_experiments=self.enable_experiments,
                )

                # Enrich inputs with the selected prompt
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
                logger.error(f"Adaptive prompt selection failed: {e}")
                return inputs

        # Build the adaptive prompt chain
        chain = (
            RunnableLambda(adaptive_prompt_selection)
            | RunnablePassthrough()
            | RunnableLambda(lambda x: x)  # Placeholder for LLM call
        )

        return chain

    def create_experiment_chain(
        self, experiment_name: str, fallback_prompt_name: str, fallback_category: str
    ) -> Runnable:
        """
        Create an A/B experiment prompt chain.

        Args:
            experiment_name: Name of the experiment
            fallback_prompt_name: Fallback prompt name if experiment is unavailable
            fallback_category: Fallback prompt category

        Returns:
            Runnable: A LangChain Runnable chain for experiment prompt selection
        """

        async def experiment_prompt_selection(inputs: Dict[str, Any]) -> Dict[str, Any]:
            """Select prompt based on experiment allocation."""
            try:
                # Retrieve experiment prompt
                # Build context for experiment prompt selection
                prompt_context = self._build_context(inputs)

                # Try to get experiment control prompt (primary)
                try:
                    (
                        prompt_info,
                        rendered_content,
                    ) = await self.prompt_manager.get_prompt(
                        name=f"{experiment_name}_control",  # Control group prompt
                        category="experiments",
                        context=prompt_context.metadata,
                        variables=prompt_context.variables,
                        enable_experiments=True,
                    )
                except ValueError:
                    # Experiment prompt not found, use fallback
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
                logger.error(f"Experiment prompt selection failed: {e}")
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
        """Build a PromptContext from the input dictionary."""
        if context_builder:
            return context_builder(inputs)

        # Build default prompt context from inputs
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
        """Record prompt usage start (placeholder for future implementation)."""
        # Placeholder for usage tracking
        pass

    def create_rag_prompt_chain(self) -> Runnable:
        """Create a prompt chain for RAG response generation."""
        return self.create_prompt_chain(
            prompt_name="rag_response",
            category="RAG",
            context_builder=self._rag_context_builder,
        )

    def create_code_execution_prompt_chain(self) -> Runnable:
        """Create a prompt chain for code execution tasks."""
        return self.create_prompt_chain(
            prompt_name="code_execution",
            category="Code-Execution",
            context_builder=self._code_execution_context_builder,
        )

    def create_data_analysis_prompt_chain(self) -> Runnable:
        """Create a prompt chain for data analysis tasks."""
        return self.create_prompt_chain(
            prompt_name="data_analysis",
            category="Data-Analysis",
            context_builder=self._data_analysis_context_builder,
        )

    def _rag_context_builder(self, inputs: Dict[str, Any]) -> PromptContext:
        """Build prompt context for RAG queries."""
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
        """Build prompt context for code execution tasks."""
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
        """Build prompt context for data analysis tasks."""
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
    """Helper class for integrating prompt management with LangGraph workflows."""

    @staticmethod
    def integrate_with_langgraph(
        workflow, prompt_manager: PromptManager, node_configs: Dict[str, Dict[str, Any]]
    ) -> None:
        """
        Integrate prompt management into a LangGraph workflow.

        Args:
            workflow: LangGraph workflow instance
            prompt_manager: Prompt manager instance
            node_configs: Node configuration mapping
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
            # Create a prompt chain for each configured node
            prompt_chain = middleware.create_prompt_chain(
                prompt_name=config["prompt_name"],
                category=config["category"],
                context_builder=config.get("context_builder"),
            )

            # Add the prompt-enhanced node to the workflow
            workflow.add_node(
                node_name, lambda state, chain=prompt_chain: chain.invoke(state)
            )

    @staticmethod
    def create_prompt_enhanced_agent(
        llm, prompt_manager: PromptManager, system_prompt_category: str = "System"
    ):
        """
        Create an agent enhanced with prompt management.

        Args:
            llm: LLM instance
            prompt_manager: Prompt manager instance
            system_prompt_category: System prompt category name

        Returns:
            Prompt-enhanced agent callable
        """
        middleware = PromptManagerMiddleware(prompt_manager)

        async def prompt_enhanced_call(messages: List[BaseMessage]) -> BaseMessage:
            """Call LLM with prompt-managed system prompt."""
            # Get the last message
            last_message = messages[-1] if messages else HumanMessage(content="")

            inputs = {
                "input": last_message.content,
                "messages": messages,
                "session_id": str(uuid.uuid4()),
            }

            # Retrieve the system prompt
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

                # Prepend system prompt to messages
                enhanced_messages = [
                    AIMessage(content=system_prompt_content)
                ] + messages

                # Call the LLM with enhanced messages
                response = await llm.ainvoke(enhanced_messages)

                # Record usage log
                usage_log = UsageLog(
                    prompt_id=system_prompt_info.id,
                    session_id=inputs["session_id"],
                    context={"message_count": len(messages)},
                    variables_used={},
                    execution_time_ms=0,  # Placeholder: actual timing not tracked here
                    success=True,
                    tokens_used=response.usage_metadata.get("total_tokens", 0)
                    if hasattr(response, "usage_metadata")
                    else 0,
                )

                asyncio.create_task(prompt_manager.record_usage_log(usage_log))

                return response

            except Exception as e:
                logger.error(f"Prompt-enhanced call failed: {e}")
                # Fallback: call LLM without prompt enhancement
                return await llm.ainvoke(messages)

        return prompt_enhanced_call
