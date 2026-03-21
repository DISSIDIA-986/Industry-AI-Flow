"use client";

import { useState, useEffect, useRef } from "react";
import {
  intentApi,
  type IntentClassifyResponse,
  type CapabilityCatalog,
} from "@/lib/api-client";
import { INTENT_STYLE } from "@/lib/intent-constants";
import IntentFlowViz, { useIntentAnimation } from "@/components/IntentFlowViz";
import IntentResultCard from "@/components/IntentResultCard";

// ── Types ──────────────────────────────────────────────────────

interface HistoryEntry {
  query: string;
  intent: string;
  confidence: number;
  timeMs: number;
  timestamp: Date;
}

// ── Page Component ─────────────────────────────────────────────

export default function IntentDebuggerPage() {
  // Query state
  const [query, setQuery] = useState("");
  const [queryB, setQueryB] = useState("");
  const [isClassifying, setIsClassifying] = useState(false);
  const [isClassifyingB, setIsClassifyingB] = useState(false);
  const [result, setResult] = useState<IntentClassifyResponse | null>(null);
  const [resultB, setResultB] = useState<IntentClassifyResponse | null>(null);
  const [lastQuery, setLastQuery] = useState("");
  const [lastQueryB, setLastQueryB] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [errorB, setErrorB] = useState<string | null>(null);

  // UI state
  const [history, setHistory] = useState<HistoryEntry[]>([]);
  const [activeCategory, setActiveCategory] = useState<string | null>(null);
  const [capabilities, setCapabilities] = useState<CapabilityCatalog | null>(null);
  const [isComparing, setIsComparing] = useState(false);

  // Stable session ID per page mount (for conversation replay)
  const sessionIdRef = useRef(`intent-debug-${Date.now()}`);

  // Animation hook
  const { nodeStates, triggerAnimation } = useIntentAnimation();

  // Load capabilities from API (DRY — no hardcoded example queries)
  useEffect(() => {
    intentApi.getCapabilities().then(setCapabilities).catch(() => {});
  }, []);

  // ── Classify handler ──────────────────────────────────────────

  const handleClassify = async (queryText: string, isQueryB = false) => {
    if (!queryText.trim()) return;
    if (isQueryB ? isClassifyingB : isClassifying) return;

    const setLoading = isQueryB ? setIsClassifyingB : setIsClassifying;
    const setRes = isQueryB ? setResultB : setResult;
    const setErr = isQueryB ? setErrorB : setError;
    const setLastQ = isQueryB ? setLastQueryB : setLastQuery;

    setLoading(true);
    setErr(null);
    setLastQ(queryText);
    if (!isQueryB) setQuery(queryText);

    try {
      const sessionId = isQueryB
        ? `intent-debug-b-${Date.now()}`
        : sessionIdRef.current;

      const res = await intentApi.classify({
        query: queryText.trim(),
        session_id: sessionId,
      });
      setRes(res);

      // Trigger animation for the most recent query
      if (res.node_trace && res.node_trace.length > 0) {
        triggerAnimation(res.node_trace);
      }

      // Add to history (only for primary query)
      if (!isQueryB) {
        setHistory((prev) => [
          {
            query: queryText.trim(),
            intent: res.intent || "unknown",
            confidence: res.confidence || 0,
            timeMs: res.processing_time_ms || 0,
            timestamp: new Date(),
          },
          ...prev.slice(0, 9),
        ]);
      }
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Classification failed";
      if (msg.toLowerCase().includes("timeout") || msg.toLowerCase().includes("abort")) {
        setErr("Classification timed out. The cloud LLM may be slow — please try again.");
      } else {
        setErr(msg);
      }
    } finally {
      setLoading(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent, isB = false) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleClassify(isB ? queryB : query, isB);
    }
  };

  // ── Comparison presets ────────────────────────────────────────

  const comparisonPairs = [
    {
      a: "Analyze construction cost trends by region",
      b: "How much does a 10-story building cost in Toronto?",
    },
    {
      a: "Run a Python script to calculate structural load capacity",
      b: "What is the structural load capacity requirement under OSHA?",
    },
  ];

  // ── Build example queries from API capabilities ───────────────

  const exampleGroups: Record<string, { label: string; queries: string[] }> = {};
  if (capabilities) {
    for (const cap of capabilities.capabilities) {
      if (cap.example_queries.length > 0) {
        const style = INTENT_STYLE[cap.id];
        exampleGroups[cap.id] = {
          label: style?.label || cap.name,
          queries: cap.example_queries,
        };
      }
    }
  }

  // ── Derive node latencies from trace ──────────────────────────

  const activeResult = result; // hero shows primary query
  const nodeLatencies: Record<string, number> = {};
  let skippedReason = "";
  if (activeResult?.node_trace) {
    for (const t of activeResult.node_trace) {
      nodeLatencies[t.node_name] = t.duration_ms;
    }
    const completedNodes = activeResult.node_trace.map((t) => t.node_name);
    const skipped = ["clarification_step", "clarification_processing", "error_handling"].filter(
      (n) => !completedNodes.includes(n)
    );
    if (skipped.length > 0) {
      const confPct = Math.round((activeResult.confidence || 0) * 100);
      if (confPct >= 80) {
        skippedReason = `Clarification skipped (confidence ${confPct}% ≥ 80%)`;
      }
    }
  }

  return (
    <div className="max-w-7xl mx-auto p-6 space-y-6">
      {/* Hero — IntentFlowViz */}
      <IntentFlowViz
        nodeStates={nodeStates}
        nodeLatencies={nodeLatencies}
        totalTime={activeResult?.processing_time_ms || undefined}
        intentLabel={
          activeResult?.intent
            ? INTENT_STYLE[activeResult.intent]?.label || activeResult.intent
            : undefined
        }
        confidence={activeResult?.confidence || undefined}
        skippedReason={skippedReason}
      />

      <div className="grid grid-cols-1 lg:grid-cols-5 gap-6">
        {/* ── Left Panel ──────────────────────────────────── */}
        <div className="lg:col-span-2 space-y-4">
          {/* Query Input */}
          <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-4" data-testid="query-input-panel">
            <h3 className="font-medium text-gray-900 mb-3">Test a Query</h3>
            <div className="flex space-x-2">
              <input
                type="text"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                onKeyDown={(e) => handleKeyDown(e)}
                placeholder="Type any query to classify..."
                className="flex-1 px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                disabled={isClassifying}
                data-testid="query-input"
              />
              <button
                onClick={() => handleClassify(query)}
                disabled={isClassifying || !query.trim()}
                className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg text-sm font-medium transition disabled:opacity-50"
                data-testid="query-submit"
              >
                {isClassifying ? "..." : "Go"}
              </button>
            </div>
            {isClassifying && (
              <div className="mt-2 flex items-center space-x-2 text-xs text-blue-600">
                <svg className="animate-spin h-3.5 w-3.5" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                </svg>
                <span>Classifying via cloud LLM... this may take up to 60 seconds.</span>
              </div>
            )}
            {error && (
              <div className="mt-2 text-xs text-red-600 bg-red-50 rounded px-2 py-1">{error}</div>
            )}

            {/* Comparison mode input B */}
            {isComparing && (
              <div className="mt-3 pt-3 border-t border-gray-100">
                <div className="text-[11px] font-semibold uppercase tracking-wider text-amber-500 mb-2">
                  Query B
                </div>
                <div className="flex space-x-2">
                  <input
                    type="text"
                    value={queryB}
                    onChange={(e) => setQueryB(e.target.value)}
                    onKeyDown={(e) => handleKeyDown(e, true)}
                    placeholder="Second query to compare..."
                    className="flex-1 px-3 py-2 border border-amber-300 rounded-lg text-sm focus:ring-2 focus:ring-amber-500 focus:border-amber-500"
                    disabled={isClassifyingB}
                    data-testid="query-input-b"
                  />
                  <button
                    onClick={() => handleClassify(queryB, true)}
                    disabled={isClassifyingB || !queryB.trim()}
                    className="bg-amber-500 hover:bg-amber-600 text-white px-4 py-2 rounded-lg text-sm font-medium transition disabled:opacity-50"
                    data-testid="query-submit-b"
                  >
                    {isClassifyingB ? "..." : "Go"}
                  </button>
                </div>
                {isClassifyingB && (
                  <div className="mt-2 flex items-center space-x-2 text-xs text-amber-600">
                    <svg className="animate-spin h-3.5 w-3.5" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                    </svg>
                    <span>Classifying Query B...</span>
                  </div>
                )}
                {errorB && (
                  <div className="mt-2 text-xs text-red-600 bg-red-50 rounded px-2 py-1">{errorB}</div>
                )}
              </div>
            )}
          </div>

          {/* Example Queries (from API) */}
          <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-4" data-testid="example-queries-panel">
            <h3 className="font-medium text-gray-900 mb-3">Example Queries</h3>
            {Object.keys(exampleGroups).length > 0 ? (
              <>
                <div className="flex flex-wrap gap-1.5 mb-3">
                  {Object.entries(exampleGroups).map(([key, val]) => {
                    const style = INTENT_STYLE[key];
                    return (
                      <button
                        key={key}
                        onClick={() => setActiveCategory(activeCategory === key ? null : key)}
                        className={`text-xs px-2.5 py-1 rounded-full border transition ${
                          activeCategory === key
                            ? `${style?.bg} ${style?.text} font-medium`
                            : "border-gray-200 text-gray-600 hover:bg-gray-50"
                        }`}
                        data-testid={`category-pill-${key}`}
                      >
                        {val.label}
                      </button>
                    );
                  })}
                </div>
                <div className="space-y-1.5 max-h-80 overflow-y-auto">
                  {Object.entries(exampleGroups)
                    .filter(([key]) => !activeCategory || key === activeCategory)
                    .flatMap(([, val]) => val.queries)
                    .map((q, i) => (
                      <button
                        key={i}
                        onClick={() => handleClassify(q)}
                        disabled={isClassifying}
                        className="w-full text-left p-2.5 bg-gray-50 hover:bg-gray-100 rounded-lg text-xs text-gray-700 transition disabled:opacity-50"
                        data-testid="example-query"
                      >
                        {q}
                      </button>
                    ))}
                </div>
              </>
            ) : (
              <div className="text-sm text-gray-400">Loading capabilities...</div>
            )}
          </div>

          {/* Comparison Presets */}
          {isComparing && (
            <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-4" data-testid="comparison-presets">
              <h3 className="font-medium text-gray-900 mb-3">Comparison Pairs</h3>
              <div className="space-y-2">
                {comparisonPairs.map((pair, i) => (
                  <button
                    key={i}
                    onClick={() => {
                      setQuery(pair.a);
                      setQueryB(pair.b);
                      handleClassify(pair.a, false);
                      handleClassify(pair.b, true);
                    }}
                    disabled={isClassifying || isClassifyingB}
                    className="w-full text-left p-3 bg-gray-50 hover:bg-gray-100 rounded-lg text-xs text-gray-700 transition disabled:opacity-50 space-y-1"
                  >
                    <div><span className="text-blue-600 font-medium">A:</span> {pair.a}</div>
                    <div><span className="text-amber-600 font-medium">B:</span> {pair.b}</div>
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* History */}
          {history.length > 0 && (
            <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-4" data-testid="history-panel">
              <h3 className="font-medium text-gray-900 mb-3">
                Classification History ({history.length})
              </h3>
              <div className="space-y-1.5 max-h-48 overflow-y-auto">
                {history.map((entry, i) => {
                  const s = INTENT_STYLE[entry.intent] || INTENT_STYLE.unclear_intent;
                  return (
                    <div
                      key={i}
                      onClick={() => handleClassify(entry.query)}
                      className="flex items-center justify-between text-xs p-2 bg-gray-50 rounded-lg cursor-pointer hover:bg-gray-100"
                      data-testid="history-entry"
                    >
                      <span className="truncate flex-1 mr-2 text-gray-700">{entry.query}</span>
                      <div className="flex items-center space-x-2 flex-shrink-0">
                        <span className={`${s.dot} w-1.5 h-1.5 rounded-full`} />
                        <span className="text-gray-500 tabular-nums">{Math.round(entry.confidence * 100)}%</span>
                        <span className="text-gray-400 tabular-nums">{entry.timeMs}ms</span>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          )}
        </div>

        {/* ── Right Panel ─────────────────────────────────── */}
        <div className="lg:col-span-3 space-y-4">
          {/* Comparison toggle */}
          <div className="flex items-center gap-3 bg-white rounded-xl shadow-sm border border-gray-200 px-4 py-3" data-testid="comparison-toggle">
            <label className="text-sm font-medium text-gray-700">Comparison Mode</label>
            <button
              onClick={() => setIsComparing(!isComparing)}
              className={`relative w-10 h-[22px] rounded-full transition-colors ${
                isComparing ? "bg-blue-600" : "bg-gray-300"
              }`}
              role="switch"
              aria-checked={isComparing}
              data-testid="comparison-switch"
            >
              <span
                className={`absolute top-[2px] w-[18px] h-[18px] bg-white rounded-full transition-transform ${
                  isComparing ? "translate-x-[20px]" : "translate-x-[2px]"
                }`}
              />
            </button>
            <span className="text-xs text-gray-500">Compare two queries side-by-side</span>
          </div>

          {/* Results */}
          {isComparing ? (
            // Comparison mode: side-by-side
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {result ? (
                <IntentResultCard
                  result={result}
                  query={lastQuery}
                  borderColor="border-t-blue-600"
                  label="Query A"
                />
              ) : (
                <div className="bg-white rounded-xl shadow-sm border border-gray-200 border-t-[3px] border-t-blue-600 p-5">
                  <div className="text-[11px] font-semibold uppercase tracking-wider text-blue-600 mb-2">Query A</div>
                  <p className="text-sm text-gray-500">Submit Query A to see results.</p>
                </div>
              )}
              {resultB ? (
                <IntentResultCard
                  result={resultB}
                  query={lastQueryB}
                  borderColor="border-t-amber-500"
                  label="Query B"
                />
              ) : (
                <div className="bg-white rounded-xl shadow-sm border border-gray-200 border-t-[3px] border-t-amber-500 p-5">
                  <div className="text-[11px] font-semibold uppercase tracking-wider text-amber-500 mb-2">Query B</div>
                  <p className="text-sm text-gray-500">Submit Query B to compare.</p>
                </div>
              )}
            </div>
          ) : (
            // Single mode
            result ? (
              <IntentResultCard result={result} query={lastQuery} />
            ) : (
              <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-5">
                <h3 className="font-medium text-gray-900 mb-3">Classification Result</h3>
                <p className="text-sm text-gray-500">
                  Submit a query to watch the AI think — the pipeline above will animate with real timing data.
                </p>
              </div>
            )
          )}

          {/* System Capabilities */}
          <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-5" data-testid="capabilities-panel">
            <h3 className="font-medium text-gray-900 mb-3">
              System Capabilities
              {capabilities && (
                <span className="ml-2 text-xs text-gray-400 font-normal">
                  {capabilities.total} registered
                </span>
              )}
            </h3>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              {(capabilities?.capabilities || []).map((cap) => {
                const style = INTENT_STYLE[cap.id] || INTENT_STYLE.unclear_intent;
                return (
                  <div key={cap.id} className={`rounded-lg p-3 border ${style.bg}`}>
                    <div className="flex items-center space-x-2 mb-1.5">
                      <div className={`w-2 h-2 rounded-full ${style.dot}`} />
                      <span className={`text-sm font-medium ${style.text}`}>{cap.name}</span>
                    </div>
                    <p className="text-xs text-gray-600 mb-2 line-clamp-2">{cap.description}</p>
                    {cap.example_queries.length > 0 && (
                      <button
                        onClick={() => handleClassify(cap.example_queries[0])}
                        className="text-[10px] text-gray-500 hover:text-gray-700 underline"
                        disabled={isClassifying}
                      >
                        Try: &quot;{cap.example_queries[0].slice(0, 50)}...&quot;
                      </button>
                    )}
                  </div>
                );
              })}
              {!capabilities && (
                <div className="col-span-2 text-sm text-gray-400">
                  Loading capabilities...
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
