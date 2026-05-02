'use client'

import { createContext, useContext, useState, useEffect, useRef, ReactNode } from 'react'
import { useRouter, usePathname } from 'next/navigation'
import { authApi, AUTH_TOKEN_KEY, AUTH_USER_KEY, AUTH_EXPIRED_EVENT } from '@/lib/api-client'
import { isJwtExpired } from '@/lib/jwt'

interface User {
  id: string
  name: string
  email: string
  roles: string[]
}

interface AuthContextType {
  user: User | null
  token: string | null
  loading: boolean
  error: string | null
  login: (email: string, password: string) => Promise<void>
  register: (name: string, email: string, password: string) => Promise<void>
  logout: () => Promise<void>
  clearError: () => void
}

const AuthContext = createContext<AuthContextType | undefined>(undefined)

function readStoredAuth(): { token: string; user: User } | null {
  if (typeof window === 'undefined') return null
  const storedToken = localStorage.getItem(AUTH_TOKEN_KEY)
  const storedUser = localStorage.getItem(AUTH_USER_KEY)
  // Inconsistent halves -> treat as no auth.
  if (!storedToken || !storedUser) return null
  if (isJwtExpired(storedToken)) return null
  try {
    const parsedUser = JSON.parse(storedUser) as User
    if (!parsedUser || typeof parsedUser !== 'object') return null
    return { token: storedToken, user: parsedUser }
  } catch {
    return null
  }
}

function clearStoredAuth() {
  if (typeof window === 'undefined') return
  localStorage.removeItem(AUTH_TOKEN_KEY)
  localStorage.removeItem(AUTH_USER_KEY)
  localStorage.removeItem('token') // legacy key cleanup
}

function writeStoredAuth(token: string, user: User) {
  localStorage.setItem(AUTH_TOKEN_KEY, token)
  localStorage.setItem(AUTH_USER_KEY, JSON.stringify(user))
}

export function AuthProvider({ children }: { children: ReactNode }) {
  // Initialize synchronously from localStorage so the first render already
  // reflects validated auth state. This prevents protected pages from
  // mounting and firing requests with a stale token before the boot effect
  // can clear it.
  const [auth, setAuth] = useState<{ token: string; user: User } | null>(() =>
    readStoredAuth(),
  )
  // After the synchronous read, if storage was inconsistent or expired,
  // remove the leftover halves. Done in an effect because we cannot touch
  // localStorage during initial render in some SSR setups.
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const router = useRouter()
  const pathname = usePathname()
  const expiredHandlingRef = useRef(false)

  // Boot cleanup: if localStorage had partial/expired state, scrub it.
  useEffect(() => {
    if (typeof window === 'undefined') return
    const tok = localStorage.getItem(AUTH_TOKEN_KEY)
    const usr = localStorage.getItem(AUTH_USER_KEY)
    const consistent = !!tok && !!usr && !isJwtExpired(tok)
    if (!consistent && (tok || usr || localStorage.getItem('token'))) {
      clearStoredAuth()
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  // Centralized auth-expiry handler. Used by both 401 events and
  // multi-tab storage events. Debounced so 4 parallel 401s on /overview
  // don't trigger 4 redirects.
  useEffect(() => {
    if (typeof window === 'undefined') return

    const onExpired = () => {
      if (expiredHandlingRef.current) return
      expiredHandlingRef.current = true
      // Reset the latch a tick later so a future expiry (e.g. user logs
      // back in then expires again) is still handled.
      setTimeout(() => {
        expiredHandlingRef.current = false
      }, 1000)

      clearStoredAuth()
      setAuth(null)
      if (pathname !== '/login') {
        router.push('/login?reason=expired')
      }
    }

    const onStorage = (e: StorageEvent) => {
      // Another tab cleared either half of the auth state -> log out here too.
      if (
        (e.key === AUTH_TOKEN_KEY || e.key === AUTH_USER_KEY) &&
        e.newValue === null
      ) {
        onExpired()
      }
    }

    window.addEventListener(AUTH_EXPIRED_EVENT, onExpired as EventListener)
    window.addEventListener('storage', onStorage)
    return () => {
      window.removeEventListener(AUTH_EXPIRED_EVENT, onExpired as EventListener)
      window.removeEventListener('storage', onStorage)
    }
  }, [pathname, router])

  const login = async (email: string, password: string) => {
    setLoading(true)
    setError(null)

    try {
      const response = await authApi.login(email, password)
      writeStoredAuth(response.token, response.user)
      setAuth({ token: response.token, user: response.user })
      router.push('/overview')
    } catch (err: unknown) {
      const errorMessage =
        err instanceof Error
          ? err.message
          : 'Login failed, please check your email and password'
      setError(errorMessage)
      throw new Error(errorMessage)
    } finally {
      setLoading(false)
    }
  }

  const register = async (name: string, email: string, password: string) => {
    setLoading(true)
    setError(null)

    try {
      const response = await authApi.register(name, email, password)
      writeStoredAuth(response.token, response.user)
      setAuth({ token: response.token, user: response.user })
      router.push('/overview')
    } catch (err: unknown) {
      const errorMessage =
        err instanceof Error ? err.message : 'Registration failed, please try again later'
      setError(errorMessage)
      throw new Error(errorMessage)
    } finally {
      setLoading(false)
    }
  }

  const logout = async () => {
    setLoading(true)
    try {
      await authApi.logout()
    } catch (err) {
      // even if API call fails, clear local state.
      console.error('Logout API error:', err)
    } finally {
      clearStoredAuth()
      setAuth(null)
      setLoading(false)
      router.push('/login')
    }
  }

  const clearError = () => setError(null)

  const value: AuthContextType = {
    user: auth?.user ?? null,
    token: auth?.token ?? null,
    loading,
    error,
    login,
    register,
    logout,
    clearError,
  }

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth() {
  const context = useContext(AuthContext)
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider')
  }
  return context
}
