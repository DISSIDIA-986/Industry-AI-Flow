# ==========================================
# Industry AI Flow - Makefile
# ==========================================
# Simplifies common development and deployment tasks

.PHONY: help install dev-setup test lint format clean docker-build docker-run docs examples test-comprehensive utilities test-phase1-gate test-kpi-gate test-rollback-rehearsal test-schema-rehearsal test-observability-replay test-release-gate export-prompt-catalog prompt-admin prompt-admin-demo

# Default target
.DEFAULT_GOAL := help

# ==========================================
# Help and Information
# ==========================================
help: ## Show this help message
	@echo "Industry AI Flow - Available Commands:"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-30s\033[0m %s\n", $$1, $$2}'

# ==========================================
# Setup and Installation
# ==========================================
install: ## Install all dependencies
	@echo "📦 Installing dependencies..."
	cd backend && pip install -r requirements.txt

dev-setup: ## Setup development environment
	@echo "🔧 Setting up development environment..."
	cd backend && pip install -r requirements.txt
	pre-commit install || echo "Pre-commit not available, skipping..."

install-dev: ## Install development dependencies only
	@echo "🛠️ Installing development dependencies..."
	cd backend && pip install -r requirements.txt
	pip install black isort flake8 mypy pytest pytest-cov pytest-asyncio

# ==========================================
# Code Quality and Testing
# ==========================================
test: ## Run all tests
	@echo "🧪 Running tests..."
	pytest tests/ -v --cov=backend --cov-report=html --cov-report=term-missing

test-unit: ## Run unit tests only
	@echo "🔬 Running unit tests..."
	pytest tests/unit/ -v

test-integration: ## Run integration tests only
	@echo "🔗 Running integration tests..."
	pytest tests/integration/ -v

test-performance: ## Run performance tests only
	@echo "⚡ Running performance tests..."
	pytest tests/performance/ -v

test-comprehensive: ## Run comprehensive test suite
	@echo "🧪 Running comprehensive test suite..."
	python tests/run_comprehensive_tests.py

test-ocr: ## Run OCR integration tests
	@echo "📷 Running OCR tests..."
	python scripts/testing/test_ocr.py

test-rag: ## Run RAG system tests
	@echo "🔍 Running RAG tests..."
	python scripts/testing/test_rag.py

test-llama: ## Run llama.cpp integration tests
	@echo "🦙 Running llama.cpp tests..."
	python scripts/testing/test_llama_cpp_simple.py

test-phase1-gate: ## Run phase-1 corrected-plan quality gate
	@echo "🛡️ Running phase-1 quality gate..."
	python -m py_compile \
		backend/config.py \
		backend/main.py \
		backend/init_database.py \
		backend/api/enhanced_query_routes.py \
		backend/api/llm_dispatch_routes.py \
		backend/api/llm_cost_routes.py \
		backend/services/llm_integration/llm_client.py \
		backend/services/llm_integration/zhipu_client.py \
		backend/services/llm_integration/types.py \
		backend/services/llm_integration/cost_tracker.py \
		backend/services/llm_integration/dispatch_service.py \
		backend/services/security/redaction_service.py \
		backend/services/security/egress_guard.py \
		backend/observability/llm_metrics.py
	pytest -q \
		tests/unit/test_dispatch_service.py \
		tests/unit/test_redaction_service.py \
		tests/unit/test_llm_api_routes.py \
		tests/unit/test_cost_tracker_budget_logic.py \
		tests/unit/test_llm_config_resolution.py \
	tests/integration/test_week1_fixes.py

test-kpi-gate: ## Run workflow KPI gate (faithfulness/relevancy/p95/cost/safety)
	@echo "📈 Running workflow KPI gate..."
	@PYTHON_BIN=$$(if [ -x venv_test/bin/python ]; then echo venv_test/bin/python; elif command -v python >/dev/null 2>&1; then echo python; else echo python3; fi); \
	$$PYTHON_BIN scripts/testing/build_kpi_payload.py \
		--audit-log tests/evaluation/fixtures/audit_sample.jsonl \
		--evaluation-json tests/evaluation/fixtures/ragas_sample_metrics.json \
		--ab-json tests/evaluation/fixtures/prompt_ab_sample_metrics.json \
		--monthly-cost-cad 360 \
		--output /tmp/kpi_gate_payload.json \
		--pretty; \
	$$PYTHON_BIN scripts/testing/run_kpi_gate.py --input /tmp/kpi_gate_payload.json --pretty; \
	if $$PYTHON_BIN scripts/testing/run_kpi_gate.py --input tests/evaluation/fixtures/kpi_gate_sample_fail.json; then \
		echo "Expected KPI gate failure did not happen"; \
		exit 1; \
	fi; \
	$$PYTHON_BIN -m pytest -q \
		tests/unit/test_kpi_payload_builder.py \
		tests/unit/test_build_kpi_payload_script.py \
		tests/unit/test_workflow_kpi_gate.py \
		tests/unit/test_run_kpi_gate_script.py

test-rollback-rehearsal: ## Run rollback rehearsal checks and unit tests
	@echo "🔁 Running rollback rehearsal..."
	@PYTHON_BIN=$$(if [ -x venv_test/bin/python ]; then echo venv_test/bin/python; elif command -v python >/dev/null 2>&1; then echo python; else echo python3; fi); \
	PROMPT_EXPERIMENTS_ENABLED=false CODE_EXECUTION_PROVIDER=docker \
	$$PYTHON_BIN scripts/testing/run_rollback_rehearsal.py --pretty; \
	$$PYTHON_BIN -m pytest -q tests/unit/test_run_rollback_rehearsal_script.py

test-schema-rehearsal: ## Run prompt schema migration rehearsal checks
	@echo "🧱 Running schema migration rehearsal..."
	@PYTHON_BIN=$$(if [ -x venv_test/bin/python ]; then echo venv_test/bin/python; elif command -v python >/dev/null 2>&1; then echo python; else echo python3; fi); \
	$$PYTHON_BIN scripts/testing/run_schema_migration_rehearsal.py --pretty; \
	$$PYTHON_BIN -m pytest -q tests/unit/test_run_schema_migration_rehearsal_script.py

test-observability-replay: ## Run workflow observability replay gate
	@echo "📊 Running observability replay..."
	@PYTHON_BIN=$$(if [ -x venv_test/bin/python ]; then echo venv_test/bin/python; elif command -v python >/dev/null 2>&1; then echo python; else echo python3; fi); \
	$$PYTHON_BIN scripts/testing/run_observability_replay.py \
		--audit-log tests/evaluation/fixtures/audit_sample.jsonl \
		--evaluation-json tests/evaluation/fixtures/ragas_sample_metrics.json \
		--ab-json tests/evaluation/fixtures/prompt_ab_sample_metrics.json \
		--monthly-cost-cad 360 \
		--min-workflow-events 5 \
		--min-dispatch-events 2 \
		--pretty; \
	if $$PYTHON_BIN scripts/testing/run_observability_replay.py --audit-log tests/evaluation/fixtures/does_not_exist.jsonl --min-workflow-events 1 --min-dispatch-events 1 --monthly-cost-cad 0; then \
		echo "Expected observability replay failure did not happen"; \
		exit 1; \
	fi; \
	$$PYTHON_BIN -m pytest -q tests/unit/test_run_observability_replay_script.py

test-release-gate: ## Run end-to-end release gates (KPI + rollback + schema + replay)
	@$(MAKE) test-kpi-gate
	@$(MAKE) test-rollback-rehearsal
	@$(MAKE) test-schema-rehearsal
	@$(MAKE) test-observability-replay

export-prompt-catalog: ## Export prompt catalog YAML mirrors to research/prompt-catalog
	@PYTHON_BIN=$$(if [ -x venv_test/bin/python ]; then echo venv_test/bin/python; elif command -v python >/dev/null 2>&1; then echo python; else echo python3; fi); \
	$$PYTHON_BIN scripts/migration/export_prompt_catalog.py --clean --pretty

lint: ## Run code linting
	@echo "🔍 Running linting..."
	flake8 backend/ tests/
	mypy backend/

format: ## Format code with black and isort
	@echo "✨ Formatting code..."
	black backend/ tests/ scripts/
	isort backend/ tests/ scripts/

format-check: ## Check code formatting without changing files
	@echo "🔎 Checking code formatting..."
	black --check backend/ tests/ scripts/
	isort --check-only backend/ tests/ scripts/

# ==========================================
# Documentation
# ==========================================
docs: ## Generate documentation
	@echo "📚 Generating documentation..."
	@mkdir -p docs/_build
	@echo "Documentation generation placeholder - add mkdocs or sphinx if needed"

# ==========================================
# Database Operations
# ==========================================
db-init: ## Initialize database with pgvector extension
	@echo "🗄️ Initializing database..."
	scripts/setup/install_pgvector_pg14.sh

db-migrate: ## Run database migrations
	@echo "🔄 Running database migrations..."
	alembic upgrade head

db-setup: ## Complete database setup (init + migrate)
	@echo "🏗️ Setting up database..."
	scripts/setup/install_pgvector_pg14.sh
	alembic upgrade head
	python scripts/migration/seed_intent_prompts.py

# ==========================================
# Docker Operations
# ==========================================
docker-build: ## Build Docker images
	@echo "🐳 Building Docker images..."
	docker build -t industry-ai-flow-backend -f infrastructure/docker/Dockerfile.backend .

docker-run: ## Run Docker containers
	@echo "🚀 Running Docker containers..."
	docker-compose -f infrastructure/docker/docker-compose.yaml up -d

docker-stop: ## Stop Docker containers
	@echo "⏹️ Stopping Docker containers..."
	docker-compose -f infrastructure/docker/docker-compose.yaml down

# ==========================================
# Examples and Utilities
# ==========================================
examples: ## Run example applications
	@echo "📚 Running example applications..."
	@echo "Choose an example to run:"
	@echo "  - rag:     Basic RAG example"
	@echo "  - ocr:     OCR functionality example"
	@echo "Usage: make examples [rag|ocr]"

example-rag: ## Run RAG example
	@echo "🔍 Running RAG example..."
	cd examples/basic_usage && python rag_example.py

example-ocr: ## Run OCR example
	@echo "📷 Running OCR example..."
	cd examples/basic_usage && python ocr_example.py

utilities: ## Show available utility scripts
	@echo "🛠️ Available utility scripts:"
	@echo "  - Import datasets:   python scripts/utilities/import_csv_datasets.py"
	@echo "  - Import documents:  python scripts/utilities/import_docs.py"
	@echo "  - Generate embeddings: python scripts/utilities/generate_test_embeddings.py"
	@echo "  - Compare configs:   python scripts/utilities/compare_configs.py"

import-data: ## Import sample datasets
	@echo "📊 Importing sample datasets..."
	python scripts/utilities/import_csv_datasets.py --input datasets/sample_data.csv

import-docs: ## Import sample documents
	@echo "📄 Importing sample documents..."
	python scripts/utilities/import_docs.py --source datasets/sample_documents/

# ==========================================
# Application Operations
# ==========================================
run: ## Run the application locally
	@echo "🏃 Running application..."
	uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000

run-prod: ## Run application in production mode
	@echo "🏭 Running application in production mode..."
	uvicorn backend.main:app --host 0.0.0.0 --port 8000 --workers 4

streamlit: ## Run Streamlit demo application
	@echo "🎨 Running Streamlit application..."
	streamlit run tools/data-generator/streamlit_app.py

streamlit-prompt: ## Run Streamlit prompt manager
	@echo "📝 Running Streamlit prompt manager..."
	streamlit run tools/prompt-admin/app.py

prompt-admin: ## Run Streamlit prompt-admin (real API management)
	@echo "🧭 Running prompt-admin..."
	streamlit run tools/prompt-admin/app.py

prompt-admin-demo: ## Run prompt-admin demo API checks
	@PYTHON_BIN=$$(if [ -x venv_test/bin/python ]; then echo venv_test/bin/python; elif command -v python >/dev/null 2>&1; then echo python; else echo python3; fi); \
	$$PYTHON_BIN scripts/testing/run_prompt_admin_demo.py --base-url $${PROMPT_API_BASE_URL:-http://localhost:8000} --pretty

# ==========================================
# Testing Intent Classification System
# ==========================================
test-intent: ## Test intent classification system
	@echo "🧠 Testing intent classification system..."
	python tests/intent/test_intent_classification_simple.py

test-intent-full: ## Test full intent classification workflow
	@echo "🔄 Testing full intent classification workflow..."
	python tests/test_intent_classification_system.py

# ==========================================
# Monitoring and Health Checks
# ==========================================
health: ## Check application health
	@echo "💓 Checking application health..."
	curl -f http://localhost:8000/api/intent/health || echo "Application not running"

# ==========================================
# Cleanup Operations
# ==========================================
clean: ## Clean temporary files and artifacts
	@echo "🧹 Cleaning temporary files..."
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	rm -rf .pytest_cache/
	rm -rf htmlcov/
	rm -rf .mypy_cache/
	rm -rf logs/

# ==========================================
# Legacy Commands (for backward compatibility)
# ==========================================
setup: ## Legacy setup command
	@echo "🚀 Using legacy setup..."
	$(MAKE) dev-setup

start: ## Legacy start command
	@echo "▶️ Legacy start command..."
	$(MAKE) run

stop: ## Legacy stop command
	@echo "⏸️ Stopping services..."
	$(MAKE) docker-stop

# ==========================================
# Quick Start Commands
# ==========================================
quick-start: ## Quick start for development
	@echo "🚀 Quick starting development environment..."
	$(MAKE) install-dev
	$(MAKE) db-setup
	$(MAKE) import-docs
	@echo "✅ Development environment ready!"
	@echo "Run 'make run' to start the application"
	@echo "Run 'make example-rag' to try the RAG example"
	@echo "Run 'make example-ocr' to try the OCR example"

quick-test: ## Quick test to verify setup
	@echo "⚡ Quick testing setup..."
	$(MAKE) test-unit
	$(MAKE) test-rag
	$(MAKE) format-check
	@echo "✅ Setup verification complete!"
