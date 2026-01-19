"""Unit tests for AgentRecommender class.

Tests agent capability matching for planning subgoals.
"""

from unittest.mock import Mock, patch

from aurora_cli.planning.agents import AgentRecommender
from aurora_cli.planning.models import Subgoal


class TestAgentRecommender:
    """Test suite for AgentRecommender."""

    def test_recommender_initialization(self) -> None:
        """Test AgentRecommender can be instantiated."""
        # Act
        recommender = AgentRecommender()

        # Assert
        assert recommender is not None
        assert hasattr(recommender, "recommend_for_subgoal")
        assert hasattr(recommender, "detect_gaps")
        assert hasattr(recommender, "get_fallback_agent")

    def test_recommender_initialization_with_manifest(self) -> None:
        """Test AgentRecommender can be instantiated with manifest."""
        # Arrange
        mock_manifest = Mock()

        # Act
        recommender = AgentRecommender(manifest=mock_manifest)

        # Assert
        assert recommender is not None
        assert recommender.manifest == mock_manifest

    def test_keyword_extraction(self) -> None:
        """Test keyword extraction from subgoal text."""
        # Arrange
        recommender = AgentRecommender()
        subgoal = Subgoal(
            id="sg-1",
            title="Implement OAuth2 authentication",
            description="Add OAuth2 authentication flow with token management",
            assigned_agent="@code-developer",
        )

        # Act
        keywords = recommender._extract_keywords(subgoal)

        # Assert
        assert "oauth2" in keywords or "oauth" in keywords
        assert "authentication" in keywords or "auth" in keywords
        # Stop words should be removed
        assert "the" not in keywords
        assert "a" not in keywords
        # Keywords should be lowercase
        assert all(k.islower() for k in keywords)

    @patch("aurora_cli.planning.agents.ManifestManager")
    def test_recommend_agent_high_score(self, mock_manager_class) -> None:
        """Test agent recommendation with high capability match."""
        # Arrange
        mock_agent1 = Mock()
        mock_agent1.id = "code-developer"
        mock_agent1.goal = "Full-stack development specialist"
        mock_agent1.when_to_use = "implementing features, coding, development"
        mock_agent1.capabilities = ["python", "javascript", "testing"]

        mock_agent2 = Mock()
        mock_agent2.id = "quality-assurance"
        mock_agent2.goal = "Quality assurance and testing specialist"
        mock_agent2.when_to_use = "testing, quality assurance, test architecture"
        mock_agent2.capabilities = ["testing", "quality", "pytest"]

        mock_manifest = Mock()
        mock_manifest.agents = [mock_agent1, mock_agent2]

        mock_manager = Mock()
        mock_manager.get_or_refresh.return_value = mock_manifest
        mock_manager_class.return_value = mock_manager

        recommender = AgentRecommender()
        subgoal = Subgoal(
            id="sg-1",
            title="Test architecture review",
            description="Review testing architecture and quality assurance processes",
            assigned_agent="@code-developer",
        )

        # Act
        agent_id, score = recommender.recommend_for_subgoal(subgoal)

        # Assert
        assert agent_id == "@quality-assurance"  # Better match for testing/quality
        assert score >= 0.5  # Above threshold

    @patch("aurora_cli.planning.agents.ManifestManager")
    def test_recommend_agent_no_match_fallback(self, mock_manager_class) -> None:
        """Test fallback agent when no good match found."""
        # Arrange
        mock_agent = Mock()
        mock_agent.id = "specialized-agent"
        mock_agent.goal = "Specialized Agent specialist"
        mock_agent.when_to_use = "very specific niche task"
        mock_agent.capabilities = ["niche", "specific"]

        mock_manifest = Mock()
        mock_manifest.agents = [mock_agent]

        mock_manager = Mock()
        mock_manager.get_or_refresh.return_value = mock_manifest
        mock_manager_class.return_value = mock_manager

        recommender = AgentRecommender()
        subgoal = Subgoal(
            id="sg-1",
            title="Implement OAuth2 authentication",
            description="Add OAuth2 authentication flow",
            assigned_agent="@code-developer",
        )

        # Act
        agent_id, score = recommender.recommend_for_subgoal(subgoal)

        # Assert
        assert agent_id == "@code-developer"  # Fallback
        assert score < 0.5  # Below threshold

    @patch("aurora_cli.planning.agents.ManifestManager")
    def test_detect_gaps(self, mock_manager_class) -> None:
        """Test gap detection when agent score is low."""
        # Arrange
        mock_agent = Mock()
        mock_agent.id = "code-developer"
        mock_agent.goal = "Full Stack Dev specialist"
        mock_agent.when_to_use = "general development"
        mock_agent.capabilities = ["python", "javascript"]

        mock_manifest = Mock()
        mock_manifest.agents = [mock_agent]
        mock_manifest.get_agent.return_value = None  # Agent doesn't exist

        mock_manager = Mock()
        mock_manager.get_or_refresh.return_value = mock_manifest
        mock_manager_class.return_value = mock_manager

        recommender = AgentRecommender()

        subgoals = [
            Subgoal(
                id="sg-1",
                title="Security audit",
                description="Perform comprehensive security audit",
                assigned_agent="@code-developer",
            ),
            Subgoal(
                id="sg-2",
                title="Implement feature",
                description="Implement new feature",
                assigned_agent="@code-developer",
            ),
        ]

        # Mock recommendations (low score for security audit)
        recommendations = {
            "sg-1": ("@security-expert", 0.3),  # Gap
            "sg-2": ("@code-developer", 0.8),  # Good match
        }

        # Act
        gaps = recommender.detect_gaps(subgoals, recommendations)

        # Assert
        assert len(gaps) == 1
        assert gaps[0].subgoal_id == "sg-1"
        assert gaps[0].ideal_agent == "@security-expert"
        assert gaps[0].assigned_agent == "@code-developer"  # Fallback
        assert gaps[0].ideal_agent_desc  # Has description

    @patch("aurora_cli.planning.agents.ManifestManager")
    def test_agent_existence_check(self, mock_manager_class) -> None:
        """Test agent existence verification."""
        # Arrange
        mock_agent = Mock()
        mock_agent.id = "code-developer"

        mock_manifest = Mock()
        mock_manifest.agents = [mock_agent]
        mock_manifest.get_agent.side_effect = lambda agent_id: (
            mock_agent if agent_id == "code-developer" else None
        )

        mock_manager = Mock()
        mock_manager.get_or_refresh.return_value = mock_manifest
        mock_manager_class.return_value = mock_manager

        recommender = AgentRecommender()

        # Act
        exists_dev = recommender.verify_agent_exists("@code-developer")
        exists_missing = recommender.verify_agent_exists("@missing-agent")

        # Assert
        assert exists_dev is True
        assert exists_missing is False

    @patch("aurora_cli.planning.agents.ManifestManager")
    def test_keyword_extraction_removes_stop_words(self, mock_manager_class) -> None:
        """Test that common stop words are removed from keywords."""
        # Arrange
        recommender = AgentRecommender()
        subgoal = Subgoal(
            id="sg-1",
            title="The implementation of the OAuth2 for the authentication",
            description="Add the OAuth2 authentication to the system",
            assigned_agent="@dev",
        )

        # Act
        keywords = recommender._extract_keywords(subgoal)

        # Assert - common stop words should be removed
        stop_words = ["the", "of", "for", "to", "a", "an", "is", "are"]
        for stop_word in stop_words:
            assert stop_word not in keywords

    def test_get_fallback_agent(self) -> None:
        """Test get_fallback_agent returns default."""
        # Arrange
        recommender = AgentRecommender()

        # Act
        fallback = recommender.get_fallback_agent()

        # Assert
        assert fallback == "@code-developer"

    @patch("aurora_cli.planning.agents.ManifestManager")
    def test_recommend_for_subgoal_manifest_unavailable(self, mock_manager_class) -> None:
        """Test graceful handling when manifest unavailable."""
        # Arrange
        mock_manager = Mock()
        mock_manager.get_or_refresh.side_effect = Exception("Manifest not found")
        mock_manager_class.return_value = mock_manager

        recommender = AgentRecommender()
        subgoal = Subgoal(
            id="sg-1",
            title="Test task",
            description="Test description for the task",
            assigned_agent="@dev",
        )

        # Act
        agent_id, score = recommender.recommend_for_subgoal(subgoal)

        # Assert - should return fallback gracefully
        assert agent_id == "@code-developer"
        assert score == 0.0

    @patch("aurora_cli.planning.agents.ManifestManager")
    def test_detect_gaps_empty_recommendations(self, mock_manager_class) -> None:
        """Test detect_gaps with empty recommendations."""
        # Arrange
        mock_manifest = Mock()
        mock_manifest.agents = []

        mock_manager = Mock()
        mock_manager.get_or_refresh.return_value = mock_manifest
        mock_manager_class.return_value = mock_manager

        recommender = AgentRecommender()
        subgoals = []
        recommendations = {}

        # Act
        gaps = recommender.detect_gaps(subgoals, recommendations)

        # Assert
        assert len(gaps) == 0
