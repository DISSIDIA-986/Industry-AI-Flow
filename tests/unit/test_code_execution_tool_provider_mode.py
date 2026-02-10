from __future__ import annotations

from backend.tools import code_execution


class _FakeManager:
    def __init__(self):
        self.calls = []

    def execute_code(self, **kwargs):
        self.calls.append(kwargs)
        return {
            "success": True,
            "stdout": "ok",
            "stderr": "",
            "error": None,
            "exit_code": 0,
            "execution_time": 0.01,
            "visualizations": [],
            "output_files": {},
        }


class _FakeExecutor:
    def __init__(self):
        self.calls = []

    def execute_code(self, **kwargs):
        self.calls.append(kwargs)
        return {
            "success": True,
            "stdout": "legacy",
            "stderr": "",
            "error": None,
            "exit_code": 0,
            "execution_time": 0.02,
            "visualizations": [],
            "output_files": {},
        }


def test_code_execution_tool_uses_manager_mode(monkeypatch):
    fake_manager = _FakeManager()
    monkeypatch.setattr(code_execution, "get_code_execution_manager", lambda: fake_manager)
    monkeypatch.setattr(code_execution, "code_executor", _FakeExecutor())
    monkeypatch.setattr(code_execution.settings, "code_execution_provider", "auto")

    result = code_execution.code_execution_tool.invoke({"code": "print('x')"})

    assert result["success"] is True
    assert fake_manager.calls
    assert fake_manager.calls[0]["mode"] == "auto"


def test_code_execution_tool_falls_back_to_legacy_executor(monkeypatch):
    fake_executor = _FakeExecutor()
    monkeypatch.setattr(code_execution, "get_code_execution_manager", lambda: None)
    monkeypatch.setattr(code_execution, "code_executor", fake_executor)

    result = code_execution.code_execution_tool.invoke({"code": "print('x')"})

    assert result["success"] is True
    assert result["stdout"] == "legacy"
    assert fake_executor.calls
