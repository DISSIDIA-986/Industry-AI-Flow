// Base64URL-safe JWT payload decoder.
// JWT uses RFC 4648 §5 base64url (- and _ instead of + and /, padding optional).
// Native atob requires standard base64 with padding, so we normalize first.

export interface JwtPayload {
  exp?: number
  iat?: number
  sub?: string
  [k: string]: unknown
}

export function decodeJwtPayload(token: string): JwtPayload | null {
  if (typeof token !== 'string' || token.length === 0) return null
  const parts = token.split('.')
  if (parts.length !== 3) return null

  let b64 = parts[1].replace(/-/g, '+').replace(/_/g, '/')
  const pad = b64.length % 4
  if (pad === 2) b64 += '=='
  else if (pad === 3) b64 += '='
  else if (pad !== 0) return null

  try {
    const json =
      typeof atob === 'function'
        ? atob(b64)
        : Buffer.from(b64, 'base64').toString('binary')
    // Handle UTF-8 in claims (e.g. names with accents).
    const utf8 = decodeURIComponent(
      Array.from(json)
        .map((c) => '%' + c.charCodeAt(0).toString(16).padStart(2, '0'))
        .join(''),
    )
    const parsed = JSON.parse(utf8)
    if (parsed && typeof parsed === 'object') return parsed as JwtPayload
    return null
  } catch {
    return null
  }
}

// Returns true if the JWT is expired beyond the clock-skew grace.
// Tokens without `exp` are treated as not expired here (server is the
// authority via 401). Returning false on missing exp avoids logging out
// users on tokens that simply omit the claim.
export function isJwtExpired(token: string, graceSeconds = 30): boolean {
  const payload = decodeJwtPayload(token)
  if (!payload) return true // malformed => treat as expired
  if (typeof payload.exp !== 'number') return false
  return payload.exp * 1000 < Date.now() - graceSeconds * 1000
}
