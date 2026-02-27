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

## Convergence

- Round 11: 13 P1 (no P0). Still above the <3 threshold for two consecutive rounds.
- Round 12: 7 P1 (no P0). Trending down (13 → 7). Still above <3 threshold.
- Round 13: 21 bugs (4 P0 + 17 P1). Deeper audit found new categories (memory management, dispatch governance, pipeline ordering). Bug count went UP because auditors explored previously unexamined areas (memory store, dispatch confidence, pipeline node ordering). Not convergent — continue TDI.
- Round 14: 51 bugs (8 P0 + 25 P1 + 18 P2) across 4 parallel audit agents. 42 fixed, 9 deferred as xfail (architectural changes in LangGraph workflow, module-level singleton, thread-safety refactors). Broadest audit yet: security headers, CORS, validator bypasses, retrieval node double-execution, cost estimation routing, EN placeholder contamination, error disclosure, Docker symlinks, rate limiter races, regex precision. Not convergent — continue TDI.
- Round 15: 41 bugs (1 P0 + 10 P1 + 20 P2 + 10 P3) across 4 parallel audit agents. All 11 P0/P1 fixed and verified. P0 count dropped from 8→1. P1 count dropped from 25→10. Focus areas: intent workflow dispatch crash, security admin key bypass, chunker content duplication, rate-limit TOCTOU, column-name injection in template code, module-level asyncio.Lock, dead clarification retry branch, unbounded chat payload. 30 P2/P3 deferred. Trending toward convergence but not yet <3 P0+P1 for two consecutive rounds.
- Round 16: 46 bugs (1 P0 + 18 P1 + 17 P2 + 10 P3) across 4 parallel audit agents. All 19 P0/P1 fixed and verified. 22 tests added. P0 count: 1 (same as R15). P1 count: 18 (up from 10 — deeper audit into previously unexamined areas: code validator whitelisted-library escapes, groundedness tokenizer inconsistency, BM25 dotted-standard splitting, numeric penalty for derived arithmetic, Jinja2 HTML-escaping of LLM prompts, CRLF code extraction, error dict propagation). 27 P2/P3 deferred. Not convergent — auditors continue finding novel patterns in unexplored areas.

## New Patterns Discovered

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
