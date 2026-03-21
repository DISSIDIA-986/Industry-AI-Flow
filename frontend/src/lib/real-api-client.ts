// real backendAPIclient
// for integrating actualFastAPIBackend services

class RealApiError extends Error {
  constructor(
    public status: number,
    public message: string,
  ) {
    super(message)
    this.name = 'RealApiError'
  }
}

function isTransientDocumentListError(error: unknown): boolean {
  if (!(error instanceof RealApiError)) {
    return false
  }
  // Proxy/network outages should not break document screens.
  return [404, 408, 500, 502, 503, 504].includes(error.status)
}

// realityAPIConfiguration (unify the front-end homologous proxy to avoid environment drift caused by direct connection to the back-end)
const REAL_API_BASE_URL = '/api/backend/api/v1'
const REAL_API_TIMEOUT = 60000 // 60seconds timeout (AIQuery may take longer)
const ALLOW_SYNTHETIC_REAL_API_FALLBACK =
  process.env.NEXT_PUBLIC_ALLOW_SYNTHETIC_REAL_API_FALLBACK === 'true'
const ALLOW_HYBRID_MOCK_FALLBACK =
  process.env.NEXT_PUBLIC_ALLOW_HYBRID_MOCK_FALLBACK === 'true'

function assertBackendHealthy(health: SystemHealth): void {
  if (health.status !== 'ok') {
    throw new RealApiError(503, 'Backend service is unavailable')
  }
}

function shouldFallbackToSyntheticData(): boolean {
  return ALLOW_SYNTHETIC_REAL_API_FALLBACK
}

function shouldFallbackToMockApi(): boolean {
  return ALLOW_HYBRID_MOCK_FALLBACK
}

// create realityAPIclient
const createRealApiClient = () => {
  const client = {
    async request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
      const url = `${REAL_API_BASE_URL}${endpoint}`
      const token = localStorage.getItem('token')
      
      const headers = new Headers(options.headers)
      if (!headers.has('Content-Type')) {
        headers.set('Content-Type', 'application/json')
      }
      
      if (token) {
        headers.set('Authorization', `Bearer ${token}`)
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
          throw new RealApiError(response.status, errorData.detail || response.statusText)
        }
        
        return await response.json()
      } catch (error) {
        clearTimeout(timeoutId)
        if (error instanceof RealApiError) {
          throw error
        }
        if (error instanceof Error && error.name === 'AbortError') {
          throw new RealApiError(408, 'Request timed out, please try again later')
        }
        throw new RealApiError(500, 'Network error, please check network connection')
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

// realityAPIClient instance
export const realApi = createRealApiClient()

// realityAPItype definition

// Workflow query request
export interface RealWorkflowQueryRequest {
  query: string
  context?: string
  file_ids?: string[]
  model?: string
  temperature?: number
  max_tokens?: number
}

// Workflow query response
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

// Document upload request
export interface RealDocumentUploadRequest {
  file: File
  metadata?: {
    title?: string
    description?: string
    tags?: string[]
    category?: string
  }
}

// Document upload response
export interface RealDocumentUploadResponse {
  id: string
  doc_id?: string
  filename: string
  title: string
  size: number
  mime_type: string
  upload_time: string
  status: 'pending' | 'processing' | 'completed' | 'failed'
  metadata?: Record<string, any>
}

// Document list response is more permissive because backend can return either
// uploaded metadata rows or indexed vectorstore fallback rows.
export interface RealDocumentListResponse {
  id: string
  filename?: string
  name?: string
  size?: number
  upload_time?: string
  uploaded_at?: string
  status?: 'pending' | 'processing' | 'completed' | 'failed' | 'processed' | 'missing' | 'deleted'
  type?: string
  source?: 'uploaded_index' | 'vector_index' | string
  chunk_count?: number
  mime_type?: string
  title?: string
  metadata?: Record<string, any>
  [key: string]: unknown
}

// Cost estimate request
export interface RealCostEstimationRequest {
  project_type: string
  location: string
  size_sqm: number
  complexity: 'low' | 'medium' | 'high'
  materials?: Record<string, any>
  timeline_months?: number
  additional_params?: Record<string, any>
}

// cost estimate response
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

// System health status
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

// realityAPIServe
export const realApiService = {
  // System health check
  async checkHealth(): Promise<SystemHealth> {
    try {
      const response = await fetch('/api/backend/api/v1/health', {
        method: 'GET',
      })
      if (!response.ok) {
        throw new RealApiError(response.status, response.statusText)
      }
      return await response.json()
    } catch (error) {
      console.warn('Health check failed:', error)
      return {
        status: 'error',
        memory_usage_mb: 0,
        docker_available: false,
        version: 'unknown',
        tenant: 'public'
      }
    }
  },
  
  // Workflow query
  async sendWorkflowQuery(request: RealWorkflowQueryRequest): Promise<RealWorkflowQueryResponse> {
    try {
      return await realApi.post<RealWorkflowQueryResponse>('/workflow/query', request)
    } catch (error) {
      console.error('Workflow query failed:', error)
      throw error
    }
  },
  
  // Unified query (RAGQuery)
  async sendUnifiedQuery(query: string): Promise<RealWorkflowQueryResponse> {
    try {
      return await realApi.post<RealWorkflowQueryResponse>('/unified/query', { query })
    } catch (error) {
      console.error('Unified query failed:', error)
      throw error
    }
  },
  
  // Document upload
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
        throw new RealApiError(response.status, 'Document upload failed')
      }
      
      return await response.json()
    } catch (error) {
      console.error('Document upload failed:', error)
      throw error
    }
  },
  
  // Get document list
  async getDocuments(): Promise<RealDocumentListResponse[]> {
    try {
      return await realApi.get<RealDocumentListResponse[]>('/documents')
    } catch (error) {
      if (shouldFallbackToSyntheticData()) {
        console.warn('Failed to get the list of documents, returning an empty list (explicitly enabled fallback):', error)
        return []
      }
      if (isTransientDocumentListError(error)) {
        console.warn('Document list endpoint temporarily unavailable; returning empty list:', error)
        return []
      }
      console.error('Failed to get document list:', error)
      throw error instanceof RealApiError
        ? error
        : new RealApiError(503, 'Failed to get document list')
    }
  },

  // Delete document
  async deleteDocument(id: string): Promise<{ success: boolean; message?: string }> {
    return await realApi.delete<{ success: boolean; message?: string }>(
      `/documents/${encodeURIComponent(id)}`
    )
  },
  
  // cost estimate
  async estimateCost(request: RealCostEstimationRequest): Promise<RealCostEstimationResponse> {
    try {
      return await realApi.post<RealCostEstimationResponse>('/cost-estimation/predict', request)
    } catch (error) {
      console.error('Cost estimate failed:', error)
      throw error
    }
  },
  
  // Batch Cost Estimation
  async estimateCostBatch(requests: RealCostEstimationRequest[]): Promise<RealCostEstimationResponse[]> {
    try {
      return await realApi.post<RealCostEstimationResponse[]>('/cost-estimation/predict/batch', requests)
    } catch (error) {
      console.error('Batch cost estimation failed:', error)
      throw error
    }
  },
  
  // Get query history
  async getQueryHistory(): Promise<RealWorkflowQueryResponse[]> {
    try {
      // NOTE: The backend may need to implement this endpoint
      return await realApi.get<RealWorkflowQueryResponse[]>('/query/history')
    } catch (error) {
      if (shouldFallbackToSyntheticData()) {
        console.warn('Failed to get query history using sample data (explicitly enabledfallback）:', error)
        return [
          {
            query: 'Estimating the cost risk of a 20-story office building in Toronto',
            response: 'Based on current market data, the cost risk of a 20-story office building in Toronto is moderate to high....',
            intent: {
              type: 'cost_estimation',
              confidence: 0.92,
              description: 'Cost estimate inquiry'
            },
            timestamp: new Date().toISOString(),
            confidence: 0.91
          },
          {
            query: 'What are the possible causes of cost overruns on medical hospital projects?',
            response: 'The main causes of cost overruns in medical hospital projects include: 1. Design changes 2. Material prices rise...',
            intent: {
              type: 'risk_analysis',
              confidence: 0.88,
              description: 'Risk analysis query'
            },
            timestamp: new Date(Date.now() - 86400000).toISOString(), // 1days ago
            confidence: 0.87
          }
        ]
      }
      console.warn('Failed to obtain query history, not enabledfallback，Return an explicit error:', error)
      throw new RealApiError(503, 'Query history interface is unavailable')
    }
  },
  
  // Get available models
  async getAvailableModels(): Promise<string[]> {
    try {
      return await realApi.get<string[]>('/query/models')
    } catch (error) {
      if (shouldFallbackToSyntheticData()) {
        console.warn('Failed to get list of models, using sample model (explicitly enabledfallback）:', error)
        return ['gpt-4', 'claude-3', 'gemini-pro']
      }
      console.warn('Failed to get model list, not enabledfallback，Return an explicit error:', error)
      throw new RealApiError(503, 'Model list interface is not available')
    }
  },
  
  // Switch model
  async switchModel(model: string): Promise<{ success: boolean; message: string }> {
    try {
      return await realApi.post<{ success: boolean; message: string }>('/query/switch-model', { model })
    } catch (error) {
      console.error('Failed to switch model:', error)
      throw error
    }
  }
}

// mixAPIclient - Prioritize the use of realAPI，Fallback to simulation on failureAPI
export const createHybridApiClient = (mockApi: any) => {
  return {
    // Workflow query - Prioritize truthAPI
    async sendWorkflowQuery(request: RealWorkflowQueryRequest): Promise<RealWorkflowQueryResponse> {
      try {
        console.log('try to use realAPIMake workflow queries...')
        const health = await realApiService.checkHealth()
        assertBackendHealthy(health)
        return await realApiService.sendWorkflowQuery(request)
      } catch (error) {
        console.warn('realityAPIfail:', error)
        if (shouldFallbackToMockApi()) {
          console.warn('Blending enabledfallback，fallback to simulationAPI')
          return mockApi.sendQuery(request)
        }
        throw error instanceof Error
          ? error
          : new RealApiError(500, 'Workflow query failed')
      }
    },
    
    // Document upload - Prioritize truthAPI
    async uploadDocument(file: File, metadata?: any): Promise<RealDocumentUploadResponse> {
      try {
        console.log('try to use realAPIUpload documents...')
        const health = await realApiService.checkHealth()
        assertBackendHealthy(health)
        return await realApiService.uploadDocument(file, metadata)
      } catch (error) {
        console.warn('realityAPIfail:', error)
        if (shouldFallbackToMockApi()) {
          console.warn('Blending enabledfallback，fallback to simulationAPI')
          return mockApi.uploadDocument(file, metadata)
        }
        throw error instanceof Error
          ? error
          : new RealApiError(500, 'Document upload failed')
      }
    },
    
    // cost estimate - Prioritize truthAPI
    async estimateCost(request: RealCostEstimationRequest): Promise<RealCostEstimationResponse> {
      try {
        console.log('try to use realAPIMake a cost estimate...')
        const health = await realApiService.checkHealth()
        assertBackendHealthy(health)
        return await realApiService.estimateCost(request)
      } catch (error) {
        console.warn('realityAPIfail:', error)
        if (shouldFallbackToMockApi()) {
          console.warn('Blending enabledfallback，fallback to simulationAPI')
          return mockApi.estimateCost(request)
        }
        throw error instanceof Error
          ? error
          : new RealApiError(500, 'Cost estimate failed')
      }
    },
    
    // Other methods...
    async getQueryHistory() {
      try {
        return await realApiService.getQueryHistory()
      } catch (error) {
        if (shouldFallbackToMockApi()) {
          return mockApi.getQueryHistory()
        }
        throw error
      }
    },
    
    async getDocuments() {
      try {
        return await realApiService.getDocuments()
      } catch (error) {
        if (shouldFallbackToMockApi()) {
          return mockApi.getDocuments()
        }
        throw error
      }
    },
    
    async getAvailableModels() {
      try {
        return await realApiService.getAvailableModels()
      } catch (error) {
        if (shouldFallbackToMockApi()) {
          return mockApi.getAvailableModels()
        }
        throw error
      }
    }
  }
}

export default {
  realApi,
  realApiService,
  createHybridApiClient
}
