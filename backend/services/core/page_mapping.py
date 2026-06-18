"""Page mapping utilities.

Maps character offsets within a document's concatenated text back to the
1-based page number they came from.  Used both at ingestion time (to stamp
``document_chunks.page_number``) and by the backfill script that retrofits
page numbers onto already-ingested documents without re-embedding.

The document loader joins per-page text with a fixed separator (``"\n\n"``).
``compute_page_starts`` reproduces the cumulative character offset where each
page begins in that joined string, and ``offset_to_page`` performs a binary
search to resolve any offset to its page.
"""

from __future__ import annotations

import bisect
from typing import List, Optional

# Must match EnhancedDocumentLoader._load_pdf join separator.
PAGE_SEPARATOR = "\n\n"


def compute_page_starts(pages: List[str], separator: str = PAGE_SEPARATOR) -> List[int]:
    """Return the char offset where each page begins in ``separator.join(pages)``.

    ``starts[i]`` is the index of the first character of page ``i`` (0-based
    page index) in the joined text.  Always starts with ``0``.  Pages with empty
    text still occupy a slot so the offsets stay aligned with the page count.
    """
    starts: List[int] = []
    cursor = 0
    sep_len = len(separator)
    for i, page in enumerate(pages):
        if i > 0:
            cursor += sep_len
        starts.append(cursor)
        cursor += len(page)
    return starts


def offset_to_page(offset: int, page_starts: List[int]) -> Optional[int]:
    """Resolve a 0-based char ``offset`` to a 1-based page number.

    Returns ``None`` when there are no page starts.  Offsets before the first
    page clamp to page 1; offsets past the last page clamp to the last page.
    """
    if not page_starts:
        return None
    if offset < 0:
        return 1
    # bisect_right - 1 gives the index of the last page start <= offset.
    idx = bisect.bisect_right(page_starts, offset) - 1
    if idx < 0:
        idx = 0
    if idx >= len(page_starts):
        idx = len(page_starts) - 1
    return idx + 1


def map_chunks_to_pages(
    full_text: str,
    chunk_contents: List[str],
    page_starts: List[int],
) -> List[Optional[int]]:
    """Assign a page number to each chunk by locating it in ``full_text``.

    Robust against the chunker's internal overlap/start_pos drift: each chunk's
    (stripped) content is located via a forward-scanning ``str.find`` from a
    monotonic cursor, so we use the *actual* offset of the chunk text rather
    than trusting reconstructed positions.  Falls back to the previous chunk's
    page when a chunk cannot be located (keeps page numbers monotonic).
    """
    if not page_starts:
        return [None] * len(chunk_contents)

    pages: List[Optional[int]] = []
    cursor = 0
    last_page = 1
    for content in chunk_contents:
        probe = (content or "").strip()
        if not probe:
            pages.append(last_page)
            continue
        # Use a bounded probe — long chunks may have been stripped/normalized,
        # so match on a leading slice that is stable across re-runs.
        needle = probe[:80]
        found = full_text.find(needle, cursor)
        if found == -1:
            # Retry from the start in case ordering drifted; else reuse last page.
            found = full_text.find(needle)
        if found == -1:
            pages.append(last_page)
            continue
        page = offset_to_page(found, page_starts) or last_page
        last_page = page
        pages.append(page)
        cursor = found + 1
    return pages
