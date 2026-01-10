"""Tests for goals.json generation and format.

This module tests the Goals model and goals.json generation that matches
FR-6.2 format from PRD-0026.
"""

import json
from datetime import datetime
from pathlib import Path

import pytest

from aurora_cli.planning.models import AgentGap, Subgoal


class TestGoalsJsonFormat:
    """Test goals.json format and generation."""

    def test_goals_json_includes_required_fields(self):
        """Test that Goals model includes all required fields from FR-6.2."""
        from aurora_cli.planning.models import Goals, MemoryContext, SubgoalData

        # Arrange
        memory_context = [
            MemoryContext(file="src/auth.py", relevance=0.85),
            MemoryContext(file="tests/test_auth.py", relevance=0.72),
        ]

        subgoals = [
            SubgoalData(
                id="sg-1",
                title="Implement OAuth provider",
                description="Add Google/GitHub OAuth",
                agent="@full-stack-dev",
                confidence=0.85,
                dependencies=[],
            ),
        ]

        gaps = [
            AgentGap(
                subgoal_id="sg-2",
                recommended_agent="@security-expert",
                agent_exists=False,
                fallback="@full-stack-dev",
                suggested_capabilities=["security", "audit"],
            ),
        ]

        # Act
        goals = Goals(
            id="0001-add-oauth2",
            title="Add OAuth2 Authentication",
            created_at=datetime.utcnow(),
            status="ready_for_planning",
            memory_context=memory_context,
            subgoals=subgoals,
            gaps=gaps,
        )

        # Assert - verify all required fields exist
        assert goals.id == "0001-add-oauth2"
        assert goals.title == "Add OAuth2 Authentication"
        assert isinstance(goals.created_at, datetime)
        assert goals.status == "ready_for_planning"
        assert len(goals.memory_context) == 2
        assert len(goals.subgoals) == 1
        assert len(goals.gaps) == 1

    def test_goals_json_serializes_correctly(self):
        """Test that Goals can be serialized to valid JSON."""
        from aurora_cli.planning.models import Goals, MemoryContext, SubgoalData

        # Arrange
        goals = Goals(
            id="0001-test",
            title="Test Goal for JSON serialization",
            created_at=datetime(2026, 1, 10, 12, 0, 0),
            status="ready_for_planning",
            memory_context=[
                MemoryContext(file="test.py", relevance=0.9),
            ],
            subgoals=[
                SubgoalData(
                    id="sg-1",
                    title="Test subgoal",
                    description="Test description",
                    agent="@test-agent",
                    confidence=0.8,
                    dependencies=[],
                ),
            ],
            gaps=[],
        )

        # Act
        json_str = goals.model_dump_json(indent=2)
        parsed = json.loads(json_str)

        # Assert - verify JSON structure
        assert parsed["id"] == "0001-test"
        assert parsed["title"] == "Test Goal for JSON serialization"
        assert "created_at" in parsed
        assert parsed["status"] == "ready_for_planning"
        assert len(parsed["memory_context"]) == 1
        assert len(parsed["subgoals"]) == 1
        assert parsed["subgoals"][0]["id"] == "sg-1"

    def test_memory_context_model(self):
        """Test MemoryContext model with file and relevance."""
        from aurora_cli.planning.models import MemoryContext

        # Act
        context = MemoryContext(file="src/api.py", relevance=0.75)

        # Assert
        assert context.file == "src/api.py"
        assert context.relevance == 0.75
        assert 0.0 <= context.relevance <= 1.0

    def test_subgoal_data_model(self):
        """Test SubgoalData model with all required fields."""
        from aurora_cli.planning.models import SubgoalData

        # Act
        subgoal = SubgoalData(
            id="sg-1",
            title="Implement feature",
            description="Detailed description",
            agent="@full-stack-dev",
            confidence=0.92,
            dependencies=["sg-0"],
        )

        # Assert
        assert subgoal.id == "sg-1"
        assert subgoal.title == "Implement feature"
        assert subgoal.description == "Detailed description"
        assert subgoal.agent == "@full-stack-dev"
        assert subgoal.confidence == 0.92
        assert subgoal.dependencies == ["sg-0"]

    def test_subgoal_data_no_dependencies(self):
        """Test SubgoalData with empty dependencies."""
        from aurora_cli.planning.models import SubgoalData

        # Act
        subgoal = SubgoalData(
            id="sg-1",
            title="First task",
            description="Description",
            agent="@agent",
            confidence=0.8,
            dependencies=[],
        )

        # Assert
        assert subgoal.dependencies == []

    def test_goals_with_multiple_subgoals(self):
        """Test Goals with multiple subgoals and dependencies."""
        from aurora_cli.planning.models import Goals, MemoryContext, SubgoalData

        # Arrange
        subgoals = [
            SubgoalData(
                id="sg-1",
                title="First task",
                description="Description 1",
                agent="@agent-1",
                confidence=0.9,
                dependencies=[],
            ),
            SubgoalData(
                id="sg-2",
                title="Second task",
                description="Description 2",
                agent="@agent-2",
                confidence=0.85,
                dependencies=["sg-1"],
            ),
            SubgoalData(
                id="sg-3",
                title="Third task",
                description="Description 3",
                agent="@agent-3",
                confidence=0.8,
                dependencies=["sg-1", "sg-2"],
            ),
        ]

        # Act
        goals = Goals(
            id="0001-complex",
            title="Complex Goal",
            created_at=datetime.utcnow(),
            status="ready_for_planning",
            memory_context=[],
            subgoals=subgoals,
            gaps=[],
        )

        # Assert
        assert len(goals.subgoals) == 3
        assert goals.subgoals[1].dependencies == ["sg-1"]
        assert goals.subgoals[2].dependencies == ["sg-1", "sg-2"]

    def test_goals_json_matches_prd_format(self):
        """Test that serialized Goals matches FR-6.2 example from PRD."""
        from aurora_cli.planning.models import Goals, MemoryContext, SubgoalData

        # Arrange - create goals matching PRD example
        goals = Goals(
            id="0001-add-oauth2",
            title="Add OAuth2 Authentication",
            created_at=datetime(2026, 1, 9, 12, 0, 0),
            status="ready_for_planning",
            memory_context=[
                MemoryContext(file="src/auth/login.py", relevance=0.85),
                MemoryContext(file="docs/auth-design.md", relevance=0.72),
            ],
            subgoals=[
                SubgoalData(
                    id="sg-1",
                    title="Implement OAuth provider integration",
                    description="Add Google/GitHub OAuth providers",
                    agent="@full-stack-dev",
                    confidence=0.85,
                    dependencies=[],
                ),
                SubgoalData(
                    id="sg-2",
                    title="Write OAuth integration tests",
                    description="Test OAuth flow end-to-end",
                    agent="@qa-test-architect",
                    confidence=0.92,
                    dependencies=["sg-1"],
                ),
            ],
            gaps=[
                AgentGap(
                    subgoal_id="sg-3",
                    recommended_agent="@security-expert",
                    agent_exists=False,
                    fallback="@full-stack-dev",
                    suggested_capabilities=["security", "audit"],
                ),
            ],
        )

        # Act
        json_str = goals.model_dump_json(indent=2)
        data = json.loads(json_str)

        # Assert - verify matches PRD format
        assert data["id"] == "0001-add-oauth2"
        assert data["title"] == "Add OAuth2 Authentication"
        assert data["status"] == "ready_for_planning"
        assert len(data["memory_context"]) == 2
        assert data["memory_context"][0]["file"] == "src/auth/login.py"
        assert data["memory_context"][0]["relevance"] == 0.85
        assert len(data["subgoals"]) == 2
        assert data["subgoals"][0]["id"] == "sg-1"
        assert data["subgoals"][0]["agent"] == "@full-stack-dev"
        assert data["subgoals"][1]["dependencies"] == ["sg-1"]
        assert len(data["gaps"]) == 1
        assert data["gaps"][0]["subgoal_id"] == "sg-3"

    def test_goals_empty_memory_context(self):
        """Test Goals with no memory context (not indexed)."""
        from aurora_cli.planning.models import Goals, SubgoalData

        # Act
        goals = Goals(
            id="0001-test",
            title="Test without memory",
            created_at=datetime.utcnow(),
            status="ready_for_planning",
            memory_context=[],
            subgoals=[
                SubgoalData(
                    id="sg-1",
                    title="Task name",
                    description="Description",
                    agent="@agent",
                    confidence=0.7,
                    dependencies=[],
                ),
            ],
            gaps=[],
        )

        # Assert
        assert goals.memory_context == []
        assert len(goals.subgoals) == 1

    def test_goals_empty_gaps(self):
        """Test Goals with no agent gaps (all agents found)."""
        from aurora_cli.planning.models import Goals, SubgoalData

        # Act
        goals = Goals(
            id="0001-test",
            title="Test without gaps",
            created_at=datetime.utcnow(),
            status="ready_for_planning",
            memory_context=[],
            subgoals=[
                SubgoalData(
                    id="sg-1",
                    title="Task name",
                    description="Description",
                    agent="@full-stack-dev",
                    confidence=0.9,
                    dependencies=[],
                ),
            ],
            gaps=[],
        )

        # Assert
        assert goals.gaps == []

    def test_generate_goals_json_function(self):
        """Test generate_goals_json() helper function."""
        from aurora_cli.planning.core import generate_goals_json

        # Arrange
        plan_id = "0001-test-goal"
        goal = "Test goal description"
        subgoals = [
            Subgoal(
                id="sg-1",
                title="Test subgoal",
                description="Test description",
                recommended_agent="@test-agent",
                dependencies=[],
            ),
        ]
        memory_context = [("test.py", 0.8)]
        gaps = []

        # Act
        goals_data = generate_goals_json(
            plan_id=plan_id,
            goal=goal,
            subgoals=subgoals,
            memory_context=memory_context,
            gaps=gaps,
        )

        # Assert
        assert goals_data.id == plan_id
        assert goals_data.title == goal
        assert len(goals_data.subgoals) == 1
        assert len(goals_data.memory_context) == 1
