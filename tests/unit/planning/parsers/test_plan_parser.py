"""Tests for PlanParser (was ChangeParser).

Ported from: src/core/parsers/change-parser.ts behavior
TDD approach: Tests written first based on TypeScript behavior.

Task: 3.2 - Write tests/unit/parsers/test_plan_parser.py
"""

import tempfile
from pathlib import Path

from aurora_planning.parsers.plan_parser import PlanParser
from aurora_planning.schemas.plan import ModificationOperation


class TestPlanParserParseWithModifications:
    """Test cases for PlanParser.parse_plan_with_modifications()."""

    def test_parses_plan_with_simple_modifications(self):
        """Should parse plan with modifications from What Changes section."""
        content = """# Add User Authentication

## Why
We need to implement user authentication to secure the application and protect user data from unauthorized access.

## What Changes
- **user-auth:** Add new user authentication specification
- **api-endpoints:** Modify to include authentication endpoints
- **database:** Remove old session management tables"""

        with tempfile.TemporaryDirectory() as tmpdir:
            plan_dir = Path(tmpdir)
            parser = PlanParser(content, str(plan_dir))
            plan = parser.parse_plan_with_modifications("add-user-auth")

            assert plan.name == "add-user-auth"
            assert len(plan.modifications) == 3
            assert plan.modifications[0].capability == "user-auth"
            assert plan.modifications[0].operation == ModificationOperation.ADDED

    def test_parses_plan_with_delta_spec_files(self):
        """Should parse plan with delta spec files from specs/ directory."""
        content = """# Add Circuit Breaker

## Why
We need to implement circuit breaker pattern to handle service failures gracefully.

## What Changes
- **circuit-breaker:** Add new circuit breaker specification"""

        delta_spec_content = """# Circuit Breaker

## ADDED Requirements

### Requirement: Circuit Breaker State Management
**ID**: REQ-CB-001

The system SHALL implement a circuit breaker with three states.

#### Scenario: Normal operation
Given the circuit breaker is in CLOSED state
When a request is made
Then the request is executed normally
"""

        with tempfile.TemporaryDirectory() as tmpdir:
            plan_dir = Path(tmpdir)
            specs_dir = plan_dir / "specs" / "circuit-breaker"
            specs_dir.mkdir(parents=True)

            spec_file = specs_dir / "spec.md"
            spec_file.write_text(delta_spec_content)

            parser = PlanParser(content, str(plan_dir))
            plan = parser.parse_plan_with_modifications("add-circuit-breaker")

            assert plan.name == "add-circuit-breaker"
            # Should have modifications from delta spec file
            assert len(plan.modifications) >= 1
            # First modification should be from delta spec
            added_mods = [
                m for m in plan.modifications if m.operation == ModificationOperation.ADDED
            ]
            assert len(added_mods) >= 1

    def test_handles_missing_specs_directory(self):
        """Should handle case when specs directory doesn't exist."""
        content = """# Simple Change

## Why
Making a simple change without detailed spec files.

## What Changes
- **simple:** Add simple feature"""

        with tempfile.TemporaryDirectory() as tmpdir:
            plan_dir = Path(tmpdir)
            parser = PlanParser(content, str(plan_dir))
            plan = parser.parse_plan_with_modifications("simple-change")

            assert plan.name == "simple-change"
            assert len(plan.modifications) == 1

    def test_combines_simple_and_delta_modifications(self):
        """Should combine modifications from What Changes and delta specs."""
        content = """# Combined Change

## Why
Testing combination of simple modifications and detailed delta specs.

## What Changes
- **feature-a:** Add feature A
- **feature-b:** Modify feature B"""

        delta_spec_content = """# Feature A

## ADDED Requirements

### Requirement: Feature A Core
The system SHALL implement feature A core functionality.

#### Scenario: Basic usage
Given the system is running
When feature A is invoked
Then it works correctly
"""

        with tempfile.TemporaryDirectory() as tmpdir:
            plan_dir = Path(tmpdir)
            specs_dir = plan_dir / "specs" / "feature-a"
            specs_dir.mkdir(parents=True)

            spec_file = specs_dir / "spec.md"
            spec_file.write_text(delta_spec_content)

            parser = PlanParser(content, str(plan_dir))
            plan = parser.parse_plan_with_modifications("combined-change")

            # Should have delta modifications (preferred) or simple ones
            assert len(plan.modifications) >= 1


class TestPlanParserDeltaOperations:
    """Test cases for parsing different delta operations."""

    def test_parses_added_requirements(self):
        """Should parse ADDED Requirements section."""
        content = """# Add Feature

## Why
Adding a new feature for better functionality.

## What Changes
- **new-feature:** Add new feature"""

        delta_spec_content = """# New Feature

## ADDED Requirements

### Requirement: New Feature Core
The system SHALL implement the new feature core.

#### Scenario: Feature works
Given the system
When using feature
Then it works
"""

        with tempfile.TemporaryDirectory() as tmpdir:
            plan_dir = Path(tmpdir)
            specs_dir = plan_dir / "specs" / "new-feature"
            specs_dir.mkdir(parents=True)
            (specs_dir / "spec.md").write_text(delta_spec_content)

            parser = PlanParser(content, str(plan_dir))
            plan = parser.parse_plan_with_modifications("add-feature")

            added = [m for m in plan.modifications if m.operation == ModificationOperation.ADDED]
            assert len(added) >= 1

    def test_parses_modified_requirements(self):
        """Should parse MODIFIED Requirements section."""
        content = """# Modify Feature

## Why
Modifying existing feature for improvements.

## What Changes
- **existing-feature:** Modify existing feature"""

        delta_spec_content = """# Existing Feature

## MODIFIED Requirements

### Requirement: Updated Behavior
The system SHALL now handle edge cases better.

#### Scenario: Edge case
Given an edge case
When handled
Then works correctly
"""

        with tempfile.TemporaryDirectory() as tmpdir:
            plan_dir = Path(tmpdir)
            specs_dir = plan_dir / "specs" / "existing-feature"
            specs_dir.mkdir(parents=True)
            (specs_dir / "spec.md").write_text(delta_spec_content)

            parser = PlanParser(content, str(plan_dir))
            plan = parser.parse_plan_with_modifications("modify-feature")

            modified = [
                m for m in plan.modifications if m.operation == ModificationOperation.MODIFIED
            ]
            assert len(modified) >= 1

    def test_parses_removed_requirements(self):
        """Should parse REMOVED Requirements section."""
        content = """# Remove Feature

## Why
Removing deprecated feature.

## What Changes
- **deprecated-feature:** Remove deprecated feature"""

        delta_spec_content = """# Deprecated Feature

## REMOVED Requirements

### Requirement: Old Behavior
The system no longer supports the old behavior.
"""

        with tempfile.TemporaryDirectory() as tmpdir:
            plan_dir = Path(tmpdir)
            specs_dir = plan_dir / "specs" / "deprecated-feature"
            specs_dir.mkdir(parents=True)
            (specs_dir / "spec.md").write_text(delta_spec_content)

            parser = PlanParser(content, str(plan_dir))
            plan = parser.parse_plan_with_modifications("remove-feature")

            removed = [
                m for m in plan.modifications if m.operation == ModificationOperation.REMOVED
            ]
            assert len(removed) >= 1

    def test_parses_renamed_requirements(self):
        """Should parse RENAMED Requirements section."""
        content = """# Rename Feature

## Why
Renaming feature for clarity.

## What Changes
- **renamed-feature:** Rename feature"""

        delta_spec_content = """# Renamed Feature

## RENAMED Requirements

- FROM: `### Requirement: Old Name`
- TO: `### Requirement: New Name`
"""

        with tempfile.TemporaryDirectory() as tmpdir:
            plan_dir = Path(tmpdir)
            specs_dir = plan_dir / "specs" / "renamed-feature"
            specs_dir.mkdir(parents=True)
            (specs_dir / "spec.md").write_text(delta_spec_content)

            parser = PlanParser(content, str(plan_dir))
            plan = parser.parse_plan_with_modifications("rename-feature")

            renamed = [
                m for m in plan.modifications if m.operation == ModificationOperation.RENAMED
            ]
            assert len(renamed) >= 1
