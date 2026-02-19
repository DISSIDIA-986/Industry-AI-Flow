// 真实后端API客户端
// 用于集成实际的FastAPI后端服务

import { ApiError } from './api-client'

// 真实API配置
const REAL_API_BASE_URL = process.env.NEXT_PUBLIC_REAL_API_URL || 'http://localhost:8001/api/v1'
const REAL_API_TIMEOUT = 60000 // 60秒超时（AI查询可能需要更长时间）

// 创建真实API客户端
const createRealApiClient = () => {
  const client = {
    async request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
      const url = `${REAL_API_BASE_URL}${endpoint}`
      const token = localStorage.getItem('token')
      
      const headers: HeadersInit = {
        'Content-Type': 'application/json',
        ...options.headers,
      }
      
      if (token) {
        headers['Authorization'] = `Bearer ${token}`
      }
      
      const controller = new AbortController()
      const timeoutId = setTimeout(() => controller.abort(), REAL_API_TIMEOUT)
      
      try {
        const response = await fetch(url, {
          ...options,
          headers,
          signal: controller.signal,
        })
        
        clearTimeout(timeoutId)
        
        if (!response.ok) {
          const errorData = await response.json().catch(() => ({}))
          throw new ApiError(response.status, errorData.detail || response.statusText)
        }
        
        return await response.json()
      } catch (error) {
        clearTimeout(timeoutId)
        if (error instanceof ApiError) {
          throw error
        }
        if (error.name === 'AbortError') {
          throw new ApiError(408, '请求超时，请稍后重试')
        }
        throw new ApiError(500, '网络错误，请检查网络连接')
      }
    },
    
    async get<T>(endpoint: string): Promise<T> {
      return this.request<T>(endpoint, { method: 'GET' })
    },
    
    async post<T>(endpoint: string, data?: any): Promise<T> {
      return this.request<T>(endpoint, {
        method: 'POST',
        body: data ? JSON.stringify(data) : undefined,
      })
    },
    
    async put<T>(endpoint: string, data?: any): Promise<T> {
      return this.request<T>(endpoint, {
        method: 'PUT',
        body: data ? JSON.stringify(data) : undefined,
      })
    },
    
    async delete<T>(endpoint: string): Promise<T> {
      return this.request<T>(endpoint, { method: 'DELETE' })
    }
  }
  
  return client
}

// 真实API客户端实例
export const realApi = createRealApiClient()

// 真实API类型定义

// 工作流查询请求
export interface RealWorkflowQueryRequest {
  query: string
  context?: string
  file_ids?: string[]
  model?: string
  temperature?: number
  max_tokens?: number
}

// 工作流查询响应
export interface RealWorkflowQueryResponse {
  id?: string
  query: string
  response: string
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
    metadata?: Record<string, any>
  }>
  timestamp: string
  confidence?: number
  usage?: {
    prompt_tokens: number
    completion_tokens: number
    total_tokens: number
  }
  model?: string
}

// 文档上传请求
export interface RealDocumentUploadRequest {
  file: File
  metadata?: {
    title?: string
    description?: string
    tags?: string[]
    category?: string
  }
}

// 文档上传响应
export interface RealDocumentUploadResponse {
  id: string
  filename: string
  title: string
  size: number
  mime_type: string
  upload_time: string
  status: 'pending' | 'processing' | 'completed' | 'failed'
  metadata?: Record<string, any>
}

// 成本估算请求
export interface RealCostEstimationRequest {
  project_type: string
  location: string
  size_sqm: number
  complexity: 'low' | 'medium' | 'high'
  materials?: Record<string, any>
  timeline_months?: number
  additional_params?: Record<string, any>
}

// 成本估算响应
export interface RealCostEstimationResponse {
  id: string
  project_type: string
  location: string
  size_sqm: number
  estimated_cost: number
  cost_breakdown: {
    materials: number
    labor: number
    equipment: number
    overhead: number
    contingency: number
  }
  confidence: number
  assumptions: string[]
  risks: Array<{
    description: string
    impact: 'low' | 'medium' | 'high'
    probability: number
    mitigation: string
  }>
  timestamp: string
}

// 系统健康状态
export interface SystemHealth {
  status: 'ok' | 'warning' | 'error'
  memory_usage_mb: number
  docker_available: boolean
  version: string
  tenant: string
  services?: Record<string, {
    status: 'ok' | 'warning' | 'error'
    message?: string
  }>
}

// 真实API服务
export const realApiService = {
  // 系统健康检查
  async checkHealth(): Promise<SystemHealth> {
    try {
      return await realApi.get<SystemHealth>('/health')
    } catch (error) {
      console.warn('健康检查失败:', error)
      return {
        status: 'error',
        memory_usage_mb: 0,
        docker_available: false,
        version: 'unknown',
        tenant: 'public'
      }
    }
  },
  
  // 工作流查询
  async sendWorkflowQuery(request: RealWorkflowQueryRequest): Promise<RealWorkflowQueryResponse> {
    try {
      return await realApi.post<RealWorkflowQueryResponse>('/workflow/query', request)
    } catch (error) {
      console.error('工作流查询失败:', error)
      throw error
    }
  },
  
  // 统一查询（RAG查询）
  async sendUnifiedQuery(query: string): Promise<RealWorkflowQueryResponse> {
    try {
      return await realApi.post<RealWorkflowQueryResponse>('/unified/query', { query })
    } catch (error) {
      console.error('统一查询失败:', error)
      throw error
    }
  },
  
  // 文档上传
  async uploadDocument(file: File, metadata?: any): Promise<RealDocumentUploadResponse> {
    try {
      const formData = new FormData()
      formData.append('file', file)
      if (metadata) {
        formData.append('metadata', JSON.stringify(metadata))
      }
      
      const response = await fetch(`${REAL_API_BASE_URL}/documents/upload`, {
        method: 'POST',
        body: formData,
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token') || ''}`
        }
      })
      
      if (!response.ok) {
        throw new ApiError(response.status, '文档上传失败')
      }
      
      return await response.json()
    } catch (error) {
      console.error('文档上传失败:', error)
      throw error
    }
  },
  
  // 获取文档列表
  async getDocuments(): Promise<RealDocumentUploadResponse[]> {
    try {
      return await realApi.get<RealDocumentUploadResponse[]>('/documents')
    } catch (error) {
      console.error('获取文档列表失败:', error)
      return []
    }
  },
  
  // 成本估算
  async estimateCost(request: RealCostEstimationRequest): Promise<RealCostEstimationResponse> {
    try {
      return await realApi.post<RealCostEstimationResponse>('/cost-estimation/predict', request)
    } catch (error) {
      console.error('成本估算失败:', error)
      throw error
    }
  },
  
  // 批量成本估算
  async estimateCostBatch(requests: RealCostEstimationRequest[]): Promise<RealCostEstimationResponse[]> {
    try {
      return await realApi.post<RealCostEstimationResponse[]>('/cost-estimation/predict/batch', requests)
    } catch (error) {
      console.error('批量成本估算失败:', error)
      throw error
    }
  },
  
  // 获取查询历史
  async getQueryHistory(): Promise<RealWorkflowQueryResponse[]> {
    try {
      // 注意：后端可能需要实现这个端点
      return await realApi.get<RealWorkflowQueryResponse[]>('/query/history')
    } catch (error) {
      console.warn('获取查询历史失败，返回模拟数据:', error)
      // 返回模拟数据作为fallback
      return [
        {
          query: '估算一个20层办公楼在多伦多的成本风险',
          response: '基于当前市场数据，20层办公楼在多伦多的成本风险中等偏高...',
          intent: {
            type: 'cost_estimation',
            confidence: 0.92,
            description: '成本估算查询'
          },
          timestamp: new Date().toISOString(),
          confidence: 0.91
        },
        {
          query: '医疗医院项目成本超支的可能原因有哪些？',
          response: '医疗医院项目成本超支的主要原因包括：1. 设计变更 2. 材料价格上涨...',
          intent: {
            type: 'risk_analysis',
            confidence: 0.88,
            description: '风险分析查询'
          },
          timestamp: new Date(Date.now() - 86400000).toISOString(), // 1天前
          confidence: 0.87
        }
      ]
    }
  },
  
  // 获取可用模型
  async getAvailableModels(): Promise<string[]> {
    try {
      return await realApi.get<string[]>('/query/models')
    } catch (error) {
      console.warn('获取模型列表失败:', error)
      return ['gpt-4', 'claude-3', 'gemini-pro']
    }
  },
  
  // 切换模型
  async switchModel(model: string): Promise<{ success: boolean; message: string }> {
    try {
      return await realApi.post<{ success: boolean; message: string }>('/query/switch-model', { model })
    } catch (error) {
      console.error('切换模型失败:', error)
      throw error
    }
  }
}

// 混合API客户端 - 优先使用真实API，失败时回退到模拟API
export const createHybridApiClient = (mockApi: any) => {
  return {
    // 工作流查询 - 优先真实API
    async sendWorkflowQuery(request: RealWorkflowQueryRequest): Promise<RealWorkflowQueryResponse> {
      try {
        console.log('尝试使用真实API进行工作流查询...')
        const health = await realApiService.checkHealth()
        if (health.status === 'ok') {
          return await realApiService.sendWorkflowQuery(request)
        }
      } catch (error) {
        console.log('真实API失败，使用模拟API:', error)
      }
      
      // 回退到模拟API
      return mockApi.sendQuery(request)
    },
    
    // 文档上传 - 优先真实API
    async uploadDocument(file: File, metadata?: any): Promise<RealDocumentUploadResponse> {
      try {
        console.log('尝试使用真实API上传文档...')
        const health = await realApiService.checkHealth()
        if (health.status === 'ok') {
          return await realApiService.uploadDocument(file, metadata)
        }
      } catch (error) {
        console.log('真实API失败，使用模拟API:', error)
      }
      
      // 回退到模拟API
      return mockApi.uploadDocument(file, metadata)
    },
    
    // 成本估算 - 优先真实API
    async estimateCost(request: RealCostEstimationRequest): Promise<RealCostEstimationResponse> {
      try {
        console.log('尝试使用真实API进行成本估算...')
        const health = await realApiService.checkHealth()
        if (health.status === 'ok') {
          return await realApiService.estimateCost(request)
        }
      } catch (error) {
        console.log('真实API失败，使用模拟API:', error)
      }
      
      // 回退到模拟API
      return mockApi.estimateCost(request)
    },
    
    // 其他方法...
    async getQueryHistory() {
      try {
        return await realApiService.getQueryHistory()
      } catch (error) {
        return mockApi.getQueryHistory()
      }
    },
    
    async getDocuments() {
      try {
        return await realApiService.getDocuments()
      } catch (error) {
        return mockApi.getDocuments()
      }
    },
    
    async getAvailableModels() {
      try {
        return await realApiService.getAvailableModels()
      } catch (error) {
        return mockApi.getAvailableModels()
      }
    }
  }
}

export default {
  realApi,
  realApiService,
  createHybridApiClient
}