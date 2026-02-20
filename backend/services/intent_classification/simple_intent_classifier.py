"""
EN - EN
EN
"""

import json
import logging
import re
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class IntentType(Enum):
    """EN"""

    KNOWLEDGE_RETRIEVAL = "knowledge_retrieval"  # EN
    DATA_ANALYSIS = "data_analysis"  # EN
    COST_ESTIMATION = "cost_estimation"  # EN
    DOCUMENT_PROCESSING = "document_processing"  # EN
    CODE_EXECUTION = "code_execution"  # EN
    UNCLEAR_INTENT = "unclear_intent"  # EN


@dataclass
class SimpleIntentResult:
    """EN"""

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
        """EN"""
        return self.confidence >= 0.7

    @property
    def is_uncertain(self) -> bool:
        """EN"""
        return self.confidence < 0.5


class SimpleIntentClassifier:
    """
    EN - EN

    ENLLMEN,EN:
    1. EN
    2. EN
    3. EN
    """

    def __init__(self, confidence_threshold: float = 0.7):
        """
        EN

        Args:
            confidence_threshold: EN
        """
        self.confidence_threshold = confidence_threshold

        # EN
        self._keyword_rules = self._build_keyword_rules()

        # EN
        self.stats = {
            "total_classifications": 0,
            "high_confidence_count": 0,
            "intent_distribution": {},
        }

        logger.info("EN")

    def _build_keyword_rules(self) -> Dict[IntentType, Dict[str, Any]]:
        """EN"""
        return {
            IntentType.KNOWLEDGE_RETRIEVAL: {
                "keywords": [
                    # EN
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
                    # EN
                    "EN",
                    "EN",
                    "EN",
                    "EN",
                    "EN",
                    "EN",
                    "EN",
                    "EN",
                    "EN",
                    "EN",
                    "EN",
                ],
                "patterns": [
                    r"what\s+(is|are|does)",
                    r"how\s+(does|do|to)",
                    r"(explain|describe|tell)\s+me",
                    r"EN",
                    r"EN.*EN",
                ],
                "priority": 1,
            },
            IntentType.DATA_ANALYSIS: {
                "keywords": [
                    # EN - EN
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
                    # EN - EN
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
                    # EN - EN
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
                    # EN - EN
                    "compare",
                    "comparison",
                    "versus",
                    "vs",
                    "difference",
                    "between",
                    "among",
                    "relation",
                    "relationship",
                    # EN - EN
                    "chart",
                    "graph",
                    "plot",
                    "visualization",
                    "visualize",
                    "histogram",
                    "scatter",
                    "bar chart",
                    "line plot",
                    # EN - EN
                    "EN",
                    "EN",
                    "EN",
                    "EN",
                    "EN",
                    "EN",
                    # EN - EN
                    "EN",
                    "EN",
                    "EN",
                    "EN",
                    "EN",
                    "EN",
                    "EN",
                    "EN",
                    "EN",
                    # EN - EN
                    "EN",
                    "EN",
                    "EN",
                    "EN",
                    "EN",
                    "EN",
                    "EN",
                    "EN",
                    "EN",
                    "EN",
                    "EN",
                    "EN",
                    # EN - EN
                    "EN",
                    "EN",
                    "EN",
                    "EN",
                    "EN",
                    # EN - EN
                    "EN",
                    "EN",
                    "EN",
                    "EN",
                    "EN",
                ],
                "patterns": [
                    r"(analyze|analysis|calculate)\s+",
                    r"(average|mean|median|max|min|sum|count)\s+",
                    r"(highest|lowest|most|least)\s+",
                    r"(compare|comparison|versus|vs)\s+",
                    r"what\s+(is|are)\s+the\s+(average|max|min|total)",
                    r"how\s+many",
                    r"(percentage|ratio)\s+of",
                    r"EN.*EN",
                    r"(EN|EN|EN|EN|EN)",
                    r"(EN|EN).*EN",
                    r"EN.*EN",
                ],
                "priority": 2,  # EN,EN
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
                    "EN",
                    "EN",
                    "EN",
                    "EN",
                    "EN",
                    "EN",
                    "EN",
                ],
                "patterns": [
                    r"(cost|budget)\s+(estimate|estimation|forecast)",
                    r"(cost|budget)\s+overrun",
                    r"(estimate|predict).*(cost|budget)",
                    r"(EN|EN).*(EN|EN)",
                    r"(EN|EN).*(EN|EN)",
                ],
                "priority": 3,
            },
            IntentType.DOCUMENT_PROCESSING: {
                "keywords": [
                    # EN
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
                    # EN
                    "pdf",
                    "EN",
                    "EN",
                    "EN",
                    "EN",
                    "EN",
                    "EN",
                    "EN",
                    "EN",
                    "EN",
                    "EN",
                ],
                "patterns": [
                    r"(extract|read|parse)\s+(text|content)\s+from",
                    r"ocr\s+",
                    r"(pdf|document|image|file)\s+",
                    r"EN.*EN",
                    r"EN.*EN",
                ],
                "priority": 1,
            },
            IntentType.CODE_EXECUTION: {
                "keywords": [
                    # EN
                    "run",
                    "execute",
                    "code",
                    "script",
                    "program",
                    "compute",
                    "calculation",
                    "algorithm",
                    "function",
                    "implement",
                    "process",
                    "batch",
                    "automation",
                    # EN
                    "EN",
                    "EN",
                    "EN",
                    "EN",
                    "EN",
                    "EN",
                    "EN",
                    "EN",
                    "EN",
                    "EN",
                    "EN",
                    "EN",
                ],
                "patterns": [
                    r"(run|execute)\s+(code|script|program)",
                    r"implement\s+",
                    r"EN.*EN",
                    r"EN.*EN",
                ],
                "priority": 1,
            },
        }

    def classify_intent(
        self, query: str, context: Optional[Dict[str, Any]] = None
    ) -> SimpleIntentResult:
        """
        EN

        Args:
            query: EN
            context: EN(EN)

        Returns:
            SimpleIntentResult: EN
        """
        try:
            # EN
            processed_query = self._preprocess_query(query)

            # EN
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

            # EN
            if context:
                intent_scores = self._adjust_scores_with_context(intent_scores, context)

            # EN
            if not intent_scores:
                # EN
                result = SimpleIntentResult(
                    intent=IntentType.UNCLEAR_INTENT,
                    confidence=0.3,
                    reasoning="EN",
                    suggested_action="EN",
                )
            else:
                # EN
                best_intent = max(intent_scores.items(), key=lambda x: x[1]["score"])
                intent_type, intent_data = best_intent

                # EN(EN)
                max_possible_score = 100.0  # EN
                confidence = min(intent_data["score"] / max_possible_score, 1.0)

                # EN
                reasoning = f"EN{len(intent_data['keywords'])}EN: {', '.join(intent_data['keywords'][:3])}"

                result = SimpleIntentResult(
                    intent=intent_type,
                    confidence=confidence,
                    reasoning=reasoning,
                    keywords=intent_data["keywords"],
                    suggested_action=self._get_suggested_action(intent_type),
                )

            # EN
            self._update_stats(result)

            logger.info(f"EN: {result.intent.value} (EN: {result.confidence:.2f})")
            return result

        except Exception as e:
            logger.error(f"EN: {e}")
            return SimpleIntentResult(
                intent=IntentType.UNCLEAR_INTENT,
                confidence=0.0,
                reasoning=f"EN: {str(e)}",
                suggested_action="EN",
            )

    def _preprocess_query(self, query: str) -> str:
        """EN"""
        # EN
        processed = query.lower()

        # EN
        processed = re.sub(r"\s+", " ", processed).strip()

        return processed

    def _calculate_intent_score(self, query: str, rules: Dict[str, Any]) -> tuple:
        """
        EN

        Args:
            query: EN
            rules: EN

        Returns:
            tuple: (EN, EN)
        """
        score = 0.0
        matched_keywords = []

        # EN
        keywords = rules.get("keywords", [])
        for keyword in keywords:
            if keyword.lower() in query:
                # EN
                base_score = 10.0

                # EN:EN
                if query.startswith(keyword.lower()):
                    base_score *= 1.5

                # EN:EN
                if len(keyword.split()) > 1:
                    base_score *= 1.2

                score += base_score
                matched_keywords.append(keyword)

        # EN
        patterns = rules.get("patterns", [])
        for pattern in patterns:
            if re.search(pattern, query, re.IGNORECASE):
                score += 15.0  # EN

        # EN
        priority = rules.get("priority", 1)
        score *= priority

        return score, matched_keywords

    def _adjust_scores_with_context(
        self, intent_scores: Dict[IntentType, Dict], context: Dict[str, Any]
    ) -> Dict[IntentType, Dict]:
        """EN"""
        # EN
        uploaded_files = context.get("uploaded_files", [])

        if uploaded_files:
            for file_info in uploaded_files:
                file_type = file_info.get("type", "").lower()
                file_ext = file_info.get("extension", "").lower()

                # CSV/ExcelEN
                if file_ext in [".csv", ".xlsx", ".xls"] or "spreadsheet" in file_type:
                    if IntentType.DATA_ANALYSIS in intent_scores:
                        intent_scores[IntentType.DATA_ANALYSIS]["score"] *= 1.5
                        intent_scores[IntentType.DATA_ANALYSIS]["keywords"].append(
                            "detected_csv_file"
                        )

                # PDF/EN
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
        """EN"""
        actions = {
            IntentType.KNOWLEDGE_RETRIEVAL: "ENRAGEN",
            IntentType.DATA_ANALYSIS: "ENAgentEN",
            IntentType.COST_ESTIMATION: "EN",
            IntentType.DOCUMENT_PROCESSING: "ENOCR AgentEN",
            IntentType.CODE_EXECUTION: "ENAgentEN",
            IntentType.UNCLEAR_INTENT: "EN",
        }
        return actions.get(intent, "EN")

    def _update_stats(self, result: SimpleIntentResult):
        """EN"""
        self.stats["total_classifications"] += 1

        if result.is_high_confidence:
            self.stats["high_confidence_count"] += 1

        intent_value = result.intent.value
        if intent_value not in self.stats["intent_distribution"]:
            self.stats["intent_distribution"][intent_value] = 0
        self.stats["intent_distribution"][intent_value] += 1

    def get_stats(self) -> Dict[str, Any]:
        """EN"""
        total = self.stats["total_classifications"]
        return {
            **self.stats,
            "high_confidence_rate": (
                self.stats["high_confidence_count"] / max(total, 1)
            ),
        }


# EN
simple_intent_classifier = SimpleIntentClassifier()
