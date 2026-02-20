'use client'

import { useState, useEffect } from 'react'
import { authApi, queryApi, documentApi, ApiError } from '@/lib/api-client'

export default function ApiTestPage() {
  const [testResults, setTestResults] = useState<Record<string, any>>({})
  const [loading, setLoading] = useState(false)
  const [testEmail] = useState('test@example.com')
  const [testPassword] = useState('test123456')
  const tokenReady = typeof window !== 'undefined' && !!window.localStorage.getItem('token')
  const userReady = typeof window !== 'undefined' && !!window.localStorage.getItem('user')

  const runTests = async () => {
    setLoading(true)
    const results: Record<string, any> = {}

    try {
      // Test 1: registerAPI
      console.log('Test 1: registerAPI')
      try {
        const registerResult = await authApi.register('test user', testEmail, testPassword)
        results.register = { success: true, data: registerResult }
        console.log('Registration successful:', registerResult)
      } catch (error) {
        results.register = { 
          success: false, 
          error: error instanceof ApiError ? error.message : 'unknown error' 
        }
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
        results.login = { 
          success: false, 
          error: error instanceof ApiError ? error.message : 'unknown error' 
        }
        console.log('Login failed:', error)
      }

      // Test 3: QueryAPI
      console.log('Test 3: QueryAPI')
      try {
        const queryResult = await queryApi.sendQuery('Test Query: Construction Cost Estimate')
        results.query = { success: true, data: queryResult }
        console.log('Query successful:', queryResult)
      } catch (error) {
        results.query = { 
          success: false, 
          error: error instanceof ApiError ? error.message : 'unknown error' 
        }
        console.log('Query failed:', error)
      }

      // Test 4: documentAPI - Get document list
      console.log('Test 4: documentAPI')
      try {
        const documentsResult = await documentApi.getDocuments()
        results.documents = { success: true, data: documentsResult }
        console.log('Obtaining the document successfully:', documentsResult)
      } catch (error) {
        results.documents = { 
          success: false, 
          error: error instanceof ApiError ? error.message : 'unknown error' 
        }
        console.log('Failed to get document:', error)
      }

    } catch (error) {
      console.error('An error occurred during testing:', error)
      results.overall = { success: false, error: 'Test process failed' }
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
              <div className={`p-4 rounded-lg ${testResults.register.success ? 'bg-green-50 border border-green-200' : 'bg-red-50 border border-red-200'}`}>
                <div className="flex items-center justify-between">
                  <div>
                    <div className={`font-medium ${testResults.register.success ? 'text-green-800' : 'text-red-800'}`}>
                      {testResults.register.success ? '✅ Test passed' : '❌ test failed'}
                    </div>
                    {testResults.register.error && (
                      <div className="text-sm text-red-600 mt-1">{testResults.register.error}</div>
                    )}
                  </div>
                  {testResults.register.success && (
                    <div className="text-sm text-gray-500">
                      Token: {testResults.register.data?.token?.substring(0, 20)}...
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
              <div className={`p-4 rounded-lg ${testResults.login.success ? 'bg-green-50 border border-green-200' : 'bg-red-50 border border-red-200'}`}>
                <div className="flex items-center justify-between">
                  <div>
                    <div className={`font-medium ${testResults.login.success ? 'text-green-800' : 'text-red-800'}`}>
                      {testResults.login.success ? '✅ Test passed' : '❌ test failed'}
                    </div>
                    {testResults.login.error && (
                      <div className="text-sm text-red-600 mt-1">{testResults.login.error}</div>
                    )}
                  </div>
                  {testResults.login.success && (
                    <div className="text-sm text-gray-500">
                      user: {testResults.login.data?.user?.name}
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
            <h3 className="font-medium text-gray-900 mb-4">3. QueryAPItest</h3>
            {testResults.query ? (
              <div className={`p-4 rounded-lg ${testResults.query.success ? 'bg-green-50 border border-green-200' : 'bg-red-50 border border-red-200'}`}>
                <div className="flex items-center justify-between">
                  <div>
                    <div className={`font-medium ${testResults.query.success ? 'text-green-800' : 'text-red-800'}`}>
                      {testResults.query.success ? '✅ Test passed' : '❌ test failed'}
                    </div>
                    {testResults.query.error && (
                      <div className="text-sm text-red-600 mt-1">{testResults.query.error}</div>
                    )}
                  </div>
                  {testResults.query.success && (
                    <div className="text-sm text-gray-500">
                      QueryID: {testResults.query.data?.id}
                    </div>
                  )}
                </div>
                {testResults.query.success && (
                  <div className="mt-3 p-3 bg-gray-50 rounded text-sm">
                    <div className="font-medium">Response content:</div>
                    <div className="mt-1 text-gray-700">{testResults.query.data?.response}</div>
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
              <div className={`p-4 rounded-lg ${testResults.documents.success ? 'bg-green-50 border border-green-200' : 'bg-red-50 border border-red-200'}`}>
                <div className="flex items-center justify-between">
                  <div>
                    <div className={`font-medium ${testResults.documents.success ? 'text-green-800' : 'text-red-800'}`}>
                      {testResults.documents.success ? '✅ Test passed' : '❌ test failed'}
                    </div>
                    {testResults.documents.error && (
                      <div className="text-sm text-red-600 mt-1">{testResults.documents.error}</div>
                    )}
                  </div>
                  {testResults.documents.success && (
                    <div className="text-sm text-gray-500">
                      Number of documents: {testResults.documents.data?.length || 0}
                    </div>
                  )}
                </div>
                {testResults.documents.success && testResults.documents.data && (
                  <div className="mt-3">
                    <div className="font-medium text-sm mb-2">Document list:</div>
                    <div className="space-y-2">
                      {testResults.documents.data.map((doc: any, index: number) => (
                        <div key={index} className="flex items-center justify-between text-sm p-2 bg-gray-50 rounded">
                          <div>{doc.name}</div>
                          <div className="text-gray-500">{doc.type} • {doc.size}</div>
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
              <div className="font-medium text-green-600">normal</div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
