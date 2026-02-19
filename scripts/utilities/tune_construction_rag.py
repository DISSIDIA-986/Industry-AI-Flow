#!/usr/bin/env python3
"""Run a first-round RAG tuning sweep for construction knowledge documents."""

from __future__ import annotations

import json
import os
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.services.core.chunker import chunk_text
from backend.services.core.embedder import embed_texts
from backend.services.core.vectorstore import VectorStore
from backend.services.document_loader import EnhancedDocumentLoader
from backend.services.rag_engine import SimpleRAG


@dataclass
class QueryCase:
    query: str
    expected_keywords: list[str]
    expected_source_hint: str


TUNING_QUERIES: list[QueryCase] = [
    QueryCase(
        query="What does P100 say about facilities standards and design requirements?",
        expected_keywords=["standards", "design", "requirements"],
        expected_source_hint="p100",
    ),
    QueryCase(
        query="What are the key requirements for cast-in-place concrete quality control?",
        expected_keywords=["concrete", "quality", "requirements"],
        expected_source_hint="03_30_00",
    ),
    QueryCase(
        query="Which topics are covered in OSHA 29 CFR 1926 construction safety rules?",
        expected_keywords=["construction", "safety", "1926"],
        expected_source_hint="osha",
    ),
    QueryCase(
        query="What information is included in IFC 4.3 schema specifications?",
        expected_keywords=["ifc", "schema", "specifications"],
        expected_source_hint="ifc",
    ),
    QueryCase(
        query="How are submittal requirements described in GSA core standards?",
        expected_keywords=["submittal", "core", "standards"],
        expected_source_hint="gsa",
    ),
]


def _normalize_text(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    lines = [ln.strip() for ln in text.split("\n")]
    compact = "\n".join(ln for ln in lines if ln)
    return compact


def _source_docs(seed_dir: Path) -> list[Path]:
    candidates = [
        "gsa_p100_2024_final.pdf",
        "ufgs_03_30_00_cast_in_place_concrete.pdf",
        "gsa_core_building_standards_memo_2025.pdf",
        "osha_29_cfr_1926.txt",
        "buildingsmart_ifc_4_3_schema_specifications.txt",
    ]
    docs: list[Path] = []
    for name in candidates:
        path = seed_dir / name
        if path.exists():
            docs.append(path)
    return docs


def _purge_tuning_docs(store: VectorStore) -> None:
    conn = store.get_connection()
    cur = conn.cursor()
    try:
        cur.execute("SELECT id FROM documents WHERE filepath LIKE 'tune://%';")
        rows = cur.fetchall()
        if not rows:
            conn.commit()
            return
        ids = [row[0] for row in rows]
        cur.execute("DELETE FROM document_chunks WHERE doc_id = ANY(%s);", (ids,))
        cur.execute("DELETE FROM documents WHERE id = ANY(%s);", (ids,))
        conn.commit()
    finally:
        cur.close()
        conn.close()


def _evaluate_case(results: list[dict], case: QueryCase) -> float:
    if not results:
        return 0.0
    text_blob = " ".join(r.get("content", "") for r in results).lower()
    keyword_hits = sum(1 for k in case.expected_keywords if k.lower() in text_blob)
    keyword_score = keyword_hits / len(case.expected_keywords)
    source_hit = any(
        case.expected_source_hint in r.get("filename", "").lower() for r in results
    )
    source_score = 1.0 if source_hit else 0.0
    return 0.7 * keyword_score + 0.3 * source_score


def run_tuning(seed_dir: Path, report_path: Path) -> dict:
    loader = EnhancedDocumentLoader(use_ocr=False)
    store = VectorStore()

    raw_docs: list[dict] = []
    for path in _source_docs(seed_dir):
        content = loader.load_document(path)
        raw_docs.append({"path": path, "content": _normalize_text(content)})

    if not raw_docs:
        raise RuntimeError(f"No tuning documents found under {seed_dir}")

    chunk_grid = [
        (300, 50),
        (512, 128),
        (800, 120),
    ]
    retrieval_grid = [
        (5, 0.8, 0.2),
        (5, 0.7, 0.3),
        (5, 0.6, 0.4),
        (8, 0.8, 0.2),
        (8, 0.7, 0.3),
        (8, 0.6, 0.4),
        (10, 0.8, 0.2),
        (10, 0.7, 0.3),
        (10, 0.6, 0.4),
    ]

    runs: list[dict] = []

    for chunk_size, chunk_overlap in chunk_grid:
        _purge_tuning_docs(store)

        chunk_counts: dict[str, int] = {}
        for entry in raw_docs:
            path = entry["path"]
            content = entry["content"]
            chunks = chunk_text(
                content, chunk_size=chunk_size, chunk_overlap=chunk_overlap
            )
            chunk_contents = [c["content"] for c in chunks]
            embeddings = embed_texts(chunk_contents)
            filename = f"tune::{path.name}"
            filepath = f"tune://{path.name}"
            store.store_document_with_chunks(
                filename=filename,
                filepath=filepath,
                chunks=chunk_contents,
                embeddings=embeddings,
            )
            chunk_counts[path.name] = len(chunks)

        rag = SimpleRAG(
            use_hybrid_search=True,
            use_reranker=False,
            enable_feedback=False,
        )
        rag.hybrid_retriever.build_bm25_index()

        for top_k, v_w, b_w in retrieval_grid:
            t0 = time.perf_counter()
            query_scores: list[float] = []
            for case in TUNING_QUERIES:
                results = rag.hybrid_retriever.search(
                    query=case.query,
                    top_k=top_k,
                    vector_weight=v_w,
                    bm25_weight=b_w,
                )
                query_scores.append(_evaluate_case(results, case))
            elapsed = (time.perf_counter() - t0) * 1000
            avg_score = sum(query_scores) / len(query_scores)
            runs.append(
                {
                    "chunk_size": chunk_size,
                    "chunk_overlap": chunk_overlap,
                    "top_k": top_k,
                    "vector_weight": v_w,
                    "bm25_weight": b_w,
                    "avg_query_score": round(avg_score, 4),
                    "query_scores": [round(s, 4) for s in query_scores],
                    "latency_ms_total": round(elapsed, 2),
                    "chunk_counts": chunk_counts,
                }
            )

    runs_sorted = sorted(
        runs,
        key=lambda x: (x["avg_query_score"], -x["latency_ms_total"]),
        reverse=True,
    )
    best = runs_sorted[0]

    _purge_tuning_docs(store)

    report = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "seed_dir": str(seed_dir.resolve()),
        "tuning_docs": [doc["path"].name for doc in raw_docs],
        "query_count": len(TUNING_QUERIES),
        "best_config": best,
        "all_runs": runs_sorted,
    }
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(
        json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    return report


def main() -> int:
    seed_dir = PROJECT_ROOT / "test_resources" / "documents" / "construction_seed_2026q1"
    report_path = PROJECT_ROOT / "logs" / "construction_rag_tuning_report.json"
    report = run_tuning(seed_dir=seed_dir, report_path=report_path)
    best = report["best_config"]
    print("Tuning finished.")
    print(f"Best chunk_size={best['chunk_size']} overlap={best['chunk_overlap']}")
    print(
        "Best retrieval: "
        f"top_k={best['top_k']} vector_weight={best['vector_weight']} "
        f"bm25_weight={best['bm25_weight']}"
    )
    print(f"Best avg_query_score={best['avg_query_score']}")
    print(f"Report: {report_path}")
    return 0


if __name__ == "__main__":
    os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
    raise SystemExit(main())
