from __future__ import annotations

from backend.services.retrieval.document_profile import DocumentProfileService


def test_extract_keywords_returns_ranked_domain_terms():
    chunks = [
        "Concrete curing checklist requires moisture control and inspection logs.",
        "Inspection checklist items include curing duration, temperature, and moisture.",
    ]

    keywords = DocumentProfileService._extract_keywords(chunks, limit=6)

    assert keywords
    assert "checklist" in keywords
    assert "inspection" in keywords


def test_extract_summary_prefers_keyword_dense_sentences():
    chunks = [
        (
            "Concrete curing shall maintain moisture for seven days. "
            "Inspection records must be signed weekly."
        ),
        "Quality checklist must include temperature and moisture observations.",
    ]
    keywords = ["curing", "inspection", "checklist", "moisture"]

    summary = DocumentProfileService._extract_summary(chunks, keywords)

    assert "curing" in summary.lower()
    assert ("inspection" in summary.lower()) or ("checklist" in summary.lower())


def test_score_profile_increases_with_query_overlap():
    high = DocumentProfileService._score_profile(
        query="concrete curing inspection checklist",
        summary="Inspection checklist for concrete curing controls.",
        keywords=["concrete", "curing", "inspection", "checklist"],
        outline=["Quality controls", "Inspection checklist"],
    )
    low = DocumentProfileService._score_profile(
        query="concrete curing inspection checklist",
        summary="General policy introduction and project overview.",
        keywords=["overview", "project"],
        outline=["Introduction"],
    )

    assert high > low


def test_to_prompt_snippets_formats_profile_context():
    profiles = [
        {
            "doc_id": "doc-1",
            "filename": "spec-a.pdf",
            "summary": "Summary A",
            "keywords": ["curing", "inspection"],
        },
        {
            "doc_id": "doc-2",
            "filename": "spec-b.pdf",
            "summary": "Summary B",
            "keywords": ["safety", "ppe"],
        },
    ]

    snippets = DocumentProfileService.to_prompt_snippets(profiles, max_items=1)

    assert len(snippets) == 1
    assert "DocProfile 1" in snippets[0]
    assert "spec-a.pdf" in snippets[0]
