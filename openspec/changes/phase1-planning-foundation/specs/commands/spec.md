# Specification: Planning Commands

**Capability**: `planning-commands`
**Status**: Specification
**Change ID**: `phase1-planning-foundation`
**Version**: 1.0

---

## Summary

The Aurora Planning Commands provide a complete CLI interface for managing plans: initialization, creation, listing, viewing, and archiving.

---

## ADDED Requirements

### Requirement: Plan Initialization Command

**Category**: CLI Interface

**Description**: The `aur plan init` command creates the directory structure and manifest for planning.

Initialization SHALL create all necessary directories and manifest file in an idempotent manner, allowing users to set up their planning environment safely.

#### Scenario: Initialize Planning Environment

**Given** I am a new user with Aurora installed
**When** I run `aur plan init`
**Then**:
- Directories are created: `~/.aurora/plans/active/` and `~/.aurora/plans/archive/`
- Directory permissions are set to `0755`
- Manifest file is created: `~/.aurora/plans/manifest.json`
- Manifest is initialized with empty plan lists and `next_id: 1`
- Command returns success status (exit code 0)
- Command completes in <100ms

#### Scenario: Idempotent Initialization

**Given** planning is already initialized
**When** I run `aur plan init` again
**Then**:
- No error is raised
- Existing directories and manifest are preserved
- Command returns success status
- User is informed that planning is already initialized

#### Scenario: Force Reinitialization

**Given** planning directory exists with plans
**When** I run `aur plan init --force`
**Then**:
- Existing directories are preserved
- Manifest is recreated with `next_id: 1`
- User is warned that manifest is reset
- Existing plan directories remain untouched

---

### Requirement: Plan Creation Command

**Category**: CLI Interface

**Description**: The `aur plan create` command generates a new plan with four-file structure.

Plan creation SHALL generate unique identifiers, create directory structure, generate valid files, and update manifest tracking in an atomic operation.

#### Scenario: Create Plan from Goal

**Given** planning is initialized
**When** I run `aur plan create "Implement OAuth2 authentication"`
**Then**:
- Unique plan ID is generated: `0001-implement-oauth2-authentication`
- Plan directory is created: `~/.aurora/plans/active/0001-implement-oauth2-authentication/`
- Four files are generated:
  - `plan.md` - High-level decomposition
  - `prd.md` - Detailed requirements
  - `tasks.md` - Implementation checklist
  - `agents.json` - Machine-readable metadata
- Manifest is updated with new plan entry
- `next_id` is incremented
- Command returns plan ID and file paths
- Command completes in <5s (aspirational)

#### Scenario: Validation of Goal

**Given** I run plan creation
**When** the goal is empty or invalid
**Then**:
- Command returns error: `INVALID_GOAL`
- Error message describes the requirement (non-empty, <500 chars)
- No plan is created
- Exit code is non-zero

#### Scenario: Planning Not Initialized

**Given** planning directories don't exist
**When** I run `aur plan create "goal"`
**Then**:
- Command returns error: `PLANNING_NOT_INITIALIZED`
- Error message suggests: "Run `aur plan init` first"
- No plan is created
- Exit code is non-zero

---

### Requirement: Plan List Command

**Category**: CLI Interface

**Description**: The `aur plan list` command displays all active or archived plans.

The list command SHALL retrieve plan information from the manifest and display it in a user-friendly format with filtering and sorting options.

#### Scenario: List Active Plans

**Given** I have created multiple plans
**When** I run `aur plan list`
**Then**:
- Output is a table with columns: ID, Slug, Tasks, Progress, Last Modified
- Table shows only active plans
- Plans are sorted by most recently modified first
- Each row shows plan ID and progress percentage
- Command completes in <500ms (aspirational)

#### Scenario: List Archived Plans

**Given** I have archived some plans
**When** I run `aur plan list --archived`
**Then**:
- Output is a table showing only archived plans
- Archive timestamp is shown instead of modification time
- Plans are sorted by archive date (newest first)

#### Scenario: List All Plans

**Given** I have both active and archived plans
**When** I run `aur plan list --all`
**Then**:
- Output shows both active and archived plans
- Status indicator shows which are active/archived
- Sorted with active plans first, then archived by date

---

### Requirement: Plan View Command

**Category**: CLI Interface

**Description**: The `aur plan view` command displays detailed plan information.

The view command SHALL retrieve a plan by ID, parse its files, and display comprehensive details including goals, subgoals, progress, and metadata.

#### Scenario: View Plan Details

**Given** I have created plan `0001-oauth2-auth`
**When** I run `aur plan view 0001`
**Then**:
- Dashboard is displayed showing:
  - Goal statement
  - Plan status (active/archived)
  - Overall progress (completed tasks / total tasks)
  - List of subgoals with task counts per subgoal
  - Agent assignments (if any)
  - Creation and modification timestamps
- Command completes in <500ms (aspirational)

#### Scenario: View with Partial Plan ID

**Given** I have multiple plans
**When** I run `aur plan view oauth` (partial slug match)
**Then**:
- Matching plan is displayed if unique match found
- If multiple matches exist: Error `AMBIGUOUS_PLAN_ID` with list of matches
- Fuzzy matching is case-insensitive

#### Scenario: View Archived Plan

**Given** a plan has been archived
**When** I run `aur plan view 0001 --archived`
**Then**:
- Archived plan is displayed
- Status shown as "Archived"
- Archive timestamp is displayed

---

### Requirement: Plan Archive Command

**Category**: CLI Interface

**Description**: The `aur plan archive` command moves a completed plan to the archive.

Archiving SHALL move plan directories atomically, update metadata with timestamps, and maintain manifest consistency while preserving full plan content.

#### Scenario: Archive Completed Plan

**Given** I have completed plan `0001-oauth2-auth`
**When** I run `aur plan archive 0001`
**Then**:
- Plan directory is moved from `active/` to `archive/`
- Archive path follows format: `~/.aurora/plans/archive/YYYY-MM-DD-0001-oauth2-auth/`
- `agents.json` is updated:
  - Status set to `"archived"`
  - `archived_at` timestamp added (ISO 8601)
- Manifest is updated:
  - Plan removed from `active_plans`
  - Plan added to `archived_plans`
- Command returns archive path
- Command completes in <1s
- Original plan content is fully preserved

#### Scenario: Archive Non-Existent Plan

**Given** plan ID doesn't exist
**When** I run `aur plan archive 9999`
**Then**:
- Command returns error: `PLAN_NOT_FOUND`
- Error message lists available plans
- No changes to filesystem or manifest

#### Scenario: Archive Already Archived Plan

**Given** a plan is already archived
**When** I run `aur plan archive 0001` (for archived plan)
**Then**:
- Command returns error: `PLAN_ALREADY_ARCHIVED`
- Plan remains in archive
- No changes to manifest

---

### Requirement: CLI Integration

**Category**: Architecture

**Description**: All planning commands are integrated into the main Aurora CLI.

The planning commands SHALL be available as subcommands under `aur plan` with proper help text and error handling integrated into Aurora's main CLI framework.

#### Scenario: Commands Available

**Given** Aurora is installed with planning package
**When** I run `aur plan --help`
**Then**:
- Command group is recognized
- All five subcommands are listed:
  - `init`
  - `create`
  - `list`
  - `view`
  - `archive`
- Each subcommand has a help description

#### Scenario: Help Display

**Given** I need information about a command
**When** I run `aur plan create --help`
**Then**:
- Detailed help is displayed
- Arguments and flags are documented
- Examples are provided
- Exit code is 0 (help, not error)

---

## Context

### Related Capabilities

- `planning-core` - Base package and infrastructure
- `planning-schemas` - Data models for manifest and metadata
- `planning-templates` - File generation for create command

### Error Handling

All commands return structured errors with:
- Error code (e.g., `PLAN_NOT_FOUND`)
- User-friendly message
- Suggested recovery action
- Non-zero exit code

### Performance Targets (Aspirational)

- `init`: <100ms
- `create`: <5s
- `list`: <500ms
- `view`: <500ms
- `archive`: <1s
