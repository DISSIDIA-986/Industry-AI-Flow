'use client'

/**
 * PipelineFlowViz — Animated 10-node pipeline visualization for the Dashboard.
 * Shows the AI workflow execution flow with sequential node animation.
 *
 * ┌──────┐   ┌──────┐   ┌──────┐   ┌──────┐   ┌──────┐
 * │Intent│──→│Safety│──→│ Cost │──→│Retrvl│──→│Rerank│──→ ...
 * └──────┘   └──────┘   └──────┘   └──────┘   └──────┘
 *   245ms      12ms       8ms      1850ms      340ms
 */

import { useCallback, useRef } from 'react'
import { useNodeAnimation, type NodeState } from '@/hooks/useNodeAnimation'
import { ALL_NODES } from './PipelineInsight'

export const NODE_LABELS: Record<string, string> = {
  intent_node: 'Intent',
  safety_node: 'Safety',
  cost_estimation_node: 'Cost Est.',
  retrieval_node: 'Retrieval',
  rerank_node: 'Rerank',
  prompt_node: 'Prompt',
  route_node: 'Route',
  code_exec_node: 'Code Exec',
  response_node: 'Response',
  groundedness_node: 'Ground.',
}

// SVG icons for each node (inline, 20x20 viewBox)
export const NODE_ICONS: Record<string, string> = {
  intent_node: 'M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z',
  safety_node: 'M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z',
  cost_estimation_node: 'M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z',
  retrieval_node: 'M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z',
  rerank_node: 'M3 4h13M3 8h9m-9 4h6m4 0l4-4m0 0l4 4m-4-4v12',
  prompt_node: 'M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z',
  route_node: 'M13 17h8m0 0V9m0 8l-8-8-4 4-6-6',
  code_exec_node: 'M10 20l4-16m4 4l4 4-4 4M6 16l-4-4 4-4',
  response_node: 'M5 3v4M3 5h4M6 17v4m-2-2h4m5-16l2.286 6.857L21 12l-5.714 2.143L13 21l-2.286-6.857L5 12l5.714-2.143L13 3z',
  groundedness_node: 'M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z',
}

interface PipelineFlowVizProps {
  nodeStates: Record<string, NodeState>
  nodeLatencies: Record<string, number>
  totalTime?: number
  intentLabel?: string
  confidence?: number
}

function getNodeClasses(state: NodeState) {
  switch (state) {
    case 'completed':
      return {
        border: 'border-emerald-500',
        bg: 'bg-emerald-900/20',
        icon: 'text-emerald-400',
        shadow: '',
      }
    case 'active':
      return {
        border: 'border-blue-500',
        bg: 'bg-blue-900/20',
        icon: 'text-blue-400',
        shadow: 'shadow-[0_0_12px_rgba(37,99,235,0.3)]',
      }
    case 'error':
      return {
        border: 'border-red-500',
        bg: 'bg-red-900/20',
        icon: 'text-red-400',
        shadow: '',
      }
    default:
      return {
        border: 'border-gray-600',
        bg: 'bg-gray-800',
        icon: 'text-gray-500',
        shadow: '',
      }
  }
}

export default function PipelineFlowViz({
  nodeStates,
  nodeLatencies,
  totalTime,
  intentLabel,
  confidence,
}: PipelineFlowVizProps) {
  const scrollRef = useRef<HTMLDivElement>(null)

  return (
    <div
      className="bg-[#1a1a2e] rounded-2xl p-6 sm:p-8 relative overflow-hidden"
      data-testid="pipeline-hero"
    >
      {/* Subtle gradient overlay */}
      <div className="absolute inset-0 bg-gradient-to-br from-blue-900/5 to-transparent pointer-events-none" />

      <div className="relative">
        <div className="text-[11px] font-semibold uppercase tracking-[1.5px] text-gray-500 mb-5">
          10-Node AI Pipeline — Query Execution Flow
        </div>

        {/* Pipeline nodes - horizontal scroll on mobile */}
        <div
          ref={scrollRef}
          className="flex items-center overflow-x-auto snap-x snap-mandatory pb-2 -mx-2 px-2"
          role="list"
          aria-label="AI Pipeline Execution Flow"
          style={{ scrollbarWidth: 'none' }}
        >
          {ALL_NODES.map((node, i) => {
            const state = nodeStates[node] || 'idle'
            const latency = nodeLatencies[node]
            const cls = getNodeClasses(state)
            const iconPath = NODE_ICONS[node]

            return (
              <div key={node} className="flex items-center snap-start" role="listitem">
                {/* Node */}
                <div
                  className="flex flex-col items-center min-w-[80px]"
                  data-testid={`pipeline-node-${node}`}
                  aria-label={`${NODE_LABELS[node]}, ${state}${latency !== undefined ? `, ${latency} milliseconds` : ''}`}
                >
                  <div
                    className={`w-11 h-11 rounded-full border-2 ${cls.border} ${cls.bg} ${cls.shadow} flex items-center justify-center transition-all duration-300`}
                  >
                    <svg
                      className={`w-5 h-5 ${cls.icon} transition-colors duration-300`}
                      fill="none"
                      viewBox="0 0 24 24"
                      stroke="currentColor"
                      strokeWidth={1.5}
                    >
                      <path strokeLinecap="round" strokeLinejoin="round" d={iconPath} />
                    </svg>
                  </div>
                  <div className="text-[9px] text-gray-500 mt-1.5 text-center leading-tight">
                    {NODE_LABELS[node]}
                  </div>
                  <div className="h-4 flex items-center">
                    {state === 'active' && (
                      <span className="text-[9px] font-mono text-blue-400 animate-pulse">...</span>
                    )}
                    {state === 'completed' && latency !== undefined && (
                      <span className="text-[9px] font-mono text-emerald-400">{latency}ms</span>
                    )}
                    {state === 'skipped' && (
                      <span className="text-[9px] text-gray-600">skipped</span>
                    )}
                    {state === 'error' && (
                      <span className="text-[9px] text-red-400">failed</span>
                    )}
                  </div>
                </div>

                {/* Connector line (not after last node) */}
                {i < ALL_NODES.length - 1 && (
                  <div
                    className={`h-[2px] min-w-[12px] flex-1 -mt-5 transition-colors duration-500 ${
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

        {/* Fade gradient for scroll indicator on right */}
        <div className="absolute right-0 top-12 bottom-8 w-8 bg-gradient-to-l from-[#1a1a2e] to-transparent pointer-events-none lg:hidden" />

        {/* Summary bar after animation */}
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

/**
 * Hook: animate pipeline nodes sequentially using real latency data.
 * Delegates to shared useNodeAnimation hook.
 */
export function usePipelineAnimation() {
  const { nodeStates, triggerAnimation: rawTrigger, isAnimating, reset } =
    useNodeAnimation({ nodeIds: ALL_NODES })

  const triggerAnimation = useCallback(
    async (
      completedNodes: string[],
      latencyMs: Record<string, number>,
      failedNode?: string,
    ) => {
      await rawTrigger({ completedNodes, latencyMs, failedNode })
    },
    [rawTrigger],
  )

  return { nodeStates, triggerAnimation, isAnimating, reset } as const
}

export { type NodeState } from '@/hooks/useNodeAnimation'

