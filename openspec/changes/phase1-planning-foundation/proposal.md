# Proposal: Phase 1 Planning Foundation

**Change ID**: `phase1-planning-foundation`
**Status**: Proposal
**Created**: 2026-01-03
**Author**: Aurora Team

---

## Summary

Integrate the refactored OpenSpec planning system as Aurora's native planning package (`aurora.planning`), establishing the foundation for intelligent plan decomposition, execution tracking, and multi-tool orchestration.

This proposal formalizes Phase 1 of the 3-phase Aurora Planning System roadmap:
- **Phase 1** (this proposal): Native planning infrastructure with OpenSpec commands
- **Phase 2**: Layer SOAR decomposition, memory retrieval, and agent discovery
- **Phase 3**: Execution orchestration with agent delegation

### Strategic Rationale

**Current State**:
- OpenSpec refactoring complete: 284 passing tests at `/tmp/openspec-source/aurora/`
- Proven planning infrastructure exists but isolated from Aurora ecosystem
- Users lack native `aur plan` commands and multi-tool configuration support

**Desired State**:
- Aurora provides first-class planning through `aur plan create/list/view/archive`
- Plans generated in 4-file structure: `plan.md`, `prd.md`, `tasks.md`, `agents.json`
- Slash commands available across Claude Code, OpenCode, AmpCode, Droid
- 284 tests migrated and passing in Aurora test structure

**Business Value**:
- Eliminates manual planning workflow (hours → seconds)
- Provides battle-tested foundation (284 tests, 97%+ coverage)
- Enables future Phase 2/3 intelligence layers without architectural rework
- Supports ecosystem integration for all major AI coding tools

---

## Scope Definition

### In Scope

1. **Package Migration** (FR-1.x)
   - Migrate OpenSpec directory structure to `packages/planning/src/aurora_planning/`
   - Update all imports from `openspec` to `aurora.planning`
   - Migrate 284 tests to Aurora test structure
   - Configure `aurora-planning` as namespace package with dependencies

2. **Planning Commands** (FR-2.x)
   - `aur plan init` - Initialize `.aurora/plans/` structure
   - `aur plan create <goal>` - Generate 4-file plan from goal statement
   - `aur plan list [--archived] [--all]` - Display plan summaries
   - `aur plan view <plan-id>` - Show detailed plan dashboard
   - `aur plan archive <plan-id>` - Archive completed plans

3. **Multi-Tool Configuration** (FR-3.x)
   - Integrate OpenSpec config module (~100 lines)
   - Generate slash command configs for 4 tools
   - Support MCP protocol for Claude Code
   - Validate configs against tool-specific schemas

4. **Four-File Workflow** (FR-4.x)
   - Define JSON schema for `agents.json` (plan metadata)
   - Create Jinja2 templates for `plan.md`, `prd.md`, `tasks.md`
   - Implement file generation pipeline with validation
   - Generate files atomically with rollback on critical failure

5. **Documentation** (FR-5.x)
   - README with quick start and examples
   - API reference from docstrings
   - User guide with workflows and troubleshooting
   - Integration guide for tool configuration

### Out of Scope (Deferred)

- **SOAR-powered decomposition** (Phase 2) - Plan files generated from rule-based templates
- **Memory-aware context** (Phase 2) - File path resolution via semantic search
- **Agent recommendation** (Phase 2) - Manifest integration for agent assignment
- **Plan execution** (Phase 3) - Task orchestration and checkpoint/resume
- **AI-driven file generation** (Phase 2+) - LLM integration for content generation
- **Full `aur init` framework** (Phase 2) - Defer all configuration generation

---

## Design Decisions

### Architecture

**Package Structure**:
```
packages/planning/
  src/aurora_planning/
    __init__.py
    commands/          # CLI commands
      archive.py
      create.py
      init.py
      list.py
      view.py
    parsers/           # Markdown/JSON parsing
      markdown.py
      requirements.py
      metadata.py
    schemas/           # Pydantic models
      plan.py
      validation.py
    validators/        # Plan validation
      __init__.py
    templates/         # Jinja2 templates
      plan.md.j2
      prd.md.j2
      tasks.md.j2
    configurators/     # Tool configuration
      base.py
      claude_code.py
      opencode.py
      ampcode.py
      droid.py
    config.py          # Configuration module
  pyproject.toml
  tests/
    unit/
    integration/
```

**Directory Layout**:
```
~/.aurora/
  plans/
    active/
      0001-oauth2-auth/
        plan.md
        prd.md
        tasks.md
        agents.json
      0002-logging/
    archive/
      2026-01-02-0001-oauth2-auth/
    manifest.json
  config.json
```

### Plan ID Format

- Format: `NNNN-slug`
- NNNN: 4-digit zero-padded auto-increment from manifest
- slug: Kebab-case derived from goal (max 50 chars)
- Example: `0001-implement-oauth2-authentication`

### Four-File Workflow

Each plan contains:

| File | Purpose | Format | Generator |
|------|---------|--------|-----------|
| `plan.md` | High-level decomposition | Markdown | Jinja2 template |
| `prd.md` | Detailed requirements | OpenSpec format | Jinja2 template |
| `tasks.md` | Implementation checklist | GFM checklist | Jinja2 template |
| `agents.json` | Machine-readable metadata | JSON/Pydantic | Generated from schema |

**Schema Design Principles**:
- `agents.json`: Pydantic model with strict validation (immutable once created)
- Markdown files: Human-editable, templated on creation, no runtime validation
- Subgoal structure: Designed for Phase 2 agent assignment integration

### Test Migration Strategy

**Source**: 284 tests from OpenSpec (verified passing)
**Target Structure**:
- `tests/unit/planning/` - Unit tests for all modules (estimated 200+ tests)
- `tests/integration/planning/` - Integration tests for workflows (estimated 80+ tests)

**Approach**:
- Reuse all existing tests without modification
- Update import statements: `openspec` → `aurora.planning`
- Adapt fixtures for Aurora directory structure (`.aurora/plans/` instead of `openspec/`)
- Fill coverage gaps only for Aurora-specific integration (manifest, CLI)
- Target: ≥95% coverage maintained, 100% test pass rate

### Configuration Approach

**Phase 1 Scope**:
- Integrate existing OpenSpec config module (~100 lines)
- Generate tool configs during `aur plan init`
- Support MCP protocol for Claude Code (primary)
- Research tool-specific config paths for OpenCode, AmpCode, Droid

**Phase 2 Deferral**:
- Full `aur init` framework configuration
- Interactive config wizard
- Tool-specific feature discovery
- Configuration validation and repair

---

## Requirements Mapping

### Capability: `planning-core`

The core planning package with all commands and file generation.

**Requirements**:
1. Package structure created at `packages/planning/src/aurora_planning/`
2. All Python modules importable via `from aurora.planning import ...`
3. Import statements updated: `openspec` → `aurora.planning`
4. 284 tests migrated and passing with ≥95% coverage
5. Package metadata configured in `pyproject.toml`
6. Directory structure uses `~/.aurora/plans/` (not `openspec/`)

**Dependencies**:
- `aurora-core>=0.2.0` - Shared utilities
- `pydantic>=2.0` - Schema validation
- `jinja2>=3.1` - Template rendering
- `python-slugify>=8.0` - Plan ID generation

### Capability: `planning-commands`

The five planning commands accessible via CLI.

**Requirements**:
1. `aur plan init` - Creates directory structure and manifest
2. `aur plan create <goal>` - Generates plan with 4-file output
3. `aur plan list [--archived] [--all]` - Displays plan summaries
4. `aur plan view <plan-id>` - Shows detailed dashboard
5. `aur plan archive <plan-id>` - Archives completed plans
6. All commands return structured results with success/error details
7. Performance: init <100ms, create <5s, list <500ms, view/archive <1s

### Capability: `planning-schemas`

JSON/Pydantic schemas for plan metadata and validation.

**Requirements**:
1. `AgentMetadata` Pydantic model with strict validation
2. `Subgoal` model for decomposition tracking
3. JSON Schema export for external validation
4. Validators for plan ID format, timestamps, subgoal uniqueness
5. Model docstrings included for auto-generated API reference

### Capability: `planning-templates`

Jinja2 templates for four-file generation.

**Requirements**:
1. `plan.md.j2` - High-level decomposition template
2. `prd.md.j2` - Detailed requirements template
3. `tasks.md.j2` - Implementation checklist template
4. All templates render without errors
5. Generated files pass format validation
6. Template comments document Phase 2 integration points

### Capability: `planning-configurators`

Multi-tool slash command configuration generation.

**Requirements**:
1. Config module imports available: `from aurora.planning.configurators import ...`
2. Claude Code config generation (MCP protocol)
3. OpenCode, AmpCode, Droid config generation (research tool paths)
4. Config validation against tool-specific schemas
5. Backup creation before file modification
6. Merge with existing configs (don't overwrite other sections)

### Capability: `planning-docs`

User and API documentation.

**Requirements**:
1. README with quick start (under 2 minutes to first plan)
2. API reference auto-generated from docstrings
3. User guide covering all workflows and troubleshooting
4. Integration guide for each tool (Claude Code, OpenCode, AmpCode, Droid)
5. Examples directory with sample plans

---

## Testing Strategy

### Unit Tests (≥95% target)

- **Module tests**: All parsers, validators, schemas (~150+ tests from OpenSpec)
- **Command tests**: Each command's core logic in isolation (~50+ tests)
- **Schema validation**: Pydantic model instantiation and validation (~30+ tests)
- **Template rendering**: Jinja2 template output validation (~20+ tests)

### Integration Tests

- **Workflow tests**: End-to-end command sequences:
  - `init` → `create` → `list` → `view` → `archive`
  - Plan ID generation and manifest updates
  - Directory creation and cleanup
- **File generation**: 4-file output validation and schema compliance
- **Configuration**: Tool config generation and merge behavior
- **Error handling**: Command failures and recovery paths

### Acceptance Tests (Manual)

- Slash command execution in each tool (Claude Code primary, others research-based)
- Cross-platform directory structure (Linux, macOS, Windows)
- Performance benchmarking against aspirational targets

---

## Migration Plan

### Phase 1A: Preparation (Day 1-2)

1. **Scaffold package structure**: Create `packages/planning/` with subdirectories
2. **Copy OpenSpec code**: Migrate source from `/tmp/openspec-source/aurora/`
3. **Update imports**: Global search/replace `openspec` → `aurora.planning`
4. **Configure package metadata**: Set up `pyproject.toml` with dependencies

### Phase 1B: Test Migration (Day 2-3)

1. **Organize test directories**: Create `tests/unit/planning/` and `tests/integration/planning/`
2. **Copy test files**: Migrate all 284 tests
3. **Update test imports**: `openspec` → `aurora.planning`
4. **Adapt fixtures**: Update directory paths to `.aurora/plans/`
5. **Run test suite**: Verify 100% pass rate, ≥95% coverage

### Phase 1C: Commands & CLI (Day 3-4)

1. **Implement plan ID generation**: Auto-increment from manifest
2. **Implement `aur plan` CLI group**: Register commands with Click/Typer
3. **Integrate commands** into Aurora CLI: Wire up to main `aur` entry point
4. **Test command workflows**: End-to-end testing

### Phase 1D: Configuration (Day 4-5)

1. **Copy config module**: Integrate OpenSpec configurators
2. **Implement Claude Code config**: Generate MCP server config
3. **Research tool paths**: OpenCode, AmpCode, Droid config locations
4. **Implement tool generators**: Create config generation for remaining tools
5. **Test configuration**: Verify file generation and merging

### Phase 1E: Documentation (Day 5)

1. **Write README**: Quick start, examples, key concepts
2. **Generate API reference**: Extract from docstrings
3. **Create user guide**: Workflows, troubleshooting, examples
4. **Write integration guides**: Tool-specific setup instructions

### Phase 1F: Validation (Day 5-6)

1. **Quality checks**: Type checking, linting, test coverage
2. **Performance benchmarking**: Measure against aspirational targets
3. **Cross-platform testing**: Linux, macOS, Windows (if applicable)
4. **Documentation review**: Completeness and accuracy

---

## Success Criteria

### Functional Success

- [ ] 284 OpenSpec tests passing in new `aurora.planning` package location
- [ ] All 5 planning commands functional: `init`, `create`, `list`, `view`, `archive`
- [ ] Four-file workflow generates valid output matching schemas
- [ ] Tool configurations generated for all 4 tools (Claude Code, OpenCode, AmpCode, Droid)
- [ ] Performance targets met: init <100ms, create <5s, list <500ms, view/archive <1s

### Quality Success

- [ ] ≥95% test coverage in `aurora.planning` package
- [ ] 0 type errors (mypy strict mode)
- [ ] 0 linting violations (ruff)
- [ ] All docstrings present and accurate
- [ ] No remaining `openspec` references in code

### Documentation Success

- [ ] README with quick start (testable in <5 minutes)
- [ ] API reference complete and auto-generated
- [ ] User guide covers all workflows
- [ ] Integration guides for all 4 tools
- [ ] Examples directory with sample plans

---

## Risks and Mitigations

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|-----------|
| Test migration incomplete | Some tests fail, coverage drops | Low | Systematic import/fixture updates, verification step before completion |
| Tool config paths unknown | Some tools can't be configured | Medium | Research task during Phase 1C, fallback to documentation-only for Phase 1 |
| Performance targets missed | Users experience slow planning | Low | Profile and optimize hot paths, aspirational targets are non-blocking |
| Import cycles created | Package fails to load | Low | Careful attention to circular dependencies, test imports early |
| Backward compatibility break | Existing code breaks | Low | This is a new package, no existing Aurora code depends on it |

---

## Dependencies

### External

- OpenSpec refactored code at `/tmp/openspec-source/aurora/` (must remain available)
- Python 3.12+ (Aurora platform requirement)
- Pydantic v2, Jinja2, python-slugify (added to `pyproject.toml`)

### Internal

- `aurora.core` - For shared utilities (import verified before package publish)
- `aurora.cli` - Integration point for `aur plan` command group
- `aurora.config` - For config file management

### Coordination

- **Phase 0.5 completion**: OpenSpec refactoring complete and stable
- **Phase 2 planning**: Coordinate handoff of decomposition logic
- **Documentation team**: Update main README with planning system overview

---

## Open Questions

1. **Tool Configuration Paths**
   - What are the exact config file paths for OpenCode, AmpCode, Droid?
   - Do these tools follow MCP protocol or custom schema?
   - Can we test config generation without actual tool installation?

2. **Plan Naming**
   - Is `NNNN-slug` format preferred or should we use UUIDs?
   - Should plan IDs be re-sequential or globally unique?
   - What's the maximum slug length?

3. **Manifest Location**
   - Should manifest live at `~/.aurora/plans/manifest.json` or `~/.aurora/config.json` (nested)?
   - How should manifest handle concurrent plan creation (race conditions)?

4. **Performance Targets**
   - Are the aspirational targets critical or nice-to-have?
   - Which operations are most performance-sensitive?

---

## Next Steps

1. **Resolve open questions** via stakeholder review
2. **Generate detailed task list** from this proposal using `2-generate-tasks`
3. **Begin Phase 1A** (package structure scaffolding)
4. **Track progress** through `/tasks/tasks-0017-PH1-aurora-planning-system.md`

---

## References

- PRD: `/tasks/0017-prd-phase1-foundation.md` (1,985 lines, comprehensive)
- Strategic Spec: `/tasks/0017-planning-specs-v2.md` (21KB, 3-phase roadmap)
- OpenSpec Refactoring: `/tmp/openspec-source/aurora/` (284 tests, ready for migration)
- Phase 1 Tasks: `/tasks/tasks-0017-PH1-aurora-planning-system.md` (tracking document)

---

## Appendix: File Checklist

**Migration Files** (from OpenSpec):
- [ ] `commands/archive.py`
- [ ] `commands/create.py`
- [ ] `commands/init.py`
- [ ] `commands/list.py`
- [ ] `commands/view.py`
- [ ] `parsers/markdown.py`
- [ ] `parsers/requirements.py`
- [ ] `parsers/metadata.py`
- [ ] `schemas/plan.py`
- [ ] `schemas/validation.py`
- [ ] `validators/__init__.py`
- [ ] `templates/plan.md.j2`
- [ ] `templates/prd.md.j2`
- [ ] `templates/tasks.md.j2`
- [ ] `configurators/base.py`
- [ ] `configurators/claude_code.py`
- [ ] `configurators/opencode.py`
- [ ] `configurators/ampcode.py`
- [ ] `configurators/droid.py`
- [ ] `config.py`

**New Aurora Files**:
- [ ] `packages/planning/pyproject.toml`
- [ ] `packages/planning/src/aurora_planning/__init__.py`
- [ ] All 284 tests in `tests/unit/planning/` and `tests/integration/planning/`
- [ ] README at `packages/planning/README.md`
- [ ] Integration guides in `docs/planning/`
