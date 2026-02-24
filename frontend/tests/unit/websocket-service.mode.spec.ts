import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

const originalMockFlag = process.env.NEXT_PUBLIC_USE_MOCK_WS
const originalWsUrl = process.env.NEXT_PUBLIC_WS_URL

describe('websocket service mode selection', () => {
  beforeEach(() => {
    vi.resetModules()
    delete process.env.NEXT_PUBLIC_USE_MOCK_WS
    delete process.env.NEXT_PUBLIC_WS_URL
  })

  afterEach(() => {
    if (originalMockFlag === undefined) {
      delete process.env.NEXT_PUBLIC_USE_MOCK_WS
    } else {
      process.env.NEXT_PUBLIC_USE_MOCK_WS = originalMockFlag
    }

    if (originalWsUrl === undefined) {
      delete process.env.NEXT_PUBLIC_WS_URL
    } else {
      process.env.NEXT_PUBLIC_WS_URL = originalWsUrl
    }
  })

  it('defaults to real websocket service when mock flag is absent', async () => {
    const mod = await import('@/lib/websocket-service')
    const service = mod.createWebSocketService()

    expect(service).toBeInstanceOf(mod.WebSocketService)
    expect(service).not.toBeInstanceOf(mod.MockWebSocketService)
  })

  it('uses mock websocket service when NEXT_PUBLIC_USE_MOCK_WS is true', async () => {
    process.env.NEXT_PUBLIC_USE_MOCK_WS = 'true'
    const mod = await import('@/lib/websocket-service')
    const service = mod.createWebSocketService()

    expect(service).toBeInstanceOf(mod.MockWebSocketService)
  })

  it('lets explicit argument override env mock flag', async () => {
    process.env.NEXT_PUBLIC_USE_MOCK_WS = 'true'
    const mod = await import('@/lib/websocket-service')
    const service = mod.createWebSocketService(false)

    expect(service).toBeInstanceOf(mod.WebSocketService)
    expect(service).not.toBeInstanceOf(mod.MockWebSocketService)
  })
})
