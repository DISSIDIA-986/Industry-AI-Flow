import { describe, expect, it } from 'vitest'
import { decodeJwtPayload, isJwtExpired } from '@/lib/jwt'

// Helpers: build a fake JWT with header.payload.signature.
// We don't need a valid signature, only a parseable payload.
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

describe('decodeJwtPayload', () => {
  it('decodes a standard payload', () => {
    const t = makeJwt({ sub: 'demo', exp: 1234567890 })
    expect(decodeJwtPayload(t)).toEqual({ sub: 'demo', exp: 1234567890 })
  })

  it('handles base64url -, _ and missing padding', () => {
    // Crafted to require URL-safe handling: includes characters that map to
    // -/_ in base64url and a payload length that needs padding.
    const payload = { sub: 'a?b>c<d', extra: 'with-/+_=chars', flag: true }
    const t = makeJwt(payload)
    // Sanity: token must contain url-safe chars (no '+' or '/').
    expect(t).not.toMatch(/[+/]/)
    expect(decodeJwtPayload(t)).toEqual(payload)
  })

  it('handles UTF-8 multibyte characters in claims', () => {
    const t = makeJwt({ name: '王小明', email: 'café@example.com' })
    expect(decodeJwtPayload(t)).toEqual({ name: '王小明', email: 'café@example.com' })
  })

  it('returns null for empty / non-string / wrong-shape input', () => {
    expect(decodeJwtPayload('')).toBeNull()
    expect(decodeJwtPayload('not.a.jwt.at.all')).toBeNull()
    expect(decodeJwtPayload('only-one-part')).toBeNull()
    expect(decodeJwtPayload(undefined as unknown as string)).toBeNull()
  })

  it('returns null when payload is not valid JSON', () => {
    const garbage = `${b64url({})}.${Buffer.from('not json {')
      .toString('base64')
      .replace(/=+$/, '')}.sig`
    expect(decodeJwtPayload(garbage)).toBeNull()
  })
})

describe('isJwtExpired', () => {
  it('returns false for an unexpired token', () => {
    const future = Math.floor(Date.now() / 1000) + 3600
    expect(isJwtExpired(makeJwt({ exp: future }))).toBe(false)
  })

  it('returns true for an expired token', () => {
    const past = Math.floor(Date.now() / 1000) - 3600
    expect(isJwtExpired(makeJwt({ exp: past }))).toBe(true)
  })

  it('honors clock-skew grace (treats just-expired as fresh)', () => {
    const justNow = Math.floor(Date.now() / 1000) - 10 // 10s ago
    expect(isJwtExpired(makeJwt({ exp: justNow }), 30)).toBe(false)
  })

  it('returns false when exp claim is missing (server is the authority)', () => {
    expect(isJwtExpired(makeJwt({ sub: 'demo' }))).toBe(false)
  })

  it('returns true for malformed token', () => {
    expect(isJwtExpired('garbage')).toBe(true)
    expect(isJwtExpired('')).toBe(true)
  })
})
