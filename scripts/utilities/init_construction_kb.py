#!/usr/bin/env python3
"""Initialize construction knowledge base from downloaded seed documents."""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import fitz

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.services.core.chunker import chunk_text
from backend.services.core.embedder import embed_texts
from backend.services.core.vectorstore import VectorStore
from backend.services.document_loader import EnhancedDocumentLoader


def _normalize_text(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    lines = [ln.strip() for ln in text.split("\n")]
    return "\n".join(ln for ln in lines if ln)


def _pdf_page_count(path: Path) -> int:
    doc = fitz.open(path)
    pages = len(doc)
    doc.close()
    return pages


def _delete_existing_by_filepath(store: VectorStore, filepath: str) -> int:
    conn = store.get_connection()
    cur = conn.cursor()
    try:
        cur.execute("SELECT id FROM documents WHERE filepath = %s;", (filepath,))
        rows = cur.fetchall()
        if not rows:
            conn.commit()
            return 0
        ids = [row[0] for row in rows]
        cur.execute("DELETE FROM document_chunks WHERE doc_id = ANY(%s);", (ids,))
        cur.execute("DELETE FROM documents WHERE id = ANY(%s);", (ids,))
        conn.commit()
        return len(ids)
    finally:
        cur.close()
        conn.close()


def run_init(
    source_dir: Path,
    chunk_size: int,
    chunk_overlap: int,
    retrieval_top_k: int,
    max_file_mb: int,
    max_pdf_pages: int,
    use_ocr: bool,
    report_path: Path,
) -> dict:
    start = time.perf_counter()
    source_dir = source_dir.resolve()
    if not source_dir.exists():
        raise FileNotFoundError(f"source_dir not found: {source_dir}")

    store = VectorStore()
    loader = EnhancedDocumentLoader(use_ocr=use_ocr)

    supported_ext = {".pdf", ".txt"}
    files = sorted(
        [
            p
            for p in source_dir.iterdir()
            if p.is_file() and p.suffix.lower() in supported_ext
        ]
    )

    report = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "source_dir": str(source_dir),
        "parameters": {
            "chunk_size": chunk_size,
            "chunk_overlap": chunk_overlap,
            "max_file_mb": max_file_mb,
            "max_pdf_pages": max_pdf_pages,
            "use_ocr": use_ocr,
            "retrieval_recommendation": {
                "top_k": retrieval_top_k,
                "vector_weight": 0.7,
                "bm25_weight": 0.3,
            },
        },
        "ingested": [],
        "skipped": [],
    }

    for index, path in enumerate(files, 1):
        size_mb = path.stat().st_size / 1024 / 1024
        if size_mb > max_file_mb:
            report["skipped"].append(
                {"file": path.name, "reason": f"file too large ({size_mb:.1f}MB)"}
            )
            continue

        page_count = None
        if path.suffix.lower() == ".pdf":
            page_count = _pdf_page_count(path)
            if page_count > max_pdf_pages:
                report["skipped"].append(
                    {
                        "file": path.name,
                        "reason": f"pdf too many pages ({page_count})",
                    }
                )
                continue

        print(f"[{index:02d}/{len(files)}] Processing {path.name}")
        t0 = time.perf_counter()
        text = loader.load_document(path)
        text = _normalize_text(text)
        if not text:
            report["skipped"].append(
                {"file": path.name, "reason": "empty extracted text"}
            )
            continue

        chunk_dicts = chunk_text(
            text, chunk_size=chunk_size, chunk_overlap=chunk_overlap
        )
        chunk_contents = [chunk["content"] for chunk in chunk_dicts]
        embeddings = embed_texts(chunk_contents)

        deleted = _delete_existing_by_filepath(store, str(path))
        doc_id = store.store_document_with_chunks(
            filename=path.name,
            filepath=str(path),
            chunks=chunk_contents,
            embeddings=embeddings,
            size_bytes=int(path.stat().st_size),
        )
        elapsed_ms = (time.perf_counter() - t0) * 1000
        report["ingested"].append(
            {
                "file": path.name,
                "doc_id": doc_id,
                "chars": len(text),
                "chunks": len(chunk_contents),
                "page_count": page_count,
                "size_mb": round(size_mb, 2),
                "replaced_existing_docs": deleted,
                "elapsed_ms": round(elapsed_ms, 2),
            }
        )

    total_elapsed = (time.perf_counter() - start) * 1000
    report["summary"] = {
        "ingested_files": len(report["ingested"]),
        "skipped_files": len(report["skipped"]),
        "total_chunks": sum(item["chunks"] for item in report["ingested"]),
        "elapsed_ms": round(total_elapsed, 2),
    }

    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="Initialize construction KB.")
    parser.add_argument(
        "--source-dir",
        default=str(
            PROJECT_ROOT / "test_resources" / "documents" / "construction_seed_2026q1"
        ),
    )
    parser.add_argument(
        "--chunk-size", type=int, default=int(os.getenv("CHUNK_SIZE", "800"))
    )
    parser.add_argument(
        "--chunk-overlap", type=int, default=int(os.getenv("CHUNK_OVERLAP", "120"))
    )
    parser.add_argument("--top-k", type=int, default=int(os.getenv("TOP_K", "10")))
    parser.add_argument("--max-file-mb", type=int, default=30)
    parser.add_argument("--max-pdf-pages", type=int, default=500)
    parser.add_argument("--disable-ocr", action="store_true")
    parser.add_argument(
        "--report-path",
        default=str(PROJECT_ROOT / "logs" / "construction_kb_init_report.json"),
    )
    args = parser.parse_args()

    report = run_init(
        source_dir=Path(args.source_dir),
        chunk_size=args.chunk_size,
        chunk_overlap=args.chunk_overlap,
        retrieval_top_k=args.top_k,
        max_file_mb=args.max_file_mb,
        max_pdf_pages=args.max_pdf_pages,
        use_ocr=not args.disable_ocr,
        report_path=Path(args.report_path),
    )

    summary = report["summary"]
    print("Initialization finished.")
    print(
        f"Ingested={summary['ingested_files']} Skipped={summary['skipped_files']} "
        f"TotalChunks={summary['total_chunks']}"
    )
    print(f"Report: {args.report_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
