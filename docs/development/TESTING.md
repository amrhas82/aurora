# AURORA Testing Guide

**Last Updated**: December 27, 2025
**Version**: 2.0.0
**Status**: Active
**Audience**: Developers, Contributors, QA Engineers

---

## Table of Contents

1. [Philosophy](#1-philosophy)
2. [Test Pyramid](#2-test-pyramid)
3. [Testing Principles](#3-testing-principles)
4. [When to Write Tests](#4-when-to-write-tests)
5. [Anti-Patterns](#5-anti-patterns)
6. [Dependency Injection Examples](#6-dependency-injection-examples)
7. [Test Markers](#7-test-markers)
8. [Running Tests](#8-running-tests)
9. [Best Practices](#best-practices)
10. [Contributing Tests](#contributing-tests)
11. [Troubleshooting](#troubleshooting)

---

## 1. Philosophy

### Why We Test

Testing is not just about catching bugs—it's about **building confidence** in our system and **enabling rapid iteration**. AURORA's testing philosophy is built on three core principles:

**1. Tests Are Executable Documentation**
- Tests show how the system *actually* works, not how we think it works
- New team members learn the codebase by reading tests
- Tests serve as living examples of API usage
- When documentation and code diverge, tests reveal the truth

**2. Tests Enable Fearless Refactoring**
- Comprehensive test coverage creates a safety net for changes
- Refactoring without tests is rewriting; refactoring with tests is improvement
- Tests catch regressions immediately, not in production
- Good tests make large-scale changes tractable

**3. Tests Validate Requirements**
- Every test traces back to a requirement in a PRD (Product Requirements Document)
- Tests provide evidence that features work as specified
- Test coverage maps to feature coverage
- Failing tests indicate unmet requirements

### Testing Values

**Pragmatism Over Perfectionism**
- We target **85% coverage** as the sweet spot (diminishing returns beyond this)
- We test critical paths thoroughly, not every line
- We balance test investment with feature velocity
- We document gaps rather than chase 100% coverage

**Quality Over Quantity**
- A few well-written integration tests beat dozens of fragile unit tests
- Tests should be maintainable (DI pattern, no mocks of external libraries)
- Clear test names and structure matter more than test count
- Fast, reliable tests are more valuable than slow, flaky tests

**Real-World Testing**
- Use real components in integration tests (not subprocess mocks)
- Test with realistic data sizes and scenarios
- Include fault injection and edge cases
- Validate performance requirements, not just functionality

### Test Investment ROI

| Investment | Benefit | Impact |
|------------|---------|--------|
| **4-6 hours** initial test documentation | Onboarding time reduced from weeks to days | **2-3 weeks saved per new developer** |
| **30% of development time** writing tests | 80-90% fewer production bugs | **Hours to days saved per bug** |
| **10-15% overhead** maintaining tests | Fearless refactoring and rapid iteration | **30-50% faster feature development** |
| **1-2 hours** per PR for test review | Higher code quality and fewer regressions | **Continuous quality improvement** |

**Bottom Line**: Testing is an investment that pays dividends in:
- Reduced debugging time
- Faster onboarding
- Higher code quality
- Lower production incidents
- Greater team confidence

### What Success Looks Like

**For Developers**:
- ✅ "I can refactor confidently without breaking things"
- ✅ "I understand how this component works by reading its tests"
- ✅ "I know exactly where to add tests for my new feature"
- ✅ "Test failures tell me exactly what broke and why"

**For Contributors**:
- ✅ "I can contribute without deep codebase knowledge"
- ✅ "Test patterns are consistent and easy to follow"
- ✅ "My PR got approved quickly because tests were clear"

**For QA Engineers**:
- ✅ "I can identify coverage gaps systematically"
- ✅ "I can trace tests back to requirements"
- ✅ "I can validate critical user workflows in E2E tests"

**For Project Leads**:
- ✅ "Coverage metrics show quality trends over time"
- ✅ "Critical features have high test coverage"
- ✅ "Team velocity is high because testing enables confidence"

### Current Test Suite Status

**Metrics** (as of December 27, 2025):
- **Total Tests**: 2,369 tests (up from 1,833 at Phase 2)
- **Coverage**: 81.06% (accepted gap from 85% target, documented in TECHNICAL_DEBT_COVERAGE.md)
- **Test Pass Rate**: 97%+ (14 skipped for external APIs)
- **Test Execution Time**: ~2-3 minutes (full suite)
- **Test Distribution**: 76.4% Unit / 21.1% Integration / 2.5% E2E

**Quality Gates**:
- ✅ All core packages exceed 85% coverage (Core: 86.8%, Context-Code: 89.25%, SOAR: 94%)
- ✅ All tests use DI pattern (no @patch decorators)
- ✅ Integration tests use real components (not subprocess mocks)
- ✅ E2E tests cover critical user workflows
- ✅ Cross-Python version compatibility (3.10-3.13)

---

## 2. Test Pyramid

### The Pyramid Principle

The test pyramid guides our testing strategy by balancing **speed**, **confidence**, and **cost**:

```
       /\
      /  \     E2E Tests (2.5%)
     / UI \    - Slowest (1-10s per test)
    /______\   - Highest confidence
   /        \  - Most expensive to maintain
  / INTEGR  \ Integration Tests (21.1%)
 /   ATION   \ - Medium speed (100ms-1s per test)
/______________\ - Good confidence
/              \ - Moderate maintenance
/     UNIT      \ Unit Tests (76.4%)
/________________\ - Fast (<10ms per test)
                   - Quick feedback
                   - Cheap to maintain
```

### Our Distribution

**Current**: 76.4% Unit / 21.1% Integration / 2.5% E2E
**Target**: 70% Unit / 20% Integration / 10% E2E

**Analysis**:
- ✅ Unit test ratio is excellent (76.4% vs 70% target)
- ✅ Integration ratio is on target (21.1% vs 20% target)
- ⚠️ E2E ratio is low (2.5% vs 10% target) BUT justified:
  - MCP package has 139 comprehensive integration tests covering E2E workflows
  - CLI has 9 subprocess integration tests + 15 E2E tests validating real user paths
  - Quality over quantity: our E2E tests are thorough, not numerous

### Layer Breakdown

#### Unit Tests (1,810 tests)

**Purpose**: Test individual components in isolation
**Speed**: <10ms per test
**Scope**: Single function or class

**Example Use Cases**:
- ACT-R activation formula correctness
- Chunk validation logic
- Store CRUD operations
- LLM client response parsing
- Configuration validation

**Coverage Target**: 80%+ per module

**Example**:
```python
def test_activation_decays_over_time():
    """Test ACT-R activation decay formula."""
    chunk = create_test_chunk()
    store = MemoryStore()
    chunk_id = store.save_chunk(chunk)

    initial_activation = store.get_activation(chunk_id, current_time=0)
    later_activation = store.get_activation(chunk_id, current_time=10)

    assert later_activation < initial_activation
    assert later_activation > 0  # Should not be zero
```

#### Integration Tests (500 tests)

**Purpose**: Test multiple components working together
**Speed**: 100ms-1s per test
**Scope**: Multi-component interactions

**Example Use Cases**:
- Parse Python file → Store chunks → Retrieve by activation
- Query → SOAR pipeline → LLM call → Response synthesis
- CLI command → Execution → Memory update → Output
- MCP tool invocation → Agent execution → Result formatting

**Coverage Target**: 70%+ for integration paths

**Example**:
```python
@pytest.mark.integration
def test_query_with_memory_retrieval_e2e(tmp_path):
    """Test complete query flow with memory retrieval."""
    store = SQLiteStore(tmp_path / "test.db")
    pipeline = SOARPipeline(store=store)

    # Index sample code
    parser = PythonParser()
    chunks = parser.parse_file("sample.py")
    for chunk in chunks:
        store.save_chunk(chunk)

    # Execute query
    result = pipeline.execute("What functions handle errors?")

    # Verify full flow
    assert result.status == "success"
    assert len(result.retrieved_chunks) > 0
    assert "error" in result.response.lower()
```

#### E2E Tests (59 tests)

**Purpose**: Test complete user workflows end-to-end
**Speed**: 1-10s per test
**Scope**: Full system integration

**Example Use Cases**:
- User indexes codebase → Runs query → Gets accurate response
- User creates agent → Executes multi-step task → Validates output
- Headless mode workflow (no user interaction)
- CLI battle-testing (real subprocess execution)

**Coverage Target**: All critical user paths

**Example**:
```python
@pytest.mark.e2e
def test_complete_user_workflow(tmp_path):
    """Test full user workflow: index → query → response."""
    # Setup
    project_dir = tmp_path / "project"
    project_dir.mkdir()
    (project_dir / "code.py").write_text("def handle_error(): pass")

    # User indexes project
    result = subprocess.run(
        ["aur", "mem", "index", str(project_dir)],
        capture_output=True,
        text=True
    )
    assert result.returncode == 0

    # User runs query
    result = subprocess.run(
        ["aur", "query", "how to handle errors?"],
        capture_output=True,
        text=True
    )
    assert result.returncode == 0
    assert "handle_error" in result.stdout
```

### Why This Distribution Works

**Fast Feedback**: 76.4% of tests are unit tests (run in seconds)
**High Confidence**: 21.1% integration tests validate component interactions
**Real-World Validation**: 2.5% E2E tests (+139 MCP tests) ensure critical paths work

**Benefits**:
- ✅ CI runs fast (~2-3 minutes for full suite)
- ✅ Developers get quick feedback locally
- ✅ High confidence in refactoring
- ✅ Critical workflows are validated end-to-end

---

## 3. Testing Principles

### Principle 1: Test Behavior, Not Implementation

**Why**: Tests tied to implementation details are brittle and break during refactoring.

**Bad Example**:
```python
def test_store_uses_dictionary():
    """Brittle: tests internal implementation."""
    store = MemoryStore()
    assert isinstance(store._chunks, dict)  # Breaks if we change to list
```

**Good Example**:
```python
def test_store_retrieves_saved_chunks():
    """Stable: tests external behavior."""
    store = MemoryStore()
    chunk = create_test_chunk()

    chunk_id = store.save_chunk(chunk)
    retrieved = store.get_chunk(chunk_id)

    assert retrieved.name == chunk.name  # Tests contract, not implementation
```

**Guideline**: Test the "what" (contract), not the "how" (implementation).

---

### Principle 2: Keep Tests Independent

**Why**: Tests that depend on each other create fragile, hard-to-debug test suites.

**Bad Example**:
```python
# Tests depend on execution order - fragile
user_id = None

def test_create_user():
    global user_id
    user_id = create_user("test")

def test_get_user():
    user = get_user(user_id)  # Depends on test_create_user
    assert user.name == "test"
```

**Good Example**:
```python
@pytest.fixture
def test_user():
    """Independent: each test gets its own user."""
    user_id = create_user("test")
    yield user_id
    cleanup_user(user_id)

def test_get_user(test_user):
    user = get_user(test_user)
    assert user.name == "test"
```

**Guideline**: Each test should be runnable in isolation, in any order.

---

### Principle 3: One Logical Assertion Per Test

**Why**: Tests with multiple assertions are hard to debug when they fail.

**Bad Example**:
```python
def test_everything():
    """Tests too many things - hard to debug."""
    store = MemoryStore()
    assert store.count() == 0  # Assertion 1
    chunk_id = store.save_chunk(create_test_chunk())
    assert store.count() == 1  # Assertion 2
    retrieved = store.get_chunk(chunk_id)
    assert retrieved.name == "test"  # Assertion 3
    store.delete_chunk(chunk_id)
    assert store.count() == 0  # Assertion 4
```

**Good Example**:
```python
def test_save_chunk_increments_count():
    store = MemoryStore()
    initial = store.count()

    store.save_chunk(create_test_chunk())

    assert store.count() == initial + 1  # One logical assertion

def test_delete_chunk_decrements_count():
    store = MemoryStore()
    chunk_id = store.save_chunk(create_test_chunk())

    store.delete_chunk(chunk_id)

    assert store.count() == 0  # One logical assertion
```

**Guideline**: Split multi-assertion tests into focused, single-purpose tests.

---

### Principle 4: Use Descriptive Test Names

**Why**: Test names are documentation. Good names make failures self-explanatory.

**Bad Examples**:
```python
def test_1():  # Meaningless
def test_store():  # Too vague
def test_edge_case():  # What edge case?
```

**Good Examples**:
```python
def test_save_chunk_with_empty_content_raises_validation_error():
def test_activation_is_zero_for_never_accessed_chunk():
def test_retrieval_returns_empty_list_when_no_matches_found():
```

**Naming Pattern**: `test_<action>_<scenario>_<expected_result>`

---

### Principle 5: Arrange-Act-Assert (AAA)

**Why**: Clear structure makes tests readable and maintainable.

**Structure**:
```python
def test_activation_decays_over_time():
    # ARRANGE: Set up test data and dependencies
    chunk = create_test_chunk()
    store = MemoryStore()
    chunk_id = store.save_chunk(chunk)

    # ACT: Perform the operation being tested
    initial_activation = store.get_activation(chunk_id, current_time=0)
    later_activation = store.get_activation(chunk_id, current_time=10)

    # ASSERT: Verify expected behavior
    assert later_activation < initial_activation
    assert later_activation > 0
```

**Guideline**: Always structure tests with clear Arrange, Act, Assert sections.

---

### Principle 6: Don't Mock What You Don't Own

**Why**: Mocking external libraries creates brittle tests that break when libraries change.

**Bad Example**:
```python
@patch('sqlite3.connect')  # Mocking external library
def test_store_with_mocked_sqlite(mock_connect):
    # Brittle - breaks if sqlite3 API changes
    pass
```

**Good Example**:
```python
def test_store_with_real_sqlite(tmp_path):
    """Use real SQLite with temporary database."""
    store = SQLiteStore(tmp_path / "test.db")
    chunk = create_test_chunk()

    chunk_id = store.save_chunk(chunk)
    retrieved = store.get_chunk(chunk_id)

    assert retrieved.name == chunk.name
```

**Guideline**: Use real implementations for external dependencies, or create adapter interfaces.

---

### Principle 7: Use Dependency Injection (DI)

**Why**: DI makes tests fast, reliable, and maintainable. No @patch decorators needed.

**Bad Example**:
```python
@patch('aurora_soar.pipeline.LLMClient')  # Fragile mock
def test_pipeline_uses_llm(mock_llm):
    pipeline = SOARPipeline()  # Hardcoded dependency
    # Test is coupled to implementation
```

**Good Example**:
```python
def test_pipeline_uses_llm():
    """DI: inject mock LLM directly."""
    mock_llm = MockLLM(response='{"result": "test"}')
    pipeline = SOARPipeline(llm_client=mock_llm)  # Inject dependency

    result = pipeline.execute("test query")

    assert mock_llm.call_count > 0
    assert result.status == "success"
```

**Guideline**: All components should accept dependencies via constructor (DI pattern).

---

## 4. When to Write Tests

### Always Write Tests For

✅ **Public APIs**
- Every public function and class
- All exposed CLI commands
- All MCP tool endpoints
- Reason: APIs are contracts with users; breaking them breaks user code

✅ **Core Business Logic**
- ACT-R activation formulas
- SOAR pipeline orchestration
- Retrieval quality assessment
- Agent execution logic
- Reason: Core logic bugs affect all users

✅ **Error Handling Paths**
- LLM timeouts and failures
- Budget exceeded scenarios
- Malformed input handling
- Network failures
- Reason: Error handling is critical for production reliability

✅ **Validation Logic**
- Input validation (chunk structure, query format)
- Configuration validation
- Schema validation
- Reason: Prevents garbage-in, garbage-out

✅ **Edge Cases and Boundaries**
- Empty input (0 chunks, empty query)
- Null/None handling
- Boundary values (min/max activation, timeout = 0)
- Reason: Edge cases cause production bugs if untested

✅ **Data Transformations**
- Parsing code to chunks
- Converting chunks to embeddings
- Formatting LLM responses
- Reason: Data transformation bugs cause silent failures

---

### Sometimes Write Tests For

⚠️ **Private Implementation Details**
- Write tests if complex algorithm (e.g., activation decay formula)
- Skip if simple helper function
- Guideline: Test if complexity > 5 lines or has edge cases

⚠️ **Configuration Parsing**
- Write tests if non-trivial (multi-layer config merging)
- Skip if simple dictionary access
- Guideline: Test if logic branches or has defaults

⚠️ **Logging and Metrics**
- Write tests if metrics affect user experience (e.g., budget tracking)
- Skip if purely observability
- Guideline: Test if logged data is used for decisions

---

### Never Write Tests For

❌ **Third-Party Library Code**
- Don't test that `sqlite3.connect()` works
- Don't test that `requests.get()` works
- Reason: Library maintainers test their own code

❌ **Simple Getters/Setters**
- Don't test `chunk.name` property access
- Don't test simple attribute assignments
- Reason: No logic to test, waste of time

❌ **Trivial Pass-Through Functions**
- Don't test thin wrappers with no logic
- Don't test simple delegation
- Reason: Integration tests will cover these

❌ **Auto-Generated Code**
- Don't test Pydantic model `__init__()`
- Don't test dataclass equality
- Reason: Framework generates and tests this

---

### Bug Fix Testing

**Required**: Every bug fix MUST include a regression test

**Process**:
1. Write failing test that reproduces bug
2. Verify test fails (proves it catches the bug)
3. Fix the bug
4. Verify test passes
5. Commit test + fix together

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
    assert activation >= 0.0
```

---

### New Feature Testing

**Required**: Every new feature MUST include tests before merging

**Test Coverage Requirements**:
- ✅ Happy path (feature works as expected)
- ✅ Error path (feature handles errors gracefully)
- ✅ Edge cases (boundary conditions)
- ✅ Integration (feature works with other components)
- ⚠️ E2E (if feature is user-facing)

**Example** (Retrieval Quality Feature - TD-P2-016):
- 18 unit tests (assess_retrieval_quality function, edge cases)
- 7 integration tests (CLI prompt scenarios, user choices)
- 3 E2E tests planned (headless mode, real user workflows)

---

### Test-Driven Development (TDD)

**When to Use TDD**:
- Complex algorithms (activation formulas)
- Critical features (retrieval quality, verification)
- Bug fixes (write test first, then fix)

**TDD Cycle**:
1. **Red**: Write failing test for desired behavior
2. **Green**: Write minimal code to make test pass
3. **Refactor**: Clean up code while keeping tests green

**Benefits**:
- Forces you to think about API design first
- Ensures tests actually catch bugs (because you saw them fail)
- Prevents over-engineering (write only what's needed)

---

## 5. Anti-Patterns

### Anti-Pattern 1: Testing Mock Behavior

**Problem**: Test verifies mock behavior, not real code behavior.

**Bad Example**:
```python
@patch('aurora_soar.pipeline.LLMClient')
def test_pipeline_calls_llm(mock_llm):
    pipeline = SOARPipeline()
    pipeline.execute("test")

    # Testing that mock was called, not that pipeline works
    mock_llm.return_value.generate.assert_called_once()
```

**Why It's Bad**: Test passes even if `execute()` doesn't work. You're testing the mock, not the code.

**Good Example**:
```python
def test_pipeline_calls_llm():
    """DI: inject real mock LLM that tracks calls."""
    mock_llm = MockLLM(response='{"result": "test"}')
    pipeline = SOARPipeline(llm_client=mock_llm)

    result = pipeline.execute("test")

    # Test real behavior: pipeline used LLM and got result
    assert mock_llm.call_count > 0
    assert result.status == "success"
```

---

### Anti-Pattern 2: Production Code Pollution

**Problem**: Adding test-only methods to production code.

**Bad Example**:
```python
# Production code
class Store:
    def _test_only_clear(self):
        """DO NOT USE IN PRODUCTION."""
        self._chunks.clear()

# Test code
def test_something():
    store = Store()
    store._test_only_clear()  # Polluting production with test code
```

**Why It's Bad**: Production code should have no awareness of tests. Test-only methods create maintenance burden.

**Good Example**:
```python
# Production code (no test pollution)
class Store:
    def clear(self):
        """Clear all chunks (public API)."""
        self._chunks.clear()

# Test code (use fixtures for fresh state)
@pytest.fixture
def empty_store():
    return Store()  # Each test gets fresh store
```

---

### Anti-Pattern 3: Over-Mocking

**Problem**: Mocking everything makes tests fragile and meaningless.

**Bad Example**:
```python
@patch('aurora_core.store.SQLiteStore')
@patch('aurora_soar.pipeline.SOARPipeline')
@patch('aurora_reasoning.llm.LLMClient')
def test_query_workflow(mock_llm, mock_pipeline, mock_store):
    # Test is 100% mocks, 0% real code
    result = execute_query("test")
    # What are we actually testing?
```

**Why It's Bad**: You're testing mocks, not real interactions. Test is useless.

**Good Example**:
```python
def test_query_workflow(tmp_path):
    """Use real components, mock only LLM (external dependency)."""
    store = SQLiteStore(tmp_path / "test.db")  # Real store
    mock_llm = MockLLM(response='{"result": "test"}')  # Mock external
    pipeline = SOARPipeline(store=store, llm_client=mock_llm)  # Real pipeline

    result = pipeline.execute("test")

    # Testing real interactions
    assert result.status == "success"
```

**Guideline**: Mock only external dependencies (LLM, network). Use real code for everything else.

---

### Anti-Pattern 4: Flaky Tests

**Problem**: Tests that pass/fail randomly are worse than no tests.

**Common Causes**:
- Timing issues (sleep, timeouts)
- Shared global state
- Nondeterministic operations (random, datetime.now())
- GC timing (memory tests)

**Bad Example**:
```python
def test_with_timing_issue():
    start_task()
    time.sleep(0.1)  # Hope task finishes in 100ms
    assert task_completed()  # Flaky: might not finish in time
```

**Good Example**:
```python
def test_with_proper_sync():
    start_task()
    # Wait for completion with timeout
    for _ in range(100):
        if task_completed():
            break
        time.sleep(0.01)
    assert task_completed()  # Reliable
```

**Guideline**: Use polling/retries instead of fixed sleeps. Use explicit synchronization.

---

### Anti-Pattern 5: Giant Test Functions

**Problem**: 200-line test functions that test everything are unmaintainable.

**Bad Example**:
```python
def test_entire_application():
    # 200 lines testing every feature
    # When it fails, who knows where the bug is?
```

**Good Example**:
```python
def test_user_login():
    # Focused: one feature

def test_user_logout():
    # Focused: one feature

def test_user_password_reset():
    # Focused: one feature
```

**Guideline**: Each test should fit on one screen (~50 lines max).

---

### Anti-Pattern 6: Testing Implementation Details

**Problem**: Tests coupled to internal implementation break during refactoring.

**Bad Example**:
```python
def test_store_uses_dictionary_internally():
    store = MemoryStore()
    assert isinstance(store._chunks, dict)  # Internal detail
```

**Good Example**:
```python
def test_store_saves_and_retrieves_chunks():
    store = MemoryStore()
    chunk = create_test_chunk()

    chunk_id = store.save_chunk(chunk)
    retrieved = store.get_chunk(chunk_id)

    assert retrieved.name == chunk.name  # Public contract
```

**Guideline**: Test public APIs and observable behavior, not internal structure.

---

## 6. Dependency Injection Examples

### Why Dependency Injection?

**Benefits**:
- ✅ No @patch decorators needed
- ✅ Fast, reliable tests
- ✅ Easy to swap implementations
- ✅ Clear dependencies
- ✅ Testable in isolation

**Core Idea**: Pass dependencies to constructors instead of hardcoding them.

---

### Example 1: SOAR Pipeline (Before/After)

**Before** (Hardcoded Dependencies):
```python
# Production code
class SOARPipeline:
    def __init__(self):
        self.store = SQLiteStore("~/.aurora/store.db")  # Hardcoded
        self.llm = LLMClient()  # Hardcoded

# Test (must use @patch)
@patch('aurora_soar.pipeline.SQLiteStore')
@patch('aurora_soar.pipeline.LLMClient')
def test_pipeline(mock_store, mock_llm):
    pipeline = SOARPipeline()  # Can't inject dependencies
    # Fragile, coupled to import paths
```

**After** (Dependency Injection):
```python
# Production code
class SOARPipeline:
    def __init__(self, store: Store, llm_client: LLMClient):
        self.store = store  # Injected
        self.llm = llm_client  # Injected

# Test (no @patch needed)
def test_pipeline(tmp_path):
    store = SQLiteStore(tmp_path / "test.db")  # Real store
    mock_llm = MockLLM(response='{"result": "test"}')  # Mock LLM
    pipeline = SOARPipeline(store=store, llm_client=mock_llm)  # Inject

    result = pipeline.execute("test")
    assert result.status == "success"
```

---

### Example 2: Store Retrieval (Before/After)

**Before** (Hardcoded):
```python
# Production code
def retrieve_chunks(query: str):
    store = get_default_store()  # Hardcoded global
    return store.retrieve(query)

# Test (must mock global)
@patch('aurora_core.retrieval.get_default_store')
def test_retrieval(mock_get_store):
    # Complex setup
    mock_store = MagicMock()
    mock_get_store.return_value = mock_store
    retrieve_chunks("test")
```

**After** (Dependency Injection):
```python
# Production code
def retrieve_chunks(query: str, store: Store):
    return store.retrieve(query)  # Injected

# Test (simple, clear)
def test_retrieval():
    store = MemoryStore()  # Real store
    chunks = [create_test_chunk()]
    for chunk in chunks:
        store.save_chunk(chunk)

    results = retrieve_chunks("test", store=store)
    assert len(results) > 0
```

---

### Example 3: CLI Execution (Real Example from AURORA)

**Before** (subprocess.run inside function):
```python
# Production code
def execute_memory_command(args: list[str]):
    result = subprocess.run(args, capture_output=True)  # Hardcoded
    return result.stdout

# Test (hard to test)
def test_memory_command():
    # Must actually run subprocess or use @patch
    result = execute_memory_command(["aur", "mem", "stats"])
    # Slow, fragile
```

**After** (Executor injection):
```python
# Production code
def execute_memory_command(args: list[str], executor=None):
    if executor is None:
        executor = SubprocessExecutor()  # Default for production
    result = executor.run(args)
    return result.stdout

# Test (fast, reliable)
def test_memory_command():
    mock_executor = MockExecutor(stdout="Memory: 100 chunks")
    result = execute_memory_command(["aur", "mem", "stats"], executor=mock_executor)
    assert "100 chunks" in result
```

---

### Example 4: Headless Orchestrator (Real AURORA Example)

**Implementation** (Good DI):
```python
# Production code
class HeadlessOrchestrator:
    def __init__(
        self,
        store: Store,
        llm_client: LLMClient,
        agent_registry: AgentRegistry
    ):
        self.store = store  # All dependencies injected
        self.llm = llm_client
        self.agents = agent_registry

# Test (clean, fast)
def test_headless_orchestrator():
    store = MemoryStore()
    mock_llm = MockLLM(response='{"result": "test"}')
    agents = AgentRegistry()

    orchestrator = HeadlessOrchestrator(
        store=store,
        llm_client=mock_llm,
        agent_registry=agents
    )

    result = orchestrator.execute("test task")
    assert result.status == "success"
```

**Why This Works**:
- ✅ No @patch decorators
- ✅ Fast (in-memory store, mock LLM)
- ✅ Reliable (no external dependencies)
- ✅ Clear (dependencies explicit in constructor)

---

### DI Best Practices

**1. Constructor Injection (Preferred)**
```python
class Pipeline:
    def __init__(self, store: Store):  # Inject via constructor
        self.store = store
```

**2. Default Arguments (For Production)**
```python
def execute(query: str, store: Store = None):
    if store is None:
        store = get_default_store()  # Production default
    return process(query, store)
```

**3. Factory Pattern (For Complex Setup)**
```python
class PipelineFactory:
    @staticmethod
    def create_for_testing() -> Pipeline:
        return Pipeline(store=MemoryStore(), llm=MockLLM())

    @staticmethod
    def create_for_production() -> Pipeline:
        return Pipeline(store=SQLiteStore(), llm=LLMClient())
```

---

## 7. Test Markers

### What Are Markers?

Markers categorize tests for selective execution. Use `@pytest.mark.marker_name` to tag tests.

**Benefits**:
- ✅ Run only unit tests for fast feedback
- ✅ Run only critical tests before merge
- ✅ Skip slow tests during development
- ✅ Run integration tests separately in CI

---

### Standard Markers

**Category Markers**:
```python
@pytest.mark.unit          # Unit test (fast, isolated)
@pytest.mark.integration   # Integration test (multi-component)
@pytest.mark.e2e           # End-to-end test (full workflow)
```

**Importance Markers**:
```python
@pytest.mark.critical      # Critical test (must pass before merge)
@pytest.mark.safety        # Safety-critical functionality
```

**Component Markers**:
```python
@pytest.mark.cli           # CLI functionality
@pytest.mark.mcp           # MCP tool functionality
@pytest.mark.soar          # SOAR pipeline
@pytest.mark.core          # Core storage/activation
```

**Speed Markers**:
```python
@pytest.mark.slow          # Test takes >1s
@pytest.mark.fast          # Test takes <100ms
```

---

### Marker Examples

**Unit Test**:
```python
@pytest.mark.unit
def test_activation_calculation():
    """Fast, isolated unit test."""
    chunk = create_test_chunk()
    activation = calculate_activation(chunk, current_time=100)
    assert activation > 0
```

**Critical Test**:
```python
@pytest.mark.critical
@pytest.mark.unit
def test_assess_retrieval_quality_none():
    """Critical: affects user experience."""
    result = assess_retrieval_quality(
        chunks=[],
        high_quality_count=0,
        groundedness=0.0
    )
    assert result == RetrievalQuality.NONE
```

**CLI Integration Test**:
```python
@pytest.mark.integration
@pytest.mark.cli
def test_memory_stats_command():
    """CLI integration: memory stats."""
    executor = MockExecutor(stdout="Chunks: 100")
    result = execute_memory_stats(executor=executor)
    assert "100" in result
```

**Slow E2E Test**:
```python
@pytest.mark.e2e
@pytest.mark.slow
@pytest.mark.mcp
def test_mcp_complete_workflow():
    """Full MCP workflow (slow)."""
    # 5-10 second test
    result = execute_mcp_tool("aurora_query", args={"query": "test"})
    assert result.status == "success"
```

---

### Marker Configuration

**pytest.ini**:
```ini
[pytest]
markers =
    unit: Unit tests (fast, isolated)
    integration: Integration tests (multi-component)
    e2e: End-to-end tests (full workflow)
    critical: Critical tests (must pass before merge)
    safety: Safety-critical functionality
    cli: CLI functionality
    mcp: MCP tool functionality
    soar: SOAR pipeline tests
    core: Core storage/activation tests
    slow: Tests taking >1s
    fast: Tests taking <100ms
```

---

### Running Tests by Marker

**Run only unit tests**:
```bash
pytest tests/ -m unit
```

**Run critical tests before merge**:
```bash
pytest tests/ -m critical
```

**Run CLI tests**:
```bash
pytest tests/ -m cli
```

**Run unit tests but skip slow ones**:
```bash
pytest tests/ -m "unit and not slow"
```

**Run critical OR safety tests**:
```bash
pytest tests/ -m "critical or safety"
```

**Run integration + e2e (not unit)**:
```bash
pytest tests/ -m "integration or e2e"
```

---

### CI Usage

**Fast Feedback** (on every commit):
```bash
pytest tests/ -m "unit and not slow" --maxfail=3
```

**Pre-Merge** (before merging PR):
```bash
pytest tests/ -m critical
```

**Full Suite** (nightly):
```bash
pytest tests/
```

---

## 8. Running Tests

### Quick Start

**Run all tests**:
```bash
make test
# OR
pytest tests/
```

**Run with coverage**:
```bash
make test-coverage
# OR
pytest tests/ --cov=packages --cov-report=term-missing
```

**Run specific test type**:
```bash
pytest tests/ -m unit              # Unit tests only
pytest tests/ -m integration       # Integration tests only
pytest tests/ -m e2e               # E2E tests only
```

---

### Common Pytest Commands

**Run specific file**:
```bash
pytest tests/unit/core/test_store.py
```

**Run specific test**:
```bash
pytest tests/unit/core/test_store.py::test_save_chunk_creates_new_record
```

**Run tests matching pattern**:
```bash
pytest tests/ -k "activation"      # All tests with "activation" in name
pytest tests/ -k "store and not slow"  # Store tests, skip slow
```

**Run with verbosity**:
```bash
pytest tests/ -v        # Verbose (show test names)
pytest tests/ -vv       # Very verbose (show all output)
pytest tests/ -q        # Quiet (just summary)
```

**Run with output**:
```bash
pytest tests/ -s        # Show print() output
pytest tests/ -v -s     # Verbose + print output
```

---

### Debugging Tests

**Drop into debugger on failure**:
```bash
pytest tests/ --pdb
```

**Drop into debugger on first failure**:
```bash
pytest tests/ -x --pdb
```

**Run only failed tests from last run**:
```bash
pytest tests/ --lf        # Last failed
pytest tests/ --ff        # Failed first, then others
```

**Stop on first N failures**:
```bash
pytest tests/ -x          # Stop on first failure
pytest tests/ --maxfail=3 # Stop after 3 failures
```

---

### Coverage Reports

**Terminal report** (shows missing lines):
```bash
pytest tests/ --cov=packages --cov-report=term-missing
```

**HTML report** (detailed, browsable):
```bash
pytest tests/ --cov=packages --cov-report=html
# Open htmlcov/index.html in browser
```

**XML report** (for CI):
```bash
pytest tests/ --cov=packages --cov-report=xml
```

**Fail if coverage below threshold**:
```bash
pytest tests/ --cov=packages --cov-fail-under=85
```

---

### Parallel Execution

**Install pytest-xdist**:
```bash
pip install pytest-xdist
```

**Run with 4 workers**:
```bash
pytest tests/ -n 4
```

**Auto-detect CPU cores**:
```bash
pytest tests/ -n auto
```

**Note**: Parallel execution speeds up test runs but may hide race conditions.

---

### Test Discovery

**List all tests without running**:
```bash
pytest tests/ --collect-only
```

**List tests matching pattern**:
```bash
pytest tests/ -k "store" --collect-only
```

**Show available markers**:
```bash
pytest tests/ --markers
```

---

### CI Configuration

**GitHub Actions** (.github/workflows/ci.yml):
```yaml
- name: Run critical tests
  run: pytest tests/ -m critical --cov=packages --cov-fail-under=81

- name: Run retrieval quality tests
  run: |
    pytest tests/unit/soar/test_retrieval_quality*.py \
           tests/integration/test_retrieval_quality*.py \
           -v --tb=short
```

**pytest.ini**:
```ini
[pytest]
minversion = 7.0
testpaths = tests
addopts =
    -ra                          # Show all test results
    --strict-markers             # Enforce marker registration
    --cov=packages               # Coverage for packages/
    --cov-fail-under=81          # Fail if coverage <81%
    -v                           # Verbose output
```

---

### Common Commands Cheat Sheet

| Task | Command |
|------|---------|
| Run all tests | `pytest tests/` |
| Run with coverage | `pytest tests/ --cov=packages` |
| Run unit tests | `pytest tests/ -m unit` |
| Run critical tests | `pytest tests/ -m critical` |
| Run specific file | `pytest tests/unit/core/test_store.py` |
| Run specific test | `pytest tests/.../test_file.py::test_name` |
| Run tests matching pattern | `pytest tests/ -k "activation"` |
| Show print output | `pytest tests/ -s` |
| Debug on failure | `pytest tests/ --pdb` |
| Run only failed | `pytest tests/ --lf` |
| Stop on first fail | `pytest tests/ -x` |
| Parallel (4 workers) | `pytest tests/ -n 4` |
| HTML coverage report | `pytest tests/ --cov=packages --cov-report=html` |

---

## Best Practices

### 1. Test File Organization

**Match production structure**:
```
packages/core/src/aurora_core/store.py
→ tests/unit/core/test_store.py

packages/soar/src/aurora_soar/pipeline.py
→ tests/unit/soar/test_pipeline.py
```

**Group related tests**:
```python
class TestActivationCalculation:
    """Group activation tests together."""

    def test_activation_decays_over_time(self):
        pass

    def test_activation_increases_on_access(self):
        pass
```

---

### 2. Use Fixtures Effectively

**Reusable setup**:
```python
# conftest.py (shared across all tests)
@pytest.fixture
def memory_store():
    return MemoryStore()

@pytest.fixture
def sqlite_store(tmp_path):
    return SQLiteStore(tmp_path / "test.db")

# Use in tests
def test_with_store(memory_store):
    chunk = create_test_chunk()
    memory_store.save_chunk(chunk)
    # ...
```

**Fixture scopes**:
```python
@pytest.fixture(scope="function")  # Default: new per test
def fresh_store():
    return MemoryStore()

@pytest.fixture(scope="module")    # One per module
def shared_store():
    return MemoryStore()

@pytest.fixture(scope="session")   # One per test session
def global_config():
    return load_config()
```

---

### 3. Parametrize for Multiple Inputs

**Test multiple scenarios efficiently**:
```python
@pytest.mark.parametrize("complexity,expected_phases", [
    ("SIMPLE", 5),
    ("MEDIUM", 7),
    ("COMPLEX", 9),
])
def test_pipeline_phases_by_complexity(complexity, expected_phases):
    pipeline = SOARPipeline()
    result = pipeline.execute("test", complexity=complexity)
    assert len(result.phases_executed) == expected_phases
```

**Test edge cases**:
```python
@pytest.mark.parametrize("chunks,expected_quality", [
    ([], RetrievalQuality.NONE),          # No chunks
    ([weak_chunk], RetrievalQuality.WEAK), # Weak match
    ([good_chunk], RetrievalQuality.GOOD), # Good match
])
def test_retrieval_quality_assessment(chunks, expected_quality):
    result = assess_retrieval_quality(chunks)
    assert result == expected_quality
```

---

### 4. Clear Assertions

**Good assertions**:
```python
assert result.status == "success", f"Expected success, got {result.status}"
assert len(chunks) > 0, "Should retrieve at least one chunk"
assert 0.5 <= activation <= 1.0, f"Activation {activation} out of range"
```

**Use pytest helpers**:
```python
# Test exceptions
with pytest.raises(ValidationError) as exc_info:
    store.save_chunk(invalid_chunk)
assert "line_end" in str(exc_info.value)

# Test warnings
with pytest.warns(UserWarning):
    deprecated_function()

# Approximate equality
assert activation == pytest.approx(0.75, rel=0.01)  # Within 1%
```

---

### 5. Test Data Factories

**Create reusable test data**:
```python
# factories.py
def create_test_chunk(
    id=None,
    name=None,
    activation=0.5,
    content="def test(): pass"
):
    return CodeChunk(
        file_path=f"/test/file_{id or 0}.py",
        element_type="function",
        name=name or f"test_func_{id or 0}",
        line_start=1,
        line_end=10,
        content=content,
        activation_score=activation,
    )

# Use in tests
def test_with_custom_chunk():
    chunk = create_test_chunk(id=42, name="my_func", activation=0.9)
    # ...
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

Before submitting PR:
- [ ] All tests pass locally (`pytest tests/`)
- [ ] New code has >80% coverage
- [ ] Tests follow naming conventions
- [ ] Tests are independent (can run in any order)
- [ ] Tests use appropriate markers
- [ ] Complex tests have docstrings
- [ ] Test data uses factories/fixtures
- [ ] Mocks used appropriately
- [ ] Integration tests cover happy + error paths

---

## Troubleshooting

### Tests Failing with "ModuleNotFoundError"

**Solution**: Install packages in editable mode:
```bash
pip install -e packages/core
pip install -e packages/soar
pip install -e packages/reasoning
pip install -e packages/cli
pip install -e packages/testing

# OR
make install-dev
```

---

### Coverage Report Shows 0%

**Solution**: Run with explicit coverage paths:
```bash
pytest tests/ --cov=packages/core/src --cov=packages/soar/src
```

---

### Tests Pass Locally but Fail in CI

**Causes**:
1. Environment differences (Python version, OS)
2. Timing issues
3. Missing dependencies

**Solution**: Reproduce CI environment:
```bash
docker run -it python:3.12 bash
# Install dependencies and run tests
```

---

### Memory Tests Flaky

**Solution**: Force garbage collection:
```python
import gc

def test_memory_usage():
    gc.collect()  # Force GC before measurement
    memory_before = get_memory_usage()

    # ... operation ...

    gc.collect()  # Force GC after
    memory_after = get_memory_usage()
    assert memory_after - memory_before < threshold
```

---

### Performance Tests Flaky

**Solution**: Use relative measurements:
```python
def test_cache_improves_performance():
    time_without = measure_operation()
    time_with = measure_operation_with_cache()

    # Relative: cache should be 2x faster
    assert time_with < time_without * 0.5
```

---

## Appendix

### pytest Plugins

**Performance**:
- `pytest-benchmark` - Microbenchmarking
- `pytest-timeout` - Timeout enforcement
- `pytest-xdist` - Parallel execution

**Quality**:
- `pytest-cov` - Coverage (already installed)
- `pytest-clarity` - Better assertions
- `pytest-mock` - Mocking utilities

**Development**:
- `pytest-watch` - Continuous runner
- `pytest-testmon` - Run affected tests only

---

### References

**Internal**:
- [Technical Debt (Coverage Gaps)](TECHNICAL_DEBT_COVERAGE.md)
- [Test Reference](TEST_REFERENCE.md) - Comprehensive test catalog

**External**:
- [pytest Documentation](https://docs.pytest.org/)
- [Python Testing with pytest](https://pragprog.com/titles/bopytest/)

---

**Last Updated**: December 27, 2025
**Maintained By**: AURORA Development Team
**Next Review**: Quarterly (March 2026)
