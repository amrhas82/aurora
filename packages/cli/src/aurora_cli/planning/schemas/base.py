"""Base schemas for Aurora Planning System: Scenario and Requirement.

These are the fundamental building blocks used across capabilities and plans.
Requirements must contain SHALL/MUST keywords and at least one scenario.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Annotated, Any

from pydantic import BaseModel, BeforeValidator, Field

if TYPE_CHECKING:
    pass

from aurora_cli.planning.validation.constants import VALIDATION_MESSAGES


def validate_non_empty_string(v: str, _field_name: str, error_msg: str) -> str:
    """Validate that a string is not empty.

    Args:
        v: String value to validate
        _field_name: Name of the field being validated (reserved for future use)
        error_msg: Error message to raise if validation fails

    Returns:
        The validated string

    Raises:
        ValueError: If string is empty or whitespace-only

    """
    if not v or len(v.strip()) == 0:
        raise ValueError(error_msg)
    return v


def validate_scenario_text(v: str) -> str:
    """Validate scenario raw_text is not empty.

    Args:
        v: Scenario text to validate

    Returns:
        The validated scenario text

    Raises:
        ValueError: If scenario text is empty

    """
    if not isinstance(v, str):
        raise ValueError(VALIDATION_MESSAGES.SCENARIO_EMPTY)
    if not v or len(v.strip()) == 0:
        raise ValueError(VALIDATION_MESSAGES.SCENARIO_EMPTY)
    return v


def validate_requirement_text(v: str) -> str:
    """Validate requirement text is not empty and contains SHALL/MUST.

    Requirements MUST contain either "SHALL" or "MUST" keyword (case-sensitive)
    to be considered valid. This enforces RFC 2119 compliance.

    Args:
        v: Requirement text to validate

    Returns:
        The validated requirement text

    Raises:
        ValueError: If text is empty or missing SHALL/MUST keyword

    """
    if not isinstance(v, str):
        raise ValueError(VALIDATION_MESSAGES.REQUIREMENT_EMPTY)
    if not v or len(v.strip()) == 0:
        raise ValueError(VALIDATION_MESSAGES.REQUIREMENT_EMPTY)
    if "SHALL" not in v and "MUST" not in v:
        raise ValueError(VALIDATION_MESSAGES.REQUIREMENT_NO_SHALL)
    return v


def validate_scenarios_list(v: list[Any]) -> list[Any]:
    """Validate scenarios list has at least one item.

    Args:
        v: List of scenarios to validate

    Returns:
        The validated scenarios list

    Raises:
        ValueError: If scenarios list is empty

    """
    if not v or len(v) == 0:
        raise ValueError(VALIDATION_MESSAGES.REQUIREMENT_NO_SCENARIOS)
    return v


# Type aliases with validators
ScenarioText = Annotated[str, BeforeValidator(validate_scenario_text)]
RequirementText = Annotated[str, BeforeValidator(validate_requirement_text)]
ScenariosList = Annotated[list["Scenario"], BeforeValidator(validate_scenarios_list)]


class Scenario(BaseModel):
    """A test scenario for a requirement.

    Scenarios describe specific test cases using WHEN/THEN/AND format.
    Each scenario validates one aspect of the requirement's behavior.

    Attributes:
        raw_text: Full scenario text including WHEN/THEN/AND blocks

    """

    raw_text: ScenarioText


class Requirement(BaseModel):
    """A requirement with SHALL/MUST keyword and scenarios.

    Requirements define system behavior using RFC 2119 keywords (SHALL/MUST).
    Each requirement must have at least one testable scenario.

    Attributes:
        text: Requirement statement (must contain SHALL or MUST)
        scenarios: List of test scenarios (minimum 1)

    """

    text: RequirementText
    scenarios: ScenariosList = Field(default_factory=list)
