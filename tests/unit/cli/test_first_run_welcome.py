"""Unit tests for first-run welcome message.

Tests the welcome message displayed when user runs aur for the first time.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from aurora_cli.main import cli


@pytest.fixture
def runner():
    """Click test runner fixture."""
    return CliRunner()


class TestFirstRunWelcome:
    """Test first-run welcome message functionality."""

    @patch("aurora_cli.config._get_aurora_home")
    def test_shows_welcome_when_no_config(
        self,
        mock_get_home,
        runner: CliRunner,
    ):
        """Test welcome message displays when config doesn't exist."""
        # Mock aurora home that doesn't exist
        mock_home = MagicMock(spec=Path)
        mock_home.exists.return_value = False
        mock_home.__truediv__ = lambda self, other: MagicMock(spec=Path, exists=lambda: False)
        mock_get_home.return_value = mock_home

        # Run aur without subcommand
        result = runner.invoke(cli, [])

        assert result.exit_code == 0
        assert "Welcome to AURORA!" in result.output
        assert "aur init" in result.output
        assert "aur doctor" in result.output
        assert "aur version" in result.output

    @patch("aurora_cli.config._get_aurora_home")
    def test_no_welcome_when_config_exists(
        self,
        mock_get_home,
        runner: CliRunner,
    ):
        """Test welcome message doesn't show when config exists."""
        # Mock aurora home with existing config
        mock_home = MagicMock(spec=Path)
        mock_home.exists.return_value = True
        mock_config = MagicMock(spec=Path)
        mock_config.exists.return_value = True
        mock_home.__truediv__ = lambda self, other: mock_config
        mock_get_home.return_value = mock_home

        # Run aur without subcommand
        result = runner.invoke(cli, [])

        assert result.exit_code == 0
        assert "Welcome to AURORA!" not in result.output

    @patch("aurora_cli.config._get_aurora_home")
    def test_no_welcome_with_subcommand(
        self,
        mock_get_home,
        runner: CliRunner,
    ):
        """Test welcome message doesn't show when running a subcommand."""
        # Mock aurora home that doesn't exist
        mock_home = MagicMock(spec=Path)
        mock_home.exists.return_value = False
        mock_home.__truediv__ = lambda self, other: MagicMock(spec=Path, exists=lambda: False)
        mock_get_home.return_value = mock_home

        # Run aur with version subcommand
        result = runner.invoke(cli, ["version"])

        # Welcome should not appear (subcommand was invoked)
        assert "Welcome to AURORA!" not in result.output

    @patch("aurora_cli.config._get_aurora_home")
    def test_shows_welcome_when_directory_exists_but_no_config(
        self,
        mock_get_home,
        runner: CliRunner,
    ):
        """Test welcome shows when .aurora exists but config doesn't."""
        # Mock aurora home that exists but config doesn't
        mock_home = MagicMock(spec=Path)
        mock_home.exists.return_value = True
        mock_config = MagicMock(spec=Path)
        mock_config.exists.return_value = False
        mock_home.__truediv__ = lambda self, other: mock_config
        mock_get_home.return_value = mock_home

        # Run aur without subcommand
        result = runner.invoke(cli, [])

        assert result.exit_code == 0
        assert "Welcome to AURORA!" in result.output
        assert "aur init" in result.output


class TestHelpTextUpdates:
    """Test that help text includes new commands."""

    def test_help_mentions_doctor(self, runner: CliRunner):
        """Test help text mentions aur doctor command."""
        result = runner.invoke(cli, ["--help"])

        assert result.exit_code == 0
        assert "doctor" in result.output.lower()

    def test_help_mentions_version(self, runner: CliRunner):
        """Test help text mentions aur version command."""
        result = runner.invoke(cli, ["--help"])

        assert result.exit_code == 0
        assert "version" in result.output.lower()

    def test_help_shows_doctor_example(self, runner: CliRunner):
        """Test help text shows doctor command examples."""
        result = runner.invoke(cli, ["--help"])

        assert result.exit_code == 0
        assert "aur doctor" in result.output

    def test_help_shows_version_in_common_commands(self, runner: CliRunner):
        """Test version appears in common commands section."""
        result = runner.invoke(cli, ["--help"])

        assert result.exit_code == 0
        # Check that version is in the common commands list
        output_lines = result.output.split("\n")
        common_commands_section = False
        for line in output_lines:
            if "Common Commands:" in line:
                common_commands_section = True
            if common_commands_section and "version" in line.lower():
                assert True
                return

        pytest.fail("version command not found in Common Commands section")
