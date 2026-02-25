'use client'

import { useState, useRef, useEffect } from 'react'
import { useAuth } from '@/contexts/AuthContext'
import { workflowApi, realApiService } from '@/lib/api-client'
import { websocketService, type QueryResponseData } from '@/lib/websocket-service'
import { buildQuickTipsFromDocuments, parsePinnedQuickTips } from '@/lib/workflow-quick-tips'

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
  suggestedQuestions?: string[]
  metadata?: Record<string, unknown>
}

function createWorkflowSessionId(): string {
  if (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function') {
    return `wf-${crypto.randomUUID()}`
  }
  return `wf-${Date.now()}-${Math.random().toString(16).slice(2)}`
}

const defaultQuickPrompts = [
  'Summarize the key compliance requirements from the uploaded construction documents and cite evidence.',
  'Generate a site safety inspection checklist based on the current knowledge base.',
  'Compare two core standards in the indexed documents and highlight conflicts or gaps.',
  'List the highest-risk compliance issues that could delay construction approval.',
  'Create a pre-construction quality-control checklist grounded in the indexed documents.',
]

const pinnedQuickPrompts = parsePinnedQuickTips(
  process.env.NEXT_PUBLIC_DEMO_PINNED_QUICK_TIPS,
  defaultQuickPrompts.length,
)

function extractSuggestedQuestions(metadata: unknown): string[] | undefined {
  if (!metadata || typeof metadata !== 'object') {
    return undefined
  }
  const payload = metadata as Record<string, unknown>
  const agentExecution =
    payload.agent_execution && typeof payload.agent_execution === 'object'
      ? (payload.agent_execution as Record<string, unknown>)
      : undefined
  const raw = payload.suggested_questions ?? agentExecution?.suggested_questions
  if (!Array.isArray(raw)) {
    return undefined
  }
  const normalized = raw
    .map((item) => String(item || '').trim())
    .filter((item) => item.length > 0)
  return normalized.length > 0 ? normalized.slice(0, 5) : undefined
}

function buildFallbackSuggestedQuestions(
  query: string,
  sourceName?: string,
): string[] {
  const normalizedQuery = query.trim().replace(/\s+/g, ' ')
  const shortQuery = normalizedQuery.length > 72
    ? `${normalizedQuery.slice(0, 72)}...`
    : normalizedQuery
  const sourceLabel = sourceName && sourceName.trim().length > 0
    ? sourceName.trim()
    : 'the referenced documents'

  return [
    `Which section in ${sourceLabel} most directly supports this answer?`,
    `What assumptions should I validate next for "${shortQuery}"?`,
    `Can you provide a step-by-step checklist to execute this recommendation?`,
  ]
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
  const [quickPrompts, setQuickPrompts] = useState<string[]>(
    pinnedQuickPrompts ?? defaultQuickPrompts,
  )
  const [sessionId] = useState<string>(createWorkflowSessionId)
  const pendingQueryRef = useRef<string>('')
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

  useEffect(() => {
    if (pinnedQuickPrompts && pinnedQuickPrompts.length > 0) {
      return
    }

    let cancelled = false

    const loadDocumentAwareQuickTips = async () => {
      try {
        const docs = await realApiService.getDocuments()
        if (cancelled) {
          return
        }

        const generated = buildQuickTipsFromDocuments(docs, defaultQuickPrompts)
        setQuickPrompts((prev) => (prev === defaultQuickPrompts ? generated : prev))
      } catch (error) {
        console.warn('Failed to build document-aware quick tips:', error)
      }
    }

    loadDocumentAwareQuickTips()

    return () => {
      cancelled = true
    }
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
      const suggestedQuestions =
        extractSuggestedQuestions(data.metadata) ??
        buildFallbackSuggestedQuestions(pendingQueryRef.current)
      const aiMessage: Message = {
        id: (Date.now() + 1).toString(),
        content: data.response,
        sender: 'ai',
        timestamp: new Date(data.timestamp),
        suggestedQuestions,
        metadata: data.metadata
      }
      
      setMessages(prev => [...prev, aiMessage])
      setQuickPrompts(suggestedQuestions)
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

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  const handleSend = async () => {
    if (!input.trim() || loading) return
    const queryText = input.trim()
    pendingQueryRef.current = queryText

    const userMessage: Message = {
      id: Date.now().toString(),
      content: queryText,
      sender: 'user',
      timestamp: new Date()
    }

    setMessages(prev => [...prev, userMessage])
    setInput('')
    setLoading(true)

    try {
      if (useWebSocket && wsStatus === 'connected') {
        // useWebSocketSend inquiry
        const sent = websocketService.sendChatMessage(queryText)
        if (!sent) {
          throw new Error('WebSocketSending failed')
        }
        // WebSocketResponses will be handled via event listeners
      } else {
        // useHTTP APISend inquiry
        const response = await workflowApi.sendQuery(
          {
            query: queryText,
            session_id: sessionId,
            thread_id: sessionId,
          },
          {
            userId: user?.id,
          },
        )
        
        const suggestedQuestions =
          (response.suggested_questions && response.suggested_questions.length > 0)
            ? response.suggested_questions
            : buildFallbackSuggestedQuestions(
                queryText,
                response.sources && response.sources.length > 0
                  ? response.sources[0].document_name
                  : undefined,
              )

        const aiMessage: Message = {
          id: (Date.now() + 1).toString(),
          content: response.response,
          sender: 'ai',
          timestamp: new Date(),
          intent: response.intent,
          sources: response.sources,
          suggestedQuestions,
          metadata: response.metadata
        }

        setMessages(prev => [...prev, aiMessage])
        setQuickPrompts(suggestedQuestions)
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

  const wsStatusDotClass =
    wsStatus === 'connected'
      ? 'bg-green-500'
      : wsStatus === 'connecting'
      ? 'bg-yellow-500'
      : 'bg-gray-400'

  const wsStatusLabel =
    wsStatus === 'connected'
      ? 'Connected'
      : wsStatus === 'connecting'
      ? 'Connecting...'
      : 'Disconnected (HTTP fallback active)'

  const wsBannerClass =
    wsStatus === 'connected'
      ? 'bg-green-50 text-green-800 border border-green-200'
      : wsStatus === 'connecting'
      ? 'bg-yellow-50 text-yellow-800 border border-yellow-200'
      : 'bg-blue-50 text-blue-800 border border-blue-200'

  const wsBannerText =
    wsStatus === 'connected'
      ? 'WebSocket real-time channel is active.'
      : wsStatus === 'connecting'
      ? 'Connecting to WebSocket service...'
      : 'WebSocket service is unavailable. Switched to HTTP API automatically; queries continue to work.'

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
              <div className={`w-2 h-2 rounded-full ${wsStatusDotClass}`}></div>
              <span className="text-xs text-gray-600">
                {wsStatusLabel}
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
          <div className={`mt-3 p-3 rounded-lg text-sm ${wsBannerClass}`}>
            {wsBannerText}
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

                    {message.sender === 'ai' &&
                      message.suggestedQuestions &&
                      message.suggestedQuestions.length > 0 && (
                        <div className="mt-3 pt-3 border-t border-gray-300 border-opacity-30">
                          <div className="text-sm font-medium mb-2">Suggested follow-up questions:</div>
                          <div className="flex flex-wrap gap-2">
                            {message.suggestedQuestions.map((question, index) => (
                              <button
                                key={`${message.id}-suggestion-${index}`}
                                type="button"
                                onClick={() => handleQuickPrompt(question)}
                                className="text-xs px-3 py-1.5 rounded-full bg-white bg-opacity-80 hover:bg-opacity-100 border border-gray-300 text-gray-700 transition"
                              >
                                {question}
                              </button>
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
