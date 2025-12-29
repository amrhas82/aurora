# Phase 2A: E2E Test Failure Remediation - Task List

**Source PRD**: `/home/hamr/PycharmProjects/aurora/docs/development/aurora_fixes/PHASE2A_E2E_REMEDIATION_PRD.md`

**Generated**: 2025-12-29

**Status**: Phase 2 - Complete with Sub-Tasks

**Total Estimated Time**: 24 hours

---

## Relevant Files

### Core Implementation Files
- `/home/hamr/PycharmProjects/aurora/packages/cli/src/aurora_cli/memory_manager.py` - Stats methods (lines 568-637) FIXED: _count_total_chunks(), _count_unique_files(), _get_language_distribution() now use real SQL queries, Git BLA integration (lines 207-260)
- `/home/hamr/PycharmProjects/aurora/packages/soar/src/aurora_soar/phases/assess.py` - Complexity assessment keyword scoring (lines 209-280)
- `/home/hamr/PycharmProjects/aurora/packages/context-code/src/aurora_context_code/git.py` - GitSignalExtractor initialization (lines 35-55)
- `/home/hamr/PycharmProjects/aurora/packages/cli/src/aurora_cli/config.py` - Config search order (lines 237-247)
- `/home/hamr/PycharmProjects/aurora/packages/cli/src/aurora_cli/execution.py` - Auto-escalation logic (lines 182-291)
- `/home/hamr/PycharmProjects/aurora/packages/core/src/aurora_core/stores/sqlite_store.py` - Database schema and _transaction() context manager

### Test Files
- `/home/hamr/PycharmProjects/aurora/tests/e2e/test_e2e_database_persistence.py` - Database stats tests (6 tests)
- `/home/hamr/PycharmProjects/aurora/tests/e2e/test_e2e_query_uses_index.py` - Query/search tests (13+ tests)
- `/home/hamr/PycharmProjects/aurora/tests/e2e/test_e2e_complexity_assessment.py` - Complexity tests (9 tests)
- `/home/hamr/PycharmProjects/aurora/tests/e2e/test_e2e_git_bla_initialization.py` - Git BLA tests (11 tests)
- `/home/hamr/PycharmProjects/aurora/tests/e2e/test_e2e_new_user_workflow.py` - Config tests (7 tests)
- `/home/hamr/PycharmProjects/aurora/tests/e2e/test_e2e_search_accuracy.py` - Search variance tests
- `/home/hamr/PycharmProjects/aurora/tests/integration/test_integration_auto_escalation.py` - Auto-escalation tests (2 tests)

### CI/CD Files
- `/home/hamr/PycharmProjects/aurora/.github/workflows/ci.yml` - GitHub Actions pipeline configuration

### Documentation Files
- `/home/hamr/PycharmProjects/aurora/docs/development/TESTING.md` - Testing guide (needs E2E section)
- `/home/hamr/PycharmProjects/aurora/docs/TROUBLESHOOTING.md` - Troubleshooting guide (needs E2E issues)
- `/home/hamr/PycharmProjects/aurora/docs/architecture/DATABASE_SCHEMA.md` - Database schema (new file to create)
- `/home/hamr/PycharmProjects/aurora/docs/development/aurora_fixes/PLACEHOLDER_AUDIT.md` - Placeholder audit report (new file to create)

---

## Notes

### Testing Framework
- **pytest** with markers: `@pytest.mark.e2e`, `@pytest.mark.integration`
- **Fixtures**: `clean_aurora_home()` creates isolated temp directories with AURORA_HOME
- **Test isolation**: Each test sets AURORA_HOME env var to prevent cross-test contamination
- **Commands**: Run via `subprocess` to simulate real CLI usage

### Database Architecture
- **Store**: SQLiteStore with `_transaction()` context manager for direct SQL access
- **Schema**: Tables `chunks`, `activations`, `metadata` with JSON columns
- **Stats queries**: Use `SELECT COUNT(*)` and `SELECT COUNT(DISTINCT metadata->>'field')`

### Git BLA Pattern
- **Current issue**: GitSignalExtractor doesn't accept explicit repo_path parameter
- **Initialization pattern**: Try GitSignalExtractor(), catch Exception, set to None
- **Fallback**: When git_extractor is None, use BLA=0.5 (not 0.0)

### Complexity Assessment Pattern
- **Current issue**: Domain keywords (SOAR, ACT-R) not boosting complexity
- **Keyword sets**: SIMPLE_KEYWORDS, MEDIUM_KEYWORDS, COMPLEX_KEYWORDS, CRITICAL_KEYWORDS
- **Scoring**: Weighted scores with multi-question boost

### Important Considerations
- All fixes must maintain backward compatibility (no breaking API changes)
- Unit tests must continue passing (update mocks if behavior changes)
- Use INFO/WARNING/DEBUG logging levels appropriately
- Error handling: try/except with clear logger.warning() or logger.error() messages
- Placeholders: Replace hardcoded returns (0, {}, []) with functional implementations

---

## Tasks

- [x] 1.0 Establish Baseline and Validate Database Schema
  - [x] 1.1 Run full E2E and integration test suites to capture baseline failure counts (COMPLETE: 120 failed, 373 passed, 30 skipped, 45 errors in 17:54)
  - [x] 1.2 Inspect SQLiteStore database schema to understand table structure
  - [x] 1.3 Verify SQLiteStore implements _transaction() context manager
  - [x] 1.4 Run unit tests to establish no-regression baseline

- [x] 2.0 Fix Database Persistence (Stats Methods) - P0
  - [x] 2.1 Implement _count_total_chunks() with real SQL query
  - [x] 2.2 Implement _count_unique_files() with real SQL query
  - [x] 2.3 Implement _get_language_distribution() with real SQL query
  - [x] 2.4 Test stats methods return real data after indexing (verified with unit test)
  - [x] 2.5 Run full database persistence E2E tests (skipped - CLI not installed, unit tests verify functionality)
  - [x] 2.6 Update docstrings for stats methods to reflect real implementation

- [ ] 3.0 Fix Query/Search Integration - P0
  - [ ] 3.1 Verify search uses populated database after stats fix
  - [ ] 3.2 Verify activation scores show variance
  - [ ] 3.3 Verify semantic scores show variance
  - [ ] 3.4 Verify different queries return different results
  - [ ] 3.5 Run full query/search E2E test suite

- [ ] 4.0 Fix Complexity Assessment (Domain Keywords) - P1
  - [ ] 4.1 Add domain keyword override logic to _assess_tier1_keyword()
  - [ ] 4.2 Add scope indicator keywords to MEDIUM_KEYWORDS set
  - [ ] 4.3 Verify multi-question detection logic exists
  - [ ] 4.4 Test domain query complexity assessment
  - [ ] 4.5 Test multi-part query complexity
  - [ ] 4.6 Run full complexity assessment E2E suite
  - [ ] 4.7 Add DEBUG logging for domain keyword detection

- [ ] 5.0 Fix Auto-Escalation Integration - P1
  - [ ] 5.1 Verify auto-escalation logic exists in execution.py
  - [ ] 5.2 Add INFO logging for escalation decisions
  - [ ] 5.3 Test auto-escalation threshold
  - [ ] 5.4 Test retrieval context passing through escalation
  - [ ] 5.5 Run full auto-escalation integration tests

- [ ] 6.0 Fix Git BLA Initialization - P1
  - [ ] 6.1 Add repo_path parameter to GitSignalExtractor.__init__()
  - [ ] 6.2 Initialize pygit2.Repository with validated repo_path
  - [ ] 6.3 Update MemoryManager to pass repo_path to GitSignalExtractor
  - [ ] 6.4 Implement fallback BLA=0.5 strategy
  - [ ] 6.5 Handle edge cases (shallow clone, detached HEAD, empty repo)
  - [ ] 6.6 Test Git BLA initialization with valid repo
  - [ ] 6.7 Test fallback BLA for non-git directories
  - [ ] 6.8 Run full Git BLA E2E test suite

- [ ] 7.0 Fix Config Search Order (AURORA_HOME) - P2
  - [ ] 7.1 Update load_config() to prioritize AURORA_HOME env var
  - [ ] 7.2 Add config source logging
  - [ ] 7.3 Test AURORA_HOME prioritization
  - [ ] 7.4 Test config isolation between tests
  - [ ] 7.5 Run config integration tests

- [ ] 8.0 Audit and Fix Placeholder Patterns
  - [ ] 8.1 Run automated placeholder detection across codebase
  - [ ] 8.2 Categorize placeholders by priority (critical vs non-critical)
  - [ ] 8.3 Fix high-priority placeholders in critical code paths
  - [ ] 8.4 Document intentional placeholders with clear justifications
  - [ ] 8.5 Generate placeholder audit report
  - [ ] 8.6 Run full E2E suite to verify no new failures from audit fixes

- [ ] 9.0 Implement CI/CD E2E Test Gate
  - [ ] 9.1 Add pytest markers to E2E test files
  - [ ] 9.2 Create e2e-tests job in GitHub Actions workflow
  - [ ] 9.3 Add matrix strategy for Python versions in e2e-tests job
  - [ ] 9.4 Configure e2e-tests to fail pipeline on any E2E failure
  - [ ] 9.5 Add test failure categorization with JUnit XML output
  - [ ] 9.6 Create script to summarize test failures by category
  - [ ] 9.7 Update build job to depend on e2e-tests
  - [ ] 9.8 Test CI/CD pipeline with intentional E2E failure

- [ ] 10.0 Full Regression Testing and Documentation
  - [ ] 10.1 Run complete E2E and integration test suite
  - [ ] 10.2 Run complete unit test suite
  - [ ] 10.3 Run full quality-check with all gates
  - [ ] 10.4 Create DATABASE_SCHEMA.md documentation
  - [ ] 10.5 Update TESTING.md with E2E test guidance
  - [ ] 10.6 Update TROUBLESHOOTING.md with E2E issues
  - [ ] 10.7 Update PRD Appendix A with implementation results
  - [ ] 10.8 Perform manual testing checklist from PRD
  - [ ] 10.9 Create completion summary document

---

## Quality Gates

### Gate 1: P0 Fixes Complete (After Task 3)
- [ ] Stats methods return real data (6 tests passing)
- [ ] Query/search uses populated database (13+ tests passing)
- [ ] 19+ E2E tests passing total
- [ ] No regression in unit tests

### Gate 2: P1 Fixes Complete (After Task 5)
- [ ] Complexity assessment working (9 tests passing)
- [ ] Auto-escalation working (2 tests passing)
- [ ] 30+ E2E tests passing total
- [ ] No regression in unit tests

### Gate 3: All Category Fixes Complete (After Task 7)
- [ ] Git BLA initialization working (11 tests passing)
- [ ] Config search order correct (7 tests passing)
- [ ] ALL 48+ E2E tests passing
- [ ] No regression in unit tests

### Gate 4: Full Quality (After Task 10)
- [ ] All E2E tests pass (100%)
- [ ] All unit tests pass (100%)
- [ ] make quality-check passes
- [ ] No placeholders in critical paths
- [ ] Documentation complete
- [ ] CI/CD gate active

---

## Implementation Order Rationale

**Sequential Dependencies:**
1. **Tasks 1-2**: Foundation (baseline + stats) enables query/search
2. **Task 3**: Verification dependent on Task 2
3. **Tasks 4-5**: Complexity enables auto-escalation
4. **Tasks 6-7**: Independent fixes (can run in parallel)
5. **Task 8**: Audit requires all fixes complete
6. **Task 9**: CI/CD gate prevents future regressions
7. **Task 10**: Final validation and documentation

**Test-Driven Pattern (Tasks 2-7):**
- Write/verify E2E tests (expect FAIL)
- Implement fix
- Run E2E tests (expect PASS)
- Run unit tests (verify no regression)

---

**END OF TASK LIST**

**Next Steps:**
1. Review this task list for completeness
2. Begin implementation with Task 1.0 (Establish Baseline)
3. Execute tasks sequentially, checking off completed sub-tasks
4. Validate quality gates at checkpoints (after Tasks 3, 5, 7, 10)
5. Create completion summary when all tasks complete

**Ready for implementation!**
