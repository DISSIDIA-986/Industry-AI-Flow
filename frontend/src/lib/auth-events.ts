// Shared auth helpers used by both api-client and real-api-client.
// Lives in its own module to avoid the import cycle that arises if
// real-api-client (imported by api-client) tries to import back from
// api-client.

export const AUTH_TOKEN_KEY = 'industry-aiflow-token'
export const AUTH_USER_KEY = 'industry-aiflow-user'
export const AUTH_EXPIRED_EVENT = 'auth:expired'

export function clearStoredAuth(): void {
  if (typeof window === 'undefined') return
  localStorage.removeItem(AUTH_TOKEN_KEY)
  localStorage.removeItem(AUTH_USER_KEY)
  // Drop legacy key from older builds, if present.
  localStorage.removeItem('token')
}

// Endpoints whose 401 means "bad credentials, not session expiry".
// Matches by suffix so both '/api/v1/auth/login' and '/api/backend/api/v1/auth/login' work.
// /auth/me and /auth/logout are intentionally NOT here — a 401 from them
// is the canonical "your token is dead" signal.
export function isAuthCredentialEndpoint(path: string): boolean {
  return /\/api\/v1\/auth\/(login|register)$/.test(path)
}

export function handleUnauthorized(path: string): void {
  if (typeof window === 'undefined') return
  if (isAuthCredentialEndpoint(path)) return
  clearStoredAuth()
  window.dispatchEvent(new CustomEvent(AUTH_EXPIRED_EVENT))
}
