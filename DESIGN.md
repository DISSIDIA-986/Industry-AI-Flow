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
- **Dark Hero Section:** #1a1a2e — used ONLY for the Pipeline visualization hero. This is a deliberate departure from the light theme to create visual contrast and convey technical depth. Text on dark: #e5e7eb (gray-200), muted: #6b7280 (gray-500), active nodes: #60a5fa (blue-400), completed nodes: #34d399 (emerald-400).
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

## Decisions Log
| Date | Decision | Rationale |
|------|----------|-----------|
| 2026-03-21 | Initial design system created | Created by /design-consultation based on codebase analysis + competitive research (OpenSpace, Mastt, Procore) |
| 2026-03-21 | Keep Inter as primary font | Already established in codebase, changing before demo is risky. Stability > novelty. |
| 2026-03-21 | Add amber-500 as accent color | Construction industry warmth. Differentiates from blue-only competitors. Used for warnings and highlight CTAs. |
| 2026-03-21 | Dark Pipeline hero (#1a1a2e) | Deliberate departure from industry-standard white backgrounds. Creates visual hierarchy and communicates technical depth. |
| 2026-03-21 | Industrial/Utilitarian aesthetic | Matches construction industry "serious work" ethos. Function over decoration. |
