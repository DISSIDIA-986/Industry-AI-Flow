/**
 * Shared hook for sequential node animation with proportional timing.
 *
 * Used by PipelineFlowViz, IntentFlowViz, CompactPipelineViz, and
 * AnalysisPipelineViz.  Extracts the common pattern:
 *   idle → active (proportional delay) → completed/skipped/error
 *
 * @see TODOS.md "Extract shared node animation hook (DRY)"
 */

import { useCallback, useRef, useState } from "react";

export type NodeState = "idle" | "active" | "completed" | "skipped" | "error";

function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

interface AnimationConfig {
  /** Ordered list of node IDs to animate through */
  nodeIds: string[];
  /** Total animation duration in ms (default 4000) */
  totalMs?: number;
  /** Minimum per-node delay in ms (default 200) */
  minDelayMs?: number;
}

interface TriggerParams {
  /** Node IDs that completed successfully */
  completedNodes: string[];
  /** Per-node latency in ms (used for proportional timing) */
  latencyMs: Record<string, number>;
  /** If set, this node shows as error and animation stops */
  failedNode?: string;
}

export function useNodeAnimation(config: AnimationConfig) {
  const { nodeIds, totalMs = 4000, minDelayMs = 200 } = config;
  const [nodeStates, setNodeStates] = useState<Record<string, NodeState>>({});
  const animatingRef = useRef(false);
  const [isAnimating, setIsAnimating] = useState(false);

  const triggerAnimation = useCallback(
    async (params: TriggerParams) => {
      const { completedNodes, latencyMs, failedNode } = params;

      // Reject concurrent animations (prevent race condition)
      if (animatingRef.current) return;

      animatingRef.current = true;
      setIsAnimating(true);

      // Reset to idle
      const initial: Record<string, NodeState> = {};
      nodeIds.forEach((id) => {
        initial[id] = "idle";
      });
      setNodeStates(initial);

      // Reduced motion: show final state immediately
      const prefersReduced =
        typeof window !== "undefined" &&
        window.matchMedia("(prefers-reduced-motion: reduce)").matches;

      if (prefersReduced) {
        const final: Record<string, NodeState> = {};
        nodeIds.forEach((id) => {
          final[id] =
            id === failedNode
              ? "error"
              : completedNodes.includes(id)
                ? "completed"
                : "skipped";
        });
        setNodeStates(final);
        animatingRef.current = false;
        setIsAnimating(false);
        return;
      }

      // Proportional animation
      const totalLatency =
        Object.values(latencyMs).reduce((a, b) => a + b, 0) || 1;

      for (const nodeId of nodeIds) {
        if (nodeId === failedNode) {
          setNodeStates((prev) => ({ ...prev, [nodeId]: "error" }));
          break;
        }
        if (!completedNodes.includes(nodeId)) {
          setNodeStates((prev) => ({ ...prev, [nodeId]: "skipped" }));
          continue;
        }

        setNodeStates((prev) => ({ ...prev, [nodeId]: "active" }));
        const nodeMs = latencyMs[nodeId] || 0;
        const delay = Math.max(minDelayMs, (nodeMs / totalLatency) * totalMs);
        await sleep(delay);
        setNodeStates((prev) => ({ ...prev, [nodeId]: "completed" }));
      }

      animatingRef.current = false;
      setIsAnimating(false);
    },
    [nodeIds, totalMs, minDelayMs],
  );

  const reset = useCallback(() => {
    setNodeStates({});
    animatingRef.current = false;
    setIsAnimating(false);
  }, []);

  return { nodeStates, triggerAnimation, isAnimating, reset } as const;
}
