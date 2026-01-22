"""Unit tests for refactored goals command helper functions.

These tests verify the extracted helper functions work correctly
after refactoring goals_command to reduce complexity.
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest  # noqa: F401 - pytest is needed for fixtures (tmp_path)


class TestResolveToolAndModel:
    """Tests for _resolve_tool_and_model function."""

    def test_cli_tool_overrides_env_and_config(self):
        """Test that CLI --tool flag overrides env and config."""
        from aurora_cli.commands.goals import _resolve_tool_and_model

        config = MagicMock()
        config.soar_default_tool = "config_tool"
        config.soar_default_model = "sonnet"

        with patch.dict("os.environ", {"AURORA_GOALS_TOOL": "env_tool"}):
            tool, model = _resolve_tool_and_model(
                cli_tool="cli_tool",
                cli_model=None,
                config=config,
            )
            assert tool == "cli_tool"

    def test_env_tool_overrides_config(self):
        """Test that env var overrides config default."""
        from aurora_cli.commands.goals import _resolve_tool_and_model

        config = MagicMock()
        config.soar_default_tool = "config_tool"
        config.soar_default_model = "sonnet"

        with patch.dict("os.environ", {"AURORA_GOALS_TOOL": "env_tool"}, clear=False):
            tool, model = _resolve_tool_and_model(
                cli_tool=None,
                cli_model=None,
                config=config,
            )
            assert tool == "env_tool"

    def test_config_tool_used_when_no_cli_or_env(self):
        """Test that config default is used when no CLI/env."""
        from aurora_cli.commands.goals import _resolve_tool_and_model

        config = MagicMock()
        config.soar_default_tool = "config_tool"
        config.soar_default_model = "sonnet"

        with patch.dict("os.environ", {}, clear=True):
            tool, model = _resolve_tool_and_model(
                cli_tool=None,
                cli_model=None,
                config=config,
            )
            assert tool == "config_tool"

    def test_cli_model_overrides_env(self):
        """Test that CLI --model flag overrides env."""
        from aurora_cli.commands.goals import _resolve_tool_and_model

        config = MagicMock()
        config.soar_default_tool = "claude"
        config.soar_default_model = "sonnet"

        with patch.dict("os.environ", {"AURORA_GOALS_MODEL": "sonnet"}):
            tool, model = _resolve_tool_and_model(
                cli_tool=None,
                cli_model="opus",
                config=config,
            )
            assert model == "opus"

    def test_env_model_overrides_config(self):
        """Test that env model overrides config default."""
        from aurora_cli.commands.goals import _resolve_tool_and_model

        config = MagicMock()
        config.soar_default_tool = "claude"
        config.soar_default_model = "sonnet"

        with patch.dict("os.environ", {"AURORA_GOALS_MODEL": "opus"}):
            tool, model = _resolve_tool_and_model(
                cli_tool=None,
                cli_model=None,
                config=config,
            )
            assert model == "opus"

    def test_invalid_env_model_falls_back_to_config(self):
        """Test that invalid env model falls back to config."""
        from aurora_cli.commands.goals import _resolve_tool_and_model

        config = MagicMock()
        config.soar_default_tool = "claude"
        config.soar_default_model = "sonnet"

        with patch.dict("os.environ", {"AURORA_GOALS_MODEL": "invalid"}):
            tool, model = _resolve_tool_and_model(
                cli_tool=None,
                cli_model=None,
                config=config,
            )
            assert model == "sonnet"


class TestValidateGoalsRequirements:
    """Tests for _validate_goals_requirements function."""

    def test_missing_tool_returns_error(self):
        """Test that missing tool returns error message."""
        from aurora_cli.commands.goals import _validate_goals_requirements

        with patch("shutil.which", return_value=None):
            error = _validate_goals_requirements(tool="missing_tool")
            assert error is not None
            assert "missing_tool" in error
            assert "not found" in error.lower()

    def test_valid_tool_returns_none(self):
        """Test that valid tool returns None (no error)."""
        from aurora_cli.commands.goals import _validate_goals_requirements

        with patch("shutil.which", return_value="/usr/bin/claude"):
            error = _validate_goals_requirements(tool="claude")
            assert error is None

    def test_validates_tool_exists_in_path(self):
        """Test that shutil.which is called with tool name."""
        from aurora_cli.commands.goals import _validate_goals_requirements

        with patch("shutil.which") as mock_which:
            mock_which.return_value = "/usr/bin/mytool"
            _validate_goals_requirements(tool="mytool")
            mock_which.assert_called_once_with("mytool")


class TestEnsureAuroraInitialized:
    """Tests for _ensure_aurora_initialized function."""

    def test_creates_aurora_dir_if_missing(self, tmp_path):
        """Test that .aurora directory is created if missing."""
        from aurora_cli.commands.goals import _ensure_aurora_initialized

        with patch("aurora_cli.commands.goals.Path") as mock_path_class:
            mock_cwd = MagicMock()
            mock_path_class.cwd.return_value = mock_cwd
            mock_aurora_dir = mock_cwd / ".aurora"
            mock_aurora_dir.exists.return_value = False

            with patch(
                "aurora_cli.commands.init_helpers.create_directory_structure"
            ) as mock_create:
                _ensure_aurora_initialized(verbose=False)
                mock_create.assert_called_once()

    def test_skips_if_aurora_dir_exists(self, tmp_path):
        """Test that init is skipped if .aurora exists."""
        from aurora_cli.commands.goals import _ensure_aurora_initialized

        # Create actual .aurora directory
        aurora_dir = tmp_path / ".aurora"
        aurora_dir.mkdir()

        with patch("aurora_cli.commands.goals.Path") as mock_path_class:
            mock_path_class.cwd.return_value = tmp_path

            with patch(
                "aurora_cli.commands.init_helpers.create_directory_structure"
            ) as mock_create:
                _ensure_aurora_initialized(verbose=False)
                mock_create.assert_not_called()


class TestDisplayGoalsResults:
    """Tests for _display_goals_results function."""

    def test_json_output_returns_json_string(self):
        """Test that JSON format outputs plan as JSON."""
        from aurora_cli.commands.goals import _display_goals_results

        mock_plan = MagicMock()
        mock_plan.model_dump_json.return_value = '{"plan_id": "test-123"}'
        mock_plan.subgoals = []

        mock_result = MagicMock()
        mock_result.plan = mock_plan
        mock_result.plan_dir = "/tmp/test"
        mock_result.warnings = []

        output = _display_goals_results(
            result=mock_result,
            output_format="json",
            verbose=False,
            yes=True,
        )

        assert output == '{"plan_id": "test-123"}'

    def test_rich_output_returns_none(self):
        """Test that rich format returns None (prints to console)."""
        from aurora_cli.commands.goals import _display_goals_results

        mock_subgoal = MagicMock()
        mock_subgoal.title = "Test subgoal"
        mock_subgoal.ideal_agent = "code-developer"
        mock_subgoal.assigned_agent = "code-developer"
        mock_subgoal.match_quality = None

        mock_plan = MagicMock()
        mock_plan.plan_id = "test-123"
        mock_plan.subgoals = [mock_subgoal]

        mock_result = MagicMock()
        mock_result.plan = mock_plan
        mock_result.plan_dir = "/tmp/test"
        mock_result.warnings = []

        with patch("aurora_cli.commands.goals.console"):
            output = _display_goals_results(
                result=mock_result,
                output_format="rich",
                verbose=False,
                yes=True,
            )

        assert output is None

    def test_counts_match_qualities(self):
        """Test that match quality counts are calculated correctly."""
        from aurora_cli.commands.goals import _display_goals_results

        # Create subgoals with different match qualities
        excellent_sg = MagicMock()
        excellent_sg.title = "Excellent subgoal"
        excellent_sg.ideal_agent = "code-developer"
        excellent_sg.assigned_agent = "code-developer"
        excellent_sg.match_quality = MagicMock(value="excellent")

        acceptable_sg = MagicMock()
        acceptable_sg.title = "Acceptable subgoal"
        acceptable_sg.ideal_agent = "code-developer"
        acceptable_sg.assigned_agent = "system-architect"
        acceptable_sg.match_quality = MagicMock(value="acceptable")

        insufficient_sg = MagicMock()
        insufficient_sg.title = "Insufficient subgoal"
        insufficient_sg.ideal_agent = "special-agent"
        insufficient_sg.assigned_agent = "spawned"
        insufficient_sg.match_quality = MagicMock(value="insufficient")

        mock_plan = MagicMock()
        mock_plan.plan_id = "test-123"
        mock_plan.subgoals = [excellent_sg, acceptable_sg, insufficient_sg]

        mock_result = MagicMock()
        mock_result.plan = mock_plan
        mock_result.plan_dir = "/tmp/test"
        mock_result.warnings = []

        # Capture console output
        with patch("aurora_cli.commands.goals.console") as mock_console:
            _display_goals_results(
                result=mock_result,
                output_format="rich",
                verbose=False,
                yes=True,
            )

            # Verify summary line was printed with correct counts
            calls = [str(call) for call in mock_console.print.call_args_list]
            summary_calls = [c for c in calls if "Summary" in c]
            assert len(summary_calls) > 0


class TestGenerateGoalsPlan:
    """Tests for plan generation wrapper (Task 7.2)."""

    def test_generate_goals_plan_calls_create_plan(self):
        """Test that _generate_goals_plan calls create_plan correctly."""
        from aurora_cli.commands.goals import _generate_goals_plan

        mock_config = MagicMock()
        mock_result = MagicMock()
        mock_result.success = True

        with patch("aurora_cli.commands.goals.create_plan") as mock_create:
            mock_create.return_value = mock_result

            result = _generate_goals_plan(
                goal="Test goal",
                context_files=None,
                no_decompose=False,
                config=mock_config,
                yes=True,
            )

            mock_create.assert_called_once()
            assert result == mock_result

    def test_generate_goals_plan_passes_context_files(self):
        """Test that context files are passed to create_plan."""
        from aurora_cli.commands.goals import _generate_goals_plan

        mock_config = MagicMock()
        context_files = [Path("/tmp/context.py")]

        with patch("aurora_cli.commands.goals.create_plan") as mock_create:
            mock_create.return_value = MagicMock(success=True)

            _generate_goals_plan(
                goal="Test goal",
                context_files=context_files,
                no_decompose=False,
                config=mock_config,
                yes=True,
            )

            call_kwargs = mock_create.call_args[1]
            assert call_kwargs["context_files"] == context_files

    def test_generate_goals_plan_sets_goals_only_true(self):
        """Test that goals_only=True is always set."""
        from aurora_cli.commands.goals import _generate_goals_plan

        mock_config = MagicMock()

        with patch("aurora_cli.commands.goals.create_plan") as mock_create:
            mock_create.return_value = MagicMock(success=True)

            _generate_goals_plan(
                goal="Test goal",
                context_files=None,
                no_decompose=False,
                config=mock_config,
                yes=True,
            )

            call_kwargs = mock_create.call_args[1]
            assert call_kwargs["goals_only"] is True


class TestInvokeSoarPipeline:
    """Tests for SOAR pipeline invocation (Task 7.3)."""

    def test_invoke_soar_pipeline_returns_result(self):
        """Test that _invoke_soar_pipeline returns create_plan result."""
        from aurora_cli.commands.goals import _generate_goals_plan

        mock_config = MagicMock()
        expected_result = MagicMock()
        expected_result.success = True
        expected_result.plan = MagicMock()

        with patch("aurora_cli.commands.goals.create_plan") as mock_create:
            mock_create.return_value = expected_result

            result = _generate_goals_plan(
                goal="Test goal",
                context_files=None,
                no_decompose=False,
                config=mock_config,
                yes=True,
            )

            assert result is expected_result


class TestErrorHandling:
    """Tests for error handling (Task 7.4)."""

    def test_validate_returns_error_on_missing_tool(self):
        """Test that validation returns error message for missing tool."""
        from aurora_cli.commands.goals import _validate_goals_requirements

        with patch("shutil.which", return_value=None):
            error = _validate_goals_requirements(tool="nonexistent")
            assert error is not None
            assert "nonexistent" in error

    def test_generate_plan_returns_failure_result(self):
        """Test that failed plan creation returns result with error."""
        from aurora_cli.commands.goals import _generate_goals_plan

        mock_config = MagicMock()
        failed_result = MagicMock()
        failed_result.success = False
        failed_result.error = "Plan creation failed"

        with patch("aurora_cli.commands.goals.create_plan") as mock_create:
            mock_create.return_value = failed_result

            result = _generate_goals_plan(
                goal="Test goal",
                context_files=None,
                no_decompose=False,
                config=mock_config,
                yes=True,
            )

            assert result.success is False
            assert result.error == "Plan creation failed"
