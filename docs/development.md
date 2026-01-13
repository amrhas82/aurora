# Aurora Development Guide

## Environment Setup

### Quick Install (Editable)
```bash
git clone https://github.com/amrhas82/aurora.git
cd aurora
./install.sh
```

### Manual Install
```bash
pip install -e packages/core
pip install -e packages/context-code
pip install -e packages/soar
pip install -e packages/reasoning
pip install -e packages/planning
pip install -e packages/spawner
pip install -e packages/implement
pip install -e packages/cli
pip install -e packages/testing
pip install -e .
```

### With Dev Dependencies
```bash
pip install -e ".[dev]"
```

### With ML Features
```bash
pip install -e ".[ml]"
```

## Development Workflow

### Daily Commands
```bash
# Run tests
make test                    # All tests
make test-unit              # Unit only (~30s)
make test-integration       # Integration (~1m)
pytest tests/unit/test_specific.py  # Single file

# Code quality
make lint                   # Ruff linter
make format                 # Auto-format
make type-check             # Mypy

# Full quality check
make quality-check          # lint + type-check + test
```

### Pre-Commit Hooks
```bash
# Install hooks
pre-commit install

# Run manually
pre-commit run --all-files
```

## Project Structure

```
aurora/
  packages/           9 internal packages (see architecture.md)
  src/                Namespace packages (aurora_mcp)
  tests/
    unit/             Fast, isolated tests
    integration/      Cross-package tests
    e2e/              End-to-end CLI tests
    performance/      Benchmarks
    fixtures/         Shared test data
  docs/               Documentation
  examples/           Usage examples
  tasks/              Task definitions
```

## Testing Strategy

### Test Markers
```bash
pytest -m unit          # Unit tests only
pytest -m integration   # Integration tests
pytest -m performance   # Benchmarks
pytest -m slow          # Long-running tests
pytest -m ml            # Requires ML dependencies
```

### Coverage Requirements
- Minimum: 84% (enforced by pytest-cov)
- Target: 85%+
- Current packages: Core 86.8%, SOAR 94%, Context-Code 89%

### Test Patterns
```python
# Use dependency injection
def test_search(mock_store):
    retriever = HybridRetriever(store=mock_store)
    results = retriever.search("query")
    assert len(results) > 0

# Use real components when possible
def test_bm25_scoring():
    scorer = BM25Scorer()  # Real implementation
    score = scorer.score("hello world", "hello")
    assert score > 0.0

# Use fixtures from conftest.py
def test_with_fixtures(sample_chunks, temp_db):
    store = MemoryStore(temp_db)
    for chunk in sample_chunks:
        store.store_chunk(chunk)
```

### Running Specific Tests
```bash
# By file
pytest tests/unit/test_bm25_tokenizer.py

# By test name
pytest -k "test_search"

# With coverage
pytest tests/unit/ --cov=packages/core --cov-report=html

# Verbose output
pytest -v tests/unit/
```

## Code Style

### Ruff Configuration
```toml
# pyproject.toml
[tool.ruff]
target-version = "py310"
line-length = 100

[tool.ruff.lint]
select = ["E", "W", "F", "I", "UP"]  # pycodestyle, pyflakes, isort, pyupgrade
```

### Type Hints
- All public functions must have type hints
- Use `from __future__ import annotations` for forward references
- Strict mypy configuration enforced

### Docstrings
```python
def search(query: str, limit: int = 5) -> list[SearchResult]:
    """Search memory for relevant chunks.

    Args:
        query: Search query string
        limit: Maximum results to return

    Returns:
        List of search results ordered by relevance
    """
```

## Adding New Features

### New CLI Command
1. Create command file: `packages/cli/src/aurora_cli/commands/new_cmd.py`
2. Define Click command:
   ```python
   @click.command()
   @click.argument("input")
   def new_command(input: str) -> None:
       """Command description."""
       pass
   ```
3. Register in `main.py`:
   ```python
   cli.add_command(new_command)
   ```
4. Add tests in `tests/unit/test_new_cmd.py`

### New Package
1. Create directory: `packages/new-pkg/`
2. Add `pyproject.toml` with hatchling build
3. Create `src/aurora_new_pkg/__init__.py`
4. Add to root `pyproject.toml` dependencies
5. Add to `Makefile` install targets

### New Parser (Language Support)
1. Install tree-sitter grammar: `pip install tree-sitter-<lang>`
2. Add parser in `packages/context-code/src/aurora_context_code/parsers/`
3. Register in parser factory
4. Add tests for chunk extraction

## Debugging

### Verbose Logging
```bash
# CLI verbose mode
aur mem search "query" --verbose
aur goals "Add feature" --debug

# Environment variable
export AURORA_LOGGING_LEVEL=DEBUG
```

### Common Issues

**Import errors**: Ensure all packages installed in editable mode
```bash
pip install -e packages/core  # etc.
```

**Database locked**: SQLite concurrent access
```bash
rm .aurora/memory.db  # Rebuild index
aur mem index .
```

**Tree-sitter parsing fails**: Missing grammar
```bash
pip install tree-sitter-python tree-sitter-javascript
```

**Tests fail with ML**: Missing dependencies
```bash
pip install -e ".[ml]"
pytest -m "not ml"  # Skip ML tests
```

## Release Process

### Version Bump
1. Update version in:
   - `pyproject.toml` (root)
   - `packages/*/pyproject.toml` (all packages)
   - `packages/cli/src/aurora_cli/main.py` (version_option)
2. Update `CHANGELOG.md`
3. Create git tag: `git tag v0.6.6`

### Build and Publish
```bash
# Build
python -m build

# Test upload
twine upload --repository testpypi dist/*

# Production upload
twine upload dist/*
```

## Useful Scripts

### Rebuild Index
```bash
rm .aurora/memory.db
aur mem index . --force
```

### Check Health
```bash
aur doctor
aur doctor --fix  # Auto-repair
```

### Clear Caches
```bash
make clean
rm -rf ~/.aurora/cache/
```

### Profile Performance
```bash
pytest tests/performance/ --benchmark-only --benchmark-verbose
```

## CI/CD

### GitHub Actions
- Runs on push to main and PRs
- Matrix: Python 3.10, 3.11, 3.12
- Steps: lint, type-check, test, coverage

### Local CI Simulation
```bash
make quality-check  # Run full quality gate
```

## Documentation

### Update Docs
- Architecture changes: `docs/architecture.md`
- CLI commands: `docs/guides/COMMANDS.md`
- Configuration: `docs/reference/CONFIG_REFERENCE.md`
- This guide: `docs/development.md`

### Build Documentation
```bash
make docs  # (Not yet implemented - uses mkdocs)
```
