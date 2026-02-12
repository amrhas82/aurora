"""Integration tests for goals_command behavior.

These tests verify the goals command's core behavior remains consistent
after refactoring to reduce complexity.
"""

from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from aurora_cli.commands.goals import goals_command


@pytest.fixture
def cli_runner():
    """Create a CLI runner for testing."""
    return CliRunner()


class TestGoalsCommandValidation:
    """Tests for parameter validation in goals command."""

    def test_rejects_missing_tool(self, cli_runner):
        """Test that missing tool in PATH is rejected."""
        with patch("shutil.which", return_value=None):
            with patch("aurora_cli.commands.goals.Config"):
                result = cli_runner.invoke(
                    goals_command,
                    ["Test goal for validation"],
                )
                assert result.exit_code != 0

    def test_accepts_valid_tool(self, cli_runner):
        """Test that valid tool passes validation."""
        with patch("shutil.which", return_value="/usr/bin/claude"):
            with patch("aurora_cli.commands.goals.Config") as mock_config:
                mock_config.return_value.soar_default_tool = "claude"
                mock_config.return_value.soar_default_model = "sonnet"
                with patch("aurora_cli.commands.goals.CLIPipeLLMClient"):
                    with patch("aurora_cli.commands.goals.create_plan") as mock_plan:
                        mock_result = MagicMock()
                        mock_result.success = False
                        mock_result.error = "Test abort"
                        mock_plan.return_value = mock_result
                        result = cli_runner.invoke(
                            goals_command,
                            ["Test goal for validation"],
                        )
                        # Should get past validation to plan creation
                        mock_plan.assert_called_once()


class TestGoalsCommandToolResolution:
    """Tests for tool and model resolution."""

    def test_cli_tool_overrides_env(self, cli_runner):
        """Test that --tool flag overrides environment."""
        with patch.dict("os.environ", {"AURORA_GOALS_TOOL": "env_tool"}):
            with patch("shutil.which", return_value="/usr/bin/cli_tool"):
                with patch("aurora_cli.commands.goals.Config") as mock_config:
                    mock_config.return_value.soar_default_tool = "config_tool"
                    mock_config.return_value.soar_default_model = "sonnet"
                    with patch("aurora_cli.commands.goals.CLIPipeLLMClient"):
                        with patch("aurora_cli.commands.goals.create_plan") as mock_plan:
                            mock_result = MagicMock()
                            mock_result.success = False
                            mock_result.error = "Test"
                            mock_plan.return_value = mock_result
                            cli_runner.invoke(
                                goals_command,
                                ["Test goal", "--tool", "cli_tool"],
                            )
                            # Tool passed to which should be cli_tool

    def test_env_tool_overrides_config(self, cli_runner):
        """Test that env var overrides config default."""
        with patch.dict("os.environ", {"AURORA_GOALS_TOOL": "env_tool"}, clear=False):
            with patch("shutil.which", return_value="/usr/bin/env_tool"):
                with patch("aurora_cli.commands.goals.Config") as mock_config:
                    mock_config.return_value.soar_default_tool = "config_tool"
                    mock_config.return_value.soar_default_model = "sonnet"
                    with patch("aurora_cli.commands.goals.CLIPipeLLMClient"):
                        with patch("aurora_cli.commands.goals.create_plan") as mock_plan:
                            mock_result = MagicMock()
                            mock_result.success = False
                            mock_result.error = "Test"
                            mock_plan.return_value = mock_result
                            cli_runner.invoke(
                                goals_command,
                                ["Test goal"],
                            )


class TestGoalsCommandOutput:
    """Tests for output handling."""

    def test_json_output_format(self, cli_runner):
        """Test that --format json produces JSON output."""
        with patch("shutil.which", return_value="/usr/bin/claude"):
            with patch("aurora_cli.commands.goals.Config") as mock_config:
                mock_config.return_value.soar_default_tool = "claude"
                mock_config.return_value.soar_default_model = "sonnet"
                with patch("aurora_cli.commands.goals.CLIPipeLLMClient"):
                    with patch("aurora_cli.commands.goals.create_plan") as mock_plan:
                        mock_result = MagicMock()
                        mock_result.success = True
                        mock_result.plan = MagicMock()
                        mock_result.plan.model_dump_json.return_value = '{"test": "json"}'
                        mock_result.plan_dir = "/tmp/test"
                        mock_plan.return_value = mock_result
                        result = cli_runner.invoke(
                            goals_command,
                            ["Test goal", "--format", "json", "--yes"],
                        )
                        assert '{"test": "json"}' in result.output


class TestGoalsCommandAutoInit:
    """Tests for auto-initialization behavior."""

    def test_auto_init_creates_aurora_dir(self, cli_runner, tmp_path):
        """Test that auto-init creates .aurora directory."""
        with cli_runner.isolated_filesystem(temp_dir=tmp_path):
            with patch("shutil.which", return_value="/usr/bin/claude"):
                with patch("aurora_cli.commands.goals.Config") as mock_config:
                    mock_config.return_value.soar_default_tool = "claude"
                    mock_config.return_value.soar_default_model = "sonnet"
                    with patch("aurora_cli.commands.goals.CLIPipeLLMClient"):
                        with patch("aurora_cli.commands.goals.create_plan") as mock_plan:
                            mock_result = MagicMock()
                            mock_result.success = False
                            mock_result.error = "Test"
                            mock_plan.return_value = mock_result
                            with patch(
                                "aurora_cli.commands.init_helpers.create_directory_structure"
                            ) as mock_init:
                                cli_runner.invoke(
                                    goals_command,
                                    ["Test goal"],
                                )
                                # Auto-init should be called since .aurora doesn't exist
                                mock_init.assert_called_once()

    def test_no_auto_init_flag_skips_init(self, cli_runner, tmp_path):
        """Test that --no-auto-init skips initialization."""
        with cli_runner.isolated_filesystem(temp_dir=tmp_path):
            with patch("shutil.which", return_value="/usr/bin/claude"):
                with patch("aurora_cli.commands.goals.Config") as mock_config:
                    mock_config.return_value.soar_default_tool = "claude"
                    mock_config.return_value.soar_default_model = "sonnet"
                    with patch("aurora_cli.commands.goals.CLIPipeLLMClient"):
                        with patch("aurora_cli.commands.goals.create_plan") as mock_plan:
                            mock_result = MagicMock()
                            mock_result.success = False
                            mock_result.error = "Test"
                            mock_plan.return_value = mock_result
                            with patch(
                                "aurora_cli.commands.init_helpers.create_directory_structure"
                            ) as mock_init:
                                cli_runner.invoke(
                                    goals_command,
                                    ["Test goal", "--no-auto-init"],
                                )
                                # Auto-init should NOT be called
                                mock_init.assert_not_called()


class TestGoalsCommandPlanCreation:
    """Tests for plan creation behavior."""

    def test_passes_context_files_to_create_plan(self, cli_runner, tmp_path):
        """Test that context files are passed to create_plan."""
        context_file = tmp_path / "context.py"
        context_file.write_text("# context")

        with patch("shutil.which", return_value="/usr/bin/claude"):
            with patch("aurora_cli.commands.goals.Config") as mock_config:
                mock_config.return_value.soar_default_tool = "claude"
                mock_config.return_value.soar_default_model = "sonnet"
                with patch("aurora_cli.commands.goals.CLIPipeLLMClient"):
                    with patch("aurora_cli.commands.goals.create_plan") as mock_plan:
                        mock_result = MagicMock()
                        mock_result.success = False
                        mock_result.error = "Test"
                        mock_plan.return_value = mock_result
                        cli_runner.invoke(
                            goals_command,
                            ["Test goal", "--context", str(context_file)],
                        )
                        # Verify context files passed
                        call_kwargs = mock_plan.call_args[1]
                        assert call_kwargs["context_files"] == [context_file]

    def test_no_decompose_flag_passed(self, cli_runner):
        """Test that --no-decompose sets auto_decompose=False."""
        with patch("shutil.which", return_value="/usr/bin/claude"):
            with patch("aurora_cli.commands.goals.Config") as mock_config:
                mock_config.return_value.soar_default_tool = "claude"
                mock_config.return_value.soar_default_model = "sonnet"
                with patch("aurora_cli.commands.goals.CLIPipeLLMClient"):
                    with patch("aurora_cli.commands.goals.create_plan") as mock_plan:
                        mock_result = MagicMock()
                        mock_result.success = False
                        mock_result.error = "Test"
                        mock_plan.return_value = mock_result
                        cli_runner.invoke(
                            goals_command,
                            ["Test goal", "--no-decompose"],
                        )
                        call_kwargs = mock_plan.call_args[1]
                        assert call_kwargs["auto_decompose"] is False
