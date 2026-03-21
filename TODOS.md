# TODOS

## Deferred Tasks

### Migrate E2E selectors from Tailwind classes to data-testid
**Priority:** Medium
**Added:** 2026-03-19 (eng review of UI design system unification)
**Blocked by:** Nothing — can be done anytime after demo

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
