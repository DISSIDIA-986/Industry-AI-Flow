"use client";

/**
 * CompactPipelineViz — Vertical animated pipeline for the Workflow Chat sidebar.
 * Dark background, SVG node icons, sequential animation during query,
 * snaps to real data on response. response_node holds "active" with elapsed
 * timer until the API responds.
 */

import { useState, useRef, useEffect } from "react";
import { ALL_NODES } from "./PipelineInsight";
import { NODE_LABELS, NODE_ICONS } from "./PipelineFlowViz";

type NodeState = "idle" | "active" | "completed" | "skipped" | "error";

function stateClasses(state: NodeState) {
  switch (state) {
    case "completed":
      return { dot: "bg-emerald-400", text: "text-gray-300", icon: "text-emerald-400" };
    case "active":
      return { dot: "bg-blue-400 animate-pulse", text: "text-blue-300", icon: "text-blue-400" };
    case "error":
      return { dot: "bg-red-400", text: "text-red-300", icon: "text-red-400" };
    case "skipped":
      return { dot: "bg-gray-600", text: "text-gray-500", icon: "text-gray-600" };
    default:
      return { dot: "bg-gray-600", text: "text-gray-500", icon: "text-gray-600" };
  }
}

interface CompactPipelineVizProps {
  metadata: Record<string, unknown> | null | undefined;
  loading: boolean;
}

export default function CompactPipelineViz({
  metadata,
  loading,
}: CompactPipelineVizProps) {
  const [nodeStates, setNodeStates] = useState<Record<string, NodeState>>({});
  const [elapsed, setElapsed] = useState<number>(0);
  const animatingRef = useRef(false);
  const loadStartRef = useRef<number>(0);
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // Start loading animation when query begins
  useEffect(() => {
    if (loading && !animatingRef.current) {
      animatingRef.current = true;
      loadStartRef.current = Date.now();
      setElapsed(0);

      // Start elapsed timer
      timerRef.current = setInterval(() => {
        setElapsed(Date.now() - loadStartRef.current);
      }, 100);

      // Run pre-response animation
      runLoadingAnimation();
    }

    if (!loading && animatingRef.current) {
      // Response arrived — stop timer, snap to real data
      animatingRef.current = false;
      if (timerRef.current) clearInterval(timerRef.current);
    }

    return () => {
      if (timerRef.current) clearInterval(timerRef.current);
    };
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [loading]);

  // Snap to real metadata when response arrives
  useEffect(() => {
    if (!loading && metadata) {
      snapToReal(metadata);
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [loading, metadata]);

  async function runLoadingAnimation() {
    const initial: Record<string, NodeState> = {};
    ALL_NODES.forEach((n) => { initial[n] = "idle"; });
    setNodeStates(initial);

    // Animate first ~7 nodes quickly, then hold response_node as active
    const preResponseNodes = ALL_NODES.slice(0, -2); // all except response + groundedness
    for (const node of preResponseNodes) {
      if (!animatingRef.current) return;
      setNodeStates((prev) => ({ ...prev, [node]: "active" }));
      await sleep(350);
      if (!animatingRef.current) return;
      setNodeStates((prev) => ({ ...prev, [node]: "completed" }));
    }

    // Hold response_node as active until real data arrives
    if (animatingRef.current) {
      setNodeStates((prev) => ({ ...prev, response_node: "active" }));
    }
  }

  function snapToReal(meta: Record<string, unknown>) {
    let completedNodes = (meta.completed_nodes as string[]) || [];

    // Handle intent_workflow responses that don't have completed_nodes
    // (same pattern as simple-dashboard/page.tsx:176)
    if (completedNodes.length === 0 && meta.workflow_runner === "intent_workflow") {
      const agentType = (meta.agent_type as string) || (meta.selected_agent as string) || "";
      const agentStatus = (meta.agent_execution_status as string) || "";
      const intent = (meta.intent as string) || "";
      const inferred: string[] = ["intent_node", "safety_node", "route_node"];
      if (agentStatus === "ok") {
        if (agentType === "rag_agent" || intent === "knowledge_retrieval") {
          inferred.push("retrieval_node", "rerank_node", "prompt_node", "response_node", "groundedness_node");
        } else if (intent === "cost_estimation") {
          inferred.push("cost_estimation_node", "response_node");
        } else if (intent === "data_analysis") {
          inferred.push("code_exec_node", "response_node");
        } else {
          inferred.push("response_node");
        }
      }
      completedNodes = inferred;
    }

    const final: Record<string, NodeState> = {};
    ALL_NODES.forEach((n) => {
      final[n] = completedNodes.includes(n) ? "completed" : "skipped";
    });
    setNodeStates(final);
  }

  // Determine display data
  const completedNodes = metadata
    ? (metadata.completed_nodes as string[]) || []
    : [];
  const nodeLatency = metadata
    ? (metadata.node_latency_ms as Record<string, number>) || {}
    : {};
  const pipelineStatus = metadata
    ? (metadata.pipeline_status as string) || "completed"
    : "";
  const totalLatency = Object.values(nodeLatency).reduce(
    (a, b) => a + b,
    0,
  );

  const hasData = !loading && metadata && completedNodes.length > 0;

  return (
    <div
      className="bg-[#1a1a2e] rounded-xl p-3 flex-shrink-0"
      data-testid="compact-pipeline"
    >
      {/* Header */}
      <div className="flex items-center justify-between mb-2">
        <h3 className="text-xs font-semibold text-gray-400 uppercase tracking-wider">
          Pipeline
        </h3>
        {hasData && (
          <span
            className={`text-[10px] px-1.5 py-0.5 rounded ${
              pipelineStatus === "completed"
                ? "bg-emerald-900/40 text-emerald-400"
                : "bg-red-900/40 text-red-400"
            }`}
          >
            {pipelineStatus}
          </span>
        )}
        {loading && (
          <span className="text-[10px] text-blue-400">
            {(elapsed / 1000).toFixed(1)}s
          </span>
        )}
      </div>

      {/* Nodes */}
      <div className="space-y-0.5">
        {ALL_NODES.map((node) => {
          const state = nodeStates[node] || "idle";
          const cls = stateClasses(state);
          const latency = nodeLatency[node];
          const isResponseActive = node === "response_node" && state === "active" && loading;

          return (
            <div
              key={node}
              className="flex items-center gap-1.5 py-0.5"
              data-testid={`pipeline-node-${node}`}
            >
              {/* Icon */}
              <svg
                className={`w-3.5 h-3.5 flex-shrink-0 ${cls.icon}`}
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
                strokeWidth={1.5}
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  d={NODE_ICONS[node] || ""}
                />
              </svg>

              {/* Label */}
              <span className={`text-[11px] flex-1 ${cls.text}`}>
                {NODE_LABELS[node] || node}
              </span>

              {/* Status */}
              {isResponseActive ? (
                <span className="text-[10px] text-blue-400 tabular-nums animate-pulse">
                  {(elapsed / 1000).toFixed(1)}s
                </span>
              ) : state === "completed" && latency !== undefined ? (
                <span className="text-[10px] text-gray-500 tabular-nums">
                  {latency}ms
                </span>
              ) : state === "skipped" && hasData ? (
                <span className="text-[10px] text-gray-600">N/A</span>
              ) : null}
            </div>
          );
        })}
      </div>

      {/* Total latency */}
      {hasData && totalLatency > 0 && (
        <div className="mt-2 pt-1.5 border-t border-gray-700/50 flex items-center justify-between">
          <span className="text-[10px] text-gray-500">Total</span>
          <span className="text-[10px] text-gray-400 tabular-nums font-medium">
            {totalLatency}ms
          </span>
        </div>
      )}

      {/* Idle state */}
      {!loading && !metadata && (
        <p className="text-[10px] text-gray-600 mt-1">
          Send a query to see the pipeline in action.
        </p>
      )}
    </div>
  );
}

function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}
