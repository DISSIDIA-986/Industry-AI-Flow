"""Structured memory extractor powered by the LLM."""

from __future__ import annotations

import json
import logging
from typing import Iterable, List

from backend.config import settings
from backend.services.llm_integration.llm_client import LLMClientFactory

logger = logging.getLogger(__name__)

EXTRACTION_PROMPT = """Analyze the following conversation and extract structured information into a JSON object with these keys:
- user_profile: Key details about the user (role, expertise, organization)
- preferences: User preferences and settings mentioned in conversation
- tasks: Action items or tasks the user wants to accomplish
- facts: Important factual information shared during the conversation

Only include fields with actual extracted content. Return valid JSON only, with no extra commentary.

Conversation:
{dialogue}
"""


class StructuredMemoryExtractor:
    """LLM-based extractor that produces structured JSON memories."""

    def __init__(self) -> None:
        try:
            self.client = LLMClientFactory.create_client(
                backend=settings.memory_summary_backend or settings.llm_backend
            )
            self.available = True
        except Exception as exc:  # pragma: no cover
            logger.warning("Memory extractor LLM client unavailable: %s", exc)
            self.client = None
            self.available = False

    def extract(self, interactions: Iterable["InteractionRecord"]) -> List[dict]:
        if not self.available:
            return []

        dialogue = "\n".join(
            f"User: {record.user_query}\nAssistant: {record.agent_response}\n"
            for record in interactions
        )
        prompt = EXTRACTION_PROMPT.format(dialogue=dialogue)

        try:
            response = self.client.generate(prompt, temperature=0.0, max_tokens=512)
            json_payload = self._safe_parse_json(response)
        except Exception as exc:  # pragma: no cover
            logger.error("Memory extraction failed: %s", exc)
            return []

        memories: List[dict] = []
        if not isinstance(json_payload, dict):
            return memories

        for memory_type in ("user_profile", "preferences", "tasks", "facts"):
            items = json_payload.get(memory_type) or []
            if isinstance(items, dict):
                items = [items]
            for item in items:
                if item:
                    memories.append(
                        {
                            "memory_type": memory_type,
                            "content": item,
                        }
                    )
        return memories

    @staticmethod
    def _safe_parse_json(payload: str):
        try:
            start = payload.find("{")
            end = payload.rfind("}")
            if start != -1 and end != -1:
                payload = payload[start : end + 1]
            return json.loads(payload)
        except Exception:
            return {}
