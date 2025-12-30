"""Unit tests for version CLI command.

Tests the `aur version` command that displays version information.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from aurora_cli.main import cli
from click.testing import CliRunner


@pytest.fixture
def runner():
    """Click test runner fixture."""
    return CliRunner()


class TestVersionCommandBasics:
    """Test basic version command functionality."""

    def test_help_text(self, runner: CliRunner):
        """Test help text displays correctly."""
        result = runner.invoke(cli, ["version", "--help"])
        assert result.exit_code == 0
        assert "version" in result.output.lower()

    def test_version_command_exists(self, runner: CliRunner):
        """Test version command is registered."""
        result = runner.invoke(cli, ["version", "--help"])
        assert result.exit_code == 0


class TestVersionOutput:
    """Test version command output formatting."""

    @patch("aurora_cli.commands.version.importlib.metadata.version")
    @patch("aurora_cli.commands.version.subprocess.run")
    @patch("aurora_cli.commands.version.sys.version_info")
    def test_output_format_with_git(
        self,
        mock_version_info,
        mock_subprocess,
        mock_metadata_version,
        runner: CliRunner,
    ):
        """Test version output format when git is available."""
        # Mock version
        mock_metadata_version.return_value = "0.2.0"

        # Mock git hash
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "abc123\n"
        mock_subprocess.return_value = mock_result

        # Mock Python version
        mock_version_info.major = 3
        mock_version_info.minor = 10
        mock_version_info.micro = 12

        result = runner.invoke(cli, ["version"])

        assert result.exit_code == 0
        assert "Aurora" in result.output
        assert "0.2.0" in result.output
        assert "abc123" in result.output
        assert "Python" in result.output
        assert "3.10.12" in result.output
        assert "Installed at:" in result.output

    @patch("aurora_cli.commands.version.importlib.metadata.version")
    @patch("aurora_cli.commands.version.subprocess.run")
    @patch("aurora_cli.commands.version.sys.version_info")
    def test_output_format_without_git(
        self,
        mock_version_info,
        mock_subprocess,
        mock_metadata_version,
        runner: CliRunner,
    ):
        """Test version output format when git is not available."""
        # Mock version
        mock_metadata_version.return_value = "0.2.0"

        # Mock git not available
        mock_subprocess.side_effect = FileNotFoundError()

        # Mock Python version
        mock_version_info.major = 3
        mock_version_info.minor = 10
        mock_version_info.micro = 12

        result = runner.invoke(cli, ["version"])

        assert result.exit_code == 0
        assert "Aurora" in result.output
        assert "0.2.0" in result.output
        # Should not have git hash
        assert "N/A" not in result.output or "(" not in result.output
        assert "Python" in result.output
        assert "3.10.12" in result.output

    @patch("aurora_cli.commands.version.importlib.metadata.version")
    def test_version_extraction(
        self,
        mock_metadata_version,
        runner: CliRunner,
    ):
        """Test version is extracted from package metadata."""
        mock_metadata_version.return_value = "1.2.3"

        result = runner.invoke(cli, ["version"])

        assert result.exit_code == 0
        assert "1.2.3" in result.output
        mock_metadata_version.assert_called_once_with("aurora-actr")

    @patch("aurora_cli.commands.version.importlib.metadata.version")
    @patch("aurora_cli.commands.version.subprocess.run")
    def test_git_hash_extraction(
        self,
        mock_subprocess,
        mock_metadata_version,
        runner: CliRunner,
    ):
        """Test git hash is extracted correctly."""
        mock_metadata_version.return_value = "0.2.0"

        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "e304815\n"
        mock_subprocess.return_value = mock_result

        result = runner.invoke(cli, ["version"])

        assert result.exit_code == 0
        assert "e304815" in result.output
        # Verify correct git command
        mock_subprocess.assert_called_once()
        call_args = mock_subprocess.call_args
        assert call_args[0][0] == ["git", "rev-parse", "--short", "HEAD"]

    @patch("aurora_cli.commands.version.importlib.metadata.version")
    def test_handles_missing_version_gracefully(
        self,
        mock_metadata_version,
        runner: CliRunner,
    ):
        """Test handles missing version metadata gracefully."""
        mock_metadata_version.side_effect = Exception("Package not found")

        result = runner.invoke(cli, ["version"])

        assert result.exit_code == 0
        assert "unknown" in result.output.lower()


class TestVersionEdgeCases:
    """Test version command edge cases."""

    @patch("aurora_cli.commands.version.importlib.metadata.version")
    @patch("aurora_cli.commands.version.subprocess.run")
    def test_git_command_timeout(
        self,
        mock_subprocess,
        mock_metadata_version,
        runner: CliRunner,
    ):
        """Test handles git command timeout."""
        mock_metadata_version.return_value = "0.2.0"
        mock_subprocess.side_effect = Exception("Timeout")

        result = runner.invoke(cli, ["version"])

        # Should still complete successfully without git hash
        assert result.exit_code == 0
        assert "Aurora" in result.output

    @patch("aurora_cli.commands.version.importlib.metadata.version")
    @patch("aurora_cli.commands.version.subprocess.run")
    def test_git_command_fails(
        self,
        mock_subprocess,
        mock_metadata_version,
        runner: CliRunner,
    ):
        """Test handles git command failure."""
        mock_metadata_version.return_value = "0.2.0"

        mock_result = MagicMock()
        mock_result.returncode = 128  # Not a git repo
        mock_subprocess.return_value = mock_result

        result = runner.invoke(cli, ["version"])

        # Should still complete successfully
        assert result.exit_code == 0
        assert "Aurora" in result.output
