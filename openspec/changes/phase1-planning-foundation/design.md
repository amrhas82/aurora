# Design Document: Phase 1 Planning Foundation

**Change ID**: `phase1-planning-foundation`
**Status**: Design Specification
**Date**: 2026-01-03

---

## Architectural Overview

### System Context

The Aurora Planning System sits at the intersection of three concerns:

1. **Local Planning** - Files and directories on user's machine (`~/.aurora/plans/`)
2. **CLI Interface** - Commands accessible via `aur plan` CLI
3. **Tool Integration** - Slash commands for Claude Code, OpenCode, AmpCode, Droid

Phase 1 establishes the foundation for all three, with Phase 2 adding intelligence (SOAR decomposition, memory retrieval) and Phase 3 adding execution.

### Design Principles

**1. Convention over Configuration**
- Directory structure predetermined: `~/.aurora/plans/active/` and `~/.aurora/plans/archive/`
- File naming standardized: always `plan.md`, `prd.md`, `tasks.md`, `agents.json`
- Plan ID format fixed: `NNNN-slug` (predictable, sortable)
- No configuration needed for basic planning workflow

**2. Immutability with History**
- Once created, plan files are human-editable but not automatically updated by Aurora
- Archive mechanism preserves history with ISO 8601 timestamps
- `agents.json` is immutable reference for plan identity
- Supports later addition of checkpoint/restore without breaking existing plans

**3. Graceful Degradation**
- Partial success acceptable: 3/4 files generated with warnings
- Missing tool configs don't block planning (feature degrades gracefully)
- Corrupt plan files reported clearly with recovery suggestions
- Archive failures don't delete active plan

**4. Schema-Driven Validation**
- `agents.json` strictly validated against Pydantic model
- Markdown files validated for format/structure, not content
- Tool configs validated against tool-specific schemas
- External tools can validate plans against exported JSON schemas

### Layered Architecture

```
┌─────────────────────────────────────────┐
│    CLI Commands Layer (aur plan ...)    │
│  (init, create, list, view, archive)    │
└──────────────┬──────────────────────────┘
               │
┌──────────────┴──────────────────────────┐
│  Command Implementation Layer            │
│  (Generate files, update manifest)       │
└──────────────┬──────────────────────────┘
               │
┌──────────────┴──────────────────────────┐
│  Core Services Layer                    │
│  (Schemas, parsers, validators,         │
│   templates, config generation)         │
└──────────────┬──────────────────────────┘
               │
┌──────────────┴──────────────────────────┐
│  Filesystem & Configuration             │
│  (~/.aurora/plans/, ~/.aurora/config)   │
└─────────────────────────────────────────┘
```

**Per-layer responsibilities**:
- **CLI**: Argument parsing, user feedback, command dispatch
- **Commands**: Business logic, manifest updates, error handling
- **Services**: Pure functionality (no side effects), reusable across commands
- **FS**: File I/O, directory structure, config management

---

## Core Design Decisions

### 1. Package Boundary: Planning as Independent Package

**Decision**: Create `packages/planning/` as separate, independently-versionable package

**Rationale**:
- Planning system is strategically important enough to warrant its own package
- Can be versioned independently: planning `0.2.0`, core `0.2.0`, etc.
- Allows future split into separate repo if needed
- Mirrors OpenSpec's proven architecture

**Tradeoffs**:
- More complex dependency management (requires `aurora.core`)
- Separate test structure and CI pipeline
- Worth it for maintainability and flexibility

**Alternative Considered**: Fold into `aurora.core`
- Simpler dependency tree but mixed concerns
- Would couple planning releases to core releases
- Would make Phase 2/3 intelligence integration more difficult

### 2. Plan ID Generation: Sequential + Slug

**Decision**: `NNNN-slug` format with sequential numbering from manifest

**Rationale**:
- Sequential numbering (0001, 0002...) is human-readable and sortable
- Slug (kebab-case from goal) is meaningful for file browsing
- Combination is unique without UUIDs
- Manifest `next_id` prevents collisions in concurrent creation

**Example**:
```
0001-implement-oauth2-authentication
0002-add-user-registration-system
0003-fix-critical-security-vulnerability
```

**Tradeoffs**:
- Sequential numbering requires manifest (single point of contention)
- UUID would be simpler for concurrency but less human-friendly
- Race condition possible but extremely rare (millisecond collision window)

**Mitigation**:
- Lock manifest during ID generation
- Fallback retry if collision detected
- Comprehensive test coverage for concurrent creation

### 3. Directory Structure: Dual Rooting

**Decision**: Separate `active/` and `archive/` directories with timestamped archive format

**Rationale**:
- Keeps workspace clean (active plans only in default view)
- Archive names include creation date: `YYYY-MM-DD-NNNN-slug`
- Timestamp enables natural sorting by date
- Preserves plan history for reference and learning

**Example**:
```
~/.aurora/plans/
  active/
    0001-oauth2-auth/         ← Currently working on
    0002-logging/
  archive/
    2026-01-02-0001-oauth2-auth/    ← Completed 2026-01-02
    2025-12-28-0003-security-fix/   ← Completed 2025-12-28
```

**Tradeoffs**:
- More directories to manage
- Archive cleanup may be needed after many plans
- Alternative would be status field in manifest, but separate dirs are cleaner

### 4. Four-File Workflow: Separation of Concerns

**Decision**: Separate files for plan structure, requirements, tasks, and metadata

**Rationale**:
- Each file has distinct purpose and audience:
  - `plan.md` - High-level structure (human)
  - `prd.md` - Detailed requirements (human + AI agents)
  - `tasks.md` - Implementation checklist (human editing)
  - `agents.json` - Machine metadata (automation)

- Allows human modification without breaking machine parsing
- Enables Phase 2 to add agent assignments without restructuring
- Follows proven OpenSpec approach

**File Format Choices**:

| File | Format | Why |
|------|--------|-----|
| `plan.md` | Markdown | Human-readable, supports rich formatting, version-controllable |
| `prd.md` | Markdown | Inherits OpenSpec format, widely used in industry |
| `tasks.md` | GFM checklist | GitHub standard, human editing (checkboxes), task tracking |
| `agents.json` | JSON | Strict schema for automation, Pydantic validation |

**Tradeoffs**:
- Markdown files can drift out of sync with metadata
- Four files more complex than single "plan" file
- Worth it for flexibility and Phase 2 integration

**Mitigation**:
- `agents.json` is source of truth for identity (immutable)
- Markdown files are templates + human edits (no auto-sync)
- Phase 2 can validate consistency if needed

### 5. Manifest Design: Single Point of Record

**Decision**: Manifest file (`~/.aurora/plans/manifest.json`) tracks all plans

**Rationale**:
- Single source of truth for active/archived plans
- Enables fast `aur plan list` without scanning directories
- Tracks `next_id` for sequential generation
- Supports future metadata (total plans, last accessed, etc.)

**Manifest Schema**:
```json
{
  "version": "1.0",
  "next_id": 5,
  "active_plans": [
    {"id": "0001-oauth2-auth", "created_at": "2026-01-02T10:00:00Z"},
    {"id": "0002-logging", "created_at": "2026-01-02T12:00:00Z"}
  ],
  "archived_plans": [
    {"id": "0003-security-fix", "archived_at": "2025-12-28T15:00:00Z"}
  ]
}
```

**Tradeoffs**:
- Manifest can become out of sync with filesystem
- Requires locking during updates
- Alternative: scan directories (simpler, slower)

**Mitigation**:
- Always update manifest atomically with directory changes
- Repair command to rebuild manifest from filesystem
- Tests verify manifest consistency

### 6. Template System: Jinja2 for Flexibility

**Decision**: Use Jinja2 for all four file templates

**Rationale**:
- Proven template engine used in many frameworks
- Supports conditionals, loops, filters for future extensions
- Can be extended with custom filters for Phase 2 (SOAR output)
- Templates are readable and maintainable

**Template Approach**:
- Each template is `.j2` file in `aurora_planning/templates/`
- Rendered with context dict: `{goal, plan_id, subgoals, created_at, ...}`
- Phase 1: Rule-based subgoal generation (5-7 generic subgoals)
- Phase 2: SOAR-powered context for richer subgoals

**Tradeoffs**:
- Requires Jinja2 dependency
- Phase 1 subgoals will be generic (improved in Phase 2)
- Alternative: string interpolation, but less flexible

### 7. Schema Validation: Pydantic for Strictness

**Decision**: Pydantic models for `agents.json` with strict validation

**Rationale**:
- Type safety and validation built-in
- JSON Schema export for external tools
- Clear documentation via type hints
- Supports custom validators for business logic

**Validation Rules**:
```python
# Plan ID format
plan_id: str  # matches ^\d{4}-[a-z0-9-]+$

# Timestamps (ISO 8601)
created_at: datetime
updated_at: datetime
archived_at: Optional[datetime]

# Status enum
status: Literal["active", "archived"]

# Subgoal uniqueness
subgoals: List[Subgoal]  # unique IDs enforced via validator
```

**Tradeoffs**:
- Pydantic adds dependency
- Strict validation prevents some flexibility (by design)
- Alternative: no validation, but defeats purpose

### 8. CLI Integration: Click/Typer for Consistency

**Decision**: Use Aurora's existing CLI framework (Click or Typer) for `aur plan` commands

**Rationale**:
- Consistent with rest of Aurora CLI
- Automatic help generation
- Type hints map to CLI arguments
- Integrates naturally with main `aur` entry point

**Command Structure**:
```bash
aur plan init                              # Initialize
aur plan create "Add OAuth2"               # Create
aur plan list [--archived] [--all]         # List
aur plan view 0001                         # View
aur plan archive 0001                      # Archive
```

**Tradeoffs**:
- Requires alignment with Aurora CLI design
- Alternative: separate CLI (more autonomy, more maintenance)

### 9. Tool Configuration: Merge Strategy

**Decision**: Generate tool configs and merge with existing, preserve backup

**Rationale**:
- Users may have other MCP servers configured (don't lose them)
- Backup allows recovery if merge fails
- Merge is idempotent (can run `aur plan init` multiple times)

**Merge Algorithm**:
1. Read existing config (if exists)
2. Parse JSON to preserve structure
3. Add/update `aurora` section
4. Write back with formatting preserved
5. Create backup with timestamp if modified

**Example** (Claude Code config):
```json
{
  "mcpServers": {
    "other-server": {...},         // ← Preserved
    "aurora": {                    // ← Added/updated
      "command": "aur plan",
      "commands": [...]
    }
  }
}
```

**Tradeoffs**:
- Merge logic adds complexity
- Backup management (cleanup old backups)
- Alternative: overwrite (simpler, data loss risk)

---

## Phase 1 vs Phase 2+ Distinction

### Phase 1: Foundation

**What's Included**:
- ✓ File generation with templates
- ✓ Rule-based subgoal decomposition (5-7 generic subgoals per plan)
- ✓ Static tool configuration
- ✓ Manifest-based tracking
- ✓ Basic file format validation

**What's Excluded** (Phase 2+):
- ✗ SOAR-powered decomposition (intelligent subgoal generation)
- ✗ Memory-aware file path resolution
- ✗ Agent recommendation with manifest integration
- ✗ Automatic requirement generation (LLM-powered)
- ✗ Plan execution and orchestration
- ✗ Checkpoint/resume workflows

### Integration Points for Phase 2

**Decomposition Hook**:
```python
# Phase 1: Rule-based
subgoals = [
    Subgoal(id="sg-1", title="Research and planning"),
    Subgoal(id="sg-2", title="Implementation"),
    ...
]

# Phase 2: SOAR-powered
subgoals = await soar_decompose(goal)
```

**Agent Assignment**:
```json
{
  "subgoals": [
    {
      "id": "sg-1",
      "agent_id": null,  // Phase 1: empty
      // Phase 2: would recommend based on manifest
    }
  ]
}
```

**Content Generation**:
```python
# Phase 1: Template-based with placeholders
requirements = templates.prd.render(goal=goal, subgoals=subgoals)

# Phase 2: LLM-powered content
requirements = await llm.generate_requirements(goal, subgoals)
```

---

## Error Handling Strategy

### Command-Level Error Types

**Initialization Errors** (aur plan init):
- `PLANNING_INIT_FAILED` - Directory creation fails
- `PLANNING_PERMISSION_DENIED` - Insufficient permissions
- Recovery: Suggest `mkdir -p ~/.aurora/plans` or check permissions

**Creation Errors** (aur plan create):
- `INVALID_GOAL` - Empty or invalid goal string
- `PLANNING_NOT_INITIALIZED` - Manifest doesn't exist
- `PLAN_ALREADY_EXISTS` - Duplicate slug (very rare)
- Recovery: Initialize first, or retry with different slug

**Lookup Errors** (aur plan list/view):
- `PLANNING_NOT_INITIALIZED` - Manifest missing
- `PLAN_NOT_FOUND` - Plan ID doesn't exist
- `AMBIGUOUS_PLAN_ID` - Multiple plans match slug
- `MANIFEST_CORRUPT` - Invalid JSON in manifest
- Recovery: Rebuild manifest from filesystem

**Archive Errors** (aur plan archive):
- `PLAN_NOT_FOUND` - Plan doesn't exist
- `PLAN_ALREADY_ARCHIVED` - Already archived
- `ARCHIVE_CONFLICT` - Archive dir exists
- Recovery: Manual rename or force flag

### File-Level Error Handling

**Generation Failures**:
- Individual file failure: Return with warning, others succeed
- Critical failure (agents.json): Rollback all files
- Partial success: Usable plan created, user warned

**Validation Failures**:
- Schema validation: Clear error message, field name included
- Format validation: Suggest tool to fix (e.g., markdown linter)
- Recovery: Suggest `aur plan update <id>` (deferred to Phase 2)

### Graceful Degradation

**Missing Tool Configs**:
- Non-critical for planning
- Plan creation succeeds, slash commands unavailable
- Documentation guides manual config

**Manifest Corruption**:
- Rare but possible
- Repair command: Rebuild from filesystem
- Fallback: Scan directories if manifest invalid

---

## Performance Considerations

### Aspirational Targets

| Operation | Target | Rationale |
|-----------|--------|-----------|
| `aur plan init` | <100ms | Filesystem ops only, should be instant |
| `aur plan create` | <5s | Template rendering + file I/O, reasonable |
| `aur plan list` | <500ms | Read manifest only, fast |
| `aur plan view` | <500ms | Read 4 files + render, single plan |
| `aur plan archive` | <1s | Move directory + update manifest |

**Non-Blocking**: These are aspirational, not hard requirements. Phase 1 focuses on correctness; performance tuning happens if needed.

### Optimization Opportunities (Phase 2+)

- Cache rendered templates
- Lazy-load plan metadata
- Batch operations for large plan counts
- Memory-optimized manifest format

---

## Testing Architecture

### Test Pyramid

```
         Acceptance (Manual)
            /          \
         E2E Tests      Tool Testing
        /        \        /      \
   Integration Tests - Scenarios
      /        \        /       \
  Unit Tests - All modules (High Coverage)
   |                                  |
   Core Services              Command Logic
```

### Coverage Targets

- **Overall**: ≥95% coverage
- **Core services**: 99% (parsers, validators, schemas)
- **Commands**: 95% (business logic + error paths)
- **Integration**: 90% (workflows, file I/O)

### Test Categories

**Unit Tests** (200+ tests from OpenSpec):
- Individual functions and classes
- Schema validation
- Template rendering
- Parser/validator behavior

**Integration Tests** (80+ tests):
- Command workflows (init → create → list → view → archive)
- File generation and validation
- Manifest updates
- Error recovery

**Acceptance Tests** (Manual):
- Slash command execution in real tools
- Cross-platform compatibility
- User documentation accuracy

---

## Security Considerations

### File Permissions

**Directory Permissions**: `0755` (user rwx, others rx)
- Allows user to read own plans
- Doesn't expose to system

**File Permissions**: `0644` (user rw, others r)
- Plans may contain sensitive information
- Consider `0600` in future if plans contain secrets

### Input Validation

**Goal Statements**:
- Max length: 500 characters
- Reject special shell characters (prevent injection)
- Sanitize for slug generation (alphanumeric + hyphens)

**Plan IDs**:
- Whitelist format validation: `^\d{4}-[a-z0-9-]+$`
- Prevent directory traversal: No `..` or `/` allowed

**File Paths**:
- Validate against `~/.aurora/plans/` root
- Prevent symlink attacks (use `Path.resolve()`)

### Configuration Security

**Tool Configs**:
- Never embed secrets in configs
- Read-only for other users
- Back up before modifying

---

## Future Extension Points

### Phase 2: Intelligence Layer

**Decomposition Integration**:
```python
# Current: Rule-based
from aurora.planning.generators import generate_subgoals_rule_based

# Future: SOAR-powered
from aurora.planning.generators import generate_subgoals_soar
```

**Agent Assignment**:
```python
# Current: Empty in JSON
subgoals[0].agent_id = None

# Future: Manifest-aware
subgoals[0].agent_id = await agent_manifest.recommend(goal)
```

### Phase 3: Execution Layer

**Plan Execution**:
```python
# New command: aur plan execute <plan-id>
# Orchestrates agents, tracks progress, handles checkpoints
```

**Checkpoint/Resume**:
```python
# Extend agents.json with execution state
{
  "status": "active",
  "execution": {
    "state": "checkpoint-sg2",
    "completed_subgoals": ["sg-1"],
    "current_subgoal": "sg-2"
  }
}
```

---

## Decision Log

| Date | Decision | Rationale | Alternatives |
|------|----------|-----------|--------------|
| 2026-01-03 | Sequential plan IDs | Human-friendly, sortable | UUIDs (less readable) |
| 2026-01-03 | Separate active/archive dirs | Clean workspace | Status field in manifest |
| 2026-01-03 | Four-file structure | Separation of concerns | Single plan.json file |
| 2026-01-03 | Manifest + filesystem | Fast list ops | Scan directories (slower) |
| 2026-01-03 | Pydantic for agents.json | Schema validation | Python dicts (no validation) |
| 2026-01-03 | Jinja2 templates | Flexible, extensible | String format (less flexible) |

---

## References

- **PRD**: `/tasks/0017-prd-phase1-foundation.md`
- **OpenSpec Source**: `/tmp/openspec-source/aurora/`
- **Strategic Plan**: `/tasks/0017-planning-specs-v2.md`
