"""
Unit tests for HeadlessConfig dataclass.

Following TDD RED-GREEN-REFACTOR cycle:
- Task 1.1-1.3: RED phase - write failing tests
- Task 1.4-1.6: GREEN phase - implement to pass tests
- Task 1.7-1.8: REFACTOR phase - improve code quality
"""

import pytest
from aurora_soar.headless.config import HeadlessConfig


class TestHeadlessConfigDefaults:
    """Test HeadlessConfig initialization with default values."""

    def test_headless_config_creates_with_defaults(self):
        """Test that HeadlessConfig can be created with default values."""
        config = HeadlessConfig()

        # Verify default values exist and are reasonable
        assert config.budget > 0, "Default budget should be positive"
        assert config.max_iterations > 0, "Default max_iterations should be positive"
        assert config.scratchpad_path is not None, "Default scratchpad_path should be set"
        assert config.dry_run is False, "Default dry_run should be False"

    def test_headless_config_custom_values(self):
        """Test that HeadlessConfig accepts custom values."""
        config = HeadlessConfig(
            budget=50000,
            max_iterations=3,
            scratchpad_path="/custom/path/scratchpad.md",
            dry_run=True
        )

        assert config.budget == 50000
        assert config.max_iterations == 3
        assert config.scratchpad_path == "/custom/path/scratchpad.md"
        assert config.dry_run is True


class TestHeadlessConfigValidation:
    """Test HeadlessConfig validation logic - Task 1.2."""

    def test_negative_budget_raises_error(self):
        """Test that negative budget raises ValueError."""
        with pytest.raises(ValueError, match="budget must be positive"):
            HeadlessConfig(budget=-1000)

    def test_zero_budget_raises_error(self):
        """Test that zero budget raises ValueError."""
        with pytest.raises(ValueError, match="budget must be positive"):
            HeadlessConfig(budget=0)

    def test_negative_max_iterations_raises_error(self):
        """Test that negative max_iterations raises ValueError."""
        with pytest.raises(ValueError, match="max_iterations must be positive"):
            HeadlessConfig(max_iterations=-1)

    def test_zero_max_iterations_raises_error(self):
        """Test that zero max_iterations raises ValueError."""
        with pytest.raises(ValueError, match="max_iterations must be positive"):
            HeadlessConfig(max_iterations=0)

    def test_excessive_max_iterations_raises_error(self):
        """Test that max_iterations beyond reasonable limit raises ValueError."""
        with pytest.raises(ValueError, match="max_iterations cannot exceed"):
            HeadlessConfig(max_iterations=100)  # Assuming limit is lower


class TestHeadlessConfigImmutability:
    """Test HeadlessConfig immutability after creation - Task 1.3."""

    def test_cannot_modify_budget_after_creation(self):
        """Test that budget cannot be modified after config creation."""
        config = HeadlessConfig(budget=30000)

        with pytest.raises((AttributeError, Exception), match="can't set attribute|cannot set field|cannot assign to field"):
            config.budget = 50000

    def test_cannot_modify_max_iterations_after_creation(self):
        """Test that max_iterations cannot be modified after config creation."""
        config = HeadlessConfig(max_iterations=5)

        with pytest.raises((AttributeError, Exception), match="can't set attribute|cannot set field|cannot assign to field"):
            config.max_iterations = 10

    def test_cannot_modify_scratchpad_path_after_creation(self):
        """Test that scratchpad_path cannot be modified after config creation."""
        config = HeadlessConfig(scratchpad_path="/path/to/scratchpad.md")

        with pytest.raises((AttributeError, Exception), match="can't set attribute|cannot set field|cannot assign to field"):
            config.scratchpad_path = "/new/path/scratchpad.md"

    def test_cannot_modify_dry_run_after_creation(self):
        """Test that dry_run cannot be modified after config creation."""
        config = HeadlessConfig(dry_run=False)

        with pytest.raises((AttributeError, Exception), match="can't set attribute|cannot set field|cannot assign to field"):
            config.dry_run = True
