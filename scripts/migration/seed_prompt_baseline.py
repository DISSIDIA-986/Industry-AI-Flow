#!/usr/bin/env python3
"""Seed and verify workflow prompt baseline required by release gates."""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.config import get_database_pool
from backend.services.database.pool import close_database_pool


@dataclass(frozen=True)
class PromptSeed:
    name: str
    category: str
    subcategory: str | None
    version: str
    content: str
    variables: list[dict[str, Any]]
    metadata: dict[str, Any]
    priority: int = 100
    created_by: str = "seed_prompt_baseline"


BASELINE_PROMPTS: tuple[PromptSeed, ...] = (
    PromptSeed(
        name="construction_rag_grounded_qa",
        category="rag",
        subcategory="construction_knowledge",
        version="1.0.0",
        content=(
            "You are a construction-domain assistant.\n"
            "User Query: {{ query }}\n"
            "Retrieved Context: {{ context }}\n"
            "Intent: {{ intent }}\n"
            "Answer with grounded facts and clearly indicate uncertainty."
        ),
        variables=[
            {"name": "query", "type": "string", "required": True},
            {"name": "context", "type": "string", "required": False},
            {"name": "intent", "type": "string", "required": False},
        ],
        metadata={"owner": "workflow", "purpose": "construction_rag"},
    ),
    PromptSeed(
        name="drawing_ocr_structured_parse",
        category="ocr",
        subcategory="drawing_parse",
        version="1.0.0",
        content=(
            "You are an OCR post-processor for construction drawings.\n"
            "User Query: {{ query }}\n"
            "OCR Context: {{ context }}\n"
            "Return structured key fields, warnings, and missing information."
        ),
        variables=[
            {"name": "query", "type": "string", "required": True},
            {"name": "context", "type": "string", "required": False},
        ],
        metadata={"owner": "workflow", "purpose": "drawing_ocr"},
    ),
    PromptSeed(
        name="code_exec_data_analysis_explainer",
        category="analysis",
        subcategory="data_analysis",
        version="1.0.0",
        content=(
            "You are a data-analysis assistant for construction datasets.\n"
            "User Query: {{ query }}\n"
            "Data/Context: {{ context }}\n"
            "Produce concise analysis, key metrics, and recommended next checks."
        ),
        variables=[
            {"name": "query", "type": "string", "required": True},
            {"name": "context", "type": "string", "required": False},
        ],
        metadata={"owner": "workflow", "purpose": "data_analysis"},
    ),
    PromptSeed(
        name="intent_classification",
        category="Intent",
        subcategory="classification",
        version="1.0.0",
        content=(
            "Classify the user request into one intent.\n"
            "Allowed intents: knowledge_retrieval, data_analysis, "
            "document_processing, code_execution, cost_estimation, unclear_intent.\n"
            "User Query: {{ user_query }}\n"
            "Session Topic: {{ session_topic }}\n"
            "Recent Intents: {{ recent_intents }}\n"
            "Uploaded Files: {{ uploaded_files }}\n"
            "User Preferences: {{ user_preferences }}\n"
            "Return JSON with keys: intent, confidence, reasoning."
        ),
        variables=[
            {"name": "user_query", "type": "string", "required": True},
            {"name": "session_topic", "type": "string", "required": False},
            {"name": "recent_intents", "type": "string", "required": False},
            {"name": "uploaded_files", "type": "string", "required": False},
            {"name": "user_preferences", "type": "json", "required": False},
        ],
        metadata={"owner": "intent", "purpose": "classification"},
    ),
    PromptSeed(
        name="intent_clarification",
        category="Intent",
        subcategory="clarification",
        version="1.0.0",
        content=(
            "Generate a clarification response when intent confidence is low.\n"
            "User Query: {{ user_query }}\n"
            "Possible Intents: {{ possible_intents }}\n"
            "Classification Result: {{ classification_result }}\n"
            "Language: {{ language }}\n"
            "Return JSON with keys: clarification_needed, clarification_message, "
            "suggested_options."
        ),
        variables=[
            {"name": "user_query", "type": "string", "required": True},
            {"name": "possible_intents", "type": "json", "required": False},
            {"name": "classification_result", "type": "string", "required": False},
            {"name": "language", "type": "string", "required": False},
        ],
        metadata={"owner": "intent", "purpose": "clarification"},
    ),
)

REQUIRED_TEMPLATES: tuple[tuple[str, str], ...] = tuple(
    (prompt.name, prompt.category) for prompt in BASELINE_PROMPTS
)


async def _upsert_prompt(conn: Any, prompt: PromptSeed) -> str:
    row = await conn.fetchrow(
        """
        INSERT INTO prompts (
            name,
            category,
            subcategory,
            version,
            content,
            variables,
            metadata,
            is_active,
            is_latest,
            priority,
            created_by,
            updated_by
        )
        VALUES (
            $1, $2, $3, $4, $5, $6::jsonb, $7::jsonb,
            true, true, $8, $9, $9
        )
        ON CONFLICT (name, category, version)
        DO UPDATE SET
            subcategory = EXCLUDED.subcategory,
            content = EXCLUDED.content,
            variables = EXCLUDED.variables,
            metadata = EXCLUDED.metadata,
            is_active = true,
            priority = EXCLUDED.priority,
            updated_by = EXCLUDED.updated_by,
            updated_at = NOW()
        RETURNING id
        """,
        prompt.name,
        prompt.category,
        prompt.subcategory,
        prompt.version,
        prompt.content,
        json.dumps(prompt.variables, ensure_ascii=False),
        json.dumps(prompt.metadata, ensure_ascii=False),
        prompt.priority,
        prompt.created_by,
    )

    prompt_id = str(row["id"])
    await conn.execute(
        """
        UPDATE prompts
        SET is_latest = CASE WHEN id = $3 THEN true ELSE false END
        WHERE name = $1 AND category = $2
        """,
        prompt.name,
        prompt.category,
        row["id"],
    )
    return prompt_id


async def seed_prompts(dry_run: bool = False) -> dict[str, Any]:
    pool = await get_database_pool()
    seeded: list[dict[str, str]] = []

    async with pool.acquire() as conn:
        if dry_run:
            return {
                "dry_run": True,
                "planned": [
                    {"name": p.name, "category": p.category, "version": p.version}
                    for p in BASELINE_PROMPTS
                ],
            }
        async with conn.transaction():
            for prompt in BASELINE_PROMPTS:
                prompt_id = await _upsert_prompt(conn, prompt)
                seeded.append(
                    {
                        "id": prompt_id,
                        "name": prompt.name,
                        "category": prompt.category,
                        "version": prompt.version,
                    }
                )

    return {"dry_run": False, "seeded": seeded, "total_seeded": len(seeded)}


async def verify_prompts() -> dict[str, Any]:
    pool = await get_database_pool()
    missing: list[dict[str, str]] = []
    inactive: list[dict[str, str]] = []
    not_latest: list[dict[str, str]] = []

    async with pool.acquire() as conn:
        for name, category in REQUIRED_TEMPLATES:
            row = await conn.fetchrow(
                """
                SELECT id, is_active, is_latest
                FROM prompts
                WHERE name = $1 AND category = $2
                ORDER BY is_latest DESC, created_at DESC
                LIMIT 1
                """,
                name,
                category,
            )
            if row is None:
                missing.append({"name": name, "category": category})
                continue
            if not bool(row["is_active"]):
                inactive.append({"name": name, "category": category})
            if not bool(row["is_latest"]):
                not_latest.append({"name": name, "category": category})

    ok = not missing and not inactive and not not_latest
    return {
        "ok": ok,
        "required_total": len(REQUIRED_TEMPLATES),
        "missing": missing,
        "inactive": inactive,
        "not_latest": not_latest,
    }


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Seed and verify workflow prompt baseline."
    )
    parser.add_argument(
        "--verify-only",
        action="store_true",
        help="Only verify required prompts without writing.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print planned prompt seeds without writing.",
    )
    parser.add_argument(
        "--pretty",
        action="store_true",
        help="Pretty-print JSON output.",
    )
    return parser


async def _run(args: argparse.Namespace) -> int:
    try:
        payload: dict[str, Any] = {}
        if args.verify_only:
            payload["verify"] = await verify_prompts()
        else:
            payload["seed"] = await seed_prompts(dry_run=args.dry_run)
            payload["verify"] = await verify_prompts()

        text = (
            json.dumps(payload, ensure_ascii=False, indent=2)
            if args.pretty
            else json.dumps(payload, ensure_ascii=False)
        )
        print(text)
        return 0 if payload["verify"]["ok"] else 1
    finally:
        await close_database_pool()


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    return asyncio.run(_run(args))


if __name__ == "__main__":
    raise SystemExit(main())
