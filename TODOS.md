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
