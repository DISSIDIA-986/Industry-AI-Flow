from __future__ import annotations

import random

from scripts.testing import run_rag_random_benchmark as benchmark


def test_sample_benchmark_cases_is_deterministic_with_seed():
    chunks = [
        benchmark.ChunkRow(
            chunk_id="1",
            filename="gsa_p100_2024_final.pdf",
            content=(
                "Guardrails shall be installed for open edges above 3 meters. "
                "Inspections must be documented weekly."
            ),
        ),
        benchmark.ChunkRow(
            chunk_id="2",
            filename="osha_29_cfr_1926.txt",
            content=(
                "Personal protective equipment includes hard hats, eye protection, "
                "and task-specific gloves for hazardous work."
            ),
        ),
    ]

    cases_1 = benchmark._sample_benchmark_cases(
        chunks,
        sample_size=2,
        seed=99,
        sampling_mode="random",
        query_style_mode="direct",
    )
    cases_2 = benchmark._sample_benchmark_cases(
        chunks,
        sample_size=2,
        seed=99,
        sampling_mode="random",
        query_style_mode="direct",
    )

    assert len(cases_1) == 2
    assert [case.query for case in cases_1] == [case.query for case in cases_2]
    assert [case.expected_source_hint for case in cases_1] == [
        case.expected_source_hint for case in cases_2
    ]
    assert [case.query_style for case in cases_1] == [
        case.query_style for case in cases_2
    ]


def test_rank_for_expected_source_matches_normalized_filename():
    results = [
        {"filename": "GSA_P100_2024_Final.PDF"},
        {"filename": "ufgs_03_30_00_cast_in_place_concrete.pdf"},
    ]

    rank = benchmark._rank_for_expected_source(results, "gsa_p100_2024_final")
    assert rank == 1


def test_query_echo_ratio_identifies_question_repetition():
    query = "What does the standard say about guardrails and inspections?"
    echoed_answer = (
        "What does the standard say about guardrails and inspections? "
        "What does the standard say about guardrails and inspections?"
    )
    non_echo_answer = (
        "Guardrails are mandatory above 3 meters and weekly inspections are required."
    )

    assert benchmark._query_echo_ratio(query, echoed_answer) > 0.95
    assert benchmark._query_echo_ratio(query, non_echo_answer) < 0.6


def test_source_hit_from_payload_supports_sources_and_citations():
    payload_with_sources = {
        "response": "Answer text without explicit citation.",
        "sources": [
            {
                "document_name": "gsa_p100_2024_final.pdf",
                "document_id": "doc-1",
            }
        ],
    }
    payload_with_citations = {
        "response": "Grounded response [Sources: osha_29_cfr_1926.txt]",
        "sources": [],
    }

    assert (
        benchmark._source_hit_from_payload(payload_with_sources, "gsa_p100_2024_final")
        is True
    )
    assert (
        benchmark._source_hit_from_payload(payload_with_citations, "osha_29_cfr_1926")
        is True
    )


def test_extract_excerpt_prefers_sentence_window():
    rng = random.Random(7)
    content = (
        "Too short. "
        "Concrete curing shall maintain moisture and temperature control for at least seven days. "
        "Another sentence."
    )
    excerpt = benchmark._extract_excerpt(content, rng)

    assert excerpt is not None
    assert "moisture" in excerpt


def test_sample_benchmark_cases_stratified_source_balances_sources():
    chunks = [
        benchmark.ChunkRow(
            chunk_id="1",
            filename="a.pdf",
            content="Safety guardrails are required for elevated work areas in all scenarios.",
        ),
        benchmark.ChunkRow(
            chunk_id="2",
            filename="a.pdf",
            content="Concrete curing schedules must be documented and audited in quality logs.",
        ),
        benchmark.ChunkRow(
            chunk_id="3",
            filename="b.pdf",
            content="Excavation controls require protection systems and hazard communication plans.",
        ),
        benchmark.ChunkRow(
            chunk_id="4",
            filename="c.pdf",
            content="HVAC commissioning records should include calibration and verification checkpoints.",
        ),
    ]

    cases = benchmark._sample_benchmark_cases(
        chunks,
        sample_size=3,
        seed=7,
        sampling_mode="stratified_source",
        query_style_mode="direct",
    )
    sampled_sources = {case.expected_source_hint for case in cases}

    assert len(cases) == 3
    assert len(sampled_sources) >= 2


def test_sample_benchmark_cases_mixed_balanced_covers_styles():
    chunks = [
        benchmark.ChunkRow(
            chunk_id=f"{idx}",
            filename=f"doc_{idx}.pdf",
            content=(
                "Concrete placement requires inspection records and curing controls for structural quality."
            ),
        )
        for idx in range(1, 8)
    ]

    cases = benchmark._sample_benchmark_cases(
        chunks,
        sample_size=5,
        seed=42,
        sampling_mode="random",
        query_style_mode="mixed_balanced",
    )
    styles = [case.query_style for case in cases]

    assert len(cases) == 5
    assert len(set(styles)) == 5
    assert "noisy" in styles


def test_group_rate_computes_success_ratio():
    rows = [
        {"expected_source_hint": "a", "hit_at_k": True},
        {"expected_source_hint": "a", "hit_at_k": False},
        {"expected_source_hint": "b", "hit_at_k": True},
    ]
    result = benchmark._group_rate(
        rows,
        group_field="expected_source_hint",
        success_field="hit_at_k",
    )
    assert result["a"]["rate"] == 0.5
    assert result["b"]["rate"] == 1.0


def test_follow_up_queries_supports_multi_turn():
    assert benchmark._follow_up_queries(1) == []
    assert len(benchmark._follow_up_queries(3)) == 2
    assert len(benchmark._follow_up_queries(5)) == 4


def test_rouge_l_f1_returns_high_score_for_similar_sentences():
    reference = "Guardrails are required for elevated edges and weekly inspections."
    candidate = "Weekly inspections are required and guardrails are mandatory for elevated edges."
    score = benchmark._rouge_l_f1(candidate, reference)

    assert score > 0.45


def test_classify_difficulty_marks_noisy_query_as_hard():
    difficulty = benchmark._classify_difficulty(
        query_style="noisy",
        expected_terms=["guardrails", "inspections", "elevated"],
        query='need quick help for "guardrails inspections" what do i do',
    )
    assert difficulty == "hard"
