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

## Convergence

- Round 11: 13 P1 (no P0). Still above the <3 threshold for two consecutive rounds.
- Round 12: 7 P1 (no P0). Trending down (13 → 7). Still above <3 threshold.
- Round 13: 21 bugs (4 P0 + 17 P1). Deeper audit found new categories (memory management, dispatch governance, pipeline ordering). Bug count went UP because auditors explored previously unexamined areas (memory store, dispatch confidence, pipeline node ordering). Not convergent — continue TDI.
- Round 14: 51 bugs (8 P0 + 25 P1 + 18 P2) across 4 parallel audit agents. 42 fixed, 9 deferred as xfail (architectural changes in LangGraph workflow, module-level singleton, thread-safety refactors). Broadest audit yet: security headers, CORS, validator bypasses, retrieval node double-execution, cost estimation routing, EN placeholder contamination, error disclosure, Docker symlinks, rate limiter races, regex precision. Not convergent — continue TDI.

## New Patterns Discovered

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
