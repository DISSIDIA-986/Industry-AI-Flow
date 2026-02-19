// WebSocket服务 - 用于实时通信
// 支持聊天消息、通知、实时数据更新

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
  private ws: WebSocket | null = null
  private reconnectAttempts = 0
  private maxReconnectAttempts = 5
  private reconnectDelay = 1000
  private heartbeatInterval: NodeJS.Timeout | null = null
  private messageHandlers: Map<WebSocketMessageType, ((data: any) => void)[]> = new Map()
  private connectionHandlers: ((connected: boolean) => void)[] = []
  private url: string
  private isConnected = false

  constructor(url: string = 'ws://localhost:8001/ws') {
    this.url = url
  }

  // 连接WebSocket
  connect(): Promise<boolean> {
    return new Promise((resolve) => {
      try {
        this.ws = new WebSocket(this.url)
        
        this.ws.onopen = () => {
          console.log('WebSocket连接成功')
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
            console.error('WebSocket消息解析失败:', error)
          }
        }
        
        this.ws.onclose = (event) => {
          console.log('WebSocket连接关闭:', event.code, event.reason)
          this.isConnected = false
          this.stopHeartbeat()
          this.notifyConnectionChange(false)
          this.attemptReconnect()
          resolve(false)
        }
        
        this.ws.onerror = (error) => {
          console.error('WebSocket错误:', error)
          this.isConnected = false
          this.notifyConnectionChange(false)
          resolve(false)
        }
        
        // 设置连接超时
        setTimeout(() => {
          if (!this.isConnected) {
            console.warn('WebSocket连接超时')
            resolve(false)
          }
        }, 5000)
        
      } catch (error) {
        console.error('WebSocket连接失败:', error)
        resolve(false)
      }
    })
  }

  // 断开连接
  disconnect(): void {
    if (this.ws) {
      this.ws.close(1000, '正常关闭')
      this.ws = null
    }
    this.stopHeartbeat()
    this.isConnected = false
    this.notifyConnectionChange(false)
  }

  // 发送消息
  send(type: WebSocketMessageType, data: any): boolean {
    if (!this.ws || this.ws.readyState !== WebSocket.OPEN) {
      console.warn('WebSocket未连接，无法发送消息')
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
      console.error('发送WebSocket消息失败:', error)
      return false
    }
  }

  // 发送聊天消息
  sendChatMessage(message: string, conversationId?: string, metadata?: any): boolean {
    const data: ChatMessageData = {
      message,
      conversation_id: conversationId,
      user_id: localStorage.getItem('userId') || undefined,
      metadata
    }
    return this.send('chat_message', data)
  }

  // 发送查询请求
  sendQuery(query: string, conversationId?: string): boolean {
    return this.sendChatMessage(query, conversationId, { is_query: true })
  }

  // 注册消息处理器
  onMessage(type: WebSocketMessageType, handler: (data: any) => void): () => void {
    if (!this.messageHandlers.has(type)) {
      this.messageHandlers.set(type, [])
    }
    this.messageHandlers.get(type)!.push(handler)
    
    // 返回取消注册的函数
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

  // 注册连接状态变化处理器
  onConnectionChange(handler: (connected: boolean) => void): () => void {
    this.connectionHandlers.push(handler)
    
    // 立即通知当前状态
    handler(this.isConnected)
    
    // 返回取消注册的函数
    return () => {
      const index = this.connectionHandlers.indexOf(handler)
      if (index > -1) {
        this.connectionHandlers.splice(index, 1)
      }
    }
  }

  // 获取连接状态
  getConnectionStatus(): boolean {
    return this.isConnected
  }

  // 私有方法
  private handleMessage(message: WebSocketMessage): void {
    console.log('收到WebSocket消息:', message)
    
    // 处理心跳消息
    if (message.type === 'ping') {
      this.send('pong', { timestamp: message.timestamp })
      return
    }
    
    if (message.type === 'pong') {
      // 心跳响应，无需处理
      return
    }
    
    // 调用注册的处理器
    const handlers = this.messageHandlers.get(message.type)
    if (handlers) {
      handlers.forEach(handler => handler(message.data))
    }
    
    // 所有消息都触发通用处理器
    const allHandlers = this.messageHandlers.get('*' as WebSocketMessageType)
    if (allHandlers) {
      allHandlers.forEach(handler => handler(message))
    }
  }

  private notifyConnectionChange(connected: boolean): void {
    this.connectionHandlers.forEach(handler => handler(connected))
  }

  private startHeartbeat(): void {
    this.stopHeartbeat()
    this.heartbeatInterval = setInterval(() => {
      if (this.isConnected) {
        this.send('ping', { timestamp: Date.now() })
      }
    }, 30000) // 每30秒发送一次心跳
  }

  private stopHeartbeat(): void {
    if (this.heartbeatInterval) {
      clearInterval(this.heartbeatInterval)
      this.heartbeatInterval = null
    }
  }

  private attemptReconnect(): void {
    if (this.reconnectAttempts >= this.maxReconnectAttempts) {
      console.log('达到最大重连次数，停止重连')
      return
    }
    
    this.reconnectAttempts++
    const delay = this.reconnectDelay * Math.pow(1.5, this.reconnectAttempts - 1)
    
    console.log(`将在 ${delay}ms 后尝试重连 (第 ${this.reconnectAttempts} 次)`)
    
    setTimeout(() => {
      if (!this.isConnected) {
        this.connect()
      }
    }, delay)
  }
}

// 模拟WebSocket服务 - 用于开发环境
export class MockWebSocketService extends WebSocketService {
  private mockResponses: Map<WebSocketMessageType, any[]> = new Map()
  private responseDelay = 500
  
  constructor() {
    super('ws://mock-server/ws')
    this.setupMockResponses()
  }

  private setupMockResponses(): void {
    // 模拟聊天响应
    this.mockResponses.set('chat_message', [
      {
        type: 'query_response',
        data: {
          query: '测试查询',
          response: '这是模拟的AI响应。在实际环境中，这会连接到真实的后端AI服务。',
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
    
    // 模拟通知
    this.mockResponses.set('notification', [
      {
        type: 'notification',
        data: {
          title: '系统通知',
          message: '欢迎使用Industry AI Flow!',
          level: 'info',
          duration: 5000
        }
      }
    ])
  }

  async connect(): Promise<boolean> {
    console.log('使用模拟WebSocket连接')
    this.isConnected = true
    this.notifyConnectionChange(true)
    
    // 模拟连接延迟
    await new Promise(resolve => setTimeout(resolve, 300))
    
    // 发送欢迎通知
    setTimeout(() => {
      this.handleMessage({
        type: 'notification',
        data: {
          title: '连接成功',
          message: '已连接到模拟WebSocket服务',
          level: 'success',
          duration: 3000
        },
        timestamp: new Date().toISOString()
      })
    }, 500)
    
    return true
  }

  disconnect(): void {
    console.log('断开模拟WebSocket连接')
    this.isConnected = false
    this.notifyConnectionChange(false)
  }

  send(type: WebSocketMessageType, data: any): boolean {
    console.log('模拟发送WebSocket消息:', { type, data })
    
    if (!this.isConnected) {
      console.warn('模拟WebSocket未连接')
      return false
    }
    
    // 模拟网络延迟
    setTimeout(() => {
      // 如果是聊天消息，返回模拟响应
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
      
      // 如果是查询，返回特定响应
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
        response: `基于我的分析，${query} 需要考虑多个因素。在建筑行业中，这通常涉及材料成本、人工费用、时间安排和风险管理。`,
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
        response: `这是一个很好的问题！${query} 在建筑项目管理中非常重要。建议进行详细的风险评估和成本分析。`,
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
        response: `关于 ${query}，根据行业最佳实践，需要考虑以下关键点：1. 合规性要求 2. 成本效益分析 3. 时间线规划 4. 风险评估。`,
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

// 创建WebSocket服务实例
export const createWebSocketService = (useMock: boolean = true): WebSocketService => {
  if (useMock || process.env.NODE_ENV === 'development') {
    console.log('使用模拟WebSocket服务')
    return new MockWebSocketService()
  }
  
  const wsUrl = process.env.NEXT_PUBLIC_WS_URL || 'ws://localhost:8001/ws'
  console.log('使用真实WebSocket服务:', wsUrl)
  return new WebSocketService(wsUrl)
}

// 默认导出
export const websocketService = createWebSocketService()

export default websocketService