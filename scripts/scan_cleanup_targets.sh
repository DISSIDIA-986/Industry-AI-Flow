#!/usr/bin/env bash
set -euo pipefail

ROOT="${1:-.}"
ROOT="$(cd "$ROOT" && pwd)"
REPORT_FILE="${CLEANUP_REPORT_FILE:-$ROOT/temp/reports/cleanup/cleanup_scan_report.tsv}"
mkdir -p "$(dirname "$REPORT_FILE")"

PROTECTED_DIRS=(
  "backend"
  "tests"
  "scripts"
  "config"
  "docs"
  "infrastructure"
  "docker"
)

PROTECTED_FILES=(
  "Makefile"
  "pyproject.toml"
  "requirements.txt"
  "README.md"
  "AGENTS.md"
  ".env.example"
  "backend/main.py"
  "backend/config.py"
  "backend/init_database.py"
  "backend/init_comprehensive_database.py"
)

is_protected() {
  local rel="$1"
  for f in "${PROTECTED_FILES[@]}"; do
    if [[ "$rel" == "$f" ]]; then
      return 0
    fi
  done
  for d in "${PROTECTED_DIRS[@]}"; do
    if [[ "$rel" == "$d" || "$rel" == "$d/"* ]]; then
      return 0
    fi
  done
  return 1
}

destination_for() {
  local rel="$1"
  local base
  base="$(basename "$rel")"
  if [[ "$base" == "cleanup_manifest.log" || "$base" == "cleanup_scan_report.tsv" || "$base" == "cleanup_orchestrator_scan_report.tsv" ]]; then
    echo "temp/reports/cleanup/legacy/$base"
    return
  fi
  if [[ "$base" == "CODE_REVIEW_RESULTS.json" ]]; then
    echo "temp/reports/code_review/$base"
    return
  fi
  if [[ "$base" == "config_comparison.json" ]]; then
    echo "temp/reports/rag/$base"
    return
  fi
  if [[ "$base" == "startup_debug.log" ]]; then
    echo "logs/$base"
    return
  fi
  if [[ "$base" == .coverage* ]]; then
    echo "temp/reports/coverage/$base"
    return
  fi
  if [[ "$base" == ".DS_Store" ]]; then
    echo "temp/session-work/$base"
    return
  fi
  if [[ "$rel" == *.md ]]; then
    echo ".deprecated/reports/auto/$base"
    return
  fi
  if [[ "$base" == verify_*.py ]]; then
    echo ".deprecated/root-scripts/$base"
    return
  fi
  if [[ -d "$ROOT/$rel" ]]; then
    echo ".deprecated/artifacts/$base"
    return
  fi
  echo "temp/session-work/$base"
}

collect_candidates() {
  (
    cd "$ROOT"
    find . -maxdepth 1 -type f \( \
      -name '*_REPORT*.md' -o \
      -name '*_SUMMARY*.md' -o \
      -name '*_PLAN*.md' -o \
      -name 'HOTFIX_*.md' -o \
      -name 'verify_*.py' -o \
      -name '*_RESULTS.json' -o \
      -name 'cleanup_*.tsv' -o \
      -name 'cleanup_manifest.log' -o \
      -name 'cleanup_orchestrator_scan_report.tsv' -o \
      -name 'startup_debug.log' -o \
      -name 'config_comparison.json' -o \
      -name '.coverage' -o \
      -name '.DS_Store' \
    \) | sed 's#^\./##'
    find . -maxdepth 1 -type d \( \
      -name 'test-results*' -o \
      -name 'test_results*' -o \
      -name '*test-results*' -o \
      -name '__pycache__' -o \
      -name '.mypy_cache' -o \
      -name 'docker_test_output' \
    \) | sed 's#^\./##'
  ) | sort -u
}

runtime_refs_for() {
  local token="$1"
  (
    cd "$ROOT" && rg -n --fixed-strings "$token" backend tests scripts .github docker infrastructure config 2>/dev/null \
      | rg -v '^(scripts/scan_cleanup_targets\.sh|scripts/cleanup_project\.sh|scripts/rollback_cleanup\.sh|scripts/code_review/run_full_review\.py):' \
      || true
  )
}

docs_refs_for() {
  local token="$1"
  (cd "$ROOT" && rg -n --fixed-strings "$token" README.md docs research 2>/dev/null || true)
}

is_disposable_artifact() {
  local rel="$1"
  case "$rel" in
    .DS_Store|.coverage|.mypy_cache|__pycache__|startup_debug.log|cleanup_manifest.log|cleanup_scan_report.tsv|cleanup_orchestrator_scan_report.tsv|CODE_REVIEW_RESULTS.json)
      return 0
      ;;
    *)
      return 1
      ;;
  esac
}

{
  echo -e "risk\treason\tsource\tdestination\truntime_refs\tdocs_refs"

  while IFS= read -r rel; do
    [[ -z "$rel" ]] && continue
    if is_protected "$rel"; then
      continue
    fi
    dst="$(destination_for "$rel")"
    token="$(basename "$rel")"
    runtime_refs="$(runtime_refs_for "$token" | head -n 1)"
    docs_refs="$(docs_refs_for "$token" | head -n 1)"

    if is_disposable_artifact "$rel"; then
      risk="safe"
      reason="known disposable artifact"
    elif [[ -n "$runtime_refs" ]]; then
      risk="blocker"
      reason="referenced in runtime/test/ci/deploy scopes"
    elif [[ -n "$docs_refs" ]]; then
      risk="review"
      reason="referenced in docs/research"
    else
      risk="safe"
      reason="no references found in scoped scan"
    fi

    echo -e "${risk}\t${reason}\t${rel}\t${dst}\t${runtime_refs:-}\t${docs_refs:-}"
  done < <(collect_candidates)
} > "$REPORT_FILE"

SAFE_COUNT="$(awk -F'\t' 'NR>1 && $1=="safe"{c++} END{print c+0}' "$REPORT_FILE")"
REVIEW_COUNT="$(awk -F'\t' 'NR>1 && $1=="review"{c++} END{print c+0}' "$REPORT_FILE")"
BLOCKER_COUNT="$(awk -F'\t' 'NR>1 && $1=="blocker"{c++} END{print c+0}' "$REPORT_FILE")"
TOTAL_COUNT="$(awk 'END{print NR-1}' "$REPORT_FILE")"

echo "Cleanup scan report: $REPORT_FILE"
echo "Total: $TOTAL_COUNT | safe: $SAFE_COUNT | review: $REVIEW_COUNT | blocker: $BLOCKER_COUNT"
echo
column -t -s $'\t' "$REPORT_FILE" || cat "$REPORT_FILE"
