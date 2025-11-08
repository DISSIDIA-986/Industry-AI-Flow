# Utility Scripts

This directory contains general utility scripts for data management, configuration, and maintenance tasks.

## Available Scripts

### `compare_configs.py`
Compares configuration files to identify differences and validate settings.

**Usage:**
```bash
python scripts/utilities/compare_configs.py [config1] [config2]
```

### `generate_test_embeddings.py`
Generates test embeddings for vector database testing and development.

**Usage:**
```bash
python scripts/utilities/generate_test_embeddings.py --output test_embeddings.json
```

### `import_csv_datasets.py`
Imports CSV datasets into the system for testing and demonstration purposes.

**Usage:**
```bash
python scripts/utilities/import_csv_datasets.py --input data.csv --collection-name test_data
```

### `import_docs.py`
Imports document files into the knowledge base for RAG functionality.

**Usage:**
```bash
python scripts/utilities/import_docs.py --source docs/ --target-collection knowledge_base
```

## Dependencies

- Python 3.8+
- Project dependencies installed (`pip install -r backend/requirements.txt`)
- Access to backend services for database operations

## Configuration

Most scripts use environment variables for configuration:

```bash
export DATABASE_URL="postgresql://user:pass@localhost/db"
export EMBEDDING_MODEL="sentence-transformers/all-MiniLM-L6-v2"
```

## Data Formats

- **CSV**: Standard CSV format with headers
- **Documents**: Markdown, TXT, PDF files supported
- **Configurations**: JSON, YAML, TOML formats supported
