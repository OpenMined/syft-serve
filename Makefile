.PHONY: help test test-unit test-integration test-cov lint format type-check clean install dev-install build publish docs serve-docs

help: ## Show this help message
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

install: ## Install package dependencies
	uv sync

dev-install: ## Install package with development dependencies
	uv sync --all-extras

test: ## Run all tests
	uv run pytest tests/ --verbose

test-unit: ## Run unit tests only
	uv run pytest tests/ -m "not integration" --verbose

test-integration: ## Run integration tests only
	uv run pytest tests/ -m integration --verbose

test-cov: ## Run tests with coverage report
	uv run pytest tests/ --cov=syft_serve --cov-report=html --cov-report=term-missing --cov-report=xml

test-fast: ## Run tests in parallel
	uv run pytest tests/ -n auto --verbose

lint: ## Run linting checks
	uv run ruff check src/ tests/
	uv run black --check src/ tests/

format: ## Format code
	uv run black src/ tests/
	uv run ruff check --fix src/ tests/

type-check: ## Run type checking
	uv run mypy src/

quality: lint type-check ## Run all quality checks

pre-commit: format lint type-check test-unit ## Run pre-commit checks

clean: ## Clean build artifacts
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info/
	rm -rf .pytest_cache/
	rm -rf .coverage
	rm -rf htmlcov/
	rm -rf .mypy_cache/
	rm -rf .ruff_cache/
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

build: clean ## Build package
	uv build

publish: build ## Publish package to PyPI
	uv publish

publish-test: build ## Publish package to Test PyPI
	uv publish --index-url https://test.pypi.org/legacy/

docs: ## Generate documentation
	@echo "Documentation is in docs/ directory"
	@echo "To serve locally: make serve-docs"

serve-docs: ## Serve documentation locally
	cd docs && python -m http.server 8080

# Development workflow targets
dev-setup: dev-install ## Setup development environment
	uv run pre-commit install

dev-test: format lint type-check test-cov ## Run full development test suite

# CI/CD targets
ci-test: ## Run tests for CI
	uv run pytest tests/ --verbose --cov=syft_serve --cov-report=xml --junit-xml=test-results.xml

ci-quality: ## Run quality checks for CI
	uv run ruff check src/ tests/
	uv run black --check src/ tests/
	uv run mypy src/

# Tutorial and examples
test-tutorial: ## Test the tutorial notebook
	uv run jupyter nbconvert --to script tutorial.ipynb
	python -m py_compile tutorial.py
	rm -f tutorial.py

# Security
security-scan: ## Run security scans
	uv add --dev bandit[toml] safety
	uv run bandit -r src/
	uv run safety check

# Package verification
verify-package: build ## Verify package can be installed
	pip install dist/*.whl --force-reinstall
	python -c "import syft_serve; print('Package verification successful')"
	pip uninstall syft-serve -y