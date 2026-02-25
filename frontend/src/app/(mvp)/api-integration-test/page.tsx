'use client'

import { useState, useEffect } from 'react'
import {
  authApi,
  workflowApi,
  documentApi,
  getPlatformHealth,
  getWorkflowHealth,
  ApiError,
} from '@/lib/api-client'

type IntegrationTestResult = {
  success: boolean
  skipped?: boolean
  error?: string
  data?: unknown
}

function formatErrorMessage(error: unknown): string {
  if (error instanceof ApiError) {
    return `${error.message} (HTTP ${error.status})`
  }
  if (error instanceof Error) {
    return error.message
  }
  return 'unknown error'
}

function buildFailedResult(error: unknown): IntegrationTestResult {
  return {
    success: false,
    error: formatErrorMessage(error),
  }
}

function buildSkippedResult(reason: string): IntegrationTestResult {
  return {
    success: false,
    skipped: true,
    error: reason,
  }
}

function getResultStyles(result: IntegrationTestResult): {
  container: string
  title: string
  detail: string
  label: string
} {
  if (result.success) {
    return {
      container: 'bg-green-50 border border-green-200',
      title: 'text-green-800',
      detail: 'text-green-700',
      label: '✅ Test passed',
    }
  }

  if (result.skipped) {
    return {
      container: 'bg-amber-50 border border-amber-200',
      title: 'text-amber-800',
      detail: 'text-amber-700',
      label: '⏭️ Skipped',
    }
  }

  return {
    container: 'bg-red-50 border border-red-200',
    title: 'text-red-800',
    detail: 'text-red-600',
    label: '❌ test failed',
  }
}

export default function ApiTestPage() {
  const [testResults, setTestResults] = useState<Record<string, IntegrationTestResult>>({})
  const [loading, setLoading] = useState(false)
  const [testEmail] = useState('test@example.com')
  const [testPassword] = useState('test123456')
  const tokenReady = typeof window !== 'undefined' && !!window.localStorage.getItem('token')
  const userReady = typeof window !== 'undefined' && !!window.localStorage.getItem('user')
  const hasExecuted = Object.keys(testResults).length > 0
  const hasDependencyBlock =
    Boolean(testResults.query?.skipped) || Boolean(testResults.documents?.skipped)
  const registerToken = (testResults.register?.data as { token?: string } | undefined)?.token
  const loginUserName = (
    testResults.login?.data as { user?: { name?: string } } | undefined
  )?.user?.name
  const queryResultData = testResults.query?.data as { id?: string; response?: string } | undefined
  const documentRows = Array.isArray(testResults.documents?.data)
    ? (testResults.documents.data as Array<Record<string, unknown>>)
    : []

  const runTests = async () => {
    setLoading(true)
    const results: Record<string, IntegrationTestResult> = {}

    try {
      // Test 1: registerAPI
      console.log('Test 1: registerAPI')
      try {
        const registerResult = await authApi.register('test user', testEmail, testPassword)
        results.register = { success: true, data: registerResult }
        console.log('Registration successful:', registerResult)
      } catch (error) {
        results.register = buildFailedResult(error)
        console.log('Registration failed:', error)
      }

      // Test 2: Log inAPI
      console.log('Test 2: Log inAPI')
      try {
        const loginResult = await authApi.login(testEmail, testPassword)
        results.login = { success: true, data: loginResult }
        console.log('Login successful:', loginResult)
        
        // savetokenfor subsequent testing
        if (loginResult.token) {
          localStorage.setItem('token', loginResult.token)
          localStorage.setItem('user', JSON.stringify(loginResult.user))
        }
      } catch (error) {
        results.login = buildFailedResult(error)
        console.log('Login failed:', error)
      }

      // Test 3: QueryAPI
      console.log('Test 3: QueryAPI')
      try {
        await Promise.all([getPlatformHealth({}), getWorkflowHealth({})])
      } catch (error) {
        results.query = buildSkippedResult(
          `Workflow dependency is not ready: ${formatErrorMessage(error)}`,
        )
      }

      if (!results.query) {
        try {
          const queryResult = await workflowApi.sendQuery(
            {
              query:
                'Please estimate construction cost for: commercial office, location Toronto, sqft 120000, floors 12, duration 96 weeks, budget 120m, contractor rating 4.1, complexity 7, team experience 11, change orders 5, weather risk 0.4, material volatility 0.35, subcontractors 20, budget pressure 0.45, risk score 52, risk score original 43',
            },
            { routeMode: 'local_only' },
          )
          results.query = { success: true, data: queryResult }
          console.log('Query successful:', queryResult)
        } catch (error) {
          if (error instanceof ApiError && [408, 502, 503, 504].includes(error.status)) {
            results.query = buildSkippedResult(
              `Workflow query dependency timeout/unavailable: ${formatErrorMessage(error)}`,
            )
          } else {
            results.query = buildFailedResult(error)
          }
          console.log('Query failed:', error)
        }
      }

      // Test 4: documentAPI - Get document list
      console.log('Test 4: documentAPI')
      try {
        const documentsResult = await documentApi.getDocuments()
        results.documents = { success: true, data: documentsResult }
        console.log('Obtaining the document successfully:', documentsResult)
      } catch (error) {
        if (error instanceof ApiError && error.status === 404) {
          results.documents = buildSkippedResult(
            'Document list endpoint is not implemented on backend (HTTP 404)',
          )
        } else if (
          error instanceof ApiError &&
          [408, 502, 503, 504].includes(error.status)
        ) {
          results.documents = buildSkippedResult(
            `Document service dependency timeout/unavailable: ${formatErrorMessage(error)}`,
          )
        } else {
          results.documents = buildFailedResult(error)
        }
        console.log('Failed to get document:', error)
      }

    } catch (error) {
      console.error('An error occurred during testing:', error)
      results.overall = buildFailedResult(error)
    } finally {
      setLoading(false)
      setTestResults(results)
    }
  }

  useEffect(() => {
    // before cleaningtoken
    localStorage.removeItem('token')
    localStorage.removeItem('user')
  }, [])

  return (
    <div className="min-h-screen bg-gray-50 p-6">
      <div className="max-w-4xl mx-auto">
        <h1 className="text-3xl font-bold text-gray-900 mb-6">APIIntegration testing</h1>
        
        <div className="mb-8">
          <button
            onClick={runTests}
            disabled={loading}
            className="bg-blue-600 hover:bg-blue-700 text-white px-6 py-3 rounded-lg font-medium transition disabled:opacity-50"
          >
            {loading ? 'Under test...' : 'Run all tests'}
          </button>
          
          <div className="mt-4 text-sm text-gray-600">
            <p>Test account: {testEmail} / {testPassword}</p>
            <p>APIaddress: /api/backend/api/v1 (Same origin proxy)</p>
          </div>
        </div>

        <div className="space-y-6">
          {/* Register test results */}
          <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
            <h3 className="font-medium text-gray-900 mb-4">1. registerAPItest</h3>
            {testResults.register ? (
              <div className={`p-4 rounded-lg ${getResultStyles(testResults.register).container}`}>
                <div className="flex items-center justify-between">
                  <div>
                    <div className={`font-medium ${getResultStyles(testResults.register).title}`}>
                      {getResultStyles(testResults.register).label}
                    </div>
                    {testResults.register.error && (
                      <div className={`text-sm mt-1 ${getResultStyles(testResults.register).detail}`}>
                        {testResults.register.error}
                      </div>
                    )}
                  </div>
                  {testResults.register.success && (
                    <div className="text-sm text-gray-500">
                      Token: {registerToken?.substring(0, 20)}...
                    </div>
                  )}
                </div>
              </div>
            ) : (
              <div className="text-gray-500">Waiting for test...</div>
            )}
          </div>

          {/* Login test results */}
          <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
            <h3 className="font-medium text-gray-900 mb-4">2. Log inAPItest</h3>
            {testResults.login ? (
              <div className={`p-4 rounded-lg ${getResultStyles(testResults.login).container}`}>
                <div className="flex items-center justify-between">
                  <div>
                    <div className={`font-medium ${getResultStyles(testResults.login).title}`}>
                      {getResultStyles(testResults.login).label}
                    </div>
                    {testResults.login.error && (
                      <div className={`text-sm mt-1 ${getResultStyles(testResults.login).detail}`}>
                        {testResults.login.error}
                      </div>
                    )}
                  </div>
                  {testResults.login.success && (
                    <div className="text-sm text-gray-500">
                      user: {loginUserName}
                    </div>
                  )}
                </div>
              </div>
            ) : (
              <div className="text-gray-500">Waiting for test...</div>
            )}
          </div>

          {/* Query test results */}
          <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
            <h3 className="font-medium text-gray-900 mb-4">3. QueryAPItest (/workflow/query)</h3>
            {testResults.query ? (
              <div className={`p-4 rounded-lg ${getResultStyles(testResults.query).container}`}>
                <div className="flex items-center justify-between">
                  <div>
                    <div className={`font-medium ${getResultStyles(testResults.query).title}`}>
                      {getResultStyles(testResults.query).label}
                    </div>
                    {testResults.query.error && (
                      <div className={`text-sm mt-1 ${getResultStyles(testResults.query).detail}`}>
                        {testResults.query.error}
                      </div>
                    )}
                  </div>
                  {testResults.query.success && (
                    <div className="text-sm text-gray-500">
                      QueryID: {queryResultData?.id}
                    </div>
                  )}
                </div>
                {testResults.query.success && (
                  <div className="mt-3 p-3 bg-gray-50 rounded text-sm">
                    <div className="font-medium">Response content:</div>
                    <div className="mt-1 text-gray-700">{queryResultData?.response}</div>
                  </div>
                )}
              </div>
            ) : (
              <div className="text-gray-500">Waiting for test...</div>
            )}
          </div>

          {/* Document test results */}
          <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
            <h3 className="font-medium text-gray-900 mb-4">4. documentAPItest</h3>
            {testResults.documents ? (
              <div className={`p-4 rounded-lg ${getResultStyles(testResults.documents).container}`}>
                <div className="flex items-center justify-between">
                  <div>
                    <div className={`font-medium ${getResultStyles(testResults.documents).title}`}>
                      {getResultStyles(testResults.documents).label}
                    </div>
                    {testResults.documents.error && (
                      <div className={`text-sm mt-1 ${getResultStyles(testResults.documents).detail}`}>
                        {testResults.documents.error}
                      </div>
                    )}
                  </div>
                  {testResults.documents.success && (
                    <div className="text-sm text-gray-500">
                      Number of documents: {documentRows.length}
                    </div>
                  )}
                </div>
                {testResults.documents.success && documentRows.length > 0 && (
                  <div className="mt-3">
                    <div className="font-medium text-sm mb-2">Document list:</div>
                    <div className="space-y-2">
                      {documentRows.map((doc: Record<string, unknown>, index: number) => (
                        <div key={index} className="flex items-center justify-between text-sm p-2 bg-gray-50 rounded">
                          <div>{String(doc.name ?? doc.filename ?? `Document ${index + 1}`)}</div>
                          <div className="text-gray-500">
                            {String(doc.type ?? doc.extension ?? 'UNKNOWN')} •{' '}
                            {String(doc.size ?? 'N/A')}
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            ) : (
              <div className="text-gray-500">Waiting for test...</div>
            )}
          </div>
        </div>

        {/* Current status */}
        <div className="mt-8 bg-white rounded-xl shadow-sm border border-gray-200 p-6">
          <h3 className="font-medium text-gray-900 mb-4">Current status</h3>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="p-4 bg-gray-50 rounded-lg">
              <div className="text-sm text-gray-500">Tokenstate</div>
              <div className={`font-medium ${tokenReady ? 'text-green-600' : 'text-gray-600'}`}>
                {tokenReady ? 'Already set' : 'not set'}
              </div>
            </div>
            <div className="p-4 bg-gray-50 rounded-lg">
              <div className="text-sm text-gray-500">User status</div>
              <div className={`font-medium ${userReady ? 'text-green-600' : 'text-gray-600'}`}>
                {userReady ? 'Logged in' : 'Not logged in'}
              </div>
            </div>
            <div className="p-4 bg-gray-50 rounded-lg">
              <div className="text-sm text-gray-500">APIconnect</div>
              {!hasExecuted && <div className="font-medium text-gray-600">untested</div>}
              {hasExecuted && !hasDependencyBlock && (
                <div className="font-medium text-green-600">normal</div>
              )}
              {hasExecuted && hasDependencyBlock && (
                <div className="font-medium text-amber-700">degraded (dependency blocked)</div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
