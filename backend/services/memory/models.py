"""Dataclasses for the conversation memory system."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, Optional


@dataclass
class LongTermMemoryEntry:
    """Represents a stored long-term memory record."""

    memory_id: str
    session_id: str
    user_id: Optional[str]
    memory_type: str
    content: Dict[str, Any]
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)
    relevance: float = 0.0
