import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

const fetchMock = vi.fn()
const originalFetch = global.fetch

const localStorageStore = new Map<string, string>()
const localStorageMock: Storage = {
  get length() {
    return localStorageStore.size
  },
  clear: vi.fn(() => localStorageStore.clear()),
  getItem: vi.fn((k: string) => (localStorageStore.has(k) ? localStorageStore.get(k)! : null)),
  key: vi.fn((i: number) => Array.from(localStorageStore.keys())[i] ?? null),
  removeItem: vi.fn((k: string) => {
    localStorageStore.delete(k)
  }),
  setItem: vi.fn((k: string, v: string) => {
    localStorageStore.set(k, v)
  }),
}

function jsonResponse(status: number, body: unknown): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'content-type': 'application/json' },
  })
}

describe('api-client 401 handling', () => {
  let dispatchSpy: ReturnType<typeof vi.spyOn>

  beforeEach(() => {
    vi.resetModules()
    fetchMock.mockReset()
    localStorageStore.clear()
    localStorageStore.set('industry-aiflow-token', 'fake.jwt.tok')
    localStorageStore.set('industry-aiflow-user', JSON.stringify({ id: '1' }))
    global.fetch = fetchMock as unknown as typeof fetch
    Object.defineProperty(globalThis, 'localStorage', {
      configurable: true,
      value: localStorageMock,
    })
    dispatchSpy = vi.spyOn(window, 'dispatchEvent')
  })

  afterEach(() => {
    global.fetch = originalFetch
    dispatchSpy.mockRestore()
  })

  it('clears auth + dispatches auth:expired on 401 from a protected endpoint', async () => {
    fetchMock.mockResolvedValueOnce(jsonResponse(401, { detail: 'expired' }))
    const { api, AUTH_EXPIRED_EVENT } = await import('@/lib/api-client')

    await expect(api.get('/cost-estimation/health')).rejects.toMatchObject({ status: 401 })

    expect(localStorageStore.has('industry-aiflow-token')).toBe(false)
    expect(localStorageStore.has('industry-aiflow-user')).toBe(false)
    const expiredEvents = dispatchSpy.mock.calls.filter(
      (call) => (call[0] as Event).type === AUTH_EXPIRED_EVENT,
    )
    expect(expiredEvents.length).toBe(1)
  })

  it('does NOT clear auth on 401 from /auth/login (bad credentials)', async () => {
    fetchMock.mockResolvedValueOnce(jsonResponse(401, { detail: 'bad password' }))
    const { authApi, AUTH_EXPIRED_EVENT } = await import('@/lib/api-client')

    await expect(authApi.login('a@b.c', 'wrong')).rejects.toMatchObject({ status: 401 })

    // Storage untouched.
    expect(localStorageStore.get('industry-aiflow-token')).toBe('fake.jwt.tok')
    const expiredEvents = dispatchSpy.mock.calls.filter(
      (call) => (call[0] as Event).type === AUTH_EXPIRED_EVENT,
    )
    expect(expiredEvents.length).toBe(0)
  })

  it('does NOT clear auth on 401 from /auth/register', async () => {
    fetchMock.mockResolvedValueOnce(jsonResponse(401, { detail: 'taken' }))
    const { authApi, AUTH_EXPIRED_EVENT } = await import('@/lib/api-client')

    await expect(authApi.register('x', 'a@b.c', 'pw')).rejects.toMatchObject({
      status: 401,
    })

    expect(localStorageStore.get('industry-aiflow-token')).toBe('fake.jwt.tok')
    expect(
      dispatchSpy.mock.calls.some(
        (call) => (call[0] as Event).type === AUTH_EXPIRED_EVENT,
      ),
    ).toBe(false)
  })

  it('does NOT clear auth on 500 from a protected endpoint', async () => {
    fetchMock.mockResolvedValueOnce(jsonResponse(500, { detail: 'oops' }))
    const { api, AUTH_EXPIRED_EVENT } = await import('@/lib/api-client')

    await expect(api.get('/cost-estimation/health')).rejects.toMatchObject({ status: 500 })

    expect(localStorageStore.get('industry-aiflow-token')).toBe('fake.jwt.tok')
    expect(
      dispatchSpy.mock.calls.some(
        (call) => (call[0] as Event).type === AUTH_EXPIRED_EVENT,
      ),
    ).toBe(false)
  })

  it('clears auth on 401 from /auth/me (canonical token-dead signal)', async () => {
    fetchMock.mockResolvedValueOnce(jsonResponse(401, { detail: 'expired' }))
    const { authApi, AUTH_EXPIRED_EVENT } = await import('@/lib/api-client')

    await expect(authApi.getCurrentUser()).rejects.toMatchObject({ status: 401 })

    expect(localStorageStore.has('industry-aiflow-token')).toBe(false)
    expect(
      dispatchSpy.mock.calls.some(
        (call) => (call[0] as Event).type === AUTH_EXPIRED_EVENT,
      ),
    ).toBe(true)
  })
})
