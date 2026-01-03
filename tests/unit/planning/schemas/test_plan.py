"""
Tests for Plan schema (was Change schema in OpenSpec).

Ported from: test/core/validation.test.ts - describe('ChangeSchema')
TDD approach: Tests written first based on TypeScript test behavior.

Task: 1.5 - Write tests/unit/schemas/test_plan.py
"""

import pytest
from pydantic import ValidationError

from aurora_planning.schemas.plan import Modification, ModificationOperation, Plan


class TestModificationOperation:
    """Test cases for ModificationOperation enum."""

    def test_valid_operations(self):
        """Should accept valid operation types."""
        assert ModificationOperation.ADDED == "ADDED"
        assert ModificationOperation.MODIFIED == "MODIFIED"
        assert ModificationOperation.REMOVED == "REMOVED"
        assert ModificationOperation.RENAMED == "RENAMED"


class TestModification:
    """Test cases for Modification model (was Delta)."""

    def test_validates_valid_modification(self):
        """Should validate a valid modification."""
        modification = Modification(
            capability="user-auth",
            operation=ModificationOperation.ADDED,
            description="Add new user authentication capability",
        )
        assert modification.capability == "user-auth"
        assert modification.operation == ModificationOperation.ADDED

    def test_rejects_modification_with_empty_capability(self):
        """Should reject modification with empty capability name."""
        with pytest.raises(ValidationError) as exc_info:
            Modification(
                capability="",
                operation=ModificationOperation.ADDED,
                description="Add something",
            )

        errors = exc_info.value.errors()
        assert any("Capability name cannot be empty" in str(e) for e in errors)

    def test_rejects_modification_with_empty_description(self):
        """Should reject modification with empty description."""
        with pytest.raises(ValidationError) as exc_info:
            Modification(
                capability="user-auth",
                operation=ModificationOperation.ADDED,
                description="",
            )

        errors = exc_info.value.errors()
        assert any("Modification description cannot be empty" in str(e) for e in errors)


class TestPlanSchema:
    """Test cases for Plan model (was Change)."""

    def test_validates_valid_plan(self):
        """Should validate a valid plan."""
        plan = Plan(
            name="add-user-auth",
            why="We need user authentication to secure the application and protect user data from unauthorized access.",
            what_changes="Add authentication module with login and logout capabilities",
            modifications=[
                Modification(
                    capability="user-auth",
                    operation=ModificationOperation.ADDED,
                    description="Add new user authentication capability",
                ),
            ],
        )
        assert plan.name == "add-user-auth"
        assert len(plan.modifications) == 1

    def test_rejects_plan_with_short_why_section(self):
        """Should reject plan with why section shorter than 50 characters."""
        with pytest.raises(ValidationError) as exc_info:
            Plan(
                name="add-user-auth",
                why="Need auth",  # Too short
                what_changes="Add authentication",
                modifications=[
                    Modification(
                        capability="user-auth",
                        operation=ModificationOperation.ADDED,
                        description="Add auth",
                    ),
                ],
            )

        errors = exc_info.value.errors()
        assert any("Why section must be at least 50 characters" in str(e) for e in errors)

    def test_rejects_plan_with_empty_name(self):
        """Should reject plan with empty name."""
        with pytest.raises(ValidationError) as exc_info:
            Plan(
                name="",
                why="We need this feature for security reasons and compliance with requirements.",
                what_changes="Add the feature",
                modifications=[
                    Modification(
                        capability="feature",
                        operation=ModificationOperation.ADDED,
                        description="Add feature",
                    ),
                ],
            )

        errors = exc_info.value.errors()
        assert any("Plan name cannot be empty" in str(e) for e in errors)

    def test_rejects_plan_without_modifications(self):
        """Should reject plan without modifications."""
        with pytest.raises(ValidationError) as exc_info:
            Plan(
                name="empty-plan",
                why="We need this feature for security reasons and compliance with requirements.",
                what_changes="Add the feature",
                modifications=[],
            )

        errors = exc_info.value.errors()
        assert any("Plan must have at least one modification" in str(e) for e in errors)

    def test_warns_about_too_many_modifications(self):
        """Should warn about plans with more than 10 modifications."""
        modifications = [
            Modification(
                capability=f"capability-{i}",
                operation=ModificationOperation.ADDED,
                description=f"Add capability {i}",
            )
            for i in range(11)
        ]

        with pytest.raises(ValidationError) as exc_info:
            Plan(
                name="massive-plan",
                why="This is a massive change that affects many parts of the system and needs to be done.",
                what_changes="Update everything",
                modifications=modifications,
            )

        errors = exc_info.value.errors()
        assert any("Consider splitting plans with more than 10 modifications" in str(e) for e in errors)

    def test_rejects_plan_with_empty_what_changes(self):
        """Should reject plan with empty what_changes."""
        with pytest.raises(ValidationError) as exc_info:
            Plan(
                name="some-plan",
                why="We need this feature for security reasons and compliance with requirements.",
                what_changes="",
                modifications=[
                    Modification(
                        capability="feature",
                        operation=ModificationOperation.ADDED,
                        description="Add feature",
                    ),
                ],
            )

        errors = exc_info.value.errors()
        assert any("What Changes section cannot be empty" in str(e) for e in errors)
