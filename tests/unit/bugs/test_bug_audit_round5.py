"""TDI Round 5 — Failing tests for Critical + High bugs found by 3-agent audit.

These tests assert CORRECT behavior that is currently broken.
All tests should FAIL before fixes are applied.
"""

from __future__ import annotations

import importlib.util
import re
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# Helper: load the legacy code_executor.py (shadowed by the package)
# ---------------------------------------------------------------------------

def _load_legacy_code_executor():
    """Import the legacy code_executor.py file directly (not the package)."""
    spec = importlib.util.spec_from_file_location(
        "code_executor_legacy",
        "backend/services/code_executor.py",
    )
    mod = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(mod)
    except Exception:
        pytest.skip("Legacy code_executor.py could not be loaded (Docker SDK missing)")
    return mod


# ---------------------------------------------------------------------------
# RAG-01 (High): RRF formula missing k-constant — rank-1 dominates 10:1
# ---------------------------------------------------------------------------

class TestRRFFormula:
    """RAG-01: Standard RRF uses 1/(k+rank), not weight/rank."""

    def test_rrf_rank1_vs_rank10_ratio_should_be_smooth(self):
        """With standard RRF (k=60), rank-1 vs rank-10 ratio should be ~1.5:1, not 10:1.

        Current code: weight/rank  =>  ratio = 10:1 for rank 1 vs 10.
        Correct code: weight/(k+rank)  =>  ratio ~ 61/70 ~ 1.16:1 with k=60.

        BUG: hybrid_search.py:268-282 uses weight/rank without k constant.
        """
        import inspect
        from backend.services.retrieval.hybrid_search import HybridRetriever

        source = inspect.getsource(HybridRetriever)

        # The RRF formula should include a k constant (typically 60)
        # Standard formula: 1/(k + rank)  or  weight/(k + rank)
        has_k_constant = bool(re.search(r"/\s*\(\s*\d+\s*\+\s*rank", source))

        assert has_k_constant, (
            "RRF formula uses weight/rank without k constant. "
            "Standard RRF uses weight/(k+rank) where k=60. Without k, "
            "rank-1 results dominate 10:1 over rank-10."
        )


# ---------------------------------------------------------------------------
# INTENT-01 (High): _call_classifier swallows real TypeErrors
# ---------------------------------------------------------------------------

class TestCallClassifierErrorHandling:
    """INTENT-01: TypeError from INSIDE classifier should NOT be swallowed."""

    def test_internal_type_error_not_swallowed(self):
        """If classify_intent raises TypeError internally (not from signature
        mismatch), the error should propagate rather than silently falling
        back to heuristic classification.

        BUG: intent_node.py:94-105 catches TypeError on each calling
        convention, but cannot distinguish signature mismatch from internal error.
        """
        import asyncio
        from backend.services.workflows.nodes.intent_node import _call_classifier

        class BrokenClassifier:
            def classify_intent(self, query: str, context: dict = None):
                # This TypeError happens INSIDE the method, not from signature
                data = None
                return data["intent"]  # TypeError: 'NoneType' not subscriptable

        classifier = BrokenClassifier()
        # Currently this returns None silently; it should raise
        with pytest.raises(TypeError):
            asyncio.get_event_loop().run_until_complete(
                _call_classifier(classifier, "test query", {})
            )


# ---------------------------------------------------------------------------
# INTENT-02 (High): Dual heuristic classifiers disagree on "how much"
# ---------------------------------------------------------------------------

class TestHeuristicConsistency:
    """INTENT-02: Heuristic should handle cost-related phrasing."""

    def test_how_much_will_it_cost_should_be_cost_estimation(self):
        """'how much will it cost to build a warehouse?' should route
        to cost_estimation. The phrase 'how much' + 'cost' is a clear
        cost intent that does NOT match any existing keyword list entry.

        BUG: _heuristic_intent requires exact substring matches like
        'cost estimate', but 'how much will it cost' doesn't contain those.
        """
        from backend.services.workflows.nodes.intent_node import _heuristic_intent

        query = "how much will it cost to build a warehouse?"
        intent = _heuristic_intent(query)
        assert intent == "cost_estimation", (
            f"_heuristic_intent returned '{intent}' for 'how much will it cost'. "
            f"This is clearly a cost query but doesn't match any keyword substring."
        )

    def test_what_is_the_price_should_be_cost_estimation(self):
        """'what is the price of this project?' should route to cost_estimation.
        The word 'price' is a natural cost synonym not in the keyword list.
        """
        from backend.services.workflows.nodes.intent_node import _heuristic_intent

        query = "what is the price of this building project?"
        intent = _heuristic_intent(query)
        assert intent == "cost_estimation", (
            f"_heuristic_intent returned '{intent}' for price query."
        )


# ---------------------------------------------------------------------------
# WF-02 (High): Safety-blocked queries still reach response_node
# ---------------------------------------------------------------------------

class TestSafetyBlockPropagation:
    """WF-02: When safety_node blocks a query, response_node should NOT
    invoke an LLM response builder."""

    def test_safety_error_prevents_response_builder(self):
        """After safety_node sets state['error'], the pipeline should NOT
        call response_node if a response_builder is attached.

        BUG: graph.py breaks on error at line 69-70, but line 84-85 runs
        response_node outside the _run_node wrapper if no response exists.
        """
        import asyncio
        from backend.services.workflows.graph import run_workflow_pipeline

        state = {"query": "rm -rf /", "metadata": {}, "metrics": {}}
        response_node_called = False

        async def mock_safety_node(s, svc):
            s["error"] = "Blocked by safety node"
            return s

        async def mock_response_node(s, svc):
            nonlocal response_node_called
            response_node_called = True
            s["response"] = s.get("error", "error")
            return s

        async def passthrough(s, svc):
            return s

        services = SimpleNamespace(
            intent_classifier=None,
            prompt_manager=None,
            response_builder=MagicMock(),
        )

        async def _run():
            nonlocal response_node_called
            with patch("backend.services.workflows.graph.intent_node", passthrough), \
                 patch("backend.services.workflows.graph.cost_estimation_node", passthrough), \
                 patch("backend.services.workflows.graph.retrieval_node", passthrough), \
                 patch("backend.services.workflows.graph.rerank_node", passthrough), \
                 patch("backend.services.workflows.graph.prompt_node", passthrough), \
                 patch("backend.services.workflows.graph.groundedness_node", passthrough), \
                 patch("backend.services.workflows.graph.route_node", passthrough), \
                 patch("backend.services.workflows.graph.safety_node", mock_safety_node), \
                 patch("backend.services.workflows.graph.code_exec_node", passthrough), \
                 patch("backend.services.workflows.graph.response_node", mock_response_node):
                return await run_workflow_pipeline(state, services)

        asyncio.get_event_loop().run_until_complete(_run())

        # response_node should NOT have been called after a safety block
        # Currently graph.py:84-85 calls response_node anyway
        assert not response_node_called, (
            "response_node was called after safety_node blocked the query. "
            "When state['error'] is set, response_node should be skipped."
        )


# ---------------------------------------------------------------------------
# CE-01 (Critical): _validate_code bypass via importlib (legacy executor)
# ---------------------------------------------------------------------------

class TestLegacyCodeValidatorBypass:
    """CE-01: Legacy _validate_code must block importlib-based escape.

    The legacy code_executor.py file is shadowed by the code_executor/ package.
    We verify the source code directly for known bypass patterns.
    """

    def test_importlib_not_in_legacy_blacklist(self):
        """importlib is not blacklisted in legacy _validate_code.

        BUG: legacy code_executor.py only blocks 'os', 'subprocess', 'sys'.
        importlib.import_module('os') passes validation.
        """
        source = open("backend/services/code_executor.py").read()

        # The legacy validator should block importlib
        blocks_importlib = (
            '"importlib"' in source
            or "'importlib'" in source
            or "importlib" in source.split("blacklisted")[0] if "blacklisted" in source else False
        )
        # Check if importlib is in any blacklist/blocklist
        has_importlib_check = "importlib" in source and (
            "blacklist" in source.lower() or "block" in source.lower()
        )
        assert blocks_importlib or has_importlib_check, (
            "Legacy code_executor.py does not block importlib. "
            "importlib.import_module('os') bypasses the sandbox validator."
        )

    def test_getattr_not_in_legacy_checks(self):
        """getattr() is not checked in legacy _validate_code.

        BUG: Only direct ast.Call with ast.Name is checked, not getattr chains.
        getattr(__builtins__, 'exec')('code') passes validation.
        """
        source = open("backend/services/code_executor.py").read()

        blocks_getattr = (
            '"getattr"' in source
            or "'getattr'" in source
            or "getattr" in source and "blacklist" in source.lower()
        )
        assert blocks_getattr, (
            "Legacy code_executor.py does not block getattr(). "
            "getattr(__builtins__, 'exec')() bypasses the sandbox validator."
        )


# ---------------------------------------------------------------------------
# CE-02 (High): Arbitrary host path mount to Docker (legacy executor)
# ---------------------------------------------------------------------------

class TestLegacyDataFilesPathValidation:
    """CE-02: Legacy code_executor should validate data_files paths."""

    def test_legacy_executor_validates_data_paths(self):
        """Legacy code_executor.py mounts arbitrary paths without validation.

        BUG: code_executor.py:189-194 mounts data_files directly to Docker.
        """
        mod = _load_legacy_code_executor()

        source_code = open("backend/services/code_executor.py").read()
        has_path_validation = (
            "_validate_data_path" in source_code
            or "_resolve_allowed_data_file" in source_code
            or "_is_subpath" in source_code
            or "allowed_roots" in source_code
        )
        assert has_path_validation, (
            "Legacy code_executor has no data_files path validation. "
            "/etc/passwd could be mounted read-only into Docker container."
        )


# ---------------------------------------------------------------------------
# CE-03 (High): No Docker timeout enforcement (legacy executor)
# ---------------------------------------------------------------------------

class TestLegacyDockerTimeout:
    """CE-03: Legacy executor must enforce execution timeout."""

    def test_legacy_executor_has_timeout(self):
        """containers.run(detach=False) blocks forever without timeout.

        BUG: code_executor.py uses containers.run(detach=False) with no
        timeout parameter.
        """
        source = open("backend/services/code_executor.py").read()
        uses_detach_true = "detach=True" in source
        uses_container_wait_timeout = "wait(timeout" in source
        uses_run_timeout = re.search(r"containers\.run\(.*timeout", source, re.DOTALL)

        assert uses_detach_true or uses_container_wait_timeout or uses_run_timeout, (
            "Legacy DockerCodeExecutor.execute_code has no timeout enforcement. "
            "A 'while True: pass' will block the API thread forever."
        )


# ---------------------------------------------------------------------------
# CE-06 + DA-06 (High): Module-level instantiation causes import crash
# ---------------------------------------------------------------------------

class TestModuleLevelInstantiation:
    """DA-06: Module-level DataAnalysisAgent() can crash at import time."""

    def test_module_level_agent_creation_is_lazy(self):
        """DataAnalysisAgent() at module level calls
        LLMClientFactory.create_client() which fails if LLM backend
        is misconfigured. Should be lazy-initialized.

        BUG: data_analysis_agent.py creates agent at import time.
        """
        source = open("backend/services/data_analysis/data_analysis_agent.py").read()
        lines = source.split("\n")
        module_level_creation = False
        for line in lines:
            stripped = line.strip()
            if "DataAnalysisAgent()" in stripped and not stripped.startswith("#"):
                if not line.startswith(" ") and not line.startswith("\t"):
                    module_level_creation = True

        assert not module_level_creation, (
            "DataAnalysisAgent() is created at module level (import time). "
            "If LLM backend or Docker is misconfigured, importing this module "
            "will crash. Should use lazy initialization."
        )


# ---------------------------------------------------------------------------
# AS-03 (High): interaction_history race condition
# ---------------------------------------------------------------------------

class TestMemorySessionThreadSafety:
    """AS-03: interaction_history mutations must be thread-safe."""

    def test_truncation_is_atomic(self):
        """session.interaction_history truncation (read-slice-assign) is not
        atomic. A background thread reading the list during truncation can
        see an inconsistent state.

        BUG: rag_engine.py truncates without locking, while spawning a
        thread that reads the same list.
        """
        import inspect
        from backend.services import rag_engine

        source = inspect.getsource(rag_engine.SimpleRAG._record_memory_interaction)

        uses_lock = (
            "lock" in source.lower()
            or "Lock()" in source
            or "threading.Lock" in source
            or "with self._" in source
        )
        copies_history = (
            "list(" in source
            or ".copy()" in source
            or "[:]" in source
        )

        assert uses_lock or copies_history, (
            "_record_memory_interaction mutates interaction_history without "
            "locking and passes the live session to a background thread. "
            "The truncation (read-slice-assign) is not atomic."
        )


# ---------------------------------------------------------------------------
# SEC-001 (Critical): Hardcoded fallback JWT secret
# ---------------------------------------------------------------------------

class TestJWTSecret:
    """SEC-001: JWT secret must not have a hardcoded fallback."""

    def test_no_hardcoded_jwt_secret_in_source(self):
        """_jwt_secret() falls back to 'industry-ai-flow-dev-secret' when
        AUTH_JWT_SECRET is empty. Any attacker who reads source can forge tokens.

        BUG: auth_routes.py:34 has hardcoded fallback secret.
        """
        source = open("backend/api/auth_routes.py").read()
        assert "industry-ai-flow-dev-secret" not in source, (
            "JWT secret has a hardcoded fallback 'industry-ai-flow-dev-secret'. "
            "Any attacker can forge valid tokens by reading the source code."
        )


# ---------------------------------------------------------------------------
# SEC-002 (Critical): Plaintext password storage
# ---------------------------------------------------------------------------

class TestPasswordStorage:
    """SEC-002: Passwords must be hashed, not stored in plaintext."""

    def test_password_not_stored_plaintext(self):
        """Passwords are stored as raw strings and compared with ==.
        Should use bcrypt/argon2 hashing.

        BUG: auth_routes.py stores and compares plaintext passwords.
        """
        source = open("backend/api/auth_routes.py").read()

        has_plaintext_compare = (
            'user.get("password") != payload.password' in source
            or "user[\"password\"] == payload.password" in source
        )
        assert not has_plaintext_compare, (
            "Passwords are compared in plaintext. "
            "Should use bcrypt.checkpw() or similar constant-time hash comparison."
        )


# ---------------------------------------------------------------------------
# SEC-003 (Critical): No auth on /train endpoint
# ---------------------------------------------------------------------------

class TestTrainEndpointAuth:
    """SEC-003: /train endpoint must require admin authorization."""

    def test_train_endpoint_has_role_check(self):
        """The train endpoint accepts arbitrary dataset_path and replaces
        the live model with no role-based authorization.

        BUG: cost_estimation_routes.py has no admin guard on /train.
        """
        source = open("backend/api/cost_estimation_routes.py").read()

        has_role_check = (
            "admin" in source.lower()
            or "role" in source.lower()
            or "authorize" in source.lower()
            or "permission" in source.lower()
        )
        assert has_role_check, (
            "The /train endpoint has no role-based authorization. "
            "Any user can retrain the cost estimation model with poisoned data."
        )


# ---------------------------------------------------------------------------
# SEC-007 (High): SQL pattern detection bypass
# ---------------------------------------------------------------------------

class TestSQLPatternDetection:
    """SEC-007: SQL pattern detection must catch common injection patterns."""

    @pytest.mark.parametrize("payload,description", [
        ("' OR '1'='1", "basic SQL injection tautology"),
        ("UNION/**/SELECT * FROM users", "comment-obfuscated UNION SELECT"),
    ])
    def test_sql_injection_patterns_detected(self, payload, description):
        """SQL_PATTERN should detect common injection patterns beyond
        just 'drop table', 'union select', '--', and ';'.

        BUG: sanitizer.py:12 SQL_PATTERN is too narrow.
        """
        from backend.security.sanitizer import SQL_PATTERN

        assert SQL_PATTERN.search(payload), (
            f"SQL pattern did not detect '{description}': {payload!r}"
        )


# ---------------------------------------------------------------------------
# SEC-008 (High): XSS detection bypass via event handlers
# ---------------------------------------------------------------------------

class TestXSSPatternDetection:
    """SEC-008: XSS detection must catch event handler-based attacks."""

    @pytest.mark.parametrize("payload,description", [
        ("<img src=x onerror=alert(1)>", "img onerror event handler"),
        ("<svg onload=alert(1)>", "svg onload event handler"),
        ("<iframe src=javascript:alert(1)>", "iframe with javascript URI"),
        ("<body onload=alert(1)>", "body onload event handler"),
    ])
    def test_xss_event_handler_patterns_detected(self, payload, description):
        """SCRIPT_PATTERN only checks <script> tags. Event handler-based
        XSS bypasses it entirely.

        BUG: sanitizer.py:11 SCRIPT_PATTERN only matches <script>.
        """
        from backend.security.sanitizer import SCRIPT_PATTERN, CONTROL_CHAR_PATTERN

        detected = (
            SCRIPT_PATTERN.search(payload)
            or CONTROL_CHAR_PATTERN.search(payload)
        )
        assert detected, (
            f"XSS pattern did not detect '{description}': {payload!r}. "
            f"Only <script> tags are caught; event handlers bypass detection."
        )


# ---------------------------------------------------------------------------
# SEC-009 (High): ILIKE wildcard injection in prompt search
# ---------------------------------------------------------------------------

class TestILIKEWildcardEscape:
    """SEC-009: ILIKE search params must escape % and _ wildcards."""

    def test_percent_wildcard_escaped_in_search(self):
        """User input '%' in ILIKE query matches ALL records.

        BUG: prompt_routes.py uses f'%{q}%' without escaping wildcards.
        """
        source = open("backend/api/prompt_routes.py").read()

        has_ilike = "ILIKE" in source or "ilike" in source
        if not has_ilike:
            pytest.skip("No ILIKE usage found in prompt_routes.py")

        has_escape = (
            "replace('%'" in source
            or "replace('_'" in source
            or "escape_like" in source
            or "escape_ilike" in source
        )
        assert has_escape, (
            "ILIKE search parameters do not escape % and _ wildcards. "
            "User input '%' will match ALL records (data leakage)."
        )


# ---------------------------------------------------------------------------
# SEC-014 (High): Internal exception details leaked to client
# ---------------------------------------------------------------------------

class TestErrorDetailLeakage:
    """SEC-014: Internal exception details must not be sent to clients."""

    def test_train_endpoint_does_not_leak_internals(self):
        """HTTPException detail contains raw exception string with file
        paths, stack traces, and internal config.

        BUG: cost_estimation_routes.py uses f'training failed: {exc}'.
        """
        source = open("backend/api/cost_estimation_routes.py").read()

        leak_patterns = [
            r'detail=f".*\{exc\}"',
            r'detail=f".*\{e\}"',
            r"detail=f'.*\{exc\}'",
            r"detail=str\(exc\)",
            r"detail=str\(e\)",
        ]

        leaks_found = []
        for pattern in leak_patterns:
            matches = re.findall(pattern, source)
            leaks_found.extend(matches)

        assert len(leaks_found) == 0, (
            f"Found {len(leaks_found)} instances of raw exception details leaked "
            f"to HTTP clients. Internal errors should return generic messages. "
            f"Matches: {leaks_found[:3]}"
        )
