"""
Tests for Capability schema (was Spec schema in OpenSpec).

Ported from: test/core/validation.test.ts - describe('SpecSchema')
TDD approach: Tests written first based on TypeScript test behavior.

Task: 1.7 - Write tests/unit/schemas/test_capability.py
"""

import pytest
from pydantic import ValidationError

from aurora_planning.schemas.base import Requirement, Scenario
from aurora_planning.schemas.capability import Capability


class TestCapabilitySchema:
    """Test cases for Capability model (was Spec)."""

    def test_validates_valid_capability(self):
        """Should validate a valid capability."""
        capability = Capability(
            name="user-auth",
            overview="This capability defines user authentication requirements",
            requirements=[
                Requirement(
                    text="The system SHALL provide user authentication",
                    scenarios=[
                        Scenario(
                            raw_text="Given a user with valid credentials\n"
                            "When they submit the login form\n"
                            "Then they are authenticated"
                        ),
                    ],
                ),
            ],
        )
        assert capability.name == "user-auth"
        assert len(capability.requirements) == 1

    def test_rejects_capability_without_requirements(self):
        """Should reject capability without requirements."""
        with pytest.raises(ValidationError) as exc_info:
            Capability(
                name="user-auth",
                overview="This capability defines user authentication requirements",
                requirements=[],
            )

        errors = exc_info.value.errors()
        assert any("Capability must have at least one requirement" in str(e) for e in errors)

    def test_rejects_capability_with_empty_name(self):
        """Should reject capability with empty name."""
        with pytest.raises(ValidationError) as exc_info:
            Capability(
                name="",
                overview="Some overview",
                requirements=[
                    Requirement(
                        text="The system SHALL do something",
                        scenarios=[Scenario(raw_text="Given x\nWhen y\nThen z")],
                    ),
                ],
            )

        errors = exc_info.value.errors()
        assert any("Capability name cannot be empty" in str(e) for e in errors)

    def test_rejects_capability_with_empty_overview(self):
        """Should reject capability with empty overview (was purpose)."""
        with pytest.raises(ValidationError) as exc_info:
            Capability(
                name="some-capability",
                overview="",
                requirements=[
                    Requirement(
                        text="The system SHALL do something",
                        scenarios=[Scenario(raw_text="Given x\nWhen y\nThen z")],
                    ),
                ],
            )

        errors = exc_info.value.errors()
        assert any("Purpose section cannot be empty" in str(e) for e in errors)

    def test_accepts_capability_with_multiple_requirements(self):
        """Should accept capability with multiple requirements."""
        capability = Capability(
            name="user-auth",
            overview="This capability defines user authentication requirements",
            requirements=[
                Requirement(
                    text="The system SHALL provide user authentication",
                    scenarios=[Scenario(raw_text="Given x\nWhen y\nThen z")],
                ),
                Requirement(
                    text="The system SHALL handle invalid login attempts",
                    scenarios=[Scenario(raw_text="Given invalid\nWhen attempt\nThen reject")],
                ),
            ],
        )
        assert len(capability.requirements) == 2
