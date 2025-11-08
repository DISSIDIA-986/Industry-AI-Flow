# ==========================================
# Industry AI Flow - Makefile
# ==========================================
# Simplifies common development and deployment tasks

.PHONY: help install dev-setup test lint format clean docker-build docker-run docs

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
	pip install -r requirements.txt

dev-setup: ## Setup development environment
	@echo "🔧 Setting up development environment..."
	pip install -r requirements.txt
	pre-commit install || echo "Pre-commit not available, skipping..."

install-dev: ## Install development dependencies only
	@echo "🛠️ Installing development dependencies..."
	pip install -r requirements.txt
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
	streamlit run tools/data-generator/streamlit_prompt_manager.py

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
	@echo "✅ Development environment ready!"
	@echo "Run 'make run' to start the application"

quick-test: ## Quick test to verify setup
	@echo "⚡ Quick testing setup..."
	$(MAKE) test-intent
	$(MAKE) format-check
	@echo "✅ Setup verification complete!"
