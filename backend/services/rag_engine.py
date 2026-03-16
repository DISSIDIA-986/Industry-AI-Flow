import asyncio
import logging
import threading
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from backend.config import settings
from backend.services.cache.query_cache import query_cache
from backend.services.core.embedder import embed_query_text, embedding_backend_status
from backend.services.core.vectorstore import VectorStore
from backend.services.feedback_system.feedback_manager import (
    FeedbackManager,
    FeedbackType,
    UserFeedback,
)
from backend.services.llm_integration.llm_client import (
    get_backend_status,
    get_llm_client,
)
from backend.services.memory.manager import ConversationMemoryManager
from backend.services.retrieval.hybrid_search import HybridRetriever
from backend.services.retrieval.reranker import Reranker
from backend.services.safety import create_safety_guard

logger = logging.getLogger(__name__)


@dataclass
class _MemoryInteraction:
    user_query: str
    agent_response: str
    timestamp: datetime = field(default_factory=datetime.utcnow)
    classified_intent: str = "rag_query"
    confidence: float = 1.0
    processing_time_ms: int = 0
    success: bool = True


@dataclass
class _MemorySession:
    session_id: str
    user_id: Optional[str] = None
    language_preference: str = "en"
    interaction_history: list[_MemoryInteraction] = field(default_factory=list)
    summary_memory: str = ""
    last_summary_time: Optional[datetime] = None
    last_summary_record_index: int = 0
    long_term_memory_refs: list[str] = field(default_factory=list)


class SimpleRAG:
    def __init__(
        self,
        use_hybrid_search: bool = True,
        use_reranker: bool = True,
        enable_feedback: bool = True,
    ):
        """
        Initialize the RAG engine with configurable retrieval components.

        Args:
            use_hybrid_search: Enable hybrid search (BM25 + vector similarity)
            use_reranker: Enable cross-encoder reranking
            enable_feedback: Enable user feedback collection
        """
        self.vectorstore = VectorStore()
        self.llm_client = get_llm_client()  # Initialize LLM client
        self.use_hybrid_search = use_hybrid_search
        self.use_reranker = use_reranker
        self.enable_feedback = enable_feedback

        # Log LLM backend status
        backend_status = get_backend_status()
        logger.info(
            f"✅ RAG engine initialized - LLM backend: {backend_status.get('backend', 'unknown')}"
        )

        # Phase 2 Step 2: Initialize hybrid retriever
        if use_hybrid_search:
            self.hybrid_retriever = HybridRetriever(self.vectorstore)
        else:
            self.hybrid_retriever = None

        # Phase 2 Step 3: Initialize cross-encoder reranker
        if use_reranker:
            self.reranker = Reranker()
        else:
            self.reranker = None

        # Initialize feedback manager
        if enable_feedback:
            self.feedback_manager = FeedbackManager(self.vectorstore, self.reranker)
        else:
            self.feedback_manager = None

        self.safety_guard = None
        if getattr(settings, "enable_safety_guard", True):
            try:
                self.safety_guard = create_safety_guard(
                    confidence_threshold=getattr(
                        settings, "safety_confidence_threshold", 0.8
                    )
                )
            except Exception as exc:
                logger.warning("Failed to initialize safety guard: %s", exc)

        self.memory_manager: Optional[ConversationMemoryManager] = None
        self._memory_sessions: dict[str, _MemorySession] = {}
        self._memory_lock = threading.Lock()
        self._max_sessions = 1000
        if getattr(settings, "enable_conversation_memory", False):
            try:
                self.memory_manager = ConversationMemoryManager()
            except Exception as exc:  # pragma: no cover - defensive
                logger.warning(
                    "Failed to initialize conversation memory manager: %s", exc
                )

    def query(
        self,
        question: str,
        top_k: int = None,
        temperature: float = None,
        max_tokens: int = None,
        session_id: Optional[str] = None,
        user_id: Optional[str] = None,
    ) -> dict:
        """Execute a RAG query and return the generated answer with sources."""
        if top_k is None:
            top_k = settings.top_k

        # Check query cache first
        tenant_id = user_id or "default"
        cached = query_cache.get(tenant_id, question, top_k)
        if cached is not None:
            logger.info("RAG query cache hit for: %s", question[:60])
            return cached

        # Generate unique query ID for tracking
        query_id = str(uuid.uuid4())

        # Get adaptive search weights (based on feedback)
        vector_weight, bm25_weight = self._get_adaptive_search_weights()

        # Phase 2 Step 2: Retrieve documents
        if self.use_hybrid_search and self.hybrid_retriever:
            # Hybrid search (BM25 + vector similarity), over-retrieve for reranking (top_k * 2)
            retrieve_k = top_k * 2 if self.use_reranker else top_k
            similar_chunks = self.hybrid_retriever.search(
                query=question,
                top_k=retrieve_k,
                vector_weight=vector_weight,
                bm25_weight=bm25_weight,
            )
        else:
            # Vector-only search fallback (Phase 1 baseline)
            retrieve_k = top_k * 2 if self.use_reranker else top_k
            query_embedding = embed_query_text(question)
            similar_chunks = self.vectorstore.similarity_search(
                query_embedding, top_k=retrieve_k
            )

        # Phase 2 Step 3: Rerank retrieved documents
        if self.use_reranker and self.reranker and similar_chunks:
            similar_chunks = self.reranker.rerank(
                query=question, documents=similar_chunks, top_k=top_k
            )

        # 3. Build context from retrieved chunks
        # Format each chunk with document numbering
        context_parts = []
        for i, chunk in enumerate(similar_chunks, 1):
            context_parts.append(f"[Reference {i}]\n{chunk['content']}")
        context = "\n\n".join(context_parts)

        memory_payload = {}
        memory_session = None
        if self.memory_manager is not None:
            memory_session = self._get_or_create_memory_session(
                session_id=session_id, user_id=user_id
            )
            memory_payload = self.memory_manager.build_memory_payload(
                memory_session, question
            )

        prompt = self._build_prompt(question, context, memory_payload)

        # 4. LLM generation
        try:
            answer = self.llm_client.generate(
                prompt, temperature=temperature, max_tokens=max_tokens
            )
        except Exception as exc:
            logger.error("LLM generation failed: %s", exc)
            answer = "I'm sorry, the language model is temporarily unavailable. Please try again shortly."

        safety_result = None
        if self.safety_guard is not None:
            try:
                context_texts = [chunk.get("content", "") for chunk in similar_chunks]
                safety_result = self.safety_guard.process_response(
                    answer=answer,
                    context=context_texts,
                    llm_client=None,  # Lexical-only check; skip extra LLM call for speed
                )
                answer = safety_result.get("enhanced_answer", answer)
                if hasattr(safety_result.get("safety_level"), "value"):
                    safety_result["safety_level"] = safety_result["safety_level"].value
            except Exception as exc:
                logger.warning("Safety guard failed, using raw answer: %s", exc)

        if memory_session is not None:
            self._record_memory_interaction(memory_session, question, answer)

        # 5. Build and return response
        embed_status = embedding_backend_status()
        result = {
            "query_id": query_id,
            "question": question,
            "answer": answer,
            "sources": [chunk["doc_id"] for chunk in similar_chunks],
            "retrieved_chunks": similar_chunks,
            "search_weights": {
                "vector_weight": vector_weight,
                "bm25_weight": bm25_weight,
            },
            "safety": safety_result,
            "embedding_backend": embed_status.get("backend", "unknown"),
        }

        # Store in cache for subsequent identical queries
        query_cache.set(tenant_id, question, top_k, result)

        return result

    def _get_adaptive_search_weights(self) -> tuple:
        """Get adaptive search weights based on recent feedback statistics."""
        if not self.feedback_manager:
            return (
                0.6,
                0.4,
            )  # Tuned for small corpus (~12 docs): boost BM25 for keyword precision

        try:
            # Adjust weights based on recent feedback performance
            stats = self.feedback_manager.get_feedback_statistics(days=1)
            if stats.total_queries >= 5:  # Need at least 5 queries for meaningful stats
                if stats.success_rate < 0.5:
                    # Low success rate, increase vector search weight
                    return 0.8, 0.2
                elif stats.success_rate > 0.8:
                    # High success rate, increase BM25 keyword weight
                    return 0.6, 0.4
        except Exception as e:
            logger.warning(f"Failed to get adaptive search weights: {e}")

        return 0.7, 0.3  # Default weights

    def _build_prompt(
        self,
        question: str,
        context: str,
        memory_payload: Optional[dict] = None,
    ) -> str:
        """Build the RAG prompt with context, memory, and instructions."""
        memory_context = self._format_memory_payload(memory_payload or {})
        history_block = (
            f"\nPrior conversation:\n{memory_context}\n"
            if memory_context != "No prior conversation history."
            else ""
        )
        return f"""You are a construction industry assistant. Answer strictly from the provided references.

Rules:
1. Use only [Reference N] content. Cite which reference(s) you used.
2. Be precise with numbers, units, standards (e.g. CSA A23.1), and dates.
3. If the references lack the answer, say: "The available documents do not contain this information."
{history_block}
{context}

Question: {question}
Answer:"""

    @staticmethod
    def _format_memory_payload(memory_payload: dict) -> str:
        short_term = memory_payload.get("short_term") or []
        summary = (memory_payload.get("summary") or "").strip()
        long_term = memory_payload.get("long_term") or []

        if not short_term and not summary and not long_term:
            return "No prior conversation history."

        lines: list[str] = []
        if summary:
            lines.append(f"- Conversation summary: {summary}")

        if short_term:
            lines.append("- Recent dialogue:")
            for entry in short_term[-6:]:
                role = entry.get("role", "unknown")
                content = str(entry.get("content", "")).strip()
                if content:
                    lines.append(f"  - {role}: {content[:240]}")

        if long_term:
            lines.append("- Long-term memory:")
            for item in long_term[:3]:
                content = item.get("content")
                if isinstance(content, dict):
                    compact = ", ".join(
                        f"{k}={v}" for k, v in list(content.items())[:3]
                    )
                else:
                    compact = str(content)
                lines.append(f"  - {compact[:240]}")

        return "\n".join(lines)

    def _get_or_create_memory_session(
        self,
        session_id: Optional[str],
        user_id: Optional[str],
    ) -> _MemorySession:
        resolved_session_id = (session_id or "default").strip() or "default"
        with self._memory_lock:
            session = self._memory_sessions.get(resolved_session_id)
            if session is None:
                # Evict oldest sessions if at capacity
                if len(self._memory_sessions) >= self._max_sessions:
                    oldest_key = next(iter(self._memory_sessions))
                    del self._memory_sessions[oldest_key]
                session = _MemorySession(
                    session_id=resolved_session_id, user_id=user_id
                )
                self._memory_sessions[resolved_session_id] = session
            elif user_id and not session.user_id:
                session.user_id = user_id
        return session

    def _record_memory_interaction(
        self,
        session: _MemorySession,
        question: str,
        answer: str,
    ) -> None:
        record = _MemoryInteraction(
            user_query=question,
            agent_response=answer,
            processing_time_ms=0,
            success=bool(answer and answer.strip()),
        )
        with self._memory_lock:
            session.interaction_history.append(record)
            if len(session.interaction_history) > 50:
                session.interaction_history = session.interaction_history[-50:]

        if self.memory_manager is None:
            return

        # Snapshot session data so the background thread doesn't access
        # the live (and potentially mutating) session object.
        with self._memory_lock:
            history_snapshot = list(session.interaction_history)
            session_snapshot = _MemorySession(
                session_id=session.session_id,
                user_id=session.user_id,
                language_preference=session.language_preference,
                interaction_history=history_snapshot,
                summary_memory=session.summary_memory,
                last_summary_time=session.last_summary_time,
                last_summary_record_index=session.last_summary_record_index,
                long_term_memory_refs=list(session.long_term_memory_refs),
            )
        memory_manager = self.memory_manager
        live_session = session

        async def _update_memory():
            await memory_manager.process_interaction(session_snapshot, record)
            # Propagate summary updates back to live session
            with self._memory_lock:
                live_session.summary_memory = session_snapshot.summary_memory
                live_session.last_summary_record_index = (
                    session_snapshot.last_summary_record_index
                )
                live_session.last_summary_time = session_snapshot.last_summary_time
                live_session.long_term_memory_refs = list(
                    session_snapshot.long_term_memory_refs
                )

        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            # No running event loop — safe to call synchronously.
            asyncio.run(_update_memory())
            return

        # Schedule onto the existing event loop without spawning a thread.
        asyncio.ensure_future(_update_memory())

    def submit_feedback(
        self,
        query_id: str,
        question: str,
        answer: str,
        feedback_type: str,
        user_comment: str = None,
        retrieved_chunks: list = None,
        feedback_weight: float = 1.0,
    ) -> bool:
        """Submit user feedback for a query result."""
        if not self.feedback_manager:
            logger.warning("Feedback system is not enabled")
            return False

        try:
            feedback_enum = FeedbackType(feedback_type.lower())
            feedback = UserFeedback(
                query_id=query_id,
                question=question,
                answer=answer,
                feedback_type=feedback_enum,
                user_comment=user_comment,
                retrieved_chunks=retrieved_chunks or [],
                feedback_weight=feedback_weight,
            )
            return self.feedback_manager.record_feedback(feedback)
        except ValueError:
            logger.error(f"Invalid feedback type: {feedback_type}")
            return False
        except Exception as e:
            logger.error(f"Failed to submit feedback: {e}")
            return False

    def get_feedback_statistics(self, days: int = 7) -> dict:
        """Get aggregated feedback statistics for the specified time period."""
        if not self.feedback_manager:
            return {"message": "Feedback system is not enabled"}

        try:
            stats = self.feedback_manager.get_feedback_statistics(days)
            return {
                "total_queries": stats.total_queries,
                "helpful_count": stats.helpful_count,
                "not_helpful_count": stats.not_helpful_count,
                "partially_helpful_count": stats.partially_helpful_count,
                "success_rate": stats.success_rate,
                "avg_feedback_weight": stats.avg_feedback_weight,
            }
        except Exception as e:
            logger.error(f"Failed to get feedback statistics: {e}")
            return {"error": "Failed to retrieve feedback statistics"}

    def get_high_quality_documents(
        self, min_score: float = 0.5, limit: int = 100
    ) -> list:
        """Retrieve documents with high quality scores based on user feedback."""
        if not self.feedback_manager:
            return []

        try:
            return self.feedback_manager.get_high_quality_documents(min_score, limit)
        except Exception as e:
            logger.error(f"Failed to get high quality documents: {e}")
            return []

    def add_documents(self, documents: list) -> bool:
        """
        Add documents to the RAG knowledge base.

        Args:
            documents: List of document dicts, each containing 'content' and 'metadata' keys

        Returns:
            bool: Whether the documents were added successfully
        """
        try:
            from backend.services.core.chunker import chunk_text
            from backend.services.core.embedder import embed_texts

            # Chunk all documents
            all_chunks = []

            for doc in documents:
                content = doc.get("content", "")
                metadata = doc.get("metadata", {})
                doc_id = metadata.get("doc_id", str(uuid.uuid4()))

                # Use the standalone chunk_text function
                chunk_dicts = chunk_text(
                    content,
                    chunk_size=settings.chunk_size,
                    chunk_overlap=settings.chunk_overlap,
                )
                for i, chunk_dict in enumerate(chunk_dicts):
                    all_chunks.append(
                        {
                            "doc_id": doc_id,
                            "chunk_id": f"{doc_id}_chunk_{i}",
                            "content": chunk_dict["content"],
                            "metadata": metadata,
                        }
                    )

            # Generate embeddings for all chunks
            texts = [chunk["content"] for chunk in all_chunks]
            embeddings = embed_texts(texts)

            # Store documents using store_document_with_chunks
            # Group by doc_id for proper storage
            doc_groups = {}
            for chunk, embedding in zip(all_chunks, embeddings):
                doc_id = chunk["doc_id"]
                if doc_id not in doc_groups:
                    doc_groups[doc_id] = {
                        "chunks": [],
                        "embeddings": [],
                        "metadata": chunk["metadata"],
                    }
                doc_groups[doc_id]["chunks"].append(chunk["content"])
                doc_groups[doc_id]["embeddings"].append(embedding)

            # Store each document
            for doc_id, data in doc_groups.items():
                metadata = data["metadata"]
                filename = metadata.get("source", doc_id)
                filepath = metadata.get("source", doc_id)
                self.vectorstore.store_document_with_chunks(
                    filename=filename,
                    filepath=filepath,
                    chunks=data["chunks"],
                    embeddings=data["embeddings"],
                )

            if self.hybrid_retriever and hasattr(
                self.hybrid_retriever, "invalidate_bm25_index"
            ):
                self.hybrid_retriever.invalidate_bm25_index()

            logger.info(
                f"Successfully added {len(documents)} documents with {len(all_chunks)} chunks"
            )
            return True

        except Exception as e:
            logger.error(f"Failed to add documents: {e}")
            import traceback

            traceback.print_exc()
            return False

    def delete_document(self, doc_id: str) -> bool:
        """
        Delete a document and all its chunks from the knowledge base.

        Args:
            doc_id: The document ID to delete

        Returns:
            bool: Whether the document was deleted successfully
        """
        try:
            # Delete all chunks for the document
            self.vectorstore.delete_by_doc_id(doc_id)
            if self.hybrid_retriever and hasattr(
                self.hybrid_retriever, "invalidate_bm25_index"
            ):
                self.hybrid_retriever.invalidate_bm25_index()
            logger.info(f"Successfully deleted document: {doc_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete document {doc_id}: {e}")
            return False
