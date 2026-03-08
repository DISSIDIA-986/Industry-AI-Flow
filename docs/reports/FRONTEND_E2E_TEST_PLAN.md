# Frontend E2E Test Plan (Pre-QA Gate)

## 1. Objective

Build a reliable frontend E2E system before handing over to QA, with measurable accuracy and coverage for the latest Next.js MVP flows.

## 2. Expert-Driven Principles

- AI expert view: prioritize deterministic automation with stable mocks, traces, and reproducible runs.
- Architecture expert view: test by user journey + critical integration boundaries (auth, API, routing, state persistence).
- Senior engineering view: gate by severity and risk, not only by test count.
- Delivery/agency view: keep smoke path fast, full suite richer, and generate artifacts for fast triage.

## 3. Tooling Strategy

- Primary E2E runner: Playwright (`frontend/playwright.config.ts`).
- Browser automation agent mode: Playwright trace/video/screenshot artifacts (agent browser style replay/debug).
- Execution modes:
  - Default: Chromium only for quick and stable gates.
  - Extended: set `PW_CROSS_BROWSER=1` to run Firefox/WebKit coverage.
- Report outputs:
  - HTML: `frontend/playwright-report/`
  - JSON: `frontend/playwright-results.json`
  - JUnit: `frontend/junit-results.xml`

## 4. Coverage Matrix

- P0 Authentication and route guard
  - Login/register entry, protected-route redirect behavior.
- P0 Workflow chat
  - Prompt input, send flow, AI response rendering, websocket toggle.
- P0 Documents management
  - Page load, search behavior, empty-state behavior.
- P0 Data dashboard
  - KPI/chart page rendering, time-range switching.
- P0 Cost estimation
  - Single prediction and batch queue run path.
- P1 API integration page
  - One-click API check and visible pass/fail state.
- P1 Navigation consistency
  - Navbar cross-page navigation among core MVP pages.

## 5. Test Data and Environment Controls

- Seed authenticated session via localStorage before protected-page navigation.
- Mock core endpoints (`/api/v1/health`, auth, workflow, documents, cost estimation) for deterministic assertions.
- Keep fallback-compatible behavior to support local backend on/off states.

## 6. Gate Definition (Before QA Handoff)

- Must pass:
  - 100% P0 scenarios green on Chromium.
  - No flaky test in 3 repeated runs (`npm run test:e2e -- --project=chromium --repeat-each=3`).
- Should pass:
  - P1 scenarios green.
  - Cross-browser run (`PW_CROSS_BROWSER=1`) without P0 failures.
- Blockers:
  - Auth flow break.
  - Core page inaccessible.
  - Chat/documents/cost-estimation core user actions broken.

## 7. Execution Commands

```bash
cd frontend
npm run test:e2e -- --project=chromium
PW_CROSS_BROWSER=1 npm run test:e2e
npm run test:e2e:report
```

## 8. QA Handoff Criteria

- Attach latest HTML report + failing trace (if any).
- Provide pass/fail summary by P0/P1 categories.
- Confirm known risks and excluded scenarios explicitly (if any).
- QA starts only after P0 gate is green and reproducibility check passes.
