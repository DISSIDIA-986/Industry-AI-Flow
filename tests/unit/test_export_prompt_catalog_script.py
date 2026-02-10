from __future__ import annotations

import json
from datetime import datetime, timezone
from uuid import uuid4

from scripts.migration import export_prompt_catalog as exporter


def test_export_prompt_catalog_script_writes_yaml_files(tmp_path, monkeypatch):
    prompt_id = uuid4()

    async def _fake_fetch_prompts(*, include_inactive: bool, include_non_latest: bool):
        assert include_inactive is False
        assert include_non_latest is False
        return [
            {
                "id": prompt_id,
                "name": "construction_rag_grounded_qa",
                "category": "rag",
                "subcategory": None,
                "version": "1.0.0",
                "is_active": True,
                "is_latest": True,
                "priority": 10,
                "performance_score": 0.91,
                "usage_count": 12,
                "success_count": 11,
                "created_by": "qa",
                "updated_by": "qa",
                "created_at": datetime(2026, 2, 10, tzinfo=timezone.utc),
                "updated_at": datetime(2026, 2, 10, tzinfo=timezone.utc),
                "tags": ["construction", "safety"],
                "variables": [{"name": "query", "type": "string"}],
                "metadata": {"owner": "team-ai"},
                "content": "answer: {{ query }}",
            }
        ]

    monkeypatch.setattr(exporter, "_fetch_prompts", _fake_fetch_prompts)

    code = exporter.main(
        [
            "--output-dir",
            str(tmp_path),
            "--clean",
            "--pretty",
        ]
    )
    assert code == 0

    index_path = tmp_path / "_index.yaml"
    assert index_path.exists()
    index_text = index_path.read_text(encoding="utf-8")
    assert "total_prompts" in index_text
    assert "construction_rag_grounded_qa" in index_text

    exported_files = [p for p in tmp_path.glob("*.yaml") if p.name != "_index.yaml"]
    assert len(exported_files) == 1
    body = exported_files[0].read_text(encoding="utf-8")
    assert "construction_rag_grounded_qa" in body
    assert "answer: {{ query }}" in body


def test_export_prompt_catalog_script_prints_json(monkeypatch, capsys, tmp_path):
    async def _fake_fetch_prompts(*, include_inactive: bool, include_non_latest: bool):
        return []

    monkeypatch.setattr(exporter, "_fetch_prompts", _fake_fetch_prompts)

    code = exporter.main(["--output-dir", str(tmp_path)])
    payload = json.loads(capsys.readouterr().out)

    assert code == 0
    assert payload["total_prompts"] == 0
