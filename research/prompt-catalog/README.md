# Prompt Catalog Mirror

This directory stores read-only YAML mirrors exported from the prompts database.

## Generate/refresh

```bash
make export-prompt-catalog
```

## Files

- `_index.yaml`: export metadata and file index.
- `*.yaml`: one file per prompt version (`{category}__{name}__v{version}.yaml`).
