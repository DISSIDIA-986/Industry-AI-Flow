from __future__ import annotations

from backend.tools.data_analysis import (
    _generate_analysis_code,
    _generate_preprocessing_code,
    _resolve_container_data_path,
)


def test_resolve_container_data_path_maps_host_path_to_workspace() -> None:
    host_path = "/private/var/tmp/demo/runtime_gate_sample.csv"
    assert (
        _resolve_container_data_path(host_path) == "/workspace/runtime_gate_sample.csv"
    )


def test_resolve_container_data_path_keeps_workspace_paths() -> None:
    workspace_path = "/workspace/already_mapped.csv"
    assert _resolve_container_data_path(workspace_path) == workspace_path


def test_generate_analysis_code_uses_mapped_container_path() -> None:
    host_path = "/private/var/tmp/demo/runtime_gate_sample.csv"
    code = _generate_analysis_code(
        data_file=host_path,
        analysis_type="summary",
        target_column=None,
        columns=None,
    )
    assert "/workspace/runtime_gate_sample.csv" in code
    assert host_path not in code


def test_generate_preprocessing_code_uses_mapped_container_path() -> None:
    host_path = "/private/var/tmp/demo/runtime_gate_sample.csv"
    code = _generate_preprocessing_code(
        data_file=host_path,
        operations=["clean_missing"],
        output_format="csv",
    )
    assert "/workspace/runtime_gate_sample.csv" in code
    assert host_path not in code
