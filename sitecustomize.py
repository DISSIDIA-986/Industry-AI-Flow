"""
Automatic path adjustments for Industry AI Flow.

Having this module at project root lets Python automatically run it on startup,
so tests and scripts no longer need to mutate sys.path manually.
"""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
BACKEND_ROOT = PROJECT_ROOT / "backend"

for path in (PROJECT_ROOT, BACKEND_ROOT):
    path_str = str(path)
    if path_str not in sys.path:
        sys.path.insert(0, path_str)
