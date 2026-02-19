# Construction RAG KB Initialization Runbook

Last updated: 2026-02-19
Owner: QA + AI Engineering

## 1. Scope And Goal

This runbook standardizes the end-to-end workflow for:

- selecting representative construction-domain seed documents,
- initializing the RAG knowledge base,
- tuning retrieval parameters,
- validating service stability and retrieval quality.

Current phase focus:

- use regular-size documents to validate full pipeline feasibility and stability,
- temporarily skip ultra-large documents,
- keep solution executable and low-complexity.

## 2. Decision Template (Required)

Use this lightweight template for every technical decision:

### 2.1 Goal Alignment

- Is the decision directly serving KB quality, retrieval accuracy, or system stability?
- Does it match current project constraints (time, compute, maintainability)?

### 2.2 Feasibility Check

- Are dependencies available in current environment?
- Is the path reproducible via scripts and logs?
- Can outputs be objectively verified?

### 2.3 Path Refinement

- Define concrete commands.
- Define acceptance criteria.
- Define rollback/fallback if the command fails.

## 3. Baseline Inputs

### 3.1 Seed Document Set

Use `test_resources/documents/construction_seed_2026q1/`.

Current operating policy:

- ingest normal-size files,
- skip the following ultra-large files in this phase:
  - `caltrans_2025_standard_plans_locked.pdf`
  - `caltrans_2025_standard_specifications.pdf`
  - `ufgs_complete.pdf`

### 3.2 Runtime Baseline

- Python: `3.13.x`
- DB: PostgreSQL + `pgvector`
- LLM serving: Ollama (`qwen2.5:7b`)
- Embedding model: `nomic-ai/nomic-embed-text-v1.5`

## 4. Recommended Parameters (Validated)

From `/logs/construction_rag_tuning_report.json`:

- `chunk_size=512`
- `chunk_overlap=128`
- `top_k=8`
- `vector_weight=0.7`
- `bm25_weight=0.3`

## 5. Standard Execution Flow

Quick path selection:

- Daily/regular updates: `docs/runbooks/construction-rag-opcard-incremental.md`
- Major changes/full recalibration: `docs/runbooks/construction-rag-opcard-full-rebuild.md`

### Step 0: Activate Environment

```bash
source .venv_capstone_arm64/bin/activate
```

### Step 1: Tune Retrieval (if new corpus or major model change)

```bash
python scripts/utilities/tune_construction_rag.py
```

Output:

- `/logs/construction_rag_tuning_report.json`

### Step 2: Apply/Confirm Runtime Config

Ensure `.env` includes:

```dotenv
EMBEDDING_MODEL=nomic-ai/nomic-embed-text-v1.5
EMBEDDING_DIM=768
CHUNK_SIZE=512
CHUNK_OVERLAP=128
TOP_K=8
LLM_BACKEND=ollama
LLM_PROVIDER=ollama
LOCAL_PRIMARY_BACKEND=ollama
HYBRID_MODE=local_only
```

### Step 3: Initialize Construction KB

Use explicit args to avoid shell env mismatch:

```bash
python scripts/utilities/init_construction_kb.py \
  --disable-ocr \
  --chunk-size 512 \
  --chunk-overlap 128 \
  --top-k 8
```

Output:

- `/logs/construction_kb_init_report.json`

### Step 4: Verify Init Result

```bash
jq '.parameters, .summary' logs/construction_kb_init_report.json
```

Acceptance:

- `parameters.chunk_size == 512`
- `parameters.chunk_overlap == 128`
- `parameters.retrieval_recommendation.top_k == 8`
- `summary.ingested_files == 9`
- `summary.skipped_files == 3`

### Step 5: Full-Stack Smoke

```bash
bash scripts/deploy/full_stack_up.sh
```

Acceptance:

- smoke summary: `pass=9 fail=0`
- backend health/workflow/cost endpoints are all healthy
- frontend proxy and rewrite checks pass

### Step 5B: Automated RAG E2E Validation

```bash
python scripts/testing/run_construction_rag_e2e_validation.py
```

Acceptance:

- `logs/construction_rag_e2e_validation_report.json` generated
- `acceptance.overall_pass == true`

### Step 6: Optional Stop

```bash
bash scripts/deploy/full_stack_down.sh
```

## 6. Artifacts To Preserve

- `/logs/construction_rag_tuning_report.json`
- `/logs/construction_kb_init_report.json`
- `/logs/backend.log`
- `/logs/frontend.log`

## 7. Known Issues And Handling

### 7.1 `llama_cpp` Warning

Symptom:

- logs show `llama-cpp-python` not installed, then fallback to Ollama.

Handling:

- acceptable for current baseline (Ollama path is supported),
- only install/configure `llama-cpp-python` if project explicitly switches to that backend.

### 7.2 Slow DB Query Warnings During Ingestion

Symptom:

- occasional `Slow DB query (store_document)` warning during large file ingestion.

Handling:

- non-blocking if final ingestion and smoke pass,
- monitor trend; optimize indexing/write strategy only if latency grows or ingestion fails.

## 8. QA Handover Checklist

- [ ] tuning report generated and archived
- [ ] `.env` matches validated parameter set
- [ ] KB init report shows expected parameter values
- [ ] expected docs ingested and large docs skipped by policy
- [ ] full-stack smoke passes with zero failures
- [ ] logs archived for traceability
