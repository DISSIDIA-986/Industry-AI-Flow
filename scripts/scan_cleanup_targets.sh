#!/usr/bin/env bash
set -euo pipefail

ROOT="${1:-.}"
ROOT="$(cd "$ROOT" && pwd)"
REPORT_FILE="$ROOT/cleanup_scan_report.tsv"

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
      -name 'verify_*.py' \
    \) | sed 's#^\./##'
    find . -maxdepth 1 -type d \( \
      -name 'test-results*' -o \
      -name 'test_results*' -o \
      -name '*test-results*' \
    \) | sed 's#^\./##'
  ) | sort -u
}

runtime_refs_for() {
  local token="$1"
  (cd "$ROOT" && rg -n --fixed-strings "$token" backend tests scripts .github docker infrastructure config 2>/dev/null || true)
}

docs_refs_for() {
  local token="$1"
  (cd "$ROOT" && rg -n --fixed-strings "$token" README.md docs research 2>/dev/null || true)
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

    if [[ -n "$runtime_refs" ]]; then
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
