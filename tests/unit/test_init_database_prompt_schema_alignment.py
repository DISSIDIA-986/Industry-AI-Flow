from __future__ import annotations

from typing import Any

import backend.init_database as init_db


class _FakeCursor:
    def __init__(self):
        self.queries: list[str] = []

    def execute(self, query: str, params: Any = None):
        self.queries.append(query)

    def fetchall(self):
        return [("prompts",), ("prompt_versions",), ("prompt_tags",)]

    def close(self):
        return None


class _FakeConn:
    def __init__(self):
        self.cursor_obj = _FakeCursor()

    def cursor(self):
        return self.cursor_obj

    def commit(self):
        return None

    def rollback(self):
        return None

    def close(self):
        return None


def test_init_database_contains_prompt_schema_alignment_sql(monkeypatch):
    fake_conn = _FakeConn()
    monkeypatch.setattr(init_db, "connect_db", lambda *_args, **_kwargs: fake_conn)

    init_db.init_database()

    sql = "\n".join(fake_conn.cursor_obj.queries)

    assert "CREATE TABLE IF NOT EXISTS prompt_versions" in sql
    assert "performance_metrics JSONB" in sql
    assert "usage_stats JSONB" in sql
    assert "ALTER TABLE prompt_versions" in sql
    assert "ADD COLUMN IF NOT EXISTS performance_metrics" in sql
    assert "ADD COLUMN IF NOT EXISTS usage_stats" in sql
    assert "CREATE TABLE IF NOT EXISTS prompt_tags" in sql
    assert "color VARCHAR(7)" in sql
    assert "ALTER TABLE prompt_tags" in sql
    assert "ADD COLUMN IF NOT EXISTS color" in sql
    assert "CREATE TABLE IF NOT EXISTS prompt_experiments" in sql
    assert "winner_prompt_id UUID REFERENCES prompts(id)" in sql
    assert "confidence_level NUMERIC(4, 3)" in sql
    assert "sample_size BIGINT DEFAULT 0" in sql
    assert "ended_at TIMESTAMP" in sql
    assert "ALTER TABLE prompt_experiments" in sql
    assert "ADD COLUMN IF NOT EXISTS winner_prompt_id" in sql
    assert "ADD COLUMN IF NOT EXISTS confidence_level" in sql
    assert "ADD COLUMN IF NOT EXISTS sample_size" in sql
    assert "ADD COLUMN IF NOT EXISTS ended_at" in sql
    assert "CREATE TABLE IF NOT EXISTS prompt_usage_logs" in sql
    assert "prompt_id UUID REFERENCES prompts(id) ON DELETE SET NULL" in sql
    assert "ALTER TABLE prompt_usage_logs" in sql
    assert "ALTER COLUMN prompt_id DROP NOT NULL" in sql
    assert "fk_prompt_usage_prompt_id" in sql
