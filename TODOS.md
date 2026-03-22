# TODOS

## Deferred Tasks

### Migrate E2E selectors from Tailwind classes to data-testid
**Priority:** Medium — **PARTIAL (Intent Demo done, Workflow Chat new elements will have data-testid, 3 other pages remain)**
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

### Extract shared node animation hook (DRY)
**Priority:** Medium — **PLANNED: Will be completed in Full-Stack Enterprise Polish PR (2026-03-22)**
**Added:** 2026-03-21 (eng review of Workflow Chat full polish)
**Blocked by:** ~~Workflow Chat redesign must be completed first~~ UNBLOCKED — bundled into full-stack polish per eng review Issue 6A

**What:** Extract `useNodeAnimation()` shared hook from PipelineFlowViz (`usePipelineAnimation`, 75 lines), IntentFlowViz (`useIntentAnimation`, 80 lines), and the new CompactPipelineViz animation. All three use identical proportional timing logic: iterate ALL_NODES, set active → sleep proportional delay → set completed/skipped.

**Why:** 3 copies of nearly identical animation timing logic. Any animation behavior change (speed, easing, error states) needs 3 edits. Classic DRY violation. Deferred because touching 3 working pages risks regression before Capstone demo.

**How to implement:**
1. Create `frontend/src/hooks/useNodeAnimation.ts` with configurable: node list, total duration, latency map, completed set
2. Return `{ nodeStates, triggerAnimation, isAnimating, reset }`
3. Refactor PipelineFlowViz, IntentFlowViz, and CompactPipelineViz to use it
4. Regression test all 3 pages: Dashboard, Intent Debugger, Workflow Chat

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
