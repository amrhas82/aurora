"""Validation types for Aurora Planning System.

Defines validation issue levels, individual issues, and validation reports.
Uses Pydantic models for type safety and automatic validation.
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, computed_field


class ValidationLevel(str, Enum):
    """Validation issue severity level.

    - ERROR: Must be fixed before proceeding
    - WARNING: Should be reviewed but not blocking
    - INFO: Informational message for improvement
    """

    ERROR = "ERROR"
    WARNING = "WARNING"
    INFO = "INFO"


class ValidationIssue(BaseModel):
    """A single validation issue found during validation.

    Attributes:
        level: Severity level (ERROR, WARNING, INFO)
        path: File path or section where issue was found
        message: Human-readable description of the issue
        line: Optional line number where issue occurs
        column: Optional column number where issue occurs

    """

    level: ValidationLevel
    path: str
    message: str
    line: int | None = None
    column: int | None = None


class ValidationSummary(BaseModel):
    """Summary counts for a validation report.

    Automatically calculated from validation issues.
    """

    errors: int = 0
    warnings: int = 0
    info: int = 0


class ValidationReport(BaseModel):
    """Complete validation report with issues and summary.

    Attributes:
        valid: True if no ERROR-level issues exist
        issues: List of all validation issues found
        summary: Auto-computed summary counts (read-only property)

    """

    valid: bool
    issues: list[ValidationIssue]

    @computed_field  # type: ignore[prop-decorator]
    @property
    def summary(self) -> ValidationSummary:
        """Auto-calculate summary from issues.

        Returns:
            ValidationSummary with counts of errors, warnings, and info messages.

        """
        errors = sum(1 for i in self.issues if i.level == ValidationLevel.ERROR)
        warnings = sum(1 for i in self.issues if i.level == ValidationLevel.WARNING)
        info = sum(1 for i in self.issues if i.level == ValidationLevel.INFO)
        return ValidationSummary(errors=errors, warnings=warnings, info=info)
