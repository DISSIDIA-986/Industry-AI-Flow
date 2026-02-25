'use client'

import { useState, useEffect } from 'react'
import { api } from '@/lib/api-client'
import { realApiService } from '@/lib/real-api-client'

export default function ApiTestPage() {
  const [health, setHealth] = useState<any>(null)
  const [loading, setLoading] = useState(true)
  const [testResults, setTestResults] = useState<Record<string, any>>({})
  const [testQuery, setTestQuery] = useState('Test workflow query')

  useEffect(() => {
    loadHealth()
  }, [])

  const loadHealth = async () => {
    try {
      const healthData = await realApiService.checkHealth()
      setHealth(healthData)
    } catch (error) {
      console.error('Health check failed:', error)
      const message = error instanceof Error ? error.message : String(error)
      setHealth({ status: 'error', message })
    } finally {
      setLoading(false)
    }
  }

  const runTest = async (endpoint: string, method: string = 'GET', data?: any) => {
    setTestResults(prev => ({ ...prev, [endpoint]: { loading: true } }))
    
    try {
      const result =
        method === 'POST'
          ? await api.post<any>(endpoint, data)
          : await api.get<any>(endpoint)
      
      setTestResults(prev => ({ 
        ...prev, 
        [endpoint]: { 
          success: true,
          status: 200,
          data: result,
          timestamp: new Date().toISOString()
        }
      }))
    } catch (error) {
      const message = error instanceof Error ? error.message : String(error)
      setTestResults(prev => ({ 
        ...prev, 
        [endpoint]: { 
          success: false, 
          error: message,
          timestamp: new Date().toISOString()
        }
      }))
    }
  }

  const testEndpoints = [
    { endpoint: '/health', method: 'GET', name: 'health check' },
    { endpoint: '/workflow/health', method: 'GET', name: 'Workflow health' },
    { endpoint: '/query/health', method: 'GET', name: 'Check health' },
    { endpoint: '/cost-estimation/health', method: 'GET', name: 'cost estimate health' },
    { endpoint: '/query/models', method: 'GET', name: 'Available models' },
    { 
      endpoint: '/workflow/query', 
      method: 'POST', 
      name: 'Workflow query',
      data: { query: testQuery }
    },
    { 
      endpoint: '/unified/query', 
      method: 'POST', 
      name: 'Unified query',
      data: { query: testQuery }
    }
  ]

  const runAllTests = async () => {
    for (const test of testEndpoints) {
      await runTest(test.endpoint, test.method, test.data)
      await new Promise(resolve => setTimeout(resolve, 500)) // Avoid requesting too quickly
    }
  }

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'ok': return 'bg-green-100 text-green-800'
      case 'error': return 'bg-red-100 text-red-800'
      default: return 'bg-yellow-100 text-yellow-800'
    }
  }

  return (
    <div className="min-h-screen bg-gray-50 p-6">
      <div className="max-w-6xl mx-auto">
        <h1 className="text-3xl font-bold text-gray-900 mb-6">APIIntegration testing</h1>
        
        {/* health status */}
        <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6 mb-6">
          <h2 className="text-xl font-semibold text-gray-900 mb-4">rear endAPIhealth status</h2>
          
          {loading ? (
            <div className="flex items-center space-x-2">
              <div className="w-4 h-4 border-2 border-blue-200 border-t-blue-600 rounded-full animate-spin"></div>
              <span className="text-gray-600">examineAPIstate...</span>
            </div>
          ) : health ? (
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <div>
                  <div className="font-medium">APIstate</div>
                  <div className="text-sm text-gray-600">rear endFastAPIServe</div>
                </div>
                <span className={`px-3 py-1 rounded-full text-sm font-medium ${getStatusColor(health.status)}`}>
                  {health.status === 'ok' ? 'normal operation' : 'abnormal'}
                </span>
              </div>
              
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div className="p-4 bg-gray-50 rounded-lg">
                  <div className="text-sm font-medium text-gray-500">memory usage</div>
                  <div className="text-lg font-semibold text-gray-900">{health.memory_usage_mb?.toFixed(1)} MB</div>
                </div>
                
                <div className="p-4 bg-gray-50 rounded-lg">
                  <div className="text-sm font-medium text-gray-500">Version</div>
                  <div className="text-lg font-semibold text-gray-900">{health.version || 'unknown'}</div>
                </div>
                
                <div className="p-4 bg-gray-50 rounded-lg">
                  <div className="text-sm font-medium text-gray-500">tenant</div>
                  <div className="text-lg font-semibold text-gray-900">{health.tenant || 'public'}</div>
                </div>
              </div>
              
              <div className="text-sm text-gray-500">
                Backend address: /api/backend/api/v1 (Same origin proxy)
              </div>
            </div>
          ) : (
            <div className="text-red-600">Unable to connect to backendAPI</div>
          )}
        </div>

        {/* APIEndpoint testing */}
        <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6 mb-6">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-xl font-semibold text-gray-900">APIEndpoint testing</h2>
            <button
              onClick={runAllTests}
              className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
            >
              Run all tests
            </button>
          </div>

          <div className="mb-4">
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Test query content
            </label>
            <input
              type="text"
              value={testQuery}
              onChange={(e) => setTestQuery(e.target.value)}
              className="w-full px-4 py-2 border border-gray-300 rounded-lg"
              placeholder="Enter test query content"
            />
          </div>

          <div className="space-y-4">
            {testEndpoints.map((test) => (
              <div key={test.endpoint} className="border border-gray-200 rounded-lg p-4">
                <div className="flex items-center justify-between mb-2">
                  <div>
                    <div className="font-medium">{test.name}</div>
                    <div className="text-sm text-gray-500">
                      {test.method} {test.endpoint}
                    </div>
                  </div>
                  <div className="flex items-center space-x-2">
                    <button
                      onClick={() => runTest(test.endpoint, test.method, test.data)}
                      className="px-3 py-1 bg-gray-100 text-gray-700 rounded hover:bg-gray-200 text-sm"
                    >
                      test
                    </button>
                    {testResults[test.endpoint] && (
                      <span className={`px-2 py-1 rounded text-xs ${
                        testResults[test.endpoint].success 
                          ? 'bg-green-100 text-green-800' 
                          : 'bg-red-100 text-red-800'
                      }`}>
                        {testResults[test.endpoint].success ? 'success' : 'fail'}
                      </span>
                    )}
                  </div>
                </div>
                
                {testResults[test.endpoint] && (
                  <div className="mt-3 pt-3 border-t border-gray-200">
                    <div className="text-sm text-gray-500 mb-1">
                      Status code: {testResults[test.endpoint].status || 'N/A'} | 
                      time: {new Date(testResults[test.endpoint].timestamp).toLocaleTimeString()}
                    </div>
                    <pre className="text-xs bg-gray-50 p-3 rounded overflow-auto max-h-40">
                      {JSON.stringify(testResults[test.endpoint].data || testResults[test.endpoint].error, null, 2)}
                    </pre>
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>

        {/* Instructions for use */}
        <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
          <h2 className="text-xl font-semibold text-gray-900 mb-4">APIIntegration instructions</h2>
          
          <div className="space-y-4">
            <div>
              <h3 className="font-medium text-gray-900 mb-2">mixAPIStrategy</h3>
              <p className="text-gray-600">
                The frontend accesses the real backend through the same-origin proxy by default. Only when
                <code className="mx-1">NEXT_PUBLIC_ALLOW_HYBRID_MOCK_FALLBACK=true</code>
                is explicitly enabled will it fall back to the simulated API.
              </p>
            </div>
            
            <div>
              <h3 className="font-medium text-gray-900 mb-2">coreAPIendpoint</h3>
              <ul className="list-disc pl-5 text-gray-600 space-y-1">
                <li><code>/api/v1/workflow/query</code> - Workflow query (AIdialogue)</li>
                <li><code>/api/v1/unified/query</code> - Unified query (RAGSearch)</li>
                <li><code>/api/v1/documents/upload</code> - Document upload</li>
                <li><code>/api/v1/cost-estimation/predict</code> - cost estimate</li>
                <li><code>/api/v1/query/models</code> - AvailableAIModel list</li>
              </ul>
            </div>
            
            <div>
              <h3 className="font-medium text-gray-900 mb-2">Development suggestions</h3>
              <ol className="list-decimal pl-5 text-gray-600 space-y-1">
                <li>Always use mixAPIClient, do not call directlyfetch</li>
                <li>for allAPICall to add appropriate error handling</li>
                <li>existUIShown inAPIconnection status</li>
                <li>Use simulated data for development and testing</li>
                <li>Switch to real in production environmentAPI</li>
              </ol>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
