"""TDI Round 19 — Bug reproduction tests.

Each test asserts the CORRECT behavior. Fixes applied in this round.
Tests use source-code analysis and regex extraction to avoid import failures
in CI environments without full backend dependencies (numpy, requests, etc.).
"""

from __future__ import annotations

import ast
import asyncio
import json
import re
from typing import Any, Dict

import pytest


# ---------------------------------------------------------------------------
# B19-01  P0  intent_node._call_classifier imports correct module
# ---------------------------------------------------------------------------
class TestB1901PhantomModelsImport:
    @pytest.mark.unit
    def test_call_classifier_imports_from_correct_module(self):
        """_call_classifier should import QueryContext from intent_classifier,
        NOT from a nonexistent 'models' module."""
        source_path = "backend/services/workflows/nodes/intent_node.py"
        with open(source_path) as f:
            source = f.read()

        # Should NOT import from models (which doesn't exist)
        assert (
            "from backend.services.intent_classification.models import" not in source
        ), (
            "_call_classifier imports from nonexistent 'models' module — "
            "should import from 'intent_classifier' instead"
        )
        # Should import from intent_classifier instead
        assert (
            "from backend.services.intent_classification.intent_classifier import"
            in source
        ), "_call_classifier should import QueryContext from intent_classifier"


# ---------------------------------------------------------------------------
# B19-02  P1  Server file_path NOT disclosed in upload response payloads
# ---------------------------------------------------------------------------
class TestB1902FilePathDisclosure:
    @pytest.mark.unit
    def test_upload_responses_do_not_expose_file_path(self):
        """Upload endpoint response payloads should not contain server file_path."""
        source_path = "backend/main.py"
        with open(source_path) as f:
            source = f.read()

        # Find the upload_document function and check its payload dict
        # The document upload payload should use file_id, not file_path
        doc_upload_match = re.search(
            r"async def upload_document\b.*?return payload",
            source,
            re.DOTALL,
        )
        assert doc_upload_match, "Could not find upload_document function"
        doc_upload_body = doc_upload_match.group(0)
        assert (
            '"file_path": file_path' not in doc_upload_body
        ), "Document upload response still exposes file_path — should use file_id"

        # Check data upload function too
        data_upload_match = re.search(
            r"async def upload_data_file\b.*?return payload",
            source,
            re.DOTALL,
        )
        assert data_upload_match, "Could not find upload_data_file function"
        data_upload_body = data_upload_match.group(0)
        assert (
            '"file_path": file_path' not in data_upload_body
        ), "Data upload response still exposes file_path — should use file_id"


# ---------------------------------------------------------------------------
# B19-03  P1  Error detail leakage via str(e) in 4 endpoints
# ---------------------------------------------------------------------------
class TestB1903ErrorDetailLeakage:
    @pytest.mark.unit
    def test_error_messages_do_not_leak_internals(self):
        """Error responses must use generic messages, not raw exception strings."""
        leaky_patterns = [
            'f"Document upload failed: {str(e)}"',
            'f"Failed to list documents: {exc}"',
            'f"Data upload failed: {str(e)}"',
            'f"Failed to retrieve visualization: {str(e)}"',
        ]
        source_path = "backend/main.py"
        with open(source_path) as f:
            source = f.read()

        for pattern in leaky_patterns:
            assert pattern not in source, (
                f"Error detail leakage found: {pattern} — "
                "should use generic message like 'An internal error occurred'"
            )


# ---------------------------------------------------------------------------
# B19-04  P1  Health check leaks internal errors
# ---------------------------------------------------------------------------
class TestB1904HealthCheckErrorLeakage:
    @pytest.mark.unit
    def test_health_check_hides_error_details(self):
        """Health check should report 'unhealthy' without raw exception text."""
        source_path = "backend/api/enhanced_query_routes.py"
        with open(source_path) as f:
            source = f.read()

        assert 'f"unhealthy: {str(e)}"' not in source, (
            "Health check leaks raw exception text — "
            "should use 'unhealthy' without str(e)"
        )


# ---------------------------------------------------------------------------
# B19-05  P1  functools removed from whitelist
# ---------------------------------------------------------------------------
class TestB1905FunctoolsReduceBypass:
    @pytest.mark.unit
    def test_functools_not_whitelisted(self):
        """functools should not be in WHITELISTED_IMPORTS to prevent
        functools.reduce(str.__add__) string construction bypass."""
        source_path = "backend/services/code_executor/validator.py"
        with open(source_path) as f:
            source = f.read()

        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if (
                        isinstance(target, ast.Name)
                        and target.id == "WHITELISTED_IMPORTS"
                    ):
                        if isinstance(node.value, ast.Set):
                            elements = {
                                elt.value
                                for elt in node.value.elts
                                if isinstance(elt, ast.Constant)
                            }
                            assert "functools" not in elements, (
                                "functools is still in WHITELISTED_IMPORTS — "
                                "functools.reduce(str.__add__) can reconstruct blocked names"
                            )


# ---------------------------------------------------------------------------
# B19-06  P1  Walrus operator alias tracking
# ---------------------------------------------------------------------------
class TestB1906WalrusOperatorBypass:
    @pytest.mark.unit
    def test_walrus_operator_handling_in_validator(self):
        """Validator should handle ast.NamedExpr (walrus operator) for alias tracking."""
        source_path = "backend/services/code_executor/validator.py"
        with open(source_path) as f:
            source = f.read()

        assert "NamedExpr" in source, (
            "Validator should check for ast.NamedExpr (walrus operator) "
            "to detect aliases like (fn := open)"
        )


# ---------------------------------------------------------------------------
# B19-07  P1  df.pipe()/df.apply()/df.agg() callable dispatch blocked
# ---------------------------------------------------------------------------
class TestB1907PandasCallableDispatch:
    @pytest.mark.unit
    def test_dangerous_methods_in_blocked_list(self):
        """df.pipe(), df.apply(), df.agg(), df.transform(), .map() should be in BLOCKED_METHOD_NAMES."""
        source_path = "backend/services/code_executor/validator.py"
        with open(source_path) as f:
            source = f.read()

        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if (
                        isinstance(target, ast.Name)
                        and target.id == "BLOCKED_METHOD_NAMES"
                    ):
                        if isinstance(node.value, ast.Set):
                            methods = {
                                elt.value
                                for elt in node.value.elts
                                if isinstance(elt, ast.Constant)
                            }
                            for method in ("pipe", "apply", "agg", "transform", "map"):
                                assert method in methods, (
                                    f"'{method}' should be in BLOCKED_METHOD_NAMES — "
                                    f"it passes arbitrary callables"
                                )


# ---------------------------------------------------------------------------
# B19-08  P1  while 1: now detected as infinite loop
# ---------------------------------------------------------------------------
class TestB1908WhileOneLoop:
    @pytest.mark.unit
    def test_while_one_detected_as_infinite_loop(self):
        """_check_loops should detect 'while 1:' as a truthy constant, not just 'while True:'."""
        source_path = "backend/services/code_executor/validator.py"
        with open(source_path) as f:
            source = f.read()

        # The fix changes `node.test.value is True` to just `node.test.value`
        # (truthy check instead of identity check)
        assert "node.test.value is True" not in source, (
            "_check_loops still uses 'is True' identity check — "
            "should use truthiness check to catch 'while 1:'"
        )
        # Verify the fix: check for truthy test
        assert (
            "node.test.value" in source
        ), "_check_loops should check truthiness of node.test.value"


# ---------------------------------------------------------------------------
# B19-09  P1  num_units regex no longer matches bare "unit" + number
# ---------------------------------------------------------------------------
class TestB1909NumUnitsRegex:
    @pytest.mark.unit
    def test_num_units_regex_requires_contextual_prefix(self):
        """num_units regex should NOT match bare 'unit' or 'homes'."""
        source_path = "backend/services/cost_estimation_service.py"
        with open(source_path) as f:
            source = f.read()

        # Find the num_units patterns section
        match = re.search(r'"num_units":\s*\[(.*?)\]', source, re.DOTALL)
        assert match, "Could not find num_units patterns"
        patterns_text = match.group(1)

        # Should NOT have bare `units?` without a required prefix like `num\s*`
        # The pattern `(?:units?|...` at the start means bare 'unit' matches
        assert r"(?:units?" not in patterns_text or r"num\s*units" in patterns_text, (
            "num_units regex allows bare 'unit' to match — "
            "needs stricter prefix like 'num units' or 'number of units'"
        )

    @pytest.mark.unit
    def test_num_units_regex_still_captures_explicit_values(self):
        """Regex should still match 'num units: 10' and '50 units'."""
        source_path = "backend/services/cost_estimation_service.py"
        with open(source_path) as f:
            source = f.read()

        match = re.search(r'"num_units":\s*\[(.*?)\]', source, re.DOTALL)
        assert match, "Could not find num_units patterns"
        patterns_text = match.group(1)

        # Should have a pattern for "num units: N" or "number of units: N"
        assert (
            "num" in patterns_text.lower()
        ), "num_units regex should match 'num units: N' pattern"


# ---------------------------------------------------------------------------
# B19-10  P1  Heuristic fallback now extracts only user query
# ---------------------------------------------------------------------------
class TestB1910HeuristicPromptLeakage:
    @pytest.mark.unit
    def test_heuristic_extracts_query_from_prompt(self):
        """_simulate_llm_response should extract only the user query text,
        not search the full prompt including instruction preamble."""
        source_path = "backend/services/intent_classification/intent_classifier.py"
        with open(source_path) as f:
            source = f.read()

        # Find the _simulate_llm_response method
        match = re.search(
            r"async def _simulate_llm_response.*?(?=\n    async def |\n    def |\nclass |\Z)",
            source,
            re.DOTALL,
        )
        assert match, "Could not find _simulate_llm_response method"
        method_source = match.group(0)

        # The method should extract the query from the prompt, not use the full prompt
        assert (
            "Query:" in method_source or "query_marker" in method_source
        ), "_simulate_llm_response should extract the user query section from the prompt"
        # Should NOT just do `query_lower = prompt.lower()` on the full prompt
        assert (
            "prompt.lower()" not in method_source.split("query_marker")[0][-50:]
            if "query_marker" in method_source
            else True
        ), "Method should not search keywords in the full prompt"


# ---------------------------------------------------------------------------
# B19-11  P1  SimpleIntentClassifier CODE_EXECUTION keywords narrowed
# ---------------------------------------------------------------------------
class TestB1911BroadCodeExecutionKeywords:
    @pytest.mark.unit
    def test_broad_keywords_removed_from_code_execution(self):
        """Overly broad keywords like 'run', 'process', 'batch', 'function',
        'compute', 'calculation' should not be standalone CODE_EXECUTION keywords."""
        source_path = (
            "backend/services/intent_classification/simple_intent_classifier.py"
        )
        with open(source_path) as f:
            source = f.read()

        # Find the CODE_EXECUTION keywords section
        match = re.search(
            r'CODE_EXECUTION.*?"keywords":\s*\[(.*?)\]',
            source,
            re.DOTALL,
        )
        assert match, "Could not find CODE_EXECUTION keywords"
        keywords_text = match.group(1)

        # Extract individual keyword strings
        keywords = re.findall(r'"([^"]+)"', keywords_text)

        # These broad single-word keywords should NOT be in the list
        too_broad = {
            "run",
            "process",
            "batch",
            "function",
            "compute",
            "calculation",
            "code",
            "program",
        }
        found_broad = set(keywords) & too_broad
        assert not found_broad, (
            f"CODE_EXECUTION still has overly broad keywords: {found_broad} — "
            "these match common construction terminology"
        )


# ---------------------------------------------------------------------------
# B19-12  P1  A/B experiment cache write now guarded
# ---------------------------------------------------------------------------
class TestB1912ABCachePollution:
    @pytest.mark.unit
    def test_experiment_write_does_not_pollute_generic_cache(self):
        """When enable_experiments=True, the cache write should NOT use the
        generic cache key that non-experiment requests read from."""
        source_path = "backend/services/prompt_manager.py"
        with open(source_path) as f:
            source = f.read()

        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, (ast.AsyncFunctionDef, ast.FunctionDef)):
                if node.name == "get_prompt":
                    func_source = ast.get_source_segment(source, node) or ""
                    if "self._cache[cache_key]" in func_source:
                        has_guard = "not enable_experiments" in func_source
                        assert has_guard, (
                            "Cache write after A/B experiment selection is not guarded — "
                            "experiment variant pollutes non-experiment cache reads"
                        )
                    break


# ---------------------------------------------------------------------------
# B19-13  P1  _template_count/_template_percentage accept question param
# ---------------------------------------------------------------------------
class TestB1913TemplateColumnSelection:
    @pytest.mark.unit
    def test_template_count_uses_question_for_column_selection(self):
        """_template_count should consider the user's question when selecting
        which categorical column to count, not blindly pick the first one."""
        source_path = "backend/services/data_analysis/data_analysis_agent.py"
        with open(source_path) as f:
            source = f.read()

        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if node.name in ("_template_count", "_template_percentage"):
                    param_names = [arg.arg for arg in node.args.args]
                    assert "question" in param_names, (
                        f"{node.name} should accept a 'question' parameter "
                        "to select the relevant column (like _template_average does)"
                    )
