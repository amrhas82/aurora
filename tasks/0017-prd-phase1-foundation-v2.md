# PRD: Aurora Planning System - Phase 1 Foundation (v2)

**Version**: 2.0 (Updated with Aurora directory structure)
**Date**: 2026-01-02
**Status**: Planning
**Sprint**: Phase 1 of 3
**Parent Spec**: `/tasks/0017-planning-specs-v2.md`

---

## CRITICAL UPDATES (v2)

### Directory Structure: Aurora-Native (NOT OpenSpec)

**Primary Location**: `.aurora/plans/` (NOT `openspec/changes/`)

```
.aurora/
├── plans/
│   ├── active/
│   │   └── 0001-oauth-auth/
│   │       ├── plan.md                 # High-level decomposition
│   │       ├── prd.md                  # Detailed requirements
│   │       ├── tasks.md                # Implementation checklist
│   │       ├── agents.json             # Machine metadata
│   │       └── specs/                  # Capability specifications
│   │           ├── oauth-auth-planning.md
│   │           ├── oauth-auth-commands.md
│   │           ├── oauth-auth-validation.md
│   │           └── oauth-auth-schemas.md
│   └── archive/
│       └── 2026-01-15-0001-oauth-auth/  # Same structure as active
└── config/
    └── tools/                          # Tool configurations (Phase 2)
```

**Naming Pattern**: `<plan-name>-<capability>.md`
- Example: `oauth-auth-planning.md`, `oauth-auth-schema.schema.md`

### Command Mapping (Aurora ↔ OpenSpec)

| Aurora Command | OpenSpec Equivalent | Phase | Status |
|----------------|---------------------|-------|--------|
| `aur init` | `openspec init` | **Phase 1** | ✅ In scope |
| `aur plan create <goal>` | `openspec change create` | **Phase 1** | ✅ In scope |
| `aur plan list [--archived]` | `openspec list` | **Phase 1** | ✅ In scope |
| `aur plan view <id>` | `openspec view` | **Phase 1** | ✅ In scope |
| `aur plan archive <id>` | `openspec archive` | **Phase 1** | ✅ In scope |
| `aur plan implement <id>` | `openspec apply` | Phase 3 | Deferred |

**Phase 1 Commands** (5 total):
- `aur init` - Full Aurora initialization (directory structure + tool configs + project setup)
- `aur plan create` - Generate new plan with 8 files
- `aur plan list` - List active/archived plans
- `aur plan view` - Display plan dashboard
- `aur plan archive` - Archive completed plan

**Phase 3 Adds**:
- `aur plan implement` - Execute plan with agent orchestration

**Key Design Decision**: Single `aur init` command handles ALL initialization
- No separate `aur plan init` (confusing, unnecessary)
- Adapted from OpenSpec configurator module (~100 lines, already ported)
- 3-step interactive flow: Welcome → Tool selection → Config generation
- Creates `.aurora/` structure + tool configs + project context in one command

### File Generation Pattern

**When running**: `aur plan create "Implement OAuth2 authentication"`

**Generates** (Plan ID: `0001-oauth-auth`):
```
.aurora/plans/active/0001-oauth-auth/
├── plan.md                               # 4 core files
├── prd.md
├── tasks.md
├── agents.json
└── specs/                                # Capability specifications
    ├── planning/
    │   └── oauth-auth-planning.md        # Planning capability spec
    ├── commands/
    │   └── oauth-auth-schema.schema.md   # Command schemas
    ├── validation/
    │   └── oauth-auth-validation.md      # Validation rules
    └── schemas/
        └── oauth-auth-schemas.md         # Data schemas
```

**Total**: 8 files per plan (4 base + 4 specs)

---

## Executive Summary

### Problem Statement

Aurora currently lacks integrated planning capabilities, forcing users to:
- Switch between CLI and external planning tools
- Manually decompose complex goals into actionable tasks
- Track implementation progress outside the Aurora ecosystem
- Recreate tool configurations for each AI coding assistant

The OpenSpec refactoring (Phase 0.5) delivered 284 passing tests with proven planning infrastructure, but it exists in isolation at `/tmp/openspec-source/` and is not integrated into Aurora.

### Solution Overview

Phase 1 integrates the refactored OpenSpec codebase as Aurora's native planning package (`aurora.planning`), providing:

1. **Native Planning Commands**: `aur plan create/list/view/archive` generating structured plans
2. **Eight-File Workflow**: Automated generation of 4 base files + 4 capability specs per plan
3. **Aurora Directory Structure**: `.aurora/plans/active/` and `.aurora/plans/archive/`
4. **Proven Foundation**: 284 migrated tests ensuring reliability from day one

**Phase 1 Scope**: Foundation infrastructure with template-based planning
**Phase 2 Vision**: Add `aur init` (tool config) + SOAR decomposition + memory retrieval + agent discovery
**Phase 3 Vision**: Add `aur plan implement` (execution orchestration with agent delegation)

### Business Value

- **Time Savings**: Automated plan generation reduces manual planning from hours to seconds
- **Quality Assurance**: 284 tests ensure robust planning infrastructure
- **Aurora Identity**: Native `.aurora/` directory structure (not OpenSpec compatibility layer)
- **Extensibility**: Proven foundation ready for Phase 2/3 intelligence layers

### Success Metrics

1. **284 OpenSpec tests passing** in new `aurora.planning` package location
2. **`aur init` working**: 3-step interactive flow, creates `.aurora/` structure, configures tools
3. **All 4 planning commands functional**: create, list, view, archive
4. **Tool configurators working**: Claude Code, OpenCode, AmpCode, Droid
5. **Eight-file structure generated** with valid schemas and content (4 base + 4 specs)
6. **Performance targets met**: <5s init, <5s plan creation, <500ms list operations

---

## 1. Introduction/Overview

### Background

**Completed Work**:
- **PRD 0016**: Agent discovery with manifest system (91 tests, 85% coverage)
- **Phase 0.5**: OpenSpec refactoring with 284 passing tests
  - Location: `/tmp/openspec-source/aurora/`
  - Status: Complete, awaiting integration
  - Features: Schemas, validation, parsers, commands, templates, config generation

**Current State**:
Basic planning implementation exists (`tasks/tasks-0017-PH1-aurora-planning-system.md` shows 147 tests) but lacks:
- Full OpenSpec feature set (only subset implemented)
- Aurora-native directory structure (`.aurora/plans/`)
- Capability specification generation
- Archive management and lifecycle tracking

### High-Level Goal

**Phase 1 Goal**: Establish planning foundation by migrating proven OpenSpec infrastructure into Aurora as a first-class planning package with Aurora-native directory structure (`.aurora/plans/`), enabling users to create, manage, and archive structured plans through native `aur plan` commands.

**Key Principle**: **Test-then-enhance** approach
- Phase 1: Integrate OpenSpec foundation with Aurora branding (proven with 284 tests)
- Phase 2: Layer Aurora intelligence (SOAR, memory, agent discovery) + `aur init` tool config
- Phase 3: Add `aur plan implement` execution orchestration

### Scope Boundaries

**In Scope (Phase 1)**:
- Full OpenSpec package migration to `aurora.planning`
- All 284 tests migrated and passing
- **`aur init` command**: Full initialization (directory + tools + config)
  - Adapted from OpenSpec CLI configurator module (~100 lines)
  - 3-step interactive flow (Welcome → Tool selection → Config generation)
  - Creates `.aurora/` structure + tool configs + project.md
- Planning commands: `aur plan create/list/view/archive` (4 commands)
- **Eight-file workflow**: 4 base files + 4 capability specs per plan
- **Aurora directory structure**: `.aurora/plans/active/` and `/archive/`
- Rule-based template generation (from OpenSpec configs)
- Documentation: README, API reference, user guide

**Out of Scope (Deferred to Phase 2/3)**:
- SOAR-powered goal decomposition (Phase 2)
- Memory-aware file path resolution (Phase 2)
- Agent recommendation with manifest integration (Phase 2)
- `aur plan implement` execution and orchestration (Phase 3)
- Checkpoint/resume workflows (Phase 3)

---

## 2. Goals

### Goal 1: OpenSpec Package Migration
**Migrate** the 284-test OpenSpec codebase from `/tmp/openspec-source/aurora/` to `packages/planning/src/aurora_planning/` with **Aurora-native directory structure**.

**Success Criteria**:
- ✅ All 284 tests passing in new location
- ✅ Package structure: `aurora.planning` with submodules
- ✅ Directory paths use `.aurora/plans/` (not `openspec/changes/`)
- ✅ Import paths: `from aurora.planning import *`

### Goal 2: Full Initialization Command
**Implement** `aur init` command for complete Aurora project setup.

**Success Criteria**:
- ✅ 3-step interactive flow (adapted from OpenSpec configurator)
- ✅ Creates `.aurora/` directory structure (plans/active/, plans/archive/, config/tools/)
- ✅ Multi-tool configuration (Claude Code, OpenCode, AmpCode, Droid)
- ✅ Generates project.md for context
- ✅ Creates root AGENTS.md stub with OpenSpec-style managed block
- ✅ Idempotent (safe to run multiple times, extends existing setup)

### Goal 3: Native Planning Commands
**Implement** 4 CLI commands that generate and manage plans.

**Success Criteria**:
- ✅ `aur plan create <goal>` generates 8-file structure
- ✅ `aur plan list` shows active/archived plans
- ✅ `aur plan view <id>` displays plan dashboard
- ✅ `aur plan archive <id>` moves to timestamped archive

### Goal 4: Eight-File Workflow
**Generate** comprehensive plan structure with 4 base files + 4 capability specs.

**Success Criteria**:
- ✅ Base files: `plan.md`, `prd.md`, `tasks.md`, `agents.json`
- ✅ Capability specs: `specs/planning/`, `specs/commands/`, `specs/validation/`, `specs/schemas/`
- ✅ Naming: `<plan-name>-<capability>.md` format
- ✅ Validation: JSON schemas for all files

### Goal 5: Aurora Directory Structure
**Establish** `.aurora/` as primary Aurora location (NOT `openspec/`).

**Success Criteria**:
- ✅ Created by `aur init`: `.aurora/plans/`, `.aurora/config/tools/`
- ✅ Active plans: `.aurora/plans/active/<plan-id>/`
- ✅ Archive: `.aurora/plans/archive/YYYY-MM-DD-<plan-id>/`
- ✅ Tool configs: `.aurora/config/tools/` (generated by init)
- ✅ No `openspec/` directory created
- ✅ Plan ID format: `NNNN-slug` (e.g., `0001-oauth-auth`)

### Goal 6: Comprehensive Documentation
**Create** user-facing documentation for planning workflows.

**Success Criteria**:
- ✅ README with quick start and examples
- ✅ API reference (all public functions documented)
- ✅ User guide (planning workflows, best practices)
- ✅ Cheat sheet (command examples)

---

## 3. User Stories

### Planning Workflow Stories

**US-1.1: Create Structured Plan**
```
AS A developer
I WANT to run `aur plan create "Implement OAuth2"`
SO THAT I get a structured plan with 8 files in `.aurora/plans/active/0001-oauth2/`
```

**Acceptance Criteria**:
- Command executes in <5s
- Generates plan ID `0001-oauth2` (auto-increment)
- Creates `.aurora/plans/active/0001-oauth2/` directory
- 4 base files present: plan/prd/tasks/agents.json
- 4 spec files present in `specs/` subdirectory
- All files validate against schemas
- Success message shows plan ID and location

**US-1.2: List Active Plans**
```
AS A developer
I WANT to run `aur plan list`
SO THAT I see all active plans with progress indicators
```

**Acceptance Criteria**:
- Shows plan ID, title, task progress (X/Y tasks)
- Lists plans from `.aurora/plans/active/`
- Sorted by most recent first
- Executes in <500ms

**US-1.3: View Plan Dashboard**
```
AS A developer
I WANT to run `aur plan view 0001`
SO THAT I see comprehensive plan details with subgoals and agents
```

**Acceptance Criteria**:
- Shows: goal, status, task counts, subgoals, agent assignments
- Reads from `.aurora/plans/active/0001-*/`
- Formatted with Rich library (colors, panels)

**US-1.4: Archive Completed Plan**
```
AS A developer
I WANT to run `aur plan archive 0001`
SO THAT completed plan moves to `.aurora/plans/archive/2026-01-15-0001-oauth2/`
```

**Acceptance Criteria**:
- Moves entire directory atomically
- Adds timestamp: `YYYY-MM-DD-<plan-id>`
- Updates agents.json with archive metadata
- Confirms before archiving incomplete plans

**US-1.5: Validate Plan Structure**
```
AS A developer
I WANT plans to be validated automatically
SO THAT I catch errors early (missing files, invalid JSON)
```

**Acceptance Criteria**:
- Pydantic validates agents.json on creation
- Schema validation for all 4 base files
- Warning messages for missing optional fields
- Errors block plan creation

### Multi-Tool Integration Stories

**US-2.1: Configure Slash Commands (Phase 2 - Deferred)**
```
AS A developer
I WANT to run `aur init`
SO THAT I select tools (Claude Code, OpenCode, etc.) and configure slash commands
```

**Status**: Deferred to Phase 2

---

## 4. Functional Requirements

### FR-1: OpenSpec Package Migration

#### FR-1.1: Package Structure Creation

**Description**: Create `aurora.planning` package with Aurora-native directory structure.

**Acceptance Criteria**:
- Package location: `packages/planning/src/aurora_planning/`
- Submodules: `commands/`, `parsers/`, `schemas/`, `templates/`, `validators/`, `config.py`
- `__init__.py` exports: `PlanCommand`, `ListCommand`, `ViewCommand`, `ArchiveCommand`
- All imports use: `from aurora.planning import *`
- Default directory: `.aurora/plans/` (configurable in config)

**Validation**:
```bash
python -c "from aurora.planning import PlanCommand; print(PlanCommand.__name__)"
# Output: PlanCommand
```

#### FR-1.2: Test Migration

**Description**: Migrate all 284 OpenSpec tests to Aurora test structure.

**Acceptance Criteria**:
- Tests location: `tests/unit/planning/`, `tests/integration/planning/`
- Import updates: `from openspec` → `from aurora.planning`
- ≥280 tests passing (allow 4 for breaking changes)
- Test coverage ≥95% (maintain OpenSpec level)
- All tests use `.aurora/plans/` paths (not `openspec/`)

**Validation**:
```bash
pytest tests/unit/planning/ tests/integration/planning/ -v
# Expected: ≥280 passed
```

#### FR-1.3: Directory Path Configuration

**Description**: Configure default planning directory to `.aurora/plans/`.

**Acceptance Criteria**:
- Config key: `planning.base_dir` defaults to `~/.aurora/plans`
- Active subdirectory: `{base_dir}/active/`
- Archive subdirectory: `{base_dir}/archive/`
- User can override via `AURORA_PLANS_DIR` env var
- Config validates directory is writable on startup

**Validation**:
```bash
aur config get planning.base_dir
# Output: /home/user/.aurora/plans
```

#### FR-1.4: Plan ID Auto-Increment

**Description**: Implement auto-incrementing plan IDs with NNNN-slug format.

**Acceptance Criteria**:
- Format: `NNNN-slug` (e.g., `0001-oauth-auth`)
- NNNN: Zero-padded 4-digit number
- Slug: Kebab-case from goal (max 30 chars)
- Scan `.aurora/plans/active/` and `/archive/` for highest NNNN
- Increment by 1 for new plan
- Handle collisions (rare: retry with next number)

**Validation**:
```bash
aur plan create "Test Goal"
# Creates: .aurora/plans/active/0001-test-goal/
aur plan create "Another Goal"
# Creates: .aurora/plans/active/0002-another-goal/
```

#### FR-1.5: Archive Timestamp Format

**Description**: Archive plans with `YYYY-MM-DD-<plan-id>` directory format.

**Acceptance Criteria**:
- Format: `YYYY-MM-DD-NNNN-slug` (e.g., `2026-01-15-0001-oauth-auth`)
- Use current date at archive time (not creation date)
- Preserve original plan ID in archived directory name
- Update agents.json with `archived_at` timestamp
- Atomic move operation (all-or-nothing)

**Validation**:
```bash
aur plan archive 0001
# Creates: .aurora/plans/archive/2026-01-15-0001-oauth-auth/
# agents.json contains: "archived_at": "2026-01-15T10:30:00Z"
```

---

### FR-2: Initialization Command

#### FR-2.0: `aur init` Command

**Description**: Full Aurora project initialization with directory structure, tool configuration, and project setup.

**Source**: Adapted from OpenSpec CLI configurator module (~100 lines, already ported in Phase 0.5)

**Acceptance Criteria**:
- Syntax: `aur init [path]` (default: current directory)
- **3-Step Interactive Flow** (OpenSpec-style):

  **Step 1: Welcome**
  - Display welcome message
  - Detect existing `.aurora/` setup
  - Show "extending" vs "initializing" message

  **Step 2: Tool Selection**
  - Multi-select prompt with arrow keys + spacebar
  - Tools: Claude Code, OpenCode, AmpCode, Droid
  - Show (◉) for selected, (○) for unselected
  - Show "(already configured)" for existing tools

  **Step 3: Review & Confirm**
  - Show selected tools
  - Press Enter to confirm or Backspace to adjust
  - Generate all configs and structure

- **Creates Directory Structure**:
  - `.aurora/plans/active/`
  - `.aurora/plans/archive/`
  - `.aurora/config/tools/`

- **Generates Files**:
  - Tool configs in `.aurora/config/tools/` (one per selected tool)
  - `project.md` with template for user to fill
  - Root `AGENTS.md` stub with OpenSpec-style managed block

- **Tool Configuration Files**:
  - Claude Code: `~/.config/Claude/claude_desktop_config.json` (Linux)
  - OpenCode: TBD path (research in implementation)
  - AmpCode: TBD path (research in implementation)
  - Droid: TBD path (research in implementation)

- **Idempotent**: Safe to run multiple times
  - Extends existing setup (adds new tools)
  - Preserves existing configs
  - Updates managed block in root AGENTS.md

- **Success Message**:
  - Shows configured tools
  - Shows next steps (restart IDE, fill project.md, create first plan)
  - Performance: <5s execution time

**Validation**:
```bash
aur init
# Output:
# Welcome to Aurora!
#
# Step 1/3: Extend your Aurora tooling
# We will help you configure AI coding tools.
#
# Step 2/3: Which tools would you like to configure?
# Use ↑/↓ to move · Space to toggle · Enter to confirm
#
#   ◉ Claude Code
#   ◉ OpenCode
#   ○ AmpCode
#   ○ Droid
#
# Step 3/3: Review selections
#   ▌ Claude Code
#   ▌ OpenCode
#
# ✓ Aurora initialized successfully!
#
# Tool summary:
#   ▌ Configured: Claude Code, OpenCode
#   ▌ Skipped: AmpCode, Droid
#
# Next steps:
#   1. Restart your IDE to load slash commands
#   2. Fill in project.md: vim .aurora/project.md
#   3. Create first plan: aur plan create "Your goal"

ls -la .aurora/
# Output: plans/ config/ project.md

ls -la .aurora/plans/
# Output: active/ archive/

ls -la .aurora/config/tools/
# Output: claude-code.json opencode.json
```

**Note**: First `aur plan create` auto-runs `aur init` if `.aurora/` doesn't exist.

---

### FR-3: Native Planning Commands

#### FR-6.1: `aur plan create` Command

**Description**: Generate new plan with 8-file structure in `.aurora/plans/active/`.

**Acceptance Criteria**:
- Syntax: `aur plan create <goal>` (goal as quoted string)
- Generates plan ID (auto-increment NNNN-slug)
- Creates directory: `.aurora/plans/active/<plan-id>/`
- Generates 4 base files: `plan.md`, `prd.md`, `tasks.md`, `agents.json`
- Generates 4 spec files: `specs/planning/`, `/commands/`, `/validation/`, `/schemas/`
- Naming: `<plan-name>-<capability>.md` (e.g., `oauth-auth-planning.md`)
- Templates use Jinja2 with goal substitution
- Success message shows plan ID and path
- Performance: <5s execution time

**Validation**:
```bash
aur plan create "Implement OAuth2 authentication"
# Output:
# ✓ Plan created: 0001-oauth-auth
# Location: /home/user/.aurora/plans/active/0001-oauth-auth/
# Files: 8 (4 base + 4 specs)

ls .aurora/plans/active/0001-oauth-auth/
# Output: plan.md prd.md tasks.md agents.json specs/

ls .aurora/plans/active/0001-oauth-auth/specs/
# Output: oauth-auth-planning.md oauth-auth-commands.md oauth-auth-validation.md oauth-auth-schemas.md
```

#### FR-6.2: `aur plan list` Command

**Description**: Display active and archived plans with progress indicators.

**Acceptance Criteria**:
- Syntax: `aur plan list [--archived] [--all]`
- Default: Shows only active plans from `.aurora/plans/active/`
- `--archived`: Shows only archived plans from `.aurora/plans/archive/`
- `--all`: Shows both active and archived
- Display format: `<plan-id>  <title>  <progress>  <last-modified>`
- Progress: `X/Y tasks (Z%)` or `Complete` or `No tasks`
- Sort: Most recent first (by last_modified timestamp)
- Performance: <500ms execution time

**Validation**:
```bash
aur plan list
# Output:
# Active Plans:
#   0002-user-auth        5/12 tasks (42%)    2h ago
#   0001-oauth-setup      12/12 tasks (100%)  1d ago

aur plan list --archived
# Output:
# Archived Plans:
#   2026-01-15-0001-oauth-setup    Completed 3d ago

aur plan list --all
# Output: (both active and archived combined)
```

#### FR-6.3: `aur plan view` Command

**Description**: Display comprehensive plan dashboard with Rich formatting.

**Acceptance Criteria**:
- Syntax: `aur plan view <plan-id>`
- Plan ID: Accepts NNNN or NNNN-slug format
- Loads from `.aurora/plans/active/<plan-id>/` or `/archive/YYYY-MM-DD-<plan-id>/`
- Displays: Goal, status, created/modified dates, task counts, subgoals, agent assignments
- Format: Rich panels with colors, bullets, progress bars
- Shows file locations (plan.md, prd.md, tasks.md, agents.json, specs/)
- Error if plan not found (suggests similar IDs)

**Validation**:
```bash
aur plan view 0001
# Output: (Rich-formatted dashboard)
# ┌─ Plan 0001: OAuth Setup ──────────────────┐
# │ Status: Active                              │
# │ Created: 2026-01-15 10:00                   │
# │ Progress: 12/12 tasks (100%)                │
# │ Files: 8 (4 base + 4 specs)                 │
# │ Location: .aurora/plans/active/0001-oauth/  │
# └─────────────────────────────────────────────┘
```

#### FR-6.4: `aur plan archive` Command

**Description**: Archive completed plan to `.aurora/plans/archive/` with timestamp.

**Acceptance Criteria**:
- Syntax: `aur plan archive <plan-id> [--force]`
- Moves from `.aurora/plans/active/<plan-id>/` to `/archive/YYYY-MM-DD-<plan-id>/`
- Timestamp uses current date (ISO 8601 format)
- Updates agents.json: Add `status: archived`, `archived_at: <timestamp>`
- Atomic operation: All files moved or none (rollback on error)
- Confirmation prompt if plan incomplete (tasks not 100%)
- `--force`: Skip confirmation
- Success message shows archive location

**Validation**:
```bash
aur plan archive 0001
# Output:
# ⚠ Plan 0001 has incomplete tasks (5/12 done). Archive anyway? (y/N)
# > y
# ✓ Plan archived: 2026-01-15-0001-oauth-setup
# Location: /home/user/.aurora/plans/archive/2026-01-15-0001-oauth-setup/

ls .aurora/plans/archive/
# Output: 2026-01-15-0001-oauth-setup/
```

#### FR-6.5: Plan Validation on Load

**Description**: Validate plan structure when loading from disk.

**Acceptance Criteria**:
- Check required files exist: `plan.md`, `prd.md`, `tasks.md`, `agents.json`
- Check optional files: `specs/planning/`, `/commands/`, `/validation/`, `/schemas/`
- Validate agents.json against Pydantic schema
- Validate plan ID format matches directory name
- Warnings for missing optional files (don't block)
- Errors for missing required files (block operations)
- Detailed error messages with file paths

**Validation**:
```bash
# Manually delete agents.json
rm .aurora/plans/active/0001-oauth/agents.json

aur plan view 0001
# Output:
# ✗ Error: Invalid plan structure for 0001-oauth
# Missing required file: agents.json
# Path: /home/user/.aurora/plans/active/0001-oauth/agents.json
# Suggestion: Recreate plan or restore from backup
```

---

### FR-4: Eight-File Workflow

#### FR-6.1: Base File Generation

**Description**: Generate 4 base files with Jinja2 templates.

**Acceptance Criteria**:
- Templates location: `aurora_planning/templates/`
- Files: `plan.md.j2`, `prd.md.j2`, `tasks.md.j2`, `agents.json.j2`
- Template variables: `{{ goal }}`, `{{ plan_id }}`, `{{ created_at }}`, `{{ plan_name }}`
- `plan.md`: High-level decomposition (subgoals, dependencies)
- `prd.md`: Detailed requirements (OpenSpec format, FR-N.M structure)
- `tasks.md`: Implementation checklist (GFM checkboxes)
- `agents.json`: Machine metadata (Pydantic-validated JSON)
- All files UTF-8 encoded, LF line endings

**Validation**:
```bash
aur plan create "Test Goal"
cat .aurora/plans/active/0001-test-goal/plan.md
# Contains: "# Plan: Test Goal"
cat .aurora/plans/active/0001-test-goal/agents.json
# Valid JSON with required fields: plan_id, goal, status, created_at
```

#### FR-6.2: Capability Spec Generation

**Description**: Generate 4 capability specification files in `specs/` subdirectory.

**Acceptance Criteria**:
- Directory: `.aurora/plans/active/<plan-id>/specs/`
- Files directly in specs/: 4 markdown files
- File naming: `<plan-name>-<capability>.md` (e.g., `oauth-auth-planning.md`)
- Templates: `planning.md.j2`, `commands.md.j2`, `validation.md.j2`, `schemas.md.j2`
- Content: Requirements and scenarios for each capability area
- Format: OpenSpec specification format (Given/When/Then scenarios)

**Validation**:
```bash
aur plan create "OAuth Auth"
ls .aurora/plans/active/0001-oauth-auth/specs/
# Output: oauth-auth-planning.md oauth-auth-commands.md oauth-auth-validation.md oauth-auth-schemas.md

# Removed - flat structure now
# Output: oauth-auth-planning.md

cat .aurora/plans/active/0001-oauth-auth/specs/oauth-auth-planning.md
# Contains: "# oauth-auth Planning Capability"
# Contains: "### Requirement:" sections
```

#### FR-6.3: JSON Schema Validation

**Description**: Validate agents.json against JSON Schema.

**Acceptance Criteria**:
- Schema location: `aurora_planning/schemas/agents.schema.json`
- Required fields: `plan_id`, `goal`, `status`, `created_at`, `subgoals`
- Optional fields: `archived_at`, `tags`, `metadata`
- Validation on: Create, update, load operations
- Pydantic model: `AgentsManifest` with field validators
- Error messages show: field name, expected type, received value

**Schema** (see Appendix A for full schema):
```json
{
  "plan_id": "0001-oauth-auth",
  "goal": "Implement OAuth2 authentication",
  "status": "active",
  "created_at": "2026-01-15T10:00:00Z",
  "subgoals": [...]
}
```

**Validation**:
```bash
# agents.json with invalid status
echo '{"plan_id": "0001", "status": "invalid"}' > .aurora/plans/active/0001-test/agents.json

aur plan view 0001
# Output:
# ✗ Validation Error: agents.json
# Field: status
# Error: Invalid value 'invalid'. Must be one of: active, archived
```

#### FR-6.4: Template Variable Substitution

**Description**: Substitute template variables in all 8 files.

**Acceptance Criteria**:
- Variables: `goal`, `plan_id`, `plan_name`, `created_at`, `subgoals`
- `plan_name`: Slug portion of plan ID (e.g., `oauth-auth` from `0001-oauth-auth`)
- `created_at`: ISO 8601 timestamp
- `goal`: User-provided goal string
- Jinja2 filters: `slugify`, `title`, `capitalize`
- All 8 files receive same variable context

**Validation**:
```bash
aur plan create "Implement OAuth2"
grep "Implement OAuth2" .aurora/plans/active/0001-implement-oauth2/plan.md
# Match found

grep "0001-implement-oauth2" .aurora/plans/active/0001-implement-oauth2/agents.json
# Match found

grep "implement-oauth2-planning" .aurora/plans/active/0001-implement-oauth2/specs/planning/*.md
# Match found (file named implement-oauth2-planning.md)
```

#### FR-6.5: File Permission and Ownership

**Description**: Set appropriate permissions on generated files.

**Acceptance Criteria**:
- Directory permissions: `0755` (rwxr-xr-x)
- File permissions: `0644` (rw-r--r--)
- Owner: Current user
- Group: User's primary group
- Preserve umask settings

**Validation**:
```bash
aur plan create "Test"
ls -ld .aurora/plans/active/0001-test/
# Output: drwxr-xr-x ... 0001-test/

ls -l .aurora/plans/active/0001-test/plan.md
# Output: -rw-r--r-- ... plan.md
```

#### FR-6.6: Atomic File Generation

**Description**: Generate all 8 files atomically (all succeed or none).

**Acceptance Criteria**:
- Use temporary directory: `.aurora/plans/.tmp/<plan-id>/`
- Generate all 8 files in temp directory
- Validate all files before moving
- Atomic move: Rename temp dir to final location
- Rollback: Delete temp dir on any error
- User sees consistent state (never partial plan)

**Validation**:
```bash
# Simulate disk full during generation (test scenario)
# Plan directory should NOT exist if generation fails
# No partial files left behind
```

#### FR-6.7: Plan Summary Display

**Description**: Display summary after successful plan creation.

**Acceptance Criteria**:
- Shows: Plan ID, goal, location, file count (8)
- Lists all generated files with sizes
- Shows next steps (edit plan.md, run tasks, archive when done)
- Colorized output with Rich library
- Copy-pasteable plan ID for other commands

**Validation**:
```bash
aur plan create "OAuth Setup"
# Output:
# ✓ Plan created successfully!
#
# Plan ID: 0001-oauth-setup
# Goal: OAuth Setup
# Location: /home/user/.aurora/plans/active/0001-oauth-setup/
#
# Files generated (8):
#   ✓ plan.md (2.1 KB)
#   ✓ prd.md (5.3 KB)
#   ✓ tasks.md (1.8 KB)
#   ✓ agents.json (0.5 KB)
#   ✓ specs/oauth-setup-planning.md (3.2 KB)
#   ✓ specs/oauth-setup-commands.md (1.5 KB)
#   ✓ specs/oauth-setup-validation.md (2.0 KB)
#   ✓ specs/oauth-setup-schemas.md (1.9 KB)
#
# Next steps:
#   1. Review: aur plan view 0001
#   2. Edit plan: vim .aurora/plans/active/0001-oauth-setup/plan.md
#   3. Implement tasks from tasks.md
#   4. Archive when done: aur plan archive 0001
```

---

### FR-5: Configuration System

#### FR-6.1: Planning Configuration Section

**Description**: Add `planning` section to `aurora_cli/config.py`.

**Acceptance Criteria**:
- Config key: `planning.base_dir` (default: `~/.aurora/plans`)
- Config key: `planning.template_dir` (default: `<package>/templates`)
- Config key: `planning.auto_increment` (default: `true`)
- Config key: `planning.archive_on_complete` (default: `false` - manual archive)
- Validation: `base_dir` must be writable
- Tilde expansion: `~/` → `/home/user/`

**Validation**:
```bash
aur config get planning.base_dir
# Output: /home/user/.aurora/plans

aur config set planning.base_dir ~/custom-plans
aur config get planning.base_dir
# Output: /home/user/custom-plans
```

#### FR-6.2: Environment Variable Overrides

**Description**: Support env vars for configuration overrides.

**Acceptance Criteria**:
- `AURORA_PLANS_DIR`: Override `planning.base_dir`
- `AURORA_TEMPLATE_DIR`: Override `planning.template_dir`
- Env vars take precedence over config file
- Validation still applies (writable check)

**Validation**:
```bash
export AURORA_PLANS_DIR=/tmp/my-plans
aur plan create "Test"
# Creates: /tmp/my-plans/active/0001-test/
```

---

### FR-6: Documentation

#### FR-6.1: README with Quick Start

**Description**: Create comprehensive README for `aurora.planning` package.

**Acceptance Criteria**:
- Sections: Overview, Installation, Quick Start, Commands, Examples, Configuration
- Quick start: 5 commands to create first plan
- Examples: Real-world use cases (OAuth, user registration, logging)
- Links to API reference and user guide
- Markdown formatted, renders on GitHub

**Location**: `packages/planning/README.md`

#### FR-6.2: API Reference Documentation

**Description**: Generate API reference from docstrings.

**Acceptance Criteria**:
- Tool: Sphinx or pdoc
- Coverage: All public functions, classes, methods
- Format: HTML with search
- Docstring format: Google style
- Examples in docstrings (with `>>>` code blocks)
- Generated from: `make docs` command

**Location**: `docs/planning/api/`

#### FR-6.3: User Guide

**Description**: Create user-facing planning workflow guide.

**Acceptance Criteria**:
- Sections: Planning Workflow, Best Practices, Troubleshooting, FAQ
- Workflow: Step-by-step guide with screenshots (terminal output)
- Best practices: Plan naming, task organization, archive triggers
- Troubleshooting: Common errors with solutions
- FAQ: 10+ common questions

**Location**: `docs/planning/user-guide.md`

#### FR-6.4: Command Cheat Sheet

**Description**: Create quick reference cheat sheet.

**Acceptance Criteria**:
- Format: Table with Command, Syntax, Example, Description
- All 4 commands: create, list, view, archive
- Common flags and options
- Printable (single page PDF)
- Markdown source with PDF generation

**Location**: `docs/planning/cheat-sheet.md`

---

## 5. Non-Goals (Deferred to Phase 2/3)

### Phase 2 Deferred Items

**SOAR Integration**:
- Automatic goal decomposition via `SOAROrchestrator`
- Intelligent subgoal generation with dependencies
- Complexity assessment (simple/moderate/complex)

**Memory Integration**:
- File path resolution from memory index
- Code-aware task generation with line numbers
- Context retrieval for plan decomposition

**Agent Discovery Integration**:
- Automatic agent recommendation for subgoals
- Capability scoring with keyword matching
- Gap detection with fallback suggestions

### Phase 3 Deferred Items

**`aur plan implement` Command**:
- Plan execution with agent delegation
- Sequential subgoal execution
- Checkpoint/resume capability
- Results collection per subgoal

**Execution Orchestration**:
- Agent subprocess spawning
- Dependency-based execution ordering
- Progress tracking with state.json
- Interactive gap resolution

---

## 6. Design Considerations

### Architecture Principles

1. **Test-Then-Enhance Approach**:
   - Phase 1: Integrate proven OpenSpec foundation (284 tests)
   - Phase 2: Layer Aurora intelligence on top
   - Incremental value delivery per phase

2. **Aurora-Native Directory Structure**:
   - Primary location: `.aurora/plans/` (NOT `openspec/`)
   - Clean Aurora branding and identity
   - No backward compatibility with OpenSpec directory structure in Phase 1

3. **Eight-File Workflow**:
   - 4 base files: `plan.md`, `prd.md`, `tasks.md`, `agents.json`
   - 4 capability specs: `specs/planning/`, `/commands/`, `/validation/`, `/schemas/`
   - Separation of concerns: Strategy, requirements, tactics, metadata, specifications

4. **Validation-First Design**:
   - Pydantic schemas for all JSON files
   - JSON Schema validation for agents.json
   - Graceful error handling with Result types
   - Detailed error messages with suggestions

### Technology Stack

**Core Dependencies**:
- **Jinja2**: Template engine for file generation
- **Pydantic**: Schema validation and data modeling
- **python-slugify**: Plan ID slug generation
- **Rich**: Terminal output formatting
- **Click**: CLI framework (existing)

**Development Dependencies**:
- **pytest**: Testing framework (existing)
- **pytest-cov**: Coverage reporting (existing)
- **mypy**: Type checking (existing)
- **ruff**: Linting (existing)

### Directory Structure

**Aurora Planning Package**:
```
packages/planning/
├── src/aurora_planning/
│   ├── __init__.py              # Package exports
│   ├── commands/                # CLI command implementations
│   │   ├── __init__.py
│   │   ├── create.py            # CreateCommand
│   │   ├── list.py              # ListCommand
│   │   ├── view.py              # ViewCommand
│   │   └── archive.py           # ArchiveCommand
│   ├── parsers/                 # Markdown parsers (from OpenSpec)
│   │   ├── __init__.py
│   │   ├── markdown.py
│   │   ├── requirements.py
│   │   └── metadata.py
│   ├── schemas/                 # Pydantic models
│   │   ├── __init__.py
│   │   ├── plan.py              # Plan schema
│   │   ├── agents.py            # AgentsManifest schema
│   │   └── agents.schema.json   # JSON Schema
│   ├── templates/               # Jinja2 templates (8 files)
│   │   ├── plan.md.j2
│   │   ├── prd.md.j2
│   │   ├── tasks.md.j2
│   │   ├── agents.json.j2
│   │   ├── planning.md.j2
│   │   ├── commands.md.j2
│   │   ├── validation.md.j2
│   │   └── schemas.md.j2
│   ├── validators/              # Validation logic (from OpenSpec)
│   │   ├── __init__.py
│   │   ├── plan.py
│   │   └── requirements.py
│   └── config.py                # Planning-specific config
├── tests/
│   ├── unit/
│   │   └── planning/            # 284 migrated tests
│   └── integration/
│       └── planning/            # ~20 new integration tests
├── README.md
└── pyproject.toml
```

**User's .aurora/ Directory**:
```
~/.aurora/
├── plans/
│   ├── active/
│   │   ├── 0001-oauth-auth/
│   │   │   ├── plan.md
│   │   │   ├── prd.md
│   │   │   ├── tasks.md
│   │   │   ├── agents.json
│   │   │   └── specs/
│   │   │       ├── planning/oauth-auth-planning.md
│   │   │       ├── commands/oauth-auth-schema.schema.md
│   │   │       ├── validation/oauth-auth-validation.md
│   │   │       └── schemas/oauth-auth-schemas.md
│   │   └── 0002-user-registration/
│   │       └── (same structure)
│   └── archive/
│       └── 2026-01-15-0001-oauth-auth/
│           └── (same structure as active)
└── config/
    └── tools/  # Phase 2: Tool configurations
```

### Integration Points

**With Existing Aurora Systems**:
- **aurora_cli**: Register `aur plan` command group
- **aurora_cli/config.py**: Add `planning` section
- **aurora_core**: No direct dependencies (planning is self-contained)
- **aurora_soar**: No integration in Phase 1 (deferred to Phase 2)
- **aurora_reasoning**: No integration in Phase 1 (deferred to Phase 2)

**With PRD 0016 (Agent Discovery)**:
- Phase 1: No integration (manual agent assignment)
- Phase 2: Will use `AgentManifest` API for agent recommendations

**With Memory System**:
- Phase 1: No integration (generic file paths)
- Phase 2: Will use `MemoryRetriever` for file path resolution

### Performance Considerations

**Targets** (Aspirational, not blocking):
- Plan creation: <5s for full 8-file generation
- Plan listing: <500ms for 50 plans
- Plan viewing: <200ms to load and format
- Archive operation: <1s for atomic move

**Optimization Strategies**:
- Lazy loading: Only load plan data when needed
- Caching: Cache plan list in memory (invalidate on filesystem changes)
- Parallel operations: Template rendering can be parallelized
- Minimal I/O: Use `os.scandir()` over `os.listdir()` for directory scanning

---

## 7. Testing Strategy

### Coverage Targets

**Overall Coverage**: ≥95% (maintain OpenSpec level)

**Per Module**:
- `commands/`: ≥90% (CLI logic with mocking)
- `parsers/`: ≥95% (critical parsing logic)
- `schemas/`: ≥98% (Pydantic validation)
- `templates/`: N/A (tested via integration)
- `validators/`: ≥95% (validation rules)

### Test Pyramid

**Unit Tests** (284 migrated from OpenSpec):
- Schema validation (Pydantic models)
- Template rendering (Jinja2)
- Parsers (markdown, requirements)
- Validators (plan structure, requirements)
- ID generation (auto-increment, slug)
- Archive operations (atomic move, rollback)

**Integration Tests** (~20 new):
- End-to-end command execution
- File generation and validation
- Directory structure creation
- Config loading and overrides
- Error handling and recovery

**Acceptance Tests** (~10 new):
- User workflow scenarios (create → list → view → archive)
- Multi-plan management
- Archive and restore
- Configuration overrides

### Test Data and Fixtures

**Fixtures**:
- `temp_plans_dir`: Temporary `.aurora/plans/` directory
- `sample_plan`: Pre-generated plan with 8 files
- `mock_config`: Config with test-specific paths
- `cli_runner`: Click CliRunner for command testing

**Test Data**:
- Valid agents.json examples
- Invalid agents.json (missing fields, wrong types)
- Sample plan.md with various structures
- Edge cases: Empty goals, very long goals, special characters

### TDD Workflow with Shell Verification

**Process**:
1. Write failing test
2. Run test: `pytest tests/unit/planning/test_create.py::test_plan_create -v`
3. Implement feature
4. Run test: Green ✅
5. **Verify with shell command**: `aur plan create "Test" && ls .aurora/plans/active/`
6. Refactor
7. Commit

**Critical Tests with Shell Verification**:
- FR-2.1 (create): `aur plan create "Test Goal"`
- FR-2.2 (list): `aur plan list`
- FR-2.3 (view): `aur plan view 0001`
- FR-2.4 (archive): `aur plan archive 0001`
- FR-4.2 (specs): `ls .aurora/plans/active/0001-*/specs/`

### CI Pipeline Checks

**On Every Commit**:
1. Lint: `ruff check packages/planning/`
2. Type check: `mypy packages/planning/`
3. Unit tests: `pytest tests/unit/planning/ --cov`
4. Integration tests: `pytest tests/integration/planning/`
5. Coverage report: Fail if <95%

**On Pull Request**:
- All above checks
- Acceptance tests: `pytest tests/acceptance/planning/`
- Documentation build: `make docs`
- Performance benchmarks: `pytest --benchmark-only`

---

## 8. Migration Plan

### 8-Phase Migration Strategy

#### Phase A: Preparation (Day 1, 2 hours)

**Goal**: Audit OpenSpec tests and prepare migration checklist.

**Tasks**:
1. Run OpenSpec tests in `/tmp/openspec-source/`: `pytest aurora/tests/ -v`
2. Document test count: 284 expected
3. Identify test categories: unit, integration, acceptance
4. Create migration checklist: List all test files to migrate
5. Document breaking changes (if any)

**Output**: `MIGRATION_CHECKLIST.md` with 284 tests listed

**Validation**:
```bash
cd /tmp/openspec-source
pytest aurora/tests/ -v --co  # List all tests
wc -l MIGRATION_CHECKLIST.md  # Should list ~284 tests
```

---

#### Phase B: Package Scaffolding (Day 1, 4 hours)

**Goal**: Create `aurora.planning` package structure.

**Tasks**:
1. Create directory: `packages/planning/src/aurora_planning/`
2. Create submodules: `commands/`, `parsers/`, `schemas/`, `templates/`, `validators/`
3. Create `__init__.py` files with exports
4. Create `pyproject.toml` with dependencies
5. Add to root `pyproject.toml` workspace
6. Create test directories: `tests/unit/planning/`, `tests/integration/planning/`

**Output**: Package skeleton with correct structure

**Validation**:
```bash
python -c "import aurora_planning; print(aurora_planning.__file__)"
# Should print: .../packages/planning/src/aurora_planning/__init__.py
```

---

#### Phase C: Code Migration (Day 1-2, 8 hours)

**Goal**: Copy OpenSpec code to `aurora_planning`, update imports.

**Tasks**:
1. Copy `commands/`: archive.py, init.py, list.py, update.py, view.py
2. Copy `parsers/`: markdown.py, requirements.py, metadata.py
3. Copy `schemas/`: plan.py, spec.py
4. Copy `templates/`: All `.j2` files (update to 8 templates)
5. Copy `validators/`: plan.py, requirement.py
6. Update all imports: `from openspec` → `from aurora.planning`
7. Update directory paths: `openspec/` → `.aurora/plans/`
8. Add `create.py` command (new, wraps existing logic)

**Output**: Functional code in `aurora_planning` package

**Validation**:
```bash
python -c "from aurora.planning.commands import ArchiveCommand; print('OK')"
# Should print: OK
```

---

#### Phase D: Test Migration (Day 2, 6 hours)

**Goal**: Migrate all 284 OpenSpec tests.

**Tasks**:
1. Copy test files to `tests/unit/planning/`
2. Update imports in tests: `from openspec` → `from aurora.planning`
3. Update fixture paths: `openspec/` → `.aurora/plans/`
4. Add `conftest.py` with shared fixtures (temp_plans_dir, sample_plan)
5. Run tests batch-by-batch, fix import errors
6. Target: ≥280 tests passing (allow 4 for breaking changes)

**Output**: 280+ tests passing

**Validation**:
```bash
pytest tests/unit/planning/ -v
# Expected: ≥280 passed, ≤4 failed
pytest tests/unit/planning/ --cov=aurora_planning
# Expected: Coverage ≥95%
```

---

#### Phase E: CLI Integration (Day 3, 4 hours)

**Goal**: Register `aur plan` command group in CLI.

**Tasks**:
1. Update `aurora_cli/main.py`: Import `plan_group` from `aurora_planning`
2. Register command group: `cli.add_command(plan_group)`
3. Update help text: Add `aur plan` examples
4. Create `aurora_planning/cli.py`: Define `plan_group` with 4 commands
5. Test command invocation: `aur plan create "Test"`

**Output**: `aur plan` commands working

**Validation**:
```bash
aur plan --help
# Should show: create, list, view, archive subcommands

aur plan create "Test Goal"
# Should create: .aurora/plans/active/0001-test-goal/
```

---

#### Phase F: Configuration & Templates (Day 3, 4 hours)

**Goal**: Add planning config section, finalize templates.

**Tasks**:
1. Update `aurora_cli/config.py`: Add `planning` section
2. Set defaults: `base_dir = ~/.aurora/plans`, `template_dir = <package>/templates`
3. Create 8 templates: plan.md.j2, prd.md.j2, tasks.md.j2, agents.json.j2, + 4 spec templates
4. Test template rendering with Jinja2
5. Test config overrides: `AURORA_PLANS_DIR` env var

**Output**: Full 8-file generation working

**Validation**:
```bash
aur plan create "OAuth Auth"
ls .aurora/plans/active/0001-oauth-auth/
# Should show: plan.md prd.md tasks.md agents.json specs/

ls .aurora/plans/active/0001-oauth-auth/specs/
# Should show: planning/ commands/ validation/ schemas/
```

---

#### Phase G: Documentation (Day 4, 4 hours)

**Goal**: Create comprehensive documentation.

**Tasks**:
1. Write `packages/planning/README.md`: Quick start, commands, examples
2. Generate API reference: `make docs` (Sphinx or pdoc)
3. Write `docs/planning/user-guide.md`: Workflows, best practices, troubleshooting
4. Create `docs/planning/cheat-sheet.md`: Command reference table
5. Review all docstrings: Ensure Google style with examples

**Output**: Complete documentation suite

**Validation**:
```bash
open packages/planning/README.md  # Review quick start
open docs/planning/api/index.html  # Browse API reference
open docs/planning/user-guide.md  # Review user guide
```

---

#### Phase H: Validation and Release (Day 4, 2 hours)

**Goal**: Final validation, release preparation.

**Tasks**:
1. Run full test suite: `pytest tests/ -v`
2. Check coverage: `pytest --cov=aurora_planning --cov-report=html`
3. Lint: `ruff check packages/planning/`
4. Type check: `mypy packages/planning/`
5. Performance benchmarks: `pytest --benchmark-only`
6. Create release notes: Document Phase 1 features
7. Tag commit: `git tag v0.1.0-phase1`

**Output**: Release-ready Phase 1 implementation

**Validation**:
```bash
pytest tests/ -v  # All tests pass
pytest --cov=aurora_planning  # Coverage ≥95%
mypy packages/planning/  # 0 errors
ruff check packages/planning/  # 0 critical issues
```

---

### Rollback Plan

**If Migration Fails**:
1. Revert to pre-migration commit: `git reset --hard <commit-hash>`
2. Keep OpenSpec source separate: Work in `/tmp/openspec-source/`
3. Investigate failures: Review test output, fix breaking changes
4. Retry migration phases incrementally

**Partial Success Handling**:
- Phases A-C complete, D fails: Fix test imports, retry Phase D
- Phases A-D complete, E fails: Fix CLI registration, retry Phase E
- Document any tests permanently skipped (with rationale)

### Migration Validation Checklist

**Critical Success Criteria**:
- [ ] ≥280 OpenSpec tests passing (≥98%)
- [ ] Coverage ≥95% across all modules
- [ ] All 4 CLI commands functional: create, list, view, archive
- [ ] 8-file generation works: 4 base + 4 specs
- [ ] `.aurora/plans/` directory structure correct
- [ ] Archive with timestamp works
- [ ] Plan ID auto-increment works
- [ ] Documentation complete: README, API, User Guide, Cheat Sheet
- [ ] 0 mypy errors
- [ ] 0 critical ruff issues

---

## 9. Success Criteria

### Top 3 Critical Criteria (Must Pass)

#### 1. OpenSpec Integration Complete
- **Metric**: ≥280 of 284 tests passing (≥98%)
- **Validation**: `pytest tests/unit/planning/ tests/integration/planning/ -v`
- **Blocker**: Cannot release if <280 tests pass

#### 2. All 4 Commands Functional
- **Metric**: `aur plan create/list/view/archive` all work end-to-end
- **Validation**: Run acceptance test suite, manual smoke test
- **Blocker**: Cannot release if any command fails

#### 3. Eight-File Structure Generated
- **Metric**: 4 base files + 4 spec files created per plan
- **Validation**: `aur plan create "Test" && ls .aurora/plans/active/0001-test/specs/`
- **Blocker**: Cannot release if file generation incomplete

### Secondary Criteria (Important, Not Blocking)

#### 4. Performance Targets Met
- **Metric**: Plan creation <5s, list <500ms
- **Validation**: `pytest --benchmark-only`
- **Status**: Aspirational (track but don't block release)

#### 5. Documentation Complete
- **Metric**: README, API reference, User guide, Cheat sheet all exist
- **Validation**: Manual review of docs/
- **Status**: Required for release (not blocking development)

#### 6. Configuration Working
- **Metric**: `planning.base_dir` configurable, env var overrides work
- **Validation**: `aur config set planning.base_dir ~/custom && aur plan create "Test"`
- **Status**: Required for release

### Acceptance Gates

**Gate 1: Code Complete** (Day 3)
- All code migrated to `aurora.planning`
- All imports updated
- Package structure correct
- Pass: Proceed to testing phase

**Gate 2: Tests Passing** (Day 3)
- ≥280 tests passing
- Coverage ≥95%
- 0 mypy errors
- Pass: Proceed to CLI integration

**Gate 3: CLI Integration** (Day 3)
- All 4 commands registered
- `aur plan --help` works
- End-to-end smoke test passes
- Pass: Proceed to documentation

**Gate 4: Documentation Complete** (Day 4)
- All 4 docs created (README, API, User Guide, Cheat Sheet)
- Docstrings complete
- Examples tested
- Pass: Ready for release

---

## 10. Timeline and Sprint Estimate

### Sprint Overview

**Duration**: 1 sprint (2 weeks, 10 working days)
**Team**: 1 developer, full-time
**Total Effort**: ~60 hours

### Week 1: Migration and Core Implementation

**Day 1** (8 hours):
- Phase A: Preparation (2h)
- Phase B: Package Scaffolding (4h)
- Phase C: Code Migration (2h) - Start

**Day 2** (8 hours):
- Phase C: Code Migration (6h) - Complete
- Phase D: Test Migration (2h) - Start

**Day 3** (8 hours):
- Phase D: Test Migration (6h) - Complete
- Phase E: CLI Integration (2h) - Start

**Day 4** (8 hours):
- Phase E: CLI Integration (2h) - Complete
- Phase F: Configuration & Templates (4h) - Complete
- Buffer: Fix test failures (2h)

**Day 5** (8 hours):
- Integration testing (4h)
- Fix bugs and edge cases (4h)

**Week 1 Milestone**: Core functionality working, tests passing

---

### Week 2: Polish, Documentation, and Release

**Day 6** (8 hours):
- Phase G: Documentation (4h) - README, API reference
- Acceptance testing (4h)

**Day 7** (8 hours):
- Phase G: Documentation (4h) - User guide, Cheat sheet
- Polish CLI output (2h)
- Error message improvements (2h)

**Day 8** (8 hours):
- Phase H: Validation (2h)
- Performance benchmarking (2h)
- Bug fixes (4h)

**Day 9** (8 hours):
- Final testing (4h)
- Release notes (2h)
- Tag and release (2h)

**Day 10** (4 hours):
- Buffer for unexpected issues
- Demo preparation
- Stakeholder review

**Week 2 Milestone**: Documentation complete, release ready

---

### Milestones

**M1: Package Migration Complete** (Day 3)
- Deliverable: `aurora.planning` package with 280+ tests passing
- Acceptance: `pytest tests/unit/planning/ -v` shows ≥280 passed

**M2: CLI Commands Working** (Day 4)
- Deliverable: All 4 commands functional (`create`, `list`, `view`, `archive`)
- Acceptance: Smoke test passes all scenarios

**M3: Documentation Complete** (Day 7)
- Deliverable: README, API reference, User guide, Cheat sheet
- Acceptance: Manual review confirms completeness

**M4: Release Ready** (Day 9)
- Deliverable: Tagged commit, release notes, all gates passed
- Acceptance: All success criteria met

---

### Risk Mitigation

**Risk 1: Test Migration Failures**
- Probability: Medium
- Impact: High (blocks release)
- Mitigation: Phase D has 6 hours buffer, document skipped tests with rationale
- Contingency: Defer up to 4 tests (98% pass rate still acceptable)

**Risk 2: Import Path Conflicts**
- Probability: Low
- Impact: Medium (delays migration)
- Mitigation: Use explicit imports, avoid `*` imports
- Contingency: 2-hour buffer on Day 5 for import fixes

**Risk 3: Template Rendering Issues**
- Probability: Low
- Impact: Medium (file generation incomplete)
- Mitigation: Test templates early in Phase F, validate with Jinja2 sandbox
- Contingency: Simplify templates if complex rendering fails

**Risk 4: Performance Below Targets**
- Probability: Medium
- Impact: Low (targets are aspirational)
- Mitigation: Profile critical paths, optimize after functionality working
- Contingency: Accept <5s if functionality correct (Phase 2 can optimize)

---

## 11. Appendices

### Appendix A: JSON Schema for agents.json

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "Aurora Planning Agents Manifest",
  "type": "object",
  "required": ["plan_id", "goal", "status", "created_at", "subgoals"],
  "properties": {
    "plan_id": {
      "type": "string",
      "pattern": "^[0-9]{4}-[a-z0-9-]+$",
      "description": "Plan identifier (NNNN-slug format)"
    },
    "goal": {
      "type": "string",
      "minLength": 1,
      "maxLength": 500,
      "description": "User-provided goal description"
    },
    "status": {
      "type": "string",
      "enum": ["active", "archived"],
      "description": "Plan lifecycle status"
    },
    "created_at": {
      "type": "string",
      "format": "date-time",
      "description": "ISO 8601 timestamp of plan creation"
    },
    "archived_at": {
      "type": "string",
      "format": "date-time",
      "description": "ISO 8601 timestamp of archive (if archived)"
    },
    "subgoals": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["id", "title", "agent_id", "status"],
        "properties": {
          "id": {
            "type": "string",
            "pattern": "^sg-[0-9]+$",
            "description": "Subgoal identifier (sg-1, sg-2, ...)"
          },
          "title": {
            "type": "string",
            "minLength": 5,
            "maxLength": 100,
            "description": "Subgoal title"
          },
          "description": {
            "type": "string",
            "maxLength": 500,
            "description": "Detailed subgoal description"
          },
          "agent_id": {
            "type": "string",
            "pattern": "^@[a-z0-9-]+$",
            "description": "Assigned agent ID (e.g., @business-analyst)"
          },
          "status": {
            "type": "string",
            "enum": ["pending", "in_progress", "completed", "blocked"],
            "description": "Subgoal execution status"
          },
          "dependencies": {
            "type": "array",
            "items": {
              "type": "string",
              "pattern": "^sg-[0-9]+$"
            },
            "description": "List of prerequisite subgoal IDs"
          }
        }
      }
    },
    "tags": {
      "type": "array",
      "items": {
        "type": "string"
      },
      "description": "User-defined tags for categorization"
    },
    "metadata": {
      "type": "object",
      "description": "Additional custom metadata"
    }
  }
}
```

**Example agents.json**:
```json
{
  "plan_id": "0001-oauth-auth",
  "goal": "Implement OAuth2 authentication",
  "status": "active",
  "created_at": "2026-01-15T10:00:00Z",
  "subgoals": [
    {
      "id": "sg-1",
      "title": "Research OAuth providers",
      "description": "Evaluate Auth0, Okta, and Google OAuth",
      "agent_id": "@business-analyst",
      "status": "completed",
      "dependencies": []
    },
    {
      "id": "sg-2",
      "title": "Implement backend OAuth flow",
      "description": "Create Auth0 SDK integration and endpoints",
      "agent_id": "@full-stack-dev",
      "status": "in_progress",
      "dependencies": ["sg-1"]
    }
  ],
  "tags": ["authentication", "oauth2", "security"],
  "metadata": {
    "complexity": "moderate",
    "estimated_hours": 40
  }
}
```

---

### Appendix B: Example plan.md Template

```jinja2
# Plan: {{ goal }}

**Plan ID**: `{{ plan_id }}`
**Created**: {{ created_at }}
**Status**: Active

---

## Goal

{{ goal }}

---

## Subgoals

{% for subgoal in subgoals %}
### {{ subgoal.id }}: {{ subgoal.title }}

**Description**: {{ subgoal.description }}
**Agent**: {{ subgoal.agent_id }}
**Status**: {{ subgoal.status }}
{% if subgoal.dependencies %}
**Dependencies**: {{ subgoal.dependencies | join(', ') }}
{% endif %}

---

{% endfor %}

## Dependencies Graph

```
{% for subgoal in subgoals %}
{{ subgoal.id }} ({{ subgoal.agent_id }}){% if subgoal.dependencies %} ← {{ subgoal.dependencies | join(', ') }}{% endif %}
{% endfor %}
```

---

## Next Steps

1. Review subgoals and refine descriptions
2. Implement tasks from `tasks.md`
3. Track progress with `aur plan view {{ plan_id }}`
4. Archive when complete: `aur plan archive {{ plan_id }}`
```

---

### Appendix C: Example Commands Cheat Sheet

| Command | Syntax | Example | Description |
|---------|--------|---------|-------------|
| **Create Plan** | `aur plan create <goal>` | `aur plan create "Implement OAuth2"` | Generate new plan with 8 files |
| **List Active** | `aur plan list` | `aur plan list` | Show all active plans with progress |
| **List Archived** | `aur plan list --archived` | `aur plan list --archived` | Show only archived plans |
| **List All** | `aur plan list --all` | `aur plan list --all` | Show active + archived plans |
| **View Dashboard** | `aur plan view <id>` | `aur plan view 0001` | Display plan details |
| **Archive Plan** | `aur plan archive <id>` | `aur plan archive 0001` | Move to archive with timestamp |
| **Force Archive** | `aur plan archive <id> --force` | `aur plan archive 0001 --force` | Skip confirmation prompt |
| **Get Config** | `aur config get planning.base_dir` | `aur config get planning.base_dir` | Show planning directory |
| **Set Config** | `aur config set planning.base_dir <path>` | `aur config set planning.base_dir ~/plans` | Change planning directory |

**Directory Locations**:
- Active plans: `~/.aurora/plans/active/<plan-id>/`
- Archived plans: `~/.aurora/plans/archive/YYYY-MM-DD-<plan-id>/`
- Config: `~/.aurora/config/config.json`

**File Structure** (8 files per plan):
- Base: `plan.md`, `prd.md`, `tasks.md`, `agents.json`
- Specs: `specs/planning/*.md`, `specs/commands/*.md`, `specs/validation/*.md`, `specs/schemas/*.md`

---

### Appendix D: Error Code Reference

| Code | Error | Cause | Solution |
|------|-------|-------|----------|
| E001 | Plan directory not writable | Permissions issue | `chmod 755 ~/.aurora/plans` |
| E002 | Invalid plan ID format | Malformed NNNN-slug | Use format `0001-my-plan` |
| E003 | Plan not found | Plan ID doesn't exist | List plans: `aur plan list --all` |
| E004 | agents.json validation error | Invalid JSON schema | Check required fields: plan_id, goal, status |
| E005 | Template rendering failed | Missing template variable | Report bug, template may be corrupt |
| E006 | Archive failed (plan incomplete) | Tasks not 100% done | Use `--force` to archive anyway |
| E007 | Config value invalid | Wrong type or format | Check config schema |
| E008 | Plan ID collision | NNNN already exists | Auto-increment should prevent this (report bug) |
| E009 | Atomic operation failed | Filesystem error mid-operation | Check disk space, rollback applied |
| E010 | Missing required file | plan.md, prd.md, tasks.md, or agents.json missing | Recreate plan or restore from backup |

---

### Appendix E: Phase 2 Integration Preview

**What Phase 2 Adds**:

1. **`aur init` Command**:
   - Interactive 3-step tool selection (Claude Code, OpenCode, AmpCode, Droid)
   - Project context setup (edit `project.md`)
   - Tool-specific slash command configuration
   - Multi-tool workflow setup

2. **SOAR Integration**:
   - Replace template-based `plan.md` with SOAR decomposition
   - Call `SOAROrchestrator.decompose(goal, context, agents)`
   - Intelligent subgoal generation with dependencies
   - Complexity assessment (simple/moderate/complex)

3. **Memory Integration**:
   - File path resolution: `MemoryRetriever.search()` for code locations
   - Code-aware tasks: `tasks.md` includes `src/auth.py lines 15-30`
   - Context retrieval: Memory provides context for decomposition

4. **Agent Discovery Integration**:
   - Agent recommendation: `recommend_agents_for_subgoals()` from PRD 0016
   - Capability scoring: Keyword matching with confidence thresholds
   - Gap detection: Identify missing agent types, suggest fallbacks
   - Update `agents.json` with recommended agents

**Migration from Phase 1 to Phase 2**:
- Phase 1 plans continue to work (backward compatible)
- New plans use enhanced SOAR/memory/agent features
- Old plans can be "upgraded" via `aur plan enhance <id>` (Phase 2 command)

---

## Document History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-01-02 | Initial PRD with OpenSpec migration focus |
| 2.0 | 2026-01-02 | Updated with Aurora-native directory structure (`.aurora/plans/`), 8-file workflow (4 base + 4 specs), command mapping clarification, Phase 2/3 deferred items |

---

**END OF PRD**

**Next Steps**:
1. Review and approve this PRD
2. Begin Phase A: Preparation (audit OpenSpec tests)
3. Execute migration plan Phases A through H
4. Generate detailed task list using `@2-generate-tasks` agent

**Questions or Feedback**: Share with team for stakeholder review before implementation begins.
