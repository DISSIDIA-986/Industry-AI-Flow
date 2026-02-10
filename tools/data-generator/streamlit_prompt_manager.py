"""Compatibility entrypoint for prompt-admin streamlit app.

This file is kept for backward compatibility. The real implementation now
lives in tools/prompt-admin/app.py.
"""

from __future__ import annotations

from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path


def _load_prompt_admin_main():
    app_path = (
        Path(__file__).resolve().parent.parent / "prompt-admin" / "app.py"
    )
    spec = spec_from_file_location("prompt_admin_app", app_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Failed to load prompt-admin app from {app_path}")
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.main


def main() -> None:
    prompt_admin_main = _load_prompt_admin_main()
    prompt_admin_main()


if __name__ == "__main__":
    main()
