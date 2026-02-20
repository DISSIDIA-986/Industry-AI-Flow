# Frontend Expert Review Report (2026-02-20)

## 1. P0/P1 Findings (Evidence First)

### P0 Summary
- No reproducible P0 defects were observed in this review run.
- Baseline evidence: `/Users/openclaw/Documents/github.com/Industry-AI-Flow/logs/frontend-review/20260219_235428/summary.txt` shows `pass=3`, `fail=0`.

### P1-1: API endpoint strategy drift and hardcoded localhost targets
- Severity: P1
- Reproduction:
  1. Start backend on a non-`8001` endpoint (e.g. `127.0.0.1:18000`) or behind proxy-only mode.
  2. Open `/api-test` and click endpoint tests.
  3. Observe requests still target hardcoded localhost and produce misleading failures.
- Evidence:
  - Hardcoded request base: `/Users/openclaw/Documents/github.com/Industry-AI-Flow/frontend/src/app/(mvp)/api-test/page.tsx:33`
  - Hardcoded backend label: `/Users/openclaw/Documents/github.com/Industry-AI-Flow/frontend/src/app/(mvp)/api-test/page.tsx:148`
  - Misleading fallback API address text: `/Users/openclaw/Documents/github.com/Industry-AI-Flow/frontend/src/app/(mvp)/api-integration-test/page.tsx:112`
  - Real API client default localhost base: `/Users/openclaw/Documents/github.com/Industry-AI-Flow/frontend/src/lib/real-api-client.ts:15`
- Impact:
  - Ops/QA 页面结论不可信，环境切换时易误判“系统故障”。
  - 增加联调成本并掩盖真实代理链路问题。

### P1-2: Hybrid client silently returns mock-like fallback data on real API failure
- Severity: P1
- Reproduction:
  1. Make `/query/history` unavailable (or simulate API failure).
  2. Call `realApiService.getQueryHistory()` or use hybrid paths relying on it.
  3. Observe synthetic history is returned instead of hard failure.
- Evidence:
  - Query history fallback to fabricated records: `/Users/openclaw/Documents/github.com/Industry-AI-Flow/frontend/src/lib/real-api-client.ts:312`
  - Model list fallback to static values: `/Users/openclaw/Documents/github.com/Industry-AI-Flow/frontend/src/lib/real-api-client.ts:347`
  - Hybrid fallback behavior (`sendWorkflowQuery/upload/estimateCost`): `/Users/openclaw/Documents/github.com/Industry-AI-Flow/frontend/src/lib/real-api-client.ts:363`
- Impact:
  - 系统在失败状态下表现为“看似可用”，会污染问题定位与业务判断。

### P1-3: Test pyramid imbalance (heavy mocked E2E, missing frontend unit/integration layer)
- Severity: P1
- Reproduction:
  1. Inspect frontend tests structure.
  2. Observe `frontend/tests` currently only contains E2E folder.
  3. Inspect core E2E and verify broad API mocking.
- Evidence:
  - Test folder only E2E: `/Users/openclaw/Documents/github.com/Industry-AI-Flow/frontend/tests`
  - Core journeys globally mock backend endpoints: `/Users/openclaw/Documents/github.com/Industry-AI-Flow/frontend/tests/e2e/core-user-journeys.spec.ts:41`
  - Mock interceptors for health/auth/workflow/cost: `/Users/openclaw/Documents/github.com/Industry-AI-Flow/frontend/tests/e2e/utils/session.ts:21`
- Impact:
  - Hook/state/formatter 级别回归无法被快速定位。
  - 合同漂移和真实后端行为偏差可能在较晚阶段才暴露。

### P1-4: Frontend toolchain dependency security backlog (dev graph)
- Severity: P1
- Reproduction:
  1. Run `cd frontend && npm audit --json`.
  2. Observe high/moderate vulnerabilities in dev dependency graph.
- Evidence:
  - Audit summary: `high=14`, `moderate=1` from `/tmp/frontend_audit_all.json`.
  - Representative affected packages include `eslint`, `eslint-config-next`, `@typescript-eslint/*`, `minimatch`.
- Impact:
  - 对本地开发与CI链路形成供应链风险。
  - 升级窗口越晚，迁移成本越高。

### P1-5: Next.js config source ambiguity (`next.config.js` and `next.config.ts` coexist)
- Severity: P1
- Reproduction:
  1. Inspect frontend root config files.
  2. Observe both JS and TS config files exist with divergent content.
- Evidence:
  - Active rewrite/cors/proxy config in JS: `/Users/openclaw/Documents/github.com/Industry-AI-Flow/frontend/next.config.js:29`
  - Stub TS config exists simultaneously: `/Users/openclaw/Documents/github.com/Industry-AI-Flow/frontend/next.config.ts:1`
- Impact:
  - 维护者容易编辑错误配置文件，导致不可预期行为。

## 2. Architecture Review Summary

### What is working
- Layout/navbar regression baseline is now executable and passing (mock + live split):
  - Live checks include health probe, cross-route navbar persistence, cost prediction/auth path:
    - `/Users/openclaw/Documents/github.com/Industry-AI-Flow/frontend/tests/e2e/layout-nav-live-api-regression.spec.ts:55`
  - Gate script starts backend and runs both suites:
    - `/Users/openclaw/Documents/github.com/Industry-AI-Flow/scripts/testing/run_frontend_layout_nav_gate.sh:74`
- CI contains dedicated frontend gate job:
  - `/Users/openclaw/Documents/github.com/Industry-AI-Flow/.github/workflows/kpi-gate.yml:35`

### Structural risks
- API access model has drift:
  - Unified proxy client exists, but parallel `real-api-client` path still keeps direct-origin and fallback semantics.
- Diagnostics pages are environment-coupled and can contradict actual runtime path.
- Test layering remains top-heavy at E2E level, reducing defect localization speed.

## 3. Must-Change Top 5

| Rank | Must-Change | Why now | Minimal actionable change | Regression proof |
|---|---|---|---|---|
| 1 | Remove hardcoded backend URLs and enforce single proxy path | Eliminates environment-specific false negatives and inconsistent diagnostics | Replace direct `localhost` calls/text in `/api-test` and `/api-integration-test` with runtime proxy-based URL source (`/api/backend/...`) | Add E2E asserting API test page requests same-origin proxy only |
| 2 | Disable silent synthetic fallback for “real” data paths | Prevents fake-success behavior and improves incident detectability | In `real-api-client`, return explicit degraded error state for `getQueryHistory/getAvailableModels` unless feature-flagged | Add unit tests for fallback policy + E2E asserting error banner appears on backend outage |
| 3 | Build a real test pyramid (unit + integration + live e2e contracts) | Current E2E-heavy strategy misses logic-level regressions and slows triage | Add Vitest (or equivalent) for hooks/formatters/API adapters and page-level integration tests for auth + proxy contracts | Gate with `npm run test:unit` and `npm run test:integration` in CI |
| 4 | Remediate high audit findings in lint/toolchain dependency tree | Reduces supply-chain exposure in CI/dev | Upgrade `eslint`/`eslint-config-next`/`@typescript-eslint` stack in a controlled branch; pin and verify | Keep `npm audit --json` diff in CI artifact and enforce threshold |
| 5 | Consolidate to a single Next config source file | Removes config-edit ambiguity and accidental drift | Keep one canonical config (`next.config.js` or `next.config.ts`) and delete the other | Add lint check to fail when both files coexist |

## 4. Delivery Decision
- Verdict: **Ready for QA/测试交付**, **Conditionally Ready for production release**.
- Rationale:
  - No P0 reproduced in this run.
  - Must-Change #1 ~ #5 are implemented with executable gates.
  - Frontend audit high/critical risk has been reduced to zero and guarded by `audit:high`.
- Preconditions to reach full production readiness:
  1. Continue tracking remaining `moderate` dev-toolchain advisories and remove override debt when upstream lint stack provides safe upgrades.
  2. Keep the combined gate (`audit:high + unit + integration + live/mock e2e`) mandatory in CI.

## 5. Evidence Index
- Branch: `codex/test-driven-optimization-20260220`
- Commit baseline: `458652d1`
- Runtime summary log: `/Users/openclaw/Documents/github.com/Industry-AI-Flow/logs/frontend-review/20260219_235428/summary.txt`
- Gate detail log: `/Users/openclaw/Documents/github.com/Industry-AI-Flow/logs/frontend-review/20260219_235428/layout_nav_gate.log`
- Toolchain audit snapshot: `/tmp/frontend_audit_all.json`
- Environment snapshot: Node `v25.6.0`, npm `11.8.0`

## 6. Date Clarification
- Review executed at local time `2026-02-19 23:57 MST` (UTC date corresponds to `2026-02-20`).

## 7. Remediation Update (Post-Review Execution)
- Update time: `2026-02-20 00:28 MST`
- Implemented in code:
  - Must-Change #1 (endpoint unification): completed.
    - API diagnostics pages no longer hardcode localhost and now show proxy path.
    - Browser-level regression added to block hardcoded backend host calls.
  - Must-Change #2 (silent fallback control): completed for real API client pathways used by history/model/doc APIs and hybrid client fallback control.
    - Default behavior switched to explicit errors unless fallback flags are explicitly enabled.
  - Must-Change #5 (single Next config source): completed.
    - `next.config.ts` removed, lint now checks duplicate config source cannot regress.
  - Must-Change #3 (test pyramid baseline): completed.
    - Added Vitest + jsdom frontend test layer with dedicated `test:unit` and `test:integration`.
    - Added unit contracts for navbar persistence and real/hybrid fallback policy.
    - Added integration contracts for shared layout shell width constraints and API proxy source consistency.
    - Frontend regression gate now executes `audit:high + unit + integration + e2e(live+mock)`.
  - Must-Change #4 (dependency vulnerability remediation): completed for high/critical risk class.
    - Added package override forcing `minimatch` to patched range (`^10.2.2`) to eliminate high-severity findings in lint toolchain transitive graph.
    - Added `npm run audit:high` gate to fail builds when `high` or `critical` vulnerabilities reappear.
- Fresh verification evidence:
  - `/Users/openclaw/Documents/github.com/Industry-AI-Flow/logs/frontend-review/20260220_002818/summary.txt` (`pass=3`, `fail=0`)
  - `/Users/openclaw/Documents/github.com/Industry-AI-Flow/logs/frontend-review/20260220_002818/layout_nav_gate.log` (7 Playwright tests passed; unit/integration/audit gate included)
  - `cd /Users/openclaw/Documents/github.com/Industry-AI-Flow/frontend && npm audit --json` => `high=0`, `critical=0`, `moderate=10` (remaining items are dev-toolchain moderate advisories with no safe non-breaking upgrade path under current Next.js lint stack).
