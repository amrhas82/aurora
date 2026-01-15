"""Tests for MarkdownParser.

Ported from: test/core/parsers/markdown-parser.test.ts
TDD approach: Tests written first based on TypeScript test behavior.

Task: 3.1 - Write tests/unit/parsers/test_markdown.py
"""

import pytest

from aurora_planning.parsers.markdown import MarkdownParser


class TestMarkdownParserParseCapability:
    """Test cases for MarkdownParser.parse_capability() (was parseSpec)."""

    def test_parses_valid_capability(self):
        """Should parse a valid capability (was spec)."""
        content = """# User Authentication Spec

## Purpose
This specification defines the requirements for user authentication.

## Requirements

### The system SHALL provide secure user authentication
Users need to be able to log in securely.

#### Scenario: Successful login
Given a user with valid credentials
When they submit the login form
Then they are authenticated

### The system SHALL handle invalid login attempts
The system must handle incorrect credentials.

#### Scenario: Invalid credentials
Given a user with invalid credentials
When they submit the login form
Then they see an error message"""

        parser = MarkdownParser(content)
        capability = parser.parse_capability("user-auth")

        assert capability.name == "user-auth"
        assert "requirements for user authentication" in capability.overview
        assert len(capability.requirements) == 2

        first_req = capability.requirements[0]
        assert first_req.text == "Users need to be able to log in securely."
        assert len(first_req.scenarios) == 1

        scenario = first_req.scenarios[0]
        assert "Given a user with valid credentials" in scenario.raw_text
        assert "When they submit the login form" in scenario.raw_text
        assert "Then they are authenticated" in scenario.raw_text

    def test_handles_multiline_scenarios(self):
        """Should handle multi-line scenarios."""
        content = """# Test Spec

## Purpose
Test overview

## Requirements

### The system SHALL handle complex scenarios
This requirement has content.

#### Scenario: Multi-line scenario
Given a user with valid credentials
  and the user has admin privileges
  and the system is in maintenance mode
When they attempt to login
  and provide their MFA token
Then they are authenticated
  and redirected to admin dashboard
  and see a maintenance warning"""

        parser = MarkdownParser(content)
        capability = parser.parse_capability("test")

        scenario = capability.requirements[0].scenarios[0]
        assert "Given a user with valid credentials" in scenario.raw_text
        assert "and the user has admin privileges" in scenario.raw_text
        assert "When they attempt to login" in scenario.raw_text
        assert "and provide their MFA token" in scenario.raw_text
        assert "Then they are authenticated" in scenario.raw_text
        assert "and see a maintenance warning" in scenario.raw_text

    def test_throws_error_for_missing_overview(self):
        """Should throw error for missing overview (Purpose section)."""
        content = """# Test Spec

## Requirements

### The system SHALL do something

#### Scenario: Test
Given test
When action
Then result"""

        parser = MarkdownParser(content)
        with pytest.raises(ValueError, match="must have a Purpose section"):
            parser.parse_capability("test")

    def test_throws_error_for_missing_requirements(self):
        """Should throw error for missing requirements."""
        content = """# Test Spec

## Purpose
This is a test spec"""

        parser = MarkdownParser(content)
        with pytest.raises(ValueError, match="must have a Requirements section"):
            parser.parse_capability("test")


class TestMarkdownParserParsePlan:
    """Test cases for MarkdownParser.parse_plan() (was parseChange)."""

    def test_parses_valid_plan(self):
        """Should parse a valid plan (was change)."""
        content = """# Add User Authentication

## Why
We need to implement user authentication to secure the application and protect user data from unauthorized access.

## What Changes
- **user-auth:** Add new user authentication specification
- **api-endpoints:** Modify to include authentication endpoints
- **database:** Remove old session management tables"""

        parser = MarkdownParser(content)
        plan = parser.parse_plan("add-user-auth")

        assert plan.name == "add-user-auth"
        assert "secure the application" in plan.why
        assert "user-auth" in plan.what_changes
        assert len(plan.modifications) == 3

        assert plan.modifications[0].capability == "user-auth"
        assert plan.modifications[0].operation.value == "ADDED"
        assert "Add new user authentication" in plan.modifications[0].description

        assert plan.modifications[1].capability == "api-endpoints"
        assert plan.modifications[1].operation.value == "MODIFIED"

        assert plan.modifications[2].capability == "database"
        assert plan.modifications[2].operation.value == "REMOVED"

    def test_throws_error_for_missing_why_section(self):
        """Should throw error for missing why section."""
        content = """# Test Change

## What Changes
- **test:** Add test"""

        parser = MarkdownParser(content)
        with pytest.raises(ValueError, match="must have a Why section"):
            parser.parse_plan("test")

    def test_throws_error_for_missing_what_changes_section(self):
        """Should throw error for missing what changes section."""
        content = """# Test Change

## Why
Because we need it"""

        parser = MarkdownParser(content)
        with pytest.raises(ValueError, match="must have a What Changes section"):
            parser.parse_plan("test")

    def test_handles_plans_without_modifications(self):
        """Should handle plans (changes) without modifications (deltas)."""
        content = """# Test Change

## Why
We need to make some changes for important reasons that justify this work.

## What Changes
Some general description of changes without specific deltas"""

        parser = MarkdownParser(content)
        plan = parser.parse_plan("test")

        assert len(plan.modifications) == 0

    def test_parses_crlf_line_endings(self):
        """Parses plan documents saved with CRLF line endings."""
        content = "\r\n".join(
            [
                "# CRLF Change",
                "",
                "## Why",
                "Reasons on Windows editors should parse like POSIX environments.",
                "",
                "## What Changes",
                "- **alpha:** Add cross-platform parsing coverage",
            ]
        )

        parser = MarkdownParser(content)
        plan = parser.parse_plan("crlf-change")

        assert "Windows editors should parse" in plan.why
        assert len(plan.modifications) == 1
        assert plan.modifications[0].capability == "alpha"


class TestMarkdownParserSectionParsing:
    """Test cases for section parsing functionality."""

    def test_handles_nested_sections_correctly(self):
        """Should handle nested sections correctly."""
        content = """# Test Spec

## Purpose
This is the overview section for testing nested sections.

## Requirements

### The system SHALL handle nested sections

#### Scenario: Test nested
Given a nested structure
When parsing sections
Then handle correctly

### Another requirement SHALL work

#### Scenario: Another test
Given another test
When running
Then success"""

        parser = MarkdownParser(content)
        capability = parser.parse_capability("test")

        assert capability is not None
        assert "testing nested sections" in capability.overview
        assert len(capability.requirements) == 2

    def test_preserves_content_between_headers(self):
        """Should preserve content between headers."""
        content = """# Test

## Purpose
This is the overview.
It has multiple lines.

Some more content here.

## Requirements

### Requirement 1
Content for requirement 1"""

        parser = MarkdownParser(content)
        capability = parser.parse_capability("test")

        assert "multiple lines" in capability.overview
        assert "more content" in capability.overview

    def test_uses_requirement_heading_as_fallback(self):
        """Should use requirement heading as fallback when no content is provided."""
        content = """# Test Spec

## Purpose
Test overview

## Requirements

### The system SHALL use heading text when no content

#### Scenario: Test
Given test
When action
Then result"""

        parser = MarkdownParser(content)
        capability = parser.parse_capability("test")

        assert (
            capability.requirements[0].text == "The system SHALL use heading text when no content"
        )

    def test_extracts_requirement_text_from_first_content_line(self):
        """Should extract requirement text from first non-empty content line."""
        content = """# Test Spec

## Purpose
Test overview

## Requirements

### Requirement heading

This is the actual requirement text.
This is additional description.

#### Scenario: Test
Given test
When action
Then result"""

        parser = MarkdownParser(content)
        capability = parser.parse_capability("test")

        assert capability.requirements[0].text == "This is the actual requirement text."
