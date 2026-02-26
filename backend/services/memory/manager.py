"""High-level coordination of the three-layer memory system."""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime
from typing import Any, Dict, Optional

from backend.config import settings
from backend.services.memory.extractor import StructuredMemoryExtractor
from backend.services.memory.store import LongTermMemoryStore
from backend.services.memory.summary import ConversationSummarizer

logger = logging.getLogger(__name__)


class ConversationMemoryManager:
    """Orchestrates short-term, summary, and long-term memories."""

    def __init__(
        self,
        config=None,
        summary: ConversationSummarizer | None = None,
        extractor: StructuredMemoryExtractor | None = None,
        store: LongTermMemoryStore | None = None,
    ) -> None:
        self.config = config or settings
        self.enabled = self.config.enable_conversation_memory
        self.short_term_window = self.config.memory_short_term_window
        self.summary_trigger = self.config.memory_summary_trigger_messages
        self.summary = summary or ConversationSummarizer()
        self.extractor = extractor or StructuredMemoryExtractor()
        self.long_term_store = store or LongTermMemoryStore()

    async def process_interaction(self, session, record) -> None:
        """Update summaries and long-term memory after each interaction."""
        if not self.enabled:
            return

        try:
            await self._update_summary(session)
            await self._extract_long_term_memory(session)
        except Exception as exc:  # pragma: no cover - defensive
            logger.error("Memory processing failed: %s", exc)

    async def _update_summary(self, session) -> None:
        history_size = len(session.interaction_history)
        interactions_since_summary = history_size - session.last_summary_record_index
        if interactions_since_summary < self.summary_trigger:
            return

        recent_interactions = session.interaction_history[
            session.last_summary_record_index :
        ]
        interaction_payload = self.summary.format_interactions(
            session.interaction_history, session.last_summary_record_index
        )

        loop = asyncio.get_running_loop()
        new_summary = await loop.run_in_executor(
            None,
            self.summary.build_summary,
            session.summary_memory,
            interaction_payload,
            session.language_preference or "en",
        )

        if new_summary:
            session.summary_memory = new_summary
            session.last_summary_record_index = history_size
            session.last_summary_time = datetime.utcnow()
            logger.debug("Summary updated for session: %s", session.session_id)

    async def _extract_long_term_memory(self, session) -> None:
        recent_interactions = session.interaction_history[-self.summary_trigger :]
        if not recent_interactions:
            return

        loop = asyncio.get_running_loop()
        extracted = await loop.run_in_executor(
            None, self.extractor.extract, recent_interactions
        )
        if not extracted:
            return

        for entry in extracted:
            memory_id = self.long_term_store.store_memory(
                session_id=session.session_id,
                user_id=session.user_id,
                memory_type=entry["memory_type"],
                content=entry["content"],
                metadata={"source": "conversation"},
            )
            session.long_term_memory_refs.append(memory_id)
        session.long_term_memory_refs = session.long_term_memory_refs[-20:]

    def build_memory_payload(
        self, session, user_query: Optional[str]
    ) -> Dict[str, Any]:
        if not self.enabled:
            return {}

        short_term_messages = self._format_short_term(session)
        summary_text = session.summary_memory

        long_term_memories = []
        if user_query:
            long_term_memories = self.long_term_store.search_memories(
                query=user_query,
                top_k=self.config.memory_long_term_top_k,
                min_similarity=self.config.memory_long_term_min_relevance,
                session_id=session.session_id,
            )

        return {
            "short_term": short_term_messages,
            "summary": summary_text,
            "long_term": long_term_memories,
        }

    def _format_short_term(self, session) -> list:
        """Return the most recent dialogue turns."""
        window = session.interaction_history[-self.short_term_window :]
        formatted = []
        for record in window:
            formatted.append({"role": "user", "content": record.user_query})
            formatted.append({"role": "assistant", "content": record.agent_response})
        return formatted
