import asyncio
from datetime import datetime
from types import SimpleNamespace

import pytest

from backend.services.context_manager import InteractionRecord, SessionContext
from backend.services.memory.manager import ConversationMemoryManager


class DummySummarizer:
    def __init__(self):
        self.calls = 0

    def build_summary(self, existing_summary, interactions, language):
        self.calls += 1
        return f"summary-{self.calls}"

    @staticmethod
    def format_interactions(history, since_index):
        return [
            {"user": record.user_query, "assistant": record.agent_response}
            for record in history[since_index:]
        ]


class DummyExtractor:
    def __init__(self):
        self.calls = 0

    def extract(self, interactions):
        self.calls += 1
        if not interactions:
            return []
        return [
            {
                "memory_type": "facts",
                "content": {"detail": f"call-{self.calls}", "turns": len(interactions)},
            }
        ]


class DummyStore:
    def __init__(self):
        self.stored = []
        self.last_query = None

    def store_memory(self, session_id, user_id, memory_type, content, metadata):
        memory_id = f"mem-{len(self.stored)}"
        self.stored.append(
            {
                "id": memory_id,
                "session_id": session_id,
                "user_id": user_id,
                "memory_type": memory_type,
                "content": content,
                "metadata": metadata,
            }
        )
        return memory_id

    def search_memories(self, query, top_k, min_similarity, session_id=None):
        self.last_query = {
            "query": query,
            "top_k": top_k,
            "min_similarity": min_similarity,
            "session_id": session_id,
        }
        return [
            {
                "memory_id": "mem-long-1",
                "memory_type": "tasks",
                "content": {"task": "analysis"},
                "relevance": 0.67,
            }
        ]


def _make_config(**overrides):
    defaults = dict(
        enable_conversation_memory=True,
        memory_short_term_window=4,
        memory_summary_trigger_messages=2,
        memory_summary_backend="llama_cpp",
        memory_summary_max_tokens=256,
        memory_long_term_top_k=3,
        memory_long_term_min_relevance=0.3,
    )
    defaults.update(overrides)
    return SimpleNamespace(**defaults)


def _make_interaction(text, idx=0):
    return InteractionRecord(
        record_id=f"rec-{idx}",
        timestamp=datetime_now(),
        user_query=f"User says {text}",
        classified_intent="general",
        agent_response="Assistant reply",
        confidence=0.9,
        processing_time_ms=100,
    )


def datetime_now():
    return datetime.now()


@pytest.mark.asyncio
async def test_process_interaction_updates_summary_and_long_term_memory():
    config = _make_config(memory_summary_trigger_messages=1)
    summarizer = DummySummarizer()
    extractor = DummyExtractor()
    store = DummyStore()
    manager = ConversationMemoryManager(
        config=config, summary=summarizer, extractor=extractor, store=store
    )

    session = SessionContext(session_id="session-1", user_id="user-42")
    record = _make_interaction("hello", 1)
    session.add_interaction(record)

    await manager.process_interaction(session, record)

    assert session.summary_memory == "summary-1"
    assert session.last_summary_record_index == len(session.interaction_history)
    assert store.stored, "long term memory should be persisted"
    assert session.long_term_memory_refs, "session tracks latest memory ids"


@pytest.mark.asyncio
async def test_build_memory_payload_returns_three_layers():
    config = _make_config(memory_short_term_window=2)
    store = DummyStore()
    manager = ConversationMemoryManager(
        config=config,
        summary=DummySummarizer(),
        extractor=DummyExtractor(),
        store=store,
    )

    session = SessionContext(session_id="session-payload")
    session.summary_memory = "Existing summary"

    for idx in range(3):
        session.add_interaction(_make_interaction(f"msg-{idx}", idx))

    payload = manager.build_memory_payload(session, user_query="最新问题")

    assert "short_term" in payload and len(payload["short_term"]) == 4
    assert payload["summary"] == "Existing summary"
    assert payload["long_term"] and payload["long_term"][0]["memory_id"] == "mem-long-1"
    assert store.last_query["query"] == "最新问题"
