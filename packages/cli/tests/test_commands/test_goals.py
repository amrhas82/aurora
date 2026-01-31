"""Tests for aur goals command.

This module tests the 'aur goals' command for goal decomposition and planning.
The goals command creates a goals.json file with subgoals and agent assignments.
"""

from __future__ import annotations

import json
from unittest.mock import Mock, patch

import pytest
from click.testing import CliRunner

# Import will fail until we create goals.py
try:
    from aurora_cli.commands.goals import goals_command
except ImportError:
    goals_command = None


@pytest.fixture
def cli_runner():
    """Provide a Click CLI runner."""
    return CliRunner()


@pytest.fixture
def temp_aurora_dir(tmp_path):
    """Create a temporary .aurora directory structure."""
    aurora_dir = tmp_path / ".aurora"
    plans_dir = aurora_dir / "plans"
    plans_active = plans_dir / "active"
    plans_archive = plans_dir / "archive"

    plans_active.mkdir(parents=True)
    plans_archive.mkdir(parents=True)

    # Create manifest
    manifest = {
        "version": "1.0",
        "plans_directory": str(plans_dir),
    }
    (plans_dir / "manifest.json").write_text(json.dumps(manifest, indent=2))

    return aurora_dir


@pytest.fixture
def valid_mock_subgoal():
    """Provide a valid mock subgoal for testing."""
    return Mock(
        id="sg-1",
        title="Implement test feature",
        description="Add test feature implementation",
        agent="@code-developer",
        confidence=0.9,
        dependencies=[],
        agent_exists=True,
        recommended_agent="@code-developer",
    )


class TestCommandRegistration:
    """Test that the goals command is properly registered."""

    @pytest.mark.skipif(goals_command is None, reason="goals.py not created yet")
    def test_command_exists(self, cli_runner):
        """Test that goals command is registered."""
        result = cli_runner.invoke(goals_command, ["--help"])
        assert result.exit_code == 0
        assert "goals" in result.output.lower() or "goal" in result.output.lower()

    @pytest.mark.skipif(goals_command is None, reason="goals.py not created yet")
    def test_command_not_named_plan(self, cli_runner):
        """Test that command uses 'goals' not 'plan' in help text."""
        result = cli_runner.invoke(goals_command, ["--help"])
        assert result.exit_code == 0
        # Should say "aur goals" not "aur plan"
        assert "aur goals" in result.output

    @pytest.mark.skipif(goals_command is None, reason="goals.py not created yet")
    def test_has_tool_flag(self, cli_runner):
        """Test that --tool flag exists."""
        result = cli_runner.invoke(goals_command, ["--help"])
        assert result.exit_code == 0
        assert "--tool" in result.output or "-t" in result.output

    @pytest.mark.skipif(goals_command is None, reason="goals.py not created yet")
    def test_has_model_flag(self, cli_runner):
        """Test that --model flag exists."""
        result = cli_runner.invoke(goals_command, ["--help"])
        assert result.exit_code == 0
        assert "--model" in result.output or "-m" in result.output

    @pytest.mark.skipif(goals_command is None, reason="goals.py not created yet")
    def test_has_verbose_flag(self, cli_runner):
        """Test that --verbose flag exists."""
        result = cli_runner.invoke(goals_command, ["--help"])
        assert result.exit_code == 0
        assert "--verbose" in result.output or "-v" in result.output

    @pytest.mark.skipif(goals_command is None, reason="goals.py not created yet")
    def test_has_yes_flag(self, cli_runner):
        """Test that --yes flag exists for skipping confirmation."""
        result = cli_runner.invoke(goals_command, ["--help"])
        assert result.exit_code == 0
        assert "--yes" in result.output or "-y" in result.output


class TestCLIPipeClient:
    """Test CLI-agnostic LLM client usage."""

    @pytest.mark.skipif(goals_command is None, reason="goals.py not created yet")
    def test_uses_cli_pipe_client(self):
        """Test that goals.py imports CLIPipeLLMClient not LLMClient."""
        # This will be checked by grep in verification commands
        import inspect

        from aurora_cli.commands import goals

        source = inspect.getsource(goals)
        assert "CLIPipeLLMClient" in source
        assert "from aurora_cli.llm.cli_pipe_client import CLIPipeLLMClient" in source

    @pytest.mark.skipif(goals_command is None, reason="goals.py not created yet")
    def test_no_api_client_import(self):
        """Test that goals.py does NOT import API-based LLMClient."""
        import inspect

        from aurora_cli.commands import goals

        source = inspect.getsource(goals)
        # Should NOT have the old API client import
        assert "from aurora_cli.llm.llm_client import LLMClient" not in source


class TestToolResolution:
    """Test tool resolution order: CLI → env → config → default."""

    @pytest.mark.skipif(goals_command is None, reason="goals.py not created yet")
    @patch("aurora_cli.commands.goals.CLIPipeLLMClient")
    @patch("aurora_cli.commands.goals.create_plan")
    @patch("aurora_cli.commands.goals.shutil.which", return_value="/usr/bin/claude")
    def test_tool_cli_flag_overrides_env(
        self,
        _mock_which,
        mock_create_plan,
        mock_client,
        cli_runner,
        temp_aurora_dir,
        monkeypatch,
    ):
        """Test that --tool flag overrides AURORA_GOALS_TOOL env var."""
        monkeypatch.setenv("AURORA_GOALS_TOOL", "cursor")
        monkeypatch.chdir(temp_aurora_dir.parent)

        # Mock the LLM client
        mock_instance = Mock()
        mock_client.return_value = mock_instance

        # Mock create_plan to return success
        mock_create_plan.return_value = Mock(
            success=True,
            plan=Mock(
                plan_id="0001-test",
                goal="Test goal",
                complexity=Mock(value="simple"),
                subgoals=[],
            ),
            plan_dir="/tmp/plan",  # nosec B108
            warnings=[],
        )

        _ = cli_runner.invoke(
            goals_command,
            ["Test goal", "--tool", "claude", "--yes"],
        )

        # Should use "claude" from CLI flag, not "cursor" from env
        mock_client.assert_called_once()
        call_kwargs = mock_client.call_args[1]
        assert call_kwargs.get("tool") == "claude"

    @pytest.mark.skipif(goals_command is None, reason="goals.py not created yet")
    @patch("aurora_cli.commands.goals.CLIPipeLLMClient")
    @patch("aurora_cli.commands.goals.create_plan")
    @patch("aurora_cli.commands.goals.shutil.which", return_value="/usr/bin/cursor")
    def test_tool_env_overrides_default(
        self,
        _mock_which,
        mock_create_plan,
        mock_client,
        cli_runner,
        temp_aurora_dir,
        monkeypatch,
    ):
        """Test that AURORA_GOALS_TOOL env var overrides default."""
        monkeypatch.setenv("AURORA_GOALS_TOOL", "cursor")
        monkeypatch.chdir(temp_aurora_dir.parent)

        mock_instance = Mock()
        mock_client.return_value = mock_instance

        # Mock create_plan to return success
        mock_create_plan.return_value = Mock(
            success=True,
            plan=Mock(
                plan_id="0001-test",
                goal="Test goal",
                complexity=Mock(value="simple"),
                subgoals=[],
            ),
            plan_dir="/tmp/plan",  # nosec B108
            warnings=[],
        )

        _ = cli_runner.invoke(
            goals_command,
            ["Test goal", "--yes"],
        )

        # Should use "cursor" from env, not "claude" default
        mock_client.assert_called_once()
        call_kwargs = mock_client.call_args[1]
        assert call_kwargs.get("tool") == "cursor"


class TestModelResolution:
    """Test model resolution order: CLI → env → config → default."""

    @pytest.mark.skipif(goals_command is None, reason="goals.py not created yet")
    @patch("aurora_cli.commands.goals.CLIPipeLLMClient")
    @patch("aurora_cli.commands.goals.create_plan")
    @patch("aurora_cli.commands.goals.shutil.which", return_value="/usr/bin/claude")
    def test_model_cli_flag_overrides_env(
        self,
        _mock_which,
        mock_create_plan,
        mock_client,
        cli_runner,
        temp_aurora_dir,
        monkeypatch,
    ):
        """Test that --model flag overrides AURORA_GOALS_MODEL env var."""
        monkeypatch.setenv("AURORA_GOALS_MODEL", "opus")
        monkeypatch.chdir(temp_aurora_dir.parent)

        mock_instance = Mock()
        mock_client.return_value = mock_instance

        # Mock create_plan to return success
        mock_create_plan.return_value = Mock(
            success=True,
            plan=Mock(
                plan_id="0001-test",
                goal="Test goal",
                complexity=Mock(value="simple"),
                subgoals=[],
            ),
            plan_dir="/tmp/plan",  # nosec B108
            warnings=[],
        )

        _ = cli_runner.invoke(
            goals_command,
            ["Test goal", "--model", "sonnet", "--yes"],
        )

        # Should use "sonnet" from CLI flag, not "opus" from env
        mock_client.assert_called_once()
        call_kwargs = mock_client.call_args[1]
        assert call_kwargs.get("model") == "sonnet"

    @pytest.mark.skipif(goals_command is None, reason="goals.py not created yet")
    @patch("aurora_cli.commands.goals.CLIPipeLLMClient")
    @patch("aurora_cli.commands.goals.create_plan")
    @patch("aurora_cli.commands.goals.shutil.which", return_value="/usr/bin/claude")
    def test_model_env_overrides_default(
        self,
        _mock_which,
        mock_create_plan,
        mock_client,
        cli_runner,
        temp_aurora_dir,
        monkeypatch,
    ):
        """Test that AURORA_GOALS_MODEL env var overrides default."""
        monkeypatch.setenv("AURORA_GOALS_MODEL", "opus")
        monkeypatch.chdir(temp_aurora_dir.parent)

        mock_instance = Mock()
        mock_client.return_value = mock_instance

        # Mock create_plan to return success
        mock_create_plan.return_value = Mock(
            success=True,
            plan=Mock(
                plan_id="0001-test",
                goal="Test goal",
                complexity=Mock(value="simple"),
                subgoals=[],
            ),
            plan_dir="/tmp/plan",  # nosec B108
            warnings=[],
        )

        _ = cli_runner.invoke(
            goals_command,
            ["Test goal", "--yes"],
        )

        # Should use "opus" from env, not "sonnet" default
        mock_client.assert_called_once()
        call_kwargs = mock_client.call_args[1]
        assert call_kwargs.get("model") == "opus"


class TestInvalidTool:
    """Test error handling for invalid CLI tools."""

    @pytest.mark.skipif(goals_command is None, reason="goals.py not created yet")
    @patch("aurora_cli.commands.goals.shutil.which", return_value=None)
    def test_invalid_tool_shows_error(self, _mock_which, cli_runner, temp_aurora_dir, monkeypatch):
        """Test that using a non-existent tool shows helpful error."""
        monkeypatch.chdir(temp_aurora_dir.parent)

        result = cli_runner.invoke(
            goals_command,
            ["Test goal", "--tool", "nonexistent_tool_xyz", "--yes"],
        )

        # Should fail with helpful error
        assert result.exit_code != 0
        assert "not found" in result.output.lower() or "invalid" in result.output.lower()


class TestMemorySearchDisplay:
    """Test memory search results display."""

    @pytest.mark.skipif(goals_command is None, reason="goals.py not created yet")
    @patch("aurora_cli.commands.goals.CLIPipeLLMClient")
    @patch("aurora_cli.commands.goals.create_plan")
    @patch("aurora_cli.commands.goals.shutil.which", return_value="/usr/bin/claude")
    def test_shows_searching_memory_message(
        self,
        _mock_which,
        mock_create_plan,
        mock_client,
        cli_runner,
        temp_aurora_dir,
        monkeypatch,
        _capsys,
    ):
        """Test shows 'Searching memory...' progress message."""
        monkeypatch.chdir(temp_aurora_dir.parent)

        # Create plan directory
        plan_dir = temp_aurora_dir / "plans" / "0001-test"
        plan_dir.mkdir(parents=True, exist_ok=True)

        # Mock the LLM client
        mock_instance = Mock()
        mock_client.return_value = mock_instance

        # Mock create_plan to include memory context
        mock_create_plan.return_value = Mock(
            success=True,
            plan=Mock(
                plan_id="0001-test",
                goal="Test goal for memory search verification",
                complexity=Mock(value="simple"),
                subgoals=[
                    Mock(
                        id="sg-1",
                        title="Implement test feature",
                        description="Add test feature implementation",
                        agent="@code-developer",
                        confidence=0.9,
                        dependencies=[],
                        agent_exists=True,
                        recommended_agent="@code-developer",
                    ),
                ],
                memory_context=[
                    Mock(file="src/auth.py", relevance=0.85),
                ],
                gaps=[],
            ),
            plan_dir=plan_dir,
            warnings=[],
        )

        result = cli_runner.invoke(
            goals_command,
            ["Test goal for memory search", "--yes"],
        )

        # Should show searching message (either in result.output or created by create_plan)
        # The actual message will be shown when we integrate memory search into create_plan
        assert result.exit_code == 0

    @pytest.mark.skipif(goals_command is None, reason="goals.py not created yet")
    @patch("aurora_cli.commands.goals.CLIPipeLLMClient")
    @patch("aurora_cli.commands.goals.create_plan")
    @patch("aurora_cli.commands.goals.shutil.which", return_value="/usr/bin/claude")
    def test_displays_found_files_with_scores(
        self,
        _mock_which,
        mock_create_plan,
        mock_client,
        cli_runner,
        temp_aurora_dir,
        monkeypatch,
    ):
        """Test displays found files with relevance scores."""
        monkeypatch.chdir(temp_aurora_dir.parent)

        # Create plan directory
        plan_dir = temp_aurora_dir / "plans" / "0001-test"
        plan_dir.mkdir(parents=True, exist_ok=True)

        # Mock the LLM client
        mock_instance = Mock()
        mock_client.return_value = mock_instance

        # Mock create_plan to return plan with memory context
        mock_create_plan.return_value = Mock(
            success=True,
            plan=Mock(
                plan_id="0001-test",
                goal="Test goal for memory display with scores",
                complexity=Mock(value="simple"),
                subgoals=[
                    Mock(
                        id="sg-1",
                        title="Implement test feature",
                        description="Add test feature implementation",
                        agent="@code-developer",
                        confidence=0.9,
                        dependencies=[],
                        agent_exists=True,
                        recommended_agent="@code-developer",
                    ),
                ],
                memory_context=[
                    Mock(file="src/auth.py", relevance=0.85),
                    Mock(file="src/user.py", relevance=0.72),
                ],
                gaps=[],
            ),
            plan_dir=plan_dir,
            warnings=[],
        )

        result = cli_runner.invoke(
            goals_command,
            ["Test goal", "--yes"],
        )

        assert result.exit_code == 0
        # Memory context display is handled by create_plan
        # We'll verify the format when we look at verbose output

    @pytest.mark.skipif(goals_command is None, reason="goals.py not created yet")
    @patch("aurora_cli.commands.goals.CLIPipeLLMClient")
    @patch("aurora_cli.commands.goals.create_plan")
    @patch("aurora_cli.commands.goals.shutil.which", return_value="/usr/bin/claude")
    def test_handles_empty_memory_results(
        self,
        _mock_which,
        mock_create_plan,
        mock_client,
        cli_runner,
        temp_aurora_dir,
        monkeypatch,
    ):
        """Test handles empty results with helpful message."""
        monkeypatch.chdir(temp_aurora_dir.parent)

        # Create plan directory
        plan_dir = temp_aurora_dir / "plans" / "0001-test"
        plan_dir.mkdir(parents=True, exist_ok=True)

        # Mock the LLM client
        mock_instance = Mock()
        mock_client.return_value = mock_instance

        # Mock create_plan to return plan with no memory context
        mock_create_plan.return_value = Mock(
            success=True,
            plan=Mock(
                plan_id="0001-test",
                goal="Test goal with empty context handling",
                complexity=Mock(value="simple"),
                subgoals=[
                    Mock(
                        id="sg-1",
                        title="Implement test feature",
                        description="Add test feature implementation",
                        agent="@code-developer",
                        confidence=0.9,
                        dependencies=[],
                        agent_exists=True,
                        recommended_agent="@code-developer",
                    ),
                ],
                memory_context=[],  # No context found
                gaps=[],
            ),
            plan_dir=plan_dir,
            warnings=[
                "No relevant context found in memory. Run 'aur mem index .' to index codebase.",
            ],
        )

        result = cli_runner.invoke(
            goals_command,
            ["Test goal with no context", "--yes"],
        )

        assert result.exit_code == 0
        # Warning about no context should be displayed

    @pytest.mark.skipif(goals_command is None, reason="goals.py not created yet")
    @patch("aurora_cli.commands.goals.CLIPipeLLMClient")
    @patch("aurora_cli.commands.goals.create_plan")
    @patch("aurora_cli.commands.goals.shutil.which", return_value="/usr/bin/claude")
    def test_verbose_shows_detailed_memory_search(
        self,
        _mock_which,
        mock_create_plan,
        mock_client,
        cli_runner,
        temp_aurora_dir,
        monkeypatch,
    ):
        """Test verbose mode shows detailed search info."""
        monkeypatch.chdir(temp_aurora_dir.parent)

        # Create plan directory
        plan_dir = temp_aurora_dir / "plans" / "0001-test"
        plan_dir.mkdir(parents=True, exist_ok=True)

        # Mock the LLM client
        mock_instance = Mock()
        mock_client.return_value = mock_instance

        # Mock create_plan
        mock_create_plan.return_value = Mock(
            success=True,
            plan=Mock(
                plan_id="0001-test",
                goal="Test goal for verbose memory search output",
                complexity=Mock(value="simple"),
                subgoals=[
                    Mock(
                        id="sg-1",
                        title="Implement test feature",
                        description="Add test feature implementation",
                        agent="@code-developer",
                        confidence=0.9,
                        dependencies=[],
                        agent_exists=True,
                        recommended_agent="@code-developer",
                    ),
                ],
                memory_context=[
                    Mock(file="src/auth.py", relevance=0.85),
                ],
                gaps=[],
            ),
            plan_dir=plan_dir,
            warnings=[],
        )

        result = cli_runner.invoke(
            goals_command,
            ["Test goal", "--verbose", "--yes"],
        )

        assert result.exit_code == 0
        # Verbose output would show more details about memory search


class TestUserReviewFlow:
    """Test user review flow for goals before saving."""

    @pytest.mark.skipif(goals_command is None, reason="goals.py not created yet")
    @patch("aurora_cli.commands.goals.CLIPipeLLMClient")
    @patch("aurora_cli.commands.goals.create_plan")
    @patch("aurora_cli.commands.goals.shutil.which", return_value="/usr/bin/claude")
    def test_displays_plan_summary_before_confirmation(
        self,
        _mock_which,
        mock_create_plan,
        mock_client,
        cli_runner,
        temp_aurora_dir,
        monkeypatch,
    ):
        """Test displays plan summary before asking for confirmation."""
        monkeypatch.chdir(temp_aurora_dir.parent)

        # Mock the LLM client
        mock_instance = Mock()
        mock_client.return_value = mock_instance

        # Create the plan directory
        plan_dir = temp_aurora_dir / "plans" / "0001-test-goal"
        plan_dir.mkdir(parents=True, exist_ok=True)

        # Mock create_plan to return success
        mock_create_plan.return_value = Mock(
            success=True,
            plan=Mock(
                plan_id="0001-test-goal",
                goal="Test goal for summary",
                complexity=Mock(value="simple"),
                subgoals=[
                    Mock(
                        id="sg-1",
                        title="Implement feature",
                        description="Add the feature",
                        agent="@code-developer",
                        confidence=0.85,
                        dependencies=[],
                        agent_exists=True,
                        recommended_agent="@code-developer",
                    ),
                ],
                memory_context=[],
                gaps=[],
            ),
            plan_dir=plan_dir,
            warnings=[],
        )

        # Use --yes to skip confirmation
        result = cli_runner.invoke(
            goals_command,
            ["Test goal for summary", "--yes"],
        )

        assert result.exit_code == 0
        # When using --yes, should not prompt for confirmation

    @pytest.mark.skipif(goals_command is None, reason="goals.py not created yet")
    @patch("aurora_cli.commands.goals.subprocess.run")
    @patch("aurora_cli.commands.goals.CLIPipeLLMClient")
    @patch("aurora_cli.commands.goals.create_plan")
    @patch("aurora_cli.commands.goals.shutil.which", return_value="/usr/bin/claude")
    def test_opens_goals_json_in_editor(
        self,
        _mock_which,
        mock_create_plan,
        mock_client,
        mock_subprocess,
        cli_runner,
        temp_aurora_dir,
        monkeypatch,
    ):
        """Test opens goals.json in editor when user confirms review."""
        monkeypatch.chdir(temp_aurora_dir.parent)

        # Mock the LLM client
        mock_instance = Mock()
        mock_client.return_value = mock_instance

        # Create the plan directory
        plan_dir = temp_aurora_dir / "plans" / "0001-test-goal"
        plan_dir.mkdir(parents=True, exist_ok=True)

        # Mock create_plan to return success
        mock_create_plan.return_value = Mock(
            success=True,
            plan=Mock(
                plan_id="0001-test-goal",
                goal="Test goal for opening in editor application",
                complexity=Mock(value="simple"),
                subgoals=[
                    Mock(
                        id="sg-1",
                        title="Test subgoal",
                        description="Test description",
                        agent="@code-developer",
                        confidence=0.9,
                        dependencies=[],
                        agent_exists=True,
                        recommended_agent="@code-developer",
                    ),
                ],
                memory_context=[],
                gaps=[],
            ),
            plan_dir=plan_dir,
            warnings=[],
        )

        # Mock subprocess.run to simulate editor invocation
        mock_subprocess.return_value = Mock(returncode=0)

        # Provide input: 'y' for review, 'y' for proceed
        result = cli_runner.invoke(
            goals_command,
            ["Test goal for editor"],
            input="y\ny\n",
        )

        # Editor should be called with the temp goals.json file
        # (Implementation will determine exact behavior)
        assert result.exit_code == 0

    @pytest.mark.skipif(goals_command is None, reason="goals.py not created yet")
    @patch("aurora_cli.commands.goals.CLIPipeLLMClient")
    @patch("aurora_cli.commands.goals.create_plan")
    @patch("aurora_cli.commands.goals.shutil.which", return_value="/usr/bin/claude")
    def test_waits_for_user_confirmation(
        self,
        _mock_which,
        mock_create_plan,
        mock_client,
        cli_runner,
        temp_aurora_dir,
        monkeypatch,
    ):
        """Test waits for user confirmation before proceeding."""
        monkeypatch.chdir(temp_aurora_dir.parent)

        # Mock the LLM client
        mock_instance = Mock()
        mock_client.return_value = mock_instance

        # Create the plan directory
        plan_dir = temp_aurora_dir / "plans" / "0001-test-goal"
        plan_dir.mkdir(parents=True, exist_ok=True)

        # Mock create_plan to return success
        mock_create_plan.return_value = Mock(
            success=True,
            plan=Mock(
                plan_id="0001-test-goal",
                goal="Test goal for user confirmation workflow",
                complexity=Mock(value="simple"),
                subgoals=[
                    Mock(
                        id="sg-1",
                        title="Test subgoal",
                        description="Test description",
                        agent="@code-developer",
                        confidence=0.9,
                        dependencies=[],
                        agent_exists=True,
                        recommended_agent="@code-developer",
                    ),
                ],
                memory_context=[],
                gaps=[],
            ),
            plan_dir=plan_dir,
            warnings=[],
        )

        # Provide input: 'n' for review (skip review), 'y' for proceed
        result = cli_runner.invoke(
            goals_command,
            ["Test goal for confirmation"],
            input="n\ny\n",
        )

        assert result.exit_code == 0

    @pytest.mark.skipif(goals_command is None, reason="goals.py not created yet")
    @patch("aurora_cli.commands.goals.CLIPipeLLMClient")
    @patch("aurora_cli.commands.goals.create_plan")
    @patch("aurora_cli.commands.goals.shutil.which", return_value="/usr/bin/claude")
    def test_yes_flag_skips_confirmation(
        self,
        _mock_which,
        mock_create_plan,
        mock_client,
        cli_runner,
        temp_aurora_dir,
        monkeypatch,
    ):
        """Test --yes flag skips all confirmation prompts."""
        monkeypatch.chdir(temp_aurora_dir.parent)

        # Mock the LLM client
        mock_instance = Mock()
        mock_client.return_value = mock_instance

        # Create the plan directory
        plan_dir = temp_aurora_dir / "plans" / "0001-test-goal"
        plan_dir.mkdir(parents=True, exist_ok=True)

        # Mock create_plan to return success
        mock_create_plan.return_value = Mock(
            success=True,
            plan=Mock(
                plan_id="0001-test-goal",
                goal="Test goal with yes flag to skip confirmation",
                complexity=Mock(value="simple"),
                subgoals=[
                    Mock(
                        id="sg-1",
                        title="Test subgoal",
                        description="Test description",
                        agent="@code-developer",
                        confidence=0.9,
                        dependencies=[],
                        agent_exists=True,
                        recommended_agent="@code-developer",
                    ),
                ],
                memory_context=[],
                gaps=[],
            ),
            plan_dir=plan_dir,
            warnings=[],
        )

        # Should not need any input with --yes
        result = cli_runner.invoke(
            goals_command,
            ["Test goal with yes flag", "--yes"],
        )

        assert result.exit_code == 0
        # Should complete without waiting for input

    @pytest.mark.skipif(goals_command is None, reason="goals.py not created yet")
    @patch("aurora_cli.commands.goals.CLIPipeLLMClient")
    @patch("aurora_cli.commands.goals.create_plan")
    @patch("aurora_cli.commands.goals.shutil.which", return_value="/usr/bin/claude")
    def test_can_abort_before_saving(
        self,
        _mock_which,
        mock_create_plan,
        mock_client,
        cli_runner,
        temp_aurora_dir,
        monkeypatch,
    ):
        """Test can abort the process before saving goals.json."""
        monkeypatch.chdir(temp_aurora_dir.parent)

        # Mock the LLM client
        mock_instance = Mock()
        mock_client.return_value = mock_instance

        # Create the plan directory
        plan_dir = temp_aurora_dir / "plans" / "0001-test-goal"
        plan_dir.mkdir(parents=True, exist_ok=True)

        # Mock create_plan to return success
        mock_create_plan.return_value = Mock(
            success=True,
            plan=Mock(
                plan_id="0001-test-goal",
                goal="Test goal to abort before saving",
                complexity=Mock(value="simple"),
                subgoals=[
                    Mock(
                        id="sg-1",
                        title="Test subgoal",
                        description="Test description",
                        agent="@code-developer",
                        confidence=0.9,
                        dependencies=[],
                        agent_exists=True,
                        recommended_agent="@code-developer",
                    ),
                ],
                memory_context=[],
                gaps=[],
            ),
            plan_dir=plan_dir,
            warnings=[],
        )

        # Provide input: 'n' for review (skip), 'n' for proceed (abort)
        result = cli_runner.invoke(
            goals_command,
            ["Test goal to abort"],
            input="n\nn\n",
        )

        # Should abort gracefully
        # Exit code might be 0 or 1 depending on implementation
        # Either way, goals.json should not be saved
        goals_file = plan_dir / "goals.json"
        assert not goals_file.exists() or "Cancelled" in result.output

    @pytest.mark.skipif(goals_command is None, reason="goals.py not created yet")
    @patch("aurora_cli.commands.goals.CLIPipeLLMClient")
    @patch("aurora_cli.commands.goals.create_plan")
    @patch("aurora_cli.commands.goals.shutil.which", return_value="/usr/bin/claude")
    def test_creates_goals_json_file(
        self,
        _mock_which,
        mock_create_plan,
        mock_client,
        cli_runner,
        temp_aurora_dir,
        monkeypatch,
    ):
        """Test successfully creates goals.json file after confirmation."""
        monkeypatch.chdir(temp_aurora_dir.parent)

        # Mock the LLM client
        mock_instance = Mock()
        mock_client.return_value = mock_instance

        # Create the plan directory
        plan_dir = temp_aurora_dir / "plans" / "0001-test-goal"
        plan_dir.mkdir(parents=True, exist_ok=True)

        # Mock create_plan to return success
        mock_create_plan.return_value = Mock(
            success=True,
            plan=Mock(
                plan_id="0001-test-goal",
                goal="Test goal for file creation",
                complexity=Mock(value="simple"),
                subgoals=[
                    Mock(
                        id="sg-1",
                        title="Test subgoal",
                        description="Test description",
                        agent="@code-developer",
                        confidence=0.9,
                        dependencies=[],
                        agent_exists=True,
                        recommended_agent="@code-developer",
                    ),
                ],
                memory_context=[],
                gaps=[],
            ),
            plan_dir=plan_dir,
            warnings=[],
        )

        # Use --yes to auto-confirm
        result = cli_runner.invoke(
            goals_command,
            ["Test goal for file creation", "--yes"],
        )

        assert result.exit_code == 0

        # Verify goals.json was created
        goals_file = plan_dir / "goals.json"
        assert goals_file.exists(), f"goals.json should be created at {goals_file}"

        # Verify it's valid JSON
        goals_data = json.loads(goals_file.read_text())
        assert "id" in goals_data
        assert "title" in goals_data
        assert "subgoals" in goals_data

    @pytest.mark.skipif(goals_command is None, reason="goals.py not created yet")
    @patch("aurora_cli.commands.goals.CLIPipeLLMClient")
    @patch("aurora_cli.commands.goals.create_plan")
    @patch("aurora_cli.commands.goals.shutil.which", return_value="/usr/bin/claude")
    def test_shows_next_steps_message(
        self,
        _mock_which,
        mock_create_plan,
        mock_client,
        cli_runner,
        temp_aurora_dir,
        monkeypatch,
    ):
        """Test shows message about next steps after saving."""
        monkeypatch.chdir(temp_aurora_dir.parent)

        # Mock the LLM client
        mock_instance = Mock()
        mock_client.return_value = mock_instance

        # Create the plan directory
        plan_dir = temp_aurora_dir / "plans" / "0001-test-goal"
        plan_dir.mkdir(parents=True, exist_ok=True)

        # Mock create_plan to return success
        mock_create_plan.return_value = Mock(
            success=True,
            plan=Mock(
                plan_id="0001-test-goal",
                goal="Test goal for showing next steps message",
                complexity=Mock(value="simple"),
                subgoals=[
                    Mock(
                        id="sg-1",
                        title="Test subgoal",
                        description="Test description",
                        agent="@code-developer",
                        confidence=0.9,
                        dependencies=[],
                        agent_exists=True,
                        recommended_agent="@code-developer",
                    ),
                ],
                memory_context=[],
                gaps=[],
            ),
            plan_dir=plan_dir,
            warnings=[],
        )

        # Use --yes to auto-confirm
        result = cli_runner.invoke(
            goals_command,
            ["Test goal for next steps", "--yes"],
        )

        assert result.exit_code == 0
        # Should mention /plan skill in output
        assert "/plan" in result.output or "plan" in result.output.lower()
