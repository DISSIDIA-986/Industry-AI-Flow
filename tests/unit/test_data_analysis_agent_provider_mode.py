from __future__ import annotations

import csv
from pathlib import Path

from backend.services.data_analysis.data_analysis_agent import DataAnalysisAgent


class _FakeLLM:
    def generate(self, prompt: str, **kwargs) -> str:
        del prompt, kwargs
        return """```python
print("summary ok")
```"""


class _FakeManager:
    def __init__(self) -> None:
        self.calls: list[dict] = []

    def execute_code(self, **kwargs) -> dict:
        self.calls.append(kwargs)
        # Fake one successful chart so the deterministic pipeline runs
        # end-to-end and surfaces success=True. We emit a valid
        # CHART_OK_JSON marker and matching output_files bytes.
        stdout = (
            'CHART_OK_JSON={"idx": 0, "type": "histogram", "status": "ok", '
            '"image_filename": "chart_00_histogram.png", '
            '"summary": {"column": "a", "count": 20, "mean": 10.5}}'
        )
        return {
            "success": True,
            "stdout": stdout,
            "stderr": "",
            "error": None,
            "execution_time": 0.1,
            "visualizations": ["chart_00_histogram.png"],
            "output_files": {"chart_00_histogram.png": b"\x89PNG"},
        }


def test_data_analysis_agent_prefers_provider_manager(monkeypatch, tmp_path: Path):
    # Dataset needs real variance so the deterministic planner picks
    # at least one chart. Otherwise the planner returns an empty plan
    # and the executor short-circuits without touching the manager.
    data_file = tmp_path / "sample.csv"
    with data_file.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["a", "b"])
        writer.writeheader()
        for i in range(20):
            writer.writerow({"a": i, "b": i * 2 + (i % 3)})

    fake_manager = _FakeManager()
    monkeypatch.setattr(
        "backend.services.data_analysis.data_analysis_agent.get_code_execution_manager",
        lambda: fake_manager,
    )
    monkeypatch.setattr(
        "backend.services.data_analysis.data_analysis_agent.code_executor",
        None,
    )
    monkeypatch.setattr(
        "backend.services.data_analysis.data_analysis_agent.settings.code_execution_provider",
        "auto",
    )

    agent = DataAnalysisAgent(llm_client=_FakeLLM())
    result = agent.analyze_query("give me summary", str(data_file))

    assert result["success"] is True
    assert fake_manager.calls
    assert fake_manager.calls[0]["mode"] == "auto"
