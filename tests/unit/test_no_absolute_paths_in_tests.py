from __future__ import annotations

from pathlib import Path


def test_no_hardcoded_user_absolute_paths_in_tests() -> None:
    root = Path("tests")
    offenders: list[str] = []
    pattern = "/" + "Users/"

    for file_path in root.rglob("test_*.py"):
        text = file_path.read_text(encoding="utf-8")
        if pattern in text:
            offenders.append(str(file_path))

    assert not offenders, f"Found hardcoded '{pattern}' paths in: {offenders}"
