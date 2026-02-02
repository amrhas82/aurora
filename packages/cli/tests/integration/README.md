# AURORA CLI Integration Tests

End-to-end integration tests for the AURORA CLI, covering complete workflows from installation through query execution.

**Test Coverage**: Query execution, memory management, configuration, error handling
**Test Budget**: ~$5/month for nightly runs with real API calls
**Framework**: pytest with fixtures and markers

---

## Table of Contents

1. [Overview](#overview)
2. [Requirements](#requirements)
3. [Running Tests](#running-tests)
4. [Test Coverage](#test-coverage)
5. [Mocking Strategy](#mocking-strategy)
6. [Adding New Tests](#adding-new-tests)
7. [Continuous Integration](#continuous-integration)

---

## Overview

Integration tests validate complete CLI workflows with real components:

- **End-to-End Workflows**: Full user journeys from `aur init` to query execution
- **Real Dependencies**: Actual database, file system, and API calls (when budget allows)
- **Error Scenarios**: Network failures, invalid configs, corrupted databases
- **Performance Validation**: Latency and throughput targets
- **Cross-Platform**: Linux, macOS, Windows compatibility

### Test Organization

```
packages/cli/tests/integration/
├── README.md                     # This file
├── test_query_e2e.py            # Query execution workflows
├── test_memory_e2e.py           # Memory indexing and search
├── test_config_e2e.py           # Configuration workflows
├── test_error_scenarios.py      # Error handling and recovery
├── test_workflows.py            # Complex multi-step workflows
└── conftest.py                  # Shared fixtures and configuration
```

---

## Requirements

### Environment Setup

```bash
# Install CLI and dependencies
pip install -e packages/cli
pip install -e packages/core
pip install -e packages/reasoning
pip install -e packages/soar

# Install test dependencies
pip install pytest pytest-asyncio pytest-mock
```

### API Key (for real API tests)

```bash
# Set API key for tests that call LLM
export ANTHROPIC_API_KEY=sk-ant-...

# Tests automatically skip if key not set
```

### Estimated Costs

- **Mocked tests**: $0 (no API calls)
- **Real API tests**: ~$0.50 per full test run
- **Nightly runs**: ~$5/month (10 runs)
- **Budget limit**: Set in test configuration to prevent overruns

---

## Running Tests

### Run All Integration Tests

```bash
# With pytest-specific args
pytest packages/cli/tests/integration/ -v

# With markers
pytest packages/cli/tests/integration/ -v -m integration
```

### Run Specific Test File

```bash
# Query tests only
pytest packages/cli/tests/integration/test_query_e2e.py -v

# Memory tests only
pytest packages/cli/tests/integration/test_memory_e2e.py -v
```

### Run with Real API Calls

```bash
# Set API key
export ANTHROPIC_API_KEY=sk-ant-...

# Run tests marked for real API
pytest packages/cli/tests/integration/ -v -m real_api

# Show API call details
pytest packages/cli/tests/integration/ -v -m real_api --log-cli-level=DEBUG
```

### Run Mocked Tests Only

```bash
# Skip real API tests (fast, $0 cost)
pytest packages/cli/tests/integration/ -v -m "not real_api"
```

### Run with Coverage

```bash
# Generate coverage report
pytest packages/cli/tests/integration/ \
  --cov=aurora_cli \
  --cov-report=html \
  --cov-report=term-missing

# Open HTML report
open htmlcov/index.html
```

---

## Test Coverage

### Workflow 1: Install → Init → Query

**File**: `test_workflows.py::test_fresh_install_workflow`

**Steps**:
1. Clean virtualenv (simulate fresh install)
2. Install CLI package
3. Run `aur init` with mocked input
4. Verify config file created
5. Run `aur query "test"` with API key
6. Verify response received

**Validates**:
- Installation correctness
- Config file creation
- API key setup
- First query execution

**Markers**: `@pytest.mark.integration`, `@pytest.mark.slow`

---

### Workflow 2: Install → Init → Index → Query

**File**: `test_workflows.py::test_full_indexing_workflow`

**Steps**:
1. Install CLI
2. Run `aur init`
3. Create test project files
4. Run `aur mem index`
5. Verify chunks in database
6. Run `aur query` with memory context
7. Verify response uses indexed context

**Validates**:
- Memory indexing
- Database creation
- Context retrieval
- AURORA pipeline execution

**Markers**: `@pytest.mark.integration`, `@pytest.mark.real_api`

---

### Workflow 3: Auto-Index Prompt

**File**: `test_memory_e2e.py::test_auto_index_on_first_query`

**Steps**:
1. Fresh installation
2. Empty memory database
3. Run `aur query "test"`
4. Mock user input "Y" for auto-index
5. Verify indexing triggered
6. Verify query uses memory context

**Validates**:
- Auto-index prompt display
- User input handling
- Background indexing
- Memory integration

**Markers**: `@pytest.mark.integration`

---

### Workflow 4: Memory Operations

**File**: `test_memory_e2e.py`

**Tests**:
- `test_index_current_directory`: Basic indexing
- `test_index_specific_path`: Custom directory
- `test_search_keyword`: Keyword search
- `test_search_semantic`: Semantic search
- `test_search_hybrid`: Hybrid scoring
- `test_search_json_format`: JSON output
- `test_memory_stats`: Statistics display

**Validates**:
- Memory indexing
- Search algorithms
- Output formatting
- Database operations

---

### Workflow 5: Configuration Precedence

**File**: `test_config_e2e.py::test_config_precedence`

**Steps**:
1. Set environment variable
2. Create config file with different value
3. Run query with CLI flag
4. Verify precedence: CLI > Env > File > Defaults

**Validates**:
- Configuration loading order
- Override behavior
- Validation

---

### Workflow 6: Error Recovery

**File**: `test_error_scenarios.py`

**Tests**:
- `test_rate_limit_retry`: Auto-retry on 429
- `test_network_error_handling`: Network failure recovery
- `test_invalid_api_key`: Clear error message
- `test_database_locked`: Lock detection and retry
- `test_corrupted_database`: Recovery guidance

**Validates**:
- Error detection
- Retry logic
- Error messages
- Recovery procedures

---

## Mocking Strategy

### When to Mock

**Mock for CI/CD** (no API budget):
- Unit tests (always mocked)
- Integration tests in PR checks
- Developer local testing

**Real API for Validation** (use budget):
- Nightly scheduled tests
- Pre-release verification
- Performance benchmarking

### Mock Components

#### Mock LLM Client

```python
from unittest.mock import Mock

def mock_llm_client():
    """Mock LLM client for testing without API calls."""
    client = Mock()
    client.generate.return_value = "Test response"
    return client

@pytest.fixture
def mocked_llm():
    return mock_llm_client()
```

#### Mock SOAR Orchestrator

```python
def mock_soar_orchestrator():
    """Mock SOAR orchestrator for testing workflow."""
    orchestrator = Mock()
    orchestrator.execute.return_value = {
        'response': 'Test response',
        'confidence': 0.85,
        'cost_usd': 0.001
    }
    return orchestrator

@pytest.fixture
def mocked_soar():
    return mock_soar_orchestrator()
```

#### Mock Memory Store

```python
from aurora_core.store import MemoryStore

class MockMemoryStore(MemoryStore):
    """In-memory store for testing."""

    def __init__(self):
        self.chunks = {}

    def save_chunk(self, chunk):
        self.chunks[chunk.chunk_id] = chunk

    def search_keyword(self, query, limit=10):
        return list(self.chunks.values())[:limit]

@pytest.fixture
def mock_store():
    return MockMemoryStore()
```

### Using Mocks in Tests

```python
import pytest
from unittest.mock import patch

@pytest.mark.integration
def test_query_with_mocked_llm(mocked_llm):
    """Test query execution with mocked LLM."""
    with patch('aurora_cli.execution.LLMClient', return_value=mocked_llm):
        result = subprocess.run(
            ['aur', 'query', 'test'],
            capture_output=True,
            text=True
        )
        assert result.returncode == 0
        assert 'Test response' in result.stdout

@pytest.mark.integration
@pytest.mark.real_api
@pytest.mark.skipif(not os.getenv('ANTHROPIC_API_KEY'), reason="No API key")
def test_query_with_real_api():
    """Test query with real API (requires API key)."""
    result = subprocess.run(
        ['aur', 'query', 'What is 2+2?', '--force-direct'],
        capture_output=True,
        text=True,
        env={**os.environ, 'ANTHROPIC_API_KEY': os.getenv('ANTHROPIC_API_KEY')}
    )
    assert result.returncode == 0
    assert '4' in result.stdout
```

---

## Adding New Tests

### Test Template

```python
import pytest
import subprocess
import tempfile
from pathlib import Path

@pytest.mark.integration
def test_new_workflow():
    """Test description.

    This test validates:
    - Thing 1
    - Thing 2
    - Thing 3
    """
    # Setup
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)

        # Create test data
        test_file = tmpdir / "test.py"
        test_file.write_text("def test(): pass")

        # Execute CLI command
        result = subprocess.run(
            ['aur', 'mem', 'index', str(tmpdir)],
            capture_output=True,
            text=True,
            cwd=tmpdir
        )

        # Assertions
        assert result.returncode == 0, f"Command failed: {result.stderr}"
        assert "Indexing complete" in result.stdout

        # Verify side effects
        db_path = tmpdir / "aurora.db"
        assert db_path.exists()

        # Cleanup (automatic with tempfile)
```

### Test Naming Conventions

- **Prefix**: `test_` for pytest discovery
- **Workflow tests**: `test_<workflow>_workflow`
- **Feature tests**: `test_<feature>_<aspect>`
- **Error tests**: `test_<error>_handling`

### Test Markers

Use pytest markers to categorize tests:

```python
@pytest.mark.integration      # Integration test (slower)
@pytest.mark.real_api          # Requires real API call
@pytest.mark.slow              # Takes >5 seconds
@pytest.mark.skip              # Temporarily disabled
@pytest.mark.skipif(condition) # Conditionally skip
```

### Test Fixtures

Add reusable fixtures to `conftest.py`:

```python
@pytest.fixture
def temp_project():
    """Create temporary project with test files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)

        # Create project structure
        (tmpdir / "src").mkdir()
        (tmpdir / "src" / "main.py").write_text("def main(): pass")
        (tmpdir / "tests").mkdir()
        (tmpdir / "tests" / "test_main.py").write_text("def test_main(): pass")

        yield tmpdir

@pytest.fixture
def api_key():
    """Get API key or skip test."""
    key = os.getenv('ANTHROPIC_API_KEY')
    if not key:
        pytest.skip("No ANTHROPIC_API_KEY set")
    return key
```

---

## Continuous Integration

### GitHub Actions Workflow

```yaml
name: Integration Tests

on:
  pull_request:
    branches: [main]
  schedule:
    - cron: '0 2 * * *'  # Nightly at 2 AM UTC

jobs:
  integration-tests:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.10'

      - name: Install dependencies
        run: |
          pip install -e packages/cli
          pip install pytest pytest-cov

      - name: Run integration tests (mocked)
        run: |
          pytest packages/cli/tests/integration/ -v -m "not real_api"

      - name: Run integration tests (real API)
        if: github.event_name == 'schedule'  # Nightly only
        env:
          ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
        run: |
          pytest packages/cli/tests/integration/ -v -m real_api

      - name: Upload coverage
        uses: codecov/codecov-action@v3
```

### Budget Protection

```python
# conftest.py
import pytest

# Track total cost across test session
_total_cost = 0.0
_cost_limit = 5.0  # $5 budget limit

def pytest_runtest_teardown(item):
    """Track API costs after each test."""
    global _total_cost

    # Get cost from test (if tracked)
    cost = getattr(item, '_test_cost', 0.0)
    _total_cost += cost

    # Fail remaining tests if over budget
    if _total_cost > _cost_limit:
        pytest.fail(f"Budget exceeded: ${_total_cost:.2f} > ${_cost_limit:.2f}")
```

---

## Test Maintenance

### Regular Tasks

- **Review test results**: Check for flaky tests
- **Update mocks**: Keep aligned with real API behavior
- **Monitor costs**: Track monthly API spending
- **Update fixtures**: Maintain test data freshness
- **Performance baselines**: Update target latencies

### When to Update Tests

- **New CLI command**: Add integration test
- **Bug fix**: Add regression test
- **Feature change**: Update affected tests
- **API changes**: Update mocks and real API tests
- **Performance regression**: Add performance test

---

## Troubleshooting

### Tests Fail with "No API Key"

```bash
# Set API key for real API tests
export ANTHROPIC_API_KEY=sk-ant-...

# Or skip real API tests
pytest packages/cli/tests/integration/ -m "not real_api"
```

### Tests Timeout

```bash
# Increase timeout
pytest packages/cli/tests/integration/ --timeout=300

# Or run individual slow tests
pytest packages/cli/tests/integration/test_workflows.py::test_slow_workflow -v
```

### Database Locked Errors

```bash
# Clean up locks before running tests
rm -f aurora.db-wal aurora.db-shm

# Or use unique database per test (automatic with fixtures)
```

### Flaky Tests

```bash
# Run test multiple times to reproduce
pytest packages/cli/tests/integration/test_flaky.py --count=10

# Add debugging output
pytest packages/cli/tests/integration/ -v --log-cli-level=DEBUG
```

---

## Related Documentation

- **CLI Usage Guide**: [../../docs/cli/CLI_USAGE_GUIDE.md](../../docs/cli/CLI_USAGE_GUIDE.md)
- **Test Strategy**: [../../../docs/TESTING_STRATEGY.md](../../../docs/TESTING_STRATEGY.md)
- **Contributing**: [../../../CONTRIBUTING.md](../../../CONTRIBUTING.md)

---

## Summary

Integration tests ensure CLI reliability through:

✅ **Complete workflows** from installation to execution
✅ **Real components** with strategic mocking
✅ **Error scenarios** with recovery validation
✅ **Budget controls** to prevent cost overruns
✅ **CI/CD integration** for automated validation

**Run tests regularly** and keep them updated with CLI changes.
