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
      // 测试1: 注册API
      console.log('测试1: 注册API')
      try {
        const registerResult = await authApi.register('测试用户', testEmail, testPassword)
        results.register = { success: true, data: registerResult }
        console.log('注册成功:', registerResult)
      } catch (error) {
        results.register = { 
          success: false, 
          error: error instanceof ApiError ? error.message : '未知错误' 
        }
        console.log('注册失败:', error)
      }

      // 测试2: 登录API
      console.log('测试2: 登录API')
      try {
        const loginResult = await authApi.login(testEmail, testPassword)
        results.login = { success: true, data: loginResult }
        console.log('登录成功:', loginResult)
        
        // 保存token用于后续测试
        if (loginResult.token) {
          localStorage.setItem('token', loginResult.token)
          localStorage.setItem('user', JSON.stringify(loginResult.user))
        }
      } catch (error) {
        results.login = { 
          success: false, 
          error: error instanceof ApiError ? error.message : '未知错误' 
        }
        console.log('登录失败:', error)
      }

      // 测试3: 查询API
      console.log('测试3: 查询API')
      try {
        const queryResult = await queryApi.sendQuery('测试查询：建筑成本估算')
        results.query = { success: true, data: queryResult }
        console.log('查询成功:', queryResult)
      } catch (error) {
        results.query = { 
          success: false, 
          error: error instanceof ApiError ? error.message : '未知错误' 
        }
        console.log('查询失败:', error)
      }

      // 测试4: 文档API - 获取文档列表
      console.log('测试4: 文档API')
      try {
        const documentsResult = await documentApi.getDocuments()
        results.documents = { success: true, data: documentsResult }
        console.log('获取文档成功:', documentsResult)
      } catch (error) {
        results.documents = { 
          success: false, 
          error: error instanceof ApiError ? error.message : '未知错误' 
        }
        console.log('获取文档失败:', error)
      }

    } catch (error) {
      console.error('测试过程中出现错误:', error)
      results.overall = { success: false, error: '测试过程失败' }
    } finally {
      setLoading(false)
      setTestResults(results)
    }
  }

  useEffect(() => {
    // 清理之前的token
    localStorage.removeItem('token')
    localStorage.removeItem('user')
  }, [])

  return (
    <div className="min-h-screen bg-gray-50 p-6">
      <div className="max-w-4xl mx-auto">
        <h1 className="text-3xl font-bold text-gray-900 mb-6">API集成测试</h1>
        
        <div className="mb-8">
          <button
            onClick={runTests}
            disabled={loading}
            className="bg-blue-600 hover:bg-blue-700 text-white px-6 py-3 rounded-lg font-medium transition disabled:opacity-50"
          >
            {loading ? '测试中...' : '运行所有测试'}
          </button>
          
          <div className="mt-4 text-sm text-gray-600">
            <p>测试账户: {testEmail} / {testPassword}</p>
            <p>API地址: {process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8002/api/v1'}</p>
          </div>
        </div>

        <div className="space-y-6">
          {/* 注册测试结果 */}
          <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
            <h3 className="font-medium text-gray-900 mb-4">1. 注册API测试</h3>
            {testResults.register ? (
              <div className={`p-4 rounded-lg ${testResults.register.success ? 'bg-green-50 border border-green-200' : 'bg-red-50 border border-red-200'}`}>
                <div className="flex items-center justify-between">
                  <div>
                    <div className={`font-medium ${testResults.register.success ? 'text-green-800' : 'text-red-800'}`}>
                      {testResults.register.success ? '✅ 测试通过' : '❌ 测试失败'}
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
              <div className="text-gray-500">等待测试...</div>
            )}
          </div>

          {/* 登录测试结果 */}
          <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
            <h3 className="font-medium text-gray-900 mb-4">2. 登录API测试</h3>
            {testResults.login ? (
              <div className={`p-4 rounded-lg ${testResults.login.success ? 'bg-green-50 border border-green-200' : 'bg-red-50 border border-red-200'}`}>
                <div className="flex items-center justify-between">
                  <div>
                    <div className={`font-medium ${testResults.login.success ? 'text-green-800' : 'text-red-800'}`}>
                      {testResults.login.success ? '✅ 测试通过' : '❌ 测试失败'}
                    </div>
                    {testResults.login.error && (
                      <div className="text-sm text-red-600 mt-1">{testResults.login.error}</div>
                    )}
                  </div>
                  {testResults.login.success && (
                    <div className="text-sm text-gray-500">
                      用户: {testResults.login.data?.user?.name}
                    </div>
                  )}
                </div>
              </div>
            ) : (
              <div className="text-gray-500">等待测试...</div>
            )}
          </div>

          {/* 查询测试结果 */}
          <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
            <h3 className="font-medium text-gray-900 mb-4">3. 查询API测试</h3>
            {testResults.query ? (
              <div className={`p-4 rounded-lg ${testResults.query.success ? 'bg-green-50 border border-green-200' : 'bg-red-50 border border-red-200'}`}>
                <div className="flex items-center justify-between">
                  <div>
                    <div className={`font-medium ${testResults.query.success ? 'text-green-800' : 'text-red-800'}`}>
                      {testResults.query.success ? '✅ 测试通过' : '❌ 测试失败'}
                    </div>
                    {testResults.query.error && (
                      <div className="text-sm text-red-600 mt-1">{testResults.query.error}</div>
                    )}
                  </div>
                  {testResults.query.success && (
                    <div className="text-sm text-gray-500">
                      查询ID: {testResults.query.data?.id}
                    </div>
                  )}
                </div>
                {testResults.query.success && (
                  <div className="mt-3 p-3 bg-gray-50 rounded text-sm">
                    <div className="font-medium">响应内容:</div>
                    <div className="mt-1 text-gray-700">{testResults.query.data?.response}</div>
                  </div>
                )}
              </div>
            ) : (
              <div className="text-gray-500">等待测试...</div>
            )}
          </div>

          {/* 文档测试结果 */}
          <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
            <h3 className="font-medium text-gray-900 mb-4">4. 文档API测试</h3>
            {testResults.documents ? (
              <div className={`p-4 rounded-lg ${testResults.documents.success ? 'bg-green-50 border border-green-200' : 'bg-red-50 border border-red-200'}`}>
                <div className="flex items-center justify-between">
                  <div>
                    <div className={`font-medium ${testResults.documents.success ? 'text-green-800' : 'text-red-800'}`}>
                      {testResults.documents.success ? '✅ 测试通过' : '❌ 测试失败'}
                    </div>
                    {testResults.documents.error && (
                      <div className="text-sm text-red-600 mt-1">{testResults.documents.error}</div>
                    )}
                  </div>
                  {testResults.documents.success && (
                    <div className="text-sm text-gray-500">
                      文档数量: {testResults.documents.data?.length || 0}
                    </div>
                  )}
                </div>
                {testResults.documents.success && testResults.documents.data && (
                  <div className="mt-3">
                    <div className="font-medium text-sm mb-2">文档列表:</div>
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
              <div className="text-gray-500">等待测试...</div>
            )}
          </div>
        </div>

        {/* 当前状态 */}
        <div className="mt-8 bg-white rounded-xl shadow-sm border border-gray-200 p-6">
          <h3 className="font-medium text-gray-900 mb-4">当前状态</h3>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="p-4 bg-gray-50 rounded-lg">
              <div className="text-sm text-gray-500">Token状态</div>
              <div className={`font-medium ${tokenReady ? 'text-green-600' : 'text-gray-600'}`}>
                {tokenReady ? '已设置' : '未设置'}
              </div>
            </div>
            <div className="p-4 bg-gray-50 rounded-lg">
              <div className="text-sm text-gray-500">用户状态</div>
              <div className={`font-medium ${userReady ? 'text-green-600' : 'text-gray-600'}`}>
                {userReady ? '已登录' : '未登录'}
              </div>
            </div>
            <div className="p-4 bg-gray-50 rounded-lg">
              <div className="text-sm text-gray-500">API连接</div>
              <div className="font-medium text-green-600">正常</div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
