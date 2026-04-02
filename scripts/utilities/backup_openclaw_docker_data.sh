#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/../.." && pwd)"
TIMESTAMP="${TIMESTAMP:-$(date +%F_%H%M%S)}"
TARGET_ROOT="${TARGET_ROOT:-/Volumes/T7 1/Transfer-260401/DockerData}"
BACKUP_ROOT="${BACKUP_ROOT:-${TARGET_ROOT%/}/industry-ai-flow_${TIMESTAMP}}"

POSTGRES_CONTAINER="${POSTGRES_CONTAINER:-industry-ai-postgres}"
POSTGRES_VOLUME="${POSTGRES_VOLUME:-industry-ai-flow_postgres_data}"
POSTGRES_DB="${POSTGRES_DB:-ai_workflow}"
POSTGRES_USER="${POSTGRES_USER:-openclaw}"
POSTGRES_PASSWORD="${POSTGRES_PASSWORD:-password}"

ORBSTACK_DATA_DIR="${ORBSTACK_DATA_DIR:-$HOME/Library/Group Containers/HUAQ24HBR6.dev.orbstack/data}"
BACKUP_ORBSTACK_DATA="${BACKUP_ORBSTACK_DATA:-true}"
REOPEN_ORBSTACK="${REOPEN_ORBSTACK:-false}"

WARNINGS=0

log() {
  printf '[%s] %s\n' "$(date '+%F %T')" "$*"
}

warn() {
  WARNINGS=$((WARNINGS + 1))
  printf '[%s] WARN: %s\n' "$(date '+%F %T')" "$*" >&2
}

die() {
  printf '[%s] ERROR: %s\n' "$(date '+%F %T')" "$*" >&2
  exit 1
}

require_cmd() {
  command -v "$1" >/dev/null 2>&1 || die "Missing required command: $1"
}

bool_is_true() {
  case "${1,,}" in
    true|1|yes|y) return 0 ;;
    *) return 1 ;;
  esac
}

find_container() {
  if docker ps -a --format '{{.Names}}' | grep -qx "${POSTGRES_CONTAINER}"; then
    printf '%s\n' "${POSTGRES_CONTAINER}"
    return
  fi

  docker ps -a --format '{{.Names}}\t{{.Image}}' \
    | awk -F '\t' '$1 ~ /industry-ai/ || $2 ~ /(pgvector|postgres)/ {print $1}' \
    | head -n 1
}

find_volume() {
  if docker volume ls --format '{{.Name}}' | grep -qx "${POSTGRES_VOLUME}"; then
    printf '%s\n' "${POSTGRES_VOLUME}"
    return
  fi

  if [[ -n "${1:-}" ]]; then
    docker inspect "$1" \
      --format '{{range .Mounts}}{{if eq .Destination "/var/lib/postgresql/data"}}{{println .Name}}{{end}}{{end}}' \
      2>/dev/null \
      | awk 'NF {print; exit}'
    return
  fi

  docker volume ls --format '{{.Name}}' \
    | awk '/industry-ai.*postgres|postgres.*industry-ai/ {print; exit}'
}

container_state() {
  docker inspect -f '{{.State.Status}}' "$1" 2>/dev/null || true
}

write_metadata() {
  log "Writing Docker inventory and recovery metadata"

  {
    printf 'timestamp=%s\n' "${TIMESTAMP}"
    printf 'user=%s\n' "$(id -un)"
    printf 'hostname=%s\n' "$(hostname)"
    printf 'root_dir=%s\n' "${ROOT_DIR}"
    printf 'target_root=%s\n' "${TARGET_ROOT}"
    printf 'backup_root=%s\n' "${BACKUP_ROOT}"
    printf 'postgres_container=%s\n' "${DETECTED_CONTAINER:-}"
    printf 'postgres_volume=%s\n' "${DETECTED_VOLUME:-}"
    printf 'postgres_db=%s\n' "${POSTGRES_DB}"
    printf 'postgres_user=%s\n' "${POSTGRES_USER}"
    printf 'orbstack_data_dir=%s\n' "${ORBSTACK_DATA_DIR}"
  } >"${BACKUP_ROOT}/meta/backup_manifest.txt"

  docker version >"${BACKUP_ROOT}/meta/docker_version.txt" 2>&1 || true
  docker info >"${BACKUP_ROOT}/meta/docker_info.txt" 2>&1 || true
  docker images >"${BACKUP_ROOT}/meta/docker_images.txt" 2>&1 || true
  docker ps -a >"${BACKUP_ROOT}/meta/docker_ps_a.txt" 2>&1 || true
  docker volume ls >"${BACKUP_ROOT}/meta/docker_volume_ls.txt" 2>&1 || true

  if [[ -n "${DETECTED_CONTAINER:-}" ]]; then
    docker inspect "${DETECTED_CONTAINER}" >"${BACKUP_ROOT}/meta/container_inspect.json" 2>&1 || true
  fi

  if [[ -n "${DETECTED_VOLUME:-}" ]]; then
    docker volume inspect "${DETECTED_VOLUME}" >"${BACKUP_ROOT}/meta/volume_inspect.json" 2>&1 || true
  fi

  if [[ -f "${ROOT_DIR}/docker-compose-postgres.yml" ]]; then
    cp "${ROOT_DIR}/docker-compose-postgres.yml" "${BACKUP_ROOT}/meta/docker-compose-postgres.yml"
  fi
}

dump_postgres() {
  local container="$1"
  local state started_for_dump dump_name dump_path_in_container

  [[ -n "${container}" ]] || {
    warn "Skipping pg_dump because no PostgreSQL container was found"
    return
  }

  state="$(container_state "${container}")"
  started_for_dump=false

  if [[ "${state}" != "running" ]]; then
    log "Starting container ${container} for pg_dump"
    if docker start "${container}" >/dev/null 2>&1; then
      started_for_dump=true
      sleep 5
    else
      warn "Could not start container ${container}; skipping pg_dump"
      return
    fi
  fi

  if ! docker exec "${container}" sh -lc \
    "PGPASSWORD='${POSTGRES_PASSWORD}' pg_isready -h 127.0.0.1 -U '${POSTGRES_USER}' -d '${POSTGRES_DB}' >/dev/null 2>&1"; then
    warn "PostgreSQL in ${container} is not ready for pg_dump with db=${POSTGRES_DB} user=${POSTGRES_USER}"
    if [[ "${started_for_dump}" == "true" ]]; then
      docker stop "${container}" >/dev/null 2>&1 || true
    fi
    return
  fi

  dump_name="${POSTGRES_DB}_${TIMESTAMP}.dump"
  dump_path_in_container="/tmp/${dump_name}"

  log "Creating logical dump ${dump_name}"
  if docker exec "${container}" sh -lc \
    "PGPASSWORD='${POSTGRES_PASSWORD}' pg_dump -h 127.0.0.1 -U '${POSTGRES_USER}' -d '${POSTGRES_DB}' -Fc -f '${dump_path_in_container}'"; then
    docker cp "${container}:${dump_path_in_container}" "${BACKUP_ROOT}/postgres/${dump_name}"
    docker exec "${container}" rm -f "${dump_path_in_container}" >/dev/null 2>&1 || true
    log "Saved logical dump to ${BACKUP_ROOT}/postgres/${dump_name}"
  else
    warn "pg_dump failed in container ${container}"
  fi

  if [[ "${started_for_dump}" == "true" ]]; then
    docker stop "${container}" >/dev/null 2>&1 || true
  fi
}

backup_volume_archive() {
  local volume="$1"
  local container="$2"
  local state archive_name container_was_running

  [[ -n "${volume}" ]] || {
    warn "Skipping volume archive because no PostgreSQL volume was found"
    return
  }

  container_was_running=false
  if [[ -n "${container}" ]]; then
    state="$(container_state "${container}")"
    if [[ "${state}" == "running" ]]; then
      log "Stopping container ${container} for a consistent volume snapshot"
      docker stop "${container}" >/dev/null 2>&1 || warn "Could not stop ${container} before volume export"
      container_was_running=true
    fi
  fi

  archive_name="${volume}_${TIMESTAMP}.tar.gz"

  log "Archiving Docker volume ${volume}"
  if docker run --rm \
    -v "${volume}:/from" \
    -v "${BACKUP_ROOT}/postgres:/to" \
    alpine sh -lc "cd /from && tar czf '/to/${archive_name}' ."; then
    log "Saved volume archive to ${BACKUP_ROOT}/postgres/${archive_name}"
  else
    warn "Failed to archive Docker volume ${volume}"
  fi

  if [[ "${container_was_running}" == "true" ]]; then
    log "Restarting container ${container} to restore its original state"
    docker start "${container}" >/dev/null 2>&1 || warn "Could not restart ${container} after volume export"
  fi
}

backup_orbstack_data_dir() {
  local orbstack_was_running=false

  if ! bool_is_true "${BACKUP_ORBSTACK_DATA}"; then
    log "Skipping OrbStack data copy because BACKUP_ORBSTACK_DATA=${BACKUP_ORBSTACK_DATA}"
    return
  fi

  [[ -d "${ORBSTACK_DATA_DIR}" ]] || {
    warn "OrbStack data directory not found: ${ORBSTACK_DATA_DIR}"
    return
  }

  if pgrep -x OrbStack >/dev/null 2>&1; then
    orbstack_was_running=true
    log "Quitting OrbStack before copying disk images"
    osascript -e 'quit app "OrbStack"' >/dev/null 2>&1 || warn "Could not quit OrbStack cleanly"
    sleep 5
  fi

  log "Copying OrbStack data directory to SSD"
  rsync -aH --sparse --info=progress2 \
    "${ORBSTACK_DATA_DIR}/" \
    "${BACKUP_ROOT}/orbstack-data/"

  if [[ "${orbstack_was_running}" == "true" ]] && bool_is_true "${REOPEN_ORBSTACK}"; then
    log "Reopening OrbStack"
    open -a OrbStack >/dev/null 2>&1 || warn "Could not reopen OrbStack"
  fi
}

write_checksums() {
  log "Writing SHA256 checksums"
  (
    cd "${BACKUP_ROOT}"
    find . -type f ! -name 'SHA256SUMS.txt' -print0 \
      | xargs -0 shasum -a 256
  ) >"${BACKUP_ROOT}/meta/SHA256SUMS.txt"
}

print_summary() {
  log "Backup complete"
  printf '\n'
  printf 'Backup root: %s\n' "${BACKUP_ROOT}"
  printf 'Postgres files:\n'
  find "${BACKUP_ROOT}/postgres" -maxdepth 1 -type f | sed 's#^#  - #'
  printf 'Metadata files:\n'
  find "${BACKUP_ROOT}/meta" -maxdepth 1 -type f | sed 's#^#  - #'
  if [[ -d "${BACKUP_ROOT}/orbstack-data" ]]; then
    printf 'OrbStack copy:\n'
    printf '  - %s\n' "${BACKUP_ROOT}/orbstack-data"
  fi
  printf 'Warnings: %s\n' "${WARNINGS}"
}

main() {
  require_cmd docker
  require_cmd rsync
  require_cmd tar
  require_cmd shasum
  require_cmd awk
  require_cmd grep
  require_cmd sed

  [[ -d "${TARGET_ROOT}" ]] || die "Target root does not exist: ${TARGET_ROOT}"

  if [[ "$(id -un)" != "openclaw" ]]; then
    warn "This script is intended to run from the openclaw account for Library access"
  fi

  mkdir -p "${BACKUP_ROOT}/meta" "${BACKUP_ROOT}/postgres"
  log "Backup root: ${BACKUP_ROOT}"

  if ! docker info >/dev/null 2>&1; then
    die "Docker daemon is not reachable; start OrbStack first"
  fi

  DETECTED_CONTAINER="$(find_container || true)"
  DETECTED_VOLUME="$(find_volume "${DETECTED_CONTAINER}" || true)"

  log "Detected PostgreSQL container: ${DETECTED_CONTAINER:-<none>}"
  log "Detected PostgreSQL volume: ${DETECTED_VOLUME:-<none>}"

  write_metadata
  dump_postgres "${DETECTED_CONTAINER:-}"
  backup_volume_archive "${DETECTED_VOLUME:-}" "${DETECTED_CONTAINER:-}"
  backup_orbstack_data_dir
  write_checksums
  print_summary
}

main "$@"
