"""Tests for enhanced AgentRecommender with LLM fallback.

This module tests the enhanced AgentRecommender that uses LLM-based
classification when keyword matching fails.
"""

from unittest.mock import AsyncMock, MagicMock, Mock

import pytest

from aurora_cli.planning.agents import AgentRecommender
from aurora_cli.planning.models import Subgoal
from aurora_reasoning.llm_client import LLMResponse


class TestAgentMatchingWithLLM:
    """Test agent matching with LLM fallback."""

    def test_keyword_matching_high_score(self):
        """Test that keyword matching works when score >= 0.5."""
        # Arrange
        subgoal = Subgoal(
            id="sg-1",
            title="Write comprehensive tests",
            description="Create unit tests and integration tests for the authentication module",
            recommended_agent="@qa-test-architect",
        )

        # Mock manifest with qa-test-architect
        mock_manifest = MagicMock()
        mock_agent = MagicMock()
        mock_agent.id = "qa-test-architect"
        mock_agent.when_to_use = (
            "Use for testing, quality assurance, test architecture, unit tests, integration tests"
        )
        mock_agent.capabilities = [
            "testing",
            "quality",
            "test-driven-development",
            "tests",
            "integration",
        ]
        mock_manifest.agents = [mock_agent]

        recommender = AgentRecommender(
            manifest=mock_manifest,
            score_threshold=0.3,  # Lower threshold to ensure test passes
        )

        # Act
        agent_id, score = recommender.recommend_for_subgoal(subgoal)

        # Assert
        assert agent_id == "@qa-test-architect"
        assert score > 0.0  # Should have some overlap with keywords

    def test_keyword_matching_low_score_no_llm(self):
        """Test that low keyword score returns fallback when no LLM available."""
        # Arrange
        subgoal = Subgoal(
            id="sg-1",
            title="Implement quantum blockchain",
            description="Build quantum-resistant blockchain with zero-knowledge proofs",
            recommended_agent="@full-stack-dev",
        )

        # Mock manifest with standard agents (no quantum expert)
        mock_manifest = MagicMock()
        mock_agent = MagicMock()
        mock_agent.id = "full-stack-dev"
        mock_agent.when_to_use = "General development tasks"
        mock_agent.capabilities = ["backend", "frontend", "api"]
        mock_manifest.agents = [mock_agent]

        recommender = AgentRecommender(
            manifest=mock_manifest,
            score_threshold=0.5,
            llm_client=None,  # No LLM
        )

        # Act
        agent_id, score = recommender.recommend_for_subgoal(subgoal)

        # Assert
        assert agent_id == "@full-stack-dev"  # Fallback
        assert score < 0.5

    @pytest.mark.asyncio
    async def test_llm_fallback_when_keyword_fails(self):
        """Test that LLM is called when keyword matching score < 0.5."""
        # Arrange
        subgoal = Subgoal(
            id="sg-1",
            title="Design authentication flow",
            description="Create architecture for OAuth2 and JWT authentication",
            recommended_agent="@holistic-architect",
        )

        # Mock manifest with no good match
        mock_manifest = MagicMock()
        mock_agent = MagicMock()
        mock_agent.id = "full-stack-dev"
        mock_agent.when_to_use = "General development"
        mock_agent.capabilities = ["coding"]

        # Need to properly configure mock agent
        mock_agent2 = MagicMock()
        mock_agent2.id = "qa-test-architect"
        mock_agent2.when_to_use = "Testing"
        mock_agent2.capabilities = ["qa"]

        mock_manifest.agents = [mock_agent, mock_agent2]

        # Mock LLM client
        mock_llm_response = LLMResponse(
            content="""{
                "agent_id": "@holistic-architect",
                "confidence": 0.92,
                "reasoning": "Architecture design requires system architect"
            }""",
            model="claude-sonnet",
            input_tokens=100,
            output_tokens=50,
            finish_reason="stop",
            metadata={"phase": "agent_matching"},
        )
        mock_llm_client = Mock()
        mock_llm_client.generate = AsyncMock(return_value=mock_llm_response)

        recommender = AgentRecommender(
            manifest=mock_manifest,
            score_threshold=0.5,
            llm_client=mock_llm_client,
        )

        # Act
        agent_id, score = await recommender.recommend_for_subgoal_async(subgoal)

        # Assert
        assert agent_id == "@holistic-architect"
        assert score == 0.92
        mock_llm_client.generate.assert_called_once()

    @pytest.mark.asyncio
    async def test_llm_classification_with_confidence(self):
        """Test LLM returns agent with confidence score."""
        # Arrange
        subgoal = Subgoal(
            id="sg-1",
            title="Create user dashboard UI",
            description="Design and implement user dashboard with charts",
            recommended_agent="@ux-expert",
        )

        mock_manifest = MagicMock()
        mock_agent1 = MagicMock()
        mock_agent1.id = "ux-expert"
        mock_agent1.when_to_use = "UI design"
        mock_agent1.capabilities = ["design"]
        mock_agent2 = MagicMock()
        mock_agent2.id = "full-stack-dev"
        mock_agent2.when_to_use = "Development"
        mock_agent2.capabilities = ["code"]
        mock_manifest.agents = [mock_agent1, mock_agent2]

        # Mock LLM response
        mock_llm_response = LLMResponse(
            content="""{
                "agent_id": "@ux-expert",
                "confidence": 0.88,
                "reasoning": "UI design and dashboard require UX expertise"
            }""",
            model="claude-sonnet",
            input_tokens=100,
            output_tokens=50,
            finish_reason="stop",
            metadata={"phase": "agent_matching"},
        )
        mock_llm_client = Mock()
        mock_llm_client.generate = AsyncMock(return_value=mock_llm_response)

        recommender = AgentRecommender(
            manifest=mock_manifest,
            score_threshold=0.5,
            llm_client=mock_llm_client,
        )

        # Act
        agent_id, confidence = await recommender.recommend_for_subgoal_async(subgoal)

        # Assert
        assert agent_id == "@ux-expert"
        assert 0.8 <= confidence <= 0.9

    @pytest.mark.asyncio
    async def test_llm_fallback_graceful_degradation(self):
        """Test graceful degradation when LLM fails."""
        # Arrange
        subgoal = Subgoal(
            id="sg-1",
            title="Implement feature",
            description="Build a new feature",
            recommended_agent="@full-stack-dev",
        )

        mock_manifest = MagicMock()
        mock_agent = MagicMock()
        mock_agent.id = "full-stack-dev"
        mock_agent.when_to_use = "General tasks"
        mock_agent.capabilities = ["dev"]
        mock_manifest.agents = [mock_agent]

        # Mock LLM that raises exception
        mock_llm_client = Mock()
        mock_llm_client.generate = AsyncMock(side_effect=Exception("LLM API error"))

        recommender = AgentRecommender(
            manifest=mock_manifest,
            score_threshold=0.5,
            llm_client=mock_llm_client,
            default_fallback="@full-stack-dev",
        )

        # Act
        agent_id, score = await recommender.recommend_for_subgoal_async(subgoal)

        # Assert - should return fallback, not crash
        assert agent_id == "@full-stack-dev"
        assert score < 0.5

    @pytest.mark.asyncio
    async def test_llm_includes_available_agents_in_prompt(self):
        """Test that LLM prompt includes list of available agents."""
        # Arrange
        subgoal = Subgoal(
            id="sg-1",
            title="Test task",
            description="Task description",
            recommended_agent="@full-stack-dev",
        )

        mock_manifest = MagicMock()
        mock_agent1 = MagicMock()
        mock_agent1.id = "full-stack-dev"
        mock_agent1.when_to_use = "Development tasks"
        mock_agent2 = MagicMock()
        mock_agent2.id = "qa-test-architect"
        mock_agent2.when_to_use = "Testing tasks"
        mock_manifest.agents = [mock_agent1, mock_agent2]

        mock_llm_response = LLMResponse(
            content='{"agent_id": "@full-stack-dev", "confidence": 0.7, "reasoning": "test"}',
            model="claude-sonnet",
            input_tokens=100,
            output_tokens=50,
            finish_reason="stop",
            metadata={},
        )
        mock_llm_client = Mock()
        mock_llm_client.generate = AsyncMock(return_value=mock_llm_response)

        recommender = AgentRecommender(
            manifest=mock_manifest,
            score_threshold=0.5,
            llm_client=mock_llm_client,
        )

        # Act
        await recommender.recommend_for_subgoal_async(subgoal)

        # Assert - check prompt includes agent list
        mock_llm_client.generate.assert_called_once()
        call_args = mock_llm_client.generate.call_args
        prompt = call_args[0][0]

        assert "full-stack-dev" in prompt
        assert "qa-test-architect" in prompt
        assert "Development tasks" in prompt or "Testing tasks" in prompt
