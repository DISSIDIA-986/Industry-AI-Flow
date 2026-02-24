from __future__ import annotations

from scripts.testing import run_rag_factor_sweep as sweep


def test_parse_list_helpers():
    assert sweep._parse_int_list("4,8,12") == [4, 8, 12]
    assert sweep._parse_float_list("0.5, 0.7,0.9") == [0.5, 0.7, 0.9]


def test_summarize_factor_effects_returns_grouped_deltas():
    runs = [
        {
            "objective_score": 0.7,
            "factors": {
                "top_k": 4,
                "hybrid_vector_weight": 0.5,
                "workflow_query_rewrite_count": 0,
                "conversation_turns": 2,
            },
        },
        {
            "objective_score": 0.8,
            "factors": {
                "top_k": 8,
                "hybrid_vector_weight": 0.5,
                "workflow_query_rewrite_count": 1,
                "conversation_turns": 3,
            },
        },
        {
            "objective_score": 0.9,
            "factors": {
                "top_k": 8,
                "hybrid_vector_weight": 0.9,
                "workflow_query_rewrite_count": 1,
                "conversation_turns": 3,
            },
        },
    ]

    summary = sweep._summarize_factor_effects(runs)

    assert summary["global_mean_objective"] == 0.8
    assert summary["effects"]["top_k"]["8"]["mean_objective"] == 0.85
    assert summary["effects"]["workflow_query_rewrite_count"]["1"]["runs"] == 2
    assert summary["effects"]["conversation_turns"]["3"]["runs"] == 2
