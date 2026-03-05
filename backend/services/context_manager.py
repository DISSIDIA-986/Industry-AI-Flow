"""
Context Manager

Manages session context, interaction history, file uploads, and user preferences.
"""

import asyncio
import json
import logging
import re
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

from backend.config import settings
from backend.services.memory.manager import ConversationMemoryManager

logger = logging.getLogger(__name__)


@dataclass
class FileContext:
    """Represents an uploaded file's metadata and context."""

    file_id: str
    file_name: str
    file_type: str
    file_size: int
    upload_time: datetime
    file_path: str
    preview: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        data = asdict(self)
        data["upload_time"] = self.upload_time.isoformat()
        return data


@dataclass
class InteractionRecord:
    """Records a single user-agent interaction."""

    record_id: str
    timestamp: datetime
    user_query: str
    classified_intent: str
    agent_response: str
    confidence: float
    processing_time_ms: int
    user_feedback: Optional[int] = None
    success: bool = True

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        data = asdict(self)
        data["timestamp"] = self.timestamp.isoformat()
        return data


@dataclass
class SessionContext:
    """Holds all context for a user session including history and preferences."""

    session_id: str
    user_id: Optional[str] = None
    start_time: datetime = field(default_factory=datetime.now)
    last_activity: datetime = field(default_factory=datetime.now)
    query_count: int = 0
    session_topic: str = ""
    session_stage: str = "initial"  # initial, exploring, deep_dive, closing
    language_preference: str = "auto"
    uploaded_files: List[FileContext] = field(default_factory=list)
    interaction_history: List[InteractionRecord] = field(default_factory=list)
    detected_intents: List[str] = field(default_factory=list)
    user_preferences: Dict[str, Any] = field(default_factory=dict)
    context_keywords: List[str] = field(default_factory=list)
    completion_rate: float = 0.0
    satisfaction_score: Optional[float] = None
    summary_memory: str = ""
    last_summary_time: Optional[datetime] = None
    last_summary_record_index: int = 0
    long_term_memory_refs: List[str] = field(default_factory=list)

    def add_interaction(self, record: InteractionRecord):
        """Add an interaction record to the session history."""
        self.interaction_history.append(record)
        self.last_activity = record.timestamp
        self.query_count += 1

        # Track detected intents
        if record.classified_intent not in self.detected_intents:
            self.detected_intents.append(record.classified_intent)
            # Keep at most 10 recent intents
            if len(self.detected_intents) > 10:
                self.detected_intents = self.detected_intents[-10:]

        # Update completion rate
        successful_interactions = sum(1 for r in self.interaction_history if r.success)
        self.completion_rate = successful_interactions / max(
            len(self.interaction_history), 1
        )

    def add_uploaded_file(self, file_context: FileContext):
        """Add an uploaded file to the session context."""
        self.uploaded_files.append(file_context)
        # Keep at most 10 recent files
        if len(self.uploaded_files) > 10:
            self.uploaded_files = self.uploaded_files[-10:]

    def get_recent_intents(self, limit: int = 5) -> List[str]:
        """Get the most recent detected intents."""
        return self.detected_intents[-limit:] if self.detected_intents else []

    def get_session_duration(self) -> float:
        """Get session duration in seconds."""
        return (self.last_activity - self.start_time).total_seconds()

    def update_session_stage(self):
        """Update the session stage based on duration and query count."""
        duration = self.get_session_duration()
        query_count = self.query_count

        if duration < 60:  # Less than 1 minute
            self.session_stage = "initial"
        elif query_count < 3:
            self.session_stage = "exploring"
        elif query_count < 10:
            self.session_stage = "deep_dive"
        else:
            self.session_stage = "closing"

    def get_context_summary(self) -> Dict[str, Any]:
        """Get a summary of the current session context."""
        return {
            "session_id": self.session_id,
            "duration_minutes": round(self.get_session_duration() / 60, 1),
            "query_count": self.query_count,
            "stage": self.session_stage,
            "topic": self.session_topic,
            "language": self.language_preference,
            "uploaded_files_count": len(self.uploaded_files),
            "completion_rate": self.completion_rate,
            "detected_intents": self.get_recent_intents(),
        }


class ContextManager:
    """Manages session contexts, interaction tracking, and file uploads."""

    def __init__(self, storage_backend: str = "memory", cache_ttl: int = 3600):
        """
        Initialize the context manager.

        Args:
            storage_backend: Storage backend type ("memory", "database", "redis").
            cache_ttl: Cache time-to-live in seconds.
        """
        self.storage_backend = storage_backend
        self.cache_ttl = cache_ttl

        # Session and file caches
        self._session_cache: Dict[str, SessionContext] = {}
        self._file_cache: Dict[str, FileContext] = {}

        # Statistics tracking
        self.stats = {
            "active_sessions": 0,
            "total_interactions": 0,
            "avg_session_duration": 0.0,
            "cache_hits": 0,
        }

        self.memory_manager = (
            ConversationMemoryManager() if settings.enable_conversation_memory else None
        )

        logger.info(f"Context manager initialized, backend: {storage_backend}")

    async def get_session_context(
        self, session_id: str, user_id: Optional[str] = None
    ) -> SessionContext:
        """
        Get or create a session context.

        Args:
            session_id: Session ID.
            user_id: Optional user ID.

        Returns:
            SessionContext: The session context object.
        """
        # Check cache first
        if session_id in self._session_cache:
            session = self._session_cache[session_id]
            # Check if session is still valid (24 hours)
            if (datetime.now() - session.last_activity).total_seconds() < 86400:
                self.stats["cache_hits"] += 1
                logger.debug(f"Session cache hit: {session_id}")
                return session
            else:
                # Session expired, remove from cache
                del self._session_cache[session_id]

        # Load from storage
        session = await self._load_session_from_storage(session_id, user_id)

        # Cache the session
        self._session_cache[session_id] = session
        self._update_active_sessions_count()

        logger.info(f"Session loaded/created: {session_id}")
        return session

    async def update_session_context(
        self, session_id: str, updates: Dict[str, Any]
    ) -> SessionContext:
        """
        Update session context with new data.

        Args:
            session_id: Session ID.
            updates: Dictionary of field names and new values.

        Returns:
            SessionContext: The updated session context.
        """
        session = await self.get_session_context(session_id)

        # Apply updates to session fields
        for field, value in updates.items():
            if hasattr(session, field):
                setattr(session, field, value)

        session.last_activity = datetime.now()
        session.update_session_stage()

        # Persist to storage
        await self._save_session_to_storage(session)

        # Update cache
        self._session_cache[session_id] = session

        return session

    async def get_memory_snapshot(
        self, session_id: str, user_query: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get a memory snapshot for the current session, including all memory layers.
        """
        if not self.memory_manager:
            return {}
        session = await self.get_session_context(session_id)
        return self.memory_manager.build_memory_payload(session, user_query)

    async def add_interaction_record(
        self,
        session_id: str,
        user_query: str,
        classified_intent: str,
        agent_response: str,
        confidence: float,
        processing_time_ms: int,
        user_feedback: Optional[int] = None,
        success: bool = True,
    ) -> None:
        """
        Record a user-agent interaction in the session.

        Args:
            session_id: Session ID.
            user_query: The user's query text.
            classified_intent: The classified intent type.
            agent_response: The agent's response text.
            confidence: Intent classification confidence score.
            processing_time_ms: Processing time in milliseconds.
            user_feedback: Optional user satisfaction score.
            success: Whether the interaction was successful.
        """
        session = await self.get_session_context(session_id)

        record = InteractionRecord(
            record_id=str(uuid.uuid4()),
            timestamp=datetime.now(),
            user_query=user_query,
            classified_intent=classified_intent,
            agent_response=agent_response,
            confidence=confidence,
            processing_time_ms=processing_time_ms,
            user_feedback=user_feedback,
            success=success,
        )

        session.add_interaction(record)
        session.detected_intents.append(classified_intent)

        # Update satisfaction score (exponential moving average)
        if user_feedback is not None:
            if session.satisfaction_score is None:
                session.satisfaction_score = user_feedback
            else:
                # Weighted average: 80% historical, 20% new feedback
                session.satisfaction_score = (
                    session.satisfaction_score * 0.8 + user_feedback * 0.2
                )

        if self.memory_manager:
            await self.memory_manager.process_interaction(session, record)

        await self._save_session_to_storage(session)
        self._session_cache[session_id] = session

        self.stats["total_interactions"] += 1

    async def add_uploaded_file(
        self,
        session_id: str,
        file_id: str,
        file_name: str,
        file_type: str,
        file_size: int,
        file_path: str,
        preview: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Record an uploaded file in the session context.

        Args:
            session_id: Session ID.
            file_id: Unique file identifier.
            file_name: Original file name.
            file_type: File MIME type or extension.
            file_size: File size in bytes.
            file_path: Path to the stored file.
            preview: Optional text preview of file content.
            metadata: Optional additional file metadata.
        """
        file_context = FileContext(
            file_id=file_id,
            file_name=file_name,
            file_type=file_type,
            file_size=file_size,
            upload_time=datetime.now(),
            file_path=file_path,
            preview=preview,
            metadata=metadata or {},
        )

        session = await self.get_session_context(session_id)
        session.add_uploaded_file(file_context)

        # Set session topic on first file upload
        if len(session.uploaded_files) == 1:
            session.session_topic = f"File analysis: {file_name}"

        await self._save_session_to_storage(session)
        self._session_cache[session_id] = session

    async def get_enhanced_context(
        self,
        session_id: str,
        max_history: int = 10,
        include_files: bool = True,
        current_query: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Get enhanced context including session info, history, files, and keywords.

        Args:
            session_id: Session ID.
            max_history: Maximum number of history records to include.
            include_files: Whether to include file context.
            current_query: Current query for memory relevance scoring.

        Returns:
            Dict[str, Any]: Enhanced context dictionary.
        """
        session = await self.get_session_context(session_id)

        # Build base context
        context = {
            "session_info": session.get_context_summary(),
            "recent_intents": session.get_recent_intents(),
            "interaction_count": session.query_count,
            "session_stage": session.session_stage,
        }

        # Add recent interaction history
        if session.interaction_history:
            recent_history = session.interaction_history[-max_history:]
            context["interaction_history"] = [
                record.to_dict() for record in recent_history
            ]

        # Add file context
        if include_files and session.uploaded_files:
            context["file_context"] = {
                "total_files": len(session.uploaded_files),
                "recent_files": [
                    file.to_dict() for file in session.uploaded_files[-3:]
                ],
                "file_types": list(
                    set(file.file_type for file in session.uploaded_files)
                ),
            }

        # Add user preferences
        if session.user_preferences:
            context["user_preferences"] = session.user_preferences

        # Extract context keywords
        context_keywords = []

        # Keywords from recent interactions
        for record in session.interaction_history[-5:]:
            context_keywords.extend(self._extract_keywords(record.user_query))
            context_keywords.extend(self._extract_keywords(record.agent_response))

        # Keywords from uploaded file names
        for file in session.uploaded_files[-3:]:
            context_keywords.append(file.file_name)

        # Deduplicate and filter stop words
        context["context_keywords"] = list(
            set(
                word
                for word in context_keywords
                if len(word) > 1
                and word.lower()
                not in [
                    "the",
                    "a",
                    "an",
                    "and",
                    "or",
                    "but",
                    "in",
                    "on",
                    "at",
                    "to",
                    "for",
                    "of",
                    "with",
                    "by",
                    "this",
                    "that",
                    "is",
                    "are",
                    "be",
                    "have",
                    "has",
                    "what",
                    "when",
                    "where",
                    "why",
                    "how",
                    "all",
                    "any",
                    "can",
                    "could",
                    "would",
                    "should",
                    "will",
                ]
            )
        )[
            :20
        ]  # Limit to 20 keywords

        if self.memory_manager:
            context["memory_layers"] = self.memory_manager.build_memory_payload(
                session, current_query
            )

        return context

    async def analyze_session_patterns(self, session_id: str) -> Dict[str, Any]:
        """
        Analyze behavioral patterns within a session.

        Args:
            session_id: Session ID to analyze.

        Returns:
            Dict[str, Any]: Analysis results including query, intent, and time patterns.
        """
        session = await self.get_session_context(session_id)

        if not session.interaction_history:
            return {"status": "no_data"}

        patterns = {
            "query_patterns": self._analyze_query_patterns(session),
            "intent_evolution": self._analyze_intent_evolution(session),
            "time_distribution": self._analyze_time_distribution(session),
            "success_patterns": self._analyze_success_patterns(session),
            "interaction_rhythm": self._analyze_interaction_rhythm(session),
        }

        return patterns

    def _extract_keywords(self, text: str) -> List[str]:
        """Extract keywords from text using simple regex tokenization."""
        if not text:
            return []

        # Extract words (English and CJK characters, 2+ chars)
        words = re.findall(r"\b[a-zA-Z\u4e00-\u9fff]{2,}\b", text.lower())
        return words

    def _analyze_query_patterns(self, session: SessionContext) -> Dict[str, Any]:
        """Analyze query length and type patterns in the session."""
        if not session.interaction_history:
            return {}

        queries = [record.user_query for record in session.interaction_history]

        # Calculate query length statistics
        lengths = [len(query) for query in queries]

        # Count question vs statement queries
        question_count = sum(1 for query in queries if "?" in query or "?" in query)
        statement_count = sum(
            1 for query in queries if query.endswith(".") or query.endswith(".")
        )

        return {
            "avg_query_length": sum(lengths) / max(len(lengths), 1),
            "max_query_length": max(lengths) if lengths else 0,
            "min_query_length": min(lengths) if lengths else 0,
            "question_ratio": question_count / max(len(queries), 1),
            "statement_ratio": statement_count / max(len(queries), 1),
        }

    def _analyze_intent_evolution(self, session: SessionContext) -> Dict[str, Any]:
        """Analyze how user intents evolve throughout the session."""
        if len(session.detected_intents) < 2:
            return {"status": "insufficient_data"}

        # Count intent transitions
        intent_changes = 0
        for i in range(1, len(session.detected_intents)):
            if session.detected_intents[i] != session.detected_intents[i - 1]:
                intent_changes += 1

        return {
            "total_intents": len(session.detected_intents),
            "unique_intents": len(set(session.detected_intents)),
            "intent_changes": intent_changes,
            "intent_diversity": intent_changes
            / max(len(session.detected_intents) - 1, 1),
            "current_intent": session.detected_intents[-1]
            if session.detected_intents
            else None,
        }

    def _analyze_time_distribution(self, session: SessionContext) -> Dict[str, Any]:
        """Analyze time intervals between interactions."""
        if len(session.interaction_history) < 2:
            return {"status": "insufficient_data"}

        timestamps = [record.timestamp for record in session.interaction_history]

        # Calculate time intervals between interactions
        intervals = []
        for i in range(1, len(timestamps)):
            interval = (timestamps[i] - timestamps[i - 1]).total_seconds()
            intervals.append(interval)

        return {
            "total_session_duration": session.get_session_duration(),
            "avg_interaction_interval": sum(intervals) / max(len(intervals), 1),
            "min_interval": min(intervals) if intervals else 0,
            "max_interval": max(intervals) if intervals else 0,
        }

    def _analyze_success_patterns(self, session: SessionContext) -> Dict[str, Any]:
        """Analyze success and confidence patterns in the session."""
        if not session.interaction_history:
            return {"status": "no_data"}

        successful = sum(1 for record in session.interaction_history if record.success)
        total = len(session.interaction_history)

        # Collect confidence scores
        confidences = [record.confidence for record in session.interaction_history]

        return {
            "success_rate": session.completion_rate,
            "total_interactions": total,
            "successful_interactions": successful,
            "avg_confidence": sum(confidences) / max(len(confidences), 1),
            "high_confidence_rate": sum(1 for c in confidences if c >= 0.8)
            / max(len(confidences), 1),
        }

    def _analyze_interaction_rhythm(self, session: SessionContext) -> Dict[str, Any]:
        """Analyze the rhythm and frequency of user interactions."""
        if len(session.interaction_history) < 2:
            return {"status": "insufficient_data"}

        timestamps = [record.timestamp for record in session.interaction_history]
        processing_times = [
            record.processing_time_ms for record in session.interaction_history
        ]

        # Calculate interaction intervals
        intervals = []
        for i in range(1, len(timestamps)):
            interval = (timestamps[i] - timestamps[i - 1]).total_seconds()
            intervals.append(interval)

        return {
            "avg_interaction_interval": sum(intervals) / max(len(intervals), 1),
            "interaction_frequency": len(session.interaction_history)
            / max(session.get_session_duration() / 60, 1),  # Interactions per minute
            "avg_processing_time": sum(processing_times)
            / max(len(processing_times), 1),
            "processing_time_trend": "stable",  # Simplified; detailed trend analysis not yet implemented
        }

    async def _load_session_from_storage(
        self, session_id: str, user_id: Optional[str] = None
    ) -> SessionContext:
        """Load session from storage backend or create a new one."""
        # In-memory stub: create a new session with defaults
        return SessionContext(
            session_id=session_id,
            user_id=user_id,
            start_time=datetime.now() - timedelta(minutes=5),
            last_activity=datetime.now() - timedelta(minutes=1),
            query_count=2,
            session_topic="General inquiry",
            detected_intents=["knowledge_retrieval"],
            user_preferences={"language": "zh-CN", "response_style": "professional"},
            context_keywords=["construction", "safety", "regulation"],
        )

    async def _save_session_to_storage(self, session: SessionContext) -> None:
        """Save session to storage backend."""
        # TODO: implement persistent storage
        # await database.save_session(session.to_dict())
        pass

    def _update_active_sessions_count(self):
        """Update the count of active sessions."""
        current_time = datetime.now()
        active_count = 0

        for session in self._session_cache.values():
            if (current_time - session.last_activity).total_seconds() < 3600:  # 1 hour
                active_count += 1

        self.stats["active_sessions"] = active_count

    def get_stats(self) -> Dict[str, Any]:
        """Get context manager statistics."""
        return {
            **self.stats,
            "cache_size": len(self._session_cache),
            "file_cache_size": len(self._file_cache),
            "storage_backend": self.storage_backend,
        }

    def clear_cache(self):
        """Clear all session and file caches."""
        self._session_cache.clear()
        self._file_cache.clear()
        self.stats["cache_hits"] = 0
        logger.info("Context manager cache cleared")

    async def cleanup_expired_sessions(self, max_age_hours: int = 24) -> int:
        """Clean up expired sessions from the cache."""
        current_time = datetime.now()
        expired_sessions = []

        for session_id, session in list(self._session_cache.items()):
            age_hours = (current_time - session.last_activity).total_seconds() / 3600
            if age_hours > max_age_hours:
                expired_sessions.append(session_id)
                del self._session_cache[session_id]

        logger.info(f"Cleaned up {len(expired_sessions)} expired sessions")
        return len(expired_sessions)

    async def health_check(self) -> Dict[str, Any]:
        """Perform a health check on the context manager."""
        return {
            "status": "healthy",
            "storage_backend": self.storage_backend,
            "active_sessions": self.stats["active_sessions"],
            "cache_size": len(self._session_cache),
            "total_interactions": self.stats["total_interactions"],
        }
