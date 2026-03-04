#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/../.." && pwd)"
LOG_DIR="${ROOT_DIR}/logs"
ENV_FILE="${ROOT_DIR}/.env"
if [[ -f "${ENV_FILE}" ]]; then
  set -a
  # shellcheck disable=SC1090
  source "${ENV_FILE}"
  set +a
fi
if [[ -z "${VENV_DIR+x}" ]]; then
  if [[ "$(uname -m)" == "arm64" ]] && [[ -x "${ROOT_DIR}/.venv_capstone_arm64/bin/python" ]]; then
    VENV_DIR="${ROOT_DIR}/.venv_capstone_arm64"
  else
    VENV_DIR="${ROOT_DIR}/.venv_capstone"
  fi
fi
PYTHON_BIN="${PYTHON_BIN:-python3.13}"
LOCK_FILE="${LOCK_FILE:-${ROOT_DIR}/requirements/lock/py313-capstone.txt}"
BACKEND_HOST="${BACKEND_HOST:-127.0.0.1}"
BACKEND_PORT="${BACKEND_PORT:-8000}"
FRONTEND_PORT="${FRONTEND_PORT:-3000}"
POSTGRES_HOST="${POSTGRES_HOST:-localhost}"
POSTGRES_PORT="${POSTGRES_PORT:-5432}"
POSTGRES_DB="${POSTGRES_DB:-ai_workflow}"
OLLAMA_MODEL="${OLLAMA_MODEL:-qwen3.5:4b}"
SKIP_FRONTEND_INSTALL="${SKIP_FRONTEND_INSTALL:-false}"

BACKEND_PID_FILE="${ROOT_DIR}/.backend.pid"
FRONTEND_PID_FILE="${ROOT_DIR}/.frontend.pid"

info() { echo "[INFO] $1"; }
warn() { echo "[WARN] $1"; }
err() { echo "[ERROR] $1"; }

require_cmd() {
  local cmd="$1"
  if ! command -v "${cmd}" >/dev/null 2>&1; then
    err "Missing required command: ${cmd}"
    exit 1
  fi
}

start_postgres_service() {
  if ! command -v brew >/dev/null 2>&1; then
    warn "brew not found; skip auto-starting PostgreSQL service"
    return
  fi

  local started=false
  for svc in postgresql@17 postgresql@16 postgresql@15 postgresql@14 postgresql; do
    if brew services list | awk '{print $1}' | grep -qx "${svc}"; then
      info "Starting PostgreSQL service via brew: ${svc}"
      brew services start "${svc}" >/dev/null || true
      started=true
      break
    fi
  done

  if [[ "${started}" == "false" ]]; then
    if command -v pg_isready >/dev/null 2>&1 && pg_isready -h "${POSTGRES_HOST}" -p "${POSTGRES_PORT}" >/dev/null 2>&1; then
      info "PostgreSQL already reachable at ${POSTGRES_HOST}:${POSTGRES_PORT}"
    else
      warn "No known postgresql brew service found; expecting PostgreSQL already running"
    fi
  fi
}

ensure_database_ready() {
  info "Ensuring database exists and pgvector extension is enabled"
  if ! psql -h "${POSTGRES_HOST}" -p "${POSTGRES_PORT}" -d postgres -tAc \
    "SELECT 1 FROM pg_database WHERE datname='${POSTGRES_DB}'" | grep -q 1; then
    createdb -h "${POSTGRES_HOST}" -p "${POSTGRES_PORT}" "${POSTGRES_DB}"
  fi

  psql -h "${POSTGRES_HOST}" -p "${POSTGRES_PORT}" -d "${POSTGRES_DB}" \
    -c "CREATE EXTENSION IF NOT EXISTS vector;" >/dev/null
}

ensure_ollama_model() {
  if ! curl -sSf "http://localhost:11434/api/tags" >/dev/null 2>&1; then
    warn "Ollama API not reachable at http://localhost:11434; trying background serve"
    nohup ollama serve >"${LOG_DIR}/ollama.log" 2>&1 &
    sleep 2
  fi

  if ! ollama list 2>/dev/null | awk 'NR>1 {print $1}' | grep -qx "${OLLAMA_MODEL}"; then
    info "Pulling Ollama model: ${OLLAMA_MODEL}"
    ollama pull "${OLLAMA_MODEL}"
  fi
}

ensure_python_env() {
  if [[ ! -x "${VENV_DIR}/bin/python" ]]; then
    info "Creating capstone virtual environment at ${VENV_DIR}"
    VENV_DIR="${VENV_DIR}" PYTHON_BIN="${PYTHON_BIN}" \
      "${ROOT_DIR}/scripts/setup/setup_capstone_env.sh"
  fi

  info "Validating Python lock-file dependencies"
  if ! "${VENV_DIR}/bin/python" "${ROOT_DIR}/scripts/setup/check_capstone_env.py" \
    --lock "${LOCK_FILE}" \
    --strict-python \
    --strict-lock >/dev/null 2>&1; then
    warn "Dependency drift detected; syncing from lock file"
    "${VENV_DIR}/bin/python" -m pip install -r "${LOCK_FILE}" >/dev/null
    "${VENV_DIR}/bin/python" "${ROOT_DIR}/scripts/setup/check_capstone_env.py" \
      --lock "${LOCK_FILE}" \
      --strict-python \
      --strict-lock
  else
    info "Python dependencies are aligned with lock file"
  fi
}

write_frontend_env() {
  local env_file="${ROOT_DIR}/frontend/.env.local"
  cat >"${env_file}" <<EOF
BACKEND_BASE_URL=http://${BACKEND_HOST}:${BACKEND_PORT}
NEXT_PUBLIC_API_URL=http://${BACKEND_HOST}:${BACKEND_PORT}/api/v1
NEXT_PUBLIC_REAL_API_URL=http://${BACKEND_HOST}:${BACKEND_PORT}/api/v1
EOF
  info "Wrote frontend env: ${env_file}"
}

start_backend() {
  info "Starting backend on ${BACKEND_HOST}:${BACKEND_PORT}"
  if [[ -f "${BACKEND_PID_FILE}" ]]; then
    local old_pid
    old_pid="$(cat "${BACKEND_PID_FILE}" || true)"
    if [[ -n "${old_pid}" ]] && kill -0 "${old_pid}" >/dev/null 2>&1; then
      warn "Existing backend process found (pid=${old_pid}); stopping it"
      kill "${old_pid}" || true
      sleep 1
    fi
  fi

  (
    cd "${ROOT_DIR}"
    source "${VENV_DIR}/bin/activate"
    LOCAL_PRIMARY_BACKEND=ollama \
    LLM_BACKEND=ollama \
    LLM_PROVIDER=ollama \
    HYBRID_MODE=local_only \
    REQUIRE_API_KEY="${REQUIRE_API_KEY:-false}" \
    WORKFLOW_RUNNER_MODE="${WORKFLOW_RUNNER_MODE:-auto}" \
    ENABLE_CONVERSATION_MEMORY="${ENABLE_CONVERSATION_MEMORY:-false}" \
    CODE_EXECUTION_PROVIDER=auto \
    ENABLE_DOCKER_SANDBOX=false \
    nohup uvicorn backend.main:app --host "${BACKEND_HOST}" --port "${BACKEND_PORT}" \
      >"${LOG_DIR}/backend.log" 2>&1 &
    echo $! >"${BACKEND_PID_FILE}"
  )
}

wait_backend() {
  local retries=60
  local url="http://${BACKEND_HOST}:${BACKEND_PORT}/api/v1/health"
  for _ in $(seq 1 "${retries}"); do
    if curl -sSf "${url}" >/dev/null 2>&1; then
      info "Backend is healthy: ${url}"
      return
    fi
    sleep 1
  done
  err "Backend failed to become healthy in time: ${url}"
  exit 1
}

start_frontend() {
  info "Starting frontend on 127.0.0.1:${FRONTEND_PORT}"
  if [[ -f "${FRONTEND_PID_FILE}" ]]; then
    local old_pid
    old_pid="$(cat "${FRONTEND_PID_FILE}" || true)"
    if [[ -n "${old_pid}" ]] && kill -0 "${old_pid}" >/dev/null 2>&1; then
      warn "Existing frontend process found (pid=${old_pid}); stopping it"
      kill "${old_pid}" || true
      sleep 1
    fi
  fi

  (
    cd "${ROOT_DIR}/frontend"
    if [[ "${SKIP_FRONTEND_INSTALL}" != "true" && ! -d node_modules ]]; then
      info "Installing frontend dependencies"
      npm install
    fi
    nohup npm run dev -- --hostname 127.0.0.1 --port "${FRONTEND_PORT}" \
      >"${LOG_DIR}/frontend.log" 2>&1 &
    echo $! >"${FRONTEND_PID_FILE}"
  )
}

wait_frontend() {
  local retries=90
  local url="http://127.0.0.1:${FRONTEND_PORT}"
  for _ in $(seq 1 "${retries}"); do
    if curl -sSf "${url}" >/dev/null 2>&1; then
      info "Frontend is ready: ${url}"
      return
    fi
    sleep 1
  done
  err "Frontend failed to become ready in time: ${url}"
  exit 1
}

run_smoke() {
  info "Running full stack smoke tests"
  BACKEND_URL="http://${BACKEND_HOST}:${BACKEND_PORT}" \
  FRONTEND_URL="http://127.0.0.1:${FRONTEND_PORT}" \
  "${ROOT_DIR}/scripts/testing/run_full_stack_smoke.sh"
}

main() {
  mkdir -p "${LOG_DIR}"

  require_cmd curl
  require_cmd psql
  require_cmd createdb
  require_cmd ollama
  require_cmd npm
  require_cmd "${PYTHON_BIN}"

  start_postgres_service
  ensure_database_ready
  ensure_ollama_model
  ensure_python_env
  write_frontend_env
  start_backend
  wait_backend
  start_frontend
  wait_frontend
  run_smoke

  echo ""
  echo "Full stack is up."
  echo "Backend:  http://${BACKEND_HOST}:${BACKEND_PORT}"
  echo "Frontend: http://127.0.0.1:${FRONTEND_PORT}"
  echo "Backend log:  ${LOG_DIR}/backend.log"
  echo "Frontend log: ${LOG_DIR}/frontend.log"
}

main "$@"
