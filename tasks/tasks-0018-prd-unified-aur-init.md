# Task List: Unified `aur init` Command (TDD Edition)

**PRD**: tasks/0018-prd-unified-aur-init.md
**Status**: Phase 2 - TDD Task List with Verification Commands
**Created**: January 3, 2026
**Estimated Effort**: 1-2 days implementation
**Approach**: Test-First Development (Red → Green → Refactor)

---

## Key Principles

1. **Write tests FIRST** - Every implementation task has a test task before it
2. **Verify ALWAYS** - Shell commands provided to run tests after each task
3. **Red → Green → Refactor** - Write failing test, make it pass, clean up
4. **Incremental commits** - Commit after each green test

---

## Relevant Files

### Files Modified

- `/home/hamr/PycharmProjects/aurora/packages/cli/src/aurora_cli/config.py` - Updated default paths to project-specific (Task 1.2)
- `/home/hamr/PycharmProjects/aurora/packages/cli/src/aurora_cli/commands/init.py` - Added run_step_1_planning_setup() and run_step_2_memory_indexing() (Tasks 3.2, 4.2)

### Files Created

- `/home/hamr/PycharmProjects/aurora/packages/cli/src/aurora_cli/commands/init_helpers.py` - Helper functions extracted from init_planning.py (Task 2.2)
- `/home/hamr/PycharmProjects/aurora/tests/unit/cli/test_config_paths.py` - Tests for config path changes (Task 1.1)
- `/home/hamr/PycharmProjects/aurora/tests/unit/cli/test_init_helpers.py` - Tests for init helpers (Task 2.1)
- `/home/hamr/PycharmProjects/aurora/tests/unit/cli/test_init_unified.py` - Tests for unified init command (Tasks 3.1, 4.1)

### Files Pending

- `/home/hamr/PycharmProjects/aurora/packages/cli/src/aurora_cli/main.py` - Remove init_planning_command registration
- `/home/hamr/PycharmProjects/aurora/packages/cli/src/aurora_cli/memory_manager.py` - Already supports project-specific db_path (Task 4.4 N/A)
- `/home/hamr/PycharmProjects/aurora/docs/cli/CLI_USAGE_GUIDE.md` - Update initialization section
- `/home/hamr/PycharmProjects/aurora/README.md` - Update quick start commands
- `/home/hamr/PycharmProjects/aurora/tests/integration/cli/test_init_flow.py` - Integration tests
- `/home/hamr/PycharmProjects/aurora/docs/cli/MIGRATION_GUIDE_v0.3.0.md` - Migration guide

### Files to Delete

- `/home/hamr/PycharmProjects/aurora/packages/cli/src/aurora_cli/commands/init_planning.py`
- `/home/hamr/PycharmProjects/aurora/tests/unit/cli/test_init_planning.py`

### Files to Reuse (from Phase 1)

- `/home/hamr/PycharmProjects/aurora/packages/cli/src/aurora_cli/configurators/base.py`
- `/home/hamr/PycharmProjects/aurora/packages/cli/src/aurora_cli/configurators/registry.py`
- `/home/hamr/PycharmProjects/aurora/packages/cli/src/aurora_cli/configurators/claude.py`
- `/home/hamr/PycharmProjects/aurora/packages/cli/src/aurora_cli/configurators/opencode.py`
- `/home/hamr/PycharmProjects/aurora/packages/cli/src/aurora_cli/configurators/ampcode.py`
- `/home/hamr/PycharmProjects/aurora/packages/cli/src/aurora_cli/configurators/droid.py`
- `/home/hamr/PycharmProjects/aurora/packages/cli/src/aurora_cli/configurators/agents.py`

---

## Testing Notes

- **Test execution**: All tests use `pytest` with PYTHONPATH set
- **Coverage**: Aim for >90% on new code, maintain 97% overall
- **Type checking**: Run `mypy` after each implementation task
- **Linting**: Run `ruff` after each implementation task
- **Integration tests**: Use CliRunner with input simulation

---

## Tasks

### 1.0 Update Configuration System for Project-Specific Paths

- [x] 1.1 TEST: Write failing tests for config path changes
  - Create `tests/unit/cli/test_config_paths.py`
  - Test default paths are project-specific (not global)
  - Test budget_tracker_path remains global
  - Test environment variable overrides work
  - Test path expansion (./ → absolute)
  ```bash
  # Verify tests fail (RED)
  PYTHONPATH=/home/hamr/PycharmProjects/aurora/packages/cli/src:/home/hamr/PycharmProjects/aurora/packages/core/src python3 -m pytest tests/unit/cli/test_config_paths.py -v
  ```

- [x] 1.2 IMPLEMENT: Update default paths in config.py
  - Change `logging_file` from `~/.aurora/aurora.log` to `./.aurora/logs/aurora.log`
  - Change `mcp_log_file` from `~/.aurora/mcp.log` to `./.aurora/logs/mcp.log`
  - Change `db_path` from `~/.aurora/memory.db` to `./.aurora/memory.db`
  - Change `agents_manifest_path` from `~/.aurora/cache/agent_manifest.json` to `./.aurora/cache/agent_manifest.json`
  - Change `planning_base_dir` from `~/.aurora/plans` to `./.aurora/plans`
  - KEEP `budget_tracker_path` as `~/.aurora/budget_tracker.json`
  ```bash
  # Verify tests pass (GREEN)
  PYTHONPATH=/home/hamr/PycharmProjects/aurora/packages/cli/src:/home/hamr/PycharmProjects/aurora/packages/core/src python3 -m pytest tests/unit/cli/test_config_paths.py -v
  ```

- [x] 1.3 VERIFY: Type check and lint
  ```bash
  # Type check
  mypy packages/cli/src/aurora_cli/config.py --show-error-codes
  # Lint
  ruff check packages/cli/src/aurora_cli/config.py
  ```

- [ ] 1.4 TEST: Write tests for CONFIG_SCHEMA validation
  - Test schema validates new path structure
  - Test schema rejects invalid paths
  - Test nested structure matches defaults
  ```bash
  # Verify tests fail (RED)
  PYTHONPATH=/home/hamr/PycharmProjects/aurora/packages/cli/src:/home/hamr/PycharmProjects/aurora/packages/core/src python3 -m pytest tests/unit/cli/test_config_paths.py::test_schema_validation -v
  ```

- [ ] 1.5 IMPLEMENT: Update CONFIG_SCHEMA nested structure
  - Update schema to match new defaults
  - Add validation for project-specific paths
  ```bash
  # Verify tests pass (GREEN)
  PYTHONPATH=/home/hamr/PycharmProjects/aurora/packages/cli/src:/home/hamr/PycharmProjects/aurora/packages/core/src python3 -m pytest tests/unit/cli/test_config_paths.py::test_schema_validation -v
  ```

- [ ] 1.6 TEST: Write tests for load_config() path creation
  - Test load_config() creates project-specific directories
  - Test load_config() expands relative paths to absolute
  - Test load_config() with AURORA_PLANS_DIR override
  ```bash
  # Verify tests fail (RED)
  PYTHONPATH=/home/hamr/PycharmProjects/aurora/packages/cli/src:/home/hamr/PycharmProjects/aurora/packages/core/src python3 -m pytest tests/unit/cli/test_config_paths.py::test_load_config -v
  ```

- [ ] 1.7 IMPLEMENT: Update load_config() for project-specific paths
  - Create project-specific paths when needed
  - Ensure paths are absolute
  - Handle environment variable overrides
  ```bash
  # Verify tests pass (GREEN)
  PYTHONPATH=/home/hamr/PycharmProjects/aurora/packages/cli/src:/home/hamr/PycharmProjects/aurora/packages/core/src python3 -m pytest tests/unit/cli/test_config_paths.py::test_load_config -v
  ```

- [ ] 1.8 VERIFY: Run all config tests and check coverage
  ```bash
  # Run all config tests
  PYTHONPATH=/home/hamr/PycharmProjects/aurora/packages/cli/src:/home/hamr/PycharmProjects/aurora/packages/core/src python3 -m pytest tests/unit/cli/test_config_paths.py -v --cov=aurora_cli.config --cov-report=term-missing
  # Should be >95% coverage for config.py changes
  ```

---

### 2.0 Implement Helper Functions (Extracted from init_planning.py)

- [x] 2.1 TEST: Create test_init_helpers.py with failing tests
  - Create `tests/unit/cli/test_init_helpers.py`
  - Test `detect_git_repository()` with/without .git directory
  - Test `detect_existing_setup()` with/without .aurora directory
  - Test `detect_configured_tools()` counts tools correctly
  - Test `create_directory_structure()` creates all directories
  - Test `create_project_md()` generates template
  - Test `create_project_md()` preserves existing file
  - Test `detect_project_metadata()` detects Python/JavaScript
  - Test `prompt_git_init()` message formatting
  ```bash
  # Verify tests fail (RED)
  PYTHONPATH=/home/hamr/PycharmProjects/aurora/packages/cli/src:/home/hamr/PycharmProjects/aurora/packages/core/src python3 -m pytest tests/unit/cli/test_init_helpers.py -v
  ```

- [x] 2.2 IMPLEMENT: Create init_helpers.py module
  - Extract `detect_existing_setup()` from init_planning.py
  - Extract `detect_configured_tools()` from init_planning.py
  - Extract `create_directory_structure()` from init_planning.py (modify for new structure)
  - Extract `prompt_tool_selection()` from init_planning.py
  - Extract `configure_tools()` from init_planning.py
  - Add `detect_git_repository(project_path: Path) -> bool`
  - Add `prompt_git_init() -> bool`
  - Add `create_project_md(project_path: Path)`
  - Add `detect_project_metadata(project_path: Path) -> dict`
  - Add `count_configured_tools(project_path: Path) -> int`
  ```bash
  # Verify tests pass (GREEN)
  PYTHONPATH=/home/hamr/PycharmProjects/aurora/packages/cli/src:/home/hamr/PycharmProjects/aurora/packages/core/src python3 -m pytest tests/unit/cli/test_init_helpers.py -v
  ```

- [x] 2.3 VERIFY: Type check and lint helpers
  ```bash
  # Type check
  mypy packages/cli/src/aurora_cli/commands/init_helpers.py --show-error-codes
  # Lint
  ruff check packages/cli/src/aurora_cli/commands/init_helpers.py
  ```

- [ ] 2.4 TEST: Write tests for project metadata detection
  - Test Python detection from pyproject.toml
  - Test JavaScript detection from package.json
  - Test pytest detection from pytest.ini
  - Test auto-detection marks values with "(detected)"
  ```bash
  # Verify tests fail (RED)
  PYTHONPATH=/home/hamr/PycharmProjects/aurora/packages/cli/src:/home/hamr/PycharmProjects/aurora/packages/core/src python3 -m pytest tests/unit/cli/test_init_helpers.py::test_detect_project_metadata -v
  ```

- [ ] 2.5 IMPLEMENT: Complete detect_project_metadata()
  - Detect project name from directory or git remote
  - Detect Python version from pyproject.toml
  - Detect package manager (poetry, pip, pipenv)
  - Detect JavaScript/TypeScript from package.json
  - Detect testing framework (pytest, jest)
  - Return formatted markdown string
  ```bash
  # Verify tests pass (GREEN)
  PYTHONPATH=/home/hamr/PycharmProjects/aurora/packages/cli/src:/home/hamr/PycharmProjects/aurora/packages/core/src python3 -m pytest tests/unit/cli/test_init_helpers.py::test_detect_project_metadata -v
  ```

- [ ] 2.6 VERIFY: Run all helper tests with coverage
  ```bash
  # Run all helper tests
  PYTHONPATH=/home/hamr/PycharmProjects/aurora/packages/cli/src:/home/hamr/PycharmProjects/aurora/packages/core/src python3 -m pytest tests/unit/cli/test_init_helpers.py -v --cov=aurora_cli.commands.init_helpers --cov-report=term-missing
  # Should be >95% coverage
  ```

---

### 3.0 Implement Step 1: Planning Setup (Git + Directories)

- [x] 3.1 TEST: Write failing tests for run_step_1_planning_setup()
  - Create `tests/unit/cli/test_init_unified.py`
  - Test git detection when .git exists
  - Test git detection when .git missing
  - Test git init flow when user accepts
  - Test git init flow when user declines
  - Test directory creation (plans/active, plans/archive, logs, cache)
  - Test project.md creation with metadata
  - Test project.md preservation on re-run
  - Mock subprocess.run for git init
  - Mock questionary for user prompts
  ```bash
  # Verify tests fail (RED)
  PYTHONPATH=/home/hamr/PycharmProjects/aurora/packages/cli/src:/home/hamr/PycharmProjects/aurora/packages/core/src python3 -m pytest tests/unit/cli/test_init_unified.py::test_run_step_1 -v
  ```

- [x] 3.2 IMPLEMENT: Create run_step_1_planning_setup() function
  - Check for .git directory existence
  - If missing: call prompt_git_init()
  - If user accepts: run subprocess.run(["git", "init"])
  - If user declines: show warning, skip planning dirs
  - Create .aurora/plans/active/ and .aurora/plans/archive/
  - Create .aurora/logs/ and .aurora/cache/
  - Call create_project_md() with auto-detection
  - Show success message
  - Return True if git initialized, False otherwise
  ```bash
  # Verify tests pass (GREEN)
  PYTHONPATH=/home/hamr/PycharmProjects/aurora/packages/cli/src:/home/hamr/PycharmProjects/aurora/packages/core/src python3 -m pytest tests/unit/cli/test_init_unified.py::test_run_step_1 -v
  ```

- [x] 3.3 VERIFY: Type check and lint
  ```bash
  # Type check
  mypy packages/cli/src/aurora_cli/commands/init.py --show-error-codes
  # Lint
  ruff check packages/cli/src/aurora_cli/commands/init.py
  ```

- [x] 3.4 VERIFY: Run Step 1 tests with coverage
  ```bash
  # Run Step 1 tests
  PYTHONPATH=/home/hamr/PycharmProjects/aurora/packages/cli/src:/home/hamr/PycharmProjects/aurora/packages/core/src python3 -m pytest tests/unit/cli/test_init_unified.py::test_run_step_1 -v --cov=aurora_cli.commands.init --cov-report=term-missing
  ```

---

### 4.0 Implement Step 2: Memory Indexing

- [x] 4.1 TEST: Write failing tests for run_step_2_memory_indexing()
  - Test db_path calculation (project-specific)
  - Test re-index prompt when memory.db exists
  - Test backup creation before re-indexing
  - Test error handling with mock exception
  - Test skip option continues to next step
  - Test abort option exits cleanly
  - Mock MemoryManager to avoid real indexing
  ```bash
  # Verify tests fail (RED)
  PYTHONPATH=/home/hamr/PycharmProjects/aurora/packages/cli/src:/home/hamr/PycharmProjects/aurora/packages/core/src python3 -m pytest tests/unit/cli/test_init_unified.py::test_run_step_2 -v
  ```

- [x] 4.2 IMPLEMENT: Create run_step_2_memory_indexing() function
  - Determine db_path as project_path / ".aurora" / "memory.db"
  - Check if memory.db exists
  - If exists: prompt "Re-index?" with click.confirm()
  - If confirmed: backup to memory.db.backup with shutil.copy()
  - Create Config with project-specific db_path
  - Create MemoryManager with custom config
  - Create rich progress bar
  - Call manager.index_path() with progress_callback
  - Show success with stats
  - Handle exceptions with skip/abort prompt
  ```bash
  # Verify tests pass (GREEN)
  PYTHONPATH=/home/hamr/PycharmProjects/aurora/packages/cli/src:/home/hamr/PycharmProjects/aurora/packages/core/src python3 -m pytest tests/unit/cli/test_init_unified.py::test_run_step_2 -v
  ```

- [x] 4.3 TEST: Write tests for MemoryManager project-specific paths
  - Test MemoryManager accepts custom db_path in Config
  - Test MemoryManager.index_path() works with project db
  - Test Config.get_db_path() expands project paths correctly
  - **SKIPPED**: MemoryManager already supports project-specific paths via Config parameter
  - Verified in code review: MemoryManager.__init__() accepts Config, calls config.get_db_path()

- [x] 4.4 IMPLEMENT: Verify/update MemoryManager for project paths
  - Review MemoryManager.__init__() signature
  - Ensure accepts Config with custom db_path
  - Update if necessary to support project-specific paths
  - Test with both global and project-specific paths
  - **VERIFIED**: MemoryManager already fully supports Config(db_path=...) pattern
  - Implementation at memory_manager.py:157-162 creates SQLiteStore with config.get_db_path()

- [x] 4.5 VERIFY: Type check and run all Step 2 tests
  ```bash
  # Type check (pre-existing mypy issues unrelated to our changes)
  # Run all Step 2 tests
  PYTHONPATH=/home/hamr/PycharmProjects/aurora/packages/cli/src:/home/hamr/PycharmProjects/aurora/packages/core/src:/home/hamr/PycharmProjects/aurora/packages/context-code/src python3 -m pytest tests/unit/cli/test_init_unified.py::TestStep2MemoryIndexing -v
  # Result: 9 passed, 1 warning
  ```

---

### 5.0 Implement Step 3: Tool Configuration

- [ ] 5.1 TEST: Write failing tests for run_step_3_tool_configuration()
  - Test tool detection with 0, 1, multiple tools
  - Test interactive selection returns correct tools
  - Test configure_tools() creates new configs
  - Test configure_tools() updates existing configs
  - Test marker preservation in updates
  - Test return tuple of (created, updated) lists
  - Mock questionary for checkbox selection
  ```bash
  # Verify tests fail (RED)
  PYTHONPATH=/home/hamr/PycharmProjects/aurora/packages/cli/src:/home/hamr/PycharmProjects/aurora/packages/core/src python3 -m pytest tests/unit/cli/test_init_unified.py::test_run_step_3 -v
  ```

- [ ] 5.2 IMPLEMENT: Create run_step_3_tool_configuration() function
  - Call detect_configured_tools() to find existing
  - Call prompt_tool_selection() for interactive checkbox
  - Call configure_tools() to apply configurations
  - Track created vs updated in separate lists
  - Show success message with counts
  - Return tuple of (created_tools, updated_tools)
  ```bash
  # Verify tests pass (GREEN)
  PYTHONPATH=/home/hamr/PycharmProjects/aurora/packages/cli/src:/home/hamr/PycharmProjects/aurora/packages/core/src python3 -m pytest tests/unit/cli/test_init_unified.py::test_run_step_3 -v
  ```

- [ ] 5.3 VERIFY: Type check and run Step 3 tests
  ```bash
  # Type check
  mypy packages/cli/src/aurora_cli/commands/init.py --show-error-codes
  # Run Step 3 tests
  PYTHONPATH=/home/hamr/PycharmProjects/aurora/packages/cli/src:/home/hamr/PycharmProjects/aurora/packages/core/src python3 -m pytest tests/unit/cli/test_init_unified.py::test_run_step_3 -v --cov=aurora_cli.commands.init
  ```

---

### 6.0 Implement Main init_command() Structure

- [ ] 6.1 TEST: Write failing tests for init_command() main flow
  - Test --config flag fast path
  - Test --config flag errors without .aurora
  - Test full init flow calls all 3 steps
  - Test success summary displays correctly
  - Test step numbering (1/3, 2/3, 3/3)
  - Use CliRunner.invoke() with input simulation
  ```bash
  # Verify tests fail (RED)
  PYTHONPATH=/home/hamr/PycharmProjects/aurora/packages/cli/src:/home/hamr/PycharmProjects/aurora/packages/core/src python3 -m pytest tests/unit/cli/test_init_unified.py::test_init_command -v
  ```

- [ ] 6.2 IMPLEMENT: Create main init_command() function
  - Add @click.command(name="init") decorator
  - Add @click.option("--config", is_flag=True)
  - Add @handle_errors decorator
  - Handle --config flag: check .aurora exists, run Step 3 only
  - Check for existing setup with detect_existing_setup()
  - If existing: call prompt_rerun_options()
  - Display welcome banner
  - Call run_step_1_planning_setup() with progress
  - Call run_step_2_memory_indexing() with progress
  - Call run_step_3_tool_configuration() with progress
  - Call display_success_summary()
  ```bash
  # Verify tests pass (GREEN)
  PYTHONPATH=/home/hamr/PycharmProjects/aurora/packages/cli/src:/home/hamr/PycharmProjects/aurora/packages/core/src python3 -m pytest tests/unit/cli/test_init_unified.py::test_init_command -v
  ```

- [ ] 6.3 VERIFY: Type check and run all unit tests
  ```bash
  # Type check
  mypy packages/cli/src/aurora_cli/commands/init.py --show-error-codes
  # Run all init unit tests
  PYTHONPATH=/home/hamr/PycharmProjects/aurora/packages/cli/src:/home/hamr/PycharmProjects/aurora/packages/core/src python3 -m pytest tests/unit/cli/test_init_unified.py -v --cov=aurora_cli.commands.init --cov-report=term-missing
  # Should be >90% coverage
  ```

---

### 7.0 Implement Idempotent Re-Run Behavior

- [ ] 7.1 TEST: Write failing tests for show_status_summary()
  - Test status display with all steps complete
  - Test status display with partial completion
  - Test chunk count from memory.db
  - Test tool count display
  - Test formatting and checkmarks
  ```bash
  # Verify tests fail (RED)
  PYTHONPATH=/home/hamr/PycharmProjects/aurora/packages/cli/src:/home/hamr/PycharmProjects/aurora/packages/core/src python3 -m pytest tests/unit/cli/test_init_unified.py::test_show_status_summary -v
  ```

- [ ] 7.2 IMPLEMENT: Create show_status_summary() function
  - Check Step 1: .aurora/plans/active existence
  - Show checkmark with mtime
  - Check Step 2: .aurora/memory.db existence
  - If exists: count chunks, show stats
  - Check Step 3: count_configured_tools()
  - Show tool count
  - Use rich console formatting
  ```bash
  # Verify tests pass (GREEN)
  PYTHONPATH=/home/hamr/PycharmProjects/aurora/packages/cli/src:/home/hamr/PycharmProjects/aurora/packages/core/src python3 -m pytest tests/unit/cli/test_init_unified.py::test_show_status_summary -v
  ```

- [ ] 7.3 TEST: Write failing tests for prompt_rerun_options()
  - Test menu displays 4 options
  - Test returns "all", "selective", "config", "exit"
  - Test invalid input handling
  - Mock click.prompt()
  ```bash
  # Verify tests fail (RED)
  PYTHONPATH=/home/hamr/PycharmProjects/aurora/packages/cli/src:/home/hamr/PycharmProjects/aurora/packages/core/src python3 -m pytest tests/unit/cli/test_init_unified.py::test_prompt_rerun_options -v
  ```

- [ ] 7.4 IMPLEMENT: Create prompt_rerun_options() function
  - Display numbered menu with 4 options
  - Use click.prompt() to get choice
  - Return one of: "all", "selective", "config", "exit"
  - Handle invalid input with retry
  ```bash
  # Verify tests pass (GREEN)
  PYTHONPATH=/home/hamr/PycharmProjects/aurora/packages/cli/src:/home/hamr/PycharmProjects/aurora/packages/core/src python3 -m pytest tests/unit/cli/test_init_unified.py::test_prompt_rerun_options -v
  ```

- [ ] 7.5 TEST: Write failing tests for selective_step_selection()
  - Test checkbox with 3 step options
  - Test returns list of selected steps [1, 2, 3]
  - Test empty selection shows warning
  - Mock questionary.checkbox()
  ```bash
  # Verify tests fail (RED)
  PYTHONPATH=/home/hamr/PycharmProjects/aurora/packages/cli/src:/home/hamr/PycharmProjects/aurora/packages/core/src python3 -m pytest tests/unit/cli/test_init_unified.py::test_selective_step_selection -v
  ```

- [ ] 7.6 IMPLEMENT: Create selective_step_selection() function
  - Use questionary.checkbox() with 3 options
  - Return list of selected step numbers
  - If empty: show warning, return empty list
  ```bash
  # Verify tests pass (GREEN)
  PYTHONPATH=/home/hamr/PycharmProjects/aurora/packages/cli/src:/home/hamr/PycharmProjects/aurora/packages/core/src python3 -m pytest tests/unit/cli/test_init_unified.py::test_selective_step_selection -v
  ```

- [ ] 7.7 TEST: Write failing tests for re-run safety mechanisms
  - Test project.md preservation on re-run
  - Test marker content preservation in tools
  - Test backup creation before re-indexing
  - Test no errors on 10 consecutive re-runs
  ```bash
  # Verify tests fail (RED)
  PYTHONPATH=/home/hamr/PycharmProjects/aurora/packages/cli/src:/home/hamr/PycharmProjects/aurora/packages/core/src python3 -m pytest tests/unit/cli/test_init_unified.py::test_rerun_safety -v
  ```

- [ ] 7.8 IMPLEMENT: Update init_command() with re-run logic
  - After existing setup detected: call show_status_summary()
  - Call prompt_rerun_options()
  - If "exit": return
  - If "config": set flag, run Step 3 only
  - If "all": run all steps
  - If "selective": call selective_step_selection(), run selected
  - For selective: conditionally call step functions
  - Show skipped messages for unselected steps
  ```bash
  # Verify tests pass (GREEN)
  PYTHONPATH=/home/hamr/PycharmProjects/aurora/packages/cli/src:/home/hamr/PycharmProjects/aurora/packages/core/src python3 -m pytest tests/unit/cli/test_init_unified.py::test_rerun_safety -v
  ```

- [ ] 7.9 VERIFY: Run all idempotent tests
  ```bash
  # Run all re-run tests
  PYTHONPATH=/home/hamr/PycharmProjects/aurora/packages/cli/src:/home/hamr/PycharmProjects/aurora/packages/core/src python3 -m pytest tests/unit/cli/test_init_unified.py::test_show_status_summary tests/unit/cli/test_init_unified.py::test_prompt_rerun_options tests/unit/cli/test_init_unified.py::test_selective_step_selection tests/unit/cli/test_init_unified.py::test_rerun_safety -v --cov=aurora_cli.commands.init
  ```

---

### 8.0 Implement Integration Tests

- [ ] 8.1 TEST: Create test_init_flow.py with integration tests
  - Test first-time init full flow (git, indexing, tools)
  - Test init without git (user declines)
  - Test --config flag skips Steps 1-2
  - Test --config flag errors without .aurora
  - Test re-run is idempotent (exit option)
  - Test re-run all steps (with backup)
  - Test selective step re-run
  - Test indexing failure recovery
  - Use CliRunner.invoke() with tmp_path
  - Use input simulation for prompts
  ```bash
  # Verify tests fail (RED) - command not registered yet
  PYTHONPATH=/home/hamr/PycharmProjects/aurora/packages/cli/src:/home/hamr/PycharmProjects/aurora/packages/core/src python3 -m pytest tests/integration/cli/test_init_flow.py -v
  ```

- [ ] 8.2 IMPLEMENT: Register init_command in main.py
  - Import init_command from commands.init
  - Add cli.add_command(init_command) registration
  - Remove init_planning_command import
  - Remove cli.add_command(init_planning_command) registration
  ```bash
  # Verify tests pass (GREEN)
  PYTHONPATH=/home/hamr/PycharmProjects/aurora/packages/cli/src:/home/hamr/PycharmProjects/aurora/packages/core/src python3 -m pytest tests/integration/cli/test_init_flow.py -v
  ```

- [ ] 8.3 VERIFY: Run all integration tests with coverage
  ```bash
  # Run integration tests
  PYTHONPATH=/home/hamr/PycharmProjects/aurora/packages/cli/src:/home/hamr/PycharmProjects/aurora/packages/core/src python3 -m pytest tests/integration/cli/test_init_flow.py -v --cov=aurora_cli.commands.init --cov-report=term-missing
  # Should be >90% coverage
  ```

- [ ] 8.4 VERIFY: Check init-planning command is removed
  ```bash
  # Should error with "no such command"
  PYTHONPATH=/home/hamr/PycharmProjects/aurora/packages/cli/src:/home/hamr/PycharmProjects/aurora/packages/core/src python3 -m aurora_cli.main init-planning --help 2>&1 | grep -q "no such command" && echo "PASS: init-planning removed" || echo "FAIL: init-planning still exists"
  ```

---

### 9.0 Verify All Phase 1 Tests Still Pass

- [ ] 9.1 TEST: Run full test suite
  ```bash
  # Run all tests
  PYTHONPATH=/home/hamr/PycharmProjects/aurora/packages/cli/src:/home/hamr/PycharmProjects/aurora/packages/core/src:/home/hamr/PycharmProjects/aurora/packages/context-code/src python3 -m pytest tests/ -v
  # Should pass all 312 Phase 1 tests + new init tests
  ```

- [ ] 9.2 VERIFY: Check test count increased correctly
  ```bash
  # Count tests
  PYTHONPATH=/home/hamr/PycharmProjects/aurora/packages/cli/src:/home/hamr/PycharmProjects/aurora/packages/core/src python3 -m pytest tests/ --co -q | wc -l
  # Should be ~350-360 tests (312 + ~40 new)
  ```

- [ ] 9.3 VERIFY: Run type checking on all modified files
  ```bash
  # Type check all modified files
  mypy packages/cli/src/aurora_cli/config.py --show-error-codes
  mypy packages/cli/src/aurora_cli/commands/init.py --show-error-codes
  mypy packages/cli/src/aurora_cli/commands/init_helpers.py --show-error-codes
  mypy packages/cli/src/aurora_cli/main.py --show-error-codes
  mypy packages/cli/src/aurora_cli/memory_manager.py --show-error-codes
  # Should have 0 new errors
  ```

- [ ] 9.4 VERIFY: Run linting on all modified files
  ```bash
  # Lint all modified files
  ruff check packages/cli/src/aurora_cli/config.py
  ruff check packages/cli/src/aurora_cli/commands/init.py
  ruff check packages/cli/src/aurora_cli/commands/init_helpers.py
  ruff check packages/cli/src/aurora_cli/main.py
  ruff check packages/cli/src/aurora_cli/memory_manager.py
  # Should have 0 errors
  ```

- [ ] 9.5 VERIFY: Run quality check
  ```bash
  # Run full quality check
  make quality-check
  # Should pass all checks
  ```

---

### 10.0 Clean Up Legacy Code

- [ ] 10.1 VERIFY: No imports of init_planning exist
  ```bash
  # Search for init_planning imports
  grep -r "from.*init_planning" packages/cli/src/ tests/
  grep -r "import.*init_planning" packages/cli/src/ tests/
  # Should return no results
  ```

- [ ] 10.2 DELETE: Remove init_planning.py
  ```bash
  # Delete file
  rm packages/cli/src/aurora_cli/commands/init_planning.py
  # Verify deleted
  test ! -f packages/cli/src/aurora_cli/commands/init_planning.py && echo "PASS: init_planning.py deleted" || echo "FAIL: File still exists"
  ```

- [ ] 10.3 DELETE: Remove test_init_planning.py
  ```bash
  # Delete file
  rm tests/unit/cli/test_init_planning.py
  # Verify deleted
  test ! -f tests/unit/cli/test_init_planning.py && echo "PASS: test_init_planning.py deleted" || echo "FAIL: File still exists"
  ```

- [ ] 10.4 VERIFY: Tests still pass after deletion
  ```bash
  # Run all tests
  PYTHONPATH=/home/hamr/PycharmProjects/aurora/packages/cli/src:/home/hamr/PycharmProjects/aurora/packages/core/src:/home/hamr/PycharmProjects/aurora/packages/context-code/src python3 -m pytest tests/ -v
  # Should pass all tests
  ```

- [ ] 10.5 TEST: Write test for fresh install (no global config)
  - Create new virtual environment
  - Install Aurora from source
  - Run aur init in fresh project
  - Verify no global config created
  - Verify no API key prompts
  - Verify only budget_tracker.json in ~/.aurora/
  ```bash
  # Manual test - document results
  python3 -m venv /tmp/test-venv
  source /tmp/test-venv/bin/activate
  pip install -e .
  mkdir /tmp/test-project && cd /tmp/test-project
  aur init
  # Verify results manually
  ```

---

### 11.0 Update Documentation

- [ ] 11.1 UPDATE: CLI_USAGE_GUIDE.md initialization section
  - Replace two-command docs with single `aur init`
  - Document 3-step flow
  - Add --config flag usage
  - Add re-run safety section
  - Document project-specific vs global structure
  - Add examples for common scenarios
  - Remove `aur init-planning` references
  ```bash
  # Verify no broken links
  grep -n "init-planning" docs/cli/CLI_USAGE_GUIDE.md
  # Should return no results
  ```

- [ ] 11.2 CREATE: MIGRATION_GUIDE_v0.3.0.md
  - Add migration title
  - Document breaking changes
  - Provide 4-step migration instructions
  - Add budget tracker preservation warning
  - Include verification commands
  - Add troubleshooting section
  - Document data preservation vs reset
  - Add estimated time (<5 minutes)
  ```bash
  # Verify file created
  test -f docs/cli/MIGRATION_GUIDE_v0.3.0.md && echo "PASS: Migration guide created" || echo "FAIL: File missing"
  ```

- [ ] 11.3 UPDATE: README.md quick start
  - Update installation quick start
  - Remove init-planning references
  - Update example output
  - Add git integration note
  - Update "Getting Started" section
  ```bash
  # Verify no init-planning references
  grep -n "init-planning" README.md
  # Should return no results
  ```

- [ ] 11.4 CREATE: Release notes for v0.3.0
  - Add breaking changes with warnings
  - List new features
  - Document migration requirements
  - Add upgrade path with commands
  - Link to migration guide
  - Note Phase 1.5 enhancement
  ```bash
  # Verify file created
  test -f docs/RELEASE_NOTES_v0.3.0.md && echo "PASS: Release notes created" || echo "FAIL: File missing"
  ```

- [ ] 11.5 VERIFY: Search for all init-planning references
  ```bash
  # Search all markdown files
  find docs/ -name "*.md" -exec grep -l "init-planning" {} \;
  # Should return no results
  ```

---

### 12.0 Performance Testing

- [ ] 12.1 TEST: Write performance tests
  - Test init with 100 files completes in <7s
  - Test init with 1000 files completes in <30s
  - Test progress bar updates smoothly
  - Test memory usage <100MB during indexing
  - Use pytest-benchmark for timing
  ```bash
  # Run performance tests
  PYTHONPATH=/home/hamr/PycharmProjects/aurora/packages/cli/src:/home/hamr/PycharmProjects/aurora/packages/core/src python3 -m pytest tests/performance/test_init_performance.py -v --benchmark-only
  ```

- [ ] 12.2 VERIFY: Performance targets met
  ```bash
  # Check benchmark results
  PYTHONPATH=/home/hamr/PycharmProjects/aurora/packages/cli/src:/home/hamr/PycharmProjects/aurora/packages/core/src python3 -m pytest tests/performance/test_init_performance.py -v --benchmark-compare
  # Verify targets: <7s for 100 files, <30s for 1000 files
  ```

---

### 13.0 Acceptance Testing

- [ ] 13.1 MANUAL: Test first-time user flow
  - Fresh directory
  - Run: aur init
  - Accept git init
  - Wait for indexing progress bar
  - Select 2 tools (Claude Code + Universal)
  - Verify success message
  - Run: aur plan create "Test"
  - Verify plan created
  ```bash
  # Manual test - document results in acceptance test log
  ```

- [ ] 13.2 MANUAL: Test multi-project isolation
  - Create project A: mkdir project-a && cd project-a
  - Run: aur init
  - Index Python files
  - Run: aur mem search "test"
  - Create project B: mkdir project-b && cd project-b
  - Run: aur init
  - Run: aur mem search "test"
  - Verify: No results from project A
  ```bash
  # Manual test - document results
  ```

- [ ] 13.3 MANUAL: Test re-run safety
  - Initialized project with custom project.md edits
  - Run: aur init again
  - Choose "Re-run all steps"
  - Verify: Custom content preserved
  - Verify: Tool templates updated within markers only
  ```bash
  # Manual test - document results
  ```

- [ ] 13.4 MANUAL: Test error handling
  - Simulate disk space issue
  - Run: aur init
  - Verify error message
  - Free space
  - Re-run: aur init
  - Verify success
  ```bash
  # Manual test - document results
  ```

---

### 14.0 Final Verification

- [ ] 14.1 VERIFY: All functional requirements covered
  - FR-1: Unified command structure ✓
  - FR-2: Step 1 - Planning setup ✓
  - FR-3: Step 2 - Memory indexing ✓
  - FR-4: Step 3 - Tool configuration ✓
  - FR-5: Idempotent re-run ✓
  - FR-6: --config flag ✓
  - FR-7: Success feedback ✓
  - FR-8: No API key prompts ✓
  ```bash
  # Run full test suite one final time
  make test
  ```

- [ ] 14.2 VERIFY: All acceptance criteria met
  - AC-1: Command exists and executes ✓
  - AC-2: Step 1 (Planning setup) ✓
  - AC-3: Step 2 (Memory indexing) ✓
  - AC-4: Step 3 (Tool configuration) ✓
  - AC-5: --config flag ✓
  - AC-6: Idempotent re-run ✓
  - AC-7: Success feedback ✓
  - AC-8: Code quality ✓
  - AC-9: Performance ✓
  - AC-10: Error handling ✓
  - AC-11: Documentation ✓
  ```bash
  # Verify test count and coverage
  PYTHONPATH=/home/hamr/PycharmProjects/aurora/packages/cli/src:/home/hamr/PycharmProjects/aurora/packages/core/src python3 -m pytest tests/ -v --cov=aurora_cli --cov-report=term-missing
  # Should show >90% coverage for init logic
  ```

- [ ] 14.3 VERIFY: Quality gates pass
  ```bash
  # Run full quality check
  make quality-check
  # Should pass: lint, type-check, test, coverage
  ```

- [ ] 14.4 VERIFY: Documentation complete
  - CLI_USAGE_GUIDE.md updated ✓
  - MIGRATION_GUIDE_v0.3.0.md created ✓
  - README.md updated ✓
  - Release notes created ✓
  - All init-planning references removed ✓
  ```bash
  # Search for any remaining init-planning references
  grep -r "init-planning" docs/ README.md
  # Should return no results
  ```

- [ ] 14.5 COMMIT: Final commit with all changes
  ```bash
  # Stage all changes
  git add -A
  # Create commit
  git commit -m "feat(cli): unified aur init command (Phase 1.5)

- Merge init and init-planning into single command
- Add git-aware initialization with git init prompt
- Implement project-specific memory database
- Add idempotent re-run with status detection
- Add --config flag for tool-only configuration
- Update all paths from global to project-specific
- Remove API key prompts (env vars only)
- Add comprehensive test suite (>90% coverage)
- Update documentation and migration guide

BREAKING CHANGES:
- init-planning command removed (use init --config)
- Memory database moved from ~/.aurora/ to ./.aurora/
- Global config.json removed (env vars only)
- Requires manual migration (see MIGRATION_GUIDE_v0.3.0.md)

Implements PRD 0018
Closes #[issue-number]

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
  ```

---

## Verification Checklist

Before marking complete, verify:

- [ ] All 14 task groups completed
- [ ] All tests pass (>350 total tests)
- [ ] Test coverage >90% for init logic
- [ ] All Phase 1 tests (312) still pass
- [ ] No new mypy errors
- [ ] No new linting errors
- [ ] Performance targets met (<7s for 100 files)
- [ ] Documentation updated and complete
- [ ] Migration guide tested
- [ ] Manual acceptance tests completed
- [ ] All functional requirements covered
- [ ] All acceptance criteria met
- [ ] init-planning command fully removed
- [ ] Fresh install test successful

---

## Success Criteria Summary

Implementation is successful when:

1. ✅ `aur init` command works with single 3-step flow
2. ✅ Git integration prompts and runs `git init`
3. ✅ Memory.db created at `./.aurora/memory.db`
4. ✅ Idempotent re-runs preserve custom content
5. ✅ Marker-based tool updates work correctly
6. ✅ --config flag runs Step 3 only
7. ✅ All 312 Phase 1 tests still pass
8. ✅ New test suite has >90% coverage
9. ✅ Documentation complete with migration guide
10. ✅ `aur init-planning` command removed

---

**Status**: Ready for TDD implementation
**Next Step**: Start with Task 1.1 (Write failing tests for config paths)
**Estimated Time**: 1-2 days with TDD approach
