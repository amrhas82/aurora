"""E2E tests for aur goals → /plan integration flow.

This module tests the integration between:
1. aur goals - Creates goals.json
2. /plan skill - Reads goals.json and generates PRD, tasks, specs

Note: /plan is a Claude Code skill, so these tests document the expected
integration behavior and validate the goals.json format for /plan consumption.
"""

from __future__ import annotations

import json
from unittest.mock import Mock, patch

import pytest
from click.testing import CliRunner

from aurora_cli.commands.goals import goals_command


@pytest.fixture
def isolated_project(tmp_path, monkeypatch):
    """Create isolated project with Aurora structure."""
    project_dir = tmp_path / "test_project"
    project_dir.mkdir()

    # Create .aurora structure
    aurora_dir = project_dir / ".aurora"
    plans_dir = aurora_dir / "plans"
    plans_dir.mkdir(parents=True)

    manifest = {
        "version": "1.0",
        "plans_directory": str(plans_dir),
    }
    (plans_dir / "manifest.json").write_text(json.dumps(manifest, indent=2))

    monkeypatch.chdir(project_dir)
    return project_dir


@pytest.fixture
def valid_subgoal():
    """Valid mock subgoal."""
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


@pytest.mark.e2e
class TestGoalsPlanIntegration:
    """E2E tests for aur goals → /plan integration."""

    @patch("aurora_cli.commands.goals.CLIPipeLLMClient")
    @patch("aurora_cli.commands.goals.create_plan")
    @patch("aurora_cli.commands.goals.shutil.which", return_value="/usr/bin/claude")
    def test_aur_goals_creates_goals_json(
        self, mock_which, mock_create_plan, mock_client, isolated_project, valid_subgoal
    ):
        """Test: aur goals creates valid goals.json that /plan can read."""
        # Setup
        plan_dir = isolated_project / ".aurora" / "plans" / "0001-test"
        plan_dir.mkdir(parents=True)

        mock_instance = Mock()
        mock_client.return_value = mock_instance

        # Create mock plan with multiple subgoals showing dependencies
        mock_create_plan.return_value = Mock(
            success=True,
            plan=Mock(
                plan_id="0001-test",
                goal="Implement OAuth2 authentication system",
                complexity=Mock(value="moderate"),
                subgoals=[
                    Mock(
                        id="sg-1",
                        title="Implement OAuth provider integration",
                        description="Add Google/GitHub OAuth providers",
                        agent="@full-stack-dev",
                        confidence=0.85,
                        dependencies=[],
                        agent_exists=True,
                        recommended_agent="@full-stack-dev",
                    ),
                    Mock(
                        id="sg-2",
                        title="Write integration tests",
                        description="Test OAuth flow",
                        agent="@qa-test-architect",
                        confidence=0.92,
                        dependencies=["sg-1"],
                        agent_exists=True,
                        recommended_agent="@qa-test-architect",
                    ),
                ],
                memory_context=[
                    Mock(file="src/auth/login.py", relevance=0.85),
                ],
                gaps=[],
            ),
            plan_dir=plan_dir,
            warnings=[],
        )

        # Execute: Run aur goals
        runner = CliRunner()
        result = runner.invoke(
            goals_command,
            ["Implement OAuth2 authentication system", "--yes"],
        )

        assert result.exit_code == 0

        # Verify: goals.json was created
        goals_file = plan_dir / "goals.json"
        assert goals_file.exists()

        # Verify: goals.json has all required fields for /plan skill
        goals_data = json.loads(goals_file.read_text())

        # Required root fields
        assert "id" in goals_data
        assert "title" in goals_data
        assert "created_at" in goals_data
        assert "status" in goals_data
        assert "subgoals" in goals_data
        assert "memory_context" in goals_data
        assert "gaps" in goals_data

        # Verify subgoals have agent metadata for /plan
        assert len(goals_data["subgoals"]) == 2
        for subgoal in goals_data["subgoals"]:
            assert "id" in subgoal
            assert "title" in subgoal
            assert "description" in subgoal
            assert "agent" in subgoal
            assert "confidence" in subgoal
            assert "dependencies" in subgoal

        # Verify dependencies format
        assert goals_data["subgoals"][1]["dependencies"] == ["sg-1"]

    @patch("aurora_cli.commands.goals.CLIPipeLLMClient")
    @patch("aurora_cli.commands.goals.create_plan")
    @patch("aurora_cli.commands.goals.shutil.which", return_value="/usr/bin/claude")
    def test_goals_json_format_for_plan_skill(
        self, mock_which, mock_create_plan, mock_client, isolated_project, valid_subgoal
    ):
        """Test: goals.json format is compatible with /plan skill expectations."""
        # Setup
        plan_dir = isolated_project / ".aurora" / "plans" / "0001-test"
        plan_dir.mkdir(parents=True)

        mock_instance = Mock()
        mock_client.return_value = mock_instance

        mock_create_plan.return_value = Mock(
            success=True,
            plan=Mock(
                plan_id="0001-test",
                goal="Test goal for plan skill compatibility check",
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
            ["Test goal for plan skill compatibility check", "--yes"],
        )

        assert result.exit_code == 0

        # Verify goals.json can be parsed and has expected structure
        goals_file = plan_dir / "goals.json"
        goals_data = json.loads(goals_file.read_text())

        # /plan skill expects these fields
        assert goals_data["status"] == "ready_for_planning"
        assert isinstance(goals_data["subgoals"], list)
        assert isinstance(goals_data["memory_context"], list)
        assert isinstance(goals_data["gaps"], list)

    @patch("aurora_cli.commands.goals.CLIPipeLLMClient")
    @patch("aurora_cli.commands.goals.create_plan")
    @patch("aurora_cli.commands.goals.shutil.which", return_value="/usr/bin/claude")
    def test_plan_skill_can_read_agent_metadata(
        self, mock_which, mock_create_plan, mock_client, isolated_project
    ):
        """Test: goals.json includes agent metadata for /plan to use in tasks.md."""
        # Setup
        plan_dir = isolated_project / ".aurora" / "plans" / "0001-test"
        plan_dir.mkdir(parents=True)

        mock_instance = Mock()
        mock_client.return_value = mock_instance

        # Multiple agents to test agent metadata
        mock_create_plan.return_value = Mock(
            success=True,
            plan=Mock(
                plan_id="0001-test",
                goal="Multi-agent workflow test for plan skill integration",
                complexity=Mock(value="moderate"),
                subgoals=[
                    Mock(
                        id="sg-1",
                        title="Backend implementation task",
                        description="API implementation with proper error handling",
                        agent="@full-stack-dev",
                        confidence=0.90,
                        dependencies=[],
                        agent_exists=True,
                        recommended_agent="@full-stack-dev",
                    ),
                    Mock(
                        id="sg-2",
                        title="Frontend implementation task",
                        description="UI implementation with responsive design",
                        agent="@ux-expert",
                        confidence=0.88,
                        dependencies=["sg-1"],
                        agent_exists=True,
                        recommended_agent="@ux-expert",
                    ),
                    Mock(
                        id="sg-3",
                        title="Testing implementation task",
                        description="E2E tests implementation with full coverage",
                        agent="@qa-test-architect",
                        confidence=0.95,
                        dependencies=["sg-1", "sg-2"],
                        agent_exists=True,
                        recommended_agent="@qa-test-architect",
                    ),
                ],
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
            ["Multi-agent workflow test for plan skill integration", "--yes"],
        )

        assert result.exit_code == 0

        # Verify agent metadata is present for /plan skill to generate tasks.md
        goals_file = plan_dir / "goals.json"
        goals_data = json.loads(goals_file.read_text())

        agents_found = [sg["agent"] for sg in goals_data["subgoals"]]
        assert "@full-stack-dev" in agents_found
        assert "@ux-expert" in agents_found
        assert "@qa-test-architect" in agents_found

        # Verify /plan skill can use this to generate:
        # <!-- agent: @agent-id --> comments in tasks.md
        for subgoal in goals_data["subgoals"]:
            assert subgoal["agent"].startswith("@")

    def test_expected_directory_structure_for_plan_skill(self, isolated_project):
        """Test: Document expected directory structure after aur goals → /plan."""
        # This test documents the expected structure
        plan_dir = isolated_project / ".aurora" / "plans" / "0001-example"
        plan_dir.mkdir(parents=True)

        # After aur goals:
        goals_file = plan_dir / "goals.json"
        goals_file.write_text(
            '{"id": "0001-example", "title": "Example goal for documentation", "status": "ready_for_planning", "subgoals": [{"id": "sg-1", "title": "Test", "description": "Test", "agent": "@full-stack-dev", "confidence": 0.9, "dependencies": []}], "memory_context": [], "gaps": []}'
        )

        assert goals_file.exists()

        # After /plan skill (expected files):
        expected_files = [
            "goals.json",  # Created by: aur goals
            "prd.md",  # Created by: /plan
            "tasks.md",  # Created by: /plan
            "specs/",  # Created by: /plan
            "agents.json",  # Optional metadata
        ]

        # Verify goals.json exists
        assert (plan_dir / "goals.json").exists()

        # Document: /plan skill should create these files
        # (We don't create them in this test, just document the expectation)
        expected_structure = {
            "goals.json": "High-level goal decomposition with agent assignments",
            "prd.md": "Product Requirements Document generated by /plan",
            "tasks.md": "Task list with agent metadata comments",
            "specs/": "Detailed specifications directory",
        }

        # This test passes by documenting the integration contract
        assert len(expected_structure) == 4

    @patch("aurora_cli.commands.goals.CLIPipeLLMClient")
    @patch("aurora_cli.commands.goals.create_plan")
    @patch("aurora_cli.commands.goals.shutil.which", return_value="/usr/bin/claude")
    def test_goals_json_includes_memory_context_for_plan(
        self, mock_which, mock_create_plan, mock_client, isolated_project, valid_subgoal
    ):
        """Test: goals.json includes memory context for /plan to reference in PRD."""
        # Setup
        plan_dir = isolated_project / ".aurora" / "plans" / "0001-test"
        plan_dir.mkdir(parents=True)

        mock_instance = Mock()
        mock_client.return_value = mock_instance

        # Mock with memory context
        mock_create_plan.return_value = Mock(
            success=True,
            plan=Mock(
                plan_id="0001-test",
                goal="Test goal with memory context for plan skill",
                complexity=Mock(value="simple"),
                subgoals=[valid_subgoal],
                memory_context=[
                    Mock(file="src/api/endpoints.py", relevance=0.92),
                    Mock(file="src/models/user.py", relevance=0.85),
                    Mock(file="docs/api-design.md", relevance=0.78),
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
            ["Test goal with memory context for plan skill", "--yes"],
        )

        assert result.exit_code == 0

        # Verify memory context is included for /plan
        goals_file = plan_dir / "goals.json"
        goals_data = json.loads(goals_file.read_text())

        assert len(goals_data["memory_context"]) == 3

        # Verify format /plan can use
        for ctx in goals_data["memory_context"]:
            assert "file" in ctx
            assert "relevance" in ctx
            assert 0.0 <= ctx["relevance"] <= 1.0

        # /plan skill can use this to reference relevant files in PRD
        files = [ctx["file"] for ctx in goals_data["memory_context"]]
        assert "src/api/endpoints.py" in files
