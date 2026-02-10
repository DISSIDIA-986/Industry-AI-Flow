from __future__ import annotations

import ast
from pathlib import Path


def test_main_mounts_prompt_router_without_extra_prefix():
    source_path = Path("backend/main.py")
    tree = ast.parse(source_path.read_text(encoding="utf-8"))

    include_calls = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            if node.func.attr == "include_router":
                include_calls.append(node)

    target_call = None
    for call in include_calls:
        if not call.args:
            continue
        first_arg = call.args[0]
        if isinstance(first_arg, ast.Name) and first_arg.id == "prompt_router":
            target_call = call
            break

    assert target_call is not None, "prompt_router must be mounted in backend/main.py"

    keyword_names = {kw.arg for kw in target_call.keywords if kw.arg is not None}
    assert "prefix" not in keyword_names, (
        "prompt_router should not be mounted with extra prefix; "
        "router already owns /api/prompts"
    )
