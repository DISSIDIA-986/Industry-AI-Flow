"""
TDI Round 14 (Pipeline) — Reproduction tests for 25 bugs (3 P0, 10 P1, 12 P2).

Focus: Workflow Pipeline, Async/State, Data Analysis, Intent Routing,
Error Propagation, Code Execution.

These bugs are NOVEL — not covered by Round 14's security-focused tests
or any previous round.
"""

import ast
import os
import re

import pytest

# --- Paths ----------------------------------------------------------------

_BACKEND = os.path.normpath(
    os.path.join(os.path.dirname(__file__), "..", "..", "..", "backend")
)

_GRAPH_PATH = os.path.join(_BACKEND, "services", "workflows", "graph.py")
_ORCHESTRATOR_PATH = os.path.join(_BACKEND, "services", "workflows", "orchestrator.py")
_STATE_PATH = os.path.join(_BACKEND, "services", "workflows", "state.py")
_INTENT_NODE_PATH = os.path.join(
    _BACKEND, "services", "workflows", "nodes", "intent_node.py"
)
_SAFETY_NODE_PATH = os.path.join(
    _BACKEND, "services", "workflows", "nodes", "safety_node.py"
)
_RETRIEVAL_NODE_PATH = os.path.join(
    _BACKEND, "services", "workflows", "nodes", "retrieval_node.py"
)
_RERANK_NODE_PATH = os.path.join(
    _BACKEND, "services", "workflows", "nodes", "rerank_node.py"
)
_PROMPT_NODE_PATH = os.path.join(
    _BACKEND, "services", "workflows", "nodes", "prompt_node.py"
)
_ROUTE_NODE_PATH = os.path.join(
    _BACKEND, "services", "workflows", "nodes", "route_node.py"
)
_RESPONSE_NODE_PATH = os.path.join(
    _BACKEND, "services", "workflows", "nodes", "response_node.py"
)
_CODE_EXEC_NODE_PATH = os.path.join(
    _BACKEND, "services", "workflows", "nodes", "code_exec_node.py"
)
_COST_ESTIMATION_NODE_PATH = os.path.join(
    _BACKEND, "services", "workflows", "nodes", "cost_estimation_node.py"
)
_GROUNDEDNESS_NODE_PATH = os.path.join(
    _BACKEND, "services", "workflows", "nodes", "groundedness_node.py"
)
_DATA_ANALYSIS_PATH = os.path.join(
    _BACKEND, "services", "data_analysis", "data_analysis_agent.py"
)
_INTENT_WORKFLOW_PATH = os.path.join(
    _BACKEND, "services", "intent_classification", "intent_workflow.py"
)
_SIMPLE_CLASSIFIER_PATH = os.path.join(
    _BACKEND, "services", "intent_classification", "simple_intent_classifier.py"
)
_ROUTING_DECISION_PATH = os.path.join(_BACKEND, "services", "routing_decision.py")
_WORKFLOW_ROUTES_PATH = os.path.join(_BACKEND, "api", "workflow_query_routes.py")


def _read(path: str) -> str:
    with open(path) as f:
        return f.read()


# =============================================================================
# P0 -- CRITICAL BUGS
# =============================================================================


class TestR14P_P0_01_RetrievalNodeDoubleExecution:
    """P0: retrieval_node calls synchronous retriever TWICE for non-async
    retrievers.

    On line 22, `retriever.retrieve(...)` is called eagerly (synchronously).
    If the result is NOT awaitable, line 27-28 calls `asyncio.to_thread(
    retriever.retrieve, ...)` again.  The first call's result is discarded
    and the retrieval is executed twice -- doubling latency and database load.

    File: backend/services/workflows/nodes/retrieval_node.py:22-29
    """

    def test_sync_retriever_not_called_twice(self):
        source = _read(_RETRIEVAL_NODE_PATH)
        tree = ast.parse(source)

        for node in ast.walk(tree):
            if not (
                isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
                and node.name == "retrieval_node"
            ):
                continue

            body_src = ast.get_source_segment(source, node)
            assert body_src is not None

            # The pattern: eagerly call retrieve(), check if awaitable,
            # and if NOT, call retrieve AGAIN via to_thread.
            has_eager_call = "result = retriever.retrieve(" in body_src
            has_reexec = (
                "asyncio.to_thread" in body_src
                and "retriever.retrieve" in body_src
            )
            if has_eager_call and has_reexec:
                has_guard = "iscoroutinefunction" in body_src or "iscoroutine" in body_src
                assert has_guard, (
                    "retrieval_node calls retriever.retrieve() eagerly on "
                    "line 22, then calls it AGAIN via asyncio.to_thread on "
                    "line 28 when the result is not awaitable.  Synchronous "
                    "retrievers execute twice -- doubling latency."
                )
            return
        pytest.fail("Could not find retrieval_node function")


class TestR14P_P0_02_CostEstimationRoutedToRAGInIntentWorkflow:
    """P0: cost_estimation intent maps to GENERAL_AGENT, which dispatches
    to RAG instead of the cost estimation model.

    In routing_decision.py, _map_intent_to_agent maps "cost_estimation" to
    AgentType.GENERAL_AGENT.  In intent_workflow.py, _dispatch_to_agent
    routes GENERAL_AGENT to _dispatch_rag_query.  Cost estimation queries
    bypass the ML model and get RAG document snippets instead.

    File: backend/services/routing_decision.py:318
    """

    def test_cost_estimation_not_routed_to_general_agent(self):
        source = _read(_ROUTING_DECISION_PATH)
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name == "_map_intent_to_agent":
                body_src = ast.get_source_segment(source, node)
                assert body_src is not None
                match = re.search(
                    r'"cost_estimation"\s*:\s*AgentType\.(\w+)', body_src
                )
                if match:
                    agent = match.group(1)
                    assert agent != "GENERAL_AGENT", (
                        f"cost_estimation maps to {agent} which routes "
                        "to _dispatch_rag_query.  The cost estimation ML "
                        "model is never used in the intent workflow path."
                    )
                return
        pytest.fail("Could not find _map_intent_to_agent method")


class TestR14P_P0_03_ENPlaceholderKeywordsFalsePositive:
    """P0: SimpleIntentClassifier has ~95 'EN' placeholder keywords that
    match any English query containing the substring 'en'.

    The i18n migration replaced Chinese keywords with "EN" markers.  Since
    _calculate_intent_score uses `keyword.lower() in query`, the literal
    string "en" matches as a substring in most English words (e.g., "cement",
    "strength", "environment"), making intent classification unreliable.

    File: backend/services/intent_classification/simple_intent_classifier.py
    """

    def test_no_en_placeholder_keywords(self):
        source = _read(_SIMPLE_CLASSIFIER_PATH)
        # Count lines that are exactly '"EN",' (with optional whitespace)
        en_keyword_lines = len(re.findall(r'^\s+"EN",?\s*$', source, re.MULTILINE))
        assert en_keyword_lines < 5, (
            f"SimpleIntentClassifier contains {en_keyword_lines} 'EN' "
            "placeholder keywords.  Since scoring uses "
            "`keyword.lower() in query`, the string 'en' matches as a "
            "substring in most English words (e.g., 'cement', 'strength'), "
            "causing massive false positives across all intent categories."
        )


# =============================================================================
# P1 -- HIGH-SEVERITY BUGS
# =============================================================================


@pytest.mark.xfail(reason="R14P-P1-01: clarification retry route is dead code — architectural fix deferred")
class TestR14P_P1_01_ClarificationRetryNeverReached:
    """P1: _route_after_clarification never returns 'retry_classification',
    making the retry edge dead code.

    The graph defines a conditional edge from clarification_processing with
    three targets including "retry_classification" -> "intent_classification".
    But _route_after_clarification only returns "await_user_input" or
    "proceed_with_fallback", never "retry_classification".

    File: backend/services/intent_classification/intent_workflow.py:694-700
    """

    def test_retry_classification_route_reachable(self):
        source = _read(_INTENT_WORKFLOW_PATH)
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name == "_route_after_clarification":
                body_src = ast.get_source_segment(source, node)
                assert body_src is not None
                assert "retry_classification" in body_src, (
                    "_route_after_clarification never returns "
                    "'retry_classification', making the clarification -> "
                    "intent reclassification loop unreachable dead code"
                )
                return
        pytest.fail("Could not find _route_after_clarification method")


class TestR14P_P1_02_NoGlobalWorkflowTimeout:
    """P1: No global timeout on workflow execution -- LLM hang freezes request.

    Neither the pipeline (graph.py), orchestrator, nor the workflow route
    handler wrap the workflow execution in asyncio.wait_for().  If any LLM
    call hangs, the entire request hangs indefinitely.

    Files: backend/services/workflows/graph.py,
           backend/api/workflow_query_routes.py
    """

    def test_workflow_has_global_timeout(self):
        graph_source = _read(_GRAPH_PATH)
        routes_source = _read(_WORKFLOW_ROUTES_PATH)
        orchestrator_source = _read(_ORCHESTRATOR_PATH)

        combined = graph_source + routes_source + orchestrator_source
        has_timeout = any(
            kw in combined
            for kw in ["wait_for", "timeout", "TIMEOUT", "deadline"]
        )
        assert has_timeout, (
            "Workflow pipeline has no global timeout.  If the LLM provider "
            "hangs, the request hangs indefinitely.  Wrap run_workflow in "
            "asyncio.wait_for() or add a per-node timeout."
        )


class TestR14P_P1_03_ResponseNodeCallsLLMOnError:
    """P1: response_node dispatches to LLM even when state has error set.

    When the pipeline breaks on error (e.g., safety_node blocks), the
    fallback code at graph.py:93 calls response_node.  If a response_builder
    (dispatch service) is configured, response_node calls it with the error
    state, wasting an LLM call.

    File: backend/services/workflows/nodes/response_node.py:32-39
    """

    def test_response_node_checks_error_before_builder(self):
        source = _read(_RESPONSE_NODE_PATH)
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if not (
                isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
                and node.name == "response_node"
            ):
                continue

            body_src = ast.get_source_segment(source, node)
            assert body_src is not None

            # Find position of builder call and error check
            builder_call_idx = body_src.find("builder(")
            if builder_call_idx == -1:
                return  # No builder call, no issue

            # Check if error is checked before builder call
            # The function checks state.get("response") early but NOT error
            error_check = body_src.find('get("error")')
            if error_check == -1:
                error_check = body_src.find("error")

            if error_check > builder_call_idx or error_check == -1:
                # _build_default_response checks error, but the builder
                # path does not.
                pre_builder = body_src[:builder_call_idx]
                if 'error' not in pre_builder.split('\n')[-5:]:
                    assert False, (
                        "response_node calls builder (LLM dispatch) when "
                        "state has error set.  Should use "
                        "_build_default_response on error paths instead of "
                        "making a wasted LLM call."
                    )
            return
        pytest.fail("Could not find response_node function")


class TestR14P_P1_04_TemplateCodeAlwaysReadCSV:
    """P1: All template code methods hardcode pd.read_csv() -- wrong for .xlsx.

    _template_describe, _template_average, _template_max, _template_min,
    _template_count, and _template_percentage all generate code with
    `pd.read_csv('/workspace/{filename}')`.  When the input file is .xlsx
    or .xls, the generated code crashes at runtime.

    File: backend/services/data_analysis/data_analysis_agent.py:410-541
    """

    def test_template_code_handles_excel_files(self):
        source = _read(_DATA_ANALYSIS_PATH)
        template_methods = [
            "_template_describe",
            "_template_average",
            "_template_max",
            "_template_min",
            "_template_count",
            "_template_percentage",
        ]
        for method_name in template_methods:
            tree = ast.parse(source)
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef) and node.name == method_name:
                    body_src = ast.get_source_segment(source, node)
                    if body_src is None:
                        continue
                    has_excel = (
                        "read_excel" in body_src
                        or "xlsx" in body_src
                        or "endswith" in body_src
                        or "_read_data_code" in body_src
                    )
                    assert has_excel, (
                        f"{method_name} hardcodes pd.read_csv() but "
                        "DataAnalysisAgent accepts .xlsx/.xls files.  "
                        "Generated code will crash with ParserError."
                    )
                    break


class TestR14P_P1_05_DataAnalysisJSONNotHandled:
    """P1: _extract_dataset_info does not handle .json files but
    _resolve_uploaded_file_path accepts them.

    In intent_workflow.py line 1412, allowed_suffixes includes ".json".
    But _extract_dataset_info only handles .csv and .xlsx/.xls.  JSON files
    always get {"error": "Unsupported data file format."}.

    File: backend/services/data_analysis/data_analysis_agent.py:178-191
    """

    def test_extract_dataset_info_handles_json(self):
        source = _read(_DATA_ANALYSIS_PATH)
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name == "_extract_dataset_info":
                body_src = ast.get_source_segment(source, node)
                assert body_src is not None
                # Must actually handle .json files -- not just mention json
                # in a comment.  Look for read_json or a .json extension check.
                has_json_handling = (
                    "read_json" in body_src
                    or '".json"' in body_src
                    or "'.json'" in body_src
                )
                assert has_json_handling, (
                    "_extract_dataset_info does not handle .json files, "
                    "but intent_workflow.py accepts .json in allowed_suffixes.  "
                    "JSON files always fail with 'Unsupported data file format'."
                )
                return
        pytest.fail("Could not find _extract_dataset_info method")


@pytest.mark.xfail(reason="R14P-P1-06: clarification processing is a no-op — architectural fix deferred")
class TestR14P_P1_06_ClarificationProcessingNoOp:
    """P1: _clarification_processing_node is effectively a no-op.

    Both branches (confidence < 0.7 and else) set
    metadata['clarification_handled'] = True and return state unchanged.
    The node does no actual processing -- no reclassification, no query
    update, no external service invocation.

    File: backend/services/intent_classification/intent_workflow.py:504-538
    """

    def test_clarification_processing_has_meaningful_logic(self):
        source = _read(_INTENT_WORKFLOW_PATH)
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if (
                isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
                and node.name == "_clarification_processing_node"
            ):
                body_src = ast.get_source_segment(source, node)
                assert body_src is not None
                has_meaningful = any(
                    kw in body_src
                    for kw in [
                        "classify",
                        "reclassify",
                        "current_query",
                        "intent_classifier",
                        "update_intent",
                    ]
                )
                assert has_meaningful, (
                    "_clarification_processing_node is a no-op: both "
                    "branches set metadata['clarification_handled'] = True "
                    "and return.  No actual processing occurs."
                )
                return
        pytest.fail("Could not find _clarification_processing_node method")


class TestR14P_P1_07_DispatchToAgentDeletesSystemPrompt:
    """P1: _dispatch_to_agent immediately deletes system_prompt, prompt_meta,
    and route_mode arguments.

    The prompt_preparation_node carefully selects and renders a prompt
    template, but _dispatch_to_agent throws it away with
    `del system_prompt, prompt_meta, route_mode`.

    File: backend/services/intent_classification/intent_workflow.py:1524
    """

    def test_dispatch_to_agent_uses_system_prompt(self):
        source = _read(_INTENT_WORKFLOW_PATH)
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if (
                isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
                and node.name == "_dispatch_to_agent"
            ):
                body_src = ast.get_source_segment(source, node)
                assert body_src is not None
                assert "del system_prompt" not in body_src, (
                    "_dispatch_to_agent deletes system_prompt, prompt_meta, "
                    "and route_mode.  The prompt_preparation_node's work "
                    "is entirely wasted."
                )
                return
        pytest.fail("Could not find _dispatch_to_agent method")


@pytest.mark.xfail(reason="R14P-P1-08: continue_workflow metadata overwrite — LangGraph architectural fix deferred")
class TestR14P_P1_08_ContinueWorkflowOverwritesMetadata:
    """P1: continue_workflow creates a fresh metadata dict that overwrites
    the checkpointed metadata from the initial run.

    LangGraph's ainvoke merges state updates with checkpoint state, but
    dicts are replaced entirely (not deep-merged).  The fresh metadata
    dict loses intent results, routing decisions, and all context from
    the initial workflow run.

    File: backend/services/intent_classification/intent_workflow.py:1657-1680
    """

    def test_continue_workflow_preserves_metadata(self):
        source = _read(_INTENT_WORKFLOW_PATH)
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if (
                isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
                and node.name == "continue_workflow"
            ):
                body_src = ast.get_source_segment(source, node)
                assert body_src is not None
                if "metadata={" in body_src or "metadata = {" in body_src:
                    # Check for ACTUAL merge logic, not just the variable
                    # name "state_update" which contains "update"
                    has_merge = any(
                        kw in body_src
                        for kw in [".update(", "merge", "**existing", "get_state"]
                    )
                    assert has_merge, (
                        "continue_workflow creates a fresh metadata dict "
                        "that replaces checkpointed metadata, losing intent "
                        "results and routing decisions from the initial run."
                    )
                return
        pytest.fail("Could not find continue_workflow method")


@pytest.mark.xfail(reason="R14P-P1-09: context_enrichment unconditional edge — LangGraph architectural fix deferred")
class TestR14P_P1_09_ContextEnrichmentErrorNotChecked:
    """P1: Graph has unconditional edge from context_enrichment to
    intent_classification, ignoring errors set by context_enrichment.

    context_enrichment_node can set state['error'] on exception (line 245).
    But the graph edge is unconditional (line 123), so intent_classification
    runs with broken state.

    File: backend/services/intent_classification/intent_workflow.py:122-124
    """

    def test_context_enrichment_error_checked(self):
        source = _read(_INTENT_WORKFLOW_PATH)
        tree = ast.parse(source)
        found_unconditional = False
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                func = node.func
                if isinstance(func, ast.Attribute) and func.attr == "add_edge":
                    if len(node.args) >= 2:
                        a0, a1 = node.args[0], node.args[1]
                        if (
                            isinstance(a0, ast.Constant)
                            and isinstance(a1, ast.Constant)
                            and a0.value == "context_enrichment"
                            and a1.value == "intent_classification"
                        ):
                            found_unconditional = True

        if not found_unconditional:
            return  # Edge is conditional or does not exist

        # Verify context_enrichment_node can set error
        for node in ast.walk(tree):
            if (
                isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
                and node.name == "_context_enrichment_node"
            ):
                body_src = ast.get_source_segment(source, node)
                if body_src and 'state["error"]' in body_src:
                    assert False, (
                        "context_enrichment_node can set state['error'] but "
                        "the graph has an unconditional edge to "
                        "intent_classification.  Errors are silently ignored."
                    )


class TestR14P_P1_10_ShortcutResponseSkipsGroundedness:
    """P1: When shortcut_response is set (cost estimation, etc.), the
    shortcut filter skips groundedness_node without annotating metadata.

    Consumers checking metadata['groundedness_passed'] will get KeyError.

    File: backend/services/workflows/graph.py:81-85
    """

    def test_shortcut_sets_groundedness_metadata(self):
        source = _read(_GRAPH_PATH)
        # Check if the shortcut logic or groundedness_node sets a default
        # status when skipped
        groundedness_src = _read(_GROUNDEDNESS_NODE_PATH)
        graph_pipeline_src = source

        # The issue: when shortcut skips groundedness_node, nothing sets
        # metadata['groundedness_passed'] or metadata['groundedness_score']
        # Check if the pipeline sets defaults for skipped nodes
        has_skip_annotation = any(
            kw in graph_pipeline_src
            for kw in ["groundedness_status", "groundedness_skipped", "groundedness_passed"]
        )
        assert has_skip_annotation, (
            "shortcut_response skips groundedness_node without setting "
            "metadata['groundedness_passed'] or a skip annotation.  "
            "Downstream consumers will get KeyError."
        )


# =============================================================================
# P2 -- MODERATE BUGS
# =============================================================================


class TestR14P_P2_01_ENRegexPatterns:
    """P2: SimpleIntentClassifier has regex patterns containing 'EN' that
    match unintended content when combined with re.IGNORECASE.

    File: backend/services/intent_classification/simple_intent_classifier.py
    """

    def test_no_en_regex_patterns(self):
        source = _read(_SIMPLE_CLASSIFIER_PATH)
        en_patterns = re.findall(r'r"EN[^"]*"', source)
        assert len(en_patterns) == 0, (
            f"Found {len(en_patterns)} regex patterns containing 'EN' "
            "placeholder -- these match unintended English text."
        )


class TestR14P_P2_02_RetrievalRunsForAllIntents:
    """P2: retrieval_node runs unconditionally for all intents including
    cost_estimation and code_execution, wasting time on pgvector queries.

    File: backend/services/workflows/nodes/retrieval_node.py
    """

    def test_retrieval_checks_intent(self):
        source = _read(_RETRIEVAL_NODE_PATH)
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if (
                isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
                and node.name == "retrieval_node"
            ):
                body_src = ast.get_source_segment(source, node)
                assert body_src is not None
                has_intent_check = "intent" in body_src
                assert has_intent_check, (
                    "retrieval_node runs for all intents, wasting time on "
                    "pgvector queries for cost_estimation/code_execution."
                )
                return
        pytest.fail("Could not find retrieval_node function")


class TestR14P_P2_03_RetrievalSearchDoubleCall:
    """P2: Same double-call pattern for the search() fallback path.

    File: backend/services/workflows/nodes/retrieval_node.py:31-37
    """

    def test_sync_search_not_called_twice(self):
        source = _read(_RETRIEVAL_NODE_PATH)
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if (
                isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
                and node.name == "retrieval_node"
            ):
                body_src = ast.get_source_segment(source, node)
                assert body_src is not None
                eager = "result = retriever.search(" in body_src
                reexec = "retriever.search" in body_src and "asyncio.to_thread" in body_src
                if eager and reexec:
                    has_guard = "iscoroutinefunction" in body_src
                    assert has_guard, (
                        "retrieval_node has the same double-call for search(): "
                        "eagerly calls search(), then re-calls via to_thread."
                    )
                return


class TestR14P_P2_04_RunPromptStageNoGuard:
    """P2: run_prompt_stage calls prompt_node directly without checking
    if services.prompt_manager is None.  This sets state['error'] unexpectedly
    for callers.

    File: backend/services/workflows/graph.py:24-26
    """

    def test_run_prompt_stage_guards_prompt_manager(self):
        source = _read(_GRAPH_PATH)
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if (
                isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
                and node.name == "run_prompt_stage"
            ):
                body_src = ast.get_source_segment(source, node)
                assert body_src is not None
                has_guard = "prompt_manager" in body_src and "None" in body_src
                assert has_guard, (
                    "run_prompt_stage calls prompt_node without checking "
                    "services.prompt_manager.  Sets error unexpectedly."
                )
                return
        pytest.fail("Could not find run_prompt_stage function")


@pytest.mark.xfail(reason="R14P-P2-05: module-level singleton — refactor deferred")
class TestR14P_P2_05_SimpleClassifierModuleSingleton:
    """P2: simple_intent_classifier.py creates a module-level singleton
    at import time, before settings are loaded.

    File: backend/services/intent_classification/simple_intent_classifier.py:569
    """

    def test_simple_classifier_lazy_init(self):
        source = _read(_SIMPLE_CLASSIFIER_PATH)
        lines = source.strip().split("\n")
        for line in lines:
            stripped = line.strip()
            if (
                stripped.startswith("simple_intent_classifier = SimpleIntentClassifier(")
                and not line.startswith(" ")
                and not line.startswith("\t")
            ):
                assert False, (
                    "simple_intent_classifier is instantiated at module "
                    "scope.  Should use lazy initialization to avoid "
                    "import-time side effects."
                )


class TestR14P_P2_06_NoPipelineCompletionStatus:
    """P2: run_workflow_pipeline does not set a completion status, so
    consumers cannot tell if the pipeline completed or broke mid-execution.

    File: backend/services/workflows/graph.py
    """

    def test_pipeline_sets_completion_status(self):
        source = _read(_GRAPH_PATH)
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if (
                isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
                and node.name == "run_workflow_pipeline"
            ):
                body_src = ast.get_source_segment(source, node)
                assert body_src is not None
                has_status = any(
                    kw in body_src
                    for kw in ["pipeline_status", "pipeline_complete", "execution_status"]
                )
                assert has_status, (
                    "run_workflow_pipeline does not set a completion status.  "
                    "Consumers cannot tell if the pipeline completed or broke."
                )
                return
        pytest.fail("Could not find run_workflow_pipeline function")


@pytest.mark.xfail(reason="R14P-P2-07: routing_stats not thread-safe — threading refactor deferred")
class TestR14P_P2_07_RoutingStatsNotThreadSafe:
    """P2: RoutingDecisionEngine.routing_stats is mutated without a lock.

    File: backend/services/routing_decision.py:499-509
    """

    def test_routing_stats_thread_safe(self):
        source = _read(_ROUTING_DECISION_PATH)
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name == "_update_routing_stats":
                body_src = ast.get_source_segment(source, node)
                assert body_src is not None
                has_lock = any(
                    kw in body_src for kw in ["lock", "Lock", "threading", "atomic"]
                )
                assert has_lock, (
                    "_update_routing_stats mutates routing_stats without "
                    "thread safety.  Concurrent requests can lose counters."
                )
                return
        pytest.fail("Could not find _update_routing_stats method")


class TestR14P_P2_08_ColumnPromptInjection:
    """P2: _build_code_generation_prompt sanitizes the question but NOT
    column names from dataset_metadata.  Malicious column names flow
    directly into the LLM code generation prompt.

    File: backend/services/data_analysis/data_analysis_agent.py:300-306
    """

    def test_column_names_sanitized(self):
        source = _read(_DATA_ANALYSIS_PATH)
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name == "_build_code_generation_prompt":
                body_src = ast.get_source_segment(source, node)
                assert body_src is not None
                # Question is sanitized: .replace("{", "").replace("}", "")
                # But columns_desc uses col['name'] directly
                question_sanitized = "clean_question" in body_src
                col_line = body_src[body_src.find("columns_desc"):]
                col_sanitized = any(
                    kw in col_line[:300]
                    for kw in ["replace", "sanitize", "escape", "clean"]
                )
                if question_sanitized and not col_sanitized:
                    assert False, (
                        "_build_code_generation_prompt sanitizes the user "
                        "question but not column names from metadata.  "
                        "Malicious column names enable prompt injection."
                    )
                return
        pytest.fail("Could not find _build_code_generation_prompt method")


class TestR14P_P2_09_TemplateMaxIloc0NaN:
    """P2: _template_max and _template_min use .iloc[0] without guarding
    against all-NaN columns where the boolean filter returns empty DataFrame.

    File: backend/services/data_analysis/data_analysis_agent.py:471, 490
    """

    def test_template_max_min_guards_iloc(self):
        source = _read(_DATA_ANALYSIS_PATH)
        for method in ("_template_max", "_template_min"):
            tree = ast.parse(source)
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef) and node.name == method:
                    body_src = ast.get_source_segment(source, node)
                    if body_src and ".iloc[0]" in body_src:
                        has_guard = any(
                            kw in body_src
                            for kw in ["empty", "len(", "try", "dropna"]
                        )
                        assert has_guard, (
                            f"{method} uses .iloc[0] without guarding against "
                            "empty DataFrames from all-NaN columns."
                        )


class TestR14P_P2_10_FallbackRunnerSilentDegradation:
    """P2: _initialize_fallback_runner creates RAG with use_reranker=False
    and does not set services.reranker, causing silent quality degradation.

    File: backend/api/workflow_query_routes.py:237-239
    """

    def test_fallback_runner_logs_no_reranker(self):
        source = _read(_WORKFLOW_ROUTES_PATH)
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if (
                isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
                and node.name == "_initialize_fallback_runner"
            ):
                body_src = ast.get_source_segment(source, node)
                assert body_src is not None
                if "use_reranker=False" in body_src:
                    # Check for explicit logging ABOUT reranker being disabled
                    # Not just generic logger.warning for other services
                    has_reranker_log = (
                        "without reranker" in body_src.lower()
                        or "reranker disabled" in body_src.lower()
                        or "services.reranker" in body_src
                    )
                    assert has_reranker_log, (
                        "_initialize_fallback_runner disables reranker "
                        "(use_reranker=False) without logging this quality "
                        "degradation.  The rerank_node silently falls back "
                        "to score-based sorting."
                    )
                return
        pytest.fail("Could not find _initialize_fallback_runner")


class TestR14P_P2_11_CostEstimationNodeNoResponseBuilder:
    """P2: cost_estimation_node always sets state['response'] directly
    without using the response_builder service, and then sets
    shortcut_response=True.  This means cost estimation results bypass
    the dispatch service entirely.  While the response_node is in the
    shortcut whitelist, it returns early because response is already set.

    The bug: cost estimation responses have no provider_used set, so
    the WorkflowQueryResponse.provider_used will be None.

    File: backend/services/workflows/nodes/cost_estimation_node.py
    """

    def test_cost_estimation_sets_provider_used(self):
        source = _read(_COST_ESTIMATION_NODE_PATH)
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if (
                isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
                and node.name == "cost_estimation_node"
            ):
                body_src = ast.get_source_segment(source, node)
                assert body_src is not None
                has_provider = "provider_used" in body_src
                assert has_provider, (
                    "cost_estimation_node sets response and shortcut_response "
                    "but never sets state['provider_used'].  The API response "
                    "will have provider_used=None for cost estimation queries."
                )


@pytest.mark.xfail(reason="R14P-P2-12: input_preprocessing unconditional edge — LangGraph architectural fix deferred")
class TestR14P_P2_12_InputPreprocessingErrorNoRecovery:
    """P2: _input_preprocessing_node can set state['error'] but the graph
    has an unconditional edge to context_enrichment.  The error propagates
    through the entire pipeline without triggering error_handling until
    confidence_evaluation finally checks for errors.

    File: backend/services/intent_classification/intent_workflow.py:158-183
    """

    def test_preprocessing_error_goes_to_error_handler(self):
        source = _read(_INTENT_WORKFLOW_PATH)
        tree = ast.parse(source)

        # Check if input_preprocessing has a conditional edge to error_handling
        has_conditional = False
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                func = node.func
                if isinstance(func, ast.Attribute) and func.attr == "add_conditional_edges":
                    if len(node.args) >= 1:
                        arg0 = node.args[0]
                        if isinstance(arg0, ast.Constant) and arg0.value == "input_preprocessing":
                            has_conditional = True

        if not has_conditional:
            # Check if input_preprocessing -> context_enrichment is unconditional
            for node in ast.walk(tree):
                if isinstance(node, ast.Call):
                    func = node.func
                    if isinstance(func, ast.Attribute) and func.attr == "add_edge":
                        if len(node.args) >= 2:
                            a0, a1 = node.args[0], node.args[1]
                            if (
                                isinstance(a0, ast.Constant)
                                and isinstance(a1, ast.Constant)
                                and a0.value == "input_preprocessing"
                                and a1.value == "context_enrichment"
                            ):
                                # Verify preprocessing can set error
                                for n2 in ast.walk(tree):
                                    if (
                                        isinstance(n2, (ast.FunctionDef, ast.AsyncFunctionDef))
                                        and n2.name == "_input_preprocessing_node"
                                    ):
                                        body = ast.get_source_segment(source, n2)
                                        if body and 'state["error"]' in body:
                                            assert False, (
                                                "input_preprocessing can set error "
                                                "but has unconditional edge to "
                                                "context_enrichment.  Error cascades "
                                                "through 3 nodes before reaching "
                                                "error_handling at confidence_evaluation."
                                            )
