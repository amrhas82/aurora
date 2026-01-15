"""Validation types: ValidationIssue, ValidationReport.

Ported from: src/core/validation/types.ts
TypeScript interfaces → Pydantic models.
"""

from enum import Enum

from pydantic import BaseModel, computed_field


class ValidationLevel(str, Enum):
    """Validation issue severity level."""

    ERROR = "ERROR"
    WARNING = "WARNING"
    INFO = "INFO"


class ValidationIssue(BaseModel):
    """A single validation issue.

    Maps to: ValidationIssue interface in TypeScript
    """

    level: ValidationLevel
    path: str
    message: str
    line: int | None = None
    column: int | None = None


class ValidationSummary(BaseModel):
    """Summary counts for a validation report."""

    errors: int = 0
    warnings: int = 0
    info: int = 0


class ValidationReport(BaseModel):
    """Complete validation report with issues and summary.

    Maps to: ValidationReport interface in TypeScript
    """

    valid: bool
    issues: list[ValidationIssue]

    @computed_field  # type: ignore[prop-decorator]
    @property
    def summary(self) -> ValidationSummary:
        """Auto-calculate summary from issues."""
        errors = sum(1 for i in self.issues if i.level == ValidationLevel.ERROR)
        warnings = sum(1 for i in self.issues if i.level == ValidationLevel.WARNING)
        info = sum(1 for i in self.issues if i.level == ValidationLevel.INFO)
        return ValidationSummary(errors=errors, warnings=warnings, info=info)
