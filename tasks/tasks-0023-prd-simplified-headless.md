# Task List: Simplified Headless Mode (PRD-0023)

**Generated**: 2026-01-05
**PRD**: /home/hamr/PycharmProjects/aurora/prds/0023-prd-simplified-headless.md
**Status**: Detailed Implementation (Phase 2)

---

## Relevant Files

### Core Implementation Files

- `/home/hamr/PycharmProjects/aurora/packages/soar/src/aurora_soar/headless/__init__.py` - Module exports for headless components (updated to import HeadlessConfig from config.py)
- `/home/hamr/PycharmProjects/aurora/packages/soar/src/aurora_soar/headless/config.py` - Configuration dataclass with validation (COMPLETE - 100% coverage)
- `/home/hamr/PycharmProjects/aurora/tests/unit/soar/headless/test_config.py` - Unit tests for HeadlessConfig (COMPLETE - 11 tests passing)
- `/home/hamr/PycharmProjects/aurora/packages/soar/src/aurora_soar/headless/prompt_loader.py` - Prompt file parser and validator (original complex version - kept for reference)
- `/home/hamr/PycharmProjects/aurora/packages/soar/src/aurora_soar/headless/prompt_loader_simplified.py` - Simplified prompt loader (COMPLETE - 95.24% coverage)
- `/home/hamr/PycharmProjects/aurora/tests/unit/soar/headless/test_prompt_loader_simplified.py` - Unit tests for simplified PromptLoader (COMPLETE - 12 tests passing)
- `/home/hamr/PycharmProjects/aurora/packages/soar/src/aurora_soar/headless/scratchpad.py` - Scratchpad manager for iteration tracking (NEW - simplified from scratchpad_manager.py)
- `/home/hamr/PycharmProjects/aurora/packages/soar/src/aurora_soar/headless/git_enforcer.py` - Git branch safety validation (EXISTS - review/simplify)
- `/home/hamr/PycharmProjects/aurora/packages/soar/src/aurora_soar/headless/orchestrator.py` - Main headless execution loop (EXISTS - review/simplify)
- `/home/hamr/PycharmProjects/aurora/packages/cli/src/aurora_cli/commands/headless.py` - CLI command entry point (EXISTS - needs simplification)

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

- [ ] 4.0 Git Safety Enforcement (TDD)
  - [ ] 4.1 RED: Write test for GitEnforcer accepting valid branch (not main/master)
  - [ ] 4.2 RED: Write test for GitEnforcer rejecting main branch
  - [ ] 4.3 RED: Write test for GitEnforcer rejecting master branch
  - [ ] 4.4 RED: Write test for GitEnforcer handling detached HEAD state
  - [ ] 4.5 RED: Write test for GitEnforcer handling non-git directory
  - [ ] 4.6 GREEN: Review existing `/home/hamr/PycharmProjects/aurora/packages/soar/src/aurora_soar/headless/git_enforcer.py`
  - [ ] 4.7 GREEN: Simplify GitEnforcer to check only branch safety (remove uncommitted changes check)
  - [ ] 4.8 GREEN: Implement GitBranchError exception with clear error messages
  - [ ] 4.9 GREEN: Add fallback for missing git command (graceful degradation)
  - [ ] 4.10 REFACTOR: Extract subprocess execution into separate _run_git_command() helper
  - [ ] 4.11 REFACTOR: Add logging for git command execution and results

- [ ] 5.0 Headless Execution Orchestrator (TDD)
  - [ ] 5.1 RED: Write test for HeadlessOrchestrator initialization with all dependencies
  - [ ] 5.2 RED: Write test for HeadlessOrchestrator.execute() successful single iteration
  - [ ] 5.3 RED: Write test for HeadlessOrchestrator.execute() handling SOAR execution failure
  - [ ] 5.4 RED: Write test for HeadlessOrchestrator evaluating goal achievement
  - [ ] 5.5 RED: Write test for HeadlessOrchestrator appending to scratchpad on each iteration
  - [ ] 5.6 GREEN: Review and simplify existing `/home/hamr/PycharmProjects/aurora/packages/soar/src/aurora_soar/headless/orchestrator.py`
  - [ ] 5.7 GREEN: Simplify to single-iteration execution (remove multi-iteration loop)
  - [ ] 5.8 GREEN: Implement HeadlessOrchestrator.__init__ with dependency injection
  - [ ] 5.9 GREEN: Implement HeadlessOrchestrator.execute() for single SOAR iteration
  - [ ] 5.10 GREEN: Implement HeadlessOrchestrator._evaluate_success() using LLM to check criteria
  - [ ] 5.11 GREEN: Integrate GitEnforcer, PromptLoader, and Scratchpad components
  - [ ] 5.12 REFACTOR: Extract result formatting into HeadlessResult dataclass
  - [ ] 5.13 REFACTOR: Add detailed logging at each execution step

- [ ] 6.0 CLI Command Integration (TDD)
  - [ ] 6.1 RED: Write test for `aur headless` command with valid prompt file
  - [ ] 6.2 RED: Write test for `aur headless` command with missing prompt file
  - [ ] 6.3 RED: Write test for `aur headless` command with invalid budget flag
  - [ ] 6.4 RED: Write test for `aur headless` command with invalid max-iter flag
  - [ ] 6.5 RED: Write test for `aur headless` command with --dry-run flag
  - [ ] 6.6 RED: Write test for `aur headless` command with custom scratchpad path
  - [ ] 6.7 GREEN: Simplify existing `/home/hamr/PycharmProjects/aurora/packages/cli/src/aurora_cli/commands/headless.py`
  - [ ] 6.8 GREEN: Remove complex configuration loading, use simplified HeadlessConfig
  - [ ] 6.9 GREEN: Implement command arguments: prompt_path (required), --scratchpad, --budget, --max-iter, --dry-run
  - [ ] 6.10 GREEN: Integrate with HeadlessOrchestrator for execution
  - [ ] 6.11 GREEN: Add rich console output for configuration display and results
  - [ ] 6.12 REFACTOR: Extract CLI output formatting into separate display functions
  - [ ] 6.13 REFACTOR: Add graceful KeyboardInterrupt handling for user cancellation

- [ ] 7.0 Integration Testing & Documentation (TDD)
  - [ ] 7.1 RED: Write integration test for full workflow (prompt → execute → scratchpad)
  - [ ] 7.2 RED: Write integration test for git safety blocking execution on main branch
  - [ ] 7.3 RED: Write integration test for invalid prompt rejection
  - [ ] 7.4 RED: Write E2E test for successful headless execution with real SOAR pipeline
  - [ ] 7.5 RED: Write E2E test for headless execution failure scenario
  - [ ] 7.6 GREEN: Implement integration tests in `/home/hamr/PycharmProjects/aurora/tests/integration/test_headless_integration.py`
  - [ ] 7.7 GREEN: Extend E2E tests in `/home/hamr/PycharmProjects/aurora/tests/e2e/test_headless_e2e.py`
  - [ ] 7.8 GREEN: Run full test suite and ensure 80%+ coverage
  - [ ] 7.9 REFACTOR: Update `/home/hamr/PycharmProjects/aurora/docs/deployment/headless-mode.md` for simplified version
  - [ ] 7.10 REFACTOR: Create `/home/hamr/PycharmProjects/aurora/docs/development/headless-architecture.md` developer guide
  - [ ] 7.11 REFACTOR: Add inline code examples to documentation
  - [ ] 7.12 REFACTOR: Create troubleshooting section with common errors and solutions

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
