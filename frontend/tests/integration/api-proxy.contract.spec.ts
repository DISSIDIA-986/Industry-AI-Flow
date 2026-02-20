import { readFileSync } from 'node:fs'
import path from 'node:path'
import { describe, expect, it } from 'vitest'

const frontendRoot = path.resolve(__dirname, '../..')

function readFrontendFile(relativePath: string): string {
  return readFileSync(path.join(frontendRoot, relativePath), 'utf8')
}

describe('api proxy source contracts', () => {
  it('uses same-origin backend proxy base in real-api-client', () => {
    const realApiClient = readFrontendFile('src/lib/real-api-client.ts')

    expect(realApiClient).toContain("const REAL_API_BASE_URL = '/api/backend/api/v1'")
    expect(realApiClient).not.toMatch(/localhost:8001|localhost:8002/)
  })

  it('keeps diagnostics pages aligned to same-origin proxy and avoids localhost hints', () => {
    const apiTestPage = readFrontendFile('src/app/(mvp)/api-test/page.tsx')
    const apiIntegrationPage = readFrontendFile('src/app/(mvp)/api-integration-test/page.tsx')

    expect(apiTestPage).toContain("import { api } from '@/lib/api-client'")
    expect(apiTestPage).toContain('/api/backend/api/v1 (同源代理)')
    expect(apiIntegrationPage).toContain('/api/backend/api/v1 (同源代理)')
    expect(apiTestPage).not.toMatch(/localhost:8001|localhost:8002/)
    expect(apiIntegrationPage).not.toMatch(/localhost:8001|localhost:8002/)
  })
})
