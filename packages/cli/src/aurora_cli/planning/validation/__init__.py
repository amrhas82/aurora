"""Validation module for Aurora planning system.

This module provides validation logic for plans, capabilities, and modification specifications.
"""

from __future__ import annotations

from aurora_cli.planning.validation.constants import VALIDATION_MESSAGES
from aurora_cli.planning.validation.types import (
    ValidationIssue,
    ValidationLevel,
    ValidationReport,
    ValidationSummary,
)


# Avoid circular import: validator imports from parsers which imports from schemas which imports constants
# Use lazy import for Validator
def __getattr__(name: str):
    if name == "Validator":
        from aurora_cli.planning.validation.validator import Validator

        return Validator
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "Validator",
    "ValidationIssue",
    "ValidationLevel",
    "ValidationReport",
    "ValidationSummary",
    "VALIDATION_MESSAGES",
]
