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

  it('keeps mvp routes on sidebar-free shell wrapper to prevent left-column collapse', () => {
    const mvpLayout = readFrontendFile('src/app/(mvp)/layout.tsx')
    const simpleShell = readFrontendFile('src/components/dashboard-shell-simple.tsx')

    expect(mvpLayout).toContain('dashboard-shell-simple')
    expect(mvpLayout).toContain('<DashboardShell>{children}</DashboardShell>')
    expect(simpleShell).toContain('shell-root-simple')
    expect(simpleShell).toContain('shell-main-simple')
    expect(simpleShell).toContain('shell-content')
  })

  it('preserves shell-main-simple width contract in global styles', () => {
    const globalsCss = readFrontendFile('src/app/globals.css')
    const shellMainSimpleBlock = globalsCss.match(/\.shell-main-simple\s*\{[^}]*\}/s)?.[0] ?? ''

    expect(shellMainSimpleBlock).toContain('padding: 1rem 1.2rem 2rem;')
    expect(shellMainSimpleBlock).toContain('width: min(1280px, 100%);')
    expect(shellMainSimpleBlock).toContain('margin: 0 auto;')
  })
})
