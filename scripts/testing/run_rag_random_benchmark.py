#!/usr/bin/env python3
"""Randomized RAG benchmark driven by existing ingested KB chunks."""

from __future__ import annotations

import argparse
import json
import math
import os
import random
import re
import sys
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Keep behavior aligned with other standalone validation scripts.
os.environ.setdefault("REQUIRE_API_KEY", "false")

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.services.core.vectorstore import VectorStore
from backend.services.retrieval.hybrid_search import HybridRetriever

DEFAULT_OUTPUT_PATH = "logs/rag_random_benchmark_report.json"
QUERY_STYLE_TEMPLATES: Dict[str, Tuple[str, ...]] = {
    "direct": (
        "What does the construction standard require for \"{topic}\"?",
        "Summarize the key requirement related to \"{topic}\".",
        "In practical terms, what guidance is given for \"{topic}\"?",
        "What requirement is described for \"{topic}\" and \"{topic2}\"?",
    ),
    "contextual": (
        "For a real project delivery scenario, what does the standard say about \"{topic}\"?",
        "When implementing compliance controls, what guidance applies to \"{topic}\"?",
        "From a QA perspective, what is the requirement for \"{topic}\"?",
    ),
    "conversational": (
        "I need a quick explanation: what should I do for \"{topic}\"?",
        "Could you clarify the rule around \"{topic}\" in plain language?",
        "What does the document actually expect for \"{topic}\"?",
    ),
    "telegraphic": (
        "Need rule: \"{topic}\"",
        "Requirement check for \"{topic}\" and \"{topic2}\"?",
        "Standard guidance, \"{topic}\"?",
    ),
    "noisy": (
        "need quick help for \"{topic}\" what do i do?",
        "for \"{topic2}\" any must-do rule? short pls",
        "this doc says what about \"{topic}\".. confused",
    ),
}
FOLLOW_UP_PROMPTS: Tuple[str, ...] = (
    "From the same source, provide two concrete facts only. Do not restate my question.",
    "Continue from the same source and add one constraint or exception in one sentence.",
    "Still using the same source, provide one actionable checklist item only.",
)
STOPWORDS = {
    "about",
    "after",
    "again",
    "also",
    "among",
    "between",
    "being",
    "build",
    "building",
    "construction",
    "document",
    "from",
    "have",
    "into",
    "must",
    "only",
    "other",
    "requirement",
    "requirements",
    "section",
    "shall",
    "should",
    "standard",
    "that",
    "their",
    "there",
    "these",
    "this",
    "with",
    "within",
    "which",
}
ACRONYM_ALLOWLIST = {
    "api",
    "bim",
    "cad",
    "cfr",
    "gsa",
    "hvac",
    "ifc",
    "iso",
    "leed",
    "osha",
    "ufgs",
}

WORD_RE = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)?")
SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+")
CITATION_RE = re.compile(
    r"\[(?:sources?|citations?)\s*:\s*([^\]]+)\]",
    flags=re.IGNORECASE,
)


@dataclass(frozen=True)
class ChunkRow:
    chunk_id: str
    filename: str
    content: str


@dataclass(frozen=True)
class BenchmarkCase:
    case_id: str
    query: str
    query_style: str
    difficulty: str
    expected_source_hint: str
    source_filename: str
    expected_terms: List[str]
    reference_excerpt: str


def _normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", str(text or "")).strip().lower()


def _tokenize(text: str) -> List[str]:
    return WORD_RE.findall(_normalize_text(text))


def _normalize_source_hint(filename: str) -> str:
    stem = Path(str(filename or "")).stem
    normalized = re.sub(r"[^a-z0-9]+", "_", stem.lower()).strip("_")
    return normalized or "unknown_source"


def _extract_excerpt(content: str, rng: random.Random) -> Optional[str]:
    normalized = _normalize_text(content)
    if not normalized:
        return None

    candidates: List[str] = []
    for sentence in SENTENCE_SPLIT_RE.split(normalized):
        text = sentence.strip()
        word_count = len(_tokenize(text))
        if 8 <= word_count <= 38:
            candidates.append(text)

    if candidates:
        return rng.choice(candidates)

    words = _tokenize(normalized)
    if len(words) < 8:
        return None
    return " ".join(words[:32])


def _extract_terms(text: str, *, limit: int = 4) -> List[str]:
    terms: List[str] = []
    seen: set[str] = set()
    for token in _tokenize(text):
        if not _is_term_candidate(token):
            continue
        if token in seen:
            continue
        seen.add(token)
        terms.append(token)
        if len(terms) >= limit:
            break
    return terms


def _is_term_candidate(token: str) -> bool:
    token = str(token or "").strip().lower()
    if not token:
        return False
    if token in STOPWORDS:
        return False

    compact = token.replace("-", "")
    if not compact:
        return False

    if compact in ACRONYM_ALLOWLIST:
        return True

    if compact.isdigit():
        return False

    if not compact.isalpha():
        # Keep mixed tokens like "a23" where standard identifiers matter.
        return bool(any(ch.isalpha() for ch in compact) and any(ch.isdigit() for ch in compact))

    if len(compact) < 4:
        return False
    if sum(1 for ch in compact if ch in "aeiou") == 0:
        return False
    if len(set(compact)) <= 2:
        return False
    return True


def _resolve_query_style(
    query_style_mode: str,
    rng: random.Random,
    *,
    case_index: int,
) -> str:
    allowed_styles = list(QUERY_STYLE_TEMPLATES.keys())
    mode = str(query_style_mode or "mixed").strip().lower()
    if mode == "mixed":
        return rng.choice(allowed_styles)
    if mode == "mixed_balanced":
        return allowed_styles[int(case_index) % len(allowed_styles)]
    if mode == "hard_focus":
        hard_focus_sequence = ["noisy", "conversational", "noisy", "contextual", "telegraphic"]
        return hard_focus_sequence[int(case_index) % len(hard_focus_sequence)]
    if mode in QUERY_STYLE_TEMPLATES:
        return mode
    return "direct"


def _build_question(
    terms: List[str],
    excerpt: str,
    rng: random.Random,
    *,
    query_style_mode: str,
    case_index: int,
) -> Tuple[str, str]:
    fallback_terms = [token for token in _tokenize(excerpt) if token not in STOPWORDS][:3]
    selected = terms[:3] if terms else fallback_terms
    if not selected:
        selected = ["quality", "control"]

    topic = " ".join(selected[:2]).strip()
    topic2 = " ".join(selected[1:3]).strip() or topic
    if not topic:
        topic = "quality control"
    if not topic2:
        topic2 = topic

    style = _resolve_query_style(query_style_mode, rng, case_index=case_index)
    template = rng.choice(QUERY_STYLE_TEMPLATES[style])
    question = template.format(topic=topic, topic2=topic2)
    if style == "noisy":
        question = _inject_noisy_typo(question, rng)
    return question.strip(), style


def _inject_noisy_typo(question: str, rng: random.Random) -> str:
    tokens = str(question or "").split()
    if not tokens:
        return str(question or "")

    candidate_indexes = [
        idx
        for idx, token in enumerate(tokens)
        if len(token) >= 5 and any(ch.isalpha() for ch in token)
    ]
    if not candidate_indexes:
        return " ".join(tokens)

    idx = rng.choice(candidate_indexes)
    token = tokens[idx]
    clean = re.sub(r"[^a-zA-Z]", "", token)
    if len(clean) < 5:
        return " ".join(tokens)

    drop_index = min(len(clean) - 2, max(1, rng.randrange(1, len(clean) - 1)))
    mutated = clean[:drop_index] + clean[drop_index + 1 :]
    if not mutated:
        return " ".join(tokens)

    tokens[idx] = token.replace(clean, mutated)
    return " ".join(tokens)


def _classify_difficulty(*, query_style: str, expected_terms: List[str], query: str) -> str:
    score = 0
    style = str(query_style or "").strip().lower()

    if style in {"contextual"}:
        score += 1
    if style in {"conversational", "noisy"}:
        score += 2
    if style in {"telegraphic"}:
        score += 1
    if len(expected_terms) >= 3:
        score += 1
    if "?" not in str(query):
        score += 1

    if score <= 1:
        return "easy"
    if score <= 3:
        return "medium"
    return "hard"


def _follow_up_queries(conversation_turns: int) -> List[str]:
    turns = max(1, int(conversation_turns))
    if turns <= 1:
        return []

    queries: List[str] = []
    follow_up_turns = turns - 1
    for idx in range(follow_up_turns):
        if idx < len(FOLLOW_UP_PROMPTS):
            queries.append(FOLLOW_UP_PROMPTS[idx])
        else:
            queries.append(
                "Continue from the same source with one additional concrete detail. "
                "Avoid repeating earlier wording."
            )
    return queries


def _response_similarity(text_a: str, text_b: str) -> float:
    tokens_a = set(_tokenize(text_a))
    tokens_b = set(_tokenize(text_b))
    if not tokens_a or not tokens_b:
        return 0.0
    overlap = len(tokens_a.intersection(tokens_b))
    union = len(tokens_a.union(tokens_b))
    if union == 0:
        return 0.0
    return overlap / union


def _lcs_length(a: List[str], b: List[str]) -> int:
    if not a or not b:
        return 0

    prev = [0] * (len(b) + 1)
    for token_a in a:
        curr = [0]
        for j, token_b in enumerate(b, start=1):
            if token_a == token_b:
                curr.append(prev[j - 1] + 1)
            else:
                curr.append(max(prev[j], curr[-1]))
        prev = curr
    return prev[-1]


def _rouge_l_f1(candidate: str, reference: str) -> float:
    cand_tokens = _tokenize(candidate)
    ref_tokens = _tokenize(reference)
    if not cand_tokens or not ref_tokens:
        return 0.0

    lcs = _lcs_length(cand_tokens, ref_tokens)
    if lcs <= 0:
        return 0.0

    precision = lcs / len(cand_tokens)
    recall = lcs / len(ref_tokens)
    if precision + recall == 0:
        return 0.0
    return (2.0 * precision * recall) / (precision + recall)


def _sample_rows_random(
    rows: List[ChunkRow],
    *,
    sample_size: int,
    rng: random.Random,
) -> List[ChunkRow]:
    pool = list(rows)
    rng.shuffle(pool)
    return pool[:sample_size]


def _sample_rows_stratified_by_source(
    rows: List[ChunkRow],
    *,
    sample_size: int,
    rng: random.Random,
) -> List[ChunkRow]:
    buckets: Dict[str, List[ChunkRow]] = {}
    for row in rows:
        key = _normalize_source_hint(row.filename)
        buckets.setdefault(key, []).append(row)

    source_keys = list(buckets.keys())
    rng.shuffle(source_keys)
    for key in source_keys:
        rng.shuffle(buckets[key])

    selected: List[ChunkRow] = []
    while len(selected) < sample_size:
        progress = False
        for key in source_keys:
            bucket = buckets.get(key, [])
            if not bucket:
                continue
            selected.append(bucket.pop())
            progress = True
            if len(selected) >= sample_size:
                break
        if not progress:
            break
    return selected


def _sample_benchmark_cases(
    chunks: List[ChunkRow],
    *,
    sample_size: int,
    seed: int,
    sampling_mode: str = "random",
    query_style_mode: str = "direct",
) -> List[BenchmarkCase]:
    rng = random.Random(seed)
    rows = list(chunks)
    mode = str(sampling_mode or "random").strip().lower()
    if mode == "stratified_source":
        candidate_rows = _sample_rows_stratified_by_source(
            rows,
            sample_size=sample_size * 3,
            rng=rng,
        )
    else:
        candidate_rows = _sample_rows_random(
            rows,
            sample_size=sample_size * 3,
            rng=rng,
        )

    cases: List[BenchmarkCase] = []
    for row in candidate_rows:
        excerpt = _extract_excerpt(row.content, rng)
        if not excerpt:
            continue
        terms = _extract_terms(excerpt)
        if not terms:
            continue
        question, query_style = _build_question(
            terms,
            excerpt,
            rng,
            query_style_mode=query_style_mode,
            case_index=len(cases),
        )
        difficulty = _classify_difficulty(
            query_style=query_style,
            expected_terms=terms,
            query=question,
        )
        case = BenchmarkCase(
            case_id=f"case-{len(cases) + 1:03d}",
            query=question,
            query_style=query_style,
            difficulty=difficulty,
            expected_source_hint=_normalize_source_hint(row.filename),
            source_filename=str(row.filename or ""),
            expected_terms=terms,
            reference_excerpt=excerpt,
        )
        cases.append(case)
        if len(cases) >= sample_size:
            break
    return cases


def _coverage_ratio(text: str, terms: List[str]) -> float:
    if not terms:
        return 0.0
    text_blob = _normalize_text(text)
    hits = sum(1 for term in terms if term in text_blob)
    return hits / len(terms)


def _query_echo_ratio(query: str, answer: str) -> float:
    query_tokens = [token for token in _tokenize(query) if token not in STOPWORDS]
    if not query_tokens:
        return 0.0
    answer_blob = _normalize_text(answer)
    copied = sum(1 for token in query_tokens if token in answer_blob)
    return copied / len(query_tokens)


def _extract_citations(answer: str) -> List[str]:
    match = CITATION_RE.search(str(answer or ""))
    if not match:
        return []
    blob = match.group(1)
    tokens = [token.strip().lower() for token in re.split(r"[,;|\n]", blob)]
    return [token for token in tokens if token]


def _normalize_source_tokens(values: List[str]) -> List[str]:
    tokens: List[str] = []
    for value in values:
        normalized = _normalize_source_hint(value)
        if normalized:
            tokens.append(normalized)
    return tokens


def _source_hit_from_payload(payload: Dict[str, Any], expected_hint: str) -> bool:
    source_values: List[str] = []
    raw_sources = payload.get("sources")
    if isinstance(raw_sources, list):
        for item in raw_sources:
            if isinstance(item, str):
                source_values.append(item)
            elif isinstance(item, dict):
                for key in ("document_name", "document_id", "filename", "source"):
                    value = item.get(key)
                    if value:
                        source_values.append(str(value))

    answer = str(payload.get("response") or "")
    source_values.extend(_extract_citations(answer))
    normalized_values = _normalize_source_tokens(source_values)
    target = _normalize_source_hint(expected_hint)
    return any(target in token or token in target for token in normalized_values)


def _rank_for_expected_source(results: List[Dict[str, Any]], expected_hint: str) -> Optional[int]:
    target = _normalize_source_hint(expected_hint)
    for idx, row in enumerate(results, 1):
        candidate = _normalize_source_hint(str(row.get("filename") or ""))
        if target in candidate or candidate in target:
            return idx
    return None


def _auth_headers() -> Dict[str, str]:
    header_name = os.getenv("API_KEY_HEADER", "X-API-Key")
    key = os.getenv("TEST_API_KEY", "").strip()
    if not key:
        keys_raw = os.getenv("API_KEYS", "")
        key = next((token.strip() for token in keys_raw.split(",") if token.strip()), "")
    if not key:
        return {}
    return {header_name: key}


def _post_json(
    url: str,
    payload: Dict[str, Any],
    timeout: int = 30,
    *,
    retries: int = 2,
) -> Tuple[int, Dict[str, Any]]:
    body = json.dumps(payload).encode("utf-8")
    headers = {"Content-Type": "application/json", **_auth_headers()}
    req = urllib.request.Request(url=url, method="POST", data=body, headers=headers)
    backoff_seconds = 0.5

    for attempt in range(retries + 1):
        try:
            with urllib.request.urlopen(req, timeout=timeout) as response:
                raw = response.read().decode("utf-8")
                return response.getcode(), json.loads(raw)
        except urllib.error.HTTPError as exc:
            # Retry only for transient server/rate-limit status.
            if exc.code not in {429, 500, 502, 503, 504} or attempt >= retries:
                raise
            time.sleep(backoff_seconds)
            backoff_seconds *= 2.0

    raise RuntimeError("unreachable post_json retry state")


def _safe_post_workflow_query(
    query_url: str,
    payload: Dict[str, Any],
    *,
    timeout: int,
) -> Tuple[int, Dict[str, Any], Optional[str]]:
    try:
        code, result = _post_json(query_url, payload, timeout=timeout, retries=2)
        return code, result, None
    except Exception as exc:
        return (
            0,
            {
                "success": False,
                "response": "",
                "sources": [],
                "error": str(exc),
            },
            str(exc),
        )


def _get_json(url: str, timeout: int = 10) -> Tuple[int, Dict[str, Any]]:
    req = urllib.request.Request(url=url, method="GET", headers=_auth_headers())
    with urllib.request.urlopen(req, timeout=timeout) as response:
        raw = response.read().decode("utf-8")
        return response.getcode(), json.loads(raw)


def _load_chunk_rows(
    vector_store: VectorStore,
    *,
    min_content_chars: int,
    max_rows: int,
) -> List[ChunkRow]:
    conn = vector_store.get_connection()
    cur = conn.cursor()
    try:
        cur.execute(
            """
            SELECT
                dc.id::text,
                d.filename,
                dc.content
            FROM document_chunks dc
            JOIN documents d ON dc.doc_id = d.id
            WHERE dc.content IS NOT NULL
              AND LENGTH(TRIM(dc.content)) >= %s
            ORDER BY d.filename, dc.chunk_id
            LIMIT %s;
            """,
            (min_content_chars, max_rows),
        )
        rows = cur.fetchall()
        return [ChunkRow(chunk_id=row[0], filename=row[1], content=row[2]) for row in rows]
    finally:
        cur.close()
        conn.close()


def _distribution(values: List[str]) -> Dict[str, Any]:
    counts: Dict[str, int] = {}
    for value in values:
        key = str(value or "").strip().lower() or "unknown"
        counts[key] = counts.get(key, 0) + 1

    sorted_items = sorted(counts.items(), key=lambda item: (-item[1], item[0]))
    return {
        "unique_count": len(counts),
        "counts": {key: count for key, count in sorted_items},
    }


def _group_rate(
    rows: List[Dict[str, Any]],
    *,
    group_field: str,
    success_field: str,
) -> Dict[str, Any]:
    grouped: Dict[str, Dict[str, float]] = {}
    for row in rows:
        key = str(row.get(group_field) or "unknown")
        entry = grouped.setdefault(key, {"total": 0.0, "success": 0.0})
        entry["total"] += 1.0
        if bool(row.get(success_field)):
            entry["success"] += 1.0

    result: Dict[str, Any] = {}
    for key, payload in sorted(grouped.items(), key=lambda item: item[0]):
        total = payload["total"] or 1.0
        result[key] = {
            "total": int(payload["total"]),
            "success": int(payload["success"]),
            "rate": round(payload["success"] / total, 4),
        }
    return result


def _evaluate_retrieval(
    cases: List[BenchmarkCase],
    *,
    retriever: HybridRetriever,
    top_k: int,
    mode: str,
    vector_weight: float,
    bm25_weight: float,
) -> Dict[str, Any]:
    per_case: List[Dict[str, Any]] = []
    hits = 0
    mrr_total = 0.0
    ndcg_total = 0.0
    latencies: List[float] = []

    for case in cases:
        started = time.perf_counter()
        results = retriever.search(
            query=case.query,
            top_k=top_k,
            vector_weight=vector_weight,
            bm25_weight=bm25_weight,
        )
        latency_ms = (time.perf_counter() - started) * 1000
        latencies.append(latency_ms)

        rank = _rank_for_expected_source(results, case.expected_source_hint)
        hit = bool(rank is not None and rank <= top_k)
        if hit:
            hits += 1
            mrr_total += 1.0 / rank
            ndcg_total += 1.0 / math.log2(rank + 1.0)

        per_case.append(
            {
                "case_id": case.case_id,
                "query": case.query,
                "query_style": case.query_style,
                "difficulty": case.difficulty,
                "expected_source_hint": case.expected_source_hint,
                "source_filename": case.source_filename,
                "top_filenames": [
                    str(item.get("filename") or "").lower() for item in results[: min(3, top_k)]
                ],
                "rank_of_expected_source": rank,
                "hit_at_k": hit,
                "latency_ms": round(latency_ms, 2),
            }
        )

    total = len(cases) or 1
    return {
        "mode": mode,
        "vector_weight": vector_weight,
        "bm25_weight": bm25_weight,
        "total_cases": len(cases),
        "top_k": top_k,
        "hit_at_k": round(hits / total, 4),
        "recall_at_k": round(hits / total, 4),
        "mrr": round(mrr_total / total, 4),
        "ndcg_at_k": round(ndcg_total / total, 4),
        "avg_latency_ms": round(sum(latencies) / len(latencies), 2) if latencies else 0.0,
        "by_source": _group_rate(
            per_case,
            group_field="expected_source_hint",
            success_field="hit_at_k",
        ),
        "by_query_style": _group_rate(
            per_case,
            group_field="query_style",
            success_field="hit_at_k",
        ),
        "by_difficulty": _group_rate(
            per_case,
            group_field="difficulty",
            success_field="hit_at_k",
        ),
        "cases": per_case,
    }


def _evaluate_workflow_case(
    *,
    case: BenchmarkCase,
    payload: Dict[str, Any],
) -> Dict[str, Any]:
    response_text = str(payload.get("response") or "")
    success = bool(payload.get("success") is True)
    source_hit = _source_hit_from_payload(payload, case.expected_source_hint)
    keyword_coverage = _coverage_ratio(response_text, case.expected_terms)
    excerpt_terms = _extract_terms(case.reference_excerpt, limit=6)
    reference_overlap = _coverage_ratio(response_text, excerpt_terms)
    rouge_l_f1 = _rouge_l_f1(response_text, case.reference_excerpt)
    echo_ratio = _query_echo_ratio(case.query, response_text)
    citation_count = len(_extract_citations(response_text))

    case_pass = bool(
        success
        and response_text.strip()
        and source_hit
        and keyword_coverage >= 0.25
        and echo_ratio < 0.9
    )

    return {
        "success": success,
        "non_empty_response": bool(response_text.strip()),
        "source_hit": source_hit,
        "keyword_coverage": round(keyword_coverage, 4),
        "reference_overlap": round(reference_overlap, 4),
        "rouge_l_f1": round(rouge_l_f1, 4),
        "query_echo_ratio": round(echo_ratio, 4),
        "citation_count": citation_count,
        "pass": case_pass,
    }


def _run_workflow_eval_http(
    *,
    cases: List[BenchmarkCase],
    base_url: str,
    route_mode: str,
    timeout: int,
    workflow_enable_query_rewrite: bool,
    workflow_query_rewrite_count: int,
    request_interval_ms: int,
    conversation_turns: int,
) -> Dict[str, Any]:
    query_url = f"{base_url.rstrip('/')}/api/v1/workflow/query"
    per_case: List[Dict[str, Any]] = []
    follow_up_queries = _follow_up_queries(conversation_turns)
    follow_up_total = 0
    follow_up_non_echo = 0
    follow_up_source_hit = 0
    follow_up_repeat_count = 0
    latencies: List[float] = []
    request_errors: List[str] = []

    for idx, case in enumerate(cases, 1):
        session_id = f"rag-benchmark-{idx:04d}"
        payload = {
            "query": case.query,
            "session_id": session_id,
            "thread_id": session_id,
            "route_mode": route_mode,
            "enable_query_rewrite": workflow_enable_query_rewrite,
            "query_rewrite_count": workflow_query_rewrite_count,
        }
        started = time.perf_counter()
        code, result, request_error = _safe_post_workflow_query(
            query_url,
            payload,
            timeout=timeout,
        )
        latency_ms = (time.perf_counter() - started) * 1000
        latencies.append(latency_ms)
        if request_error:
            request_errors.append(request_error)

        evaluation = _evaluate_workflow_case(case=case, payload=result)
        previous_response = str(result.get("response") or "")
        follow_up_turn_metrics: List[Dict[str, Any]] = []
        follow_pass_count = 0
        follow_source_hit_count = 0
        follow_non_echo_count = 0
        follow_repeat_count = 0
        follow_max_echo = 0.0
        first_follow_http_code = 0
        first_follow_source_hit = False

        for turn_index, follow_query in enumerate(follow_up_queries, start=2):
            follow_payload = {
                "query": follow_query,
                "session_id": session_id,
                "thread_id": session_id,
                "route_mode": route_mode,
                "enable_query_rewrite": workflow_enable_query_rewrite,
                "query_rewrite_count": workflow_query_rewrite_count,
            }
            follow_code, follow_result, follow_error = _safe_post_workflow_query(
                query_url,
                follow_payload,
                timeout=timeout,
            )
            if follow_error:
                request_errors.append(follow_error)

            follow_eval = _evaluate_workflow_case(case=case, payload=follow_result)
            follow_response = str(follow_result.get("response") or "")
            repeat_similarity = _response_similarity(previous_response, follow_response)
            repeat_flag = repeat_similarity >= 0.88 and bool(follow_response.strip())

            follow_up_total += 1
            if follow_eval["query_echo_ratio"] < 0.9:
                follow_up_non_echo += 1
                follow_non_echo_count += 1
            if follow_eval["source_hit"]:
                follow_up_source_hit += 1
                follow_source_hit_count += 1
            if repeat_flag:
                follow_up_repeat_count += 1
                follow_repeat_count += 1
            if follow_eval["pass"]:
                follow_pass_count += 1
            follow_max_echo = max(follow_max_echo, float(follow_eval["query_echo_ratio"]))

            if turn_index == 2:
                first_follow_http_code = int(follow_code)
                first_follow_source_hit = bool(follow_eval["source_hit"])

            follow_up_turn_metrics.append(
                {
                    "turn": turn_index,
                    "query": follow_query,
                    "http_code": int(follow_code),
                    "pass": bool(follow_eval["pass"]),
                    "source_hit": bool(follow_eval["source_hit"]),
                    "echo_ratio": float(follow_eval["query_echo_ratio"]),
                    "repeat_similarity_with_prev_turn": round(repeat_similarity, 4),
                    "repeat_flag": repeat_flag,
                }
            )
            if follow_response.strip():
                previous_response = follow_response

        per_case.append(
            {
                "case_id": case.case_id,
                "query": case.query,
                "query_style": case.query_style,
                "difficulty": case.difficulty,
                "expected_source_hint": case.expected_source_hint,
                "source_filename": case.source_filename,
                "http_code": code,
                "latency_ms": round(latency_ms, 2),
                **evaluation,
                "follow_up_http_code": first_follow_http_code,
                "follow_up_pass": (
                    follow_pass_count == len(follow_up_queries) if follow_up_queries else True
                ),
                "follow_up_source_hit": first_follow_source_hit,
                "follow_up_echo_ratio": round(follow_max_echo, 4),
                "follow_up_turn_count": len(follow_up_queries),
                "follow_up_pass_rate": round(
                    follow_pass_count / len(follow_up_queries), 4
                )
                if follow_up_queries
                else 1.0,
                "follow_up_source_hit_rate": round(
                    follow_source_hit_count / len(follow_up_queries), 4
                )
                if follow_up_queries
                else 1.0,
                "follow_up_non_echo_rate": round(
                    follow_non_echo_count / len(follow_up_queries), 4
                )
                if follow_up_queries
                else 1.0,
                "follow_up_repeat_rate": round(
                    follow_repeat_count / len(follow_up_queries), 4
                )
                if follow_up_queries
                else 0.0,
                "follow_up_turn_metrics": follow_up_turn_metrics,
            }
        )
        if request_interval_ms > 0:
            time.sleep(float(request_interval_ms) / 1000.0)

    summary = _summarize_workflow_eval(
        transport="http",
        health_ok=True,
        per_case=per_case,
        latencies=latencies,
        follow_up_total=follow_up_total,
        follow_up_non_echo=follow_up_non_echo,
        follow_up_source_hit=follow_up_source_hit,
        follow_up_repeat_count=follow_up_repeat_count,
    )
    if request_errors:
        summary["request_errors"] = request_errors[:10]
    return summary


def _run_workflow_eval_testclient(
    *,
    cases: List[BenchmarkCase],
    route_mode: str,
    fallback_reason: str,
    workflow_enable_query_rewrite: bool,
    workflow_query_rewrite_count: int,
    request_interval_ms: int,
    conversation_turns: int,
) -> Dict[str, Any]:
    from fastapi.testclient import TestClient

    from backend.main import app

    headers = _auth_headers()
    per_case: List[Dict[str, Any]] = []
    latencies: List[float] = []
    follow_up_queries = _follow_up_queries(conversation_turns)
    follow_up_total = 0
    follow_up_non_echo = 0
    follow_up_source_hit = 0
    follow_up_repeat_count = 0

    with TestClient(app) as client:
        health_resp = client.get("/api/v1/workflow/health", headers=headers)
        health_ok = health_resp.status_code == 200

        for idx, case in enumerate(cases, 1):
            session_id = f"rag-benchmark-{idx:04d}"
            payload = {
                "query": case.query,
                "session_id": session_id,
                "thread_id": session_id,
                "route_mode": route_mode,
                "enable_query_rewrite": workflow_enable_query_rewrite,
                "query_rewrite_count": workflow_query_rewrite_count,
            }
            started = time.perf_counter()
            response = client.post("/api/v1/workflow/query", json=payload, headers=headers)
            latency_ms = (time.perf_counter() - started) * 1000
            latencies.append(latency_ms)
            try:
                result = response.json()
            except Exception:
                result = {}
            evaluation = _evaluate_workflow_case(case=case, payload=result)
            previous_response = str(result.get("response") or "")
            follow_up_turn_metrics: List[Dict[str, Any]] = []
            follow_pass_count = 0
            follow_source_hit_count = 0
            follow_non_echo_count = 0
            follow_repeat_count = 0
            follow_max_echo = 0.0
            first_follow_http_code = 0
            first_follow_source_hit = False

            for turn_index, follow_query in enumerate(follow_up_queries, start=2):
                follow_payload = {
                    "query": follow_query,
                    "session_id": session_id,
                    "thread_id": session_id,
                    "route_mode": route_mode,
                    "enable_query_rewrite": workflow_enable_query_rewrite,
                    "query_rewrite_count": workflow_query_rewrite_count,
                }
                follow_response = client.post(
                    "/api/v1/workflow/query", json=follow_payload, headers=headers
                )
                try:
                    follow_result = follow_response.json()
                except Exception:
                    follow_result = {}

                follow_eval = _evaluate_workflow_case(case=case, payload=follow_result)
                follow_response_text = str(follow_result.get("response") or "")
                repeat_similarity = _response_similarity(
                    previous_response, follow_response_text
                )
                repeat_flag = repeat_similarity >= 0.88 and bool(
                    follow_response_text.strip()
                )

                follow_up_total += 1
                if follow_eval["query_echo_ratio"] < 0.9:
                    follow_up_non_echo += 1
                    follow_non_echo_count += 1
                if follow_eval["source_hit"]:
                    follow_up_source_hit += 1
                    follow_source_hit_count += 1
                if repeat_flag:
                    follow_up_repeat_count += 1
                    follow_repeat_count += 1
                if follow_eval["pass"]:
                    follow_pass_count += 1
                follow_max_echo = max(
                    follow_max_echo, float(follow_eval["query_echo_ratio"])
                )

                if turn_index == 2:
                    first_follow_http_code = int(follow_response.status_code)
                    first_follow_source_hit = bool(follow_eval["source_hit"])

                follow_up_turn_metrics.append(
                    {
                        "turn": turn_index,
                        "query": follow_query,
                        "http_code": int(follow_response.status_code),
                        "pass": bool(follow_eval["pass"]),
                        "source_hit": bool(follow_eval["source_hit"]),
                        "echo_ratio": float(follow_eval["query_echo_ratio"]),
                        "repeat_similarity_with_prev_turn": round(repeat_similarity, 4),
                        "repeat_flag": repeat_flag,
                    }
                )
                if follow_response_text.strip():
                    previous_response = follow_response_text

            per_case.append(
                {
                    "case_id": case.case_id,
                    "query": case.query,
                    "query_style": case.query_style,
                    "difficulty": case.difficulty,
                    "expected_source_hint": case.expected_source_hint,
                    "source_filename": case.source_filename,
                    "http_code": response.status_code,
                    "latency_ms": round(latency_ms, 2),
                    **evaluation,
                    "follow_up_http_code": first_follow_http_code,
                    "follow_up_pass": (
                        follow_pass_count == len(follow_up_queries) if follow_up_queries else True
                    ),
                    "follow_up_source_hit": first_follow_source_hit,
                    "follow_up_echo_ratio": round(follow_max_echo, 4),
                    "follow_up_turn_count": len(follow_up_queries),
                    "follow_up_pass_rate": round(
                        follow_pass_count / len(follow_up_queries), 4
                    )
                    if follow_up_queries
                    else 1.0,
                    "follow_up_source_hit_rate": round(
                        follow_source_hit_count / len(follow_up_queries), 4
                    )
                    if follow_up_queries
                    else 1.0,
                    "follow_up_non_echo_rate": round(
                        follow_non_echo_count / len(follow_up_queries), 4
                    )
                    if follow_up_queries
                    else 1.0,
                    "follow_up_repeat_rate": round(
                        follow_repeat_count / len(follow_up_queries), 4
                    )
                    if follow_up_queries
                    else 0.0,
                    "follow_up_turn_metrics": follow_up_turn_metrics,
                }
            )
            if request_interval_ms > 0:
                time.sleep(float(request_interval_ms) / 1000.0)

    summary = _summarize_workflow_eval(
        transport="inprocess_testclient",
        health_ok=health_ok,
        per_case=per_case,
        latencies=latencies,
        follow_up_total=follow_up_total,
        follow_up_non_echo=follow_up_non_echo,
        follow_up_source_hit=follow_up_source_hit,
        follow_up_repeat_count=follow_up_repeat_count,
    )
    summary["fallback_reason"] = fallback_reason
    return summary


def _run_workflow_eval_direct(
    *,
    cases: List[BenchmarkCase],
    route_mode: str,
    workflow_enable_query_rewrite: bool,
    workflow_query_rewrite_count: int,
    request_interval_ms: int,
    conversation_turns: int,
) -> Dict[str, Any]:
    import asyncio

    from backend.api import workflow_query_routes as workflow_routes

    async def _run() -> Dict[str, Any]:
        runner = await workflow_routes.get_workflow_runner()
        per_case: List[Dict[str, Any]] = []
        latencies: List[float] = []
        follow_up_queries = _follow_up_queries(conversation_turns)
        follow_up_total = 0
        follow_up_non_echo = 0
        follow_up_source_hit = 0
        follow_up_repeat_count = 0

        for idx, case in enumerate(cases, 1):
            session_id = f"rag-benchmark-direct-{idx:04d}"
            started = time.perf_counter()
            result = await runner.run_workflow(
                query=case.query,
                session_id=session_id,
                user_id=None,
                thread_id=session_id,
                route_mode=route_mode,
            )
            latency_ms = (time.perf_counter() - started) * 1000
            latencies.append(latency_ms)

            metadata = result.get("metadata") or {}
            payload = {
                "success": bool(result.get("success")),
                "response": str(result.get("agent_response") or ""),
                "sources": workflow_routes._extract_sources(metadata),
            }
            evaluation = _evaluate_workflow_case(case=case, payload=payload)
            previous_response = str(payload.get("response") or "")
            follow_up_turn_metrics: List[Dict[str, Any]] = []
            follow_pass_count = 0
            follow_source_hit_count = 0
            follow_non_echo_count = 0
            follow_repeat_count = 0
            follow_max_echo = 0.0
            first_follow_http_code = 0
            first_follow_source_hit = False

            for turn_index, follow_query in enumerate(follow_up_queries, start=2):
                follow_result = await runner.run_workflow(
                    query=follow_query,
                    session_id=session_id,
                    user_id=None,
                    thread_id=session_id,
                    route_mode=route_mode,
                )
                follow_metadata = follow_result.get("metadata") or {}
                follow_payload = {
                    "success": bool(follow_result.get("success")),
                    "response": str(follow_result.get("agent_response") or ""),
                    "sources": workflow_routes._extract_sources(follow_metadata),
                }
                follow_eval = _evaluate_workflow_case(case=case, payload=follow_payload)
                follow_response = str(follow_payload.get("response") or "")
                repeat_similarity = _response_similarity(previous_response, follow_response)
                repeat_flag = repeat_similarity >= 0.88 and bool(follow_response.strip())

                follow_up_total += 1
                if follow_eval["query_echo_ratio"] < 0.9:
                    follow_up_non_echo += 1
                    follow_non_echo_count += 1
                if follow_eval["source_hit"]:
                    follow_up_source_hit += 1
                    follow_source_hit_count += 1
                if repeat_flag:
                    follow_up_repeat_count += 1
                    follow_repeat_count += 1
                if follow_eval["pass"]:
                    follow_pass_count += 1
                follow_max_echo = max(
                    follow_max_echo, float(follow_eval["query_echo_ratio"])
                )

                follow_http_code = 200 if follow_eval["success"] else 500
                if turn_index == 2:
                    first_follow_http_code = follow_http_code
                    first_follow_source_hit = bool(follow_eval["source_hit"])

                follow_up_turn_metrics.append(
                    {
                        "turn": turn_index,
                        "query": follow_query,
                        "http_code": follow_http_code,
                        "pass": bool(follow_eval["pass"]),
                        "source_hit": bool(follow_eval["source_hit"]),
                        "echo_ratio": float(follow_eval["query_echo_ratio"]),
                        "repeat_similarity_with_prev_turn": round(repeat_similarity, 4),
                        "repeat_flag": repeat_flag,
                    }
                )
                if follow_response.strip():
                    previous_response = follow_response

            per_case.append(
                {
                    "case_id": case.case_id,
                    "query": case.query,
                    "query_style": case.query_style,
                    "difficulty": case.difficulty,
                    "expected_source_hint": case.expected_source_hint,
                    "source_filename": case.source_filename,
                    "http_code": 200 if evaluation["success"] else 500,
                    "latency_ms": round(latency_ms, 2),
                    **evaluation,
                    "follow_up_http_code": first_follow_http_code,
                    "follow_up_pass": (
                        follow_pass_count == len(follow_up_queries) if follow_up_queries else True
                    ),
                    "follow_up_source_hit": first_follow_source_hit,
                    "follow_up_echo_ratio": round(follow_max_echo, 4),
                    "follow_up_turn_count": len(follow_up_queries),
                    "follow_up_pass_rate": round(
                        follow_pass_count / len(follow_up_queries), 4
                    )
                    if follow_up_queries
                    else 1.0,
                    "follow_up_source_hit_rate": round(
                        follow_source_hit_count / len(follow_up_queries), 4
                    )
                    if follow_up_queries
                    else 1.0,
                    "follow_up_non_echo_rate": round(
                        follow_non_echo_count / len(follow_up_queries), 4
                    )
                    if follow_up_queries
                    else 1.0,
                    "follow_up_repeat_rate": round(
                        follow_repeat_count / len(follow_up_queries), 4
                    )
                    if follow_up_queries
                    else 0.0,
                    "follow_up_turn_metrics": follow_up_turn_metrics,
                }
            )
            if request_interval_ms > 0:
                await asyncio.sleep(float(request_interval_ms) / 1000.0)

        return _summarize_workflow_eval(
            transport="direct_runner",
            health_ok=True,
            per_case=per_case,
            latencies=latencies,
            follow_up_total=follow_up_total,
            follow_up_non_echo=follow_up_non_echo,
            follow_up_source_hit=follow_up_source_hit,
            follow_up_repeat_count=follow_up_repeat_count,
        )

    return asyncio.run(_run())


def _summarize_workflow_eval(
    *,
    transport: str,
    health_ok: bool,
    per_case: List[Dict[str, Any]],
    latencies: List[float],
    follow_up_total: int,
    follow_up_non_echo: int,
    follow_up_source_hit: int,
    follow_up_repeat_count: int,
) -> Dict[str, Any]:
    total = len(per_case) or 1
    success_count = sum(1 for item in per_case if item.get("success"))
    source_hit_count = sum(1 for item in per_case if item.get("source_hit"))
    non_echo_count = sum(1 for item in per_case if float(item.get("query_echo_ratio", 1.0)) < 0.9)
    pass_count = sum(1 for item in per_case if item.get("pass"))
    avg_keyword_coverage = (
        sum(float(item.get("keyword_coverage", 0.0)) for item in per_case) / total
    )
    avg_reference_overlap = (
        sum(float(item.get("reference_overlap", 0.0)) for item in per_case) / total
    )
    avg_rouge_l_f1 = sum(float(item.get("rouge_l_f1", 0.0)) for item in per_case) / total
    avg_latency = round(sum(latencies) / len(latencies), 2) if latencies else 0.0

    follow_up_denominator = follow_up_total or 1
    follow_up_non_echo_rate = round(follow_up_non_echo / follow_up_denominator, 4)
    follow_up_source_hit_rate = round(follow_up_source_hit / follow_up_denominator, 4)
    follow_up_repeat_rate = round(follow_up_repeat_count / follow_up_denominator, 4)
    avg_follow_up_turns = (
        sum(float(item.get("follow_up_turn_count", 0.0)) for item in per_case) / total
    )

    return {
        "transport": transport,
        "health_ok": health_ok,
        "total_cases": len(per_case),
        "success_rate": round(success_count / total, 4),
        "source_hit_rate": round(source_hit_count / total, 4),
        "non_echo_rate": round(non_echo_count / total, 4),
        "avg_keyword_coverage": round(avg_keyword_coverage, 4),
        "avg_reference_overlap": round(avg_reference_overlap, 4),
        "avg_rouge_l_f1": round(avg_rouge_l_f1, 4),
        "avg_latency_ms": avg_latency,
        "pass_rate": round(pass_count / total, 4),
        "follow_up_non_echo_rate": follow_up_non_echo_rate,
        "follow_up_source_hit_rate": follow_up_source_hit_rate,
        "follow_up_repeat_rate": follow_up_repeat_rate,
        "avg_follow_up_turns": round(avg_follow_up_turns, 4),
        "by_source_pass_rate": _group_rate(
            per_case,
            group_field="expected_source_hint",
            success_field="pass",
        ),
        "by_source_source_hit_rate": _group_rate(
            per_case,
            group_field="expected_source_hint",
            success_field="source_hit",
        ),
        "by_query_style_pass_rate": _group_rate(
            per_case,
            group_field="query_style",
            success_field="pass",
        ),
        "by_difficulty_pass_rate": _group_rate(
            per_case,
            group_field="difficulty",
            success_field="pass",
        ),
        "cases": per_case,
    }


def _run_workflow_eval(
    *,
    cases: List[BenchmarkCase],
    base_url: str,
    route_mode: str,
    timeout: int,
    workflow_enable_query_rewrite: bool,
    workflow_query_rewrite_count: int,
    request_interval_ms: int,
    workflow_transport: str,
    conversation_turns: int,
) -> Dict[str, Any]:
    transport_mode = str(workflow_transport or "http").strip().lower()
    if transport_mode == "direct_runner":
        return _run_workflow_eval_direct(
            cases=cases,
            route_mode=route_mode,
            workflow_enable_query_rewrite=workflow_enable_query_rewrite,
            workflow_query_rewrite_count=workflow_query_rewrite_count,
            request_interval_ms=request_interval_ms,
            conversation_turns=conversation_turns,
        )

    def _failed_summary(reason: str) -> Dict[str, Any]:
        return {
            "transport": "failed",
            "health_ok": False,
            "total_cases": len(cases),
            "success_rate": 0.0,
            "source_hit_rate": 0.0,
            "non_echo_rate": 0.0,
            "avg_keyword_coverage": 0.0,
            "avg_reference_overlap": 0.0,
            "avg_rouge_l_f1": 0.0,
            "avg_latency_ms": 0.0,
            "pass_rate": 0.0,
            "follow_up_non_echo_rate": 0.0,
            "follow_up_source_hit_rate": 0.0,
            "follow_up_repeat_rate": 0.0,
            "avg_follow_up_turns": 0.0,
            "by_source_pass_rate": {},
            "by_source_source_hit_rate": {},
            "by_query_style_pass_rate": {},
            "by_difficulty_pass_rate": {},
            "cases": [],
            "error": reason,
        }

    health_url = f"{base_url.rstrip('/')}/api/v1/workflow/health"
    try:
        code, payload = _get_json(health_url, timeout=min(timeout, 10))
        healthy = code == 200 and str(payload.get("status")).lower() == "ok"
        if healthy:
            try:
                return _run_workflow_eval_http(
                    cases=cases,
                    base_url=base_url,
                    route_mode=route_mode,
                    timeout=timeout,
                    workflow_enable_query_rewrite=workflow_enable_query_rewrite,
                    workflow_query_rewrite_count=workflow_query_rewrite_count,
                    request_interval_ms=request_interval_ms,
                    conversation_turns=conversation_turns,
                )
            except Exception as exc:
                try:
                    return _run_workflow_eval_testclient(
                        cases=cases,
                        route_mode=route_mode,
                        fallback_reason=f"http query failed: {exc}",
                        workflow_enable_query_rewrite=workflow_enable_query_rewrite,
                        workflow_query_rewrite_count=workflow_query_rewrite_count,
                        request_interval_ms=request_interval_ms,
                        conversation_turns=conversation_turns,
                    )
                except Exception as fallback_exc:
                    return _failed_summary(
                        f"http+testclient failed: {exc}; {fallback_exc}"
                    )
    except Exception as exc:
        fallback_reason = str(exc)
        try:
            return _run_workflow_eval_testclient(
                cases=cases,
                route_mode=route_mode,
                fallback_reason=fallback_reason,
                workflow_enable_query_rewrite=workflow_enable_query_rewrite,
                workflow_query_rewrite_count=workflow_query_rewrite_count,
                request_interval_ms=request_interval_ms,
                conversation_turns=conversation_turns,
            )
        except Exception as fallback_exc:
            return _failed_summary(
                f"health-check+testclient failed: {fallback_reason}; {fallback_exc}"
            )

    try:
        return _run_workflow_eval_testclient(
            cases=cases,
            route_mode=route_mode,
            fallback_reason="workflow health endpoint returned non-OK status",
            workflow_enable_query_rewrite=workflow_enable_query_rewrite,
            workflow_query_rewrite_count=workflow_query_rewrite_count,
            request_interval_ms=request_interval_ms,
            conversation_turns=conversation_turns,
        )
    except Exception as fallback_exc:
        return _failed_summary(f"workflow health non-OK and fallback failed: {fallback_exc}")


def run_benchmark(
    *,
    sample_size: int,
    seed: int,
    top_k: int,
    min_content_chars: int,
    max_chunk_rows: int,
    base_url: str,
    route_mode: str,
    timeout: int,
    sampling_mode: str = "stratified_source",
    query_style_mode: str = "mixed",
    hybrid_vector_weight: float = 0.7,
    hybrid_bm25_weight: float = 0.3,
    workflow_enable_query_rewrite: bool = True,
    workflow_query_rewrite_count: int = 1,
    conversation_turns: int = 3,
    workflow_request_interval_ms: int = 0,
    workflow_transport: str = "http",
) -> Dict[str, Any]:
    started = time.perf_counter()
    vector_store = VectorStore()
    retriever = HybridRetriever(vector_store)
    retriever.build_bm25_index()

    chunks = _load_chunk_rows(
        vector_store,
        min_content_chars=min_content_chars,
        max_rows=max_chunk_rows,
    )
    cases = _sample_benchmark_cases(
        chunks,
        sample_size=sample_size,
        seed=seed,
        sampling_mode=sampling_mode,
        query_style_mode=query_style_mode,
    )

    retrieval_semantic = _evaluate_retrieval(
        cases,
        retriever=retriever,
        top_k=top_k,
        mode="semantic",
        vector_weight=1.0,
        bm25_weight=0.0,
    )
    retrieval_hybrid = _evaluate_retrieval(
        cases,
        retriever=retriever,
        top_k=top_k,
        mode="hybrid",
        vector_weight=float(hybrid_vector_weight),
        bm25_weight=float(hybrid_bm25_weight),
    )
    retrieval_keyword = _evaluate_retrieval(
        cases,
        retriever=retriever,
        top_k=top_k,
        mode="keyword",
        vector_weight=0.0,
        bm25_weight=1.0,
    )
    from backend.config import settings as runtime_settings

    original_enable_rewrite = getattr(runtime_settings, "enable_rag_query_rewrite", True)
    original_rewrite_count = getattr(runtime_settings, "rag_query_rewrite_count", 1)
    runtime_settings.enable_rag_query_rewrite = bool(workflow_enable_query_rewrite)
    runtime_settings.rag_query_rewrite_count = int(workflow_query_rewrite_count)
    try:
        workflow = _run_workflow_eval(
            cases=cases,
            base_url=base_url,
            route_mode=route_mode,
            timeout=timeout,
            workflow_enable_query_rewrite=bool(workflow_enable_query_rewrite),
            workflow_query_rewrite_count=int(workflow_query_rewrite_count),
            request_interval_ms=max(0, int(workflow_request_interval_ms)),
            workflow_transport=str(workflow_transport),
            conversation_turns=max(1, int(conversation_turns)),
        )
    finally:
        runtime_settings.enable_rag_query_rewrite = original_enable_rewrite
        runtime_settings.rag_query_rewrite_count = original_rewrite_count

    thresholds = {
        "min_hybrid_retrieval_hit_at_k": 0.75,
        "min_hybrid_retrieval_mrr": 0.55,
        "min_workflow_source_hit_rate": 0.70,
        "min_workflow_non_echo_rate": 0.80,
        "min_workflow_follow_up_non_echo_rate": 0.80,
        "min_workflow_follow_up_source_hit_rate": 0.70,
        "max_workflow_follow_up_repeat_rate": 0.45,
    }

    acceptance = {
        "hybrid_retrieval_hit_at_k_pass": retrieval_hybrid["hit_at_k"]
        >= thresholds["min_hybrid_retrieval_hit_at_k"],
        "hybrid_retrieval_mrr_pass": retrieval_hybrid["mrr"]
        >= thresholds["min_hybrid_retrieval_mrr"],
        "workflow_source_hit_pass": workflow["source_hit_rate"]
        >= thresholds["min_workflow_source_hit_rate"],
        "workflow_non_echo_pass": workflow["non_echo_rate"]
        >= thresholds["min_workflow_non_echo_rate"],
        "workflow_follow_up_non_echo_pass": workflow["follow_up_non_echo_rate"]
        >= thresholds["min_workflow_follow_up_non_echo_rate"],
        "workflow_follow_up_source_hit_pass": workflow["follow_up_source_hit_rate"]
        >= thresholds["min_workflow_follow_up_source_hit_rate"],
        "workflow_follow_up_repeat_pass": workflow["follow_up_repeat_rate"]
        <= thresholds["max_workflow_follow_up_repeat_rate"],
    }
    acceptance["overall_pass"] = all(acceptance.values())

    elapsed_ms = (time.perf_counter() - started) * 1000
    return {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "config": {
            "sample_size": sample_size,
            "seed": seed,
            "top_k": top_k,
            "min_content_chars": min_content_chars,
            "max_chunk_rows": max_chunk_rows,
            "base_url": base_url,
            "route_mode": route_mode,
            "timeout": timeout,
            "sampling_mode": sampling_mode,
            "query_style_mode": query_style_mode,
            "hybrid_vector_weight": hybrid_vector_weight,
            "hybrid_bm25_weight": hybrid_bm25_weight,
            "workflow_enable_query_rewrite": bool(workflow_enable_query_rewrite),
            "workflow_query_rewrite_count": int(workflow_query_rewrite_count),
            "conversation_turns": int(conversation_turns),
            "workflow_request_interval_ms": int(workflow_request_interval_ms),
            "workflow_transport": str(workflow_transport),
        },
        "dataset_snapshot": {
            "candidate_chunk_rows": len(chunks),
            "sampled_cases": len(cases),
            "unique_sources": len({case.expected_source_hint for case in cases}),
            "source_distribution": _distribution(
                [case.expected_source_hint for case in cases]
            ),
            "query_style_distribution": _distribution(
                [case.query_style for case in cases]
            ),
            "difficulty_distribution": _distribution(
                [case.difficulty for case in cases]
            ),
        },
        "retrieval_metrics": {
            "semantic": retrieval_semantic,
            "hybrid": retrieval_hybrid,
            "keyword": retrieval_keyword,
        },
        "workflow_metrics": workflow,
        "thresholds": thresholds,
        "acceptance": acceptance,
        "elapsed_ms": round(elapsed_ms, 2),
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run randomized RAG accuracy benchmark from vectorized KB docs."
    )
    parser.add_argument("--sample-size", type=int, default=30)
    parser.add_argument("--seed", type=int, default=20260220)
    parser.add_argument("--top-k", type=int, default=8)
    parser.add_argument("--min-content-chars", type=int, default=220)
    parser.add_argument("--max-chunk-rows", type=int, default=5000)
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--route-mode", default="local_only")
    parser.add_argument("--timeout", type=int, default=45)
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
    parser.add_argument("--hybrid-vector-weight", type=float, default=0.7)
    parser.add_argument("--hybrid-bm25-weight", type=float, default=0.3)
    parser.add_argument(
        "--workflow-enable-query-rewrite",
        choices=("true", "false"),
        default="true",
    )
    parser.add_argument("--workflow-query-rewrite-count", type=int, default=1)
    parser.add_argument("--conversation-turns", type=int, default=3)
    parser.add_argument("--workflow-request-interval-ms", type=int, default=0)
    parser.add_argument(
        "--workflow-transport",
        choices=("http", "direct_runner"),
        default="http",
    )
    parser.add_argument("--output", default=DEFAULT_OUTPUT_PATH)
    parser.add_argument("--pretty", action="store_true")
    return parser


def main(argv: Optional[List[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    report = run_benchmark(
        sample_size=max(1, int(args.sample_size)),
        seed=int(args.seed),
        top_k=max(1, int(args.top_k)),
        min_content_chars=max(50, int(args.min_content_chars)),
        max_chunk_rows=max(100, int(args.max_chunk_rows)),
        base_url=str(args.base_url),
        route_mode=str(args.route_mode),
        timeout=max(10, int(args.timeout)),
        sampling_mode=str(args.sampling_mode),
        query_style_mode=str(args.query_style_mode),
        hybrid_vector_weight=max(0.0, float(args.hybrid_vector_weight)),
        hybrid_bm25_weight=max(0.0, float(args.hybrid_bm25_weight)),
        workflow_enable_query_rewrite=(
            str(args.workflow_enable_query_rewrite).strip().lower() == "true"
        ),
        workflow_query_rewrite_count=max(0, int(args.workflow_query_rewrite_count)),
        conversation_turns=max(1, int(args.conversation_turns)),
        workflow_request_interval_ms=max(0, int(args.workflow_request_interval_ms)),
        workflow_transport=str(args.workflow_transport),
    )

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2 if args.pretty else None) + "\n",
        encoding="utf-8",
    )

    print("RAG random benchmark finished.")
    print(f"sampled_cases={report['dataset_snapshot']['sampled_cases']}")
    print(f"sampled_unique_sources={report['dataset_snapshot']['unique_sources']}")
    print(
        "query_styles="
        f"{list(report['dataset_snapshot']['query_style_distribution']['counts'].keys())}"
    )
    print(
        "difficulty_levels="
        f"{list(report['dataset_snapshot']['difficulty_distribution']['counts'].keys())}"
    )
    print(f"hybrid_retrieval_hit_at_k={report['retrieval_metrics']['hybrid']['hit_at_k']}")
    print(f"hybrid_retrieval_mrr={report['retrieval_metrics']['hybrid']['mrr']}")
    print(f"workflow_source_hit_rate={report['workflow_metrics']['source_hit_rate']}")
    print(f"workflow_non_echo_rate={report['workflow_metrics']['non_echo_rate']}")
    print(
        "workflow_follow_up_non_echo_rate="
        f"{report['workflow_metrics']['follow_up_non_echo_rate']}"
    )
    print(
        "workflow_follow_up_repeat_rate="
        f"{report['workflow_metrics']['follow_up_repeat_rate']}"
    )
    print(f"workflow_avg_rouge_l_f1={report['workflow_metrics']['avg_rouge_l_f1']}")
    print(f"overall_pass={report['acceptance']['overall_pass']}")
    print(f"report={output_path}")
    return 0 if report["acceptance"]["overall_pass"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
