'use client'

import { useState, useEffect, useCallback } from 'react'
import Link from 'next/link'
import { useAuth } from '@/contexts/AuthContext'
import { MetricCard } from '@/components/charts'

interface ServiceHealth {
  name: string
  healthy: boolean
  detail?: string
}

interface ActivityEntry {
  id: string
  type: string
  description: string
  time: string
}

export default function OverviewDashboardPage() {
  const { user } = useAuth()
  const [stats, setStats] = useState({
    totalDocuments: 0,
    totalChunks: 0,
    llmRequests: 0,
    llmCostUsd: 0,
  })
  const [services, setServices] = useState<ServiceHealth[]>([])
  const [activities, setActivities] = useState<ActivityEntry[]>([])
  const [loading, setLoading] = useState(true)

  const loadData = useCallback(async () => {
    try {
      const { dashboardApi, documentApi } = await import('@/lib/api-client')

      const results = await Promise.allSettled([
        dashboardApi.getDocumentStats(),
        dashboardApi.getLlmUsage(30),
        dashboardApi.getHealth(),
        dashboardApi.getOperationsLog(8),
        documentApi.getDocuments(),
      ])

      // Document stats
      const docStats = results[0].status === 'fulfilled'
        ? (results[0].value as Record<string, unknown>)
        : {}

      // LLM usage
      const llmUsage = results[1].status === 'fulfilled'
        ? (results[1].value as Record<string, unknown>)
        : {}
      const totals = (llmUsage.totals || {}) as Record<string, unknown>

      // Health
      const health = results[2].status === 'fulfilled'
        ? (results[2].value as Record<string, unknown>)
        : {}

      // Operations log → recent activities
      const opsLog = results[3].status === 'fulfilled'
        ? (results[3].value as Record<string, unknown>)
        : {}
      const logs = (Array.isArray(opsLog.logs) ? opsLog.logs : []) as Array<Record<string, unknown>>

      // Document list count
      const docs = results[4].status === 'fulfilled'
        ? (results[4].value as unknown[])
        : []

      setStats({
        totalDocuments: (docs.length as number) || Number(docStats.total_documents || 0),
        totalChunks: Number(docStats.total_chunks || 0),
        llmRequests: Number(totals.request_count || 0),
        llmCostUsd: Number(totals.total_cost_usd || 0),
      })

      // Map health response to service status
      const embedding = (health.embedding || {}) as Record<string, unknown>
      const codeExec = (health.code_execution || {}) as Record<string, unknown>
      setServices([
        {
          name: 'Backend API',
          healthy: health.status === 'ok',
          detail: health.status === 'ok' ? `Memory: ${Number(health.memory_usage_mb || 0).toFixed(0)} MB` : 'Unreachable',
        },
        {
          name: 'Embedding Engine',
          healthy: !!embedding.ready,
          detail: embedding.ready ? String(embedding.backend || 'active') : 'Not ready',
        },
        {
          name: 'Code Execution',
          healthy: !!codeExec.healthy,
          detail: codeExec.healthy ? String(codeExec.mode || 'active') : 'Unavailable',
        },
      ])

      // Map operations log to activities
      setActivities(
        logs.slice(0, 8).map((log) => {
          const op = String(log.operation || 'unknown')
          const createdAt = log.created_at ? new Date(String(log.created_at)) : new Date()
          const ago = formatTimeAgo(createdAt)
          return {
            id: String(log.id || Math.random()),
            type: op === 'create' ? 'document' : op === 'delete' ? 'system' : 'analysis',
            description: `${op.charAt(0).toUpperCase() + op.slice(1)}: ${log.filename || 'document'}`,
            time: ago,
          }
        }),
      )
    } catch (error) {
      console.error('Failed to load dashboard data:', error)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    loadData()
  }, [loadData])

  const quickActions = [
    { title: 'Start a New Query', description: 'Chat with the AI assistant', href: '/workflow-chat', color: 'blue' },
    { title: 'Upload Documents', description: 'Process and analyze documents', href: '/documents', color: 'green' },
    { title: 'Dynamic Analytics', description: 'AI-powered data analysis', href: '/data-analysis', color: 'purple' },
    { title: 'Cost Estimation', description: 'Estimate project costs', href: '/cost-estimation', color: 'orange' },
  ]

  return (
    <div className="min-h-screen bg-gray-50 p-6">
      <div className="max-w-7xl mx-auto">
        {/* Welcome banner */}
        <div className="bg-gradient-to-r from-blue-600 to-blue-800 rounded-2xl p-8 mb-8 text-white">
          <h1 className="text-3xl font-bold mb-2">
            Welcome back, {user?.name || 'User'}!
          </h1>
          <p className="text-blue-100">
            {loading
              ? 'Loading system overview...'
              : `${stats.totalDocuments} documents indexed with ${stats.totalChunks.toLocaleString()} chunks`}
          </p>
        </div>

        {/* Statistics cards */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
          <MetricCard
            title="Documents Indexed"
            value={stats.totalDocuments}
            change="In vector store"
          />
          <MetricCard
            title="Total Chunks"
            value={stats.totalChunks.toLocaleString()}
            change="Searchable segments"
          />
          <MetricCard
            title="LLM Requests (30d)"
            value={stats.llmRequests}
            change="Across all providers"
          />
          <MetricCard
            title="LLM Cost (30d)"
            value={`$${stats.llmCostUsd.toFixed(2)}`}
            change="Cloud API spend"
          />
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
          {/* Quick Actions */}
          <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
            <h2 className="text-xl font-semibold text-gray-900 mb-6">Quick Actions</h2>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              {quickActions.map((action, index) => (
                <Link
                  key={index}
                  href={action.href}
                  className="p-4 rounded-lg border border-gray-200 hover:border-blue-300 hover:bg-blue-50 transition group"
                >
                  <div className="text-blue-600 font-medium mb-1">{action.title}</div>
                  <div className="text-sm text-gray-600">{action.description}</div>
                  <div className="mt-2 text-sm text-gray-400 group-hover:text-gray-600">
                    Click to start &rarr;
                  </div>
                </Link>
              ))}
            </div>
          </div>

          {/* Recent Activity */}
          <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
            <h2 className="text-xl font-semibold text-gray-900 mb-6">Recent Activity</h2>
            <div className="space-y-4">
              {activities.length === 0 && !loading && (
                <div className="text-sm text-gray-500">No recent operations</div>
              )}
              {activities.map((activity) => (
                <div key={activity.id} className="flex items-start space-x-3">
                  <div
                    className={`w-2 h-2 mt-2 rounded-full ${
                      activity.type === 'document'
                        ? 'bg-green-500'
                        : activity.type === 'analysis'
                          ? 'bg-purple-500'
                          : 'bg-gray-500'
                    }`}
                  ></div>
                  <div className="flex-1">
                    <div className="text-sm text-gray-900">{activity.description}</div>
                    <div className="text-xs text-gray-500">{activity.time}</div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* System Status */}
        <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6 mt-8">
          <h2 className="text-xl font-semibold text-gray-900 mb-6">System Status</h2>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {services.length === 0 ? (
              <div className="text-sm text-gray-500 col-span-3">Loading status...</div>
            ) : (
              services.map((svc) => (
                <div key={svc.name} className="p-4 bg-gray-50 rounded-lg">
                  <div className="text-sm font-medium text-gray-500">{svc.name}</div>
                  <div className="flex items-center mt-2">
                    <div
                      className={`w-2 h-2 rounded-full mr-2 ${svc.healthy ? 'bg-green-500' : 'bg-red-500'}`}
                    ></div>
                    <div className={`font-medium ${svc.healthy ? 'text-green-600' : 'text-red-600'}`}>
                      {svc.healthy ? 'Running' : 'Down'}
                    </div>
                  </div>
                  {svc.detail && (
                    <div className="text-xs text-gray-400 mt-1">{svc.detail}</div>
                  )}
                </div>
              ))
            )}
          </div>
        </div>
      </div>
    </div>
  )
}

function formatTimeAgo(date: Date): string {
  const seconds = Math.floor((Date.now() - date.getTime()) / 1000)
  if (seconds < 60) return 'just now'
  const minutes = Math.floor(seconds / 60)
  if (minutes < 60) return `${minutes} min ago`
  const hours = Math.floor(minutes / 60)
  if (hours < 24) return `${hours} hour${hours > 1 ? 's' : ''} ago`
  const days = Math.floor(hours / 24)
  return `${days} day${days > 1 ? 's' : ''} ago`
}
