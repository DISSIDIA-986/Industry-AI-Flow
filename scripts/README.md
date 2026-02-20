# Scripts Directory

This directory contains various utility and operational scripts for the Industry AI Flow project.

## Directory Structure

### [`deployment/`](./deployment/)
Deployment-related scripts for Docker and production environments.

### [`deploy/`](./deploy/)
Operational deployment scripts for full-stack startup/shutdown and health checks.

### [`migration/`](./migration/)
Database migration and data transformation scripts.

### [`monitoring/`](./monitoring/)
System monitoring and performance tracking scripts.

### [`setup/`](./setup/)
Environment setup and installation scripts.

### [`testing/`](./testing/)
Test scripts and validation utilities.

### [`utilities/`](./utilities/)
General utility scripts for data import, configuration, and maintenance.

### [`versioning/`](./versioning/)
Python version compatibility checkers and environment diagnosis utilities.

## Usage

Most scripts can be run from the project root directory:

```bash
# Run setup script
./scripts/setup/setup_local.sh

# Run migration script
python scripts/migration/migrate_to_pgvector.sh

# Run utility script
python scripts/utilities/import_docs.py

# Run version compatibility check
python scripts/versioning/version_manager.py --check-deps paddleocr

# Run repository structure hygiene check
bash scripts/testing/check_project_structure.sh
```

## Permissions

Make sure shell scripts have execute permissions:

```bash
chmod +x scripts/**/*.sh
```
