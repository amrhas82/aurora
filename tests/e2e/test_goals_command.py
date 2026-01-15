"""E2E tests for aur goals command.

This module contains end-to-end tests for the full goals workflow:
- Input goal → memory search → decompose → match → review → output

Tests use temporary directories for isolation and mock LLM calls for deterministic results.
"""

from __future__ import annotations

import json
from unittest.mock import Mock, patch

import pytest
from click.testing import CliRunner

from aurora_cli.commands.goals import goals_command


@pytest.fixture
def isolated_project(tmp_path, monkeypatch):
    """Create an isolated project directory with Aurora structure and change to it."""
    project_dir = tmp_path / "test_project"
    project_dir.mkdir()

    # Create .aurora structure
    aurora_dir = project_dir / ".aurora"
    plans_dir = aurora_dir / "plans"
    plans_dir.mkdir(parents=True)

    # Create manifest
    manifest = {
        "version": "1.0",
        "plans_directory": str(plans_dir),
    }
    (plans_dir / "manifest.json").write_text(json.dumps(manifest, indent=2))

    # Change to project directory
    monkeypatch.chdir(project_dir)

    return project_dir


@pytest.fixture
def valid_subgoal():
    """Provide a valid mock subgoal."""
    return Mock(
        id="sg-1",
        title="Implement test feature",
        description="Add test feature implementation",
        agent="@full-stack-dev",
        confidence=0.9,
        dependencies=[],
        agent_exists=True,
        recommended_agent="@full-stack-dev",
    )


class TestGoalsCommandE2E:
    """End-to-end tests for aur goals command."""

    @patch("aurora_cli.commands.goals.CLIPipeLLMClient")
    @patch("aurora_cli.commands.goals.create_plan")
    @patch("aurora_cli.commands.goals.shutil.which", return_value="/usr/bin/claude")
    def test_full_flow_with_yes_flag(
        self, mock_which, mock_create_plan, mock_client, isolated_project, valid_subgoal
    ):
        """Test full workflow: goal → decompose → match → output with --yes flag."""
        # Setup plan directory
        plan_dir = isolated_project / ".aurora" / "plans" / "0001-add-oauth2"
        plan_dir.mkdir(parents=True)

        # Mock LLM client
        mock_instance = Mock()
        mock_client.return_value = mock_instance

        # Mock create_plan to simulate successful plan creation
        mock_create_plan.return_value = Mock(
            success=True,
            plan=Mock(
                plan_id="0001-add-oauth2",
                goal="Implement OAuth2 authentication with JWT tokens",
                complexity=Mock(value="moderate"),
                subgoals=[valid_subgoal],
                memory_context=[
                    Mock(file="src/auth/login.py", relevance=0.85),
                ],
                gaps=[],
            ),
            plan_dir=plan_dir,
            warnings=[],
        )

        # Execute
        runner = CliRunner()
        result = runner.invoke(
            goals_command,
            ["Implement OAuth2 authentication with JWT tokens", "--yes"],
        )

        # Assert
        assert result.exit_code == 0, f"Command failed: {result.output}"

        # Verify goals.json was created
        goals_file = plan_dir / "goals.json"
        assert goals_file.exists(), f"goals.json not found at {goals_file}"

        # Verify goals.json content
        goals_data = json.loads(goals_file.read_text())
        assert goals_data["id"] == "0001-add-oauth2"
        assert "OAuth2" in goals_data["title"]
        assert len(goals_data["subgoals"]) >= 1

        # Verify output mentions next steps
        assert "/plan" in result.output

    @patch("aurora_cli.commands.goals.CLIPipeLLMClient")
    @patch("aurora_cli.commands.goals.create_plan")
    @patch("aurora_cli.commands.goals.shutil.which", return_value="/usr/bin/claude")
    def test_directory_creation_and_file_output(
        self, mock_which, mock_create_plan, mock_client, isolated_project, valid_subgoal
    ):
        """Test that directory and goals.json file are created correctly."""
        # Setup
        plan_dir = isolated_project / ".aurora" / "plans" / "0001-test"
        plan_dir.mkdir(parents=True)

        # Mock LLM client
        mock_instance = Mock()
        mock_client.return_value = mock_instance

        # Mock create_plan
        mock_create_plan.return_value = Mock(
            success=True,
            plan=Mock(
                plan_id="0001-test",
                goal="Test goal for directory and file verification",
                complexity=Mock(value="simple"),
                subgoals=[valid_subgoal],
                memory_context=[],
                gaps=[],
            ),
            plan_dir=plan_dir,
            warnings=[],
        )

        # Execute
        runner = CliRunner()
        result = runner.invoke(
            goals_command,
            ["Test goal for directory and file verification", "--yes"],
        )

        # Assert
        assert result.exit_code == 0

        # Verify directory exists
        assert plan_dir.exists()
        assert plan_dir.is_dir()

        # Verify goals.json exists and is valid
        goals_file = plan_dir / "goals.json"
        assert goals_file.exists()

        goals_data = json.loads(goals_file.read_text())
        assert "id" in goals_data
        assert "title" in goals_data
        assert "subgoals" in goals_data
        assert "memory_context" in goals_data

    @patch("aurora_cli.commands.goals.shutil.which", return_value=None)
    def test_invalid_tool_error(self, mock_which, isolated_project):
        """Test error handling when CLI tool not found."""
        runner = CliRunner()
        result = runner.invoke(
            goals_command,
            ["Test goal", "--tool", "nonexistent_tool", "--yes"],
        )

        # Should fail with helpful error
        assert result.exit_code != 0
        assert "not found" in result.output.lower()

    @patch("aurora_cli.commands.goals.CLIPipeLLMClient")
    @patch("aurora_cli.commands.goals.create_plan")
    @patch("aurora_cli.commands.goals.shutil.which", return_value="/usr/bin/claude")
    def test_error_during_plan_creation(
        self, mock_which, mock_create_plan, mock_client, isolated_project
    ):
        """Test error handling when plan creation fails."""
        # Mock LLM client
        mock_instance = Mock()
        mock_client.return_value = mock_instance

        # Mock create_plan to return failure
        mock_create_plan.return_value = Mock(
            success=False,
            error="Failed to decompose goal: LLM error",
            plan=None,
            plan_dir=None,
            warnings=[],
        )

        # Execute
        runner = CliRunner()
        result = runner.invoke(
            goals_command,
            ["Test goal that will fail", "--yes"],
        )

        # Should fail gracefully
        assert result.exit_code != 0
        assert "Failed to decompose" in result.output or "error" in result.output.lower()
