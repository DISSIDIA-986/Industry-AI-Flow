#!/usr/bin/env bash
set -euo pipefail

BACKEND_URL="${BACKEND_URL:-http://127.0.0.1:8000}"
FRONTEND_URL="${FRONTEND_URL:-http://127.0.0.1:3123}"
SMOKE_TIMEOUT="${SMOKE_TIMEOUT:-12}"
DEEP_SMOKE_TIMEOUT="${DEEP_SMOKE_TIMEOUT:-60}"

PASS_COUNT=0
FAIL_COUNT=0

pass() {
  echo "PASS  $1"
  PASS_COUNT=$((PASS_COUNT + 1))
}

fail() {
  echo "FAIL  $1"
  FAIL_COUNT=$((FAIL_COUNT + 1))
}

check_http_status() {
  local name="$1"
  local url="$2"
  local expected="${3:-200}"
  local follow_redirects="${4:-false}"

  local code
  local curl_args=(-sS -o /tmp/fullstack_smoke_body.$$ -w "%{http_code}" --max-time "${SMOKE_TIMEOUT}")
  if [[ "${follow_redirects}" == "true" ]]; then
    curl_args+=(-L)
  fi

  code="$(curl "${curl_args[@]}" "${url}" || true)"
  if [[ "${code}" == "${expected}" ]]; then
    pass "${name} (${url})"
  else
    fail "${name} (${url}) expected=${expected} actual=${code}"
  fi
}

parse_json_field_equals() {
  local body="$1"
  local key="$2"
  local expected="$3"

  python3 - "${body}" "${key}" "${expected}" <<'PY'
import json
import sys

body = sys.argv[1]
key = sys.argv[2]
expected = sys.argv[3].lower()

try:
    payload = json.loads(body)
except Exception:
    sys.exit(1)

value = str(payload.get(key, "")).lower()
sys.exit(0 if value == expected else 1)
PY
}

check_json_field_equals() {
  local name="$1"
  local url="$2"
  local key="$3"
  local expected="$4"
  local body

  if ! body="$(curl -sS --max-time "${SMOKE_TIMEOUT}" "${url}" 2>/dev/null)"; then
    fail "${name} (${url}) request failed"
    return
  fi

  if parse_json_field_equals "${body}" "${key}" "${expected}"; then
    pass "${name} (${url})"
  else
    fail "${name} (${url}) payload.${key} != ${expected}"
  fi
}

check_json_post_status() {
  local name="$1"
  local url="$2"
  local payload="$3"
  local response_file="/tmp/fullstack_smoke_post_body.$$"

  local code
  code="$(curl -sS -o "${response_file}" -w "%{http_code}" \
    --max-time "${DEEP_SMOKE_TIMEOUT}" \
    -H "Content-Type: application/json" \
    -X POST "${url}" \
    -d "${payload}" || true)"

  if [[ "${code}" != "200" ]]; then
    fail "${name} (${url}) expected=200 actual=${code}"
    return
  fi

  local body
  body="$(cat "${response_file}")"
  if parse_json_field_equals "${body}" "success" "true"; then
    pass "${name} (${url})"
  else
    fail "${name} (${url}) payload.success != true"
  fi
}

check_frontend_proxy_health() {
  local name="$1"
  local path="$2"
  local target="${FRONTEND_URL}${path}"
  check_json_field_equals "${name}" "${target}" "status" "ok"
}

echo "== Full Stack Smoke =="
echo "BACKEND_URL=${BACKEND_URL}"
echo "FRONTEND_URL=${FRONTEND_URL}"

check_json_field_equals "backend platform health" "${BACKEND_URL}/api/v1/health" "status" "ok"
check_json_field_equals "backend workflow health" "${BACKEND_URL}/api/v1/workflow/health" "status" "ok"
check_json_field_equals "backend cost health" "${BACKEND_URL}/api/v1/cost-estimation/health" "status" "ok"

# Root may redirect to auth page; treat redirect + final 200 as healthy.
check_http_status "frontend home page" "${FRONTEND_URL}" "200" "true"

# Check both frontend API paths:
# 1) dedicated app-route proxy
check_frontend_proxy_health "frontend proxy platform health" "/api/backend/api/v1/health"
check_frontend_proxy_health "frontend proxy workflow health" "/api/backend/api/v1/workflow/health"
# 2) fallback rewrite proxy
check_frontend_proxy_health "frontend rewrite platform health" "/api/v1/health"

# Deeper backend smoke via live HTTP.
check_json_post_status "backend live cost prediction" \
  "${BACKEND_URL}/api/v1/cost-estimation/predict" \
  '{"project":{"project_type":"office","location":"toronto","sqft":120000,"floors":20,"num_units":10,"planned_duration_weeks":80,"estimated_cost_cad":50000000,"contractor_rating":4.1,"complexity_score":7,"team_experience_years":12,"num_change_orders":6,"weather_risk_factor":0.4,"material_volatility":0.35,"num_subcontractors":8,"budget_pressure":0.5,"risk_score":0.45,"risk_score_original":0.45},"confidence_quantile":0.9}'

check_json_post_status "backend live workflow query" \
  "${BACKEND_URL}/api/v1/workflow/query" \
  '{"query":"Estimate construction cost risk for a Toronto office tower","session_id":"fullstack-smoke-session","route_mode":"local_only"}'

echo ""
echo "SUMMARY pass=${PASS_COUNT} fail=${FAIL_COUNT}"
if [[ "${FAIL_COUNT}" -gt 0 ]]; then
  exit 1
fi
