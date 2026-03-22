#!/usr/bin/env python3
"""
Batch generate AI summaries for all processed documents.

Reads extracted text from document_chunks, generates a summary via LLM,
and stores it in document_profiles.summary.

Usage:
    python scripts/generate_document_summaries.py [--force]

    --force: Regenerate summaries even if they already exist
"""

import sys
import os
import json
import argparse
import logging
import time

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.config import settings
from backend.services.database.driver_compat import connect as connect_db
from backend.services.database.driver_compat import fetchall_dicts
from backend.services.llm_integration.llm_client import LLMClientFactory

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)

SUMMARY_PROMPT = """You are an AI assistant that summarizes construction documents.
Given the following extracted text from a document, provide:

1. A 2-3 sentence overview of what this document covers
2. 4-6 key findings or requirements as bullet points (format as JSON array of objects with "title" and "detail" keys)
3. Document classification (type, jurisdiction if applicable)

Respond in this exact JSON format:
{{
  "summary": "2-3 sentence overview...",
  "key_findings": [
    {{"title": "Finding Title", "detail": "Brief description"}},
    ...
  ],
  "classification": {{
    "type": "e.g. Building Code, Safety Regulation, etc.",
    "jurisdiction": "e.g. Canada, Ontario, etc."
  }}
}}

Document text (first 4000 characters):
---
{text}
---

Respond ONLY with the JSON object, no other text."""


def get_documents_needing_summaries(conn, force: bool = False):
    """Get documents that have chunks but no/empty summary in document_profiles."""
    cur = conn.cursor()
    try:
        if force:
            cur.execute(
                """
                SELECT dp.doc_id, dp.filename, dp.chunk_count
                FROM document_profiles dp
                WHERE dp.chunk_count > 0
                ORDER BY dp.updated_at DESC
                """
            )
        else:
            cur.execute(
                """
                SELECT dp.doc_id, dp.filename, dp.chunk_count
                FROM document_profiles dp
                WHERE dp.chunk_count > 0
                  AND (dp.summary IS NULL OR dp.summary = '' OR dp.summary = 'Auto-generated profile')
                ORDER BY dp.updated_at DESC
                """
            )
        return fetchall_dicts(cur)
    finally:
        cur.close()


def get_document_text(conn, doc_id: str, max_chars: int = 4000) -> str:
    """Get concatenated chunk text for a document."""
    cur = conn.cursor()
    try:
        cur.execute(
            """
            SELECT content FROM document_chunks
            WHERE doc_id = %s
            ORDER BY chunk_id ASC
            """,
            (doc_id,),
        )
        rows = fetchall_dicts(cur)
        text = "\n".join(str(row.get("content", "")) for row in rows)
        return text[:max_chars]
    finally:
        cur.close()


def generate_summary(llm_client, text: str) -> dict:
    """Generate summary using LLM."""
    prompt = SUMMARY_PROMPT.format(text=text)
    response = llm_client.generate(prompt, temperature=0.3, max_tokens=1024)

    # Parse JSON response
    response = response.strip()
    # Handle markdown code blocks
    if response.startswith("```"):
        response = response.split("\n", 1)[1] if "\n" in response else response
        if response.endswith("```"):
            response = response[:-3]
        response = response.strip()
        if response.startswith("json"):
            response = response[4:].strip()

    try:
        return json.loads(response)
    except json.JSONDecodeError:
        logger.warning("Failed to parse LLM response as JSON, using raw text")
        return {"summary": response[:500], "key_findings": [], "classification": {}}


def store_summary(conn, doc_id: str, summary_data: dict):
    """Store summary in document_profiles table."""
    cur = conn.cursor()
    try:
        summary_text = summary_data.get("summary", "")
        outline = json.dumps(summary_data.get("key_findings", []))
        keywords_data = summary_data.get("classification", {})
        keywords = json.dumps(
            [keywords_data] if isinstance(keywords_data, dict) else keywords_data
        )

        cur.execute(
            """
            UPDATE document_profiles
            SET summary = %s, outline = %s::jsonb, keywords = %s::jsonb,
                updated_at = CURRENT_TIMESTAMP
            WHERE doc_id = %s
            """,
            (summary_text, outline, keywords, doc_id),
        )
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        cur.close()


def main():
    parser = argparse.ArgumentParser(description="Generate AI summaries for documents")
    parser.add_argument(
        "--force", action="store_true", help="Regenerate even if summary exists"
    )
    args = parser.parse_args()

    logger.info("Connecting to database...")
    conn = connect_db(settings.database_url)

    docs = get_documents_needing_summaries(conn, force=args.force)
    logger.info("Found %d documents needing summaries", len(docs))

    if not docs:
        logger.info("All documents already have summaries. Use --force to regenerate.")
        conn.close()
        return

    logger.info("Initializing LLM client (backend: %s)...", settings.llm_backend)
    llm_client = LLMClientFactory.create_client()

    success_count = 0
    fail_count = 0

    for i, doc in enumerate(docs):
        doc_id = str(doc.get("doc_id", ""))
        filename = str(doc.get("filename", "unknown"))
        chunk_count = int(doc.get("chunk_count", 0))

        logger.info(
            "[%d/%d] Processing: %s (%d chunks)",
            i + 1,
            len(docs),
            filename,
            chunk_count,
        )

        try:
            text = get_document_text(conn, doc_id)
            if not text.strip():
                logger.warning("  Skipped: no text content")
                continue

            start = time.time()
            summary_data = generate_summary(llm_client, text)
            elapsed = time.time() - start

            store_summary(conn, doc_id, summary_data)
            logger.info(
                "  Done in %.1fs: %s",
                elapsed,
                (summary_data.get("summary", "")[:80] + "..."),
            )
            success_count += 1

        except Exception as e:
            logger.error("  Failed: %s", e)
            fail_count += 1
            continue

    conn.close()
    logger.info(
        "Complete: %d succeeded, %d failed out of %d total",
        success_count,
        fail_count,
        len(docs),
    )


if __name__ == "__main__":
    main()
