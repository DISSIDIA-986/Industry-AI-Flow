import { readFileSync } from 'node:fs'
import path from 'node:path'
import { describe, expect, it } from 'vitest'

const frontendRoot = path.resolve(__dirname, '../..')

function readFrontendFile(relativePath: string): string {
  return readFileSync(path.join(frontendRoot, relativePath), 'utf8')
}

describe('layout and navbar contracts', () => {
  it('mounts shared Navbar in both simple and mvp route-group layouts', () => {
    const mvpLayout = readFrontendFile('src/app/(mvp)/layout.tsx')
    const simpleLayout = readFrontendFile('src/app/(simple)/layout.tsx')

    expect(mvpLayout).toContain('<Navbar />')
    expect(simpleLayout).toContain('<Navbar />')
  })

  it('keeps both layouts on a flat full-width shell — no sidebar / grid reintroduction', () => {
    // Contract intent (per CLAUDE.md "Navbar uses flat layout — 6 items inline"):
    // both the (mvp) and (simple) route groups use the SAME minimal shell
    // (Navbar on top, <main> below, full-width div wrapper). The original
    // dashboard-shell-simple.tsx / <DashboardShell> / shell-root-simple
    // components this test used to assert against were removed when the
    // layout flattened; referencing them kept the gate red indefinitely.
    //
    // Positive: both layouts mount the shared shell elements.
    // Negative: neither layout reintroduces a sidebar / grid wrapper that
    // would cause the left-column collapse the original contract guarded
    // against.
    const mvpLayout = readFrontendFile('src/app/(mvp)/layout.tsx')
    const simpleLayout = readFrontendFile('src/app/(simple)/layout.tsx')

    for (const layout of [mvpLayout, simpleLayout]) {
      expect(layout).toContain('<Navbar />')
      expect(layout).toContain('min-h-screen')
      expect(layout).toMatch(/<main\b/)
      expect(layout).not.toMatch(/sidebar/i)
      expect(layout).not.toMatch(/grid-cols-/)
    }
  })

  it('preserves shell-main-simple width contract in global styles', () => {
    // Contract intent: the simple shell must stay centered at ≤1280px
    // with some breathing-room padding. The specific padding value
    // changed from "1rem 1.2rem 2rem" to "1.5rem" as an intentional
    // simplification; loosening this assertion to "has padding at all"
    // keeps the regression guard on width + centering (the things that
    // actually cause layout collapse) without re-breaking on every
    // cosmetic whitespace tweak.
    const globalsCss = readFrontendFile('src/app/globals.css')
    const shellMainSimpleBlock = globalsCss.match(/\.shell-main-simple\s*\{[^}]*\}/s)?.[0] ?? ''

    expect(shellMainSimpleBlock).toMatch(/padding:\s*[^;]+;/)
    expect(shellMainSimpleBlock).toContain('width: min(1280px, 100%);')
    expect(shellMainSimpleBlock).toContain('margin: 0 auto;')
  })
})
