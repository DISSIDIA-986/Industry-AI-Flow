"""
Simple Intent Classifier - Keyword-based intent classification.
Lightweight classifier that uses keyword matching and regex patterns without LLM calls.
"""

import json
import logging
import re
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class IntentType(Enum):
    """Supported intent types for classification."""

    KNOWLEDGE_RETRIEVAL = "knowledge_retrieval"  # Knowledge/document retrieval queries
    DATA_ANALYSIS = "data_analysis"  # Data analysis and statistics queries
    COST_ESTIMATION = "cost_estimation"  # Construction cost estimation queries
    DOCUMENT_PROCESSING = "document_processing"  # Document processing and OCR queries
    CODE_EXECUTION = "code_execution"  # Code execution queries
    UNCLEAR_INTENT = "unclear_intent"  # Intent could not be determined


@dataclass
class SimpleIntentResult:
    """Result of a simple intent classification."""

    intent: IntentType
    confidence: float = 0.0
    reasoning: str = ""
    keywords: List[str] = None
    suggested_action: str = ""

    def __post_init__(self):
        if self.keywords is None:
            self.keywords = []

    @property
    def is_high_confidence(self) -> bool:
        """Check if classification confidence is above the high threshold."""
        return self.confidence >= 0.7

    @property
    def is_uncertain(self) -> bool:
        """Check if classification confidence is below the uncertainty threshold."""
        return self.confidence < 0.5


class SimpleIntentClassifier:
    """
    Simple Intent Classifier - Keyword and pattern-based intent classification.

    A lightweight classifier that does not require LLM calls, using instead:
    1. Keyword matching with weighted scoring
    2. Regex pattern matching
    3. Context-based score adjustment
    """

    def __init__(self, confidence_threshold: float = 0.7):
        """
        Initialize the simple intent classifier.

        Args:
            confidence_threshold: Minimum confidence threshold for high-confidence classification
        """
        self.confidence_threshold = confidence_threshold

        # Build keyword matching rules
        self._keyword_rules = self._build_keyword_rules()

        # Classification statistics
        self.stats = {
            "total_classifications": 0,
            "high_confidence_count": 0,
            "intent_distribution": {},
        }

        logger.info("Simple intent classifier initialized")

    def _build_keyword_rules(self) -> Dict[IntentType, Dict[str, Any]]:
        """Build keyword and pattern rules for each intent type."""
        return {
            IntentType.KNOWLEDGE_RETRIEVAL: {
                "keywords": [
                    # Knowledge retrieval keywords
                    "what is",
                    "how does",
                    "explain",
                    "define",
                    "tell me",
                    "describe",
                    "show me",
                    "information about",
                    "details of",
                    "concept",
                    "principle",
                    "mechanism",
                    "theory",
                ],
                "patterns": [
                    r"what\s+(is|are|does)",
                    r"how\s+(does|do|to)",
                    r"(explain|describe|tell)\s+me",
                ],
                "priority": 1,
            },
            IntentType.DATA_ANALYSIS: {
                "keywords": [
                    # Analysis action keywords
                    "analyze",
                    "analysis",
                    "statistics",
                    "stat",
                    "calculate",
                    "compute",
                    "summarize",
                    "aggregate",
                    "trend",
                    "pattern",
                    # Data-related keywords
                    "data",
                    "dataset",
                    "csv",
                    "excel",
                    "table",
                    "column",
                    "row",
                    "record",
                    "field",
                    "value",
                    "distribution",
                    # Statistical operation keywords
                    "average",
                    "mean",
                    "median",
                    "max",
                    "min",
                    "sum",
                    "count",
                    "highest",
                    "lowest",
                    "most",
                    "least",
                    "percentage",
                    "ratio",
                    "correlation",
                    "variance",
                    "standard deviation",
                    # Comparison keywords
                    "compare",
                    "comparison",
                    "versus",
                    "vs",
                    "difference",
                    "between",
                    "among",
                    "relation",
                    "relationship",
                    # Visualization keywords
                    "chart",
                    "graph",
                    "plot",
                    "visualization",
                    "visualize",
                    "histogram",
                    "scatter",
                    "bar chart",
                    "line plot",
                ],
                "patterns": [
                    r"(analyze|analysis|calculate)\s+",
                    r"(average|mean|median|max|min|sum|count)\s+",
                    r"(highest|lowest|most|least)\s+",
                    r"(compare|comparison|versus|vs)\s+",
                    r"what\s+(is|are)\s+the\s+(average|max|min|total)",
                    r"how\s+many",
                    r"(percentage|ratio)\s+of",
                ],
                "priority": 1,  # Equal priority — disambiguation via specific keywords
            },
            IntentType.COST_ESTIMATION: {
                "keywords": [
                    "cost estimate",
                    "cost estimation",
                    "construction cost",
                    "budget estimate",
                    "cost overrun",
                    "overrun",
                    "estimate cost",
                ],
                "patterns": [
                    r"(cost|budget)\s+(estimate|estimation|forecast)",
                    r"(cost|budget)\s+overrun",
                    r"(estimate|predict).*(cost|budget)",
                ],
                "priority": 3,
            },
            IntentType.DOCUMENT_PROCESSING: {
                "keywords": [
                    # Document and file type keywords
                    "pdf",
                    "document",
                    "file",
                    "image",
                    "picture",
                    "photo",
                    "scan",
                    "ocr",
                    "extract",
                    "extract text",
                    "read document",
                    "parse",
                    "convert",
                    "jpg",
                    "png",
                    "tiff",
                    "jpeg",
                ],
                "patterns": [
                    r"(extract|read|parse)\s+(text|content)\s+from",
                    r"ocr\s+",
                    r"(pdf|document|image|file)\s+",
                ],
                "priority": 1,
            },
            IntentType.CODE_EXECUTION: {
                "keywords": [
                    # Strong multi-word code-execution signals only.
                    # Single-word keywords like "run", "process", "batch"
                    # are too broad and match construction terminology.
                    "run code",
                    "execute code",
                    "run script",
                    "execute script",
                    "run program",
                    "execute program",
                    "run python",
                    "python script",
                    "python code",
                    "code execution",
                    "execute",
                    "script",
                    "algorithm",
                    "automation",
                ],
                "patterns": [
                    r"(run|execute)\s+(code|script|program)",
                    r"(run|execute)\s+.*python",
                    r"python\s+script",
                    r"implement\s+.*\b(code|algorithm|function)\b",
                ],
                "priority": 1,
            },
        }

    def classify_intent(
        self, query: str, context: Optional[Any] = None
    ) -> SimpleIntentResult:
        """
        Classify the intent of a user query using keyword and pattern matching.

        Args:
            query: User query string
            context: Optional context for score adjustment (e.g. uploaded files)

        Returns:
            SimpleIntentResult: Classification result with intent, confidence, and reasoning
        """
        try:
            # Preprocess the query
            processed_query = self._preprocess_query(query)

            # Calculate scores for each intent type
            intent_scores = {}

            for intent_type, rules in self._keyword_rules.items():
                score, matched_keywords = self._calculate_intent_score(
                    processed_query, rules
                )

                if score > 0:
                    intent_scores[intent_type] = {
                        "score": score,
                        "keywords": matched_keywords,
                    }

            # Adjust scores based on context (e.g. uploaded files)
            if context:
                normalized_context = self._normalize_context(context)
                intent_scores = self._adjust_scores_with_context(
                    intent_scores, normalized_context
                )

            # Determine the best matching intent
            if not intent_scores:
                # No keywords matched any intent
                result = SimpleIntentResult(
                    intent=IntentType.UNCLEAR_INTENT,
                    confidence=0.3,
                    reasoning="No matching keywords found for any known intent",
                    suggested_action="Please rephrase your question with more specific terms",
                )
            else:
                # Select the intent with the highest score
                best_intent = max(intent_scores.items(), key=lambda x: x[1]["score"])
                intent_type, intent_data = best_intent

                # Calibrate confidence so that even a single keyword match
                # yields a meaningful score (≥0.5).  Previously dividing by
                # 100 caused most queries to land at 0.1 confidence.
                max_possible_score = 30.0
                raw_confidence = min(intent_data["score"] / max_possible_score, 1.0)
                confidence = (
                    max(raw_confidence, 0.5) if intent_data["score"] > 0 else 0.0
                )

                # Build reasoning string
                reasoning = f"Matched {len(intent_data['keywords'])} keywords: {', '.join(intent_data['keywords'][:3])}"

                result = SimpleIntentResult(
                    intent=intent_type,
                    confidence=confidence,
                    reasoning=reasoning,
                    keywords=intent_data["keywords"],
                    suggested_action=self._get_suggested_action(intent_type),
                )

            # Update classification statistics
            self._update_stats(result)

            logger.info(
                f"Intent classified: {result.intent.value} (confidence: {result.confidence:.2f})"
            )
            return result

        except Exception as e:
            logger.error(f"Intent classification failed: {e}")
            return SimpleIntentResult(
                intent=IntentType.UNCLEAR_INTENT,
                confidence=0.0,
                reasoning=f"Classification error: {str(e)}",
                suggested_action="Please rephrase your question",
            )

    def _preprocess_query(self, query: str) -> str:
        """Preprocess query: lowercase and normalize whitespace."""
        # Convert to lowercase
        processed = query.lower()

        # Normalize whitespace
        processed = re.sub(r"\s+", " ", processed).strip()

        return processed

    def _calculate_intent_score(self, query: str, rules: Dict[str, Any]) -> tuple:
        """
        Calculate the intent score for a query against a set of rules.

        Args:
            query: Preprocessed query string
            rules: Keyword and pattern rules for an intent type

        Returns:
            tuple: (total score, list of matched keywords)
        """
        score = 0.0
        matched_keywords = []

        # Score keyword matches
        keywords = rules.get("keywords", [])
        for keyword in keywords:
            if keyword.lower() in query:
                # Base score for a keyword match
                base_score = 10.0

                # Boost: keyword appears at the start of the query
                if query.startswith(keyword.lower()):
                    base_score *= 1.5

                # Boost: multi-word keyword (more specific match)
                if len(keyword.split()) > 1:
                    base_score *= 1.2

                score += base_score
                matched_keywords.append(keyword)

        # Score pattern matches
        patterns = rules.get("patterns", [])
        for pattern in patterns:
            if re.search(pattern, query, re.IGNORECASE):
                score += (
                    15.0  # Pattern matches are weighted higher than keyword matches
                )

        # Apply priority multiplier
        priority = rules.get("priority", 1)
        score *= priority

        return score, matched_keywords

    def _normalize_context(self, context: Any) -> Dict[str, Any]:
        """Normalize heterogeneous context payloads to a mapping."""
        if isinstance(context, dict):
            return context

        # Intent workflow may pass QueryContext dataclass instances.
        return {
            "uploaded_files": getattr(context, "uploaded_files", []) or [],
            "session_topic": getattr(context, "session_topic", "") or "",
            "recent_intents": getattr(context, "recent_intents", []) or [],
        }

    def _adjust_scores_with_context(
        self, intent_scores: Dict[IntentType, Dict], context: Dict[str, Any]
    ) -> Dict[IntentType, Dict]:
        """Adjust intent scores based on contextual information like uploaded files."""
        # Check for uploaded files
        uploaded_files = context.get("uploaded_files", [])

        if uploaded_files:
            for file_info in uploaded_files:
                file_type = file_info.get("type", "").lower()
                file_ext = file_info.get("extension", "").lower()

                # CSV/Excel files boost data analysis intent
                if file_ext in [".csv", ".xlsx", ".xls"] or "spreadsheet" in file_type:
                    if IntentType.DATA_ANALYSIS in intent_scores:
                        intent_scores[IntentType.DATA_ANALYSIS]["score"] *= 1.5
                        intent_scores[IntentType.DATA_ANALYSIS]["keywords"].append(
                            "detected_csv_file"
                        )

                # PDF/image files boost document processing intent
                elif (
                    file_ext in [".pdf", ".jpg", ".png", ".jpeg", ".tiff"]
                    or "image" in file_type
                    or "pdf" in file_type
                ):
                    if IntentType.DOCUMENT_PROCESSING in intent_scores:
                        intent_scores[IntentType.DOCUMENT_PROCESSING]["score"] *= 1.5
                        intent_scores[IntentType.DOCUMENT_PROCESSING][
                            "keywords"
                        ].append("detected_document_file")

        return intent_scores

    def _get_suggested_action(self, intent: IntentType) -> str:
        """Return a suggested action description for the classified intent."""
        actions = {
            IntentType.KNOWLEDGE_RETRIEVAL: "Route to RAG knowledge retrieval engine",
            IntentType.DATA_ANALYSIS: "Route to Data Analysis Agent for processing",
            IntentType.COST_ESTIMATION: "Route to cost estimation service",
            IntentType.DOCUMENT_PROCESSING: "Route to OCR Agent for document extraction",
            IntentType.CODE_EXECUTION: "Route to Code Execution Agent for processing",
            IntentType.UNCLEAR_INTENT: "Request clarification from the user",
        }
        return actions.get(intent, "Route to default handler")

    def _update_stats(self, result: SimpleIntentResult):
        """Update classification statistics with the latest result."""
        self.stats["total_classifications"] += 1

        if result.is_high_confidence:
            self.stats["high_confidence_count"] += 1

        intent_value = result.intent.value
        if intent_value not in self.stats["intent_distribution"]:
            self.stats["intent_distribution"][intent_value] = 0
        self.stats["intent_distribution"][intent_value] += 1

    def get_stats(self) -> Dict[str, Any]:
        """Return classification statistics including confidence rate."""
        total = self.stats["total_classifications"]
        return {
            **self.stats,
            "high_confidence_rate": (
                self.stats["high_confidence_count"] / max(total, 1)
            ),
        }


_simple_intent_classifier: Optional[SimpleIntentClassifier] = None


def get_simple_intent_classifier() -> SimpleIntentClassifier:
    global _simple_intent_classifier
    if _simple_intent_classifier is None:
        _simple_intent_classifier = SimpleIntentClassifier()
    return _simple_intent_classifier
