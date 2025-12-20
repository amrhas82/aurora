.PHONY: help install install-dev clean test test-unit test-integration test-performance lint format type-check quality-check benchmark coverage docs

help:
	@echo "AURORA Development Commands"
	@echo "=========================="
	@echo "install          - Install all packages in editable mode"
	@echo "install-dev      - Install with development dependencies"
	@echo "clean            - Remove build artifacts and caches"
	@echo "test             - Run all tests"
	@echo "test-unit        - Run unit tests only"
	@echo "test-integration - Run integration tests only"
	@echo "test-performance - Run performance benchmarks"
	@echo "lint             - Run ruff linter"
	@echo "format           - Format code with ruff"
	@echo "type-check       - Run mypy type checker"
	@echo "quality-check    - Run all quality checks (lint, type-check, test)"
	@echo "benchmark        - Run performance benchmarks with detailed output"
	@echo "coverage         - Generate and open HTML coverage report"
	@echo "docs             - Build documentation"

install:
	pip install -e packages/core
	pip install -e packages/context-code
	pip install -e packages/soar
	pip install -e packages/testing
	pip install -e .

install-dev:
	pip install -e "packages/core[dev]"
	pip install -e "packages/context-code[dev]"
	pip install -e "packages/soar[dev]"
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
	pytest tests/

test-unit:
	pytest tests/unit/ -m unit

test-integration:
	pytest tests/integration/ -m integration

test-performance:
	pytest tests/performance/ -m performance

lint:
	ruff check packages/ tests/

format:
	ruff check --fix packages/ tests/
	ruff format packages/ tests/

type-check:
	mypy packages/core/src packages/context-code/src packages/soar/src packages/testing/src

quality-check: lint type-check test

benchmark:
	pytest tests/performance/ -m performance --benchmark-only --benchmark-verbose

coverage:
	pytest tests/ --cov=packages --cov-report=html
	@echo "Opening coverage report..."
	@python -m webbrowser htmlcov/index.html || xdg-open htmlcov/index.html || open htmlcov/index.html

docs:
	@echo "Documentation building not yet implemented"
