"""
Capability Registry — Single source of truth for system capabilities.

Inspired by MCP's tools/list pattern: capabilities are registered as structured
objects, and consumers (intent classifier, routing engine, API endpoints) derive
their behavior from the registry rather than hardcoded logic.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

import yaml

logger = logging.getLogger(__name__)

_CONFIG_PATH = Path(__file__).resolve().parents[2] / "config" / "capabilities.yaml"


@dataclass(frozen=True)
class Capability:
    """A single system capability (maps 1:1 to an intent type)."""

    id: str  # e.g. "knowledge_retrieval" — matches IntentType.value
    name: str  # e.g. "Knowledge Retrieval"
    description: str  # Rich description for LLM prompt context
    agent_type: str  # e.g. "rag_agent" — matches AgentType value
    keywords: tuple[str, ...] = ()  # Heuristic matching keywords
    patterns: tuple[str, ...] = ()  # Regex patterns for heuristic
    example_queries: tuple[str, ...] = ()  # For API catalog + frontend
    parameters: dict[str, Any] = field(default_factory=dict)
    fallback_ids: tuple[str, ...] = ()  # Ordered fallback capability IDs
    priority: int = 0  # Keyword check order (higher = checked first)
    confidence: float = 0.85  # Default heuristic confidence
    enabled: bool = True


class CapabilityRegistry:
    """In-memory registry of system capabilities."""

    def __init__(self) -> None:
        self._capabilities: dict[str, Capability] = {}
        self._compiled_patterns: dict[str, list[re.Pattern]] = {}

    # ── Registration ──────────────────────────────────────────────

    def register(self, capability: Capability) -> None:
        self._capabilities[capability.id] = capability
        if capability.patterns:
            self._compiled_patterns[capability.id] = [
                re.compile(p) for p in capability.patterns
            ]
        else:
            self._compiled_patterns[capability.id] = []

    def get(self, capability_id: str) -> Optional[Capability]:
        return self._capabilities.get(capability_id)

    def list_all(self, *, enabled_only: bool = True) -> list[Capability]:
        caps = list(self._capabilities.values())
        if enabled_only:
            caps = [c for c in caps if c.enabled]
        return sorted(caps, key=lambda c: (-c.priority, c.id))

    # ── For IntentClassifier LLM prompt ───────────────────────────

    def build_intent_prompt_section(self) -> str:
        """Build the intent list section for the LLM classification prompt."""
        lines = []
        for cap in self.list_all():
            lines.append(f"- {cap.id}: {cap.description}")
        lines.append("- unclear_intent: Intent could not be determined.")
        return "\n".join(lines)

    # ── For heuristic classifiers ─────────────────────────────────

    def classify_heuristic(self, query: str) -> tuple[str, float, str]:
        """Classify query using keyword/pattern heuristics.

        Returns (intent_id, confidence, reasoning).
        Uses a scoring approach: all capabilities are scored, best match wins.
        Word-boundary matching prevents false positives like "code" in "building_code".
        """
        text = (query or "").strip().lower()
        if not text:
            return "knowledge_retrieval", 0.51, "Empty query, defaulting to knowledge retrieval"

        best_id = ""
        best_score = 0.0
        best_conf = 0.51
        best_reason = "No keywords matched, defaulting to knowledge retrieval"

        for cap in self.list_all():
            score = 0.0
            matched: list[str] = []

            # Check regex patterns (high weight)
            patterns = self._compiled_patterns.get(cap.id, [])
            for p in patterns:
                if p.search(text):
                    score += 15.0
                    matched.append(f"pattern:{p.pattern}")

            # Check keywords with word-boundary matching
            if cap.keywords:
                for kw in cap.keywords:
                    # Use word boundaries to prevent substring false positives
                    if re.search(r"(?<![a-z])" + re.escape(kw) + r"(?![a-z])", text):
                        weight = 2.0 if " " in kw else 1.0  # multi-word = stronger
                        score += weight
                        matched.append(kw)

            # Apply priority as a tiebreaker (small bonus)
            score += cap.priority * 0.01

            if score > best_score:
                best_score = score
                best_id = cap.id
                best_conf = cap.confidence
                best_reason = f"Query matches {cap.name} [{', '.join(matched[:3])}]"

        if best_id:
            return best_id, best_conf, best_reason

        # Default fallback
        return "knowledge_retrieval", 0.51, best_reason

    # ── For routing engine ────────────────────────────────────────

    def get_agent_mapping(self) -> dict[str, str]:
        """Return intent_id -> agent_type mapping."""
        return {cap.id: cap.agent_type for cap in self.list_all()}

    def get_fallback_mapping(self) -> dict[str, list[str]]:
        """Return capability_id -> list of fallback capability IDs."""
        return {cap.id: list(cap.fallback_ids) for cap in self.list_all()}

    # ── For API / frontend (MCP-like tools/list) ──────────────────

    def to_catalog(self) -> list[dict[str, Any]]:
        """Serialize capabilities for API response (excludes internal fields)."""
        result = []
        for cap in self.list_all():
            result.append(
                {
                    "id": cap.id,
                    "name": cap.name,
                    "description": cap.description,
                    "example_queries": list(cap.example_queries),
                    "parameters": dict(cap.parameters),
                    "enabled": cap.enabled,
                }
            )
        return result


# ── YAML loading ──────────────────────────────────────────────────


def _load_from_yaml(registry: CapabilityRegistry, path: Path) -> None:
    """Load capability definitions from a YAML config file."""
    with open(path, encoding="utf-8") as f:
        data = yaml.safe_load(f)

    for item in data.get("capabilities", []):
        cap = Capability(
            id=item["id"],
            name=item["name"],
            description=item.get("description", ""),
            agent_type=item.get("agent_type", "general_agent"),
            keywords=tuple(item.get("keywords", [])),
            patterns=tuple(item.get("patterns", [])),
            example_queries=tuple(item.get("example_queries", [])),
            parameters=dict(item.get("parameters", {})),
            fallback_ids=tuple(item.get("fallback_ids", [])),
            priority=int(item.get("priority", 0)),
            confidence=float(item.get("confidence", 0.85)),
            enabled=bool(item.get("enabled", True)),
        )
        registry.register(cap)


# ── Singleton ─────────────────────────────────────────────────────

_default_registry: Optional[CapabilityRegistry] = None


def get_capability_registry() -> CapabilityRegistry:
    """Return the singleton capability registry, loading from YAML on first call."""
    global _default_registry
    if _default_registry is None:
        _default_registry = CapabilityRegistry()
        if _CONFIG_PATH.exists():
            try:
                _load_from_yaml(_default_registry, _CONFIG_PATH)
                logger.info(
                    "Capability registry loaded from %s (%d capabilities)",
                    _CONFIG_PATH,
                    len(_default_registry.list_all()),
                )
            except Exception as e:
                logger.error("Failed to load capabilities YAML: %s", e)
                _register_hardcoded_defaults(_default_registry)
        else:
            logger.warning("capabilities.yaml not found, using hardcoded defaults")
            _register_hardcoded_defaults(_default_registry)
    return _default_registry


def _register_hardcoded_defaults(registry: CapabilityRegistry) -> None:
    """Fallback: register the 5 default capabilities without YAML."""
    defaults = [
        Capability(
            id="cost_estimation",
            name="Cost Estimation",
            description="Predict construction project cost overruns using ML model.",
            agent_type="cost_estimation_agent",
            keywords=("cost estimate", "budget", "overrun", "construction cost", "how much"),
            priority=10,
            confidence=0.91,
        ),
        Capability(
            id="knowledge_retrieval",
            name="Knowledge Retrieval",
            description="Search the construction knowledge base using RAG retrieval.",
            agent_type="rag_agent",
            keywords=("what is", "how to", "explain", "regulation", "safety", "osha"),
            priority=0,
            confidence=0.85,
        ),
        Capability(
            id="data_analysis",
            name="Data Analysis",
            description="Analyze datasets, generate statistics and visualizations.",
            agent_type="data_analysis_agent",
            keywords=("analyze", "analysis", "dataset", "chart", "statistics"),
            priority=1,
            confidence=0.90,
        ),
        Capability(
            id="document_processing",
            name="Document Processing",
            description="Extract text from PDFs or images using OCR.",
            agent_type="document_processing_agent",
            keywords=("ocr", "scan document", "upload document", "extract text from"),
            priority=1,
            confidence=0.88,
        ),
        Capability(
            id="code_execution",
            name="Code Execution",
            description="Execute Python code in a sandboxed environment.",
            agent_type="code_execution_agent",
            keywords=("execute code", "run code", "python", "script", "compute"),
            priority=1,
            confidence=0.87,
        ),
    ]
    for cap in defaults:
        registry.register(cap)
