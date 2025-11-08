#!/usr/bin/env python3
"""
Comprehensive Import Path Fix Script
Fixes all incorrect import paths across the project
"""

import os
import re
import sys
from pathlib import Path

# Colors
GREEN = '\033[92m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
RESET = '\033[0m'

def log(msg, color=BLUE):
    print(f"{color}{msg}{RESET}")

def fix_file(filepath, dry_run=False):
    """Fix imports in a single file"""
    if not os.path.exists(filepath):
        return False

    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    original = content
    fixes = []

    # Define all replacement patterns
    replacements = [
        (r'from backend\.services\.embedder import', 'from backend.services.core.embedder import'),
        (r'from backend\.services\.vectorstore import', 'from backend.services.core.vectorstore import'),
        (r'from backend\.services\.llm_client import', 'from backend.services.llm_integration.llm_client import'),
        (r'from backend\.services\.feedback_manager import', 'from backend.services.feedback_system.feedback_manager import'),
    ]

    for pattern, replacement in replacements:
        if re.search(pattern, content):
            content = re.sub(pattern, replacement, content)
            fixes.append(f"{pattern} → {replacement}")

    if content != original:
        if not dry_run:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
        log(f"{'[DRY-RUN] ' if dry_run else ''}Fixed: {filepath}", GREEN)
        for fix in fixes:
            log(f"  - {fix}", BLUE)
        return True
    return False

def main():
    dry_run = '--dry-run' in sys.argv
    project_root = Path(__file__).parent.parent
    os.chdir(project_root)

    log("="*60)
    log("Comprehensive Import Fix Script")
    log("="*60)
    if dry_run:
        log("DRY RUN MODE", YELLOW)

    # Files to fix
    files_to_check = []
    for root, dirs, files in os.walk("backend"):
        dirs[:] = [d for d in dirs if d not in ['venv', '__pycache__', 'venv_llamacpp']]
        for file in files:
            if file.endswith('.py'):
                files_to_check.append(os.path.join(root, file))

    log(f"\nScanning {len(files_to_check)} Python files...")

    fixed_count = 0
    for filepath in files_to_check:
        if fix_file(filepath, dry_run):
            fixed_count += 1

    # Create missing __init__.py files
    init_files = [
        "backend/__init__.py",
        "backend/services/core/__init__.py",
        "backend/services/llm_integration/__init__.py",
        "backend/services/feedback_system/__init__.py",
        "backend/services/intent_classification/__init__.py",
    ]

    for init_file in init_files:
        if not os.path.exists(init_file):
            if not dry_run:
                os.makedirs(os.path.dirname(init_file), exist_ok=True)
                with open(init_file, 'w') as f:
                    f.write('"""Package initialization"""\n')
            log(f"{'[DRY-RUN] ' if dry_run else ''}Created: {init_file}", GREEN)
            fixed_count += 1

    log(f"\n{'Would fix' if dry_run else 'Fixed'} {fixed_count} files", GREEN)

    return 0

if __name__ == "__main__":
    sys.exit(main())
