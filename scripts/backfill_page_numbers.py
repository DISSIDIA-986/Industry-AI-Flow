#!/usr/bin/env python3
"""Backfill document_chunks.page_number and repair stale document filepaths.

Why this exists
---------------
Existing demo documents were ingested before chunks carried page numbers, and
their recorded `documents.filepath` values point at wiped/deleted locations
(workspace/uploads was cleared; some seed copies were git-deleted). This script
retrofits page numbers WITHOUT re-embedding (vectors stay byte-identical) and
re-points filepaths to source files that still exist in the repo, so the
document preview renders again and citations can deep-link to a page.

How it works
------------
For each document:
  1. Resolve a source file (existing filepath first, else search the repo by
     basename, preferring the newest construction-seed copy).
  2. Re-point documents.filepath to the resolved file when the recorded path is
     missing.
  3. For PDFs: re-extract per-page text (same DocumentExtractor used at ingest),
     locate each STORED chunk's text inside the re-extracted full text, and read
     the page it falls on. Only writes page_number when the match rate clears a
     threshold (else leaves NULL — never guesses).
  4. TXT / non-paged formats: page_number stays NULL (citations deep-link via
     chunk scroll instead of a page jump).

Safe by default (dry-run). Pass --apply to write. Pass --doc <filename> to limit.
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Optional

# Ensure repo root on path when run directly.
REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from backend.config import settings  # noqa: E402
from backend.services.core.chunker import chunk_text  # noqa: E402
from backend.services.core.page_mapping import (  # noqa: E402
    compute_page_starts,
    offset_to_page,
)
from backend.services.core.vectorstore import VectorStore  # noqa: E402
from backend.services.document_processing.document_extractor import (  # noqa: E402
    DocumentExtractor,
)

# Directories searched (in order) when the recorded filepath is gone.
SEARCH_ROOTS = [
    REPO_ROOT / "test_resources" / "documents" / "construction_seed_20260313",
    REPO_ROOT / "test_resources" / "documents" / "construction_seed_2026q1",
    REPO_ROOT / "test_resources" / "documents",
    REPO_ROOT / "workspace" / "uploads",
    REPO_ROOT / "docs",
]

MATCH_THRESHOLD = 0.80  # fraction of chunks that must locate to trust mapping


def _build_basename_index() -> Dict[str, List[Path]]:
    index: Dict[str, List[Path]] = {}
    for root in SEARCH_ROOTS:
        if not root.exists():
            continue
        for dp, _dirs, files in os.walk(root):
            for f in files:
                index.setdefault(f, []).append(Path(dp) / f)
    return index


def _resolve_source(filename: str, filepath: Optional[str],
                    index: Dict[str, List[Path]]) -> Optional[Path]:
    if filepath:
        p = Path(filepath)
        if p.exists():
            return p
    hits = index.get(filename) or []
    return hits[0] if hits else None


def _page_numbers_for_pdf(src: Path, db_chunks: List[dict]) -> Optional[dict]:
    """Return {chunk_id: page} mapping + stats, or None if extraction failed."""
    extractor = DocumentExtractor(use_ocr=False)
    content = extractor.extract(src)
    page_texts = content.metadata.get("page_texts")
    if not isinstance(page_texts, list) or not page_texts:
        return None
    full_text = content.text
    page_starts = compute_page_starts(page_texts)

    mapping: Dict[int, int] = {}
    located = 0
    cursor = 0
    last_page = 1
    for row in db_chunks:
        chunk_id = int(row["chunk_id"])
        probe = str(row["content"] or "").strip()
        needle = probe[:80]
        page = last_page
        if needle:
            found = full_text.find(needle, cursor)
            if found == -1:
                found = full_text.find(needle)
            if found != -1:
                located += 1
                page = offset_to_page(found, page_starts) or last_page
                cursor = found + 1
        last_page = page
        mapping[chunk_id] = page
    return {
        "mapping": mapping,
        "located": located,
        "total": len(db_chunks),
        "num_pages": len(page_texts),
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true", help="write changes (default: dry-run)")
    ap.add_argument("--doc", help="limit to documents whose filename contains this string")
    args = ap.parse_args()

    index = _build_basename_index()
    vs = VectorStore()
    conn = vs.get_connection()
    cur = conn.cursor()

    cur.execute("SELECT id, filename, filepath, chunk_count FROM documents ORDER BY filename")
    docs = cur.fetchall()

    print(f"{'APPLY' if args.apply else 'DRY-RUN'} — {len(docs)} documents\n")
    summary = {"filepath_fixed": 0, "pages_written": 0, "docs_paged": 0, "docs_skipped": 0}

    for doc_id, filename, filepath, chunk_count in docs:
        if args.doc and args.doc.lower() not in (filename or "").lower():
            continue
        src = _resolve_source(filename, filepath, index)
        line = f"• {filename[:48]:48} chunks={chunk_count}"
        if src is None:
            print(line + "  -> NO SOURCE (page_number left NULL)")
            summary["docs_skipped"] += 1
            continue

        # Re-point filepath if recorded path is missing.
        fp_fixed = ""
        if not (filepath and Path(filepath).exists()):
            fp_fixed = f"  filepath->{src}"
            summary["filepath_fixed"] += 1
            if args.apply:
                cur.execute(
                    "UPDATE documents SET filepath = %s WHERE id = %s",
                    (str(src), doc_id),
                )

        ext = src.suffix.lower()
        if ext != ".pdf":
            print(line + f"  [{ext}] non-paged -> NULL{fp_fixed}")
            if args.apply:
                conn.commit()
            continue

        cur.execute(
            "SELECT chunk_id, content FROM document_chunks WHERE doc_id = %s ORDER BY chunk_id ASC",
            (doc_id,),
        )
        db_chunks = [{"chunk_id": r[0], "content": r[1]} for r in cur.fetchall()]
        if not db_chunks:
            print(line + f"  no chunks in DB{fp_fixed}")
            if args.apply:
                conn.commit()
            continue

        try:
            result = _page_numbers_for_pdf(src, db_chunks)
        except Exception as exc:  # pragma: no cover - per-doc resilience
            print(line + f"  EXTRACT FAILED: {exc}{fp_fixed}")
            summary["docs_skipped"] += 1
            if args.apply:
                conn.commit()
            continue

        if result is None:
            print(line + f"  no page_texts -> NULL{fp_fixed}")
            if args.apply:
                conn.commit()
            continue

        match_rate = result["located"] / max(1, result["total"])
        pages_seen = sorted(set(result["mapping"].values()))
        page_span = f"p{pages_seen[0]}..{pages_seen[-1]}" if pages_seen else "-"
        verdict = "WRITE" if match_rate >= MATCH_THRESHOLD else "LOW-MATCH skip"
        print(
            line
            + f"  match={match_rate:.0%} pages={result['num_pages']} span={page_span}"
            + f"  [{verdict}]{fp_fixed}"
        )

        if match_rate >= MATCH_THRESHOLD:
            summary["docs_paged"] += 1
            if args.apply:
                for chunk_id, page in result["mapping"].items():
                    cur.execute(
                        "UPDATE document_chunks SET page_number = %s WHERE doc_id = %s AND chunk_id = %s",
                        (page, doc_id, chunk_id),
                    )
                summary["pages_written"] += len(result["mapping"])
        else:
            summary["docs_skipped"] += 1

        if args.apply:
            conn.commit()

    cur.close()
    conn.close()
    print("\nSummary:", summary)
    if not args.apply:
        print("Dry-run only. Re-run with --apply to write.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
