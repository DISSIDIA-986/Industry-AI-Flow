import { act, render, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { AuthProvider, useAuth } from '@/contexts/AuthContext'

const pushMock = vi.fn()
let pathname = '/overview'

vi.mock('next/navigation', () => ({
  useRouter: () => ({ push: pushMock, replace: pushMock }),
  usePathname: () => pathname,
}))

// Stub authApi so login/logout don't hit the network.
vi.mock('@/lib/api-client', async () => {
  const actual = await vi.importActual<typeof import('@/lib/api-client')>(
    '@/lib/api-client',
  )
  return {
    ...actual,
    authApi: {
      login: vi.fn(),
      register: vi.fn(),
      logout: vi.fn().mockResolvedValue({ success: true }),
      getCurrentUser: vi.fn(),
    },
  }
})

function b64url(obj: unknown): string {
  return Buffer.from(JSON.stringify(obj))
    .toString('base64')
    .replace(/\+/g, '-')
    .replace(/\//g, '_')
    .replace(/=+$/, '')
}
function makeJwt(payload: unknown): string {
  return `${b64url({ alg: 'HS256', typ: 'JWT' })}.${b64url(payload)}.sig`
}

function Probe() {
  const { user, token } = useAuth()
  return (
    <div>
      <span data-testid="user">{user ? user.name : 'none'}</span>
      <span data-testid="token">{token ?? 'none'}</span>
    </div>
  )
}

describe('AuthContext', () => {
  beforeEach(() => {
    pushMock.mockReset()
    pathname = '/overview'
    localStorage.clear()
  })

  afterEach(() => {
    localStorage.clear()
  })

  it('restores user when token+user pair is valid and unexpired', async () => {
    const t = makeJwt({ sub: '1', exp: Math.floor(Date.now() / 1000) + 3600 })
    localStorage.setItem('industry-aiflow-token', t)
    localStorage.setItem(
      'industry-aiflow-user',
      JSON.stringify({ id: '1', name: 'Demo', email: 'd@e.f', roles: [] }),
    )

    const { getByTestId } = render(
      <AuthProvider>
        <Probe />
      </AuthProvider>,
    )

    expect(getByTestId('user').textContent).toBe('Demo')
    expect(getByTestId('token').textContent).toBe(t)
  })

  it('does not restore an expired token and scrubs storage', async () => {
    const expired = makeJwt({ sub: '1', exp: Math.floor(Date.now() / 1000) - 3600 })
    localStorage.setItem('industry-aiflow-token', expired)
    localStorage.setItem(
      'industry-aiflow-user',
      JSON.stringify({ id: '1', name: 'Demo', email: 'd@e.f', roles: [] }),
    )

    const { getByTestId } = render(
      <AuthProvider>
        <Probe />
      </AuthProvider>,
    )

    expect(getByTestId('user').textContent).toBe('none')
    await waitFor(() => {
      expect(localStorage.getItem('industry-aiflow-token')).toBeNull()
      expect(localStorage.getItem('industry-aiflow-user')).toBeNull()
    })
  })

  it('does not restore when token exists without user (split storage)', async () => {
    const t = makeJwt({ sub: '1', exp: Math.floor(Date.now() / 1000) + 3600 })
    localStorage.setItem('industry-aiflow-token', t)
    // User missing.

    const { getByTestId } = render(
      <AuthProvider>
        <Probe />
      </AuthProvider>,
    )

    expect(getByTestId('user').textContent).toBe('none')
    await waitFor(() => {
      expect(localStorage.getItem('industry-aiflow-token')).toBeNull()
    })
  })

  it('does not restore when user JSON is corrupted', async () => {
    const t = makeJwt({ sub: '1', exp: Math.floor(Date.now() / 1000) + 3600 })
    localStorage.setItem('industry-aiflow-token', t)
    localStorage.setItem('industry-aiflow-user', '{not json')

    const { getByTestId } = render(
      <AuthProvider>
        <Probe />
      </AuthProvider>,
    )

    expect(getByTestId('user').textContent).toBe('none')
  })

  it('handles auth:expired event: clears state and pushes /login?reason=expired', async () => {
    const t = makeJwt({ sub: '1', exp: Math.floor(Date.now() / 1000) + 3600 })
    localStorage.setItem('industry-aiflow-token', t)
    localStorage.setItem(
      'industry-aiflow-user',
      JSON.stringify({ id: '1', name: 'Demo', email: 'd@e.f', roles: [] }),
    )

    const { getByTestId } = render(
      <AuthProvider>
        <Probe />
      </AuthProvider>,
    )
    expect(getByTestId('user').textContent).toBe('Demo')

    await act(async () => {
      window.dispatchEvent(new CustomEvent('auth:expired'))
    })

    expect(getByTestId('user').textContent).toBe('none')
    expect(pushMock).toHaveBeenCalledWith('/login?reason=expired')
    expect(localStorage.getItem('industry-aiflow-token')).toBeNull()
  })

  it('debounces N parallel auth:expired events to a single redirect', async () => {
    const t = makeJwt({ sub: '1', exp: Math.floor(Date.now() / 1000) + 3600 })
    localStorage.setItem('industry-aiflow-token', t)
    localStorage.setItem(
      'industry-aiflow-user',
      JSON.stringify({ id: '1', name: 'Demo', email: 'd@e.f', roles: [] }),
    )

    render(
      <AuthProvider>
        <Probe />
      </AuthProvider>,
    )

    await act(async () => {
      // Simulate 4 parallel 401s firing simultaneously.
      window.dispatchEvent(new CustomEvent('auth:expired'))
      window.dispatchEvent(new CustomEvent('auth:expired'))
      window.dispatchEvent(new CustomEvent('auth:expired'))
      window.dispatchEvent(new CustomEvent('auth:expired'))
    })

    expect(pushMock).toHaveBeenCalledTimes(1)
    expect(pushMock).toHaveBeenCalledWith('/login?reason=expired')
  })

  it('does not redirect if already on /login', async () => {
    pathname = '/login'
    const t = makeJwt({ sub: '1', exp: Math.floor(Date.now() / 1000) + 3600 })
    localStorage.setItem('industry-aiflow-token', t)
    localStorage.setItem(
      'industry-aiflow-user',
      JSON.stringify({ id: '1', name: 'Demo', email: 'd@e.f', roles: [] }),
    )

    render(
      <AuthProvider>
        <Probe />
      </AuthProvider>,
    )

    await act(async () => {
      window.dispatchEvent(new CustomEvent('auth:expired'))
    })

    expect(pushMock).not.toHaveBeenCalled()
  })

  it('reacts to multi-tab logout via storage event on token key', async () => {
    const t = makeJwt({ sub: '1', exp: Math.floor(Date.now() / 1000) + 3600 })
    localStorage.setItem('industry-aiflow-token', t)
    localStorage.setItem(
      'industry-aiflow-user',
      JSON.stringify({ id: '1', name: 'Demo', email: 'd@e.f', roles: [] }),
    )

    const { getByTestId } = render(
      <AuthProvider>
        <Probe />
      </AuthProvider>,
    )
    expect(getByTestId('user').textContent).toBe('Demo')

    await act(async () => {
      window.dispatchEvent(
        new StorageEvent('storage', {
          key: 'industry-aiflow-token',
          newValue: null,
        }),
      )
    })

    expect(getByTestId('user').textContent).toBe('none')
    expect(pushMock).toHaveBeenCalledWith('/login?reason=expired')
  })

  it('reacts to multi-tab logout via storage event on user key', async () => {
    const t = makeJwt({ sub: '1', exp: Math.floor(Date.now() / 1000) + 3600 })
    localStorage.setItem('industry-aiflow-token', t)
    localStorage.setItem(
      'industry-aiflow-user',
      JSON.stringify({ id: '1', name: 'Demo', email: 'd@e.f', roles: [] }),
    )

    render(
      <AuthProvider>
        <Probe />
      </AuthProvider>,
    )

    await act(async () => {
      window.dispatchEvent(
        new StorageEvent('storage', {
          key: 'industry-aiflow-user',
          newValue: null,
        }),
      )
    })

    expect(pushMock).toHaveBeenCalledWith('/login?reason=expired')
  })
})
