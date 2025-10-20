# AWS FinOps Platform - Enterprise Makefile

.PHONY: help install test lint deploy clean docs

# Default target
help: ## Show this help message
	@echo "AWS FinOps Platform - Available Commands:"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

# Development Setup
install: ## Install dependencies and setup development environment
	@echo "Setting up development environment..."
	pip install -r requirements.txt
	pip install -r requirements-dev.txt
	pre-commit install

install-dev: ## Install development dependencies only
	pip install -r requirements-dev.txt
	pip install -r tests/requirements.txt

# Code Quality
lint: ## Run code linting and formatting
	@echo "Running code quality checks..."
	black src/ tests/
	flake8 src/ tests/
	pylint src/
	mypy src/

format: ## Format code with black and isort
	black src/ tests/
	isort src/ tests/

security-scan: ## Run security vulnerability scanning
	bandit -r src/
	safety check

# Testing
test: ## Run all tests
	@echo "Running test suite..."
	pytest tests/ -v --cov=src --cov-report=html --cov-report=term

test-unit: ## Run unit tests only
	pytest tests/unit/ -v

test-integration: ## Run integration tests only
	pytest tests/integration/ -v

test-coverage: ## Generate test coverage report
	pytest tests/ --cov=src --cov-report=html --cov-report=term --cov-fail-under=80

# Infrastructure
plan: ## Plan Terraform infrastructure changes
	@echo "Planning infrastructure changes..."
	cd infrastructure/terraform && terraform plan

deploy-infra: ## Deploy infrastructure with Terraform
	@echo "Deploying infrastructure..."
	cd infrastructure/terraform && terraform apply

destroy-infra: ## Destroy infrastructure (use with caution)
	@echo "WARNING: This will destroy all infrastructure!"
	@read -p "Are you sure? [y/N] " -n 1 -r; \
	if [[ $$REPLY =~ ^[Yy]$$ ]]; then \
		cd infrastructure/terraform && terraform destroy; \
	fi

# Lambda Deployment
package-lambda: ## Package Lambda functions for deployment
	@echo "Packaging Lambda functions..."
	./scripts/deployment/package_lambdas.sh

deploy-lambda: ## Deploy Lambda functions
	@echo "Deploying Lambda functions..."
	./scripts/deployment/deploy_lambdas.sh

deploy: ## Full deployment (infrastructure + Lambda functions)
	make deploy-infra
	make package-lambda
	make deploy-lambda

# Environment Management
deploy-dev: ## Deploy to development environment
	@echo "Deploying to development environment..."
	export ENV=dev && make deploy

deploy-staging: ## Deploy to staging environment
	@echo "Deploying to staging environment..."
	export ENV=staging && make deploy

deploy-prod: ## Deploy to production environment
	@echo "Deploying to production environment..."
	export ENV=production && make deploy

# Monitoring and Operations
logs: ## View Lambda function logs
	@echo "Viewing recent Lambda logs..."
	./scripts/utilities/view_logs.sh

metrics: ## Display cost optimization metrics
	@echo "Displaying optimization metrics..."
	python scripts/utilities/display_metrics.py

benchmark: ## Run performance benchmarks
	@echo "Running performance benchmarks..."
	python benchmark.py

# Documentation
docs: ## Generate documentation
	@echo "Generating documentation..."
	mkdocs build
	@echo "Documentation available at site/index.html"

docs-serve: ## Serve documentation locally
	mkdocs serve

# Utilities
clean: ## Clean build artifacts and temporary files
	@echo "Cleaning build artifacts..."
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	rm -rf build/ dist/ .coverage htmlcov/

backup: ## Backup configuration and state files
	@echo "Creating backup..."
	./scripts/utilities/backup.sh

validate: ## Validate configuration and code
	@echo "Validating configuration..."
	./scripts/deployment/validate.sh
	make lint
	make test-unit

# CI/CD Support
ci-test: ## Run CI test suite
	make lint
	make security-scan
	make test-coverage

ci-deploy: ## CI deployment pipeline
	make validate
	make package-lambda
	make deploy

# Development Helpers
setup-local: ## Setup local development environment
	@echo "Setting up local development..."
	./tools/local_development/setup.sh

docker-build: ## Build Docker image for local development
	docker build -t aws-finops-platform -f tools/docker/Dockerfile .

docker-run: ## Run application in Docker container
	docker-compose -f tools/docker/docker-compose.yml up

# Cost Analysis
calculate-savings: ## Calculate potential cost savings
	@echo "Calculating potential savings..."
	python calculate-savings.py

generate-report: ## Generate cost optimization report
	@echo "Generating cost optimization report..."
	python scripts/utilities/generate_report.py

# Quick Commands
quick-deploy: validate package-lambda deploy-lambda ## Quick Lambda deployment (skip infrastructure)
full-setup: install deploy docs ## Complete setup from scratch
health-check: ## Check system health and configuration
	@echo "Running health checks..."
	./scripts/utilities/health_check.sh
