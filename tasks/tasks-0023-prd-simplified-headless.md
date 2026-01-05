# Task List: Simplified Headless Mode (PRD-0023)

**Generated**: 2026-01-05
**PRD**: /home/hamr/PycharmProjects/aurora/prds/0023-prd-simplified-headless.md
**Status**: Detailed Implementation (Phase 2)

---

## Relevant Files

### Core Implementation Files

- `/home/hamr/PycharmProjects/aurora/packages/soar/src/aurora_soar/headless/__init__.py` - Module exports for headless components (UPDATED to export simplified components)
- `/home/hamr/PycharmProjects/aurora/packages/soar/src/aurora_soar/headless/config.py` - Configuration dataclass with validation (COMPLETE - 82.35% coverage, 11 tests passing)
- `/home/hamr/PycharmProjects/aurora/tests/unit/soar/headless/test_config.py` - Unit tests for HeadlessConfig (COMPLETE - 11 tests passing)
- `/home/hamr/PycharmProjects/aurora/packages/soar/src/aurora_soar/headless/prompt_loader.py` - Prompt file parser and validator (original complex version - kept for reference)
- `/home/hamr/PycharmProjects/aurora/packages/soar/src/aurora_soar/headless/prompt_loader_simplified.py` - Simplified prompt loader (COMPLETE - 95.24% coverage, 12 tests passing)
- `/home/hamr/PycharmProjects/aurora/tests/unit/soar/headless/test_prompt_loader_simplified.py` - Unit tests for simplified PromptLoader (COMPLETE - 12 tests passing)
- `/home/hamr/PycharmProjects/aurora/packages/soar/src/aurora_soar/headless/scratchpad.py` - Simplified scratchpad manager (COMPLETE - 89.89% coverage, 12 tests passing)
- `/home/hamr/PycharmProjects/aurora/tests/unit/soar/headless/test_scratchpad_simplified.py` - Unit tests for simplified Scratchpad (COMPLETE - 12 tests passing)
- `/home/hamr/PycharmProjects/aurora/packages/soar/src/aurora_soar/headless/git_enforcer.py` - Git branch safety validation (COMPLETE - 90.79% coverage, 33 tests passing)
- `/home/hamr/PycharmProjects/aurora/tests/unit/soar/headless/test_git_enforcer.py` - Unit tests for GitEnforcer (COMPLETE - 33 tests passing)
- `/home/hamr/PycharmProjects/aurora/packages/soar/src/aurora_soar/headless/orchestrator_simplified.py` - Simplified single-iteration orchestrator (COMPLETE - 93.70% coverage, 7 tests passing)
- `/home/hamr/PycharmProjects/aurora/tests/unit/soar/headless/test_orchestrator_simplified.py` - Unit tests for simplified orchestrator (COMPLETE - 7 tests passing)
- `/home/hamr/PycharmProjects/aurora/packages/soar/src/aurora_soar/headless/orchestrator.py` - Main headless execution loop (OLD VERSION - kept for reference)
- `/home/hamr/PycharmProjects/aurora/packages/cli/src/aurora_cli/commands/headless.py` - CLI command entry point (COMPLETE - 91.55% coverage, simplified)
- `/home/hamr/PycharmProjects/aurora/tests/unit/cli/test_headless_command.py` - CLI command unit tests (COMPLETE - 24 tests passing)

### Template Files

- `/home/hamr/PycharmProjects/aurora/.aurora/headless/prompt.md.template` - Template for experiment prompts (ALREADY EXISTS)
- `/home/hamr/PycharmProjects/aurora/.aurora/headless/README.md` - User guide for headless mode (ALREADY EXISTS)

### Test Files

- `/home/hamr/PycharmProjects/aurora/tests/unit/soar/headless/test_config.py` - Unit tests for configuration (NEW)
- `/home/hamr/PycharmProjects/aurora/tests/unit/soar/headless/test_prompt_loader.py` - Unit tests for prompt parsing (EXISTS - extend)
- `/home/hamr/PycharmProjects/aurora/tests/unit/soar/headless/test_scratchpad.py` - Unit tests for scratchpad (NEW)
- `/home/hamr/PycharmProjects/aurora/tests/unit/soar/headless/test_git_enforcer.py` - Unit tests for git safety (EXISTS - extend)
- `/home/hamr/PycharmProjects/aurora/tests/unit/soar/headless/test_orchestrator.py` - Unit tests for orchestrator (EXISTS - extend)
- `/home/hamr/PycharmProjects/aurora/tests/unit/cli/test_headless_command.py` - Unit tests for CLI command (EXISTS - extend)
- `/home/hamr/PycharmProjects/aurora/tests/integration/test_headless_integration.py` - Integration tests for full workflow (NEW)
- `/home/hamr/PycharmProjects/aurora/tests/e2e/test_headless_e2e.py` - End-to-end tests for complete scenarios (EXISTS - extend)

### Documentation Files

- `/home/hamr/PycharmProjects/aurora/docs/deployment/headless-mode.md` - User-facing documentation (EXISTS - update for simplified version)
- `/home/hamr/PycharmProjects/aurora/docs/development/headless-architecture.md` - Developer architecture guide (NEW)

---

## Notes

### Testing Strategy

**TDD Workflow for Every Component**:
1. **RED Phase**: Write failing test that defines expected behavior
2. **GREEN Phase**: Write minimal implementation to make test pass
3. **REFACTOR Phase**: Improve code quality while keeping tests green

**Test Coverage Requirements**:
- Unit tests: 80%+ line coverage per module
- Integration tests: All component boundaries
- E2E tests: Complete user workflows

**Test Utilities**:
- Use `pytest` fixtures for shared test setup
- Use `tmp_path` for file system operations
- Use `unittest.mock.Mock` for dependency injection
- Use `click.testing.CliRunner` for CLI testing

### Architecture Patterns

**Simplified Design Goals**:
- Remove complex features (budget tracking, multi-iteration loops)
- Focus on single-iteration execution with clear success/failure
- Maintain safety features (git enforcement, validation)
- Keep clear separation of concerns

**Dependency Injection**:
- All components accept dependencies via constructor
- Makes testing easier with mock objects
- Enables composition and flexibility

**Configuration Management**:
- Use Python dataclasses for type safety
- Validate at construction time
- Immutable after creation

**Error Handling**:
- Specific exception types for each error category
- Clear error messages for users
- Graceful degradation where possible

### Implementation Priorities

1. **Safety First**: Git enforcement and validation before execution
2. **User Experience**: Clear error messages and helpful feedback
3. **Testability**: Design for easy testing with dependency injection
4. **Simplicity**: Remove complexity, focus on core workflow

### Existing Code to Review

The following files already exist and should be reviewed for simplification:
- `prompt_loader.py` - May be over-engineered, simplify validation
- `git_enforcer.py` - Likely good as-is, verify safety checks
- `orchestrator.py` - Complex multi-iteration logic needs simplification
- `scratchpad_manager.py` - Full-featured, create simple `scratchpad.py` instead

---

## Tasks

- [x] 1.0 Headless Configuration Foundation (TDD)
  - [x] 1.1 RED: Write test for HeadlessConfig dataclass with default values
  - [x] 1.2 RED: Write test for HeadlessConfig validation (negative budget, negative max_iter)
  - [x] 1.3 RED: Write test for HeadlessConfig immutability after creation
  - [x] 1.4 GREEN: Implement HeadlessConfig dataclass in `/home/hamr/PycharmProjects/aurora/packages/soar/src/aurora_soar/headless/config.py`
  - [x] 1.5 GREEN: Add validation logic in `__post_init__` to enforce positive budget and max_iter
  - [x] 1.6 GREEN: Make dataclass frozen (immutable) with `@dataclass(frozen=True)`
  - [x] 1.7 REFACTOR: Add docstrings and type hints to all config fields
  - [x] 1.8 REFACTOR: Extract validation constants (MIN_BUDGET, MAX_ITERATIONS_LIMIT) to module level

- [x] 2.0 Prompt File Validation & Parsing (TDD)
  - [x] 2.1 RED: Write test for PromptLoader loading valid prompt file with all sections
  - [x] 2.2 RED: Write test for PromptLoader rejecting prompt missing Goal section
  - [x] 2.3 RED: Write test for PromptLoader rejecting prompt missing Success Criteria section
  - [x] 2.4 RED: Write test for PromptLoader handling optional Context section
  - [x] 2.5 RED: Write test for PromptLoader rejecting non-existent file path
  - [x] 2.6 GREEN: Review existing `/home/hamr/PycharmProjects/aurora/packages/soar/src/aurora_soar/headless/prompt_loader.py`
  - [x] 2.7 GREEN: Simplify PromptLoader to parse only Goal, Success Criteria, Constraints, and Context sections
  - [x] 2.8 GREEN: Implement PromptValidationError exception class with descriptive messages
  - [x] 2.9 GREEN: Add file existence check before parsing
  - [x] 2.10 REFACTOR: Extract markdown parsing logic into separate helper functions
  - [x] 2.11 REFACTOR: Add comprehensive docstrings with examples of valid/invalid prompts

- [x] 3.0 Scratchpad Management System (TDD)
  - [x] 3.1 RED: Write test for Scratchpad initialization creating new file
  - [x] 3.2 RED: Write test for Scratchpad appending iteration entry with timestamp
  - [x] 3.3 RED: Write test for Scratchpad reading existing entries
  - [x] 3.4 RED: Write test for Scratchpad updating status (PENDING → IN_PROGRESS → COMPLETED)
  - [x] 3.5 RED: Write test for Scratchpad appending termination signal
  - [x] 3.6 GREEN: Create new simplified `/home/hamr/PycharmProjects/aurora/packages/soar/src/aurora_soar/headless/scratchpad.py`
  - [x] 3.7 GREEN: Implement Scratchpad.__init__ to create/load scratchpad file
  - [x] 3.8 GREEN: Implement Scratchpad.append_iteration() to log iteration details
  - [x] 3.9 GREEN: Implement Scratchpad.update_status() to change execution status
  - [x] 3.10 GREEN: Implement Scratchpad.append_signal() to add termination signals
  - [x] 3.11 REFACTOR: Extract markdown formatting into separate ScratchpadFormatter class (SKIPPED - simple enough for now)
  - [x] 3.12 REFACTOR: Add file backup before writing to prevent data loss (SKIPPED - overkill for simplified version)

- [x] 4.0 Git Safety Enforcement (TDD)
  - [x] 4.1 RED: Write test for GitEnforcer accepting valid branch (not main/master)
  - [x] 4.2 RED: Write test for GitEnforcer rejecting main branch
  - [x] 4.3 RED: Write test for GitEnforcer rejecting master branch
  - [x] 4.4 RED: Write test for GitEnforcer handling detached HEAD state
  - [x] 4.5 RED: Write test for GitEnforcer handling non-git directory
  - [x] 4.6 GREEN: Review existing `/home/hamr/PycharmProjects/aurora/packages/soar/src/aurora_soar/headless/git_enforcer.py`
  - [x] 4.7 GREEN: Simplify GitEnforcer to check only branch safety (remove uncommitted changes check)
  - [x] 4.8 GREEN: Implement GitBranchError exception with clear error messages
  - [x] 4.9 GREEN: Add fallback for missing git command (graceful degradation)
  - [x] 4.10 REFACTOR: Extract subprocess execution into separate _run_git_command() helper
  - [x] 4.11 REFACTOR: Add logging for git command execution and results

- [x] 5.0 Headless Execution Orchestrator (TDD)
  - [x] 5.1 RED: Write test for HeadlessOrchestrator initialization with all dependencies
  - [x] 5.2 RED: Write test for HeadlessOrchestrator.execute() successful single iteration
  - [x] 5.3 RED: Write test for HeadlessOrchestrator.execute() handling SOAR execution failure
  - [x] 5.4 RED: Write test for HeadlessOrchestrator evaluating goal achievement
  - [x] 5.5 RED: Write test for HeadlessOrchestrator appending to scratchpad on each iteration
  - [x] 5.6 GREEN: Review and simplify existing `/home/hamr/PycharmProjects/aurora/packages/soar/src/aurora_soar/headless/orchestrator.py`
  - [x] 5.7 GREEN: Simplify to single-iteration execution (remove multi-iteration loop)
  - [x] 5.8 GREEN: Implement HeadlessOrchestrator.__init__ with dependency injection
  - [x] 5.9 GREEN: Implement HeadlessOrchestrator.execute() for single SOAR iteration
  - [x] 5.10 GREEN: Implement HeadlessOrchestrator._evaluate_success() using simple heuristic
  - [x] 5.11 GREEN: Integrate GitEnforcer, PromptLoader, and Scratchpad components
  - [x] 5.12 REFACTOR: Extract result formatting into HeadlessResult dataclass
  - [x] 5.13 REFACTOR: Add detailed logging at each execution step

- [x] 6.0 CLI Command Integration (TDD)
  - [x] 6.1 RED: Write test for `aur headless` command with valid prompt file (ALREADY EXISTS - 24 tests)
  - [x] 6.2 RED: Write test for `aur headless` command with missing prompt file (ALREADY EXISTS)
  - [x] 6.3 RED: Write test for `aur headless` command with invalid budget flag (ALREADY EXISTS)
  - [x] 6.4 RED: Write test for `aur headless` command with invalid max-iter flag (ALREADY EXISTS)
  - [x] 6.5 RED: Write test for `aur headless` command with --dry-run flag (ALREADY EXISTS)
  - [x] 6.6 RED: Write test for `aur headless` command with custom scratchpad path (ALREADY EXISTS)
  - [x] 6.7 GREEN: Simplify existing `/home/hamr/PycharmProjects/aurora/packages/cli/src/aurora_cli/commands/headless.py`
  - [x] 6.8 GREEN: Fix parameter name mismatch - use budget (int tokens) instead of budget_limit (float USD)
  - [x] 6.9 GREEN: Update to use simplified orchestrator_simplified.py instead of orchestrator.py
  - [x] 6.10 GREEN: Fix HeadlessConfig initialization to match simplified config.py interface
  - [x] 6.11 GREEN: Update __init__.py to export simplified orchestrator components
  - [x] 6.12 REFACTOR: Updated tests to match simplified interface (all 24 tests passing)
  - [x] 6.13 REFACTOR: Fixed orchestrator to use GitEnforcer defaults instead of config.required_branch

- [ ] 7.0 Integration Testing & Documentation (TDD)
  - [x] 7.1 RED: Write integration test for full workflow (prompt → execute → scratchpad)
  - [x] 7.2 RED: Write integration test for git safety blocking execution on main branch
  - [x] 7.3 RED: Write integration test for invalid prompt rejection
  - [x] 7.4 GREEN: Implement 11 integration tests in `/home/hamr/PycharmProjects/aurora/tests/integration/test_headless_integration.py` (ALL PASSING)
  - [x] 7.5 GREEN: Run full test suite - 110 tests passing with 89%+ coverage on all simplified components
  - [ ] 7.6 REFACTOR: Update `/home/hamr/PycharmProjects/aurora/docs/deployment/headless-mode.md` for simplified version
  - [ ] 7.7 REFACTOR: Create `/home/hamr/PycharmProjects/aurora/docs/development/headless-architecture.md` developer guide
  - [ ] 7.8 REFACTOR: Add troubleshooting section with common errors and solutions to documentation

---

## Implementation Workflow

### Phase 1: Foundation (Tasks 1.0 - 2.0)
Build the configuration and prompt parsing foundation with full test coverage.

**Entry Point**: Start with `test_config.py`, write failing tests, then implement `config.py`.

**Success Criteria**:
- All configuration tests pass (RED → GREEN)
- Prompt loader can parse valid prompts and reject invalid ones
- Clear error messages for all validation failures

### Phase 2: Core Components (Tasks 3.0 - 4.0)
Implement scratchpad tracking and git safety enforcement.

**Entry Point**: Start with `test_scratchpad.py`, then `test_git_enforcer.py`.

**Success Criteria**:
- Scratchpad can initialize, append, and read entries
- Git enforcer blocks main/master branches
- All component tests pass with 80%+ coverage

### Phase 3: Orchestration (Task 5.0)
Wire all components together in the main orchestrator.

**Entry Point**: Start with `test_orchestrator.py`, test component integration.

**Success Criteria**:
- Single-iteration execution works end-to-end
- Dependencies are properly injected
- Error handling is comprehensive

### Phase 4: CLI & Integration (Tasks 6.0 - 7.0)
Add CLI command and validate full workflow.

**Entry Point**: Start with `test_headless_command.py`, then integration tests.

**Success Criteria**:
- CLI command works with all flags
- Integration tests pass for complete workflows
- E2E tests validate realistic scenarios
- Documentation is complete and accurate

---

## Verification Checklist

Before marking each parent task complete:

- [ ] All RED phase tests written and failing
- [ ] All GREEN phase implementations passing tests
- [ ] All REFACTOR phase improvements applied
- [ ] Code coverage ≥80% for the module
- [ ] No linting errors (ruff, mypy)
- [ ] Docstrings added to all public functions/classes
- [ ] Type hints complete and accurate
- [ ] Error messages are clear and actionable

---

## Self-Review Questions

Before proceeding to next task:

1. Does every implementation have a failing test first? (TDD RED phase)
2. Does the minimal implementation pass all tests? (TDD GREEN phase)
3. Is the code clean and well-structured? (TDD REFACTOR phase)
4. Are error messages helpful to end users?
5. Is the code testable with dependency injection?
6. Are all edge cases covered by tests?

---

**Total Sub-Tasks**: 84 (across 7 parent tasks)
**Estimated Duration**: 12-16 hours (assuming 1-4 hours per parent task)
**Test Coverage Goal**: 80%+ line coverage
**TDD Compliance**: 100% (all implementations follow RED → GREEN → REFACTOR)

---

**Phase 2 Complete**: Detailed sub-tasks generated with strict TDD ordering.

**Next Step**: Begin implementation starting with Task 1.1 (RED phase for HeadlessConfig tests).
