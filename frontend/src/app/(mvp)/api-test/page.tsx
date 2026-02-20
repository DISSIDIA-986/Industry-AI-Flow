'use client'

import { useState, useEffect } from 'react'
import { realApiService } from '@/lib/real-api-client'

export default function ApiTestPage() {
  const [health, setHealth] = useState<any>(null)
  const [loading, setLoading] = useState(true)
  const [testResults, setTestResults] = useState<Record<string, any>>({})
  const [testQuery, setTestQuery] = useState('测试工作流查询')

  useEffect(() => {
    loadHealth()
  }, [])

  const loadHealth = async () => {
    try {
      const healthData = await realApiService.checkHealth()
      setHealth(healthData)
    } catch (error) {
      console.error('健康检查失败:', error)
      const message = error instanceof Error ? error.message : String(error)
      setHealth({ status: 'error', message })
    } finally {
      setLoading(false)
    }
  }

  const runTest = async (endpoint: string, method: string = 'GET', data?: any) => {
    setTestResults(prev => ({ ...prev, [endpoint]: { loading: true } }))
    
    try {
      const url = `http://localhost:8001/api/v1${endpoint}`
      
      const options: RequestInit = {
        method,
        headers: { 'Content-Type': 'application/json' }
      }
      
      if (data) {
        options.body = JSON.stringify(data)
      }
      
      const response = await fetch(url, options)
      const result = await response.json()
      
      setTestResults(prev => ({ 
        ...prev, 
        [endpoint]: { 
          success: response.ok, 
          status: response.status,
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
    { endpoint: '/health', method: 'GET', name: '健康检查' },
    { endpoint: '/workflow/health', method: 'GET', name: '工作流健康' },
    { endpoint: '/query/health', method: 'GET', name: '查询健康' },
    { endpoint: '/cost-estimation/health', method: 'GET', name: '成本估算健康' },
    { endpoint: '/query/models', method: 'GET', name: '可用模型' },
    { 
      endpoint: '/workflow/query', 
      method: 'POST', 
      name: '工作流查询',
      data: { query: testQuery }
    },
    { 
      endpoint: '/unified/query', 
      method: 'POST', 
      name: '统一查询',
      data: { query: testQuery }
    }
  ]

  const runAllTests = async () => {
    for (const test of testEndpoints) {
      await runTest(test.endpoint, test.method, test.data)
      await new Promise(resolve => setTimeout(resolve, 500)) // 避免请求过快
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
        <h1 className="text-3xl font-bold text-gray-900 mb-6">API集成测试</h1>
        
        {/* 健康状态 */}
        <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6 mb-6">
          <h2 className="text-xl font-semibold text-gray-900 mb-4">后端API健康状态</h2>
          
          {loading ? (
            <div className="flex items-center space-x-2">
              <div className="w-4 h-4 border-2 border-blue-200 border-t-blue-600 rounded-full animate-spin"></div>
              <span className="text-gray-600">检查API状态...</span>
            </div>
          ) : health ? (
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <div>
                  <div className="font-medium">API状态</div>
                  <div className="text-sm text-gray-600">后端FastAPI服务</div>
                </div>
                <span className={`px-3 py-1 rounded-full text-sm font-medium ${getStatusColor(health.status)}`}>
                  {health.status === 'ok' ? '正常运行' : '异常'}
                </span>
              </div>
              
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div className="p-4 bg-gray-50 rounded-lg">
                  <div className="text-sm font-medium text-gray-500">内存使用</div>
                  <div className="text-lg font-semibold text-gray-900">{health.memory_usage_mb?.toFixed(1)} MB</div>
                </div>
                
                <div className="p-4 bg-gray-50 rounded-lg">
                  <div className="text-sm font-medium text-gray-500">版本</div>
                  <div className="text-lg font-semibold text-gray-900">{health.version || '未知'}</div>
                </div>
                
                <div className="p-4 bg-gray-50 rounded-lg">
                  <div className="text-sm font-medium text-gray-500">租户</div>
                  <div className="text-lg font-semibold text-gray-900">{health.tenant || 'public'}</div>
                </div>
              </div>
              
              <div className="text-sm text-gray-500">
                后端地址: http://localhost:8001
              </div>
            </div>
          ) : (
            <div className="text-red-600">无法连接到后端API</div>
          )}
        </div>

        {/* API端点测试 */}
        <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6 mb-6">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-xl font-semibold text-gray-900">API端点测试</h2>
            <button
              onClick={runAllTests}
              className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
            >
              运行所有测试
            </button>
          </div>

          <div className="mb-4">
            <label className="block text-sm font-medium text-gray-700 mb-2">
              测试查询内容
            </label>
            <input
              type="text"
              value={testQuery}
              onChange={(e) => setTestQuery(e.target.value)}
              className="w-full px-4 py-2 border border-gray-300 rounded-lg"
              placeholder="输入测试查询内容"
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
                      测试
                    </button>
                    {testResults[test.endpoint] && (
                      <span className={`px-2 py-1 rounded text-xs ${
                        testResults[test.endpoint].success 
                          ? 'bg-green-100 text-green-800' 
                          : 'bg-red-100 text-red-800'
                      }`}>
                        {testResults[test.endpoint].success ? '成功' : '失败'}
                      </span>
                    )}
                  </div>
                </div>
                
                {testResults[test.endpoint] && (
                  <div className="mt-3 pt-3 border-t border-gray-200">
                    <div className="text-sm text-gray-500 mb-1">
                      状态码: {testResults[test.endpoint].status || 'N/A'} | 
                      时间: {new Date(testResults[test.endpoint].timestamp).toLocaleTimeString()}
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

        {/* 使用说明 */}
        <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
          <h2 className="text-xl font-semibold text-gray-900 mb-4">API集成说明</h2>
          
          <div className="space-y-4">
            <div>
              <h3 className="font-medium text-gray-900 mb-2">混合API策略</h3>
              <p className="text-gray-600">
                前端采用混合API策略：优先使用真实后端API，如果连接失败则自动回退到模拟API。
                这确保了开发和生产环境的无缝切换。
              </p>
            </div>
            
            <div>
              <h3 className="font-medium text-gray-900 mb-2">核心API端点</h3>
              <ul className="list-disc pl-5 text-gray-600 space-y-1">
                <li><code>/api/v1/workflow/query</code> - 工作流查询（AI对话）</li>
                <li><code>/api/v1/unified/query</code> - 统一查询（RAG检索）</li>
                <li><code>/api/v1/documents/upload</code> - 文档上传</li>
                <li><code>/api/v1/cost-estimation/predict</code> - 成本估算</li>
                <li><code>/api/v1/query/models</code> - 可用AI模型列表</li>
              </ul>
            </div>
            
            <div>
              <h3 className="font-medium text-gray-900 mb-2">开发建议</h3>
              <ol className="list-decimal pl-5 text-gray-600 space-y-1">
                <li>始终使用混合API客户端，不要直接调用fetch</li>
                <li>为所有API调用添加适当的错误处理</li>
                <li>在UI中显示API连接状态</li>
                <li>使用模拟数据进行开发和测试</li>
                <li>在生产环境中切换到真实API</li>
              </ol>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
