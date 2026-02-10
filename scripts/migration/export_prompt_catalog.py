#!/usr/bin/env python3
"""Export prompt catalog from DB to read-only YAML mirrors."""

from __future__ import annotations

import argparse
import asyncio
import json
import re
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.config import get_database_pool

try:
    import yaml  # type: ignore[import-untyped]
except Exception:  # pragma: no cover - optional dependency
    yaml = None


@dataclass(frozen=True)
class ExportConfig:
    output_dir: str = "research/prompt-catalog"
    include_inactive: bool = False
    include_non_latest: bool = False
    clean_output: bool = False


def _slug(value: str) -> str:
    text = re.sub(r"[^a-zA-Z0-9._-]+", "_", (value or "").strip())
    return re.sub(r"_+", "_", text).strip("._-").lower() or "prompt"


def _jsonish(value: Any) -> Any:
    if isinstance(value, str):
        stripped = value.strip()
        if stripped.startswith("{") or stripped.startswith("["):
            try:
                return json.loads(stripped)
            except Exception:
                return value
        return value
    return value


def _as_primitive(value: Any) -> Any:
    if hasattr(value, "isoformat"):
        return value.isoformat()
    if isinstance(value, dict):
        return {str(k): _as_primitive(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_as_primitive(v) for v in value]
    return value


def _to_yaml_text(payload: Dict[str, Any]) -> str:
    serializable = _as_primitive(payload)
    if yaml is None:
        return json.dumps(serializable, ensure_ascii=False, indent=2) + "\n"
    return yaml.safe_dump(
        serializable,
        allow_unicode=False,
        sort_keys=False,
        default_flow_style=False,
    )


def _build_catalog_doc(row: Dict[str, Any], exported_at: str) -> Dict[str, Any]:
    return {
        "id": str(row["id"]),
        "name": row["name"],
        "category": row["category"],
        "subcategory": row.get("subcategory"),
        "version": row["version"],
        "is_active": bool(row.get("is_active", False)),
        "is_latest": bool(row.get("is_latest", False)),
        "priority": int(row.get("priority") or 0),
        "performance_score": float(row.get("performance_score") or 0.0),
        "usage_count": int(row.get("usage_count") or 0),
        "success_count": int(row.get("success_count") or 0),
        "created_by": row.get("created_by"),
        "updated_by": row.get("updated_by"),
        "created_at": _as_primitive(row.get("created_at")),
        "updated_at": _as_primitive(row.get("updated_at")),
        "tags": [tag for tag in (row.get("tags") or []) if tag],
        "variables": _jsonish(row.get("variables")) or [],
        "metadata": _jsonish(row.get("metadata")) or {},
        "content": row.get("content") or "",
        "mirror_exported_at": exported_at,
        "mirror_source": "database",
    }


async def _fetch_prompts(
    *,
    include_inactive: bool,
    include_non_latest: bool,
) -> List[Dict[str, Any]]:
    pool = await get_database_pool()
    async with pool.acquire() as conn:
        conditions = ["1=1"]
        if not include_inactive:
            conditions.append("p.is_active = true")
        if not include_non_latest:
            conditions.append("p.is_latest = true")
        where_clause = " AND ".join(conditions)

        query = f"""
            SELECT p.*,
                   COALESCE(
                       array_agg(t.name ORDER BY t.name) FILTER (WHERE t.name IS NOT NULL),
                       ARRAY[]::VARCHAR[]
                   ) AS tags
            FROM prompts p
            LEFT JOIN prompt_tag_relations ptr ON p.id = ptr.prompt_id
            LEFT JOIN prompt_tags t ON ptr.tag_id = t.id
            WHERE {where_clause}
            GROUP BY p.id
            ORDER BY p.category ASC, p.name ASC, p.version DESC
        """
        rows = await conn.fetch(query)

    return [dict(row) for row in rows]


async def export_prompt_catalog(config: ExportConfig) -> Dict[str, Any]:
    output_dir = Path(config.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    if config.clean_output:
        for file_path in output_dir.glob("*.yaml"):
            file_path.unlink()

    prompts = await _fetch_prompts(
        include_inactive=config.include_inactive,
        include_non_latest=config.include_non_latest,
    )
    exported_at = datetime.now(timezone.utc).isoformat()

    entries: List[Dict[str, Any]] = []
    for prompt in prompts:
        doc = _build_catalog_doc(prompt, exported_at=exported_at)
        file_name = (
            f"{_slug(str(doc['category']))}__{_slug(str(doc['name']))}"
            f"__v{_slug(str(doc['version']))}.yaml"
        )
        target = output_dir / file_name
        target.write_text(_to_yaml_text(doc), encoding="utf-8")
        try:
            relative_path = str(target.relative_to(PROJECT_ROOT))
        except ValueError:
            relative_path = str(target)
        entries.append(
            {
                "path": relative_path,
                "id": doc["id"],
                "name": doc["name"],
                "category": doc["category"],
                "version": doc["version"],
            }
        )

    index_payload = {
        "generated_at": exported_at,
        "total_prompts": len(entries),
        "filters": {
            "include_inactive": config.include_inactive,
            "include_non_latest": config.include_non_latest,
        },
        "entries": entries,
    }
    index_path = output_dir / "_index.yaml"
    index_path.write_text(_to_yaml_text(index_payload), encoding="utf-8")

    return {
        "output_dir": str(output_dir),
        "total_prompts": len(entries),
        "index_file": str(index_path),
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Export prompts from DB to research/prompt-catalog YAML mirrors"
    )
    parser.add_argument(
        "--output-dir",
        default="research/prompt-catalog",
        help="Directory for YAML mirror output",
    )
    parser.add_argument(
        "--include-inactive",
        action="store_true",
        help="Include inactive prompts",
    )
    parser.add_argument(
        "--include-non-latest",
        action="store_true",
        help="Include non-latest prompt versions",
    )
    parser.add_argument(
        "--clean",
        action="store_true",
        help="Delete existing *.yaml files in output dir before export",
    )
    parser.add_argument(
        "--pretty",
        action="store_true",
        help="Pretty-print JSON result",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    result = asyncio.run(
        export_prompt_catalog(
            ExportConfig(
                output_dir=args.output_dir,
                include_inactive=args.include_inactive,
                include_non_latest=args.include_non_latest,
                clean_output=args.clean,
            )
        )
    )
    if args.pretty:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
