#!/usr/bin/env python3
"""Build KPI gate payload JSON from runtime/evaluation artifacts."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.services.workflows.kpi_payload_builder import (
    KPIPayloadBuildConfig,
    build_kpi_payload,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build workflow KPI gate payload")
    parser.add_argument(
        "--audit-log",
        default="logs/audit.log",
        help="Path to audit log JSONL (default: logs/audit.log)",
    )
    parser.add_argument(
        "--evaluation-json",
        help="Optional path to faithfulness/relevancy metrics JSON",
    )
    parser.add_argument(
        "--ab-json",
        help="Optional path to prompt A/B metrics JSON",
    )
    parser.add_argument(
        "--tenant-id",
        default="public",
        help="Tenant id filter (default: public)",
    )
    parser.add_argument(
        "--monthly-cost-cad",
        type=float,
        help="Optional explicit monthly CAD cost; overrides DB lookup",
    )
    parser.add_argument(
        "--cad-per-usd",
        type=float,
        default=1.35,
        help="CAD conversion rate for DB-derived monthly cost (default: 1.35)",
    )
    parser.add_argument(
        "--output",
        help="Optional output JSON file path; prints to stdout when omitted",
    )
    parser.add_argument(
        "--pretty",
        action="store_true",
        help="Pretty-print JSON output",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    payload = build_kpi_payload(
        KPIPayloadBuildConfig(
            audit_log_path=args.audit_log,
            evaluation_json_path=args.evaluation_json,
            ab_json_path=args.ab_json,
            tenant_id=args.tenant_id,
            monthly_cost_cad=args.monthly_cost_cad,
            cad_per_usd=args.cad_per_usd,
        )
    )

    raw = json.dumps(payload, ensure_ascii=False, indent=2 if args.pretty else None)
    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(raw + "\n", encoding="utf-8")
    else:
        print(raw)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
