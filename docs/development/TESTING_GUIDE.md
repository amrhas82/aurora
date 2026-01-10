# Aurora Testing Guide

This document provides comprehensive guidelines for writing, organizing, and maintaining tests in the Aurora project.

## Table of Contents

- [Import Patterns](#import-patterns)
- [Test Classification](#test-classification)
- [Test Pyramid](#test-pyramid)
- [Decision Tree](#decision-tree)
- [Examples](#examples)
- [Best Practices](#best-practices)
- [Markers](#markers)
- [Migration Lessons Learned](#migration-lessons-learned)

---

## Import Patterns

Aurora uses **underscore-separated package names** (`aurora_*`) instead of dot-separated (`aurora.*`).

### Correct Import Patterns ✅

```python
# Core packages
from aurora_core.memory import MemoryStore
from aurora_core.activation import calculate_activation

# Planning
from aurora_planning.schemas import Plan, Task, Modification
from aurora_planning.manager import PlanManager

# CLI
from aurora_cli.commands import plan_group, query_command
from aurora_cli.config import load_config

# Reasoning (SOAR)
from aurora_reasoning.soar import SOARPipeline
from aurora_reasoning.operators import Operator

# Context/Code
from aurora_context_code.semantic import SemanticAnalyzer
from aurora_context_code.chunking import ChunkStore
```

### Incorrect Import Patterns ❌

```python
# WRONG - dot-separated (legacy pattern)
from aurora.memory import MemoryStore       # ❌ Will fail
from aurora.planning import PlanManager     # ❌ Will fail
from aurora.cli import query_command        # ❌ Will fail

# WRONG - mixed patterns
from aurora.core.memory import MemoryStore  # ❌ Will fail
from aurora_core import memory as mem       # ⚠️  Works but inconsistent
```

### Why Underscore Separation?

1. **Python namespace package compatibility**: Avoids conflicts with implicit namespace packages
2. **Clearer package boundaries**: Each `aurora_*` package is independent
3. **Easier migration**: No nested package resolution issues
4. **Better IDE support**: Autocomplete works more reliably

### Pre-Commit Hook Validation

Import patterns are validated automatically via pre-commit hook:

```yaml
# .pre-commit-config.yaml
- id: validate-imports
  name: Validate Aurora import patterns
  entry: python scripts/validate_imports.py
  language: system
  pass_filenames: true
  types: [python]
```

**What it checks:**
- Detects old `aurora.*` import patterns
- Provides line-by-line error messages
- Suggests correct `aurora_*` replacements
- Blocks commits with invalid imports

**Testing the hook:**
```bash
# Try to commit file with old import
echo "from aurora.memory import Store" > test.py
git add test.py
git commit -m "test"  # Will fail with clear error message
```

### Migration Guide

If you encounter old import patterns:

1. **Find all occurrences**:
   ```bash
   grep -r "from aurora\." packages/ tests/
   ```

2. **Replace systematically**:
   ```bash
   # Use migration script
   python scripts/migrate_imports.py --path packages/
   python scripts/migrate_imports.py --path tests/
   ```

3. **Verify tests pass**:
   ```bash
   pytest --collect-only  # Verify no collection errors
   pytest tests/          # Verify all tests pass
   ```

4. **Commit changes**:
   ```bash
   git add -A
   git commit -m "fix(imports): migrate from aurora.* to aurora_* pattern"
   ```

---

## Test Classification

Aurora uses a three-tier test classification system based on scope, dependencies, and execution speed.

### Unit Tests (`tests/unit/`)

**Purpose:** Verify individual components in isolation

**Characteristics:**
- ✅ Tests a single function, class, or module
- ✅ Uses dependency injection with mocks/stubs
- ✅ No I/O operations (no disk, network, database)
- ✅ Deterministic (same input → same output)
- ✅ Fast execution (< 1 second per test)
- ✅ No external dependencies

**Location:** `tests/unit/`

**When to Write Unit Tests:**
- Testing pure functions (calculations, transformations)
- Testing class methods with mocked dependencies
- Testing business logic in isolation
- Testing error handling and edge cases
- Testing utility functions

---

### Integration Tests (`tests/integration/`)

**Purpose:** Verify multiple components working together

**Characteristics:**
- ✅ Tests multiple components/modules interacting
- ✅ May use real implementations (SQLiteStore, file system)
- ✅ May spawn subprocesses or use temporary resources
- ✅ Isolated state (uses tmp_path, mock databases)
- ✅ Moderate execution time (< 10 seconds per test)
- ✅ Tests component contracts and interfaces

**Location:** `tests/integration/`

**When to Write Integration Tests:**
- Testing database operations (with in-memory or temp DBs)
- Testing multiple modules working together
- Testing subprocess spawning and communication
- Testing file system operations (with tmp_path)
- Testing component boundaries and contracts
- Testing configuration loading and validation

---

### End-to-End (E2E) Tests (`tests/e2e/`)

**Purpose:** Verify complete user workflows

**Characteristics:**
- ✅ Tests complete user journeys/workflows
- ✅ Uses real CLI commands and tools
- ✅ May use real databases, files, and configurations
- ✅ Tests from user's perspective
- ✅ Longer execution time (< 60 seconds per test)
- ✅ Includes setup and cleanup procedures

**Location:** `tests/e2e/`

**When to Write E2E Tests:**
- Testing complete CLI workflows
- Testing multi-step user scenarios
- Testing system initialization and setup
- Testing real-world use cases
- Testing interaction between all system components
- Validating user-facing functionality

---

## Test Pyramid

Aurora follows the **60/30/10 test pyramid** distribution:

```
        /\
       /  \
      / E2E \ (10% - ~400 tests)
     /______\
    /        \
   /  INTEG   \ (30% - ~1200 tests)
  /____________\
 /              \
/      UNIT      \ (60% - ~2400 tests)
/__________________\
```

**Target Distribution:**
- **60%** Unit Tests: Fast, focused, isolated
- **30%** Integration Tests: Component interactions
- **10%** E2E Tests: Complete workflows

**Why This Distribution?**
- Unit tests are fast and provide immediate feedback
- Integration tests catch interface issues
- E2E tests validate real-world scenarios
- Pyramid ensures fast test suites and quick debugging

---

## Decision Tree

Use this decision tree to classify your test:

```
┌─────────────────────────────────────┐
│ Does the test use real CLI commands │
│ or test a complete user workflow?   │
└──────────────┬──────────────────────┘
               │
         ┌─────┴─────┐
         │    YES    │ → E2E Test (tests/e2e/)
         └───────────┘
               │
         ┌─────┴─────┐
         │     NO    │
         └─────┬─────┘
               │
┌──────────────┴───────────────────────┐
│ Does the test spawn subprocesses OR  │
│ use SQLiteStore/filesystem with      │
│ tmp_path OR test multiple components?│
└──────────────┬───────────────────────┘
               │
         ┌─────┴─────┐
         │    YES    │ → Integration Test (tests/integration/)
         └───────────┘
               │
         ┌─────┴─────┐
         │     NO    │
         └─────┬─────┘
               │
┌──────────────┴───────────────────────┐
│ Does the test mock all dependencies  │
│ and test a single component?         │
└──────────────┬───────────────────────┘
               │
         ┌─────┴─────┐
         │    YES    │ → Unit Test (tests/unit/)
         └───────────┘
               │
         ┌─────┴─────┐
         │     NO    │ → Reclassify using criteria above
         └───────────┘
```

---

## Examples

### Unit Test Examples

#### Example 1: Pure Function Test
```python
# tests/unit/core/test_activation_formulas.py
def test_base_level_learning_with_zero_references():
    """Test BLL calculation when chunk has never been referenced."""
    result = calculate_base_level_learning(references=[], decay=0.5)
    assert result == float('-inf')  # Undefined activation
```

#### Example 2: Class Method with Mocked Dependencies
```python
# tests/unit/soar/test_phase_route.py
def test_route_to_correct_agent(mock_agent_registry):
    """Test routing logic selects correct agent based on task type."""
    router = TaskRouter(agent_registry=mock_agent_registry)
    task = Task(type="code_analysis")

    agent = router.route(task)

    assert agent.name == "code-analyzer"
    mock_agent_registry.get_agent.assert_called_once_with("code_analysis")
```

#### Example 3: Error Handling Test
```python
# tests/unit/core/test_store_base.py
def test_store_raises_error_on_invalid_chunk_id():
    """Test Store raises ChunkNotFoundError for invalid IDs."""
    store = MemoryStore()

    with pytest.raises(ChunkNotFoundError, match="Chunk 'invalid' not found"):
        store.get_chunk("invalid")
```

#### Example 4: Edge Case Test
```python
# tests/unit/aurora_memory/test_parsing_logic.py
def test_parse_chunk_with_empty_content():
    """Test parser handles empty content gracefully."""
    chunk = parse_chunk(content="", chunk_type="code")

    assert chunk.content == ""
    assert chunk.tokens == []
    assert chunk.metadata == {}
```

#### Example 5: Deterministic Business Logic
```python
# tests/unit/planning/test_id_generator.py
def test_generate_plan_id_format():
    """Test plan ID follows expected format: NNNN-kebab-case."""
    plan_id = generate_plan_id("Add User Authentication")

    assert re.match(r'^\d{4}-[a-z-]+$', plan_id)
    assert plan_id == "0001-add-user-authentication"
```

---

### Integration Test Examples

#### Example 1: Database Operations
```python
# tests/integration/test_memory_store_contract.py
def test_store_persist_and_retrieve(tmp_path):
    """Test SQLiteStore can persist and retrieve chunks."""
    db_path = tmp_path / "test.db"
    store = SQLiteStore(db_path=db_path)

    chunk = CodeChunk(content="def foo(): pass", file_path="test.py")
    chunk_id = store.add_chunk(chunk)

    retrieved = store.get_chunk(chunk_id)
    assert retrieved.content == chunk.content
```

#### Example 2: Multiple Components Interacting
```python
# tests/integration/test_planning_workflow.py
def test_plan_creation_and_task_generation(tmp_path):
    """Test plan creation followed by task generation."""
    plan_manager = PlanManager(project_root=tmp_path)
    task_generator = TaskGenerator()

    plan = plan_manager.create_plan("Feature X")
    tasks = task_generator.generate_tasks(plan)

    assert len(tasks) > 0
    assert all(task.plan_id == plan.id for task in tasks)
```

#### Example 3: Subprocess Usage
```python
# tests/integration/test_git_extractor.py
def test_extract_file_history_using_git(tmp_git_repo):
    """Test GitExtractor calls git subprocess correctly."""
    extractor = GitExtractor(repo_path=tmp_git_repo)

    history = extractor.get_file_history("README.md")

    assert len(history) > 0
    assert all(commit.file_path == "README.md" for commit in history)
```

#### Example 4: File System Operations
```python
# tests/integration/test_index_rebuild.py
def test_rebuild_index_from_filesystem(tmp_path):
    """Test index rebuild scans filesystem and rebuilds correctly."""
    # Create test files
    (tmp_path / "file1.py").write_text("content1")
    (tmp_path / "file2.py").write_text("content2")

    indexer = Indexer(root=tmp_path)
    indexer.rebuild()

    assert indexer.count() == 2
```

#### Example 5: Component Boundary Test
```python
# tests/integration/test_cli_contract.py
def test_cli_formatter_output_contract():
    """Test CLI formatter produces expected output format."""
    formatter = CLIFormatter()
    data = {"plans": [{"id": "0001", "name": "Test"}]}

    output = formatter.format_plan_list(data)

    assert "ID:" in output
    assert "0001" in output
    assert "Test" in output
```

---

### E2E Test Examples

#### Example 1: Complete CLI Workflow
```python
# tests/e2e/test_full_memory_workflow.py
def test_init_learn_search_query_workflow(tmp_path):
    """Test complete memory workflow: init → learn → search → query."""
    os.chdir(tmp_path)

    # Step 1: Initialize
    result = subprocess.run(["aur", "init"], capture_output=True)
    assert result.returncode == 0

    # Step 2: Create test file
    (tmp_path / "test.py").write_text("def hello(): pass")

    # Step 3: Learn from file
    result = subprocess.run(["aur", "learn", "test.py"], capture_output=True)
    assert result.returncode == 0

    # Step 4: Search
    result = subprocess.run(["aur", "search", "hello"], capture_output=True)
    assert b"test.py" in result.stdout

    # Step 5: Query
    result = subprocess.run(["aur", "query", "what functions exist?"], capture_output=True)
    assert result.returncode == 0
```

#### Example 2: Multi-Step User Journey
```python
# tests/e2e/test_planning_workflow.py
def test_create_edit_archive_plan_workflow(tmp_path):
    """Test complete planning workflow: create → edit → archive."""
    os.chdir(tmp_path)
    subprocess.run(["aur", "init"])

    # Create plan
    result = subprocess.run(
        ["aur", "plan", "create", "Add Feature X"],
        capture_output=True
    )
    assert result.returncode == 0
    plan_id = extract_plan_id(result.stdout)

    # Edit plan (add tasks)
    edit_plan_file(tmp_path / ".aurora/plans" / plan_id / "tasks.md")

    # Archive plan
    result = subprocess.run(["aur", "plan", "archive", plan_id], capture_output=True)
    assert result.returncode == 0
    assert (tmp_path / ".aurora/plans/archive").exists()
```

#### Example 3: System Initialization
```python
# tests/e2e/test_e2e_new_user_workflow.py
def test_new_user_first_time_setup(tmp_path):
    """Test complete first-time user setup and first query."""
    os.chdir(tmp_path)

    # New user runs init
    result = subprocess.run(["aur", "init"], capture_output=True)
    assert result.returncode == 0
    assert b"Aurora initialized" in result.stdout

    # Verify directory structure created
    assert (tmp_path / ".aurora").exists()
    assert (tmp_path / ".aurora/memory.db").exists()

    # New user makes first query
    result = subprocess.run(
        ["aur", "query", "How do I use Aurora?"],
        capture_output=True
    )
    assert result.returncode == 0
```

---

## Best Practices

### General Guidelines

1. **One Assertion Per Concept**: Each test should verify one specific behavior
2. **Descriptive Names**: Test names should describe what is being tested and expected outcome
3. **AAA Pattern**: Arrange (setup) → Act (execute) → Assert (verify)
4. **Independent Tests**: Tests should not depend on execution order
5. **Deterministic**: Same input should always produce same output
6. **Fast Feedback**: Prioritize fast tests for quick feedback loops

### Unit Test Best Practices

- Mock all external dependencies (databases, APIs, file system)
- Use dependency injection to make mocking easier
- Test edge cases and error conditions
- Aim for 100% branch coverage of critical logic
- Keep tests simple and focused

### Integration Test Best Practices

- Use `tmp_path` fixture for file system operations
- Use in-memory databases when possible (SQLite `:memory:`)
- Clean up resources in teardown or use fixtures with cleanup
- Test component contracts and interfaces
- Verify error handling at component boundaries

### E2E Test Best Practices

- Test real user workflows, not implementation details
- Include setup and teardown for each test
- Use realistic test data
- Verify user-visible outputs
- Keep E2E tests minimal (expensive to maintain)

---

## Markers

Aurora uses minimal, essential markers:

### `@pytest.mark.ml`
Tests requiring ML dependencies (torch, transformers). Skipped if dependencies not installed.

```python
@pytest.mark.ml
def test_embedding_generation():
    """Test requires torch and sentence-transformers."""
    pass
```

### `@pytest.mark.slow`
Tests with runtime > 5 seconds. Used to track optimization opportunities.

```python
@pytest.mark.slow
def test_large_index_rebuild():
    """This test processes 10k files and takes ~8 seconds."""
    pass
```

### `@pytest.mark.real_api`
Tests calling external APIs (costs money, requires API keys). Skipped in CI.

```python
@pytest.mark.real_api
def test_anthropic_api_integration():
    """Makes real API call to Anthropic (costs $)."""
    pass
```

---

## Migration Guide

When reclassifying tests:

1. **Read the test**: Understand what it's testing
2. **Apply decision tree**: Use the flowchart above
3. **Check dependencies**: Look for subprocess, SQLiteStore, filesystem usage
4. **Move file**: `git mv tests/unit/foo.py tests/integration/foo.py`
5. **Update imports**: Ensure relative imports still work
6. **Run test**: Verify test still passes after move
7. **Commit**: Make granular commits per batch

---

## Running Tests

```bash
# Run all tests
pytest

# Run only unit tests
pytest tests/unit/

# Run only integration tests
pytest tests/integration/

# Run only E2E tests
pytest tests/e2e/

# Skip slow and ML tests
pytest -m "not slow and not ml"

# Skip tests requiring API keys
pytest -m "not real_api"

# Run with coverage
pytest --cov=packages --cov-report=html

# Run specific test file
pytest tests/unit/core/test_store_memory.py

# Run specific test
pytest tests/unit/core/test_store_memory.py::test_add_chunk
```

---

## Troubleshooting

### Common Issues

**Import errors after moving test:**
- Update relative imports in the test file
- Ensure `__init__.py` exists in new directory

**Test fails after reclassification:**
- Check if test assumed specific working directory
- Verify fixtures are still accessible
- Check if test dependencies changed

**Test collection errors:**
- Ensure test file starts with `test_`
- Ensure test functions start with `test_`
- Check for syntax errors in test file

---

## Further Reading

- [Pytest Documentation](https://docs.pytest.org/)
- [Test Pyramid](https://martinfowler.com/articles/practical-test-pyramid.html)
- [Aurora Architecture](./ARCHITECTURE.md)

---

## Migration Lessons Learned

These lessons were learned during the **January 2026 Testing Infrastructure Overhaul** (tasks-0023), which restored a broken test suite and improved testing practices.

### What Went Wrong (December 2025)

1. **No Baseline Measurement**
   - Started refactoring without documenting test count or coverage
   - Made it impossible to measure progress or detect regressions
   - **Lesson**: Always establish baseline before any refactoring

2. **Bulk Changes Without Verification**
   - Applied all import changes at once (73 broken files)
   - Couldn't isolate which change caused failures
   - **Lesson**: Work in small batches with verification between each

3. **Incomplete Import Migration**
   - Migration script missed edge cases in test files
   - Some files had mixed old/new patterns
   - **Lesson**: Use dry-run mode, review output, test incrementally

4. **No Pre-Commit Validation**
   - Regressions not caught until CI failed
   - Wasted time debugging in CI instead of locally
   - **Lesson**: Install pre-commit hooks early, validate patterns locally

5. **Test Classification Drift**
   - Integration tests accumulated in `tests/unit/`
   - Test pyramid became inverted (97.5% unit, 2% integration)
   - Slow tests in unit directory slowed down development
   - **Lesson**: Enforce classification criteria, audit quarterly

6. **Marker Bloat**
   - 14 markers defined, only ~5% actually used
   - Redundant markers (`@pytest.mark.unit` in `tests/unit/`)
   - Cognitive overhead with unclear purpose
   - **Lesson**: Keep markers minimal and essential (3 is enough)

### What Worked Well (January 2026)

1. **Dry-Run Mode First**
   - Migration scripts showed changes before applying
   - Caught false positives and edge cases
   - Built confidence before making real changes
   - **Tool**: `python scripts/migrate_imports.py --dry-run`

2. **Batch Migration with Verification**
   - Applied changes in small batches (5-10 files)
   - Ran `pytest --collect-only` after each batch
   - Isolated failures to specific batches
   - **Pattern**: Apply → Verify → Commit → Repeat

3. **Granular Git Commits**
   - One commit per batch or logical change
   - Easy to rollback individual changes
   - Clear audit trail of what changed when
   - **Pattern**: `git commit -m "fix(tests): migrate batch 1 (10 files)"`

4. **Parallel CI Strategy**
   - Created new CI workflow alongside legacy
   - Validated changes without breaking existing workflow
   - Zero downtime during migration
   - **Files**: `testing-infrastructure-new.yml` ran in parallel

5. **Verification Gates Between Phases**
   - Required explicit verification before proceeding
   - Forced documentation of progress
   - Prevented rushing ahead before verifying stability
   - **Example**: Gate 1 (CI green) → Gate 2 (pyramid correct) → etc.

6. **Automation Scripts with Safety**
   - All scripts support `--dry-run` and `--help`
   - Exit with non-zero on errors (fail fast)
   - Provide actionable error messages
   - **Scripts**: `validate_imports.py`, `classify_tests.py`, `migrate_tests.py`

7. **Pre-Commit Hooks for Prevention**
   - Installed hooks to prevent regressions
   - Validate imports, test classification, marker usage
   - Fast feedback (<3s total runtime)
   - Catches issues before commit, not in CI
   - **Config**: `.pre-commit-config.yaml`

8. **Comprehensive Documentation**
   - Created migration checklist for future refactorings
   - Documented lessons learned in detail
   - Updated TESTING.md with new patterns
   - Created root cause analysis document
   - **Docs**: `TEST_MIGRATION_CHECKLIST.md`, `ROOT_CAUSE_ANALYSIS_TESTING_BREAKAGE_2025.md`

### Key Principles

1. **Verify at Every Step**
   - Never proceed without confirmation tests still pass
   - Run `pytest --collect-only` after every change
   - Run full test suite after each batch
   - Compare results to baseline

2. **Automate When Possible**
   - Scripts reduce human error
   - Ensure consistency across large codebases
   - Dry-run mode builds confidence
   - Pre-commit hooks prevent regressions

3. **Validate Early and Often**
   - Pre-commit hooks catch issues before CI
   - Local validation faster than CI feedback
   - Failed commit better than failed CI build
   - Shift left: catch errors as early as possible

4. **Document Everything**
   - Migration plans with batch details
   - Test results before/after each phase
   - Lessons learned from failures
   - Clear rollback procedures

5. **Small Batches, Frequent Commits**
   - 5-10 files per batch maximum
   - One logical change per commit
   - Easy to identify what broke
   - Easy to rollback if needed

6. **Parallel Safety Nets**
   - Run new CI alongside legacy
   - Keep backup branches
   - Test in isolation before merging
   - Gradual rollout reduces risk

### Recommendations for Future Work

1. **Quarterly Test Pyramid Audits**
   - Run `scripts/classify_tests.py` every quarter
   - Review pyramid distribution (60/30/10 target)
   - Migrate misclassified tests promptly
   - Track trends over time

2. **Regular Marker Usage Review**
   - Audit marker usage bi-annually
   - Remove unused markers immediately
   - Keep to 3 essential markers only
   - Document purpose of each marker clearly

3. **Pre-Commit Hooks Required**
   - Make pre-commit hooks mandatory for contributors
   - Add hook validation to CI (enforce hooks installed)
   - Keep hook runtime under 5 seconds
   - Update hooks when new patterns emerge

4. **Coverage Monitoring**
   - Track coverage trends in CI
   - Alert on coverage drops >5%
   - Set per-package coverage targets
   - Require tests for new code (review process)

5. **Test Isolation Improvements**
   - Investigate intermittent test failures (see TD-TEST-004)
   - Add proper fixture cleanup
   - Eliminate shared state
   - Add pytest-randomly to catch order dependencies

6. **Integration and E2E Test Expansion**
   - Current pyramid inverted (97.5% / 2% / 0.5%)
   - Target: 60% / 30% / 10%
   - Add 100+ integration tests (see TD-TEST-002)
   - Set up E2E CI with mock LLM provider (see TD-TEST-003)

### Related Documents

- **Migration Checklist**: `/docs/TEST_MIGRATION_CHECKLIST.md` - Step-by-step guide for future refactorings
- **Root Cause Analysis**: `/docs/ROOT_CAUSE_ANALYSIS_TESTING_BREAKAGE_2025.md` - Detailed RCA of 2025 breakage
- **Technical Debt**: `/docs/TESTING_TECHNICAL_DEBT.md` - Current status, coverage metrics, remaining issues
- **tasks-0023**: `/tasks/tasks-0023-prd-testing-infrastructure-overhaul.md` - Full task breakdown and progress

---

**Last Updated:** 2026-01-06
**Maintained By:** Aurora Team
