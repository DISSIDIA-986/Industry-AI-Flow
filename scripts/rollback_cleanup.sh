#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
MANIFEST_FILE="${1:-$ROOT/cleanup_manifest.log}"

if [[ ! -f "$MANIFEST_FILE" ]]; then
  echo "Manifest not found: $MANIFEST_FILE"
  exit 1
fi

echo "Rollback from manifest: $MANIFEST_FILE"

TMP_REV="$(mktemp)"
grep -v '^#' "$MANIFEST_FILE" | tac > "$TMP_REV"

rolled=0
while IFS='|' read -r _ts src dst _risk; do
  [[ -z "$src" || -z "$dst" ]] && continue
  if [[ ! -e "$ROOT/$dst" ]]; then
    echo "SKIP missing destination: $dst"
    continue
  fi
  mkdir -p "$ROOT/$(dirname "$src")"
  mv "$ROOT/$dst" "$ROOT/$src"
  echo "ROLLED BACK: $dst -> $src"
  rolled=$((rolled + 1))
done < "$TMP_REV"

rm -f "$TMP_REV"
echo "Rollback complete. Restored: $rolled"
