# Frontend Architecture

> 🇨🇳 中文版： **[FRONTEND_ARCHITECTURE.zh.md](FRONTEND_ARCHITECTURE.zh.md)**

## Overview

The Industry AI Flow frontend is a Next.js (App Router) single-page application talking to the FastAPI backend over a thin proxy. It is layered into four tiers: App Router → React components → state management → API integration.

```
┌──────────────────────────────────────────────┐
│              Next.js App                       │
│  App Router    — page routes, layouts,         │
│                  server + client components    │
│  Components    — UI (forms, tables, cards,     │
│                  modals) + feature + shared    │
│  State         — React Context (Auth, config), │
│                  local state, server state     │
│  API layer     — REST client, error handling   │
└──────────────────────────────────────────────┘
                       │
                       ▼
┌──────────────────────────────────────────────┐
│            FastAPI backend                     │
│  Auth (JWT) · AI workflow · document           │
│  processing · PostgreSQL + pgvector            │
└──────────────────────────────────────────────┘
```

## Tech stack

- **Framework** — Next.js (App Router, Server Components), React, TypeScript.
- **Styling** — Tailwind CSS.
- **State** — React Context for global state (auth, app config); local state with `useState`/`useReducer`; server-state caching for data fetching.
- **API** — Fetch-based API client; React Hook Form for forms.
- **UI** — Custom component library, SVG icon set, Recharts for data visualization.

## Directory structure

```
frontend/src/
├── app/                 # Next.js App Router
│   ├── (mvp)/           # Main feature pages: overview, workflow-chat,
│   │                    #   documents, data-dashboard, cost-estimation,
│   │                    #   prompt-admin, intent-demo
│   ├── (simple)/        # Simplified dashboard pages
│   ├── login/           # Login page
│   ├── api/             # Frontend proxy routes to the backend
│   ├── layout.tsx       # Root layout
│   └── globals.css      # Global styles
├── components/          # forms, tables, cards, modals, charts,
│                        #   layout, ProtectedRoute, Navbar
├── contexts/            # AuthContext, AppConfigContext
├── hooks/               # useAuth, useApi, animation hooks
├── lib/                 # api-client, formatters, validators, constants
└── styles/              # component + theme styles
```

## Feature modules

1. **Authentication** — JWT login, automatic token refresh and expiry handling, role-based access control. Session expiry is self-healing: any 401 from a protected endpoint clears auth state and redirects to login.
2. **Workflow chat** — The primary demo surface. Live query/response with source citations, message history, file upload, and an animated intent/pipeline visualization.
3. **Document management** — Batch upload with format validation, format-aware preview (PDF, images, text/CSV/JSON, Office extracts), full-text search, and an AI-generated summary per document.
4. **Data dashboard / system overview** — Real-time health and metrics for each module, multiple chart types, configurable views.
5. **Cost estimation** — Parameter form, real-time prediction with SHAP explainability, what-if scenario sliders, similar-project comparison, and report export.

## Performance

- **Code splitting** — route-level and component-level lazy loading; on-demand third-party libraries.
- **Caching** — Next.js server cache, client-side data cache, HTTP cache headers.
- **Images** — Next.js `Image` with lazy loading and WebP.
- **Bundling** — tree shaking, minification, bundle-size monitoring.

## Security

- **Auth** — HTTPS-only, short-lived JWTs; protection against session hijacking.
- **Input** — real-time client-side validation plus server-side validation; Content-Security-Policy against XSS.
- **API** — API versioning under `/api/v1/`; request validation; upload scanning.

## Development workflow

```bash
npm install      # install dependencies
npm run dev      # dev server (:3123)
npm run build    # production build
npm run lint     # lint
npm run test     # tests
```

Quality tooling: strict TypeScript, ESLint, Prettier.

## Compatibility & monitoring

- **Browsers** — modern evergreen browsers (Chrome 90+, Firefox 88+, Safari 14+) with graceful degradation.
- **Monitoring** — Core Web Vitals (LCP/INP/CLS), custom business metrics, front-end error tracking.

---

**Document version:** 1.1 · **Last updated:** 2026-06-14
