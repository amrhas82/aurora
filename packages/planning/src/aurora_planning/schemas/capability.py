"""Capability schema (was Spec schema in OpenSpec).

Ported from: src/core/schemas/spec.schema.ts
Zod → Pydantic translation.
Terminology: spec→capability
"""

from typing import Annotated, Any

from pydantic import BaseModel, BeforeValidator

from aurora_planning.validators.constants import VALIDATION_MESSAGES


def validate_capability_name(v: str) -> str:
    """Validate capability name is not empty."""
    if not isinstance(v, str):
        raise ValueError(VALIDATION_MESSAGES.CAPABILITY_NAME_EMPTY)
    if not v or len(v.strip()) == 0:
        raise ValueError(VALIDATION_MESSAGES.CAPABILITY_NAME_EMPTY)
    return v


def validate_overview(v: str) -> str:
    """Validate overview (purpose) is not empty."""
    if not isinstance(v, str):
        raise ValueError(VALIDATION_MESSAGES.CAPABILITY_PURPOSE_EMPTY)
    if not v or len(v.strip()) == 0:
        raise ValueError(VALIDATION_MESSAGES.CAPABILITY_PURPOSE_EMPTY)
    return v


def validate_requirements_list(v: list[Any]) -> list[Any]:
    """Validate requirements list has at least one item."""
    if not v or len(v) == 0:
        raise ValueError(VALIDATION_MESSAGES.CAPABILITY_NO_REQUIREMENTS)
    return v


# Type aliases with validators
CapabilityName = Annotated[str, BeforeValidator(validate_capability_name)]
Overview = Annotated[str, BeforeValidator(validate_overview)]
RequirementsList = Annotated[list[Any], BeforeValidator(validate_requirements_list)]


class CapabilityMetadata(BaseModel):
    """Metadata for a capability."""

    version: str = "1.0.0"
    format: str = "aurora-capability"  # Was 'openspec'
    source_path: str | None = None


class Capability(BaseModel):
    """A system capability (was Spec).

    Maps to: SpecSchema in TypeScript
    """

    name: CapabilityName
    overview: Overview  # Was 'overview' in TS, maps to 'Purpose' section
    requirements: RequirementsList
    metadata: CapabilityMetadata | None = None
