"""Plan schema (was Change schema in OpenSpec).

Ported from: src/core/schemas/change.schema.ts
Zod → Pydantic translation.
Terminology: change→plan, delta→modification, spec→capability
"""

from enum import Enum
from typing import Annotated

from pydantic import BaseModel, BeforeValidator, Field

from aurora_planning.schemas.base import Requirement
from aurora_planning.validators.constants import (
    MAX_MODIFICATIONS_PER_PLAN,
    MAX_WHY_SECTION_LENGTH,
    MIN_WHY_SECTION_LENGTH,
    VALIDATION_MESSAGES,
)


class ModificationOperation(str, Enum):
    """Operation types for modifications (was DeltaOperationType)."""

    ADDED = "ADDED"
    MODIFIED = "MODIFIED"
    REMOVED = "REMOVED"
    RENAMED = "RENAMED"


def validate_capability_name(v: str) -> str:
    """Validate capability name is not empty."""
    if not isinstance(v, str):
        raise ValueError(VALIDATION_MESSAGES.MODIFICATION_CAPABILITY_EMPTY)
    if not v or len(v.strip()) == 0:
        raise ValueError(VALIDATION_MESSAGES.MODIFICATION_CAPABILITY_EMPTY)
    return v


def validate_modification_description(v: str) -> str:
    """Validate modification description is not empty."""
    if not isinstance(v, str):
        raise ValueError(VALIDATION_MESSAGES.MODIFICATION_DESCRIPTION_EMPTY)
    if not v or len(v.strip()) == 0:
        raise ValueError(VALIDATION_MESSAGES.MODIFICATION_DESCRIPTION_EMPTY)
    return v


def validate_plan_name(v: str) -> str:
    """Validate plan name is not empty."""
    if not isinstance(v, str):
        raise ValueError(VALIDATION_MESSAGES.PLAN_NAME_EMPTY)
    if not v or len(v.strip()) == 0:
        raise ValueError(VALIDATION_MESSAGES.PLAN_NAME_EMPTY)
    return v


def validate_why_section(v: str) -> str:
    """Validate why section length."""
    if not isinstance(v, str):
        raise ValueError(VALIDATION_MESSAGES.PLAN_WHY_TOO_SHORT)
    if len(v) < MIN_WHY_SECTION_LENGTH:
        raise ValueError(VALIDATION_MESSAGES.PLAN_WHY_TOO_SHORT)
    if len(v) > MAX_WHY_SECTION_LENGTH:
        raise ValueError(VALIDATION_MESSAGES.PLAN_WHY_TOO_LONG)
    return v


def validate_what_changes(v: str) -> str:
    """Validate what_changes is not empty."""
    if not isinstance(v, str):
        raise ValueError(VALIDATION_MESSAGES.PLAN_WHAT_EMPTY)
    if not v or len(v.strip()) == 0:
        raise ValueError(VALIDATION_MESSAGES.PLAN_WHAT_EMPTY)
    return v


def validate_modifications_list(v: list["Modification"]) -> list["Modification"]:
    """Validate modifications list has at least one item and not too many."""
    if not v or len(v) == 0:
        raise ValueError(VALIDATION_MESSAGES.PLAN_NO_MODIFICATIONS)
    if len(v) > MAX_MODIFICATIONS_PER_PLAN:
        raise ValueError(VALIDATION_MESSAGES.PLAN_TOO_MANY_MODIFICATIONS)
    return v


# Type aliases with validators
CapabilityName = Annotated[str, BeforeValidator(validate_capability_name)]
ModificationDescription = Annotated[str, BeforeValidator(validate_modification_description)]
PlanName = Annotated[str, BeforeValidator(validate_plan_name)]
WhySection = Annotated[str, BeforeValidator(validate_why_section)]
WhatChanges = Annotated[str, BeforeValidator(validate_what_changes)]
ModificationsList = Annotated[list["Modification"], BeforeValidator(validate_modifications_list)]


class RenameInfo(BaseModel):
    """Information for RENAMED operations."""

    model_config = {"populate_by_name": True}

    from_name: str = Field(alias="from")
    to_name: str = Field(alias="to")


class Modification(BaseModel):
    """A modification to a capability (was Delta).

    Maps to: DeltaSchema in TypeScript
    """

    capability: CapabilityName  # Was 'spec'
    operation: ModificationOperation
    description: ModificationDescription
    requirement: Requirement | None = None
    requirements: list[Requirement] | None = None
    rename: RenameInfo | None = None


class PlanMetadata(BaseModel):
    """Metadata for a plan."""

    version: str = "1.0.0"
    format: str = "aurora-plan"  # Was 'openspec-change'
    source_path: str | None = None


class Plan(BaseModel):
    """A plan for changes (was Change).

    Maps to: ChangeSchema in TypeScript
    """

    name: PlanName
    why: WhySection
    what_changes: WhatChanges  # Was 'whatChanges'
    modifications: ModificationsList  # Was 'deltas'
    metadata: PlanMetadata | None = None
