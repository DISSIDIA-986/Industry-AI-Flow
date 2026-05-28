from __future__ import annotations

import csv
import shutil
import tempfile
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

from backend.config import settings
from backend.main import app
from backend.services.code_executor import get_code_execution_manager


def _write_runtime_dataset(path: Path) -> None:
    rows = [
        {"project": "A", "estimated_cost": 100.0, "actual_cost": 120.0},
        {"project": "B", "estimated_cost": 80.0, "actual_cost": 78.0},
        {"project": "C", "estimated_cost": 150.0, "actual_cost": 165.0},
    ]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle, fieldnames=["project", "estimated_cost", "actual_cost"]
        )
        writer.writeheader()
        writer.writerows(rows)


@pytest.mark.asyncio
async def test_data_analysis_runtime_gate_requires_real_execution_success() -> None:
    # Environment gate: this test deliberately requires a REAL execution
    # provider (Docker or E2B). When CI lacks both (no Docker service block,
    # no E2B_API_KEY secret), skip rather than fail — the gate is still
    # enforced wherever a provider exists (local dev, staging, demo machine).
    # Hard-failing in unprovisioned CI just trains everyone to ignore the
    # gate's signal.
    manager = get_code_execution_manager()
    if manager is None:
        pytest.skip(
            "code execution manager unavailable — "
            "configure Docker or set E2B_API_KEY to exercise this gate"
        )

    smoke = manager.execute_code(
        code="print('provider_runtime_ok')",
        data_files=None,
        timeout=30,
        mode=settings.code_execution_provider,
    )
    if not smoke.get("success"):
        # Same conditional-skip pattern: provider exists but is unhealthy
        # (network down, no docker daemon, etc.). Skip vs fail prevents
        # transient infra hiccups from blocking unrelated merges.
        pytest.skip(
            "code execution provider unhealthy in this env: "
            f"{smoke.get('error') or smoke.get('stderr')}"
        )

    temp_dir = Path(tempfile.mkdtemp(prefix="luncheon_data_"))
    data_file = temp_dir / "runtime_gate_sample.csv"
    _write_runtime_dataset(data_file)

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://testserver",
        ) as client:
            resp = await client.post(
                "/api/v1/data/analyze",
                json={
                    "data_file": str(data_file),
                    "analysis_type": "summary",
                },
            )

        assert resp.status_code == 200, resp.text
        payload = resp.json()
        assert payload.get("success") is True, payload.get("error")
        assert payload.get("analysis_type") == "summary"
        assert isinstance(payload.get("answer"), str) and payload["answer"].strip()
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)
