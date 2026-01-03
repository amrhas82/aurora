# Specification: Planning Schemas and Validation

**Capability**: `planning-schemas`
**Status**: Specification
**Change ID**: `phase1-planning-foundation`
**Version**: 1.0

---

## Summary

The Planning Schemas define the data models and validation rules for all planning artifacts, ensuring data integrity and enabling external tools to validate plans.

---

## ADDED Requirements

### Requirement: Agent Metadata Schema

**Category**: Data Model

**Description**: Pydantic models define the structure and validation for plan metadata.

Pydantic models SHALL provide type-safe, validated data structures for plan metadata with JSON serialization support and schema export for external validation.

#### Scenario: AgentMetadata Model

**Given** a plan needs machine-readable metadata
**When** I define the AgentMetadata model
**Then**:
- Model contains required fields:
  - `plan_id: str` - Format: `NNNN-slug` (validated with regex)
  - `goal: str` - Original goal statement (1-500 chars)
  - `status: Literal["active", "archived"]` - Current plan status
  - `created_at: datetime` - ISO 8601 timestamp
  - `updated_at: datetime` - ISO 8601 timestamp
  - `subgoals: List[Subgoal]` - Decomposition into subgoals
- Model contains optional fields:
  - `archived_at: Optional[datetime]` - Set when archived
  - `complexity: Optional[Literal["simple", "moderate", "complex"]]` - For Phase 2
- Validators ensure:
  - Plan ID matches regex: `^\d{4}-[a-z0-9-]+$`
  - Timestamps are valid ISO 8601
  - Subgoal IDs are unique within plan
- Model can be serialized to JSON and deserialized back losslessly

#### Scenario: Subgoal Model

**Given** plans are decomposed into subgoals
**When** I define the Subgoal model
**Then**:
- Model contains fields:
  - `id: str` - Format: `sg-N` (e.g., `sg-1`, `sg-2`)
  - `title: str` - Brief description of subgoal
  - `description: Optional[str]` - Detailed description
  - `status: Literal["pending", "in_progress", "completed"]` - Subgoal progress
  - `agent_id: Optional[str]` - Agent assignment (Phase 2, empty in Phase 1)
  - `tasks: List[str]` - Task IDs from tasks.md
- Validators ensure:
  - ID format is valid: `^sg-\d+$`
  - Status transitions are logical

#### Scenario: JSON Schema Export

**Given** external tools need to validate plans
**When** I export JSON Schema from Pydantic models
**Then**:
- Schema is valid JSON Schema (draft 2020-12)
- Schema includes all required fields
- Schema includes validators (pattern, enum, etc.)
- Schema is exportable: `AgentMetadata.model_json_schema()`
- External tools can use schema for validation: `jsonschema.validate(data, schema)`

---

### Requirement: Plan ID Validation

**Category**: Validation

**Description**: Plan ID format is strictly validated to ensure consistency.

Plan IDs SHALL follow a strict format that is human-readable, sortable, and machine-parseable for reliable identification and filesystem organization.

#### Scenario: Valid Plan IDs

**Given** plan IDs are generated
**When** I validate against the plan ID schema
**Then**:
- Valid formats accepted:
  - `0001-implement-oauth2-authentication`
  - `0002-add-user-registration`
  - `9999-simple-plan`
- Format enforced: `NNNN-slug`
  - NNNN: 4 digits
  - slug: lowercase alphanumeric + hyphens
  - No spaces, underscores, or special characters allowed

#### Scenario: Invalid Plan IDs Rejected

**Given** invalid plan IDs are attempted
**When** I validate against the plan ID schema
**Then**:
- Invalid formats rejected:
  - `1-short` (less than 4 digits)
  - `0001_underscores` (underscores not allowed)
  - `0001-UPPERCASE` (must be lowercase)
  - `0001-with spaces` (spaces not allowed)
- Validation error clearly describes requirement

---

### Requirement: Timestamp Validation

**Category**: Validation

**Description**: All timestamps must be valid ISO 8601 format.

Timestamps SHALL use consistent ISO 8601 format across all plan metadata for portability and standardization.

#### Scenario: ISO 8601 Timestamps

**Given** times are recorded in plan metadata
**When** I validate timestamps
**Then**:
- Format: `YYYY-MM-DDTHH:MM:SSZ` or with timezone
- Examples accepted:
  - `2026-01-03T14:30:00Z` (UTC)
  - `2026-01-03T14:30:00+00:00` (explicit UTC)
  - `2026-01-03T14:30:00-05:00` (timezone offset)
- Seconds precision minimum (milliseconds optional)
- Timezone information preserved on round-trip

---

### Requirement: Subgoal Uniqueness

**Category**: Validation

**Description**: Subgoal IDs must be unique within a plan.

Uniqueness validation SHALL ensure that each subgoal is identifiable and there are no ambiguities in plan decomposition.

#### Scenario: Unique Subgoal IDs

**Given** a plan has multiple subgoals
**When** I create or validate the plan
**Then**:
- Each subgoal ID is checked for uniqueness
- Duplicate IDs are rejected with error
- Error message identifies duplicates

#### Scenario: Subgoal ID Format

**Given** subgoals are created
**When** I validate IDs
**Then**:
- Format required: `sg-N` where N is a number
- Examples: `sg-1`, `sg-2`, `sg-10`
- Format is validated on model instantiation

---

### Requirement: Status Validation

**Category**: Validation

**Description**: Plan and subgoal status values are constrained to valid states.

Status values SHALL be from a predefined set to ensure consistency and enable programmatic state machine logic.

#### Scenario: Plan Status Values

**Given** a plan is created or archived
**When** I set the status field
**Then**:
- Only valid values accepted: `"active"`, `"archived"`
- Invalid values rejected with error
- Status must be set at creation

#### Scenario: Subgoal Status Values

**Given** a subgoal progresses
**When** I set the status field
**Then**:
- Only valid values accepted: `"pending"`, `"in_progress"`, `"completed"`
- Invalid values rejected with error

---

### Requirement: Complex Validation Rules

**Category**: Validation

**Description**: Complex validation rules that span multiple fields.

Multi-field validators SHALL ensure data consistency and referential integrity across plan metadata.

#### Scenario: Archived Plan Consistency

**Given** a plan is archived
**When** I validate the metadata
**Then**:
- If `status == "archived"`, `archived_at` must be present
- If `status == "active"`, `archived_at` must be null
- `archived_at` must be equal or after `created_at`

#### Scenario: Subgoal Task IDs

**Given** a subgoal references tasks
**When** I validate the subgoal
**Then**:
- Task IDs must match pattern from tasks.md (e.g., `1.1`, `1.2`, `2.1`)
- All referenced tasks must exist in the plan's tasks.md
- Empty tasks list is valid (subgoal with no tasks)

---

## Context

### Related Capabilities

- `planning-core` - Uses schemas for metadata
- `planning-templates` - Renders subgoals from these models
- `planning-commands` - Validates metadata in create/archive

### Type Safety

All models are fully type-hinted with:
- Required vs. optional fields clearly marked
- Literal types for enums (not strings)
- List and Dict types parameterized
- datetime for timestamps (not strings)

### Extensibility for Phase 2

- `complexity` field reserved for Phase 2 analysis
- `agent_id` field reserved for Phase 2 recommendations
- Validators designed to be extensible without breaking
