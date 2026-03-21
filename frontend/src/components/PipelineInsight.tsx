"use client";

/**
 * PipelineInsight — Visualizes the AI workflow pipeline execution.
 * Shows intent classification, confidence, routing decision, and node latencies.
 */

const INTENT_CONFIG: Record<string, { label: string; dotColor: string; bgColor: string; textColor: string }> = {
  knowledge_retrieval: { label: "Knowledge Retrieval", dotColor: "bg-blue-500", bgColor: "bg-blue-50", textColor: "text-blue-700" },
  cost_estimation:     { label: "Cost Estimation",     dotColor: "bg-green-500", bgColor: "bg-green-50", textColor: "text-green-700" },
  data_analysis:       { label: "Data Analysis",       dotColor: "bg-purple-500", bgColor: "bg-purple-50", textColor: "text-purple-700" },
  document_processing: { label: "Document Processing", dotColor: "bg-orange-500", bgColor: "bg-orange-50", textColor: "text-orange-700" },
  code_execution:      { label: "Code Execution",      dotColor: "bg-red-500", bgColor: "bg-red-50", textColor: "text-red-700" },
  unclear_intent:      { label: "Unclear Intent",      dotColor: "bg-gray-400", bgColor: "bg-gray-50", textColor: "text-gray-600" },
};

const NODE_LABELS: Record<string, string> = {
  intent_node: "Intent Classification",
  safety_node: "Safety Check",
  cost_estimation_node: "Cost Estimation",
  retrieval_node: "Document Retrieval",
  rerank_node: "Reranking",
  prompt_node: "Prompt Selection",
  route_node: "Provider Routing",
  code_exec_node: "Code Execution",
  response_node: "Response Generation",
  groundedness_node: "Groundedness Check",
};

export const ALL_NODES = [
  "intent_node", "safety_node", "cost_estimation_node", "retrieval_node",
  "rerank_node", "prompt_node", "route_node", "code_exec_node",
  "response_node", "groundedness_node",
];

interface PipelineInsightProps {
  metadata: Record<string, unknown> | null | undefined;
  loading: boolean;
}

function getConfidenceColor(confidence: number): string {
  if (confidence >= 0.8) return "bg-green-500";
  if (confidence >= 0.6) return "bg-blue-500";
  if (confidence >= 0.4) return "bg-yellow-500";
  return "bg-red-500";
}

function getConfidenceLabel(confidence: number): string {
  if (confidence >= 0.8) return "High";
  if (confidence >= 0.6) return "Good";
  if (confidence >= 0.4) return "Moderate";
  return "Low";
}

export default function PipelineInsight({ metadata, loading }: PipelineInsightProps) {
  if (loading) {
    return (
      <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-4">
        <h3 className="font-medium text-gray-900 mb-3">AI Pipeline</h3>
        <div className="flex items-center space-x-2 text-sm text-gray-500">
          <div className="w-3 h-3 border-2 border-blue-500 border-t-transparent rounded-full animate-spin"></div>
          <span>Processing query...</span>
        </div>
      </div>
    );
  }

  if (!metadata) {
    return (
      <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-4">
        <h3 className="font-medium text-gray-900 mb-3">AI Pipeline</h3>
        <p className="text-sm text-gray-500">
          Send a query to see the AI pipeline in action.
        </p>
        <div className="mt-3 space-y-1.5 text-xs text-gray-400">
          {ALL_NODES.map((node) => (
            <div key={node} className="flex items-center space-x-2">
              <div className="w-1.5 h-1.5 rounded-full bg-gray-300"></div>
              <span>{NODE_LABELS[node] || node}</span>
            </div>
          ))}
        </div>
      </div>
    );
  }

  const intent = (metadata.intent as string) || "unknown";
  const confidence = (metadata.intent_confidence as number) || (metadata.confidence as number) || 0;
  const intentSource = (metadata.intent_source as string) || "classifier";
  const completedNodes = (metadata.completed_nodes as string[]) || [];
  const nodeLatency = (metadata.node_latency_ms as Record<string, number>) || {};
  const pipelineStatus = (metadata.pipeline_status as string) || "completed";
  const providerUsed = (metadata.provider_used as string) || "";

  const intentCfg = INTENT_CONFIG[intent] || INTENT_CONFIG.unclear_intent;
  const confidencePct = Math.round(confidence * 100);
  const totalLatency = Object.values(nodeLatency).reduce((a, b) => a + b, 0);

  return (
    <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-4">
      <div className="flex items-center justify-between mb-3">
        <h3 className="font-medium text-gray-900">AI Pipeline</h3>
        <span className={`text-xs px-1.5 py-0.5 rounded ${
          pipelineStatus === "completed" ? "bg-green-100 text-green-700" : "bg-red-100 text-red-700"
        }`}>
          {pipelineStatus}
        </span>
      </div>

      {/* Intent Badge */}
      <div className={`rounded-lg p-3 mb-3 ${intentCfg.bgColor}`}>
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <div className={`w-2.5 h-2.5 rounded-full ${intentCfg.dotColor}`}></div>
            <span className={`text-sm font-medium ${intentCfg.textColor}`}>
              {intentCfg.label}
            </span>
          </div>
          <span className="text-xs text-gray-500">{intentSource}</span>
        </div>

        {/* Confidence Bar */}
        <div className="mt-2">
          <div className="flex items-center justify-between text-xs mb-1">
            <span className="text-gray-600">Confidence</span>
            <span className={`font-medium ${intentCfg.textColor}`}>
              {confidencePct}% ({getConfidenceLabel(confidence)})
            </span>
          </div>
          <div className="w-full bg-gray-200 rounded-full h-1.5">
            <div
              className={`h-1.5 rounded-full transition-all duration-500 ${getConfidenceColor(confidence)}`}
              style={{ width: `${confidencePct}%` }}
            ></div>
          </div>
        </div>
      </div>

      {/* Routing Info */}
      {providerUsed && (
        <div className="text-xs text-gray-500 mb-3 flex items-center justify-between">
          <span>Provider: <span className="font-medium text-gray-700">{providerUsed}</span></span>
          {totalLatency > 0 && (
            <span>Total: <span className="font-medium text-gray-700">{totalLatency}ms</span></span>
          )}
        </div>
      )}

      {/* Pipeline Nodes */}
      <div className="space-y-1">
        <div className="text-xs font-medium text-gray-500 mb-1">Pipeline Nodes</div>
        {ALL_NODES.map((node) => {
          const completed = completedNodes.includes(node);
          const latency = nodeLatency[node];
          return (
            <div key={node} className="flex items-center justify-between text-xs py-0.5">
              <div className="flex items-center space-x-1.5">
                {completed ? (
                  <svg className="w-3 h-3 text-green-500" fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                  </svg>
                ) : (
                  <div className="w-3 h-3 flex items-center justify-center">
                    <div className="w-1.5 h-1.5 rounded-full bg-gray-300"></div>
                  </div>
                )}
                <span className={completed ? "text-gray-700" : "text-gray-400"}>
                  {NODE_LABELS[node] || node}
                </span>
              </div>
              {latency !== undefined && (
                <span className="text-gray-400 tabular-nums">{latency}ms</span>
              )}
              {!completed && latency === undefined && (
                <span className="text-gray-300 text-[10px]">skipped</span>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
