# Construction RAG Operation Card (Full Rebuild)

Last updated: 2026-02-19
Use case: major corpus/model/runtime changes that require re-tuning and full verification.

## 1. When To Use

Use this card when:

- seed corpus changed significantly,
- embedding model or retrieval strategy changed,
- baseline quality regressed and requires full recalibration.

## 2. Execute

### Step A: Environment

```bash
source .venv_capstone_arm64/bin/activate
```

### Step B: Re-tune

```bash
python scripts/utilities/tune_construction_rag.py
jq '.best_config' logs/construction_rag_tuning_report.json
```

### Step C: Apply Best Parameters

Update `.env` to best config from tuning report, then run initialization with explicit args:

```bash
python scripts/utilities/init_construction_kb.py \
  --disable-ocr \
  --chunk-size 512 \
  --chunk-overlap 128 \
  --top-k 8
```

Note:

- replace `512/128/8` with the newly tuned winner when it changes.

### Step D: Verify Initialization

```bash
jq '.parameters, .summary' logs/construction_kb_init_report.json
```

### Step E: Full-Stack Validation

```bash
bash scripts/deploy/full_stack_up.sh
python scripts/testing/run_construction_rag_e2e_validation.py
```

## 3. Acceptance Gate

- best config is documented in `logs/construction_rag_tuning_report.json`
- init report parameters match applied config
- skip policy for ultra-large files is respected
- smoke summary: `pass=9 fail=0`
- e2e report `acceptance.overall_pass == true`

## 4. Outputs

- `logs/construction_rag_tuning_report.json`
- `logs/construction_kb_init_report.json`
- `logs/construction_rag_e2e_validation_report.json`
- `logs/backend.log`
- `logs/frontend.log`
