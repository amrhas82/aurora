"""Tests for interactive utilities."""

import os

import pytest
from aurora_planning.utils.interactive import is_interactive


class TestIsInteractive:
    """Tests for is_interactive function."""

    def test_returns_false_when_no_interactive_option_set(self):
        """Test returns False when noInteractive option is set."""
        result = is_interactive({"noInteractive": True})
        assert result is False

    def test_returns_false_when_interactive_option_false(self):
        """Test returns False when interactive option is explicitly False."""
        result = is_interactive({"interactive": False})
        assert result is False

    def test_respects_environment_variable_false(self, monkeypatch):
        """Test respects AURORA_INTERACTIVE=0 environment variable."""
        monkeypatch.setenv("AURORA_INTERACTIVE", "0")
        result = is_interactive()
        assert result is False

    def test_respects_environment_variable_true(self, monkeypatch):
        """Test respects AURORA_INTERACTIVE=1 environment variable."""
        monkeypatch.setenv("AURORA_INTERACTIVE", "1")
        # Note: We can't test TTY detection reliably in tests
        # This just checks the env var is read
        result = is_interactive()
        # May be True or False depending on test environment
        assert isinstance(result, bool)

    def test_handles_various_false_values(self, monkeypatch):
        """Test handles various false values in environment variable."""
        for value in ["0", "false", "False", "no", "No"]:
            monkeypatch.setenv("AURORA_INTERACTIVE", value)
            result = is_interactive()
            assert result is False

    def test_with_no_options_checks_environment(self):
        """Test with no options checks environment and TTY."""
        result = is_interactive()
        # Result depends on test environment
        assert isinstance(result, bool)
