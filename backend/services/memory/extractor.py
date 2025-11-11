"""Structured memory extractor powered by the LLM."""

from __future__ import annotations

import json
import logging
from typing import Iterable, List

from backend.config import settings
from backend.services.llm_integration.llm_client import LLMClientFactory

logger = logging.getLogger(__name__)

EXTRACTION_PROMPT = """
你是一名记忆提取助手。给定最新的对话轮次，请提取对未来对话仍然有用的事实，并以 JSON 格式返回，键包括：
- user_profile: 关于用户身份或角色的重要事实
- preferences: 用户的偏好、喜好或风格
- tasks: 用户正在进行或计划进行的任务
- facts: 需要长期保存的重要事实

如果某个字段没有内容，请使用空数组。
仅返回 JSON，不要添加额外文本。

对话内容：
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
            logger.warning("结构化记忆提取不可用: %s", exc)
            self.client = None
            self.available = False

    def extract(self, interactions: Iterable["InteractionRecord"]) -> List[dict]:
        if not self.available:
            return []

        dialogue = "\n".join(
            f"用户: {record.user_query}\n助手: {record.agent_response}\n"
            for record in interactions
        )
        prompt = EXTRACTION_PROMPT.format(dialogue=dialogue)

        try:
            response = self.client.generate(prompt, temperature=0.0, max_tokens=512)
            json_payload = self._safe_parse_json(response)
        except Exception as exc:  # pragma: no cover
            logger.error("提取结构化记忆失败: %s", exc)
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
