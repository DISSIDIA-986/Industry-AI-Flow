"""
Intent Classification Module - RAG Intent Classifier.
Classifies user queries into intent categories and routes them to the appropriate LLM agent.
"""

import asyncio
import hashlib
import json
import logging
import re
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple, Union

import numpy as np
from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.output_parsers import JsonOutputParser

logger = logging.getLogger(__name__)


class IntentType(Enum):
    """Enumeration of primary intent categories."""

    KNOWLEDGE_RETRIEVAL = "knowledge_retrieval"  # Knowledge base retrieval
    DATA_ANALYSIS = "data_analysis"  # Data analysis and visualization
    COST_ESTIMATION = "cost_estimation"  # Cost estimation and prediction
    DOCUMENT_PROCESSING = "document_processing"  # Document and image processing
    CODE_EXECUTION = "code_execution"  # Code execution and computation
    UNCLEAR_INTENT = "unclear_intent"  # Intent could not be determined


class SubIntentType(Enum):
    """Enumeration of sub-intent categories for finer-grained classification."""

    # Knowledge retrieval sub-intents
    FACT_QUERY = "fact_query"  # Factual question
    CONCEPT_EXPLANATION = "concept_explanation"  # Concept explanation
    COMPARISON_ANALYSIS = "comparison_analysis"  # Comparison analysis
    HOW_TO_GUIDE = "how_to_guide"  # How-to guide

    # Data analysis sub-intents
    EXPLORATORY_ANALYSIS = "exploratory_analysis"  # Exploratory data analysis
    STATISTICAL_ANALYSIS = "statistical_analysis"  # Statistical analysis
    MACHINE_LEARNING = "machine_learning"  # Machine learning task
    VISUALIZATION = "visualization"  # Data visualization

    # Document processing sub-intents
    OCR_PROCESSING = "ocr_processing"  # OCR text recognition
    TABLE_EXTRACTION = "table_extraction"  # Table extraction
    IMAGE_ANALYSIS = "image_analysis"  # Image analysis
    TEXT_EXTRACTION = "text_extraction"  # Text extraction

    # Code execution sub-intents
    SCRIPT_EXECUTION = "script_execution"  # Script execution
    COMPUTATION_TASK = "computation_task"  # Computation task
    ALGORITHM_IMPLEMENTATION = "algorithm_implementation"  # Algorithm implementation
    DEBUGGING = "debugging"  # Debugging


@dataclass
class IntentResult:
    """Data class holding intent classification results."""

    intent: IntentType
    sub_intent: Optional[SubIntentType] = None
    confidence: float = 0.0
    reasoning: str = ""
    keywords: List[str] = None
    context_clues: List[str] = None
    suggested_action: str = ""
    uncertainty_factors: List[str] = None
    processing_time_ms: int = 0
    llm_response: Optional[str] = None

    def __post_init__(self):
        if self.keywords is None:
            self.keywords = []
        if self.context_clues is None:
            self.context_clues = []
        if self.uncertainty_factors is None:
            self.uncertainty_factors = []

    def to_dict(self) -> Dict[str, Any]:
        """Convert the intent result to a dictionary."""
        return {
            **asdict(self),
            "intent": self.intent.value
            if isinstance(self.intent, IntentType)
            else self.intent,
            "sub_intent": self.sub_intent.value if self.sub_intent else None,
        }

    @property
    def is_high_confidence(self) -> bool:
        """Return True if confidence is at or above 0.7."""
        return self.confidence >= 0.7

    @property
    def is_very_high_confidence(self) -> bool:
        """Return True if confidence is at or above 0.9."""
        return self.confidence >= 0.9

    @property
    def is_uncertain(self) -> bool:
        """Return True if confidence is below 0.5."""
        return self.confidence < 0.5


@dataclass
class QueryContext:
    """Data class holding query context for intent classification."""

    session_id: str
    user_id: Optional[str] = None
    session_topic: str = ""
    recent_intents: List[str] = None
    uploaded_files: List[Dict[str, Any]] = None
    user_preferences: Dict[str, Any] = None
    interaction_history: List[Dict[str, Any]] = None
    time_of_day: str = ""
    query_count_in_session: int = 0

    def __post_init__(self):
        if self.recent_intents is None:
            self.recent_intents = []
        if self.uploaded_files is None:
            self.uploaded_files = []
        if self.user_preferences is None:
            self.user_preferences = {}
        if self.interaction_history is None:
            self.interaction_history = []

    def add_intent(self, intent: str):
        """Add an intent to the recent intents list."""
        self.recent_intents.append(intent)
        # Keep only the 5 most recent intents
        if len(self.recent_intents) > 5:
            self.recent_intents = self.recent_intents[-5:]

    def add_uploaded_file(self, file_info: Dict[str, Any]):
        """Add an uploaded file to the context."""
        self.uploaded_files.append(file_info)
        # Keep only the 3 most recent uploaded files
        if len(self.uploaded_files) > 3:
            self.uploaded_files = self.uploaded_files[-3:]


class IntentClassifier:
    """Intent classifier that uses LLM and heuristics to classify user queries."""

    def __init__(
        self,
        prompt_manager,
        llm_client,
        confidence_threshold: float = 0.7,
        enable_cache: bool = True,
        cache_ttl: int = 300,
    ):
        """
        Initialize the intent classifier.

        Args:
            prompt_manager: Prompt manager instance for retrieving classification prompts.
            llm_client: LLM client instance for generating classifications.
            confidence_threshold: Minimum confidence threshold for accepting a classification.
            enable_cache: Whether to enable classification result caching.
            cache_ttl: Cache time-to-live in seconds.
        """
        self.prompt_manager = prompt_manager
        self.llm_client = llm_client
        self.confidence_threshold = confidence_threshold
        self.enable_cache = enable_cache
        self.cache_ttl = cache_ttl

        # Classification result cache
        self._classification_cache: Dict[str, Tuple[IntentResult, datetime]] = {}

        # Classification statistics
        self.stats = {
            "total_classifications": 0,
            "high_confidence_count": 0,
            "clarification_count": 0,
            "cache_hits": 0,
            "avg_confidence": 0.0,
        }

        logger.info("Intent classifier initialized")

    async def classify_intent(self, query: str, context: QueryContext) -> IntentResult:
        """
        Classify the intent of a user query.

        Args:
            query: The user's input query string.
            context: Query context including session and file information.

        Returns:
            IntentResult: The classification result with intent, confidence, and metadata.
        """
        start_time = datetime.now()

        try:
            # 1. Preprocess the input query
            processed_query = await self._preprocess_input(query)

            # 2. Check the cache for a previous classification
            cache_key = self._generate_cache_key(processed_query, context)
            if self.enable_cache:
                cached_result = self._get_from_cache(cache_key)
                if cached_result:
                    self.stats["cache_hits"] += 1
                    logger.debug(f"Cache hit for intent: {cached_result.intent}")
                    return cached_result

            # 3. Build the classification request
            classification_request = await self._build_classification_request(
                processed_query, context
            )

            # 4. Retrieve the prompt template (if available)
            prompt_prefix = ""
            if self.prompt_manager is not None:
                try:
                    _, prompt_content = await self.prompt_manager.get_prompt(
                        name="intent_classification",
                        category="Intent",
                        context={
                            "query_length": len(processed_query),
                            "has_uploaded_files": len(context.uploaded_files) > 0,
                            "session_depth": context.query_count_in_session,
                        },
                        variables={
                            "user_query": processed_query,
                            "session_topic": context.session_topic,
                            "recent_intents": ", ".join(context.recent_intents[-3:])
                            if context.recent_intents
                            else "",
                            "uploaded_files": ", ".join(
                                [f["name"] for f in context.uploaded_files]
                            )
                            if context.uploaded_files
                            else "none",
                            "user_preferences": json.dumps(
                                context.user_preferences, ensure_ascii=False
                            ),
                        },
                    )
                    prompt_prefix = prompt_content
                except Exception as prompt_exc:
                    logger.warning(
                        "Failed to retrieve prompt template, using fallback: %s", prompt_exc
                    )

            # 5. Call the LLM for classification
            final_prompt = (
                f"{prompt_prefix}\n\n{classification_request}"
                if prompt_prefix
                else classification_request
            )
            llm_response = await self._call_llm_for_classification(final_prompt)

            # 6. Parse the classification result
            intent_result = await self._parse_classification_result(llm_response)

            # 7. Post-process the result
            intent_result = await self._post_process_result(
                intent_result, query, context
            )

            # 8. Save to cache
            if self.enable_cache:
                self._save_to_cache(cache_key, intent_result)

            # 9. Update statistics
            self._update_stats(intent_result)

            # 10. Record processing time
            intent_result.processing_time_ms = int(
                (datetime.now() - start_time).total_seconds() * 1000
            )
            intent_result.llm_response = llm_response

            logger.info(
                f"Classification result: {intent_result.intent} (confidence: {intent_result.confidence:.2f})"
            )
            return intent_result

        except Exception as e:
            logger.error(f"Intent classification failed: {e}")
            # Return a fallback result on error
            return IntentResult(
                intent=IntentType.UNCLEAR_INTENT,
                confidence=0.0,
                reasoning=f"Classification error: {str(e)}",
                processing_time_ms=int(
                    (datetime.now() - start_time).total_seconds() * 1000
                ),
            )

    async def _preprocess_input(self, query: str) -> str:
        """
        Preprocess the user query by normalizing whitespace and punctuation.

        Args:
            query: The raw user query string.

        Returns:
            str: The preprocessed query string.
        """
        if not query:
            return ""

        # Normalize whitespace
        processed = re.sub(r"\s+", " ", query.strip())

        # Remove special characters (keep alphanumerics, CJK characters, and common punctuation)
        processed = re.sub(r'[^\w\s\u4e00-\u9fff.,!?;:()\[\]{}"\'-]', "", processed)

        # Normalize punctuation
        processed = re.sub(
            r"[,.!?;:]",
            lambda m: {",": ",", ".": ".", "!": "!", "?": "?", ";": ";", ":": ":"}[
                m.group()
            ],
            processed,
        )

        # Lowercase English-heavy text for consistent matching
        processed = (
            processed.lower() if self._is_english_heavy(processed) else processed
        )

        return processed.strip()

    def _is_english_heavy(self, text: str) -> bool:
        """Return True if the text contains more English characters than Chinese."""
        if not text:
            return False

        english_chars = len(re.findall(r"[a-zA-Z]", text))
        chinese_chars = len(re.findall(r"[\u4e00-\u9fff]", text))
        total_chars = len(re.findall(r"\w", text))

        return english_chars > chinese_chars and total_chars > 0

    async def _extract_context(self, session_id: str) -> QueryContext:
        """
        Extract query context from the session.

        Args:
            session_id: The session ID to extract context for.

        Returns:
            QueryContext: The extracted query context.
        """
        # TODO: Integrate with actual session storage
        # Return a default context for now
        return QueryContext(
            session_id=session_id,
            session_topic="general",
            recent_intents=[],
            uploaded_files=[],
            user_preferences={},
            interaction_history=[],
            time_of_day=datetime.now().strftime("%H:%M"),
            query_count_in_session=1,
        )

    async def _build_classification_request(
        self, query: str, context: QueryContext
    ) -> str:
        """
        Build the classification request prompt.

        Args:
            query: The preprocessed user query.
            context: The query context with session information.

        Returns:
            str: The formatted classification request prompt.
        """
        recent_intents = (
            ", ".join(context.recent_intents[-3:]) if context.recent_intents else "(none)"
        )
        uploaded_files = (
            ", ".join(
                str(item.get("name") or "")
                for item in context.uploaded_files
                if isinstance(item, dict)
            )
            if context.uploaded_files
            else "(none)"
        )
        user_preferences = (
            json.dumps(context.user_preferences, ensure_ascii=False)
            if context.user_preferences
            else "{}"
        )

        return (
            "You are an intent classifier for an enterprise RAG workflow.\n"
            "Classify the user request into one of the exact intents:\n"
            "- knowledge_retrieval\n"
            "- data_analysis\n"
            "- cost_estimation\n"
            "- document_processing\n"
            "- code_execution\n"
            "- unclear_intent\n\n"
            "Return ONLY strict JSON with keys:\n"
            "intent, confidence, reasoning, keywords, context_clues, suggested_action, uncertainty_factors.\n"
            "confidence must be a number between 0 and 1.\n\n"
            f"Query:\n{query}\n\n"
            f"Session topic: {context.session_topic or '(none)'}\n"
            f"Recent intents: {recent_intents}\n"
            f"Uploaded files: {uploaded_files}\n"
            f"User preferences: {user_preferences}\n"
        )

    async def _call_llm_for_classification(self, prompt: str) -> str:
        """
        Call the LLM to classify the intent.

        Args:
            prompt: The classification prompt to send to the LLM.

        Returns:
            str: The LLM response as a JSON string.
        """
        try:
            if self.llm_client is not None and hasattr(self.llm_client, "generate"):
                response = await asyncio.to_thread(
                    self.llm_client.generate,
                    prompt,
                    temperature=0.0,
                    max_tokens=320,
                )
                if isinstance(response, str) and response.strip():
                    return response
                logger.warning("Intent LLM classification returned empty text, fallback to heuristic simulator")
            return await self._simulate_llm_response(prompt)
        except Exception as e:
            logger.warning("LLM classification failed, falling back to heuristic: %s", e)
            return await self._simulate_llm_response(prompt)

    async def _simulate_llm_response(self, prompt: str) -> str:
        """
        Simulate an LLM response using keyword-based heuristics (fallback).

        Args:
            prompt: The classification prompt to analyze.

        Returns:
            str: A simulated LLM response as a JSON string.
        """
        # Extract only the user query text — NOT the full prompt (which contains
        # intent names in the preamble that would cause false keyword matches).
        query_text = prompt
        query_marker = "Query:\n"
        marker_idx = prompt.find(query_marker)
        if marker_idx >= 0:
            query_text = prompt[marker_idx + len(query_marker):]
            # Truncate at the next section boundary
            end_idx = query_text.find("\n\n")
            if end_idx >= 0:
                query_text = query_text[:end_idx]
        query_lower = query_text.lower()

        # Match intent based on keywords.
        # Cost estimation is checked BEFORE knowledge retrieval because
        # generic knowledge prefixes like "how to" overlap with cost queries
        # (e.g., "how to estimate construction cost").
        if any(
            keyword in query_lower
            for keyword in [
                "cost estimate",
                "cost estimation",
                "budget",
                "overrun",
                "construction cost",
                "price",
                "pricing",
                "how much",
                "estimate cost",
                "project cost",
            ]
        ):
            intent = "cost_estimation"
            confidence = 0.91
            reasoning = "Query contains cost estimation keywords"
        elif any(keyword in query_lower for keyword in [
            "what is", "how to", "tell me", "explain", "define", "describe",
            "properties of", "requirements for", "difference between",
            "what are", "how does", "why is", "when should",
        ]):
            intent = "knowledge_retrieval"
            confidence = 0.85
            reasoning = "Query contains knowledge retrieval keywords"
        elif any(
            keyword in query_lower for keyword in [
                "analyze", "analysis", "statistics", "chart", "data", "dataset",
                "compare", "trend", "visualization", "graph",
            ]
        ):
            intent = "data_analysis"
            confidence = 0.90
            reasoning = "Query contains data analysis keywords"
        elif any(
            keyword in query_lower for keyword in [
                "pdf", "image", "ocr", "extract", "scan", "upload", "document",
                "read file", "parse",
            ]
        ):
            intent = "document_processing"
            confidence = 0.88
            reasoning = "Query contains document/OCR processing keywords"
        elif any(keyword in query_lower for keyword in [
            "run", "execute", "code", "calculate", "script", "compute",
            "program", "function",
        ]):
            intent = "code_execution"
            confidence = 0.87
            reasoning = "Query contains code execution keywords"
        else:
            intent = "unclear_intent"
            confidence = 0.45
            reasoning = "Unable to determine clear intent from query"

        # Extract detected keywords
        keywords = []
        if "cost" in query_lower:
            keywords.append("cost")
        if "data" in query_lower:
            keywords.append("data")
        if "pdf" in query_lower:
            keywords.append("PDF")
        if "code" in query_lower:
            keywords.append("code")

        return json.dumps(
            {
                "intent": intent,
                "confidence": confidence,
                "reasoning": reasoning,
                "keywords": keywords,
                "context_clues": [],
                "suggested_action": f"Route to {intent} handler",
                "uncertainty_factors": [] if confidence > 0.7 else ["Low confidence classification"],
            },
            ensure_ascii=False,
        )

    async def _parse_classification_result(self, llm_response: str) -> IntentResult:
        """
        Parse the LLM classification response into an IntentResult.

        Args:
            llm_response: The raw LLM response string.

        Returns:
            IntentResult: The parsed classification result.
        """
        try:
            # Try direct JSON parsing
            if llm_response.strip().startswith("{"):
                data = json.loads(llm_response)
            else:
                # Extract JSON object from mixed text response
                json_match = re.search(r"\{.*\}", llm_response, re.DOTALL)
                if json_match:
                    data = json.loads(json_match.group())
                else:
                    raise ValueError("No JSON object found in LLM response")

            # Build IntentResult from parsed data
            intent_value = self._normalize_intent_value(data.get("intent", "unclear_intent"))
            intent = (
                IntentType(intent_value)
                if intent_value in [e.value for e in IntentType]
                else IntentType.UNCLEAR_INTENT
            )

            sub_intent_value = data.get("sub_intent")
            sub_intent = None
            if sub_intent_value and sub_intent_value in [
                e.value for e in SubIntentType
            ]:
                sub_intent = SubIntentType(sub_intent_value)

            return IntentResult(
                intent=intent,
                sub_intent=sub_intent,
                confidence=float(data.get("confidence", 0.0)),
                reasoning=data.get("reasoning", ""),
                keywords=data.get("keywords", []),
                context_clues=data.get("context_clues", []),
                suggested_action=data.get("suggested_action", ""),
                uncertainty_factors=data.get("uncertainty_factors", []),
            )

        except Exception as e:
            logger.error(f"Failed to parse classification result: {e}")
            # Return a fallback result on parse failure
            return IntentResult(
                intent=IntentType.UNCLEAR_INTENT,
                confidence=0.0,
                reasoning=f"Parse error: {str(e)}",
            )

    @staticmethod
    def _normalize_intent_value(raw: Any) -> str:
        value = str(raw or "").strip().lower()
        if not value:
            return "unclear_intent"

        aliases = {
            "knowledge": "knowledge_retrieval",
            "knowledge retrieval": "knowledge_retrieval",
            "knowledge-retrieval": "knowledge_retrieval",
            "rag": "knowledge_retrieval",
            "retrieval": "knowledge_retrieval",
            "analysis": "data_analysis",
            "data analysis": "data_analysis",
            "data-analysis": "data_analysis",
            "cost estimate": "cost_estimation",
            "cost estimation": "cost_estimation",
            "cost-estimation": "cost_estimation",
            "document": "document_processing",
            "doc_processing": "document_processing",
            "document processing": "document_processing",
            "document-processing": "document_processing",
            "code": "code_execution",
            "coding": "code_execution",
            "execution": "code_execution",
            "code execution": "code_execution",
            "code-execution": "code_execution",
            "unclear": "unclear_intent",
            "unknown": "unclear_intent",
        }
        return aliases.get(value, value)

    async def _post_process_result(
        self, result: IntentResult, original_query: str, context: QueryContext
    ) -> IntentResult:
        """
        Post-process the classification result with contextual adjustments.

        Args:
            result: The initial classification result.
            original_query: The original user query.
            context: The query context with session information.

        Returns:
            IntentResult: The adjusted classification result.
        """
        # Clamp confidence to [0.0, 1.0]
        result.confidence = max(0.0, min(1.0, result.confidence))

        # Boost confidence if intent matches recent session history
        if (
            context.recent_intents
            and result.intent.value in context.recent_intents[-2:]
        ):
            # Intent matches recent history, boost confidence
            result.confidence = min(1.0, result.confidence + 0.1)
            result.reasoning += f" (intent '{result.intent.value}' matches recent session history, confidence boosted)"

        # Adjust confidence based on uploaded file types
        if context.uploaded_files:
            file_types = [f.get("type", "") for f in context.uploaded_files]
            if "data" in file_types and result.intent == IntentType.DATA_ANALYSIS:
                result.confidence = min(1.0, result.confidence + 0.15)
                result.reasoning += " (data file uploaded, confidence boosted)"
            elif (
                any("pdf" in ft.lower() or "image" in ft.lower() for ft in file_types)
                and result.intent == IntentType.DOCUMENT_PROCESSING
            ):
                result.confidence = min(1.0, result.confidence + 0.15)
                result.reasoning += " (PDF/image file uploaded, confidence boosted)"

        # Append detected keywords to reasoning
        if result.keywords:
            result.reasoning += f" (detected keywords: {', '.join(result.keywords)})"

        # Set suggested action based on intent
        result.suggested_action = self._get_suggested_action(result.intent)

        return result

    def _get_suggested_action(self, intent: IntentType) -> str:
        """Get suggested action for the classified intent."""
        actions = {
            IntentType.KNOWLEDGE_RETRIEVAL: "Use RAG engine for knowledge retrieval",
            IntentType.DATA_ANALYSIS: "Route to Data Analysis Agent for processing",
            IntentType.COST_ESTIMATION: "Route to cost estimation module",
            IntentType.DOCUMENT_PROCESSING: "Route to OCR Agent for document processing",
            IntentType.CODE_EXECUTION: "Route to Code Execution Agent for processing",
            IntentType.UNCLEAR_INTENT: "Request clarification from user",
        }
        return actions.get(intent, "Route to general handler")

    def _generate_cache_key(self, query: str, context: QueryContext) -> str:
        """Generate a cache key from the query and context."""
        key_data = {
            "query": query,
            "recent_intents": context.recent_intents[-2:]
            if context.recent_intents
            else [],
            "has_files": len(context.uploaded_files) > 0,
        }
        payload = json.dumps(key_data, sort_keys=True, ensure_ascii=False)
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    def _get_from_cache(self, cache_key: str) -> Optional[IntentResult]:
        """Retrieve a classification result from the cache if still valid."""
        if cache_key in self._classification_cache:
            result, cached_at = self._classification_cache[cache_key]
            if datetime.now() - cached_at < timedelta(seconds=self.cache_ttl):
                return result
            else:
                del self._classification_cache[cache_key]
        return None

    def _save_to_cache(self, cache_key: str, result: IntentResult):
        """Save a classification result to the cache."""
        self._classification_cache[cache_key] = (result, datetime.now())

        # Evict oldest entry if cache exceeds limit
        if len(self._classification_cache) > 1000:
            # Remove the oldest cached entry
            oldest_key = min(
                self._classification_cache.keys(),
                key=lambda k: self._classification_cache[k][1],
            )
            del self._classification_cache[oldest_key]

    def _update_stats(self, result: IntentResult):
        """Update classification statistics with the latest result."""
        self.stats["total_classifications"] += 1
        if result.is_high_confidence:
            self.stats["high_confidence_count"] += 1
        if result.is_uncertain:
            self.stats["clarification_count"] += 1

        # Update running average confidence
        total = self.stats["total_classifications"]
        current_avg = self.stats["avg_confidence"]
        self.stats["avg_confidence"] = (
            (current_avg * (total - 1)) + result.confidence
        ) / total

    async def get_clarification_prompt(self, query: str, result: IntentResult) -> str:
        """
        Generate a clarification prompt when intent is uncertain.

        Args:
            query: The original user query.
            result: The uncertain classification result.

        Returns:
            str: A clarification prompt to present to the user.
        """
        try:
            prompt_info, prompt_content = await self.prompt_manager.get_prompt(
                name="intent_clarification",
                category="Intent",
                context={"confidence": result.confidence},
                variables={
                    "user_query": query,
                    "possible_intents": json.dumps(
                        [
                            {"type": "knowledge_retrieval", "desc": "Search and retrieve knowledge"},
                            {"type": "data_analysis", "desc": "Analyze and visualize data"},
                            {"type": "cost_estimation", "desc": "Estimate project costs"},
                            {"type": "document_processing", "desc": "Process documents with OCR"},
                            {"type": "code_execution", "desc": "Execute code and computations"},
                        ],
                        ensure_ascii=False,
                    ),
                },
            )

            # Use prompt_manager content if available, otherwise simulate
            if prompt_content:
                return prompt_content
            return await self._simulate_clarification_response(query, result)

        except Exception as e:
            logger.error(f"Failed to generate clarification prompt: {e}")
            return (
                "I'm not sure I understand your request. "
                "Could you please clarify what you'd like to do? For example: "
                "1. Search for information "
                "2. Analyze data "
                "3. Process a document "
                "4. Run some code"
            )

    async def _simulate_clarification_response(
        self, query: str, result: IntentResult
    ) -> str:
        """Generate a simulated clarification response for ambiguous queries."""
        return f"""I noticed your query "{query}" could be interpreted in several ways. Could you please clarify which of the following you'd like to do?

1. **Knowledge Retrieval** - Search the knowledge base for relevant information
2. **Data Analysis** - Analyze datasets and generate visualizations
3. **Document Processing** - Extract text from PDFs or images using OCR
4. **Code Execution** - Run code or perform computations

Please select the option that best matches your intent, or provide more details."""

    async def route_to_agent(
        self, result: IntentResult, context: QueryContext
    ) -> Dict[str, Any]:
        """
        Route the classified intent to the appropriate agent.

        Args:
            result: The classification result.
            context: The query context.

        Returns:
            Dict[str, Any]: Routing information for the target agent.
        """
        routing_info = {
            "success": True,
            "intent": result.intent.value,
            "sub_intent": result.sub_intent.value if result.sub_intent else None,
            "confidence": result.confidence,
            "agent_type": self._get_agent_type(result.intent),
            "routing_reason": result.reasoning,
            "requires_clarification": result.is_uncertain,
            "suggested_action": result.suggested_action,
        }

        # Add agent-specific routing metadata
        if result.intent == IntentType.DATA_ANALYSIS:
            routing_info.update(
                {
                    "requires_docker": True,
                    "supported_formats": ["csv", "excel", "json", "parquet"],
                    "default_visualization": True,
                }
            )
        elif result.intent == IntentType.COST_ESTIMATION:
            routing_info.update(
                {
                    "supported_formats": ["csv", "excel", "json"],
                    "model_inference": True,
                    "prediction_targets": ["cost_overrun_pct", "actual_cost_cad"],
                }
            )
        elif result.intent == IntentType.DOCUMENT_PROCESSING:
            routing_info.update(
                {
                    "supported_formats": ["pdf", "jpg", "png", "tiff"],
                    "ocr_engines": ["pytesseract", "deepscan"],
                    "output_format": "text",
                }
            )
        elif result.intent == IntentType.CODE_EXECUTION:
            routing_info.update(
                {
                    "supported_languages": ["python", "javascript", "sql"],
                    "execution_timeout": 30,
                    "safety_checks": True,
                }
            )

        return routing_info

    def _get_agent_type(self, intent: IntentType) -> str:
        """Get the agent type name for the given intent."""
        agent_mapping = {
            IntentType.KNOWLEDGE_RETRIEVAL: "RAGAgent",
            IntentType.DATA_ANALYSIS: "DataAnalysisAgent",
            IntentType.COST_ESTIMATION: "CostEstimationAgent",
            IntentType.DOCUMENT_PROCESSING: "OCRAgent",
            IntentType.CODE_EXECUTION: "CodeExecutorAgent",
            IntentType.UNCLEAR_INTENT: "ClarificationAgent",
        }
        return agent_mapping.get(intent, "GeneralAgent")

    def get_stats(self) -> Dict[str, Any]:
        """Return classification statistics."""
        total = self.stats["total_classifications"]
        return {
            **self.stats,
            "high_confidence_rate": (
                self.stats["high_confidence_count"] / max(total, 1)
            ),
            "clarification_rate": (self.stats["clarification_count"] / max(total, 1)),
            "cache_hit_rate": (self.stats["cache_hits"] / max(total, 1)),
            "cache_size": len(self._classification_cache),
        }

    def clear_cache(self):
        """Clear the classification result cache."""
        self._classification_cache.clear()
        logger.info("Classification cache cleared")

    async def health_check(self) -> Dict[str, Any]:
        """Perform a health check on the intent classifier."""
        try:
            # Verify the prompt manager is accessible
            test_prompt, _ = await self.prompt_manager.get_prompt(
                name="intent_classification", category="Intent"
            )

            return {
                "status": "healthy",
                "prompt_manager": "connected",
                "cache_size": len(self._classification_cache),
                "confidence_threshold": self.confidence_threshold,
                "stats": self.get_stats(),
            }

        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "prompt_manager": "disconnected",
            }
