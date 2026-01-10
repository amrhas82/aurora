"""
Tests for validation types: ValidationIssue, ValidationReport.

Ported from: src/core/validation/types.ts
TDD approach: Tests written first based on TypeScript interface behavior.

Task: 2.3 - Write tests/unit/validation/test_types.py
"""

import pytest

from aurora_planning.validators.types import ValidationIssue, ValidationLevel, ValidationReport


class TestValidationLevel:
    """Test cases for ValidationLevel enum."""

    def test_valid_levels(self):
        """Should have correct level values."""
        assert ValidationLevel.ERROR == "ERROR"
        assert ValidationLevel.WARNING == "WARNING"
        assert ValidationLevel.INFO == "INFO"


class TestValidationIssue:
    """Test cases for ValidationIssue model."""

    def test_creates_issue_with_required_fields(self):
        """Should create issue with required fields."""
        issue = ValidationIssue(
            level=ValidationLevel.ERROR,
            path="requirements/0",
            message="Requirement must contain SHALL or MUST",
        )
        assert issue.level == ValidationLevel.ERROR
        assert issue.path == "requirements/0"
        assert "SHALL" in issue.message

    def test_creates_issue_with_optional_line_column(self):
        """Should create issue with optional line and column."""
        issue = ValidationIssue(
            level=ValidationLevel.WARNING,
            path="overview",
            message="Purpose section is too brief",
            line=5,
            column=1,
        )
        assert issue.line == 5
        assert issue.column == 1

    def test_issue_without_optional_fields(self):
        """Should allow issue without line and column."""
        issue = ValidationIssue(
            level=ValidationLevel.INFO,
            path="metadata",
            message="Some info message",
        )
        assert issue.line is None
        assert issue.column is None


class TestValidationReport:
    """Test cases for ValidationReport model."""

    def test_creates_valid_report(self):
        """Should create a valid report with no issues."""
        report = ValidationReport(valid=True, issues=[])
        assert report.valid is True
        assert len(report.issues) == 0
        assert report.summary.errors == 0
        assert report.summary.warnings == 0
        assert report.summary.info == 0

    def test_creates_invalid_report_with_errors(self):
        """Should create an invalid report with errors."""
        issues = [
            ValidationIssue(
                level=ValidationLevel.ERROR,
                path="requirements/0",
                message="Missing SHALL/MUST",
            ),
            ValidationIssue(
                level=ValidationLevel.ERROR,
                path="requirements/1",
                message="No scenarios",
            ),
        ]
        report = ValidationReport(valid=False, issues=issues)
        assert report.valid is False
        assert len(report.issues) == 2
        assert report.summary.errors == 2
        assert report.summary.warnings == 0

    def test_creates_report_with_mixed_issues(self):
        """Should create report with mixed issue levels."""
        issues = [
            ValidationIssue(level=ValidationLevel.ERROR, path="name", message="Name empty"),
            ValidationIssue(level=ValidationLevel.WARNING, path="overview", message="Too brief"),
            ValidationIssue(level=ValidationLevel.INFO, path="metadata", message="Info note"),
        ]
        report = ValidationReport(valid=False, issues=issues)
        assert report.summary.errors == 1
        assert report.summary.warnings == 1
        assert report.summary.info == 1

    def test_report_auto_calculates_summary(self):
        """Should auto-calculate summary from issues."""
        issues = [
            ValidationIssue(level=ValidationLevel.WARNING, path="a", message="warn 1"),
            ValidationIssue(level=ValidationLevel.WARNING, path="b", message="warn 2"),
            ValidationIssue(level=ValidationLevel.WARNING, path="c", message="warn 3"),
        ]
        report = ValidationReport(valid=True, issues=issues)
        assert report.summary.errors == 0
        assert report.summary.warnings == 3
        assert report.summary.info == 0
