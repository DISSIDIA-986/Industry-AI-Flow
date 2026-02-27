"""
TDI Round 14 -- Reproduction tests for 25 bugs (5 P0, 20 P1).

Categories: Code Validator Bypass, Path Traversal, API Security,
Response Headers, Authorization, Error Disclosure, SSRF, Rate Limiting.
"""

import ast
import os
import re

import pytest

# --- Paths ----------------------------------------------------------------

_BACKEND = os.path.normpath(
    os.path.join(os.path.dirname(__file__), "..", "..", "..", "backend")
)

_VALIDATOR_PATH = os.path.join(_BACKEND, "services", "code_executor", "validator.py")
_DOCKER_EXEC_PATH = os.path.join(
    _BACKEND, "services", "code_executor", "docker_executor.py"
)
_PPIO_PROVIDER_PATH = os.path.join(
    _BACKEND, "services", "code_executor", "providers", "ppio_provider.py"
)
_COST_EST_ROUTES_PATH = os.path.join(_BACKEND, "api", "cost_estimation_routes.py")
_DOC_MGMT_ROUTES_PATH = os.path.join(
    _BACKEND, "api", "document_management_routes.py"
)
_ENHANCED_QUERY_PATH = os.path.join(_BACKEND, "api", "enhanced_query_routes.py")
_PROMPT_ROUTES_PATH = os.path.join(_BACKEND, "api", "prompt_routes.py")
_FEEDBACK_ROUTES_PATH = os.path.join(_BACKEND, "api", "feedback_routes.py")
_AUTH_ROUTES_PATH = os.path.join(_BACKEND, "api", "auth_routes.py")
_INTENT_ROUTES_PATH = os.path.join(_BACKEND, "api", "intent_classification_routes.py")
_LLM_DISPATCH_ROUTES_PATH = os.path.join(_BACKEND, "api", "llm_dispatch_routes.py")
_MAIN_PATH = os.path.join(_BACKEND, "main.py")
_DEPENDENCIES_PATH = os.path.join(_BACKEND, "security", "dependencies.py")
_ERROR_HANDLER_PATH = os.path.join(_BACKEND, "middleware", "error_handler.py")
_SANITIZER_PATH = os.path.join(_BACKEND, "security", "sanitizer.py")
_MEMORY_STORE_PATH = os.path.join(_BACKEND, "services", "memory", "store.py")
_CONFIG_PATH = os.path.join(_BACKEND, "config.py")


def _read(path: str) -> str:
    with open(path) as f:
        return f.read()


# =============================================================================
# CODE VALIDATOR BYPASS (New patterns beyond rounds 1-13)
# =============================================================================


class TestR14_VAL01_CodecsDecodeBypass:
    """P0: codecs.decode('bfrff','rot13') reconstructs 'os.exec' without
    matching DANGEROUS_PATTERNS or BLACKLISTED_IMPORTS.

    The 'codecs' module is NOT in BLACKLISTED_IMPORTS, and in non-strict mode
    it passes through.  Even in strict mode, adding it to the whitelist is the
    wrong fix — codecs.decode with rot13/hex/base64 can reconstruct any
    string to evade pattern matching, then use it with builtins.
    """

    def test_codecs_blocked(self):
        source = _read(_VALIDATOR_PATH)
        # codecs must appear in BLACKLISTED_IMPORTS, or the BLOCKED_CALL_NAMES
        # set must include "codecs.decode", or there must be explicit handling
        has_codecs_protection = (
            '"codecs"' in source
            or "'codecs'" in source
            or "codecs" in source.split("BLACKLISTED_IMPORTS")[1].split("}")[0]
            if "BLACKLISTED_IMPORTS" in source
            else False
        )
        assert has_codecs_protection, (
            "codecs module is not blocked — codecs.decode('...', 'rot13') can "
            "reconstruct any string to bypass pattern-based security checks. "
            "Add 'codecs' to BLACKLISTED_IMPORTS."
        )


class TestR14_VAL02_SubclassesCallNotBlocked:
    """P0: ().__class__.__bases__[0].__subclasses__() is blocked by regex on
    '.__subclasses__' but calling the result via subscript indexing is not:

        cls_list = [].__class__.__mro__   # blocked by regex
        # But this pattern avoids any dotted dunder access:
        x = [1,2,3]
        t = type(x)              # <class 'list'>
        # type(x) is not blocked (only 3-arg type is blocked)

    More importantly, the DANGEROUS_PATTERNS regex for dunders requires a
    DOTTED prefix (the pattern starts with '\\.'). Code like:

        result = __import__('os')

    is caught by BLOCKED_CALL_NAMES, but:

        name = chr(95)+chr(95)+'import'+chr(95)+chr(95)

    constructs '__import__' dynamically.  The validator has no defence against
    string construction via chr() since chr() is not blocked.
    """

    def test_chr_builtin_blocked_or_restricted(self):
        source = _read(_VALIDATOR_PATH)
        # chr() combined with string concatenation can construct any dunder
        # attribute name. The validator must either block chr() calls or
        # implement runtime sandboxing beyond static analysis.
        has_chr_protection = any(
            kw in source
            for kw in ['"chr"', "'chr'", "chr", "BLOCKED_BUILTINS"]
            if kw in source.split("BLOCKED_CALL_NAMES")[1]
        ) if "BLOCKED_CALL_NAMES" in source else False

        # Alternative: check if there's a general "string construction"
        # defense or runtime sandbox
        has_runtime_sandbox = "builtins" in source and ("restrict" in source.lower() or "sandbox" in source.lower())

        assert has_chr_protection or has_runtime_sandbox, (
            "chr() is not blocked — chr(95)+chr(95)+'import'+chr(95)+chr(95) "
            "constructs '__import__' to bypass all pattern-based dunder checks. "
            "Either block chr() or implement runtime builtins restriction."
        )


class TestR14_VAL03_LambdaExecBypass:
    """P1: Lambda can reference blocked builtins indirectly.

    The container-reference check (lines 255-268) only checks ast.List,
    ast.Tuple, ast.Set, and ast.Dict values. But a lambda body that
    captures a Name node is NOT inside a container literal:

        f = lambda: __import__('os')

    __import__ is in BLOCKED_CALL_NAMES, BUT the check on line 296-298
    only looks at ast.Call with ast.Name — it catches f() if f is in
    blocked_names. However the alias detection (lines 270-291) only tracks
    ast.Assign, not lambda definitions. So:

        f = lambda: None  # Not flagged as alias
        g = (lambda: __import__)()  # __import__ as a Name in lambda body
                                     # is not in a container literal
    """

    def test_lambda_returning_blocked_name_caught(self):
        source = _read(_VALIDATOR_PATH)
        # The validator should check for blocked names inside lambda bodies
        # or any expression that yields a reference to a blocked function
        tree = ast.parse(source)

        # Look for lambda handling in _validate_blocked_calls
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name == "_validate_blocked_calls":
                body_src = ast.get_source_segment(source, node)
                assert body_src is not None
                has_lambda_check = "Lambda" in body_src or "lambda" in body_src.lower()
                assert has_lambda_check, (
                    "_validate_blocked_calls does not inspect ast.Lambda bodies "
                    "for references to blocked names like __import__, exec, eval"
                )
                return
        pytest.fail("Could not find _validate_blocked_calls method")


class TestR14_VAL04_FStringEvalBypass:
    """P1: f-string expressions are evaluated at runtime and can call
    functions. The validator does regex pattern matching on source text,
    but f-string internals are embedded in AST FormattedValue nodes,
    not directly visible in the raw source pattern check.

    Example: f'{eval("1+1")}' - the 'eval' call inside f-string is an
    ast.Call inside ast.FormattedValue. The ast.walk in
    _validate_blocked_calls DOES traverse into FormattedValue, so direct
    eval() calls would be caught. But:
        f'{getattr(__builtins__, "eval")("code")}'
    uses getattr which IS in DANGEROUS_PATTERNS regex, but the regex check
    runs against source text -- and the f-string source DOES contain 'getattr'.

    The real gap is: f-string can contain arbitrary expressions that are
    only visible in AST, not caught by source-level regex. The AST walk
    catches direct calls but not constructed calls.
    """

    def test_fstring_blocked_calls_documented_or_handled(self):
        source = _read(_VALIDATOR_PATH)
        # At minimum, the validator should have a comment or check
        # acknowledging f-string evaluation risks
        has_fstring_awareness = any(
            kw in source.lower()
            for kw in ["f-string", "fstring", "formattedvalue", "joinedstr"]
        )
        assert has_fstring_awareness, (
            "Validator has no awareness of f-string evaluation risks. "
            "f'{eval(\"code\")}' contains callable expressions inside "
            "FormattedValue AST nodes that need explicit traversal."
        )


class TestR14_VAL05_NonStrictModeCodecsPassthrough:
    """P1: In non-strict mode (strict_mode=False), any module NOT in
    BLACKLISTED_IMPORTS passes through. This means modules like:
    - codecs (string obfuscation)
    - builtins (direct access to all builtins)
    - types (FunctionType for code object injection)
    - gc (garbage collector for object graph traversal)
    - inspect (source code and frame inspection)
    are all allowed.
    """

    def test_dangerous_modules_in_blacklist(self):
        source = _read(_VALIDATOR_PATH)
        # Extract the BLACKLISTED_IMPORTS set contents
        blacklist_section = source.split("BLACKLISTED_IMPORTS")[1].split("}")[0]

        missing_dangerous = []
        for module in ["codecs", "builtins", "types", "gc", "inspect"]:
            if f'"{module}"' not in blacklist_section and f"'{module}'" not in blacklist_section:
                missing_dangerous.append(module)

        assert not missing_dangerous, (
            f"BLACKLISTED_IMPORTS is missing dangerous modules: {missing_dangerous}. "
            "These modules enable sandbox escapes even in non-strict mode: "
            "codecs (string obfuscation), builtins (direct builtin access), "
            "types (code object injection), gc (object graph traversal), "
            "inspect (frame inspection)."
        )


# =============================================================================
# PATH TRAVERSAL
# =============================================================================


class TestR14_PATH01_SymlinkBypassInResolve:
    """P0: _resolve_allowed_path / _resolve_allowed_data_file uses
    Path.resolve() BEFORE checking _is_subpath. If an attacker creates a
    symlink inside an allowed root (e.g. /tmp/link -> /etc/passwd), then:
      1. Path('/tmp/link').resolve() -> /etc/passwd
      2. _is_subpath(/etc/passwd, /tmp) -> False -> BLOCKED

    But the REAL vulnerability is the RACE CONDITION (TOCTOU):
      1. User uploads a valid file to /tmp/luncheon_data_xx/data.csv
      2. _resolve_allowed_data_file validates it -> OK
      3. Between validation and container mount, attacker replaces
         data.csv with a symlink to /etc/shadow
      4. Docker mounts the symlink target into the container

    The docker_executor.py does NOT check for symlinks before mounting.
    """

    def test_docker_executor_checks_symlinks(self):
        source = _read(_DOCKER_EXEC_PATH)
        has_symlink_check = any(
            kw in source
            for kw in ["is_symlink", "symlink", "follow_symlinks", "lstat"]
        )
        assert has_symlink_check, (
            "DockerExecutor does not check for symlinks before mounting "
            "workspace directory. TOCTOU race: file validated as safe, then "
            "replaced with symlink to sensitive host file before Docker mount."
        )


class TestR14_PATH02_InputFilenamePathTraversal:
    """P1: DockerExecutor.execute() writes input_files with user-supplied
    filenames directly:
        file_path = workspace / filename   (line 209)

    If 'filename' contains '../' (e.g., '../../../etc/cron.d/exploit'),
    the file is written OUTSIDE the workspace directory. The container
    only mounts /workspace, but the HOST filesystem is affected because
    the write happens BEFORE container creation.
    """

    def test_input_filenames_sanitized(self):
        source = _read(_DOCKER_EXEC_PATH)
        # Find the section where input_files are written
        if "input_files" not in source:
            pytest.skip("input_files handling not found")

        # The code should sanitize filenames (strip path separators)
        has_filename_sanitization = any(
            kw in source
            for kw in [
                "basename",
                "sanitize",
                "os.path.basename",
                ".name",
                "replace('..'",
                "path.name",
            ]
        )
        # Check if there's path traversal protection in the filename handling
        if not has_filename_sanitization:
            # Check for the specific vulnerable pattern
            vulnerable = "workspace / filename" in source or 'workspace / file' in source
            assert not vulnerable, (
                "Input files are written to 'workspace / filename' without "
                "sanitizing the filename. A filename like '../../etc/cron.d/x' "
                "writes outside the workspace before Docker container starts."
            )


# =============================================================================
# API SECURITY — MISSING RESPONSE HEADERS
# =============================================================================


class TestR14_HDR01_NoSecurityHeaders:
    """P0: No security headers middleware. The application does not set:
    - X-Content-Type-Options: nosniff
    - X-Frame-Options: DENY
    - Strict-Transport-Security: max-age=...
    - Content-Security-Policy: default-src 'self'
    - X-XSS-Protection: 0 (modern recommendation)
    - Cache-Control: no-store (for API responses)
    - Referrer-Policy: strict-origin-when-cross-origin

    These headers are required by OWASP Secure Headers Project.
    """

    def test_security_headers_middleware_exists(self):
        main_source = _read(_MAIN_PATH)
        error_source = _read(_ERROR_HANDLER_PATH)

        has_security_headers = any(
            kw in main_source or kw in error_source
            for kw in [
                "X-Content-Type-Options",
                "X-Frame-Options",
                "Content-Security-Policy",
                "SecurityHeadersMiddleware",
                "security_headers",
                "Strict-Transport-Security",
            ]
        )
        assert has_security_headers, (
            "Application has no security response headers middleware. "
            "Missing X-Content-Type-Options, X-Frame-Options, CSP, HSTS. "
            "This enables MIME-sniffing, clickjacking, and content injection."
        )


class TestR14_HDR02_NoCORSConfiguration:
    """P0: No CORSMiddleware is configured. The FastAPI app has no CORS
    policy, which means:
    - In development: frontend on localhost:3000 cannot call API on :8000
    - In production: either CORS fails or a proxy bypasses it entirely
    - No explicit allow_origins means implicit browser-default (same-origin)

    The app SHOULD have explicit CORSMiddleware with restricted origins.
    """

    def test_cors_middleware_configured(self):
        source = _read(_MAIN_PATH)
        has_cors = "CORSMiddleware" in source or "cors" in source.lower()
        assert has_cors, (
            "No CORSMiddleware configured. Frontend at localhost:3000 cannot "
            "call the API at localhost:8000. Must add CORSMiddleware with "
            "explicit allow_origins for demo and production."
        )


# =============================================================================
# AUTHORIZATION GAPS
# =============================================================================


class TestR14_AUTH01_DocumentEndpointsMissingAuth:
    """P1: Document restore/version endpoints lack authorization checks.

    POST /documents/{doc_id}/restore/{version} — no tenant check, no
    admin check. Any authenticated user can restore any document version.
    GET /documents/{doc_id}/versions — no tenant check.
    GET /documents/operations/log — no tenant check; returns ALL logs.
    GET /documents/statistics — no tenant check.
    """

    def test_restore_requires_tenant_or_admin(self):
        source = _read(_DOC_MGMT_ROUTES_PATH)
        # Find the restore_document_version function
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if node.name == "restore_document_version":
                    body_src = ast.get_source_segment(source, node)
                    assert body_src is not None
                    has_auth = (
                        "tenant" in body_src.lower()
                        or "admin" in body_src.lower()
                        or "get_current_tenant" in body_src
                        or "_require_admin" in body_src
                    )
                    assert has_auth, (
                        "restore_document_version has no authorization check — "
                        "any authenticated user can restore any document to "
                        "any version across all tenants"
                    )
                    return
        pytest.fail("Could not find restore_document_version function")


class TestR14_AUTH02_LLMConfigNoAuth:
    """P1: POST /query/config and POST /query/switch-model allow any
    authenticated user to change LLM configuration and switch models
    globally. These affect ALL users — there's no admin check or
    per-tenant isolation.
    """

    def test_llm_config_update_requires_admin(self):
        source = _read(_ENHANCED_QUERY_PATH)
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if node.name == "update_llm_config":
                    body_src = ast.get_source_segment(source, node)
                    assert body_src is not None
                    has_admin_check = any(
                        kw in body_src
                        for kw in ["admin", "require_admin", "roles", "permission"]
                    )
                    assert has_admin_check, (
                        "update_llm_config has no admin check — any authenticated "
                        "user can change global LLM temperature, max_tokens, top_p "
                        "for all users"
                    )
                    return
        pytest.fail("Could not find update_llm_config function")


class TestR14_AUTH03_SwitchModelNoAuth:
    """P1: POST /query/switch-model allows changing the active model
    without any role/admin check.
    """

    def test_switch_model_requires_admin(self):
        source = _read(_ENHANCED_QUERY_PATH)
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if node.name == "switch_model":
                    body_src = ast.get_source_segment(source, node)
                    assert body_src is not None
                    has_admin_check = any(
                        kw in body_src
                        for kw in ["admin", "require_admin", "roles", "permission"]
                    )
                    assert has_admin_check, (
                        "switch_model has no admin check — any authenticated user "
                        "can switch the active LLM model for all users"
                    )
                    return
        pytest.fail("Could not find switch_model function")


class TestR14_AUTH04_AdminKeyTimingAttack:
    """P1: _require_admin in cost_estimation_routes uses '!=' for key
    comparison, which is vulnerable to timing attacks. Should use
    hmac.compare_digest for constant-time comparison.
    """

    def test_admin_key_uses_constant_time_compare(self):
        source = _read(_COST_EST_ROUTES_PATH)
        # Find _require_admin function
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name == "_require_admin":
                body_src = ast.get_source_segment(source, node)
                assert body_src is not None
                uses_constant_time = any(
                    kw in body_src
                    for kw in ["compare_digest", "hmac", "secrets.compare_digest"]
                )
                assert uses_constant_time, (
                    "_require_admin uses '!=' for admin key comparison, which is "
                    "vulnerable to timing attacks. Use hmac.compare_digest() "
                    "for constant-time string comparison."
                )
                return
        pytest.fail("Could not find _require_admin function")


# =============================================================================
# ERROR / INFORMATION DISCLOSURE
# =============================================================================


class TestR14_ERR01_ExceptionStrInResponse:
    """P1: Multiple route handlers expose raw exception messages in
    HTTP responses via f"Internal server error: {str(e)}". This leaks:
    - Database connection strings and table names
    - File paths on the host system
    - Library versions and internal class names
    - SQL query fragments
    """

    def test_no_raw_exception_in_500_responses(self):
        # Check multiple route files for the pattern
        files_with_leak = []
        for path, name in [
            (_ENHANCED_QUERY_PATH, "enhanced_query_routes"),
            (_DOC_MGMT_ROUTES_PATH, "document_management_routes"),
            (_FEEDBACK_ROUTES_PATH, "feedback_routes"),
        ]:
            source = _read(path)
            # Pattern: detail=f"...: {str(e)}" or detail=f"...{e}"
            if re.search(r'detail=f"[^"]*\{str\(e\)\}"', source) or \
               re.search(r'detail=f"[^"]*\{e\}"', source):
                files_with_leak.append(name)

        assert not files_with_leak, (
            f"Raw exception messages exposed in HTTP 500 responses in: "
            f"{files_with_leak}. Patterns like detail=f'Internal server error: "
            f"{{str(e)}}' leak database info, file paths, and class names. "
            f"Use generic messages; log details server-side only."
        )


class TestR14_ERR02_PromptRoutes500LeaksSQLErrors:
    """P1: prompt_routes.py catches Exception and returns detail=str(e)
    on line 233, 273, 314, etc. For database errors, this leaks the
    full SQL query, table schema, and PostgreSQL error details.
    """

    def test_prompt_routes_no_raw_exception(self):
        source = _read(_PROMPT_ROUTES_PATH)
        # Count occurrences of detail=str(e) in 500 error paths
        leaky_patterns = re.findall(r'detail=str\(e\)', source)
        assert len(leaky_patterns) == 0, (
            f"prompt_routes.py has {len(leaky_patterns)} instances of "
            f"detail=str(e) in error handlers. This leaks SQL errors, "
            f"table names, and connection details to API callers."
        )


class TestR14_ERR03_AuthTokenErrorLeak:
    """P1: GET /auth/me returns f"Invalid token: {exc}" which leaks
    JWT library error details (algorithm mismatch, key info, etc.).
    """

    def test_auth_me_no_token_details(self):
        source = _read(_AUTH_ROUTES_PATH)
        # Find the me() function
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if node.name == "me":
                    body_src = ast.get_source_segment(source, node)
                    assert body_src is not None
                    has_token_leak = "Invalid token: {exc}" in body_src or \
                                     "Invalid token: {e}" in body_src
                    assert not has_token_leak, (
                        "GET /auth/me leaks JWT error details in response: "
                        "'Invalid token: {exc}'. This reveals algorithm info, "
                        "key type, and library internals. Use a generic message."
                    )
                    return
        pytest.fail("Could not find me() function")


class TestR14_ERR04_IntentClassifyLeaksInternals:
    """P1: POST /intent/classify returns f"Internal classification
    error: {str(e)}" in the response body (not via HTTPException, but
    directly in ClassifyResponse.error). This bypasses the error_handler
    middleware's sanitization.
    """

    def test_classify_error_not_raw(self):
        source = _read(_INTENT_ROUTES_PATH)
        has_raw_error = 'f"Internal classification error: {str(e)}"' in source
        assert not has_raw_error, (
            "POST /intent/classify returns raw exception in ClassifyResponse.error: "
            "'Internal classification error: {str(e)}'. This bypasses the "
            "error_handler middleware and leaks internal details."
        )


# =============================================================================
# SSRF (Server-Side Request Forgery)
# =============================================================================


class TestR14_SSRF01_PPIOBaseURLFromConfig:
    """P1: PPIOExecutionProvider.base_url comes from settings (env var)
    which is safe. BUT the _resolve_url method (line 231-237) accepts
    paths that start with http:// or https:// and returns them directly,
    bypassing the base_url entirely:

        def _resolve_url(self, path: str) -> str:
            cleaned = (path or "").strip()
            if cleaned.startswith("http://") or cleaned.startswith("https://"):
                return cleaned     # <-- ANY URL passes through

    If the execute_path or health_path config values are set to an
    attacker-controlled URL (via env var injection), the PPIO provider
    makes HTTP requests to arbitrary hosts.
    """

    def test_resolve_url_restricts_absolute_urls(self):
        source = _read(_PPIO_PROVIDER_PATH)
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name == "_resolve_url":
                body_src = ast.get_source_segment(source, node)
                assert body_src is not None
                # The method should either reject absolute URLs or validate
                # they match the configured base_url host
                allows_any_url = (
                    'return cleaned' in body_src
                    and 'startswith("http' in body_src
                )
                has_host_validation = any(
                    kw in body_src
                    for kw in ["urlparse", "hostname", "netloc", "base_url"]
                )
                if allows_any_url:
                    assert has_host_validation, (
                        "_resolve_url returns ANY absolute URL without host "
                        "validation. If execute_path is set to an attacker-"
                        "controlled URL, the server makes requests to arbitrary "
                        "hosts (SSRF). Validate hostname matches base_url."
                    )
                return
        pytest.fail("Could not find _resolve_url method")


# =============================================================================
# DOCKER TIMEOUT ENFORCEMENT
# =============================================================================


class TestR14_DOCK01_NoContainerStopTimeout:
    """P1: DockerExecutor._run_container uses container.wait(timeout=...)
    which raises on timeout (ConnectionError), but does NOT call
    container.stop() or container.kill() in the exception handler.
    The finally block calls container.remove(force=True), but if the
    timeout exception is a ReadTimeout from the Docker SDK, the container
    may still be running when remove is called. Docker's remove with
    force=True sends SIGKILL, but there's a race window where the
    container consumes resources.

    More critically: the Docker daemon's own timeout is not set via
    --stop-timeout. The container could run indefinitely if the SDK's
    wait() hangs or the network connection to dockerd is slow.
    """

    def test_container_killed_on_timeout(self):
        source = _read(_DOCKER_EXEC_PATH)
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name == "_run_container":
                body_src = ast.get_source_segment(source, node)
                assert body_src is not None
                has_stop_or_kill = any(
                    kw in body_src
                    for kw in ["container.stop", "container.kill", "stop_timeout"]
                )
                assert has_stop_or_kill, (
                    "_run_container does not call container.stop() or "
                    "container.kill() on timeout. The finally block uses "
                    "remove(force=True), but there's a race window where "
                    "the container runs unchecked. Add explicit stop/kill."
                )
                return
        pytest.fail("Could not find _run_container method")


# =============================================================================
# INPUT VALIDATION GAPS
# =============================================================================


class TestR14_INP01_FeedbackWeightUnbounded:
    """P1: FeedbackRequest.feedback_weight has no upper bound (default 1.0
    but no Field(le=...)). A malicious user can submit feedback_weight=999999
    to dominate the feedback-based weight adjustment.
    """

    def test_feedback_weight_has_upper_bound(self):
        source = _read(_FEEDBACK_ROUTES_PATH)
        # Check FeedbackRequest class
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef) and node.name == "FeedbackRequest":
                body_src = ast.get_source_segment(source, node)
                assert body_src is not None
                has_upper_bound = "le=" in body_src or "lt=" in body_src
                # Also check if feedback_weight has max validation
                if "feedback_weight" in body_src:
                    assert has_upper_bound, (
                        "FeedbackRequest.feedback_weight has no upper bound. "
                        "A user can submit feedback_weight=999999 to dominate "
                        "the adaptive search weight calculation."
                    )
                return
        pytest.fail("Could not find FeedbackRequest class")


class TestR14_INP02_OperationLogLimitUnbounded:
    """P1: GET /documents/operations/log has limit parameter with no
    upper bound (default=50 but no max). A request with limit=1000000
    could return the entire operation log, causing memory pressure.
    """

    def test_operation_log_limit_bounded(self):
        source = _read(_DOC_MGMT_ROUTES_PATH)
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if node.name == "get_operation_log":
                    body_src = ast.get_source_segment(source, node)
                    assert body_src is not None
                    # Check function signature for Query(le=...) or similar
                    has_limit = "le=" in body_src or "max(" in body_src or "min(" in body_src
                    assert has_limit, (
                        "get_operation_log 'limit' parameter has no upper bound. "
                        "limit=1000000 could return entire audit log. "
                        "Add Query(..., le=500) or clamp with min()."
                    )
                    return
        pytest.fail("Could not find get_operation_log function")


class TestR14_INP03_FeedbackDaysUnbounded:
    """P1: GET /feedback/statistics has 'days' parameter with no
    validation (no ge/le constraints). A request with days=-1 or
    days=999999 could cause unexpected SQL behavior.
    """

    def test_feedback_days_has_bounds(self):
        source = _read(_FEEDBACK_ROUTES_PATH)
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if node.name == "get_feedback_statistics":
                    body_src = ast.get_source_segment(source, node)
                    assert body_src is not None
                    has_bounds = "ge=" in body_src or "le=" in body_src or "Query(" in body_src
                    assert has_bounds, (
                        "get_feedback_statistics 'days' parameter has no bounds. "
                        "days=-1 or days=999999 causes unexpected SQL behavior. "
                        "Add bounds: days: int = Query(7, ge=1, le=365)."
                    )
                    return
        pytest.fail("Could not find get_feedback_statistics function")


# =============================================================================
# RATE LIMITING / DOS
# =============================================================================


@pytest.mark.xfail(reason="R14-RL01: rate limit proxy bypass — infrastructure fix deferred")
class TestR14_RL01_RateLimitBypassViaIPSpoofing:
    """P1: Rate limiting key is f"{tenant_id}:{client_host}" where
    client_host comes from request.client.host. Behind a reverse proxy,
    this is the proxy's IP, not the real client. All users share the
    same rate limit bucket.

    The fix requires checking X-Forwarded-For or X-Real-IP headers
    when behind a known proxy, or using uvicorn's --proxy-headers flag.
    """

    def test_rate_limiter_uses_forwarded_headers(self):
        source = _read(_DEPENDENCIES_PATH)
        has_forwarded = any(
            kw in source
            for kw in [
                "X-Forwarded-For",
                "X-Real-IP",
                "forwarded",
                "proxy_headers",
                "real_ip",
            ]
        )
        assert has_forwarded, (
            "Rate limiter key uses request.client.host which is the proxy's "
            "IP behind a reverse proxy. All users share one rate limit bucket. "
            "Check X-Forwarded-For/X-Real-IP when trusted proxy is configured."
        )


# =============================================================================
# MEMORY STORE SQL INJECTION
# =============================================================================


@pytest.mark.xfail(reason="R14-SQL01: f-string SQL TABLE_NAME — safe constant but pattern deferred")
class TestR14_SQL01_MemoryStoreTableNameInterpolation:
    """P1: LongTermMemoryStore uses f-string interpolation for TABLE_NAME
    in SQL queries:
        f"INSERT INTO {self.TABLE_NAME} ..."
        f"SELECT ... FROM {self.TABLE_NAME} ..."

    TABLE_NAME is a class constant ('conversation_memories'), so this is
    NOT directly exploitable. However, it sets a dangerous pattern — if
    anyone subclasses LongTermMemoryStore and overrides TABLE_NAME with
    user input, it becomes SQL injection. The pattern should use
    sql.Identifier or at minimum validate TABLE_NAME format.
    """

    def test_table_name_not_fstring_interpolated(self):
        source = _read(_MEMORY_STORE_PATH)
        # Count f-string SQL with TABLE_NAME interpolation
        interpolation_count = len(
            re.findall(r'f"""[^"]*\{self\.TABLE_NAME\}', source)
        )
        if interpolation_count > 0:
            # Check if TABLE_NAME is validated
            has_validation = any(
                kw in source
                for kw in [
                    "sql.Identifier",
                    "re.match",
                    "isidentifier",
                    "TABLE_NAME_PATTERN",
                ]
            )
            assert has_validation, (
                f"LongTermMemoryStore uses f-string SQL interpolation for "
                f"TABLE_NAME in {interpolation_count} queries. While TABLE_NAME "
                f"is currently a safe constant, this pattern is dangerous if "
                f"subclassed. Use sql.Identifier() or validate format."
            )


# =============================================================================
# PASSWORD HASHING
# =============================================================================


class TestR14_PW01_SHA256NotAdequate:
    """P1: auth_routes.py uses SHA256 with a random salt for password
    hashing. While salted SHA256 is better than plaintext (which was
    fixed in a previous round), SHA256 is NOT a password hashing
    algorithm. It's fast by design, enabling rapid brute-force attacks.

    OWASP recommends bcrypt, scrypt, or Argon2id for password storage.
    SHA256 can do billions of hashes/second on a GPU.
    """

    def test_uses_proper_password_hashing(self):
        source = _read(_AUTH_ROUTES_PATH)
        has_proper_hash = any(
            kw in source
            for kw in ["bcrypt", "scrypt", "argon2", "pbkdf2", "passlib"]
        )
        assert has_proper_hash, (
            "auth_routes uses SHA256 for password hashing. SHA256 is a fast "
            "hash — GPUs can compute billions per second, enabling brute-force. "
            "Use bcrypt, scrypt, Argon2id, or PBKDF2 for password storage."
        )


# =============================================================================
# USER REGISTRATION UNBOUNDED
# =============================================================================


class TestR14_REG01_UnboundedInMemoryRegistration:
    """P1: auth_routes stores registered users in a module-level dict
    (_users). There's no limit on registrations. An attacker can
    POST /auth/register thousands of times, growing the dict
    unboundedly and consuming server memory.
    """

    def test_registration_has_limit(self):
        source = _read(_AUTH_ROUTES_PATH)
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if node.name == "register":
                    body_src = ast.get_source_segment(source, node)
                    assert body_src is not None
                    has_limit = any(
                        kw in body_src
                        for kw in [
                            "max_users",
                            "len(_users)",
                            "registration_limit",
                            "rate_limit",
                            "MAX_REGISTERED",
                        ]
                    )
                    assert has_limit, (
                        "User registration has no limit on the in-memory _users "
                        "dict. Attacker can POST /auth/register thousands of "
                        "times to exhaust server memory. Add a max user count."
                    )
                    return
        pytest.fail("Could not find register function")
