#!/usr/bin/env python3
"""Parameter sweep for RAG benchmark to surface influential factors."""

from __future__ import annotations

import argparse
import json
import statistics
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.testing.run_rag_random_benchmark import run_benchmark

DEFAULT_OUTPUT_PATH = "logs/rag_factor_sweep_report.json"


def _parse_int_list(raw: str) -> List[int]:
    values: List[int] = []
    for token in str(raw or "").split(","):
        token = token.strip()
        if not token:
            continue
        values.append(int(token))
    return values


def _parse_float_list(raw: str) -> List[float]:
    values: List[float] = []
    for token in str(raw or "").split(","):
        token = token.strip()
        if not token:
            continue
        values.append(float(token))
    return values


def _safe_mean(values: Iterable[float]) -> float:
    vals = [float(v) for v in values]
    if not vals:
        return 0.0
    return float(statistics.fmean(vals))


def _objective_score(report: Dict[str, Any]) -> float:
    hybrid = report["retrieval_metrics"]["hybrid"]
    workflow = report["workflow_metrics"]
    repeat_penalty = float(workflow.get("follow_up_repeat_rate", 0.0))
    return round(
        (
            0.30 * float(hybrid["mrr"])
            + 0.20 * float(hybrid["hit_at_k"])
            + 0.20 * float(workflow["source_hit_rate"])
            + 0.10 * float(workflow["follow_up_source_hit_rate"])
            + 0.08 * float(workflow["non_echo_rate"])
            + 0.07 * float(workflow.get("avg_rouge_l_f1", 0.0))
            + 0.05 * max(0.0, 1.0 - repeat_penalty)
        ),
        6,
    )


def _summarize_factor_effects(
    successful_runs: List[Dict[str, Any]],
) -> Dict[str, Any]:
    if not successful_runs:
        return {}

    overall_mean = _safe_mean(item["objective_score"] for item in successful_runs)
    factor_fields = (
        "top_k",
        "hybrid_vector_weight",
        "workflow_query_rewrite_count",
        "conversation_turns",
    )
    summary: Dict[str, Any] = {}

    for factor in factor_fields:
        buckets: Dict[str, List[float]] = {}
        for row in successful_runs:
            key = str(row["factors"][factor])
            buckets.setdefault(key, []).append(float(row["objective_score"]))

        values: Dict[str, Any] = {}
        for key, scores in sorted(buckets.items(), key=lambda item: item[0]):
            mean_score = _safe_mean(scores)
            values[key] = {
                "runs": len(scores),
                "mean_objective": round(mean_score, 6),
                "delta_vs_global_mean": round(mean_score - overall_mean, 6),
            }
        summary[factor] = values

    return {
        "global_mean_objective": round(overall_mean, 6),
        "effects": summary,
    }


def run_sweep(
    *,
    sample_size: int,
    seeds: List[int],
    top_k_values: List[int],
    hybrid_vector_weights: List[float],
    workflow_query_rewrite_counts: List[int],
    conversation_turn_values: List[int],
    sampling_mode: str,
    query_style_mode: str,
    base_url: str,
    route_mode: str,
    timeout: int,
    min_content_chars: int,
    max_chunk_rows: int,
    workflow_request_interval_ms: int,
    workflow_transport: str,
) -> Dict[str, Any]:
    started = time.perf_counter()
    runs: List[Dict[str, Any]] = []

    run_id = 0
    for seed in seeds:
        for top_k in top_k_values:
            for vector_weight in hybrid_vector_weights:
                bm25_weight = max(0.0, round(1.0 - float(vector_weight), 6))
                for rewrite_count in workflow_query_rewrite_counts:
                    for conversation_turns in conversation_turn_values:
                        run_id += 1
                        factors = {
                            "seed": int(seed),
                            "top_k": int(top_k),
                            "hybrid_vector_weight": float(vector_weight),
                            "hybrid_bm25_weight": float(bm25_weight),
                            "workflow_query_rewrite_count": int(rewrite_count),
                            "conversation_turns": int(conversation_turns),
                        }
                        try:
                            report = run_benchmark(
                                sample_size=sample_size,
                                seed=int(seed),
                                top_k=max(1, int(top_k)),
                                min_content_chars=min_content_chars,
                                max_chunk_rows=max_chunk_rows,
                                base_url=base_url,
                                route_mode=route_mode,
                                timeout=timeout,
                                sampling_mode=sampling_mode,
                                query_style_mode=query_style_mode,
                                hybrid_vector_weight=float(vector_weight),
                                hybrid_bm25_weight=float(bm25_weight),
                                workflow_enable_query_rewrite=int(rewrite_count) > 0,
                                workflow_query_rewrite_count=max(0, int(rewrite_count)),
                                conversation_turns=max(1, int(conversation_turns)),
                                workflow_request_interval_ms=max(
                                    0, int(workflow_request_interval_ms)
                                ),
                                workflow_transport=str(workflow_transport),
                            )
                            objective = _objective_score(report)
                            runs.append(
                                {
                                    "run_id": run_id,
                                    "status": "ok",
                                    "factors": factors,
                                    "objective_score": objective,
                                    "acceptance_pass": bool(
                                        report.get("acceptance", {}).get("overall_pass", False)
                                    ),
                                    "metrics": {
                                        "hybrid_hit_at_k": report["retrieval_metrics"][
                                            "hybrid"
                                        ]["hit_at_k"],
                                        "hybrid_mrr": report["retrieval_metrics"]["hybrid"][
                                            "mrr"
                                        ],
                                        "workflow_source_hit_rate": report["workflow_metrics"][
                                            "source_hit_rate"
                                        ],
                                        "workflow_follow_up_source_hit_rate": report[
                                            "workflow_metrics"
                                        ]["follow_up_source_hit_rate"],
                                        "workflow_non_echo_rate": report["workflow_metrics"][
                                            "non_echo_rate"
                                        ],
                                        "workflow_follow_up_repeat_rate": report[
                                            "workflow_metrics"
                                        ]["follow_up_repeat_rate"],
                                        "workflow_avg_rouge_l_f1": report[
                                            "workflow_metrics"
                                        ]["avg_rouge_l_f1"],
                                    },
                                }
                            )
                        except Exception as exc:  # pragma: no cover - runtime dependent
                            runs.append(
                                {
                                    "run_id": run_id,
                                    "status": "error",
                                    "factors": factors,
                                    "error": str(exc),
                                }
                            )

    successful_runs = [item for item in runs if item.get("status") == "ok"]
    successful_scores = [float(item["objective_score"]) for item in successful_runs]
    best_run = (
        max(successful_runs, key=lambda item: float(item["objective_score"]))
        if successful_runs
        else None
    )
    factor_effects = _summarize_factor_effects(successful_runs)

    elapsed_ms = (time.perf_counter() - started) * 1000
    return {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "config": {
            "sample_size": int(sample_size),
            "seeds": [int(item) for item in seeds],
            "top_k_values": [int(item) for item in top_k_values],
            "hybrid_vector_weights": [float(item) for item in hybrid_vector_weights],
            "workflow_query_rewrite_counts": [
                int(item) for item in workflow_query_rewrite_counts
            ],
            "conversation_turn_values": [int(item) for item in conversation_turn_values],
            "sampling_mode": sampling_mode,
            "query_style_mode": query_style_mode,
            "base_url": base_url,
            "route_mode": route_mode,
            "timeout": int(timeout),
            "min_content_chars": int(min_content_chars),
            "max_chunk_rows": int(max_chunk_rows),
            "workflow_request_interval_ms": int(workflow_request_interval_ms),
            "workflow_transport": str(workflow_transport),
        },
        "summary": {
            "total_runs": len(runs),
            "successful_runs": len(successful_runs),
            "failed_runs": len(runs) - len(successful_runs),
            "mean_objective_score": round(_safe_mean(successful_scores), 6),
            "best_objective_score": round(max(successful_scores), 6)
            if successful_scores
            else 0.0,
        },
        "best_run": best_run,
        "factor_effects": factor_effects,
        "runs": runs,
        "elapsed_ms": round(elapsed_ms, 2),
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run RAG benchmark parameter sweep and rank influential factors."
    )
    parser.add_argument("--sample-size", type=int, default=40)
    parser.add_argument("--seeds", default="20260220,20260221")
    parser.add_argument("--top-k-values", default="4,8,12")
    parser.add_argument("--hybrid-vector-weights", default="0.5,0.7,0.9")
    parser.add_argument("--workflow-query-rewrite-counts", default="0,1,2")
    parser.add_argument("--conversation-turn-values", default="2,3")
    parser.add_argument(
        "--sampling-mode",
        choices=("random", "stratified_source"),
        default="stratified_source",
    )
    parser.add_argument(
        "--query-style-mode",
        choices=(
            "mixed",
            "mixed_balanced",
            "hard_focus",
            "direct",
            "contextual",
            "conversational",
            "telegraphic",
            "noisy",
        ),
        default="mixed",
    )
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--route-mode", default="local_only")
    parser.add_argument("--timeout", type=int, default=45)
    parser.add_argument("--min-content-chars", type=int, default=220)
    parser.add_argument("--max-chunk-rows", type=int, default=5000)
    parser.add_argument("--workflow-request-interval-ms", type=int, default=60)
    parser.add_argument(
        "--workflow-transport",
        choices=("http", "direct_runner"),
        default="direct_runner",
    )
    parser.add_argument("--output", default=DEFAULT_OUTPUT_PATH)
    parser.add_argument("--pretty", action="store_true")
    return parser


def main(argv: List[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    report = run_sweep(
        sample_size=max(1, int(args.sample_size)),
        seeds=_parse_int_list(args.seeds),
        top_k_values=_parse_int_list(args.top_k_values),
        hybrid_vector_weights=_parse_float_list(args.hybrid_vector_weights),
        workflow_query_rewrite_counts=_parse_int_list(args.workflow_query_rewrite_counts),
        conversation_turn_values=_parse_int_list(args.conversation_turn_values),
        sampling_mode=str(args.sampling_mode),
        query_style_mode=str(args.query_style_mode),
        base_url=str(args.base_url),
        route_mode=str(args.route_mode),
        timeout=max(10, int(args.timeout)),
        min_content_chars=max(50, int(args.min_content_chars)),
        max_chunk_rows=max(100, int(args.max_chunk_rows)),
        workflow_request_interval_ms=max(0, int(args.workflow_request_interval_ms)),
        workflow_transport=str(args.workflow_transport),
    )

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2 if args.pretty else None) + "\n",
        encoding="utf-8",
    )

    print("RAG factor sweep finished.")
    print(f"total_runs={report['summary']['total_runs']}")
    print(f"successful_runs={report['summary']['successful_runs']}")
    print(f"mean_objective_score={report['summary']['mean_objective_score']}")
    best = report.get("best_run") or {}
    print(f"best_objective_score={best.get('objective_score', 0.0)}")
    if best:
        print(f"best_factors={best.get('factors')}")
    print(f"report={output_path}")
    return 0 if report["summary"]["successful_runs"] > 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())
