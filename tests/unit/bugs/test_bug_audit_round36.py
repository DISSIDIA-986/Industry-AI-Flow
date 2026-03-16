"""TDI Round 36 regression tests.

Focus: prevent path traversal when DockerExecutor writes input_files into the
temporary workspace.
"""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

import backend.services.code_executor.docker_executor as docker_executor_module
from backend.services.code_executor.docker_executor import DockerExecutor


class _FixedTemporaryDirectory:
    def __init__(self, path: Path) -> None:
        self.path = path

    def __enter__(self) -> str:
        self.path.mkdir(parents=True, exist_ok=True)
        return str(self.path)

    def __exit__(self, exc_type, exc, tb) -> None:  # noqa: ANN001
        del exc_type, exc, tb
        shutil.rmtree(self.path, ignore_errors=True)


def _build_executor() -> DockerExecutor:
    executor = object.__new__(DockerExecutor)
    executor.timeout = 60
    executor._validate_code = lambda code: []  # noqa: E731
    executor._run_container = lambda workspace, timeout=None: {  # noqa: E731
        "stdout": "ok",
        "stderr": "",
    }
    return executor


@pytest.mark.unit
def test_execute_rejects_parent_traversal_filename(tmp_path, monkeypatch) -> None:
    workspace = tmp_path / "workspace"
    escaped = tmp_path / "escaped.txt"
    monkeypatch.setattr(
        docker_executor_module.tempfile,
        "TemporaryDirectory",
        lambda: _FixedTemporaryDirectory(workspace),
    )

    executor = _build_executor()
    result = executor.execute("print('ok')", input_files={"../escaped.txt": b"boom"})

    assert result.success is False, "Traversal filename must be rejected."
    assert "invalid input filename" in (result.error or "").lower()
    assert (
        not escaped.exists()
    ), "Traversal filename should not create files outside workspace."


@pytest.mark.unit
def test_execute_rejects_absolute_input_filename(tmp_path, monkeypatch) -> None:
    workspace = tmp_path / "workspace"
    monkeypatch.setattr(
        docker_executor_module.tempfile,
        "TemporaryDirectory",
        lambda: _FixedTemporaryDirectory(workspace),
    )

    executor = _build_executor()
    result = executor.execute("print('ok')", input_files={"/tmp/owned.txt": b"boom"})

    assert result.success is False, "Absolute input filename must be rejected."
    assert "invalid input filename" in (result.error or "").lower()


@pytest.mark.unit
def test_execute_accepts_safe_input_filename(tmp_path, monkeypatch) -> None:
    workspace = tmp_path / "workspace"
    monkeypatch.setattr(
        docker_executor_module.tempfile,
        "TemporaryDirectory",
        lambda: _FixedTemporaryDirectory(workspace),
    )

    executor = _build_executor()
    content = b"col1,col2\n1,2\n"
    result = executor.execute("print('ok')", input_files={"input.csv": content})

    assert result.success is True
    assert result.output_files.get("input.csv") == content
