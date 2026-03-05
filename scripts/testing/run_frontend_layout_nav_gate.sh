#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/../.." && pwd)"
FRONTEND_DIR="${ROOT_DIR}/frontend"
LOG_DIR="${ROOT_DIR}/logs"

BACKEND_HOST="${BACKEND_HOST:-127.0.0.1}"
BACKEND_PORT="${BACKEND_PORT:-18000}"
BACKEND_BASE_URL="http://${BACKEND_HOST}:${BACKEND_PORT}"
BACKEND_HEALTH_URL="${BACKEND_BASE_URL}/api/v1/health"
BACKEND_LOG="${LOG_DIR}/backend-e2e-live.log"
FRONTEND_HOST="${FRONTEND_HOST:-127.0.0.1}"
FRONTEND_PORT="${FRONTEND_PORT:-3200}"

if [[ -x "${ROOT_DIR}/.venv/bin/python" ]]; then
  PYTHON_BIN="${ROOT_DIR}/.venv/bin/python"
else
  PYTHON_BIN="${PYTHON_BIN:-python}"
fi

backend_pid=""

cleanup() {
  if [[ -n "${backend_pid}" ]] && kill -0 "${backend_pid}" >/dev/null 2>&1; then
    kill "${backend_pid}" >/dev/null 2>&1 || true
    wait "${backend_pid}" 2>/dev/null || true
  fi
}

trap cleanup EXIT

mkdir -p "${LOG_DIR}"

if ! command -v curl >/dev/null 2>&1; then
  echo "[ERROR] curl is required"
  exit 1
fi

echo "[INFO] Running frontend unit/integration contract suites"
(
  cd "${FRONTEND_DIR}"
  npm run audit:high
  npm run test:unit
  npm run test:integration
)

echo "[INFO] Starting backend for live Playwright regression: ${BACKEND_BASE_URL}"
(
  cd "${ROOT_DIR}"
  REQUIRE_API_KEY=false \
  REQUIRE_USER_AUTH=false \
  AUTH_JWT_SECRET="" \
  WORKFLOW_RUNNER_MODE=fallback \
  HYBRID_MODE=local_only \
  LOCAL_PRIMARY_BACKEND=ollama \
  LLM_BACKEND=ollama \
  LLM_PROVIDER=ollama \
  ENABLE_DOCKER_SANDBOX=false \
  ENABLE_CONVERSATION_MEMORY=false \
  PROMPT_EXPERIMENTS_ENABLED=false \
  "${PYTHON_BIN}" -m uvicorn backend.main:app --host "${BACKEND_HOST}" --port "${BACKEND_PORT}"
) >"${BACKEND_LOG}" 2>&1 &
backend_pid=$!

backend_ready="false"
for _ in $(seq 1 90); do
  if curl -fsS "${BACKEND_HEALTH_URL}" >/dev/null 2>&1; then
    backend_ready="true"
    break
  fi
  sleep 1
done

if [[ "${backend_ready}" != "true" ]]; then
  echo "[ERROR] Backend failed to become healthy: ${BACKEND_HEALTH_URL}"
  echo "[ERROR] Backend log tail:"
  tail -n 80 "${BACKEND_LOG}" || true
  exit 1
fi

echo "[INFO] Running Playwright regression suites (mock + live API)"
(
  cd "${FRONTEND_DIR}"
  CI= \
  PW_FRONTEND_HOST="${FRONTEND_HOST}" \
  PW_FRONTEND_PORT="${FRONTEND_PORT}" \
  BACKEND_BASE_URL="${BACKEND_BASE_URL}" \
  npm run test:e2e -- --workers=1 \
    tests/e2e/layout-nav-regression.spec.ts \
    tests/e2e/layout-nav-live-api-regression.spec.ts
)

echo "[INFO] Frontend layout/nav regression gate passed"
