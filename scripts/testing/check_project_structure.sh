#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"

failed=0

echo "🔎 Checking repository structure hygiene..."

report_issue() {
  local msg="$1"
  echo "❌ $msg"
  failed=$((failed + 1))
}

require_dir() {
  local dir="$1"
  if [[ ! -d "$dir" ]]; then
    report_issue "Missing required directory: $dir"
  fi
}

# Required status lifecycle directories
require_dir "docs/development/status/active"
require_dir "docs/development/status/archive"

# Only README should remain at docs/development/status root
status_root_md="$(find docs/development/status -maxdepth 1 -type f -name '*.md' ! -name 'README.md' | wc -l | tr -d ' ')"
if [[ "$status_root_md" != "0" ]]; then
  report_issue "Found markdown files directly under docs/development/status; move them into active/ or archive/"
  find docs/development/status -maxdepth 1 -type f -name '*.md' ! -name 'README.md' -print
fi

# Root should not accumulate temporary reports/artifacts
root_noise_files=(
  "*_REPORT*.md"
  "*_SUMMARY*.md"
  "*_PLAN*.md"
  "HOTFIX_*.md"
  "WEEK*_*.md"
  "P0_*.md"
  "verify_*.py"
  "*_analysis_script.py"
  "CODE_REVIEW_RESULTS.json"
  "cleanup_*.tsv"
  "cleanup_manifest.log"
  "cleanup_orchestrator_scan_report.tsv"
  "startup_debug.log"
  ".coverage"
  ".DS_Store"
)

for pattern in "${root_noise_files[@]}"; do
  if find . -maxdepth 1 -type f -name "$pattern" | grep -q .; then
    report_issue "Root contains forbidden artifact pattern: $pattern"
    find . -maxdepth 1 -type f -name "$pattern" -print
  fi
done

root_noise_dirs=(
  "docker_test_output"
  "__pycache__"
  ".mypy_cache"
  "test-results*"
  "test_results*"
  "*test-results*"
)

for pattern in "${root_noise_dirs[@]}"; do
  if find . -maxdepth 1 -type d -name "$pattern" | grep -q .; then
    report_issue "Root contains forbidden artifact directory pattern: $pattern"
    find . -maxdepth 1 -type d -name "$pattern" -print
  fi
done

# Legacy script files should live under scripts/setup or scripts/versioning
if [[ -f "install_python313_paddleocr.sh" || -f "install_with_compatibility_check.sh" || -f "version_manager.py" || -f "python_version_checker.py" || -f "advanced_version_manager.py" ]]; then
  report_issue "Found legacy setup/versioning scripts at repository root"
fi

if [[ "$failed" -gt 0 ]]; then
  echo "❌ Structure check failed with $failed issue(s)."
  exit 1
fi

echo "✅ Structure check passed."
