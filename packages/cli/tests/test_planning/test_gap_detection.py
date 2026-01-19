"""Tests for agent gap detection in AgentRecommender.

This module tests the gap detection functionality that identifies
subgoals with low-confidence agent matches and suggests required capabilities.
"""

from unittest.mock import MagicMock

from aurora_cli.planning.agents import AgentRecommender
from aurora_cli.planning.models import Subgoal


class TestGapDetection:
    """Test agent gap detection."""

    def test_detect_gaps_with_low_confidence(self):
        """Test that gaps are detected for subgoals with confidence < 0.5."""
        # Arrange
        subgoals = [
            Subgoal(
                id="sg-1",
                title="Implement quantum blockchain",
                description="Build quantum-resistant blockchain",
                recommended_agent="@quantum-expert",
            ),
            Subgoal(
                id="sg-2",
                title="Write tests",
                description="Create test suite",
                recommended_agent="@quality-assurance",
            ),
        ]

        recommendations = {
            "sg-1": ("@code-developer", 0.15),  # Low confidence - gap
            "sg-2": ("@quality-assurance", 0.85),  # High confidence - no gap
        }

        # Mock manifest
        mock_manifest = MagicMock()
        mock_agent = MagicMock()
        mock_agent.id = "quality-assurance"
        mock_manifest.agents = [mock_agent]
        mock_manifest.get_agent = MagicMock(
            side_effect=lambda x: mock_agent if x == "quality-assurance" else None
        )

        recommender = AgentRecommender(
            manifest=mock_manifest,
            score_threshold=0.5,
        )

        # Act
        gaps = recommender.detect_gaps(subgoals, recommendations)

        # Assert
        assert len(gaps) == 1
        assert gaps[0].subgoal_id == "sg-1"
        assert gaps[0].fallback == "@code-developer"

    def test_detect_gaps_no_gaps_all_high_confidence(self):
        """Test that no gaps detected when all confidence scores >= 0.5."""
        # Arrange
        subgoals = [
            Subgoal(
                id="sg-1",
                title="Write tests",
                description="Create test suite",
                recommended_agent="@quality-assurance",
            ),
            Subgoal(
                id="sg-2",
                title="Implement API",
                description="Build REST API",
                recommended_agent="@code-developer",
            ),
        ]

        recommendations = {
            "sg-1": ("@quality-assurance", 0.85),
            "sg-2": ("@code-developer", 0.72),
        }

        mock_manifest = MagicMock()
        mock_agent1 = MagicMock()
        mock_agent1.id = "quality-assurance"
        mock_agent2 = MagicMock()
        mock_agent2.id = "code-developer"
        mock_manifest.agents = [mock_agent1, mock_agent2]
        mock_manifest.get_agent = MagicMock(return_value=mock_agent1)

        recommender = AgentRecommender(
            manifest=mock_manifest,
            score_threshold=0.5,
        )

        # Act
        gaps = recommender.detect_gaps(subgoals, recommendations)

        # Assert
        assert len(gaps) == 0

    def test_detect_gaps_extracts_keywords_for_capabilities(self):
        """Test that suggested capabilities are extracted from subgoal keywords."""
        # Arrange
        subgoals = [
            Subgoal(
                id="sg-1",
                title="Implement blockchain consensus algorithm",
                description="Build proof-of-stake consensus with validator rotation",
                recommended_agent="@blockchain-expert",
            ),
        ]

        recommendations = {
            "sg-1": ("@code-developer", 0.15),  # Low confidence
        }

        mock_manifest = MagicMock()
        mock_agent = MagicMock()
        mock_agent.id = "code-developer"
        mock_manifest.agents = [mock_agent]
        mock_manifest.get_agent = MagicMock(return_value=None)  # Agent doesn't exist

        recommender = AgentRecommender(
            manifest=mock_manifest,
            score_threshold=0.5,
        )

        # Act
        gaps = recommender.detect_gaps(subgoals, recommendations)

        # Assert
        assert len(gaps) == 1
        gap = gaps[0]
        assert gap.subgoal_id == "sg-1"
        # Should contain keywords from title/description
        capabilities = [c.lower() for c in gap.suggested_capabilities]
        assert any("blockchain" in c or "consensus" in c or "validator" in c for c in capabilities)

    def test_detect_gaps_formats_for_goals_json(self):
        """Test that gaps are formatted correctly for goals.json output."""
        # Arrange
        subgoals = [
            Subgoal(
                id="sg-1",
                title="AI model training",
                description="Train neural network",
                recommended_agent="@ml-engineer",
            ),
        ]

        recommendations = {
            "sg-1": ("@code-developer", 0.25),
        }

        mock_manifest = MagicMock()
        mock_agent = MagicMock()
        mock_agent.id = "code-developer"
        mock_manifest.agents = [mock_agent]
        mock_manifest.get_agent = MagicMock(return_value=None)

        recommender = AgentRecommender(
            manifest=mock_manifest,
            score_threshold=0.5,
        )

        # Act
        gaps = recommender.detect_gaps(subgoals, recommendations)

        # Assert
        assert len(gaps) == 1
        gap = gaps[0]
        # Verify AgentGap has all required fields for JSON serialization
        assert hasattr(gap, "subgoal_id")
        assert hasattr(gap, "recommended_agent")
        assert hasattr(gap, "agent_exists")
        assert hasattr(gap, "fallback")
        assert hasattr(gap, "suggested_capabilities")
        assert isinstance(gap.suggested_capabilities, list)

    def test_detect_gaps_reports_fallback_agent(self):
        """Test that gap includes fallback agent for each gap."""
        # Arrange
        subgoals = [
            Subgoal(
                id="sg-1",
                title="Specialized task",
                description="Needs expert",
                recommended_agent="@specialist",
            ),
        ]

        recommendations = {
            "sg-1": ("@code-developer", 0.2),
        }

        mock_manifest = MagicMock()
        mock_agent = MagicMock()
        mock_agent.id = "code-developer"
        mock_manifest.agents = [mock_agent]
        mock_manifest.get_agent = MagicMock(return_value=None)

        custom_fallback = "@custom-fallback"
        recommender = AgentRecommender(
            manifest=mock_manifest,
            score_threshold=0.5,
            default_fallback=custom_fallback,
        )

        # Act
        gaps = recommender.detect_gaps(subgoals, recommendations)

        # Assert
        assert len(gaps) == 1
        assert gaps[0].fallback == custom_fallback

    def test_detect_gaps_multiple_gaps(self):
        """Test detection of multiple gaps in single call."""
        # Arrange
        subgoals = [
            Subgoal(
                id="sg-1",
                title="Task 1",
                description="First specialized task",
                recommended_agent="@specialist-1",
            ),
            Subgoal(
                id="sg-2",
                title="Task 2",
                description="Second specialized task",
                recommended_agent="@specialist-2",
            ),
            Subgoal(
                id="sg-3",
                title="Task 3",
                description="General task",
                recommended_agent="@code-developer",
            ),
        ]

        recommendations = {
            "sg-1": ("@fallback", 0.15),
            "sg-2": ("@fallback", 0.25),
            "sg-3": ("@code-developer", 0.85),
        }

        mock_manifest = MagicMock()
        mock_agent = MagicMock()
        mock_agent.id = "code-developer"
        mock_manifest.agents = [mock_agent]
        mock_manifest.get_agent = MagicMock(
            side_effect=lambda x: mock_agent if x == "code-developer" else None
        )

        recommender = AgentRecommender(
            manifest=mock_manifest,
            score_threshold=0.5,
        )

        # Act
        gaps = recommender.detect_gaps(subgoals, recommendations)

        # Assert
        assert len(gaps) == 2
        gap_ids = {gap.subgoal_id for gap in gaps}
        assert gap_ids == {"sg-1", "sg-2"}

    def test_detect_gaps_limits_capabilities_to_10(self):
        """Test that suggested capabilities are limited to 10."""
        # Arrange
        # Create subgoal with many keywords
        long_description = " ".join([f"capability{i}" for i in range(20)])
        subgoals = [
            Subgoal(
                id="sg-1",
                title="Complex task with many requirements",
                description=long_description,
                recommended_agent="@specialist",
            ),
        ]

        recommendations = {
            "sg-1": ("@fallback", 0.1),
        }

        mock_manifest = MagicMock()
        mock_agent = MagicMock()
        mock_agent.id = "fallback"
        mock_manifest.agents = [mock_agent]
        mock_manifest.get_agent = MagicMock(return_value=None)

        recommender = AgentRecommender(
            manifest=mock_manifest,
            score_threshold=0.5,
        )

        # Act
        gaps = recommender.detect_gaps(subgoals, recommendations)

        # Assert
        assert len(gaps) == 1
        assert len(gaps[0].suggested_capabilities) <= 10

    def test_detect_gaps_empty_recommendations(self):
        """Test that empty recommendations dict returns empty gaps."""
        # Arrange
        subgoals = [
            Subgoal(
                id="sg-1",
                title="Task name",
                description="Task description",
                recommended_agent="@agent",
            ),
        ]

        recommendations = {}

        mock_manifest = MagicMock()
        recommender = AgentRecommender(manifest=mock_manifest)

        # Act
        gaps = recommender.detect_gaps(subgoals, recommendations)

        # Assert
        assert len(gaps) == 0

    def test_verify_agent_exists_true(self):
        """Test verify_agent_exists returns True for existing agent."""
        # Arrange
        mock_manifest = MagicMock()
        mock_agent = MagicMock()
        mock_agent.id = "quality-assurance"
        mock_manifest.agents = [mock_agent]
        mock_manifest.get_agent = MagicMock(return_value=mock_agent)

        recommender = AgentRecommender(manifest=mock_manifest)

        # Act
        exists = recommender.verify_agent_exists("@quality-assurance")

        # Assert
        assert exists is True

    def test_verify_agent_exists_false(self):
        """Test verify_agent_exists returns False for missing agent."""
        # Arrange
        mock_manifest = MagicMock()
        mock_manifest.agents = []
        mock_manifest.get_agent = MagicMock(return_value=None)

        recommender = AgentRecommender(manifest=mock_manifest)

        # Act
        exists = recommender.verify_agent_exists("@nonexistent")

        # Assert
        assert exists is False

    def test_verify_agent_exists_strips_at_prefix(self):
        """Test verify_agent_exists works with or without @ prefix."""
        # Arrange
        mock_manifest = MagicMock()
        mock_agent = MagicMock()
        mock_agent.id = "code-developer"
        mock_manifest.agents = [mock_agent]
        mock_manifest.get_agent = MagicMock(return_value=mock_agent)

        recommender = AgentRecommender(manifest=mock_manifest)

        # Act
        with_prefix = recommender.verify_agent_exists("@code-developer")
        without_prefix = recommender.verify_agent_exists("code-developer")

        # Assert
        assert with_prefix is True
        assert without_prefix is True

    def test_detect_gaps_marks_agent_exists_false(self):
        """Test that gaps mark agent_exists=False when agent not found."""
        # Arrange
        subgoals = [
            Subgoal(
                id="sg-1",
                title="Task name",
                description="Task description",
                recommended_agent="@missing-agent",
            ),
        ]

        recommendations = {
            "sg-1": ("@missing-agent", 0.3),
        }

        mock_manifest = MagicMock()
        mock_manifest.agents = []
        mock_manifest.get_agent = MagicMock(return_value=None)

        recommender = AgentRecommender(manifest=mock_manifest, score_threshold=0.5)

        # Act
        gaps = recommender.detect_gaps(subgoals, recommendations)

        # Assert
        assert len(gaps) == 1
        assert gaps[0].agent_exists is False
        assert gaps[0].recommended_agent == "@missing-agent"
