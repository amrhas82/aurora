"""Unit tests for setup.py post-install message.

Tests the display_install_feedback() function that shows after pip install.

NOTE: These tests are obsolete - the project now uses pyproject.toml instead of setup.py.
Marked as skip until/unless post-install messaging is reimplemented.
"""

from __future__ import annotations

import importlib.util
import sys
from io import StringIO
from pathlib import Path
from unittest.mock import patch

import pytest

pytestmark = pytest.mark.skip(reason="setup.py no longer exists - project uses pyproject.toml")


def load_setup_module():
    """Load setup.py module without executing setup() call."""
    setup_path = Path(__file__).parent.parent.parent / "setup.py"
    spec = importlib.util.spec_from_file_location("setup_module", setup_path)
    if spec is None or spec.loader is None:
        raise ImportError("Could not load setup.py")

    setup_module = importlib.util.module_from_spec(spec)

    # Mock sys.argv to prevent setup() from running
    original_argv = sys.argv
    sys.argv = ["setup.py", "--version"]  # Harmless command

    try:
        spec.loader.exec_module(setup_module)
    finally:
        sys.argv = original_argv

    return setup_module


class TestPostInstallMessage:
    """Test post-install message display."""

    def test_display_install_feedback_all_components_installed(self):
        """Test message when all components are installed."""
        setup = load_setup_module()

        # Capture stdout
        captured_output = StringIO()
        with patch("sys.stdout", captured_output):
            setup.display_install_feedback()

        output = captured_output.getvalue()

        # Verify beads-style header
        assert "🔗 Aurora Installer" in output
        assert "==> Installation complete!" in output
        assert "==> Aurora v0.2.0 installed successfully" in output

        # Verify success message
        assert "Aurora is installed and ready!" in output

        # Verify "Get started" section
        assert "Get started:" in output
        assert "aur init" in output
        assert "aur mem index ." in output
        assert 'aur query "question"' in output

        # Verify interactive setup section
        assert "For interactive setup:" in output
        assert "aur init --interactive" in output

        # Verify health check section
        assert "Check installation health:" in output
        assert "aur doctor" in output
        assert "aur version" in output

    def test_display_install_feedback_missing_components(self):
        """Test message when some components are missing."""
        setup = load_setup_module()

        # Mock __import__ to fail for some packages
        import builtins

        original_import = builtins.__import__

        def mock_import(name, *args, **kwargs):
            if name == "aurora_core":
                raise ImportError(f"No module named '{name}'")
            return original_import(name, *args, **kwargs)

        captured_output = StringIO()
        with patch("sys.stdout", captured_output):
            with patch("builtins.__import__", side_effect=mock_import):
                setup.display_install_feedback()

        output = captured_output.getvalue()

        # Should still show success header
        assert "🔗 Aurora Installer" in output
        assert "==> Installation complete!" in output

        # Should show warning about missing components
        assert "⚠️  Warning: Some components failed to install:" in output
        assert "✗ aurora_core" in output

        # Should still show next steps
        assert "Get started:" in output

    def test_output_format_matches_prd_example(self):
        """Test output format matches PRD example from FR-6.1."""
        setup = load_setup_module()

        captured_output = StringIO()
        with patch("sys.stdout", captured_output):
            setup.display_install_feedback()

        output = captured_output.getvalue()

        # Verify format matches PRD requirements:
        # - Emoji icon (🔗)
        # - "==>" arrows for key messages
        # - Clear section headers
        # - Indented commands
        # - Friendly messaging

        assert "🔗" in output
        assert "==>" in output
        assert output.count("aur init") >= 2  # Both regular and interactive
        assert output.count("aur doctor") == 1
        assert output.count("aur version") == 1

    def test_no_verbose_pip_output(self):
        """Test that output is clean without verbose pip details."""
        setup = load_setup_module()

        captured_output = StringIO()
        with patch("sys.stdout", captured_output):
            setup.display_install_feedback()

        output = captured_output.getvalue()

        # Should NOT contain verbose pip output
        assert "Collecting" not in output
        assert "Downloading" not in output
        assert "Installing" not in output
        assert "Successfully installed" not in output.lower() or output.count(
            "successfully"
        ) == 1  # Only our message

        # Should be concise
        line_count = len(output.strip().split("\n"))
        assert line_count < 25  # Reasonable length, not verbose

    def test_message_shows_version(self):
        """Test that version is displayed in message."""
        setup = load_setup_module()

        captured_output = StringIO()
        with patch("sys.stdout", captured_output):
            setup.display_install_feedback()

        output = captured_output.getvalue()

        # Should show version
        assert "v0.2.0" in output or "0.2.0" in output

    def test_message_suggests_key_commands(self):
        """Test that key commands are suggested."""
        setup = load_setup_module()

        captured_output = StringIO()
        with patch("sys.stdout", captured_output):
            setup.display_install_feedback()

        output = captured_output.getvalue()

        # Should suggest all key commands from FR-6.1
        assert "aur init" in output
        assert "aur mem index" in output
        assert "aur query" in output
        assert "aur doctor" in output
        assert "aur version" in output  # FR-6.2 integration

    def test_post_develop_command_exists(self):
        """Test that PostDevelopCommand class exists."""
        setup = load_setup_module()

        # Just verify the classes exist (actual testing requires complex setup mocking)
        assert hasattr(setup, "PostDevelopCommand")
        assert hasattr(setup, "PostInstallCommand")

        # Verify they call the right function (check method resolution)
        assert hasattr(setup.PostDevelopCommand, "run")
        assert hasattr(setup.PostInstallCommand, "run")
