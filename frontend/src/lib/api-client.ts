// Unified frontend API client aligned with backend contracts.

const API_TIMEOUT = 30000
const BACKEND_PROXY_PREFIX = '/api/backend'
const WORKFLOW_QUERY_TIMEOUT = resolveTimeoutMs(
  process.env.NEXT_PUBLIC_WORKFLOW_QUERY_TIMEOUT_MS,
  240000,
)
const DATA_ANALYSIS_TIMEOUT = resolveTimeoutMs(
  process.env.NEXT_PUBLIC_DATA_ANALYSIS_TIMEOUT_MS,
  120000,
)

function resolveTimeoutMs(value: string | number | undefined, fallback: number): number {
  const parsed = Number(value)
  if (!Number.isFinite(parsed) || parsed <= 0) {
    return fallback
  }
  return Math.floor(parsed)
}

export type RouteMode = 'local_only' | 'hybrid_auto' | 'cloud_only'

export interface RuntimeAppConfig {
  apiKey?: string
  tenantId?: string
  userId?: string
  routeMode?: RouteMode
}

export class ApiError extends Error {
  constructor(
    public status: number,
    public message: string,
    public data?: unknown,
  ) {
    super(message)
    this.name = 'ApiError'
  }
}

function getStoredToken(): string {
  if (typeof window === 'undefined') {
    return ''
  }
  return localStorage.getItem('token') || localStorage.getItem('industry-aiflow-token') || ''
}

function buildRuntimeHeaders(config: RuntimeAppConfig = {}, extraHeaders?: HeadersInit): Headers {
  const headers = new Headers(extraHeaders || {})
  if (config.apiKey) {
    headers.set('x-api-key', config.apiKey)
  }
  if (config.tenantId) {
    headers.set('x-tenant-id', config.tenantId)
  }

  const token = getStoredToken()
  if (token && !headers.has('Authorization')) {
    headers.set('Authorization', `Bearer ${token}`)
  }

  return headers
}

async function parseError(response: Response): Promise<string> {
  try {
    const payload = await response.json()
    const detail = payload?.detail
    if (typeof detail === 'string') {
      return detail
    }
    if (detail && typeof detail === 'object') {
      if (typeof detail.message === 'string') {
        return detail.message
      }
      return JSON.stringify(detail)
    }
    if (typeof payload?.message === 'string') {
      return payload.message
    }
    return JSON.stringify(payload)
  } catch {
    return (await response.text()) || response.statusText
  }
}

async function parseResponse<T>(response: Response): Promise<T> {
  const contentType = response.headers.get('content-type') || ''
  if (contentType.includes('application/json')) {
    return (await response.json()) as T
  }
  return (await response.text()) as T
}

async function requestBackend<T>(
  path: string,
  options: {
    method?: 'GET' | 'POST' | 'PUT' | 'PATCH' | 'DELETE'
    config?: RuntimeAppConfig
    body?: unknown
    formData?: FormData
    headers?: HeadersInit
    timeoutMs?: number
  } = {},
): Promise<T> {
  const controller = new AbortController()
  const effectiveTimeout = resolveTimeoutMs(options.timeoutMs, API_TIMEOUT)
  const timeoutId = setTimeout(() => controller.abort(), effectiveTimeout)

  try {
    const { method = 'GET', config = {}, body, formData, headers: extraHeaders } = options
    const headers = buildRuntimeHeaders(config, extraHeaders)

    let payload: BodyInit | undefined
    if (formData) {
      payload = formData
    } else if (body !== undefined) {
      headers.set('Content-Type', 'application/json')
      payload = JSON.stringify(body)
    }

    const response = await fetch(`${BACKEND_PROXY_PREFIX}${path}`, {
      method,
      headers,
      body: payload,
      signal: controller.signal,
    })

    if (!response.ok) {
      throw new ApiError(response.status, await parseError(response))
    }

    return await parseResponse<T>(response)
  } catch (error) {
    if (error instanceof ApiError) {
      throw error
    }
    if (error instanceof Error && error.name === 'AbortError') {
      throw new ApiError(408, 'Request timeout')
    }
    throw new ApiError(500, 'Network error')
  } finally {
    clearTimeout(timeoutId)
  }
}

// Legacy API adapter (kept for existing imports)
export const api = {
  get<T>(endpoint: string, config?: RuntimeAppConfig) {
    return requestBackend<T>(`/api/v1${endpoint}`, { method: 'GET', config })
  },
  post<T>(endpoint: string, data?: unknown, config?: RuntimeAppConfig) {
    return requestBackend<T>(`/api/v1${endpoint}`, { method: 'POST', body: data, config })
  },
  put<T>(endpoint: string, data?: unknown, config?: RuntimeAppConfig) {
    return requestBackend<T>(`/api/v1${endpoint}`, { method: 'PUT', body: data, config })
  },
  delete<T>(endpoint: string, config?: RuntimeAppConfig) {
    return requestBackend<T>(`/api/v1${endpoint}`, { method: 'DELETE', config })
  },
  upload<T>(endpoint: string, formData: FormData, config?: RuntimeAppConfig) {
    return requestBackend<T>(`/api/v1${endpoint}`, { method: 'POST', formData, config })
  },
}

interface AuthUser {
  id: string
  name: string
  email: string
  roles: string[]
}

interface AuthResponse {
  token: string
  user: AuthUser
}

export const authApi = {
  async login(email: string, password: string): Promise<AuthResponse> {
    return requestBackend<AuthResponse>('/api/v1/auth/login', {
      method: 'POST',
      body: { email, password },
    })
  },

  async register(name: string, email: string, password: string): Promise<AuthResponse> {
    return requestBackend<AuthResponse>('/api/v1/auth/register', {
      method: 'POST',
      body: { name, email, password },
    })
  },

  async logout(): Promise<{ success: boolean }> {
    return requestBackend<{ success: boolean }>('/api/v1/auth/logout', {
      method: 'POST',
    })
  },

  async getCurrentUser(): Promise<AuthUser> {
    return requestBackend<AuthUser>('/api/v1/auth/me', {
      method: 'GET',
    })
  },
}

export const queryApi = {
  async sendQuery(query: string): Promise<{
    id: string
    query: string
    response: string
    timestamp: string
    confidence: number
  }> {
    const payload = await requestBackend<{
      query_id: string
      question: string
      answer: string
      latency_ms?: number
    }>('/api/v1/query', {
      method: 'POST',
      body: { question: query },
      timeoutMs: WORKFLOW_QUERY_TIMEOUT,
    })

    return {
      id: payload.query_id,
      query: payload.question,
      response: payload.answer,
      timestamp: new Date().toISOString(),
      confidence: 1,
    }
  },

  async getQueryHistory(): Promise<Array<Record<string, unknown>>> {
    // Backend does not expose query history endpoint yet.
    return []
  },
}

export const documentApi = {
  async uploadDocuments(files: File[], config: RuntimeAppConfig = {}) {
    const uploaded = [] as Array<{
      id: string
      name: string
      type: string
      size: string
      uploadedAt: string
      status: 'processing' | 'processed' | 'error'
    }>

    for (const file of files) {
      const formData = new FormData()
      formData.append('file', file)

      const payload = await requestBackend<{
        sanitized_filename?: string
        filename?: string
        file_path?: string
        size?: number
      }>('/api/v1/documents/upload', {
        method: 'POST',
        config,
        formData,
      })

      uploaded.push({
        id: payload.file_path || `${Date.now()}-${file.name}`,
        name: payload.sanitized_filename || payload.filename || file.name,
        type: (file.name.split('.').pop() || '').toUpperCase() || 'FILE',
        size: `${((payload.size ?? file.size) / 1024 / 1024).toFixed(2)} MB`,
        uploadedAt: new Date().toISOString(),
        status: 'processed',
      })
    }

    return {
      success: true,
      message: `Uploaded ${uploaded.length} file(s)`,
      documents: uploaded,
    }
  },

  async getDocuments(): Promise<Array<Record<string, unknown>>> {
    const payload = await requestBackend<
      Array<Record<string, unknown>> | { documents?: Array<Record<string, unknown>> }
    >('/api/v1/documents', {
      method: 'GET',
    })

    if (Array.isArray(payload)) {
      return payload
    }

    if (payload && Array.isArray(payload.documents)) {
      return payload.documents
    }

    return []
  },

  async deleteDocument(id: string): Promise<{ success: boolean; id: string }> {
    const payload = await requestBackend<{ success?: boolean; message?: string }>(
      `/api/v1/documents/${encodeURIComponent(id)}`,
      { method: 'DELETE' },
    )
    return { success: payload.success !== false, id }
  },

  async getDocumentStatus(id: string): Promise<{ id: string; status: string; progress: number }> {
    return { id, status: 'processed', progress: 100 }
  },
}

export interface CostProjectFeatures {
  project_type: string
  location: string
  sqft: number
  floors: number
  num_units: number
  planned_duration_weeks: number
  estimated_cost_cad: number
  contractor_rating: number
  complexity_score: number
  team_experience_years: number
  num_change_orders: number
  weather_risk_factor: number
  material_volatility: number
  num_subcontractors: number
  budget_pressure: number
  risk_score: number
  risk_score_original?: number
}

export interface CostPrediction {
  predicted_actual_cost_cad: number
  predicted_cost_overrun_pct: number
  prediction_interval_cad: {
    confidence_quantile: number
    lower: number
    upper: number
  }
  estimated_cost_cad: number
  uncertainty: { ape_quantile: number }
  reasonableness: { within_training_range: boolean; flags: string[] }
  unknown_categories: Record<string, string>
  confidence_degraded: boolean
  warning: string | null
}

export interface CostPredictionResponse {
  success: boolean
  prediction: CostPrediction
}

export interface CostBatchPredictionResponse {
  success: boolean
  count: number
  predictions: CostPrediction[]
}

export const costEstimationApi = {
  async predictCost(
    config: RuntimeAppConfig,
    project: CostProjectFeatures,
    confidenceQuantile = 0.9,
  ): Promise<CostPredictionResponse> {
    return requestBackend<CostPredictionResponse>('/api/v1/cost-estimation/predict', {
      method: 'POST',
      config,
      body: {
        project,
        confidence_quantile: confidenceQuantile,
      },
    })
  },

  async predictCostBatch(
    config: RuntimeAppConfig,
    projects: CostProjectFeatures[],
    confidenceQuantile = 0.9,
  ): Promise<CostBatchPredictionResponse> {
    return requestBackend<CostBatchPredictionResponse>('/api/v1/cost-estimation/predict/batch', {
      method: 'POST',
      config,
      body: {
        projects,
        confidence_quantile: confidenceQuantile,
      },
    })
  },
}

export function predictCost(
  config: RuntimeAppConfig,
  project: CostProjectFeatures,
  confidenceQuantile = 0.9,
): Promise<CostPredictionResponse> {
  return costEstimationApi.predictCost(config, project, confidenceQuantile)
}

export function predictCostBatch(
  config: RuntimeAppConfig,
  projects: CostProjectFeatures[],
  confidenceQuantile = 0.9,
): Promise<CostBatchPredictionResponse> {
  return costEstimationApi.predictCostBatch(config, projects, confidenceQuantile)
}

/* What-if scenario analysis */
export interface WhatIfOverride {
  feature: string
  value: number
}

export interface WhatIfResponse {
  success: boolean
  modified_prediction: CostPrediction & {
    shap_contributions?: Array<{
      feature: string
      label: string
      value: number | string
      contribution_pct: number
      direction: string
    }>
    shap_base_rate_pct?: number
    model_info?: Record<string, unknown>
  }
  overrides_applied: WhatIfOverride[]
  warnings: string[]
}

export async function predictWhatIf(
  config: RuntimeAppConfig,
  project: CostProjectFeatures,
  overrides: WhatIfOverride[],
  confidenceQuantile = 0.9,
): Promise<WhatIfResponse> {
  return requestBackend<WhatIfResponse>('/api/v1/cost-estimation/what-if', {
    method: 'POST',
    config,
    body: { project, overrides, confidence_quantile: confidenceQuantile },
  })
}

/* Similar projects lookup */
export interface SimilarProject {
  project_type: string
  location: string
  sqft: number
  estimated_cost_cad: number
  actual_overrun_pct: number
  key_diff: string
  similarity_score: number
}

export interface SimilarProjectsResponse {
  success: boolean
  count: number
  projects: SimilarProject[]
}

export async function findSimilarProjects(
  config: RuntimeAppConfig,
  project: CostProjectFeatures,
  topK = 5,
): Promise<SimilarProjectsResponse> {
  return requestBackend<SimilarProjectsResponse>('/api/v1/cost-estimation/similar', {
    method: 'POST',
    config,
    body: { project, top_k: topK },
  })
}

/* Data transparency */
export interface DataTransparencyResponse {
  available: boolean
  dataset?: { rows: number; source: string; features_numeric: number; features_categorical: number }
  stats?: Record<string, number>
  model_performance?: { overrun_r2: number | null; overrun_mape: number | null; actual_cost_r2: number | null; actual_cost_mape: number | null }
  limitations?: string[]
}

export async function getCostTransparency(
  config: RuntimeAppConfig,
): Promise<DataTransparencyResponse> {
  return requestBackend<DataTransparencyResponse>('/api/v1/cost-estimation/data-transparency', {
    method: 'GET',
    config,
  })
}

export interface WorkflowQueryRequest {
  query: string
  session_id?: string
  thread_id?: string
  context?: string
  file_ids?: string[]
}

export interface WorkflowQueryResponse {
  id: string
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
  }>
  timestamp: string
  confidence: number
  metadata?: Record<string, unknown>
  suggested_questions?: string[]
}

type WorkflowIntentPayload =
  | string
  | {
      type?: string
      confidence?: number
      description?: string
    }

function normalizeWorkflowSources(
  sources: WorkflowQueryResponse['sources'] | undefined,
  metadata: Record<string, unknown> | undefined,
): WorkflowQueryResponse['sources'] {
  const extract = (value: unknown): WorkflowQueryResponse['sources'] => {
    if (!Array.isArray(value)) {
      return undefined
    }

    const normalized = value
      .map((item) => {
        if (!item || typeof item !== 'object') {
          return null
        }

        const source = item as Record<string, unknown>
        const documentId = String(
          source.document_id ?? source.doc_id ?? source.source ?? source.filename ?? '',
        ).trim()
        const documentName = String(
          source.document_name ?? source.filename ?? source.source ?? documentId,
        ).trim()
        if (!documentId && !documentName) {
          return null
        }

        return {
          document_id: documentId || documentName,
          document_name: documentName || documentId,
          relevance: Number(source.relevance ?? source.score ?? 0),
          content: String(source.content ?? source.text ?? ''),
        }
      })
      .filter((item): item is NonNullable<typeof item> => item !== null)

    return normalized.length > 0 ? normalized : undefined
  }

  const direct = extract(sources)
  if (direct) {
    return direct
  }

  const agentExecution =
    metadata && typeof metadata.agent_execution === 'object'
      ? (metadata.agent_execution as Record<string, unknown>)
      : undefined

  return extract(agentExecution?.sources ?? metadata?.sources)
}

function normalizeWorkflowIntent(
  intent: WorkflowIntentPayload | undefined,
  metadata: Record<string, unknown> | undefined,
): WorkflowQueryResponse['intent'] {
  if (!intent) {
    return undefined
  }

  if (typeof intent === 'string') {
    return {
      type: intent,
      confidence: Number(metadata?.intent_confidence ?? 0),
      description: intent,
    }
  }

  const type = String(intent.type || '')
  const confidence = Number(
    intent.confidence ?? metadata?.intent_confidence ?? 0,
  )
  const description = String(intent.description || intent.type || '')

  if (!type && !description) {
    return undefined
  }

  return {
    type: type || description,
    confidence: Number.isFinite(confidence) ? confidence : 0,
    description: description || type,
  }
}

function normalizeSuggestedQuestions(
  metadata: Record<string, unknown> | undefined,
): string[] | undefined {
  const agentExecution =
    metadata && typeof metadata.agent_execution === 'object'
      ? (metadata.agent_execution as Record<string, unknown>)
      : undefined

  const raw = metadata?.suggested_questions ?? agentExecution?.suggested_questions
  if (!Array.isArray(raw)) {
    return undefined
  }
  const normalized = raw
    .map((item) => String(item || '').trim())
    .filter((item) => item.length > 0)
  return normalized.length > 0 ? normalized.slice(0, 5) : undefined
}

export const workflowApi = {
  async sendQuery(
    request: WorkflowQueryRequest,
    config: RuntimeAppConfig = {},
  ): Promise<WorkflowQueryResponse> {
    const payload = await requestBackend<{
      id?: string
      trace_id?: string
      query?: string
      intent?: WorkflowIntentPayload
      response?: string
      sources?: WorkflowQueryResponse['sources']
      timestamp?: string
      confidence?: number
      metadata?: Record<string, unknown>
    }>('/api/v1/workflow/query', {
      method: 'POST',
      config,
      timeoutMs: WORKFLOW_QUERY_TIMEOUT,
      body: {
        query: request.query,
        session_id: request.session_id,
        thread_id: request.thread_id,
        user_id: config.userId,
        route_mode: config.routeMode,
      },
    })

    return {
      id: payload.id || payload.trace_id || `${Date.now()}`,
      query: payload.query || request.query,
      response: payload.response || '',
      intent: normalizeWorkflowIntent(payload.intent, payload.metadata),
      sources: normalizeWorkflowSources(payload.sources, payload.metadata),
      timestamp: payload.timestamp || new Date().toISOString(),
      confidence: Number(
        payload.confidence ?? payload.metadata?.intent_confidence ?? 0,
      ),
      metadata: payload.metadata,
      suggested_questions: normalizeSuggestedQuestions(payload.metadata),
    }
  },

  async getQueryHistory(): Promise<WorkflowQueryResponse[]> {
    return []
  },
}

export interface HealthResponse {
  status: string
  component?: string
  version?: string
  memory_usage_mb?: number
  model?: unknown
}

async function getBackendHealth(path: string, config: RuntimeAppConfig): Promise<HealthResponse> {
  return requestBackend<HealthResponse>(path, {
    method: 'GET',
    config,
  })
}

export async function getPlatformHealth(config: RuntimeAppConfig): Promise<HealthResponse> {
  return getBackendHealth('/api/v1/health', config)
}

export async function getWorkflowHealth(config: RuntimeAppConfig): Promise<HealthResponse> {
  return getBackendHealth('/api/v1/workflow/health', config)
}

export async function getCostHealth(config: RuntimeAppConfig): Promise<HealthResponse> {
  return getBackendHealth('/api/v1/cost-estimation/health', config)
}

export async function previewDataFile(
  config: RuntimeAppConfig,
  dataFile: string,
): Promise<Record<string, unknown>> {
  return requestBackend<Record<string, unknown>>('/api/v1/data/preview', {
    method: 'POST',
    config,
    body: { data_file: dataFile },
  })
}

export async function uploadDataFile(
  config: RuntimeAppConfig,
  file: File,
): Promise<Record<string, unknown>> {
  const formData = new FormData()
  formData.append('file', file)
  return requestBackend<Record<string, unknown>>('/api/v1/data/upload', {
    method: 'POST',
    config,
    formData,
  })
}

export async function runDataAnalysis(
  config: RuntimeAppConfig,
  payload: {
    data_file: string
    analysis_type?: string
    [key: string]: unknown
  },
): Promise<Record<string, unknown>> {
  return requestBackend<Record<string, unknown>>('/api/v1/data/analyze', {
    method: 'POST',
    config,
    body: payload,
    timeoutMs: DATA_ANALYSIS_TIMEOUT,
  })
}

/**
 * Start a streaming data analysis job — returns job_id for SSE subscription.
 */
export async function startDataAnalysisJob(
  config: RuntimeAppConfig,
  payload: {
    data_file: string
    analysis_type?: string
    [key: string]: unknown
  },
): Promise<{ job_id: string }> {
  return requestBackend<{ job_id: string }>('/api/v1/data/analyze/start', {
    method: 'POST',
    config,
    body: payload,
    timeoutMs: 15_000,
  })
}

/**
 * Build the SSE stream URL for a data analysis job.
 * Uses the Next.js backend proxy at /api/backend/.
 */
export function dataAnalysisStreamUrl(_config: RuntimeAppConfig, jobId: string): string {
  return `/api/backend/api/v1/data/analyze/stream/${encodeURIComponent(jobId)}`
}

export async function generateVisualization(
  config: RuntimeAppConfig,
  payload: {
    data_file: string
    chart_type?: string
    [key: string]: unknown
  },
): Promise<Record<string, unknown>> {
  return requestBackend<Record<string, unknown>>('/api/v1/visualization/generate', {
    method: 'POST',
    config,
    body: payload,
    timeoutMs: DATA_ANALYSIS_TIMEOUT,
  })
}

export interface BudgetPolicyRequest {
  monthly_budget_usd: number
  soft_limit_ratio: number
  hard_limit_ratio: number
  policy_mode: 'local_only' | 'block'
}

export interface LlmBudgetResponse {
  tenant_id: string
  policy: BudgetPolicyRequest | null
  current_month_spend_usd: number
  budget_evaluation: Record<string, unknown>
}

export interface LlmUsageResponse {
  [key: string]: unknown
}

export async function getLlmUsage(
  config: RuntimeAppConfig,
  days = 30,
  tenantId?: string,
): Promise<LlmUsageResponse> {
  const query = new URLSearchParams({ days: String(days) })
  if (tenantId) {
    query.set('tenant_id', tenantId)
  }
  return requestBackend<LlmUsageResponse>(`/llm/usage?${query.toString()}`, {
    method: 'GET',
    config,
  })
}

export async function getLlmBudget(
  config: RuntimeAppConfig,
  tenantId: string,
): Promise<LlmBudgetResponse> {
  return requestBackend<LlmBudgetResponse>(`/llm/budget/${encodeURIComponent(tenantId)}`, {
    method: 'GET',
    config,
  })
}

export async function updateLlmBudget(
  config: RuntimeAppConfig,
  tenantId: string,
  policy: BudgetPolicyRequest,
): Promise<{ success: boolean; policy: BudgetPolicyRequest }> {
  return requestBackend<{ success: boolean; policy: BudgetPolicyRequest }>(
    `/llm/budget/${encodeURIComponent(tenantId)}`,
    {
      method: 'POST',
      config,
      body: policy,
    },
  )
}

export async function getPromptMetrics(
  config: RuntimeAppConfig,
  params: { days?: number; category?: string; top_limit?: number } = {},
): Promise<Record<string, unknown>> {
  const query = new URLSearchParams()
  if (params.days) query.set('days', String(params.days))
  if (params.category) query.set('category', params.category)
  if (params.top_limit) query.set('top_limit', String(params.top_limit))
  const suffix = query.toString() ? `?${query.toString()}` : ''
  return requestBackend<Record<string, unknown>>(`/api/prompts/metrics/summary${suffix}`, {
    method: 'GET',
    config,
  })
}

export async function listPrompts(
  config: RuntimeAppConfig,
  params: { page?: number; size?: number; category?: string } = {},
): Promise<Record<string, unknown>> {
  const query = new URLSearchParams()
  if (params.page) query.set('page', String(params.page))
  if (params.size) query.set('size', String(params.size))
  if (params.category) query.set('category', params.category)
  const suffix = query.toString() ? `?${query.toString()}` : ''
  return requestBackend<Record<string, unknown>>(`/api/prompts/${suffix}`, {
    method: 'GET',
    config,
  })
}

export const dashboardApi = {
  async getDocumentStats(): Promise<Record<string, unknown>> {
    return requestBackend<Record<string, unknown>>('/api/v1/documents/statistics', {
      method: 'GET',
    })
  },

  async getHealth(): Promise<Record<string, unknown>> {
    return requestBackend<Record<string, unknown>>('/api/v1/health', { method: 'GET' })
  },

  async getLlmUsage(days = 30): Promise<Record<string, unknown>> {
    return requestBackend<Record<string, unknown>>(`/llm/usage?days=${days}`, {
      method: 'GET',
    })
  },

  async getOperationsLog(limit = 10): Promise<Record<string, unknown>> {
    return requestBackend<Record<string, unknown>>(
      `/api/v1/documents/operations/log?limit=${limit}`,
      { method: 'GET' },
    )
  },

  async getCostEstimationHealth(): Promise<Record<string, unknown>> {
    return requestBackend<Record<string, unknown>>('/api/v1/cost-estimation/health', {
      method: 'GET',
    })
  },

  async getFeedbackStats(days = 30): Promise<Record<string, unknown>> {
    return requestBackend<Record<string, unknown>>(`/api/v1/feedback/statistics?days=${days}`, {
      method: 'GET',
    })
  },

  async getWorkflowStats(): Promise<Record<string, unknown>> {
    return requestBackend<Record<string, unknown>>('/api/intent/stats/workflow', {
      method: 'GET',
    })
  },
}

export interface DemoModeState {
  mode: 'live_hybrid' | 'local_safe' | 'scripted_replay'
  allow_cloud_override: boolean
  profile?: Record<string, unknown>
}

export async function getDemoMode(config: RuntimeAppConfig): Promise<DemoModeState> {
  return requestBackend<DemoModeState>('/api/v1/demo/mode', {
    method: 'GET',
    config,
  })
}

export async function updateDemoMode(
  config: RuntimeAppConfig,
  payload: {
    mode: 'live_hybrid' | 'local_safe' | 'scripted_replay'
    allow_cloud_override: boolean
  },
): Promise<DemoModeState> {
  return requestBackend<DemoModeState>('/api/v1/demo/mode', {
    method: 'POST',
    config,
    body: payload,
  })
}

// Real/hybrid clients (legacy compatibility)
import { createHybridApiClient, realApiService } from './real-api-client'

const hybridWorkflowApi = createHybridApiClient(workflowApi)
const hybridDocumentApi = createHybridApiClient(documentApi)
const hybridCostEstimationApi = createHybridApiClient(costEstimationApi)

// ── Intent Classification API ─────────────────────────────────────

export interface IntentClassifyRequest {
  query: string
  session_id: string
  user_id?: string
  context?: Record<string, unknown>
}

export interface NodeTraceEntry {
  node_name: string
  start_ms: number
  end_ms: number
  duration_ms: number
  decision: string
  metadata: Record<string, unknown>
}

export interface CapabilityScore {
  score: number
  confidence: number
  matched_keywords: string[]
  penalized: boolean
}

export interface IntentClassifyResponse {
  success: boolean
  intent: string | null
  confidence: number | null
  reasoning: string | null
  routing_decision: Record<string, unknown> | null
  agent_response: string | null
  clarification_needed: boolean
  clarification_message: string | null
  processing_time_ms: number | null
  metadata: Record<string, unknown>
  node_trace: NodeTraceEntry[]
  capability_scores: Record<string, CapabilityScore> | null
  matched_keywords: Array<[string, string]> | null
  error: string | null
}

export interface CapabilityCatalog {
  capabilities: Array<{
    id: string
    name: string
    description: string
    example_queries: string[]
    parameters: Record<string, unknown>
    enabled: boolean
  }>
  version: string
  total: number
}

export const intentApi = {
  async classify(
    request: IntentClassifyRequest,
    config: RuntimeAppConfig = {},
  ): Promise<IntentClassifyResponse> {
    return requestBackend<IntentClassifyResponse>('/api/intent/classify', {
      method: 'POST',
      config,
      body: request,
      timeoutMs: 90_000,
    })
  },

  async getCapabilities(
    config: RuntimeAppConfig = {},
  ): Promise<CapabilityCatalog> {
    return requestBackend<CapabilityCatalog>('/api/intent/capabilities', {
      method: 'GET',
      config,
    })
  },
}

export { realApiService, hybridWorkflowApi, hybridDocumentApi, hybridCostEstimationApi }

export default {
  api,
  authApi,
  queryApi,
  documentApi,
  costEstimationApi,
  workflowApi,
  intentApi,
  realApiService,
  hybridWorkflowApi,
  hybridDocumentApi,
  hybridCostEstimationApi,
}
