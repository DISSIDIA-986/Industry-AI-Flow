#!/usr/bin/env python3
"""Run prompt schema migration rehearsal checks without mutating a real database."""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import List, Sequence
from unittest.mock import patch

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import backend.init_database as init_db

REQUIRED_SQL_TOKENS = (
    "CREATE TABLE IF NOT EXISTS prompt_usage_logs",
    "CREATE TABLE IF NOT EXISTS prompt_tags",
    "CREATE TABLE IF NOT EXISTS prompt_experiments",
    "ALTER TABLE prompt_tags",
    "ADD COLUMN IF NOT EXISTS color",
    "ALTER TABLE prompt_experiments",
    "ADD COLUMN IF NOT EXISTS winner_prompt_id",
    "ADD COLUMN IF NOT EXISTS confidence_level",
    "ADD COLUMN IF NOT EXISTS sample_size",
    "ADD COLUMN IF NOT EXISTS ended_at",
    "ALTER TABLE prompt_usage_logs",
    "ALTER COLUMN prompt_id DROP NOT NULL",
    "fk_prompt_usage_prompt_id",
    "INSERT INTO schema_migrations (version, description)",
    "2026_02_10_prompt_schema_unify_v1",
)

FORBIDDEN_SQL_TOKENS = (
    "DROP TABLE ",
    "TRUNCATE TABLE ",
)


@dataclass(frozen=True)
class RehearsalCheck:
    name: str
    passed: bool
    expected: str
    actual: str
    message: str


@dataclass
class RehearsalScenarioResult:
    scenario: str
    passed: bool
    checks: List[RehearsalCheck] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "scenario": self.scenario,
            "passed": self.passed,
            "failed_count": len([item for item in self.checks if not item.passed]),
            "checks": [asdict(item) for item in self.checks],
        }


@dataclass
class RehearsalResult:
    passed: bool
    scenarios: List[RehearsalScenarioResult]

    def to_dict(self) -> dict:
        return {
            "passed": self.passed,
            "failed_scenarios": len([item for item in self.scenarios if not item.passed]),
            "scenarios": [item.to_dict() for item in self.scenarios],
        }


class _FakeCursor:
    def __init__(self, table_names: Sequence[str]):
        self.queries: List[str] = []
        self.params: List[object] = []
        self._table_names = list(table_names)

    def execute(self, query: str, params=None):
        self.queries.append(query)
        if params is not None:
            self.params.append(params)

    def fetchall(self):
        return [(name,) for name in self._table_names]

    def close(self):
        return None


class _FakeConn:
    def __init__(self, table_names: Sequence[str]):
        self.cursor_obj = _FakeCursor(table_names)
        self.commit_count = 0
        self.rollback_count = 0

    def cursor(self):
        return self.cursor_obj

    def commit(self):
        self.commit_count += 1
        return None

    def rollback(self):
        self.rollback_count += 1
        return None

    def close(self):
        return None


def _run_init_database(table_names: Sequence[str]) -> _FakeConn:
    conn = _FakeConn(table_names)
    if hasattr(init_db, "connect_db"):
        with patch.object(init_db, "connect_db", return_value=conn):
            init_db.init_database()
    else:
        with patch.object(init_db.psycopg2, "connect", return_value=conn):
            init_db.init_database()
    return conn


def _evaluate_scenario(name: str, table_names: Sequence[str]) -> RehearsalScenarioResult:
    checks: List[RehearsalCheck] = []
    conn = _run_init_database(table_names)
    sql = "\n".join(conn.cursor_obj.queries)
    params_dump = "\n".join(str(item) for item in conn.cursor_obj.params)
    sql_upper = sql.upper()

    checks.append(
        RehearsalCheck(
            name="transaction_commit",
            passed=conn.commit_count > 0,
            expected="commit_count > 0",
            actual=str(conn.commit_count),
            message="init_database should complete and commit at least once.",
        )
    )
    checks.append(
        RehearsalCheck(
            name="transaction_rollback",
            passed=conn.rollback_count == 0,
            expected="rollback_count == 0",
            actual=str(conn.rollback_count),
            message="schema rehearsal should not trigger rollback on nominal scenarios.",
        )
    )

    for token in REQUIRED_SQL_TOKENS:
        present = token in sql or token in params_dump
        checks.append(
            RehearsalCheck(
                name=f"required_sql:{token}",
                passed=present,
                expected="present",
                actual="present" if present else "missing",
                message="required schema alignment SQL token must exist.",
            )
        )

    for token in FORBIDDEN_SQL_TOKENS:
        checks.append(
            RehearsalCheck(
                name=f"forbidden_sql:{token.strip()}",
                passed=token.upper() not in sql_upper,
                expected="absent",
                actual="present" if token.upper() in sql_upper else "absent",
                message="rehearsal forbids destructive prompt schema operations.",
            )
        )

    return RehearsalScenarioResult(
        scenario=name,
        passed=all(item.passed for item in checks),
        checks=checks,
    )


def run_rehearsal(*, scenario: str) -> RehearsalResult:
    selected = ["empty", "legacy"] if scenario == "both" else [scenario]
    scenario_tables = {
        "empty": [],
        "legacy": [
            "prompts",
            "prompt_versions",
            "prompt_usage_logs",
            "prompt_experiments",
            "prompt_tags",
            "schema_migrations",
        ],
    }

    results = [
        _evaluate_scenario(name=item, table_names=scenario_tables[item])
        for item in selected
    ]
    return RehearsalResult(
        passed=all(item.passed for item in results),
        scenarios=results,
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run prompt schema migration rehearsal")
    parser.add_argument(
        "--scenario",
        choices=("empty", "legacy", "both"),
        default="both",
        help="Rehearsal scenario selector (default: both)",
    )
    parser.add_argument(
        "--pretty",
        action="store_true",
        help="Pretty-print JSON output",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    result = run_rehearsal(scenario=args.scenario)
    payload = result.to_dict()
    if args.pretty:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(json.dumps(payload, ensure_ascii=False))
    return 0 if result.passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
