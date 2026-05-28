'use client'

import { useState, useEffect, useCallback } from 'react'
import { dashboardApi } from '@/lib/api-client'

// --- Types ---

type HealthStatus = 'healthy' | 'degraded' | 'unhealthy' | 'loading'

interface ModuleHealth {
  status: HealthStatus
  metrics: Record<string, unknown>
  detail: string
}

interface SystemBannerData {
  status: HealthStatus
  memoryMb: number
  docker: boolean
  embedding: boolean
  llmModel: string
  modulesOnline: number
}

// --- SVG Icon Paths (reused from PipelineFlowViz) ---

const MODULE_ICONS: Record<string, string> = {
  intent:
    'M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z',
  rag: 'M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z',
  cost: 'M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z',
  data: 'M10 20l4-16m4 4l4 4-4 4M6 16l-4-4 4-4',
}

const MODULE_COLORS: Record<string, { border: string; bg: string; text: string }> = {
  intent: { border: 'border-l-blue-600', bg: 'bg-blue-50', text: 'text-blue-600' },
  rag: { border: 'border-l-green-600', bg: 'bg-green-50', text: 'text-green-600' },
  cost: { border: 'border-l-amber-500', bg: 'bg-amber-50', text: 'text-amber-600' },
  data: { border: 'border-l-purple-600', bg: 'bg-purple-50', text: 'text-purple-600' },
}

// --- Health Badge ---

function HealthBadge({ status }: { status: HealthStatus }) {
  const config = {
    healthy: { dot: 'bg-green-600', bg: 'bg-green-50', text: 'text-green-700', label: 'Healthy' },
    degraded: { dot: 'bg-amber-500', bg: 'bg-amber-50', text: 'text-amber-700', label: 'Degraded' },
    unhealthy: { dot: 'bg-red-600', bg: 'bg-red-50', text: 'text-red-700', label: 'Unavailable' },
    loading: { dot: 'bg-gray-400', bg: 'bg-gray-50', text: 'text-gray-500', label: 'Loading...' },
  }
  const c = config[status]
  return (
    <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium ${c.bg} ${c.text}`}>
      <span className={`w-2 h-2 rounded-full ${c.dot}`} />
      {c.label}
    </span>
  )
}

// --- Module Card (DRY component) ---

interface ModuleCardProps {
  moduleKey: string
  title: string
  subtitle: string
  health: ModuleHealth
  heroLabel: string
  heroValue: string
  metrics: Array<{ label: string; value: string; detail?: string }>
  children?: React.ReactNode
}

function ModuleCard({ moduleKey, title, subtitle, health, heroLabel, heroValue, metrics, children }: ModuleCardProps) {
  const colors = MODULE_COLORS[moduleKey]
  const iconPath = MODULE_ICONS[moduleKey]

  return (
    <div
      className={`bg-white rounded-xl shadow-sm border border-gray-200 border-l-4 ${colors.border} p-5 transition-shadow hover:shadow-md`}
      role="article"
      aria-label={`${title} Status`}
      tabIndex={0}
    >
      {/* Header */}
      <div className="flex items-center justify-between mb-4 pb-3 border-b border-gray-100">
        <div className="flex items-center gap-2.5">
          <div className={`w-8 h-8 rounded-lg ${colors.bg} flex items-center justify-center`}>
            <svg className={`w-4.5 h-4.5 ${colors.text}`} fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" d={iconPath} />
            </svg>
          </div>
          <div>
            <div className="text-sm font-semibold text-gray-900">{title}</div>
            <div className="text-xs text-gray-500">{subtitle}</div>
          </div>
        </div>
        <HealthBadge status={health.status} />
      </div>

      {/* Hero Metric */}
      <div className="mb-4">
        <div className="text-xs font-medium text-gray-500 uppercase tracking-wider">{heroLabel}</div>
        <div className="text-3xl font-bold text-gray-900 font-mono mt-0.5">{heroValue}</div>
      </div>

      {/* Supporting Metrics Grid */}
      <div className="grid grid-cols-2 gap-3">
        {metrics.map((m) => (
          <div key={m.label}>
            <div className="text-xs font-medium text-gray-500 uppercase tracking-wider">{m.label}</div>
            <div className="text-lg font-bold text-gray-900 font-mono mt-0.5">{m.value}</div>
            {m.detail && <div className="text-xs text-gray-400">{m.detail}</div>}
          </div>
        ))}
      </div>

      {/* Optional extra content (agent bar, doc types) */}
      {children}
    </div>
  )
}

// --- Agent Distribution Bar ---

function AgentDistributionBar({ rates }: { rates: Record<string, number> }) {
  const rag = Math.round((rates.rag || 0) * 100)
  const code = Math.round((rates.code_execution || rates.data_analysis || 0) * 100)
  const cost = Math.round((rates.cost_estimation || 0) * 100)

  if (rag + code + cost === 0) return null

  return (
    <div className="mt-4">
      <div className="text-xs font-medium text-gray-500 uppercase tracking-wider mb-1.5">Agent Distribution</div>
      <div className="flex h-1.5 rounded-full overflow-hidden bg-gray-100" role="img" aria-label={`RAG ${rag}%, Code ${code}%, Cost ${cost}%`}>
        {rag > 0 && <div className="bg-blue-600 transition-all" style={{ width: `${rag}%` }} />}
        {code > 0 && <div className="bg-purple-600 transition-all" style={{ width: `${code}%` }} />}
        {cost > 0 && <div className="bg-amber-500 transition-all" style={{ width: `${cost}%` }} />}
      </div>
      <div className="flex gap-3 mt-1.5 text-xs text-gray-500">
        {rag > 0 && <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-sm bg-blue-600" />RAG {rag}%</span>}
        {code > 0 && <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-sm bg-purple-600" />Code {code}%</span>}
        {cost > 0 && <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-sm bg-amber-500" />Cost {cost}%</span>}
      </div>
    </div>
  )
}

// --- Doc Type Tags ---

function DocTypeTags({ docs }: { docs: Record<string, unknown> }) {
  const byType = (docs.by_type || {}) as Record<string, number>
  const entries = Object.entries(byType).sort(([, a], [, b]) => b - a).slice(0, 4)
  if (entries.length === 0) return null

  return (
    <div className="mt-4">
      <div className="text-xs font-medium text-gray-500 uppercase tracking-wider mb-1.5">Document Types</div>
      <div className="flex gap-1.5 flex-wrap">
        {entries.map(([type, count]) => (
          <span key={type} className="inline-flex items-center gap-1 px-2 py-0.5 bg-gray-100 rounded text-xs text-gray-700">
            {type.toUpperCase()} <span className="font-mono font-semibold">{count}</span>
          </span>
        ))}
      </div>
    </div>
  )
}

// --- Main Page ---

export default function SystemOverviewPage() {
  const [loading, setLoading] = useState(true)
  const [banner, setBanner] = useState<SystemBannerData>({
    status: 'loading', memoryMb: 0, docker: false, embedding: false, llmModel: '—', modulesOnline: 0,
  })
  const [intentHealth, setIntentHealth] = useState<ModuleHealth>({ status: 'loading', metrics: {}, detail: '' })
  const [ragHealth, setRagHealth] = useState<ModuleHealth>({ status: 'loading', metrics: {}, detail: '' })
  const [costHealth, setCostHealth] = useState<ModuleHealth>({ status: 'loading', metrics: {}, detail: '' })
  const [dataHealth, setDataHealth] = useState<ModuleHealth>({ status: 'loading', metrics: {}, detail: '' })

  // Raw data for visual elements
  const [agentRates, setAgentRates] = useState<Record<string, number>>({})
  const [docStats, setDocStats] = useState<Record<string, unknown>>({})
  const [intentStats, setIntentStats] = useState<Record<string, unknown>>({})
  const [costModel, setCostModel] = useState<Record<string, unknown>>({})

  const loadData = useCallback(async () => {
    setLoading(true)

    const results = await Promise.allSettled([
      dashboardApi.getHealth(),                // 0: system health
      dashboardApi.getWorkflowStats(),         // 1: intent stats
      dashboardApi.getDocumentStats(),         // 2: doc stats
      dashboardApi.getFeedbackStats(30),       // 3: feedback
      dashboardApi.getCostEstimationHealth(),  // 4: cost model
    ])

    let modulesOnline = 0

    // --- System Banner ---
    if (results[0].status === 'fulfilled') {
      const h = results[0].value as Record<string, unknown>
      const codeExec = (h.code_execution || {}) as Record<string, unknown>
      const emb = (h.embedding || {}) as Record<string, unknown>
      setBanner({
        status: 'healthy',
        memoryMb: Number(h.memory_usage_mb || 0),
        docker: Boolean(h.docker_available),
        embedding: Boolean(emb.ready),
        llmModel: String(h.version || 'v1.0.0'),
        modulesOnline: 0, // updated below
      })

      // Data Analysis health (from code_execution)
      const codeHealthy = Boolean(codeExec.healthy)
      const codeMode = String(codeExec.mode || codeExec.selected_provider || 'docker')
      if (codeHealthy) modulesOnline++
      setDataHealth({
        status: codeHealthy ? 'healthy' : 'unhealthy',
        metrics: {},
        detail: codeMode,
      })
    } else {
      setBanner(prev => ({ ...prev, status: 'unhealthy' }))
      setDataHealth({ status: 'unhealthy', metrics: {}, detail: 'Backend unreachable' })
    }

    // --- Intent Classifier ---
    if (results[1].status === 'fulfilled') {
      const s = results[1].value as Record<string, unknown>
      setIntentStats(s)
      const agentUsage = (s.agent_usage_rates || {}) as Record<string, number>
      setAgentRates(agentUsage)
      modulesOnline++
      setIntentHealth({
        status: 'healthy',
        metrics: s,
        detail: `${Number(s.total_routes || 0)} routes processed`,
      })
    } else {
      setIntentHealth({ status: 'unhealthy', metrics: {}, detail: 'Could not reach Intent Classifier' })
    }

    // --- RAG Knowledge Base ---
    if (results[2].status === 'fulfilled') {
      const d = results[2].value as Record<string, unknown>
      setDocStats(d)
      const total = Number(d.total_documents || 0)
      const active = Number(d.active_documents || d.processed_documents || 0)
      const processed = active > 0 ? active : (Number(d.total_chunks || 0) > 0 ? total : 0)
      const ratio = total > 0 ? processed / total : 0

      let ragStatus: HealthStatus = 'healthy'
      if (ratio < 0.25) ragStatus = 'unhealthy'
      else if (ratio < 0.5) ragStatus = 'degraded'
      if (ragStatus === 'healthy') modulesOnline++

      // Feedback data
      let satisfaction = '—'
      if (results[3].status === 'fulfilled') {
        const f = results[3].value as Record<string, unknown>
        const totalQ = Number(f.total_queries || 0)
        const helpful = Number(f.helpful_count || 0)
        satisfaction = totalQ > 0 ? `${Math.round((helpful / totalQ) * 100)}%` : '—'
      }

      setRagHealth({
        status: ragStatus,
        metrics: { processed, total, satisfaction },
        detail: `${Number(d.total_chunks || 0).toLocaleString()} chunks indexed`,
      })
    } else {
      setRagHealth({ status: 'unhealthy', metrics: {}, detail: 'Could not reach Knowledge Base' })
    }

    // --- Cost Estimation ---
    if (results[4].status === 'fulfilled') {
      const c = results[4].value as Record<string, unknown>
      const model = (c.model || {}) as Record<string, unknown>
      setCostModel(model)
      const metrics = (model.metrics || {}) as Record<string, unknown>
      const cv = (metrics.cross_validation || {}) as Record<string, unknown>
      const actual = (cv.actual_cost || {}) as Record<string, number>
      const r2 = Number(actual.r2 || 0)

      let costStatus: HealthStatus = 'healthy'
      if (r2 < 0.5) costStatus = 'unhealthy'
      else if (r2 < 0.7) costStatus = 'degraded'
      if (costStatus === 'healthy') modulesOnline++

      setCostHealth({
        status: costStatus,
        metrics: { r2, mape: actual.mape || 0 },
        detail: `${Number(model.training_rows || 0).toLocaleString()} training samples`,
      })
    } else {
      setCostHealth({ status: 'unhealthy', metrics: {}, detail: 'Could not reach Cost Model' })
    }

    // Update banner with final count
    setBanner(prev => ({
      ...prev,
      modulesOnline,
      status: modulesOnline >= 4 ? 'healthy' : modulesOnline >= 2 ? 'degraded' : 'unhealthy',
    }))

    setLoading(false)
  }, [])

  useEffect(() => {
    loadData()
  }, [loadData])

  // --- Skeleton Loading ---
  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 p-6">
        <div className="max-w-7xl mx-auto">
          <div className="animate-pulse">
            <div className="h-8 bg-gray-200 rounded w-1/3 mb-6" />
            <div className="h-20 bg-gray-700 rounded-xl mb-6" />
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
              {[...Array(4)].map((_, i) => (
                <div key={i} className="h-56 bg-gray-200 rounded-xl" />
              ))}
            </div>
          </div>
        </div>
      </div>
    )
  }

  // --- Derived values ---
  const directRate = Math.round(Number(intentStats.direct_routing_rate || 0) * 100)
  const clarifyRate = Math.round(Number(intentStats.clarification_rate || 0) * 100)
  const fallbackRate = Math.round(Number(intentStats.fallback_rate || 0) * 100)
  const totalRoutes = Number(intentStats.total_routes || 0)

  const ragProcessed = Number(ragHealth.metrics.processed || 0)
  const ragTotal = Number(ragHealth.metrics.total || 0)
  const totalChunks = Number(docStats.total_chunks || 0)
  const satisfaction = String(ragHealth.metrics.satisfaction || '—')

  const r2 = Number(costHealth.metrics.r2 || 0)
  const mape = Number(costHealth.metrics.mape || 0)
  const trainingRows = Number(costModel.training_rows || 0)
  const ridgeAlpha = costModel.ridge_alpha != null ? String(costModel.ridge_alpha) : '—'

  const codeExecMode = dataHealth.detail || 'docker'

  return (
    <div className="min-h-screen bg-gray-50 p-6">
      <div className="max-w-7xl mx-auto">
        {/* Page Header */}
        <div className="flex items-center justify-between mb-6">
          <div>
            <h1 className="text-2xl font-bold text-gray-900 tracking-tight">System Overview</h1>
            <p className="text-sm text-gray-500 mt-0.5">Real-time health and performance across all AI modules</p>
          </div>
          <button
            onClick={loadData}
            className="px-3 py-1.5 text-sm text-gray-600 border border-gray-300 rounded-lg hover:bg-gray-50 transition"
          >
            Refresh
          </button>
        </div>

        {/* System Banner (dark hero) */}
        <div
          className="bg-[#1a1a2e] rounded-xl px-6 py-4 mb-6 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3"
          role="status"
          aria-label="System Health Status"
        >
          <div className="flex items-center gap-3">
            <span
              className={`w-3 h-3 rounded-full ${
                banner.status === 'healthy'
                  ? 'bg-emerald-400 shadow-[0_0_8px_rgba(52,211,153,0.5)]'
                  : banner.status === 'degraded'
                  ? 'bg-amber-400 shadow-[0_0_8px_rgba(245,158,11,0.5)]'
                  : 'bg-red-400 shadow-[0_0_8px_rgba(239,68,68,0.5)]'
              }`}
            />
            <div>
              <div className="text-base font-semibold text-gray-200">
                {banner.status === 'healthy'
                  ? 'All Systems Online'
                  : banner.status === 'degraded'
                  ? `${banner.modulesOnline}/4 Modules Online`
                  : 'System Unavailable'}
              </div>
              <div className="text-xs text-gray-500">{banner.modulesOnline} modules healthy</div>
            </div>
          </div>
          <div className="flex flex-wrap gap-x-5 gap-y-1 text-xs text-gray-500 font-mono">
            <span>Memory: <span className="text-gray-300">{banner.memoryMb.toFixed(0)} MB</span></span>
            <span>Docker: <span className="text-gray-300">{banner.docker ? '✓' : '✗'}</span></span>
            <span>Embedding: <span className="text-gray-300">{banner.embedding ? 'Ready' : 'Not Ready'}</span></span>
          </div>
        </div>

        {/* 4 Module Cards (2x2 grid) */}
        <div
          className="grid grid-cols-1 lg:grid-cols-2 gap-4 mb-6"
          role="region"
          aria-label="Module Health"
        >
          {/* Intent Classifier */}
          <ModuleCard
            moduleKey="intent"
            title="Intent Classifier"
            subtitle="11-node StateGraph · Zhipu LLM"
            health={intentHealth}
            heroLabel="Direct Routing Rate"
            heroValue={`${directRate}%`}
            metrics={[
              { label: 'Total Routes', value: totalRoutes.toLocaleString() },
              { label: 'Clarification', value: `${clarifyRate}%`, detail: 'Max 2 rounds' },
              { label: 'Fallback', value: `${fallbackRate}%` },
              { label: 'Agents', value: String(intentStats.available_agents || '—') },
            ]}
          >
            <AgentDistributionBar rates={agentRates} />
          </ModuleCard>

          {/* RAG Knowledge Base */}
          <ModuleCard
            moduleKey="rag"
            title="RAG Knowledge Base"
            subtitle="Hybrid BM25 + Vector · bge-reranker"
            health={ragHealth}
            heroLabel="Documents Processed"
            heroValue={`${ragProcessed} / ${ragTotal}`}
            metrics={[
              { label: 'Chunks', value: totalChunks.toLocaleString(), detail: '512 chars · 128 overlap' },
              { label: 'User Satisfaction', value: satisfaction, detail: 'Feedback-based' },
            ]}
          >
            <DocTypeTags docs={docStats} />
          </ModuleCard>

          {/* Cost Estimation */}
          <ModuleCard
            moduleKey="cost"
            title="Cost Estimation"
            subtitle="Ridge Regression · ML Pipeline"
            health={costHealth}
            heroLabel="R² Score"
            heroValue={r2.toFixed(3)}
            metrics={[
              { label: 'MAPE', value: `${(mape * 100).toFixed(1)}%`, detail: 'Mean absolute % error' },
              { label: 'Training Data', value: trainingRows.toLocaleString(), detail: 'Construction projects' },
              { label: 'Ridge Alpha', value: ridgeAlpha, detail: 'Regularization' },
            ]}
          />

          {/* Data Analysis */}
          <ModuleCard
            moduleKey="data"
            title="Dynamic Data Analysis"
            subtitle="Cloud LLM Code Gen · Docker Sandbox"
            health={dataHealth}
            heroLabel="Sandbox Status"
            heroValue={dataHealth.status === 'healthy' ? `${codeExecMode} ✓` : 'Offline'}
            metrics={[
              { label: 'Cloud LLM', value: 'Zhipu', detail: 'Gemini fallback ready' },
              { label: 'Chart Types', value: '8', detail: 'line, bar, scatter, pie...' },
              { label: 'Code Validator', value: 'Strict', detail: 'Blocked methods enforced' },
            ]}
          />
        </div>

        {/* System Architecture */}
        <section className="mt-12" data-testid="system-architecture-section">
          <div className="mb-4">
            <h2 className="text-lg font-semibold text-gray-900">System Architecture</h2>
            <p className="mt-1 text-sm text-gray-500">
              C4 Container Diagram (Level 2) · Client → API Gateway → Orchestration → AI Runtime → Data &amp; Storage.
            </p>
          </div>
          <div className="overflow-x-auto rounded-lg border border-gray-200 bg-white p-4 shadow-sm">
            <img
              src="/diagrams/system-architecture.svg"
              alt="Industry AI Flow system architecture"
              className="min-w-[1200px] w-full h-auto"
            />
          </div>
        </section>

        {/* Main Request Flow (Data Flow) */}
        <section className="mt-12" data-testid="data-flow-section">
          <div className="mb-4">
            <h2 className="text-lg font-semibold text-gray-900">Main Request Flow</h2>
            <p className="mt-1 text-sm text-gray-500">
              UML Activity Diagram · Frontend → Intent Classification → 10-Node Execution Pipeline → Response render.
            </p>
          </div>
          <div className="overflow-x-auto rounded-lg border border-gray-200 bg-white p-4 shadow-sm">
            <img
              src="/diagrams/data-flow.svg"
              alt="Industry AI Flow main request flow"
              className="mx-auto max-w-[900px] w-full h-auto"
            />
          </div>
        </section>

        {/* Database ERD */}
        <section className="mt-12" data-testid="database-erd-section">
          <div className="mb-4">
            <h2 className="text-lg font-semibold text-gray-900">Database Schema (ERD)</h2>
            <p className="mt-1 text-sm text-gray-500">
              PostgreSQL 14+ with pgvector · 19 tables across Documents / RAG, Prompt Management, and LLM Ops.
            </p>
          </div>
          <div className="overflow-x-auto rounded-lg border border-gray-200 bg-white p-4 shadow-sm">
            <img
              src="/diagrams/database-erd.svg"
              alt="Industry AI Flow database ERD"
              className="min-w-[1200px] w-full h-auto"
            />
          </div>
        </section>
      </div>
    </div>
  )
}
