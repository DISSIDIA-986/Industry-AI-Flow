# Prompt Admin

Real API Streamlit admin for prompt CRUD, A/B experiments, and usage metrics.

## Run

```bash
export PROMPT_API_BASE_URL=http://localhost:8000
streamlit run tools/prompt-admin/app.py
```

Optional:

```bash
export PROMPT_API_KEY=your_api_key
```

## Pages

- `Prompt List`: query and inspect prompts.
- `Prompt Editor`: create/update prompt records.
- `Prompt Test`: run `/api/prompts/{id}/test` render checks.
- `Experiments`: create experiments and apply ramp traffic (`10% -> 30% -> 50%`).
- `Metrics`: read `/api/prompts/metrics/summary`.

## Demo Script

```bash
python scripts/testing/run_prompt_admin_demo.py --base-url http://localhost:8000 --execute-experiment
```
