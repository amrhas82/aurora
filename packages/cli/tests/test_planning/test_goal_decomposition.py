"""Tests for goal decomposition logic using CLIPipeLLMClient.

This module tests the decompose_goal function that uses LLM-based
decomposition to break down high-level goals into concrete subgoals.
"""

from unittest.mock import AsyncMock, Mock

import pytest

from aurora_cli.llm.cli_pipe_client import CLIPipeLLMClient
from aurora_cli.planning.core import decompose_goal
from aurora_cli.planning.models import Subgoal
from aurora_reasoning.llm_client import LLMResponse


class TestGoalDecomposition:
    """Test goal decomposition with LLM."""

    @pytest.mark.asyncio
    async def test_decompose_simple_goal(self):
        """Test decomposition of a simple goal into 2 subgoals."""
        # Arrange
        goal = "Add login functionality"
        context_files = [
            ("src/auth/models.py", 0.85),
            ("src/auth/views.py", 0.72),
        ]

        # Mock LLM response
        mock_response = LLMResponse(
            content="""[
                {
                    "id": "sg-1",
                    "title": "Implement login endpoint",
                    "description": "Create API endpoint for user authentication",
                    "recommended_agent": "@full-stack-dev",
                    "dependencies": []
                },
                {
                    "id": "sg-2",
                    "title": "Add login UI",
                    "description": "Create login form component",
                    "recommended_agent": "@ux-expert",
                    "dependencies": ["sg-1"]
                }
            ]""",
            model="claude-sonnet",
            input_tokens=100,
            output_tokens=200,
            finish_reason="stop",
            metadata={"phase": "decompose"},
        )

        mock_client = Mock(spec=CLIPipeLLMClient)
        mock_client.generate = AsyncMock(return_value=mock_response)

        # Act
        subgoals = await decompose_goal(goal, context_files, mock_client)

        # Assert
        assert len(subgoals) == 2
        assert subgoals[0].id == "sg-1"
        assert subgoals[0].title == "Implement login endpoint"
        assert subgoals[0].recommended_agent == "@full-stack-dev"
        assert subgoals[0].dependencies == []

        assert subgoals[1].id == "sg-2"
        assert subgoals[1].dependencies == ["sg-1"]

    @pytest.mark.asyncio
    async def test_decompose_complex_goal(self):
        """Test decomposition of a complex goal into 5-7 subgoals."""
        # Arrange
        goal = "Implement OAuth2 authentication with JWT tokens and refresh flow"
        context_files = []

        mock_response = LLMResponse(
            content="""[
                {
                    "id": "sg-1",
                    "title": "Design auth architecture",
                    "description": "Design OAuth2 flow and JWT structure",
                    "recommended_agent": "@holistic-architect",
                    "dependencies": []
                },
                {
                    "id": "sg-2",
                    "title": "Implement token generation",
                    "description": "Create JWT token generation logic",
                    "recommended_agent": "@full-stack-dev",
                    "dependencies": ["sg-1"]
                },
                {
                    "id": "sg-3",
                    "title": "Implement OAuth2 providers",
                    "description": "Add Google and GitHub OAuth providers",
                    "recommended_agent": "@full-stack-dev",
                    "dependencies": ["sg-1"]
                },
                {
                    "id": "sg-4",
                    "title": "Add refresh token flow",
                    "description": "Implement token refresh mechanism",
                    "recommended_agent": "@full-stack-dev",
                    "dependencies": ["sg-2"]
                },
                {
                    "id": "sg-5",
                    "title": "Write auth tests",
                    "description": "Comprehensive testing of auth flows",
                    "recommended_agent": "@qa-test-architect",
                    "dependencies": ["sg-2", "sg-3", "sg-4"]
                }
            ]""",
            model="claude-sonnet",
            input_tokens=150,
            output_tokens=350,
            finish_reason="stop",
            metadata={"phase": "decompose"},
        )

        mock_client = Mock(spec=CLIPipeLLMClient)
        mock_client.generate = AsyncMock(return_value=mock_response)

        # Act
        subgoals = await decompose_goal(goal, context_files, mock_client)

        # Assert
        assert 5 <= len(subgoals) <= 7
        assert all(sg.id.startswith("sg-") for sg in subgoals)
        assert all(sg.recommended_agent.startswith("@") for sg in subgoals)

    @pytest.mark.asyncio
    async def test_decompose_uses_context_files(self):
        """Test that context files are included in prompt."""
        # Arrange
        goal = "Refactor authentication system"
        context_files = [
            ("src/auth/login.py", 0.95),
            ("src/auth/oauth.py", 0.88),
            ("tests/test_auth.py", 0.75),
        ]

        mock_response = LLMResponse(
            content="""[{
                "id": "sg-1",
                "title": "Analyze current auth code",
                "description": "Review existing authentication implementation",
                "recommended_agent": "@holistic-architect",
                "dependencies": []
            }]""",
            model="claude-sonnet",
            input_tokens=100,
            output_tokens=150,
            finish_reason="stop",
            metadata={"phase": "decompose"},
        )

        mock_client = Mock(spec=CLIPipeLLMClient)
        mock_client.generate = AsyncMock(return_value=mock_response)

        # Act
        await decompose_goal(goal, context_files, mock_client)

        # Assert
        mock_client.generate.assert_called_once()
        call_args = mock_client.generate.call_args
        prompt = call_args[0][0]

        # Verify context files are in prompt
        assert "src/auth/login.py" in prompt
        assert "0.95" in prompt or "95" in prompt
        assert "src/auth/oauth.py" in prompt

    @pytest.mark.asyncio
    async def test_decompose_with_dependencies(self):
        """Test subgoals with proper dependency tracking."""
        # Arrange
        goal = "Build API with tests"
        context_files = []

        mock_response = LLMResponse(
            content="""[
                {
                    "id": "sg-1",
                    "title": "Design API",
                    "description": "Design API endpoints",
                    "recommended_agent": "@holistic-architect",
                    "dependencies": []
                },
                {
                    "id": "sg-2",
                    "title": "Implement API",
                    "description": "Build API implementation",
                    "recommended_agent": "@full-stack-dev",
                    "dependencies": ["sg-1"]
                },
                {
                    "id": "sg-3",
                    "title": "Test API",
                    "description": "Write API tests",
                    "recommended_agent": "@qa-test-architect",
                    "dependencies": ["sg-2"]
                }
            ]""",
            model="claude-sonnet",
            input_tokens=100,
            output_tokens=200,
            finish_reason="stop",
            metadata={"phase": "decompose"},
        )

        mock_client = Mock(spec=CLIPipeLLMClient)
        mock_client.generate = AsyncMock(return_value=mock_response)

        # Act
        subgoals = await decompose_goal(goal, context_files, mock_client)

        # Assert
        assert subgoals[0].dependencies == []
        assert subgoals[1].dependencies == ["sg-1"]
        assert subgoals[2].dependencies == ["sg-2"]

    @pytest.mark.asyncio
    async def test_decompose_validates_output(self):
        """Test that invalid LLM output is rejected."""
        # Arrange
        goal = "Invalid goal test"
        context_files = []

        # Mock invalid response (missing required fields)
        mock_response = LLMResponse(
            content="""[
                {
                    "id": "sg-1",
                    "title": "Do something"
                }
            ]""",
            model="claude-sonnet",
            input_tokens=100,
            output_tokens=50,
            finish_reason="stop",
            metadata={"phase": "decompose"},
        )

        mock_client = Mock(spec=CLIPipeLLMClient)
        mock_client.generate = AsyncMock(return_value=mock_response)

        # Act & Assert
        with pytest.raises((ValueError, KeyError)):
            await decompose_goal(goal, context_files, mock_client)
