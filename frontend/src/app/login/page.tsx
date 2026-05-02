'use client'

import { useState, Suspense } from 'react'
import { useSearchParams } from 'next/navigation'
import { useAuth } from '@/contexts/AuthContext'

function LoginPageInner() {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const { login, error: authError } = useAuth()
  const searchParams = useSearchParams()
  const reason = searchParams?.get('reason') ?? null

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)
    setError('')

    try {
      await login(email, password)
      // AuthContext.login handles the post-login redirect.
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Login failed')
    } finally {
      setLoading(false)
    }
  }

  // Show errors in authentication context
  const displayError = error || authError

  // Honest banner: we know the prior session is invalid, but we don't
  // know whether it was clock-expiry, server restart, secret rotation,
  // or a backend bug. So the message is intentionally generic.
  const sessionNotice =
    reason === 'expired' ? 'Please log in again to continue.' : null

  return (
    <div className="min-h-screen bg-gray-50 flex items-center justify-center p-4">
      <div className="max-w-md w-full bg-white rounded-2xl shadow-xl p-8">
        <div className="text-center mb-8">
          <h1 className="text-3xl font-bold text-gray-900 mb-2">
            Industry AI Flow
          </h1>
          <p className="text-gray-600">Enterprise Level AI Workflow Platform</p>
        </div>

        {sessionNotice && (
          <div
            data-testid="session-expired-banner"
            className="mb-6 bg-amber-50 border border-amber-200 text-amber-800 px-4 py-3 rounded-lg text-sm"
          >
            {sessionNotice}
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-6">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Email address
            </label>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition"
              placeholder="your@email.com"
              required
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Password
            </label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition"
              placeholder="••••••••"
              required
            />
          </div>

          {displayError && (
            <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg">
              {displayError}
            </div>
          )}

          <button
            type="submit"
            disabled={loading}
            className="w-full bg-blue-600 hover:bg-blue-700 text-white font-medium py-3 px-4 rounded-lg transition disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {loading ? 'Logging in...' : 'Log in'}
          </button>
        </form>

      </div>
    </div>
  )
}

export default function LoginPage() {
  // useSearchParams must be wrapped in Suspense for Next.js App Router CSR bailout.
  return (
    <Suspense fallback={null}>
      <LoginPageInner />
    </Suspense>
  )
}
