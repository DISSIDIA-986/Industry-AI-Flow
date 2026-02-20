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
      content: 'Hello! I amIndustry AI Flowassistant. I can help you with construction cost estimates, risk analysis and data queries. How can I help you?',
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

  // examineAPIconnection status
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
    // Check every 30 secondsAPIstate
    const interval = setInterval(checkApiHealth, 30000)
    return () => clearInterval(interval)
  }, [])

  // WebSocketConnection management
  useEffect(() => {
    if (!useWebSocket) return
    
    setWsStatus('connecting')
    
    const connectWebSocket = async () => {
      const connected = await websocketService.connect()
      setWsStatus(connected ? 'connected' : 'disconnected')
    }
    
    connectWebSocket()
    
    // Monitor connection status changes
    const unsubscribe = websocketService.onConnectionChange((connected) => {
      setWsStatus(connected ? 'connected' : 'disconnected')
    })
    
    // Listen for query responses
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
    
    // Listen for notifications
    const unsubscribeNotification = websocketService.onMessage('notification', (data: unknown) => {
      console.log('Notification received:', data)
      // Here you can add notification display logic
    })
    
    return () => {
      unsubscribe()
      unsubscribeResponse()
      unsubscribeNotification()
      websocketService.disconnect()
    }
  }, [useWebSocket])

  const quickPrompts = [
    'Estimating the cost risk of a 20-story office building in Toronto',
    'What are the possible causes of cost overruns on medical hospital projects?',
    'Analyze material cost trends for residential projects',
    'Generate a risk assessment report for a construction project',
    'Compare the cost-effectiveness of different construction methods'
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
        // useWebSocketSend inquiry
        const sent = websocketService.sendChatMessage(input)
        if (!sent) {
          throw new Error('WebSocketSending failed')
        }
        // WebSocketResponses will be handled via event listeners
      } else {
        // useHTTP APISend inquiry
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
        content: 'Sorry, an error occurred while processing your query. Please try again later.',
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
            <h1 className="text-2xl font-bold text-gray-900">Workflow chat</h1>
            <p className="text-gray-600 mt-2">
              andAIAssistant dialogue for cost estimation, risk analysis and data query
            </p>
          </div>
          <div className="flex items-center space-x-4">
            {/* WebSocketcontrol */}
            <div className="flex items-center space-x-2">
              <button
                onClick={() => setUseWebSocket(!useWebSocket)}
                className={`px-3 py-1 rounded-lg text-sm font-medium transition-colors ${
                  useWebSocket 
                    ? 'bg-blue-600 text-white hover:bg-blue-700' 
                    : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
                }`}
              >
                {useWebSocket ? 'WebSocket: open' : 'WebSocket: close'}
              </button>
              <div className={`w-2 h-2 rounded-full ${
                wsStatus === 'connected' ? 'bg-green-500' :
                wsStatus === 'connecting' ? 'bg-yellow-500' : 'bg-red-500'
              }`}></div>
              <span className="text-xs text-gray-600">
                {wsStatus === 'connected' ? 'Connected' :
                 wsStatus === 'connecting' ? 'Connecting...' : 'Not connected'}
              </span>
            </div>
            
            {/* APIstate */}
            <div className="flex items-center space-x-2">
              <div className={`w-2 h-2 rounded-full ${
                apiStatus === 'connected' ? 'bg-green-500' :
                apiStatus === 'disconnected' ? 'bg-red-500' : 'bg-yellow-500'
              }`}></div>
              <span className="text-sm text-gray-600">
                {apiStatus === 'connected' ? 'APIConnected' :
                 apiStatus === 'disconnected' ? 'APIConnection failed (please check backend)' : 'examineAPIstate...'}
              </span>
            </div>
          </div>
        </div>
        
        {/* WebSocketStatus prompt */}
        {useWebSocket && (
          <div className={`mt-3 p-3 rounded-lg text-sm ${
            wsStatus === 'connected' 
              ? 'bg-green-50 text-green-800 border border-green-200' 
              : wsStatus === 'connecting'
              ? 'bg-yellow-50 text-yellow-800 border border-yellow-200'
              : 'bg-red-50 text-red-800 border border-red-200'
          }`}>
            {wsStatus === 'connected' 
              ? '✅ WebSocketLive connection is enabled and messages will be pushed in real time' 
              : wsStatus === 'connecting'
              ? '🔄 ConnectingWebSocketServe...'
              : '❌ WebSocketConnection failed, automatically switched toHTTP API'}
          </div>
        )}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Main chat area */}
        <div className="lg:col-span-2">
          <div className="bg-white rounded-xl shadow-sm border border-gray-200">
            {/* Chat message area */}
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
                    
                    {/* Display intent information (onlyAIinformation) */}
                    {message.sender === 'ai' && message.intent && (
                      <div className="mt-3 pt-3 border-t border-gray-300 border-opacity-30">
                        <div className="flex items-center justify-between text-sm">
                          <span className="font-medium">Intent recognition:</span>
                          <span className="bg-blue-100 text-blue-800 px-2 py-1 rounded text-xs">
                            {message.intent.description}
                          </span>
                        </div>
                        <div className="mt-1 text-xs text-gray-600">
                          Confidence: {(message.intent.confidence * 100).toFixed(1)}%
                        </div>
                      </div>
                    )}
                    
                    {/* Show source information (onlyAIinformation) */}
                    {message.sender === 'ai' && message.sources && message.sources.length > 0 && (
                      <div className="mt-3 pt-3 border-t border-gray-300 border-opacity-30">
                        <div className="text-sm font-medium mb-2">Reference sources:</div>
                        <div className="space-y-2">
                          {message.sources.map((source, index) => (
                            <div key={index} className="text-xs bg-white bg-opacity-50 p-2 rounded">
                              <div className="font-medium">{source.document_name}</div>
                              <div className="text-gray-600 truncate">{source.content}</div>
                              <div className="text-gray-500 mt-1">
                                Relevance: {(source.relevance * 100).toFixed(0)}%
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

            {/* input area */}
            <div className="border-t border-gray-200 p-4">
              <div className="flex space-x-2">
                <textarea
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  onKeyPress={handleKeyPress}
                  placeholder="Enter your question or query..."
                  className="flex-1 px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 resize-none"
                  rows={2}
                  disabled={loading}
                />
                <button
                  onClick={handleSend}
                  disabled={loading || !input.trim()}
                  className="bg-blue-600 hover:bg-blue-700 text-white px-6 py-3 rounded-lg font-medium transition disabled:opacity-50 disabled:cursor-not-allowed self-end"
                >
                  {loading ? 'Sending...' : 'send'}
                </button>
              </div>
              
              <div className="mt-3 text-sm text-gray-500">
                according to Enter send,Shift + Enter newline
              </div>
            </div>
          </div>
        </div>

        {/* sidebar */}
        <div className="space-y-6">
          {/* Quick Tips */}
          <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-4">
            <h3 className="font-medium text-gray-900 mb-3">Quick Tips</h3>
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

          {/* User information */}
          <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-4">
            <h3 className="font-medium text-gray-900 mb-3">User information</h3>
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
                    Sent {messages.filter(m => m.sender === 'user').length} messages
                  </div>
                </div>
              </div>
            ) : (
              <div className="text-gray-500 text-sm">Not logged in</div>
            )}
          </div>

          {/* Function description */}
          <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-4">
            <h3 className="font-medium text-gray-900 mb-3">Function description</h3>
            <ul className="space-y-2 text-sm text-gray-600">
              <li className="flex items-start">
                <div className="w-2 h-2 bg-blue-500 rounded-full mt-1.5 mr-2"></div>
                <span>Construction Cost Estimation and Analysis</span>
              </li>
              <li className="flex items-start">
                <div className="w-2 h-2 bg-green-500 rounded-full mt-1.5 mr-2"></div>
                <span>Risk assessment and forecasting</span>
              </li>
              <li className="flex items-start">
                <div className="w-2 h-2 bg-purple-500 rounded-full mt-1.5 mr-2"></div>
                <span>Data query and visualization</span>
              </li>
              <li className="flex items-start">
                <div className="w-2 h-2 bg-orange-500 rounded-full mt-1.5 mr-2"></div>
                <span>Report generation and export</span>
              </li>
            </ul>
          </div>
        </div>
      </div>
    </div>
  )
}
