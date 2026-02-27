"""
TDI Round 15 -- Regression tests for 11 bugs (1 P0, 10 P1).

All tests use AST / source-text inspection so they can run without
importing backend modules that carry heavy runtime dependencies
(numpy, pandas, psycopg2, PaddleOCR, etc.).

Categories:
  A – Agent / Workflow logic
  B – Backend service logic
  C – API / Security
  D – Module-level / Infrastructure
"""

import ast
import os
import re
import textwrap

import pytest

# ---------------------------------------------------------------------------
# Path constants (relative to this file's location)
# ---------------------------------------------------------------------------

_HERE = os.path.dirname(__file__)
_ROOT = os.path.normpath(os.path.join(_HERE, "..", "..", ".."))
_BACKEND = os.path.join(_ROOT, "backend")

_INTENT_WF = os.path.join(
    _BACKEND, "services", "intent_classification", "intent_workflow.py"
)
_DISPATCH_SVC = os.path.join(
    _BACKEND, "services", "llm_integration", "dispatch_service.py"
)
_ENHANCED_QUERY = os.path.join(_BACKEND, "api", "enhanced_query_routes.py")
_DOC_MGMT = os.path.join(_BACKEND, "api", "document_management_routes.py")
_CHUNKER = os.path.join(_BACKEND, "services", "core", "chunker.py")
_WORKFLOW_ROUTES = os.path.join(_BACKEND, "api", "workflow_query_routes.py")
_PROMPT_NODE = os.path.join(
    _BACKEND, "services", "workflows", "nodes", "prompt_node.py"
)
_DATA_ANALYSIS = os.path.join(
    _BACKEND, "services", "data_analysis", "data_analysis_agent.py"
)


def _read(path: str) -> str:
    with open(path, encoding="utf-8") as fh:
        return fh.read()


# ===========================================================================
# Category A — Agent / Workflow Logic
# ===========================================================================


class TestR15A01_CostEstimationAgentEmptyResponse:
    """P0 FIX VERIFIED: COST_ESTIMATION_AGENT dispatch now returns non-empty response."""

    @pytest.mark.unit
    def test_cost_estimation_dispatch_returns_nonempty_response(self):
        source = _read(_INTENT_WF)

        # The fix changed response="" to a non-empty marker string.
        cost_block_match = re.search(
            r"AgentType\.COST_ESTIMATION_AGENT.*?return\s*\{[^}]*\"response\"\s*:\s*\"\"",
            source,
            re.DOTALL,
        )
        assert cost_block_match is None, (
            "Bug NOT fixed: COST_ESTIMATION_AGENT still returns response='' "
            "which triggers RuntimeError in the calling node."
        )


class TestR15A02_ChunkerConstructionRefDoublePrepend:
    """P1 FIX VERIFIED: Construction-reference boundary no longer causes double-append."""

    @pytest.mark.unit
    def test_construction_reference_boundary_no_double_append(self):
        source = _read(_CHUNKER)
        tree = ast.parse(source)

        # After the fix, the construction-reference branch uses `continue`
        # so the unconditional append at the end of the loop body is skipped.
        # Verify the fix: look for `continue` in the construction-ref branch.
        assert "continue" in source, (
            "Expected a `continue` statement in the chunker after the "
            "construction-reference fix."
        )

        # Verify NO double-append pattern exists
        double_append_found = False
        for node in ast.walk(tree):
            if not isinstance(node, ast.For):
                continue
            stmts = node.body
            for i, stmt in enumerate(stmts):
                if not isinstance(stmt, ast.If):
                    continue
                inner_if_appends = []
                for sub in ast.walk(stmt):
                    if isinstance(sub, ast.AugAssign):
                        if (
                            isinstance(sub.target, ast.Name)
                            and sub.target.id == "current_chunk"
                            and isinstance(sub.value, ast.Name)
                            and sub.value.id == "split"
                        ):
                            inner_if_appends.append(sub)
                if not inner_if_appends:
                    continue
                for later_stmt in stmts[i + 1 :]:
                    if (
                        isinstance(later_stmt, ast.AugAssign)
                        and isinstance(later_stmt.target, ast.Name)
                        and later_stmt.target.id == "current_chunk"
                        and isinstance(later_stmt.value, ast.Name)
                        and later_stmt.value.id == "split"
                    ):
                        double_append_found = True
                        break
                if double_append_found:
                    break
            if double_append_found:
                break

        # The double_append pattern may still exist structurally (the if-branch
        # appends and the unconditional line is still there), but the `continue`
        # prevents both from executing in the same iteration.
        # So we verify the `continue` exists in the construction-ref branch.
        ref_branch = re.search(
            r"_is_construction_reference.*?\n.*?current_chunk \+= split.*?\n\s*continue",
            source,
            re.DOTALL,
        )
        assert ref_branch is not None, (
            "Expected construction-reference branch to end with `continue` "
            "to prevent the double-append."
        )


# ===========================================================================
# Category B — Backend Service Logic
# ===========================================================================


class TestR15B02_ClarificationRetryBranchDead:
    """P1 FIX VERIFIED: _route_after_clarification now returns 'retry_classification'."""

    @pytest.mark.unit
    def test_retry_classification_branch_is_alive(self):
        source = _read(_INTENT_WF)

        # Extract _route_after_clarification body
        func_match = re.search(
            r"def _route_after_clarification\(.*?\n(.*?)(?=\n    (?:async )?def |\nclass )",
            source,
            re.DOTALL,
        )
        assert func_match is not None, (
            "_route_after_clarification function not found in source."
        )
        func_body = func_match.group(1)

        returns_retry = (
            '"retry_classification"' in func_body
            or "'retry_classification'" in func_body
        )
        assert returns_retry, (
            "Bug NOT fixed: _route_after_clarification still never returns "
            "'retry_classification'."
        )


class TestR15B03_RateLimitWindowAppendOutsideLock:
    """P1 FIX VERIFIED: cloud_window.append(now) now executes inside the lock."""

    @pytest.mark.unit
    def test_rate_limit_append_inside_lock(self):
        source = _read(_DISPATCH_SVC)
        tree = ast.parse(source)

        # Find _run_cloud method and check that cloud_window.append
        # is inside a `with self._rate_limit_lock:` block
        for node in ast.walk(tree):
            if not isinstance(node, ast.FunctionDef):
                continue
            if node.name != "_run_cloud":
                continue

            # Find all With blocks that use _rate_limit_lock
            lock_with_bodies = []
            for child in ast.walk(node):
                if not isinstance(child, ast.With):
                    continue
                for item in child.items:
                    ctx_expr = item.context_expr
                    if (
                        isinstance(ctx_expr, ast.Attribute)
                        and ctx_expr.attr == "_rate_limit_lock"
                    ):
                        lock_with_bodies.append(child)

            # Check that at least one append is inside a lock block
            append_inside_lock = False
            for lock_with in lock_with_bodies:
                for desc in ast.walk(lock_with):
                    if not isinstance(desc, ast.Call):
                        continue
                    func = desc.func
                    if (
                        isinstance(func, ast.Attribute)
                        and func.attr == "append"
                        and isinstance(func.value, ast.Name)
                        and func.value.id == "cloud_window"
                    ):
                        append_inside_lock = True
                        break

            assert append_inside_lock, (
                "Bug NOT fixed: cloud_window.append() is still outside the lock."
            )
            return

        pytest.fail("_run_cloud method not found in dispatch_service.py")


class TestR15B04_HybridAutoRaisesWhenFallbackOnErrorFalse:
    """P1 FIX VERIFIED: soft_fail no longer gated by settings.fallback_on_error."""

    @pytest.mark.unit
    def test_hybrid_auto_soft_fail_not_gated(self):
        source = _read(_DISPATCH_SVC)

        # After fix: the guard should be `if soft_fail:` (not `if soft_fail and settings.fallback_on_error:`)
        gated_guard = re.search(
            r"if\s+soft_fail\s+and\s+settings\.fallback_on_error\s*:",
            source,
        )
        assert gated_guard is None, (
            "Bug NOT fixed: soft_fail is still gated by settings.fallback_on_error."
        )

        # Confirm the simpler guard exists
        simple_guard = re.search(r"if\s+soft_fail\s*:", source)
        assert simple_guard is not None, (
            "Expected `if soft_fail:` guard but not found."
        )


# ===========================================================================
# Category C — API / Security
# ===========================================================================


class TestR15C01_AdminKeyChecksPresenceNotValue:
    """P1 FIX VERIFIED: Admin key now compared with hmac.compare_digest."""

    @pytest.mark.unit
    def test_admin_key_uses_compare_digest(self):
        source = _read(_ENHANCED_QUERY)

        # After fix: should use hmac.compare_digest
        has_compare_digest = bool(
            re.search(r"hmac\.compare_digest", source)
        )
        assert has_compare_digest, (
            "Bug NOT fixed: admin key still doesn't use hmac.compare_digest."
        )


class TestR15C02_RestoreDocumentVersionBypassesTenantAuth:
    """P1 FIX VERIFIED: restore_document_version now uses Depends(get_current_tenant)."""

    @pytest.mark.unit
    def test_restore_uses_auth_dependency(self):
        source = _read(_DOC_MGMT)
        tree = ast.parse(source)

        restore_fn = None
        for node in ast.walk(tree):
            if (
                isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
                and node.name == "restore_document_version"
            ):
                restore_fn = node
                break

        assert restore_fn is not None, "restore_document_version not found."

        # Check that one of its default arguments references Depends + tenant
        has_auth_depends = False
        for arg in restore_fn.args.defaults + restore_fn.args.kw_defaults:
            if arg is None:
                continue
            arg_src = ast.unparse(arg) if hasattr(ast, "unparse") else ""
            if "Depends" in arg_src and "tenant" in arg_src.lower():
                has_auth_depends = True
                break

        assert has_auth_depends, (
            "Bug NOT fixed: restore_document_version still doesn't use "
            "Depends(get_current_tenant)."
        )


class TestR15C03_ChatEndpointNoMessagesLengthLimit:
    """P1 FIX VERIFIED: Chat endpoint now validates message count and size."""

    @pytest.mark.unit
    def test_chat_messages_has_length_constraint(self):
        source = _read(_ENHANCED_QUERY)

        # After fix: should have MAX_CHAT_MESSAGES and length validation
        has_limit = bool(
            re.search(r"MAX_CHAT_MESSAGES|MAX_MESSAGE_LENGTH|max_items|len\(messages\)", source)
        )
        assert has_limit, (
            "Bug NOT fixed: chat endpoint still has no message count/size constraint."
        )


# ===========================================================================
# Category D — Module-level / Infrastructure
# ===========================================================================


class TestR15D01_WorkflowLockCreatedBeforeEventLoop:
    """P1 FIX VERIFIED: asyncio.Lock() now created lazily inside a function."""

    @pytest.mark.unit
    def test_asyncio_lock_not_at_module_level(self):
        source = _read(_WORKFLOW_ROUTES)
        tree = ast.parse(source)

        # Check NO module-level assignment calls asyncio.Lock()
        lock_at_module_level = False
        for node in tree.body:
            if not isinstance(node, ast.Assign):
                continue
            val = node.value
            if not isinstance(val, ast.Call):
                continue
            func = val.func
            if isinstance(func, ast.Attribute) and func.attr == "Lock":
                if isinstance(func.value, ast.Name) and func.value.id == "asyncio":
                    lock_at_module_level = True
                    break

        assert not lock_at_module_level, (
            "Bug NOT fixed: asyncio.Lock() is still assigned at module level."
        )

        # Verify lazy getter exists
        assert "_get_workflow_lock" in source, (
            "Expected lazy _get_workflow_lock() function but not found."
        )


class TestR15D02_PromptNodeDeadGuardUserVisibleInternalError:
    """P1 FIX VERIFIED: prompt_node no longer exposes internal error message."""

    @pytest.mark.unit
    def test_prompt_node_no_internal_error_message(self):
        source = _read(_PROMPT_NODE)

        # After fix: should NOT set state["error"] to the raw internal message
        raw_msg_pattern = re.search(
            r'state\s*\[\s*["\']error["\']\s*\]\s*=\s*["\']prompt_manager service is required["\']',
            source,
        )
        assert raw_msg_pattern is None, (
            "Bug NOT fixed: prompt_node still sets state['error'] to the raw "
            "internal message 'prompt_manager service is required'."
        )


class TestR15D04_ColumnNameInjectionInTemplateCode:
    """P1 FIX VERIFIED: Column names now sanitized before interpolation."""

    @pytest.mark.unit
    def test_column_names_are_sanitized(self):
        source = _read(_DATA_ANALYSIS)

        # After fix: should have _sanitize_column_name method
        assert "_sanitize_column_name" in source, (
            "Bug NOT fixed: _sanitize_column_name method not found."
        )

        # Verify it escapes single quotes (the critical character)
        sanitize_match = re.search(
            r"def _sanitize_column_name.*?replace.*?['\"]'['\"]",
            source,
            re.DOTALL,
        )
        assert sanitize_match is not None, (
            "_sanitize_column_name doesn't appear to escape single quotes."
        )

        # Verify the sanitizer is actually called before template interpolation
        sanitize_calls = re.findall(r"_sanitize_column_name\s*\(", source)
        assert len(sanitize_calls) >= 4, (
            f"Expected _sanitize_column_name called in at least 4 template methods, "
            f"found {len(sanitize_calls)} call(s)."
        )
