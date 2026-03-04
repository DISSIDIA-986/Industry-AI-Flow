#!/usr/bin/env python3
"""Generate randomized RAG question bank CSV from vectorized documents."""

from __future__ import annotations

import argparse
import csv
import math
import random
import re
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.services.core.vectorstore import VectorStore

WORD_RE = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)?")
SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+")
WS_RE = re.compile(r"\s+")

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

TURN_TEMPLATES: dict[int, tuple[str, ...]] = {
    1: (
        "What does this document require for \"{topic1}\"?",
        "Explain the core rule around \"{topic1}\" in this standard.",
        "From this source, what is the key expectation for \"{topic1}\"?",
    ),
    2: (
        "Summarize the main points about \"{topic1}\" and \"{topic2}\" from this document.",
        "Give a concise summary of the guidance related to \"{topic1}\".",
        "What are the most important requirements tied to \"{topic1}\" here?",
    ),
    3: (
        "Based on your previous answer, provide one concrete evidence detail for \"{topic1}\".",
        "Continue the thread and cite a specific clause or detail about \"{topic1}\".",
        "From the same source, what exact evidence supports the point about \"{topic1}\"?",
    ),
    4: (
        "Considering \"{topic1}\" and \"{topic2}\", what risk or trade-off should a project team watch?",
        "How should teams balance \"{topic1}\" versus \"{topic2}\" in practice?",
        "What conflict or dependency can occur between \"{topic1}\" and \"{topic2}\"?",
    ),
    5: (
        "Using this conversation context, propose a 3-step checklist for \"{topic1}\".",
        "From this thread, suggest next actions to implement the requirements for \"{topic1}\".",
        "What follow-up questions should be asked next to validate \"{topic1}\" execution?",
    ),
}

TURN_TYPE = {
    1: "understanding",
    2: "summary",
    3: "follow_up",
    4: "reasoning",
    5: "multi_turn_action",
}


@dataclass(frozen=True)
class ChunkRow:
    chunk_id: int
    content: str


@dataclass(frozen=True)
class DocumentRow:
    doc_id: str
    filename: str
    chunk_count: int


def _normalize_text(text: str) -> str:
    return WS_RE.sub(" ", str(text or "")).strip().lower()


def _tokenize(text: str) -> list[str]:
    return WORD_RE.findall(_normalize_text(text))


def _clean_excerpt(text: str, *, max_chars: int = 220) -> str:
    cleaned = WS_RE.sub(" ", str(text or "")).strip()
    if len(cleaned) <= max_chars:
        return cleaned
    return cleaned[: max_chars - 3].rstrip() + "..."


def _extract_excerpt(content: str, rng: random.Random) -> str:
    normalized = _normalize_text(content)
    if not normalized:
        return ""

    candidates: list[str] = []
    for sentence in SENTENCE_SPLIT_RE.split(normalized):
        text = sentence.strip()
        words = _tokenize(text)
        if 8 <= len(words) <= 40:
            candidates.append(text)
    if candidates:
        return _clean_excerpt(rng.choice(candidates))

    words = _tokenize(normalized)
    if not words:
        return ""
    return _clean_excerpt(" ".join(words[:30]))


def _is_term_candidate(token: str) -> bool:
    token = str(token or "").strip().lower()
    if not token or token in STOPWORDS:
        return False
    if token.isdigit():
        return False
    compact = token.replace("-", "")
    if not compact:
        return False
    if len(compact) < 4 and not any(ch.isdigit() for ch in compact):
        return False
    if compact.isalpha() and sum(1 for ch in compact if ch in "aeiou") == 0:
        return False
    return True


def _extract_terms(text: str, *, limit: int = 6) -> list[str]:
    terms: list[str] = []
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


def _topic_from_terms(terms: Iterable[str], fallback: str) -> str:
    filtered = [item for item in terms if item]
    if not filtered:
        return fallback
    if len(filtered) == 1:
        return filtered[0]
    return f"{filtered[0]} {filtered[1]}"


def _doc_label(filename: str) -> str:
    stem = Path(filename).stem
    return re.sub(r"[_-]+", " ", stem).strip()


def _load_documents(vector_store: VectorStore) -> list[DocumentRow]:
    conn = vector_store.get_connection()
    cur = conn.cursor()
    try:
        cur.execute(
            """
            SELECT d.id::text, d.filename, COUNT(dc.id) AS chunk_count
            FROM documents d
            JOIN document_chunks dc ON dc.doc_id = d.id
            WHERE dc.embedding IS NOT NULL
            GROUP BY d.id, d.filename
            ORDER BY d.filename;
            """
        )
        rows = cur.fetchall()
        return [DocumentRow(doc_id=row[0], filename=row[1], chunk_count=int(row[2])) for row in rows]
    finally:
        cur.close()
        conn.close()


def _load_chunks(vector_store: VectorStore, doc_id: str, *, min_chars: int) -> list[ChunkRow]:
    conn = vector_store.get_connection()
    cur = conn.cursor()
    try:
        cur.execute(
            """
            SELECT chunk_id, content
            FROM document_chunks
            WHERE doc_id = %s
              AND content IS NOT NULL
              AND LENGTH(TRIM(content)) >= %s
            ORDER BY chunk_id;
            """,
            (doc_id, min_chars),
        )
        rows = cur.fetchall()
        return [ChunkRow(chunk_id=int(row[0]), content=str(row[1])) for row in rows]
    finally:
        cur.close()
        conn.close()


def build_question_bank(
    *,
    questions_per_doc: int,
    seed: int,
    min_chars: int,
) -> tuple[list[dict[str, str]], dict[str, int]]:
    rng = random.Random(seed)
    vector_store = VectorStore()
    docs = _load_documents(vector_store)
    if not docs:
        raise RuntimeError("No vectorized documents found in database.")

    records: list[dict[str, str]] = []
    counts: dict[str, int] = {}
    global_index = 0

    for doc_index, doc in enumerate(docs, start=1):
        chunks = _load_chunks(vector_store, doc.doc_id, min_chars=min_chars)
        if not chunks:
            chunks = _load_chunks(vector_store, doc.doc_id, min_chars=1)
        if not chunks:
            continue

        groups = math.ceil(questions_per_doc / 5)
        doc_records: list[dict[str, str]] = []

        for group_index in range(1, groups + 1):
            chunk_a = rng.choice(chunks)
            chunk_b = rng.choice(chunks) if len(chunks) == 1 else rng.choice([c for c in chunks if c.chunk_id != chunk_a.chunk_id])

            excerpt_a = _extract_excerpt(chunk_a.content, rng)
            excerpt_b = _extract_excerpt(chunk_b.content, rng)

            terms_a = _extract_terms(excerpt_a or chunk_a.content)
            terms_b = _extract_terms(excerpt_b or chunk_b.content)

            topic1 = _topic_from_terms(terms_a, fallback="compliance requirement")
            topic2 = _topic_from_terms(terms_b, fallback="implementation detail")

            for turn_index in range(1, 6):
                template = rng.choice(TURN_TEMPLATES[turn_index])
                question = template.format(
                    topic1=topic1,
                    topic2=topic2,
                    doc_label=_doc_label(doc.filename),
                )
                global_index += 1
                doc_records.append(
                    {
                        "question_id": f"Q{global_index:04d}",
                        "document_index": str(doc_index),
                        "document_filename": doc.filename,
                        "document_question_index": str(len(doc_records) + 1),
                        "conversation_group": f"{Path(doc.filename).stem}-g{group_index:02d}",
                        "turn_index": str(turn_index),
                        "question_type": TURN_TYPE[turn_index],
                        "question_text": question,
                        "source_chunk_id": str(chunk_a.chunk_id),
                        "secondary_chunk_id": str(chunk_b.chunk_id),
                        "topic_primary": topic1,
                        "topic_secondary": topic2,
                        "source_excerpt": excerpt_a,
                        "secondary_excerpt": excerpt_b,
                        "random_seed": str(seed),
                    }
                )

        trimmed = doc_records[:questions_per_doc]
        counts[doc.filename] = len(trimmed)
        records.extend(trimmed)

    return records, counts


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate randomized RAG question bank CSV from vectorized documents."
    )
    parser.add_argument(
        "--output",
        default=str(PROJECT_ROOT / "docs" / "testing" / "rag_question_bank_180.csv"),
    )
    parser.add_argument("--questions-per-doc", type=int, default=20)
    parser.add_argument("--seed", type=int, default=20260303)
    parser.add_argument("--min-content-chars", type=int, default=180)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    records, counts = build_question_bank(
        questions_per_doc=max(1, int(args.questions_per_doc)),
        seed=int(args.seed),
        min_chars=max(1, int(args.min_content_chars)),
    )

    generated_at = datetime.now(timezone.utc).isoformat()
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    fieldnames = [
        "generated_at_utc",
        "question_id",
        "document_index",
        "document_filename",
        "document_question_index",
        "conversation_group",
        "turn_index",
        "question_type",
        "question_text",
        "source_chunk_id",
        "secondary_chunk_id",
        "topic_primary",
        "topic_secondary",
        "source_excerpt",
        "secondary_excerpt",
        "random_seed",
    ]

    with output_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for record in records:
            writer.writerow({"generated_at_utc": generated_at, **record})

    print("RAG question bank generation complete.")
    print(f"output={output_path}")
    print(f"total_questions={len(records)}")
    print(f"documents={len(counts)}")
    for filename, count in sorted(counts.items()):
        print(f"{filename}\t{count}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
