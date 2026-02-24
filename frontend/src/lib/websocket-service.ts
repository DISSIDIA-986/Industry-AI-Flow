// WebSocketServe - for real-time communication
// Supports chat messages, notifications, and real-time data updates

export type WebSocketMessageType = 
  | 'chat_message'
  | 'query_response'
  | 'notification'
  | 'status_update'
  | 'error'
  | 'ping'
  | 'pong'

export interface WebSocketMessage {
  type: WebSocketMessageType
  data: any
  timestamp: string
  id?: string
  sender?: string
}

export interface ChatMessageData {
  message: string
  conversation_id?: string
  user_id?: string
  metadata?: {
    intent?: string
    confidence?: number
    sources?: Array<{
      document_id: string
      document_name: string
      relevance: number
    }>
  }
}

export interface QueryResponseData {
  query: string
  response: string
  conversation_id: string
  timestamp: string
  metadata?: {
    model?: string
    tokens_used?: number
    processing_time?: number
  }
}

export interface NotificationData {
  title: string
  message: string
  level: 'info' | 'warning' | 'error' | 'success'
  duration?: number
  action?: {
    label: string
    onClick: () => void
  }
}

export interface StatusUpdateData {
  service: string
  status: 'online' | 'offline' | 'degraded'
  message?: string
  metrics?: Record<string, any>
}

export class WebSocketService {
  protected ws: WebSocket | null = null
  protected reconnectAttempts = 0
  protected maxReconnectAttempts = 5
  protected reconnectDelay = 1000
  protected heartbeatInterval: NodeJS.Timeout | null = null
  protected messageHandlers: Map<WebSocketMessageType, ((data: any) => void)[]> = new Map()
  protected connectionHandlers: ((connected: boolean) => void)[] = []
  protected url: string
  protected isConnected = false

  constructor(url: string = 'ws://localhost:8001/ws') {
    this.url = url
  }

  // connectWebSocket
  connect(): Promise<boolean> {
    return new Promise((resolve) => {
      try {
        this.ws = new WebSocket(this.url)
        
        this.ws.onopen = () => {
          console.log('WebSocketConnection successful')
          this.isConnected = true
          this.reconnectAttempts = 0
          this.startHeartbeat()
          this.notifyConnectionChange(true)
          resolve(true)
        }
        
        this.ws.onmessage = (event) => {
          try {
            const message: WebSocketMessage = JSON.parse(event.data)
            this.handleMessage(message)
          } catch (error) {
            console.error('WebSocketMessage parsing failed:', error)
          }
        }
        
        this.ws.onclose = (event) => {
          console.log('WebSocketConnection closed:', event.code, event.reason)
          this.isConnected = false
          this.stopHeartbeat()
          this.notifyConnectionChange(false)
          this.attemptReconnect()
          resolve(false)
        }
        
        this.ws.onerror = (error) => {
          console.error('WebSocketmistake:', error)
          this.isConnected = false
          this.notifyConnectionChange(false)
          resolve(false)
        }
        
        // Set connection timeout
        setTimeout(() => {
          if (!this.isConnected) {
            console.warn('WebSocketConnection timeout')
            resolve(false)
          }
        }, 5000)
        
      } catch (error) {
        console.error('WebSocketConnection failed:', error)
        resolve(false)
      }
    })
  }

  // Disconnect
  disconnect(): void {
    if (this.ws) {
      this.ws.close(1000, 'Normal shutdown')
      this.ws = null
    }
    this.stopHeartbeat()
    this.isConnected = false
    this.notifyConnectionChange(false)
  }

  // Send message
  send(type: WebSocketMessageType, data: any): boolean {
    if (!this.ws || this.ws.readyState !== WebSocket.OPEN) {
      console.warn('WebSocketNot connected, unable to send message')
      return false
    }
    
    try {
      const message: WebSocketMessage = {
        type,
        data,
        timestamp: new Date().toISOString(),
        id: Math.random().toString(36).substr(2, 9)
      }
      
      this.ws.send(JSON.stringify(message))
      return true
    } catch (error) {
      console.error('sendWebSocketMessage failed:', error)
      return false
    }
  }

  // Send chat message
  sendChatMessage(message: string, conversationId?: string, metadata?: any): boolean {
    const data: ChatMessageData = {
      message,
      conversation_id: conversationId,
      user_id: localStorage.getItem('userId') || undefined,
      metadata
    }
    return this.send('chat_message', data)
  }

  // Send query request
  sendQuery(query: string, conversationId?: string): boolean {
    return this.sendChatMessage(query, conversationId, { is_query: true })
  }

  // Register message handler
  onMessage(type: WebSocketMessageType, handler: (data: any) => void): () => void {
    if (!this.messageHandlers.has(type)) {
      this.messageHandlers.set(type, [])
    }
    this.messageHandlers.get(type)!.push(handler)
    
    // Returns the unregistered function
    return () => {
      const handlers = this.messageHandlers.get(type)
      if (handlers) {
        const index = handlers.indexOf(handler)
        if (index > -1) {
          handlers.splice(index, 1)
        }
      }
    }
  }

  // Register connection state change handler
  onConnectionChange(handler: (connected: boolean) => void): () => void {
    this.connectionHandlers.push(handler)
    
    // Immediately notify the current status
    handler(this.isConnected)
    
    // Returns the unregistered function
    return () => {
      const index = this.connectionHandlers.indexOf(handler)
      if (index > -1) {
        this.connectionHandlers.splice(index, 1)
      }
    }
  }

  // Get connection status
  getConnectionStatus(): boolean {
    return this.isConnected
  }

  // private method
  protected handleMessage(message: WebSocketMessage): void {
    console.log('receiveWebSocketinformation:', message)
    
    // Handle heartbeat messages
    if (message.type === 'ping') {
      this.send('pong', { timestamp: message.timestamp })
      return
    }
    
    if (message.type === 'pong') {
      // Heartbeat response, no processing required
      return
    }
    
    // Call registered handler
    const handlers = this.messageHandlers.get(message.type)
    if (handlers) {
      handlers.forEach(handler => handler(message.data))
    }
    
    // All messages trigger a general handler
    const allHandlers = this.messageHandlers.get('*' as WebSocketMessageType)
    if (allHandlers) {
      allHandlers.forEach(handler => handler(message))
    }
  }

  protected notifyConnectionChange(connected: boolean): void {
    this.connectionHandlers.forEach(handler => handler(connected))
  }

  private startHeartbeat(): void {
    this.stopHeartbeat()
    this.heartbeatInterval = setInterval(() => {
      if (this.isConnected) {
        this.send('ping', { timestamp: Date.now() })
      }
    }, 30000) // Send a heartbeat every 30 seconds
  }

  private stopHeartbeat(): void {
    if (this.heartbeatInterval) {
      clearInterval(this.heartbeatInterval)
      this.heartbeatInterval = null
    }
  }

  private attemptReconnect(): void {
    if (this.reconnectAttempts >= this.maxReconnectAttempts) {
      console.log('Reached the maximum number of reconnections and stopped reconnecting.')
      return
    }
    
    this.reconnectAttempts++
    const delay = this.reconnectDelay * Math.pow(1.5, this.reconnectAttempts - 1)
    
    console.log(`will be in ${delay}ms Then try to reconnect (No. ${this.reconnectAttempts} Second-rate)`)
    
    setTimeout(() => {
      if (!this.isConnected) {
        this.connect()
      }
    }, delay)
  }
}

// simulationWebSocketServe - for development environment
export class MockWebSocketService extends WebSocketService {
  private mockResponses: Map<WebSocketMessageType, any[]> = new Map()
  private responseDelay = 500
  
  constructor() {
    super('ws://mock-server/ws')
    this.setupMockResponses()
  }

  private setupMockResponses(): void {
    // Simulate chat response
    this.mockResponses.set('chat_message', [
      {
        type: 'query_response',
        data: {
          query: 'Test query',
          response: 'This is simulatedAIresponse. In a real environment this would connect to a real backendAIServe.',
          conversation_id: 'mock-conv-123',
          timestamp: new Date().toISOString(),
          metadata: {
            model: 'gpt-4',
            tokens_used: 150,
            processing_time: 1200
          }
        }
      }
    ])
    
    // Simulate notification
    this.mockResponses.set('notification', [
      {
        type: 'notification',
        data: {
          title: 'System notification',
          message: 'WelcomeIndustry AI Flow!',
          level: 'info',
          duration: 5000
        }
      }
    ])
  }

  async connect(): Promise<boolean> {
    console.log('Use simulationWebSocketconnect')
    this.isConnected = true
    this.notifyConnectionChange(true)
    
    // Simulate connection latency
    await new Promise(resolve => setTimeout(resolve, 300))
    
    // Send welcome notification
    setTimeout(() => {
      this.handleMessage({
        type: 'notification',
        data: {
          title: 'Connection successful',
          message: 'Connected to simulationWebSocketServe',
          level: 'success',
          duration: 3000
        },
        timestamp: new Date().toISOString()
      })
    }, 500)
    
    return true
  }

  disconnect(): void {
    console.log('Disconnect simulationWebSocketconnect')
    this.isConnected = false
    this.notifyConnectionChange(false)
  }

  send(type: WebSocketMessageType, data: any): boolean {
    console.log('Analog sendingWebSocketinformation:', { type, data })
    
    if (!this.isConnected) {
      console.warn('simulationWebSocketNot connected')
      return false
    }
    
    // Simulate network latency
    setTimeout(() => {
      // If it is a chat message, return a simulated response
      if (type === 'chat_message') {
        const responses = this.mockResponses.get('query_response') || []
        responses.forEach(response => {
          setTimeout(() => {
            this.handleMessage({
              ...response,
              timestamp: new Date().toISOString()
            })
          }, this.responseDelay)
        })
      }
      
      // If it is a query, return a specific response
      if (type === 'chat_message' && data.message) {
        const mockResponse = this.generateMockResponse(data.message)
        setTimeout(() => {
          this.handleMessage({
            type: 'query_response',
            data: mockResponse,
            timestamp: new Date().toISOString()
          })
        }, this.responseDelay)
      }
    }, 100)
    
    return true
  }

  private generateMockResponse(query: string): any {
    const responses = [
      {
        query,
        response: `Based on my analysis,${query} There are several factors to consider. In the construction industry, this typically involves material costs, labor charges, timing, and risk management.`,
        conversation_id: 'mock-conv-' + Date.now(),
        timestamp: new Date().toISOString(),
        metadata: {
          model: 'gpt-4',
          tokens_used: 200,
          processing_time: 1500,
          confidence: 0.85
        }
      },
      {
        query,
        response: `This is a great question!${query} Very important in construction project management. A detailed risk assessment and cost analysis is recommended.`,
        conversation_id: 'mock-conv-' + Date.now(),
        timestamp: new Date().toISOString(),
        metadata: {
          model: 'claude-3',
          tokens_used: 180,
          processing_time: 1200,
          confidence: 0.88
        }
      },
      {
        query,
        response: `about ${query}，Based on industry best practices, the following key points need to be considered: 1. Compliance requirements 2. cost benefit analysis 3. timeline planning 4. risk assessment.`,
        conversation_id: 'mock-conv-' + Date.now(),
        timestamp: new Date().toISOString(),
        metadata: {
          model: 'gemini-pro',
          tokens_used: 220,
          processing_time: 1800,
          confidence: 0.82
        }
      }
    ]
    
    return responses[Math.floor(Math.random() * responses.length)]
  }
}

function shouldUseMockWebSocket(explicitUseMock?: boolean): boolean {
  if (typeof explicitUseMock === 'boolean') {
    return explicitUseMock
  }

  const raw = String(process.env.NEXT_PUBLIC_USE_MOCK_WS || '')
    .trim()
    .toLowerCase()
  return raw === '1' || raw === 'true' || raw === 'yes' || raw === 'on'
}

// createWebSocketService instance
export const createWebSocketService = (useMock?: boolean): WebSocketService => {
  if (shouldUseMockWebSocket(useMock)) {
    console.log('Use simulationWebSocketServe')
    return new MockWebSocketService()
  }

  const wsUrl = process.env.NEXT_PUBLIC_WS_URL || 'ws://localhost:8001/ws'
  console.log('use realWebSocketServe:', wsUrl)
  return new WebSocketService(wsUrl)
}

// Default export
export const websocketService = createWebSocketService()

export default websocketService
