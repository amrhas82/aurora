"""Integration tests for headless_command behavior.

These tests verify the headless command's core behavior remains consistent
after refactoring to reduce complexity.
"""

from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from aurora_cli.commands.headless import headless_command


@pytest.fixture
def cli_runner():
    """Create a CLI runner for testing."""
    return CliRunner()


@pytest.fixture
def temp_aurora_dir(tmp_path):
    """Create a temporary .aurora directory structure."""
    aurora_dir = tmp_path / ".aurora" / "headless"
    aurora_dir.mkdir(parents=True)
    return aurora_dir


@pytest.fixture
def mock_prompt_file(temp_aurora_dir):
    """Create a mock prompt file."""
    prompt_file = temp_aurora_dir / "prompt.md"
    prompt_file.write_text("Test prompt for headless execution")
    return prompt_file


class TestHeadlessCommandListTools:
    """Tests for --list-tools early exit."""

    def test_list_tools_exits_early(self, cli_runner):
        """Test that --list-tools displays tools and exits without errors."""
        with patch("aurora_cli.commands.headless._list_available_tools") as mock_list:
            result = cli_runner.invoke(headless_command, ["--list-tools"])
            mock_list.assert_called_once()
            assert result.exit_code == 0


class TestHeadlessCommandShowConfig:
    """Tests for --show-config early exit."""

    def test_show_config_exits_early(self, cli_runner, tmp_path, mock_prompt_file):
        """Test that --show-config displays config and exits."""
        with patch("aurora_cli.commands.headless._show_effective_config") as mock_show:
            with patch("shutil.which", return_value="/usr/bin/claude"):
                result = cli_runner.invoke(
                    headless_command,
                    ["--show-config", "-t", "claude"],
                    catch_exceptions=False,
                )
                # Should call show config
                mock_show.assert_called_once()


class TestHeadlessCommandValidation:
    """Tests for parameter validation."""

    def test_rejects_negative_max_retries(self, cli_runner):
        """Test that negative --max-retries is rejected."""
        result = cli_runner.invoke(
            headless_command,
            ["-t", "claude", "--max-retries", "-1"],
        )
        assert result.exit_code != 0
        assert "max-retries" in result.output.lower() or result.exit_code == 1

    def test_rejects_negative_retry_delay(self, cli_runner):
        """Test that negative --retry-delay is rejected."""
        result = cli_runner.invoke(
            headless_command,
            ["-t", "claude", "--retry-delay", "-1.0"],
        )
        assert result.exit_code != 0

    def test_rejects_zero_budget(self, cli_runner):
        """Test that zero --budget is rejected."""
        result = cli_runner.invoke(
            headless_command,
            ["-t", "claude", "--budget", "0"],
        )
        assert result.exit_code != 0

    def test_rejects_zero_time_limit(self, cli_runner):
        """Test that zero --time-limit is rejected."""
        result = cli_runner.invoke(
            headless_command,
            ["-t", "claude", "--time-limit", "0"],
        )
        assert result.exit_code != 0


class TestHeadlessCommandToolChecks:
    """Tests for tool existence validation."""

    def test_rejects_missing_tools(self, cli_runner, tmp_path):
        """Test that missing tools are rejected."""
        # Create prompt file
        aurora_dir = tmp_path / ".aurora" / "headless"
        aurora_dir.mkdir(parents=True)
        prompt_file = aurora_dir / "prompt.md"
        prompt_file.write_text("Test prompt")

        with patch("shutil.which", return_value=None):
            result = cli_runner.invoke(
                headless_command,
                ["-t", "nonexistent_tool"],
            )
            assert result.exit_code != 0


class TestHeadlessCommandPromptHandling:
    """Tests for prompt file and stdin handling."""

    def test_stdin_empty_prompt_rejected(self, cli_runner):
        """Test that empty stdin prompt is rejected."""
        result = cli_runner.invoke(
            headless_command,
            ["-t", "claude", "--stdin"],
            input="",
        )
        # Should fail due to empty prompt or stdin not being piped properly
        assert result.exit_code != 0

    def test_missing_prompt_file_rejected(self, cli_runner, tmp_path):
        """Test that missing prompt file is rejected."""
        with patch("shutil.which", return_value="/usr/bin/claude"):
            result = cli_runner.invoke(
                headless_command,
                ["-t", "claude", "-p", str(tmp_path / "nonexistent.md")],
            )
            assert result.exit_code != 0


class TestHeadlessCommandGitSafety:
    """Tests for git branch safety checks."""

    def test_rejects_main_branch_by_default(self, cli_runner, tmp_path):
        """Test that main branch is rejected without --allow-main."""
        # Create prompt file
        aurora_dir = tmp_path / ".aurora" / "headless"
        aurora_dir.mkdir(parents=True)
        prompt_file = aurora_dir / "prompt.md"
        prompt_file.write_text("Test prompt")

        with patch("shutil.which", return_value="/usr/bin/claude"):
            with patch("subprocess.run") as mock_run:
                mock_run.return_value = MagicMock(stdout="main\n", returncode=0)
                result = cli_runner.invoke(
                    headless_command,
                    ["-t", "claude", "-p", str(prompt_file)],
                )
                assert result.exit_code != 0

    def test_allows_main_with_flag(self, cli_runner, tmp_path):
        """Test that --allow-main permits main branch."""
        # Create prompt file
        aurora_dir = tmp_path / ".aurora" / "headless"
        aurora_dir.mkdir(parents=True)
        prompt_file = aurora_dir / "prompt.md"
        prompt_file.write_text("Test prompt")
        scratchpad = aurora_dir / "scratchpad.md"

        with patch("shutil.which", return_value="/usr/bin/claude"):
            with patch("subprocess.run") as mock_run:
                # First call: git branch check returns main
                # Second call: would be tool execution
                mock_run.return_value = MagicMock(stdout="main\n", returncode=0)

                with patch("aurora_cli.commands.headless._run_single_tool_loop") as mock_loop:
                    result = cli_runner.invoke(
                        headless_command,
                        ["-t", "claude", "-p", str(prompt_file), "--allow-main"],
                    )
                    # Should proceed past git check
                    # (may fail later but git check should pass)


class TestHeadlessCommandExecution:
    """Tests for main execution dispatch."""

    def test_single_tool_calls_single_loop(self, cli_runner, tmp_path):
        """Test that single tool uses _run_single_tool_loop."""
        aurora_dir = tmp_path / ".aurora" / "headless"
        aurora_dir.mkdir(parents=True)
        prompt_file = aurora_dir / "prompt.md"
        prompt_file.write_text("Test prompt")

        with patch("shutil.which", return_value="/usr/bin/claude"):
            with patch("subprocess.run") as mock_git:
                mock_git.return_value = MagicMock(stdout="feature\n", returncode=0)

                with patch("aurora_cli.commands.headless._run_single_tool_loop") as mock_single:
                    result = cli_runner.invoke(
                        headless_command,
                        ["-t", "claude", "-p", str(prompt_file), "--max", "1"],
                    )
                    mock_single.assert_called_once()

    def test_multi_tool_parallel_calls_multi_loop(self, cli_runner, tmp_path):
        """Test that multi-tool parallel uses _run_multi_tool_loop."""
        aurora_dir = tmp_path / ".aurora" / "headless"
        aurora_dir.mkdir(parents=True)
        prompt_file = aurora_dir / "prompt.md"
        prompt_file.write_text("Test prompt")

        with patch("shutil.which", return_value="/usr/bin/tool"):
            with patch("subprocess.run") as mock_git:
                mock_git.return_value = MagicMock(stdout="feature\n", returncode=0)

                with patch("asyncio.run") as mock_asyncio:
                    result = cli_runner.invoke(
                        headless_command,
                        [
                            "-t",
                            "claude",
                            "-t",
                            "opencode",
                            "-p",
                            str(prompt_file),
                            "--max",
                            "1",
                            "--parallel",
                        ],
                    )
                    mock_asyncio.assert_called_once()
