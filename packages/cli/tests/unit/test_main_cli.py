"""Unit tests for aurora_cli.main CLI routing and commands.

This module tests the main CLI entry point and command routing.
IMPORTANT: These are UNIT tests - they use mocks, NOT subprocess.run().
"""

from __future__ import annotations

import logging
from unittest.mock import Mock, patch

import pytest
from click.testing import CliRunner

from aurora_cli.main import cli


class TestCliGroup:
    """Test the main CLI group function and flag combinations."""

    @pytest.mark.cli
    @pytest.mark.critical
    @patch("aurora_cli.main.logging.basicConfig")
    def test_cli_with_verbose_flag(self, mock_basic_config: Mock) -> None:
        """Test cli() function with --verbose flag sets INFO logging level."""
        runner = CliRunner()
        result = runner.invoke(cli, ["--verbose"])

        # Verify logging was configured with INFO level
        mock_basic_config.assert_called_once_with(level=logging.INFO)
        assert result.exit_code == 0

    @patch("aurora_cli.main.logging.basicConfig")
    def test_cli_with_debug_flag(self, mock_basic_config: Mock) -> None:
        """Test cli() function with --debug flag sets DEBUG logging level."""
        runner = CliRunner()
        result = runner.invoke(cli, ["--debug"])

        # Verify logging was configured with DEBUG level
        mock_basic_config.assert_called_once_with(level=logging.DEBUG)
        assert result.exit_code == 0

    def test_cli_without_flags(self) -> None:
        """Test cli() function without any flags."""
        runner = CliRunner()
        result = runner.invoke(cli, [])
        assert result.exit_code == 0

    def test_cli_version_flag(self) -> None:
        """Test cli() function with --version flag."""
        runner = CliRunner()
        result = runner.invoke(cli, ["--version"])
        assert result.exit_code == 0
        assert "aur v" in result.output


class TestCliCommands:
    """Test CLI commands are properly registered."""

    def test_help_shows_available_commands(self) -> None:
        """Test --help shows available commands."""
        runner = CliRunner()
        result = runner.invoke(cli, ["--help"])
        assert result.exit_code == 0
        # Check for key commands
        assert "init" in result.output
        assert "doctor" in result.output
        assert "mem" in result.output

    def test_init_command_exists(self) -> None:
        """Test init command is registered."""
        runner = CliRunner()
        result = runner.invoke(cli, ["init", "--help"])
        assert result.exit_code == 0

    def test_doctor_command_exists(self) -> None:
        """Test doctor command is registered."""
        runner = CliRunner()
        result = runner.invoke(cli, ["doctor", "--help"])
        assert result.exit_code == 0

    def test_mem_command_exists(self) -> None:
        """Test mem command is registered."""
        runner = CliRunner()
        result = runner.invoke(cli, ["mem", "--help"])
        assert result.exit_code == 0

    def test_soar_command_exists(self) -> None:
        """Test soar command is registered."""
        runner = CliRunner()
        result = runner.invoke(cli, ["soar", "--help"])
        assert result.exit_code == 0

    def test_goals_command_exists(self) -> None:
        """Test goals command is registered."""
        runner = CliRunner()
        result = runner.invoke(cli, ["goals", "--help"])
        assert result.exit_code == 0

    def test_spawn_command_exists(self) -> None:
        """Test spawn command is registered."""
        runner = CliRunner()
        result = runner.invoke(cli, ["spawn", "--help"])
        assert result.exit_code == 0

    def test_plan_command_exists(self) -> None:
        """Test plan command is registered."""
        runner = CliRunner()
        result = runner.invoke(cli, ["plan", "--help"])
        assert result.exit_code == 0

    def test_agents_command_exists(self) -> None:
        """Test agents command is registered."""
        runner = CliRunner()
        result = runner.invoke(cli, ["agents", "--help"])
        assert result.exit_code == 0

    def test_budget_command_exists(self) -> None:
        """Test budget command is registered."""
        runner = CliRunner()
        result = runner.invoke(cli, ["budget", "--help"])
        assert result.exit_code == 0

    def test_friction_command_exists(self) -> None:
        """Test friction command is registered."""
        runner = CliRunner()
        result = runner.invoke(cli, ["friction", "--help"])
        assert result.exit_code == 0
