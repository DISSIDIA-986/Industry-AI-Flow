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
        return {
            "success": True,
            "stdout": "summary ok",
            "stderr": "",
            "error": None,
            "execution_time": 0.1,
            "visualizations": [],
            "output_files": {},
        }


def test_data_analysis_agent_prefers_provider_manager(monkeypatch, tmp_path: Path):
    data_file = tmp_path / "sample.csv"
    with data_file.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["a", "b"])
        writer.writeheader()
        writer.writerow({"a": 1, "b": 2})

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
