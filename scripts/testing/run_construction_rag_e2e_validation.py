#!/usr/bin/env python3
"""End-to-end validation for construction RAG workflow."""

from __future__ import annotations

import json
import os
import sys
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.services.core.embedder import embed_query_text
from backend.services.core.vectorstore import VectorStore
from backend.services.retrieval.hybrid_search import HybridRetriever


@dataclass
class QueryCase:
    query: str
    expected_source_hint: str
    expected_keywords: list[str]


QUERY_CASES: list[QueryCase] = [
    QueryCase(
        query="What does P100 say about federal facility design standards?",
        expected_source_hint="gsa_p100",
        expected_keywords=["standards", "facility", "design"],
    ),
    QueryCase(
        query="What are cast-in-place concrete requirements in UFGS?",
        expected_source_hint="03_30_00",
        expected_keywords=["concrete", "requirements", "quality"],
    ),
    QueryCase(
        query="What topics are covered in OSHA 29 CFR 1926?",
        expected_source_hint="osha_29_cfr_1926",
        expected_keywords=["safety", "construction", "1926"],
    ),
    QueryCase(
        query="What is IFC 4.3 schema specification used for?",
        expected_source_hint="ifc_4_3",
        expected_keywords=["ifc", "schema", "specification"],
    ),
]


EXPECTED_INGESTED_DOCS = [
    "buildingsmart_ifc_4_3_schema_specifications.txt",
    "caltrans_2025_standard_plans_digest.pdf",
    "caltrans_2025_standard_specifications_digest.pdf",
    "gsa_core_building_standards_memo_2025.pdf",
    "gsa_core_building_training_2025-04-30.pdf",
    "gsa_p100_2024_final.pdf",
    "osha_29_cfr_1926.txt",
    "ufgs_03_30_00_cast_in_place_concrete.pdf",
    "ufgs_toc.pdf",
]


def _contains_all_keywords(text_blob: str, keywords: list[str]) -> float:
    if not keywords:
        return 0.0
    hits = sum(1 for kw in keywords if kw.lower() in text_blob)
    return hits / len(keywords)


def _extract_text_blob(results: list[dict]) -> str:
    return " ".join((row.get("content") or "") for row in results).lower()


def _extract_filenames(results: list[dict]) -> list[str]:
    return [str(row.get("filename") or "").lower() for row in results]


def _run_retrieval_mode(
    mode: str,
    retriever: HybridRetriever,
    vector_store: VectorStore,
    top_k: int,
) -> dict:
    per_case = []
    latencies_ms = []
    pass_count = 0

    for case in QUERY_CASES:
        started = time.perf_counter()
        if mode == "semantic":
            query_embedding = embed_query_text(case.query)
            results = vector_store.similarity_search(query_embedding, top_k=top_k)
        elif mode == "hybrid":
            results = retriever.search(
                query=case.query, top_k=top_k, vector_weight=0.7, bm25_weight=0.3
            )
        elif mode == "keyword":
            results = retriever.search(
                query=case.query, top_k=top_k, vector_weight=0.0, bm25_weight=1.0
            )
        else:
            raise ValueError(f"Unsupported mode: {mode}")
        latency_ms = (time.perf_counter() - started) * 1000
        latencies_ms.append(latency_ms)

        filenames = _extract_filenames(results)
        text_blob = _extract_text_blob(results)
        source_hit = any(case.expected_source_hint in name for name in filenames)
        keyword_score = _contains_all_keywords(text_blob, case.expected_keywords)
        case_pass = bool(source_hit or keyword_score >= 0.67)
        if case_pass:
            pass_count += 1

        per_case.append(
            {
                "query": case.query,
                "expected_source_hint": case.expected_source_hint,
                "expected_keywords": case.expected_keywords,
                "source_hit": source_hit,
                "keyword_score": round(keyword_score, 4),
                "top_filenames": filenames[:3],
                "latency_ms": round(latency_ms, 2),
                "pass": case_pass,
            }
        )

    avg_latency = sum(latencies_ms) / len(latencies_ms) if latencies_ms else 0.0
    pass_rate = pass_count / len(QUERY_CASES) if QUERY_CASES else 0.0
    return {
        "mode": mode,
        "top_k": top_k,
        "avg_latency_ms": round(avg_latency, 2),
        "pass_count": pass_count,
        "total_cases": len(QUERY_CASES),
        "pass_rate": round(pass_rate, 4),
        "cases": per_case,
    }


def _check_storage(vector_store: VectorStore) -> dict:
    conn = vector_store.get_connection()
    cur = conn.cursor()
    try:
        cur.execute("SELECT EXISTS(SELECT 1 FROM pg_extension WHERE extname='vector');")
        has_pgvector = bool(cur.fetchone()[0])

        cur.execute("SELECT COUNT(*) FROM documents;")
        doc_count = int(cur.fetchone()[0])

        cur.execute("SELECT COUNT(*) FROM document_chunks;")
        chunk_count = int(cur.fetchone()[0])

        cur.execute(
            """
            SELECT filename FROM documents
            WHERE filename = ANY(%s)
            ORDER BY filename;
            """,
            (EXPECTED_INGESTED_DOCS,),
        )
        present_docs = [row[0] for row in cur.fetchall()]

        vector_dim = None
        if has_pgvector:
            cur.execute(
                """
                SELECT vector_dims(embedding)
                FROM document_chunks
                WHERE embedding IS NOT NULL
                LIMIT 1;
                """
            )
            row = cur.fetchone()
            vector_dim = int(row[0]) if row and row[0] is not None else None

        return {
            "has_pgvector": has_pgvector,
            "document_count": doc_count,
            "chunk_count": chunk_count,
            "expected_docs_present": present_docs,
            "expected_docs_present_count": len(present_docs),
            "expected_docs_total": len(EXPECTED_INGESTED_DOCS),
            "vector_dim_sample": vector_dim,
            "pass": bool(
                has_pgvector
                and len(present_docs) == len(EXPECTED_INGESTED_DOCS)
                and chunk_count > 0
                and (vector_dim in (None, 768) or vector_dim > 0)
            ),
        }
    finally:
        cur.close()
        conn.close()


def _post_json(url: str, payload: dict, timeout: int = 30) -> tuple[int, dict]:
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url=url,
        method="POST",
        data=data,
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=timeout) as response:
        body = response.read().decode("utf-8")
        return response.getcode(), json.loads(body)


def _get_json(url: str, timeout: int = 10) -> tuple[int, dict]:
    with urllib.request.urlopen(url, timeout=timeout) as response:
        body = response.read().decode("utf-8")
        return response.getcode(), json.loads(body)


def _check_workflow_api(base_url: str = "http://127.0.0.1:8000") -> dict:
    health_url = f"{base_url}/api/v1/workflow/health"
    query_url = f"{base_url}/api/v1/workflow/query"
    probe_questions = [
        "Summarize concrete quality control requirements from the construction standards.",
        "What safety topics are covered by OSHA 29 CFR 1926?",
        "What does GSA P100 emphasize for federal facilities?",
    ]

    def _run_checks_with_http() -> dict:
        status_code, payload = _get_json(health_url)
        health_ok = status_code == 200 and str(payload.get("status")).lower() == "ok"

        query_results = []
        query_pass_count = 0
        for idx, question in enumerate(probe_questions, 1):
            payload = {
                "query": question,
                "session_id": f"construction-e2e-{idx}",
                "route_mode": "local_only",
            }
            started = time.perf_counter()
            code, result = _post_json(query_url, payload)
            latency_ms = (time.perf_counter() - started) * 1000
            success = bool(code == 200 and result.get("success") is True)
            response_text = str(result.get("response") or "")
            non_empty = len(response_text.strip()) > 0
            case_pass = success and non_empty
            if case_pass:
                query_pass_count += 1
            query_results.append(
                {
                    "question": question,
                    "http_code": code,
                    "success": success,
                    "non_empty_response": non_empty,
                    "response_preview": response_text[:180],
                    "latency_ms": round(latency_ms, 2),
                    "pass": case_pass,
                }
            )

        return {
            "transport": "http",
            "health_ok": health_ok,
            "query_pass_count": query_pass_count,
            "query_total": len(probe_questions),
            "results": query_results,
            "pass": bool(health_ok and query_pass_count == len(probe_questions)),
        }

    def _run_checks_with_testclient() -> dict:
        from fastapi.testclient import TestClient

        from backend.main import app

        query_results = []
        query_pass_count = 0
        with TestClient(app) as client:
            health_resp = client.get("/api/v1/workflow/health")
            try:
                payload = health_resp.json()
            except Exception:
                payload = {}
            health_ok = bool(
                health_resp.status_code == 200
                and str(payload.get("status")).lower() == "ok"
            )

            for idx, question in enumerate(probe_questions, 1):
                data = {
                    "query": question,
                    "session_id": f"construction-e2e-{idx}",
                    "route_mode": "local_only",
                }
                started = time.perf_counter()
                resp = client.post("/api/v1/workflow/query", json=data)
                latency_ms = (time.perf_counter() - started) * 1000
                try:
                    result = resp.json()
                except Exception:
                    result = {}
                success = bool(resp.status_code == 200 and result.get("success") is True)
                response_text = str(result.get("response") or "")
                non_empty = len(response_text.strip()) > 0
                case_pass = success and non_empty
                if case_pass:
                    query_pass_count += 1
                query_results.append(
                    {
                        "question": question,
                        "http_code": resp.status_code,
                        "success": success,
                        "non_empty_response": non_empty,
                        "response_preview": response_text[:180],
                        "latency_ms": round(latency_ms, 2),
                        "pass": case_pass,
                    }
                )

        return {
            "transport": "inprocess_testclient",
            "health_ok": health_ok,
            "query_pass_count": query_pass_count,
            "query_total": len(probe_questions),
            "results": query_results,
            "pass": bool(health_ok and query_pass_count == len(probe_questions)),
        }

    try:
        return _run_checks_with_http()
    except Exception as http_exc:
        try:
            fallback = _run_checks_with_testclient()
            fallback["fallback_reason"] = str(http_exc)
            return fallback
        except Exception as fallback_exc:
            return {
                "transport": "failed",
                "health_ok": False,
                "query_pass_count": 0,
                "query_total": len(probe_questions),
                "pass": False,
                "error": f"http error: {http_exc}; testclient error: {fallback_exc}",
            }


def run_validation() -> dict:
    started = time.perf_counter()
    vector_store = VectorStore()
    retriever = HybridRetriever(vector_store)
    retriever.build_bm25_index()

    storage = _check_storage(vector_store)
    retrieval_semantic = _run_retrieval_mode(
        mode="semantic", retriever=retriever, vector_store=vector_store, top_k=8
    )
    retrieval_hybrid = _run_retrieval_mode(
        mode="hybrid", retriever=retriever, vector_store=vector_store, top_k=8
    )
    retrieval_keyword = _run_retrieval_mode(
        mode="keyword", retriever=retriever, vector_store=vector_store, top_k=8
    )
    workflow_api = _check_workflow_api(base_url="http://127.0.0.1:8000")

    semantic_pass = retrieval_semantic["pass_rate"] >= 0.5
    hybrid_pass = retrieval_hybrid["pass_rate"] >= 0.75
    keyword_pass = retrieval_keyword["pass_rate"] >= 0.75
    mode_pass = bool(semantic_pass and hybrid_pass and keyword_pass)
    overall_pass = bool(storage["pass"] and workflow_api["pass"] and mode_pass)

    elapsed_ms = (time.perf_counter() - started) * 1000
    return {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "seed_dir": str(
            PROJECT_ROOT / "test_resources" / "documents" / "construction_seed_2026q1"
        ),
        "storage_validation": storage,
        "retrieval_validation": {
            "semantic": retrieval_semantic,
            "hybrid": retrieval_hybrid,
            "keyword_bm25": retrieval_keyword,
        },
        "workflow_api_validation": workflow_api,
        "acceptance": {
            "storage_pass": storage["pass"],
            "retrieval_modes_pass": mode_pass,
            "retrieval_thresholds": {
                "semantic_min_pass_rate": 0.5,
                "hybrid_min_pass_rate": 0.75,
                "keyword_min_pass_rate": 0.75,
            },
            "retrieval_mode_breakdown": {
                "semantic_pass": semantic_pass,
                "hybrid_pass": hybrid_pass,
                "keyword_pass": keyword_pass,
            },
            "workflow_api_pass": workflow_api["pass"],
            "overall_pass": overall_pass,
        },
        "elapsed_ms": round(elapsed_ms, 2),
    }


def main() -> int:
    report = run_validation()
    report_path = PROJECT_ROOT / "logs" / "construction_rag_e2e_validation_report.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(
        json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    acceptance = report["acceptance"]
    print("Construction RAG E2E validation finished.")
    print(f"storage_pass={acceptance['storage_pass']}")
    print(f"retrieval_modes_pass={acceptance['retrieval_modes_pass']}")
    print(f"workflow_api_pass={acceptance['workflow_api_pass']}")
    print(f"overall_pass={acceptance['overall_pass']}")
    print(f"Report: {report_path}")
    return 0 if acceptance["overall_pass"] else 2


if __name__ == "__main__":
    os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
    raise SystemExit(main())
