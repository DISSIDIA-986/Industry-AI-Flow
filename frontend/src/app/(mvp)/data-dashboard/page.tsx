'use client'

import { useState, useEffect, useCallback } from 'react'
import {
  BarChartComponent, PieChartComponent,
  MetricCard, DataTable
} from '@/components/charts'

interface LlmProviderUsage {
  provider: string
  model: string
  request_count: number
  total_tokens: number
  total_cost_usd: number
}

export default function DataDashboardPage() {
  const [loading, setLoading] = useState(true)
  const [docStats, setDocStats] = useState<Record<string, unknown>>({})
  const [llmSummary, setLlmSummary] = useState<LlmProviderUsage[]>([])
  const [llmTotals, setLlmTotals] = useState({ requests: 0, tokens: 0, cost: 0 })
  const [costModelStats, setCostModelStats] = useState<Record<string, unknown>>({})
  const [documents, setDocuments] = useState<Array<Record<string, unknown>>>([])

  const loadData = useCallback(async () => {
    setLoading(true)
    try {
      const { dashboardApi, documentApi } = await import('@/lib/api-client')

      const results = await Promise.allSettled([
        dashboardApi.getDocumentStats(),
        dashboardApi.getLlmUsage(30),
        dashboardApi.getCostEstimationHealth(),
        documentApi.getDocuments(),
      ])

      // Document stats
      if (results[0].status === 'fulfilled') {
        setDocStats(results[0].value as Record<string, unknown>)
      }

      // LLM usage
      if (results[1].status === 'fulfilled') {
        const usage = results[1].value as Record<string, unknown>
        const summary = (Array.isArray(usage.summary) ? usage.summary : []) as LlmProviderUsage[]
        setLlmSummary(summary)
        const totals = (usage.totals || {}) as Record<string, number>
        setLlmTotals({
          requests: totals.request_count || 0,
          tokens: totals.total_tokens || 0,
          cost: totals.total_cost_usd || 0,
        })
      }

      // Cost model health
      if (results[2].status === 'fulfilled') {
        const health = results[2].value as Record<string, unknown>
        const model = (health.model || {}) as Record<string, unknown>
        setCostModelStats(model)
      }

      // Document list
      if (results[3].status === 'fulfilled') {
        setDocuments(results[3].value as Array<Record<string, unknown>>)
      }
    } catch (error) {
      console.error('Failed to load data:', error)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    loadData()
  }, [loadData])

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 p-6">
        <div className="max-w-7xl mx-auto">
          <div className="animate-pulse">
            <div className="h-8 bg-gray-200 rounded w-1/4 mb-8"></div>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
              {[...Array(4)].map((_, i) => (
                <div key={i} className="h-32 bg-gray-200 rounded"></div>
              ))}
            </div>
            <div className="h-96 bg-gray-200 rounded"></div>
          </div>
        </div>
      </div>
    )
  }

  // Derive chart data from real backend data
  const docTypeDistribution = deriveDocTypeDistribution(documents)
  const llmProviderDistribution = llmSummary.map((s) => ({
    name: `${s.provider}/${s.model}`,
    value: s.request_count,
  }))
  const llmCostDistribution = llmSummary
    .filter((s) => s.total_cost_usd > 0)
    .map((s) => ({
      name: `${s.provider}/${s.model}`,
      value: Number(s.total_cost_usd.toFixed(4)),
    }))

  // Cost model metrics
  const modelMetrics = (costModelStats.metrics || {}) as Record<string, unknown>
  const crossVal = (modelMetrics.cross_validation || {}) as Record<string, unknown>
  const actualCost = (crossVal.actual_cost || {}) as Record<string, number>

  return (
    <div className="min-h-screen bg-gray-50 p-6">
      <div className="max-w-7xl mx-auto">
        <div className="flex items-center justify-between mb-8">
          <h1 className="text-3xl font-bold text-gray-900">Data Analysis Dashboard</h1>
          <button
            onClick={loadData}
            className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition"
          >
            Refresh
          </button>
        </div>

        {/* KPI Cards */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
          <MetricCard
            title="Documents"
            value={Number(docStats.total_documents || documents.length || 0)}
            change={`${Number(docStats.total_chunks || 0).toLocaleString()} chunks`}
          />
          <MetricCard
            title="LLM Requests"
            value={llmTotals.requests}
            change="Last 30 days"
          />
          <MetricCard
            title="Total Tokens"
            value={llmTotals.tokens.toLocaleString()}
            change="Last 30 days"
          />
          <MetricCard
            title="API Cost"
            value={`$${llmTotals.cost.toFixed(2)}`}
            change="Cloud LLM spend"
          />
        </div>

        {/* Charts row 1 */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
          <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
            <h2 className="text-xl font-semibold text-gray-900 mb-6">Document Type Distribution</h2>
            {docTypeDistribution.length > 0 ? (
              <PieChartComponent
                data={docTypeDistribution}
                title="By file type"
                height={300}
              />
            ) : (
              <div className="h-64 flex items-center justify-center text-gray-400">
                No documents indexed
              </div>
            )}
          </div>

          <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
            <h2 className="text-xl font-semibold text-gray-900 mb-6">LLM Usage by Provider</h2>
            {llmProviderDistribution.length > 0 ? (
              <BarChartComponent
                data={llmProviderDistribution}
                title="Requests per provider/model"
                height={300}
              />
            ) : (
              <div className="h-64 flex items-center justify-center text-gray-400">
                No LLM usage data
              </div>
            )}
          </div>
        </div>

        {/* Charts row 2 */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
          <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
            <h2 className="text-xl font-semibold text-gray-900 mb-6">LLM Cost Breakdown</h2>
            {llmCostDistribution.length > 0 ? (
              <BarChartComponent
                data={llmCostDistribution}
                title="Cost (USD) per provider"
                height={300}
              />
            ) : (
              <div className="h-64 flex items-center justify-center text-gray-400">
                No cost data (local LLM is free)
              </div>
            )}
          </div>

          {/* Cost Estimation Model Stats */}
          <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
            <h2 className="text-xl font-semibold text-gray-900 mb-6">Cost Estimation Model</h2>
            {costModelStats.loaded ? (
              <div className="space-y-4">
                <div className="grid grid-cols-2 gap-4">
                  <div className="p-3 bg-gray-50 rounded-lg">
                    <div className="text-xs text-gray-500">Training Rows</div>
                    <div className="text-lg font-bold">{Number(costModelStats.training_rows || 0).toLocaleString()}</div>
                  </div>
                  <div className="p-3 bg-gray-50 rounded-lg">
                    <div className="text-xs text-gray-500">R² Score</div>
                    <div className="text-lg font-bold">{(actualCost.r2 ?? 0).toFixed(3)}</div>
                  </div>
                  <div className="p-3 bg-gray-50 rounded-lg">
                    <div className="text-xs text-gray-500">MAPE</div>
                    <div className="text-lg font-bold">{((actualCost.mape ?? 0) * 100).toFixed(1)}%</div>
                  </div>
                  <div className="p-3 bg-gray-50 rounded-lg">
                    <div className="text-xs text-gray-500">Ridge Alpha</div>
                    <div className="text-lg font-bold">{String(costModelStats.ridge_alpha ?? 'N/A')}</div>
                  </div>
                </div>
                <div className="text-xs text-gray-400 mt-2">
                  Cross-validated on {String(crossVal.folds ?? 0)} folds
                </div>
              </div>
            ) : (
              <div className="h-64 flex items-center justify-center text-gray-400">
                Cost model not loaded
              </div>
            )}
          </div>
        </div>

        {/* Document table */}
        <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
          <h2 className="text-xl font-semibold text-gray-900 mb-6">Document Index</h2>
          {documents.length > 0 ? (
            <DataTable
              data={documents.map((d) => ({
                name: String(d.name || d.filename || ''),
                type: String(d.type || ''),
                size: typeof d.size === 'number'
                  ? `${(d.size / 1024 / 1024).toFixed(2)} MB`
                  : String(d.size || ''),
                status: String(d.status || 'unknown'),
                source: String(d.source || ''),
              }))}
              columns={[
                { key: 'name', label: 'Filename' },
                { key: 'type', label: 'Type' },
                { key: 'size', label: 'Size' },
                { key: 'status', label: 'Status' },
                { key: 'source', label: 'Source' },
              ]}
            />
          ) : (
            <div className="text-center py-8 text-gray-400">No documents found</div>
          )}
        </div>
      </div>
    </div>
  )
}

function deriveDocTypeDistribution(docs: Array<Record<string, unknown>>): Array<{ name: string; value: number }> {
  const counts: Record<string, number> = {}
  for (const doc of docs) {
    const ext = String(doc.type || 'UNKNOWN').toUpperCase()
    counts[ext] = (counts[ext] || 0) + 1
  }
  return Object.entries(counts)
    .map(([name, value]) => ({ name, value }))
    .sort((a, b) => b.value - a.value)
}
