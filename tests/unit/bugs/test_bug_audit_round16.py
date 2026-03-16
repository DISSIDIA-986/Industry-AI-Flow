"""TDI Round 16 — Bug reproduction tests.

Covers 19 P0/P1 bugs found across 4 parallel audit agents (RAG, Cost/Intent/Dispatch,
Security, Workflow/Async/DataAnalysis).

Tests use source inspection where imports fail (Python 3.14 venv missing deps).
"""

import ast
import re

import pytest

# ---------------------------------------------------------------------------
# Helper: import with fallback to source-text validation
# ---------------------------------------------------------------------------


def _import_or_skip(module_path, name):
    """Import a name from a module or skip the test if import fails."""
    try:
        import importlib

        mod = importlib.import_module(module_path)
        return getattr(mod, name)
    except (ImportError, ModuleNotFoundError) as e:
        pytest.skip(f"Cannot import {module_path}: {e}")


def _import_validator():
    """Import CodeValidator, bypassing the code_executor package __init__."""
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "validator", "backend/services/code_executor/validator.py"
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.CodeValidator


# ---------------------------------------------------------------------------
# Security — Code Validator
# ---------------------------------------------------------------------------


class TestCodeValidatorRound16:
    """Code validator security bypass tests."""

    def _get_validator(self):
        cls = _import_validator()
        return cls(strict_mode=True)

    def test_pd_eval_sandbox_escape(self):
        """C-R16-01 (P0): pd.eval() can execute arbitrary code because pandas
        is whitelisted but pd.eval(engine='python') evaluates Python expressions."""
        v = self._get_validator()
        code = "import pandas as pd\nresult = pd.eval(\"1+1\", engine='python')"
        result = v.validate(code)
        assert not result.is_valid, (
            "pd.eval() with engine='python' must be blocked — "
            "can execute arbitrary Python expressions"
        )

    def test_df_query_sandbox_escape(self):
        """C-R16-01 variant: DataFrame.query() can execute arbitrary expressions."""
        v = self._get_validator()
        code = (
            "import pandas as pd\n"
            "df = pd.DataFrame({'a': [1, 2, 3]})\n"
            "df.query('a > 1')"
        )
        result = v.validate(code)
        assert not result.is_valid, (
            "df.query() must be blocked — can reference local scope via @ and "
            "execute arbitrary expressions"
        )

    def test_bytes_name_construction(self):
        """C-R16-02 (P1): bytes() can construct blocked function names at runtime."""
        v = self._get_validator()
        code = "name = bytes([101,118,97,108]).decode()\n"
        result = v.validate(code)
        assert not result.is_valid, (
            "bytes() name construction must be blocked — can build 'eval', "
            "'exec', 'open' at runtime"
        )

    def test_bytearray_name_construction(self):
        """C-R16-02 variant: bytearray can also construct blocked names."""
        v = self._get_validator()
        code = "name = bytearray([111,112,101,110]).decode()\n"
        result = v.validate(code)
        assert not result.is_valid, "bytearray() name construction must be blocked"

    def test_np_load_deserialization(self):
        """C-R16-01 variant: np.load() can deserialize pickle by default."""
        v = self._get_validator()
        code = "import numpy as np\ndata = np.load('payload.npy', allow_pickle=True)"
        result = v.validate(code)
        assert not result.is_valid, (
            "np.load(allow_pickle=True) must be blocked — can deserialize "
            "arbitrary pickle payloads"
        )


# ---------------------------------------------------------------------------
# Security — Admin Endpoints & Info Disclosure
# ---------------------------------------------------------------------------


class TestAdminAndDisclosureRound16:
    """Admin bypass and information disclosure tests."""

    def test_switch_model_admin_key_any_value(self):
        """C-R16-03 (P1): switch_model only checks if admin_key is non-empty,
        any string passes the check."""
        source = open("backend/api/enhanced_query_routes.py").read()
        # Find the switch_model function and check it uses hmac.compare_digest
        idx_func = source.find("def switch_model")
        assert idx_func > 0, "switch_model function not found"
        # Get the function body (until the next def or end of file)
        next_def = source.find("\ndef ", idx_func + 1)
        func_body = source[idx_func:next_def] if next_def > 0 else source[idx_func:]
        assert "compare_digest" in func_body, (
            "switch_model must use hmac.compare_digest for admin key validation, "
            "not just 'if not admin_key'"
        )

    def test_intent_routes_no_raw_exception_in_response(self):
        """C-R16-04 (P1): Intent classification routes leak raw exception strings."""
        source = open("backend/api/intent_classification_routes.py").read()
        # Count patterns like f"...{str(e)}" or f"...{e}" in error responses
        leak_patterns = re.findall(
            r'(?:error|detail)\s*=\s*f"[^"]*\{(?:str\(e\)|e)\}[^"]*"', source
        )
        assert len(leak_patterns) == 0, (
            f"Found {len(leak_patterns)} error detail leakage patterns in "
            f"intent_classification_routes.py — exception strings must not be "
            f"returned to clients"
        )

    def test_legacy_executor_no_workspace_path_in_response(self):
        """C-R16-05 (P1): Legacy code executor returns workspace_path to clients."""
        source = open("backend/services/code_executor.py").read()
        occurrences = source.count('"workspace_path"')
        assert occurrences == 0, (
            f"Found {occurrences} occurrences of 'workspace_path' in code_executor.py "
            f"return dicts — internal paths must not be exposed to clients"
        )

    def test_document_version_no_filepath(self):
        """C-R16-06 (P1): DocumentVersionResponse exposes server filesystem paths."""
        source = open("backend/api/document_management_routes.py").read()
        assert "filepath: str" not in source or "filepath: Optional[str]" in source, (
            "DocumentVersionResponse should not expose raw server filepath — "
            "either remove the field or return a safe relative path"
        )


# ---------------------------------------------------------------------------
# RAG Quality — Groundedness Node (source inspection)
# ---------------------------------------------------------------------------


class TestGroundednessNodeRound16:
    """Groundedness node bugs — verified via source inspection."""

    def test_groundedness_node_tokenizer_strips_punctuation(self):
        """A-R16-01 (P1): Groundedness node uses .split() which keeps punctuation
        attached to tokens. Must use regex tokenizer instead."""
        source = open("backend/services/workflows/nodes/groundedness_node.py").read()
        # After fix, the node should NOT use answer.lower().split()
        uses_split = (
            "answer.lower().split()" in source
            or "answer_tokens = set(answer.lower().split())" in source
        )
        uses_regex = (
            "re.findall" in source or "_tokenize" in source or "_TOKEN_RE" in source
        )
        assert not uses_split, (
            "Groundedness node still uses .split() tokenizer which keeps "
            "punctuation attached to tokens"
        )
        assert (
            uses_regex
        ), "Groundedness node should use regex tokenizer that strips punctuation"

    def test_groundedness_node_dict_without_content_key(self):
        """D-R16-04 (P1): Context dict without 'content' key causes TypeError
        when c.get('content', c) returns dict and join() expects strings."""
        source = open("backend/services/workflows/nodes/groundedness_node.py").read()
        # After fix, the fallback should produce a string, not return dict
        # Check for str() wrapping or explicit .get("text", ...) fallback
        has_safe_fallback = (
            "str(c.get(" in source
            or 'c.get("text"' in source
            or "c.get('text'" in source
            or "_extract_context_text" in source
        )
        assert has_safe_fallback, (
            "Groundedness node must safely handle context dicts without 'content' key — "
            "c.get('content', c) returns dict which crashes ' '.join()"
        )


# ---------------------------------------------------------------------------
# RAG Quality — Hybrid Search
# ---------------------------------------------------------------------------


class TestHybridSearchRound16:
    """Hybrid search normalization and tokenizer bugs."""

    def test_min_max_normalization_floor(self):
        """A-R16-03 (P1): Min-max normalization forces worst result to score=0.0,
        misleading downstream components."""
        source = open("backend/services/retrieval/hybrid_search.py").read()
        # After fix, the normalization should scale to [0.1, 1.0] or similar floor
        # Check for a floor offset in the normalization formula
        has_floor = (
            "0.1 +" in source
            or "+ 0.1" in source
            or "0.1 *" in source
            or "normalized * 0.9" in source
            or "floor" in source.lower()
        )
        assert has_floor, (
            "Hybrid search min-max normalization must include a floor > 0 to "
            "prevent misleading 0.0 scores for relevant results"
        )

    def test_bm25_tokenizer_preserves_dotted_standards(self):
        """A-R16-02 (P1): BM25 tokenizer splits dotted construction standard
        numbers like 'A23.1' at the period, losing precision."""
        try:
            from backend.services.retrieval.hybrid_search import HybridRetriever

            class MockVS:
                pass

            retriever = HybridRetriever(MockVS())
            result_tokens = retriever._regex_tokenize("csa a23.1 standard")
            assert "a23.1" in result_tokens, (
                f"BM25 tokenizer should preserve dotted standards like 'a23.1' — "
                f"got tokens: {result_tokens}"
            )
        except ImportError:
            # Fallback: check source
            source = open("backend/services/retrieval/hybrid_search.py").read()
            # The regex should include a dot character class
            assert (
                r"[.-]" in source or r"\." in source
            ), "BM25 regex tokenizer should preserve dotted standard identifiers"


# ---------------------------------------------------------------------------
# RAG Quality — Groundedness Checker
# ---------------------------------------------------------------------------


class TestGroundednessCheckerRound16:
    """Groundedness checker numeric penalty bug."""

    def test_derived_arithmetic_not_penalized(self):
        """A-R16-04 (P1): Numeric mismatch penalty penalizes correct arithmetic
        derived from context (e.g., 30000 sqft * $50/sqft = $1,500,000)."""
        source = open("backend/services/safety/groundedness_checker.py").read()
        # After fix, there should be arithmetic derivation check
        has_derivation = (
            "_is_derivable" in source
            or "derivable" in source
            or "a * b" in source
            or "arithmetic" in source.lower()
        )
        assert has_derivation, (
            "Groundedness checker must tolerate numbers derivable from context "
            "numbers via simple arithmetic (multiplication, addition)"
        )


# ---------------------------------------------------------------------------
# Intent Classification
# ---------------------------------------------------------------------------


class TestIntentClassificationRound16:
    """Intent classification bugs."""

    def test_cost_estimation_agent_mapping(self):
        """B-R16-01 (P1): IntentClassifier._get_agent_type maps COST_ESTIMATION
        to DataAnalysisAgent instead of CostEstimationAgent."""
        source = open(
            "backend/services/intent_classification/intent_classifier.py"
        ).read()
        match = re.search(r'IntentType\.COST_ESTIMATION\s*:\s*"(\w+)"', source)
        assert match, "Could not find COST_ESTIMATION mapping in intent_classifier.py"
        agent_name = match.group(1)
        assert agent_name != "DataAnalysisAgent", (
            f"COST_ESTIMATION maps to '{agent_name}' — should be "
            f"'CostEstimationAgent', not 'DataAnalysisAgent'"
        )

    def test_clarification_prompt_uses_prompt_content(self):
        """B-R16-02 (P1): get_clarification_prompt discards prompt_manager result
        and always returns simulated response."""
        source = open(
            "backend/services/intent_classification/intent_classifier.py"
        ).read()
        idx_get_prompt = source.find("prompt_info, prompt_content")
        idx_simulate = source.find("_simulate_clarification_response", idx_get_prompt)
        between = (
            source[idx_get_prompt:idx_simulate]
            if idx_get_prompt >= 0 and idx_simulate >= 0
            else ""
        )
        uses_prompt_content = (
            "if prompt_content" in between or "return prompt_content" in between
        )
        assert uses_prompt_content, (
            "get_clarification_prompt must check and use prompt_content from "
            "prompt_manager before falling through to _simulate_clarification_response"
        )

    def test_how_much_not_cost_for_general_queries(self):
        """D-R16-05 (P1): 'how much' in heuristic intent matches general
        knowledge queries that aren't about cost estimation."""
        source = open("backend/services/workflows/nodes/intent_node.py").read()
        # After fix, bare "how much" should not be in the cost token list
        # It should be more specific like "how much does it cost"
        has_bare_how_much = (
            '"how much"' in source and '"how much does it cost"' not in source
        )
        assert not has_bare_how_much, (
            "Heuristic intent should not use bare 'how much' as cost estimation "
            "trigger — it matches non-cost queries like 'how much water'"
        )

        # Also check "price" is not bare
        has_bare_price = (
            '"price"' in source
            and '"price estimate"' not in source
            and '"price prediction"' not in source
        )
        assert not has_bare_price, (
            "Heuristic intent should not use bare 'price' as cost estimation "
            "trigger — it matches non-cost queries"
        )


# ---------------------------------------------------------------------------
# Dispatch Service
# ---------------------------------------------------------------------------


class TestDispatchServiceRound16:
    """LLM dispatch service bugs."""

    def test_truncate_prompt_respects_backend_context_window(self):
        """B-R16-03 (P1): _truncate_prompt callers must pass appropriate context
        window for their backend, not rely on hardcoded 4096 default."""
        source = open("backend/services/llm_integration/dispatch_service.py").read()
        cloud_section = source[source.find("def _run_cloud") :]
        truncate_call = re.search(
            r"_truncate_prompt\([^)]*context_window\s*=\s*(\d+)",
            cloud_section,
        )
        assert truncate_call, (
            "_run_cloud must pass context_window to _truncate_prompt — "
            "currently uses hardcoded 4096 default"
        )
        window_value = int(truncate_call.group(1))
        assert (
            window_value > 4096
        ), f"Cloud context_window should be >4096 for cloud LLMs — got {window_value}"


# ---------------------------------------------------------------------------
# Cost Estimation
# ---------------------------------------------------------------------------


class TestCostEstimationRound16:
    """Cost estimation regex bugs."""

    def test_bare_cost_regex_false_match(self):
        """B-R16-04 (P1): Bare 'cost' in estimated_cost_cad regex matches
        non-cost numbers like 'cost overrun 10%' extracting 10 as cost."""
        source = open("backend/services/cost_estimation_service.py").read()
        # Find the estimated_cost_cad regex patterns
        match = re.search(r'"estimated_cost_cad":\s*\[(.*?)\]', source, re.DOTALL)
        assert match, "Could not find estimated_cost_cad patterns"
        patterns_text = match.group(1)
        # Bare "cost" without qualifier should not be present
        # It should require a qualifier like "estimated cost", "project cost", etc.
        has_bare_cost = re.search(r"\|cost\)", patterns_text)
        assert not has_bare_cost, (
            "estimated_cost_cad regex contains bare 'cost' which matches "
            "non-cost contexts like 'cost overrun 10%' extracting 10 as cost"
        )


# ---------------------------------------------------------------------------
# Pipeline — Prompt Manager
# ---------------------------------------------------------------------------


class TestPromptManagerRound16:
    """Prompt manager bugs."""

    def test_jinja2_autoescape_disabled_for_llm_prompts(self):
        """D-R16-01 (P1): Jinja2 autoescape=True HTML-escapes characters like
        <, >, & in prompts sent to LLMs, corrupting the prompt."""
        source = open("backend/services/prompt_manager.py").read()
        match = re.search(r"autoescape\s*=\s*(True|False)", source)
        assert match, "Could not find autoescape setting in prompt_manager.py"
        assert match.group(1) == "False", (
            "Jinja2 autoescape must be False for LLM prompts — HTML escaping "
            "corrupts <, >, & characters in prompts sent to language models"
        )


# ---------------------------------------------------------------------------
# Data Analysis Agent
# ---------------------------------------------------------------------------


class TestDataAnalysisAgentRound16:
    """Data analysis agent bugs."""

    def test_code_extraction_handles_crlf(self):
        """D-R16-02 (P1): Code extraction regex fails on CRLF line endings."""
        crlf_response = "```python\r\nimport pandas as pd\r\nprint('hello')\r\n```"

        source = open("backend/services/data_analysis/data_analysis_agent.py").read()
        pattern_match = re.search(r'code_pattern\s*=\s*r"([^"]+)"', source)
        assert pattern_match, "Could not find code_pattern in data_analysis_agent.py"
        actual_pattern = pattern_match.group(1)
        matches = re.findall(actual_pattern, crlf_response, re.DOTALL)
        assert len(matches) > 0, (
            f"data_analysis_agent code_pattern '{actual_pattern}' fails on "
            f"CRLF line endings from cloud LLMs"
        )

    def test_extract_dataset_info_error_dict_handled(self):
        """D-R16-03 (P1): Error dict from _extract_dataset_info is truthy and
        silently propagated to code generation as if it were valid metadata."""
        error_dict = {"error": "Unsupported data file format."}
        assert bool(error_dict), "Error dict should be truthy (this is the problem)"

        source = open("backend/services/data_analysis/data_analysis_agent.py").read()
        has_error_check = (
            'dataset_metadata.get("error")' in source
            or '"error" in dataset_metadata' in source
            or "dataset_metadata.get('error')" in source
        )
        assert has_error_check, (
            "analyze_query must check for 'error' key in dataset_metadata — "
            "error dicts are truthy and pass 'if not dataset_metadata' check"
        )
