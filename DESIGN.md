# Design System — Industry AI Flow

## Product Context
- **What this is:** AI-powered construction intelligence platform with RAG knowledge QA, ML cost estimation, and dynamic data analysis
- **Who it's for:** Construction industry professionals; evaluated by SAIT Capstone faculty
- **Space/industry:** Construction technology (ConTech) / AI platforms
- **Project type:** Web app / Dashboard

## Aesthetic Direction
- **Direction:** Industrial/Utilitarian — function-first, data-dense, professional
- **Decoration level:** Minimal — typography does all the work, no decorative elements
- **Mood:** "A serious engineering tool that earns trust through precision and clarity." The system should feel like it was built by engineers who care about the craft, not by a marketing team.
- **Reference sites:** OpenSpace.ai, Mastt.com, Procore.com — all use blue/white; our dark Pipeline hero and amber accent differentiate us

## Typography
- **Display/Hero:** Inter 700/800 — clean, professional, letter-spacing: -0.02em for display sizes
- **Body:** Inter 400/500 — established, stable. 15-16px base size, line-height 1.5-1.65
- **UI/Labels:** Inter 500/600 — uppercase with letter-spacing 0.05-0.08em for eyebrows/labels
- **Data/Tables:** JetBrains Mono 400 — tabular-nums for aligned numbers, ligatures off
- **Code:** JetBrains Mono 400/500
- **Loading:** next/font/google (self-hosted via Next.js, no external requests at runtime)
- **Scale:**
  - `xs`: 12px (labels, captions)
  - `sm`: 14px (body small, UI elements)
  - `base`: 16px (body text)
  - `lg`: 20px (section headers)
  - `xl`: 24px (page headers)
  - `2xl`: 30px (hero subheadings)
  - `3xl`: 36px (hero headings)

## Color
- **Approach:** Restrained with one accent — primary blue + amber accent + neutrals
- **Primary (Steel):** #2563eb — interactive elements, links, active states, primary buttons
- **Primary Soft:** #dbeafe — selected backgrounds, info alerts
- **Primary Hover:** #1d4ed8 — button hover state
- **Accent (Amber):** #f59e0b — construction industry warmth, warning states, highlight moments (Live Demo button)
- **Accent Soft:** #fef3c7 — warning alert backgrounds
- **Neutrals (cool gray):**
  - Background: #f9fafb (gray-50)
  - Background accent: #f3f4f6 (gray-100)
  - Surface: #ffffff
  - Line/Border: #e5e7eb (gray-200)
  - Muted text: #6b7280 (gray-500)
  - Secondary text: #374151 (gray-700)
  - Primary text: #111827 (gray-900)
- **Semantic:**
  - Success: #16a34a (green-600) / soft: #dcfce7
  - Warning: #f59e0b (amber-500) / soft: #fef3c7
  - Error: #dc2626 (red-600) / soft: #fef2f2
  - Info: #2563eb (blue-600) / soft: #dbeafe
- **Dark Hero Section:** #1a1a2e — used for page hero headers and pipeline visualization sections across all 7 demo pages (Dashboard, Workflow Chat, Documents, Data Analysis, Cost Estimation, Intent Debugger, System Overview). Creates visual contrast and conveys technical depth. Compact variant (px-6 py-4 rounded-2xl) for page headers; full-width variant for pipeline/flow visualizations. Text on dark: #e5e7eb (gray-200), muted: #6b7280 (gray-500), active nodes: #60a5fa (blue-400), completed nodes: #34d399 (emerald-400).
- **Module colors** (used in architecture diagrams + frontend pipeline visualizations):
  - RAG: #2563EB (blue-600) — matches primary
  - Cost Estimation: #16A34A (green-600) — as established in C4 diagrams
  - Data Analysis: #9333EA (purple-600) — as established in C4 diagrams
  - Intent Classification: #7C3AED (violet-600) — orchestration layer
  - Note: Poster Key Metrics strip uses amber/emerald for visual variety; diagrams use green/purple per C4 convention
- **Dark mode strategy:** CSS custom properties in `globals.css`. Reduce saturation 10-20% for primary/accent. Dark surfaces: #0f172a (slate-900), #1e293b (slate-800).

## Spacing
- **Base unit:** 4px
- **Density:** Comfortable
- **Scale:**
  - 2xs: 2px
  - xs: 4px
  - sm: 8px
  - md: 16px
  - lg: 24px
  - xl: 32px
  - 2xl: 48px
  - 3xl: 64px
- **Section gaps:** 48px between major sections (3xl)
- **Card internal padding:** 24px (lg) on desktop, 16px (md) on mobile
- **Grid gaps:** 16-24px between cards

## Layout
- **Approach:** Grid-disciplined — strict columns, predictable alignment
- **Grid:** 1 column mobile, 2 columns tablet, 3-4 columns desktop
- **Max content width:** 1280px (80rem), centered with auto margins
- **Border radius (hierarchical):**
  - sm: 4px — inline elements, code snippets
  - md: 8px — alerts, small badges
  - lg: 12px — buttons, inputs, small cards
  - xl: 16px — page cards, panels, hero sections
  - full: 9999px — pills, chips, status dots
- **Card pattern:** `bg-white rounded-xl shadow-sm border border-gray-200 p-6`
- **Shadow:**
  - sm: `0 1px 2px rgba(0,0,0,0.05)` — cards at rest
  - default: `0 4px 6px -1px rgba(0,0,0,0.1), 0 2px 4px -1px rgba(0,0,0,0.06)` — elevated elements

## Motion
- **Approach:** Minimal-functional — only transitions that aid comprehension
- **Easing:** enter: ease-out, exit: ease-in, move: ease-in-out
- **Duration:**
  - micro: 50-100ms (hover state changes)
  - short: 150-250ms (button transitions, border-color changes)
  - medium: 380-450ms (page entrance animations — `rise`, `slide-in`)
  - long: 400-700ms (pipeline node animation — sequential with proportional delays)
- **Existing animations:**
  - `slide-in`: 450ms ease-out (page container entrance)
  - `rise`: 380ms ease (staggered card entrance, 80ms delay between items)
- **Reduced motion:** Respect `prefers-reduced-motion` — skip entrance animations, show final state immediately
- **Pipeline animation:** Post-hoc replay of actual execution data. Total duration: 4 seconds. Per-node: `max(200ms, (node_latency / total_latency) * 4000ms)`

## CSS Custom Properties (globals.css)
All design tokens are defined as CSS custom properties on `:root` for consistency:
```css
--bg, --bg-accent, --surface, --surface-2
--text, --muted, --line
--steel (#2563eb), --steel-soft (#dbeafe)
--copper (#dc2626), --ok (#16a34a), --warn (#dc2626)
--shadow
--font-display (Inter), --font-mono (JetBrains Mono)
```

## Component Patterns
- **Buttons:** Primary (blue), Accent (amber, for CTAs like "Live Demo"), Secondary (gray border), Ghost (text-only)
- **Status dots:** 7-8px circles — green (healthy), amber (warning), red (error)
- **Alerts:** Colored background + dot + text. Success/Warning/Error/Info.
- **Cards:** White surface, gray-200 border, rounded-xl, shadow-sm. Hero cards get gradient background.
- **Inputs:** Gray-200 border, rounded-md (8px), blue focus ring with 3px shadow
- **Chips/Badges:** Pill shape (rounded-full), mono font, 1px border
- **Collapsible sections:** Gray-100 bg, rounded-lg, triangle marker, hover highlight

## Page-Specific: Document Detail (`/documents/[id]`)

### Layout
- **Two-column grid:** `grid-template-columns: 1fr 380px` at ≥768px, single column below
- **Preview panel** (left, ~65%): white surface, gray-200 border, rounded-xl. Toolbar at top with gray-50 bg.
- **AI Intelligence panel** (right, ~35%): stacked cards with 16px gap

### Hero Header
- Same DarkHeroWrapper as all demo pages
- **Breadcrumb:** `Documents > [filename]` — muted gray-500 link + gray-200 current
- **Title:** 24px Inter 700, hero-text color (#e5e7eb)
- **Meta row:** Status badge (green pill), Type badge (blue outline pill), Size, Chunks (mono), Upload date

### Document Preview
- **Toolbar:** gray-50 bg, gray-200 bottom border. Prev/Next buttons + page counter (mono) left, Zoom +/− and Download right
- **PDF rendering area:** gray-100 bg padding, white PDF page with shadow
- **PDF text layer:** enabled for text selection (renderTextLayer={true})
- **Image preview:** centered with `object-fit: contain`, max-height 600px
- **Text/code preview:** 14px JetBrains Mono, gray-50 bg with 24px padding
- **Fallback (missing file):** gray-100 bg, centered message "Original file unavailable — AI summary and chunks are still accessible" in gray-500

### AI Intelligence Panel Cards
- **Document Summary:** AI icon (20px blue-600 square, white "AI" text) + "Auto-generated" badge (gray-100 bg, gray-500 text). Summary text 14px Inter, bullet points with 6px blue-600 dots. Bold labels + normal detail text.
- **Document Details:** key-value rows with gray-200 bottom border. Labels in gray-500, values in gray-900. Numeric values in JetBrains Mono.
- **Vectorized Chunks:** Search input (gray-200 border, blue focus ring). Chunk cards with blue-600 3px left border on gray-50 bg. Text 12px, match highlights in amber-soft bg (#fef3c7). Chunk metadata in JetBrains Mono 11px gray-500.

### Action Buttons
- **"Ask AI About This Document":** amber-500 bg, white text, full width, rounded-lg. Navigates to `/workflow-chat` with document name prefilled.
- **"Download Original File":** white bg, gray-200 border, gray-700 text, full width

### Interaction States
| Feature | Loading | Empty | Error | Success |
|---------|---------|-------|-------|---------|
| Document Preview | Gray skeleton with page outline | "Empty document" + download link | "Unable to render — download instead" | Rendered content |
| AI Summary | 3 skeleton lines with pulse animation | "AI is reading this document..." (auto-retry 10s) | "Summary generation failed. Retry?" | Full summary with bullets |
| Document Details | Shimmer cards | N/A (always has basic metadata) | N/A | Metadata grid |
| Chunk Preview | 3 skeleton blocks | "No chunks — this document hasn't been vectorized" | "Unable to load chunks" | Chunk cards |
| Chunk Search | N/A (instant) | "No matches for '[query]'" with clear button | N/A | Highlighted matching chunks |

### Responsive
- **Mobile (<768px):** Single column. AI summary card on top (most important first). Document preview collapses to "View Document" button → fullscreen overlay. All touch targets 44px minimum.
- **Tablet (768-1024px):** Two columns at 55/45 ratio. AI panel slightly narrower.
- **Desktop (≥1024px):** Two columns at 1fr/380px.

### Preview Page Reference
Preview HTML at `/tmp/design-consultation-preview-doc-detail.html` — open in browser to see the full rendered design.

## Presentation Materials

All showcase materials (architecture diagrams, poster, PPT) use the same design system as the product.

- **Architecture Diagrams** (`docs/ARCHITECTURE_DIAGRAM.drawio`, `docs/PRODUCT_ARCHITECTURE.drawio`): C4 Container style with colored containers per capability path (blue=RAG, green=Cost, purple=Data Analysis). Updated 2026-03-24.
- **Capstone Poster** (`docs/CAPSTONE_POSTER.html`): Migrated to DESIGN.md tokens on 2026-03-23. Uses `--primary: #2563EB`, Inter for all headings, `--accent-teal: #F59E0B` (amber).
- **PPT**: `docs/presentation/Industry_AI_Flow_Capstone_Presentation.pptx` — binary file, manual review checklist in design plan.

## Decisions Log
| Date | Decision | Rationale |
|------|----------|-----------|
| 2026-03-21 | Initial design system created | Created by /design-consultation based on codebase analysis + competitive research (OpenSpace, Mastt, Procore) |
| 2026-03-21 | Keep Inter as primary font | Already established in codebase, changing before demo is risky. Stability > novelty. |
| 2026-03-21 | Add amber-500 as accent color | Construction industry warmth. Differentiates from blue-only competitors. Used for warnings and highlight CTAs. |
| 2026-03-21 | Dark Pipeline hero (#1a1a2e) | Deliberate departure from industry-standard white backgrounds. Creates visual hierarchy and communicates technical depth. |
| 2026-03-21 | Industrial/Utilitarian aesthetic | Matches construction industry "serious work" ethos. Function over decoration. |
| 2026-03-22 | Document Detail page design specs | Two-column layout (preview + AI panel), reuses DarkHeroWrapper, all tokens from existing system. No new colors, fonts, or patterns. Consistency with Dashboard/Cost Estimation prioritized. |
| 2026-03-23 | Poster migrated to DESIGN.md tokens | Poster's `--primary` changed from #4F46E5 (indigo) to #2563EB (blue-600). Heading font changed from Outfit to Inter. Accent changed from teal to amber-500. All presentation materials now use the unified design system. |
| 2026-03-23 | Architecture diagrams updated (C4 Container) | System Architecture + Product Architecture diagrams updated: removed llama.cpp, added CatBoost+SHAP+What-If, updated to Gemini/Zhipu dual fallback, 28 docs, JWT auth, 7 demo pages, SSE pipeline, PII detector. |
| 2026-03-23 | Module color system defined | 4-module colors (blue/amber/emerald/purple) for architecture diagrams and pipeline visualizations. CVD-safe quadrant with grayscale border-style fallbacks. |
