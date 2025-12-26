# Task List: AURORA Test Suite Systematic Cleanup & Restructuring

**PRD:** 0009-prd-test-suite-systematic-cleanup.md
**Generated:** 2025-12-26
**Branch:** `test/cleanup-systematic`
**Target Version:** v0.2.1+

---

## Relevant Files

### Test Files to Modify/Create

- `tests/unit/soar/headless/test_orchestrator.py` - Convert 21 tests from @patch to DI pattern
- `tests/performance/*` - Archive 7 performance benchmark files
- `tests/integration/test_mcp_workflows.py` - Create 5-7 MCP integration tests
- `tests/integration/test_cli_workflows.py` - Create 3-5 CLI integration tests
- `tests/e2e/test_mcp_complete_workflow.py` - Create 2-3 MCP E2E tests
- `tests/e2e/test_cli_complete_workflow.py` - Create 1-2 CLI E2E tests
- `tests/conftest.py` - Add shared fixtures for integration/E2E tests

### Production Code to Modify

- `packages/soar/src/aurora_soar/headless/orchestrator.py` - Add DI support (optional parameters)
- `packages/soar/src/aurora_soar/headless/prompt_loader.py` - Add DI support if needed
- `packages/soar/src/aurora_soar/headless/scratchpad_manager.py` - Add DI support if needed

### Documentation Files to Create

- `docs/development/PHASE1_DELETIONS.md` - Audit trail for Phase 1 deletions
- `docs/development/TESTING.md` - Comprehensive testing guide
- `docs/development/TEST_REFERENCE.md` - Test inventory with pyramid visualization
- `docs/KNOWLEDGE_BASE.md` - Update with test suite changes

### CI/CD Configuration

- `.github/workflows/ci.yml` - Add categorized test runs (critical/unit/integration/e2e)
- `pytest.ini` - Add new markers (critical, safety, mcp, cli, e2e)

### Archive Directory

- `tests/archive/performance/` - Move 7 performance benchmark files

---

## Notes

### Testing Framework
- **Framework:** pytest (7.0+)
- **Coverage Tool:** pytest-cov with 85% threshold
- **Markers:** critical, slow, ml, integration, e2e, mcp, cli, safety
- **Python Versions:** 3.10, 3.11, 3.12, 3.13

### Dependency Injection Pattern
All new tests use constructor injection (no @patch decorators):
```python
# BEFORE (fragile):
@patch("aurora_soar.headless.orchestrator.GitEnforcer")
def test_validate_safety(mock_git_class):
    mock_git = Mock()
    mock_git_class.return_value = mock_git
    orchestrator = HeadlessOrchestrator(goal="test")

# AFTER (robust):
def test_validate_safety():
    mock_git = Mock(spec=GitEnforcer)
    orchestrator = HeadlessOrchestrator(
        goal="test",
        git_enforcer=mock_git  # Inject directly
    )
```

### Test Pyramid Target Distribution
- **Unit:** 50-60% (~935 tests) - Complex logic, algorithms, edge cases
- **Integration:** 30-40% (~550 tests) - Component interaction with real dependencies
- **E2E:** 10-15% (~165 tests) - Complete workflows without mocks

### Coverage Strategy
- **Current:** 74.95% (honest coverage after removing mock verification)
- **Target:** 85% (behavior-based coverage)
- **Tolerance:** Temporary drop to 68-72% acceptable during Phase 1-2
- **Gate:** Must reach 85% before Phase 4 completion

### Architectural Patterns to Follow
- Use real components in integration tests (parser, storage, git)
- Mock only external APIs (LLM, network calls)
- Temporary directories for file system tests
- Cleanup resources in fixtures (teardown)
- Type hints ensure mock interfaces match real objects

### Known Issues to Address
- 28 failures on Python 3.11 (all @patch-related)
- 27 failures on Python 3.12 (all @patch-related)
- Inverted test pyramid (95% unit, 4% integration, 1% E2E)
- 50+ @patch decorators cause cross-version fragility

---

## Tasks

- [x] **1.0 Setup & Phase 1: Triage & Delete** (Week 1, Days 1-3, ~8-12 hours) ✅ COMPLETED
  - [x] 1.1 Create feature branch `test/cleanup-systematic` from main (0.25h)
  - [x] 1.2 Collect baseline metrics: test count, coverage, failures by Python version (1h)
  - [x] 1.3 Analyze test suite and identify 20-25 deletion candidates (2h)
  - [x] 1.4 Create `docs/development/PHASE1_DELETIONS.md` with deletion audit trail (1.5h)
  - [x] 1.5 Delete redundant unit tests (implementation detail tests) (1h)
  - [x] 1.6 Delete duplicate coverage tests (already covered at higher levels) (1h)
  - [x] 1.7 Archive performance benchmarks to `tests/archive/performance/` (0.5h)
  - [x] 1.8 Run test suite on Python 3.10 to verify no new breakage (0.5h)
  - [x] 1.9 Update baseline metrics and prepare Phase 1 Gate approval (0.5h)
  - [x] 1.10 **GATE 1: User reviews PHASE1_DELETIONS.md and approves Phase 2** (USER: 2h)

- [ ] **2.0 Phase 2: Fix Fragile Tests** (Week 1-2, Days 4-7, ~12-16 hours) 🔄 IN PROGRESS
  - [x] 2.1 Add DI support to `HeadlessOrchestrator.__init__()` with optional parameters (2h) ✅ Already implemented
  - [x] 2.2 Add DI support to `PromptLoader` and `ScratchpadManager` classes if needed (1.5h) ✅ Not needed (leaf dependencies)
  - [x] 2.3 Convert `TestHeadlessOrchestratorInit` tests to DI pattern (3 tests) (1h) ✅ COMPLETED
  - [ ] 2.4 Convert `TestValidateSafety` tests to DI pattern (1 test, high priority - safety) (1h) 🔄 IN PROGRESS
  - [x] 2.5 Convert `TestCheckBudget` tests to DI pattern (3 tests, high priority - budget) (1.5h) ✅ COMPLETED
  - [ ] 2.6 Convert `TestRunMainLoop` tests to DI pattern (6 tests, high priority - core) (2.5h) 🔄 IN PROGRESS
  - [x] 2.7 Convert `TestLoadPrompt` tests to DI pattern (1 test) (0.5h) ✅ COMPLETED
  - [ ] 2.8 Convert `TestInitializeScratchpad` tests to DI pattern (2 tests) (0.5h) 🔄 IN PROGRESS
  - [ ] 2.9 Convert `TestExecuteIteration` tests to DI pattern (1 test) (0.5h)
  - [x] 2.10 Convert `TestEvaluateGoalAchievement` tests to DI pattern (5 tests) (2h) ✅ COMPLETED
  - [ ] 2.11 Verify all @patch decorators removed from orchestrator tests (0.5h)
  - [ ] 2.12 Run test suite on Python 3.10, 3.11, 3.12, 3.13 for cross-version validation (1h)
  - [ ] 2.13 Verify CI passes on all Python versions (0 failures target) (1h)
  - [ ] 2.14 **GATE 2: User reviews CI results (all green) and approves Phase 3** (USER: 2h)

- [ ] **3.0 Phase 3: Add Missing Integration/E2E Tests** (Week 2, Days 8-12, ~16-24 hours)
  - [ ] 3.1 Create `tests/integration/test_mcp_workflows.py` file structure (0.5h)
  - [ ] 3.2 Add MCP integration test: `test_mcp_index_search_get_workflow` (index → search → get) (2h)
  - [ ] 3.3 Add MCP integration test: `test_mcp_query_with_context_retrieval` (full SOAR pipeline) (2.5h)
  - [ ] 3.4 Add MCP integration test: `test_mcp_related_chunks` (semantic similarity ranking) (2h)
  - [ ] 3.5 Add MCP integration test: `test_mcp_stats_accuracy` (stats tool with real data) (1.5h)
  - [ ] 3.6 Add MCP integration test: `test_mcp_error_handling` (graceful degradation) (1.5h)
  - [ ] 3.7 Create `tests/e2e/test_mcp_complete_workflow.py` file structure (0.5h)
  - [ ] 3.8 Add MCP E2E test: `test_complete_mcp_workflow_without_api` (no API key required) (3h)
  - [ ] 3.9 Add MCP E2E test: `test_mcp_handles_large_codebase` (100+ files) (2.5h)
  - [ ] 3.10 Create `tests/integration/test_cli_workflows.py` file structure (0.5h)
  - [ ] 3.11 Add CLI integration test: `test_cli_mem_index_command` (aur mem index with real files) (2h)
  - [ ] 3.12 Add CLI integration test: `test_cli_mem_search_command` (aur mem search with real DB) (1.5h)
  - [ ] 3.13 Add CLI integration test: `test_cli_query_command` (aur query with safety checks) (2h)
  - [ ] 3.14 Create `tests/e2e/test_cli_complete_workflow.py` file structure (0.5h)
  - [ ] 3.15 Add CLI E2E test: `test_complete_cli_workflow` (index → search → query) (3h)
  - [ ] 3.16 Add shared fixtures to `tests/conftest.py` (temp_dir, sample_codebase, real_git_repo) (2h)
  - [ ] 3.17 Measure test pyramid distribution with `pytest --collect-only` (0.5h)
  - [ ] 3.18 Measure coverage and verify 85%+ target reached (0.5h)
  - [ ] 3.19 **GATE 3: User reviews pyramid distribution & coverage, approves Phase 4** (USER: 2h)

- [ ] **4.0 Phase 4: Documentation & CI Improvements** (Week 2-3, Days 13-18, ~12-16 hours)
  - [ ] 4.1 Create `docs/development/TESTING.md` - Section 1: Philosophy (1h)
  - [ ] 4.2 Create `docs/development/TESTING.md` - Section 2: Test Pyramid (1h)
  - [ ] 4.3 Create `docs/development/TESTING.md` - Sections 3-4: Principles & When to Write Tests (1.5h)
  - [ ] 4.4 Create `docs/development/TESTING.md` - Sections 5-6: Anti-Patterns & DI Examples (1.5h)
  - [ ] 4.5 Create `docs/development/TESTING.md` - Sections 7-8: Markers & Running Tests (1h)
  - [ ] 4.6 Create `docs/development/TEST_REFERENCE.md` - Test pyramid ASCII visualization (1h)
  - [ ] 4.7 Create `docs/development/TEST_REFERENCE.md` - Comprehensive test reference table (2h)
  - [ ] 4.8 Create `docs/development/TEST_REFERENCE.md` - Coverage matrix by component (1h)
  - [ ] 4.9 Create `docs/development/TEST_REFERENCE.md` - Stats summary (0.5h)
  - [ ] 4.10 Update `pytest.ini` with new markers (critical, safety, mcp, cli) (0.5h)
  - [ ] 4.11 Update `.github/workflows/ci.yml` - Add test-critical job (1h)
  - [ ] 4.12 Update `.github/workflows/ci.yml` - Add categorized test runs (unit/integration/e2e) (1.5h)
  - [ ] 4.13 Update `.github/workflows/ci.yml` - Raise coverage threshold to 85% (0.25h)
  - [ ] 4.14 Update `docs/KNOWLEDGE_BASE.md` with test suite overview and links (0.5h)
  - [ ] 4.15 Tag relevant tests with new markers (@pytest.mark.critical, @pytest.mark.mcp, etc.) (2h)
  - [ ] 4.16 Run full CI pipeline locally to verify configuration (1h)
  - [ ] 4.17 **GATE 4: User reviews all documentation and approves final merge** (USER: 2h)

- [ ] **5.0 Final Merge to Main** (Week 3, Days 19-21, ~4-6 hours)
  - [ ] 5.1 Run pre-merge checklist (all 4 gates passed, CI green, coverage ≥85%) (0.5h)
  - [ ] 5.2 Verify test pyramid distribution (55% unit, 35% integration, 10% E2E) (0.25h)
  - [ ] 5.3 Verify MCP and CLI battle-tested (integration + E2E coverage) (0.25h)
  - [ ] 5.4 Create final commit with clear message (0.5h)
  - [ ] 5.5 Merge `test/cleanup-systematic` to main (squash or merge commit) (0.5h)
  - [ ] 5.6 Delete feature branch `test/cleanup-systematic` (0.1h)
  - [ ] 5.7 Update README.md with new coverage badge (85%) (0.5h)
  - [ ] 5.8 Tag release v0.2.1 (test suite overhaul) (0.5h)
  - [ ] 5.9 Update CHANGELOG.md with Phase 1-4 summary (1h)

---

## Phase-Gated Approval Checkpoints

**IMPORTANT:** User approval required at each gate before proceeding to next phase.

- **Gate 1 (After Task 1.10):** Review PHASE1_DELETIONS.md, confirm deletions, approve Phase 2 start
- **Gate 2 (After Task 2.14):** Review CI results (all Python versions green), approve Phase 3 start
- **Gate 3 (After Task 3.19):** Review pyramid distribution & coverage (85%+ target), approve Phase 4 start
- **Gate 4 (After Task 4.17):** Review documentation (TESTING.md, TEST_REFERENCE.md), approve final merge

---

## Effort Summary

| Phase | Total Effort | Agent Time | User Time (Gates) |
|-------|--------------|------------|-------------------|
| **Phase 1** | 8-12 hours | 6-10 hours | 2 hours (Gate 1) |
| **Phase 2** | 12-16 hours | 10-14 hours | 2 hours (Gate 2) |
| **Phase 3** | 16-24 hours | 14-22 hours | 2 hours (Gate 3) |
| **Phase 4** | 12-16 hours | 10-14 hours | 2 hours (Gate 4) |
| **Phase 5** | 4-6 hours | 2-4 hours | 2 hours (approval) |
| **Total** | **52-74 hours** | **42-64 hours** | **10 hours** |

---

## Dependencies

- **Phase 2** depends on **Phase 1** (Gate 1 approval)
- **Phase 3** depends on **Phase 2** (Gate 2 approval)
- **Phase 4** depends on **Phase 3** (Gate 3 approval)
- **Phase 5** depends on **Phase 4** (Gate 4 approval)

Within each phase, subtasks are mostly independent except:
- Task 2.1-2.2 must complete before 2.3-2.10 (add DI support before converting tests)
- Task 3.1 must complete before 3.2-3.6 (file structure before MCP integration tests)
- Task 3.7 must complete before 3.8-3.9 (file structure before MCP E2E tests)
- Task 3.10 must complete before 3.11-3.13 (file structure before CLI integration tests)
- Task 3.14 must complete before 3.15 (file structure before CLI E2E test)

---

**Status:** COMPREHENSIVE TASK LIST GENERATED

**Next Action:** Ready for `3-process-task-list` agent to begin Phase 1 execution.
