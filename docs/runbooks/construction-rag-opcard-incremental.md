# Construction RAG Operation Card (Incremental Update)

Last updated: 2026-02-19
Use case: routine KB updates with stable model/parameter baseline.

## 1. When To Use

Use this card when:

- only a small batch of regular-size documents is updated,
- embedding model and retrieval strategy remain unchanged,
- you need fast, low-risk refresh and validation.

Do not use this card for major corpus/model changes. Use full rebuild card instead.

## 2. Fixed Baseline

- `EMBEDDING_MODEL=nomic-ai/nomic-embed-text-v1.5`
- `CHUNK_SIZE=512`
- `CHUNK_OVERLAP=128`
- `TOP_K=8`
- `vector_weight=0.7`
- `bm25_weight=0.3`

## 3. Execute

```bash
source .venv_capstone_arm64/bin/activate
python scripts/utilities/init_construction_kb.py \
  --disable-ocr \
  --chunk-size 512 \
  --chunk-overlap 128 \
  --top-k 8
jq '.parameters, .summary' logs/construction_kb_init_report.json
bash scripts/deploy/full_stack_up.sh
python scripts/testing/run_construction_rag_e2e_validation.py
```

## 4. Acceptance Gate

- init report:
  - `chunk_size == 512`
  - `chunk_overlap == 128`
  - `top_k == 8`
- ingest report is complete with expected skip policy
- smoke summary: `pass=9 fail=0`
- e2e report `acceptance.overall_pass == true`

## 5. Outputs

- `logs/construction_kb_init_report.json`
- `logs/backend.log`
- `logs/frontend.log`
