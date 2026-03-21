'use client'

import { useState, useEffect, useCallback, useRef } from 'react'
import Link from 'next/link'
import { useAuth } from '@/contexts/AuthContext'
import PipelineFlowViz, { usePipelineAnimation } from '@/components/PipelineFlowViz'
import {
  workflowApi,
  getPlatformHealth,
  getWorkflowHealth,
  getCostHealth,
  dashboardApi,
} from '@/lib/api-client'
import type { RuntimeAppConfig } from '@/lib/api-client'

const AUTO_RUN_DEMO = true

const SAMPLE_QUERIES = [
  'What are the fire safety requirements in the National Building Code?',
  'What is the minimum concrete cover for reinforced concrete?',
  'Summarize the key structural requirements in NBC 2020',
]

const INTENT_LABELS: Record<string, { label: string; color: string }> = {
  knowledge_retrieval: { label: 'RAG', color: 'bg-blue-100 text-blue-700' },
  cost_estimation: { label: 'Cost', color: 'bg-amber-100 text-amber-700' },
  data_analysis: { label: 'Code', color: 'bg-purple-100 text-purple-700' },
  code_execution: { label: 'Code', color: 'bg-purple-100 text-purple-700' },
  document_processing: { label: 'Doc', color: 'bg-orange-100 text-orange-700' },
}

interface RecentExecution {
  query: string
  intent: string
  nodesExecuted: number
  totalMs: number
  timestamp: string
}

interface StatusCardData {
  loading: boolean
  error: string | null
  value: string
  detail: string
  healthy: boolean
}

export default function PipelineFlowDashboard() {
  const { user } = useAuth()
  const { nodeStates, triggerAnimation, isAnimating, reset } = usePipelineAnimation()
  const [nodeLatencies, setNodeLatencies] = useState<Record<string, number>>({})
  const [totalTime, setTotalTime] = useState<number | undefined>()
  const [intentLabel, setIntentLabel] = useState<string | undefined>()
  const [confidence, setConfidence] = useState<number | undefined>()
  const [demoRunning, setDemoRunning] = useState(false)
  const demoRunningRef = useRef(false)
  const [demoError, setDemoError] = useState<string | null>(null)
  const [recentExecutions, setRecentExecutions] = useState<RecentExecution[]>([])
  const queryIndexRef = useRef(0)
  const autoRanRef = useRef(false)

  // Status cards
  const [knowledgeBase, setKnowledgeBase] = useState<StatusCardData>({
    loading: true, error: null, value: '—', detail: 'Loading...', healthy: false,
  })
  const [llmEngine, setLlmEngine] = useState<StatusCardData>({
    loading: true, error: null, value: '—', detail: 'Loading...', healthy: false,
  })
  const [systemHealth, setSystemHealth] = useState<StatusCardData>({
    loading: true, error: null, value: '—', detail: 'Loading...', healthy: false,
  })

  const config: RuntimeAppConfig = {}

  // Load status cards (parallel to avoid sequential stalling)
  const loadStatusCards = useCallback(async () => {
    // Run all health checks in parallel
    const [docResult, healthResult, wfResult, costResult] = await Promise.allSettled([
      dashboardApi.getDocumentStats(),
      getPlatformHealth(config),
      getWorkflowHealth(config),
      getCostHealth(config),
    ])

    // Knowledge Base
    if (docResult.status === 'fulfilled') {
      const stats = docResult.value
      const total = Number(stats.total_documents ?? stats.total ?? 0)
      const active = Number(stats.active_documents ?? stats.processed_documents ?? stats.processed ?? 0)
      const totalChunks = Number(stats.total_chunks ?? 0)
      // If active_documents is 0 but we have chunks, documents are processed but not "active" in the DB sense
      const processed = active > 0 ? active : (totalChunks > 0 ? total : 0)
      const pending = total - processed
      setKnowledgeBase({
        loading: false, error: null,
        value: `${processed} / ${total}`,
        detail: `Documents processed · ${pending} pending · pgvector 768-dim`,
        healthy: processed > total * 0.5,
      })
    } else {
      setKnowledgeBase({
        loading: false, error: 'Could not reach document service',
        value: '—', detail: '', healthy: false,
      })
    }

    // LLM Engine
    if (healthResult.status === 'fulfilled') {
      const health = healthResult.value
      const modelName = typeof health.model === 'string' ? health.model : 'Qwen3.5:4b'
      setLlmEngine({
        loading: false, error: null,
        value: modelName,
        detail: 'Ollama · Metal GPU · ~28 TPS',
        healthy: health.status === 'ok' || health.status === 'healthy',
      })
    } else {
      setLlmEngine({
        loading: false, error: 'Ollama unreachable',
        value: '—', detail: '', healthy: false,
      })
    }

    // System Health (aggregate results)
    const services = [
      { name: 'FastAPI', result: healthResult },
      { name: 'Workflow', result: wfResult },
      { name: 'Cost Est.', result: costResult },
    ]
    let online = 0
    const names: string[] = []
    for (const svc of services) {
      if (svc.result.status === 'fulfilled') {
        const h = svc.result.value
        if (h.status === 'ok' || h.status === 'healthy') {
          online++
          names.push(svc.name)
        }
      }
    }
    setSystemHealth({
      loading: false, error: online < services.length ? `${online}/${services.length} services online` : null,
      value: online === services.length ? 'All Online' : `${online}/${services.length} Online`,
      detail: names.length > 0 ? names.join(' · ') : 'No services reachable',
      healthy: online === services.length,
    })
  }, [])

  // Run Live Demo query
  const runLiveDemo = useCallback(async () => {
    if (demoRunningRef.current || isAnimating) return
    demoRunningRef.current = true
    setDemoRunning(true)
    setDemoError(null)
    reset()
    setTotalTime(undefined)
    setIntentLabel(undefined)
    setConfidence(undefined)
    setNodeLatencies({})

    const query = SAMPLE_QUERIES[queryIndexRef.current % SAMPLE_QUERIES.length]
    queryIndexRef.current++

    try {
      const result = await workflowApi.sendQuery({ query }, config)

      const metadata = result.metadata || {}
      let completedNodes = (metadata.completed_nodes as string[]) || []
      let latencyMs = (metadata.node_latency_ms as Record<string, number>) || {}
      const pipelineIntent = (metadata.intent as string) || result.intent?.type || 'unknown'
      const pipelineConfidence = (metadata.intent_confidence as number) || result.confidence || 0
      const pipelineStatus = (metadata.pipeline_status as string) || 'unknown'
      const failedNode = metadata.failed_node as string | undefined

      // If intent_workflow (no pipeline nodes), infer node states from metadata timestamps
      if (completedNodes.length === 0 && metadata.workflow_runner === 'intent_workflow') {
        const agentType = metadata.agent_type as string || metadata.selected_agent as string || ''
        const agentStatus = metadata.agent_execution_status as string || ''
        const inferred: string[] = ['intent_node', 'safety_node']
        const inferredLatency: Record<string, number> = {}

        // Calculate timing from timestamps
        const start = metadata.start_timestamp as string
        const classTs = metadata.classification_timestamp as string
        const routeTs = metadata.routing_timestamp as string
        const completeTs = metadata.completion_timestamp as string
        if (start && classTs) {
          inferredLatency.intent_node = Math.max(1, Math.round(
            (new Date(classTs).getTime() - new Date(start).getTime())
          ))
        }
        inferredLatency.safety_node = 5 // implicit, near-instant

        // Route node
        if (routeTs && classTs) {
          inferred.push('route_node')
          inferredLatency.route_node = Math.max(1, Math.round(
            (new Date(routeTs).getTime() - new Date(classTs).getTime())
          ))
        }

        // Agent-specific nodes based on which agent ran
        if (agentStatus === 'ok') {
          if (agentType === 'rag_agent' || pipelineIntent === 'knowledge_retrieval') {
            inferred.push('retrieval_node', 'rerank_node', 'prompt_node', 'response_node', 'groundedness_node')
          } else if (agentType === 'cost_estimation_agent' || pipelineIntent === 'cost_estimation') {
            inferred.push('cost_estimation_node', 'response_node')
          } else if (agentType === 'data_analysis_agent' || pipelineIntent === 'data_analysis') {
            inferred.push('code_exec_node', 'response_node')
          } else {
            inferred.push('response_node')
          }
          // Distribute remaining time across agent nodes
          if (routeTs && completeTs) {
            const agentMs = Math.max(1, Math.round(
              (new Date(completeTs).getTime() - new Date(routeTs).getTime())
            ))
            const agentNodes = inferred.filter(n => !['intent_node', 'safety_node', 'route_node'].includes(n))
            const perNode = Math.round(agentMs / Math.max(1, agentNodes.length))
            agentNodes.forEach(n => { inferredLatency[n] = perNode })
          }
        }

        completedNodes = inferred
        latencyMs = inferredLatency
      }

      // Check for pipeline-level failure
      if (pipelineStatus === 'error' && completedNodes.length === 0) {
        setDemoError('Pipeline execution failed — no nodes completed.')
        return
      }

      setNodeLatencies(latencyMs)
      const total = Object.values(latencyMs).reduce((a, b) => a + b, 0)
      setTotalTime(total)
      setIntentLabel(pipelineIntent)
      setConfidence(pipelineConfidence)

      // Trigger animation (mark failed node if present)
      await triggerAnimation(completedNodes, latencyMs, failedNode)

      // Add to recent executions
      setRecentExecutions((prev) => [
        {
          query,
          intent: pipelineIntent,
          nodesExecuted: completedNodes.length,
          totalMs: total,
          timestamp: new Date().toISOString(),
        },
        ...prev.slice(0, 4),
      ])
    } catch (err) {
      setDemoError('Pipeline query failed — check if Ollama is running.')
    } finally {
      demoRunningRef.current = false
      setDemoRunning(false)
    }
  }, [isAnimating, reset, triggerAnimation])

  // Load data on mount
  useEffect(() => {
    loadStatusCards().then(() => {
      if (AUTO_RUN_DEMO && !autoRanRef.current) {
        autoRanRef.current = true
        runLiveDemo()
      }
    })
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  return (
    <div className="min-h-screen bg-gray-50 p-4 sm:p-6">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="flex items-center justify-between mb-6">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">Industry AI Flow</h1>
            <p className="text-sm text-gray-500">AI-Powered Construction Intelligence Platform</p>
          </div>
          <div className="text-sm text-gray-500">
            {user?.name || 'Demo User'}
          </div>
        </div>

        {/* Pipeline Visualization Hero */}
        <div className="mb-6">
          <PipelineFlowViz
            nodeStates={nodeStates}
            nodeLatencies={nodeLatencies}
            totalTime={totalTime}
            intentLabel={intentLabel}
            confidence={confidence}
          />

          {/* Live Demo Button — inside hero context */}
          <div className="flex justify-center -mt-1">
            <button
              onClick={runLiveDemo}
              disabled={demoRunning || isAnimating}
              className="mt-4 px-6 py-3 bg-amber-500 hover:bg-amber-600 disabled:opacity-60 disabled:cursor-not-allowed text-white font-semibold rounded-xl text-sm transition-all flex items-center gap-2 min-h-[48px]"
              data-testid="live-demo-button"
              aria-label="Run a sample query through the AI pipeline"
              aria-busy={demoRunning || isAnimating}
            >
              {demoRunning ? (
                <>
                  <span className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                  Running...
                </>
              ) : isAnimating ? (
                <>
                  <span className="w-2 h-2 bg-emerald-400 rounded-full animate-pulse" />
                  Animating...
                </>
              ) : (
                <>
                  <span className="w-2 h-2 bg-green-400 rounded-full animate-pulse" />
                  Live Demo — Try a Query
                </>
              )}
            </button>
          </div>

          {/* Error toast */}
          {demoError && (
            <div className="mt-3 text-center text-sm text-red-500 bg-red-50 rounded-lg py-2 px-4 mx-auto max-w-md">
              {demoError}
            </div>
          )}
        </div>

        {/* Status Cards */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-6" data-testid="status-cards">
          <StatusCard
            label="Knowledge Base"
            data={knowledgeBase}
            testId="status-knowledge-base"
          />
          <StatusCard
            label="LLM Engine"
            data={llmEngine}
            testId="status-llm-engine"
          />
          <StatusCard
            label="System Health"
            data={systemHealth}
            testId="status-system-health"
          />
        </div>

        {/* Bottom row: Recent Executions + Quick Actions */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
          {/* Recent Pipeline Executions */}
          <div className="lg:col-span-2 bg-white rounded-xl shadow-sm border border-gray-200 p-5" data-testid="recent-executions">
            <h2 className="text-sm font-semibold text-gray-900 mb-3">Recent Pipeline Executions</h2>
            {recentExecutions.length === 0 ? (
              <div className="text-center py-8 text-gray-400 text-sm border border-dashed border-gray-200 rounded-lg">
                {AUTO_RUN_DEMO && (demoRunning || isAnimating)
                  ? 'Running first query...'
                  : "Click 'Live Demo' to see your first pipeline execution"}
              </div>
            ) : (
              <div className="space-y-2">
                {recentExecutions.map((exec, i) => {
                  const intentCfg = INTENT_LABELS[exec.intent] || { label: exec.intent, color: 'bg-gray-100 text-gray-600' }
                  return (
                    <div key={i} className="flex items-center justify-between py-2 border-b border-gray-100 last:border-0">
                      <div className="text-sm text-gray-700 truncate max-w-[400px]">
                        &ldquo;{exec.query}&rdquo;
                      </div>
                      <div className="flex items-center gap-3 text-xs text-gray-400 shrink-0 ml-3">
                        <span className={`px-2 py-0.5 rounded-full text-[10px] font-medium ${intentCfg.color}`}>
                          {intentCfg.label}
                        </span>
                        <span>{exec.nodesExecuted} nodes</span>
                        <span className="font-mono">{(exec.totalMs / 1000).toFixed(1)}s</span>
                      </div>
                    </div>
                  )
                })}
              </div>
            )}
          </div>

          {/* Quick Actions */}
          <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-5" data-testid="quick-actions">
            <h2 className="text-sm font-semibold text-gray-900 mb-3">Quick Actions</h2>
            <div className="space-y-2">
              {[
                { title: 'Ask the Knowledge Base', href: '/workflow-chat', icon: '💬' },
                { title: 'Upload Documents', href: '/documents-integrated', icon: '📄' },
                { title: 'Run Data Analysis', href: '/data-analysis', icon: '📊' },
                { title: 'Estimate Costs', href: '/cost-estimation', icon: '💰' },
              ].map((action) => (
                <Link
                  key={action.href}
                  href={action.href}
                  className="flex items-center gap-3 p-3 rounded-lg border border-gray-200 hover:border-blue-300 hover:bg-blue-50 transition text-sm text-gray-700 group"
                >
                  <span className="text-base">{action.icon}</span>
                  <span className="font-medium">{action.title}</span>
                  <span className="ml-auto text-gray-300 group-hover:text-gray-500">&rarr;</span>
                </Link>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

// Status Card component
function StatusCard({ label, data, testId }: {
  label: string
  data: StatusCardData
  testId: string
}) {
  return (
    <article
      className="bg-white rounded-xl shadow-sm border border-gray-200 p-5"
      data-testid={testId}
      aria-label={`${label}: ${data.value}`}
    >
      <div className="flex items-center gap-2 text-xs text-gray-500 uppercase tracking-wide mb-2">
        <span
          className={`w-2 h-2 rounded-full ${
            data.loading ? 'bg-gray-300 animate-pulse' :
            data.error && !data.healthy ? 'bg-red-500' :
            data.healthy ? 'bg-green-500' : 'bg-amber-500'
          }`}
        />
        {label}
      </div>
      {data.loading ? (
        <div className="space-y-2">
          <div className="h-7 bg-gray-200 rounded animate-pulse w-20" />
          <div className="h-3 bg-gray-200 rounded animate-pulse w-40" />
        </div>
      ) : (
        <>
          <div className="text-2xl font-bold text-gray-900">{data.value}</div>
          {data.error ? (
            <div className="text-xs text-red-400 mt-1">{data.error}</div>
          ) : (
            <div className="text-xs text-gray-500 mt-1">{data.detail}</div>
          )}
        </>
      )}
    </article>
  )
}
