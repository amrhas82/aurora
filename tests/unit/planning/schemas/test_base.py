"""
Tests for base schemas: Scenario and Requirement.

Ported from: test/core/validation.test.ts - describe('Validation Schemas')
TDD approach: Tests written first based on TypeScript test behavior.

Task: 1.3 - Write tests/unit/schemas/test_base.py
"""

import pytest
from aurora_planning.schemas.base import Requirement, Scenario
from pydantic import ValidationError


class TestScenarioSchema:
    """Test cases for Scenario model - ported from ScenarioSchema tests."""

    def test_validates_valid_scenario(self):
        """Should validate a valid scenario."""
        scenario = Scenario(
            raw_text="Given a user is logged in\n"
            "When they click logout\n"
            "Then they are redirected to login page"
        )
        assert scenario.raw_text is not None
        assert "Given a user is logged in" in scenario.raw_text

    def test_rejects_scenario_with_empty_text(self):
        """Should reject scenario with empty text."""
        with pytest.raises(ValidationError) as exc_info:
            Scenario(raw_text="")

        errors = exc_info.value.errors()
        assert len(errors) >= 1
        # Check for the specific error message from constants
        assert any("Scenario text cannot be empty" in str(e) for e in errors)


class TestRequirementSchema:
    """Test cases for Requirement model - ported from RequirementSchema tests."""

    def test_validates_valid_requirement(self):
        """Should validate a valid requirement."""
        requirement = Requirement(
            text="The system SHALL provide user authentication",
            scenarios=[
                Scenario(
                    raw_text="Given a user with valid credentials\n"
                    "When they submit the login form\n"
                    "Then they are authenticated"
                )
            ],
        )
        assert requirement.text is not None
        assert "SHALL" in requirement.text
        assert len(requirement.scenarios) == 1

    def test_rejects_requirement_without_shall_or_must(self):
        """Should reject requirement without SHALL or MUST."""
        with pytest.raises(ValidationError) as exc_info:
            Requirement(
                text="The system provides user authentication",
                scenarios=[
                    Scenario(raw_text="Given a user\nWhen they login\nThen authenticated")
                ],
            )

        errors = exc_info.value.errors()
        assert any("Requirement must contain SHALL or MUST keyword" in str(e) for e in errors)

    def test_rejects_requirement_without_scenarios(self):
        """Should reject requirement without scenarios."""
        with pytest.raises(ValidationError) as exc_info:
            Requirement(
                text="The system SHALL provide user authentication",
                scenarios=[],
            )

        errors = exc_info.value.errors()
        assert any("Requirement must have at least one scenario" in str(e) for e in errors)

    def test_rejects_requirement_with_empty_text(self):
        """Should reject requirement with empty text."""
        with pytest.raises(ValidationError) as exc_info:
            Requirement(
                text="",
                scenarios=[Scenario(raw_text="Given something\nWhen action\nThen result")],
            )

        errors = exc_info.value.errors()
        assert any("Requirement text cannot be empty" in str(e) for e in errors)

    def test_accepts_requirement_with_must_keyword(self):
        """Should accept requirement with MUST keyword (alternative to SHALL)."""
        requirement = Requirement(
            text="The system MUST log all authentication attempts",
            scenarios=[
                Scenario(raw_text="Given an auth attempt\nWhen it occurs\nThen it is logged")
            ],
        )
        assert "MUST" in requirement.text

    def test_accepts_requirement_with_multiple_scenarios(self):
        """Should accept requirement with multiple scenarios."""
        requirement = Requirement(
            text="The system SHALL handle various login cases",
            scenarios=[
                Scenario(raw_text="Given valid credentials\nWhen login\nThen success"),
                Scenario(raw_text="Given invalid credentials\nWhen login\nThen failure"),
                Scenario(raw_text="Given locked account\nWhen login\nThen account locked message"),
            ],
        )
        assert len(requirement.scenarios) == 3
