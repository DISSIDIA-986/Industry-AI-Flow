from __future__ import annotations

import ast
from pathlib import Path


def test_main_mounts_cost_estimation_router() -> None:
    source_path = Path("backend/main.py")
    tree = ast.parse(source_path.read_text(encoding="utf-8"))

    include_calls = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            if node.func.attr == "include_router":
                include_calls.append(node)

    mounted = False
    for call in include_calls:
        if not call.args:
            continue
        first_arg = call.args[0]
        if isinstance(first_arg, ast.Name) and first_arg.id == "cost_estimation_router":
            mounted = True
            break

    assert mounted, "cost_estimation_router must be mounted in backend/main.py"
