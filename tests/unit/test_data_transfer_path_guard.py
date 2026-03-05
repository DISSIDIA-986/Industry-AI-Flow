from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from backend.services.data_transfer import DataFileTransfer


def test_data_transfer_rejects_outside_allowed_paths() -> None:
    service = DataFileTransfer()

    result = service.transfer_file_for_docker("/etc/hosts", transfer_method="file_mapping")

    assert result["success"] is False
    assert "outside allowed" in (result.get("error") or "").lower()


def test_data_transfer_accepts_workspace_file_and_cleans_up() -> None:
    service = DataFileTransfer()
    workspace_temp = Path.cwd() / "temp" / "tdo_path_guard_tests"
    workspace_temp.mkdir(parents=True, exist_ok=True)
    source_file = workspace_temp / f"sample_{uuid4().hex[:8]}.csv"
    source_file.write_text("a,b\n1,2\n", encoding="utf-8")

    result = service.transfer_file_for_docker(str(source_file), transfer_method="file_mapping")

    assert result["success"] is True
    transferred_path = Path(result["transferred_path"])
    assert transferred_path.exists()
    assert transferred_path.name == source_file.name

    assert service.cleanup_transferred_data(result) is True
    assert not transferred_path.exists()

    source_file.unlink(missing_ok=True)
