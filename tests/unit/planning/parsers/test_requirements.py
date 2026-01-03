"""
Tests for requirements block parsing utilities.

Ported from: src/core/parsers/requirement-blocks.ts
TDD approach: Tests written first based on TypeScript behavior.

Task: 3.3 - Write tests/unit/parsers/test_requirements.py
"""

import pytest

from aurora_planning.parsers.requirements import (
    RequirementBlock,
    RequirementsSectionParts,
    ModificationPlan,
    extract_requirements_section,
    normalize_requirement_name,
    parse_modification_spec,
)


class TestNormalizeRequirementName:
    """Test cases for normalize_requirement_name()."""

    def test_trims_whitespace(self):
        """Should trim whitespace from requirement name."""
        assert normalize_requirement_name("  Test Requirement  ") == "Test Requirement"

    def test_handles_normal_name(self):
        """Should handle normal name without extra whitespace."""
        assert normalize_requirement_name("Valid Name") == "Valid Name"

    def test_handles_empty_string(self):
        """Should handle empty string."""
        assert normalize_requirement_name("") == ""


class TestExtractRequirementsSection:
    """Test cases for extract_requirements_section()."""

    def test_extracts_requirements_section(self):
        """Should extract the requirements section from content."""
        content = """# Test Spec

## Purpose
This is the purpose.

## Requirements

### Requirement: First Requirement
The system SHALL do something.

#### Scenario: Test
Given test
When action
Then result

### Requirement: Second Requirement
The system MUST do another thing.

#### Scenario: Another
Given another
When acting
Then resulting

## Notes
Some notes here."""

        parts = extract_requirements_section(content)

        assert "## Purpose" in parts.before
        assert parts.header_line == "## Requirements"
        assert len(parts.body_blocks) == 2
        assert parts.body_blocks[0].name == "First Requirement"
        assert parts.body_blocks[1].name == "Second Requirement"
        assert "## Notes" in parts.after

    def test_handles_missing_requirements_section(self):
        """Should create empty requirements section if missing."""
        content = """# Test Spec

## Purpose
This is the purpose."""

        parts = extract_requirements_section(content)

        assert parts.header_line == "## Requirements"
        assert len(parts.body_blocks) == 0
        assert parts.preamble == ""

    def test_extracts_preamble(self):
        """Should extract preamble content before first requirement."""
        content = """# Test Spec

## Requirements

This is the preamble text.

### Requirement: First
The system SHALL work."""

        parts = extract_requirements_section(content)

        assert "preamble text" in parts.preamble
        assert len(parts.body_blocks) == 1

    def test_handles_crlf_line_endings(self):
        """Should handle CRLF line endings."""
        content = "# Test Spec\r\n\r\n## Requirements\r\n\r\n### Requirement: Test\r\nContent"

        parts = extract_requirements_section(content)

        assert len(parts.body_blocks) == 1
        assert parts.body_blocks[0].name == "Test"


class TestParseModificationSpec:
    """Test cases for parse_modification_spec() (was parseDeltaSpec)."""

    def test_parses_added_requirements(self):
        """Should parse ADDED Requirements section."""
        content = """# Test Spec

## ADDED Requirements

### Requirement: New Feature
The system SHALL implement the new feature.

#### Scenario: Works
Given setup
When action
Then result
"""

        plan = parse_modification_spec(content)

        assert plan.section_presence["added"] is True
        assert len(plan.added) == 1
        assert plan.added[0].name == "New Feature"

    def test_parses_modified_requirements(self):
        """Should parse MODIFIED Requirements section."""
        content = """# Test Spec

## MODIFIED Requirements

### Requirement: Updated Feature
The system MUST now handle edge cases.

#### Scenario: Edge case
Given edge
When handled
Then works
"""

        plan = parse_modification_spec(content)

        assert plan.section_presence["modified"] is True
        assert len(plan.modified) == 1
        assert plan.modified[0].name == "Updated Feature"

    def test_parses_removed_requirements(self):
        """Should parse REMOVED Requirements section."""
        content = """# Test Spec

## REMOVED Requirements

### Requirement: Deprecated Feature
"""

        plan = parse_modification_spec(content)

        assert plan.section_presence["removed"] is True
        assert "Deprecated Feature" in plan.removed

    def test_parses_renamed_requirements(self):
        """Should parse RENAMED Requirements section."""
        content = """# Test Spec

## RENAMED Requirements

- FROM: `### Requirement: Old Name`
- TO: `### Requirement: New Name`
"""

        plan = parse_modification_spec(content)

        assert plan.section_presence["renamed"] is True
        assert len(plan.renamed) == 1
        assert plan.renamed[0]["from"] == "Old Name"
        assert plan.renamed[0]["to"] == "New Name"

    def test_parses_multiple_sections(self):
        """Should parse multiple delta sections."""
        content = """# Test Spec

## ADDED Requirements

### Requirement: New One
The system SHALL add new one.

## MODIFIED Requirements

### Requirement: Updated One
The system MUST update this.

## REMOVED Requirements

### Requirement: Old One
"""

        plan = parse_modification_spec(content)

        assert plan.section_presence["added"] is True
        assert plan.section_presence["modified"] is True
        assert plan.section_presence["removed"] is True
        assert len(plan.added) == 1
        assert len(plan.modified) == 1
        assert "Old One" in plan.removed

    def test_handles_empty_content(self):
        """Should handle empty content gracefully."""
        content = ""

        plan = parse_modification_spec(content)

        assert len(plan.added) == 0
        assert len(plan.modified) == 0
        assert len(plan.removed) == 0
        assert len(plan.renamed) == 0

    def test_case_insensitive_section_headers(self):
        """Should handle case-insensitive section headers."""
        content = """# Test Spec

## Added Requirements

### Requirement: Test Feature
The system SHALL work.
"""

        plan = parse_modification_spec(content)

        assert plan.section_presence["added"] is True
        assert len(plan.added) == 1

    def test_parses_bullet_list_removed(self):
        """Should parse removed requirements in bullet list format."""
        content = """# Test Spec

## REMOVED Requirements

- `### Requirement: First Removed`
- `### Requirement: Second Removed`
"""

        plan = parse_modification_spec(content)

        assert "First Removed" in plan.removed
        assert "Second Removed" in plan.removed
