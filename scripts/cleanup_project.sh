#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SCAN_SCRIPT="$ROOT/scripts/scan_cleanup_targets.sh"
REPORT_FILE="$ROOT/cleanup_scan_report.tsv"
MANIFEST_FILE="$ROOT/cleanup_manifest.log"
ROLLBACK_SCRIPT="$ROOT/scripts/rollback_cleanup.sh"

MODE="dry-run"
INCLUDE_REVIEW="false"

usage() {
  cat <<'EOF'
Usage: bash scripts/cleanup_project.sh [--dry-run|--analyze-only|--execute|--rollback|--verify] [--include-review]

Modes:
  --dry-run       Run scanner and print planned moves (default)
  --analyze-only  Run scanner only
  --execute       Move files per report and write cleanup_manifest.log
  --rollback      Rollback using cleanup_manifest.log
  --verify        Verify manifest consistency and protected-path safety

Options:
  --include-review   Include "review" risk items in --execute / --dry-run
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --dry-run) MODE="dry-run" ;;
    --analyze-only) MODE="analyze-only" ;;
    --execute) MODE="execute" ;;
    --rollback) MODE="rollback" ;;
    --verify) MODE="verify" ;;
    --include-review) INCLUDE_REVIEW="true" ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown option: $1"; usage; exit 1 ;;
  esac
  shift
done

run_scan() {
  bash "$SCAN_SCRIPT" "$ROOT"
}

select_moves() {
  local allowed_regex='^(safe)$'
  if [[ "$INCLUDE_REVIEW" == "true" ]]; then
    allowed_regex='^(safe|review)$'
  fi
  awk -F'\t' -v rgx="$allowed_regex" '
    NR>1 && $1 ~ rgx {
      print $3 "\t" $4 "\t" $1 "\t" $2
    }
  ' "$REPORT_FILE"
}

dry_run() {
  run_scan
  echo
  echo "Planned moves (include_review=$INCLUDE_REVIEW):"
  select_moves | while IFS=$'\t' read -r src dst risk reason; do
    echo "  [$risk] $src -> $dst ($reason)"
  done
}

execute_moves() {
  run_scan
  local blocker_count
  blocker_count="$(awk -F'\t' 'NR>1 && $1=="blocker"{c++} END{print c+0}' "$REPORT_FILE")"
  if [[ "$blocker_count" -gt 0 ]]; then
    echo "Found blocker items: $blocker_count. They will not be moved."
  fi

  : > "$MANIFEST_FILE"
  echo "#timestamp|source|destination|risk" >> "$MANIFEST_FILE"

  local moved=0
  select_moves | while IFS=$'\t' read -r src dst risk _reason; do
    [[ -z "$src" || -z "$dst" ]] && continue
    if [[ ! -e "$ROOT/$src" ]]; then
      echo "SKIP missing: $src"
      continue
    fi
    mkdir -p "$ROOT/$(dirname "$dst")"
    mv "$ROOT/$src" "$ROOT/$dst"
    echo "$(date -u +%Y-%m-%dT%H:%M:%SZ)|$src|$dst|$risk" >> "$MANIFEST_FILE"
    echo "MOVED [$risk] $src -> $dst"
    moved=$((moved + 1))
  done

  echo "Manifest written: $MANIFEST_FILE"
  echo "Moved count: $(awk 'END{print NR-1}' "$MANIFEST_FILE")"
}

verify_manifest() {
  if [[ ! -f "$MANIFEST_FILE" ]]; then
    echo "Manifest not found: $MANIFEST_FILE"
    exit 1
  fi

  local failed=0
  while IFS='|' read -r ts src dst risk; do
    [[ "$ts" == \#* ]] && continue
    if [[ ! -e "$ROOT/$dst" ]]; then
      echo "VERIFY FAIL: destination missing: $dst"
      failed=$((failed + 1))
    fi
    if [[ -e "$ROOT/$src" ]]; then
      echo "VERIFY WARN: source still exists: $src"
    fi
    case "$src" in
      backend/*|tests/*|scripts/*|config/*|docs/*|infrastructure/*|docker/*)
        echo "VERIFY FAIL: protected path in manifest source: $src"
        failed=$((failed + 1))
        ;;
      Makefile|pyproject.toml|requirements.txt|README.md|AGENTS.md|.env.example)
        echo "VERIFY FAIL: protected file in manifest source: $src"
        failed=$((failed + 1))
        ;;
    esac
  done < "$MANIFEST_FILE"

  if [[ "$failed" -gt 0 ]]; then
    echo "Verify failed: $failed issue(s)"
    exit 1
  fi
  echo "Verify passed."
}

case "$MODE" in
  dry-run) dry_run ;;
  analyze-only) run_scan ;;
  execute) execute_moves ;;
  rollback) bash "$ROLLBACK_SCRIPT" "$MANIFEST_FILE" ;;
  verify) verify_manifest ;;
  *) usage; exit 1 ;;
esac
