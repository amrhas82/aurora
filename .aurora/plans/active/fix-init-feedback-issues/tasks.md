# Implementation Tasks: Fix aur init Feedback Issues

## 1. Fix Project-Local Configuration (CRITICAL)

### 1.1 Investigate Current Config Loading
- [ ] Read `packages/cli/src/aurora_cli/config.py:load_config()`
- [ ] Trace where config is loaded in plan creation
- [ ] Identify why global config is used instead of project-local
- [ ] Document current behavior vs expected behavior

### 1.2 Fix Config Loading Priority
- [ ] Update `load_config()` to check `./.aurora/config.json` first
- [ ] Ensure project-local config takes full precedence (no merging)
- [ ] Verify `get_plans_path()` uses project-local paths
- [ ] Add logging to show which config file was loaded

### 1.3 Verify All Path Resolution
- [ ] Check `db_path` resolves to `./.aurora/memory.db`
- [ ] Check `planning_base_dir` resolves to `./.aurora/plans`
- [ ] Check `agents_manifest_path` resolves to `./.aurora/cache/agent_manifest.json`
- [ ] Check `logging_file` resolves to `./.aurora/logs/aurora.log`
- [ ] Verify `budget_tracker_path` remains `~/.aurora/budget_tracker.json` (global)

### 1.4 Test Config Resolution
- [ ] Create test project in `/tmp/test-config`
- [ ] Run `aur init`
- [ ] Create plan with `aur plan create "Test"`
- [ ] Verify plan created in `./.aurora/plans/active/`
- [ ] Verify NOT in `~/.aurora/plans/active/`

## 2. Fix Plan ID Sequential Numbering

### 2.1 Investigate ID Generator
- [ ] Read `packages/planning/src/aurora_planning/id_generator.py`
- [ ] Identify current numbering logic
- [ ] Find where high numbers (2042) come from
- [ ] Check if counting global plans instead of project plans

### 2.2 Implement Sequential Numbering
- [ ] Modify ID generator to use 4-digit format: `{num:04d}-{name}`
- [ ] Count plans in project directory only (not global)
- [ ] Start from 0001 in new projects
- [ ] Continue from highest number in existing projects
- [ ] Include archived plans in count

### 2.3 Test Plan Numbering
- [ ] Create fresh project: `/tmp/test-numbering`
- [ ] Create first plan → should be `0001-<name>`
- [ ] Create second plan → should be `0002-<name>`
- [ ] Create third plan → should be `0003-<name>`
- [ ] Archive plan 0001 → verify numbering still works
- [ ] Create fourth plan → should be `0004-<name>`

## 3. Enhance `aur mem stats`

### 3.1 Add Error Tracking to Indexing
- [ ] Modify `memory_manager.py` to store failed files
- [ ] Store error messages for each failed file
- [ ] Track warnings during indexing
- [ ] Save metadata to database or separate JSON file

### 3.2 Enhance Stats Output
- [ ] Add "Last Indexed" timestamp to output
- [ ] Add "Success Rate" calculation
- [ ] Add "Failed Files" section with errors
- [ ] Add "Warnings" section with counts
- [ ] Add suggestion to re-index if errors present
- [ ] Add `--verbose` flag for full error list

### 3.3 Update Stats Command
- [ ] Modify `packages/cli/src/aurora_cli/commands/memory.py:stats()`
- [ ] Query indexing metadata from storage
- [ ] Format output with error details
- [ ] Use Rich tables for better presentation

### 3.4 Test Enhanced Stats
- [ ] Index project with some failures
- [ ] Run `aur mem stats`
- [ ] Verify failed files are shown
- [ ] Verify warnings are displayed
- [ ] Verify success rate calculated correctly

## 4. Update Messages to Reference `aur mem stats`

### 4.1 Update Planning Messages
- [ ] `packages/cli/src/aurora_cli/planning/errors.py:85` - Change to "aur mem stats"
- [ ] `packages/cli/src/aurora_cli/planning/memory.py:53` - Change to "aur mem stats"
- [ ] `packages/cli/src/aurora_cli/planning/core.py:1098` - Change to "aur mem stats"
- [ ] `packages/cli/src/aurora_cli/planning/core.py:1177` - Change to "aur mem stats"

### 4.2 Update Error Messages
- [ ] `packages/cli/src/aurora_cli/errors.py:340` - Change to "aur mem stats"
- [ ] `packages/cli/src/aurora_cli/errors.py:383` - Change to "aur mem stats"
- [ ] `packages/cli/src/aurora_cli/errors.py:399` - Change to "aur mem stats"
- [ ] `packages/cli/src/aurora_cli/errors.py:523` - Change to "aur mem stats"
- [ ] `packages/cli/src/aurora_cli/errors.py:578` - Change to "aur mem stats"

### 4.3 Update Memory Command Messages
- [ ] `packages/cli/src/aurora_cli/commands/memory.py:228` - Already correct
- [ ] `packages/cli/src/aurora_cli/commands/memory.py:275` - Verify message
- [ ] `packages/cli/src/aurora_cli/commands/memory.py:344` - Verify message

### 4.4 Update Templates
- [ ] `packages/cli/src/aurora_cli/templates/agents.py` - Check if needs update
- [ ] `packages/cli/src/aurora_cli/templates/slash_commands.py` - Check if needs update

### 4.5 Verify Message Consistency
- [ ] Grep for remaining "aur doctor" in indexing context
- [ ] Ensure "aur doctor" only used for system health
- [ ] Test error messages show correct command

## 5. Add Tool Integration Checks to `aur doctor`

### 5.1 Create ToolIntegrationChecks Class
- [ ] Open `packages/cli/src/aurora_cli/health_checks.py`
- [ ] Add `ToolIntegrationChecks` class (similar to existing check classes)
- [ ] Add `__init__` method taking config
- [ ] Add `run_checks()` method returning list of results

### 5.2 Implement Slash Command Detection
- [ ] Import `SlashCommandRegistry` from configurators
- [ ] For each tool in registry, check if slash commands exist
- [ ] Count installed commands per tool (e.g., 7/7)
- [ ] Return check result: ("pass"|"warning"|"fail", message, details)
- [ ] Store tool_id, installed_count, expected_count in details

### 5.3 Implement MCP Server Detection
- [ ] Import MCP configurators (Claude, Cursor, Cline, Continue)
- [ ] For each MCP-capable tool, check if config file exists
- [ ] Validate JSON structure of config file
- [ ] Check if Aurora MCP server entry exists in config
- [ ] Return check result with status and config path

### 5.4 Add Suggestions Generation
- [ ] Collect tools that failed/warned
- [ ] Generate suggestion: "Run 'aur init --config --tools=<tools>' to fix"
- [ ] Group by type (slash commands vs MCP)
- [ ] Return suggestions in details dict

### 5.5 Integrate into `aur doctor`
- [ ] Open `packages/cli/src/aurora_cli/commands/doctor.py`
- [ ] Add ToolIntegrationChecks instantiation
- [ ] Add new section "TOOL INTEGRATION" after CONFIGURATION
- [ ] Run checks and display results
- [ ] Show suggestions at end if any tools need fixing

### 5.6 Test Tool Integration Checks
- [ ] Test with no tools configured → should show all as missing
- [ ] Test with Claude configured → should show ✓
- [ ] Test with partial config → should show ⚠
- [ ] Test with broken MCP config → should show ✗
- [ ] Verify suggestions are actionable
- [ ] Test `aur doctor` includes new section

## 6. Integration Testing

### 6.1 End-to-End Test: Fresh Project
- [ ] Create `/tmp/e2e-test-project`
- [ ] Run `git init`
- [ ] Run `aur init --tools=claude`
- [ ] Verify `./.aurora/` created (not `~/.aurora/`)
- [ ] Run `aur plan create "Feature 1"` → Verify `0001-feature-1`
- [ ] Run `aur plan create "Feature 2"` → Verify `0002-feature-2`
- [ ] Run `aur mem index .`
- [ ] Run `aur mem stats` → Verify enhanced output
- [ ] Run `aur doctor` → Verify TOOL INTEGRATION section shown
- [ ] Verify all messages reference correct commands

### 6.2 Test: Existing Project Migration
- [ ] Create project with existing global config
- [ ] Create `./.aurora/` directory
- [ ] Run `aur plan create "Test"`
- [ ] Verify uses project-local config
- [ ] Verify doesn't break existing plans

### 6.3 Test: Multiple Projects
- [ ] Create `/tmp/project-a` and `/tmp/project-b`
- [ ] Init both with Aurora
- [ ] Create plans in project-a: 0001, 0002
- [ ] Create plans in project-b: 0001, 0002
- [ ] Verify independent numbering
- [ ] Verify separate memory databases

### 6.4 Update Documentation
- [ ] Update CLI usage guide with project-local behavior
- [ ] Document `aur mcp` command in docs
- [ ] Update CHANGELOG with breaking changes (if any)
- [ ] Add migration guide for existing users

## 7. Code Review and Cleanup

- [ ] Run all unit tests: `pytest tests/unit/`
- [ ] Run integration tests: `pytest tests/integration/`
- [ ] Fix any test failures
- [ ] Update test fixtures if needed
- [ ] Run linters: `ruff check`
- [ ] Run type checker: `mypy`
- [ ] Address any issues

## Summary Checklist

**Critical Path** (Must be done first):
- [ ] Task 1: Fix project-local configuration
- [ ] Task 2: Fix plan ID numbering

**Independent Tasks** (Can be done in parallel):
- [ ] Task 3: Enhance `aur mem stats`
- [ ] Task 4: Update message consistency
- [ ] Task 5: Add tool integration checks to `aur doctor`

**Final Steps**:
- [ ] Task 6: Integration testing
- [ ] Task 7: Code review and cleanup

**Estimated Effort**: 14-20 hours total
