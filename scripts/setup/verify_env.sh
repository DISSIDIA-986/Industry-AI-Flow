#!/usr/bin/env bash
set -euo pipefail

echo "🔍 Verifying Capstone demo environment..."

POSTGRES_HOST="${POSTGRES_HOST:-localhost}"
POSTGRES_PORT="${POSTGRES_PORT:-5432}"
POSTGRES_DB="${POSTGRES_DB:-ai_workflow}"
OLLAMA_HOST="${OLLAMA_HOST:-http://localhost:11434}"
OLLAMA_MODEL="${OLLAMA_MODEL:-qwen3.5:9b}"

# 1) PostgreSQL readiness
if command -v pg_isready >/dev/null 2>&1; then
  if pg_isready -h "$POSTGRES_HOST" -p "$POSTGRES_PORT" >/dev/null 2>&1; then
    echo "✅ PostgreSQL TCP reachable at ${POSTGRES_HOST}:${POSTGRES_PORT}"
  else
    echo "❌ PostgreSQL is not reachable at ${POSTGRES_HOST}:${POSTGRES_PORT}"
    echo "   Start DB service first, then rerun this check."
    exit 1
  fi
else
  echo "⚠️ pg_isready not found; skipping TCP probe"
fi

if command -v psql >/dev/null 2>&1; then
  if psql "$POSTGRES_DB" -c "SELECT 1;" >/dev/null 2>&1; then
    echo "✅ PostgreSQL query check passed for DB '${POSTGRES_DB}'"
  else
    echo "❌ PostgreSQL query check failed for DB '${POSTGRES_DB}'"
    exit 1
  fi

  if psql "$POSTGRES_DB" -c "SELECT 1 FROM pg_extension WHERE extname='vector';" 2>/dev/null | grep -q "1"; then
    echo "✅ pgvector extension is enabled"
  else
    echo "⚠️ pgvector extension is not enabled (recommended for RAG vectors)"
    echo "   Run: psql ${POSTGRES_DB} -c 'CREATE EXTENSION IF NOT EXISTS vector;'"
  fi
else
  echo "❌ psql command not found"
  exit 1
fi

# 2) Ollama readiness + model availability
if ! command -v ollama >/dev/null 2>&1; then
  echo "❌ ollama command not found"
  exit 1
fi

if curl -sSf "${OLLAMA_HOST%/}/api/tags" >/dev/null 2>&1; then
  echo "✅ Ollama API reachable at ${OLLAMA_HOST}"
else
  echo "❌ Ollama API not reachable at ${OLLAMA_HOST}"
  exit 1
fi

if ollama list 2>/dev/null | awk 'NR>1 {print $1}' | grep -qx "$OLLAMA_MODEL"; then
  echo "✅ Ollama model available: ${OLLAMA_MODEL}"
else
  echo "❌ Configured OLLAMA_MODEL not found: ${OLLAMA_MODEL}"
  echo "   Installed models:"
  ollama list || true
  echo "   Fix: ollama pull ${OLLAMA_MODEL}  (or update OLLAMA_MODEL in .env)"
  exit 1
fi

# 3) Python dependency sanity (psycopg3 preferred, psycopg2 optional)
PYTHON_BIN="python3"
if command -v python3.13 >/dev/null 2>&1; then
  PYTHON_BIN="python3.13"
fi

if "$PYTHON_BIN" - <<'PY' >/dev/null 2>&1
import importlib
required = ["fastapi", "pgvector", "pydantic_settings"]
for name in required:
    if importlib.util.find_spec(name) is None:
        raise SystemExit(1)
if importlib.util.find_spec("psycopg") is None and importlib.util.find_spec("psycopg2") is None:
    raise SystemExit(1)
PY
then
  echo "✅ Python dependency sanity check passed (${PYTHON_BIN})"
else
  echo "❌ Python dependency sanity check failed (${PYTHON_BIN})"
  echo "   Install/refresh environment with: make capstone-env-setup"
  exit 1
fi

echo ""
echo "✅ Environment verification passed"
