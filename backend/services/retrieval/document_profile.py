"""Lightweight document-profile layer for query routing and follow-up guidance."""

from __future__ import annotations

import json
import logging
import re
import threading
from collections import Counter
from typing import Any, Dict, Iterable, List, Optional, Sequence

logger = logging.getLogger(__name__)

_TOKEN_RE = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)?")
_SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+")
_HEADING_RE = re.compile(r"^\s*(?:\d+(?:\.\d+){0,3}\s+)?[A-Za-z][A-Za-z0-9\-\s:/]{3,80}$")

# Common website UI / navigation strings that leak through OCR/scraping.
# Include both clean and garbled (OCR-truncated) variants.
_UI_ARTIFACT_STEMS = {
    "select", "language", "skip", "content", "cookie", "privacy",
    "terms", "service", "loading", "search", "print", "share",
    "navigation", "menu", "sidebar", "footer", "header", "toolbar",
    "bookmark", "download", "upload", "subscribe", "login", "logout",
}


def _is_plausible_heading(text: str) -> bool:
    """Return False for OCR artifacts, UI chrome, and garbled text."""
    words = text.split()
    if not words:
        return False
    # Reject if most words are very short (< 3 chars) — sign of OCR garbage
    short_words = sum(1 for w in words if len(w) < 3)
    if len(words) >= 2 and short_words / len(words) > 0.6:
        return False
    # Reject headings where multiple words are prefix-matches of known UI stems.
    # Catches OCR-truncated UI text like "Selec Targe Language" → stems: select, target, language
    lowered_words = [w.lower() for w in words]
    ui_hits = 0
    for w in lowered_words:
        for stem in _UI_ARTIFACT_STEMS:
            if len(w) >= 4 and (stem.startswith(w) or w.startswith(stem)):
                ui_hits += 1
                break
    if len(words) >= 2 and ui_hits >= 2:
        return False
    # Reject if it looks like a garbled phrase — multiple words with no vowels
    _vowels = set("aeiouAEIOU")
    no_vowel_words = sum(1 for w in words if len(w) > 2 and not (_vowels & set(w)))
    if len(words) >= 2 and no_vowel_words / len(words) > 0.5:
        return False
    return True


_STOPWORDS = {
    "about",
    "after",
    "again",
    "also",
    "among",
    "been",
    "before",
    "between",
    "being",
    "building",
    "construction",
    "context",
    "document",
    "from",
    "into",
    "must",
    "only",
    "other",
    "required",
    "requirement",
    "requirements",
    "section",
    "shall",
    "should",
    "standard",
    "than",
    "that",
    "their",
    "there",
    "these",
    "this",
    "with",
    "within",
    "which",
}


def _normalize_text(value: str) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip().lower()


def _tokenize(value: str) -> List[str]:
    return _TOKEN_RE.findall(_normalize_text(value))


def _is_keyword_token(token: str) -> bool:
    token = str(token or "").strip().lower()
    if not token or token in _STOPWORDS:
        return False
    compact = token.replace("-", "")
    if len(compact) < 4:
        return False
    if compact.isdigit():
        return False
    return any(ch in "aeiou" for ch in compact)


class DocumentProfileService:
    """Stores and scores compact document profiles for RAG routing."""

    def __init__(self, vectorstore: Any):
        self.vectorstore = vectorstore
        self._table_ready = False
        self._table_lock = threading.Lock()

    def _ensure_table(self) -> None:
        if self._table_ready:
            return
        with self._table_lock:
            if self._table_ready:
                return

            conn = self.vectorstore.get_connection()
            cur = conn.cursor()
            try:
                cur.execute(
                    """
                    CREATE TABLE IF NOT EXISTS document_profiles (
                        doc_id VARCHAR(255) PRIMARY KEY,
                        filename VARCHAR(255) NOT NULL,
                        summary TEXT NOT NULL,
                        outline JSONB DEFAULT '[]'::jsonb,
                        keywords JSONB DEFAULT '[]'::jsonb,
                        chunk_count INTEGER NOT NULL DEFAULT 0,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (doc_id) REFERENCES documents(id) ON DELETE CASCADE
                    )
                    """
                )
                cur.execute(
                    """
                    CREATE INDEX IF NOT EXISTS idx_document_profiles_updated
                    ON document_profiles(updated_at DESC)
                    """
                )
                try:
                    cur.execute(
                        """
                        CREATE INDEX IF NOT EXISTS idx_document_profiles_summary_fts
                        ON document_profiles USING gin (to_tsvector('simple', summary))
                        """
                    )
                except Exception:
                    conn.rollback()
                    cur.execute(
                        """
                        CREATE TABLE IF NOT EXISTS document_profiles (
                            doc_id VARCHAR(255) PRIMARY KEY,
                            filename VARCHAR(255) NOT NULL,
                            summary TEXT NOT NULL,
                            outline JSONB DEFAULT '[]'::jsonb,
                            keywords JSONB DEFAULT '[]'::jsonb,
                            chunk_count INTEGER NOT NULL DEFAULT 0,
                            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                            FOREIGN KEY (doc_id) REFERENCES documents(id) ON DELETE CASCADE
                        )
                        """
                    )
                conn.commit()
                self._table_ready = True
            except Exception:
                conn.rollback()
                raise
            finally:
                cur.close()
                conn.close()

    def _fetch_document_chunks(self, doc_id: str) -> tuple[str, int, List[str]]:
        conn = self.vectorstore.get_connection()
        cur = conn.cursor()
        try:
            cur.execute(
                "SELECT filename, chunk_count FROM documents WHERE id = %s",
                (doc_id,),
            )
            row = cur.fetchone()
            if not row:
                return "", 0, []

            filename = str(row[0] or "")
            chunk_count = int(row[1] or 0)
            cur.execute(
                """
                SELECT content
                FROM document_chunks
                WHERE doc_id = %s
                ORDER BY chunk_id
                LIMIT 220
                """,
                (doc_id,),
            )
            chunks = [str(item[0] or "").strip() for item in cur.fetchall()]
            return filename, chunk_count, [item for item in chunks if item]
        finally:
            cur.close()
            conn.close()

    @staticmethod
    def _extract_outline(chunks: Sequence[str]) -> List[str]:
        lines: List[str] = []
        seen: set[str] = set()
        for chunk in chunks[:40]:
            for line in str(chunk).splitlines():
                clean = re.sub(r"\s+", " ", line).strip()
                if len(clean) < 6 or len(clean) > 90:
                    continue
                if clean.lower() in seen:
                    continue
                if not _HEADING_RE.match(clean):
                    continue
                if not _is_plausible_heading(clean):
                    continue
                seen.add(clean.lower())
                lines.append(clean)
                if len(lines) >= 10:
                    return lines
        return lines

    @staticmethod
    def _extract_keywords(chunks: Sequence[str], limit: int = 14) -> List[str]:
        counter: Counter[str] = Counter()
        for chunk in chunks:
            counter.update(token for token in _tokenize(chunk) if _is_keyword_token(token))
        if not counter:
            return []
        ranked = sorted(counter.items(), key=lambda item: (-item[1], item[0]))
        return [token for token, _ in ranked[:limit]]

    @staticmethod
    def _extract_summary(chunks: Sequence[str], keywords: Sequence[str]) -> str:
        sentences: List[str] = []
        for chunk in chunks[:70]:
            normalized = re.sub(r"\s+", " ", str(chunk or "")).strip()
            if not normalized:
                continue
            for sentence in _SENTENCE_SPLIT_RE.split(normalized):
                text = sentence.strip()
                words = _tokenize(text)
                if 8 <= len(words) <= 36:
                    sentences.append(text)
                if len(sentences) >= 160:
                    break
            if len(sentences) >= 160:
                break

        if not sentences:
            fallback = re.sub(r"\s+", " ", " ".join(chunks[:3])).strip()
            return fallback[:520]

        keyword_set = set(keywords)
        scored: List[tuple[float, int, str]] = []
        for index, sentence in enumerate(sentences):
            sentence_tokens = _tokenize(sentence)
            overlap = sum(1 for token in sentence_tokens if token in keyword_set)
            length_bonus = min(len(sentence_tokens), 26) / 26.0
            score = overlap + 0.2 * length_bonus
            scored.append((score, index, sentence))

        scored.sort(key=lambda item: (-item[0], item[1]))
        selected: List[str] = []
        seen = set()
        total_chars = 0
        for _, _, sentence in scored:
            key = sentence.lower()
            if key in seen:
                continue
            seen.add(key)
            selected.append(sentence)
            total_chars += len(sentence)
            if len(selected) >= 4 or total_chars >= 520:
                break

        return " ".join(selected)[:560].strip()

    def refresh_profile_for_document(self, doc_id: str) -> bool:
        self._ensure_table()
        filename, chunk_count, chunks = self._fetch_document_chunks(doc_id)
        if not filename:
            return False

        if chunk_count <= 0 or not chunks:
            self.remove_profile(doc_id)
            return False

        keywords = self._extract_keywords(chunks)
        outline = self._extract_outline(chunks)
        summary = self._extract_summary(chunks, keywords)
        if not summary:
            summary = "No summary available."

        conn = self.vectorstore.get_connection()
        cur = conn.cursor()
        try:
            cur.execute(
                """
                INSERT INTO document_profiles (
                    doc_id,
                    filename,
                    summary,
                    outline,
                    keywords,
                    chunk_count,
                    updated_at
                )
                VALUES (%s, %s, %s, %s::jsonb, %s::jsonb, %s, CURRENT_TIMESTAMP)
                ON CONFLICT (doc_id) DO UPDATE SET
                    filename = EXCLUDED.filename,
                    summary = EXCLUDED.summary,
                    outline = EXCLUDED.outline,
                    keywords = EXCLUDED.keywords,
                    chunk_count = EXCLUDED.chunk_count,
                    updated_at = CURRENT_TIMESTAMP
                """,
                (
                    doc_id,
                    filename,
                    summary,
                    json.dumps(outline, ensure_ascii=False),
                    json.dumps(keywords, ensure_ascii=False),
                    chunk_count,
                ),
            )
            conn.commit()
            return True
        except Exception:
            conn.rollback()
            raise
        finally:
            cur.close()
            conn.close()

    def remove_profile(self, doc_id: str) -> None:
        self._ensure_table()
        conn = self.vectorstore.get_connection()
        cur = conn.cursor()
        try:
            cur.execute("DELETE FROM document_profiles WHERE doc_id = %s", (doc_id,))
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            cur.close()
            conn.close()

    def refresh_profiles_if_stale(self, doc_ids: Sequence[str]) -> int:
        self._ensure_table()
        unique_doc_ids = sorted({str(doc_id or "").strip() for doc_id in doc_ids if doc_id})
        if not unique_doc_ids:
            return 0

        conn = self.vectorstore.get_connection()
        cur = conn.cursor()
        try:
            cur.execute(
                """
                SELECT id, chunk_count
                FROM documents
                WHERE id = ANY(%s)
                """,
                (unique_doc_ids,),
            )
            documents = {str(row[0]): int(row[1] or 0) for row in cur.fetchall()}
            if not documents:
                return 0

            cur.execute(
                """
                SELECT doc_id, chunk_count
                FROM document_profiles
                WHERE doc_id = ANY(%s)
                """,
                (list(documents.keys()),),
            )
            profiles = {str(row[0]): int(row[1] or 0) for row in cur.fetchall()}
        finally:
            cur.close()
            conn.close()

        stale_ids = [
            doc_id
            for doc_id, chunk_count in documents.items()
            if chunk_count > 0 and profiles.get(doc_id) != chunk_count
        ]
        refreshed = 0
        for doc_id in stale_ids:
            try:
                if self.refresh_profile_for_document(doc_id):
                    refreshed += 1
            except Exception as exc:  # pragma: no cover - defensive runtime guard
                logger.warning("Failed to refresh profile for %s: %s", doc_id, exc)
        return refreshed

    @staticmethod
    def _score_profile(
        *,
        query: str,
        summary: str,
        keywords: Sequence[str],
        outline: Sequence[str],
    ) -> float:
        query_tokens = [token for token in _tokenize(query) if _is_keyword_token(token)]
        if not query_tokens:
            return 0.0

        query_set = set(query_tokens)
        summary_tokens = set(_tokenize(summary))
        keyword_tokens = set(token for token in keywords if isinstance(token, str))
        outline_tokens = set(_tokenize(" ".join(outline)))

        keyword_overlap = len(query_set.intersection(keyword_tokens))
        summary_overlap = len(query_set.intersection(summary_tokens))
        outline_overlap = len(query_set.intersection(outline_tokens))

        norm = max(len(query_set), 1)
        lexical = (0.55 * (keyword_overlap / norm)) + (0.3 * (summary_overlap / norm))
        structural = 0.15 * (outline_overlap / norm)
        return round(lexical + structural, 6)

    @staticmethod
    def _decode_json_array(value: Any) -> List[str]:
        if isinstance(value, list):
            return [str(item).strip() for item in value if str(item).strip()]
        if isinstance(value, str):
            try:
                loaded = json.loads(value)
            except Exception:
                return []
            if isinstance(loaded, list):
                return [str(item).strip() for item in loaded if str(item).strip()]
        return []

    def get_ranked_profiles(
        self,
        query: str,
        *,
        top_k: int = 3,
        candidate_doc_ids: Optional[Sequence[str]] = None,
        auto_refresh_stale: bool = True,
    ) -> List[Dict[str, Any]]:
        self._ensure_table()
        query_text = str(query or "").strip()
        if not query_text:
            return []

        doc_ids = [
            str(doc_id).strip()
            for doc_id in (candidate_doc_ids or [])
            if str(doc_id).strip()
        ]
        if auto_refresh_stale and doc_ids:
            self.refresh_profiles_if_stale(doc_ids)

        conn = self.vectorstore.get_connection()
        cur = conn.cursor()
        try:
            if doc_ids:
                cur.execute(
                    """
                    SELECT doc_id, filename, summary, outline, keywords, chunk_count, updated_at
                    FROM document_profiles
                    WHERE doc_id = ANY(%s)
                    """,
                    (doc_ids,),
                )
            else:
                cur.execute(
                    """
                    SELECT doc_id, filename, summary, outline, keywords, chunk_count, updated_at
                    FROM document_profiles
                    ORDER BY updated_at DESC
                    LIMIT 200
                    """
                )
            rows = cur.fetchall()
        finally:
            cur.close()
            conn.close()

        ranked: List[Dict[str, Any]] = []
        for row in rows:
            doc_id = str(row[0] or "").strip()
            filename = str(row[1] or "").strip()
            summary = str(row[2] or "").strip()
            outline = self._decode_json_array(row[3])
            keywords = self._decode_json_array(row[4])
            score = self._score_profile(
                query=query_text,
                summary=summary,
                keywords=keywords,
                outline=outline,
            )
            ranked.append(
                {
                    "doc_id": doc_id,
                    "filename": filename,
                    "summary": summary,
                    "outline": outline[:6],
                    "keywords": keywords[:12],
                    "chunk_count": int(row[5] or 0),
                    "profile_score": score,
                }
            )

        if not ranked:
            return []

        ranked.sort(
            key=lambda item: (
                float(item.get("profile_score") or 0.0),
                int(item.get("chunk_count") or 0),
            ),
            reverse=True,
        )
        selected = ranked[: max(int(top_k), 1)]
        if all(float(item.get("profile_score") or 0.0) <= 0.0 for item in selected):
            return ranked[: max(int(top_k), 1)]
        return selected

    @staticmethod
    def to_prompt_snippets(
        profiles: Iterable[Dict[str, Any]],
        *,
        max_items: int = 3,
    ) -> List[str]:
        lines: List[str] = []
        for index, item in enumerate(profiles, 1):
            if index > max_items:
                break
            filename = str(item.get("filename") or item.get("doc_id") or "unknown")
            summary = str(item.get("summary") or "").strip()
            keywords = item.get("keywords") or []
            keyword_text = ", ".join(str(token) for token in keywords[:5] if str(token).strip())
            snippet = f"[DocProfile {index}] source={filename}\nsummary={summary[:280]}"
            if keyword_text:
                snippet += f"\nkeywords={keyword_text}"
            lines.append(snippet)
        return lines
