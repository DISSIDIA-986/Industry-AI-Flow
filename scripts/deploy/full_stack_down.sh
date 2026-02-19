#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/../.." && pwd)"
BACKEND_PID_FILE="${ROOT_DIR}/.backend.pid"
FRONTEND_PID_FILE="${ROOT_DIR}/.frontend.pid"

stop_by_pid_file() {
  local file="$1"
  local name="$2"

  if [[ ! -f "${file}" ]]; then
    echo "[INFO] ${name}: pid file not found (${file})"
    return
  fi

  local pid
  pid="$(cat "${file}" || true)"
  if [[ -z "${pid}" ]]; then
    echo "[WARN] ${name}: empty pid file (${file})"
    rm -f "${file}"
    return
  fi

  if kill -0 "${pid}" >/dev/null 2>&1; then
    echo "[INFO] ${name}: stopping pid ${pid}"
    kill "${pid}" || true
    sleep 1
  else
    echo "[INFO] ${name}: pid ${pid} already stopped"
  fi

  rm -f "${file}"
}

main() {
  stop_by_pid_file "${BACKEND_PID_FILE}" "backend"
  stop_by_pid_file "${FRONTEND_PID_FILE}" "frontend"

  # Best-effort cleanup for orphaned dev servers.
  pkill -f "uvicorn backend.main:app" >/dev/null 2>&1 || true
  pkill -f "next dev --hostname 127.0.0.1" >/dev/null 2>&1 || true

  echo "[INFO] Full stack stop sequence completed"
}

main "$@"

