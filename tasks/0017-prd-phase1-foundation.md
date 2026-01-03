# PRD: Aurora Planning System - Phase 1 Foundation

**Version**: 1.0
**Date**: 2026-01-02
**Status**: Planning
**Sprint**: Phase 1 of 3
**Parent Spec**: `/tasks/0017-planning-specs-v2.md`

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
2. **Four-File Workflow**: Automated generation of `plan.md`, `prd.md`, `tasks.md`, `agents.json`
3. **Multi-Tool Configuration**: Slash commands for Claude Code, OpenCode, AmpCode, Droid
4. **Proven Foundation**: 284 migrated tests ensuring reliability from day one

**Phase 1 Scope**: Foundation infrastructure with template-based planning
**Phase 2 Vision**: Layer Aurora intelligence (SOAR decomposition, memory retrieval, agent discovery)
**Phase 3 Vision**: Execution orchestration with agent delegation

### Business Value

- **Time Savings**: Automated plan generation reduces manual planning from hours to seconds
- **Quality Assurance**: 284 tests ensure robust planning infrastructure
- **Ecosystem Integration**: Seamless workflow across 4 AI coding tools
- **Extensibility**: Proven foundation ready for Phase 2/3 intelligence layers

### Success Metrics

1. **284 OpenSpec tests passing** in new `aurora.planning` package location
2. **All 4 planning commands functional**: create, list, view, archive
3. **4 tool configurators working**: Claude Code, OpenCode, AmpCode, Droid
4. **Four-file structure generated** with valid schemas and content
5. **Performance targets met**: <5s plan creation, <500ms list operations

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
- Multi-tool configuration support
- Complete validation and schema infrastructure
- Archive management and lifecycle tracking

### High-Level Goal

**Phase 1 Goal**: Establish planning foundation by migrating proven OpenSpec infrastructure into Aurora as a first-class planning package, enabling users to create, manage, and archive structured plans through native `aur plan` commands and slash command interfaces across multiple AI coding tools.

**Key Principle**: **Test-then-enhance** approach
- Phase 1: Integrate OpenSpec foundation natively (proven with 284 tests)
- Phase 2: Layer Aurora intelligence (SOAR, memory, agent discovery) on top
- Phase 3: Add execution orchestration

### Scope Boundaries

**In Scope (Phase 1)**:
- Full OpenSpec package migration to `aurora.planning`
- All 284 tests migrated and passing
- Planning commands: `aur plan create/list/view/archive`
- Four-file workflow with validation
- Multi-tool configuration module (Claude Code, OpenCode, AmpCode, Droid)
- Rule-based template generation (from OpenSpec configs)
- Documentation: README, API reference, user guide

**Out of Scope (Deferred to Phase 2/3)**:
- SOAR-powered goal decomposition (Phase 2)
- Memory-aware file path resolution (Phase 2)
- Agent recommendation with manifest integration (Phase 2)
- Plan execution and orchestration (Phase 3)
- Checkpoint/resume workflows (Phase 3)
- `aur init` full framework configuration (Phase 2)

---

## 2. Goals

### Primary Objectives

1. **Migrate OpenSpec Foundation** (FR-1.x)
   - Copy `/tmp/openspec-source/aurora/` to `packages/planning/src/aurora_planning/`
   - Update all imports from `openspec` to `aurora.planning`
   - Maintain all 284 tests in refactored Aurora structure
   - Ensure 100% test pass rate post-migration

2. **Implement Native Planning Commands** (FR-2.x)
   - `aur plan init` - Initialize `.aurora/plans/` directory structure
   - `aur plan create <goal>` - Generate plan with 4-file output
   - `aur plan list [--archived] [--all]` - List active/archived plans
   - `aur plan view <plan-id>` - Display plan dashboard
   - `aur plan archive <plan-id>` - Move plan to archive with timestamp

3. **Enable Multi-Tool Slash Commands** (FR-3.x)
   - Integrate OpenSpec config module (~100 lines)
   - Generate slash command configs for 4 tools
   - Validate configs against tool-specific schemas
   - Document configuration process

4. **Establish Four-File Workflow** (FR-4.x)
   - Define JSON schemas for all 4 files
   - Create example templates with comments
   - Implement validation rules
   - Generate files with correct Aurora directory structure

5. **Deliver Comprehensive Documentation** (FR-5.x)
   - README with quick start and examples
   - API reference from docstrings
   - User guide covering workflows and troubleshooting

### Secondary Objectives

- Performance benchmarking infrastructure (aspirational targets, non-blocking)
- Graceful degradation patterns for error handling
- Extensibility hooks for Phase 2 integration points

---

## 3. User Stories

### Planning Workflow

**US-1.1**: As a developer, I want to initialize Aurora planning so I can manage structured plans
**Given** I have Aurora installed
**When** I run `aur plan init`
**Then** Aurora creates `.aurora/plans/active/` and `.aurora/plans/archive/` directories with proper permissions

---

**US-1.2**: As a developer, I want to create a plan from a goal statement so I can decompose work into actionable tasks
**Given** I have initialized Aurora planning
**When** I run `aur plan create "Implement OAuth2 authentication"`
**Then** Aurora generates:
- Plan ID `0001-implement-oauth2-authentication`
- Four files: `plan.md`, `prd.md`, `tasks.md`, `agents.json`
- Files placed in `.aurora/plans/active/0001-implement-oauth2-authentication/`
- Content follows defined schemas and templates

---

**US-1.3**: As a developer, I want to list all active plans so I can see what's in progress
**Given** I have created multiple plans
**When** I run `aur plan list`
**Then** Aurora displays:
- Plan IDs with slugs
- Task completion percentages
- Last modified timestamps
- Sorted by most recent first

---

**US-1.4**: As a developer, I want to view a plan's details so I can review subgoals and tasks
**Given** I have an active plan `0001-implement-oauth2-authentication`
**When** I run `aur plan view 0001`
**Then** Aurora displays:
- Goal statement
- Subgoals with descriptions
- Task breakdown per subgoal
- Agent assignments (if any)
- Overall progress percentage

---

**US-1.5**: As a developer, I want to archive a completed plan so I can keep my workspace clean
**Given** I have completed plan `0001-implement-oauth2-authentication`
**When** I run `aur plan archive 0001`
**Then** Aurora:
- Moves plan to `.aurora/plans/archive/2026-01-02-0001-implement-oauth2-authentication/`
- Updates `agents.json` with `archived_at` timestamp
- Removes plan from active list
- Preserves all plan content

---

### Multi-Tool Integration

**US-2.1**: As a Claude Code user, I want slash commands for planning so I can stay in my workflow
**Given** Aurora planning is configured
**When** I type `/aur:plan "Add user registration"`
**Then** Claude Code executes `aur plan create "Add user registration"` and streams output to chat

---

**US-2.2**: As an OpenCode user, I want the same slash command experience so I can use Aurora planning
**Given** Aurora planning is configured
**When** I type `/aur:plan "Add user registration"`
**Then** OpenCode executes `aur plan create "Add user registration"` with identical output

---

**US-2.3**: As a developer using multiple AI tools, I want consistent configuration so I don't repeat setup
**Given** Aurora planning is installed
**When** I run `aur plan init`
**Then** Aurora generates configuration files for:
- Claude Code: `~/.config/Claude/claude_desktop_config.json` (Linux)
- OpenCode: Tool-specific config path
- AmpCode: Tool-specific config path
- Droid: Tool-specific config path

---

### Error Handling

**US-3.1**: As a developer, I want clear error messages when initialization fails so I can fix issues
**Given** `.aurora/plans/` already exists with incorrect permissions
**When** I run `aur plan init`
**Then** Aurora:
- Returns structured error with code `PLANNING_INIT_FAILED`
- Suggests fix: "Directory exists. Use --force to reinitialize or check permissions."
- Exits with non-zero status code

---

**US-3.2**: As a developer, I want graceful degradation if plan generation partially fails so I don't lose work
**Given** Plan creation succeeds but `prd.md` generation fails
**When** I run `aur plan create "goal"`
**Then** Aurora:
- Creates plan directory with plan ID
- Generates `plan.md`, `tasks.md`, `agents.json` successfully
- Returns `PlanResult` with `success=True`, `warnings=["prd.md generation failed"]`
- Allows retry with `aur plan update 0001`

---

## 4. Functional Requirements

### FR-1: OpenSpec Package Migration

**FR-1.1**: Migrate OpenSpec Directory Structure
**Description**: Copy OpenSpec source code from `/tmp/openspec-source/aurora/` to Aurora's package structure
**Acceptance Criteria**:
- Package structure created at `packages/planning/src/aurora_planning/`
- Subdirectories match OpenSpec structure:
  - `commands/` - archive, init, list, update, view
  - `parsers/` - markdown, requirements, metadata
  - `schemas/` - plan, spec, validation
  - `templates/` - AGENTS.md, project.md
  - `validators/` - plan validators, requirement validators
  - `config.py` - Configuration module
- All Python files copied with proper `__init__.py` files
- No OpenSpec branding or references remain in code

**Validation**:
```bash
# Directory structure exists
ls -la packages/planning/src/aurora_planning/

# All modules importable
python -c "from aurora.planning import commands, parsers, schemas, templates, validators"
```

---

**FR-1.2**: Update Import Statements
**Description**: Replace all `from openspec` imports with `from aurora.planning` throughout migrated codebase
**Acceptance Criteria**:
- All internal imports updated (e.g., `from openspec.schemas import Plan` → `from aurora.planning.schemas import Plan`)
- Cross-package imports use `aurora.*` namespace (e.g., `from aurora.core import ...`)
- No remaining `openspec` strings in import statements
- All modules resolve without ImportError

**Validation**:
```bash
# No openspec imports remain
grep -r "from openspec" packages/planning/src/aurora_planning/
# Should return: (no output)

# Import check passes
python -c "from aurora.planning.schemas import Plan; print('OK')"
```

---

**FR-1.3**: Migrate Test Suite
**Description**: Move all 284 OpenSpec tests to Aurora test structure and update imports
**Acceptance Criteria**:
- Tests organized as:
  - `tests/unit/planning/` - Unit tests for all modules
  - `tests/integration/planning/` - Integration tests for command workflows
- All test imports updated to `aurora.planning`
- Test fixtures adapted for Aurora directory structure (`.aurora/plans/` instead of `openspec/`)
- All 284 tests passing with pytest
- Test coverage maintained at ≥95%

**Validation**:
```bash
# Test count matches
pytest tests/unit/planning/ tests/integration/planning/ --collect-only | grep "test session starts"
# Should show: 284 tests collected

# All tests pass
pytest tests/unit/planning/ tests/integration/planning/ -v
# Should show: 284 passed

# Coverage check
pytest --cov=packages/planning/src/aurora_planning --cov-report=term-missing
# Should show: ≥95% coverage
```

---

**FR-1.4**: Configure Package Metadata
**Description**: Set up `pyproject.toml` for `aurora-planning` package with dependencies
**Acceptance Criteria**:
- Package name: `aurora-planning`
- Version: `0.2.0` (aligned with Aurora core)
- Dependencies listed:
  - `pydantic>=2.0`
  - `python-slugify>=8.0` (for plan ID generation)
  - `jinja2>=3.1` (for template rendering)
  - `aurora-core>=0.2.0` (for shared utilities)
- Namespace package configured: `aurora.planning` maps to `aurora_planning`
- Entry points defined for CLI integration

**Validation**:
```bash
# Package builds
cd packages/planning && pip install -e .

# Namespace import works
python -c "import aurora.planning; print(aurora.planning.__version__)"
# Should print: 0.2.0
```

---

**FR-1.5**: Adapt Aurora Directory Structure
**Description**: Configure planning package to use Aurora's directory conventions
**Acceptance Criteria**:
- Planning root: `~/.aurora/plans/` (not `openspec/`)
- Active plans: `~/.aurora/plans/active/`
- Archived plans: `~/.aurora/plans/archive/`
- Archive format: `YYYY-MM-DD-NNNN-slug/` (OpenSpec format preserved)
- Config file: `~/.aurora/config.json` includes planning settings
- Respects `AURORA_HOME` environment variable if set

**Validation**:
```bash
# Init creates correct structure
aur plan init
ls -la ~/.aurora/plans/
# Should show: active/ and archive/ directories

# Config includes planning
cat ~/.aurora/config.json | jq '.planning'
# Should show: planning configuration object
```

---

### FR-2: Native Planning Commands

**FR-2.1**: Implement `aur plan init`
**Description**: Initialize planning directory structure and generate tool configurations
**Acceptance Criteria**:
- Creates `.aurora/plans/active/` and `.aurora/plans/archive/`
- Sets directory permissions: `0755` (user rwx, group/other rx)
- Generates plan manifest file: `.aurora/plans/manifest.json`
- Initializes empty manifest: `{"active_plans": [], "archived_plans": [], "next_id": 1}`
- Returns `InitResult` with success status and created paths
- Supports `--force` flag to reinitialize existing directory
- Execution time: <100ms

**Validation**:
```bash
# Success case
aur plan init
echo $?
# Should return: 0

# Idempotent - doesn't fail if already exists
aur plan init
echo $?
# Should return: 0 (with warning message)

# Force flag works
aur plan init --force
# Should recreate directories
```

**Error Cases**:
- Insufficient permissions → `PLANNING_INIT_FAILED` with suggestion to check permissions
- Existing directory with files → Warns but doesn't overwrite unless `--force`

---

**FR-2.2**: Implement `aur plan create <goal>`
**Description**: Generate new plan with four-file structure from goal statement
**Acceptance Criteria**:
- Accepts goal string (quoted or unquoted)
- Generates unique plan ID: `NNNN-slug` format
  - NNNN: Auto-increment from manifest `next_id` (zero-padded to 4 digits)
  - slug: Kebab-case from goal (max 50 chars, alphanumeric + hyphens)
- Creates directory: `.aurora/plans/active/NNNN-slug/`
- Generates 4 files (detailed in FR-4.x):
  - `plan.md` - High-level decomposition from template
  - `prd.md` - Detailed requirements in OpenSpec format
  - `tasks.md` - Implementation checklist
  - `agents.json` - Machine-readable metadata
- Updates manifest with new plan entry
- Returns `PlanResult` with plan ID, file paths, and any warnings
- Execution time: <5s (aspirational)

**Validation**:
```bash
# Create plan
aur plan create "Implement OAuth2 authentication"
# Should output: Plan created: 0001-implement-oauth2-authentication

# Verify files exist
ls ~/.aurora/plans/active/0001-implement-oauth2-authentication/
# Should show: plan.md prd.md tasks.md agents.json

# Verify manifest updated
cat ~/.aurora/plans/manifest.json | jq '.next_id'
# Should show: 2
```

**Error Cases**:
- Empty goal string → `INVALID_GOAL` error
- Planning not initialized → `PLANNING_NOT_INITIALIZED` with suggestion to run `aur plan init`
- Duplicate plan ID (race condition) → Retry with next ID

---

**FR-2.3**: Implement `aur plan list`
**Description**: Display all active and/or archived plans with summary information
**Acceptance Criteria**:
- Default: Shows active plans only
- Flag `--archived`: Shows archived plans only
- Flag `--all`: Shows both active and archived
- Output format (table):
  ```
  ID    Slug                          Tasks    Progress    Last Modified
  0001  implement-oauth2-auth         12/15    80%        2h ago
  0002  add-logging-system            0/8      0%         1d ago
  ```
- Sorting: Most recently modified first
- Returns `ListResult` with plan summaries
- Execution time: <500ms for 100 plans (aspirational)

**Validation**:
```bash
# List active plans
aur plan list
# Should show: table of active plans

# List archived plans
aur plan list --archived
# Should show: table of archived plans

# List all
aur plan list --all
# Should show: combined table with status indicator
```

**Error Cases**:
- Planning not initialized → `PLANNING_NOT_INITIALIZED`
- Corrupt manifest → `MANIFEST_CORRUPT` with recovery suggestion

---

**FR-2.4**: Implement `aur plan view <plan-id>`
**Description**: Display detailed dashboard for a specific plan
**Acceptance Criteria**:
- Accepts plan ID (NNNN or full slug)
- Searches active plans by default
- Flag `--archived`: Searches archived plans
- Output includes:
  - Goal statement
  - Plan status (active/archived)
  - Overall progress (completed tasks / total tasks)
  - Subgoals list with task counts
  - Agent assignments (if present)
  - Creation and last modified timestamps
- Returns `ShowResult` with plan details
- Execution time: <500ms

**Validation**:
```bash
# View by ID
aur plan view 0001
# Should show: detailed dashboard

# View by partial slug
aur plan view oauth
# Should show: same dashboard (fuzzy match)

# View archived plan
aur plan view 0001 --archived
# Should show: dashboard with "Archived" status
```

**Error Cases**:
- Plan ID not found → `PLAN_NOT_FOUND` with suggestion to run `aur plan list`
- Ambiguous partial slug → `AMBIGUOUS_PLAN_ID` with list of matches
- Corrupt plan files → `PLAN_CORRUPT` with details on which file

---

**FR-2.5**: Implement `aur plan archive <plan-id>`
**Description**: Move completed plan to archive with timestamp preservation
**Acceptance Criteria**:
- Accepts plan ID (NNNN or full slug)
- Verifies plan exists in active directory
- Generates archive directory name: `YYYY-MM-DD-NNNN-slug/`
- Moves entire plan directory atomically (rollback on failure)
- Updates `agents.json` with:
  - `status: "archived"`
  - `archived_at: "2026-01-02T14:30:00Z"`
- Updates manifest:
  - Removes from `active_plans`
  - Adds to `archived_plans`
- Returns `ArchiveResult` with archive path
- Execution time: <1s

**Validation**:
```bash
# Archive plan
aur plan archive 0001
# Should output: Plan archived: 2026-01-02-0001-implement-oauth2-authentication

# Verify move
ls ~/.aurora/plans/active/0001-* 2>/dev/null
# Should return: (no output - plan moved)

ls ~/.aurora/plans/archive/2026-01-02-0001-*/
# Should show: plan.md prd.md tasks.md agents.json

# Verify metadata
cat ~/.aurora/plans/archive/2026-01-02-0001-*/agents.json | jq '.archived_at'
# Should show: ISO timestamp
```

**Error Cases**:
- Plan not found → `PLAN_NOT_FOUND`
- Plan already archived → `PLAN_ALREADY_ARCHIVED`
- Archive directory exists (conflict) → `ARCHIVE_CONFLICT` with suggestion to rename manually

---

### FR-3: Multi-Tool Slash Command Configuration

**FR-3.1**: Integrate OpenSpec Config Module
**Description**: Copy OpenSpec configuration generation code into Aurora planning package
**Acceptance Criteria**:
- Module location: `aurora_planning/configurators/`
- Files included:
  - `__init__.py` - Exports main functions
  - `claude_code.py` - Claude Code config generator
  - `opencode.py` - OpenCode config generator
  - `ampcode.py` - AmpCode config generator
  - `droid.py` - Droid config generator
  - `base.py` - Shared configuration logic
- Total code: ~100 lines (from OpenSpec)
- No modifications to config generation logic (preserve OpenSpec behavior)

**Validation**:
```python
# All configurators importable
from aurora.planning.configurators import (
    generate_claude_config,
    generate_opencode_config,
    generate_ampcode_config,
    generate_droid_config
)
```

---

**FR-3.2**: Generate Claude Code Configuration
**Description**: Create slash command config for Claude Code during `aur plan init`
**Acceptance Criteria**:
- Config path: `~/.config/Claude/claude_desktop_config.json` (Linux)
- Config format: JSON with `mcpServers` section (MCP protocol)
- Commands defined:
  - `/aur:plan <goal>` → `aur plan create "<goal>"`
  - `/aur:list [--archived] [--all]` → `aur plan list [flags]`
  - `/aur:view <plan-id>` → `aur plan view <plan-id>`
  - `/aur:archive <plan-id>` → `aur plan archive <plan-id>`
- Each command includes:
  - Description string
  - Argument schema (if applicable)
  - Error handling specifications
- Merges with existing config (doesn't overwrite other MCP servers)
- Creates backup before modification: `claude_desktop_config.json.bak`

**Validation**:
```bash
# Config exists
cat ~/.config/Claude/claude_desktop_config.json | jq '.mcpServers.aurora'
# Should show: Aurora MCP server configuration

# Backup created
ls ~/.config/Claude/claude_desktop_config.json.bak
# Should exist

# Commands registered
cat ~/.config/Claude/claude_desktop_config.json | jq '.mcpServers.aurora.commands | length'
# Should show: 4
```

---

**FR-3.3**: Generate OpenCode Configuration
**Description**: Create slash command config for OpenCode tool
**Acceptance Criteria**:
- Config path determined by OpenCode conventions (research task if unknown)
- Config format follows OpenCode schema (from OpenSpec configurator)
- Same 4 slash commands as Claude Code
- Validation against OpenCode schema (if available)

**Validation**:
```bash
# Config generated
cat <opencode-config-path> | jq '.commands.aurora'
# Should show: Aurora command configuration
```

---

**FR-3.4**: Generate AmpCode Configuration
**Description**: Create slash command config for AmpCode tool
**Acceptance Criteria**:
- Config path determined by AmpCode conventions
- Config format follows AmpCode schema (from OpenSpec configurator)
- Same 4 slash commands as other tools
- Validation against AmpCode schema (if available)

**Validation**:
```bash
# Config generated
cat <ampcode-config-path> | jq '.commands.aurora'
# Should show: Aurora command configuration
```

---

**FR-3.5**: Generate Droid Configuration
**Description**: Create slash command config for Droid tool
**Acceptance Criteria**:
- Config path determined by Droid conventions
- Config format follows Droid schema (from OpenSpec configurator)
- Same 4 slash commands as other tools
- Validation against Droid schema (if available)

**Validation**:
```bash
# Config generated
cat <droid-config-path> | jq '.commands.aurora'
# Should show: Aurora command configuration
```

---

**FR-3.6**: Configuration Validation and Testing
**Description**: Verify all tool configurations work end-to-end
**Acceptance Criteria**:
- Automated tests validate JSON schema for each tool
- Manual testing checklist for slash command execution:
  - Test `/aur:plan "test goal"` in each tool
  - Verify output streams to tool's chat interface
  - Confirm error messages display correctly
  - Validate argument parsing (quoted strings, flags)
- Documentation includes tool-specific setup instructions

**Validation**:
```bash
# Schema validation tests pass
pytest tests/integration/planning/test_configurators.py -v
# Should show: All configuration tests passing
```

---

### FR-4: Four-File Workflow and Validation

**FR-4.1**: Define JSON Schema for `agents.json`
**Description**: Create Pydantic model and JSON schema for machine-readable plan metadata
**Acceptance Criteria**:
- Pydantic model: `aurora.planning.schemas.AgentMetadata`
- Required fields:
  - `plan_id: str` - Format: `NNNN-slug`
  - `goal: str` - Original goal statement
  - `status: Literal["active", "archived"]`
  - `created_at: datetime` - ISO 8601 format
  - `updated_at: datetime` - ISO 8601 format
  - `subgoals: List[Subgoal]` - List of subgoal objects
- Optional fields:
  - `archived_at: Optional[datetime]` - Set when archived
  - `complexity: Optional[Literal["simple", "moderate", "complex"]]` - For Phase 2
- Subgoal schema:
  - `id: str` - Format: `sg-N` (e.g., `sg-1`, `sg-2`)
  - `title: str` - Brief description
  - `agent_id: Optional[str]` - Format: `@agent-name` (Phase 2)
  - `status: Literal["pending", "in_progress", "completed"]`
  - `tasks: List[str]` - Task IDs from tasks.md
- Validators:
  - Plan ID matches regex: `^\d{4}-[a-z0-9-]+$`
  - Timestamps are valid ISO 8601
  - Subgoal IDs are unique within plan
- JSON Schema export for external validation

**Validation**:
```python
# Model instantiation
from aurora.planning.schemas import AgentMetadata, Subgoal

metadata = AgentMetadata(
    plan_id="0001-test-plan",
    goal="Test goal",
    status="active",
    created_at=datetime.now(),
    updated_at=datetime.now(),
    subgoals=[
        Subgoal(id="sg-1", title="Subgoal 1", status="pending", tasks=[])
    ]
)

# Export to JSON
with open("agents.json", "w") as f:
    f.write(metadata.model_dump_json(indent=2))

# Validate against schema
import jsonschema
schema = AgentMetadata.model_json_schema()
jsonschema.validate(metadata.model_dump(), schema)
# Should not raise ValidationError
```

---

**FR-4.2**: Define Markdown Template for `plan.md`
**Description**: Create Jinja2 template for high-level plan decomposition
**Acceptance Criteria**:
- Template location: `aurora_planning/templates/plan.md.j2`
- Sections:
  1. **Goal** - Original goal statement
  2. **Subgoals** - Numbered list with descriptions
  3. **Dependencies** - Graph or list showing subgoal dependencies
  4. **Agent Assignments** - Table mapping subgoals to agents (Phase 2)
- Variables:
  - `{{ goal }}` - Goal string
  - `{{ plan_id }}` - Plan identifier
  - `{{ subgoals }}` - List of Subgoal objects
  - `{{ created_at }}` - Creation timestamp
- Template includes placeholder comments for Phase 2 SOAR output
- Example output provided in template comments

**Validation**:
```python
# Template renders without errors
from jinja2 import Template
from pathlib import Path

template_path = Path("packages/planning/src/aurora_planning/templates/plan.md.j2")
template = Template(template_path.read_text())

output = template.render(
    goal="Implement OAuth2 authentication",
    plan_id="0001-implement-oauth2-authentication",
    subgoals=[
        {"id": "sg-1", "title": "Research OAuth providers", "description": "..."},
        {"id": "sg-2", "title": "Implement backend", "description": "..."}
    ],
    created_at="2026-01-02T14:30:00Z"
)

# Output is valid markdown
assert "# Goal" in output
assert "## Subgoals" in output
```

---

**FR-4.3**: Define Markdown Template for `prd.md`
**Description**: Create template for detailed requirements in OpenSpec format
**Acceptance Criteria**:
- Template location: `aurora_planning/templates/prd.md.j2`
- Sections (from OpenSpec PRD format):
  1. **Executive Summary** - Problem, solution, value
  2. **Goals** - Primary and secondary objectives
  3. **User Stories** - "As a [user], I want to [action] so that [benefit]"
  4. **Functional Requirements** - FR-N.M format with acceptance criteria
  5. **Non-Goals** - Out of scope items
  6. **Testing Strategy** - Unit, integration, acceptance test plans
  7. **Success Metrics** - Measurable indicators
- Variables:
  - `{{ goal }}` - Goal statement
  - `{{ subgoals }}` - Subgoal list for requirement generation
- Phase 1: Template generates placeholder requirements
- Phase 2: Will populate from SOAR decomposition analysis

**Validation**:
```python
# Template renders with OpenSpec format
output = prd_template.render(goal="Add OAuth2", subgoals=[...])

# Contains all required sections
required_sections = [
    "# Executive Summary",
    "## Goals",
    "## User Stories",
    "## Functional Requirements",
    "## Non-Goals",
    "## Testing Strategy"
]
for section in required_sections:
    assert section in output
```

---

**FR-4.4**: Define Markdown Template for `tasks.md`
**Description**: Create checklist template for implementation tasks
**Acceptance Criteria**:
- Template location: `aurora_planning/templates/tasks.md.j2`
- Format: GitHub-flavored markdown checklist
- Structure:
  - Tasks grouped by subgoal
  - Each task: `- [ ] Task description`
  - Task IDs: `N.M` format (subgoal.task, e.g., `1.1`, `1.2`)
- Variables:
  - `{{ subgoals }}` - Subgoal list with task breakdowns
- Phase 1: Generic task descriptions (e.g., "Implement subgoal 1")
- Phase 2: Will include file paths from memory retrieval
- Checkbox state persisted in file for manual tracking

**Validation**:
```python
# Template renders checklist
output = tasks_template.render(subgoals=[
    {"id": "sg-1", "title": "Setup", "tasks": ["Task 1.1", "Task 1.2"]},
    {"id": "sg-2", "title": "Implementation", "tasks": ["Task 2.1"]}
])

# Contains checkboxes
assert "- [ ] Task 1.1" in output
assert "- [ ] Task 2.1" in output

# Grouped by subgoal
assert "## Subgoal 1: Setup" in output
```

---

**FR-4.5**: Implement File Generation Pipeline
**Description**: Orchestrate generation of all 4 files during `aur plan create`
**Acceptance Criteria**:
- Function: `generate_plan_files(goal: str, plan_id: str, output_dir: Path) -> PlanResult`
- Steps:
  1. Parse goal statement (extract keywords for template context)
  2. Generate subgoals (rule-based in Phase 1, SOAR in Phase 2)
  3. Render templates with context
  4. Write files atomically (temp files + rename for safety)
  5. Validate each file against schema/format
  6. Return result with file paths and any warnings
- Error handling:
  - Partial success: If 3/4 files succeed, return success=True with warnings
  - Critical failure: If `agents.json` fails, rollback all files
  - File conflicts: Overwrite with warning (shouldn't happen with unique IDs)

**Validation**:
```python
# Generate files
from aurora.planning.generator import generate_plan_files

result = generate_plan_files(
    goal="Implement OAuth2 authentication",
    plan_id="0001-implement-oauth2-authentication",
    output_dir=Path("~/.aurora/plans/active/0001-implement-oauth2-authentication")
)

assert result.success is True
assert result.plan_id == "0001-implement-oauth2-authentication"
assert len(result.files_created) == 4

# Files exist and are valid
for file in ["plan.md", "prd.md", "tasks.md", "agents.json"]:
    assert (output_dir / file).exists()
```

---

**FR-4.6**: Implement Validation Rules
**Description**: Validate generated files against schemas and format constraints
**Acceptance Criteria**:
- Validators location: `aurora_planning/validators/`
- Validation functions:
  - `validate_agents_json(file_path: Path) -> ValidationResult` - JSON schema validation
  - `validate_plan_md(file_path: Path) -> ValidationResult` - Markdown structure check
  - `validate_prd_md(file_path: Path) -> ValidationResult` - OpenSpec format compliance
  - `validate_tasks_md(file_path: Path) -> ValidationResult` - Checklist format verification
- ValidationResult includes:
  - `is_valid: bool`
  - `errors: List[str]` - Error messages with line numbers
  - `warnings: List[str]` - Non-critical issues
- Called during file generation and optionally during `aur plan view` (validation health check)

**Validation**:
```python
# Validate agents.json
from aurora.planning.validators import validate_agents_json

result = validate_agents_json(Path("agents.json"))

assert result.is_valid is True
assert len(result.errors) == 0

# Invalid file
invalid_result = validate_agents_json(Path("invalid_agents.json"))
assert invalid_result.is_valid is False
assert "plan_id" in invalid_result.errors[0]  # Missing required field
```

---

**FR-4.7**: Create Example Templates with Documentation
**Description**: Provide commented example outputs for each of the 4 files
**Acceptance Criteria**:
- Examples location: `aurora_planning/templates/examples/`
- Files:
  - `plan.md.example` - Annotated with section explanations
  - `prd.md.example` - Shows complete OpenSpec PRD structure
  - `tasks.md.example` - Demonstrates task grouping and checkbox syntax
  - `agents.json.example` - Includes inline JSON comments (via separate .md explanation)
- Each example includes:
  - Realistic content (not "lorem ipsum")
  - Inline comments explaining each section
  - References to relevant documentation
- Examples used in integration tests as fixtures

**Validation**:
```bash
# Examples exist
ls aurora_planning/templates/examples/
# Should show: 4 example files

# Examples are valid
pytest tests/integration/planning/test_example_validation.py
# Should pass: Examples validate against schemas
```

---

### FR-5: Documentation

**FR-5.1**: Create README with Quick Start
**Description**: Write comprehensive README for Aurora planning package
**Acceptance Criteria**:
- File: `packages/planning/README.md`
- Sections:
  1. **Overview** - What is Aurora planning, why use it
  2. **Installation** - `pip install aurora-actr[planning]`
  3. **Quick Start** - 5-minute workflow from init to archive
  4. **Commands Reference** - All `aur plan` commands with examples
  5. **Slash Commands** - How to use `/aur:plan` in each tool
  6. **Four-File Workflow** - Explanation of plan structure
  7. **FAQ** - Common issues and solutions
  8. **Contributing** - Link to contribution guidelines
- Code examples use realistic goals (not "foo", "bar")
- Screenshots or ASCII art for command output (optional)

**Validation**:
```bash
# README exists and renders
cat packages/planning/README.md | head -20
# Should show: Well-formatted markdown header

# Links are valid (check in Phase 2 when docs published)
```

---

**FR-5.2**: Generate API Reference from Docstrings
**Description**: Use Sphinx or mkdocs to generate API documentation
**Acceptance Criteria**:
- All public functions/classes have docstrings (Google style)
- Docstrings include:
  - One-line summary
  - Args with types and descriptions
  - Returns with type and description
  - Raises with exception types
  - Examples where appropriate
- Generated docs published to: `docs/api/planning/` (or ReadTheDocs)
- API reference includes:
  - `aurora.planning.commands` module
  - `aurora.planning.schemas` module
  - `aurora.planning.validators` module
  - `aurora.planning.configurators` module

**Validation**:
```bash
# Docstrings present
python -c "from aurora.planning.commands import create_plan; print(create_plan.__doc__)"
# Should show: Docstring with Args/Returns sections

# Docs build without errors
cd docs && make html
# Should succeed
```

---

**FR-5.3**: Write User Guide for Planning Workflows
**Description**: Create step-by-step guide covering common planning scenarios
**Acceptance Criteria**:
- File: `docs/guides/planning-user-guide.md`
- Sections:
  1. **Getting Started** - Installation and initialization
  2. **Creating Your First Plan** - Walkthrough with example goal
  3. **Managing Plans** - List, view, update workflows
  4. **Archiving Completed Plans** - Best practices for cleanup
  5. **Multi-Tool Setup** - Configuring slash commands for all tools
  6. **Troubleshooting** - Common errors and solutions
  7. **Advanced Topics** - Custom templates (Phase 2), validation rules
  8. **Integration with Aurora Memory** - How Phase 2 will enhance planning
- Real-world examples (OAuth, logging system, refactoring)
- Troubleshooting includes error codes with explanations

**Validation**:
```bash
# User guide exists
cat docs/guides/planning-user-guide.md | wc -l
# Should show: Substantial content (e.g., >500 lines)

# Cross-references are correct
grep -o '\[.*\](.*)' docs/guides/planning-user-guide.md
# Should show: Valid relative links
```

---

**FR-5.4**: Document Configuration Module
**Description**: Explain how slash command configuration works for each tool
**Acceptance Criteria**:
- File: `docs/guides/slash-command-configuration.md`
- Sections for each tool:
  - Claude Code configuration (JSON format, MCP server setup)
  - OpenCode configuration (format from OpenSpec)
  - AmpCode configuration (format from OpenSpec)
  - Droid configuration (format from OpenSpec)
- Each section includes:
  - Config file path
  - JSON schema explanation
  - Manual configuration steps (if auto-generation fails)
  - Validation commands
  - Troubleshooting tips

**Validation**:
```bash
# Configuration guide exists
cat docs/guides/slash-command-configuration.md | grep "## Claude Code"
# Should show: Claude Code configuration section
```

---

## 5. Non-Goals (Out of Scope)

### Deferred to Phase 2

- **SOAR-Powered Decomposition**: Phase 1 uses rule-based templates; Phase 2 integrates `SOAROrchestrator.decompose()`
- **Memory-Aware File Paths**: Phase 1 generates generic task descriptions; Phase 2 adds `MemoryRetriever` integration for file path resolution
- **Agent Recommendation**: Phase 1 leaves agent assignments empty; Phase 2 uses `AgentManifest` for capability scoring
- **Checkpoint Workflows**: Phase 1 has single-step plan creation; Phase 2 adds decomposition → review → expand workflow
- **Full Framework Initialization**: `aur init` for complete Aurora setup is Phase 2; Phase 1 only has `aur plan init`

### Deferred to Phase 3

- **Plan Execution**: `/aur:implement` command for automated task execution
- **Agent Orchestration**: SOAR spawning agent subprocesses per subgoal
- **Progress Tracking**: State management for in-progress plans
- **Checkpoint/Resume**: Pause and resume multi-day plan execution

### Removed from Scope

- **Real-Time UI**: Terminal output only; web dashboard is future work
- **Parallel Execution**: Sequential task processing only
- **Advanced Retry Logic**: Simple fail-and-block error handling
- **Plan Templates Library**: No pre-built plan templates for common patterns (future enhancement)

---

## 6. Design Considerations

### Architecture Principles

**1. Test-Then-Enhance Approach**
- Phase 1: Establish proven foundation (284 OpenSpec tests)
- Phase 2: Layer Aurora intelligence without breaking foundation
- Phase 3: Add execution capabilities incrementally

**2. Graceful Degradation**
- Partial failures return success with warnings (e.g., 3/4 files generated)
- Result types (`PlanResult`, `ListResult`, etc.) always include success flag and warnings list
- Commands never crash; structured errors returned for programmatic handling

**3. Extensibility Hooks**
- Template variables reserved for Phase 2 (e.g., `{{ memory_context }}`, `{{ soar_subgoals }}`)
- Schema fields marked as optional for future use (e.g., `complexity`, `agent_id`)
- Configuration module designed to support additional tools beyond initial 4

**4. Namespace Consistency**
- All imports use `aurora.planning` namespace (not `aurora_planning`)
- Cross-package imports reference `aurora.core`, `aurora.soar`, etc.
- No circular dependencies between Aurora packages

### Technology Stack

**Core Dependencies**:
- `pydantic>=2.0` - Data validation and JSON schema generation
- `python-slugify>=8.0` - Plan ID slug generation
- `jinja2>=3.1` - Template rendering for plan files
- `aurora-core>=0.2.0` - Shared utilities and configuration

**Optional Dependencies**:
- `pytest-benchmark` - Performance testing (development only)
- `sphinx` or `mkdocs` - Documentation generation

**Python Version**: 3.9+ (aligned with Aurora core compatibility)

### Directory Structure

```
packages/planning/
├── src/
│   └── aurora_planning/
│       ├── __init__.py              # Package exports
│       ├── commands/                # CLI command implementations
│       │   ├── __init__.py
│       │   ├── archive.py
│       │   ├── create.py
│       │   ├── init.py
│       │   ├── list.py
│       │   └── view.py
│       ├── parsers/                 # Markdown and metadata parsers
│       │   ├── __init__.py
│       │   ├── markdown.py
│       │   ├── requirements.py
│       │   └── metadata.py
│       ├── schemas/                 # Pydantic models and JSON schemas
│       │   ├── __init__.py
│       │   ├── plan.py              # Plan model
│       │   ├── spec.py              # Spec model (future)
│       │   └── validation.py        # Validation models
│       ├── templates/               # Jinja2 templates
│       │   ├── plan.md.j2
│       │   ├── prd.md.j2
│       │   ├── tasks.md.j2
│       │   └── examples/            # Example outputs
│       │       ├── plan.md.example
│       │       ├── prd.md.example
│       │       ├── tasks.md.example
│       │       └── agents.json.example
│       ├── validators/              # File validation logic
│       │   ├── __init__.py
│       │   ├── plan_validator.py
│       │   └── requirement_validator.py
│       ├── configurators/           # Slash command config generators
│       │   ├── __init__.py
│       │   ├── base.py              # Shared config logic
│       │   ├── claude_code.py
│       │   ├── opencode.py
│       │   ├── ampcode.py
│       │   └── droid.py
│       └── config.py                # Planning configuration
├── tests/
│   ├── unit/
│   │   └── planning/                # 284 migrated tests
│   │       ├── test_commands.py
│   │       ├── test_parsers.py
│   │       ├── test_schemas.py
│   │       ├── test_validators.py
│   │       └── test_configurators.py
│   ├── integration/
│   │   └── planning/
│   │       ├── test_cli_workflows.py
│   │       ├── test_file_generation.py
│   │       └── test_slash_commands.py
│   └── acceptance/
│       └── planning/
│           ├── test_e2e_planning.py
│           └── test_multi_tool_integration.py
├── pyproject.toml                   # Package metadata
└── README.md                        # Package documentation
```

### Integration Points with Existing Aurora Systems

**1. Aurora Core (`aurora.core`)**
- **Configuration**: Extend `~/.aurora/config.json` with planning settings
- **File Utilities**: Reuse atomic file operations and directory management
- **Logging**: Use Aurora's structured logging for command execution

**2. Aurora CLI (`aurora.cli`)**
- **Command Registration**: Add `plan` command group to main CLI
- **Argument Parsing**: Use consistent Click conventions for flags and options
- **Output Formatting**: Apply Aurora's table and JSON output formatters

**3. PRD 0016 Agent Discovery (Future - Phase 2)**
- **AgentManifest**: Import for capability scoring and gap detection
- **Agent Validation**: Verify agent IDs in `agents.json` against manifest

**4. SOAR Orchestrator (Future - Phase 2)**
- **Decomposition**: Call `SOAROrchestrator.decompose()` for subgoal generation
- **Complexity Assessment**: Use SOAR's complexity scoring for plan metadata

**5. Memory System (Future - Phase 2)**
- **Context Retrieval**: Query indexed codebase for relevant files
- **File Path Resolution**: Resolve task descriptions to actual file paths
- **`--context` Flag**: Load custom context files for plan generation

### Performance Considerations

**Aspirational Targets** (documented, not blocking):
- `aur plan init`: <100ms
- `aur plan create`: <5s (template rendering + file I/O)
- `aur plan list`: <500ms for 100 plans (manifest caching)
- `aur plan view`: <500ms (single plan load)
- `aur plan archive`: <1s (atomic directory move)

**Optimization Strategies**:
- Manifest caching: Load once per session, invalidate on writes
- Lazy template loading: Compile Jinja2 templates on first use
- Atomic operations: Use temp files + rename for crash safety
- Parallel config generation: Write tool configs concurrently (if no conflicts)

**Benchmarking**:
- Add `pytest-benchmark` tests for each command
- Run benchmarks in CI to detect performance regressions
- Document actual performance in README after implementation

---

## 7. Testing Strategy

### Test Coverage Targets

- **Overall Coverage**: ≥95% (aligned with Aurora core standards)
- **Critical Paths**: 100% coverage for file generation, validation, and archiving
- **Unit Tests**: 284 migrated from OpenSpec (REUSE existing)
- **Integration Tests**: ~20 new tests for CLI workflows
- **Acceptance Tests**: ~10 new tests for end-to-end scenarios

### Test Pyramid

**Unit Tests (284 from OpenSpec + gaps)**:
- Pydantic model validation (schemas)
- Template rendering (all 4 file types)
- Validators (JSON schema, markdown format)
- Configurators (each tool's config generation)
- Parsers (markdown, metadata extraction)
- Plan ID generation and slug creation
- Manifest CRUD operations

**Integration Tests (~20 new tests)**:
- `aur plan init` with various flags
- `aur plan create` → verify 4 files generated
- `aur plan list` filtering and sorting
- `aur plan view` with fuzzy matching
- `aur plan archive` atomicity and rollback
- Configuration file merging (don't overwrite existing)
- Error handling for missing directories, corrupt files

**Acceptance Tests (~10 new tests)**:
- E2E: Init → create → list → view → archive full workflow
- E2E: Create multiple plans, verify ID auto-increment
- E2E: Archive plan, verify it disappears from active list
- E2E: Corrupt a plan file, verify graceful degradation in `view`
- Multi-tool: Validate configs for all 4 tools (schema validation only, no live testing)

### Test Data and Fixtures

**Fixtures** (reuse from OpenSpec where possible):
- `tmp_planning_dir`: Temporary `.aurora/plans/` directory
- `sample_plan`: Complete plan with all 4 files
- `sample_manifest`: Manifest with 3 active, 2 archived plans
- `mock_templates`: Pre-rendered template outputs for fast testing

**Test Data**:
- Example goals: "Implement OAuth2", "Add logging system", "Refactor database layer"
- Valid/invalid `agents.json` files for schema validation
- Malformed markdown files for error handling tests

### Testing Tools

- `pytest`: Test runner with parallel execution
- `pytest-cov`: Coverage reporting
- `pytest-benchmark`: Performance benchmarking (optional)
- `pytest-mock`: Mocking file I/O where needed (prefer real files in temp dirs)
- `hypothesis`: Property-based testing for plan ID generation and slug creation
- `jsonschema`: Validate `agents.json` against JSON Schema

### TDD Workflow

**During Implementation**:
1. **Migrate OpenSpec Tests First**: Copy 284 tests to Aurora structure, update imports, verify all pass
2. **Identify Coverage Gaps**: Run coverage report, find uncovered code paths
3. **Write Gap Tests**: Add unit/integration tests ONLY for gaps (don't duplicate OpenSpec tests)
4. **Verify After Each Task**: Run `pytest` and observe real output (no simulation)
5. **Document Test Results**: Update task list with actual test counts and pass rates

**Shell Command Verification Example**:
```bash
# After implementing FR-2.2 (aur plan create)
aur plan create "Test OAuth implementation"
ls ~/.aurora/plans/active/
cat ~/.aurora/plans/active/0001-test-oauth-implementation/agents.json | jq '.'

# Verify tests pass
pytest tests/unit/planning/test_create_command.py -v
pytest tests/integration/planning/test_cli_workflows.py::test_create_plan_e2e -v
```

### Continuous Integration

**CI Pipeline Checks**:
1. **Linting**: `ruff check` (Aurora's linter)
2. **Type Checking**: `mypy --strict`
3. **Unit Tests**: `pytest tests/unit/planning/ -v --cov`
4. **Integration Tests**: `pytest tests/integration/planning/ -v`
5. **Acceptance Tests**: `pytest tests/acceptance/planning/ -v` (if applicable)
6. **Coverage Report**: Fail if <95%
7. **Performance Benchmarks**: Run and report (informational, non-blocking)

**Test Execution Time Targets**:
- Unit tests: <30s
- Integration tests: <60s
- Acceptance tests: <120s
- Total CI pipeline: <5 minutes

---

## 8. Migration Plan (OpenSpec → Aurora)

### Migration Phases

**Phase A: Preparation** (Before coding)
1. Audit OpenSpec test suite (`/tmp/openspec-source/aurora/tests/`)
   - Identify all 284 tests
   - Map tests to Aurora package structure
   - Document any OpenSpec-specific test utilities to migrate
2. Review OpenSpec configurator code (~100 lines)
   - Understand config generation for all 4 tools
   - Identify any external dependencies
3. Validate OpenSpec refactoring is complete
   - All 284 tests passing in `/tmp/openspec-source/`
   - Integration guide reviewed

**Phase B: Package Scaffolding**
1. Create `packages/planning/` directory structure (see FR-1.1)
2. Set up `pyproject.toml` with dependencies (see FR-1.4)
3. Configure namespace package mapping (`aurora.planning` → `aurora_planning`)
4. Create empty `__init__.py` files for all modules

**Phase C: Code Migration**
1. Copy OpenSpec source files to `aurora_planning/`
   - Commands: `archive.py`, `init.py`, `list.py`, `update.py`, `view.py`
   - Parsers: `markdown.py`, `requirements.py`, `metadata.py`
   - Schemas: `plan.py`, `spec.py`, `validation.py`
   - Templates: `plan.md.j2`, `prd.md.j2`, etc.
   - Validators: `plan_validator.py`, `requirement_validator.py`
   - Configurators: All 4 tool config generators
2. Update all imports: `from openspec` → `from aurora.planning`
3. Update directory paths: `openspec/` → `.aurora/plans/`
4. Update terminology: Preserve "plan" (already refactored in OpenSpec from "change")

**Phase D: Test Migration**
1. Copy 284 test files to `tests/unit/planning/` and `tests/integration/planning/`
2. Update test imports to `aurora.planning`
3. Update test fixtures for Aurora directory structure
4. Run tests, fix import errors and path mismatches
5. Verify all 284 tests pass

**Phase E: CLI Integration**
1. Implement `aur plan` command group in `aurora_cli/commands/plan.py`
2. Register command group in `aurora_cli/main.py`
3. Add planning configuration to `aurora_cli/config.py`
4. Test CLI commands manually (TDD verification step)

**Phase F: Configuration Module Integration**
1. Copy configurator code to `aurora_planning/configurators/`
2. Update config generation to use Aurora paths
3. Test config generation for all 4 tools (schema validation)
4. Write integration tests for config merging

**Phase G: Documentation**
1. Write README (FR-5.1)
2. Generate API reference (FR-5.2)
3. Write user guide (FR-5.3)
4. Write configuration guide (FR-5.4)

**Phase H: Validation and Release**
1. Run full test suite (284 + new tests)
2. Run coverage report (verify ≥95%)
3. Run type checking (`mypy --strict`)
4. Run linting (`ruff check`)
5. Performance benchmarking (informational)
6. Final manual testing of all commands
7. Update CHANGELOG.md
8. Tag release: `v0.2.0-planning-phase1`

### Migration Validation Checklist

- [ ] All 284 OpenSpec tests copied to Aurora structure
- [ ] All tests passing with `aurora.planning` imports
- [ ] No remaining `openspec` imports in codebase
- [ ] Directory structure uses `.aurora/plans/` (not `openspec/`)
- [ ] All 4 tool configurators working
- [ ] CLI commands registered and functional
- [ ] Documentation complete (README, API, user guide)
- [ ] Coverage ≥95%
- [ ] Type checking passes with `mypy --strict`
- [ ] Linting passes with `ruff check`

### Rollback Plan

**If migration fails**:
1. OpenSpec code remains intact at `/tmp/openspec-source/` (don't delete until Phase 1 complete)
2. Revert Aurora changes: `git checkout main packages/planning/`
3. Document failure reason and blockers
4. Re-plan migration strategy

**Partial Success**:
- If 280/284 tests pass, document failing tests and proceed (95% pass rate acceptable)
- If critical command fails (e.g., `create`), block release until fixed

---

## 9. Success Criteria

### Top 3 Critical Success Criteria (Must Pass)

**1. OpenSpec Integrated as Native `aurora.planning` Package**
- [ ] All 284 tests migrated to `tests/unit/planning/` and `tests/integration/planning/`
- [ ] Test pass rate: ≥280/284 (≥98.6%)
- [ ] All imports updated to `aurora.planning`
- [ ] Package installable via `pip install aurora-actr[planning]`
- [ ] No OpenSpec branding or references in code

**Validation**:
```bash
pytest tests/unit/planning/ tests/integration/planning/ -v | tail -1
# Should show: 284 passed (or ≥280 passed, ≤4 skipped/xfailed)

python -c "import aurora.planning; print(aurora.planning.__version__)"
# Should print: 0.2.0
```

---

**2. Planning Commands Work: `aur plan create/list/view/archive` with 4-File Output**
- [ ] `aur plan init` creates `.aurora/plans/active/` and `.aurora/plans/archive/`
- [ ] `aur plan create "goal"` generates plan with unique ID and 4 files
- [ ] `aur plan list` shows active plans with progress percentages
- [ ] `aur plan view <id>` displays plan dashboard
- [ ] `aur plan archive <id>` moves plan to archive with timestamp
- [ ] All commands return structured results (success flag, warnings, data)

**Validation**:
```bash
# E2E test
aur plan init
aur plan create "Implement OAuth2 authentication"
aur plan list
aur plan view 0001
aur plan archive 0001

# Verify 4 files
ls ~/.aurora/plans/active/0001-*/
# Should show: plan.md prd.md tasks.md agents.json

# Verify archive
ls ~/.aurora/plans/archive/$(date +%Y-%m-%d)-0001-*/
# Should show: Same 4 files with archived_at timestamp in agents.json
```

---

**3. Config Module Included: All Tool Configurators from OpenSpec**
- [ ] Configurator code migrated to `aurora_planning/configurators/`
- [ ] Config generation working for all 4 tools: Claude Code, OpenCode, AmpCode, Droid
- [ ] Configs validate against tool-specific schemas (if available)
- [ ] Slash commands defined: `/aur:plan`, `/aur:list`, `/aur:view`, `/aur:archive`
- [ ] Documentation explains configuration process for each tool

**Validation**:
```bash
# Configurators exist
ls packages/planning/src/aurora_planning/configurators/
# Should show: claude_code.py opencode.py ampcode.py droid.py base.py

# Import check
python -c "from aurora.planning.configurators import generate_claude_config; print('OK')"
# Should print: OK

# Schema validation tests pass
pytest tests/integration/planning/test_configurators.py -v
# Should show: All configuration tests passing
```

---

### Secondary Success Criteria (High Priority)

**4. Four-File Workflow with Valid Schemas**
- [ ] JSON schema defined for `agents.json` (Pydantic model)
- [ ] Jinja2 templates created for `plan.md`, `prd.md`, `tasks.md`
- [ ] Example files with documentation in `templates/examples/`
- [ ] Validation functions for all 4 file types
- [ ] Files generated during `aur plan create` pass validation

**Validation**:
```bash
# Schema export
python -c "from aurora.planning.schemas import AgentMetadata; import json; print(json.dumps(AgentMetadata.model_json_schema(), indent=2))" > schema.json
cat schema.json | jq '.required'
# Should show: ["plan_id", "goal", "status", "created_at", "updated_at", "subgoals"]

# Validation passes
pytest tests/unit/planning/test_validators.py -v
# Should show: All validation tests passing
```

---

**5. Documentation Complete**
- [ ] README with quick start and command reference
- [ ] API reference generated from docstrings
- [ ] User guide with workflows and troubleshooting
- [ ] Configuration guide for all 4 tools

**Validation**:
```bash
# Documentation files exist
ls packages/planning/README.md docs/guides/planning-user-guide.md docs/guides/slash-command-configuration.md
# Should show: All 3 files

# Docstrings present
python -c "from aurora.planning.commands import create_plan; assert create_plan.__doc__ is not None"
# Should not raise AssertionError
```

---

**6. Performance Targets Met (Aspirational)**
- [ ] `aur plan create` completes in <5s
- [ ] `aur plan list` completes in <500ms (for ≤100 plans)
- [ ] Benchmarks documented in README
- [ ] CI runs performance regression tests (informational)

**Validation**:
```bash
# Benchmark tests
pytest tests/unit/planning/test_performance.py --benchmark-only
# Should report: Timing results for each command
```

---

### Acceptance Gates

**Gate 1: Code Complete**
- All FR-1 through FR-5 implemented
- All functions have docstrings
- Type hints on all public APIs
- No `# TODO` or `# FIXME` comments in main branch

**Gate 2: Quality Assurance**
- 284 OpenSpec tests passing
- Integration tests passing
- Coverage ≥95%
- `mypy --strict` passes with 0 errors
- `ruff check` passes with 0 errors

**Gate 3: Documentation Complete**
- README reviewed and approved
- User guide tested by following steps
- Configuration guide validated for all 4 tools
- API reference builds without warnings

**Gate 4: Manual Verification**
- All commands tested manually on Linux
- Slash commands validated in at least 1 tool (Claude Code)
- Error messages reviewed for clarity
- Performance benchmarks recorded

**Final Gate: Stakeholder Approval**
- Demo presented showing E2E workflow
- Known issues documented in README
- Phase 2 integration plan reviewed
- Release tagged and published

---

## 10. Timeline and Sprint Estimate

### Sprint Breakdown

**Total Estimated Effort**: 1 sprint (2 weeks, assuming 1 developer full-time)

**Week 1: Migration and Core Commands**
- **Day 1-2**: OpenSpec migration (FR-1.1 through FR-1.5)
  - Copy code, update imports, adapt directory structure
  - Migrate 284 tests, fix import errors
  - Target: All 284 tests passing by end of Day 2
- **Day 3-4**: Core commands (FR-2.1 through FR-2.5)
  - Implement `init`, `create`, `list`, `view`, `archive`
  - CLI integration with Click
  - Integration tests for each command
- **Day 5**: Four-file workflow (FR-4.1 through FR-4.7)
  - Define schemas and templates
  - Implement file generation pipeline
  - Validation rules

**Week 2: Configuration, Testing, and Documentation**
- **Day 6-7**: Multi-tool configuration (FR-3.1 through FR-3.6)
  - Migrate configurator code
  - Generate configs for all 4 tools
  - Integration tests for config generation
- **Day 8**: Integration and acceptance testing
  - Write E2E tests
  - Manual testing of all commands
  - Performance benchmarking
- **Day 9**: Documentation (FR-5.1 through FR-5.4)
  - README with examples
  - User guide and configuration guide
  - API reference generation
- **Day 10**: Polish and release prep
  - Fix any remaining test failures
  - Address code review feedback
  - Tag release `v0.2.0-planning-phase1`

### Risk Mitigation

**High-Risk Items**:
1. **OpenSpec test migration complexity** (284 tests)
   - Mitigation: Allocate 2 full days, accept ≥280 passing (≥98.6%)
2. **Unknown config formats for OpenCode/AmpCode/Droid**
   - Mitigation: OpenSpec configurator already has this logic (~100 lines)
3. **Performance targets (<5s for `create`)**
   - Mitigation: Treat as aspirational, document actual performance

**Medium-Risk Items**:
1. **Template complexity for `prd.md`**
   - Mitigation: Use simplified template in Phase 1, enhance in Phase 2
2. **Validation schema completeness**
   - Mitigation: Start with required fields only, expand incrementally

**Buffer**:
- 2 days built into schedule for unexpected issues
- Can extend to 3 weeks if critical blockers arise

### Dependencies

**Blocking Dependencies**:
- OpenSpec refactoring Phase 0.5 must be complete (✓ Already done, 284 tests passing)

**Non-Blocking Dependencies**:
- PRD 0016 agent discovery (only needed for Phase 2 integration)
- SOAR orchestrator (only needed for Phase 2 decomposition)

### Milestones

**Milestone 1 (End of Day 2)**: OpenSpec Integrated
- 284 tests passing in Aurora structure
- All imports updated
- Package installable

**Milestone 2 (End of Day 5)**: Core Commands Working
- All 5 commands functional (`init`, `create`, `list`, `view`, `archive`)
- Four-file workflow generating valid output
- Integration tests passing

**Milestone 3 (End of Day 7)**: Multi-Tool Configuration Complete
- Configurators migrated
- Configs generated for all 4 tools
- Schema validation tests passing

**Milestone 4 (End of Day 10)**: Phase 1 Complete
- All acceptance criteria met
- Documentation published
- Release tagged: `v0.2.0-planning-phase1`

---

## 11. Open Questions

### Technical Questions

**Q1**: Do OpenCode, AmpCode, and Droid use the same slash command config format as Claude Code (MCP protocol)?
- **Answer Needed From**: OpenSpec configurator code review
- **Impact**: Configuration module design (FR-3.x)
- **Resolution Timeline**: During Phase B (Package Scaffolding)

**Q2**: Should `aur plan init` generate tool configs, or should that be a separate command?
- **Current Decision**: `aur plan init` only creates `.aurora/plans/` directory; tool config generation happens during package installation or via `aur init` (Phase 2)
- **Rationale**: Separation of concerns - planning initialization vs. framework initialization

**Q3**: What happens if a plan ID collision occurs (race condition with concurrent `create` commands)?
- **Current Decision**: Retry with next ID (increment and try again)
- **Better Solution**: Use lock file or atomic manifest updates (evaluate during implementation)

### Requirements Clarification

**Q4**: Should archived plans be searchable with `aur plan list --archived`?
- **Assumption**: Yes, with same filtering as active plans
- **Needs Confirmation**: User feedback during testing

**Q5**: Should `aur plan view` validate files and report corruption warnings?
- **Current Decision**: Yes, run validators and display warnings if files are invalid
- **Rationale**: Provides health check for plan integrity

**Q6**: Should templates support custom user-defined sections in Phase 1?
- **Current Decision**: No, fixed templates in Phase 1; customization in Phase 2
- **Rationale**: Reduces complexity, validates structure first

### Phase 2 Planning Questions

**Q7**: How should Phase 2 integrate SOAR decomposition without breaking Phase 1 templates?
- **Strategy**: Templates include placeholders like `{{ soar_subgoals }}` that are empty in Phase 1, populated in Phase 2
- **Migration Path**: No breaking changes to Phase 1 plans

**Q8**: Should Phase 2 support updating existing Phase 1 plans with memory-aware file paths?
- **Nice-to-Have**: `aur plan enhance <id>` command to retrofit old plans
- **Priority**: Medium (evaluate during Phase 2 planning)

---

## 12. Appendices

### Appendix A: JSON Schema for `agents.json`

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "required": ["plan_id", "goal", "status", "created_at", "updated_at", "subgoals"],
  "properties": {
    "plan_id": {
      "type": "string",
      "pattern": "^\\d{4}-[a-z0-9-]+$",
      "description": "Unique plan identifier (e.g., 0001-implement-oauth2-authentication)"
    },
    "goal": {
      "type": "string",
      "minLength": 1,
      "description": "Original goal statement"
    },
    "status": {
      "type": "string",
      "enum": ["active", "archived"],
      "description": "Current plan status"
    },
    "created_at": {
      "type": "string",
      "format": "date-time",
      "description": "ISO 8601 timestamp of plan creation"
    },
    "updated_at": {
      "type": "string",
      "format": "date-time",
      "description": "ISO 8601 timestamp of last modification"
    },
    "archived_at": {
      "type": "string",
      "format": "date-time",
      "description": "ISO 8601 timestamp of archival (null if active)"
    },
    "complexity": {
      "type": "string",
      "enum": ["simple", "moderate", "complex"],
      "description": "Plan complexity assessment (Phase 2)"
    },
    "subgoals": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["id", "title", "status", "tasks"],
        "properties": {
          "id": {
            "type": "string",
            "pattern": "^sg-\\d+$",
            "description": "Subgoal identifier (e.g., sg-1, sg-2)"
          },
          "title": {
            "type": "string",
            "minLength": 1,
            "description": "Brief subgoal description"
          },
          "agent_id": {
            "type": "string",
            "pattern": "^@[a-z0-9-]+$",
            "description": "Assigned agent (e.g., @full-stack-dev) - Phase 2"
          },
          "status": {
            "type": "string",
            "enum": ["pending", "in_progress", "completed"],
            "description": "Subgoal completion status"
          },
          "tasks": {
            "type": "array",
            "items": {
              "type": "string",
              "pattern": "^\\d+\\.\\d+$",
              "description": "Task IDs (e.g., 1.1, 1.2)"
            },
            "description": "List of task IDs belonging to this subgoal"
          }
        }
      },
      "description": "List of subgoals decomposing the main goal"
    }
  }
}
```

### Appendix B: Example `plan.md` Template

```markdown
# Plan: {{ goal }}

**Plan ID**: {{ plan_id }}
**Created**: {{ created_at }}
**Status**: {{ status }}

---

## Goal

{{ goal }}

---

## Subgoals

{% for subgoal in subgoals %}
### {{ loop.index }}. {{ subgoal.title }} ({{ subgoal.id }})

**Description**: {{ subgoal.description }}
**Agent**: {{ subgoal.agent_id or "TBD (Phase 2)" }}
**Status**: {{ subgoal.status }}
**Tasks**: {{ subgoal.tasks | length }} tasks

{% endfor %}

---

## Dependencies

{% if dependencies %}
{% for dep in dependencies %}
- Subgoal {{ dep.target }} depends on Subgoal {{ dep.source }}
{% endfor %}
{% else %}
No dependencies detected (subgoals can run in parallel).
{% endif %}

---

## Notes

- Phase 1: Subgoals generated from rule-based templates
- Phase 2: Will use SOAR orchestrator for intelligent decomposition
- Phase 3: Execution orchestration with agent delegation
```

### Appendix C: Example Commands Cheat Sheet

```bash
# Initialize planning
aur plan init

# Create a new plan
aur plan create "Implement OAuth2 authentication"
aur plan create "Add comprehensive logging system"

# List plans
aur plan list                    # Active plans only
aur plan list --archived         # Archived plans only
aur plan list --all              # Both active and archived

# View plan details
aur plan view 0001               # By plan ID
aur plan view oauth              # By partial slug (fuzzy match)
aur plan view 0001 --archived    # View archived plan

# Archive completed plan
aur plan archive 0001
aur plan archive oauth           # By partial slug

# Slash commands (in Claude Code, OpenCode, etc.)
/aur:plan "Add user registration"
/aur:list
/aur:view 0001
/aur:archive 0001
```

### Appendix D: Error Code Reference

| Code | Message | Resolution |
|------|---------|-----------|
| `PLANNING_NOT_INITIALIZED` | Planning directory not found | Run `aur plan init` |
| `PLANNING_INIT_FAILED` | Failed to initialize planning | Check directory permissions |
| `INVALID_GOAL` | Goal string is empty or invalid | Provide non-empty goal statement |
| `PLAN_NOT_FOUND` | Plan ID not found in active or archived plans | Run `aur plan list` to see available plans |
| `PLAN_ALREADY_ARCHIVED` | Plan is already in archive | No action needed |
| `ARCHIVE_CONFLICT` | Archive directory already exists | Manually rename conflicting archive |
| `MANIFEST_CORRUPT` | Plan manifest is corrupted | Run `aur plan init --force` to rebuild |
| `PLAN_CORRUPT` | Plan files are corrupted or missing | Inspect plan directory, restore from backup |
| `FILE_GENERATION_FAILED` | Failed to generate plan files | Check disk space and permissions |
| `VALIDATION_FAILED` | Plan files failed validation | Review validation errors in output |

### Appendix E: Phase 2 Integration Preview

**What Changes in Phase 2**:

1. **SOAR Decomposition**:
   - `aur plan create` calls `SOAROrchestrator.decompose(goal, context)`
   - Subgoals generated intelligently instead of from templates
   - Complexity assessment added to `agents.json`

2. **Memory Integration**:
   - `--context` flag loads files from memory index
   - Task descriptions include file paths resolved via `MemoryRetriever`
   - Example: `"Modify User model" → "Edit src/models/user.py lines 15-30"`

3. **Agent Recommendation**:
   - `AgentManifest` queried for capability matching
   - Agent IDs auto-populated in `agents.json`
   - Gap detection with fallback suggestions

4. **Checkpoint Workflow**:
   - `aur plan create` shows decomposition preview, asks to continue
   - User can abort before expensive PRD generation

**Migration Path**:
- Phase 1 plans remain valid
- Phase 2 adds optional fields to `agents.json` (backward compatible)
- Templates support both Phase 1 (empty variables) and Phase 2 (populated variables)

---

## Document History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-01-02 | Claude Code | Initial comprehensive PRD for Phase 1 Foundation |

---

**Next Steps**:
1. Review this PRD with stakeholders
2. Confirm OpenSpec refactoring is complete (validate 284 tests)
3. Begin Sprint: Start with OpenSpec migration (FR-1.x)
4. Daily standups to track progress against timeline

---

**END OF PRD**
