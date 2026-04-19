#!/usr/bin/env bash
# Pre-warm the backend so the first demo query doesn't pay cold-start tax.
#
# CLAUDE.md demo-critical note: first-query cold start is ~49s without
# pre-warm (model load, reranker init, CatBoost unpickle, E2B sandbox
# spin + bootstrap pip install). This script fires one representative
# request at each hot path so every subsequent demo query lands warm.
#
# Usage:
#   bash scripts/demo/prewarm.sh [BASE_URL]
#
# Default BASE_URL is http://localhost:8000. For the Cloudflare Tunnel:
#   bash scripts/demo/prewarm.sh https://iai.dissidia.me

set -u
BASE_URL="${1:-http://localhost:8000}"

# Colors (honored in most terminals, skipped when non-tty)
if [ -t 1 ]; then
  C_OK=$'\033[32m'; C_WARN=$'\033[33m'; C_ERR=$'\033[31m'; C_RST=$'\033[0m'
else
  C_OK=""; C_WARN=""; C_ERR=""; C_RST=""
fi

_t0=$(date +%s)

_step() {
  local name="$1"; shift
  local t_start=$(date +%s)
  echo -n "  [${name}] ... "
  local output
  output=$("$@" 2>&1)
  local rc=$?
  local dur=$(( $(date +%s) - t_start ))
  if [ "$rc" -eq 0 ]; then
    echo "${C_OK}ok${C_RST} (${dur}s)"
  else
    echo "${C_ERR}fail${C_RST} (${dur}s)"
    # Show abbreviated output on failure so operator can triage
    echo "${output:0:300}"
  fi
  return $rc
}

echo "== Pre-warming ${BASE_URL} =="

# 1. Health — fastest signal the backend even booted.
_step "health" \
  curl -fsS --max-time 10 "${BASE_URL}/api/v1/health" -o /dev/null

# 2. Environment + documents list — warms DB pool + tenant isolation path.
_step "environment" \
  curl -fsS --max-time 15 "${BASE_URL}/api/v1/environment" -o /dev/null

_step "documents list" \
  curl -fsS --max-time 20 "${BASE_URL}/api/v1/documents" -o /dev/null

# 3. Intent classification — warms Zhipu cloud path + heuristic keyword
#    cache + capability registry.
_step "intent classify (Zhipu)" \
  curl -fsS --max-time 30 -X POST "${BASE_URL}/api/intent/classify" \
    -H "Content-Type: application/json" \
    -d '{"query": "What are the fire safety requirements for 5-storey buildings?"}' \
    -o /dev/null

# 4. RAG query — warms vector index, BM25 index, bge-reranker cross-encoder,
#    and the LLM backend. Slowest single warm-up (~15-30s cold).
_step "RAG query (reranker + LLM)" \
  curl -fsS --max-time 90 -X POST "${BASE_URL}/api/v1/workflow/query" \
    -H "Content-Type: application/json" \
    -d '{"query": "What is the NBC 2020 minimum ceiling height for residential spaces?"}' \
    -o /dev/null

# 5. Cost estimation — warms CatBoost unpickle + SHAP TreeExplainer.
_step "cost estimation (CatBoost + SHAP)" \
  curl -fsS --max-time 30 -X POST "${BASE_URL}/api/v1/cost-estimation/predict" \
    -H "Content-Type: application/json" \
    -d '{
      "project_type": "residential",
      "sqft": 2000,
      "floors": 2,
      "location": "Ontario",
      "contractor_rating": 4.2,
      "num_change_orders": 1,
      "weather_risk_factor": 0.3,
      "material_volatility": 0.2,
      "budget_pressure": 0.5,
      "risk_score": 0.4,
      "confidence_level": 0.90
    }' \
    -o /dev/null

# 6. Data analysis — warms the agentic loop end-to-end: Zhipu GLM-4.7,
#    E2B sandbox spin + BOOTSTRAP_PACKAGES pip install, validator, chart
#    render. This is the longest single warm-up (~15-25s cold).
# Uses a tiny public dataset that always ships with the repo.
_dataset="test_resources/datasets/e2e_public/tips.csv"
if [ -f "$_dataset" ]; then
  _step "data analysis (agentic path)" \
    curl -fsS --max-time 90 -X POST "${BASE_URL}/api/v1/data/analyze" \
      -H "Content-Type: application/json" \
      -d "{\"data_file\": \"${_dataset}\", \"instruction\": \"mean tip by party size\"}" \
      -o /dev/null
else
  echo "  [data analysis (agentic path)] ${C_WARN}skip${C_RST} (no tips.csv found)"
fi

_elapsed=$(( $(date +%s) - _t0 ))
echo "== Done in ${_elapsed}s =="
echo
echo "Smoke check after pre-warm — every subsequent demo query should"
echo "land warm. If any step above failed, fix before showtime."
