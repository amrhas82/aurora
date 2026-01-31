"""Base schemas: Scenario and Requirement.

Ported from: src/core/schemas/base.schema.ts
Zod → Pydantic translation.
Terminology: openspec→aurora
"""

from typing import TYPE_CHECKING, Annotated, Any

from pydantic import BaseModel, BeforeValidator, Field

if TYPE_CHECKING:
    pass

from aurora_planning.validators.constants import VALIDATION_MESSAGES


def validate_non_empty_string(v: str, _field_name: str, error_msg: str) -> str:
    """Validate that a string is not empty."""
    if not v or len(v.strip()) == 0:
        raise ValueError(error_msg)
    return v


def validate_scenario_text(v: str) -> str:
    """Validate scenario raw_text is not empty."""
    if not isinstance(v, str):
        raise ValueError(VALIDATION_MESSAGES.SCENARIO_EMPTY)
    if not v or len(v.strip()) == 0:
        raise ValueError(VALIDATION_MESSAGES.SCENARIO_EMPTY)
    return v


def validate_requirement_text(v: str) -> str:
    """Validate requirement text is not empty and contains SHALL/MUST."""
    if not isinstance(v, str):
        raise ValueError(VALIDATION_MESSAGES.REQUIREMENT_EMPTY)
    if not v or len(v.strip()) == 0:
        raise ValueError(VALIDATION_MESSAGES.REQUIREMENT_EMPTY)
    if "SHALL" not in v and "MUST" not in v:
        raise ValueError(VALIDATION_MESSAGES.REQUIREMENT_NO_SHALL)
    return v


def validate_scenarios_list(v: list[Any]) -> list[Any]:
    """Validate scenarios list has at least one item."""
    if not v or len(v) == 0:
        raise ValueError(VALIDATION_MESSAGES.REQUIREMENT_NO_SCENARIOS)
    return v


# Type aliases with validators
ScenarioText = Annotated[str, BeforeValidator(validate_scenario_text)]
RequirementText = Annotated[str, BeforeValidator(validate_requirement_text)]
ScenariosList = Annotated[list["Scenario"], BeforeValidator(validate_scenarios_list)]


class Scenario(BaseModel):
    """A test scenario for a requirement.

    Maps to: ScenarioSchema in TypeScript
    """

    raw_text: ScenarioText


class Requirement(BaseModel):
    """A requirement with SHALL/MUST keyword and scenarios.

    Maps to: RequirementSchema in TypeScript
    """

    text: RequirementText
    scenarios: ScenariosList = Field(default_factory=list)
