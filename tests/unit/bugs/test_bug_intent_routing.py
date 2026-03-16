"""BUG-4 (High): DATA_ANALYSIS priority=2 unfairly doubles scores vs CODE_EXECUTION priority=1.

The `SimpleIntentClassifier._build_keyword_rules` assigns `priority=2` to
DATA_ANALYSIS and `priority=1` to CODE_EXECUTION.  In `_calculate_intent_score`,
the total score is multiplied by priority.  Combined with shared keywords
like "compute", "calculation", "process", "batch", this causes queries that
are clearly about code execution to be mis-routed to data analysis.

This test asserts that code-execution-specific queries are correctly classified
as CODE_EXECUTION, not DATA_ANALYSIS.  It should FAIL until the priority
imbalance is fixed.
"""

from __future__ import annotations

import pytest


@pytest.mark.unit
class TestBug4IntentPriorityImbalance:
    def test_run_python_script_should_be_code_execution(self):
        """'run a python script to compute statistics' should route to code_execution."""
        from backend.services.intent_classification.simple_intent_classifier import (
            IntentType,
            SimpleIntentClassifier,
        )

        classifier = SimpleIntentClassifier()
        result = classifier.classify_intent("run a python script to compute statistics")

        assert result.intent == IntentType.CODE_EXECUTION, (
            f"BUG-4: 'run a python script to compute statistics' was classified as "
            f"{result.intent.value} (confidence={result.confidence:.2f}) instead of "
            f"code_execution. The priority=2 on DATA_ANALYSIS unfairly doubles its "
            f"score for shared keywords like 'compute'."
        )

    def test_execute_batch_calculation_should_be_code_execution(self):
        """'execute a batch calculation process' should route to code_execution."""
        from backend.services.intent_classification.simple_intent_classifier import (
            IntentType,
            SimpleIntentClassifier,
        )

        classifier = SimpleIntentClassifier()
        result = classifier.classify_intent("execute a batch calculation process")

        assert result.intent == IntentType.CODE_EXECUTION, (
            f"BUG-4: 'execute a batch calculation process' was classified as "
            f"{result.intent.value} instead of code_execution. All of 'batch', "
            f"'calculation', 'process' are shared keywords, but DATA_ANALYSIS "
            f"wins due to priority=2 multiplier."
        )

    def test_analyze_dataset_should_still_be_data_analysis(self):
        """'analyze this CSV dataset' should remain data_analysis — priority
        shouldn't break legitimate data analysis classification."""
        from backend.services.intent_classification.simple_intent_classifier import (
            IntentType,
            SimpleIntentClassifier,
        )

        classifier = SimpleIntentClassifier()
        result = classifier.classify_intent(
            "analyze this CSV dataset and show statistics"
        )

        assert result.intent == IntentType.DATA_ANALYSIS, (
            f"Regression check: 'analyze this CSV dataset' should remain "
            f"data_analysis, but got {result.intent.value}"
        )
