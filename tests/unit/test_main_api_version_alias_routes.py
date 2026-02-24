from __future__ import annotations

import ast
from pathlib import Path


def _collect_route_paths(tree: ast.AST) -> set[str]:
    paths: set[str] = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        if not isinstance(node.func, ast.Attribute):
            continue
        if node.func.attr not in {"get", "post", "put", "patch", "delete"}:
            continue
        if not node.args:
            continue
        first = node.args[0]
        if isinstance(first, ast.Constant) and isinstance(first.value, str):
            paths.add(first.value)
    return paths


def test_main_registers_versioned_alias_routes_for_core_endpoints() -> None:
    source_path = Path("backend/main.py")
    tree = ast.parse(source_path.read_text(encoding="utf-8"))
    paths = _collect_route_paths(tree)

    expected = {
        "/health",
        "/api/v1/health",
        "/documents",
        "/api/v1/documents",
        "/documents/upload",
        "/api/v1/documents/upload",
        "/data/upload",
        "/api/v1/data/upload",
        "/data/analyze",
        "/api/v1/data/analyze",
        "/visualization/generate",
        "/api/v1/visualization/generate",
    }

    missing = sorted(expected - paths)
    assert not missing, f"missing route aliases: {missing}"
