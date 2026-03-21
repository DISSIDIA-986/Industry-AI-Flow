'use client'

/**
 * IntentResultCard — Classification result with keyword highlights,
 * capability score breakdown, and decision path visualization.
 */

import type { IntentClassifyResponse, CapabilityScore } from '@/lib/api-client'
import { INTENT_STYLE } from '@/lib/intent-constants'

interface IntentResultCardProps {
  result: IntentClassifyResponse
  query: string
  borderColor?: string
  label?: string
}

/** Highlight matched keywords in the query text */
function HighlightedQuery({
  query,
  matchedKeywords,
}: {
  query: string
  matchedKeywords: Array<[string, string]> | null
}) {
  if (!matchedKeywords || matchedKeywords.length === 0) {
    return <span>{query}</span>
  }

  // Build set of unique keywords to highlight
  const keywords = [...new Set(matchedKeywords.map(([kw]) => kw))]
    .sort((a, b) => b.length - a.length) // longest first to avoid partial matches

  // Build regex
  const pattern = new RegExp(
    `(${keywords.map((k) => k.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')).join('|')})`,
    'gi',
  )

  const parts = query.split(pattern)
  return (
    <>
      {parts.map((part, i) => {
        const isMatch = keywords.some((kw) => part.toLowerCase() === kw.toLowerCase())
        return isMatch ? (
          <mark key={i} className="bg-purple-100 text-purple-800 px-0.5 rounded">
            {part}
          </mark>
        ) : (
          <span key={i}>{part}</span>
        )
      })}
    </>
  )
}

/** Horizontal bar chart of capability scores */
function CapabilityScoresChart({
  scores,
  winnerId,
}: {
  scores: Record<string, CapabilityScore>
  winnerId: string
}) {
  const entries = Object.entries(scores)
    .filter(([, s]) => s.score > 0)
    .sort((a, b) => b[1].score - a[1].score)

  if (entries.length === 0) return null

  const maxScore = entries[0][1].score

  return (
    <div className="space-y-1.5" data-testid="capability-scores">
      {entries.map(([capId, s]) => {
        const style = INTENT_STYLE[capId] || INTENT_STYLE.unclear_intent
        const isWinner = capId === winnerId
        const widthPct = maxScore > 0 ? (s.score / maxScore) * 100 : 0

        return (
          <div key={capId} className="flex items-center gap-2 text-xs">
            <div className={`w-2 h-2 rounded-full flex-shrink-0 ${style.dot}`} />
            <span
              className={`w-28 truncate ${isWinner ? 'font-semibold text-gray-900' : 'text-gray-500'}`}
            >
              {style.label}
            </span>
            <div className="flex-1 h-2 bg-gray-100 rounded-full overflow-hidden">
              <div
                className={`h-full rounded-full transition-all duration-500 ${
                  isWinner ? style.barColor : 'bg-gray-300'
                }`}
                style={{ width: `${widthPct}%` }}
              />
            </div>
            <span className={`font-mono w-10 text-right ${isWinner ? 'font-semibold text-gray-900' : 'text-gray-400'}`}>
              {s.score.toFixed(1)}
            </span>
            {s.penalized && (
              <span className="text-[9px] text-amber-500 font-medium">-50%</span>
            )}
          </div>
        )
      })}
    </div>
  )
}

export default function IntentResultCard({
  result,
  query,
  borderColor,
  label,
}: IntentResultCardProps) {
  const intentStyle =
    INTENT_STYLE[(result.intent as string) || ''] || INTENT_STYLE.unclear_intent
  const confidencePct = Math.round((result.confidence || 0) * 100)

  // Determine decision path
  const metadata = result.metadata || {}
  const isHeuristic = !metadata.llm_called
  const wasSkipped = confidencePct >= 85

  return (
    <div
      className={`bg-white rounded-xl shadow-sm border border-gray-200 p-5 ${
        borderColor ? `border-t-[3px] ${borderColor}` : ''
      }`}
      data-testid="intent-result-card"
    >
      {label && (
        <div className="text-[11px] font-semibold uppercase tracking-wider text-amber-500 mb-2">
          {label}
        </div>
      )}
      <h3 className="font-medium text-gray-900 mb-4">Classification Result</h3>

      {/* Intent badge */}
      <div className={`rounded-lg p-4 border ${intentStyle.bg} mb-4`}>
        <div className="flex items-center space-x-3 mb-3">
          <div className={`w-4 h-4 rounded-full ${intentStyle.dot}`} />
          <span className={`text-lg font-semibold ${intentStyle.text}`}>
            {intentStyle.label}
          </span>
        </div>
        {/* Confidence bar */}
        <div>
          <div className="flex justify-between text-sm mb-1">
            <span className="text-gray-600">Confidence</span>
            <span className={`font-semibold ${intentStyle.text}`}>{confidencePct}%</span>
          </div>
          <div className="w-full bg-white bg-opacity-60 rounded-full h-2.5">
            <div
              className={`h-2.5 rounded-full transition-all duration-700 ${
                confidencePct >= 80
                  ? 'bg-green-500'
                  : confidencePct >= 60
                    ? 'bg-blue-500'
                    : confidencePct >= 40
                      ? 'bg-yellow-500'
                      : 'bg-red-500'
              }`}
              style={{ width: `${confidencePct}%` }}
            />
          </div>
        </div>
      </div>

      {/* Keyword highlights */}
      {result.matched_keywords && result.matched_keywords.length > 0 && (
        <div className="mb-4">
          <div className="text-[11px] font-semibold uppercase tracking-wider text-gray-400 mb-2">
            Matched Keywords
          </div>
          <div className="text-sm text-gray-700 bg-gray-50 rounded-lg p-3 border border-gray-100">
            <HighlightedQuery query={query} matchedKeywords={result.matched_keywords} />
          </div>
        </div>
      )}

      {/* Decision path */}
      <div className="mb-4">
        <div className="text-[11px] font-semibold uppercase tracking-wider text-gray-400 mb-2">
          Decision Path
        </div>
        <div className="flex flex-wrap gap-1.5">
          <span className="inline-flex items-center gap-1 px-2 py-1 rounded text-[11px] font-medium bg-gray-100 text-gray-600">
            <span
              className={`w-3 h-3 rounded-full text-[8px] text-white flex items-center justify-center ${
                isHeuristic ? 'bg-amber-500' : 'bg-blue-600'
              }`}
            >
              {isHeuristic ? 'H' : 'L'}
            </span>
            {isHeuristic ? `Heuristic: ${confidencePct}%` : `LLM: ${confidencePct}%`}
          </span>
          {wasSkipped && (
            <span className="inline-flex items-center gap-1 px-2 py-1 rounded text-[11px] font-medium bg-gray-100 text-gray-500">
              <span className="w-3 h-3 rounded-full bg-gray-400 text-[8px] text-white flex items-center justify-center">
                ✓
              </span>
              LLM skipped (≥85%)
            </span>
          )}
          <span className="inline-flex items-center gap-1 px-2 py-1 rounded text-[11px] font-medium bg-gray-100 text-gray-600">
            → Direct routing
          </span>
        </div>
      </div>

      {/* Capability scores breakdown */}
      {result.capability_scores && (
        <div className="mb-4">
          <div className="text-[11px] font-semibold uppercase tracking-wider text-gray-400 mb-2">
            Capability Scores
          </div>
          <CapabilityScoresChart
            scores={result.capability_scores}
            winnerId={result.intent || ''}
          />
        </div>
      )}

      {/* Details grid */}
      <div className="grid grid-cols-2 gap-3 text-sm">
        {result.reasoning && (
          <div className="col-span-2">
            <div className="text-gray-500 text-xs mb-0.5">Reasoning</div>
            <div className="text-gray-800">{result.reasoning}</div>
          </div>
        )}
        {result.routing_decision && (
          <>
            <div>
              <div className="text-gray-500 text-xs mb-0.5">Agent</div>
              <div className="text-gray-800 font-medium">
                {(result.routing_decision as Record<string, unknown>).selected_agent as string || 'N/A'}
              </div>
            </div>
            <div>
              <div className="text-gray-500 text-xs mb-0.5">Routing Path</div>
              <div className="text-gray-800">
                {(result.routing_decision as Record<string, unknown>).routing_path as string || 'N/A'}
              </div>
            </div>
          </>
        )}
        <div>
          <div className="text-gray-500 text-xs mb-0.5">Processing Time</div>
          <div className="text-gray-800 font-medium tabular-nums">
            {result.processing_time_ms || 0}ms
          </div>
        </div>
        <div>
          <div className="text-gray-500 text-xs mb-0.5">Clarification</div>
          <div
            className={
              result.clarification_needed ? 'text-yellow-600 font-medium' : 'text-green-600'
            }
          >
            {result.clarification_needed ? 'Yes' : 'No'}
          </div>
        </div>
      </div>
    </div>
  )
}
