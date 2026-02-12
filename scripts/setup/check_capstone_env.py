#!/usr/bin/env python3
"""Validate Capstone runtime assumptions (Python and pinned dependencies)."""

from __future__ import annotations

import argparse
import importlib.metadata as md
import re
import sys
from pathlib import Path
from typing import Dict, List, Tuple

PACKAGE_PATTERN = re.compile(r"^\s*([A-Za-z0-9_.\-\[\]]+)\s*==\s*([^\s#]+)")


def _normalize_name(raw: str) -> str:
    name = raw.strip().lower()
    if "[" in name:
        name = name.split("[", 1)[0]
    return name.replace("_", "-")


def parse_lock_file(lock_path: Path) -> Dict[str, str]:
    if not lock_path.exists():
        raise FileNotFoundError(f"lock file not found: {lock_path}")

    parsed: Dict[str, str] = {}
    for line in lock_path.read_text(encoding="utf-8").splitlines():
        if not line or line.strip().startswith("#"):
            continue
        match = PACKAGE_PATTERN.match(line)
        if not match:
            continue
        name, version = match.groups()
        parsed[_normalize_name(name)] = version.strip()
    return parsed


def check_python_version(strict: bool) -> Tuple[bool, str]:
    current = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    valid = (sys.version_info.major, sys.version_info.minor) == (3, 13)
    if valid:
        return True, f"Python version OK: {current}"

    message = (
        f"Python version is {current}; expected 3.13.x for Capstone standard."
    )
    if strict:
        return False, message
    return True, f"[WARN] {message}"


def check_locked_dependencies(
    locked: Dict[str, str],
    strict: bool,
) -> Tuple[bool, List[str]]:
    messages: List[str] = []
    mismatches: List[str] = []

    for package, expected in sorted(locked.items()):
        try:
            actual = md.version(package)
        except md.PackageNotFoundError:
            msg = f"missing: {package}=={expected}"
            mismatches.append(msg)
            continue

        if actual != expected:
            mismatches.append(f"mismatch: {package} expected {expected}, got {actual}")

    if not mismatches:
        messages.append("Dependency lock check OK.")
        return True, messages

    messages.extend(mismatches)
    if strict:
        return False, messages

    messages.insert(
        0,
        "[WARN] dependency lock check found drift; run in strict mode to enforce failure.",
    )
    return True, messages


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--lock",
        default="requirements/lock/py313-capstone.txt",
        help="Path to lock file.",
    )
    parser.add_argument(
        "--strict-python",
        action="store_true",
        help="Fail if Python minor version is not 3.13.",
    )
    parser.add_argument(
        "--strict-lock",
        action="store_true",
        help="Fail if installed packages drift from lock file.",
    )
    args = parser.parse_args()

    lock_path = Path(args.lock)
    try:
        locked = parse_lock_file(lock_path)
    except FileNotFoundError as exc:
        print(f"ERROR: {exc}")
        return 1

    python_ok, python_msg = check_python_version(strict=args.strict_python)
    print(python_msg)

    deps_ok, dep_msgs = check_locked_dependencies(locked, strict=args.strict_lock)
    for msg in dep_msgs:
        print(msg)

    if python_ok and deps_ok:
        print("Capstone environment check finished.")
        return 0

    print("Capstone environment check failed.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
