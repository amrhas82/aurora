.PHONY: help install install-dev clean test test-unit test-integration lint format type-check quality-check coverage docs

help:
	@echo "AURORA Development Commands"
	@echo "=========================="
	@echo "install          - Install all packages in editable mode"
	@echo "install-dev      - Install with development dependencies"
	@echo "clean            - Remove build artifacts and caches"
	@echo "test             - Run all tests"
	@echo "test-unit        - Run unit tests only"
	@echo "test-integration - Run integration tests only"
	@echo "lint             - Run ruff linter"
	@echo "format           - Format code with ruff"
	@echo "type-check       - Run mypy type checker"
	@echo "quality-check    - Run all quality checks (lint, type-check, test)"
	@echo "coverage         - Generate and open HTML coverage report"
	@echo "docs             - Build documentation"

install:
	pip install -e packages/core
	pip install -e packages/context-code
	pip install -e packages/context-doc
	pip install -e packages/soar
	pip install -e packages/reasoning
	pip install -e packages/planning
	pip install -e packages/spawner
	pip install -e packages/implement
	pip install -e packages/cli
	pip install -e packages/testing
	pip install -e .

install-dev:
	pip install -e "packages/core[dev]"
	pip install -e "packages/context-code[dev]"
	pip install -e "packages/context-doc[dev]"
	pip install -e "packages/soar[dev]"
	pip install -e "packages/reasoning[dev]"
	pip install -e "packages/planning[dev]"
	pip install -e "packages/spawner[dev]"
	pip install -e "packages/implement[dev]"
	pip install -e "packages/cli[dev]"
	pip install -e "packages/testing[dev]"
	pip install -e ".[dev]"

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type f -name "*.coverage" -delete
	rm -rf build dist htmlcov .coverage coverage.xml

test:
	pytest packages/

test-unit:
	pytest packages/ -m unit

test-integration:
	pytest packages/ -m integration

lint:
	ruff check packages/

format:
	ruff check --fix packages/
	ruff format packages/

type-check:
	mypy -p aurora_core -p aurora_context_code -p aurora_soar

quality-check: lint type-check test

coverage:
	pytest packages/ --cov=packages --cov-report=html
	@echo "Opening coverage report..."
	@python -m webbrowser htmlcov/index.html || xdg-open htmlcov/index.html || open htmlcov/index.html

docs:
	@echo "Documentation building not yet implemented"
