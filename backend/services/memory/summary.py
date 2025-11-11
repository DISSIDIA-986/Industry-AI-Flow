"""Conversation summarizer using the project LLM stack."""

from __future__ import annotations

import logging
from typing import Iterable, List

from backend.config import settings
from backend.services.llm_integration.llm_client import LLMClientFactory

logger = logging.getLogger(__name__)


class ConversationSummarizer:
    """Produces rolling summaries of recent interactions."""

    def __init__(self) -> None:
        backend = settings.memory_summary_backend or getattr(
            settings, "llm_backend", "llama_cpp"
        )
        try:
            self.client = LLMClientFactory.create_client(backend=backend)
            self.available = True
        except Exception as exc:  # pragma: no cover - defensive
            logger.warning("无法初始化摘要 LLM，记忆摘要被禁用: %s", exc)
            self.client = None
            self.available = False

    def build_summary(
        self,
        existing_summary: str,
        interactions: Iterable[dict],
        language: str = "zh",
    ) -> str:
        """Combine the existing summary with new interactions."""
        if not self.available or not interactions:
            return existing_summary

        interactions_text = "\n".join(
            f"用户: {item['user']}\n助手: {item['assistant']}\n---" for item in interactions
        )

        prompt = f"""
你是一名对话总结助手，请将对话信息总结成200字以内的关键上下文。

现有摘要:
{existing_summary or '（暂无）'}

新增对话:
{interactions_text}

请给出更新后的摘要，包含：
1. 用户的目标和任务
2. 关键细节与限制条件
3. 尚未解决的问题

输出语言：{language}
"""

        try:
            summary = self.client.generate(
                prompt,
                temperature=0.2,
                max_tokens=settings.memory_summary_max_tokens,
            )
            return summary.strip()
        except Exception as exc:  # pragma: no cover - LLM failure
            logger.error("生成对话摘要失败: %s", exc)
            return existing_summary

    @staticmethod
    def format_interactions(
        history: List["InteractionRecord"], since_index: int
    ) -> List[dict]:
        """Utility to convert InteractionRecord objects to prompt-friendly dicts."""
        formatted = []
        for record in history[since_index:]:
            formatted.append(
                {
                    "user": record.user_query,
                    "assistant": record.agent_response,
                    "intent": record.classified_intent,
                }
            )
        return formatted
