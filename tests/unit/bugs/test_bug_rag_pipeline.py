"""BUG-5 (High): _record_memory_interaction spawns unbounded threads.

`SimpleRAG._record_memory_interaction` spawns a new `threading.Thread` per
interaction when an asyncio event loop is already running.  Each thread calls
`asyncio.run()`, creating a new event loop.  Under sustained load, this
causes thread accumulation and potential resource exhaustion.

This test asserts that the memory recording mechanism does NOT spawn unbounded
threads.  It should FAIL until the threading model is fixed (e.g., using a
bounded thread pool or task queue).
"""

from __future__ import annotations

import asyncio
import sys
import threading
import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

pytestmark = pytest.mark.filterwarnings(
    "ignore:datetime\\.datetime\\.utcnow\\(\\) is deprecated.*:DeprecationWarning"
)


@pytest.mark.unit
class TestBug5MemoryInteractionThreadLeak:
    def test_record_memory_does_not_spawn_thread_per_call(self):
        """Recording 20 memory interactions should NOT create 20 threads."""
        # Count threads before and after
        initial_thread_count = threading.active_count()

        # Mock out all the heavy dependencies
        with (
            patch("backend.services.rag_engine.VectorStore"),
            patch("backend.services.rag_engine.get_llm_client"),
            patch(
                "backend.services.rag_engine.get_backend_status",
                return_value={"backend": "mock"},
            ),
            patch("backend.services.rag_engine.HybridRetriever"),
            patch("backend.services.rag_engine.Reranker"),
            patch("backend.services.rag_engine.FeedbackManager"),
            patch("backend.services.rag_engine.create_safety_guard", return_value=None),
            patch("backend.services.rag_engine.settings") as mock_settings,
        ):
            mock_settings.enable_safety_guard = False
            mock_settings.enable_conversation_memory = True

            # Mock ConversationMemoryManager
            with patch(
                "backend.services.rag_engine.ConversationMemoryManager"
            ) as MockMemoryManager:
                mock_manager = MagicMock()
                # Make process_interaction a coroutine
                mock_manager.process_interaction = AsyncMock()
                mock_manager.build_memory_payload = MagicMock(return_value={})
                MockMemoryManager.return_value = mock_manager

                from backend.services.rag_engine import SimpleRAG, _MemorySession

                rag = SimpleRAG.__new__(SimpleRAG)
                rag.memory_manager = mock_manager
                rag._memory_sessions = {}
                rag._memory_lock = threading.Lock()

                session = _MemorySession(session_id="test-session")

                # Simulate having a running event loop (as in FastAPI)
                loop = asyncio.new_event_loop()

                def run_in_loop():
                    asyncio.set_event_loop(loop)
                    try:
                        loop.run_until_complete(asyncio.sleep(2))
                    except RuntimeError as exc:
                        if "Event loop stopped before Future completed." not in str(
                            exc
                        ):
                            raise

                loop_thread = threading.Thread(target=run_in_loop, daemon=True)
                loop_thread.start()
                time.sleep(0.1)  # Let the loop start

                # Record 20 interactions
                for i in range(20):
                    rag._record_memory_interaction(
                        session, f"question_{i}", f"answer_{i}"
                    )

                # Give threads time to start
                time.sleep(0.5)

                thread_count_after = threading.active_count()
                new_threads = thread_count_after - initial_thread_count

                # Cleanup
                loop.call_soon_threadsafe(loop.stop)
                loop_thread.join(timeout=2)
                loop.close()

        # Allow for the event loop thread + some overhead, but NOT 20 new threads
        assert new_threads <= 5, (
            f"BUG-5: _record_memory_interaction spawned {new_threads} threads for "
            f"20 interactions. This will cause thread exhaustion under load. "
            f"Expected at most 5 (1 event loop + bounded pool)."
        )
