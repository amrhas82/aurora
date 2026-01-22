"""Plan schema for Aurora Planning System.

Defines the structure for plans (proposals for changes), including:
- Plan metadata (name, why, what changes)
- Modifications (operations on capabilities)
- Modification operations (ADDED, MODIFIED, REMOVED, RENAMED)

Plans describe what changes will be made to system capabilities and why.
"""

from __future__ import annotations

from enum import Enum
from typing import Annotated

from pydantic import BaseModel, BeforeValidator, Field

from aurora_cli.planning.schemas.base import Requirement
from aurora_cli.planning.validation.constants import (
    MAX_MODIFICATIONS_PER_PLAN,
    MAX_WHY_SECTION_LENGTH,
    MIN_WHY_SECTION_LENGTH,
    VALIDATION_MESSAGES,
)


class ModificationOperation(str, Enum):
    """Operation types for capability modifications.

    - ADDED: New requirements being added to capability
    - MODIFIED: Existing requirements being changed
    - REMOVED: Requirements being removed from capability
    - RENAMED: Requirements being renamed (FROM/TO)
    """

    ADDED = "ADDED"
    MODIFIED = "MODIFIED"
    REMOVED = "REMOVED"
    RENAMED = "RENAMED"


def validate_capability_name(v: str) -> str:
    """Validate capability name is not empty.

    Args:
        v: Capability name to validate

    Returns:
        The validated capability name

    Raises:
        ValueError: If capability name is empty

    """
    if not isinstance(v, str):
        raise ValueError(VALIDATION_MESSAGES.MODIFICATION_CAPABILITY_EMPTY)
    if not v or len(v.strip()) == 0:
        raise ValueError(VALIDATION_MESSAGES.MODIFICATION_CAPABILITY_EMPTY)
    return v


def validate_modification_description(v: str) -> str:
    """Validate modification description is not empty.

    Args:
        v: Modification description to validate

    Returns:
        The validated description

    Raises:
        ValueError: If description is empty

    """
    if not isinstance(v, str):
        raise ValueError(VALIDATION_MESSAGES.MODIFICATION_DESCRIPTION_EMPTY)
    if not v or len(v.strip()) == 0:
        raise ValueError(VALIDATION_MESSAGES.MODIFICATION_DESCRIPTION_EMPTY)
    return v


def validate_plan_name(v: str) -> str:
    """Validate plan name is not empty.

    Args:
        v: Plan name to validate

    Returns:
        The validated plan name

    Raises:
        ValueError: If plan name is empty

    """
    if not isinstance(v, str):
        raise ValueError(VALIDATION_MESSAGES.PLAN_NAME_EMPTY)
    if not v or len(v.strip()) == 0:
        raise ValueError(VALIDATION_MESSAGES.PLAN_NAME_EMPTY)
    return v


def validate_why_section(v: str) -> str:
    """Validate why section length.

    The "Why" section must be between MIN_WHY_SECTION_LENGTH and
    MAX_WHY_SECTION_LENGTH characters.

    Args:
        v: Why section text to validate

    Returns:
        The validated why section text

    Raises:
        ValueError: If text is too short or too long

    """
    if not isinstance(v, str):
        raise ValueError(VALIDATION_MESSAGES.PLAN_WHY_TOO_SHORT)
    if len(v) < MIN_WHY_SECTION_LENGTH:
        raise ValueError(VALIDATION_MESSAGES.PLAN_WHY_TOO_SHORT)
    if len(v) > MAX_WHY_SECTION_LENGTH:
        raise ValueError(VALIDATION_MESSAGES.PLAN_WHY_TOO_LONG)
    return v


def validate_what_changes(v: str) -> str:
    """Validate what_changes is not empty.

    Args:
        v: What changes text to validate

    Returns:
        The validated what changes text

    Raises:
        ValueError: If text is empty

    """
    if not isinstance(v, str):
        raise ValueError(VALIDATION_MESSAGES.PLAN_WHAT_EMPTY)
    if not v or len(v.strip()) == 0:
        raise ValueError(VALIDATION_MESSAGES.PLAN_WHAT_EMPTY)
    return v


def validate_modifications_list(v: list[Modification]) -> list[Modification]:
    """Validate modifications list has at least one item and not too many.

    Args:
        v: List of modifications to validate

    Returns:
        The validated modifications list

    Raises:
        ValueError: If list is empty or has too many items

    """
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
    """Information for RENAMED operations.

    Describes a requirement being renamed from one name to another.

    Attributes:
        from_name: Original requirement name
        to_name: New requirement name

    """

    model_config = {"populate_by_name": True}

    from_name: str = Field(alias="from")
    to_name: str = Field(alias="to")


class Modification(BaseModel):
    """A modification to a capability.

    Represents a change being proposed to a system capability, such as:
    - Adding new requirements (ADDED)
    - Modifying existing requirements (MODIFIED)
    - Removing requirements (REMOVED)
    - Renaming requirements (RENAMED)

    Attributes:
        capability: Name of the capability being modified
        operation: Type of modification (ADDED/MODIFIED/REMOVED/RENAMED)
        description: Human-readable description of the modification
        requirement: Single requirement (for ADDED/MODIFIED operations)
        requirements: Multiple requirements (for batch operations)
        rename: Rename information (for RENAMED operations)

    """

    capability: CapabilityName
    operation: ModificationOperation
    description: ModificationDescription
    requirement: Requirement | None = None
    requirements: list[Requirement] | None = None
    rename: RenameInfo | None = None


class PlanMetadata(BaseModel):
    """Metadata for a plan.

    Tracks plan version, format, and source information.

    Attributes:
        version: Schema version (default: "1.0.0")
        format: Format identifier (default: "aurora-plan")
        source_path: Optional path to source file

    """

    version: str = "1.0.0"
    format: str = "aurora-plan"
    source_path: str | None = None


class Plan(BaseModel):
    """A plan for changes to system capabilities.

    Plans describe proposed changes to capabilities, including:
    - Why the changes are needed (motivation)
    - What changes will be made (high-level summary)
    - Detailed modifications to specific capabilities

    Attributes:
        name: Name/title of the plan
        why: Explanation of why changes are needed (50-1000 chars)
        what_changes: Summary of what will change
        modifications: List of detailed modifications (1-10)
        metadata: Optional metadata (version, format, source path)

    """

    name: PlanName
    why: WhySection
    what_changes: WhatChanges
    modifications: ModificationsList
    metadata: PlanMetadata | None = None
