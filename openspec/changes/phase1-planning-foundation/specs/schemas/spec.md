# Specification: Four-File Workflow

**Capability**: `planning-templates`
**Status**: Specification
**Change ID**: `phase1-planning-foundation`
**Version**: 1.0

---

## Summary

The Four-File Workflow defines the structure and content generation for the four files created with each plan: `plan.md`, `prd.md`, `tasks.md`, and `agents.json`.

---

## ADDED Requirements

### Requirement: Plan Markdown Template

**Category**: File Format

**Description**: The `plan.md` file provides high-level plan decomposition in Markdown format.

Templates SHALL generate human-readable files with consistent structure and formatting to support user editing and manual planning workflows.

#### Scenario: Plan File Structure

**Given** a new plan is created
**When** `plan.md` is generated
**Then**:
- File contains sections:
  - `# Goal` - Original goal statement
  - `## Subgoals` - Numbered list of subgoals with descriptions
  - `## Dependencies` - Dependencies between subgoals (graph or list)
  - `## Agent Assignments` - Table mapping subgoals to agents (Phase 2, empty in Phase 1)
- File is valid Markdown (no rendering errors)
- All template variables are rendered (no `{{ }}` syntax remains)
- File is human-readable and editable

#### Scenario: Subgoals Generated

**Given** a goal statement is provided
**When** subgoals are generated for the plan
**Then**:
- 5-7 generic subgoals are created (rule-based, Phase 1)
- Each subgoal has:
  - ID: `sg-1`, `sg-2`, etc.
  - Title: Meaningful description
  - Description: Details about what the subgoal accomplishes
- Subgoals follow logical progression
- Phase 2 will replace with SOAR-powered decomposition

---

### Requirement: Requirements Markdown Template

**Category**: File Format

**Description**: The `prd.md` file contains detailed requirements in OpenSpec format.

Requirements documentation SHALL follows industry-standard PRD format for consistency with Aurora development practices.

#### Scenario: PRD File Structure

**Given** a new plan is created
**When** `prd.md` is generated
**Then**:
- File contains sections:
  - `# Executive Summary` - Problem, solution, value
  - `## Goals` - Primary and secondary objectives
  - `## User Stories` - "As a [user], I want to [action]" format
  - `## Functional Requirements` - FR-N.M format with acceptance criteria
  - `## Non-Goals` - Out of scope items
  - `## Testing Strategy` - Unit, integration, acceptance test plans
  - `## Success Metrics` - Measurable indicators
- Format follows OpenSpec conventions
- All sections are present (even if placeholder in Phase 1)
- File is valid Markdown

#### Scenario: Placeholder Content

**Given** Phase 1 doesn't have AI-powered requirement generation
**When** `prd.md` is generated
**Then**:
- Sections contain placeholder text indicating Phase 2 will populate
- Example: "## Functional Requirements - To be detailed in Phase 2"
- User can manually edit sections for Phase 1 use
- Phase 2 will auto-populate from SOAR analysis

---

### Requirement: Tasks Checklist Template

**Category**: File Format

**Description**: The `tasks.md` file contains an implementation checklist in GitHub-flavored Markdown.

Checklists SHALL provide an interactive way for users to track task progress and decompose work into actionable items.

#### Scenario: Checklist Structure

**Given** a new plan is created
**When** `tasks.md` is generated
**Then**:
- File uses GFM checklist syntax: `- [ ] Task description`
- Tasks are grouped by subgoal:
  - `## Subgoal 1: Research and Planning`
  - `- [ ] Task 1.1: Do research`
  - `- [ ] Task 1.2: Plan architecture`
- Task IDs follow format: `N.M` (subgoal.task)
- Checkboxes are unchecked initially
- User can manually check boxes to track progress

#### Scenario: Subgoal Task Lists

**Given** subgoals are defined
**When** tasks are generated
**Then**:
- Each subgoal has 2-5 associated tasks
- Tasks are concise and actionable
- All tasks contribute to completing the subgoal
- Phase 2 will include file paths from memory retrieval

---

### Requirement: Metadata JSON Schema

**Category**: File Format

**Description**: The `agents.json` file contains machine-readable plan metadata and is strictly validated.

JSON metadata SHALL enable programmatic plan manipulation, external tool integration, and Phase 2 intelligence layer features.

#### Scenario: JSON File Format

**Given** a new plan is created
**When** `agents.json` is generated
**Then**:
- File is valid JSON (2-space indentation)
- Content conforms to AgentMetadata Pydantic model
- Structure:
  ```json
  {
    "plan_id": "0001-oauth2-auth",
    "goal": "Implement OAuth2 authentication",
    "status": "active",
    "created_at": "2026-01-03T14:30:00Z",
    "updated_at": "2026-01-03T14:30:00Z",
    "subgoals": [
      {
        "id": "sg-1",
        "title": "Research OAuth providers",
        "status": "pending",
        "tasks": ["1.1", "1.2"]
      }
    ]
  }
  ```
- All required fields present
- ISO 8601 timestamps used
- File can be parsed by external tools

#### Scenario: Metadata Round-Trip

**Given** metadata is created and saved
**When** I load and re-save the file
**Then**:
- All data is preserved losslessly
- Timestamps maintain precision
- No data corruption or transformation
- File can be validated against JSON Schema

---

### Requirement: File Generation Pipeline

**Category**: Process

**Description**: The pipeline orchestrates generation of all four files atomically.

Atomic file generation SHALL ensure consistency and prevents partial plan creation that could leave the system in an inconsistent state.

#### Scenario: Atomic File Generation

**Given** I create a new plan
**When** all four files are generated
**Then**:
- Files are written atomically:
  - Temp files created first
  - All files written successfully
  - Temp files renamed to final names simultaneously
- If any file fails to write:
  - Partial failure: Success with warnings if 3/4 files succeed
  - Critical failure: All files rolled back if `agents.json` fails
  - Partial files cleaned up

#### Scenario: File Validation

**Given** files are generated
**When** validation is performed
**Then**:
- `plan.md`: Valid Markdown syntax, no template variables remain
- `prd.md`: Valid Markdown, all sections present
- `tasks.md`: Valid GFM checklist, all tasks formatted correctly
- `agents.json`: Valid JSON, conforms to AgentMetadata schema
- If any file fails validation: Error returned with details

#### Scenario: Goal Processing

**Given** a goal statement is provided
**When** files are generated
**Then**:
- Goal is analyzed to extract context:
  - Keywords identified for categorization
  - Domain inferred (web, security, etc.)
  - Complexity estimated (simple, moderate, complex)
- Subgoals generated based on context
- Templates rendered with goal context

---

### Requirement: Template Variables

**Category**: Implementation

**Description**: Templates receive context variables for rendering.

Template variables SHALL provide flexible content generation while maintaining clean separation between data and presentation.

#### Scenario: Template Context

**Given** files are being rendered
**When** templates are evaluated
**Then**:
- Variables available to all templates:
  - `{{ goal }}` - Original goal string
  - `{{ plan_id }}` - Plan identifier (e.g., `0001-oauth2-auth`)
  - `{{ created_at }}` - Creation timestamp (ISO 8601)
  - `{{ updated_at }}` - Last update timestamp
- Subgoal-specific variables:
  - `{{ subgoals }}` - List of Subgoal objects
  - `{{ subgoals[i].id }}` - Subgoal ID (e.g., `sg-1`)
  - `{{ subgoals[i].title }}` - Subgoal title
  - `{{ subgoals[i].description }}` - Subgoal description
- Filters available:
  - `{{ goal | upper }}` - Convert to uppercase
  - `{{ goal | length }}` - String length
  - `{{ subgoals | length }}` - Subgoal count

---

### Requirement: Phase 1 vs Phase 2 Placeholders

**Category**: Extensibility

**Description**: Templates include placeholders for Phase 2 features that will be enhanced.

Placeholders SHALL ensure that Phase 1 files can be extended in Phase 2 without requiring restructuring or breaking existing plans.

#### Scenario: Agent Assignment Placeholders

**Given** Phase 1 generates files
**When** templates render agent assignment sections
**Then**:
- Comments indicate Phase 2 will populate: `<!-- Phase 2: Agent assignment via manifest -->`
- `agent_id` fields in `agents.json` are null
- Agent assignment table in `plan.md` is empty
- Phase 2 can populate these fields without restructuring

#### Scenario: Decomposition Hooks

**Given** subgoal generation completes
**When** templates are rendered
**Then**:
- Comments in templates indicate where SOAR will enhance:
  - `<!-- Phase 2: Enhanced from SOAR analysis -->`
  - `<!-- Phase 2: File paths from memory retrieval -->`
- Current output is usable but generic
- Phase 2 can enhance without breaking Phase 1 files

---

## Context

### Related Capabilities

- `planning-core` - File generation happens here
- `planning-schemas` - `agents.json` validates against AgentMetadata
- `planning-commands` - Create command generates these files

### Generation Algorithm

1. Parse goal statement and extract context
2. Generate 5-7 subgoals (rule-based, Phase 1)
3. Create context dict with goal, plan_id, subgoals, timestamps
4. Render `plan.md.j2` → `plan.md`
5. Render `prd.md.j2` → `prd.md`
6. Render `tasks.md.j2` → `tasks.md`
7. Create AgentMetadata from subgoals → serialize to `agents.json`
8. Validate all files against their schemas
9. Return result with file paths and any warnings

### Extensibility for Phase 2

- Subgoal generation can be swapped: `generate_subgoals_rule_based()` → `generate_subgoals_soar()`
- Template context can be enriched: Add file paths, agent recommendations, etc.
- Validation can be enhanced: Check consistency across files
- No breaking changes to file structures needed
