#!/usr/bin/env python3
"""Run KPI quality gate evaluation from JSON payload."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.services.workflows.kpi_gate import (
    evaluate_kpi_gate,
    payload_from_dict,
    thresholds_from_dict,
)


def _load_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise ValueError(f"JSON payload must be an object: {path}")
    return data


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run workflow KPI gate checks")
    parser.add_argument(
        "--input",
        required=True,
        help="Path to KPI input JSON",
    )
    parser.add_argument(
        "--thresholds",
        required=False,
        help="Optional path to KPI threshold JSON",
    )
    parser.add_argument(
        "--pretty",
        action="store_true",
        help="Pretty-print JSON output",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    payload = payload_from_dict(_load_json(Path(args.input)))

    thresholds = None
    if args.thresholds:
        thresholds = thresholds_from_dict(_load_json(Path(args.thresholds)))

    result = evaluate_kpi_gate(payload=payload, thresholds=thresholds)
    output = result.to_dict()
    if args.pretty:
        print(json.dumps(output, ensure_ascii=False, indent=2))
    else:
        print(json.dumps(output, ensure_ascii=False))

    return 0 if result.passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
