import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

const fetchMock = vi.fn()
const originalFetch = global.fetch
const originalLocalStorage = global.localStorage

const localStorageMock = {
  getItem: vi.fn<() => string | null>().mockReturnValue(null),
  setItem: vi.fn(),
  removeItem: vi.fn(),
  clear: vi.fn(),
}

describe('real-api-client fallback contracts', () => {
  beforeEach(() => {
    vi.resetModules()
    fetchMock.mockReset()
    global.fetch = fetchMock as unknown as typeof fetch
    global.localStorage = localStorageMock as unknown as Storage
    localStorageMock.getItem.mockReset()
    localStorageMock.getItem.mockReturnValue(null)
    localStorageMock.setItem.mockReset()
    localStorageMock.removeItem.mockReset()
    localStorageMock.clear.mockReset()
    delete process.env.NEXT_PUBLIC_ALLOW_SYNTHETIC_REAL_API_FALLBACK
    delete process.env.NEXT_PUBLIC_ALLOW_HYBRID_MOCK_FALLBACK
  })

  afterEach(() => {
    global.fetch = originalFetch
    global.localStorage = originalLocalStorage
  })

  it('throws explicit query-history error when synthetic fallback is disabled', async () => {
    fetchMock.mockRejectedValueOnce(new Error('network down'))
    const { realApiService } = await import('@/lib/real-api-client')

    await expect(realApiService.getQueryHistory()).rejects.toMatchObject({
      message: 'Query history interface is unavailable',
      status: 503,
    })
  })

  it('returns empty document list when backend proxy is temporarily unavailable', async () => {
    fetchMock.mockResolvedValueOnce(
      new Response(JSON.stringify({ detail: 'fetch failed' }), {
        status: 502,
        headers: { 'content-type': 'application/json' },
      }),
    )
    const { realApiService } = await import('@/lib/real-api-client')

    const docs = await realApiService.getDocuments()

    expect(docs).toEqual([])
  })

  it('keeps auth errors explicit for document list', async () => {
    fetchMock.mockResolvedValueOnce(
      new Response(JSON.stringify({ detail: 'Invalid or missing API key' }), {
        status: 401,
        headers: { 'content-type': 'application/json' },
      }),
    )
    const { realApiService } = await import('@/lib/real-api-client')

    await expect(realApiService.getDocuments()).rejects.toMatchObject({
      status: 401,
      message: 'Invalid or missing API key',
    })
  })

  it('returns synthetic query history only when synthetic fallback flag is enabled', async () => {
    process.env.NEXT_PUBLIC_ALLOW_SYNTHETIC_REAL_API_FALLBACK = 'true'
    vi.resetModules()
    fetchMock.mockReset()
    global.fetch = fetchMock as unknown as typeof fetch
    fetchMock.mockRejectedValueOnce(new Error('network down'))

    const { realApiService } = await import('@/lib/real-api-client')
    const history = await realApiService.getQueryHistory()

    expect(history.length).toBeGreaterThan(0)
    expect(history[0]).toHaveProperty('query')
    expect(history[0]).toHaveProperty('response')
  })

  it('does not call mock API when hybrid fallback flag is disabled', async () => {
    fetchMock.mockRejectedValueOnce(new Error('health check down'))
    const { createHybridApiClient } = await import('@/lib/real-api-client')
    const mockApi = {
      sendQuery: vi.fn(),
    }

    const hybridApi = createHybridApiClient(mockApi)
    await expect(hybridApi.sendWorkflowQuery({ query: 'test' })).rejects.toMatchObject({
      message: 'Backend service is unavailable',
      status: 503,
    })
    expect(mockApi.sendQuery).not.toHaveBeenCalled()
  })

  it('falls back to mock API only when hybrid fallback flag is enabled', async () => {
    process.env.NEXT_PUBLIC_ALLOW_HYBRID_MOCK_FALLBACK = 'true'
    vi.resetModules()
    fetchMock.mockReset()
    global.fetch = fetchMock as unknown as typeof fetch
    fetchMock.mockRejectedValueOnce(new Error('health check down'))

    const { createHybridApiClient } = await import('@/lib/real-api-client')
    const mockPayload = {
      query: 'test',
      response: 'mock response',
      timestamp: '2026-02-20T00:00:00.000Z',
    }
    const mockApi = {
      sendQuery: vi.fn().mockResolvedValue(mockPayload),
    }

    const hybridApi = createHybridApiClient(mockApi)
    const result = await hybridApi.sendWorkflowQuery({ query: 'test' })

    expect(mockApi.sendQuery).toHaveBeenCalledWith({ query: 'test' })
    expect(result).toEqual(mockPayload)
  })
})
