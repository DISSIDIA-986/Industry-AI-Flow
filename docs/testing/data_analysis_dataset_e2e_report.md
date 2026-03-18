# Data Analysis Dataset E2E Report

**Generated**: 2026-03-18 04:36 UTC
**Backend**: http://127.0.0.1:8000

## Summary

| Metric | Value |
|--------|-------|
| Total test cases | 11 |
| PASS | 11 |
| FAIL | 0 |
| TIMEOUT | 0 |
| ERROR/NOT_RUN | 0 |
| **Pass rate** | **100%** |
| Threshold (≥83%) | YES |

## Detailed Results

| Case | Dataset | Status | Mode | Viz | Privacy | Time | Error |
|------|---------|--------|------|-----|---------|------|-------|
| TC1-P1 | tips | PASS | llm | no | ok | 7.2s |  |
| TC1-P2 | tips | PASS | llm | no | ok | 9.3s |  |
| TC1-P3 | tips | PASS | llm | no | ok | 7.3s |  |
| TC2-P1 | titanic | PASS | template_fallback | no | ok | 13.2s |  |
| TC2-P2 | titanic | PASS | template_fallback | no | ok | 13.2s |  |
| TC3-P1 | penguins | PASS | llm | no | ok | 12.8s |  |
| TC3-P2 | penguins | PASS | llm | no | ok | 10.6s |  |
| TC4-P1 | mpg | PASS | template_fallback_runtime | no | ok | 13.7s |  |
| TC4-P2 | mpg | PASS | llm | no | ok | 10.1s |  |
| TC5-P1 | airline | PASS | template_fallback_runtime | no | ok | 9.4s |  |
| TC5-P2 | airline | PASS | llm | no | ok | 7.1s |  |
## Triage Guide

| Symptom | Likely Cause | Action |
|---------|-------------|--------|
| mode=template_fallback | Cloud LLM unreachable/failed | Check API keys, network |
| TIMEOUT | Docker execution >30s | Check Docker health, simplify prompt |
| Code validator rejection | Generated code uses banned imports | Review validator allowlist |
| No visualization | LLM didn't generate plot code | Adjust prompt wording |
| NaN/missing data crash | Dataset has nulls | Ensure code handles `dropna()` |
