'use client'

/**
 * IntentFlowViz — Animated 11-node intent workflow visualization.
 * Adapted from PipelineFlowViz but with diamond decision nodes and branching paths.
 *
 * Main path (high confidence):
 * ┌──────┐  ┌──────┐  ┌──────┐  ◇──────◇  ┌──────┐  ┌──────┐  ◇──────◇  ┌──────┐  ┌──────┐
 * │Input │→ │Contxt│→ │Intent│→ │Confid.│→ │Route │→ │Prompt│→ │Clarif│→ │Agent │→ │Resp. │
 * └──────┘  └──────┘  └──────┘  ◇──────◇  └──────┘  └──────┘  ◇──────◇  └──────┘  └──────┘
 */

import { useCallback } from 'react'

import { useNodeAnimation, type NodeState } from '@/hooks/useNodeAnimation'
import type { NodeTraceEntry } from '@/lib/api-client'
import {
  INTENT_WORKFLOW_NODES,
  INTENT_NODE_ICONS,
} from '@/lib/intent-constants'

interface IntentFlowVizProps {
  nodeStates: Record<string, NodeState>
  nodeLatencies: Record<string, number>
  totalTime?: number
  intentLabel?: string
  confidence?: number
  skippedReason?: string
}

function getNodeClasses(state: NodeState, isDecision: boolean) {
  const base = {
    completed: {
      border: isDecision ? 'border-emerald-500' : 'border-emerald-500',
      bg: 'bg-emerald-900/20',
      icon: 'text-emerald-400',
      shadow: '',
    },
    active: {
      border: isDecision ? 'border-amber-500' : 'border-blue-500',
      bg: isDecision ? 'bg-amber-900/20' : 'bg-blue-900/20',
      icon: isDecision ? 'text-amber-400' : 'text-blue-400',
      shadow: isDecision
        ? 'shadow-[0_0_12px_rgba(245,158,11,0.3)]'
        : 'shadow-[0_0_12px_rgba(37,99,235,0.3)]',
    },
    error: {
      border: 'border-red-500',
      bg: 'bg-red-900/20',
      icon: 'text-red-400',
      shadow: '',
    },
    idle: {
      border: isDecision ? 'border-amber-800/40 border-dashed' : 'border-gray-600',
      bg: 'bg-gray-800',
      icon: 'text-gray-500',
      shadow: '',
    },
    skipped: {
      border: 'border-gray-700',
      bg: 'bg-gray-800/50',
      icon: 'text-gray-600',
      shadow: '',
    },
  }
  return base[state] || base.idle
}

export default function IntentFlowViz({
  nodeStates,
  nodeLatencies,
  totalTime,
  intentLabel,
  confidence,
  skippedReason,
}: IntentFlowVizProps) {
  return (
    <div
      className="bg-[#1a1a2e] rounded-2xl p-6 sm:p-8 relative overflow-hidden"
      data-testid="intent-flow-hero"
    >
      <div className="absolute inset-0 bg-gradient-to-br from-blue-900/5 to-transparent pointer-events-none" />

      <div className="relative">
        <div className="text-[11px] font-semibold uppercase tracking-[1.5px] text-gray-500 mb-1">
          11-Node LangGraph StateGraph
        </div>
        <h2 className="text-xl font-bold text-gray-200 mb-5">Intent Debugger</h2>

        {/* 11-node flow */}
        <div
          className="flex items-center overflow-x-auto pb-2 -mx-2 px-2"
          role="list"
          aria-label="Intent Classification Pipeline"
          style={{ scrollbarWidth: 'none' }}
        >
          {INTENT_WORKFLOW_NODES.map((node, i) => {
            const state = nodeStates[node.id] || 'idle'
            const latency = nodeLatencies[node.id]
            const cls = getNodeClasses(state, node.isDecision)
            const iconPath = INTENT_NODE_ICONS[node.id]

            return (
              <div key={node.id} className="flex items-center snap-start" role="listitem">
                <div
                  className="flex flex-col items-center min-w-[76px]"
                  data-testid={`intent-node-${node.id}`}
                >
                  {/* Node shape: diamond for decision, circle for regular */}
                  <div
                    className={`${
                      node.isDecision ? 'w-11 h-11 rotate-45' : 'w-11 h-11 rounded-full'
                    } border-2 ${cls.border} ${cls.bg} ${cls.shadow} flex items-center justify-center transition-all duration-300`}
                    style={node.isDecision ? { borderRadius: '4px' } : undefined}
                  >
                    <svg
                      className={`w-5 h-5 ${cls.icon} transition-colors duration-300 ${
                        node.isDecision ? '-rotate-45' : ''
                      }`}
                      fill="none"
                      viewBox="0 0 24 24"
                      stroke="currentColor"
                      strokeWidth={1.5}
                    >
                      <path strokeLinecap="round" strokeLinejoin="round" d={iconPath} />
                    </svg>
                  </div>
                  <div className="text-[9px] text-gray-500 mt-1.5 text-center leading-tight whitespace-pre-line">
                    {node.label}
                  </div>
                  <div className="h-4 flex items-center">
                    {state === 'active' && (
                      <span className="text-[9px] font-mono text-blue-400 animate-pulse">...</span>
                    )}
                    {state === 'completed' && latency !== undefined && (
                      <span className="text-[9px] font-mono text-emerald-400">{Math.round(latency)}ms</span>
                    )}
                    {state === 'skipped' && (
                      <span className="text-[9px] text-gray-600">&oslash;</span>
                    )}
                    {state === 'error' && (
                      <span className="text-[9px] text-red-400">failed</span>
                    )}
                  </div>
                </div>

                {/* Connector */}
                {i < INTENT_WORKFLOW_NODES.length - 1 && (
                  <div
                    className={`h-[2px] min-w-[8px] flex-1 -mt-5 transition-colors duration-500 ${
                      state === 'completed'
                        ? 'bg-gradient-to-r from-emerald-500 to-blue-500'
                        : 'bg-gray-700'
                    }`}
                  />
                )}
              </div>
            )
          })}
        </div>

        {/* Skipped info */}
        {skippedReason && (
          <div className="mt-2 text-[11px] text-gray-500">
            &oslash; {skippedReason}
          </div>
        )}

        {/* Fade for mobile scroll */}
        <div className="absolute right-0 top-16 bottom-8 w-8 bg-gradient-to-l from-[#1a1a2e] to-transparent pointer-events-none lg:hidden" />

        {/* Summary bar */}
        {totalTime !== undefined && (
          <div className="mt-4 flex items-center justify-center gap-4 text-xs">
            <span className="text-gray-400">
              Total: <span className="text-emerald-400 font-mono font-medium">{totalTime}ms</span>
            </span>
            {intentLabel && (
              <span className="text-gray-400">
                Intent: <span className="text-blue-400 font-medium">{intentLabel}</span>
              </span>
            )}
            {confidence !== undefined && confidence > 0 && (
              <span className="text-gray-400">
                Confidence: <span className="text-blue-400 font-mono">{Math.round(confidence * 100)}%</span>
              </span>
            )}
          </div>
        )}
      </div>
    </div>
  )
}

/** Hook: animate intent workflow nodes sequentially using real trace data. */
export function useIntentAnimation() {
  const nodeIds = INTENT_WORKFLOW_NODES.map((n) => n.id)
  const { nodeStates, triggerAnimation: rawTrigger, isAnimating, reset } =
    useNodeAnimation({ nodeIds })

  const triggerAnimation = useCallback(
    async (nodeTrace: NodeTraceEntry[]) => {
      const completedNodes = nodeTrace
        .filter((t) => t.decision !== 'error')
        .map((t) => t.node_name)
      const latencyMs: Record<string, number> = {}
      nodeTrace.forEach((t) => { latencyMs[t.node_name] = t.duration_ms })
      const failedNode = nodeTrace.find((t) => t.decision === 'error')?.node_name

      await rawTrigger({ completedNodes, latencyMs, failedNode })
    },
    [rawTrigger],
  )

  return { nodeStates, triggerAnimation, isAnimating, reset } as const
}

export { type NodeState } from '@/hooks/useNodeAnimation'
