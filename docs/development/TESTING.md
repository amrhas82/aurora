# AURORA Testing Guide

**Last Updated**: December 24, 2025
**Version**: 1.0.0
**Status**: Complete
**Audience**: Developers, Contributors, QA Engineers

---

## Table of Contents

1. [Overview](#overview)
2. [Why Test Documentation Matters](#why-test-documentation-matters)
3. [Test Organization](#test-organization)
4. [Test Types](#test-types)
5. [Running Tests](#running-tests)
6. [Writing Tests](#writing-tests)
7. [Test Infrastructure](#test-infrastructure)
8. [Coverage Expectations](#coverage-expectations)
9. [Continuous Integration](#continuous-integration)
10. [Troubleshooting](#troubleshooting)
11. [Best Practices](#best-practices)
12. [Contributing Tests](#contributing-tests)

---

## Overview

### Test Suite Statistics

- **Total Tests**: 1,824+ tests
- **Test Files**: 93 files
- **Code Coverage**: 88.41% (exceeds 85% target)
- **Test Pass Rate**: 100%
- **Test Execution Time**: ~2-3 minutes (full suite)

### Testing Philosophy

AURORA follows a **comprehensive testing strategy** that includes:

1. **Unit Tests**: Fast, isolated tests for individual components
2. **Integration Tests**: Multi-component interactions and E2E flows
3. **Performance Tests**: Benchmarks and profiling
4. **Fault Injection Tests**: Error handling and resilience
5. **Calibration Tests**: Verification accuracy validation

**Key Principles**:
- Tests are **executable documentation** of how the system works
- Tests provide **safety net** for refactoring and changes
- Tests **prevent regressions** and catch bugs early
- Tests **validate requirements** from PRDs

---

## Why Test Documentation Matters

### For Developers

**Reduces Onboarding Time**
- New developers understand test structure immediately
- Know where to add tests for new features
- Learn codebase through tests (tests as documentation)

**Increases Productivity**
- No time wasted figuring out test conventions
- Clear patterns to follow
- Quick reference for running specific tests

**Improves Code Quality**
- Consistent test patterns across codebase
- Higher test coverage when guidelines are clear
- Better test maintainability

### For Contributors

**Lowers Contribution Barrier**
- External contributors can write tests confidently
- Clear expectations for PRs (all PRs must include tests)
- Faster PR review cycles

### For QA Engineers

**Enables Systematic Testing**
- Understand what's already tested
- Identify coverage gaps
- Plan additional test scenarios
- Validate requirements traceability

### For Project Managers

**Provides Confidence**
- Test metrics track product quality
- Coverage reports show risk areas
- Test trends show stability improvements

### Value Proposition

| Benefit | Impact | Time Saved |
|---------|--------|------------|
| Faster onboarding | New devs productive in days not weeks | 2-3 weeks per developer |
| Reduced bugs | Catch issues before production | Hours per bug |
| Faster reviews | Clear test expectations | 30-50% review time |
| Better coverage | Systematic test planning | Ongoing |

**Conclusion**: Test documentation is **essential** for any project with:
- Multiple contributors
- Long-term maintenance
- Quality requirements
- Onboarding needs

**Investment**: 4-6 hours to create, 30 minutes/month to maintain
**Return**: Hundreds of hours saved across team

---

## Test Organization

### Directory Structure

```
tests/
├── unit/                       # Unit tests (fast, isolated)
│   ├── cli/                    # CLI package tests
│   ├── context_code/           # Code context tests
│   ├── core/                   # Core package tests
│   ├── reasoning/              # Reasoning package tests
│   └── soar/                   # SOAR pipeline tests
│
├── integration/                # Integration tests (multi-component)
│   ├── test_simple_query_e2e.py
│   ├── test_medium_query_e2e.py
│   ├── test_complex_query_e2e.py
│   ├── test_parse_and_store.py
│   ├── test_semantic_retrieval.py
│   ├── test_agent_execution.py
│   ├── test_headless_execution.py
│   └── test_error_recovery.py
│
├── performance/                # Performance benchmarks
│   ├── test_parser_benchmarks.py
│   ├── test_storage_benchmarks.py
│   ├── test_activation_benchmarks.py
│   ├── test_embedding_benchmarks.py
│   ├── test_soar_benchmarks.py
│   └── test_memory_profiling.py
│
├── fault_injection/            # Error handling tests
│   ├── test_llm_timeout.py
│   ├── test_malformed_output.py
│   ├── test_budget_exceeded.py
│   ├── test_agent_failure.py
│   └── test_bad_decomposition.py
│
├── calibration/                # Verification accuracy tests
│   └── test_verification_calibration.py
│
└── fixtures/                   # Test data and fixtures
    ├── sample_python_files/    # Code parsing test data
    ├── agents/                 # Agent configuration fixtures
    └── headless/               # Headless mode fixtures
```

### Package Structure

```
packages/testing/
└── src/aurora_testing/
    ├── __init__.py             # Package entry point
    ├── fixtures.py             # Pytest fixtures (stores, chunks, etc.)
    ├── mocks.py                # Mock implementations (LLM, agents, etc.)
    └── benchmarks.py           # Performance benchmarking utilities
```

### Test Naming Conventions

**Files**: `test_<feature>.py`
- `test_store.py` - Tests for storage functionality
- `test_actr_activation.py` - Tests for ACT-R activation
- `test_soar_pipeline.py` - Tests for SOAR pipeline

**Classes**: `Test<Feature>` (optional, for grouping)
- `TestSQLiteStore` - Group of SQLite store tests
- `TestACTRActivation` - Group of activation tests

**Functions**: `test_<behavior>_<scenario>`
- `test_save_chunk_creates_new_record()`
- `test_get_chunk_returns_none_when_not_found()`
- `test_activation_decays_over_time()`
- `test_pipeline_handles_complex_query()`

**Pattern**: Start with action verb (test_), describe behavior, include scenario

---

## Test Types

### 1. Unit Tests (597+ tests)

**Purpose**: Test individual components in isolation

**Characteristics**:
- Fast (<10ms per test)
- No external dependencies
- Use mocks for dependencies
- Test single function/class

**Location**: `tests/unit/`

**Example**:
```python
# tests/unit/core/test_store.py
import pytest
from aurora_core.store import MemoryStore
from aurora_core.chunks import CodeChunk

def test_save_chunk_creates_new_record():
    """Test that saving a chunk creates a new record with correct ID."""
    store = MemoryStore()
    chunk = CodeChunk(
        file_path="/test/file.py",
        element_type="function",
        name="test_func",
        line_start=1,
        line_end=10,
        content="def test_func(): pass"
    )

    chunk_id = store.save_chunk(chunk)

    assert chunk_id is not None
    retrieved = store.get_chunk(chunk_id)
    assert retrieved.name == "test_func"
    assert retrieved.file_path == "/test/file.py"

def test_get_chunk_returns_none_when_not_found():
    """Test that getting non-existent chunk returns None."""
    store = MemoryStore()

    result = store.get_chunk("nonexistent-id")

    assert result is None
```

**When to Write Unit Tests**:
- For all public APIs
- For complex algorithms (ACT-R formula, activation decay)
- For validation logic
- For error handling
- For edge cases

**Coverage Target**: 80%+ per module

---

### 2. Integration Tests (149+ tests)

**Purpose**: Test multiple components working together

**Characteristics**:
- Slower (100ms - 1s per test)
- Test component interactions
- May use real implementations (not mocks)
- Test E2E workflows

**Location**: `tests/integration/`

**Example**:
```python
# tests/integration/test_simple_query_e2e.py
import pytest
from aurora_soar import SOARPipeline
from aurora_core.store import SQLiteStore

@pytest.mark.integration
def test_simple_query_end_to_end(tmp_path):
    """Test complete query flow from input to response."""
    # Setup
    store = SQLiteStore(tmp_path / "test.db")
    pipeline = SOARPipeline(store=store)

    # Populate store with test data
    # ... (add chunks to store)

    # Execute query
    result = pipeline.execute("What functions handle errors?")

    # Verify results
    assert result.status == "success"
    assert len(result.retrieved_chunks) > 0
    assert "error" in result.response.lower()
    assert result.metadata["complexity"] in ["SIMPLE", "MEDIUM"]
```

**When to Write Integration Tests**:
- For cross-package interactions
- For complete user workflows
- For API contracts between modules
- For configuration handling
- For data flow validation

**Coverage Target**: 70%+ for integration paths

---

### 3. Performance Tests (44+ tests)

**Purpose**: Validate performance requirements and catch regressions

**Characteristics**:
- Measure latency, throughput, memory
- Use realistic data sizes
- Set performance budgets
- Track trends over time

**Location**: `tests/performance/`

**Example**:
```python
# tests/performance/test_storage_benchmarks.py
import pytest
from aurora_testing.benchmarks import PerformanceBenchmark
from aurora_core.store import SQLiteStore

@pytest.mark.performance
def test_save_chunk_latency(benchmark_suite, tmp_path):
    """Benchmark chunk save operation latency."""
    store = SQLiteStore(tmp_path / "bench.db")
    chunks = generate_test_chunks(count=1000)

    benchmark = benchmark_suite.create("save_chunk")

    for chunk in chunks:
        with benchmark.measure():
            store.save_chunk(chunk)

    # Performance targets
    assert benchmark.p50 < 1.0, "p50 latency should be <1ms"
    assert benchmark.p95 < 5.0, "p95 latency should be <5ms"
    assert benchmark.p99 < 10.0, "p99 latency should be <10ms"

@pytest.mark.performance
def test_memory_usage_scales_linearly(memory_profiler):
    """Test that memory usage scales linearly with data size."""
    store = SQLiteStore(":memory:")

    memory_profiler.baseline()

    # Add 10K chunks
    for i in range(10000):
        chunk = create_test_chunk(i)
        store.save_chunk(chunk)

    memory_usage = memory_profiler.current_usage()

    # Should be <100MB for 10K chunks (requirement)
    assert memory_usage < 100 * 1024 * 1024, f"Memory {memory_usage} exceeds 100MB"
```

**When to Write Performance Tests**:
- For operations with latency requirements
- For memory-intensive operations
- For throughput-sensitive code paths
- For cache effectiveness

**Coverage Target**: All critical performance paths

**Performance Requirements**:
- Query latency p95 < 500ms (10K chunks)
- Memory < 100MB (10K chunks)
- Throughput > 10 queries/sec
- Parser < 200ms (1000-line file)

---

### 4. Fault Injection Tests (79+ tests)

**Purpose**: Validate error handling and resilience

**Characteristics**:
- Simulate failures (network, LLM, disk)
- Test error propagation
- Validate recovery mechanisms
- Test degraded operation modes

**Location**: `tests/fault_injection/`

**Example**:
```python
# tests/fault_injection/test_llm_timeout.py
import pytest
from aurora_soar import SOARPipeline
from aurora_testing.mocks import MockLLM

@pytest.mark.fault_injection
def test_pipeline_retries_on_llm_timeout():
    """Test that pipeline retries when LLM times out."""
    # Create mock that fails twice then succeeds
    mock_llm = MockLLM(
        fail_count=2,
        failure_type="timeout",
        retry_delay=0.1
    )

    pipeline = SOARPipeline(llm_client=mock_llm)

    # Should succeed after retries
    result = pipeline.execute("test query")

    assert result.status == "success"
    assert mock_llm.call_count == 3  # Failed twice, succeeded third time

@pytest.mark.fault_injection
def test_pipeline_degrades_gracefully_on_budget_exceeded():
    """Test graceful degradation when budget is exceeded."""
    pipeline = SOARPipeline(budget_tokens=100)  # Very low budget

    result = pipeline.execute("complex query requiring many tokens")

    # Should return partial results, not crash
    assert result.status == "partial"
    assert result.metadata["budget_exceeded"] is True
    assert result.response is not None
    assert "budget exceeded" in result.response.lower()
```

**When to Write Fault Injection Tests**:
- For all external dependencies (LLM, network, disk)
- For budget/quota enforcement
- For timeout handling
- For malformed input handling
- For concurrent access edge cases

**Coverage Target**: 95%+ error recovery rate

---

### 5. Calibration Tests (13+ tests)

**Purpose**: Validate verification system accuracy

**Characteristics**:
- Use known ground-truth data
- Measure precision/recall
- Test adversarial cases
- Validate against requirements

**Location**: `tests/calibration/`

**Example**:
```python
# tests/calibration/test_verification_calibration.py
import pytest
from aurora_soar import SOARPipeline

@pytest.mark.calibration
def test_verification_accuracy_on_ground_truth():
    """Test verification accuracy on known correct/incorrect responses."""
    pipeline = SOARPipeline()

    test_cases = load_calibration_dataset()  # 13+ cases with ground truth

    results = []
    for case in test_cases:
        verification_result = pipeline.verify(
            response=case.response,
            query=case.query,
            context=case.context
        )

        # Compare to ground truth
        is_correct = verification_result.passed == case.expected_valid
        results.append(is_correct)

    accuracy = sum(results) / len(results)

    # Target: >90% accuracy on calibration set
    assert accuracy >= 0.90, f"Verification accuracy {accuracy:.1%} below 90%"
```

**When to Write Calibration Tests**:
- For verification system changes
- After prompt engineering
- For new complexity levels
- After LLM model changes

**Coverage Target**: Continuous monitoring, >90% accuracy

---

## Running Tests

### Quick Start

```bash
# Run all tests
make test

# Run with coverage report
make test-coverage

# Run specific test type
make test-unit              # Unit tests only
make test-integration       # Integration tests only
make test-performance       # Performance benchmarks only
```

### Using pytest Directly

```bash
# Run all tests
pytest tests/

# Run specific test file
pytest tests/unit/core/test_store.py

# Run specific test function
pytest tests/unit/core/test_store.py::test_save_chunk_creates_new_record

# Run tests matching pattern
pytest tests/ -k "activation"    # All tests with "activation" in name
pytest tests/ -k "test_get"       # All "get" tests

# Run tests with specific marker
pytest tests/ -m unit             # Unit tests only
pytest tests/ -m integration      # Integration tests only
pytest tests/ -m "unit and not slow"  # Fast unit tests only
pytest tests/ -m "performance or slow"  # Performance tests
```

### Verbosity Levels

```bash
# Quiet (just summary)
pytest tests/ -q

# Normal (default)
pytest tests/

# Verbose (show test names)
pytest tests/ -v

# Very verbose (show all output)
pytest tests/ -vv
```

### Coverage Reports

```bash
# Run with coverage
pytest tests/ --cov=packages --cov-report=term-missing

# Generate HTML report
pytest tests/ --cov=packages --cov-report=html
# Open htmlcov/index.html in browser

# Generate XML report (for CI)
pytest tests/ --cov=packages --cov-report=xml
```

### Parallel Execution

```bash
# Install pytest-xdist
pip install pytest-xdist

# Run tests in parallel (4 workers)
pytest tests/ -n 4

# Run tests with auto-scaling (detects CPU cores)
pytest tests/ -n auto
```

### Filtering Tests

```bash
# Run only failed tests from last run
pytest tests/ --lf

# Run failed tests first, then others
pytest tests/ --ff

# Stop on first failure
pytest tests/ -x

# Stop after N failures
pytest tests/ --maxfail=3
```

### Test Discovery

```bash
# List all tests without running
pytest tests/ --collect-only

# List tests matching pattern
pytest tests/ -k "store" --collect-only

# Show test markers
pytest tests/ --markers
```

---

## Writing Tests

### Test Structure: Arrange-Act-Assert

```python
def test_activation_decays_over_time():
    # Arrange: Set up test data and mocks
    chunk = create_test_chunk()
    store = MemoryStore()
    chunk_id = store.save_chunk(chunk)

    # Act: Perform the operation being tested
    initial_activation = store.get_activation(chunk_id)
    time.sleep(1)  # Simulate time passing
    later_activation = store.get_activation(chunk_id)

    # Assert: Verify expected behavior
    assert later_activation < initial_activation
    assert later_activation > 0  # Should not be zero
```

### Test Naming: Behavior, Not Implementation

**Good**:
```python
def test_save_chunk_creates_new_record()
def test_get_chunk_returns_none_when_not_found()
def test_activation_decays_exponentially()
```

**Bad**:
```python
def test_save_chunk()  # Too vague
def test_store_insert()  # Implementation detail
def test_case_1()  # Meaningless
```

### Fixtures: Reuse Test Setup

```python
# conftest.py
import pytest
from aurora_core.store import MemoryStore

@pytest.fixture
def empty_store():
    """Provide a fresh, empty MemoryStore for testing."""
    return MemoryStore()

@pytest.fixture
def populated_store():
    """Provide a MemoryStore with 100 test chunks."""
    store = MemoryStore()
    for i in range(100):
        chunk = create_test_chunk(id=i)
        store.save_chunk(chunk)
    return store

# Use in tests
def test_retrieval_with_populated_store(populated_store):
    results = populated_store.retrieve_by_activation(limit=10)
    assert len(results) == 10
```

### Parametrized Tests: Test Multiple Inputs

```python
@pytest.mark.parametrize("complexity,expected_phases", [
    ("SIMPLE", 5),      # Simple queries skip some phases
    ("MEDIUM", 7),      # Medium uses most phases
    ("COMPLEX", 9),     # Complex uses all phases
])
def test_pipeline_phase_count_by_complexity(complexity, expected_phases):
    """Test that different complexity levels use appropriate phases."""
    pipeline = SOARPipeline()
    result = pipeline.execute("test", complexity=complexity)

    assert len(result.phases_executed) == expected_phases
```

### Mocking: Isolate Unit Tests

```python
from unittest.mock import Mock, patch
from aurora_testing.mocks import MockLLM

def test_pipeline_uses_llm_for_decomposition():
    """Test that pipeline calls LLM for decomposition."""
    mock_llm = MockLLM(
        response='{"subgoals": ["goal1", "goal2"]}'
    )

    pipeline = SOARPipeline(llm_client=mock_llm)
    result = pipeline.execute("test query", complexity="MEDIUM")

    # Verify LLM was called
    assert mock_llm.call_count > 0
    assert "decompose" in mock_llm.last_prompt.lower()
```

### Testing Exceptions

```python
def test_save_chunk_raises_error_on_invalid_chunk():
    """Test that invalid chunk raises ValidationError."""
    store = MemoryStore()
    invalid_chunk = CodeChunk(
        file_path="",  # Empty path is invalid
        element_type="function",
        name="test",
        line_start=1,
        line_end=0,  # End before start is invalid
        content="test"
    )

    with pytest.raises(ValidationError) as exc_info:
        store.save_chunk(invalid_chunk)

    assert "line_end" in str(exc_info.value)
```

### Testing Async Code

```python
import pytest

@pytest.mark.asyncio
async def test_async_retrieval():
    """Test asynchronous chunk retrieval."""
    store = AsyncMemoryStore()
    chunk = create_test_chunk()

    chunk_id = await store.save_chunk(chunk)
    retrieved = await store.get_chunk(chunk_id)

    assert retrieved.name == chunk.name
```

### Test Data: Use Factories

```python
# factories.py
def create_test_chunk(id=None, name=None, complexity=0.5):
    """Factory function for creating test chunks with defaults."""
    return CodeChunk(
        file_path=f"/test/file_{id or 'default'}.py",
        element_type="function",
        name=name or f"test_func_{id or 0}",
        line_start=1,
        line_end=10,
        content="def test(): pass",
        complexity_score=complexity,
        language="python"
    )

# Use in tests
def test_with_custom_chunk():
    chunk = create_test_chunk(id=42, name="my_func", complexity=0.8)
    # ... test with chunk
```

---

## Test Infrastructure

### Pytest Fixtures (`packages/testing/src/aurora_testing/fixtures.py`)

**Available Fixtures**:

```python
@pytest.fixture
def memory_store() -> MemoryStore:
    """Provide a fresh in-memory store."""

@pytest.fixture
def sqlite_store(tmp_path) -> SQLiteStore:
    """Provide a SQLite store in temporary directory."""

@pytest.fixture
def code_chunk() -> CodeChunk:
    """Provide a sample CodeChunk."""

@pytest.fixture
def reasoning_chunk() -> ReasoningChunk:
    """Provide a sample ReasoningChunk."""

@pytest.fixture
def mock_llm() -> MockLLM:
    """Provide a mock LLM client."""

@pytest.fixture
def benchmark_suite() -> BenchmarkSuite:
    """Provide performance benchmarking suite."""

@pytest.fixture
def memory_profiler() -> MemoryProfiler:
    """Provide memory profiling utilities."""
```

**Usage**:
```python
def test_using_fixture(memory_store, code_chunk):
    """Test automatically gets fixtures injected."""
    chunk_id = memory_store.save_chunk(code_chunk)
    assert chunk_id is not None
```

### Mock Implementations (`packages/testing/src/aurora_testing/mocks.py`)

**MockLLM**: Rule-based LLM for testing
```python
mock_llm = MockLLM(
    response='{"result": "test"}',
    latency=0.1,  # Simulate 100ms latency
    fail_count=2,  # Fail first 2 calls
)
```

**MockAgent**: Simulated agent for testing
```python
mock_agent = MockAgent(
    capabilities=["search", "analysis"],
    response="Agent response",
)
```

**MockParser**: Fake code parser
```python
mock_parser = MockParser(
    chunks=[chunk1, chunk2],
    parse_time=0.05,
)
```

### Performance Benchmarking (`packages/testing/src/aurora_testing/benchmarks.py`)

**PerformanceBenchmark**: Measure latency
```python
benchmark = PerformanceBenchmark("operation_name")

with benchmark.measure():
    perform_operation()

print(f"p50: {benchmark.p50}ms")
print(f"p95: {benchmark.p95}ms")
print(f"p99: {benchmark.p99}ms")
```

**MemoryProfiler**: Measure memory usage
```python
profiler = MemoryProfiler()
profiler.baseline()

# Perform operation
result = operation()

memory_used = profiler.current_usage()
print(f"Memory: {memory_used / 1024 / 1024:.2f} MB")
```

### Test Data Fixtures (`tests/fixtures/`)

**Sample Python Files**: Real code for parsing tests
- `tests/fixtures/sample_python_files/simple.py`
- `tests/fixtures/sample_python_files/complex_class.py`
- `tests/fixtures/sample_python_files/with_errors.py`

**Agent Configurations**: Test agent configs
- `tests/fixtures/agents/search_agent.json`
- `tests/fixtures/agents/analysis_agent.json`

**Headless Prompts**: Headless mode test fixtures
- `tests/fixtures/headless/prompt.md`
- `tests/fixtures/headless/prompt_invalid_*.md`

---

## Coverage Expectations

### Overall Coverage Target

**Minimum**: 85% line coverage
**Current**: 88.41% (exceeds target by 3.41%)
**Stretch Goal**: 90%+

### Per-Module Targets

| Module Type | Target | Notes |
|-------------|--------|-------|
| Core modules (storage, chunks) | 90%+ | Critical path, high coverage |
| SOAR pipeline | 85%+ | Complex but well-tested |
| LLM clients | 70%+ | External dependencies, harder to test |
| Parsers | 80%+ | Important but tree-sitter mocking difficult |
| CLI | 70%+ | UI code, less critical |
| Utilities | 80%+ | Should be well-tested |

### What to Test

**Always Test**:
- ✅ Public APIs
- ✅ Core business logic
- ✅ Error handling paths
- ✅ Validation logic
- ✅ Edge cases (empty, null, boundary values)
- ✅ Data transformations

**Sometimes Test**:
- ⚠️ Private implementation details (if complex)
- ⚠️ Configuration parsing (if non-trivial)
- ⚠️ Logging and metrics (if critical)

**Don't Bother Testing**:
- ❌ Third-party library code
- ❌ Simple getters/setters
- ❌ Trivial pass-through functions
- ❌ Auto-generated code

### Known Coverage Gaps

See `docs/TECHNICAL_DEBT.md` for detailed coverage gap tracking:

**Critical Gaps** (P1):
- `migrations.py` (30% coverage) - Migration logic untested
- `llm_client.py` (36% coverage) - Error paths untested
- Semantic embedding error handling

**Medium Gaps** (P2):
- Connection pooling concurrency tests
- Parser registry thread safety
- Some verification edge cases

---

## Continuous Integration

### GitHub Actions / CI Pipeline

**On Every Commit**:
```yaml
# .github/workflows/test.yml
- name: Run tests
  run: |
    pytest tests/ \
      --cov=packages \
      --cov-report=xml \
      --cov-report=term \
      --cov-fail-under=84
```

**Test Stages**:
1. **Lint**: ruff check (code quality)
2. **Type Check**: mypy (type safety)
3. **Unit Tests**: Fast tests (~30s)
4. **Integration Tests**: E2E tests (~1-2min)
5. **Coverage Check**: Fail if <84%

**Nightly CI** (optional):
- Performance benchmarks (slower)
- Memory profiling
- Full calibration suite
- Dependency security scan

### Pre-commit Hooks

```bash
# Install pre-commit
pip install pre-commit
pre-commit install

# Runs on every commit:
# - Code formatting (ruff format)
# - Linting (ruff check)
# - Type checking (mypy)
# - Fast unit tests
```

### CI Configuration

**pytest.ini**:
```ini
[pytest]
minversion = 7.0
testpaths = tests
addopts =
    -ra                           # Show all test results
    --strict-markers              # Enforce marker registration
    --cov=packages                # Coverage for packages/
    --cov-fail-under=84           # Fail if coverage <84%
    -v                            # Verbose output
markers =
    unit: Unit tests
    integration: Integration tests
    performance: Performance benchmarks
    slow: Tests >1s execution time
```

### Skipping Tests

**Skip in CI only**:
```python
@pytest.mark.skipif(
    os.getenv("CI") == "true",
    reason="Requires external API (OpenAI)"
)
def test_with_real_openai_api():
    # Test that uses real OpenAI API
    pass
```

**Skip conditionally**:
```python
@pytest.mark.skipif(
    not SENTENCE_TRANSFORMERS_AVAILABLE,
    reason="sentence-transformers not installed"
)
def test_semantic_embeddings():
    # Test that requires optional dependency
    pass
```

---

## Troubleshooting

### Common Issues

#### Issue: Tests Failing with "ModuleNotFoundError"

**Cause**: Packages not installed in development mode

**Solution**:
```bash
# Install all packages in editable mode
pip install -e packages/core
pip install -e packages/context-code
pip install -e packages/soar
pip install -e packages/reasoning
pip install -e packages/cli
pip install -e packages/testing

# Or use convenience script
make install-dev
```

---

#### Issue: Coverage Report Shows 0% Coverage

**Cause**: Coverage not measuring code in `packages/` directory

**Solution**:
```bash
# Run with explicit coverage paths
pytest tests/ --cov=packages/core/src --cov=packages/soar/src
```

---

#### Issue: Tests Pass Locally but Fail in CI

**Causes**:
1. Environment differences (Python version, OS)
2. Timing issues (GC, network latency)
3. Missing dependencies
4. File path assumptions

**Solution**:
```bash
# Reproduce CI environment locally
docker run -it python:3.12 bash
# ... install dependencies and run tests

# Or use tox for multi-environment testing
pip install tox
tox  # Runs tests in isolated environments
```

---

#### Issue: Memory Tests Occasionally Fail

**Cause**: Garbage collection timing (see TD-P3-005 in TECHNICAL_DEBT.md)

**Solution**:
```python
import gc

def test_memory_usage():
    # Force GC before measurement
    gc.collect()

    # Measure memory
    memory_before = get_memory_usage()

    # ... perform operation ...

    # Force GC again
    gc.collect()
    memory_after = get_memory_usage()

    assert memory_after - memory_before < threshold
```

---

#### Issue: Performance Tests Are Flaky

**Cause**: System load variability

**Solution**:
```python
# Use relative measurements, not absolute thresholds
def test_cache_improves_performance():
    # Measure without cache
    time_without_cache = measure_operation()

    # Measure with cache
    time_with_cache = measure_operation()

    # Assert relative improvement (cache should be 2x faster)
    assert time_with_cache < time_without_cache * 0.5
```

---

#### Issue: Tests Hang or Timeout

**Cause**: Infinite loops, deadlocks, or slow operations

**Solution**:
```python
# Add timeout to tests
@pytest.mark.timeout(10)  # Timeout after 10 seconds
def test_that_might_hang():
    # ... test code ...
    pass

# Or use pytest-timeout globally
pytest tests/ --timeout=10
```

---

### Debugging Tests

**Run Single Test with Print Output**:
```bash
pytest tests/unit/core/test_store.py::test_save_chunk -v -s
# -s shows print() output
```

**Use pytest Debugger**:
```python
def test_with_debugger():
    result = some_operation()

    import pdb; pdb.set_trace()  # Drop into debugger

    assert result == expected
```

**Use pytest --pdb flag**:
```bash
# Drop into debugger on failure
pytest tests/ --pdb

# Drop into debugger on first failure
pytest tests/ -x --pdb
```

**Verbose Assertion Output**:
```python
# pytest rewrites assertions to show details
def test_with_good_assertion_info():
    result = {"a": 1, "b": 2}
    expected = {"a": 1, "b": 3}

    assert result == expected
    # Failure shows: AssertionError: {'b': 2} != {'b': 3}
```

---

## Best Practices

### 1. Test Behavior, Not Implementation

**Bad**:
```python
def test_store_uses_dictionary():
    """Tests implementation detail - brittle."""
    store = MemoryStore()
    assert isinstance(store._chunks, dict)  # Breaks if implementation changes
```

**Good**:
```python
def test_store_retrieves_saved_chunks():
    """Tests behavior - stable."""
    store = MemoryStore()
    chunk = create_test_chunk()

    chunk_id = store.save_chunk(chunk)
    retrieved = store.get_chunk(chunk_id)

    assert retrieved.name == chunk.name
```

---

### 2. Keep Tests Independent

**Bad**:
```python
# Tests depend on execution order - fragile
def test_create_user():
    global user_id
    user_id = create_user("test")

def test_get_user():
    user = get_user(user_id)  # Depends on test_create_user running first
    assert user.name == "test"
```

**Good**:
```python
@pytest.fixture
def test_user():
    user_id = create_user("test")
    yield user_id
    cleanup_user(user_id)

def test_get_user(test_user):
    user = get_user(test_user)
    assert user.name == "test"
```

---

### 3. Use Descriptive Test Names

**Bad**:
```python
def test_1():
def test_store():
def test_edge_case():
```

**Good**:
```python
def test_save_chunk_with_empty_content_raises_validation_error():
def test_activation_is_zero_for_never_accessed_chunk():
def test_retrieval_returns_empty_list_when_no_matches_found():
```

---

### 4. Test Edge Cases and Boundaries

```python
def test_activation_boundaries():
    """Test activation at boundary conditions."""
    store = MemoryStore()
    chunk = create_test_chunk()

    # Test: Never accessed (edge case)
    chunk_id = store.save_chunk(chunk)
    activation = store.get_activation(chunk_id)
    assert activation == 0.0

    # Test: Just accessed (boundary)
    store.update_activation(chunk_id)
    activation = store.get_activation(chunk_id)
    assert activation > 0.0

    # Test: Very old chunk (boundary)
    # ... simulate old timestamp ...
    activation = store.get_activation(chunk_id)
    assert activation < 0.1  # Decayed significantly
```

---

### 5. Don't Mock What You Don't Own

**Bad**:
```python
@patch('sqlite3.connect')  # Mocking external library
def test_store_with_mocked_sqlite(mock_connect):
    # Brittle - breaks if sqlite3 API changes
    pass
```

**Good**:
```python
def test_store_with_real_sqlite(tmp_path):
    # Use real SQLite with temporary database
    store = SQLiteStore(tmp_path / "test.db")
    # ... test with real implementation ...
```

---

### 6. One Logical Assertion Per Test

**Bad**:
```python
def test_everything():
    """Tests too many things - hard to debug."""
    store = MemoryStore()
    chunk = create_test_chunk()

    # Multiple unrelated assertions
    assert store.count() == 0
    chunk_id = store.save_chunk(chunk)
    assert store.count() == 1
    retrieved = store.get_chunk(chunk_id)
    assert retrieved is not None
    assert retrieved.name == chunk.name
    store.delete_chunk(chunk_id)
    assert store.count() == 0
```

**Good**:
```python
def test_save_chunk_increments_count():
    store = MemoryStore()
    initial_count = store.count()

    store.save_chunk(create_test_chunk())

    assert store.count() == initial_count + 1

def test_delete_chunk_decrements_count():
    store = MemoryStore()
    chunk_id = store.save_chunk(create_test_chunk())

    store.delete_chunk(chunk_id)

    assert store.count() == 0
```

---

### 7. Use Test Markers for Organization

```python
@pytest.mark.unit
def test_unit_functionality():
    pass

@pytest.mark.integration
def test_integration_flow():
    pass

@pytest.mark.slow
@pytest.mark.performance
def test_performance_benchmark():
    pass

# Run only unit tests
# pytest tests/ -m unit

# Run unit tests but skip slow ones
# pytest tests/ -m "unit and not slow"
```

---

## Contributing Tests

### Required for All PRs

**Every pull request MUST include tests**:
- ✅ New features must have unit tests
- ✅ Bug fixes must have regression tests
- ✅ Refactoring must maintain coverage
- ✅ Coverage must not decrease

### Test Review Checklist

Before submitting PR, verify:
- [ ] All tests pass locally (`pytest tests/`)
- [ ] New code has >80% coverage (`pytest tests/ --cov`)
- [ ] Tests follow naming conventions
- [ ] Tests are independent (can run in any order)
- [ ] Tests use appropriate markers (`@pytest.mark.unit`, etc.)
- [ ] Complex tests have docstrings explaining purpose
- [ ] Test data uses factories or fixtures (not hardcoded)
- [ ] Mocks are used appropriately (isolate external dependencies)
- [ ] Integration tests cover happy path and error cases
- [ ] Performance tests have clear thresholds

### Writing Tests for Bug Fixes

**Process**:
1. Write failing test that reproduces bug
2. Verify test fails (proves it catches the bug)
3. Fix the bug
4. Verify test passes
5. Add test to regression suite

**Example**:
```python
def test_activation_handles_zero_time_delta():
    """Regression test for bug #123: ZeroDivisionError when time_delta=0."""
    store = MemoryStore()
    chunk = create_test_chunk()
    chunk_id = store.save_chunk(chunk)

    # Access chunk twice with no time between
    store.update_activation(chunk_id, timestamp=100.0)
    store.update_activation(chunk_id, timestamp=100.0)  # Same timestamp

    # Should not raise ZeroDivisionError
    activation = store.get_activation(chunk_id, current_time=100.0)

    assert activation >= 0.0  # Should return valid activation
```

---

## Appendix

### Useful pytest Plugins

**Performance Testing**:
- `pytest-benchmark` - Microbenchmarking
- `pytest-timeout` - Test timeout enforcement
- `pytest-xdist` - Parallel test execution

**Quality**:
- `pytest-cov` - Coverage reporting (already installed)
- `pytest-clarity` - Better assertion output
- `pytest-mock` - Improved mocking utilities

**Development**:
- `pytest-watch` - Continuous test runner
- `pytest-testmon` - Run only tests affected by changes
- `pytest-sugar` - Better terminal output

**Installation**:
```bash
pip install pytest-benchmark pytest-timeout pytest-xdist pytest-clarity
```

---

### References

**Internal Documentation**:
- [Coverage Analysis](../reports/testing/COVERAGE_ANALYSIS.md) - Detailed coverage metrics
- [Technical Debt](../TECHNICAL_DEBT.md) - Known test coverage gaps
- [Phase Verification Reports](../phases/) - Test results by phase

**External Resources**:
- [pytest Documentation](https://docs.pytest.org/) - Official pytest docs
- [Python Testing with pytest (Book)](https://pragprog.com/titles/bopytest/) - Comprehensive guide
- [Testing Best Practices](https://docs.python-guide.org/writing/tests/) - Python best practices

---

## Changelog

| Date | Change | Author |
|------|--------|--------|
| 2025-12-24 | Initial creation | Claude |
| TBD | Quarterly review and update | TBD |

---

**End of Testing Guide**
