# Specification: Planning Core Package

**Capability**: `planning-core`
**Status**: Specification
**Change ID**: `phase1-planning-foundation`
**Version**: 1.0

---

## Summary

The Aurora Planning Core package provides the foundational infrastructure for creating, managing, and organizing structured plans. Phase 1 establishes the package structure, test infrastructure, and directory conventions without adding AI-powered decomposition (Phase 2).

---

## ADDED Requirements

### Requirement: Package Structure and Organization

**Category**: Infrastructure

**Description**: The Aurora Planning Core is organized as a Python namespace package with standardized module organization.

The planning package SHALL be structured to enable modular development, testing, and maintenance while maintaining compatibility with Aurora's namespace package conventions.

#### Scenario: Package Structure Created

**Given** I am migrating OpenSpec source code to Aurora
**When** I create the package directory structure
**Then**:
- Package is located at `packages/planning/src/aurora_planning/`
- Namespace configuration allows import as `from aurora.planning import ...`
- Module organization preserves OpenSpec structure:
  - `commands/` - CLI command implementations
  - `parsers/` - Markdown and metadata parsing
  - `schemas/` - Pydantic data models
  - `validators/` - Plan validation logic
  - `templates/` - Jinja2 templates for file generation
  - `configurators/` - Tool-specific configuration generators
- All modules are importable and functional

#### Scenario: Cross-Package Imports Work

**Given** the planning core is integrated into Aurora
**When** code imports utilities from other Aurora packages
**Then**:
- Imports use `from aurora.*` namespace (e.g., `from aurora.core import ...`)
- No references to `openspec` remain in import statements
- Import resolution succeeds for all cross-package dependencies
- Type checking (mypy) passes in strict mode

---

### Requirement: Package Metadata and Dependencies

**Category**: Configuration

**Description**: The planning package is properly configured with all required metadata and dependencies.

Configuration in `pyproject.toml` SHALL declare all dependencies, versioning, and namespace package information needed for proper installation and integration with Aurora.

#### Scenario: Package Configuration

**Given** the planning package needs to be installable
**When** I configure `pyproject.toml`
**Then**:
- Package name is `aurora-planning`
- Version matches Aurora core: `0.2.0`
- Dependencies declared:
  - `pydantic>=2.0` - Schema validation
  - `jinja2>=3.1` - Template rendering
  - `python-slugify>=8.0` - Plan ID generation
  - `aurora-core>=0.2.0` - Shared utilities
- Namespace package is configured correctly
- Package can be installed: `pip install -e .`

---

### Requirement: Test Suite Migration

**Category**: Quality Assurance

**Description**: All 284 OpenSpec tests are migrated to Aurora test structure with import updates and fixture adaptations.

The test migration SHALL preserve all test logic while updating imports and fixtures to work with Aurora's directory structure and conventions, ensuring comprehensive coverage and reliability.

#### Scenario: All Tests Passing

**Given** 284 OpenSpec tests exist
**When** I migrate tests to `tests/unit/planning/` and `tests/integration/planning/`
**Then**:
- All 284 tests are executable: `pytest tests/*/planning/`
- All tests pass with 100% success rate
- Test coverage for `aurora.planning` is ≥95%
- No tests are skipped due to missing dependencies
- Test imports reference `aurora.planning` (not `openspec`)

#### Scenario: Test Fixtures Adapted

**Given** tests need to work with Aurora directory structure
**When** I adapt test fixtures
**Then**:
- Fixtures use `~/.aurora/plans/` as root directory
- `active/` and `archive/` subdirectories used correctly
- Manifest file location: `~/.aurora/plans/manifest.json`
- Temporary test directories are cleaned up after tests
- No test pollution between test runs

---

### Requirement: Directory Structure Conventions

**Category**: Architecture

**Description**: The planning system uses standardized directory conventions for organization and lifecycle management.

The directory structure SHALL organize plans into active and archived directories with predictable naming conventions that support browsing, archival, and lifecycle tracking.

#### Scenario: Directory Structure Created

**Given** the user initializes planning
**When** I create the directory structure
**Then**:
- Root directory: `~/.aurora/plans/`
- Active plans: `~/.aurora/plans/active/`
- Archived plans: `~/.aurora/plans/archive/`
- Each plan has a unique directory: `NNNN-slug/` format
- Directory permissions are set appropriately (mode 0755)

#### Scenario: Plan Archiving Preserves History

**Given** a plan is completed
**When** I archive the plan
**Then**:
- Plan directory is moved to `archive/`
- Archive path follows format: `YYYY-MM-DD-NNNN-slug/`
- Timestamp reflects completion date
- Original plan content is fully preserved
- Plan is no longer listed in active plans

---

## MODIFIED Requirements

*No modifications to existing requirements (this is Phase 1 foundation)*

---

## REMOVED Requirements

*No requirements removed (Phase 1 is additive)*

---

## Context

### Related Capabilities

- `planning-commands` - CLI command implementations using this core
- `planning-schemas` - Data models and validation
- `planning-templates` - File generation templates
- `planning-configurators` - Tool-specific configuration

### Acceptance Criteria for Phase 1

1. Package structure created and importable
2. All 284 tests migrated and passing
3. ≥95% test coverage
4. 0 type errors (mypy strict mode)
5. 0 linting violations (ruff)
6. Directory conventions documented and tested

### Acceptance Criteria for Phase 2

- Phase 2 will add SOAR-powered decomposition
- Phase 2 will add memory-aware context integration
- Core package structure remains stable (no breaking changes)
