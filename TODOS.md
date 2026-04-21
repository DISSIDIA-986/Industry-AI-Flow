# TODOS

## Deferred Tasks

### Migrate E2E selectors from Tailwind classes to data-testid
**Priority:** Medium — **PARTIAL (Intent Demo + Workflow Chat + Data Analysis done — 2 other pages remain: RAG Agent, Cost Estimation, Dashboard)**
**Added:** 2026-03-19 (eng review of UI design system unification)
**Blocked by:** Nothing — Intent Demo page has data-testid attributes as of Intent Debugger PR

**What:** All 4 browser E2E test scripts (`run_rag_agent_browser_e2e.py`, `run_data_analysis_browser_e2e.py`, `run_cost_estimation_agent_browser_e2e.py`, `run_data_dashboard_agent_browser_e2e.py`) use hardcoded Tailwind CSS class names as selectors (e.g., `bg-blue-600`, `space-y-6`, `overflow-y-auto`). Any CSS styling change can break these tests.

**Why:** Decouple test stability from visual styling. Currently, every CSS change requires manual E2E selector updates (per CLAUDE.md's E2E Sync Rule). With `data-testid` attributes, only DOM structure changes would break tests.

**How to implement:**
1. Add `data-testid` attributes to key interactive elements in frontend pages (buttons, forms, result containers, chat bubbles)
2. Update all 4 E2E scripts to use `[data-testid="..."]` selectors instead of Tailwind classes
3. Keep the CLAUDE.md E2E Sync Rule but note it applies to structure changes, not CSS changes

**Effort:** human: ~1 day / CC: ~15 min

### Multi-file concurrent upload progress
**Priority:** Low
**Added:** 2026-03-20 (eng review of document pipeline staged processing)
**Blocked by:** SSE progress implementation must be completed first

**What:** Frontend supports displaying independent SSE progress bars for multiple files being uploaded simultaneously, instead of sequential single-file progress.

**Why:** Current design shows progress for one file at a time, processing multiple files sequentially. If users need batch uploads in the future, the UX would be significantly better with per-file progress tracking and concurrent SSE connections.

**How to implement:**
1. Add per-file state management (Map of doc_id → progress state) in the upload component
2. Open independent EventSource connections per file
3. Display stacked progress components, each with its own staged pipeline view
4. Handle concurrent EventSource cleanup on unmount

**Effort:** human: ~2 days / CC: ~15 min

### Persist upload progress to database
**Priority:** Medium
**Added:** 2026-03-20 (eng review of document pipeline staged processing)
**Blocked by:** SSE progress implementation + janus.Queue must be completed first

**What:** Write pipeline stage progress to `uploaded_documents_index` table (new `processing_stage` field) instead of relying solely on in-memory janus.Queue.

**Why:** janus.Queue is ephemeral — page refresh, reconnect, or server restart loses all progress state. With DB persistence, the polling fallback can show meaningful stage progress, and page refresh recovers current state. Codex review specifically flagged this as a gap (late subscribers, reconnects get no state).

**How to implement:**
1. Add `processing_stage VARCHAR(32)` and `processing_detail TEXT` columns to `uploaded_documents_index`
2. Update stage progress in DB at each stage transition (extract→chunk→embed→store)
3. Modify list endpoint to include `processing_stage` in response for status='processing' documents
4. Frontend polling fallback reads stage from API response instead of getting no progress

**Effort:** human: ~4 hours / CC: ~10 min

### ~~Extract shared node animation hook (DRY)~~ — DONE (2026-03-22)
**Completed in:** Full-Stack Enterprise Polish commit `c179edae` + follow-up

**What was done:**
1. Created `frontend/src/hooks/useNodeAnimation.ts` — shared hook with configurable node list, total duration, latency map
2. Refactored `PipelineFlowViz.usePipelineAnimation()` to delegate to shared hook
3. Refactored `IntentFlowViz.useIntentAnimation()` to delegate to shared hook
4. CompactPipelineViz not refactored (unique dual-mode animation pattern — not worth forcing into shared hook)

**Effort:** human: ~4 hours / CC: ~10 min

### Intent Debugger — Conversation Replay (stretch goal)
**Priority:** Medium
**Added:** 2026-03-21 (eng review of Intent Debugger design)
**Blocked by:** Intent Debugger Phases 1-3 must be completed first

**What:** Multi-turn conversation replay component + backend session trace storage. Shows how intent evolves across clarification rounds (e.g., unclear_intent → cost_estimation after user clarifies). Timeline UI with step-forward/back playback controls, color-coded by intent at each turn.

**Why:** Demonstrates the core architectural innovation of the 11-node StateGraph — specifically the clarification loop (MAX_CLARIFICATION_ROUNDS=2) that distinguishes this system from a simple keyword matcher. Evaluators can see the system "learn" what the user wants across multiple turns.

**How to implement:**
1. Add in-memory `workflow_traces: dict[str, list]` to intent workflow (keyed by session_id)
2. Each classification appends full `node_trace` + result to the session's trace list
3. New endpoint: `GET /api/intent/session/{session_id}/trace` → returns ordered list
4. New frontend component: `IntentConversationReplay` — vertical timeline with connected dots
5. Playback controls: step forward/back through turns, show intent evolution

**Effort:** human: ~2 days / CC: ~20 min

### ~~Update DESIGN.md Decisions Log — Presentation Materials Token Unification~~ — DONE (2026-03-23)
**Completed in:** design-consultation session

**What was done:**
1. Added 3 entries to DESIGN.md Decisions Log (poster migration, architecture diagrams, module colors)
2. Added "Presentation Materials" section to DESIGN.md documenting all showcase artifacts
3. Added module color system (blue/amber/emerald/purple) to Color section
4. Updated Dark Hero Section page list to all 7 demo pages

### Validate PII redaction in agentic CRISP-DM path
**Priority:** Medium — blocks Stage 3 flag flip to production
**Added:** 2026-04-18 (plan-eng-review of Dynamic Analysis refactor spike)
**Blocked by:** Stage 2 of Dynamic Analysis spike completes with green verdict

**What:** The current `pii_detector.py` warns-only on column names (no redaction). The agentic refactor (Stage 3) will send column metadata to GLM-5 via a richer, less controlled prompt than the old deterministic path. Re-validate the privacy boundary before flipping `USE_GLM5_AGENT=true` in prod.

**Why:** Privacy-by-design is a named demo-critical property. Attendees uploading arbitrary CSVs may include PII column names (SSN, DOB, credit_card_number). The agentic path must not leak these in generated code comments, analysis plans, or sandbox stdout.

**How to implement:**
1. Audit the V2 agentic prompt (`crispdm_plan_and_code.md`) for places where column names echo into `analysis_plan` / `assumptions` output fields.
2. Decide: (a) redact PII-flagged column names before prompt, (b) instruct LLM to rename internally, or (c) scrub output before returning to user.
3. Add a test case: upload a CSV with `ssn`, `dob`, `credit_card_number` columns and assert generated code/summary never echoes those strings.

**Effort:** human: ~4 hours / CC: ~30 min

### Align E2B sandbox image with validator whitelist
**Priority:** High — blocks Plan-stage forecast capability, discovered in spike 2026-04-18
**Added:** 2026-04-18 (spike GLM-5 run, airline-passengers-Q2 ModuleNotFoundError)
**Blocked by:** Nothing

**What:** Three library boundaries must stay in sync, not two: (1) the prompt's "allowed libraries" list, (2) `CodeValidator.WHITELISTED_IMPORTS` in `backend/services/code_executor/validator.py`, and (3) what's actually installed inside the E2B sandbox runtime. The spike exposed this gap: statsmodels was added to (1) and (2) but is not pre-installed in E2B's default `code-interpreter` image, so forecast code passes validation then crashes at import.

**Why:** If we tell the LLM "you may use statsmodels" and the validator agrees but the sandbox doesn't have the package, every forecast/time-series task fails with a confusing sandbox traceback. Users (demo attendees uploading arbitrary CSVs) will see a cryptic `ModuleNotFoundError` instead of a working chart.

**How to implement (pick one):**
1. **Pre-install in sandbox:** Build a custom E2B template image that pip-installs statsmodels (and any other libraries we commit to supporting). Maintenance: rebuild when whitelist changes.
2. **Runtime pip injection:** Before executing generated code, run `sbx.commands.run("pip install statsmodels")` in the sandbox. Slower (~5s per call) but zero image maintenance.
3. **Constrain prompt to available libs only:** Regenerate the "allowed libraries" list from the actual E2B image contents at startup. The validator whitelist becomes derived, not authoritative.

**Test:** After implementing, re-run airline-passengers-Q2 in the spike harness — it should pass with a valid forecast chart.

**Effort:** human: ~2 hours / CC: ~20 min (option 2 is fastest)

### Build custom E2B template image with full validator library set
**Priority:** Medium — follow-up to W1 startup probe
**Added:** 2026-04-18 (Plan Appendix E.7)
**Blocked by:** W1 shipping, W1's probe showing any missing packages

**What:** W1 uses a startup probe against E2B's default `code-interpreter` image. If the probe reveals missing packages (statsmodels was the known gap), the right fix is a custom E2B template image built once rather than runtime installs. This TODO tracks the image build.

**Why:** Probe-only without image control means every library gap blocks the agentic path until a manual image update. Pre-baking the image eliminates that class of failure.

**How to implement:**
1. Write a Dockerfile extending E2B's base code-interpreter with pip-installed extras (statsmodels, plus any future adds)
2. Build + push to E2B as a custom template
3. Update `EXTRA_SANDBOX_PACKAGES` constant or point client to the custom template
4. Rebuild pipeline documented in runbook

**Effort:** human: ~4 hours / CC: ~1 hour

### Retire deterministic chart_plan.py after showcase
**Priority:** Low — post-showcase cleanup
**Added:** 2026-04-18 (Plan Appendix E.7)
**Blocked by:** Successful showcase demo with USE_GLM5_AGENT=true in production

**What:** `chart_plan.py` exists as Day-of-demo rollback target per Plan E.5. After the April showcase confirms agentic path is stable, delete `chart_plan.py`, `chart_executor.py` (deterministic portions), and the `use_glm5_agent=false` branch in `analyze_query()`.

**Why:** Single path is easier to maintain. Keeping both branches indefinitely creates "which path did this bug go through?" confusion.

**How to implement:**
1. Verify 2-3 weeks of showcase/post-showcase stability on agentic path
2. Delete dead files
3. Remove feature flag, make `analyze_query()` call `run_agentic_analysis()` directly
4. Update tests that exercised the deterministic path

**Effort:** human: ~3 hours / CC: ~20 min

### Prompt A/B testing via prompt_manager integration
**Priority:** Low — post-showcase enhancement
**Added:** 2026-04-18 (Plan Appendix E.7, Open Question A.3.1)
**Blocked by:** Agentic path stable in production

**What:** Current prompt templates live in committed markdown files under `backend/services/data_analysis/prompts/`. Project already has `prompt_manager.py` for versioned prompts with performance scoring. Wire agentic prompts through prompt_manager to enable A/B tests and per-version latency/accuracy tracking.

**Why:** Prompt is the lever for agentic quality. A/B testing lets us iterate empirically rather than by vibes.

**How to implement:**
1. Import the 3 markdown templates as prompt_manager seed data
2. Route agentic_loop prompt loading through prompt_manager
3. Add variant routing (hash-based user sharding)
4. Log per-variant trial outcomes (already captured via Langfuse)

**Effort:** human: ~1 day / CC: ~45 min

### Surface GLM-5 token counts from Zhipu client
**Priority:** Low — cost visibility for post-showcase
**Added:** 2026-04-18 (Plan Appendix E.7)
**Blocked by:** Nothing

**What:** Zhipu's Anthropic-compatible endpoint returns token usage in the response body, but `backend/services/llm_integration/zhipu_client.py::generate()` currently discards it (returns only the text). Agentic path records `tokens_in/tokens_out/cost_usd = None` per trial as a result. Parse and surface the usage so we can attribute cost per request.

**Why:** Once agentic is in prod, cost tracking matters for budgeting. Also required for any future multi-tenant cost attribution.

**How to implement:**
1. Change `generate()` to return a small dataclass `GenerationResult(text, tokens_in, tokens_out)`
2. Update callers to extract .text where they previously used the return value
3. agentic_loop records the full tuple
4. llm_usage_logs table already exists — write records there

**Effort:** human: ~3 hours / CC: ~30 min

### Canonical `has_presentable_output` predicate across agentic loop/envelope/UI
**Priority:** Medium
**Added:** 2026-04-20 (plan-eng-review + Codex on fix-data-analysis-demo-eve-stability)

**What:** Success is decided in 4 places: `RoundRecord.is_successful()`, `_classify_repair_trigger()`, `_finalize()`, and the frontend banner in `page.tsx`. Currently they compose multiplicatively; any missed update produces a silent user-visible regression.

**Why:** Demo-eve fix loosened the predicate at each site independently. The correct long-term shape is one `has_presentable_output()` helper imported everywhere. Codex flagged this as a structural blind spot during plan-eng-review.

**How to implement:**
1. Add `backend/services/data_analysis/success_predicate.py` with `has_presentable_output(sandbox_success, chart_exists, summary_emitted, metrics_present) -> bool`
2. Call from `is_successful()`, `_classify_repair_trigger()`, `_finalize()`
3. Mirror in frontend `page.tsx` so banner logic reads from a single source
4. Add a cross-module test that asserts the 4 sites agree on the same inputs

**Effort:** human: ~3 hours / CC: ~20 min

### Deterministic-planner fallback feature flag for agentic failure
**Priority:** Medium
**Added:** 2026-04-20 (plan-eng-review; Codex alternative recommendation)

**What:** When the agentic (glm5_agent) path fails, fall back to `deterministic_planner` instead of surfacing the failure to the user. Behind a config flag so dev can still debug agentic.

**Why:** Deterministic planner is stable for EDA + single-chart analyses. Agentic is needed for ML comparison but currently has no fallback. On demo-eve this was risky; long-term it's a feature-flagged resilience win.

**How to implement:**
1. Add `settings.agentic_auto_fallback_to_deterministic: bool = False`
2. In `DataAnalysisAgent.analyze_query`, if agentic path returns `success=False` AND flag is True, re-run through `deterministic_planner` and compose an envelope with `code_generation.mode = "deterministic_fallback_from_agentic"`
3. Frontend badge to show fallback was triggered

**Effort:** human: ~4 hours / CC: ~25 min

### Fix frontend TS test env (missing React imports / jest-dom types)
**Priority:** Low
**Added:** 2026-04-20 (discovered during /ship of fix-data-analysis-demo-eve-stability)

**What:** `frontend/tests/unit/navbar.contract.spec.tsx` and `frontend/tests/unit/chart-lightbox.spec.tsx` currently fail to type-check: missing `import React from 'react'` (JSX in module context), and `toBeInTheDocument` / `toBeDisabled` matchers from `@testing-library/jest-dom` not augmented into the vitest matcher types.

**Why:** Blocks writing new frontend unit tests. Had to defer the single-flight guard unit test for the data-analysis page because the env can't run frontend specs.

**How to implement:**
1. Add `"@testing-library/jest-dom"` to `tsconfig.json` compilerOptions.types
2. Add `import '@testing-library/jest-dom';` to `vitest.setup.ts` (or create if missing)
3. Ensure `jsx: "react-jsx"` in tsconfig so React auto-import works (or add explicit imports)
4. Add frontend unit test: double-click Run Analysis fires exactly one `startDataAnalysisJob`

**Effort:** human: ~1 hour / CC: ~10 min
