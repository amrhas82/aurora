# Product Requirements Document
# AURORA Test Suite Systematic Cleanup & Restructuring

**PRD Number:** 0009
**Created:** 2025-12-26
**Status:** APPROVED
**Priority:** P0 (Blocker for MVP)
**Timeline:** 2-3 weeks (Phases 1-4)
**Target Version:** v0.2.1+

---

## Executive Summary

AURORA's test suite has become a liability rather than an asset. With 28 failures on Python 3.11/3.12, an inverted test pyramid (95% unit, 4% integration, 1% E2E), and tests that verify implementation details rather than behavior, the CI/CD pipeline generates noise instead of signal. This systematic cleanup transforms testing from a gate-keeper that blocks development into a **first-line-of-defense early warning system** that surfaces real bugs and enables MVP velocity.

**Strategic Importance:**
- **MVP Blocker:** Cannot ship on Python 3.11/3.12 until tests pass
- **Developer Velocity:** Frequent small changes require robust, reliable testing
- **Signal vs Noise:** Eliminate false positives that drown real bugs
- **Sustainable Growth:** Test suite must support, not block, rapid iteration
- **Quality Philosophy:** CI/CD as actionable feedback, not decoration

**Key Outcomes:**
- 85% coverage (up from current 74.95%, target raised from original 84%)
- 0 failures across Python 3.10/3.11/3.12/3.13
- Industry-standard test pyramid: 50-60% unit, 30-40% integration, 10-15% E2E
- MCP and CLI battle-tested (core feature priority)
- Comprehensive test documentation with pyramid visualization and reference table
- Phase-gated execution (4 approval checkpoints for solo developer)

---

## Problem Statement

### Current Pain Points (Quantified)

**1. CI/CD Generates False Positives, Not Actionable Insights**
- **Data:** 28 failures on Python 3.11, 27 on Python 3.12 (all false positives from fragile mocks)
- **Impact:** Developer cannot distinguish real bugs from test infrastructure issues
- **Root Cause:** Over-mocking (50+ `@patch` decorators) tests implementation, not behavior
- **User Quote:** "I don't want to spend time fixing symptoms but use test results as an input and early warnings for things that need fixing"

**2. Inverted Test Pyramid Creates False Confidence**
- **Data:** 95% unit, 4% integration, 1% E2E (should be 55/35/10)
- **Impact:** High coverage (74.95%) but low confidence in real-world behavior
- **Example:** `_validate_safety()` tested in isolation with mocks, never tested with real git
- **Strategic Risk:** MVP will encounter bugs in production that tests never caught

**3. Test Maintenance Burden Blocks Feature Development**
- **Data:** 1,800+ tests, ~20-25 redundant/low-value tests identified
- **Impact:** Every code change breaks multiple tests for wrong reasons
- **Example:** Switching from `@patch` to DI dropped coverage and broke 55+ tests
- **User Context:** "Frequent small changes, bug fixing, tech debt" expected during MVP phase

**4. Coverage Metrics Are Misleading**
- **Data:** Coverage dropped from 84% to 74.95% when removing mocks
- **Reality:** Tests were verifying mock setup, not actual code behavior
- **User Quote:** "The whole sprint is about test cleanup and have proper CI/CD that passes"
- **Goal:** Raise target to 85% with honest, behavior-based coverage

**5. Critical Components Lack Battle-Testing**
- **MCP:** 2 E2E tests for entire framework (user priority: "should be battle tested")
- **CLI:** Light integration testing (user priority: secondary battle-test target)
- **Impact:** Core features may fail in real usage despite passing unit tests

### Cost of Inaction

**Immediate (Week 1-2):**
- Cannot merge PRs on Python 3.11/3.12 (CI blocked)
- Developer time wasted on false positive investigations
- Real bugs masked by noisy test failures

**Short-term (Month 1-2):**
- Test suite becomes unmaintainable (abandoned or ignored)
- MVP launch delayed by CI/CD debugging
- Technical debt accumulates exponentially

**Long-term (Month 3+):**
- Loss of confidence in test suite leads to reduced testing
- Production bugs increase as testing becomes unreliable
- Refactoring becomes impossible (fear of breaking fragile tests)

---

## Goals & Success Metrics

### Primary Goals

**G1: Transform CI/CD into Reliable Early Warning System**
- **Metric:** 0 false positive failures across Python 3.10/3.11/3.12/3.13
- **Philosophy:** "CI/CD pipeline is our first line of defense not a decorator"
- **Validation:** All CI runs pass; failures indicate real bugs requiring immediate attention

**G2: Achieve 85% Honest, Behavior-Based Coverage**
- **Metric:** 85% coverage (raised from current 74.95% and original 84% target)
- **Constraint:** Coverage may drop temporarily during transition (acceptable)
- **Quality:** Every percentage point represents real behavior, not mock verification

**G3: Implement Industry-Standard Test Pyramid**
- **Target Distribution:**
  - Unit: 50-60% (complex logic, algorithms, edge cases)
  - Integration: 30-40% (component interaction, real dependencies)
  - E2E: 10-15% (complete workflows, user journeys)
- **Current:** 95% unit, 4% integration, 1% E2E (INVERTED)
- **User Quote:** "Overall the pyramid testing needs to be adjusted according to industry standards to fit our case: units is the base, integration is less, e2e is smaller, no overlaps, no repeat"

**G4: Battle-Test MCP and CLI (Core Features)**
- **MCP Priority:** "MCP is the core that should be battle tested"
- **CLI Priority:** Secondary battle-test target
- **Coverage:** Integration + E2E tests for all critical MCP workflows (index, search, get, query)

**G5: Enable MVP Velocity with Sustainable Testing**
- **Context:** "Frequent small changes, bug fixing, tech debt at first"
- **Requirement:** Test suite supports rapid iteration, doesn't block it
- **Maintenance:** "Me and Claude" - must be maintainable by solo developer

### Success Metrics (Quantitative)

| Metric | Before | After | Status |
|--------|--------|-------|--------|
| **Total Tests** | 1,800+ | 1,650-1,700 | Delete 20-25 low-value + archive perf tests |
| **Python 3.10 Pass Rate** | 100% | 100% | Maintain |
| **Python 3.11 Pass Rate** | ❌ 28 failures | ✅ 100% | CRITICAL FIX |
| **Python 3.12 Pass Rate** | ❌ 27 failures | ✅ 100% | CRITICAL FIX |
| **Coverage** | 74.95% | 85% | +10.05pp increase |
| **Unit Tests** | 95% | 50-60% | Reduce redundancy |
| **Integration Tests** | 4% | 30-40% | Add 50-70 new tests |
| **E2E Tests** | 1% | 10-15% | Add 15-25 new tests |
| **Test Execution Time** | Baseline | -15-20% | Faster feedback loop |
| **@patch Decorators** | 50+ | 0 in new tests | DI pattern only |

### Success Metrics (Qualitative)

**Test Suite Characteristics:**
- ✅ Tests verify behavior, not implementation details
- ✅ Tests pass on Python 3.10/3.11/3.12/3.13 (cross-version compatibility)
- ✅ No `@patch` decorators in new tests (DI pattern enforced)
- ✅ Each test validates one behavior (1:1 mapping)
- ✅ Integration tests use real components (minimal mocking)
- ✅ E2E tests run complete workflows (no mocks except external APIs)

**Developer Experience:**
- ✅ CI failures indicate real bugs requiring immediate action
- ✅ Test categorization enables severity assessment (critical/unit/integration/e2e)
- ✅ Fast feedback: unit tests <30s, integration <2min, full suite <5min
- ✅ Test documentation provides comprehensive reference for maintenance
- ✅ New developers can understand test coverage via pyramid visualization

**Quality Gates:**
- ✅ CI/CD passes = high confidence in merge safety
- ✅ CI/CD fails = actionable signal (not noise)
- ✅ Coverage metrics reflect real behavior testing
- ✅ Test failures provide clear diagnosis of root cause

---

## User Stories

**Solo Developer Perspective:**

**US1: Trustworthy CI/CD Feedback**
> As a solo developer working on MVP features,
> I want CI/CD to pass/fail based on real bugs (not test infrastructure issues),
> So that I can trust test failures as signals requiring immediate action and focus on fixing root causes instead of symptoms.

**Acceptance Criteria:**
- CI runs pass on all Python versions (3.10/3.11/3.12/3.13) when code is correct
- CI failures clearly indicate real bugs with actionable error messages
- No test failures due to mock setup, Python version differences, or implementation detail changes
- Test categorization (critical/unit/integration/e2e) enables severity assessment

**US2: Rapid Feature Iteration Without Test Breakage**
> As a solo developer making frequent small changes during MVP phase,
> I want tests that validate behavior (not implementation),
> So that refactoring and bug fixes don't break unrelated tests and slow down development velocity.

**Acceptance Criteria:**
- Changing internal method names/signatures doesn't break tests (unless behavior changes)
- Refactoring code with DI pattern doesn't reduce coverage
- Tests document expected behavior (living documentation)
- New features require E2E + integration tests (pyramid maintained)

**US3: Confidence in Core Features (MCP & CLI)**
> As a solo developer preparing for MVP launch,
> I want MCP and CLI to be battle-tested with integration and E2E tests,
> So that I have high confidence these core features work in real-world usage scenarios.

**Acceptance Criteria:**
- MCP workflows (index → search → get → query) tested end-to-end with real components
- CLI commands tested with real file system, real git repos, real parsers
- Safety features (git branch protection, budget limits) tested with real dependencies
- Error handling validated in integration tests (not just mocked exceptions)

**US4: Maintainable Test Suite for "Me and Claude"**
> As a solo developer maintaining AURORA long-term,
> I want comprehensive test documentation and clear testing principles,
> So that I (and Claude) can add/update tests consistently without re-learning testing philosophy.

**Acceptance Criteria:**
- TESTING.md documents principles, anti-patterns, and examples
- Test pyramid visualization shows distribution with stats
- Test reference table lists all tests: coverage, behavior, file location, type
- pytest markers categorize tests (critical/slow/ml/integration/e2e)

**US5: Early Warning System for Regressions**
> As a solo developer fixing bugs and adding features,
> I want test failures to warn me about regressions before merging,
> So that I catch bugs early (cheap to fix) instead of in production (expensive to fix).

**Acceptance Criteria:**
- All critical behaviors have test coverage (safety, memory, SOAR, budget)
- Integration tests catch component interaction bugs
- E2E tests validate complete workflows
- Coverage threshold (85%) enforced by CI to prevent regression

---

## Functional Requirements

### FR1: Phase 1 - Triage & Delete (Week 1)

**FR1.1: Identify and Delete Redundant Unit Tests**
- **Requirement:** Delete 10-15 test methods that verify implementation details
- **Criteria:**
  - Tests that verify constructor calls (e.g., `test_init_creates_components`)
  - Tests that check internal method call order
  - Tests that validate query string formatting (not behavior)
  - Tests that verify mock setup (not actual code)
- **Examples from Codebase:**
  - `DELETE: TestHeadlessOrchestratorInit::test_init_creates_components` (tests constructor)
  - `DELETE: TestBuildIterationQuery::test_build_query_truncates_long_scratchpad` (tests formatting)
  - `DELETE: TestBuildIterationQuery::test_build_query_with_prompt_data` (tests implementation)
  - `KEEP: TestBuildIterationQuery::test_build_query_includes_goal` (tests behavior requirement)
- **Validation:** Run `pytest tests/unit/` - no failures from deletions

**FR1.2: Identify and Delete Duplicate Coverage Tests**
- **Requirement:** Delete 5-10 test methods that duplicate coverage at higher levels
- **Criteria:**
  - Private method tested separately AND through public API
  - Behavior already covered by integration/E2E tests
  - Multiple tests for same behavior at different levels
- **Examples from Codebase:**
  - `DELETE: TestValidateSafety::test_validate_safety_success` (covered by TestExecute)
  - `DELETE: TestLoadPrompt::test_load_prompt_success` (covered by integration tests)
- **Validation:** Coverage doesn't drop below 70% after deletions

**FR1.3: Archive Performance Benchmarks**
- **Requirement:** Move `tests/performance/*` to `tests/archive/performance/`
- **Exceptions:** Keep `test_activation_benchmarks.py` (critical algorithm validation)
- **Rationale:** Performance tests are valuable but run manually during optimization work
- **Validation:** Archived tests still runnable with `pytest tests/archive/`

**FR1.4: Document Deletion Decisions**
- **Requirement:** Create PHASE1_DELETIONS.md listing:
  - Test name
  - Deletion reason (implementation detail / duplicate coverage / archived)
  - Replacement coverage (if applicable)
- **Purpose:** Audit trail for restoration if needed

**FR1.5: Phase 1 Gate - Approval Required**
- **Deliverable:** Phase 1 complete branch pushed to `test_cleanup`
- **Metrics:** ~20-25 tests deleted/archived, CI still passing on Python 3.10
- **Approval Checkpoint:** User reviews PHASE1_DELETIONS.md before proceeding to Phase 2

### FR2: Phase 2 - Fix Fragile Tests (Week 1-2)

**FR2.1: Convert @patch Tests to Dependency Injection Pattern**
- **Requirement:** Update 16-20 test methods in `test_orchestrator.py` to use DI
- **Pattern:**
  ```python
  # BEFORE (fragile):
  @patch("aurora_soar.headless.orchestrator.GitEnforcer")
  def test_validate_safety_git_error(self, mock_git_class):
      mock_git = Mock()
      mock_git.validate.side_effect = GitBranchError("...")
      mock_git_class.return_value = mock_git
      orchestrator = HeadlessOrchestrator(...)
      # Fails on Python 3.11/3.12

  # AFTER (robust):
  def test_validate_safety_git_error(self):
      mock_git = Mock()
      mock_git.validate.side_effect = GitBranchError("...")
      orchestrator = HeadlessOrchestrator(..., git_enforcer=mock_git)
      # Works on all Python versions
  ```

**FR2.2: Update Test Classes (Priority Order)**
- **High Priority (Python 3.11/3.12 blockers):**
  1. TestValidateSafety (2 tests) - Safety critical
  2. TestRunMainLoop (6 tests) - Core orchestration
  3. TestCheckBudget (3 tests) - Cost protection
- **Medium Priority:**
  4. TestEvaluateGoalAchievement (5 tests)
  5. TestExecuteIteration (1 test)
- **Low Priority:**
  6. TestLoadPrompt (1 test)
  7. TestInitializeScratchpad (1 test)

**FR2.3: Cross-Version Validation**
- **Requirement:** All updated tests must pass on Python 3.10/3.11/3.12/3.13
- **Validation Commands:**
  ```bash
  python3.10 -m pytest tests/unit/soar/headless/test_orchestrator.py
  python3.11 -m pytest tests/unit/soar/headless/test_orchestrator.py
  python3.12 -m pytest tests/unit/soar/headless/test_orchestrator.py
  python3.13 -m pytest tests/unit/soar/headless/test_orchestrator.py  # if available
  ```
- **Success Criteria:** 0 failures on all versions

**FR2.4: Eliminate @patch Decorators**
- **Requirement:** Remove all `@patch` decorators from orchestrator tests
- **Validation:** `grep -r "@patch" tests/unit/soar/headless/test_orchestrator.py` returns 0 results
- **Exception:** External API mocks (LLM calls) acceptable if clearly documented

**FR2.5: Phase 2 Gate - Approval Required**
- **Deliverable:** All Python versions CI passing
- **Metrics:** 0 @patch decorators, 0 failures on 3.10/3.11/3.12
- **Approval Checkpoint:** User reviews CI results before proceeding to Phase 3

### FR3: Phase 3 - Add Missing Integration/E2E Tests (Week 2)

**FR3.1: Add MCP Integration Tests (Battle-Test Priority #1)**
- **Requirement:** Add 5-7 integration tests for MCP workflows
- **Critical Tests:**
  1. `test_mcp_index_search_integration` - Index codebase → search → verify results
  2. `test_mcp_get_chunk_real_storage` - Real database, real parser, real retrieval
  3. `test_mcp_query_pipeline_no_api_key` - Full SOAR pipeline with mocked LLM
  4. `test_mcp_safety_real_git` - Real git repo, real enforcer, real failure
  5. `test_mcp_budget_enforcement_real_tracker` - Real cost tracking, mocked API
- **Pattern:** Use real components (parser, storage, git), mock only external APIs
- **Validation:** Tests pass without API keys (safety + local functionality)

**FR3.2: Add CLI Integration Tests (Battle-Test Priority #2)**
- **Requirement:** Add 3-5 integration tests for CLI commands
- **Critical Tests:**
  1. `test_cli_mem_index_real_files` - Real file system, real parser, real indexing
  2. `test_cli_mem_search_real_results` - Real database queries, real ranking
  3. `test_cli_query_safety_real_git` - Real git check, real branch validation
  4. `test_cli_verify_health_check` - Real component initialization
- **Pattern:** Use temporary directories, real git repos, real file parsing
- **Validation:** Tests clean up temp resources, no side effects

**FR3.3: Add E2E Workflow Tests**
- **Requirement:** Add 2-3 E2E tests for complete workflows
- **Critical Tests:**
  1. `test_e2e_index_search_query_workflow` - Complete MCP workflow without mocks
  2. `test_e2e_cli_pipeline_from_files` - CLI commands → indexed → searched → queried
  3. `test_e2e_safety_budget_integration` - Git safety + budget limits in real scenario
- **Pattern:** No mocks except external APIs (LLM), real components throughout
- **Validation:** Tests validate end-user value (not internal state)

**FR3.4: Achieve Target Pyramid Distribution**
- **Requirement:** Test distribution after Phase 3 additions:
  - Unit: 50-60% (reduce from 95%)
  - Integration: 30-40% (increase from 4%)
  - E2E: 10-15% (increase from 1%)
- **Calculation:** Add 50-70 integration + 15-25 E2E tests
- **Validation:** Run `pytest --collect-only` and categorize by markers

**FR3.5: Phase 3 Gate - Approval Required**
- **Deliverable:** Test pyramid balanced, MCP/CLI battle-tested
- **Metrics:** 85%+ coverage, pyramid distribution achieved
- **Approval Checkpoint:** User reviews integration/E2E test results before Phase 4

### FR4: Phase 4 - Documentation & CI Improvements (Week 2-3)

**FR4.1: Create Comprehensive TESTING.md Guide**
- **Requirement:** Document testing principles, anti-patterns, examples
- **Sections:**
  1. **Philosophy** - Behavior over implementation, CI/CD as early warning
  2. **Test Pyramid** - Distribution targets, when to use each level
  3. **Principles** - Minimize mocking, prefer real components, integration > unit
  4. **When to Write Tests** - New feature (E2E+integration), bug fix (test-first), complex logic (unit edges)
  5. **Anti-Patterns** - Constructor testing, private method testing, >2 mock dependencies
  6. **DI Pattern Examples** - Code samples for injecting dependencies
  7. **Markers** - How to categorize tests (critical/slow/ml/integration/e2e)
- **Validation:** Document reviewed by user, clear for solo developer maintenance

**FR4.2: Create Test Reference Documentation**
- **Requirement:** Comprehensive test inventory with pyramid visualization
- **Components:**
  1. **Test Pyramid Diagram:**
     ```
            E2E (165 tests, 10%)          ← Complete workflows
           /                    \
      Integration (550 tests, 33%)        ← Component interaction
         /                          \
     Unit (935 tests, 57%)                ← Complex logic only

     Total: 1,650 tests | 85% coverage | 0 failures
     ```
  2. **Test Reference Table:**
     | Test Name | Coverage | Behavior Tested | File Location | Type | Markers |
     |-----------|----------|-----------------|---------------|------|---------|
     | test_mcp_index_search_integration | MCP index→search | Index files, search chunks, verify results | tests/integration/test_mcp_workflows.py | Integration | critical,integration |
     | test_e2e_complete_query_pipeline | SOAR 9-phase | Full query with real components | tests/e2e/test_complete_workflows.py | E2E | e2e,slow |
     | ... | ... | ... | ... | ... | ... |
  3. **Coverage Matrix:**
     | Component | Unit | Integration | E2E | Total Coverage |
     |-----------|------|-------------|-----|----------------|
     | MCP | 45% | 35% | 15% | 95% |
     | CLI | 50% | 30% | 10% | 90% |
     | SOAR | 60% | 25% | 10% | 95% |
     | ACT-R | 70% | 20% | 5% | 95% |
     | Storage | 55% | 30% | 10% | 95% |
  4. **Stats Summary:**
     - Total tests: 1,650
     - Pass rate: 100% (all Python versions)
     - Coverage: 85%
     - Execution time: <5min full suite
     - Maintenance: Solo developer + Claude

**FR4.3: Configure pytest Markers**
- **Requirement:** Add markers to pytest.ini for test categorization
- **Markers:**
  ```ini
  [pytest]
  markers =
      critical: Critical safety/correctness tests (always run first)
      slow: Slow tests >5s (run in nightly builds)
      ml: Requires ML dependencies (skip if not installed)
      integration: Integration tests (component interaction)
      e2e: End-to-end tests (complete workflows)
      mcp: MCP-specific tests (core feature)
      cli: CLI-specific tests (core feature)
      safety: Safety/security tests (git protection, budget limits)
  ```
- **Usage:** Tests tagged with relevant markers for CI categorization
- **Validation:** `pytest --markers` shows all defined markers

**FR4.4: Update CI/CD Configuration**
- **Requirement:** Categorized test runs in `.github/workflows/ci.yml`
- **Test Jobs:**
  ```yaml
  test-critical:
    name: Critical Tests (Fast)
    run: pytest -m "critical and not ml" tests/
    timeout: 2min

  test-unit:
    name: Unit Tests
    run: pytest -m "not ml and not slow" tests/unit/
    timeout: 5min

  test-integration:
    name: Integration Tests
    run: pytest -m "integration and not ml" tests/integration/
    timeout: 10min

  test-e2e:
    name: E2E Tests
    run: pytest -m "e2e and not ml" tests/e2e/
    timeout: 15min

  test-coverage:
    name: Coverage Report
    run: pytest --cov=packages --cov-report=term --cov-fail-under=85
  ```
- **Philosophy:** "If a one word would explain actual problem that would be great"
- **Benefit:** Categorization helps "weight fixes and know bug severity"

**FR4.5: Update Coverage Threshold**
- **Requirement:** Raise coverage threshold to 85% in pytest.ini
- **Configuration:**
  ```ini
  [pytest]
  addopts = --cov=packages --cov-report=term-missing --cov-fail-under=85
  ```
- **Rationale:** Higher bar than original 84%, honest behavior-based coverage
- **Enforcement:** CI fails if coverage drops below 85%

**FR4.6: Phase 4 Gate - Final Approval**
- **Deliverable:** Complete test suite with documentation
- **Metrics:** All gates passed, documentation complete, CI configured
- **Approval Checkpoint:** User reviews final state before merging to main

### FR5: Cross-Cutting Requirements

**FR5.1: Branching Strategy**
- **Branch:** `test_cleanup` (not `test/cleanup-systematic` from original plan)
- **Merge:** Incremental merging per phase after approval gates
- **Protection:** Do not merge to main until all 4 phases complete + approved

**FR5.2: Test Deletion Safety**
- **Archive First:** Move tests to `tests/archive/` before permanent deletion
- **Restoration:** Tests can be restored from archive if needed
- **Documentation:** PHASE1_DELETIONS.md provides audit trail

**FR5.3: Coverage Monitoring**
- **Baseline:** 74.95% before cleanup
- **Target:** 85% after cleanup
- **Tolerance:** Temporary drop acceptable during transition (Phase 1-2)
- **Gate:** Must reach 85% before final merge to main

**FR5.4: Python Version Compatibility**
- **Versions:** 3.10, 3.11, 3.12, 3.13 (if available)
- **Requirement:** All tests pass on all versions
- **Validation:** CI matrix runs all versions in parallel
- **Blocker:** Python 3.11/3.12 failures must be fixed in Phase 2

**FR5.5: No Over-Engineering**
- **Philosophy:** "Don't overengineer - leave details to agent"
- **Focus:** Battle-test MCP and CLI (core features), not every edge case
- **Pragmatism:** 85% coverage is sufficient, 100% is unnecessary

---

## Non-Functional Requirements

### NFR1: Performance

**NFR1.1: Test Execution Speed**
- **Unit Tests:** <30 seconds for full unit test suite
- **Integration Tests:** <2 minutes for full integration test suite
- **E2E Tests:** <3 minutes for full E2E test suite
- **Full Suite:** <5 minutes for all tests (enables fast feedback loop)
- **Rationale:** Solo developer needs rapid iteration, slow tests block velocity

**NFR1.2: Resource Usage**
- **Memory:** <500MB peak during test execution
- **Disk:** <100MB temporary files (cleaned up after tests)
- **CPU:** Tests should not peg CPU (parallel execution acceptable)

**NFR1.3: Test Startup Time**
- **Fixture Loading:** <5 seconds to load all fixtures
- **Database Setup:** <2 seconds to initialize test database
- **File Parsing:** <3 seconds to parse test files with tree-sitter

### NFR2: Maintainability

**NFR2.1: Code Quality**
- **DRY Principle:** Shared fixtures in `conftest.py`, no copy-paste tests
- **Clear Naming:** Test names describe behavior (e.g., `test_git_rejects_main_branch`)
- **Single Assertion:** Each test validates one behavior (exceptions for related checks)
- **Documentation:** Docstrings explain "what" and "why", not "how"

**NFR2.2: Solo Developer Friendly**
- **Context:** "Me and Claude" maintain the test suite
- **Requirement:** Tests must be understandable without domain expertise
- **Examples:** Inline comments for complex setup, clear error messages
- **Documentation:** TESTING.md serves as onboarding guide

**NFR2.3: Minimal External Dependencies**
- **Mocking:** Only mock external APIs (LLM, network calls)
- **Real Components:** Use real parser, storage, git for integration tests
- **Isolation:** Tests don't depend on external services (except documented ML tests)

### NFR3: Reliability

**NFR3.1: Deterministic Results**
- **No Flaky Tests:** Tests pass/fail consistently (no timing issues)
- **Isolation:** Tests don't depend on execution order
- **Cleanup:** Tests clean up temp files, databases, git repos

**NFR3.2: Clear Failure Messages**
- **Context:** Error messages include input values, expected vs actual
- **Debugging:** Stack traces point to root cause (not deep in fixtures)
- **Markers:** Failed tests categorized by severity (critical > integration > unit)

**NFR3.3: Cross-Platform Compatibility**
- **OS:** Tests pass on Linux, macOS, Windows (if applicable)
- **Python:** Tests pass on 3.10/3.11/3.12/3.13
- **CI:** GitHub Actions matrix tests all combinations

### NFR4: Documentation

**NFR4.1: Living Documentation**
- **Test Names:** Self-documenting (e.g., `test_budget_enforcer_blocks_expensive_query`)
- **Docstrings:** Explain expected behavior in plain English
- **Examples:** Test code serves as usage examples for API

**NFR4.2: Test Reference Completeness**
- **Coverage:** Test reference table lists ALL tests (no gaps)
- **Accuracy:** Table updated automatically (script or CI check)
- **Accessibility:** Markdown format, easy to search/filter

**NFR4.3: Testing Guide Clarity**
- **Audience:** Written for junior developers (or future self)
- **Examples:** Concrete code samples, not abstract principles
- **Anti-Patterns:** Show bad examples with explanation (not just theory)

### NFR5: CI/CD Integration

**NFR5.1: Fast Feedback Loop**
- **Critical Tests:** Run first (fail fast on safety issues)
- **Parallel Execution:** Unit/integration/E2E run in parallel
- **Early Exit:** Stop on first failure in critical tests

**NFR5.2: Actionable Failures**
- **Categorization:** Test type (critical/unit/integration/e2e) visible in CI output
- **Severity:** Critical failures highlighted in red, others in yellow
- **Context:** CI comment on PR includes: failed test name, category, error message

**NFR5.3: Coverage Reporting**
- **Threshold:** 85% enforced by CI (build fails if below)
- **Trend:** Coverage badge in README shows current %
- **Report:** Detailed coverage report uploaded as CI artifact

---

## Non-Goals (Out of Scope)

### NG1: Test Generation or Automation Tools
- **Not Building:** Test generation frameworks, property-based testing (hypothesis)
- **Rationale:** Focus on systematic cleanup, not new tooling
- **Exception:** Simple scripts to categorize tests acceptable

### NG2: Performance Optimization Beyond 15-20% Reduction
- **Not Targeting:** <1min full suite, aggressive parallelization
- **Rationale:** 5min full suite sufficient for solo developer
- **Future Work:** Performance optimization separate initiative if needed

### NG3: 100% Coverage or Zero Skipped Tests
- **Not Requiring:** 100% coverage (85% target is sufficient)
- **Accepting:** 14 skipped tests for external APIs (documented)
- **Pragmatism:** Diminishing returns above 85% coverage

### NG4: Migration to Alternative Test Frameworks
- **Not Changing:** pytest as test runner
- **Not Adding:** unittest, nose, behave, etc.
- **Rationale:** pytest is sufficient, migration adds risk without benefit

### NG5: Comprehensive Regression Test Suite for All Historical Bugs
- **Not Requiring:** Test for every bug ever fixed
- **Focusing:** Critical behaviors (safety, memory, SOAR, budget)
- **Rationale:** Pragmatic coverage of core features, not exhaustive history

### NG6: Test Data Management or Fixture Generators
- **Not Building:** Complex fixture generation systems
- **Using:** Simple fixtures in conftest.py, temp files for integration
- **Rationale:** Keep it simple for solo developer maintenance

### NG7: Mutation Testing or Advanced Coverage Metrics
- **Not Implementing:** Mutation testing (pytest-mutpy), branch coverage analysis
- **Rationale:** Line coverage + behavior testing sufficient for MVP
- **Future Work:** Advanced metrics if test suite proves inadequate

### NG8: UI/Visual Testing for CLI Output
- **Not Testing:** CLI output formatting, colors, ASCII art
- **Testing:** CLI functionality (indexing, searching, querying)
- **Rationale:** Focus on behavior, not aesthetics

---

## Design Considerations

### DC1: Dependency Injection Pattern

**Pattern:**
```python
# Production code (constructor DI)
class HeadlessOrchestrator:
    def __init__(
        self,
        goal: str,
        context: Optional[str] = None,
        git_enforcer: Optional[GitEnforcer] = None,  # Injectable
        llm_client: Optional[LLMClient] = None,      # Injectable
        memory_store: Optional[MemoryStore] = None,  # Injectable
    ):
        self.git_enforcer = git_enforcer or GitEnforcer()
        self.llm_client = llm_client or create_default_llm()
        self.memory_store = memory_store or MemoryStore()

# Test code (inject mocks)
def test_validate_safety_git_error():
    mock_git = Mock()
    mock_git.validate.side_effect = GitBranchError("protected branch")

    orchestrator = HeadlessOrchestrator(
        goal="test",
        git_enforcer=mock_git  # Inject mock
    )

    with pytest.raises(GitBranchError):
        orchestrator.execute()
```

**Benefits:**
- Works across Python versions (no `@patch` issues)
- Makes dependencies explicit
- Enables true unit testing (isolate component)
- Simplifies debugging (clear dependency graph)

**Constraints:**
- Requires refactoring production code (add optional parameters)
- All tests must migrate to DI pattern (consistency)
- Mocks must match real interface (type checking helps)

### DC2: Test Fixture Organization

**Structure:**
```
tests/
├── conftest.py              # Shared fixtures (all tests)
├── unit/
│   └── conftest.py         # Unit-specific fixtures
├── integration/
│   └── conftest.py         # Integration-specific fixtures
├── e2e/
│   └── conftest.py         # E2E-specific fixtures
└── fixtures/
    ├── sample_code/        # Real Python files for parsing
    ├── sample_repos/       # Git repos for safety tests
    └── sample_data/        # JSON/YAML test data
```

**Shared Fixtures (tests/conftest.py):**
```python
@pytest.fixture
def temp_dir():
    """Temporary directory, auto-cleanup."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)

@pytest.fixture
def sample_python_file(temp_dir):
    """Real Python file for parser tests."""
    code = "def foo():\n    return 42"
    file_path = temp_dir / "sample.py"
    file_path.write_text(code)
    return file_path

@pytest.fixture
def mock_llm_client():
    """Mock LLM that returns predictable responses."""
    mock = Mock(spec=LLMClient)
    mock.complete.return_value = "Test response"
    return mock
```

**Integration Fixtures (tests/integration/conftest.py):**
```python
@pytest.fixture
def real_git_repo(temp_dir):
    """Real git repo with branches for safety tests."""
    subprocess.run(["git", "init"], cwd=temp_dir)
    subprocess.run(["git", "checkout", "-b", "feature"], cwd=temp_dir)
    return temp_dir

@pytest.fixture
def indexed_codebase(temp_dir, sample_python_files):
    """Codebase indexed with real parser and storage."""
    memory_store = MemoryStore(str(temp_dir / "test.db"))
    parser = PythonParser()

    for file in sample_python_files:
        chunks = parser.parse(file)
        memory_store.store_chunks(chunks)

    return memory_store
```

### DC3: Test Naming Conventions

**Format:** `test_<component>_<behavior>_<condition>`

**Examples:**
- `test_git_enforcer_rejects_main_branch` (unit)
- `test_mcp_index_search_returns_relevant_results` (integration)
- `test_e2e_complete_query_pipeline_without_api_key` (e2e)

**Rules:**
- Use underscores (not camelCase)
- Describe behavior (not implementation)
- Include condition if not obvious (e.g., `_when_file_missing`)
- Keep under 80 characters (readable in CI output)

### DC4: Test Markers Strategy

**Usage:**
```python
@pytest.mark.critical
@pytest.mark.safety
def test_git_enforcer_blocks_main_branch():
    """Critical safety test: must reject main branch."""
    ...

@pytest.mark.integration
@pytest.mark.mcp
def test_mcp_index_search_integration():
    """Integration test for MCP index→search workflow."""
    ...

@pytest.mark.e2e
@pytest.mark.slow
def test_e2e_complete_soar_pipeline():
    """E2E test: full SOAR 9-phase pipeline (slow)."""
    ...
```

**Marker Combinations:**
- `critical` + `safety` = highest priority (run first)
- `integration` + `mcp` = battle-test core feature
- `e2e` + `slow` = run in separate CI job (timeout 15min)
- `ml` = skip if dependencies not installed

### DC5: Existing Components to Leverage

**No UI/UX Work:**
- Tests are code-only (no mockups, no wireframes)
- CLI output formatting not in scope
- Focus on functionality, not aesthetics

**Existing Test Infrastructure:**
- pytest fixtures in `conftest.py` (reuse where possible)
- `tests/fixtures/` directory (sample files, repos)
- CI configuration in `.github/workflows/ci.yml` (extend, don't replace)

**Reusable Components:**
- `MemoryStore` for test databases
- `PythonParser` for parsing test files
- `GitEnforcer` for safety tests
- `MockLLMClient` for SOAR tests

---

## Technical Considerations

### TC1: Dependency Injection Implementation

**Constraints:**
- Must maintain backward compatibility (existing code can't break)
- Optional parameters with defaults (DI is opt-in for tests)
- Type hints for clarity (mypy catches interface mismatches)

**Integration Points:**
- `HeadlessOrchestrator` (main entry point)
- `GitEnforcer` (safety checks)
- `LLMClient` (external API)
- `MemoryStore` (storage layer)

**Suggested Approach (from user):**
- "Leave details to agent" (don't over-specify implementation)
- Focus on enabling DI pattern, not mandating specific design

### TC2: Python Version Compatibility

**Root Cause of Failures:**
- `@patch` decorator behavior changed in Python 3.11/3.12
- Mock object spec validation stricter in newer versions
- Import path resolution differences

**Solution:**
- DI pattern eliminates `@patch` entirely
- Direct mock injection bypasses import resolution issues
- Type hints ensure mock interfaces match real objects

**Validation:**
- CI matrix tests all versions in parallel
- Local testing with `tox` or manual version switching

### TC3: Coverage Calculation

**Current Issue:**
- Coverage dropped from 84% to 74.95% when removing mocks
- False positive coverage from mock verification (not real code)

**Target Approach:**
- 85% coverage from real behavior testing
- Integration/E2E tests exercise real code paths
- Unit tests for complex logic only (not every method)

**Tools:**
- `pytest-cov` for coverage reports
- `coverage.py` for detailed line-by-line analysis
- CI artifact upload for historical tracking

### TC4: Test Categorization

**Pytest Markers:**
- Defined in `pytest.ini`
- Applied via decorators in test code
- Queried in CI with `-m` flag

**CI Jobs:**
- Separate jobs for critical/unit/integration/e2e
- Parallel execution for speed
- Sequential execution for dependencies (e.g., build before test)

**User Philosophy:**
- "If a one word would explain actual problem that would be great"
- Categorization enables "weight fixes and know bug severity"
- CI/CD as "first line of defense not a decorator"

### TC5: Documentation Generation

**Test Reference Table:**
- **Option A:** Manual maintenance (Markdown table in docs/)
- **Option B:** Auto-generate from test code (pytest plugin or script)
- **Recommendation:** Manual for Phase 4, auto-generate in future iteration

**Test Pyramid Visualization:**
- ASCII art in TESTING.md (simple, readable)
- Stats from `pytest --collect-only` output
- Updated manually per phase

**Coverage Matrix:**
- Generate from coverage report (parsing XML/JSON output)
- Script: `scripts/generate_coverage_matrix.py`
- Run in CI, commit updated table to docs/

### TC6: Risk Mitigation Strategies

**Risk:** Deleting useful tests
- **Mitigation:** Archive first, audit trail in PHASE1_DELETIONS.md
- **Recovery:** Restore from `tests/archive/` if needed

**Risk:** Temporary coverage drop below 70%
- **Mitigation:** Work in feature branch, don't merge until 85% reached
- **Acceptance:** User approved temporary drop during transition

**Risk:** Phase 2 introduces new failures
- **Mitigation:** Phase gate - user approval required before Phase 3
- **Rollback:** Git branch allows clean revert if needed

**Risk:** Integration tests too slow (>2min)
- **Mitigation:** Use temp files/databases, parallel execution
- **Optimization:** Profile slow tests, optimize fixtures if needed

**Risk:** E2E tests flaky (timing issues)
- **Mitigation:** Avoid sleep(), use explicit waits or retries
- **Design:** Tests should be deterministic (no randomness)

---

## Testing Strategy

### TS1: What TO Test (Required Coverage)

**Critical Behaviors (MUST HAVE):**
1. **Safety:** Block execution on protected branches (main, master, production)
2. **Safety:** Validate prompt format before execution (prevent injection)
3. **Memory:** Store and retrieve code chunks correctly (round-trip test)
4. **Memory:** ACT-R activation scoring produces correct ranks (deterministic)
5. **SOAR:** 9-phase pipeline executes in order (no phase skipped)
6. **Query:** Context retrieval returns relevant results (semantic search works)
7. **Budget:** Track and limit API costs (prevent runaway spending)
8. **MCP:** Tools work without API keys (local functionality)
9. **Error Handling:** Graceful degradation on failures (no crashes)

**Complex Logic (SHOULD TEST):**
- Algorithm correctness (activation scoring, semantic search)
- Edge cases in parsing/chunking (empty files, syntax errors)
- Budget calculations and limits (overflow, negative values)
- Error recovery logic (retry, fallback, timeout)

**MCP Battle-Testing (User Priority #1):**
- Index codebase (real files, real parser)
- Search chunks (real database, real ranking)
- Get chunk content (real retrieval, real formatting)
- Query pipeline (real SOAR, mocked LLM)
- All workflows without API keys (local mode)

**CLI Battle-Testing (User Priority #2):**
- `aur mem index` (real file system, real indexing)
- `aur mem search` (real database, real results)
- `aur query` (real safety checks, real escalation)
- `aur --verify` (real health check)

### TS2: What NOT to Test (Excluded)

**Implementation Details:**
- Constructor calls (`assert mock_git.called`)
- Internal method call order
- Private method internals (test via public API)
- Query string formatting (test result, not format)
- Mock setup verification

**Already Covered Elsewhere:**
- Behaviors tested at higher level (E2E covers it, skip unit)
- Framework features (pytest, SQLite, tree-sitter)
- Type correctness (mypy handles this)

**User Guidance:**
- "I don't know, ultrathink and decide" (agent has discretion)
- "Don't overengineer" (pragmatic testing, not exhaustive)

### TS3: Test Pyramid Distribution

**Target:**
```
         E2E (165 tests, 10%)          ← Complete workflows
        /                    \
   Integration (550 tests, 33%)        ← Component interaction
      /                          \
   Unit (935 tests, 57%)                ← Complex logic only

Total: 1,650 tests | 85% coverage | 0 failures
```

**Rationale:**
- Unit: Test complex algorithms, edge cases, error conditions
- Integration: Test component interaction with real dependencies
- E2E: Validate complete user workflows without mocks

**User Quote:**
- "Overall the pyramid testing needs to be adjusted according to industry standards to fit our case: units is the base, integration is less, e2e is smaller, no overlaps, no repeat"

### TS4: Mocking Philosophy

**Minimize Mocking:**
- Integration tests: Mock only external APIs (LLM, network)
- E2E tests: Mock only unavoidable external dependencies
- Unit tests: Mock dependencies, but prefer real objects when simple

**DI Pattern:**
- Inject mocks via constructor (not `@patch`)
- Mocks must match real interface (type hints enforce)
- Clear distinction: real vs mock (naming convention)

**Example:**
```python
# GOOD: Minimal mocking, real components
def test_mcp_index_search_integration(temp_dir):
    memory_store = MemoryStore(str(temp_dir / "test.db"))  # Real
    parser = PythonParser()                                 # Real
    # ... test with real components

# BAD: Over-mocking, no confidence
@patch("aurora.core.storage.MemoryStore")
@patch("aurora.context_code.parser.PythonParser")
def test_mcp_index_search_mocked(mock_store, mock_parser):
    # ... tests mock setup, not real behavior
```

### TS5: Test Validation Strategy

**Phase 1 Validation:**
- Run `pytest tests/unit/` - no failures from deletions
- Check coverage: shouldn't drop below 70%
- Review PHASE1_DELETIONS.md - audit trail complete

**Phase 2 Validation:**
- Run pytest on all Python versions: 3.10/3.11/3.12/3.13
- Check for @patch decorators: `grep -r "@patch" tests/` returns 0
- CI status: all versions green

**Phase 3 Validation:**
- Run `pytest --collect-only` - count tests by type
- Check pyramid distribution: 50-60% unit, 30-40% integration, 10-15% E2E
- MCP/CLI coverage: integration + E2E tests exist

**Phase 4 Validation:**
- TESTING.md reviewed and approved by user
- Test reference table complete (all tests listed)
- CI configuration updated and working
- Coverage threshold enforced: 85%

---

## Documentation Requirements

### DR1: TESTING.md (Comprehensive Guide)

**Purpose:** Living documentation for test suite maintenance

**Sections:**

**1. Philosophy**
- CI/CD as first line of defense, not decorator
- Test behavior, not implementation
- Signal over noise (eliminate false positives)
- Integration > unit for confidence

**2. Test Pyramid**
- Target distribution: 50-60% unit, 30-40% integration, 10-15% E2E
- ASCII diagram with stats
- When to use each level
- How to maintain distribution

**3. Testing Principles**
- Minimize mocking (prefer real components)
- Use DI pattern (not @patch)
- Each test = one behavior
- Cross-version compatibility (Python 3.10-3.13)

**4. When to Write Tests**
- New feature: E2E test + integration test (minimum)
- Bug fix: Add failing test first (TDD)
- Complex logic: Unit test for edge cases
- Refactoring: Tests should still pass (if behavior unchanged)

**5. Anti-Patterns to Avoid**
- Testing constructor calls
- Testing private methods directly
- Mocking >2 dependencies
- Testing framework behavior
- Duplicate coverage at multiple levels

**6. DI Pattern Examples**
- Code samples for constructor injection
- Before/after examples (fragile vs robust)
- Type hints for mock interfaces

**7. Markers and Categorization**
- List all pytest markers with descriptions
- Examples of marker usage
- CI job mapping (which markers run in which jobs)

**8. Running Tests Locally**
- Commands for different test types
- Coverage report generation
- Debugging failing tests

**Delivery:** Markdown file in `/home/hamr/PycharmProjects/aurora/docs/development/TESTING.md`

### DR2: Test Reference Documentation

**Purpose:** Comprehensive inventory of test suite for maintenance and onboarding

**Components:**

**1. Test Pyramid Visualization**
```
         E2E (165 tests, 10%)          ← Complete workflows
        /                    \
   Integration (550 tests, 33%)        ← Component interaction
      /                          \
   Unit (935 tests, 57%)                ← Complex logic only

Total: 1,650 tests | 85% coverage | 0 failures

Python Version Compatibility:
✅ Python 3.10: 100% pass
✅ Python 3.11: 100% pass
✅ Python 3.12: 100% pass
✅ Python 3.13: 100% pass

Execution Time:
- Unit: 28s
- Integration: 1m 45s
- E2E: 2m 30s
- Full Suite: 4m 43s
```

**2. Test Reference Table**

| Test Name | Coverage | Behavior Tested | File Location | Type | Markers |
|-----------|----------|-----------------|---------------|------|---------|
| test_git_enforcer_blocks_main_branch | Safety | Git enforcer rejects main/master branches | tests/unit/safety/test_git_enforcer.py | Unit | critical,safety |
| test_mcp_index_search_integration | MCP | Index files → search chunks → verify results | tests/integration/test_mcp_workflows.py | Integration | integration,mcp |
| test_e2e_complete_query_pipeline | SOAR | Full 9-phase pipeline with real components | tests/e2e/test_complete_workflows.py | E2E | e2e,slow |
| test_actr_activation_scoring | Memory | ACT-R activation formula produces correct ranks | tests/unit/core/test_activation.py | Unit | critical |
| test_budget_enforcer_blocks_expensive_query | Budget | Cost tracking prevents >$1 queries | tests/unit/reasoning/test_budget.py | Unit | critical,safety |
| test_cli_mem_index_real_files | CLI | CLI index command with real file system | tests/integration/test_cli_commands.py | Integration | integration,cli |
| ... | ... | ... | ... | ... | ... |

**Format:** Markdown table, sortable/filterable

**3. Coverage Matrix**

| Component | Unit Coverage | Integration Coverage | E2E Coverage | Total Coverage | Test Count |
|-----------|---------------|----------------------|--------------|----------------|------------|
| MCP (aurora.mcp) | 45% | 35% | 15% | 95% | 85 |
| CLI (aurora.cli) | 50% | 30% | 10% | 90% | 72 |
| SOAR (aurora.soar) | 60% | 25% | 10% | 95% | 145 |
| ACT-R (aurora.core) | 70% | 20% | 5% | 95% | 230 |
| Storage (aurora.core.storage) | 55% | 30% | 10% | 95% | 110 |
| Context-Code (aurora.context_code) | 50% | 35% | 10% | 95% | 95 |
| Reasoning (aurora.reasoning) | 65% | 25% | 5% | 95% | 88 |
| Testing (aurora.testing) | 80% | 15% | 0% | 95% | 45 |

**Total:** 1,650 tests | 85% average coverage

**4. Stats Summary**
- **Total tests:** 1,650
- **Pass rate:** 100% (all Python versions)
- **Coverage:** 85% (line coverage, behavior-based)
- **Execution time:** <5min full suite
- **Python versions:** 3.10, 3.11, 3.12, 3.13
- **Critical tests:** 42 (always run first)
- **Slow tests:** 18 (run in nightly builds)
- **Skipped tests:** 14 (external APIs, documented)
- **Maintenance:** Solo developer + Claude

**Delivery:** Markdown file in `/home/hamr/PycharmProjects/aurora/docs/development/TEST_REFERENCE.md`

### DR3: PHASE1_DELETIONS.md (Audit Trail)

**Purpose:** Document all test deletions for restoration if needed

**Format:**
```markdown
# Phase 1 Test Deletions

**Date:** 2025-12-26
**Branch:** test_cleanup
**Total Deleted:** 23 tests
**Total Archived:** 7 performance tests

## Deleted Tests (Redundant Implementation Details)

### 1. test_init_creates_components
- **File:** tests/unit/soar/headless/test_orchestrator.py
- **Reason:** Tests constructor calls (implementation detail)
- **Replacement:** Behavior tested via test_execute_success_*
- **Restored:** No

### 2. test_build_query_truncates_long_scratchpad
- **File:** tests/unit/soar/headless/test_orchestrator.py
- **Reason:** Tests internal formatting (not behavior)
- **Replacement:** N/A (implementation detail)
- **Restored:** No

... (continue for all 23 deleted tests)

## Archived Tests (Performance Benchmarks)

### 1. tests/performance/test_activation_benchmarks.py
- **Reason:** Keep (critical algorithm validation)
- **Location:** Kept in tests/performance/

### 2. tests/performance/test_storage_benchmarks.py
- **Reason:** Archived (run manually)
- **Location:** tests/archive/performance/

... (continue for all 7 archived tests)
```

**Delivery:** Markdown file in `/home/hamr/PycharmProjects/aurora/docs/development/PHASE1_DELETIONS.md`

### DR4: Update Existing KNOWLEDGE_BASE.md

**Requirement:** Update `/home/hamr/PycharmProjects/aurora/docs/KNOWLEDGE_BASE.md` with test suite changes

**Sections to Add/Update:**
- Testing strategy (pyramid distribution)
- Coverage targets (85%)
- CI/CD philosophy (early warning system)
- Link to TESTING.md for detailed guide
- Link to TEST_REFERENCE.md for test inventory

---

## Phase-Gated Milestones

**User Requirement:** "Stop at each parent task (phase gates for approval)"

### Milestone 1: Phase 1 Complete - Triage & Delete

**Timeline:** Week 1 (Days 1-3)

**Deliverables:**
1. `test_cleanup` branch created
2. PHASE1_DELETIONS.md documenting all deletions
3. 20-25 tests deleted (archived first)
4. Performance tests moved to tests/archive/
5. CI passing on Python 3.10 (baseline maintained)
6. Coverage: 68-72% (temporary drop acceptable)

**Approval Gate:**
- User reviews PHASE1_DELETIONS.md
- Confirms deletion decisions
- Approves progression to Phase 2

**Success Criteria:**
- ✅ All deletions documented with rationale
- ✅ Tests archived (not permanently deleted)
- ✅ Python 3.10 CI still green
- ✅ No critical behaviors lost

**Rollback Plan:** If user rejects deletions, restore from archive and re-evaluate

---

### Milestone 2: Phase 2 Complete - Fix Fragile Tests

**Timeline:** Week 1-2 (Days 4-7)

**Deliverables:**
1. All `test_orchestrator.py` tests migrated to DI pattern
2. 0 `@patch` decorators in orchestrator tests
3. CI passing on Python 3.10/3.11/3.12/3.13
4. Cross-version validation script in scripts/
5. Coverage: 72-76% (still building back up)

**Approval Gate:**
- User reviews CI results (all versions green)
- Confirms no @patch decorators remain
- Approves progression to Phase 3

**Success Criteria:**
- ✅ 0 failures on Python 3.11/3.12 (BLOCKER RESOLVED)
- ✅ DI pattern demonstrated with examples
- ✅ Tests maintainable (clear dependency injection)
- ✅ All Python versions CI green

**Rollback Plan:** If CI still fails, investigate root cause before Phase 3

---

### Milestone 3: Phase 3 Complete - Add Integration/E2E Tests

**Timeline:** Week 2 (Days 8-12)

**Deliverables:**
1. 50-70 new integration tests (MCP, CLI, SOAR)
2. 15-25 new E2E tests (complete workflows)
3. Test pyramid balanced: 55% unit, 35% integration, 10% E2E
4. MCP battle-tested (5-7 integration tests)
5. CLI battle-tested (3-5 integration tests)
6. Coverage: 82-87% (target range)

**Approval Gate:**
- User reviews test pyramid distribution
- Confirms MCP/CLI adequately battle-tested
- Confirms coverage target (85%) reached
- Approves progression to Phase 4

**Success Criteria:**
- ✅ Test pyramid follows industry standard
- ✅ MCP core workflows tested end-to-end
- ✅ CLI commands tested with real components
- ✅ 85% coverage reached (or clear path to 85%)

**Rollback Plan:** If coverage below 83%, add more integration tests before Phase 4

---

### Milestone 4: Phase 4 Complete - Documentation & CI

**Timeline:** Week 2-3 (Days 13-18)

**Deliverables:**
1. TESTING.md comprehensive guide
2. TEST_REFERENCE.md with pyramid + table + stats
3. PHASE1_DELETIONS.md audit trail
4. Updated KNOWLEDGE_BASE.md
5. pytest.ini with markers configured
6. CI configuration with categorized test runs
7. Coverage threshold enforced (85%)

**Approval Gate:**
- User reviews all documentation
- Confirms TESTING.md clear and actionable
- Confirms TEST_REFERENCE.md complete
- Confirms CI configuration working
- Approves merge to main

**Success Criteria:**
- ✅ All documentation complete and reviewed
- ✅ CI categorized test runs working
- ✅ Coverage threshold enforced (85%)
- ✅ Test suite sustainable for MVP development

**Rollback Plan:** If documentation inadequate, revise before final merge

---

### Final Milestone: Merge to Main

**Timeline:** Week 3 (Day 19-21)

**Pre-Merge Checklist:**
- [ ] All 4 phases complete
- [ ] All 4 approval gates passed
- [ ] CI passing on all Python versions
- [ ] Coverage ≥85%
- [ ] Test pyramid balanced (55/35/10)
- [ ] MCP/CLI battle-tested
- [ ] Documentation complete
- [ ] User final approval

**Merge Strategy:**
- Squash merge or merge commit (user preference)
- Clear commit message: "feat(testing): systematic test suite cleanup to 85% coverage"
- Tag release: v0.2.1 (test suite overhaul)

**Post-Merge:**
- Delete `test_cleanup` branch
- Update README with new coverage badge
- Announce in release notes

---

## Risk Management

### Risk 1: Deleting Useful Tests

**Likelihood:** Medium
**Impact:** Medium
**Severity:** MEDIUM

**Mitigation:**
- Archive first, don't permanently delete
- Document all deletions in PHASE1_DELETIONS.md
- User review and approval at Phase 1 gate
- Restoration process documented (copy from archive/)

**Contingency:**
- If test proves valuable later, restore from archive
- If behavior uncovered, write integration test (not unit mock)

---

### Risk 2: Temporary Coverage Drop Below 70%

**Likelihood:** Low
**Impact:** Low (temporary)
**Severity:** LOW

**Mitigation:**
- Work in feature branch (main unaffected)
- User accepted temporary drop: "Yes, acceptable"
- Coverage builds back up in Phase 3

**Contingency:**
- If drop below 65%, pause and add critical tests before continuing
- Monitor coverage per-phase, don't let it drop too far

---

### Risk 3: Phase 2 Introduces New Failures

**Likelihood:** Medium
**Impact:** High (blocks Phase 3)
**Severity:** HIGH

**Mitigation:**
- Phase 2 gate requires all Python versions green
- Cross-version validation script
- DI pattern tested before mass migration

**Contingency:**
- If new failures, debug before Phase 3 approval
- Rollback to Phase 1 state if DI pattern fundamentally broken
- Consult user if blockers emerge

---

### Risk 4: Integration Tests Too Slow (>2min)

**Likelihood:** Low
**Impact:** Medium (slower feedback)
**Severity:** MEDIUM

**Mitigation:**
- Use temp files/databases (fast setup/teardown)
- Parallel test execution in CI
- Profile slow tests, optimize fixtures

**Contingency:**
- If integration tests >3min, move some to nightly builds (mark as "slow")
- Balance speed vs coverage (pragmatic trade-offs)

---

### Risk 5: E2E Tests Flaky (Non-Deterministic)

**Likelihood:** Medium
**Impact:** High (false positives return)
**Severity:** HIGH

**Mitigation:**
- Avoid timing-based tests (no sleep())
- Use deterministic mocks for external APIs
- Explicit waits or retries where needed

**Contingency:**
- If flaky tests emerge, quarantine (mark "slow" or "skip")
- Rewrite flaky tests to be deterministic
- User philosophy: signal over noise (flaky tests are noise)

---

### Risk 6: MCP/CLI Not Adequately Battle-Tested

**Likelihood:** Low
**Impact:** High (core features fail in production)
**Severity:** HIGH

**Mitigation:**
- Phase 3 gate requires user approval of MCP/CLI coverage
- Integration + E2E tests for all critical workflows
- Real components (not mocks) in integration tests

**Contingency:**
- If user identifies gaps in Phase 3 review, add tests before Phase 4
- Prioritize MCP (user: "should be battle tested")
- CLI secondary but still critical

---

### Risk 7: Documentation Incomplete or Unclear

**Likelihood:** Low
**Impact:** Medium (maintenance harder)
**Severity:** MEDIUM

**Mitigation:**
- Phase 4 gate requires user review of all docs
- TESTING.md written for solo developer (clear examples)
- TEST_REFERENCE.md comprehensive (all tests listed)

**Contingency:**
- If docs unclear, revise before final merge
- User provides feedback, agent iterates

---

### Risk 8: Coverage Threshold Too Aggressive (Cannot Reach 85%)

**Likelihood:** Low
**Impact:** High (blocks merge)
**Severity:** HIGH

**Mitigation:**
- Phase 3 adds 50-70 integration + 15-25 E2E tests (sufficient for 85%)
- User raised bar deliberately (from 84% to 85%)
- Coverage calculation includes integration/E2E (honest coverage)

**Contingency:**
- If 85% unreachable, negotiate with user (83-84% acceptable?)
- Identify uncovered code, add targeted tests
- If uncovered code is unreachable, exclude from coverage

---

### Risk 9: Solo Developer Overwhelmed by 2-3 Week Timeline

**Likelihood:** Medium
**Impact:** High (delays MVP)
**Severity:** MEDIUM

**Mitigation:**
- Phase gates allow breaks (not continuous 3 weeks)
- User quote: "2-3 week timeline: Acceptable if that's what's needed"
- Incremental progress, merge per phase if needed

**Contingency:**
- If timeline slips, prioritize Phase 1-2 (fix Python 3.11/3.12 blocker)
- Phase 3-4 can extend if needed (user flexibility)

---

### Risk 10: Test Suite Still Fragile After Cleanup

**Likelihood:** Low
**Impact:** Critical (entire initiative fails)
**Severity:** CRITICAL

**Mitigation:**
- DI pattern eliminates @patch fragility
- Integration/E2E tests use real components
- Cross-version validation enforced
- Phase gates catch issues early

**Contingency:**
- If tests still fragile, root cause analysis before merge
- User quote: "don't want to spend time fixing symptoms"
- Escalate to user if fundamental design issue

---

## Timeline & Execution Plan

### Week 1: Phase 1-2 (Foundation)

**Days 1-3: Phase 1 - Triage & Delete**
- **Day 1:** Create `test_cleanup` branch, identify 20-25 deletion candidates
- **Day 2:** Delete/archive tests, create PHASE1_DELETIONS.md
- **Day 3:** Validate CI (Python 3.10 green), user review + approval

**Days 4-7: Phase 2 - Fix Fragile Tests**
- **Day 4:** High-priority test classes (Safety, MainLoop, Budget)
- **Day 5:** Medium-priority test classes
- **Day 6:** Low-priority test classes, validate @patch removal
- **Day 7:** Cross-version validation (3.10/3.11/3.12/3.13), user review + approval

**Week 1 Milestone:** Python 3.11/3.12 blocker resolved, all versions green

---

### Week 2: Phase 3 (Integration/E2E)

**Days 8-10: MCP Integration Tests (Priority #1)**
- **Day 8:** Add 3 MCP integration tests (index, search, get)
- **Day 9:** Add 2 MCP integration tests (query pipeline, safety)
- **Day 10:** Add MCP E2E tests (complete workflows)

**Days 11-12: CLI Integration + E2E Tests (Priority #2)**
- **Day 11:** Add CLI integration tests (index, search, query, verify)
- **Day 12:** Add E2E workflow tests, validate pyramid distribution

**Week 2 Milestone:** Test pyramid balanced, MCP/CLI battle-tested, 85% coverage reached

---

### Week 3: Phase 4 (Documentation & CI)

**Days 13-15: Documentation**
- **Day 13:** Write TESTING.md (philosophy, principles, examples)
- **Day 14:** Create TEST_REFERENCE.md (pyramid, table, stats)
- **Day 15:** Update KNOWLEDGE_BASE.md, finalize PHASE1_DELETIONS.md

**Days 16-18: CI Configuration**
- **Day 16:** Configure pytest markers in pytest.ini
- **Day 17:** Update CI configuration (categorized test runs)
- **Day 18:** Raise coverage threshold to 85%, user review + approval

**Week 3 Milestone:** Documentation complete, CI configured, ready for merge

---

### Days 19-21: Final Merge

**Day 19:** Pre-merge checklist, final validation
**Day 20:** User final approval, merge to main
**Day 21:** Post-merge cleanup (delete branch, update README, release notes)

---

### Effort Estimation

| Phase | Description | Estimated Hours | Agent Time | User Time |
|-------|-------------|-----------------|------------|-----------|
| **Phase 1** | Triage & Delete | 8-12 hours | 6-10 hours | 2 hours (review) |
| **Phase 2** | Fix Fragile Tests | 12-16 hours | 10-14 hours | 2 hours (review) |
| **Phase 3** | Integration/E2E | 16-24 hours | 14-22 hours | 2 hours (review) |
| **Phase 4** | Documentation/CI | 12-16 hours | 10-14 hours | 2 hours (review) |
| **Final Merge** | Validation & Merge | 4-6 hours | 2-4 hours | 2 hours (approval) |
| **Total** | **52-74 hours** | **42-64 hours** | **10 hours** |

**Assumptions:**
- Agent (Claude) does implementation work
- User does review and approval at phase gates
- Solo developer context: no team coordination overhead
- Incremental progress: can pause between phases

---

## Appendix

### A1: Test Inventory (Current State)

**Total Test Files:** 92
- Unit: 55 files
- Integration: 19 files
- E2E: 2 files
- Performance: 8 files (7 to archive)
- Fault Injection: 5 files
- Calibration: 1 file
- Archived: 2 files

**Total Test Methods:** ~1,800

**Current Coverage:** 74.95% (down from 84%)

**CI Status:**
- ✅ Python 3.10: All pass
- ❌ Python 3.11: 28 failures
- ❌ Python 3.12: 27 failures

**Identified Issues:**
- 50+ tests use `@patch` decorators
- 20-25 tests identified as low-value (redundant/implementation details)
- 7 performance tests to archive
- 95% unit / 4% integration / 1% E2E (inverted pyramid)

---

### A2: Deletion Candidates (Detailed)

**Redundant Unit Tests (10-15 to delete):**
1. `TestHeadlessOrchestratorInit::test_init_creates_components` - Constructor calls
2. `TestBuildIterationQuery::test_build_query_truncates_long_scratchpad` - Formatting detail
3. `TestBuildIterationQuery::test_build_query_with_prompt_data` - Implementation detail
4. `TestValidateSafety::test_validate_safety_success` - Duplicate coverage
5. `TestLoadPrompt::test_load_prompt_success` - Duplicate coverage
6-15. (Additional tests identified during Phase 1 triage)

**Performance Tests to Archive (7 tests):**
1. `tests/performance/test_storage_benchmarks.py`
2. `tests/performance/test_parser_benchmarks.py`
3. `tests/performance/test_soar_benchmarks.py`
4. `tests/performance/test_memory_benchmarks.py`
5. `tests/performance/test_query_benchmarks.py`
6. `tests/performance/test_actr_benchmarks.py`
7. `tests/performance/test_llm_benchmarks.py`

**Keep (Critical):**
- `tests/performance/test_activation_benchmarks.py` - Algorithm validation

---

### A3: Coverage Matrix (Target State)

| Component | Current Coverage | Target Coverage | Gap | Strategy |
|-----------|------------------|-----------------|-----|----------|
| **MCP** | 72% | 95% | +23pp | Add 5-7 integration + 2-3 E2E tests |
| **CLI** | 68% | 90% | +22pp | Add 3-5 integration + 1-2 E2E tests |
| **SOAR** | 82% | 95% | +13pp | Add 3-5 integration tests |
| **ACT-R** | 88% | 95% | +7pp | Add 2-3 unit tests (edge cases) |
| **Storage** | 76% | 95% | +19pp | Add 3-5 integration tests |
| **Context-Code** | 70% | 95% | +25pp | Add 4-6 integration tests (parser) |
| **Reasoning** | 80% | 95% | +15pp | Add 2-3 integration tests (LLM) |
| **Testing** | 90% | 95% | +5pp | Add 1-2 unit tests |
| **Overall** | **74.95%** | **85%** | **+10.05pp** | **50-70 integration + 15-25 E2E** |

---

### A4: Test Markers Reference

| Marker | Description | CI Job | Example Usage |
|--------|-------------|--------|---------------|
| `critical` | Critical safety/correctness tests | test-critical (fast, fail fast) | Safety checks, budget limits |
| `slow` | Slow tests >5s | nightly-builds | Large file parsing, E2E workflows |
| `ml` | Requires ML dependencies | test-with-ml (separate job) | LLM integration tests |
| `integration` | Integration tests | test-integration | Component interaction |
| `e2e` | End-to-end tests | test-e2e | Complete workflows |
| `mcp` | MCP-specific tests | (no separate job) | MCP tool tests |
| `cli` | CLI-specific tests | (no separate job) | CLI command tests |
| `safety` | Safety/security tests | test-critical | Git protection, prompt validation |

---

### A5: Success Criteria Summary

**Quantitative (Must Achieve):**
- ✅ 0 failures on Python 3.10/3.11/3.12/3.13
- ✅ 85% coverage (line coverage, behavior-based)
- ✅ Test pyramid: 50-60% unit, 30-40% integration, 10-15% E2E
- ✅ 1,650 total tests (~150 deleted/archived, 50-70 integration added, 15-25 E2E added)
- ✅ 0 `@patch` decorators in new tests
- ✅ <5min full test suite execution

**Qualitative (Must Demonstrate):**
- ✅ CI/CD failures indicate real bugs (not test infrastructure)
- ✅ MCP battle-tested (integration + E2E coverage)
- ✅ CLI battle-tested (integration + E2E coverage)
- ✅ Tests maintainable by solo developer + Claude
- ✅ Documentation comprehensive (TESTING.md + TEST_REFERENCE.md)
- ✅ Test categorization enables severity assessment

**User Philosophy (Must Embody):**
- ✅ CI/CD as first line of defense, not decorator
- ✅ Signal over noise (eliminate false positives)
- ✅ Test results as input for root cause fixes
- ✅ Industry standard pyramid (no overlaps, no repeats)
- ✅ Support MVP velocity (frequent small changes)

---

## Document Control

**Author:** Claude Sonnet 4.5 (feature-planner agent)
**Reviewer:** User (solo developer)
**Approver:** User
**Version:** 1.0
**Status:** APPROVED
**Last Updated:** 2025-12-26

**Change History:**
- 2025-12-26: Initial PRD creation based on TEST_CLEANUP_PLAN.md and user discovery answers

**Related Documents:**
- TEST_CLEANUP_PLAN.md (source input)
- TESTING.md (to be created in Phase 4)
- TEST_REFERENCE.md (to be created in Phase 4)
- PHASE1_DELETIONS.md (to be created in Phase 1)
- KNOWLEDGE_BASE.md (to be updated in Phase 4)

**Next Steps:**
1. User reviews and approves PRD
2. Invoke `2-generate-tasks` agent to create granular task list
3. Invoke `3-process-task-list` agent to execute Phase 1

---

**End of Product Requirements Document**
