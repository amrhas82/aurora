# CI/CD Architecture

## Overview

AURORA's CI/CD pipeline is optimized to handle both lightweight tests and ML-dependent tests efficiently, preventing disk space exhaustion while maintaining comprehensive test coverage.

## Problem Statement

Previously, the CI pipeline installed ML dependencies (PyTorch ~2GB, sentence-transformers, etc.) in **every job**, causing:
- Disk space exhaustion on GitHub Actions runners (~14GB available)
- 5+ GB of dependencies per job × 5 parallel jobs = 25+ GB total
- CI failures due to "No space left on device" errors
- Slow CI runs due to redundant installations

## Solution Architecture

### Test Organization

Tests are categorized using pytest markers:

```python
# Non-ML tests (1,876 tests - 96.9%)
- Run on all Python versions (3.10, 3.11, 3.12)
- No ML dependencies required
- Fast, lightweight

# ML tests (60 tests - 3.1%)
- Marked with @pytest.mark.ml
- Run on Python 3.10 only
- Require torch + sentence-transformers
```

### CI/CD Jobs

#### 1. Lint (No dependencies)
- Runs: `ruff check` and `ruff format --check`
- Purpose: Code quality and style enforcement
- Dependencies: ruff only (~5MB)

#### 2. Type Check (Dev dependencies only)
- Runs: `mypy` on all packages
- Purpose: Static type checking
- Dependencies: Development tools (no ML)

#### 3. Test Matrix (Non-ML, Python 3.10/3.11/3.12)
- Runs: 1,876 non-ML tests on 3 Python versions
- Purpose: Cross-version compatibility
- Dependencies: Dev tools only (no ML)
- Command: `pytest tests/ -m "not ml"`

#### 4. Test ML (Python 3.10 only)
- Runs: 60 ML-dependent tests on Python 3.10
- Purpose: Validate ML functionality
- Dependencies: torch + sentence-transformers (~5GB)
- Optimizations:
  - Pip cache enabled
  - Pre-run disk cleanup (removes .NET, GHC, boost)
  - `--no-cache-dir` flag on ML packages
- Command: `pytest tests/ -m ml`

#### 5. Performance (Non-ML benchmarks)
- Runs: Performance tests excluding ML
- Purpose: Track performance metrics
- Dependencies: Dev tools only
- Command: `pytest tests/performance/ -m "performance and not ml"`

#### 6. Security (Bandit scan)
- Runs: Static security analysis
- Purpose: Vulnerability detection
- Dependencies: bandit only

#### 7. Build (Package build)
- Runs: After all tests pass
- Purpose: Build distribution packages
- Dependencies: build tools only

## Disk Space Management

### Problem Metrics
- GitHub Actions runner: ~14GB available
- PyTorch: ~2GB
- sentence-transformers + dependencies: ~1.5GB
- Other ML dependencies: ~1GB
- **Total per job with ML: ~5GB**

### Solution
1. **Separate ML job**: Only 1 job installs ML dependencies (not 5)
2. **Disk cleanup**: Remove unused system components before ML install
3. **Pip caching**: Reuse downloaded ML packages across runs
4. **No-cache install**: Use `--no-cache-dir` for ML packages

```bash
# Disk cleanup (frees ~10GB)
sudo rm -rf /usr/share/dotnet
sudo rm -rf /opt/ghc
sudo rm -rf /usr/local/share/boost
```

## Test Markers

### Available Markers

```ini
[pytest.ini]
markers =
    unit: Unit tests that test individual components
    integration: Integration tests across components
    performance: Performance benchmark tests
    slow: Tests taking >1 second
    real_api: Tests making real API calls
    ml: Tests requiring ML dependencies (NEW)
```

### Marking ML Tests

```python
# Option 1: Module-level (entire file)
pytestmark = pytest.mark.ml

# Option 2: Multiple markers
pytestmark = [
    pytest.mark.ml,
    pytest.mark.skipif(not HAS_ML, reason="ML not installed"),
]

# Option 3: Individual test
@pytest.mark.ml
def test_embedding_generation():
    ...
```

### Running Tests Locally

```bash
# All tests
pytest tests/

# Non-ML tests only (fast, no ML deps needed)
pytest tests/ -m "not ml"

# ML tests only (requires torch + sentence-transformers)
pytest tests/ -m ml

# Performance tests excluding ML
pytest tests/performance/ -m "performance and not ml"
```

## ML-Dependent Test Files

Currently 5 files marked with `@pytest.mark.ml`:

1. **tests/integration/test_memory_e2e.py**
   - End-to-end memory indexing and retrieval
   - Uses EmbeddingProvider for semantic search

2. **tests/integration/test_semantic_retrieval.py**
   - Hybrid retrieval precision validation
   - Compares activation-only vs semantic-enhanced

3. **tests/performance/test_embedding_benchmarks.py**
   - Embedding generation performance
   - Target: <50ms per chunk

4. **tests/performance/test_hybrid_retrieval_precision.py**
   - Precision@K benchmarks
   - Target: ≥85% precision @5

5. **tests/unit/context_code/semantic/test_embedding_fallback.py**
   - Fallback behavior when embeddings unavailable
   - Error handling for ML failures

## Benefits

### Before Optimization
- 5 jobs × 5GB ML deps = 25GB total
- Disk exhaustion failures
- 10+ minute install times per job
- All jobs blocked by ML dependency issues

### After Optimization
- 1 job × 5GB ML deps = 5GB total (80% reduction)
- No disk space issues
- Fast non-ML tests run in parallel
- ML tests isolated and cacheable

### Metrics
- **Disk usage**: -80% (25GB → 5GB)
- **Test distribution**: 96.9% non-ML, 3.1% ML
- **Job parallelism**: 4 lightweight jobs run in parallel
- **Coverage maintained**: 100% of tests still run

## Future Considerations

### Optional: Skip ML in PRs
To speed up PR feedback, ML tests could be optional:

```yaml
test-ml:
  if: github.event_name == 'push' && github.ref == 'refs/heads/main'
```

### Optional: Self-Hosted Runners
For repos with frequent ML test runs:
- Persistent ML installations
- GPU acceleration
- Larger disk space

### Optional: ML Test Parallelization
If ML test suite grows significantly:
- Split into smaller groups
- Run multiple ML jobs with different test subsets
- Use pytest-xdist for parallel execution

## Maintenance

### Adding New ML Tests
1. Import ML dependencies in test file
2. Add `pytestmark = pytest.mark.ml` at module level
3. Add conditional skip for missing dependencies:
   ```python
   pytestmark = [
       pytest.mark.ml,
       pytest.mark.skipif(not HAS_ML, reason="ML not installed"),
   ]
   ```

### Verifying CI Configuration
```bash
# Check test distribution
pytest --co -q -m ml tests/          # Should show ~60 tests
pytest --co -q -m "not ml" tests/    # Should show ~1,876 tests

# Test locally without ML
pytest tests/ -m "not ml" --cov=packages

# Test ML functionality (requires installation)
pip install sentence-transformers torch
pytest tests/ -m ml
```

## Related Documentation

- [Testing Guide](TESTING.md)
- [Package Development](PACKAGE_DEVELOPMENT.md)
- [MCP Setup](MCP_SETUP.md)
