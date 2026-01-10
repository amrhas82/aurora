"""Unit tests for validation types module.

Tests ValidationLevel, ValidationIssue, ValidationSummary, and ValidationReport
Pydantic models to ensure correct validation and serialization.
"""

import pytest
from pydantic import ValidationError

from aurora_cli.planning.validation.types import (
    ValidationIssue,
    ValidationLevel,
    ValidationReport,
    ValidationSummary,
)


class TestValidationLevel:
    """Tests for ValidationLevel enum."""

    def test_validation_level_values(self):
        """Verify ValidationLevel has correct enum values."""
        assert ValidationLevel.ERROR.value == "ERROR"
        assert ValidationLevel.WARNING.value == "WARNING"
        assert ValidationLevel.INFO.value == "INFO"

    def test_validation_level_string_comparison(self):
        """Verify ValidationLevel can be compared as strings."""
        assert ValidationLevel.ERROR == "ERROR"
        assert ValidationLevel.WARNING == "WARNING"
        assert ValidationLevel.INFO == "INFO"


class TestValidationIssue:
    """Tests for ValidationIssue model."""

    def test_validation_issue_creation_minimal(self):
        """Test creating a ValidationIssue with minimal required fields."""
        issue = ValidationIssue(level=ValidationLevel.ERROR, path="test.md", message="Test error")
        assert issue.level == ValidationLevel.ERROR
        assert issue.path == "test.md"
        assert issue.message == "Test error"
        assert issue.line is None
        assert issue.column is None

    def test_validation_issue_creation_full(self):
        """Test creating a ValidationIssue with all fields."""
        issue = ValidationIssue(
            level=ValidationLevel.WARNING,
            path="docs/spec.md",
            message="Deprecated field used",
            line=42,
            column=10,
        )
        assert issue.level == ValidationLevel.WARNING
        assert issue.path == "docs/spec.md"
        assert issue.message == "Deprecated field used"
        assert issue.line == 42
        assert issue.column == 10

    def test_validation_issue_missing_required_field(self):
        """Test ValidationIssue raises error when required field missing."""
        with pytest.raises(ValidationError) as exc_info:
            ValidationIssue(
                level=ValidationLevel.ERROR,
                path="test.md",
                # Missing 'message' field
            )
        assert "message" in str(exc_info.value)

    def test_validation_issue_invalid_level(self):
        """Test ValidationIssue raises error with invalid level."""
        with pytest.raises(ValidationError) as exc_info:
            ValidationIssue(
                level="CRITICAL", path="test.md", message="Test"  # Not a valid ValidationLevel
            )
        assert "validation error" in str(exc_info.value).lower()

    def test_validation_issue_serialization(self):
        """Test ValidationIssue can be serialized to dict."""
        issue = ValidationIssue(
            level=ValidationLevel.INFO,
            path="README.md",
            message="Consider adding examples",
            line=15,
        )
        data = issue.model_dump()
        assert data["level"] == "INFO"
        assert data["path"] == "README.md"
        assert data["message"] == "Consider adding examples"
        assert data["line"] == 15
        assert data["column"] is None

    def test_validation_issue_json_serialization(self):
        """Test ValidationIssue can be serialized to JSON."""
        issue = ValidationIssue(
            level=ValidationLevel.ERROR,
            path="src/main.py",
            message="Syntax error",
            line=10,
            column=5,
        )
        json_str = issue.model_dump_json()
        assert '"level":"ERROR"' in json_str
        assert '"path":"src/main.py"' in json_str
        assert '"message":"Syntax error"' in json_str
        assert '"line":10' in json_str
        assert '"column":5' in json_str


class TestValidationSummary:
    """Tests for ValidationSummary model."""

    def test_validation_summary_default_values(self):
        """Test ValidationSummary initializes with zero counts."""
        summary = ValidationSummary()
        assert summary.errors == 0
        assert summary.warnings == 0
        assert summary.info == 0

    def test_validation_summary_with_values(self):
        """Test ValidationSummary with explicit counts."""
        summary = ValidationSummary(errors=3, warnings=5, info=2)
        assert summary.errors == 3
        assert summary.warnings == 5
        assert summary.info == 2

    def test_validation_summary_serialization(self):
        """Test ValidationSummary serialization."""
        summary = ValidationSummary(errors=1, warnings=2, info=3)
        data = summary.model_dump()
        assert data == {"errors": 1, "warnings": 2, "info": 3}


class TestValidationReport:
    """Tests for ValidationReport model."""

    def test_validation_report_empty(self):
        """Test ValidationReport with no issues."""
        report = ValidationReport(valid=True, issues=[])
        assert report.valid is True
        assert len(report.issues) == 0
        assert report.summary.errors == 0
        assert report.summary.warnings == 0
        assert report.summary.info == 0

    def test_validation_report_with_errors(self):
        """Test ValidationReport with error issues."""
        issues = [
            ValidationIssue(level=ValidationLevel.ERROR, path="test1.md", message="Error 1"),
            ValidationIssue(level=ValidationLevel.ERROR, path="test2.md", message="Error 2"),
        ]
        report = ValidationReport(valid=False, issues=issues)
        assert report.valid is False
        assert len(report.issues) == 2
        assert report.summary.errors == 2
        assert report.summary.warnings == 0
        assert report.summary.info == 0

    def test_validation_report_with_mixed_issues(self):
        """Test ValidationReport with mixed issue levels."""
        issues = [
            ValidationIssue(level=ValidationLevel.ERROR, path="test.md", message="Error"),
            ValidationIssue(level=ValidationLevel.WARNING, path="test.md", message="Warning 1"),
            ValidationIssue(level=ValidationLevel.WARNING, path="test.md", message="Warning 2"),
            ValidationIssue(level=ValidationLevel.INFO, path="test.md", message="Info 1"),
            ValidationIssue(level=ValidationLevel.INFO, path="test.md", message="Info 2"),
            ValidationIssue(level=ValidationLevel.INFO, path="test.md", message="Info 3"),
        ]
        report = ValidationReport(valid=False, issues=issues)
        assert len(report.issues) == 6
        assert report.summary.errors == 1
        assert report.summary.warnings == 2
        assert report.summary.info == 3

    def test_validation_report_summary_auto_computed(self):
        """Test that ValidationReport.summary is auto-computed from issues."""
        # Start with empty report
        report = ValidationReport(valid=True, issues=[])
        assert report.summary.errors == 0

        # Add issues directly to the list
        report.issues.append(
            ValidationIssue(level=ValidationLevel.ERROR, path="test.md", message="New error")
        )
        # Summary should update automatically on next access
        assert report.summary.errors == 1

    def test_validation_report_serialization(self):
        """Test ValidationReport serialization includes summary."""
        issues = [
            ValidationIssue(
                level=ValidationLevel.WARNING, path="test.md", message="Warning", line=10
            )
        ]
        report = ValidationReport(valid=True, issues=issues)
        data = report.model_dump()

        assert data["valid"] is True
        assert len(data["issues"]) == 1
        assert data["issues"][0]["level"] == "WARNING"
        assert "summary" in data
        assert data["summary"]["warnings"] == 1
        assert data["summary"]["errors"] == 0

    def test_validation_report_json_serialization(self):
        """Test ValidationReport JSON serialization."""
        issues = [
            ValidationIssue(
                level=ValidationLevel.ERROR, path="src/main.py", message="Syntax error", line=5
            )
        ]
        report = ValidationReport(valid=False, issues=issues)
        json_str = report.model_dump_json()

        assert '"valid":false' in json_str
        assert '"level":"ERROR"' in json_str
        assert '"summary"' in json_str
        assert '"errors":1' in json_str

    def test_validation_report_deserialization(self):
        """Test ValidationReport can be deserialized from dict."""
        data = {
            "valid": False,
            "issues": [
                {
                    "level": "ERROR",
                    "path": "test.md",
                    "message": "Test error",
                    "line": 10,
                    "column": None,
                }
            ],
        }
        report = ValidationReport(**data)
        assert report.valid is False
        assert len(report.issues) == 1
        assert report.issues[0].level == ValidationLevel.ERROR
        assert report.summary.errors == 1
