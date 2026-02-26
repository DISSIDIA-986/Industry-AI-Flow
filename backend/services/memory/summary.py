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
            logger.warning("Failed to initialize summary LLM client: %s", exc)
            self.client = None
            self.available = False

    def build_summary(
        self,
        existing_summary: str,
        interactions: Iterable[dict],
        language: str = "en",
    ) -> str:
        """Combine the existing summary with new interactions."""
        if not self.available or not interactions:
            return existing_summary

        interactions_text = "\n".join(
            f"User: {item['user']}\nAssistant: {item['assistant']}\n---"
            for item in interactions
        )

        prompt = f"""
Summarize the following conversation history into a concise summary of no more than 200 words.

Existing summary:
{existing_summary or '(No previous summary)'}

New interactions:
{interactions_text}

Instructions:
1. Preserve key facts, decisions, and user preferences from the conversation
2. Merge the existing summary with the new interactions into a single coherent summary
3. Focus on information that would be useful for future interactions

Language: {language}
"""

        try:
            summary = self.client.generate(
                prompt,
                temperature=0.2,
                max_tokens=settings.memory_summary_max_tokens,
            )
            return summary.strip()
        except Exception as exc:  # pragma: no cover - LLM failure
            logger.error("Summary generation failed: %s", exc)
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
