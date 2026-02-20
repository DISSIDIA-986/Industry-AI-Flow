'use client'

import { useState, useRef, useEffect } from 'react'
import { useAuth } from '@/contexts/AuthContext'
import { workflowApi, realApiService } from '@/lib/api-client'
import { websocketService, type QueryResponseData } from '@/lib/websocket-service'

interface Message {
  id: string
  content: string
  sender: 'user' | 'ai'
  timestamp: Date
  intent?: {
    type: string
    confidence: number
    description: string
  }
  sources?: Array<{
    document_id: string
    document_name: string
    relevance: number
    content: string
  }>
  metadata?: Record<string, unknown>
}

export default function WorkflowChatPage() {
  const [messages, setMessages] = useState<Message[]>([
    {
      id: '1',
      content: '你好！我是Industry AI Flow助手。我可以帮助您进行建筑成本估算、风险分析和数据查询。请问有什么可以帮助您的？',
      sender: 'ai',
      timestamp: new Date()
    }
  ])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [apiStatus, setApiStatus] = useState<'checking' | 'connected' | 'disconnected'>('checking')
  const [wsStatus, setWsStatus] = useState<'disconnected' | 'connecting' | 'connected'>('disconnected')
  const [useWebSocket, setUseWebSocket] = useState(false)
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const { user } = useAuth()

  // 检查API连接状态
  useEffect(() => {
    const checkApiHealth = async () => {
      try {
        const health = await realApiService.checkHealth()
        setApiStatus(health.status === 'ok' ? 'connected' : 'disconnected')
      } catch {
        setApiStatus('disconnected')
      }
    }
    
    checkApiHealth()
    // 每30秒检查一次API状态
    const interval = setInterval(checkApiHealth, 30000)
    return () => clearInterval(interval)
  }, [])

  // WebSocket连接管理
  useEffect(() => {
    if (!useWebSocket) return
    
    setWsStatus('connecting')
    
    const connectWebSocket = async () => {
      const connected = await websocketService.connect()
      setWsStatus(connected ? 'connected' : 'disconnected')
    }
    
    connectWebSocket()
    
    // 监听连接状态变化
    const unsubscribe = websocketService.onConnectionChange((connected) => {
      setWsStatus(connected ? 'connected' : 'disconnected')
    })
    
    // 监听查询响应
    const unsubscribeResponse = websocketService.onMessage('query_response', (data: QueryResponseData) => {
      const aiMessage: Message = {
        id: (Date.now() + 1).toString(),
        content: data.response,
        sender: 'ai',
        timestamp: new Date(data.timestamp),
        metadata: data.metadata
      }
      
      setMessages(prev => [...prev, aiMessage])
      setLoading(false)
    })
    
    // 监听通知
    const unsubscribeNotification = websocketService.onMessage('notification', (data: unknown) => {
      console.log('收到通知:', data)
      // 这里可以添加通知显示逻辑
    })
    
    return () => {
      unsubscribe()
      unsubscribeResponse()
      unsubscribeNotification()
      websocketService.disconnect()
    }
  }, [useWebSocket])

  const quickPrompts = [
    '估算一个20层办公楼在多伦多的成本风险',
    '医疗医院项目成本超支的可能原因有哪些？',
    '分析住宅项目的材料成本趋势',
    '生成一个建筑项目的风险评估报告',
    '比较不同施工方法的成本效益'
  ]

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  const handleSend = async () => {
    if (!input.trim() || loading) return

    const userMessage: Message = {
      id: Date.now().toString(),
      content: input,
      sender: 'user',
      timestamp: new Date()
    }

    setMessages(prev => [...prev, userMessage])
    setInput('')
    setLoading(true)

    try {
      if (useWebSocket && wsStatus === 'connected') {
        // 使用WebSocket发送查询
        const sent = websocketService.sendChatMessage(input)
        if (!sent) {
          throw new Error('WebSocket发送失败')
        }
        // WebSocket响应将通过事件监听器处理
      } else {
        // 使用HTTP API发送查询
        const response = await workflowApi.sendQuery({ query: input })
        
        const aiMessage: Message = {
          id: (Date.now() + 1).toString(),
          content: response.response,
          sender: 'ai',
          timestamp: new Date(),
          intent: response.intent,
          sources: response.sources
        }

        setMessages(prev => [...prev, aiMessage])
        setLoading(false)
      }
    } catch (error) {
      console.error('Query error:', error)
      
      const errorMessage: Message = {
        id: (Date.now() + 2).toString(),
        content: '抱歉，处理您的查询时出现错误。请稍后重试。',
        sender: 'ai',
        timestamp: new Date()
      }
      
      setMessages(prev => [...prev, errorMessage])
      setLoading(false)
    }
  }

  const handleQuickPrompt = (prompt: string) => {
    setInput(prompt)
  }

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  return (
    <div className="max-w-6xl mx-auto p-4 md:p-6">
      <div className="mb-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">工作流聊天</h1>
            <p className="text-gray-600 mt-2">
              与AI助手对话，进行成本估算、风险分析和数据查询
            </p>
          </div>
          <div className="flex items-center space-x-4">
            {/* WebSocket控制 */}
            <div className="flex items-center space-x-2">
              <button
                onClick={() => setUseWebSocket(!useWebSocket)}
                className={`px-3 py-1 rounded-lg text-sm font-medium transition-colors ${
                  useWebSocket 
                    ? 'bg-blue-600 text-white hover:bg-blue-700' 
                    : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
                }`}
              >
                {useWebSocket ? 'WebSocket: 开' : 'WebSocket: 关'}
              </button>
              <div className={`w-2 h-2 rounded-full ${
                wsStatus === 'connected' ? 'bg-green-500' :
                wsStatus === 'connecting' ? 'bg-yellow-500' : 'bg-red-500'
              }`}></div>
              <span className="text-xs text-gray-600">
                {wsStatus === 'connected' ? '已连接' :
                 wsStatus === 'connecting' ? '连接中...' : '未连接'}
              </span>
            </div>
            
            {/* API状态 */}
            <div className="flex items-center space-x-2">
              <div className={`w-2 h-2 rounded-full ${
                apiStatus === 'connected' ? 'bg-green-500' :
                apiStatus === 'disconnected' ? 'bg-red-500' : 'bg-yellow-500'
              }`}></div>
              <span className="text-sm text-gray-600">
                {apiStatus === 'connected' ? 'API已连接' :
                 apiStatus === 'disconnected' ? 'API未连接（使用模拟数据）' : '检查API状态...'}
              </span>
            </div>
          </div>
        </div>
        
        {/* WebSocket状态提示 */}
        {useWebSocket && (
          <div className={`mt-3 p-3 rounded-lg text-sm ${
            wsStatus === 'connected' 
              ? 'bg-green-50 text-green-800 border border-green-200' 
              : wsStatus === 'connecting'
              ? 'bg-yellow-50 text-yellow-800 border border-yellow-200'
              : 'bg-red-50 text-red-800 border border-red-200'
          }`}>
            {wsStatus === 'connected' 
              ? '✅ WebSocket实时连接已启用，消息将实时推送' 
              : wsStatus === 'connecting'
              ? '🔄 正在连接WebSocket服务...'
              : '❌ WebSocket连接失败，已自动切换到HTTP API'}
          </div>
        )}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* 聊天主区域 */}
        <div className="lg:col-span-2">
          <div className="bg-white rounded-xl shadow-sm border border-gray-200">
            {/* 聊天消息区域 */}
            <div className="h-[500px] overflow-y-auto p-4">
              {messages.map((message) => (
                <div
                  key={message.id}
                  className={`mb-6 ${message.sender === 'user' ? 'text-right' : 'text-left'}`}
                >
                  <div
                    className={`inline-block max-w-[80%] rounded-2xl px-4 py-4 ${
                      message.sender === 'user'
                        ? 'bg-blue-600 text-white'
                        : 'bg-gray-100 text-gray-800'
                    }`}
                  >
                    <div className="whitespace-pre-wrap">{message.content}</div>
                    
                    {/* 显示意图信息（仅AI消息） */}
                    {message.sender === 'ai' && message.intent && (
                      <div className="mt-3 pt-3 border-t border-gray-300 border-opacity-30">
                        <div className="flex items-center justify-between text-sm">
                          <span className="font-medium">意图识别:</span>
                          <span className="bg-blue-100 text-blue-800 px-2 py-1 rounded text-xs">
                            {message.intent.description}
                          </span>
                        </div>
                        <div className="mt-1 text-xs text-gray-600">
                          置信度: {(message.intent.confidence * 100).toFixed(1)}%
                        </div>
                      </div>
                    )}
                    
                    {/* 显示来源信息（仅AI消息） */}
                    {message.sender === 'ai' && message.sources && message.sources.length > 0 && (
                      <div className="mt-3 pt-3 border-t border-gray-300 border-opacity-30">
                        <div className="text-sm font-medium mb-2">参考来源:</div>
                        <div className="space-y-2">
                          {message.sources.map((source, index) => (
                            <div key={index} className="text-xs bg-white bg-opacity-50 p-2 rounded">
                              <div className="font-medium">{source.document_name}</div>
                              <div className="text-gray-600 truncate">{source.content}</div>
                              <div className="text-gray-500 mt-1">
                                相关性: {(source.relevance * 100).toFixed(0)}%
                              </div>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                    
                    <div
                      className={`text-xs mt-3 ${
                        message.sender === 'user'
                          ? 'text-blue-200'
                          : 'text-gray-500'
                      }`}
                    >
                      {message.timestamp.toLocaleTimeString([], { 
                        hour: '2-digit', 
                        minute: '2-digit' 
                      })}
                    </div>
                  </div>
                </div>
              ))}
              
              {loading && (
                <div className="text-left mb-4">
                  <div className="inline-block max-w-[80%] rounded-2xl px-4 py-3 bg-gray-100">
                    <div className="flex items-center space-x-2">
                      <div className="w-2 h-2 bg-gray-400 rounded-full animate-pulse"></div>
                      <div className="w-2 h-2 bg-gray-400 rounded-full animate-pulse delay-150"></div>
                      <div className="w-2 h-2 bg-gray-400 rounded-full animate-pulse delay-300"></div>
                    </div>
                  </div>
                </div>
              )}
              
              <div ref={messagesEndRef} />
            </div>

            {/* 输入区域 */}
            <div className="border-t border-gray-200 p-4">
              <div className="flex space-x-2">
                <textarea
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  onKeyPress={handleKeyPress}
                  placeholder="输入您的问题或查询..."
                  className="flex-1 px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 resize-none"
                  rows={2}
                  disabled={loading}
                />
                <button
                  onClick={handleSend}
                  disabled={loading || !input.trim()}
                  className="bg-blue-600 hover:bg-blue-700 text-white px-6 py-3 rounded-lg font-medium transition disabled:opacity-50 disabled:cursor-not-allowed self-end"
                >
                  {loading ? '发送中...' : '发送'}
                </button>
              </div>
              
              <div className="mt-3 text-sm text-gray-500">
                按 Enter 发送，Shift + Enter 换行
              </div>
            </div>
          </div>
        </div>

        {/* 侧边栏 */}
        <div className="space-y-6">
          {/* 快速提示 */}
          <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-4">
            <h3 className="font-medium text-gray-900 mb-3">快速提示</h3>
            <div className="space-y-2">
              {quickPrompts.map((prompt, index) => (
                <button
                  key={index}
                  onClick={() => handleQuickPrompt(prompt)}
                  className="w-full text-left p-3 bg-gray-50 hover:bg-gray-100 rounded-lg text-sm text-gray-700 transition"
                >
                  {prompt}
                </button>
              ))}
            </div>
          </div>

          {/* 用户信息 */}
          <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-4">
            <h3 className="font-medium text-gray-900 mb-3">用户信息</h3>
            {user ? (
              <div className="space-y-2">
                <div className="flex items-center space-x-3">
                  <div className="w-10 h-10 bg-blue-100 rounded-full flex items-center justify-center">
                    <span className="text-blue-600 font-medium">
                      {user.name.charAt(0).toUpperCase()}
                    </span>
                  </div>
                  <div>
                    <div className="font-medium">{user.name}</div>
                    <div className="text-sm text-gray-500">{user.email}</div>
                  </div>
                </div>
                <div className="pt-3 border-t border-gray-200">
                  <div className="text-sm text-gray-600">
                    已发送 {messages.filter(m => m.sender === 'user').length} 条消息
                  </div>
                </div>
              </div>
            ) : (
              <div className="text-gray-500 text-sm">未登录</div>
            )}
          </div>

          {/* 功能说明 */}
          <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-4">
            <h3 className="font-medium text-gray-900 mb-3">功能说明</h3>
            <ul className="space-y-2 text-sm text-gray-600">
              <li className="flex items-start">
                <div className="w-2 h-2 bg-blue-500 rounded-full mt-1.5 mr-2"></div>
                <span>建筑成本估算和分析</span>
              </li>
              <li className="flex items-start">
                <div className="w-2 h-2 bg-green-500 rounded-full mt-1.5 mr-2"></div>
                <span>风险评估和预测</span>
              </li>
              <li className="flex items-start">
                <div className="w-2 h-2 bg-purple-500 rounded-full mt-1.5 mr-2"></div>
                <span>数据查询和可视化</span>
              </li>
              <li className="flex items-start">
                <div className="w-2 h-2 bg-orange-500 rounded-full mt-1.5 mr-2"></div>
                <span>报告生成和导出</span>
              </li>
            </ul>
          </div>
        </div>
      </div>
    </div>
  )
}
