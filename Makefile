# ==========================================
# Industry AI Flow - Makefile
# ==========================================
# Simplifies common development and deployment tasks

.PHONY: help install dev-setup test lint format clean docker-build docker-run docs examples test-comprehensive utilities test-phase1-gate test-kpi-gate test-rollback-rehearsal test-schema-rehearsal test-observability-replay test-legacy-regression test-cost-estimation-gate test-demo-mode-gate test-demo-smoke test-demo-smoke-gate test-demo-smoke-live-gate test-data-analysis-gate test-prompt-baseline-gate test-language-compliance test-release-gate export-prompt-catalog prompt-admin prompt-admin-demo frontend-install frontend-dev frontend-build frontend-lint test-frontend-layout-nav-gate capstone-env-setup capstone-env-check fullstack-up fullstack-down fullstack-smoke test-construction-rag-e2e rebuild-construction-kb test-construction-rag-full check-structure

# Default target
.DEFAULT_GOAL := help
PYTHON_BIN ?= $(shell if [ -x .venv_capstone/bin/python ]; then echo .venv_capstone/bin/python; elif [ -x venv_test/bin/python ]; then echo venv_test/bin/python; elif command -v python3.13 >/dev/null 2>&1; then echo python3.13; elif command -v python >/dev/null 2>&1; then echo python; else echo python3; fi)
PYTHON_BIN_ARM64 ?= $(shell if [ -x .venv_capstone_arm64/bin/python ]; then echo .venv_capstone_arm64/bin/python; elif [ -x .venv_capstone/bin/python ]; then echo .venv_capstone/bin/python; elif [ -x venv_test/bin/python ]; then echo venv_test/bin/python; elif command -v python3.13 >/dev/null 2>&1; then echo python3.13; elif command -v python >/dev/null 2>&1; then echo python; else echo python3; fi)

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
	$(PYTHON_BIN) -m pip install -r requirements/base.txt

dev-setup: ## Setup development environment
	@echo "🔧 Setting up development environment..."
	$(PYTHON_BIN) -m pip install -r requirements/dev.txt
	pre-commit install || echo "Pre-commit not available, skipping..."

install-dev: ## Install development dependencies only
	@echo "🛠️ Installing development dependencies..."
	$(PYTHON_BIN) -m pip install -r requirements/dev.txt

# ==========================================
# Code Quality and Testing
# ==========================================
test: ## Run all tests
	@echo "🧪 Running tests..."
	$(PYTHON_BIN) -m pytest tests/ -v --cov=backend --cov-report=html --cov-report=term-missing

test-unit: ## Run unit tests only
	@echo "🔬 Running unit tests..."
	$(PYTHON_BIN) -m pytest tests/unit/ -v

test-integration: ## Run integration tests only
	@echo "🔗 Running integration tests..."
	$(PYTHON_BIN) -m pytest tests/integration/ -v

test-performance: ## Run performance tests only
	@echo "⚡ Running performance tests..."
	$(PYTHON_BIN) -m pytest tests/performance/ -v

test-comprehensive: ## Run comprehensive test suite
	@echo "🧪 Running comprehensive test suite..."
	$(PYTHON_BIN) tests/run_comprehensive_tests.py

test-ocr: ## Run OCR integration tests
	@echo "📷 Running OCR tests..."
	$(PYTHON_BIN) scripts/testing/test_ocr.py

test-rag: ## Run RAG system tests
	@echo "🔍 Running RAG tests..."
	$(PYTHON_BIN) scripts/testing/test_rag.py

test-llama: ## Run llama.cpp integration tests
	@echo "🦙 Running llama.cpp tests..."
	$(PYTHON_BIN) scripts/testing/test_llama_cpp_simple.py

test-phase1-gate: ## Run phase-1 corrected-plan quality gate
	@echo "🛡️ Running phase-1 quality gate..."
	$(PYTHON_BIN) -m py_compile \
		backend/config.py \
		backend/main.py \
		backend/init_database.py \
		backend/api/enhanced_query_routes.py \
		backend/api/llm_dispatch_routes.py \
		backend/api/llm_cost_routes.py \
		backend/api/cost_estimation_routes.py \
		backend/services/llm_integration/llm_client.py \
		backend/services/llm_integration/zhipu_client.py \
		backend/services/llm_integration/types.py \
		backend/services/llm_integration/cost_tracker.py \
		backend/services/llm_integration/dispatch_service.py \
		backend/services/cost_estimation_service.py \
		backend/services/security/redaction_service.py \
		backend/services/security/egress_guard.py \
		backend/services/workflows/nodes/cost_estimation_node.py \
		backend/observability/llm_metrics.py
	$(PYTHON_BIN) -m pytest -q \
		tests/unit/test_dispatch_service.py \
		tests/unit/test_redaction_service.py \
		tests/unit/test_llm_api_routes.py \
		tests/unit/test_cost_tracker_budget_logic.py \
		tests/unit/test_llm_config_resolution.py \
		tests/unit/test_cost_estimation_service.py \
		tests/unit/test_cost_estimation_workflow_intent.py \
		tests/unit/test_workflow_orchestrator_pipeline.py \
		tests/unit/test_main_cost_estimation_router_mount_contract.py \
		tests/integration/test_cost_estimation_api.py \
		tests/integration/test_workflow_cost_estimation_query_api.py \
		tests/integration/test_week1_fixes.py

test-cost-estimation-gate: ## Run cost-estimation API/workflow gate
	@echo "💰 Running cost-estimation gate..."
	$(PYTHON_BIN) -m py_compile \
		backend/api/cost_estimation_routes.py \
		backend/services/cost_estimation_service.py \
		backend/services/workflows/nodes/cost_estimation_node.py
	$(PYTHON_BIN) -m pytest -q \
		tests/integration/test_cost_estimation_api.py \
		tests/integration/test_workflow_cost_estimation_query_api.py \
		tests/unit/test_cost_estimation_service.py \
		tests/unit/test_cost_estimation_workflow_intent.py \
		tests/unit/test_workflow_intent_node.py \
		tests/unit/test_workflow_orchestrator_pipeline.py \
		tests/unit/test_main_cost_estimation_router_mount_contract.py

test-demo-mode-gate: ## Run demo-mode workflow/dispatch gate
	@echo "🎬 Running demo-mode gate..."
	$(PYTHON_BIN) -m py_compile \
		backend/config.py \
		backend/api/demo_mode_routes.py \
		backend/services/demo_mode_service.py \
		backend/api/workflow_query_routes.py \
		backend/api/llm_dispatch_routes.py \
		backend/services/llm_integration/dispatch_service.py
	$(PYTHON_BIN) -m pytest -q \
		tests/unit/test_demo_mode_service.py \
		tests/integration/test_demo_mode_api.py \
		tests/unit/test_workflow_query_routes.py \
		tests/unit/test_intent_workflow_dispatch_runtime.py \
		tests/unit/test_langchain_compat_gateway.py \
		tests/unit/test_dispatch_service.py \
		tests/unit/test_llm_config_resolution.py \
		tests/unit/test_main_api_version_alias_routes.py \
		tests/unit/test_main_demo_mode_router_mount_contract.py

test-demo-smoke: ## Run capstone demo smoke preflight + API sanity checks
	@echo "🔥 Running capstone demo smoke..."
	$(PYTHON_BIN) scripts/testing/run_demo_smoke.py --pretty --train-model-if-missing $${DEMO_SMOKE_ARGS:-}

test-demo-smoke-gate: ## Run CI-friendly demo smoke gate (skip external Postgres/Ollama)
	@echo "🧪 Running demo smoke gate (CI-friendly)..."
	$(PYTHON_BIN) scripts/testing/run_demo_smoke.py \
		--pretty \
		--train-model-if-missing \
		--skip-postgres-check \
		--skip-ollama-check \
		--dataset-path datasets/unified_construction_projects_enhanced.csv \
		--model-path /tmp/industry_ai_flow_smoke_model.json

test-demo-smoke-live-gate: ## Run local live demo smoke gate (requires Postgres/Ollama)
	@echo "🚦 Running demo smoke gate (live external dependencies)..."
	$(PYTHON_BIN) scripts/testing/run_demo_smoke.py \
		--pretty \
		--train-model-if-missing \
		--dataset-path datasets/unified_construction_projects_enhanced.csv \
		--model-path /tmp/industry_ai_flow_smoke_model.json \
		$${DEMO_SMOKE_LIVE_ARGS:-}

test-kpi-gate: ## Run workflow KPI gate (faithfulness/relevancy/p95/cost/safety)
	@echo "📈 Running workflow KPI gate..."
	$(PYTHON_BIN) scripts/testing/build_kpi_payload.py \
		--audit-log tests/evaluation/fixtures/audit_sample.jsonl \
		--evaluation-json tests/evaluation/fixtures/ragas_sample_metrics.json \
		--ab-json tests/evaluation/fixtures/prompt_ab_sample_metrics.json \
		--monthly-cost-cad 360 \
		--output /tmp/kpi_gate_payload.json \
		--pretty
	$(PYTHON_BIN) scripts/testing/run_kpi_gate.py --input /tmp/kpi_gate_payload.json --pretty
	if $(PYTHON_BIN) scripts/testing/run_kpi_gate.py --input tests/evaluation/fixtures/kpi_gate_sample_fail.json; then \
		echo "Expected KPI gate failure did not happen"; \
		exit 1; \
	fi
	$(PYTHON_BIN) -m pytest -q \
		tests/unit/test_kpi_payload_builder.py \
		tests/unit/test_build_kpi_payload_script.py \
		tests/unit/test_workflow_kpi_gate.py \
		tests/unit/test_run_kpi_gate_script.py

test-rollback-rehearsal: ## Run rollback rehearsal checks and unit tests
	@echo "🔁 Running rollback rehearsal..."
	PROMPT_EXPERIMENTS_ENABLED=false CODE_EXECUTION_PROVIDER=docker \
	$(PYTHON_BIN) scripts/testing/run_rollback_rehearsal.py --pretty
	$(PYTHON_BIN) -m pytest -q tests/unit/test_run_rollback_rehearsal_script.py

test-schema-rehearsal: ## Run prompt schema migration rehearsal checks
	@echo "🧱 Running schema migration rehearsal..."
	$(PYTHON_BIN) scripts/testing/run_schema_migration_rehearsal.py --pretty
	$(PYTHON_BIN) -m pytest -q tests/unit/test_run_schema_migration_rehearsal_script.py

test-observability-replay: ## Run workflow observability replay gate
	@echo "📊 Running observability replay..."
	$(PYTHON_BIN) scripts/testing/run_observability_replay.py \
		--audit-log tests/evaluation/fixtures/audit_sample.jsonl \
		--evaluation-json tests/evaluation/fixtures/ragas_sample_metrics.json \
		--ab-json tests/evaluation/fixtures/prompt_ab_sample_metrics.json \
		--monthly-cost-cad 360 \
		--min-workflow-events 5 \
		--min-dispatch-events 2 \
		--pretty
	if $(PYTHON_BIN) scripts/testing/run_observability_replay.py --audit-log tests/evaluation/fixtures/does_not_exist.jsonl --min-workflow-events 1 --min-dispatch-events 1 --monthly-cost-cad 0; then \
		echo "Expected observability replay failure did not happen"; \
		exit 1; \
	fi
	$(PYTHON_BIN) -m pytest -q tests/unit/test_run_observability_replay_script.py

test-legacy-regression: ## Run legacy /api/v1/query and /query/dispatch regression
	@echo "🧪 Running legacy API regression..."
	$(PYTHON_BIN) -m pytest -q tests/unit/test_llm_api_routes.py

test-construction-rag-e2e: ## Run construction RAG end-to-end validation report
	@echo "🏗️ Running construction RAG E2E validation..."
	$(PYTHON_BIN_ARM64) scripts/testing/run_construction_rag_e2e_validation.py

rebuild-construction-kb: ## Rebuild construction KB with tuned parameters (512/128/top_k=8)
	@echo "📚 Rebuilding construction KB (chunk=512 overlap=128 top_k=8)..."
	$(PYTHON_BIN_ARM64) scripts/utilities/init_construction_kb.py \
		--disable-ocr \
		--chunk-size 512 \
		--chunk-overlap 128 \
		--top-k 8

test-construction-rag-full: ## Rebuild KB then run construction RAG E2E validation
	@$(MAKE) rebuild-construction-kb
	@$(MAKE) test-construction-rag-e2e

test-prompt-baseline-gate: ## Verify workflow prompt baseline exists and is active/latest
	@echo "🧩 Running prompt baseline gate..."
	$(PYTHON_BIN) scripts/migration/seed_prompt_baseline.py --verify-only --pretty

test-data-analysis-gate: ## Run data-analysis runtime/contract gate
	@echo "📊 Running data-analysis gate..."
	set -e; \
	$(PYTHON_BIN) -m py_compile \
		backend/main.py \
		backend/tools/data_analysis.py \
		backend/services/data_analysis/data_analysis_agent.py \
		backend/agents/langchain_compat.py \
		backend/agents/unified_agent.py; \
	$(PYTHON_BIN) scripts/migration/seed_prompt_baseline.py --verify-only; \
	$(PYTHON_BIN) -m pytest -q \
			tests/unit/test_main_runtime_contracts.py \
			tests/unit/test_docker_provider_health.py \
			tests/unit/test_data_analysis_agent_provider_mode.py \
			tests/unit/test_intent_workflow_dispatch_runtime.py \
			tests/unit/test_langchain_compat_gateway.py \
			tests/unit/test_data_analysis.py \
			tests/unit/test_no_absolute_paths_in_tests.py \
			tests/integration/test_data_analysis_runtime_gate.py

test-language-compliance: ## Enforce runtime English-only policy for frontend/backend
	@echo "🌐 Running runtime language compliance gate..."
	$(PYTHON_BIN) scripts/testing/check_runtime_english_compliance.py

test-release-gate: ## Run end-to-end release gates (KPI + rollback + schema + replay + legacy)
	@$(MAKE) test-language-compliance
	@$(MAKE) test-prompt-baseline-gate
	@$(MAKE) test-cost-estimation-gate
	@$(MAKE) test-demo-mode-gate
	@$(MAKE) test-data-analysis-gate
	@$(MAKE) test-demo-smoke-gate
	@$(MAKE) test-kpi-gate
	@$(MAKE) test-rollback-rehearsal
	@$(MAKE) test-schema-rehearsal
	@$(MAKE) test-observability-replay
	@$(MAKE) test-legacy-regression

export-prompt-catalog: ## Export prompt catalog YAML mirrors to research/prompt-catalog
	$(PYTHON_BIN) scripts/migration/export_prompt_catalog.py --clean --pretty

lint: ## Run code linting
	@echo "🔍 Running linting..."
	$(PYTHON_BIN) -m flake8 backend/ tests/
	$(PYTHON_BIN) -m mypy backend/

check-structure: ## Validate repository structure hygiene
	@bash scripts/testing/check_project_structure.sh

format: ## Format code with black and isort
	@echo "✨ Formatting code..."
	$(PYTHON_BIN) -m black backend/ tests/ scripts/
	$(PYTHON_BIN) -m isort backend/ tests/ scripts/

format-check: ## Check code formatting without changing files
	@echo "🔎 Checking code formatting..."
	$(PYTHON_BIN) -m black --check backend/ tests/ scripts/
	$(PYTHON_BIN) -m isort --check-only backend/ tests/ scripts/

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
	@scripts/setup/install_pgvector_pg14.sh
	@alembic upgrade head
	$(PYTHON_BIN) scripts/migration/seed_prompt_baseline.py --pretty

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
	cd docs/examples && $(PYTHON_BIN) demo_version_solution.py

example-ocr: ## Run OCR example
	@echo "📷 Running OCR example..."
	cd docs/examples && $(PYTHON_BIN) demo_python313_paddleocr_solution.py

utilities: ## Show available utility scripts
	@echo "🛠️ Available utility scripts:"
	@echo "  - Import datasets:   python scripts/utilities/import_csv_datasets.py"
	@echo "  - Import documents:  python scripts/utilities/import_docs.py"
	@echo "  - Generate embeddings: python scripts/utilities/generate_test_embeddings.py"
	@echo "  - Compare configs:   python scripts/utilities/compare_configs.py"

import-data: ## Import sample datasets
	@echo "📊 Importing sample datasets..."
	$(PYTHON_BIN) scripts/utilities/import_csv_datasets.py --input datasets/sample_data.csv

import-docs: ## Import sample documents
	@echo "📄 Importing sample documents..."
	$(PYTHON_BIN) scripts/utilities/import_docs.py --source datasets/sample_documents/

# ==========================================
# Application Operations
# ==========================================
run: ## Run the application locally
	@echo "🏃 Running application..."
	uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000

fullstack-up: ## Start full local stack and run full-stack smoke
	@echo "🚀 Starting full local stack..."
	bash scripts/deploy/full_stack_up.sh

fullstack-down: ## Stop local backend/frontend started by fullstack-up
	@echo "🛑 Stopping full local stack..."
	bash scripts/deploy/full_stack_down.sh

fullstack-smoke: ## Run full-stack connectivity smoke checks
	@echo "🧪 Running full-stack smoke..."
	bash scripts/testing/run_full_stack_smoke.sh

capstone-env-check: ## Check Capstone Python/dependency baseline (advisory by default)
	@echo "🧭 Checking Capstone environment..."
	$(PYTHON_BIN) scripts/setup/check_capstone_env.py --lock requirements/lock/py313-capstone.txt

capstone-env-setup: ## Create Python 3.13 venv and install locked Capstone dependencies
	@echo "🏗️ Setting up Capstone environment..."
	bash scripts/setup/setup_capstone_env.sh

frontend-install: ## Install frontend dependencies
	@echo "🧩 Installing frontend dependencies..."
	cd frontend && npm install

frontend-dev: ## Run Next.js frontend locally
	@echo "🎨 Running Next.js frontend..."
	cd frontend && npm run dev

frontend-lint: ## Run frontend lint checks
	@echo "🧪 Running frontend lint..."
	cd frontend && npm run lint

frontend-build: ## Build frontend for production
	@echo "🏗️ Building frontend..."
	cd frontend && npm run build

test-frontend-layout-nav-gate: ## Run frontend Playwright layout/navbar regression gate (mock + live API)
	@echo "🧭 Running frontend layout/navbar regression gate..."
	bash scripts/testing/run_frontend_layout_nav_gate.sh

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
	$(PYTHON_BIN) scripts/testing/run_prompt_admin_demo.py --base-url $${PROMPT_API_BASE_URL:-http://localhost:8000} --pretty

# ==========================================
# Testing Intent Classification System
# ==========================================
test-intent: ## Test intent classification system
	@echo "🧠 Testing intent classification system..."
	$(PYTHON_BIN) tests/intent/test_intent_classification_simple.py

test-intent-full: ## Test full intent classification workflow
	@echo "🔄 Testing full intent classification workflow..."
	$(PYTHON_BIN) tests/test_intent_classification_system.py

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
