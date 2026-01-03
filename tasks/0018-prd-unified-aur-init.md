# PRD 0018: Unified `aur init` Command
## Product Requirements Document

**Version**: 1.0
**Date**: January 3, 2026
**Status**: Ready for Implementation
**Phase**: Phase 1.5 - Refinement (post Phase 1)
**Product**: AURORA CLI
**Dependencies**: Phase 1 completion (312 tests passing, 8-file planning workflow)
**Estimated Effort**: 1-2 days implementation

---

## TABLE OF CONTENTS

1. [Executive Summary](#1-executive-summary)
2. [Problem Statement](#2-problem-statement)
3. [Goals & Success Metrics](#3-goals--success-metrics)
4. [User Personas](#4-user-personas)
5. [User Stories](#5-user-stories)
6. [Functional Requirements](#6-functional-requirements)
7. [Non-Functional Requirements](#7-non-functional-requirements)
8. [Non-Goals (Out of Scope)](#8-non-goals-out-of-scope)
9. [Technical Architecture](#9-technical-architecture)
10. [Migration Plan](#10-migration-plan)
11. [Test Strategy](#11-test-strategy)
12. [Success Metrics](#12-success-metrics)
13. [Acceptance Criteria](#13-acceptance-criteria)

---

## 1. Executive Summary

**What**: Unify two separate init commands (`aur init` and `aur init-planning`) into a single, simplified `aur init` command with a clean 3-step flow.

**Why**: Current two-command setup confuses users about which command to run first. The split was initially designed for global config + API keys, but with functionality moving to slash commands, we can simplify to project-specific initialization only.

**How**: Merge both commands into one streamlined flow:
1. **Step 1**: Planning setup (git check + `.aurora/plans/` structure)
2. **Step 2**: Memory indexing (project-specific `./.aurora/memory.db`)
3. **Step 3**: AI tool templates (CLAUDE.md, OPENCODE.md, AGENTS.md, etc.)

**Key Changes**:
- **Remove API key prompts** (environment variables only)
- **Remove global config.json** (use defaults + env vars)
- **Project-specific everything** (memory, logs, cache, plans) except budget tracker
- **Global only**: `~/.aurora/budget_tracker.json` (track API spend across projects)
- **Git-aware initialization** (offers `git init` if missing)
- **Idempotent behavior** (safe to re-run)
- **Single `--config` flag** for tool configuration only

**Architecture Shift** (Option 2 - Minimal Global):
```
BEFORE (Global + Project):
~/.aurora/
├── config.json          ❌ Remove
├── memory.db            → Move to project
├── mcp.log              → Move to project
├── aurora.log           → Move to project
├── cache/               → Move to project
├── budget_tracker.json  ✅ Keep (only global file)
└── plans/               → Move to project

AFTER (Project-Specific):
~/.aurora/
└── budget_tracker.json  ← Only global file

project/
└── .aurora/
    ├── plans/active/
    ├── plans/archive/
    ├── memory.db
    ├── project.md
    ├── logs/
    │   ├── aurora.log
    │   └── mcp.log
    └── cache/
        └── agent_manifest.json
```

---

## 2. Problem Statement

### Current State (Pre Phase 1.5)

Users face confusion with **two separate init commands**:

1. **`aur init`** (packages/cli/src/aurora_cli/commands/init.py):
   - Creates `~/.aurora/config.json` (global)
   - Prompts for API keys (no longer needed)
   - Sets up global `~/.aurora/memory.db`
   - Offers to index current directory
   - **Problem**: Global memory.db doesn't work well for multi-project workflows

2. **`aur init-planning`** (packages/cli/src/aurora_cli/commands/init_planning.py):
   - Creates `.aurora/plans/` directories (project-specific)
   - Configures AI tool templates (CLAUDE.md, etc.)
   - 3-step interactive wizard
   - **Problem**: Doesn't set up memory indexing

### User Pain Points

1. **Unclear order**: "Do I run `aur init` first or `aur init-planning`?"
2. **Redundant prompts**: API key prompts are unnecessary (slash commands handle auth)
3. **Global memory confusion**: Global `~/.aurora/memory.db` mixes contexts across projects
4. **Split setup flow**: Users expect one command to "just set up everything"
5. **No git integration**: Neither command checks for git or offers to initialize

### Desired State (Post Phase 1.5)

**Single unified command**: `aur init`
- One command does everything project-specific
- Git-aware (checks for `.git/`, offers `git init`)
- Project-specific memory (`./.aurora/memory.db`)
- No API key prompts (environment variables only)
- Idempotent (safe to re-run)
- Clear 3-step flow with progress feedback

---

## 3. Goals & Success Metrics

### Primary Goals

1. **Simplify UX**: Reduce two commands to one with clear linear flow
2. **Project-specific setup**: All Aurora data lives in `./.aurora/` (not global)
3. **Git integration**: Detect and offer git initialization if missing
4. **Idempotent behavior**: Safe to re-run without destroying custom content
5. **No API prompts**: Remove all API key prompting (use env vars only)

### Success Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| **User comprehension** | 95% of users understand first init run | User testing feedback |
| **Setup success rate** | 98% successful init without errors | Telemetry/error logs |
| **Re-run safety** | 100% idempotent (no data loss on re-run) | Integration tests |
| **Time to first plan** | <2 minutes from `aur init` to `aur plan create` | User flow timing |
| **Git adoption** | 80% of users accept `git init` offer | Usage analytics |
| **Migration smoothness** | 100% of existing users migrate without manual intervention | Migration test suite |

### Non-Goals (See Section 8)

- Global configuration files (removing `~/.aurora/config.json`)
- Model selection (haiku/sonnet/opus) - deferred to future
- Automated migration from old two-command setup
- Multi-project workspace detection

---

## 4. User Personas

### Persona 1: New Aurora User (Emma)

**Background**:
- Software engineer trying Aurora for first time
- Familiar with CLIs (npm, git, cargo)
- Expects `init` command to "just work"

**Goals**:
- Quick setup without reading docs
- Clear feedback on what's happening
- Ability to start planning immediately

**Pain Points with Current System**:
- Confused about `aur init` vs `aur init-planning`
- Annoyed by API key prompt (already set in env)
- Doesn't understand why memory.db is global

**Success Criteria**:
- Runs `aur init` once, understands all steps
- Creates first plan within 2 minutes
- No need to re-run init or fix mistakes

---

### Persona 2: Multi-Project Developer (Marcus)

**Background**:
- Works on 5+ projects simultaneously
- Uses Aurora for different clients/repos
- Needs isolated project contexts

**Goals**:
- Per-project memory isolation
- Quick project switching
- No cross-contamination of indexed code

**Pain Points with Current System**:
- Global memory.db mixes all projects
- Can't easily clear memory for one project
- Re-indexing one project affects others

**Success Criteria**:
- Each project has its own `.aurora/memory.db`
- Can delete `.aurora/` to reset project
- `aur mem search` only searches current project

---

### Persona 3: Team Lead (Sarah)

**Background**:
- Setting up Aurora for team of 6 developers
- Needs reproducible setup process
- Wants to commit `.aurora/` templates to git

**Goals**:
- Consistent setup across team
- Documented initialization process
- Easy onboarding for new team members

**Pain Points with Current System**:
- Two-step init is hard to document
- Can't commit global config to repo
- New team members make setup mistakes

**Success Criteria**:
- Single command in README: `aur init`
- Can commit `.aurora/` templates (not memory.db)
- New team members succeed on first try

---

## 5. User Stories

### Story 1: First-Time Project Setup

**As a** new Aurora user
**I want to** run a single init command
**So that** my project is ready for planning without confusion

**Acceptance Criteria**:
- ✅ Running `aur init` creates all necessary directories
- ✅ Command shows clear progress through 3 steps
- ✅ Git initialization is offered if `.git/` missing
- ✅ Memory indexing completes without errors
- ✅ At least one AI tool template is created
- ✅ Success message shows next steps

**Testing**: Unit + Integration (full flow)

---

### Story 2: Re-Running Init (Idempotent Behavior)

**As a** developer who already ran `aur init`
**I want to** re-run the command without breaking my setup
**So that** I can safely update or extend my configuration

**Acceptance Criteria**:
- ✅ Shows status checkmarks for completed steps
- ✅ Asks which steps to re-do (interactive menu)
- ✅ Preserves custom content in tool templates
- ✅ Doesn't overwrite `.aurora/project.md` edits
- ✅ Offers to re-index memory (doesn't force)
- ✅ Updates tool templates within marker boundaries only

**Testing**: Integration (re-run scenarios)

---

### Story 3: Git-Aware Initialization

**As a** developer starting a new project
**I want** Aurora to detect if git is initialized
**So that** I can set up version control and planning together

**Acceptance Criteria**:
- ✅ Checks for `.git/` directory
- ✅ If missing, explains benefits and offers `git init`
- ✅ If user accepts, runs `git init` and continues
- ✅ If user declines, skips planning directories but continues to Steps 2-3
- ✅ Never blocks on git (always allows proceeding)

**Testing**: Unit (git detection) + Integration (user flow)

---

### Story 4: Project-Specific Memory

**As a** multi-project developer
**I want** each project to have its own memory database
**So that** my projects don't interfere with each other

**Acceptance Criteria**:
- ✅ Memory.db created at `./.aurora/memory.db` (not global)
- ✅ `aur mem index .` indexes to project-specific db
- ✅ `aur mem search` searches project-specific db
- ✅ Deleting `.aurora/` resets project completely
- ✅ No global config file created

**Testing**: Integration (multi-project simulation)

---

### Story 5: Tool Configuration Only (--config flag)

**As a** developer who already initialized planning
**I want to** reconfigure AI tools without re-running full init
**So that** I can quickly add/update tool templates

**Acceptance Criteria**:
- ✅ `aur init --config` runs Step 3 only (tool templates)
- ✅ Skips Steps 1-2 silently
- ✅ Errors if `.aurora/` doesn't exist ("Run `aur init` first")
- ✅ Interactive checkbox for tool selection
- ✅ Updates templates with marker preservation

**Testing**: Unit + Integration (flag behavior)

---

### Story 6: Memory Indexing Failure Recovery

**As a** developer with a corrupted file in my project
**I want** Aurora to handle indexing errors gracefully
**So that** I can choose to skip indexing and continue setup

**Acceptance Criteria**:
- ✅ Catches indexing errors (corrupted files, OOM, etc.)
- ✅ Shows error message with file path if identifiable
- ✅ Prompts: "Indexing failed. Skip and continue? (y/n)"
- ✅ If yes, proceeds to Step 3 and marks Step 2 incomplete
- ✅ If no, exits cleanly with error guidance
- ✅ Can re-run `aur init` to retry indexing later

**Testing**: Unit (error simulation) + Integration (failure paths)

---

## 6. Functional Requirements

### FR-1: Unified Command Structure

**Requirement**: Merge `aur init` and `aur init-planning` into single `aur init` command.

**Details**:
- Single entry point: `aur init [--config]`
- Linear 3-step flow (planning → memory → tools)
- Rich console output with step numbering
- Progress feedback for long-running operations

**Acceptance Criteria**:
- ✅ `aur init` command exists and executes
- ✅ `aur init-planning` command removed
- ✅ Help text describes all 3 steps
- ✅ Console shows "Step 1/3", "Step 2/3", "Step 3/3"

---

### FR-2: Step 1 - Planning Setup (Git + Directories)

**Requirement**: Check for git and create Aurora directory structure using existing OpenSpec functions.

**Implementation Note**: Directory creation and project.md template are **ALREADY IMPLEMENTED** in Phase 1 at `packages/cli/src/aurora_cli/commands/init_planning.py`. We are **REUSING** these existing functions, not creating new ones.

**Details**:

**2.1 Git Detection** (NEW - to be implemented):
- Check for `.git/` directory in project root
- If missing:
  ```
  Git repository not found.

  Benefits of using git with Aurora:
  - Version control for plans and generated files
  - Easy rollback of planning iterations
  - Collaboration with team members

  Initialize git repository? (Y/n)
  ```
- If user selects Yes: Run `git init`, show confirmation
- If user selects No: Show warning, skip planning directories, proceed to Step 2
- If `.git/` exists: Show checkmark, proceed

**2.2 Directory Structure Creation** (MODIFY EXISTING):
- **Function to modify**: `create_directory_structure()` from `init_planning.py` (lines 216-271)
- **Current Phase 1 structure**:
  ```
  .aurora/
  ├── plans/
  │   ├── active/
  │   └── archive/
  ├── config/
  │   └── tools/        # ← Remove this (unused)
  └── project.md
  ```
- **New unified structure** (Option 2 - Project-Specific):
  ```
  .aurora/
  ├── plans/
  │   ├── active/
  │   └── archive/
  ├── logs/             # ← New: project logs (aurora.log, mcp.log)
  ├── cache/            # ← New: project cache (agent_manifest.json)
  ├── memory.db         # ← New: project-specific memory (created by Step 2)
  └── project.md
  ```
- **Changes needed**:
  - Remove line 227: `(aurora_dir / "config" / "tools").mkdir(...)` (unused directory)
  - Add: `(aurora_dir / "logs").mkdir(parents=True, exist_ok=True)`
  - Add: `(aurora_dir / "cache").mkdir(parents=True, exist_ok=True)`
  - Keep existing `mkdir(parents=True, exist_ok=True)` - already idempotent
  - Keep existing project.md preservation (checks `if not project_md.exists()`)
  - memory.db is created by memory indexing (Step 2), not directory setup
- **Global directory** (ensure exists):
  - Create `~/.aurora/` only for `budget_tracker.json`
  - Use `Path.home().joinpath(".aurora").mkdir(exist_ok=True)`

**2.3 project.md Template** (REUSE EXISTING):
- **Template source**: Hardcoded in `create_directory_structure()` function (lines 232-270)
- **Existing template** includes:
  ```markdown
  # Project Overview

  <!-- Fill in details about your project -->

  ## Description
  [Brief description of your project]

  ## Tech Stack
  - **Language**: [e.g., Python 3.10]
  - **Framework**: [e.g., FastAPI, Django, Flask]
  - **Database**: [e.g., PostgreSQL, MongoDB]
  - **Tools**: [e.g., Docker, pytest, mypy]

  ## Conventions
  - **Code Style**: [e.g., Black, Ruff, PEP 8]
  - **Testing**: [e.g., pytest, 90% coverage target]
  - **Documentation**: [e.g., Google-style docstrings]
  - **Git**: [e.g., conventional commits, feature branches]

  ## Architecture
  [Brief overview of your system architecture]

  ## Key Directories
  - `src/` - [Description]
  - `tests/` - [Description]
  - `docs/` - [Description]

  ## Notes
  [Any additional context for AI assistants]
  ```

**Optional Enhancement** (can be added later):
- Auto-detect project name from git or directory name
- Scan for package.json, pyproject.toml to detect tech stack
- Pre-fill detected values with "detected" annotations

**Files to Reuse** (from Phase 1):
- `packages/cli/src/aurora_cli/commands/init_planning.py`:
  - `create_directory_structure(project_path)` function (lines 216-271)
  - Will be moved to helper module in unified implementation

**Acceptance Criteria**:
- ✅ Checks for `.git/` directory (NEW)
- ✅ Offers `git init` if missing with explanation (NEW)
- ✅ Creates `.aurora/plans/active/` and `.aurora/plans/archive/` (EXISTING)
- ✅ Creates `.aurora/config/tools/` (EXISTING)
- ✅ Creates `.aurora/project.md` with template (EXISTING)
- ✅ Skips project.md if already exists (EXISTING - already implemented)
- ✅ If git declined: Shows warning, skips planning dirs, continues to Step 2 (NEW)

---

### FR-3: Step 2 - Memory Indexing

**Requirement**: Index project codebase to project-specific memory database.

**Details**:

**3.1 Database Location**:
- Create at `./.aurora/memory.db` (project-specific, not global)
- Ensure `.aurora/` parent directory exists
- Create database if doesn't exist

**3.2 Indexing Scope**:
- Index entire project root (respects `.gitignore`)
- Scan for Python files (current limitation)
- Show progress bar during indexing
- Display stats on completion

**3.3 Progress Display**:
```
Step 2/3: Memory Indexing
Indexing project codebase...

[████████████████████░░] 85% (127/150 files)

✓ Indexed 150 files, 1,245 chunks in 3.42s
```

**3.4 Error Handling**:
- Catch indexing errors (corrupted files, encoding issues, OOM)
- Display error with file path if identifiable
- Prompt: "Indexing failed. Skip and continue? (y/n)"
- If skip: Mark Step 2 incomplete, proceed to Step 3
- If abort: Exit with guidance to fix and re-run

**3.5 Re-run Behavior**:
- If memory.db exists: Detect and ask "Re-index? (y/n)"
- If yes: Backup existing db (memory.db.backup), re-index
- If no: Skip to Step 3

**Acceptance Criteria**:
- ✅ Creates `./.aurora/memory.db` (not `~/.aurora/memory.db`)
- ✅ Indexes entire project root (respects .gitignore)
- ✅ Shows progress bar with file count
- ✅ Displays success stats (files, chunks, duration)
- ✅ Handles errors gracefully with skip option
- ✅ On re-run: Offers to re-index, backups existing db

---

### FR-4: Step 3 - AI Tool Configuration

**Requirement**: Use existing OpenSpec configurator system to create AI tool templates with interactive selection.

**Implementation Note**: This functionality is **ALREADY IMPLEMENTED** in Phase 1 at `packages/cli/src/aurora_cli/configurators/`. We are **REUSING** this existing module, not creating a new one.

**Details**:

**4.1 Tool Selection (Interactive)**:
- Uses existing `ToolRegistry` from `packages/cli/src/aurora_cli/configurators/registry.py`
- Show questionary checkbox prompt (already implemented)
- Options (all configurators already exist):
  - [ ] Claude Code → `configurators/claude.py` → creates CLAUDE.md
  - [ ] OpenCode → `configurators/opencode.py` → creates OPENCODE.md
  - [ ] AmpCode → `configurators/ampcode.py` → creates AMPCODE.md
  - [ ] Droid → `configurators/droid.py` → creates DROID.md
  - [x] Universal AGENTS.md → `configurators/agents.py` (always checked by default)
- Mark already-configured tools: "Claude Code (already configured)"
- Allow multi-select with space bar, confirm with enter

**4.2 Marker-Based Updates (Already Implemented)**:
- Uses existing `BaseConfigurator` from `packages/cli/src/aurora_cli/configurators/base.py`
- Markers: `<!-- AURORA:START -->` and `<!-- AURORA:END -->` (Phase 1 implementation)
- **Note**: PRD originally specified `<!-- AURORA:MANAGED:v1:START -->` but existing code uses `<!-- AURORA:START -->`. Keep existing markers for consistency.
- Preserve all content outside markers
- Replace content within markers with new template
- Example structure (already working):
  ```markdown
  # My Custom Content (preserved)

  <!-- AURORA:START -->
  # Aurora Planning System

  This section is managed by Aurora. Changes here will be overwritten.
  <!-- AURORA:END -->

  # More Custom Content (preserved)
  ```

**4.3 Template Content (Already Implemented)**:
Each configurator already creates templates with:
- Workflow instructions (how to use Aurora with that tool)
- Available commands (aur plan, aur agents, etc.)
- Example usage
- Link to `.aurora/project.md`
- Link to active plans directory

**4.4 Universal AGENTS.md (Already Implemented)**:
- Created by `configurators/agents.py`
- Contains agent registry for tools without native agent support
- Used by SOAR orchestrator for agent recommendations

**4.5 Detection of Existing Configuration (Already Implemented)**:
- Each configurator checks for `<!-- AURORA:START -->` marker
- `detect_configured_tools()` function already exists in `init_planning.py` (will be moved to helper)
- If found: Mark as "(already configured)" in checkbox
- On re-run: Pre-check configured tools

**Files to Reuse** (from Phase 1):
- `packages/cli/src/aurora_cli/configurators/__init__.py` - Exports ToolRegistry, TOOL_OPTIONS
- `packages/cli/src/aurora_cli/configurators/base.py` - BaseConfigurator class with marker handling
- `packages/cli/src/aurora_cli/configurators/registry.py` - ToolRegistry.get() for configurator lookup
- `packages/cli/src/aurora_cli/configurators/claude.py` - Claude Code configurator
- `packages/cli/src/aurora_cli/configurators/opencode.py` - OpenCode configurator
- `packages/cli/src/aurora_cli/configurators/ampcode.py` - AmpCode configurator
- `packages/cli/src/aurora_cli/configurators/droid.py` - Droid configurator
- `packages/cli/src/aurora_cli/configurators/agents.py` - Universal AGENTS.md configurator

**Acceptance Criteria**:
- ✅ Interactive checkbox with all tool options
- ✅ Universal AGENTS.md always created
- ✅ Detects already-configured tools and marks them
- ✅ Uses `<!-- AURORA:MANAGED:v1:START/END -->` markers
- ✅ Preserves custom content outside markers
- ✅ On re-run: Pre-checks existing tools, offers to update

---

### FR-5: Idempotent Re-Run Behavior

**Requirement**: `aur init` must be safe to run multiple times without data loss.

**Details**:

**5.1 Detection on Re-Run**:
When `.aurora/` already exists:
```
Aurora is already initialized in this project.

Setup Status:
  ✓ Step 1: Planning structure (2026-01-03)
  ✓ Step 2: Memory indexed (150 files, 1,245 chunks)
  ✓ Step 3: Tools configured (3 tools)

What would you like to do?
  1. Re-run all steps (will backup existing data)
  2. Re-run specific steps (choose which)
  3. Skip to tool configuration (--config flag)
  4. Exit (no changes)

Choice [1-4]:
```

**5.2 Selective Re-Run**:
If user chooses option 2:
```
Select steps to re-run:
  [ ] Step 1: Planning setup (recreate directories)
  [x] Step 2: Memory indexing (will backup existing)
  [ ] Step 3: Tool configuration (update templates)
```

**5.3 Safety Mechanisms**:
- Never delete user-created files without confirmation
- Backup memory.db before re-indexing (memory.db.backup)
- Preserve custom content in project.md
- Preserve custom content outside marker boundaries
- Show diff summary before overwriting templates

**Acceptance Criteria**:
- ✅ Detects existing `.aurora/` directory
- ✅ Shows setup status with checkmarks
- ✅ Offers re-run options (all, specific, config-only, exit)
- ✅ Backs up memory.db before re-indexing
- ✅ Never overwrites custom content
- ✅ Can run 10 times without errors or data loss

---

### FR-6: --config Flag (Tool Configuration Only)

**Requirement**: Provide fast path to reconfigure AI tools without full init.

**Details**:

**6.1 Behavior**:
```bash
$ aur init --config

Step 3/3: AI Tool Configuration
Select tools to configure...
```

**6.2 Prerequisites**:
- If `.aurora/` doesn't exist: Error + guidance
  ```
  Error: Aurora not initialized in this project.

  Run 'aur init' first to set up planning structure and memory indexing.
  ```
- If `.aurora/` exists: Skip directly to tool configuration step

**6.3 Use Cases**:
- Add new tool after initial setup
- Update existing tool templates
- Reconfigure tools without re-indexing

**Acceptance Criteria**:
- ✅ `aur init --config` skips Steps 1-2
- ✅ Runs Step 3 (tool configuration) only
- ✅ Errors if `.aurora/` doesn't exist with helpful message
- ✅ Uses same interactive checkbox UI as full init

---

### FR-7: Success Feedback & Next Steps

**Requirement**: Provide clear summary of what was created and what to do next.

**Details**:

**7.1 Success Message**:
```
✓ Aurora initialized successfully!

Summary:
  ✓ Step 1: Planning structure created
    - .aurora/plans/active/
    - .aurora/plans/archive/
    - .aurora/project.md (with auto-detected metadata)

  ✓ Step 2: Memory indexed
    - Indexed 150 files (1,245 chunks) in 3.42s
    - Database: ./.aurora/memory.db

  ✓ Step 3: Tools configured
    - Created: CLAUDE.md, AGENTS.md
    - Updated: (none)

Next Steps:
  1. Fill in project.md
     .aurora/project.md
     Add project-specific context for better AI assistance

  2. Create your first plan
     aur plan create "Your goal here"

  3. Search indexed code
     aur mem search "authentication"

  4. List plans
     aur plan list

For help: aur --help
```

**Acceptance Criteria**:
- ✅ Shows summary of all created files/directories
- ✅ Displays indexing stats (files, chunks, duration)
- ✅ Lists created vs updated tool configs
- ✅ Provides 4 concrete next steps with commands
- ✅ Consistent formatting with rich console output

---

### FR-8: Remove API Key Prompts

**Requirement**: Eliminate all API key prompting from init flow.

**Details**:

**8.1 Rationale**:
- API keys no longer needed in init (slash commands handle auth)
- Encourages environment variable usage (best practice)
- Simplifies init flow

**8.2 Environment Variable Guidance**:
- If API operations fail later: Show env var setup instructions
- Documentation update in CLI_USAGE_GUIDE.md
- Example:
  ```bash
  export ANTHROPIC_API_KEY=sk-ant-...
  export OPENAI_API_KEY=sk-...
  ```

**8.3 Removed Behaviors**:
- No prompt for API key during init
- No storage of API keys in config.json
- No validation of API key format

**Acceptance Criteria**:
- ✅ `aur init` never prompts for API key
- ✅ No API key stored in any config file
- ✅ Documentation updated with env var setup
- ✅ Error messages guide to env var setup if needed

---

## 7. Non-Functional Requirements

### NFR-1: Performance

**Requirement**: Init must complete quickly for typical projects.

**Targets**:
| Operation | Target | Measurement |
|-----------|--------|-------------|
| Planning setup (Step 1) | <500ms | Wall clock time |
| Memory indexing 100 files (Step 2) | <5s | Wall clock time |
| Tool configuration (Step 3) | <1s | Wall clock time |
| **Total init (100 files)** | **<7s** | End-to-end timing |

**Optimization Strategies**:
- Parallel file scanning during indexing
- Lazy loading of configurators
- Minimal I/O operations

**Acceptance Criteria**:
- ✅ Full init (100 files) completes in <7s on standard hardware
- ✅ No blocking operations during progress display
- ✅ Progress bar updates smoothly (>10 FPS)

---

### NFR-2: Reliability

**Requirement**: Init must be robust against failures.

**Targets**:
- **Success rate**: 98% of init runs succeed without errors
- **Partial failure handling**: 100% of partial failures offer recovery
- **Idempotent guarantee**: 100% data preservation on re-run

**Error Scenarios**:
1. **Disk full**: Catch and show clear error
2. **Permission denied**: Catch and show chmod guidance
3. **Corrupted file during indexing**: Skip file, continue, report
4. **Git not installed**: Don't offer `git init`, continue
5. **Interrupted init**: Safe to re-run, resumes where left off

**Acceptance Criteria**:
- ✅ All error scenarios tested with clear messages
- ✅ Partial failures don't leave broken state
- ✅ Can re-run after any failure without manual cleanup

---

### NFR-3: Usability

**Requirement**: Init must be intuitive for developers familiar with CLIs.

**Principles**:
- Clear progress indication (step numbers, progress bars)
- Sane defaults (Universal AGENTS.md always selected)
- Helpful error messages with next steps
- Consistent terminology (plans, memory, tools)

**Accessibility**:
- Works with screen readers (questionary support)
- Keyboard-only navigation (no mouse required)
- Color-blind friendly (uses symbols not just colors)

**Acceptance Criteria**:
- ✅ User testing shows 95% comprehension on first run
- ✅ All prompts have clear defaults
- ✅ Error messages tested with non-experts

---

### NFR-4: Maintainability

**Requirement**: Code must be easy to extend with new tools and features.

**Design Principles**:
- Configurator registry pattern (existing)
- Step functions clearly separated
- Marker-based template system
- Minimal coupling between steps

**Extension Points**:
- Add new tools via ToolRegistry
- Add new steps by extending main flow
- Customize templates via configurators

**Acceptance Criteria**:
- ✅ Adding new tool requires <50 lines of code
- ✅ Step functions have <100 lines each
- ✅ Test coverage >90% for init logic

---

## 8. Non-Goals (Out of Scope)

### NG-1: Global Configuration Files

**Not included**:
- No `~/.aurora/config.json` creation
- No global settings or preferences
- No cross-project configuration

**Rationale**:
- Aurora is now project-specific by design
- Environment variables handle global settings (API keys)
- Simplifies implementation and UX

**Future consideration**: May add global preferences in Phase 2 if needed

---

### NG-2: Model Selection (haiku/sonnet/opus)

**Not included**:
- No model selection prompts during init
- No per-project model preferences
- No cost optimization settings

**Rationale**:
- Not needed for Phase 1.5 scope
- Can be added later when cost tracking is more mature
- Default model (sonnet-4) works for most users

**Future consideration**: Add `aur config set model sonnet-4` command

---

### NG-3: Automated Migration

**Not included**:
- No automatic detection of old two-command setup
- No automated data migration from `~/.aurora/` to `./.aurora/`
- No migration wizard

**Rationale**:
- Manual migration is straightforward (documented)
- Small user base (Phase 1 just completed)
- 1-2 day effort not worth automation complexity

**Migration docs will cover**:
- How to move global memory.db to project-specific
- How to delete old global config
- How to re-initialize projects

---

### NG-4: Multi-Project Workspace Detection

**Not included**:
- No detection of monorepo/workspace structure
- No multi-project initialization
- No workspace-level configuration

**Rationale**:
- Out of scope for Phase 1.5
- Current per-project approach handles most cases
- Monorepo support can be added later

**Future consideration**: Add `aur init --workspace` for monorepos

---

### NG-5: Interactive Template Editing

**Not included**:
- No in-CLI editor for project.md
- No guided project setup wizard
- No template customization UI

**Rationale**:
- Users prefer their own editors
- Scope creep (init should be fast)
- Template files are already pre-filled with TODOs

**Alternative**: Link to external editor in success message

---

## 9. Technical Architecture

### 9.1 File Structure Changes

**Before (Phase 1)**:
```
packages/cli/src/aurora_cli/commands/
├── init.py                  # Global config + API keys
└── init_planning.py         # Tool configuration

~/.aurora/                   # Global
├── config.json
└── memory.db

.aurora/                     # Project-specific
├── plans/
└── project.md
```

**After (Phase 1.5)** - Option 2: Minimal Global:
```
packages/cli/src/aurora_cli/commands/
└── init.py                  # Unified init (all steps)
    # init_planning.py DELETED

~/.aurora/                   # Minimal global
└── budget_tracker.json      # Only global file

.aurora/                     # All project-specific
├── plans/
│   ├── active/
│   └── archive/
├── logs/
│   ├── aurora.log           # Moved from global
│   └── mcp.log              # Moved from global
├── cache/
│   └── agent_manifest.json  # Moved from global
├── memory.db                # Moved from global
└── project.md
```

---

### 9.1.1 Config.py Path Changes

**File**: `packages/cli/src/aurora_cli/config.py`

**Current defaults** (global paths):
```python
logging_file: str = "~/.aurora/aurora.log"
mcp_log_file: str = "~/.aurora/mcp.log"
db_path: str = "~/.aurora/memory.db"
budget_tracker_path: str = "~/.aurora/budget_tracker.json"
agents_manifest_path: str = "~/.aurora/cache/agent_manifest.json"
planning_base_dir: str = "~/.aurora/plans"
```

**New defaults** (project-specific paths):
```python
logging_file: str = "./.aurora/logs/aurora.log"           # ← Changed
mcp_log_file: str = "./.aurora/logs/mcp.log"             # ← Changed
db_path: str = "./.aurora/memory.db"                      # ← Changed
budget_tracker_path: str = "~/.aurora/budget_tracker.json"  # ← Keep global
agents_manifest_path: str = "./.aurora/cache/agent_manifest.json"  # ← Changed
planning_base_dir: str = "./.aurora/plans"                # ← Changed
```

**Why these paths?**
- **Budget tracker**: Global to track API spend across all projects
- **Everything else**: Project-specific for isolation and easy backup

---

### 9.2 Command Flow

```
aur init [--config]
    ↓
main.py registers init_command()
    ↓
init_command(config: bool)
    ↓
    ├─→ if config flag:
    │      ├─ Check .aurora/ exists (error if not)
    │      └─ run_step_3_tool_configuration()
    │
    └─→ else (full init):
           ├─ detect_existing_setup()
           │     ↓
           ├─ if existing:
           │     ├─ show_status_summary()
           │     └─ prompt_rerun_options()
           │           ↓
           ├─ run_step_1_planning_setup()
           │     ├─ check_git()
           │     ├─ offer_git_init()
           │     ├─ create_directories()
           │     └─ create_project_md()
           │           ↓
           ├─ run_step_2_memory_indexing()
           │     ├─ create_memory_db()
           │     ├─ index_project()
           │     ├─ show_progress()
           │     └─ handle_errors()
           │           ↓
           ├─ run_step_3_tool_configuration()
           │     ├─ detect_configured_tools()
           │     ├─ prompt_tool_selection()
           │     ├─ configure_tools()
           │     └─ update_with_markers()
           │           ↓
           └─ display_success_summary()
```

---

### 9.3 Key Components

**Component 1: init.py (New Unified Implementation)**

```python
# packages/cli/src/aurora_cli/commands/init.py

@click.command(name="init")
@click.option("--config", is_flag=True, help="Configure AI tools only")
@handle_errors
def init_command(config: bool) -> None:
    """Initialize Aurora for current project."""
    project_path = Path.cwd()

    # Fast path for --config
    if config:
        if not (project_path / ".aurora").exists():
            console.print("[red]Error: Aurora not initialized.[/]")
            console.print("Run 'aur init' first.")
            raise click.Abort()
        run_step_3_tool_configuration(project_path)
        return

    # Full init flow
    existing = detect_existing_setup(project_path)

    if existing:
        choice = prompt_rerun_options(project_path)
        if choice == "exit":
            return
        # Handle selective re-run based on choice

    # Step 1: Planning setup
    git_initialized = run_step_1_planning_setup(project_path)

    # Step 2: Memory indexing
    run_step_2_memory_indexing(project_path)

    # Step 3: Tool configuration
    run_step_3_tool_configuration(project_path)

    # Success summary
    display_success_summary(project_path)
```

**Component 2: Step Functions**

Each step is a separate function for testability:

```python
def run_step_1_planning_setup(project_path: Path) -> bool:
    """Step 1: Planning setup (git + directories).

    Returns:
        True if git was initialized, False otherwise
    """
    console.print("[bold]Step 1/3: Planning Setup[/]")

    # Git detection
    git_dir = project_path / ".git"
    if not git_dir.exists():
        if prompt_git_init():
            subprocess.run(["git", "init"], cwd=project_path)
            console.print("[green]✓[/] Git initialized")
        else:
            console.print("[yellow]⚠[/] Skipping planning directories")
            return False

    # Create directories
    aurora_dir = project_path / ".aurora"
    (aurora_dir / "plans" / "active").mkdir(parents=True, exist_ok=True)
    (aurora_dir / "plans" / "archive").mkdir(parents=True, exist_ok=True)

    # Create project.md
    create_project_md(project_path)

    console.print("[green]✓[/] Planning structure created")
    return True


def run_step_2_memory_indexing(project_path: Path) -> None:
    """Step 2: Memory indexing."""
    console.print("[bold]Step 2/3: Memory Indexing[/]")

    db_path = project_path / ".aurora" / "memory.db"

    # Check for existing db
    if db_path.exists():
        if not click.confirm("Memory already indexed. Re-index?", default=False):
            console.print("[dim]Skipping memory indexing[/]")
            return
        # Backup existing
        shutil.copy(db_path, db_path.with_suffix(".db.backup"))

    # Index with progress bar
    try:
        from aurora_cli.memory_manager import MemoryManager
        from aurora_cli.config import Config

        config = Config(database={"path": str(db_path)})
        manager = MemoryManager(config=config)

        with create_progress_bar() as progress:
            stats = manager.index_path(project_path, progress_callback=...)

        console.print(f"[green]✓[/] Indexed {stats.files_indexed} files, "
                     f"{stats.chunks_created} chunks in {stats.duration_seconds:.2f}s")

    except Exception as e:
        console.print(f"[red]Indexing failed: {e}[/]")
        if click.confirm("Skip and continue?", default=True):
            console.print("[yellow]⚠[/] Skipped memory indexing")
            return
        raise


def run_step_3_tool_configuration(project_path: Path) -> tuple[list[str], list[str]]:
    """Step 3: Tool configuration.

    Returns:
        Tuple of (created tools, updated tools)
    """
    console.print("[bold]Step 3/3: AI Tool Configuration[/]")

    # Detect existing configuration
    configured = detect_configured_tools(project_path)

    # Interactive selection (reuse from init_planning.py)
    selected = asyncio.run(prompt_tool_selection(configured))

    # Configure tools (reuse from init_planning.py)
    created, updated = asyncio.run(configure_tools(project_path, selected))

    console.print(f"[green]✓[/] Configured {len(created)} tool(s)")
    return created, updated
```

**Component 3: Helper Functions**

```python
def detect_existing_setup(project_path: Path) -> bool:
    """Detect if .aurora/ exists."""
    return (project_path / ".aurora").exists()


def show_status_summary(project_path: Path) -> None:
    """Show current setup status."""
    aurora_dir = project_path / ".aurora"

    console.print("\nAurora is already initialized.\n")
    console.print("[bold]Setup Status:[/]")

    # Step 1
    plans_active = (aurora_dir / "plans" / "active").exists()
    console.print(f"  {'✓' if plans_active else '✗'} Step 1: Planning structure")

    # Step 2
    memory_db = aurora_dir / "memory.db"
    if memory_db.exists():
        # Count chunks
        console.print(f"  ✓ Step 2: Memory indexed (... chunks)")
    else:
        console.print(f"  ✗ Step 2: Memory indexing")

    # Step 3
    tools = count_configured_tools(project_path)
    console.print(f"  {'✓' if tools > 0 else '✗'} Step 3: Tools configured ({tools} tools)")


def prompt_rerun_options(project_path: Path) -> str:
    """Prompt user for re-run options.

    Returns:
        One of: "all", "selective", "config", "exit"
    """
    console.print("\n[bold]What would you like to do?[/]")
    console.print("  1. Re-run all steps")
    console.print("  2. Re-run specific steps")
    console.print("  3. Skip to tool configuration")
    console.print("  4. Exit (no changes)")

    choice = click.prompt("Choice", type=int, default=4)
    return ["all", "selective", "config", "exit"][choice - 1]


def create_project_md(project_path: Path) -> None:
    """Create project.md with auto-detected metadata."""
    project_md = project_path / ".aurora" / "project.md"

    if project_md.exists():
        return  # Don't overwrite

    # Detect metadata
    metadata = detect_project_metadata(project_path)

    template = f"""# Project Overview: {metadata['name']}

<!-- Auto-detected by Aurora on {metadata['date']} -->

## Description

[TODO: Add project description]

## Tech Stack

{metadata['tech_stack']}

## Conventions

[TODO: Add code style, testing, documentation conventions]

## Architecture

[TODO: Brief system architecture overview]

## Notes

[TODO: Additional context for AI assistants]
"""

    project_md.write_text(template, encoding="utf-8")


def detect_project_metadata(project_path: Path) -> dict:
    """Auto-detect project metadata.

    Returns:
        Dictionary with keys: name, date, tech_stack
    """
    metadata = {
        "name": project_path.name,
        "date": datetime.now().strftime("%Y-%m-%d"),
        "tech_stack": "",
    }

    # Detect Python
    if (project_path / "pyproject.toml").exists():
        pyproject = toml.load(project_path / "pyproject.toml")
        python_version = pyproject.get("tool", {}).get("poetry", {}).get("dependencies", {}).get("python")
        metadata["tech_stack"] += f"- **Language**: Python {python_version or '3.x'} (detected)\n"
        metadata["tech_stack"] += f"- **Package Manager**: poetry (detected)\n"

    # Detect testing
    if (project_path / "pytest.ini").exists() or "pytest" in str(project_path / "pyproject.toml"):
        metadata["tech_stack"] += f"- **Testing**: pytest (detected)\n"

    # Detect JavaScript
    if (project_path / "package.json").exists():
        package = json.load((project_path / "package.json").open())
        metadata["tech_stack"] += f"- **Runtime**: Node.js (detected)\n"
        metadata["tech_stack"] += f"- **Package Manager**: {detect_js_pm(project_path)}\n"

    return metadata
```

---

### 9.4 Memory Manager Integration

**Key Change**: Memory manager must support project-specific databases.

**Before (Phase 1)**:
```python
# Fixed global path
db_path = Path.home() / ".aurora" / "memory.db"
```

**After (Phase 1.5)**:
```python
# Project-specific path
db_path = Path.cwd() / ".aurora" / "memory.db"

# Or from config
config = Config(database={"path": str(db_path)})
manager = MemoryManager(config=config)
```

**Changes Needed**:
1. Update `MemoryManager` to accept db_path in constructor
2. Update `aur mem` commands to use project-specific db
3. Update `aur query` to use project-specific db

---

### 9.5 Marker System (Template Updates)

**Marker Format**: `<!-- AURORA:MANAGED:v1:START -->` ... `<!-- AURORA:MANAGED:v1:END -->`

**Why v1?**: Version markers allow future template schema changes.

**Update Algorithm**:
```python
def update_template_with_markers(
    file_path: Path,
    new_content: str,
    marker_start: str = "<!-- AURORA:MANAGED:v1:START -->",
    marker_end: str = "<!-- AURORA:MANAGED:v1:END -->",
) -> None:
    """Update file content within marker boundaries.

    Preserves all content outside markers.
    Creates markers if they don't exist (first-time setup).
    """
    if not file_path.exists():
        # First-time creation
        full_content = f"{marker_start}\n{new_content}\n{marker_end}\n"
        file_path.write_text(full_content, encoding="utf-8")
        return

    # Read existing content
    existing = file_path.read_text(encoding="utf-8")

    # Check for markers
    if marker_start not in existing:
        # No markers - append managed section
        full_content = f"{existing}\n\n{marker_start}\n{new_content}\n{marker_end}\n"
        file_path.write_text(full_content, encoding="utf-8")
        return

    # Markers exist - replace content between them
    start_idx = existing.index(marker_start)
    end_idx = existing.index(marker_end) + len(marker_end)

    before = existing[:start_idx]
    after = existing[end_idx:]

    updated = f"{before}{marker_start}\n{new_content}\n{marker_end}{after}"
    file_path.write_text(updated, encoding="utf-8")
```

**Edge Cases**:
1. **Multiple marker pairs**: Only update first pair (warn user)
2. **Malformed markers**: Error with clear message
3. **User-added markers**: Unique v1 version avoids conflicts

---

## 10. Migration Plan

### 10.1 Migration Strategy: Manual with Documentation

**Decision**: No automated migration (see NG-3).

**Rationale**:
- Small user base (Phase 1 just completed ~1 week ago)
- Simple manual steps (copy 1 file, run 1 command)
- Estimated 10-20 users maximum affected
- Implementation time saved: 4-6 hours

---

### 10.2 Migration Steps (for Users)

**Document in CLI_USAGE_GUIDE.md**:

```markdown
## Migrating from Phase 1 (Two-Command Setup)

If you initialized Aurora before Phase 1.5, follow these steps:

### Step 1: Backup Global Memory (Optional)

```bash
# Backup your global memory database
cp ~/.aurora/memory.db ~/.aurora/memory.db.backup
```

### Step 2: Re-Initialize Projects

For each project that used Aurora:

```bash
cd /path/to/project

# Remove old .aurora structure (if exists)
rm -rf .aurora/

# Run new unified init
aur init
```

### Step 3: Clean Up Global Files (Optional - Keep Budget Tracker)

```bash
# Option 2: Keep only budget tracker (recommended)
cd ~/.aurora/
rm -f config.json memory.db mcp.log  # Remove old global files
rm -rf cache/ plans/                  # Remove old global directories
# Keep budget_tracker.json (tracks API spend across projects)

# OR: Complete cleanup (lose budget tracking history)
rm -rf ~/.aurora/
```

### Step 4: Verify

```bash
# Check project-specific memory
aur mem search "test"

# Create a test plan
aur plan create "Test plan"
aur plan list
```

**Note**: Your old plans and memory are preserved in the backup.
```

---

### 10.3 Breaking Changes Communication

**Release Notes (v0.3.0)**:

```markdown
# Aurora v0.3.0 - Unified Init (Phase 1.5)

## Breaking Changes

⚠️ **Two-command initialization removed**:
- `aur init` is now a unified command (planning + memory + tools)
- `aur init-planning` command removed (use `aur init --config` instead)

⚠️ **Memory database moved**:
- Old: `~/.aurora/memory.db` (global)
- New: `./.aurora/memory.db` (project-specific)
- Projects are now isolated (better multi-project workflows)

⚠️ **Global config removed**:
- `~/.aurora/config.json` no longer created
- API keys via environment variables only
- Set: `export ANTHROPIC_API_KEY=sk-ant-...`

## Migration Required

See docs/cli/CLI_USAGE_GUIDE.md#migrating-from-phase-1 for steps.

**TL;DR**: Delete old `.aurora/`, run `aur init` in each project.

## New Features

✨ Git-aware initialization (offers `git init`)
✨ Project-specific memory (multi-project isolation)
✨ Idempotent re-run (safe to run multiple times)
✨ Auto-detected project metadata in project.md
✨ Faster tool configuration with `aur init --config`

## Upgrade Path

```bash
# For each project
cd /path/to/project
rm -rf .aurora/
aur init

# Clean up global config (optional)
rm -rf ~/.aurora/
```
```

---

### 10.4 Backwards Compatibility

**None provided** (breaking release).

**Justification**:
- Early in product lifecycle (Phase 1 just completed)
- Small user base (<20 users estimated)
- Clean break simplifies codebase
- Old system fundamentally incompatible (global vs project-specific)

---

## 11. Test Strategy

### 11.1 Unit Tests

**Test File**: `tests/unit/cli/test_init_unified.py`

**Coverage**:
- ✅ Git detection (`test_detect_git_repository`)
- ✅ Directory creation (`test_create_directory_structure`)
- ✅ project.md generation (`test_create_project_md`)
- ✅ Metadata detection (`test_detect_project_metadata`)
- ✅ Existing setup detection (`test_detect_existing_setup`)
- ✅ Re-run options prompt (`test_prompt_rerun_options`)
- ✅ Tool selection (`test_prompt_tool_selection`)
- ✅ Marker-based updates (`test_update_template_with_markers`)
- ✅ --config flag behavior (`test_config_flag_without_aurora`)

**Example Tests**:

```python
def test_detect_git_repository(tmp_path):
    """Test git detection in project."""
    # No git
    assert not detect_git_repository(tmp_path)

    # With git
    (tmp_path / ".git").mkdir()
    assert detect_git_repository(tmp_path)


def test_create_project_md_with_metadata(tmp_path):
    """Test project.md creation with auto-detected metadata."""
    # Setup Python project
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text("[tool.poetry.dependencies]\npython = \"^3.10\"")

    create_project_md(tmp_path)

    project_md = tmp_path / ".aurora" / "project.md"
    content = project_md.read_text()

    assert "Python 3.10" in content
    assert "poetry" in content


def test_update_template_with_markers(tmp_path):
    """Test marker-based template update preserves custom content."""
    file_path = tmp_path / "CLAUDE.md"

    # Initial custom content
    file_path.write_text("# My Custom Section\n\nCustom notes here.\n")

    # First update (adds markers)
    update_template_with_markers(file_path, "# Aurora Content\n\nManaged section.")

    content = file_path.read_text()
    assert "My Custom Section" in content
    assert "Aurora Content" in content
    assert "<!-- AURORA:MANAGED:v1:START -->" in content

    # Second update (replaces within markers)
    update_template_with_markers(file_path, "# Updated Aurora Content")

    content = file_path.read_text()
    assert "My Custom Section" in content  # Preserved
    assert "Updated Aurora Content" in content
    assert "Aurora Content" not in content  # Replaced
```

---

### 11.2 Integration Tests

**Test File**: `tests/integration/cli/test_init_flow.py`

**Scenarios**:

**Scenario 1: First-Time Init (Full Flow)**
```python
@pytest.mark.integration
def test_first_time_init_full_flow(runner, tmp_project):
    """Test complete first-time init flow."""
    result = runner.invoke(cli, ["init"], input="y\ny\n")  # Git init, tools

    assert result.exit_code == 0
    assert ".aurora/plans/active" in result.output
    assert "Step 1/3" in result.output
    assert "Step 2/3" in result.output
    assert "Step 3/3" in result.output

    # Verify structure
    aurora_dir = tmp_project / ".aurora"
    assert (aurora_dir / "plans" / "active").exists()
    assert (aurora_dir / "plans" / "archive").exists()
    assert (aurora_dir / "project.md").exists()
    assert (aurora_dir / "memory.db").exists()
```

**Scenario 2: Re-Run (Idempotent)**
```python
@pytest.mark.integration
def test_rerun_init_idempotent(runner, initialized_project):
    """Test re-running init is safe."""
    # Run init first time
    result1 = runner.invoke(cli, ["init"], input="y\ny\n")
    assert result1.exit_code == 0

    # Run again
    result2 = runner.invoke(cli, ["init"], input="4\n")  # Exit option
    assert result2.exit_code == 0
    assert "already initialized" in result2.output

    # Verify no data loss
    project_md = initialized_project / ".aurora" / "project.md"
    assert project_md.exists()
```

**Scenario 3: No Git (Skip Planning)**
```python
@pytest.mark.integration
def test_init_without_git_skips_planning(runner, tmp_project):
    """Test init skips planning directories if git declined."""
    result = runner.invoke(cli, ["init"], input="n\ny\n")  # No git, yes tools

    assert result.exit_code == 0
    assert "Skipping planning directories" in result.output

    # Memory and tools still created
    assert (tmp_project / ".aurora" / "memory.db").exists()

    # Planning directories NOT created
    assert not (tmp_project / ".aurora" / "plans").exists()
```

**Scenario 4: --config Flag**
```python
@pytest.mark.integration
def test_config_flag_only_runs_step_3(runner, initialized_project):
    """Test --config flag skips to tool configuration."""
    result = runner.invoke(cli, ["init", "--config"], input="y\n")

    assert result.exit_code == 0
    assert "Step 3/3" in result.output
    assert "Step 1/3" not in result.output
    assert "Step 2/3" not in result.output
```

**Scenario 5: Indexing Failure Recovery**
```python
@pytest.mark.integration
def test_indexing_failure_recovery(runner, tmp_project, monkeypatch):
    """Test graceful handling of indexing errors."""
    def mock_index_error(*args, **kwargs):
        raise RuntimeError("Corrupted file")

    monkeypatch.setattr("aurora_cli.memory_manager.MemoryManager.index_path", mock_index_error)

    result = runner.invoke(cli, ["init"], input="y\ny\n")  # Git, skip on error

    assert result.exit_code == 0
    assert "Indexing failed" in result.output
    assert "Skipped memory indexing" in result.output
```

---

### 11.3 Acceptance Tests

**Manual Testing Checklist**:

**Test 1: First-Time User Flow**
```
[ ] Fresh project directory
[ ] Run: aur init
[ ] Accept git init
[ ] Wait for memory indexing progress bar
[ ] Select 2 tools (Claude Code + Universal)
[ ] Verify success message
[ ] Run: aur plan create "Test"
[ ] Verify plan created successfully
```

**Test 2: Multi-Project Isolation**
```
[ ] Create project A: mkdir project-a && cd project-a
[ ] Run: aur init
[ ] Index some Python files
[ ] Run: aur mem search "test"
[ ] Create project B: mkdir project-b && cd project-b
[ ] Run: aur init
[ ] Run: aur mem search "test"
[ ] Verify: No results from project A appear
```

**Test 3: Re-Run Safety**
```
[ ] Initialized project with custom project.md edits
[ ] Run: aur init again
[ ] Choose "Re-run all steps"
[ ] Verify: Custom project.md content preserved
[ ] Verify: Tool templates updated within markers only
```

**Test 4: Error Handling**
```
[ ] Project with disk space 99% full
[ ] Run: aur init
[ ] Verify: Clear error message about disk space
[ ] Free space
[ ] Re-run: aur init
[ ] Verify: Completes successfully
```

---

### 11.4 Test Coverage Targets

| Component | Target | Current |
|-----------|--------|---------|
| init.py (new) | >90% | N/A |
| Step functions | >95% | N/A |
| Helper functions | >85% | N/A |
| Configurators (reused) | >90% | 92% |
| **Overall init flow** | **>90%** | **N/A** |

---

## 12. Success Metrics

### 12.1 Quantitative Metrics

**Metric 1: Init Success Rate**
- **Target**: 98% of init runs succeed without errors
- **Measurement**: Telemetry + error logs
- **Baseline**: N/A (new feature)

**Metric 2: Time to First Plan**
- **Target**: <2 minutes from `aur init` to `aur plan create`
- **Measurement**: User flow timing studies
- **Baseline**: N/A (new feature)

**Metric 3: Re-Run Safety**
- **Target**: 0 data loss incidents on re-run
- **Measurement**: Issue reports + test suite
- **Baseline**: N/A (new feature)

**Metric 4: Migration Smoothness**
- **Target**: <5 migration issues reported
- **Measurement**: GitHub issues with "migration" label
- **Baseline**: ~20 users migrating

---

### 12.2 Qualitative Metrics

**Metric 1: User Comprehension**
- **Target**: 95% of users understand init flow on first run
- **Measurement**: User interviews + surveys
- **Question**: "How clear was the init process? (1-5)"

**Metric 2: Git Adoption**
- **Target**: 80% of users accept `git init` offer
- **Measurement**: Telemetry (if added) or surveys
- **Insight**: Validates git integration value

**Metric 3: Tool Configuration Satisfaction**
- **Target**: 90% of users satisfied with tool setup
- **Measurement**: Survey + issue reports
- **Question**: "Was tool configuration easy? (1-5)"

---

### 12.3 Success Criteria Summary

**Phase 1.5 is successful if**:

1. ✅ `aur init` command replaces two-command setup
2. ✅ 98% init success rate (no critical errors)
3. ✅ Project-specific memory.db works correctly
4. ✅ Git integration adopted by 80% of users
5. ✅ Idempotent re-runs preserve all custom content
6. ✅ All 312 Phase 1 tests still pass
7. ✅ <5 migration issues reported
8. ✅ Documentation updated (CLI_USAGE_GUIDE.md, README.md)

---

## 13. Acceptance Criteria

### 13.1 Functional Acceptance

**AC-1: Command Exists and Executes**
- [ ] `aur init` command runs without errors
- [ ] `aur init --config` runs without errors
- [ ] `aur init --help` shows updated help text
- [ ] `aur init-planning` command removed (ImportError)

**AC-2: Step 1 (Planning Setup)**
- [ ] Detects `.git/` directory correctly
- [ ] Offers `git init` with explanation if missing
- [ ] Runs `git init` if user accepts
- [ ] Creates `.aurora/plans/active/` and `.aurora/plans/archive/`
- [ ] Creates `.aurora/project.md` with auto-detected metadata
- [ ] Skips planning directories if git declined
- [ ] Never blocks on git requirement

**AC-3: Step 2 (Memory Indexing)**
- [ ] Creates `./.aurora/memory.db` (not global)
- [ ] Indexes entire project root (respects .gitignore)
- [ ] Shows progress bar during indexing
- [ ] Displays success stats (files, chunks, duration)
- [ ] Handles indexing errors gracefully with skip option
- [ ] Offers to re-index on re-run (backs up existing db)
- [ ] Memory.db is project-specific (multi-project isolation)

**AC-4: Step 3 (Tool Configuration)**
- [ ] Interactive checkbox for tool selection
- [ ] Universal AGENTS.md always created
- [ ] Detects already-configured tools
- [ ] Uses `<!-- AURORA:MANAGED:v1:START/END -->` markers
- [ ] Preserves custom content outside markers
- [ ] On re-run: Pre-checks configured tools

**AC-5: --config Flag**
- [ ] Skips Steps 1-2, runs Step 3 only
- [ ] Errors if `.aurora/` doesn't exist
- [ ] Interactive checkbox works same as full init

**AC-6: Idempotent Re-Run**
- [ ] Shows setup status with checkmarks
- [ ] Offers re-run options (all, selective, config-only, exit)
- [ ] Backs up memory.db before re-indexing
- [ ] Preserves custom content in project.md
- [ ] Preserves custom content outside marker boundaries
- [ ] Can run 10 times without errors or data loss

**AC-7: Success Feedback**
- [ ] Shows summary of created files/directories
- [ ] Displays indexing stats
- [ ] Lists created vs updated tool configs
- [ ] Provides 4 concrete next steps with commands

---

### 13.2 Technical Acceptance

**AC-8: Code Quality**
- [ ] Test coverage >90% for init logic
- [ ] All Phase 1 tests (312) still pass
- [ ] No new mypy errors introduced
- [ ] No new linting errors
- [ ] Docstrings for all public functions

**AC-9: Performance**
- [ ] Full init (100 files) completes in <7s
- [ ] Progress bar updates smoothly (>10 FPS)
- [ ] No blocking operations during display

**AC-10: Error Handling**
- [ ] All error scenarios tested
- [ ] Clear error messages with next steps
- [ ] Partial failures don't leave broken state
- [ ] Can re-run after any failure

**AC-11: Documentation**
- [ ] CLI_USAGE_GUIDE.md updated with new flow
- [ ] README.md updated (remove two-command mentions)
- [ ] Migration guide added to docs
- [ ] API docs updated if needed

---

### 13.3 User Acceptance

**AC-12: Usability**
- [ ] User testing shows 95% comprehension on first run
- [ ] All prompts have clear defaults
- [ ] Step numbering clear (1/3, 2/3, 3/3)
- [ ] Success message actionable

**AC-13: Migration**
- [ ] Migration guide complete and tested
- [ ] <5 migration issues reported in first week
- [ ] Old users can migrate in <5 minutes

**AC-14: Backwards Compatibility**
- [ ] Breaking changes documented in release notes
- [ ] Upgrade path clear and tested
- [ ] No silent failures for old users

---

## Appendix A: File Deletion Checklist

**Files to Delete**:
- [ ] `packages/cli/src/aurora_cli/commands/init_planning.py`
- [ ] `tests/unit/cli/test_init_planning.py`

**Files to Modify**:
- [ ] `packages/cli/src/aurora_cli/commands/init.py` (rewrite)
- [ ] `packages/cli/src/aurora_cli/main.py` (remove init_planning_command import/registration)
- [ ] `packages/cli/src/aurora_cli/memory_manager.py` (support project-specific db_path)
- [ ] `docs/cli/CLI_USAGE_GUIDE.md` (update init section + add migration guide)
- [ ] `README.md` (update quick start)

**Files to Create**:
- [ ] `tests/unit/cli/test_init_unified.py` (unit tests)
- [ ] `tests/integration/cli/test_init_flow.py` (integration tests)

---

## Appendix B: Example Output

**Full Init Run**:
```
$ aur init

Aurora Planning System Initialization

Step 1/3: Planning Setup
Git repository not found.

Benefits of using git with Aurora:
- Version control for plans and generated files
- Easy rollback of planning iterations
- Collaboration with team members

Initialize git repository? (Y/n): y
✓ Git initialized

✓ Planning structure created
  - .aurora/plans/active/
  - .aurora/plans/archive/
  - .aurora/project.md (with auto-detected metadata)

Step 2/3: Memory Indexing
Indexing project codebase...

[████████████████████████████████] 100% (150/150 files)

✓ Indexed 150 files, 1,245 chunks in 3.42s
  Database: ./.aurora/memory.db

Step 3/3: AI Tool Configuration
Select tools to configure:
  [x] Claude Code
  [ ] OpenCode
  [ ] AmpCode
  [ ] Droid
  [x] Universal AGENTS.md

✓ Configured 2 tool(s)
  Created: CLAUDE.md, AGENTS.md

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✓ Aurora initialized successfully!

Summary:
  ✓ Step 1: Planning structure created
  ✓ Step 2: Memory indexed (150 files, 1,245 chunks)
  ✓ Step 3: Tools configured (2 tools)

Next Steps:
  1. Fill in project.md
     .aurora/project.md
     Add project-specific context for better AI assistance

  2. Create your first plan
     aur plan create "Your goal here"

  3. Search indexed code
     aur mem search "authentication"

  4. List plans
     aur plan list

For help: aur --help
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

**Re-Run**:
```
$ aur init

Aurora is already initialized in this project.

Setup Status:
  ✓ Step 1: Planning structure (2026-01-03)
  ✓ Step 2: Memory indexed (150 files, 1,245 chunks)
  ✓ Step 3: Tools configured (2 tools)

What would you like to do?
  1. Re-run all steps (will backup existing data)
  2. Re-run specific steps (choose which)
  3. Skip to tool configuration (--config flag)
  4. Exit (no changes)

Choice [1-4]: 4
No changes made.
```

---

## Document History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-01-03 | PRD System | Initial comprehensive PRD |

---

**END OF PRD 0018**
