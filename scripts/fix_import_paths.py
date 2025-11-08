#!/usr/bin/env python3
"""
Automated Fix Script for Import Paths
Industry AI Flow RAG System
"""

import os
import re
import sys
from pathlib import Path

# Colors for terminal output
RED = '\033[91m'
GREEN = '\033[92m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
RESET = '\033[0m'

def log_info(msg):
    print(f"{BLUE}ℹ️  {msg}{RESET}")

def log_success(msg):
    print(f"{GREEN}✅ {msg}{RESET}")

def log_warning(msg):
    print(f"{YELLOW}⚠️  {msg}{RESET}")

def log_error(msg):
    print(f"{RED}❌ {msg}{RESET}")


def fix_file_imports(filepath, replacements, dry_run=False):
    """
    Fix imports in a file

    Args:
        filepath: Path to file to fix
        replacements: Dict of {pattern: replacement}
        dry_run: If True, only show what would be changed

    Returns:
        True if changes were made/would be made
    """
    if not os.path.exists(filepath):
        log_warning(f"File not found: {filepath}")
        return False

    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
        original = content

    changes_made = []
    for pattern, replacement in replacements.items():
        matches = list(re.finditer(pattern, content))
        if matches:
            content = re.sub(pattern, replacement, content)
            changes_made.append((pattern, replacement, len(matches)))

    if content != original:
        if dry_run:
            log_info(f"Would fix: {filepath}")
            for pattern, replacement, count in changes_made:
                log_info(f"  {count}x: {pattern} → {replacement}")
        else:
            # Backup original file
            backup_path = f"{filepath}.backup"
            with open(backup_path, 'w', encoding='utf-8') as f:
                f.write(original)

            # Write fixed content
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)

            log_success(f"Fixed: {filepath}")
            for pattern, replacement, count in changes_made:
                log_info(f"  {count}x: {pattern[:50]}... → {replacement[:50]}...")
        return True
    return False


def main():
    """Main fix script"""
    print("="*60)
    print("Import Path Fix Script - Industry AI Flow")
    print("="*60)

    # Check for dry-run flag
    dry_run = '--dry-run' in sys.argv or '-n' in sys.argv
    if dry_run:
        log_info("DRY RUN MODE - No files will be modified")

    # Get project root
    project_root = Path(__file__).parent.parent
    os.chdir(project_root)
    log_info(f"Project root: {project_root}")

    fixes_applied = 0

    # Fix 1: backend/services/rag_engine.py
    log_info("\n[1/4] Fixing backend/services/rag_engine.py...")
    rag_engine_path = "backend/services/rag_engine.py"
    rag_engine_fixes = {
        r'from backend\.services\.embedder import': 'from backend.services.core.embedder import',
        r'from backend\.services\.vectorstore import': 'from backend.services.core.vectorstore import',
        r'from backend\.services\.llm_client import': 'from backend.services.llm_integration.llm_client import',
        r'from backend\.services\.feedback_manager import': 'from backend.services.feedback_system.feedback_manager import',
    }
    if fix_file_imports(rag_engine_path, rag_engine_fixes, dry_run):
        fixes_applied += 1

    # Fix 2: Check for other files with similar issues
    log_info("\n[2/4] Scanning for similar import issues...")

    # Find all Python files that might have incorrect imports
    for root, dirs, files in os.walk("backend"):
        # Skip virtual environments and cache
        dirs[:] = [d for d in dirs if d not in ['venv', '__pycache__', '.git', 'venv_llamacpp']]

        for file in files:
            if file.endswith('.py'):
                filepath = os.path.join(root, file)

                # Check for potential import issues
                with open(filepath, 'r', encoding='utf-8') as f:
                    content = f.read()

                # Look for imports that might need fixing
                potential_issues = []

                if 'from backend.services.embedder import' in content:
                    potential_issues.append('embedder import needs services.core')
                if 'from backend.services.vectorstore import' in content:
                    potential_issues.append('vectorstore import needs services.core')
                if 'from backend.services.llm_client import' in content:
                    potential_issues.append('llm_client import needs services.llm_integration')

                if potential_issues:
                    log_warning(f"Potential issues in {filepath}:")
                    for issue in potential_issues:
                        log_warning(f"  - {issue}")

    # Fix 3: Verify all service module __init__.py files exist
    log_info("\n[3/4] Verifying __init__.py files...")

    required_init_files = [
        "backend/__init__.py",
        "backend/services/__init__.py",
        "backend/services/core/__init__.py",
        "backend/services/llm_integration/__init__.py",
        "backend/services/retrieval/__init__.py",
        "backend/services/feedback_system/__init__.py",
        "backend/services/intent_classification/__init__.py",
        "backend/services/document_processing/__init__.py",
    ]

    for init_file in required_init_files:
        if not os.path.exists(init_file):
            log_warning(f"Missing: {init_file}")
            if not dry_run:
                os.makedirs(os.path.dirname(init_file), exist_ok=True)
                with open(init_file, 'w', encoding='utf-8') as f:
                    f.write('"""Package initialization"""\n')
                log_success(f"Created: {init_file}")
                fixes_applied += 1
        else:
            log_success(f"Exists: {init_file}")

    # Fix 4: Create import validation script
    log_info("\n[4/4] Creating import validation script...")

    validation_script = """#!/usr/bin/env python3
\"\"\"
Validate imports across the project
\"\"\"
import sys
import importlib.util

def check_import(module_path):
    try:
        spec = importlib.util.find_spec(module_path)
        if spec is None:
            return False, f"Module {module_path} not found"
        return True, "OK"
    except Exception as e:
        return False, str(e)

# Critical imports to check
critical_imports = [
    "backend.config",
    "backend.services.rag_engine",
    "backend.services.core.embedder",
    "backend.services.core.vectorstore",
]

print("Validating critical imports...")
all_ok = True
for module in critical_imports:
    ok, msg = check_import(module)
    status = "✅" if ok else "❌"
    print(f"{status} {module}: {msg}")
    if not ok:
        all_ok = False

sys.exit(0 if all_ok else 1)
"""

    if not dry_run:
        validation_path = "scripts/validate_imports.py"
        with open(validation_path, 'w', encoding='utf-8') as f:
            f.write(validation_script)
        os.chmod(validation_path, 0o755)
        log_success(f"Created: {validation_path}")
        fixes_applied += 1

    # Summary
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)

    if dry_run:
        log_info("Dry run completed - no changes made")
        log_info(f"Would apply {fixes_applied} fixes")
        log_info("Run without --dry-run to apply fixes")
    else:
        log_success(f"Applied {fixes_applied} fixes")
        log_info("\nNext steps:")
        log_info("1. Review the changes")
        log_info("2. Run: python test_comprehensive.py")
        log_info("3. If tests fail, check backup files (*.backup)")

    return 0 if fixes_applied > 0 else 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:
        log_error(f"Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
