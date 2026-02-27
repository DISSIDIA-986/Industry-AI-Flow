"""
TDI Round 13 — Reproduction tests for 21 bugs (4 P0, 17 P1).

Categories: RAG Infrastructure, RAG Quality, Security, LLM Dispatch,
Cost Estimation, Workflow, Data Analysis.
"""

import ast
import math
import os
import re
import threading
import time

import pytest

# ─── Paths ───────────────────────────────────────────────────────────────────

_BACKEND = os.path.normpath(
    os.path.join(os.path.dirname(__file__), "..", "..", "..", "backend")
)

_MEMORY_STORE_PATH = os.path.join(_BACKEND, "services", "memory", "store.py")
_RAG_ENGINE_PATH = os.path.join(_BACKEND, "services", "rag_engine.py")
_MEMORY_MANAGER_PATH = os.path.join(_BACKEND, "services", "memory", "manager.py")
_HYBRID_SEARCH_PATH = os.path.join(
    _BACKEND, "services", "retrieval", "hybrid_search.py"
)
_INTENT_WORKFLOW_PATH = os.path.join(
    _BACKEND, "services", "intent_classification", "intent_workflow.py"
)
_RERANKER_PATH = os.path.join(_BACKEND, "services", "retrieval", "reranker.py")
_VALIDATOR_PATH = os.path.join(_BACKEND, "services", "code_executor", "validator.py")
_DATA_ANALYSIS_PATH = os.path.join(
    _BACKEND, "services", "data_analysis", "data_analysis_agent.py"
)
_DISPATCH_PATH = os.path.join(
    _BACKEND, "services", "llm_integration", "dispatch_service.py"
)
_COST_EST_PATH = os.path.join(_BACKEND, "services", "cost_estimation_service.py")
_COST_TRACKER_PATH = os.path.join(
    _BACKEND, "services", "llm_integration", "cost_tracker.py"
)
_COST_EST_ROUTES_PATH = os.path.join(_BACKEND, "api", "cost_estimation_routes.py")
_GRAPH_PATH = os.path.join(_BACKEND, "services", "workflows", "graph.py")
_GROUNDEDNESS_PATH = os.path.join(
    _BACKEND, "services", "workflows", "nodes", "groundedness_node.py"
)
_CODE_EXEC_NODE_PATH = os.path.join(
    _BACKEND, "services", "workflows", "nodes", "code_exec_node.py"
)


def _read(path: str) -> str:
    with open(path) as f:
        return f.read()


# ═══════════════════════════════════════════════════════════════════════════════
# RAG INFRASTRUCTURE
# ═══════════════════════════════════════════════════════════════════════════════


class TestR13_RAG01_MemoryStoreIVFFlatProbes:
    """P0: LongTermMemoryStore.search_memories never sets IVFFlat probes."""

    def test_search_memories_sets_probes(self):
        source = _read(_MEMORY_STORE_PATH)
        # The search_memories method must call SET ivfflat.probes before the
        # ORDER BY embedding <=> query.  Without it, pgvector defaults to
        # probes=1 which examines only 1/N of the IVFFlat lists.
        assert "ivfflat.probes" in source, (
            "search_memories must SET ivfflat.probes before vector similarity query"
        )


class TestR13_RAG02_MemorySessionsUnbounded:
    """P1: _memory_sessions dict has no eviction — unbounded memory leak."""

    def test_memory_sessions_has_eviction_or_max_size(self):
        source = _read(_RAG_ENGINE_PATH)
        # The code should contain some form of session eviction or max-size
        # enforcement.  Acceptable patterns: LRU, TTL, max_sessions, popitem,
        # OrderedDict with maxlen.
        has_eviction = any(
            kw in source
            for kw in ["max_sessions", "lru", "popitem", "OrderedDict", "_evict"]
        )
        assert has_eviction, (
            "_memory_sessions dict must have an eviction policy to prevent "
            "unbounded memory growth on long-running servers"
        )


class TestR13_RAG03_MemoryInteractionRace:
    """P1: _record_memory_interaction mutates session without lock."""

    def test_record_interaction_holds_lock(self):
        source = _read(_RAG_ENGINE_PATH)
        # Find the _record_memory_interaction method body and verify it
        # acquires _memory_lock before mutating interaction_history.
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name == "_record_memory_interaction":
                # Check that _memory_lock is used within this method
                body_src = ast.get_source_segment(source, node)
                assert body_src is not None
                assert "_memory_lock" in body_src, (
                    "_record_memory_interaction must acquire _memory_lock "
                    "before mutating session.interaction_history"
                )
                return
        pytest.fail("Could not find _record_memory_interaction method")


class TestR13_RAG04_SummaryWrittenToSnapshot:
    """P1: Summary and long-term refs written to snapshot, never propagated back."""

    def test_summary_propagated_back_to_live_session(self):
        source = _read(_RAG_ENGINE_PATH)
        # After process_interaction(session_snapshot, record), the code must
        # copy summary_memory back to the live session. The propagation can
        # be in the method body or an inner async function.
        # Check that within _record_memory_interaction, there's code that
        # writes back snapshot.summary_memory to live_session or session.
        assert "summary_memory = session_snapshot.summary_memory" in source or \
            "summary_memory = snapshot.summary_memory" in source, (
            "After process_interaction(), summary_memory must be "
            "propagated from snapshot back to the live session"
        )


# ═══════════════════════════════════════════════════════════════════════════════
# RAG QUALITY
# ═══════════════════════════════════════════════════════════════════════════════


class TestR13_RAG05_ScoreNormMaxOnly:
    """P1: Hybrid search uses max-only normalization, not min-max."""

    def test_single_weak_result_not_score_one(self):
        source = _read(_HYBRID_SEARCH_PATH)
        # The normalization block should use min-max scaling or preserve raw
        # scores.  Currently it's just score/max_score which gives 1.0 for
        # any single result regardless of how weak the match is.
        # Check for min_score usage in normalization
        norm_section = source[source.find("Normalize fusion scores") :]
        assert "min_score" in norm_section or "raw_score" in norm_section, (
            "Score normalization should use min-max scaling or preserve raw "
            "scores so single weak results don't appear as 100% relevant"
        )


class TestR13_RAG06_SourceDedupDropsChunks:
    """P1: Source dedup at document level drops distinct chunks from same doc."""

    def test_dedup_key_includes_chunk_identity(self):
        source = _read(_INTENT_WORKFLOW_PATH)
        # Find the source_key construction near line 1272
        if "source_key" not in source:
            pytest.skip("source_key dedup not found in intent_workflow.py")
        # The dedup key must include chunk-level identity, not just doc_id:doc_name
        dedup_match = re.search(r'source_key\s*=\s*f?"([^"]*)"', source)
        if dedup_match:
            key_pattern = dedup_match.group(1)
            assert "chunk" in key_pattern.lower() or "content" in key_pattern.lower(), (
                f"source_key '{key_pattern}' deduplicates at document level, "
                "which drops distinct chunks from the same document"
            )
        else:
            pytest.fail("Could not parse source_key pattern")


class TestR13_RAG07_RerankerTruncation:
    """P1: Reranker 512-token window silently truncates long chunks."""

    def test_reranker_warns_or_handles_long_input(self):
        source = _read(_RERANKER_PATH)
        # The reranker should either: log a warning on truncation, use a
        # sliding window, or document the limitation.  Currently it silently
        # truncates via max_length=512 with no indication.
        # "truncation=True" in tokenizer call doesn't count — that ENABLES
        # silent truncation rather than warning about it.
        has_truncation_handling = any(
            kw in source
            for kw in ["sliding_window", "max_chunk_length", "truncation_warning",
                        "chunk too long", "truncated"]
        )
        assert has_truncation_handling, (
            "Reranker should warn when truncating input pairs or use a "
            "sliding-window approach for long chunks"
        )


# ═══════════════════════════════════════════════════════════════════════════════
# SECURITY
# ═══════════════════════════════════════════════════════════════════════════════


class TestR13_SEC01_GetattributeBypass:
    """P0: Sandbox escape via object.__getattribute__ + chr() string construction."""

    def test_getattribute_bypass_blocked(self):
        from backend.services.code_executor.validator import validate_code

        # This exploit uses __getattribute__ (not blocked) + chr() to avoid
        # literal dunder strings in source code.
        exploit = (
            "import functools\n"
            "ga = object.__getattribute__\n"
            "a = '__'\n"
            "b = 'buil'\n"
            "c = 'tins'\n"
            "name = a + b + c + a\n"
        )
        result = validate_code(exploit, strict_mode=False)
        assert not result.is_valid, (
            "object.__getattribute__ must be blocked — it enables bypass of "
            "all attribute-based security checks"
        )


class TestR13_SEC02_DataAnalysisNoValidation:
    """P0: DataAnalysisAgent executes LLM-generated code without validate_code()."""

    def test_analyze_query_calls_validate_code(self):
        source = _read(_DATA_ANALYSIS_PATH)
        # Find the analyze_query method and check it calls validate_code
        # before passing code to any executor
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == "analyze_query":
                body_src = ast.get_source_segment(source, node)
                assert body_src is not None
                assert "validate_code" in body_src, (
                    "analyze_query must call validate_code() on LLM-generated "
                    "code before passing it to any executor"
                )
                return
        pytest.fail("Could not find analyze_query method")


class TestR13_SEC03_HardcodedAdminKey:
    """P1: Hardcoded admin key 'capstone-admin-2026' in cost estimation routes."""

    def test_admin_key_not_hardcoded(self):
        source = _read(_COST_EST_ROUTES_PATH)
        assert "capstone-admin-2026" not in source, (
            "Admin key must not be hardcoded in source code — use environment "
            "variable with no fallback default"
        )


class TestR13_SEC04_MissingDunderBlocks:
    """P1: Validator missing critical dunder attributes in DANGEROUS_PATTERNS."""

    def test_critical_dunders_blocked(self):
        from backend.services.code_executor.validator import validate_code

        critical_dunders = [
            "x = object.__mro__",
            "x = int.__bases__",
            "x = print.__init__",
            "x = str.__dict__",
        ]
        for code in critical_dunders:
            result = validate_code(code, strict_mode=False)
            assert not result.is_valid, (
                f"Code '{code}' should be blocked — these dunder attributes "
                "enable class hierarchy traversal for sandbox escape"
            )


# ═══════════════════════════════════════════════════════════════════════════════
# LLM DISPATCH
# ═══════════════════════════════════════════════════════════════════════════════


class TestR13_DSP01_TruncatePromptEmpty:
    """P0: _truncate_prompt returns empty string when max_tokens >= context_window."""

    def test_truncate_prompt_preserves_content(self):
        source = _read(_DISPATCH_PATH)
        # We can test this by checking the logic in source or by importing
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name == "_truncate_prompt":
                body_src = ast.get_source_segment(source, node)
                assert body_src is not None
                # Must guard against max_tokens >= context_window
                assert "max_input_chars" in body_src
                # Check that there's a guard for <= 0
                assert "<= 0" in body_src or "< 0" in body_src or "max(" in body_src.split("max_input_chars")[1], (
                    "_truncate_prompt must guard against max_input_chars <= 0 "
                    "when max_tokens >= context_window"
                )
                return
        pytest.fail("Could not find _truncate_prompt method")


class TestR13_DSP02_FalseHighConfidence:
    """P1: _estimate_confidence gives high scores to long but wrong output."""

    def test_long_generic_text_not_high_confidence(self):
        source = _read(_DISPATCH_PATH)
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name == "_estimate_confidence":
                body_src = ast.get_source_segment(source, node)
                assert body_src is not None
                # Must have content quality checks beyond length and hedging
                has_quality_check = any(
                    kw in body_src.lower()
                    for kw in ["relevance", "semantic", "domain", "factual", "citation"]
                )
                assert has_quality_check, (
                    "_estimate_confidence must assess content quality, not just "
                    "length and hedging phrases — currently any 300+ char "
                    "response gets >= 0.75 confidence"
                )
                return
        pytest.fail("Could not find _estimate_confidence method")


class TestR13_DSP03_HybridAutoRerunsLocal:
    """P1: hybrid_auto re-runs already-rejected local when cloud is blocked."""

    def test_cloud_blocked_returns_previous_local_not_rerun(self):
        source = _read(_DISPATCH_PATH)
        # When cloud is blocked in hybrid_auto, the code should return the
        # previous local result (with low-confidence warning), not re-run it.
        # Count how many times _run_local appears in _run_cloud
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name == "_run_cloud":
                body_src = ast.get_source_segment(source, node)
                assert body_src is not None
                run_local_count = body_src.count("_run_local")
                assert run_local_count == 0, (
                    f"_run_cloud calls _run_local {run_local_count} times — "
                    "when cloud is blocked, should return previously-computed "
                    "local result, not re-execute it"
                )
                return
        pytest.fail("Could not find _run_cloud method")


class TestR13_DSP04_SingletonNoLock:
    """P1: get_dispatch_service() has no thread-safety."""

    def test_dispatch_service_singleton_thread_safe(self):
        source = _read(_DISPATCH_PATH)
        # Find get_dispatch_service and verify it uses a lock
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name == "get_dispatch_service":
                body_src = ast.get_source_segment(source, node)
                assert body_src is not None
                has_lock = any(
                    kw in body_src for kw in ["Lock", "lock", "threading"]
                )
                assert has_lock, (
                    "get_dispatch_service() must use a threading.Lock for "
                    "double-checked locking — concurrent startup creates "
                    "duplicate instances with split rate-limit state"
                )
                return
        pytest.fail("Could not find get_dispatch_service function")


# ═══════════════════════════════════════════════════════════════════════════════
# COST ESTIMATION
# ═══════════════════════════════════════════════════════════════════════════════


class TestR13_CST01_SingleDigitDuration:
    """P1: planned_duration_weeks regex requires 2+ digits — misses single digit."""

    def test_single_digit_duration_captured(self):
        source = _read(_COST_EST_PATH)
        # Find the planned_duration_weeks regex patterns — look for the dict
        # entry that maps to a list of regex patterns (contains r"...")
        lines = source.split("\n")
        pattern_lines = []
        in_duration = False
        for line in lines:
            if '"planned_duration_weeks": [' in line or "'planned_duration_weeks': [" in line:
                in_duration = True
                continue
            if in_duration:
                stripped = line.strip()
                if stripped.startswith("]"):
                    break
                if "r\"" in stripped or "r'" in stripped:
                    match = re.search(r'r["\'](.+?)["\']', stripped)
                    if match:
                        pattern_lines.append(match.group(1))

        assert pattern_lines, "No regex patterns found for planned_duration_weeks"

        # Test that single-digit values (1-9) match at least one pattern
        test_strings = [
            "duration 8 weeks",
            "planned duration 4",
            "duration 6",
        ]
        for test in test_strings:
            matched = False
            for pattern in pattern_lines:
                if re.search(pattern, test, re.IGNORECASE):
                    matched = True
                    break
            assert matched, (
                f"'{test}' does not match any planned_duration_weeks pattern — "
                "single-digit durations are common for renovation projects"
            )


class TestR13_CST02_BudgetIgnoresCurrentCost:
    """P1: evaluate_budget never receives additional_cost_usd from caller."""

    def test_budget_eval_receives_estimated_cost(self):
        source = _read(_DISPATCH_PATH)
        # Find calls to evaluate_budget and verify they pass additional_cost_usd
        eval_calls = re.findall(r"evaluate_budget\([^)]*\)", source)
        assert eval_calls, "No evaluate_budget calls found"
        for call in eval_calls:
            assert "additional_cost" in call, (
                f"evaluate_budget call '{call}' does not pass "
                "additional_cost_usd — budget enforcement checks only past "
                "spend without accounting for current request cost"
            )


# ═══════════════════════════════════════════════════════════════════════════════
# WORKFLOW PIPELINE
# ═══════════════════════════════════════════════════════════════════════════════


class TestR13_WF01_GroundednessBeforeResponse:
    """P1: Groundedness node runs before response is generated — always 0.0."""

    def test_groundedness_after_response_in_pipeline(self):
        source = _read(_GRAPH_PATH)
        tree = ast.parse(source)
        # Find the pipeline list and check ordering
        pipeline_order = []
        for node in ast.walk(tree):
            if isinstance(node, ast.List):
                for elt in node.elts:
                    if isinstance(elt, ast.Tuple) and len(elt.elts) >= 1:
                        first = elt.elts[0]
                        if isinstance(first, ast.Constant) and isinstance(first.value, str):
                            pipeline_order.append(first.value)
        if not pipeline_order:
            pytest.fail("Could not extract pipeline order from graph.py")

        if "groundedness_node" in pipeline_order and "response_node" in pipeline_order:
            g_idx = pipeline_order.index("groundedness_node")
            r_idx = pipeline_order.index("response_node")
            assert g_idx > r_idx, (
                f"groundedness_node is at position {g_idx} but response_node "
                f"is at position {r_idx} — groundedness must come AFTER "
                "response generation to have an answer to score"
            )
        else:
            pytest.skip("groundedness_node or response_node not in pipeline")


class TestR13_WF02_CodeToExecuteNeverPopulated:
    """P1: code_to_execute is never written by any pipeline node."""

    def test_code_to_execute_populated_somewhere(self):
        # Scan all node files for any code that sets code_to_execute
        nodes_dir = os.path.join(_BACKEND, "services", "workflows", "nodes")
        found_write = False
        for fname in os.listdir(nodes_dir):
            if not fname.endswith(".py"):
                continue
            source = _read(os.path.join(nodes_dir, fname))
            # Look for assignments to code_to_execute (not just reads)
            if re.search(r'["\'"]code_to_execute["\'"]\s*\]?\s*=', source):
                found_write = True
                break
        assert found_write, (
            "No pipeline node writes metadata['code_to_execute'] — "
            "code_exec_node always falls back to dummy 'print(...)' statement"
        )


class TestR13_WF03_DirectResponseNodeCall:
    """P1: Direct response_node call at end of pipeline bypasses _run_node."""

    def test_final_response_node_uses_run_node(self):
        source = _read(_GRAPH_PATH)
        # Find the direct response_node call after the pipeline loop
        # It should use _run_node, not call response_node directly
        lines = source.split("\n")
        for i, line in enumerate(lines):
            stripped = line.strip()
            if "await response_node(" in stripped and "_run_node" not in stripped:
                # Verify this is the post-loop fallback, not inside the loop
                assert False, (
                    f"Line {i+1}: direct 'await response_node(state, services)' "
                    "call bypasses _run_node error handling and latency tracking"
                )


# ═══════════════════════════════════════════════════════════════════════════════
# DATA ANALYSIS
# ═══════════════════════════════════════════════════════════════════════════════


class TestR13_DA01_SafeFloatInfinity:
    """P1: _safe_float does not guard against Infinity — JSON crash."""

    def test_safe_float_rejects_infinity(self):
        source = _read(_DATA_ANALYSIS_PATH)
        # Find _safe_float function and check it handles infinity
        if "_safe_float" not in source:
            pytest.skip("_safe_float not found in data_analysis_agent.py")
        # Check for infinity handling in the function body
        func_start = source.find("def _safe_float")
        # Find end of function (next def or dedented line)
        func_body = source[func_start:]
        lines = func_body.split("\n")
        func_lines = [lines[0]]
        for line in lines[1:]:
            if line and not line[0].isspace() and line.strip():
                break
            func_lines.append(line)
        func_text = "\n".join(func_lines)
        # Must explicitly check for infinity — NaN check (f != f) does NOT
        # catch inf.  Need math.isfinite, math.isinf, or explicit comparison.
        has_inf_check = any(
            kw in func_text
            for kw in ["isfinite", "isinf", "== float("]
        )
        assert has_inf_check, (
            "_safe_float must guard against float('inf') and float('-inf') — "
            "these values break json.dumps() with ValueError"
        )
