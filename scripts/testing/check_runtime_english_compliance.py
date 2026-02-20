#!/usr/bin/env python3
"""Runtime English compliance gate for frontend/backend source files."""

from __future__ import annotations

import re
import sys
from pathlib import Path

HAN_RE = re.compile(r"[\u3400-\u4DBF\u4E00-\u9FFF\uF900-\uFAFF]")
RUNTIME_HINT_RE = re.compile(
    r"(HTTPException|detail\s*=|logger\.(info|warning|error|debug)|print\(|"
    r"return\s*\{|message|error|agent_response|description\s*=|prompt|console\.)"
)
PROMPT_START_RE = re.compile(r"\b(prompt|message|agent_response)\b\s*=\s*([\"']{3})")


def _read_text(path: Path) -> str | None:
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return None


def _check_frontend_file(path: Path) -> list[tuple[int, str]]:
    text = _read_text(path)
    if text is None:
        return []
    offenders: list[tuple[int, str]] = []
    for idx, line in enumerate(text.splitlines(), start=1):
        if HAN_RE.search(line):
            offenders.append((idx, line.strip()))
    return offenders


def _check_backend_file(path: Path) -> list[tuple[int, str]]:
    text = _read_text(path)
    if text is None:
        return []

    offenders: list[tuple[int, str]] = []
    lines = text.splitlines()
    in_prompt_literal = False
    prompt_delimiter = ""

    for idx, line in enumerate(lines, start=1):
        if not HAN_RE.search(line):
            if in_prompt_literal and prompt_delimiter and prompt_delimiter in line:
                in_prompt_literal = False
                prompt_delimiter = ""
            continue

        stripped = line.strip()
        if stripped.startswith("#"):
            continue
        if stripped.startswith('"""') or stripped.startswith("'''"):
            # Treat module/class/function docstrings as non-runtime documentation.
            continue

        if in_prompt_literal:
            offenders.append((idx, stripped))
            if prompt_delimiter and prompt_delimiter in line:
                in_prompt_literal = False
                prompt_delimiter = ""
            continue

        prompt_start = PROMPT_START_RE.search(line)
        if prompt_start:
            in_prompt_literal = True
            prompt_delimiter = prompt_start.group(2)
            offenders.append((idx, stripped))
            if prompt_delimiter in line[prompt_start.end() :]:
                in_prompt_literal = False
                prompt_delimiter = ""
            continue

        if RUNTIME_HINT_RE.search(line):
            offenders.append((idx, stripped))

    return offenders


def _iter_files(root: Path, rel: str) -> list[Path]:
    base = root / rel
    if base.is_file():
        return [base]

    if not base.exists():
        return []

    files: list[Path] = []
    for suffix in ("*.py", "*.ts", "*.tsx", "*.js", "*.jsx", "*.css"):
        files.extend(base.rglob(suffix))
    return sorted(set(files))


def main() -> int:
    repo_root = Path(__file__).resolve().parents[2]

    frontend_paths = _iter_files(repo_root, "frontend/src")
    backend_paths: list[Path] = []
    for rel in (
        "backend/main.py",
        "backend/api",
        "backend/services",
        "backend/agents",
        "backend/middleware",
    ):
        backend_paths.extend(_iter_files(repo_root, rel))
    backend_paths = sorted(set(backend_paths))

    violations: list[str] = []

    for path in frontend_paths:
        offenders = _check_frontend_file(path)
        for line_no, snippet in offenders:
            violations.append(f"[frontend] {path.relative_to(repo_root)}:{line_no} {snippet}")

    for path in backend_paths:
        offenders = _check_backend_file(path)
        for line_no, snippet in offenders:
            violations.append(f"[backend] {path.relative_to(repo_root)}:{line_no} {snippet}")

    if violations:
        print("Runtime English compliance check failed.")
        for item in violations:
            print(item)
        print(f"Total violations: {len(violations)}")
        return 1

    print("Runtime English compliance check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
