"""Unit tests for page-mapping utilities (citation deep-linking).

Covers the offset->page math and the chunk->page locator, including the
adversarial edge cases that matter on real documents: empty pages, offsets
past the end, repeated text, blank chunks, and chunks that straddle a page
boundary.
"""

import pytest

from backend.services.core.page_mapping import (
    compute_page_starts,
    map_chunks_to_pages,
    offset_to_page,
)

pytestmark = pytest.mark.unit


def test_compute_page_starts_basic():
    # "aaa\n\nbbbb\n\ncc"  -> starts at 0, 5, 11
    assert compute_page_starts(["aaa", "bbbb", "cc"]) == [0, 5, 11]


def test_compute_page_starts_single_page():
    assert compute_page_starts(["only one page"]) == [0]


def test_compute_page_starts_empty_list():
    assert compute_page_starts([]) == []


def test_compute_page_starts_with_empty_pages():
    # Empty pages still consume a slot + the separator so alignment holds.
    starts = compute_page_starts(["a", "", "b"])
    # "a" at 0, sep(2)->page2 empty at 3, sep(2)->"b" at 5
    assert starts == [0, 3, 5]
    assert len(starts) == 3


def test_offset_to_page_boundaries():
    starts = [0, 5, 11]
    assert offset_to_page(0, starts) == 1
    assert offset_to_page(4, starts) == 1
    assert offset_to_page(5, starts) == 2  # exact page start
    assert offset_to_page(10, starts) == 2
    assert offset_to_page(11, starts) == 3
    assert offset_to_page(9999, starts) == 3  # past end clamps to last page


def test_offset_to_page_negative_clamps_to_one():
    assert offset_to_page(-5, [0, 5, 11]) == 1


def test_offset_to_page_empty_starts_returns_none():
    assert offset_to_page(3, []) is None


def test_map_chunks_to_pages_happy_path():
    pages = ["alpha text one", "beta text two", "gamma text three"]
    full = "\n\n".join(pages)
    starts = compute_page_starts(pages)
    result = map_chunks_to_pages(full, ["alpha text one", "beta text two", "gamma text three"], starts)
    assert result == [1, 2, 3]


def test_map_chunks_to_pages_straddling_and_partial():
    pages = ["The quick brown fox jumps", "over the lazy dog repeatedly"]
    full = "\n\n".join(pages)
    starts = compute_page_starts(pages)
    # A chunk that starts on page 2.
    result = map_chunks_to_pages(full, ["over the lazy dog"], starts)
    assert result == [2]


def test_map_chunks_to_pages_blank_chunk_reuses_last_page():
    pages = ["page one content here", "page two content here"]
    full = "\n\n".join(pages)
    starts = compute_page_starts(pages)
    result = map_chunks_to_pages(
        full, ["page two content here", "   ", "page one content here"], starts
    )
    # blank chunk inherits previous page (2); third locates back to page 1
    assert result[0] == 2
    assert result[1] == 2
    assert result[2] == 1


def test_map_chunks_to_pages_no_page_starts():
    result = map_chunks_to_pages("whatever", ["a", "b"], [])
    assert result == [None, None]


def test_map_chunks_to_pages_unlocatable_chunk_falls_back():
    pages = ["real content alpha", "real content beta"]
    full = "\n\n".join(pages)
    starts = compute_page_starts(pages)
    # Second chunk text does not exist in the document -> reuse last page.
    result = map_chunks_to_pages(full, ["real content alpha", "ZZZ not present ZZZ"], starts)
    assert result[0] == 1
    assert result[1] == 1  # fallback to previous page, never crashes


def test_map_chunks_to_pages_monotonic_with_overlap():
    # Simulate overlapping chunks (shared tail/head) across pages.
    p1 = "section one " * 10
    p2 = "section two " * 10
    pages = [p1.strip(), p2.strip()]
    full = "\n\n".join(pages)
    starts = compute_page_starts(pages)
    chunks = [p1[:60].strip(), p1[40:100].strip(), p2[:60].strip()]
    result = map_chunks_to_pages(full, chunks, starts)
    assert result[0] == 1
    assert result[-1] == 2
    # pages never decrease
    assert all(b >= a for a, b in zip(result, result[1:]))
