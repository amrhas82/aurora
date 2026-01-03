# Tasks: Phase 1 Planning Foundation

**Change ID**: `phase1-planning-foundation`
**Status**: Proposal
**Estimated Duration**: 6 days (1 developer, 50 hours)

---

## Overview

The task list is organized by phase with dependencies noted. Parallel work is possible within each phase but sequence between phases is fixed.

**Legend**:
- ✓ Ready to start (no dependencies)
- ◆ Depends on other tasks (see notes)
- **TDD**: Each task includes test-first verification
- **Verification**: Shell command validation required after completion

---

## Phase 1A: Preparation (Days 1-2)

### Task 1.1: Create Package Directory Structure ✓

**User Story**: As a developer, I need to scaffold the planning package so code can be organized

**Description**: Create `packages/planning/` with all required subdirectories

**Acceptance Criteria**:
- [ ] `packages/planning/src/aurora_planning/` exists
- [ ] All module directories created:
  - [ ] `commands/`
  - [ ] `parsers/`
  - [ ] `schemas/`
  - [ ] `validators/`
  - [ ] `templates/`
  - [ ] `configurators/`
- [ ] All `__init__.py` files exist and are importable
- [ ] Package structure matches OpenSpec layout

**Verification**:
```bash
# Check structure exists
find packages/planning/src/aurora_planning -name "__init__.py" | wc -l
# Should show: 7 files (one per package + root)

# Verify imports work
python -c "from aurora import planning; print('OK')"
```

**Dependencies**: None

---

### Task 1.2: Create pyproject.toml for Planning Package ✓

**User Story**: As a package maintainer, I need dependency configuration so the package can be published

**Description**: Set up `packages/planning/pyproject.toml` with all metadata and dependencies

**Acceptance Criteria**:
- [ ] File created at `packages/planning/pyproject.toml`
- [ ] Package name: `aurora-planning`
- [ ] Version: `0.2.0`
- [ ] Dependencies specified:
  - [ ] `pydantic>=2.0`
  - [ ] `jinja2>=3.1`
  - [ ] `python-slugify>=8.0`
  - [ ] `aurora-core>=0.2.0` (with marker)
- [ ] Namespace package configured: `aurora.planning` → `aurora_planning`
- [ ] Entry points defined for CLI commands
- [ ] License and metadata complete

**Verification**:
```bash
# Install package
cd packages/planning && pip install -e .

# Verify version
python -c "import aurora.planning; print(aurora.planning.__version__)"
# Should show: 0.2.0

# Check dependencies installed
pip list | grep -E "pydantic|jinja|python-slugify"
```

**Dependencies**: Task 1.1

---

### Task 1.3: Copy OpenSpec Source Code ✓

**User Story**: As a developer, I need to migrate OpenSpec code so Phase 1 foundation exists

**Description**: Copy all OpenSpec source files from `/tmp/openspec-source/aurora/` to `packages/planning/src/aurora_planning/`

**Acceptance Criteria**:
- [ ] All Python files copied:
  - [ ] `commands/archive.py`, `create.py`, `init.py`, `list.py`, `view.py`
  - [ ] `parsers/markdown.py`, `requirements.py`, `metadata.py`
  - [ ] `schemas/plan.py`, `validation.py`
  - [ ] `validators/__init__.py`
  - [ ] `templates/` - All `.j2` files
  - [ ] `configurators/base.py`, `claude_code.py`, `opencode.py`, `ampcode.py`, `droid.py`
  - [ ] `config.py`
- [ ] All files preserve original logic (no modifications)
- [ ] File permissions preserved (executable where needed)
- [ ] No temporary or build files copied

**Verification**:
```bash
# Count files
find packages/planning/src/aurora_planning -type f -name "*.py" | wc -l
# Should show: ~20+ Python files

# Verify key files exist
test -f packages/planning/src/aurora_planning/commands/create.py && echo "OK"
test -f packages/planning/src/aurora_planning/configurators/base.py && echo "OK"
```

**Dependencies**: Task 1.2

---

### Task 1.4: Global Import Replacement ✓

**User Story**: As a developer, I need to update imports so the codebase references Aurora, not OpenSpec

**Description**: Replace all `from openspec` imports with `from aurora.planning` throughout the migrated codebase

**Acceptance Criteria**:
- [ ] All internal imports updated: `openspec` → `aurora.planning`
  - Example: `from openspec.schemas import Plan` → `from aurora.planning.schemas import Plan`
- [ ] Cross-package imports use `aurora.*` namespace
  - Example: `from openspec.core import ...` → `from aurora.core import ...`
- [ ] No remaining `openspec` strings in import statements
- [ ] All modules parse without syntax errors
- [ ] Tests confirm all imports resolve

**Verification**:
```bash
# Search for remaining openspec imports
grep -r "from openspec" packages/planning/src/ || echo "None found (correct)"

# Verify Python syntax
python -m py_compile packages/planning/src/aurora_planning/**/*.py

# Test imports
python -c "from aurora.planning.commands import create; print('OK')"
python -c "from aurora.planning.schemas import Plan; print('OK')"
```

**Dependencies**: Task 1.3

---

## Phase 1B: Test Migration (Days 2-3)

### Task 2.1: Organize Test Directories ✓

**User Story**: As a QA engineer, I need test structure organized so coverage is clear

**Description**: Create test directories for planning package tests

**Acceptance Criteria**:
- [ ] Directory structure created:
  - [ ] `tests/unit/planning/` exists
  - [ ] `tests/integration/planning/` exists
- [ ] `conftest.py` placed in both for shared fixtures
- [ ] `.gitkeep` files added to ensure directories tracked

**Verification**:
```bash
# Check directories exist
ls -d tests/unit/planning tests/integration/planning

# Verify structure
find tests/*/planning -name "conftest.py" | wc -l
# Should show: 2 files
```

**Dependencies**: None (can start in parallel with 1.A)

---

### Task 2.2: Copy Test Files ✓

**User Story**: As a QA engineer, I need the test suite migrated so coverage is preserved

**Description**: Copy all 284 tests from OpenSpec to Aurora test structure

**Acceptance Criteria**:
- [ ] All test files copied from `/tmp/openspec-source/tests/` to `tests/unit/planning/` and `tests/integration/planning/`
- [ ] Directory organization preserved:
  - Unit tests: `tests/unit/planning/test_*.py`
  - Integration tests: `tests/integration/planning/test_*.py`
- [ ] No test code modified (logic preserved)
- [ ] All fixtures and utilities included
- [ ] Test count matches: 284 tests collected

**Verification**:
```bash
# Count collected tests
pytest tests/unit/planning tests/integration/planning --collect-only -q
# Should show: 284 tests collected

# Verify no syntax errors
python -m py_compile tests/unit/planning/test_*.py tests/integration/planning/test_*.py
```

**Dependencies**: Task 2.1

---

### Task 2.3: Update Test Imports ✓

**User Story**: As a QA engineer, I need test imports updated so tests run against Aurora code

**Description**: Replace all `from openspec` imports in tests with `from aurora.planning`

**Acceptance Criteria**:
- [ ] All test imports updated: `openspec` → `aurora.planning`
- [ ] Fixture imports updated if they reference OpenSpec
- [ ] No remaining `openspec` imports in test files
- [ ] All test modules parse without syntax errors

**Verification**:
```bash
# Check for remaining openspec imports in tests
grep -r "from openspec" tests/unit/planning tests/integration/planning || echo "None found (correct)"

# Verify syntax
python -m py_compile tests/unit/planning/test_*.py tests/integration/planning/test_*.py
```

**Dependencies**: Task 2.2

---

### Task 2.4: Adapt Test Fixtures for Aurora Structure ◆

**User Story**: As a QA engineer, I need fixtures updated so tests work with Aurora directories

**Description**: Update test fixtures to use Aurora's `.aurora/plans/` structure instead of OpenSpec's `openspec/`

**Acceptance Criteria**:
- [ ] Fixtures use `~/.aurora/plans/active/` for active plans
- [ ] Fixtures use `~/.aurora/plans/archive/` for archived plans
- [ ] Manifest file location: `~/.aurora/plans/manifest.json`
- [ ] All path references updated
- [ ] Temporary test directories cleaned up after tests

**TDD Verification**:
```python
# Test fixture works
import tempfile
from pathlib import Path
from aurora.planning.fixtures import TempPlanDirectory

with TempPlanDirectory() as tmpdir:
    plan_dir = tmpdir / "active" / "0001-test"
    plan_dir.mkdir(parents=True)
    assert plan_dir.exists()
```

**Dependencies**: Task 2.3

---

### Task 2.5: Run Full Test Suite ✓

**User Story**: As a developer, I need all tests passing so code quality is verified

**Description**: Execute test suite and verify all 284 tests pass

**Acceptance Criteria**:
- [ ] `pytest tests/unit/planning tests/integration/planning` runs successfully
- [ ] All 284 tests pass (0 failures)
- [ ] No skipped tests (all are executable)
- [ ] Coverage report shows ≥95% coverage for `aurora.planning`

**Verification**:
```bash
# Run tests
pytest tests/unit/planning tests/integration/planning -v

# Check coverage
pytest tests/unit/planning tests/integration/planning \
  --cov=packages/planning/src/aurora_planning \
  --cov-report=term-missing

# Verify pass rate
pytest tests/unit/planning tests/integration/planning -v | grep "passed"
# Should show: 284 passed
```

**Dependencies**: Task 2.4

**Blocking**: If any tests fail, debug and fix before proceeding

---

## Phase 1C: Commands & CLI (Days 3-4)

### Task 3.1: Implement Plan ID Generation ✓

**User Story**: As a developer, I need plan ID generation so plans have unique identifiers

**Description**: Implement plan ID generator that creates `NNNN-slug` format from manifest

**Acceptance Criteria**:
- [ ] Function: `generate_plan_id(goal: str, next_id: int) -> str`
- [ ] Reads `next_id` from manifest
- [ ] Extracts slug from goal:
  - [ ] Converts to kebab-case
  - [ ] Limits to 50 characters
  - [ ] Allows only alphanumeric + hyphens
- [ ] Returns format: `0001-slug`, `0002-slug`, etc.
- [ ] Handles edge cases:
  - [ ] Very long goals (truncate slug)
  - [ ] Goals with special characters (sanitize)
  - [ ] Goals with only numbers (fallback slug)

**TDD Verification**:
```python
from aurora.planning.generators import generate_plan_id

# Test cases
assert generate_plan_id("Implement OAuth2 authentication", 1) == "0001-implement-oauth2-authentication"
assert generate_plan_id("Fix!@#$% security", 2) == "0002-fix-security"
assert generate_plan_id("A" * 100, 3) == "0003-" + "a" * 50
assert generate_plan_id("123 456", 4) == "0004-123-456"
```

**Dependencies**: None (can start in parallel with Phase 1B)

---

### Task 3.2: Implement Manifest Management ◆

**User Story**: As a developer, I need manifest operations so plans are tracked

**Description**: Implement functions to read, write, and update manifest file

**Acceptance Criteria**:
- [ ] Function: `read_manifest(path) -> Manifest`
  - [ ] Reads JSON from `~/.aurora/plans/manifest.json`
  - [ ] Parses to Manifest dataclass
  - [ ] Handles missing file: returns empty manifest
- [ ] Function: `write_manifest(manifest, path) -> None`
  - [ ] Writes JSON atomically (temp file + rename)
  - [ ] Preserves formatting
  - [ ] Creates backup before overwriting
- [ ] Function: `add_plan(manifest, plan_id) -> Manifest`
  - [ ] Adds plan to `active_plans`
  - [ ] Increments `next_id`
  - [ ] Returns updated manifest
- [ ] Function: `archive_plan(manifest, plan_id) -> Manifest`
  - [ ] Moves plan from `active_plans` to `archived_plans`
  - [ ] Timestamps with `archived_at`
  - [ ] Returns updated manifest

**TDD Verification**:
```python
from aurora.planning.manifest import read_manifest, write_manifest, add_plan

# Test roundtrip
manifest = Manifest(version="1.0", next_id=1, active_plans=[], archived_plans=[])
write_manifest(manifest, Path("/tmp/test_manifest.json"))
loaded = read_manifest(Path("/tmp/test_manifest.json"))
assert loaded.version == "1.0"
assert loaded.next_id == 1
```

**Dependencies**: Task 3.1

---

### Task 3.3: Implement Initialization Command ◆

**User Story**: As a user, I want to run `aur plan init` so my planning environment is ready

**Description**: Implement `aur plan init` command that creates directory structure

**Acceptance Criteria**:
- [ ] Command: `aur plan init`
- [ ] Creates directories:
  - [ ] `~/.aurora/plans/active/` (mode 0755)
  - [ ] `~/.aurora/plans/archive/` (mode 0755)
- [ ] Creates manifest: `~/.aurora/plans/manifest.json`
- [ ] Manifest initialized: `{"version": "1.0", "next_id": 1, "active_plans": [], "archived_plans": []}`
- [ ] Flag `--force`: Reinitialize existing directory
- [ ] Returns `InitResult` with success status
- [ ] Exit code: 0 on success, non-zero on error
- [ ] Idempotent: Can run multiple times without error

**TDD Verification**:
```bash
# Test basic init
aur plan init
echo $?  # Should be 0

# Test idempotent
aur plan init
echo $?  # Should be 0 (no error on re-run)

# Verify directories
ls -d ~/.aurora/plans/active ~/.aurora/plans/archive
# Should list both directories
```

**Dependencies**: Task 3.2

---

### Task 3.4: Implement Create Command ◆

**User Story**: As a user, I want to run `aur plan create "goal"` so a new plan is generated

**Description**: Implement `aur plan create <goal>` command

**Acceptance Criteria**:
- [ ] Command: `aur plan create "goal string"`
- [ ] Validates goal (non-empty, <500 chars)
- [ ] Generates plan ID using `generate_plan_id()`
- [ ] Creates plan directory: `~/.aurora/plans/active/NNNN-slug/`
- [ ] Generates 4 files (see FR-4.x for details):
  - [ ] `plan.md`
  - [ ] `prd.md`
  - [ ] `tasks.md`
  - [ ] `agents.json`
- [ ] Updates manifest with new plan
- [ ] Returns `PlanResult` with plan ID and file paths
- [ ] Execution time: <5s (aspirational)
- [ ] Error handling:
  - [ ] Empty goal → `INVALID_GOAL` error
  - [ ] Not initialized → `PLANNING_NOT_INITIALIZED` error

**Verification**:
```bash
# Create plan
aur plan create "Implement OAuth2 authentication"

# Verify output
ls ~/.aurora/plans/active/0001-implement-oauth2-authentication/
# Should show: plan.md prd.md tasks.md agents.json

# Verify manifest updated
cat ~/.aurora/plans/manifest.json | jq '.next_id'
# Should show: 2
```

**Dependencies**: Task 3.3, Task 3.4 (file generation in parallel)

---

### Task 3.5: Implement List Command ◆

**User Story**: As a user, I want to run `aur plan list` so I see my active plans

**Description**: Implement `aur plan list` command

**Acceptance Criteria**:
- [ ] Command: `aur plan list [options]`
- [ ] Default: Shows active plans only
- [ ] Flag `--archived`: Shows archived plans only
- [ ] Flag `--all`: Shows both active and archived
- [ ] Output format: Table with columns:
  - [ ] ID (e.g., `0001`)
  - [ ] Slug (e.g., `implement-oauth2-auth`)
  - [ ] Tasks (e.g., `12/15`)
  - [ ] Progress (e.g., `80%`)
  - [ ] Last Modified (e.g., `2h ago`)
- [ ] Sorting: Most recently modified first
- [ ] Returns `ListResult` with plan summaries
- [ ] Execution time: <500ms (aspirational)

**Verification**:
```bash
# List active plans
aur plan list

# List archived plans
aur plan list --archived

# List all
aur plan list --all
```

**Dependencies**: Task 3.2 (manifest reading)

---

### Task 3.6: Implement View Command ◆

**User Story**: As a user, I want to run `aur plan view <id>` so I see plan details

**Description**: Implement `aur plan view <plan-id>` command

**Acceptance Criteria**:
- [ ] Command: `aur plan view <plan-id>`
- [ ] Accepts plan ID (NNNN or full slug)
- [ ] Searches active plans by default
- [ ] Flag `--archived`: Searches archived plans
- [ ] Output includes:
  - [ ] Goal statement
  - [ ] Plan status (active/archived)
  - [ ] Overall progress
  - [ ] Subgoals list with task counts
  - [ ] Agent assignments
  - [ ] Timestamps
- [ ] Dashboard-style display (similar to OpenSpec `show` command)
- [ ] Execution time: <500ms

**Verification**:
```bash
# View by ID
aur plan view 0001

# View by slug (partial match)
aur plan view oauth

# View archived
aur plan view 0001 --archived
```

**Dependencies**: Task 3.2, Task 4.5 (plan generation)

---

### Task 3.7: Implement Archive Command ◆

**User Story**: As a user, I want to run `aur plan archive <id>` so I can clean up completed plans

**Description**: Implement `aur plan archive <plan-id>` command

**Acceptance Criteria**:
- [ ] Command: `aur plan archive <plan-id>`
- [ ] Accepts plan ID (NNNN or full slug)
- [ ] Verifies plan exists in active directory
- [ ] Generates archive path: `~/.aurora/plans/archive/YYYY-MM-DD-NNNN-slug/`
- [ ] Moves directory atomically (rollback on failure)
- [ ] Updates `agents.json`:
  - [ ] Sets `status: "archived"`
  - [ ] Adds `archived_at: "ISO8601 timestamp"`
- [ ] Updates manifest:
  - [ ] Removes from `active_plans`
  - [ ] Adds to `archived_plans`
- [ ] Returns `ArchiveResult` with archive path
- [ ] Execution time: <1s

**Verification**:
```bash
# Archive plan
aur plan archive 0001

# Verify move
ls ~/.aurora/plans/active/0001-* 2>/dev/null || echo "Moved successfully"

# Verify archive exists
ls ~/.aurora/plans/archive/2026-01-03-0001-*/
```

**Dependencies**: Task 3.2 (manifest operations)

---

### Task 3.8: Integrate Commands into Aurora CLI ◆

**User Story**: As a developer, I need CLI integration so `aur plan` is available at top level

**Description**: Wire up planning commands to main Aurora CLI

**Acceptance Criteria**:
- [ ] Create command group: `aur plan`
- [ ] Register all 5 subcommands:
  - [ ] `init`
  - [ ] `create`
  - [ ] `list`
  - [ ] `view`
  - [ ] `archive`
- [ ] Help messages display correctly
- [ ] `aur plan --help` shows all commands
- [ ] `aur plan <cmd> --help` shows command details

**Verification**:
```bash
# Check command group exists
aur plan --help | head -1

# Verify all subcommands listed
aur plan --help | grep -E "init|create|list|view|archive"
```

**Dependencies**: Task 3.3 through 3.7

**Blocking**: All command implementations must be complete before this

---

## Phase 1D: Configuration (Days 4-5)

### Task 4.1: Copy Configurator Module ✓

**User Story**: As a developer, I need the config module integrated so tool configurations can be generated

**Description**: Copy OpenSpec configurator module to Aurora

**Acceptance Criteria**:
- [ ] Files copied to `packages/planning/src/aurora_planning/configurators/`:
  - [ ] `__init__.py`
  - [ ] `base.py`
  - [ ] `claude_code.py`
  - [ ] `opencode.py`
  - [ ] `ampcode.py`
  - [ ] `droid.py`
- [ ] Total code: ~100 lines (from OpenSpec)
- [ ] No modifications to config generation logic
- [ ] All imports updated: `openspec` → `aurora.planning`

**Verification**:
```python
from aurora.planning.configurators import (
    generate_claude_config,
    generate_opencode_config,
    generate_ampcode_config,
    generate_droid_config
)
print("All configurators imported successfully")
```

**Dependencies**: Task 1.4 (import updates done)

---

### Task 4.2: Implement Claude Code Configuration ◆

**User Story**: As a Claude Code user, I want slash commands configured so I can use Aurora planning

**Description**: Generate slash command config for Claude Code during init

**Acceptance Criteria**:
- [ ] Config path: `~/.config/Claude/claude_desktop_config.json` (Linux)
- [ ] Config format: JSON with `mcpServers.aurora` section (MCP protocol)
- [ ] Commands defined:
  - [ ] `/aur:plan <goal>` → `aur plan create "<goal>"`
  - [ ] `/aur:list [--archived]` → `aur plan list [flags]`
  - [ ] `/aur:view <plan-id>` → `aur plan view <plan-id>`
  - [ ] `/aur:archive <plan-id>` → `aur plan archive <plan-id>`
- [ ] Each command includes description and argument schema
- [ ] Merges with existing config (preserves other MCP servers)
- [ ] Creates backup: `claude_desktop_config.json.bak`

**Verification**:
```bash
# Config exists and includes Aurora
cat ~/.config/Claude/claude_desktop_config.json | jq '.mcpServers.aurora' | head -10

# Backup created
ls -la ~/.config/Claude/claude_desktop_config.json.bak

# Command count
cat ~/.config/Claude/claude_desktop_config.json | jq '.mcpServers.aurora.commands | length'
# Should show: 4
```

**Dependencies**: Task 4.1, Task 3.3 (init command ready)

---

### Task 4.3: Implement OpenCode Configuration ◆

**User Story**: As an OpenCode user, I want the same slash commands configured

**Description**: Generate slash command config for OpenCode

**Acceptance Criteria**:
- [ ] Research OpenCode config location (likely `~/.opencode/config.json`)
- [ ] Config format follows OpenCode schema (from OpenSpec configurator)
- [ ] Same 4 slash commands as Claude Code
- [ ] Config generated during `aur plan init`
- [ ] Validation against OpenCode schema (if available)

**Verification**:
```bash
# Research first
ls ~/.opencode/ 2>/dev/null || echo "Research step needed"

# Config generated
cat <opencode-config-path> | jq '.commands.aurora' 2>/dev/null || echo "Configuration method determined"
```

**Dependencies**: Task 4.1, Task 4.2 (to establish pattern)

**Research Task**: Determine exact config path and schema for OpenCode before implementation

---

### Task 4.4: Implement AmpCode Configuration ◆

**User Story**: As an AmpCode user, I want Aurora planning configured

**Description**: Generate slash command config for AmpCode

**Acceptance Criteria**:
- [ ] Research AmpCode config location (likely `~/.ampcode/config.json`)
- [ ] Config format follows AmpCode schema
- [ ] Same 4 slash commands
- [ ] Config generated during `aur plan init`

**Verification**:
```bash
# Research
ls ~/.ampcode/ 2>/dev/null || echo "Research step needed"
```

**Dependencies**: Task 4.1, Task 4.2

**Research Task**: Determine exact config path and schema for AmpCode

---

### Task 4.5: Implement Droid Configuration ◆

**User Story**: As a Droid user, I want Aurora planning configured

**Description**: Generate slash command config for Droid

**Acceptance Criteria**:
- [ ] Research Droid config location
- [ ] Config format follows Droid schema
- [ ] Same 4 slash commands
- [ ] Config generated during `aur plan init`

**Verification**:
```bash
# Research
echo "Determine Droid config path"
```

**Dependencies**: Task 4.1, Task 4.2

**Research Task**: Determine exact config path and schema for Droid

---

### Task 4.6: Integrate Config Generation into Init ◆

**User Story**: As a user, I want configs generated automatically when I run init

**Description**: Call all configurators during `aur plan init`

**Acceptance Criteria**:
- [ ] `aur plan init` calls config generators for all 4 tools
- [ ] Failures in config generation don't block planning init
- [ ] Warnings returned if config generation fails (e.g., unknown tool path)
- [ ] Success message lists configured tools
- [ ] User can re-run `aur plan init` to update configs

**Verification**:
```bash
aur plan init
# Should output: "Planning initialized. Configured: Claude Code, OpenCode, AmpCode, Droid"

# Or with warnings:
# Should output: "Planning initialized. Configured: Claude Code (OpenCode path not found)"
```

**Dependencies**: Task 4.2, 4.3, 4.4, 4.5

---

### Task 4.7: Configuration Validation and Testing ◆

**User Story**: As a QA engineer, I need to verify configurations work end-to-end

**Description**: Validate all tool configurations with tests

**Acceptance Criteria**:
- [ ] Unit tests validate JSON schema for each tool
- [ ] Tests verify:
  - [ ] Config files are valid JSON
  - [ ] Required fields present
  - [ ] Command definitions complete
  - [ ] Merge with existing configs works
- [ ] Integration tests verify:
  - [ ] `aur plan init` generates valid configs
  - [ ] Backup creation works
  - [ ] Config merging preserves existing servers
- [ ] Manual testing checklist (non-blocking for Phase 1):
  - [ ] Test `/aur:plan "test"` in Claude Code (primary)
  - [ ] Verify output streams to chat
  - [ ] Test other tools (research-based, may defer to Phase 1.5)

**Verification**:
```bash
# Run validation tests
pytest tests/integration/planning/test_configurators.py -v

# Should show: All configuration tests passing
```

**Dependencies**: Task 4.6

**Manual**: Tool-specific testing may be deferred if tool paths unknown

---

## Phase 1E: File Generation (Days 4-5)

### Task 5.1: Implement File Generation Pipeline ✓

**User Story**: As a developer, I need the file generation pipeline so plans can be created

**Description**: Implement core file generation functions (schemas, templates, validators)

**Acceptance Criteria**:
- [ ] Pydantic models created:
  - [ ] `AgentMetadata` with all required fields
  - [ ] `Subgoal` model for decomposition
  - [ ] Validators for plan ID format, timestamps, uniqueness
- [ ] Templates created (Jinja2):
  - [ ] `plan.md.j2`
  - [ ] `prd.md.j2`
  - [ ] `tasks.md.j2`
- [ ] Generator function: `generate_plan_files(goal, plan_id, output_dir) -> PlanResult`
  - [ ] Generates subgoals (rule-based, ~5-7 per plan)
  - [ ] Renders all templates with context
  - [ ] Validates each file before writing
  - [ ] Handles partial success (3/4 files ok)
  - [ ] Critical failure recovery (agents.json → rollback all)

**Verification**:
```python
from aurora.planning.generator import generate_plan_files

result = generate_plan_files(
    goal="Implement OAuth2 authentication",
    plan_id="0001-implement-oauth2-authentication",
    output_dir=Path("~/.aurora/plans/active/0001-implement-oauth2-authentication")
)

assert result.success is True
assert result.plan_id == "0001-implement-oauth2-authentication"
assert result.files_created == ["plan.md", "prd.md", "tasks.md", "agents.json"]
```

**Dependencies**: Task 3.1 (plan ID generation available)

---

### Task 5.2: Validate File Generation Output ◆

**User Story**: As a QA engineer, I need to ensure generated files are valid

**Description**: Validate all generated files against schemas and formats

**Acceptance Criteria**:
- [ ] `plan.md` validation:
  - [ ] Valid Markdown syntax
  - [ ] Contains required sections: Goal, Subgoals, etc.
  - [ ] All variables rendered (no `{{ }}` remaining)
- [ ] `prd.md` validation:
  - [ ] Valid Markdown syntax
  - [ ] Contains all required sections
  - [ ] OpenSpec format compliance
- [ ] `tasks.md` validation:
  - [ ] Valid GFM checklist syntax
  - [ ] All tasks properly formatted
  - [ ] Task IDs present and unique
- [ ] `agents.json` validation:
  - [ ] Valid JSON syntax
  - [ ] Conforms to `AgentMetadata` Pydantic schema
  - [ ] All required fields present
  - [ ] Timestamps are ISO 8601

**Verification**:
```bash
# Validate JSON schema
python -c "
from aurora.planning.schemas import AgentMetadata
import json

with open('~/.aurora/plans/active/0001-*/agents.json') as f:
    data = json.load(f)
    metadata = AgentMetadata(**data)
    print('Valid schema')
"

# Validate Markdown structure
python -c "
import re
with open('~/.aurora/plans/active/0001-*/plan.md') as f:
    content = f.read()
    assert '# Goal' in content
    assert '## Subgoals' in content
    assert not '{{' in content  # No unrendered variables
    print('Valid structure')
"
```

**Dependencies**: Task 5.1

---

## Phase 1F: Documentation (Day 5)

### Task 6.1: Write README ✓

**User Story**: As a new user, I need documentation so I can get started quickly

**Description**: Create comprehensive README for planning system

**Acceptance Criteria**:
- [ ] File: `packages/planning/README.md`
- [ ] Sections:
  - [ ] Quick start (under 5 minutes to first plan)
  - [ ] Installation instructions
  - [ ] Basic usage examples
  - [ ] File structure explanation
  - [ ] Troubleshooting guide
  - [ ] Key concepts (plan IDs, subgoals, etc.)
- [ ] Includes runnable examples:
  - [ ] `aur plan init`
  - [ ] `aur plan create "example goal"`
  - [ ] `aur plan list`
  - [ ] `aur plan view 0001`
  - [ ] `aur plan archive 0001`

**Verification**:
```bash
# Check file exists
test -f packages/planning/README.md && echo "OK"

# Verify sections present
grep -q "Quick start" packages/planning/README.md && echo "OK"
grep -q "Installation" packages/planning/README.md && echo "OK"
```

**Dependencies**: None (can start in parallel with other tasks)

---

### Task 6.2: Generate API Reference ✓

**User Story**: As a developer, I need API documentation so I can integrate planning into my code

**Description**: Auto-generate API reference from docstrings

**Acceptance Criteria**:
- [ ] File: `docs/planning/API_REFERENCE.md`
- [ ] Coverage:
  - [ ] All public functions documented
  - [ ] All Pydantic models documented
  - [ ] All command-line commands documented
- [ ] Format:
  - [ ] Function signatures with type hints
  - [ ] Docstrings in clear format
  - [ ] Examples for key functions
  - [ ] Error codes documented

**Verification**:
```bash
# Generate from docstrings
pdoc aurora.planning > docs/planning/API_REFERENCE.md

# Verify key sections
grep -q "def generate_plan_id" docs/planning/API_REFERENCE.md && echo "OK"
grep -q "class AgentMetadata" docs/planning/API_REFERENCE.md && echo "OK"
```

**Dependencies**: All code implementation complete

---

### Task 6.3: Write User Guide ✓

**User Story**: As a user, I need workflow documentation so I understand how to use planning

**Description**: Create comprehensive user guide covering all workflows

**Acceptance Criteria**:
- [ ] File: `docs/planning/USER_GUIDE.md`
- [ ] Sections:
  - [ ] Workflow overview (init → create → view → archive)
  - [ ] Detailed command reference
  - [ ] Plan file descriptions (what's in each file)
  - [ ] Working with tasks (editing tasks.md, tracking progress)
  - [ ] Archiving completed plans
  - [ ] Troubleshooting (error messages, recovery)
- [ ] Common scenarios:
  - [ ] Creating your first plan
  - [ ] Viewing plan progress
  - [ ] Updating tasks as work progresses
  - [ ] Archiving when complete

**Verification**:
```bash
test -f docs/planning/USER_GUIDE.md && echo "OK"
grep -q "workflow" docs/planning/USER_GUIDE.md && echo "OK"
```

**Dependencies**: None (can start in parallel)

---

### Task 6.4: Write Tool Integration Guides ✓

**User Story**: As a Claude Code/OpenCode/etc. user, I need setup instructions so slash commands work

**Description**: Create integration guide for each tool

**Acceptance Criteria**:
- [ ] File: `docs/planning/TOOL_INTEGRATION.md`
- [ ] Sections per tool:
  - [ ] Claude Code
  - [ ] OpenCode
  - [ ] AmpCode
  - [ ] Droid
- [ ] Each section includes:
  - [ ] Automatic setup via `aur plan init`
  - [ ] Manual setup instructions (if needed)
  - [ ] Slash command examples
  - [ ] Troubleshooting for that tool

**Verification**:
```bash
test -f docs/planning/TOOL_INTEGRATION.md && echo "OK"
grep -q "Claude Code" docs/planning/TOOL_INTEGRATION.md && echo "OK"
```

**Dependencies**: Tasks 4.2-4.5 (config generation complete)

---

## Phase 1G: Validation & Quality (Day 5-6)

### Task 7.1: Type Checking ✓

**User Story**: As a developer, I need type safety so code quality is high

**Description**: Run mypy in strict mode on planning package

**Acceptance Criteria**:
- [ ] Command: `mypy packages/planning/src/aurora_planning --strict`
- [ ] Result: 0 errors (strict mode)
- [ ] All type hints present and correct
- [ ] No `Any` types (except where documented)

**Verification**:
```bash
mypy packages/planning/src/aurora_planning --strict
echo $?
# Should output: 0
```

**Dependencies**: All code implementation complete

**Blocking**: 0 type errors required before merging

---

### Task 7.2: Linting ✓

**User Story**: As a developer, I need code style compliance so the codebase is consistent

**Description**: Run linter (ruff) on planning package

**Acceptance Criteria**:
- [ ] Command: `ruff check packages/planning/src/aurora_planning`
- [ ] Result: 0 violations
- [ ] Code style follows Aurora conventions

**Verification**:
```bash
ruff check packages/planning/src/aurora_planning
echo $?
# Should output: 0
```

**Dependencies**: All code implementation complete

---

### Task 7.3: Test Coverage Verification ✓

**User Story**: As a QA engineer, I need coverage metrics so we meet quality gates

**Description**: Verify test coverage meets ≥95% target

**Acceptance Criteria**:
- [ ] Command: `pytest --cov=packages/planning/src/aurora_planning --cov-report=term-missing`
- [ ] Overall coverage: ≥95%
- [ ] Core services: ≥99%
- [ ] Commands: ≥95%
- [ ] No uncovered lines in critical paths

**Verification**:
```bash
pytest tests/unit/planning tests/integration/planning \
  --cov=packages/planning/src/aurora_planning \
  --cov-report=term-missing | tail -20

# Should show: X% coverage (≥95%)
```

**Dependencies**: Task 2.5 (all tests passing)

**Blocking**: <95% coverage blocks merge

---

### Task 7.4: Performance Benchmarking ◆

**User Story**: As a developer, I want to verify performance meets targets

**Description**: Benchmark each command against aspirational targets

**Acceptance Criteria**:
- [ ] Benchmark script: `scripts/benchmark_planning.py`
- [ ] Measurements:
  - [ ] `aur plan init`: <100ms
  - [ ] `aur plan create`: <5s
  - [ ] `aur plan list`: <500ms
  - [ ] `aur plan view`: <500ms
  - [ ] `aur plan archive`: <1s
- [ ] Non-blocking: Log results but don't fail if targets exceeded
- [ ] Identify optimization opportunities for Phase 2

**Verification**:
```bash
python scripts/benchmark_planning.py
# Should output: Benchmark results with timing for each operation
```

**Dependencies**: All command implementations complete

**Non-Blocking**: Aspirational targets; actual measurements logged but don't block merge

---

### Task 7.5: Cross-Platform Testing ◆

**User Story**: As a user on macOS/Windows, I need planning to work on my system

**Description**: Test planning on Linux, macOS, Windows (if applicable)

**Acceptance Criteria**:
- [ ] Directory structure creation verified on each platform
- [ ] Path handling correct for each OS
- [ ] File permissions appropriate
- [ ] Config file paths correct for each OS
- [ ] All tests pass on each platform

**Verification** (per platform):
```bash
# Linux
pytest tests/unit/planning tests/integration/planning

# macOS
pytest tests/unit/planning tests/integration/planning

# Windows (if applicable)
pytest tests/unit/planning tests/integration/planning
```

**Dependencies**: All code implementation complete

**Non-Blocking**: Platform-specific issues logged for Phase 1.5 if not critical

---

### Task 7.6: Documentation Review ✓

**User Story**: As a user, I need accurate documentation so I can use planning effectively

**Description**: Review all documentation for accuracy and completeness

**Acceptance Criteria**:
- [ ] README tested: Quick start can be completed in <5 minutes
- [ ] Examples all runnable and accurate
- [ ] API reference complete and up-to-date
- [ ] User guide covers all workflows
- [ ] Tool integration guides verified for Claude Code (others best-effort)
- [ ] No typos or broken links

**Verification**:
```bash
# Manual review checklist
# - [ ] Read README, follow quick start
# - [ ] Run all example commands successfully
# - [ ] Check API reference for completeness
# - [ ] Review user guide for clarity
```

**Dependencies**: Tasks 6.1-6.4

---

## Task Dependencies Summary

```
Phase 1A (Preparation):
  1.1 → 1.2 → 1.3 → 1.4

Phase 1B (Tests):
  2.1 → 2.2 → 2.3 → 2.4 → 2.5
  (parallel with Phase 1A)

Phase 1C (Commands):
  3.1 (parallel with 1B)
  3.2 → 3.3 → 3.4,3.5,3.6,3.7
  3.4,3.5,3.6,3.7 → 3.8 (all must complete)

Phase 1D (Configuration):
  4.1 → 4.2 → 4.3,4.4,4.5 (research-based)
  4.2,4.3,4.4,4.5 → 4.6 → 4.7

Phase 1E (File Generation):
  5.1 → 5.2

Phase 1F (Documentation):
  6.1,6.2,6.3 (parallel, independent)
  4.7 → 6.4

Phase 1G (Validation):
  All code → 7.1,7.2,7.3
  All code → 7.4 (non-blocking)
  All code → 7.5 (non-blocking)
  6.1-6.4 → 7.6
```

---

## Definition of Done (Completion Criteria)

✓ **All tasks completed** when:

1. **Code Quality**:
   - [ ] All 284 tests passing
   - [ ] ≥95% coverage (overall)
   - [ ] mypy: 0 type errors (strict)
   - [ ] ruff: 0 linting violations

2. **Functionality**:
   - [ ] All 5 commands implemented and working
   - [ ] 4-file workflow generates valid files
   - [ ] All 4 tools have configs generated
   - [ ] Manifest tracking works correctly

3. **Documentation**:
   - [ ] README with working quick start
   - [ ] API reference complete
   - [ ] User guide with all workflows
   - [ ] Tool integration guides for all tools

4. **Integration**:
   - [ ] `aur plan` command group available
   - [ ] Planning package in Aurora namespace
   - [ ] Tests integrated into main test suite
   - [ ] Documentation linked from main docs

✓ **Ready for Phase 2** when all above complete and approved

---

## Estimated Timeline

- **Phase 1A**: 2 days (8 hours)
- **Phase 1B**: 1.5 days (6 hours)
- **Phase 1C**: 1.5 days (6 hours)
- **Phase 1D**: 1 day (4 hours)
- **Phase 1E**: 1 day (4 hours)
- **Phase 1F**: 1 day (4 hours)
- **Phase 1G**: 1 day (4 hours)

**Total**: ~6 days / 40 hours (1 developer, full-time)

**With Part-Time**: ~10-12 days (1 developer, part-time)
