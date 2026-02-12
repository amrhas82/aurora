"""Tests for aur goals command.

Tests goal creation, tool/model resolution, error handling, and user review flow.
"""

from __future__ import annotations

import json
from unittest.mock import Mock, patch

import pytest
from click.testing import CliRunner

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

    manifest = {
        "version": "1.0",
        "plans_directory": str(plans_dir),
    }
    (plans_dir / "manifest.json").write_text(json.dumps(manifest, indent=2))

    return aurora_dir


def _mock_plan_result(temp_aurora_dir, plan_id="0001-test", goal="Test goal", subgoals=None):
    """Helper to create a mock create_plan result with plan directory."""
    plan_dir = temp_aurora_dir / "plans" / plan_id
    plan_dir.mkdir(parents=True, exist_ok=True)

    if subgoals is None:
        subgoals = [
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
        ]

    return Mock(
        success=True,
        plan=Mock(
            plan_id=plan_id,
            goal=goal,
            complexity=Mock(value="simple"),
            subgoals=subgoals,
            memory_context=[],
            gaps=[],
        ),
        plan_dir=plan_dir,
        warnings=[],
    )


class TestToolResolution:
    """Test tool resolution order: CLI flag > env var > default."""

    @pytest.mark.skipif(goals_command is None, reason="goals.py not created yet")
    @patch("aurora_cli.commands.goals.CLIPipeLLMClient")
    @patch("aurora_cli.commands.goals.create_plan")
    @patch("aurora_cli.commands.goals.shutil.which", return_value="/usr/bin/claude")
    def test_tool_cli_flag_overrides_env(
        self, _mock_which, mock_create_plan, mock_client,
        cli_runner, temp_aurora_dir, monkeypatch,
    ):
        """Test that --tool flag overrides AURORA_GOALS_TOOL env var."""
        monkeypatch.setenv("AURORA_GOALS_TOOL", "cursor")
        monkeypatch.chdir(temp_aurora_dir.parent)

        mock_client.return_value = Mock()
        mock_create_plan.return_value = _mock_plan_result(temp_aurora_dir)

        cli_runner.invoke(goals_command, ["Test goal", "--tool", "claude", "--yes"])

        mock_client.assert_called_once()
        assert mock_client.call_args[1].get("tool") == "claude"

    @pytest.mark.skipif(goals_command is None, reason="goals.py not created yet")
    @patch("aurora_cli.commands.goals.CLIPipeLLMClient")
    @patch("aurora_cli.commands.goals.create_plan")
    @patch("aurora_cli.commands.goals.shutil.which", return_value="/usr/bin/cursor")
    def test_tool_env_overrides_default(
        self, _mock_which, mock_create_plan, mock_client,
        cli_runner, temp_aurora_dir, monkeypatch,
    ):
        """Test that AURORA_GOALS_TOOL env var overrides default."""
        monkeypatch.setenv("AURORA_GOALS_TOOL", "cursor")
        monkeypatch.chdir(temp_aurora_dir.parent)

        mock_client.return_value = Mock()
        mock_create_plan.return_value = _mock_plan_result(temp_aurora_dir)

        cli_runner.invoke(goals_command, ["Test goal", "--yes"])

        mock_client.assert_called_once()
        assert mock_client.call_args[1].get("tool") == "cursor"


class TestModelResolution:
    """Test model resolution order: CLI flag > env var > default."""

    @pytest.mark.skipif(goals_command is None, reason="goals.py not created yet")
    @patch("aurora_cli.commands.goals.CLIPipeLLMClient")
    @patch("aurora_cli.commands.goals.create_plan")
    @patch("aurora_cli.commands.goals.shutil.which", return_value="/usr/bin/claude")
    def test_model_cli_flag_overrides_env(
        self, _mock_which, mock_create_plan, mock_client,
        cli_runner, temp_aurora_dir, monkeypatch,
    ):
        """Test that --model flag overrides AURORA_GOALS_MODEL env var."""
        monkeypatch.setenv("AURORA_GOALS_MODEL", "opus")
        monkeypatch.chdir(temp_aurora_dir.parent)

        mock_client.return_value = Mock()
        mock_create_plan.return_value = _mock_plan_result(temp_aurora_dir)

        cli_runner.invoke(goals_command, ["Test goal", "--model", "sonnet", "--yes"])

        mock_client.assert_called_once()
        assert mock_client.call_args[1].get("model") == "sonnet"

    @pytest.mark.skipif(goals_command is None, reason="goals.py not created yet")
    @patch("aurora_cli.commands.goals.CLIPipeLLMClient")
    @patch("aurora_cli.commands.goals.create_plan")
    @patch("aurora_cli.commands.goals.shutil.which", return_value="/usr/bin/claude")
    def test_model_env_overrides_default(
        self, _mock_which, mock_create_plan, mock_client,
        cli_runner, temp_aurora_dir, monkeypatch,
    ):
        """Test that AURORA_GOALS_MODEL env var overrides default."""
        monkeypatch.setenv("AURORA_GOALS_MODEL", "opus")
        monkeypatch.chdir(temp_aurora_dir.parent)

        mock_client.return_value = Mock()
        mock_create_plan.return_value = _mock_plan_result(temp_aurora_dir)

        cli_runner.invoke(goals_command, ["Test goal", "--yes"])

        mock_client.assert_called_once()
        assert mock_client.call_args[1].get("model") == "opus"


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

        assert result.exit_code != 0
        assert "not found" in result.output.lower() or "invalid" in result.output.lower()


class TestEmptyMemoryResults:
    """Test handling of empty memory search results."""

    @pytest.mark.skipif(goals_command is None, reason="goals.py not created yet")
    @patch("aurora_cli.commands.goals.CLIPipeLLMClient")
    @patch("aurora_cli.commands.goals.create_plan")
    @patch("aurora_cli.commands.goals.shutil.which", return_value="/usr/bin/claude")
    def test_handles_empty_memory_results(
        self, _mock_which, mock_create_plan, mock_client,
        cli_runner, temp_aurora_dir, monkeypatch,
    ):
        """Test handles empty results gracefully."""
        monkeypatch.chdir(temp_aurora_dir.parent)

        mock_client.return_value = Mock()
        result_mock = _mock_plan_result(temp_aurora_dir)
        result_mock.warnings = [
            "No relevant context found in memory. Run 'aur mem index .' to index codebase.",
        ]
        mock_create_plan.return_value = result_mock

        result = cli_runner.invoke(
            goals_command,
            ["Test goal with no context", "--yes"],
        )

        assert result.exit_code == 0


class TestUserReviewFlow:
    """Test user review flow for goals before saving."""

    @pytest.mark.skipif(goals_command is None, reason="goals.py not created yet")
    @patch("aurora_cli.commands.goals.subprocess.run")
    @patch("aurora_cli.commands.goals.CLIPipeLLMClient")
    @patch("aurora_cli.commands.goals.create_plan")
    @patch("aurora_cli.commands.goals.shutil.which", return_value="/usr/bin/claude")
    def test_opens_goals_json_in_editor(
        self, _mock_which, mock_create_plan, mock_client, mock_subprocess,
        cli_runner, temp_aurora_dir, monkeypatch,
    ):
        """Test opens goals.json in editor when user confirms review."""
        monkeypatch.chdir(temp_aurora_dir.parent)

        mock_client.return_value = Mock()
        mock_create_plan.return_value = _mock_plan_result(temp_aurora_dir, plan_id="0001-test-goal")
        mock_subprocess.return_value = Mock(returncode=0)

        result = cli_runner.invoke(
            goals_command,
            ["Test goal for editor"],
            input="y\ny\n",
        )

        assert result.exit_code == 0

    @pytest.mark.skipif(goals_command is None, reason="goals.py not created yet")
    @patch("aurora_cli.commands.goals.CLIPipeLLMClient")
    @patch("aurora_cli.commands.goals.create_plan")
    @patch("aurora_cli.commands.goals.shutil.which", return_value="/usr/bin/claude")
    def test_waits_for_user_confirmation(
        self, _mock_which, mock_create_plan, mock_client,
        cli_runner, temp_aurora_dir, monkeypatch,
    ):
        """Test waits for user confirmation before proceeding."""
        monkeypatch.chdir(temp_aurora_dir.parent)

        mock_client.return_value = Mock()
        mock_create_plan.return_value = _mock_plan_result(temp_aurora_dir, plan_id="0001-test-goal")

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
        self, _mock_which, mock_create_plan, mock_client,
        cli_runner, temp_aurora_dir, monkeypatch,
    ):
        """Test --yes flag skips all confirmation prompts."""
        monkeypatch.chdir(temp_aurora_dir.parent)

        mock_client.return_value = Mock()
        mock_create_plan.return_value = _mock_plan_result(temp_aurora_dir, plan_id="0001-test-goal")

        result = cli_runner.invoke(
            goals_command,
            ["Test goal with yes flag", "--yes"],
        )

        assert result.exit_code == 0

    @pytest.mark.skipif(goals_command is None, reason="goals.py not created yet")
    @patch("aurora_cli.commands.goals.CLIPipeLLMClient")
    @patch("aurora_cli.commands.goals.create_plan")
    @patch("aurora_cli.commands.goals.shutil.which", return_value="/usr/bin/claude")
    def test_can_abort_before_saving(
        self, _mock_which, mock_create_plan, mock_client,
        cli_runner, temp_aurora_dir, monkeypatch,
    ):
        """Test can abort the process before saving goals.json."""
        monkeypatch.chdir(temp_aurora_dir.parent)

        mock_client.return_value = Mock()
        plan_result = _mock_plan_result(temp_aurora_dir, plan_id="0001-test-goal")
        plan_dir = plan_result.plan_dir
        mock_create_plan.return_value = plan_result

        result = cli_runner.invoke(
            goals_command,
            ["Test goal to abort"],
            input="n\nn\n",
        )

        goals_file = plan_dir / "goals.json"
        assert not goals_file.exists() or "Cancelled" in result.output

    @pytest.mark.skipif(goals_command is None, reason="goals.py not created yet")
    @patch("aurora_cli.commands.goals.CLIPipeLLMClient")
    @patch("aurora_cli.commands.goals.create_plan")
    @patch("aurora_cli.commands.goals.shutil.which", return_value="/usr/bin/claude")
    def test_creates_goals_json_file(
        self, _mock_which, mock_create_plan, mock_client,
        cli_runner, temp_aurora_dir, monkeypatch,
    ):
        """Test successfully creates goals.json file after confirmation."""
        monkeypatch.chdir(temp_aurora_dir.parent)

        mock_client.return_value = Mock()
        plan_result = _mock_plan_result(temp_aurora_dir, plan_id="0001-test-goal")
        plan_dir = plan_result.plan_dir
        mock_create_plan.return_value = plan_result

        result = cli_runner.invoke(
            goals_command,
            ["Test goal for file creation", "--yes"],
        )

        assert result.exit_code == 0

        goals_file = plan_dir / "goals.json"
        assert goals_file.exists(), f"goals.json should be created at {goals_file}"

        goals_data = json.loads(goals_file.read_text())
        assert "id" in goals_data
        assert "title" in goals_data
        assert "subgoals" in goals_data
