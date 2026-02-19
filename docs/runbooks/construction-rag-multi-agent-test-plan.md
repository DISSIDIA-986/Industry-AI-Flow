# Construction RAG Multi-Agent Test Plan

Last updated: 2026-02-19
Scope: construction-domain RAG full workflow validation (ingest -> retrieval -> workflow API).

## 1. Objective

Build a cross-functional, executable test plan that verifies:

- document ingestion and preprocessing stability,
- embedding + PGVector write integrity,
- retrieval quality across semantic/hybrid/keyword modes,
- end-to-end workflow path availability and response validity.

## 2. Team Roles And Decision Responsibilities

### AI Architect

- own retrieval strategy and thresholds,
- review embedding model behavior and semantic recall risks,
- approve changes to retrieval weighting/chunking strategy.

### Project Architect

- own runtime topology and dependency readiness,
- review database/index health and service-level constraints,
- approve deployment/smoke gate and rollback policy.

### Senior QA

- own test matrix completeness and acceptance criteria,
- drive E2E/automation execution and defect classification,
- approve release readiness based on objective evidence.

### Software Engineers

- implement and maintain validation scripts,
- fix failures, regressions, and flaky checks,
- keep test artifacts reproducible in CI/local.

## 3. Test Dimensions

### D1. Data Pipeline Validation

- seed corpus presence and file policy (including intentional large-file skip),
- ingestion report integrity,
- chunk count and replacement behavior.

### D2. Vector Store Validation

- pgvector extension availability,
- stored embedding dimension consistency,
- expected construction docs present in `documents` table.

### D3. Retrieval Validation

- semantic-only retrieval (`vector similarity`),
- hybrid retrieval (`vector + BM25`),
- keyword retrieval (`BM25-only` via hybrid with `vector_weight=0`).

### D4. Workflow E2E Validation

- `/api/v1/workflow/health` accessibility,
- `/api/v1/workflow/query` execution success,
- non-empty response payload and traceability metadata.

## 4. Automation Assets

- Ingestion script:
  - `scripts/utilities/init_construction_kb.py`
- E2E validation script:
  - `scripts/testing/run_construction_rag_e2e_validation.py`
- Reports:
  - `logs/construction_kb_init_report.json`
  - `logs/construction_rag_e2e_validation_report.json`

## 5. Standard Execution

```bash
source .venv_capstone_arm64/bin/activate
python scripts/utilities/init_construction_kb.py \
  --disable-ocr \
  --chunk-size 512 \
  --chunk-overlap 128 \
  --top-k 8
python scripts/testing/run_construction_rag_e2e_validation.py
```

## 6. Acceptance Gates

### Gate A: Ingestion And Vector Store

- `ingested_files == 9`
- `skipped_files == 3`
- `chunk_size == 512`
- `chunk_overlap == 128`
- `top_k == 8`
- `has_pgvector == true`
- `vector_dim_sample == 768`

### Gate B: Retrieval Quality

- semantic pass rate >= 0.50
- hybrid pass rate >= 0.75
- keyword pass rate >= 0.75

### Gate C: Workflow E2E

- workflow health check passes,
- workflow query pass count equals query total.

### Gate D: Overall

- `acceptance.overall_pass == true`

## 7. Review And Escalation Loop

When any gate fails:

1. QA files issue with report links and failed gate IDs.
2. Software engineer proposes fix and reruns automation.
3. AI architect validates retrieval-related changes.
4. Project architect signs off runtime/deploy impact.
5. QA closes gate only after re-run evidence is attached.

