# TDI Audit Log

| Round | Date | Bugs Found | Critical | High | Fixed | Graduated | New Patterns |
|-------|------|-----------|----------|------|-------|-----------|-------------|
| 5     | 2026-02-25 | 70  | 8        | 18   | 14    | pending   | 3           |
| 6     | 2026-02-25 | 25  | 8        | 17   | 13    | pending   | 2           |

## Round 6 Details

**Audit agents**: 4 parallel (RAG, Cost/Intent/Dispatch, Security/API, Workflow/Async)
**Raw findings**: 94 (deduplicated to 25 P0+P1)
**Fix strategy**: 3 parallel worktrees (Fix-RAG, Fix-Dispatch, Fix-API)
**Merge conflicts**: 4 (all resolved)
**Regressions**: 0

### Fixed (13 bugs)

| ID | Severity | Description | File |
|----|----------|-------------|------|
| BUG-A013 | P0 | Safety disclaimers corrupted EN placeholders | groundedness_checker.py |
| BUG-A014 | P0 | Refusal messages corrupted EN placeholders | groundedness_checker.py |
| BUG-A005 | P0 | Fallback embedding dim 384 vs 768 | embedder.py |
| BUG-LD02 | P0 | "EN" in text matches common English | dispatch_service.py |
| BUG-D008 | P0 | DataAnalysisAgent init crashes without LLM | data_analysis_agent.py |
| BUG-A001 | P1 | IVFFlat probes never set | vectorstore.py |
| BUG-A003 | P1 | Memory summary prompt corrupted CN | summary.py |
| BUG-A004 | P1 | Memory extraction prompt corrupted CN | extractor.py |
| BUG-A009 | P1 | Memory race condition (history_snapshot unused) | rag_engine.py |
| BUG-LD01 | P1 | Confidence purely length-based | dispatch_service.py |
| BUG-LD03 | P1 | Double fallback returns empty | dispatch_service.py |
| BUG-XC01 | P1 | shortcut_response flag sticky across turns | graph.py |
| BUG-D014 | P1 | threading.Lock blocks async event loop | cost_estimation_routes.py |

### Remaining (12 bugs, xfail)

| ID | Severity | Description | File |
|----|----------|-------------|------|
| BUG-SEC29 | P0 | HTTP 200 errors with raw str(e) | main.py |
| BUG-SEC01 | P0 | No auth on /train endpoint | cost_estimation_routes.py |
| BUG-SEC20 | P0 | Code validator bypass via getattr | code_executor.py |
| BUG-D023 | P0 | Module-level Docker init | code_executor.py |
| BUG-A002 | P1 | Groundedness lexical-only | groundedness_checker.py |
| BUG-CE01 | P1 | Unseen category silent bad prediction | cost_estimation_service.py |
| BUG-CE04 | P1 | Relative model path breaks | cost_estimation_service.py |
| BUG-IC02 | P1 | Dict where QueryContext expected | intent_node.py |
| BUG-LD07 | P1 | No context window guard | dispatch_service.py + rag_engine.py |
| BUG-D021 | P1 | Fake groundedness (count proxy) | groundedness_node.py |
| BUG-D001 | P1 | Error string leaked as response | graph.py |
| BUG-SEC26 | P1 | Tenant ID spoofable | dependencies.py |
| BUG-D012 | P1 | Prompt injection in code gen | data_analysis_agent.py |
| BUG-D011 | P1 | Template max/min ignores context | data_analysis_agent.py |

### New Patterns Discovered

1. **Corrupted i18n placeholders**: "EN" and Chinese text fragments scattered throughout safety, memory, and dispatch modules from incomplete localization
2. **Sticky workflow metadata**: State dict keys set by one node persist across turns when not explicitly cleared
