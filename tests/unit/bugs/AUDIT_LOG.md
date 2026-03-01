# TDI Audit Log — Industry AI Flow

Round-over-round metrics for Test-Driven Improvement cycles.

| Round | Date       | Bugs Found | P0 | P1 | Fixed | Tests Added | New Patterns |
|-------|------------|-----------|----|----|-------|-------------|-------------|
| 5-7   | 2026-02-24 | 70        | 8  | 18 | 14    | ~50         | 12          |
| 8     | 2026-02-25 | 5         | 0  | 5  | 5     | 9           | 1           |
| 9     | 2026-02-25 | 8         | 0  | 8  | 8     | 9           | 2           |
| 10    | 2026-02-25 | 14        | 2  | 12 | 14    | 14          | 3           |
| 11    | 2026-02-26 | 13        | 0  | 13 | 13    | 19          | 2           |
| 12    | 2026-02-26 | 7         | 0  | 7  | 7     | 12          | 1           |
| 13    | 2026-02-27 | 21        | 4  | 17 | 21    | 21          | 4           |
| 14    | 2026-02-27 | 51        | 8  | 25 | 42    | 51          | 10          |
| 15    | 2026-02-26 | 41        | 1  | 10 | 11    | 11          | 11          |
| 16    | 2026-02-26 | 46        | 1  | 18 | 19    | 22          | 19          |
| 17    | 2026-02-26 | 37        | 1  | 13 | 14    | 16          | 8           |
| 18    | 2026-02-27 | 14        | 1  | 9  | 10    | 12          | 3           |
| 19    | 2026-02-27 | 67        | 3  | 31 | 13    | 14          | 12          |
| 20    | 2026-02-27 | 10        | 0  | 8  | 10    | 3           | 4           |
| 21    | 2026-02-27 | 3         | 0  | 0  | 3     | 0           | 0           |
| 22    | 2026-02-27 | 5         | 0  | 0  | 5     | 0           | 1           |
| 23    | 2026-02-27 | 4         | 0  | 0  | 4     | 0           | 1           |
| 24    | 2026-02-27 | 1         | 0  | 0  | 1     | 0           | 1           |
| 28    | 2026-02-27 | 2         | 0  | 2  | 2     | 3           | 2           |
| 29    | 2026-02-27 | 6         | 0  | 3  | 6     | 0           | 3           |
| 30    | 2026-02-27 | 2         | 0  | 1  | 2     | 3           | 2           |
| 31    | 2026-02-28 | 1         | 0  | 1  | 1     | 3           | 3           |
| 32    | 2026-02-28 | 1         | 0  | 1  | 1     | 3           | 2           |

## Convergence

- Round 11: 13 P1 (no P0). Still above the <3 threshold for two consecutive rounds.
- Round 12: 7 P1 (no P0). Trending down (13 → 7). Still above <3 threshold.
- Round 13: 21 bugs (4 P0 + 17 P1). Deeper audit found new categories (memory management, dispatch governance, pipeline ordering). Bug count went UP because auditors explored previously unexamined areas (memory store, dispatch confidence, pipeline node ordering). Not convergent — continue TDI.
- Round 14: 51 bugs (8 P0 + 25 P1 + 18 P2) across 4 parallel audit agents. 42 fixed, 9 deferred as xfail (architectural changes in LangGraph workflow, module-level singleton, thread-safety refactors). Broadest audit yet: security headers, CORS, validator bypasses, retrieval node double-execution, cost estimation routing, EN placeholder contamination, error disclosure, Docker symlinks, rate limiter races, regex precision. Not convergent — continue TDI.
- Round 15: 41 bugs (1 P0 + 10 P1 + 20 P2 + 10 P3) across 4 parallel audit agents. All 11 P0/P1 fixed and verified. P0 count dropped from 8→1. P1 count dropped from 25→10. Focus areas: intent workflow dispatch crash, security admin key bypass, chunker content duplication, rate-limit TOCTOU, column-name injection in template code, module-level asyncio.Lock, dead clarification retry branch, unbounded chat payload. 30 P2/P3 deferred. Trending toward convergence but not yet <3 P0+P1 for two consecutive rounds.
- Round 16: 46 bugs (1 P0 + 18 P1 + 17 P2 + 10 P3) across 4 parallel audit agents. All 19 P0/P1 fixed and verified. 22 tests added. P0 count: 1 (same as R15). P1 count: 18 (up from 10 — deeper audit into previously unexamined areas: code validator whitelisted-library escapes, groundedness tokenizer inconsistency, BM25 dotted-standard splitting, numeric penalty for derived arithmetic, Jinja2 HTML-escaping of LLM prompts, CRLF code extraction, error dict propagation). 27 P2/P3 deferred. Not convergent — auditors continue finding novel patterns in unexplored areas.
- Round 17: 37 bugs (1 P0 + 13 P1 + 17 P2 + 6 P3) across 4 parallel audit agents. All 14 P0/P1 fixed and verified. 16 tests added. P0 count: 1 (same as R15/R16 — clarification loop). P1 count: 13 (down from 18). Focus areas: infinite clarification loop (P0), budget force_local bypass, keyword priority misrouting, broken preprocessing regex, BM25 dotted token loss, document replacement rollback, unbounded chunk growth, timing-safe password comparison, metaclass hook validator bypass, atexit/_thread blacklist, QueryRequest validation, A/B cache defeat, unified agent EN placeholder contamination (keywords + system prompt). 23 P2/P3 deferred. Trending down (P1: 18→13). Not yet <3 P0+P1 for two consecutive rounds — continue TDI.
- Round 18: 14 bugs (1 P0 + 9 P1 + 4 P2) via manual audit. All 10 P0/P1 fixed and verified. 12 tests added. P0 count: 1 (workflow_query_routes response key mismatch — fallback runner sets "response" but handler reads "agent_response"). P1 count: 9 (down from 13). Focus areas: f-string validator bypass, bleach sanitization on un-decoded input, intent routing precision ("analyze costs" misroute, "analyze" too broad), hardcoded 4096 context window, __reduce__/__reduce_ex__ pickle exploit, response_builder None fallthrough, error detail leakage, missing embedding quality signal. 4 P2 deferred. Trending down (P0+P1: 14→10). Not yet <3 P0+P1 for two consecutive rounds — continue TDI.
- Round 19: 67 bugs (3 P0 + 31 P1 + 26 P2 + 7 P3) across 4 parallel audit agents. 13 P0/P1 fixed and verified, 14 tests added. Broadest audit yet with 4 deep-dive agents. P0 count: 3 (phantom module import in intent_node, partial state corruption on timeout, file_path disclosure in uploads). P1 count: 31 (across security/validator: functools string bypass, walrus operator alias, df.pipe/apply/agg callable dispatch, while-1 detection, scipy.io.loadmat; intent: heuristic preamble pollution, SimpleIntentClassifier broad keywords; cost estimation: num_units regex false positives; prompt: A/B cache pollution; data analysis: template column selection). 54 P2/P3 deferred. Bug count up because deepest audit coverage yet (4 dedicated agents exploring every file). Not convergent — continue TDI.
- Round 20: 10 findings (0 P0 + 8 P1 + 2 regression-test drift) discovered via full unit gate walk with iterative `-x` triage. All 10 fixed and verified. Key fixes: optional dependency import hardening (`uvicorn`/`Pillow`/`fitz`), stale Round3 regression assertions updated to current secure behavior, DataAnalysisAgent compatibility hook restored for historical monkeypatch contract, spaced-number area parsing (`5 000 square feet`), budget phrase extraction (`budget 120m`), and workflow error-first response behavior when stale responses exist. Unit gate advanced from first failure at ~38% to >61% before next independent failure class, with all targeted and regression bundles passing.
- Round 21: 3 regression-test drift findings (0 P0 + 0 P1) discovered in continued `tests/unit -x` sweep. All 3 fixed and verified by restoring correct test payload semantics: two Chinese-input rejection tests were using English text, and one intent-node test retained `EN` placeholders from i18n migration. Post-fix gate result: `tests/unit` passed end-to-end (`507 passed, 8 xfailed, 1 xpassed`).
- Round 22: 5 test-contract compatibility findings (0 P0 + 0 P1) discovered while extending sweep to `tests/integration`, full `tests`, and `test-release-gate`. All 5 fixed and verified. Fixes covered: admin-key enforcement drift on cost-estimation training integration tests, sanitized prediction error-detail assertions, missing async marker for EDA integration test, prompt-node no-op contract update (no internal error leakage), and Python 3.13 event-loop API compatibility (`asyncio.run` replacing `get_event_loop().run_until_complete`). Gate results: `tests` full pass (`592 passed, 1 skipped, 8 xfailed, 1 xpassed`) and `make test-release-gate` pass.
- Round 23: 4 test-hygiene/compatibility findings (0 P0 + 0 P1) discovered in continued full-suite sweeps. All 4 fixed and verified: registered missing `cache` marker at runtime pytest config layer, removed unhandled thread-exception warning in RAG thread-leak regression test, normalized EDA/performance probe tests to pytest-native semantics (assert/skip wrappers instead of returning values), and cleaned transient generated probe artifacts from repo root. Full-suite result after fixes: `586 passed, 7 skipped, 8 xfailed, 1 xpassed`.
- Round 24: 1 high-fanout runtime-compatibility finding (0 P0 + 0 P1) fixed in shared logging path: replaced deprecated `datetime.utcfromtimestamp()` usage with timezone-aware `datetime.fromtimestamp(..., UTC)` in JSON logging formatter. Full-suite result remained green (`586 passed, 7 skipped, 8 xfailed, 1 xpassed`) while warnings dropped sharply (`422 → 116`).
- Round 25: 8 test-hygiene/runtime-compatibility findings (0 P0 + 0 P1) fixed while continuing post-R24 stabilization. Changes: removed 5 obsolete Chinese-specific legacy suites from active test paths (`tests/integration|unit|performance`) for the English-only project profile, refactored script-style unit probes (`test_code_execution.py`, `test_document_processing.py`) into pytest-native assert/skip contracts with `tmp_path`-based isolation, converted remaining `datetime.utcnow()` usages in shared/runtime-touched paths (`memory/manager.py`, prompt demo script, prompt API integration test), and quarantined manual local environment diagnostics behind module-level skip marks. Full-suite result after fixes: `560 passed, 27 skipped, 8 xfailed, 1 xpassed`; warning count reduced further (`116 → 79`).
- Round 26: 1 warning-signal hygiene finding (0 P0 + 0 P1) fixed by adding precise `filterwarnings` marks to two legacy dynamic-code bug-repro suites that emit unavoidable `<string>:5` `utcnow` deprecation noise during simulated execution. Full-suite result remained green (`560 passed, 27 skipped, 8 xfailed, 1 xpassed`) and warning count dropped to near-clean baseline (`79 → 4`), leaving only benign `PytestCollectionWarning` dataclass collection notices.
- Round 27: 2 hardening findings fixed in continued post-gate audit (0 P0 + 1 P1 + 1 hygiene). P1 fix: eliminated absolute-path disclosure from `/api/v1/cost-estimation/train` missing-file error path (`404` now returns generic `"path does not exist"`), with new integration regression coverage to prevent reintroduction. Hygiene fix: removed final dataclass/class collection warnings by marking helper data containers as non-tests (`__test__ = False`) in legacy script-style suites. Full-suite result after fixes: `561 passed, 27 skipped, 8 xfailed, 1 xpassed` with zero warning output.
- Round 28: 2 security findings fixed (0 P0 + 2 P1) via targeted re-audit of deferred xfail items. Fixes: trusted-proxy-aware client IP resolution for rate limiting (`X-Forwarded-For` / `X-Real-IP` / `Forwarded` only when direct peer is trusted), and SQL identifier hardening for memory-store table names using explicit `TABLE_NAME_PATTERN` validation before interpolation. Deferred xfail debt reduced (`8 → 6`) and suite stayed green with improved signal (`487 passed, 20 skipped, 6 xfailed`).
- Round 29: 6 deferred pipeline findings closed (0 P0 + 3 P1 + 3 P2). Fixes: converted `intent_workflow` preprocessing/context-enrichment transitions to error-aware conditional routing, implemented meaningful clarification processing with query enrichment + best-effort reclassification, preserved checkpoint metadata during `continue_workflow` via merge instead of replacement, replaced module-level simple-intent singleton with lazy getter, and added lock-based synchronization for routing statistics updates/reads. Deferred xfail backlog cleared (`6 → 0`). Unit suite result: `493 passed, 20 skipped`.
- Round 30: 2 findings fixed (0 P0 + 1 P1 + 1 test-isolation hygiene). P1 fix: blocked higher-order callable reference bypasses in `CodeValidator` (`map(eval, ...)`, `sorted(..., key=eval)`, `(lambda fn: fn(...))(eval)`) by validating blocked callable references in call arguments/kwargs. Hygiene fix: removed global `sys.modules` package stubbing in `test_bug_audit_round18` that poisoned later workflow imports (`... is not a package`). Validation: `tests/unit/bugs` passed (`296 passed`) and targeted code-execution regression suite remained green.
- Round 31: 1 P1 security finding fixed in `CodeValidator` alias tracking. New bypasses validated and blocked: expression aliases (`fn = eval if True else ...`), default-argument carriers (`def run(fn=eval)`), and class-attribute alias calls (`X.fn(...)`). Added 3 regression tests and extended validator checks to detect blocked callable references in assignment expressions, default arguments, and attribute-based alias calls. Validation: `tests/unit/bugs` passed (`299 passed`) and code-execution regression tests remained green.
- Round 32: 1 P1 security finding fixed in `CodeValidator` builtin-namespace guarding. New bypasses validated and blocked: `__builtins__['eval'](...)`, `__builtins__['exec'](...)`, and `__builtins__.__getitem__('eval')(...)`. Added 3 regression tests and hardened AST validation to reject direct `__builtins__` namespace access before call-path analysis. Validation: `tests/unit/bugs` passed (`302 passed`) and code-execution regression tests remained green.

## New Patterns Discovered

### Round 30
- **Higher-order callable reference bypass in validator**: blocking direct `eval(...)`/`open(...)` calls is insufficient when blocked callables are passed as first-class values (`map(eval, ...)`, `key=eval`, lambda argument injection). Validator must inspect call arguments/kwargs recursively for blocked references.
- **Global `sys.modules` poisoning from tests**: injecting placeholder modules for package names without teardown can downgrade real packages into plain modules and trigger cascading `ModuleNotFoundError` failures in unrelated suites.

### Round 31
- **Expression-level alias bypass**: blocking only direct-name aliases (`fn = eval`) misses alias construction via conditional/bool expressions (`fn = eval if ... else ...`).
- **Default-argument carrier bypass**: blocked callables can be smuggled through function defaults (`def run(fn=eval)`), avoiding direct call checks.
- **Attribute alias invocation gap**: class/object attribute aliases (`X.fn = eval; X.fn(...)`) require attribute-call alias checks, not just name-call checks.

### Round 32
- **Builtin namespace lookup bypass**: blocked callables can be recovered via `__builtins__` subscript/lookup paths even when direct calls are denied.
- **Call-target-only filtering is insufficient**: validating only direct `ast.Name/ast.Attribute` call targets misses indirect namespace retrieval (`__getitem__` / subscript-then-call) unless namespace access itself is denied.

### Round 20
- **Optional dependency import traps in app import chain**: importing `backend.main` can transitively require runtime-only packages if imports are top-level.
- **Regression test drift as hidden failure class**: legacy bug-repro tests can fail on fixed behavior and block discovery of real regressions.
- **Feature extraction locale formatting gap**: space-grouped numerics (`5 000`) may parse in helper functions but still fail at regex capture layer.
- **Error-path stale response masking**: pipeline fallback conditions and node early-return ordering can silently preserve stale success responses after failures.

### Round 22
- **Runtime-policy test drift after security hardening**: integration tests asserting raw internal error/details or unauthenticated training paths can fail after secure contracts are tightened.

### Round 23
- **Probe-style tests returning non-None values mask intent and pollute signal**: script-like tests that return booleans/tuples instead of asserting/skip semantics create `PytestReturnNotNoneWarning` noise and can hide real pass/fail meaning.

### Round 24
- **High-fanout deprecation hotspot in shared observability path**: a single deprecated timestamp API (`utcfromtimestamp`) inside centralized log formatter can multiply into hundreds of warnings across otherwise unrelated suites.

### Round 25
- **Legacy script-style tests in active pytest paths create false confidence**: tests returning booleans/paths and relying on print output can appear "green" while bypassing assertion semantics; these should be converted to assert/skip or removed from automated suites.
- **Language-profile drift in test inventory**: historical Chinese visualization/OCR suites can silently persist in English-only delivery profiles, inflating maintenance surface and introducing irrelevant runtime dependencies.

### Round 26
- **Deprecation-noise dominance in simulation-heavy repro tests**: dynamic `exec`-style bug-repro suites can emit repetitive third-party/runtime deprecations that overwhelm warning signal; targeted per-module filters are preferable to global suppression.

### Round 27
- **Validation-path filesystem disclosure**: returning resolved absolute paths in client-visible 404 details (`path does not exist: /abs/path`) leaks host filesystem topology and should be replaced with generic user-safe errors plus server-side logging if needed.

### Round 28
- **Proxy-aware rate-limit keying requires trust boundary**: forwarded headers should influence client identity only when the immediate peer is a trusted proxy; otherwise spoofed headers can evade or distort per-client quotas.
- **Constant SQL identifiers still need explicit guardrails**: class constants used in SQL identifier interpolation should be validated by a strict identifier pattern to prevent unsafe subclass/override drift.

### Round 29
- **Early-node failures need explicit edge-level routing**: if preprocessing/enrichment nodes can set `state["error"]`, unconditional graph edges silently continue execution and bury the original fault.
- **Workflow continuation must merge checkpoint metadata**: continuation updates that replace `metadata` wholesale can erase prior intent/routing context and degrade follow-up behavior.
- **Shared routing telemetry requires synchronization**: per-request stats mutation without a lock can lose counters under concurrent traffic.

### Round 19
- **Phantom module import degradation**: `from backend.services.intent_classification.models import QueryContext` imports a nonexistent module — silently falls back to passing raw dict where dataclass expected
- **functools.reduce(str.__add__) string construction**: Whitelisted `functools` enables `reduce(str.__add__, ["e","x","e","c"])` to build "exec" bypassing chr/bytes/bytearray blocklist
- **Walrus operator (ast.NamedExpr) alias bypass**: `(fn := open)('test.txt')` creates alias via NamedExpr not tracked by ast.Assign-based alias detection
- **df.pipe()/df.apply()/df.agg() callable dispatch**: Pandas methods that accept arbitrary callables were not in BLOCKED_METHOD_NAMES
- **while 1: vs while True detection**: `_check_loops` used `is True` identity check, missing the most common Python infinite loop idiom `while 1:`
- **Upload response file_path disclosure**: Both document and data upload endpoints returned full server filesystem paths in JSON response payloads
- **Heuristic prompt preamble pollution**: `_simulate_llm_response` searched keywords in the full classification prompt including "cost_estimation" in the intent list preamble, causing universal false match
- **Overly broad SimpleIntentClassifier keywords**: Bare words "run", "process", "batch", "function", "compute" in CODE_EXECUTION keywords match common construction terminology
- **num_units regex false positive**: Bare `units?` alternation extracts "unit cost of 500" as num_units=500 and "homes for 200 people" as num_units=200
- **A/B experiment cache write pollution (incomplete R17 fix)**: R17 fixed the cache read path but the write path still caches experiment variants under the generic key, polluting non-experiment reads
- **Template column selection inconsistency**: `_template_count` and `_template_percentage` always pick `categorical_cols[0]` while `_template_average` uses `_pick_relevant_column` with the user question
- **Health check error detail leakage**: `/query/health` endpoint exposes raw `str(e)` in unhealthy status values

### Round 18
- **Workflow response key mismatch**: graph.py fallback runner sets `state["response"]` but `workflow_query_routes.py` reads `result.get("agent_response")` — user gets None response when fallback orchestrator is used
- **f-string expression validator bypass**: `f"{__import__('os').getcwd()}"` and `f"{eval('1+1')}"` bypass all validator checks because dangerous calls inside `ast.FormattedValue` nodes are invisible to both regex patterns and top-level AST call walking
- **bleach.clean on un-decoded input**: `sanitize_text` URL-decodes iteratively for pattern checks but passes original `stripped` (not `decoded`) to `bleach.clean` — double-encoded HTML entities survive sanitization

### Round 17
- **Infinite clarification loop via unconditional clarification_handled**: `_clarification_processing_node` always sets `clarification_handled=True` in both branches, causing `_route_after_clarification` to always return `retry_classification` even without new user input — infinite loop capped only by LangGraph's recursion_limit (25 wasted LLM calls)
- **Budget force_local returns allowed=True**: `evaluate_budget` returns `"allowed": policy.policy_mode != "block"` — for `local_only` mode, this evaluates to True, meaning dispatch_service proceeds with cloud calls despite the budget hard limit
- **Keyword priority ordering in heuristic fallback**: `_simulate_llm_response` checks knowledge_retrieval keywords ("how to", "what is") before cost_estimation — queries like "how to estimate construction cost" misroute to RAG
- **Broken _preprocess_input regex**: Unescaped `[]` in character class `[^\w\s\u4e00-\u9fff.,!?;:()[]{}"\'-]` prematurely closes the class — regex matches nothing, special characters never removed
- **BM25 tokenizer drops dotted tokens**: Post-tokenization filter only keeps `isalnum()` or hyphenated tokens — dotted references like `nbc2020.4` fail both checks and are silently dropped from BM25 index
- **Metaclass hooks bypass code validator**: `__init_subclass__`, `__set_name__`, `__prepare__` execute at class definition time, not at call time — neither regex patterns nor AST call validators detect them
- **atexit/_thread not in BLACKLISTED_IMPORTS**: `atexit.register()` runs callbacks after sandbox timeout; `_thread` (low-level) bypasses the `threading` blacklist
- **A/B experiment cache defeats traffic split**: `get_prompt` caches under generic `{category}:{name}` key regardless of experiment state — first caller's variant served to all subsequent callers until cache TTL expires

### Round 16
- **pd.eval()/df.query() sandbox escape via whitelisted library**: Pandas is whitelisted for data analysis, but `pd.eval(engine='python')` and `df.query()` evaluate arbitrary Python expressions — dangerous payload hides inside string literals invisible to AST validation
- **bytes()/bytearray() name construction**: `bytes([101,118,97,108]).decode()` builds "eval" at runtime — neither `bytes` nor `bytearray` were in BLOCKED_CALL_NAMES
- **Groundedness node tokenizer divergence**: Workflow groundedness_node used `.split()` while GroundednessChecker used proper regex tokenizer — inconsistent scoring with punctuation-attached tokens
- **BM25 dotted standard splitting**: Regex tokenizer `[a-z0-9]+(?:-[a-z0-9]+)*` splits "CSA A23.1" at the period, destroying precision for construction standard references
- **Min-max normalization zero floor**: Scaling to [0, 1] always gives worst result 0.0 even when it had positive fusion score — misleads reranker and UI
- **Numeric penalty on derived arithmetic**: Groundedness checker penalizes numbers derived from context via multiplication (e.g., 30000 * 50 = 1500000)
- **Jinja2 autoescape HTML-mangles LLM prompts**: `autoescape=True` escapes `<`, `>`, `&` in prompts sent to LLMs — domain mismatch (HTML escaping for non-HTML output)
- **CRLF code extraction failure**: `code_pattern = r"```python\n"` requires Unix LF — cloud LLMs frequently return CRLF
- **Error dict truthy propagation**: `_extract_dataset_info` returns `{"error": "..."}` which is truthy, passes `if not dataset_metadata`, and silently becomes metadata for code generation
- **COST_ESTIMATION→DataAnalysisAgent mapping**: IntentClassifier._get_agent_type had wrong agent for cost estimation (different from routing_decision.py fix in R14)
- **Clarification prompt discards prompt_manager content**: `get_clarification_prompt` fetches prompt but unconditionally returns simulated response
- **Bare "how much"/"price" false positive**: Matches non-cost queries like "how much water does concrete curing require?"
- **Hardcoded 4096 context window for all backends**: Cloud backends with 128K context unnecessarily truncated
- **Bare "cost" regex in estimated_cost_cad**: Matches "cost overrun 10%" extracting 10 as estimated_cost_cad
- **switch_model admin key presence-only check**: Same pattern as R15 admin key bypass, in a different endpoint
- **Error detail leakage in 6 intent classification endpoints**: `str(e)` returned in error responses
- **Legacy executor workspace_path disclosure**: Full server paths exposed in API responses
- **DocumentVersionResponse filepath disclosure**: Server filesystem paths in version response schema
- **np.load(allow_pickle=True) deserialization**: NumPy whitelisted but np.load can deserialize pickle payloads

### Round 15
- **COST_ESTIMATION_AGENT stub dispatch crash**: Intentional `response=""` return from `_dispatch_to_agent` for cost estimation always triggers `RuntimeError("Agent returned empty response")` — two workflow systems (intent_workflow vs graph.py) have incompatible cost estimation paths
- **Chunker construction-reference double-append**: When `_is_construction_reference()` fires at a chunk boundary, `split` is appended both inside the if-branch AND unconditionally at the end of the for-loop body — duplicating content
- **Dead clarification retry_classification branch**: Graph edge `retry_classification → intent_classification` is registered but `_route_after_clarification` never returns `"retry_classification"`, making user clarification structurally ignored for re-classification
- **Rate-limit window TOCTOU**: `cloud_window.append(now)` after cloud call executes outside `_rate_limit_lock`, allowing concurrent threads to both pass the rate check and both append
- **hybrid_auto soft_fail gated by fallback_on_error**: `if soft_fail and settings.fallback_on_error:` — soft_fail was never sufficient alone; local failure propagates when `FALLBACK_ON_ERROR=false`
- **Admin key presence-only check**: `if not admin_key:` grants admin access to any non-empty string — no `hmac.compare_digest` against a configured secret
- **Restore endpoint tenant auth bypass**: `restore_document_version` manually reads X-Tenant-ID header instead of using `Depends(get_current_tenant)`, bypassing the standardized auth chain
- **Unbounded chat message payload**: `messages: List[Dict[str, str]] = Body(...)` with no `max_items` or content length — enables OOM/DoS
- **Module-level asyncio.Lock()**: `_workflow_lock = asyncio.Lock()` at module import time can bind to wrong event loop in multi-worker deployments
- **prompt_node dead guard exposes internal message**: `state["error"] = "prompt_manager service is required"` leaks implementation detail to users
- **Column name injection in template code**: CSV column names interpolated via f-string `df['{target_col}']` into executable Python without sanitization — full code injection vector

### Round 14
- **String obfuscation via codecs**: `codecs.decode('bfrff','rot13')` reconstructs any string without triggering regex patterns — codecs module not in BLACKLISTED_IMPORTS enables bypassing all pattern-based security
- **chr() dynamic name construction**: `chr(95)+chr(95)+'import'+chr(95)+chr(95)` builds dunder names character-by-character, evading both regex and AST-level dunder pattern checks
- **Missing security response headers**: No CORSMiddleware, no X-Content-Type-Options, no X-Frame-Options, no CSP — fundamental web security hygiene absent from the middleware stack
- **Admin-level endpoints without authorization**: LLM config change, model switch, document restore all affect all users but have no admin/role check — only API key authentication (shared by all users)
- **Error detail leakage via non-HTTPException paths**: Intent classification and other routes return raw exception strings in response body fields (not via HTTPException), bypassing the error_handler middleware's sanitization
- **Async/sync detection double-execution**: Eagerly calling a method then checking if awaitable causes synchronous methods to execute twice — use inspect.iscoroutinefunction() BEFORE calling
- **Agent-type misrouting**: Intent-to-AgentType mapping routing cost_estimation to GENERAL_AGENT which dispatches to RAG — specialized intents need dedicated agent types
- **i18n placeholder contamination of scoring**: ~95 "EN" marker strings from incomplete i18n migration poison substring-based keyword matching in intent classification
- **Zero-score RRF pollution**: Including zero-score BM25 results in RRF fusion gives irrelevant documents non-zero fusion scores from their arbitrary rank
- **No-catch inference pattern**: ML model inference wrapped in "check availability first" misses runtime errors (OOM, encoding) during actual inference

### Round 13
- **Snapshot mutation isolation**: Summary updates written to a deep-copy snapshot are silently lost because they're never propagated back to the live session object
- **IVFFlat probes replication**: Same "probes not set" bug (R10-03) reappeared in a different module (LongTermMemoryStore) — pattern: pgvector probes fix must be applied to ALL query sites, not just the primary one
- **Dunder attribute chain escape**: `object.__getattribute__` + `chr()` string construction bypasses both regex pattern matching and AST-based call detection — pattern: denylist approaches fundamentally cannot catch dynamic attribute construction
- **Pipeline ordering semantics**: Groundedness node positioned before response_node means it always scores 0.0 — pattern: pipeline stages that depend on another stage's output must be ordered after it

### Round 12
- **Systemic EN-placeholder propagation**: i18n pass converted Chinese strings to "EN" markers but left them in template methods, fallback answers, keyword matching lists, and clarification generators — affecting 4 modules across 3 packages

### Round 11
- **Container indirection bypass**: `[exec][0](...)` and `{"e": exec}["e"](...)` bypass AST-based code validators that only check `ast.Name` call targets
- **Regex `\s` + suffix false match**: `([0-9][0-9,.\s]*[kmb]?)` captures whitespace + first letter of next word as K/M/B suffix
