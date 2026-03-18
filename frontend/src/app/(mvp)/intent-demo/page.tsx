"use client";

import { useState, useEffect } from "react";
import { intentApi, type IntentClassifyResponse, type CapabilityCatalog } from "@/lib/api-client";

// ── Intent display config ──────────────────────────────────────

const INTENT_STYLE: Record<string, { label: string; dot: string; bg: string; text: string }> = {
  knowledge_retrieval: { label: "Knowledge Retrieval", dot: "bg-blue-500", bg: "bg-blue-50 border-blue-200", text: "text-blue-700" },
  cost_estimation:     { label: "Cost Estimation",     dot: "bg-green-500", bg: "bg-green-50 border-green-200", text: "text-green-700" },
  data_analysis:       { label: "Data Analysis",       dot: "bg-purple-500", bg: "bg-purple-50 border-purple-200", text: "text-purple-700" },
  document_processing: { label: "Document Processing", dot: "bg-orange-500", bg: "bg-orange-50 border-orange-200", text: "text-orange-700" },
  code_execution:      { label: "Code Execution",      dot: "bg-red-500", bg: "bg-red-50 border-red-200", text: "text-red-700" },
  unclear_intent:      { label: "Unclear",             dot: "bg-gray-400", bg: "bg-gray-50 border-gray-200", text: "text-gray-600" },
};

const EXAMPLE_QUERIES: Record<string, { label: string; queries: string[] }> = {
  knowledge_retrieval: {
    label: "RAG Knowledge",
    queries: [
      "What are the fall protection requirements under Ontario Regulation 213/91?",
      "What safety equipment must workers wear according to OSHA 29 CFR 1926?",
      "How does the National Building Code of Canada define fire compartment?",
    ],
  },
  cost_estimation: {
    label: "Cost Estimation",
    queries: [
      "How much does a 10-story commercial office building cost in Toronto?",
      "Estimate the construction cost for a residential project with 5 floors and 20,000 sqft.",
      "What is the typical budget overrun percentage for healthcare projects?",
    ],
  },
  data_analysis: {
    label: "Data Analysis",
    queries: [
      "Analyze the trend of construction costs over the past 5 years.",
      "Create a visualization comparing project budgets by location.",
      "Show me statistics on cost overruns for different project types.",
    ],
  },
  document_processing: {
    label: "Document Processing",
    queries: [
      "Upload and scan this PDF document for text extraction using OCR.",
      "Process the uploaded image and extract text from the building permit.",
    ],
  },
  code_execution: {
    label: "Code Execution",
    queries: [
      "Run a Python script to calculate the structural load capacity.",
      "Execute a computation to determine material requirements for a 50m bridge span.",
    ],
  },
};

const PIPELINE_NODES = [
  "Input Preprocessing", "Context Enrichment", "Intent Classification",
  "Confidence Evaluation", "Routing Decision", "Prompt Preparation",
  "Agent Dispatch", "Response Processing",
];

// ── Types ──────────────────────────────────────────────────────

interface HistoryEntry {
  query: string;
  intent: string;
  confidence: number;
  timeMs: number;
  timestamp: Date;
}

// ── Component ──────────────────────────────────────────────────

export default function IntentDemoPage() {
  const [query, setQuery] = useState("");
  const [isClassifying, setIsClassifying] = useState(false);
  const [result, setResult] = useState<IntentClassifyResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [history, setHistory] = useState<HistoryEntry[]>([]);
  const [activeCategory, setActiveCategory] = useState<string | null>(null);
  const [capabilities, setCapabilities] = useState<CapabilityCatalog | null>(null);

  useEffect(() => {
    intentApi.getCapabilities().then(setCapabilities).catch(() => {});
  }, []);

  const handleClassify = async (queryText: string) => {
    if (!queryText.trim() || isClassifying) return;
    setIsClassifying(true);
    setError(null);
    setQuery(queryText);

    try {
      const res = await intentApi.classify({
        query: queryText.trim(),
        session_id: `intent-demo-${Date.now()}`,
      });
      setResult(res);
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
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Classification failed";
      if (msg.toLowerCase().includes("timeout") || msg.toLowerCase().includes("abort")) {
        setError("Classification timed out. The cloud LLM may be slow — please try again.");
      } else {
        setError(msg);
      }
    } finally {
      setIsClassifying(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleClassify(query);
    }
  };

  const intentStyle = INTENT_STYLE[(result?.intent as string) || ""] || INTENT_STYLE.unclear_intent;
  const confidencePct = Math.round((result?.confidence || 0) * 100);

  return (
    <div className="max-w-7xl mx-auto p-6 space-y-6">
      {/* Hero */}
      <div className="bg-gradient-to-r from-blue-600 to-indigo-700 rounded-2xl p-6 text-white">
        <div className="text-xs font-medium uppercase tracking-wider opacity-80 mb-1">
          11-Node LangGraph StateGraph
        </div>
        <h1 className="text-2xl font-bold mb-2">AI Intent Classification Engine</h1>
        <p className="text-blue-100 text-sm">
          See how the system understands and routes your queries to the right capability.
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-5 gap-6">
        {/* Left Panel — Input & Examples */}
        <div className="lg:col-span-2 space-y-4">
          {/* Custom query input */}
          <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-4">
            <h3 className="font-medium text-gray-900 mb-3">Test a Query</h3>
            <div className="flex space-x-2">
              <input
                type="text"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder="Type any query to classify..."
                className="flex-1 px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                disabled={isClassifying}
              />
              <button
                onClick={() => handleClassify(query)}
                disabled={isClassifying || !query.trim()}
                className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg text-sm font-medium transition disabled:opacity-50"
              >
                {isClassifying ? "..." : "Go"}
              </button>
            </div>
            {isClassifying && (
              <div className="mt-2 flex items-center space-x-2 text-xs text-blue-600">
                <svg className="animate-spin h-3.5 w-3.5" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"></path>
                </svg>
                <span>Classifying via cloud LLM... this may take up to 60 seconds.</span>
              </div>
            )}
            {error && (
              <div className="mt-2 text-xs text-red-600 bg-red-50 rounded px-2 py-1">{error}</div>
            )}
          </div>

          {/* Example queries by category */}
          <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-4">
            <h3 className="font-medium text-gray-900 mb-3">Example Queries</h3>
            <div className="flex flex-wrap gap-1.5 mb-3">
              {Object.entries(EXAMPLE_QUERIES).map(([key, val]) => {
                const style = INTENT_STYLE[key];
                return (
                  <button
                    key={key}
                    onClick={() => setActiveCategory(activeCategory === key ? null : key)}
                    className={`text-xs px-2.5 py-1 rounded-full border transition ${
                      activeCategory === key
                        ? `${style.bg} ${style.text} font-medium`
                        : "border-gray-200 text-gray-600 hover:bg-gray-50"
                    }`}
                  >
                    {val.label}
                  </button>
                );
              })}
            </div>
            <div className="space-y-1.5 max-h-80 overflow-y-auto">
              {Object.entries(EXAMPLE_QUERIES)
                .filter(([key]) => !activeCategory || key === activeCategory)
                .flatMap(([, val]) => val.queries)
                .map((q, i) => (
                  <button
                    key={i}
                    onClick={() => handleClassify(q)}
                    disabled={isClassifying}
                    className="w-full text-left p-2.5 bg-gray-50 hover:bg-gray-100 rounded-lg text-xs text-gray-700 transition disabled:opacity-50"
                  >
                    {q}
                  </button>
                ))}
            </div>
          </div>

          {/* Pipeline flow */}
          <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-4">
            <h3 className="font-medium text-gray-900 mb-3">Intent Workflow Pipeline</h3>
            <div className="flex flex-wrap gap-1">
              {PIPELINE_NODES.map((node, i) => (
                <div key={node} className="flex items-center">
                  <span className={`text-[10px] px-2 py-1 rounded ${
                    result && i <= 4
                      ? "bg-green-100 text-green-700"
                      : "bg-gray-100 text-gray-500"
                  }`}>
                    {node}
                  </span>
                  {i < PIPELINE_NODES.length - 1 && (
                    <span className="text-gray-300 mx-0.5 text-xs">&rarr;</span>
                  )}
                </div>
              ))}
            </div>
          </div>

          {/* History */}
          {history.length > 0 && (
            <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-4">
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
                    >
                      <span className="truncate flex-1 mr-2 text-gray-700">{entry.query}</span>
                      <div className="flex items-center space-x-2 flex-shrink-0">
                        <span className={`${s.dot} w-1.5 h-1.5 rounded-full`}></span>
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

        {/* Right Panel — Results & Capabilities */}
        <div className="lg:col-span-3 space-y-4">
          {/* Classification Result */}
          {result ? (
            <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-5">
              <h3 className="font-medium text-gray-900 mb-4">Classification Result</h3>

              {/* Intent badge */}
              <div className={`rounded-lg p-4 border ${intentStyle.bg} mb-4`}>
                <div className="flex items-center space-x-3 mb-3">
                  <div className={`w-4 h-4 rounded-full ${intentStyle.dot}`}></div>
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
                        confidencePct >= 80 ? "bg-green-500" :
                        confidencePct >= 60 ? "bg-blue-500" :
                        confidencePct >= 40 ? "bg-yellow-500" : "bg-red-500"
                      }`}
                      style={{ width: `${confidencePct}%` }}
                    ></div>
                  </div>
                </div>
              </div>

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
                        {(result.routing_decision as Record<string, unknown>).selected_agent as string || "N/A"}
                      </div>
                    </div>
                    <div>
                      <div className="text-gray-500 text-xs mb-0.5">Routing Path</div>
                      <div className="text-gray-800">
                        {(result.routing_decision as Record<string, unknown>).routing_path as string || "N/A"}
                      </div>
                    </div>
                  </>
                )}
                <div>
                  <div className="text-gray-500 text-xs mb-0.5">Processing Time</div>
                  <div className="text-gray-800 font-medium tabular-nums">{result.processing_time_ms || 0}ms</div>
                </div>
                <div>
                  <div className="text-gray-500 text-xs mb-0.5">Clarification Needed</div>
                  <div className={result.clarification_needed ? "text-yellow-600 font-medium" : "text-green-600"}>
                    {result.clarification_needed ? "Yes" : "No"}
                  </div>
                </div>
              </div>
            </div>
          ) : (
            <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-5">
              <h3 className="font-medium text-gray-900 mb-3">Classification Result</h3>
              <p className="text-sm text-gray-500">
                Click an example query or type your own to see how the system classifies it.
              </p>
            </div>
          )}

          {/* System Capabilities */}
          <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-5">
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
                      <div className={`w-2 h-2 rounded-full ${style.dot}`}></div>
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
