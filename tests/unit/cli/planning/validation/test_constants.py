"""Unit tests for validation constants module.

Tests that validation thresholds and messages are defined correctly
and accessible for use in validation logic.
"""

import pytest

from aurora_cli.planning.validation.constants import (
    MAX_MODIFICATIONS_PER_PLAN,
    MAX_REQUIREMENT_TEXT_LENGTH,
    MAX_WHY_SECTION_LENGTH,
    MIN_MODIFICATION_DESCRIPTION_LENGTH,
    MIN_PURPOSE_LENGTH,
    MIN_WHY_SECTION_LENGTH,
    VALIDATION_MESSAGES,
)


class TestValidationThresholds:
    """Tests for validation threshold constants."""

    def test_min_thresholds_are_positive(self):
        """Verify all minimum thresholds are positive integers."""
        assert MIN_WHY_SECTION_LENGTH > 0
        assert MIN_PURPOSE_LENGTH > 0
        assert MIN_MODIFICATION_DESCRIPTION_LENGTH > 0

    def test_max_thresholds_are_positive(self):
        """Verify all maximum thresholds are positive integers."""
        assert MAX_WHY_SECTION_LENGTH > 0
        assert MAX_REQUIREMENT_TEXT_LENGTH > 0
        assert MAX_MODIFICATIONS_PER_PLAN > 0

    def test_min_max_relationship(self):
        """Verify minimum thresholds are less than maximum thresholds."""
        assert MIN_WHY_SECTION_LENGTH < MAX_WHY_SECTION_LENGTH

    def test_threshold_values(self):
        """Verify specific threshold values match expected."""
        assert MIN_WHY_SECTION_LENGTH == 50
        assert MIN_PURPOSE_LENGTH == 50
        assert MAX_WHY_SECTION_LENGTH == 1000
        assert MAX_REQUIREMENT_TEXT_LENGTH == 500
        assert MAX_MODIFICATIONS_PER_PLAN == 10
        assert MIN_MODIFICATION_DESCRIPTION_LENGTH == 20


class TestValidationMessages:
    """Tests for VALIDATION_MESSAGES class."""

    def test_required_content_messages_exist(self):
        """Verify all required content validation messages are defined."""
        assert hasattr(VALIDATION_MESSAGES, "SCENARIO_EMPTY")
        assert hasattr(VALIDATION_MESSAGES, "REQUIREMENT_EMPTY")
        assert hasattr(VALIDATION_MESSAGES, "REQUIREMENT_NO_SHALL")
        assert hasattr(VALIDATION_MESSAGES, "REQUIREMENT_NO_SCENARIOS")
        assert hasattr(VALIDATION_MESSAGES, "CAPABILITY_NAME_EMPTY")
        assert hasattr(VALIDATION_MESSAGES, "CAPABILITY_PURPOSE_EMPTY")
        assert hasattr(VALIDATION_MESSAGES, "CAPABILITY_NO_REQUIREMENTS")
        assert hasattr(VALIDATION_MESSAGES, "PLAN_NAME_EMPTY")
        assert hasattr(VALIDATION_MESSAGES, "PLAN_WHY_TOO_SHORT")
        assert hasattr(VALIDATION_MESSAGES, "PLAN_WHY_TOO_LONG")
        assert hasattr(VALIDATION_MESSAGES, "PLAN_WHAT_EMPTY")
        assert hasattr(VALIDATION_MESSAGES, "PLAN_NO_MODIFICATIONS")
        assert hasattr(VALIDATION_MESSAGES, "PLAN_TOO_MANY_MODIFICATIONS")
        assert hasattr(VALIDATION_MESSAGES, "MODIFICATION_CAPABILITY_EMPTY")
        assert hasattr(VALIDATION_MESSAGES, "MODIFICATION_DESCRIPTION_EMPTY")

    def test_warning_messages_exist(self):
        """Verify all warning validation messages are defined."""
        assert hasattr(VALIDATION_MESSAGES, "PURPOSE_TOO_BRIEF")
        assert hasattr(VALIDATION_MESSAGES, "REQUIREMENT_TOO_LONG")
        assert hasattr(VALIDATION_MESSAGES, "MODIFICATION_DESCRIPTION_TOO_BRIEF")
        assert hasattr(VALIDATION_MESSAGES, "MODIFICATION_MISSING_REQUIREMENTS")

    def test_guidance_messages_exist(self):
        """Verify all guidance messages are defined."""
        assert hasattr(VALIDATION_MESSAGES, "GUIDE_NO_MODIFICATIONS")
        assert hasattr(VALIDATION_MESSAGES, "GUIDE_MISSING_CAPABILITY_SECTIONS")
        assert hasattr(VALIDATION_MESSAGES, "GUIDE_MISSING_PLAN_SECTIONS")
        assert hasattr(VALIDATION_MESSAGES, "GUIDE_SCENARIO_FORMAT")

    def test_messages_are_non_empty_strings(self):
        """Verify all messages are non-empty strings."""
        message_attrs = [
            attr
            for attr in dir(VALIDATION_MESSAGES)
            if not attr.startswith("_") and isinstance(getattr(VALIDATION_MESSAGES, attr), str)
        ]
        assert len(message_attrs) > 0, "Should have at least one message"

        for attr in message_attrs:
            message = getattr(VALIDATION_MESSAGES, attr)
            assert isinstance(message, str), f"{attr} should be a string"
            assert len(message) > 0, f"{attr} should not be empty"

    def test_aurora_terminology_used(self):
        """Verify messages use Aurora terminology, not OpenSpec terms."""
        # Collect all message values
        message_values = []
        for attr in dir(VALIDATION_MESSAGES):
            if not attr.startswith("_"):
                value = getattr(VALIDATION_MESSAGES, attr)
                if isinstance(value, str):
                    message_values.append(value.lower())

        all_text = " ".join(message_values)

        # Should NOT contain OpenSpec terminology
        assert "openspec" not in all_text, "Messages should not reference 'openspec'"
        assert "change" not in all_text or "changes" in all_text, (
            "Should use 'plan' or 'changes' (as a verb), not 'change' (as a noun)"
        )
        # Note: "spec" might appear in "inspect", so we check for specific phrases

        # Should contain Aurora terminology
        assert "plan" in all_text, "Messages should reference 'plan'"
        assert "capability" in all_text or "capabilities" in all_text, (
            "Messages should reference 'capability'"
        )

    def test_messages_include_threshold_values(self):
        """Verify messages that reference thresholds include the actual values."""
        # Check that WHY section messages include the threshold values
        assert str(MIN_WHY_SECTION_LENGTH) in VALIDATION_MESSAGES.PLAN_WHY_TOO_SHORT
        assert str(MAX_WHY_SECTION_LENGTH) in VALIDATION_MESSAGES.PLAN_WHY_TOO_LONG

        # Check that purpose message includes threshold
        assert str(MIN_PURPOSE_LENGTH) in VALIDATION_MESSAGES.PURPOSE_TOO_BRIEF

        # Check that requirement length message includes threshold
        assert str(MAX_REQUIREMENT_TEXT_LENGTH) in VALIDATION_MESSAGES.REQUIREMENT_TOO_LONG

        # Check that modifications count message includes threshold
        assert str(MAX_MODIFICATIONS_PER_PLAN) in VALIDATION_MESSAGES.PLAN_TOO_MANY_MODIFICATIONS

    def test_guidance_messages_provide_actionable_help(self):
        """Verify guidance messages provide actionable remediation steps."""
        # Guidance should be longer than simple error messages
        assert len(VALIDATION_MESSAGES.GUIDE_NO_MODIFICATIONS) > 100
        assert len(VALIDATION_MESSAGES.GUIDE_MISSING_CAPABILITY_SECTIONS) > 100
        assert len(VALIDATION_MESSAGES.GUIDE_MISSING_PLAN_SECTIONS) > 50
        assert len(VALIDATION_MESSAGES.GUIDE_SCENARIO_FORMAT) > 50

        # Should contain examples or specific instructions
        assert "capability-specs/" in VALIDATION_MESSAGES.GUIDE_NO_MODIFICATIONS
        assert "#### Scenario:" in VALIDATION_MESSAGES.GUIDE_MISSING_CAPABILITY_SECTIONS
        assert "## Why" in VALIDATION_MESSAGES.GUIDE_MISSING_PLAN_SECTIONS
        assert "#### Scenario:" in VALIDATION_MESSAGES.GUIDE_SCENARIO_FORMAT

    def test_no_openspec_specific_references(self):
        """Verify no OpenSpec-specific directory references remain."""
        all_guidance = [
            VALIDATION_MESSAGES.GUIDE_NO_MODIFICATIONS,
            VALIDATION_MESSAGES.GUIDE_MISSING_CAPABILITY_SECTIONS,
            VALIDATION_MESSAGES.GUIDE_MISSING_PLAN_SECTIONS,
            VALIDATION_MESSAGES.GUIDE_SCENARIO_FORMAT,
        ]

        for guidance in all_guidance:
            assert "openspec/" not in guidance.lower(), (
                f"Should not reference 'openspec/' directory: {guidance}"
            )
            # Check for Aurora-specific paths
            if "directory" in guidance.lower() or "specs/" in guidance.lower():
                # Should reference Aurora paths if mentioning directories
                assert (
                    "capability-specs/" in guidance or ".aurora/" in guidance
                ), f"Should use Aurora paths: {guidance}"
