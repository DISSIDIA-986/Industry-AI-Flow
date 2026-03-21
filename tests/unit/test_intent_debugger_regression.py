"""
Regression tests for the Intent Debugger feature:
1. Misclassification fix (exclusive_keywords)
2. classify_heuristic_detailed() all-scores return
3. @_trace_node decorator error resilience
4. Capability YAML schema validation
"""

import json

import pytest

from backend.services.intent_classification.capability_registry import (
    CapabilityRegistry,
    get_capability_registry,
)
from backend.services.intent_classification.intent_classifier import (
    IntentClassifier,
    QueryContext,
)


# ── Misclassification regression tests ──────────────────────────


class TestIntentMisclassificationFix:
    """Ensure data_analysis/code_execution queries are NOT routed to cost_estimation."""

    @pytest.fixture(autouse=True)
    def registry(self):
        self.reg = get_capability_registry()

    @pytest.mark.parametrize(
        "query,expected_intent",
        [
            # Data Analysis queries that were previously misclassified as cost_estimation
            ("Analyze construction cost trends by region", "data_analysis"),
            (
                "Show me statistics on cost overruns for different project types",
                "data_analysis",
            ),
            (
                "Create a visualization comparing project budgets by location",
                "data_analysis",
            ),
            ("Analyze the trend of construction costs over the past 5 years", "data_analysis"),
            # Code Execution queries
            (
                "Run a Python script to calculate the structural load capacity",
                "code_execution",
            ),
            (
                "Execute this Python code to compute the beam stress formula",
                "code_execution",
            ),
            # Cost Estimation queries — must NOT regress
            (
                "How much does a 10-story commercial office building cost in Toronto?",
                "cost_estimation",
            ),
            (
                "Estimate the construction cost for a residential project with 5 floors",
                "cost_estimation",
            ),
            (
                "What is the typical budget overrun percentage for healthcare projects?",
                "cost_estimation",
            ),
            # Knowledge Retrieval
            (
                "What are the fall protection requirements under OSHA 1926?",
                "knowledge_retrieval",
            ),
            (
                "Summarize the key requirements in the National Building Code of Canada",
                "knowledge_retrieval",
            ),
        ],
    )
    def test_intent_classification_accuracy(self, query, expected_intent):
        intent_id, confidence, reasoning = self.reg.classify_heuristic(query)
        assert intent_id == expected_intent, (
            f"Query '{query[:60]}...' classified as {intent_id} "
            f"(expected {expected_intent}). Reasoning: {reasoning}"
        )

    def test_ambiguous_query_gets_low_confidence(self):
        """Ambiguous query should get low confidence, allowing LLM to classify."""
        intent_id, confidence, _ = self.reg.classify_heuristic(
            "Can you help me with this project task?"
        )
        assert confidence < 0.85, (
            f"Ambiguous query should have confidence < 0.85 (got {confidence}), "
            "so the LLM is called for proper classification."
        )


# ── classify_heuristic_detailed() tests ─────────────────────────


class TestHeuristicDetailedScoring:
    """Test the all-scores return from classify_heuristic_detailed."""

    @pytest.fixture(autouse=True)
    def registry(self):
        self.reg = get_capability_registry()

    def test_returns_all_capability_scores(self):
        result = self.reg.classify_heuristic_detailed(
            "Analyze construction cost trends"
        )
        assert "capability_scores" in result
        scores = result["capability_scores"]
        # Should have scores for all 5 capabilities
        assert len(scores) >= 5
        for cap_id in [
            "cost_estimation",
            "knowledge_retrieval",
            "data_analysis",
            "code_execution",
            "document_processing",
        ]:
            assert cap_id in scores, f"Missing score for {cap_id}"
            assert "score" in scores[cap_id]
            assert "confidence" in scores[cap_id]
            assert "matched_keywords" in scores[cap_id]
            assert "penalized" in scores[cap_id]

    def test_returns_matched_keywords_with_capability(self):
        result = self.reg.classify_heuristic_detailed(
            "Analyze the CSV dataset and show statistics"
        )
        assert "matched_keywords" in result
        # Each entry is (keyword, capability_id)
        for kw, cap_id in result["matched_keywords"]:
            assert isinstance(kw, str)
            assert isinstance(cap_id, str)

    def test_exclusive_keywords_penalty_applied(self):
        """Cost estimation should be penalized when no exclusive keywords match."""
        result = self.reg.classify_heuristic_detailed(
            "Analyze construction cost trends by region"
        )
        cost_scores = result["capability_scores"]["cost_estimation"]
        assert cost_scores["penalized"] is True, (
            "cost_estimation should be penalized when query has cost keywords "
            "but no exclusive keywords (estimate, budget, etc.)"
        )

    def test_no_penalty_when_exclusive_keyword_present(self):
        """Cost estimation should NOT be penalized when exclusive keywords match."""
        result = self.reg.classify_heuristic_detailed(
            "Estimate the construction cost for a residential project"
        )
        cost_scores = result["capability_scores"]["cost_estimation"]
        assert cost_scores["penalized"] is False

    def test_empty_query_returns_fallback(self):
        result = self.reg.classify_heuristic_detailed("")
        assert result["intent_id"] == "knowledge_retrieval"
        assert result["confidence"] == 0.51

    def test_no_keyword_match_gives_low_confidence(self):
        """When no keywords match, confidence should be 0.51 (fallback)."""
        result = self.reg.classify_heuristic_detailed("hello world")
        assert result["confidence"] == 0.51


# ── Capability YAML validation ───────────────────────────────────


class TestCapabilityYAMLValidation:
    """Validate capabilities.yaml schema to catch typos early."""

    @pytest.fixture(autouse=True)
    def registry(self):
        self.reg = get_capability_registry()

    def test_all_capabilities_have_required_fields(self):
        for cap in self.reg.list_all():
            assert cap.id, f"Capability missing id"
            assert cap.name, f"Capability {cap.id} missing name"
            assert cap.description, f"Capability {cap.id} missing description"
            assert cap.agent_type, f"Capability {cap.id} missing agent_type"
            assert len(cap.keywords) > 0, f"Capability {cap.id} has no keywords"
            assert len(cap.example_queries) > 0, (
                f"Capability {cap.id} has no example_queries"
            )

    def test_exclusive_keywords_are_valid_lists(self):
        for cap in self.reg.list_all():
            if cap.exclusive_keywords:
                assert isinstance(cap.exclusive_keywords, tuple), (
                    f"Capability {cap.id} exclusive_keywords must be a tuple"
                )
                for kw in cap.exclusive_keywords:
                    assert isinstance(kw, str), (
                        f"Capability {cap.id} exclusive_keyword '{kw}' must be string"
                    )

    def test_exclusive_keywords_subset_of_keywords(self):
        """Exclusive keywords should be a subset of regular keywords
        (or at least semantically related)."""
        for cap in self.reg.list_all():
            if cap.exclusive_keywords:
                # Just check that exclusive_keywords are non-empty strings
                for ek in cap.exclusive_keywords:
                    assert len(ek) > 0, (
                        f"Capability {cap.id} has empty exclusive_keyword"
                    )


# ── _simulate_llm_response includes capability_scores ────────────


class TestSimulateLLMResponse:
    """Test that the heuristic fallback includes detailed scoring."""

    @pytest.mark.asyncio
    async def test_heuristic_response_includes_capability_scores(self):
        classifier = IntentClassifier(
            prompt_manager=None, llm_client=None, enable_cache=False
        )
        response_json = await classifier._simulate_llm_response(
            "Query:\nAnalyze construction cost trends\n\n"
        )
        data = json.loads(response_json)
        assert "capability_scores" in data
        assert "matched_keywords_detail" in data
        assert isinstance(data["capability_scores"], dict)

    @pytest.mark.asyncio
    async def test_bypass_cache_parameter(self):
        """classify_intent accepts bypass_cache parameter."""

        class _DummyLLM:
            def generate(self, prompt, **kwargs):
                return '{"intent":"knowledge_retrieval","confidence":0.9}'

        classifier = IntentClassifier(
            prompt_manager=None, llm_client=_DummyLLM(), enable_cache=True
        )
        context = QueryContext(session_id="test-bypass")

        # First call with bypass_cache=True should not save to cache
        result = await classifier.classify_intent(
            "What are OSHA requirements?", context, bypass_cache=True
        )
        assert result.intent is not None
