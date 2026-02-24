import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

const fetchMock = vi.fn()
const originalFetch = global.fetch
const originalWindowFetch = globalThis.window?.fetch
const originalLocalStorage = global.localStorage
const localStorageMock = {
  getItem: vi.fn<() => string | null>().mockReturnValue(null),
  setItem: vi.fn(),
  removeItem: vi.fn(),
  clear: vi.fn(),
}

function mockJsonResponse(payload: unknown, status = 200): Response {
  return new Response(JSON.stringify(payload), {
    status,
    headers: { 'content-type': 'application/json' },
  })
}

describe('workflowApi request contracts', () => {
  beforeEach(() => {
    vi.resetModules()
    fetchMock.mockReset()
    localStorageMock.getItem.mockReset()
    localStorageMock.getItem.mockReturnValue(null)
    localStorageMock.setItem.mockReset()
    localStorageMock.removeItem.mockReset()
    localStorageMock.clear.mockReset()

    global.fetch = fetchMock as unknown as typeof fetch
    globalThis.fetch = fetchMock as unknown as typeof fetch
    if (globalThis.window) {
      globalThis.window.fetch = fetchMock as unknown as typeof fetch
    }
    Object.defineProperty(globalThis, 'localStorage', {
      value: localStorageMock,
      configurable: true,
    })
    delete process.env.NEXT_PUBLIC_WORKFLOW_QUERY_TIMEOUT_MS
  })

  afterEach(() => {
    global.fetch = originalFetch
    globalThis.fetch = originalFetch
    if (globalThis.window) {
      globalThis.window.fetch = originalWindowFetch as typeof fetch
    }
    Object.defineProperty(globalThis, 'localStorage', {
      value: originalLocalStorage,
      configurable: true,
    })
  })

  it('sends stable session and thread ids to workflow query endpoint', async () => {
    fetchMock.mockResolvedValueOnce(
      mockJsonResponse({
        trace_id: 'trace-1',
        response: 'ok',
        metadata: {},
      }),
    )

    const { workflowApi } = await import('@/lib/api-client')
    await workflowApi.sendQuery(
      {
        query: 'Need standards summary',
        session_id: 'session-abc',
        thread_id: 'thread-abc',
      },
      { userId: 'user-42' },
    )

    expect(fetchMock).toHaveBeenCalledTimes(1)
    const [, requestInit] = fetchMock.mock.calls[0] as [string, RequestInit]
    const body = JSON.parse(String(requestInit.body))

    expect(body.query).toBe('Need standards summary')
    expect(body.session_id).toBe('session-abc')
    expect(body.thread_id).toBe('thread-abc')
    expect(body.user_id).toBe('user-42')
  })

  it('normalizes source list from metadata when top-level sources are absent', async () => {
    fetchMock.mockResolvedValueOnce(
      mockJsonResponse({
        trace_id: 'trace-2',
        response: 'grounded answer',
        metadata: {
          agent_execution: {
            sources: [
              {
                doc_id: 'doc-1',
                filename: 'guide.pdf',
                score: 0.83,
                content: 'Guideline',
              },
            ],
          },
        },
      }),
    )

    const { workflowApi } = await import('@/lib/api-client')
    const result = await workflowApi.sendQuery({ query: 'Need standards summary' })

    expect(result.sources).toEqual([
      {
        document_id: 'doc-1',
        document_name: 'guide.pdf',
        relevance: 0.83,
        content: 'Guideline',
      },
    ])
  })

  it('returns suggested follow-up questions from metadata', async () => {
    fetchMock.mockResolvedValueOnce(
      mockJsonResponse({
        trace_id: 'trace-3',
        response: 'grounded answer',
        metadata: {
          suggested_questions: [
            'What evidence supports this answer?',
            'What are the exceptions in this standard?',
          ],
        },
      }),
    )

    const { workflowApi } = await import('@/lib/api-client')
    const result = await workflowApi.sendQuery({ query: 'Need standards summary' })

    expect(result.suggested_questions).toEqual([
      'What evidence supports this answer?',
      'What are the exceptions in this standard?',
    ])
    expect(result.metadata).toBeTruthy()
  })

  it('extracts follow-up questions from agent_execution metadata', async () => {
    fetchMock.mockResolvedValueOnce(
      mockJsonResponse({
        trace_id: 'trace-3b',
        response: 'grounded answer',
        metadata: {
          agent_execution: {
            suggested_questions: [
              'Which clause in this source is most relevant?',
              'Do these requirements change by project type?',
            ],
          },
        },
      }),
    )

    const { workflowApi } = await import('@/lib/api-client')
    const result = await workflowApi.sendQuery({ query: 'Need standards summary' })

    expect(result.suggested_questions).toEqual([
      'Which clause in this source is most relevant?',
      'Do these requirements change by project type?',
    ])
  })

  it('uses configured extended timeout for workflow query', async () => {
    process.env.NEXT_PUBLIC_WORKFLOW_QUERY_TIMEOUT_MS = '95000'
    const timeoutSpy = vi.spyOn(globalThis, 'setTimeout')
    fetchMock.mockResolvedValueOnce(
      mockJsonResponse({
        trace_id: 'trace-4',
        response: 'ok',
        metadata: {},
      }),
    )

    const { workflowApi } = await import('@/lib/api-client')
    await workflowApi.sendQuery({ query: 'Need standards summary' })

    const timeoutValues = timeoutSpy.mock.calls.map((call) => Number(call[1]))
    expect(timeoutValues).toContain(95000)
    timeoutSpy.mockRestore()
  })

  it('uses extended default timeout for workflow query when env is absent', async () => {
    const timeoutSpy = vi.spyOn(globalThis, 'setTimeout')
    fetchMock.mockResolvedValueOnce(
      mockJsonResponse({
        trace_id: 'trace-5',
        response: 'ok',
        metadata: {},
      }),
    )

    const { workflowApi } = await import('@/lib/api-client')
    await workflowApi.sendQuery({ query: 'Need standards summary' })

    const timeoutValues = timeoutSpy.mock.calls.map((call) => Number(call[1]))
    expect(timeoutValues).toContain(240000)
    timeoutSpy.mockRestore()
  })
})
