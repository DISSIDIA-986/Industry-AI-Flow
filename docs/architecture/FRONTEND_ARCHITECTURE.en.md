# Frontend Architecture

> 🌐 Language: **English** · [中文](./FRONTEND_ARCHITECTURE.md)

## Overview

The Industry AI Flow frontend uses a modern decoupled frontend/backend architecture, built on Next.js 14, delivering a high-performance and scalable UI.

```
┌─────────────────────────────────────────────────────────────┐
│                    Next.js 14 Application                   │
│  ┌─────────────────────────────────────────────────────┐  │
│  │                App Router (App Directory)           │  │
│  │  • Page routes                                      │  │
│  │  • Layout components                                │  │
│  │  • Server Components                                │  │
│  │  • Client Components                                │  │
│  └─────────────────────────────────────────────────────┘  │
│                                                            │
│  ┌─────────────────────────────────────────────────────┐  │
│  │                  React Component Layer              │  │
│  │  • UI library (Forms, Tables, Cards, Modals)        │  │
│  │  • Business components (Chat, DocumentManager, ...) │  │
│  │  • Shared components (Navbar, Sidebar, Footer)      │  │
│  └─────────────────────────────────────────────────────┘  │
│                                                            │
│  ┌─────────────────────────────────────────────────────┐  │
│  │                   State Management                  │  │
│  │  • React Context (Auth, AppConfig)                  │  │
│  │  • Local state (useState, useReducer)               │  │
│  │  • Server state (React Query / SWR)                 │  │
│  └─────────────────────────────────────────────────────┘  │
│                                                            │
│  ┌─────────────────────────────────────────────────────┐  │
│  │                   API Integration                   │  │
│  │  • API client (RESTful calls)                       │  │
│  │  • WebSocket client (real-time)                     │  │
│  │  • Error handling and retry                         │  │
│  └─────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                  FastAPI Backend Services                   │
│  • Authentication (JWT, OAuth2)                             │
│  • Business logic (AI workflows, document processing)       │
│  • Data storage (PostgreSQL, pgvector)                      │
│  • File storage (MinIO / S3)                                │
└─────────────────────────────────────────────────────────────┘
```

## Tech Stack

### Core Framework
- **Next.js 14** — full-stack React framework with App Router and Server Components
- **React 18** — modern React with concurrent features
- **TypeScript** — type-safe JavaScript
- **Tailwind CSS** — utility-first CSS

### State Management
- **React Context** — global state (auth, app config)
- **React Query** — server state and data fetching
- **Zustand** — lightweight state (optional)

### API Integration
- **Fetch API** — native browser API
- **Axios** — HTTP client (backup)
- **WebSocket** — real-time communication
- **React Hook Form** — form handling

### Component Libraries
- **Custom component library** — project-specific UI components
- **Headless UI** — unstyled UI primitives
- **Heroicons** — SVG icon set
- **Recharts** — data visualization charts

## Directory Structure

```
frontend/
├── src/
│   ├── app/                          # Next.js App Router
│   │   ├── (mvp)/                    # MVP feature pages
│   │   │   ├── layout.tsx            # MVP layout
│   │   │   ├── overview/             # Overview page
│   │   │   ├── workflow-chat/        # Workflow chat
│   │   │   ├── documents/            # Document management
│   │   │   ├── data-dashboard/       # Data dashboard
│   │   │   ├── cost-estimation/      # Cost estimation
│   │   │   ├── prompt-admin/         # Prompt management
│   │   │   └── components-demo/      # Component demo
│   │   ├── (simple)/                 # Simplified pages
│   │   ├── login/                    # Login
│   │   ├── register/                 # Register
│   │   ├── api/                      # API routes (frontend proxy)
│   │   ├── layout.tsx                # Root layout
│   │   └── globals.css               # Global styles
│   │
│   ├── components/                   # React components
│   │   ├── forms/                    # Form components
│   │   ├── tables/                   # Table components
│   │   ├── cards/                    # Card components
│   │   ├── modals/                   # Modal components
│   │   ├── feedback/                 # Feedback components
│   │   ├── files/                    # File components
│   │   ├── charts/                   # Chart components
│   │   ├── layout/                   # Layout components
│   │   ├── ProtectedRoute.tsx        # Auth-gated route wrapper
│   │   └── Navbar.tsx                # Navbar
│   │
│   ├── contexts/                     # React contexts
│   │   ├── AuthContext.tsx           # Auth context
│   │   └── AppConfigContext.tsx      # App config context
│   │
│   ├── hooks/                        # Custom hooks
│   │   ├── useAuth.ts                # Auth hook
│   │   ├── useApi.ts                 # API hook
│   │   └── useWebSocket.ts           # WebSocket hook
│   │
│   ├── lib/                          # Utilities
│   │   ├── api-client.ts             # API client
│   │   ├── websocket-client.ts       # WebSocket client
│   │   ├── formatters.ts             # Formatters
│   │   ├── validators.ts             # Validators
│   │   └── constants.ts              # Constants
│   │
│   └── styles/                       # Styles
│       ├── components.css            # Component styles
│       └── themes.css                # Themes
│
├── public/                           # Static assets
│   ├── favicon.ico                   # Favicon
│   ├── images/                       # Images
│   └── fonts/                        # Fonts
│
├── package.json                      # Dependencies
├── next.config.js                    # Next.js config
├── tailwind.config.js                # Tailwind config
├── tsconfig.json                     # TypeScript config
└── .env.local                        # Environment variables
```

## Core Feature Modules

### 1. Authentication System
- **Login/Register** — JWT-based auth flow
- **Session management** — automatic token refresh and expiry handling
- **Access control** — role-based authorization
- **Social login** — OAuth2 integration (optional)

### 2. Workflow Chat UI
- **Real-time chat** — bidirectional WebSocket communication
- **Message history** — local storage with server sync
- **File upload** — drag-and-drop with progress indicator
- **Intent recognition** — shows AI intent classification

### 3. Document Management
- **Document upload** — batch upload with format validation
- **Document preview** — PDF, Word, Excel preview
- **Document search** — full-text search and filters
- **Versioning** — document version control

### 4. Data Visualization Dashboard
- **Real-time monitoring** — system status and performance metrics
- **Chart display** — multiple chart types
- **Data export** — CSV, Excel, PDF
- **Custom views** — user-configurable dashboards

### 5. Cost Estimation Tool
- **Parameter input** — project parameter form
- **Live calculation** — cost prediction and risk assessment
- **Result comparison** — multi-scenario comparison
- **Report generation** — detailed estimation reports

## Performance Optimization

### 1. Code Splitting
- **Route-level splitting** — dynamic page loading
- **Component-level splitting** — lazy-load heavy components
- **Library-level splitting** — load third-party libraries on demand

### 2. Caching Strategy
- **Server-side caching** — Next.js built-in caching
- **Client-side caching** — React Query cache
- **Browser caching** — HTTP cache headers

### 3. Image Optimization
- **Next.js Image** — automatic image optimization
- **Lazy loading** — in-viewport image loading
- **Format conversion** — WebP support

### 4. Bundle Optimization
- **Tree shaking** — remove unused code
- **Minification** — JavaScript and CSS compression
- **Bundle analysis** — bundle size monitoring

## Security Considerations

### 1. Auth Security
- **JWT security** — HTTPS transport, short-lived tokens
- **Password security** — salted hashes
- **Session security** — session hijacking prevention

### 2. Input Validation
- **Client-side validation** — real-time form validation
- **Server-side validation** — API parameter validation
- **XSS protection** — Content Security Policy

### 3. Data Protection
- **Sensitive data** — encrypted local storage
- **API security** — request signing and replay prevention
- **File security** — scanning uploaded files

## Development Workflow

### 1. Local Development
```bash
# Install dependencies
npm install

# Start dev server
npm run dev

# Run tests
npm run test

# Lint
npm run lint
```

### 2. Build & Deploy
```bash
# Production build
npm run build

# Start production server
npm start

# Static export (optional)
npm run export
```

### 3. Code Quality
- **TypeScript** — strict type checking
- **ESLint** — code style enforcement
- **Prettier** — code formatting
- **Husky** — git hooks

## Backward Compatibility

### 1. API Versioning
- **API version** — `/api/v1/` prefix
- **Backward compatibility** — legacy version support
- **Deprecation** — phased migration plan

### 2. Browser Support
- **Modern browsers** — Chrome 90+, Firefox 88+, Safari 14+
- **Progressive enhancement** — graceful degradation for core features
- **Polyfills** — as needed

## Monitoring & Logs

### 1. Performance Monitoring
- **Core Web Vitals** — LCP, FID, CLS
- **Custom metrics** — business-specific metrics
- **Error tracking** — frontend error collection

### 2. User Analytics
- **User behavior** — page views and interactions
- **Feature usage** — feature usage statistics
- **Performance data** — client-side performance

---

**Doc version**: 1.0
**Last updated**: 2026-02-14
**Maintainer**: Industry AI Flow development team
