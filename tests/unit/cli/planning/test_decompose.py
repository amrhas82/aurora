"""Unit tests for PlanDecomposer class.

Tests the integration of SOAR decomposition into the planning workflow,
including context building, agent loading, and graceful fallback.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock

from aurora_cli.planning.decompose import PlanDecomposer
from aurora_cli.planning.models import Subgoal, Complexity


class TestPlanDecomposer:
    """Tests for PlanDecomposer class."""

    def test_decomposer_initialization(self):
        """Test that PlanDecomposer can be instantiated with config."""
        decomposer = PlanDecomposer()
        assert decomposer is not None
        assert hasattr(decomposer, 'decompose')
        assert hasattr(decomposer, '_build_context')
        assert hasattr(decomposer, '_call_soar')
        assert hasattr(decomposer, '_fallback_to_heuristics')

    def test_decomposer_initialization_with_config(self):
        """Test PlanDecomposer initialization with explicit config."""
        mock_config = Mock()
        decomposer = PlanDecomposer(config=mock_config)
        assert decomposer is not None
        # Config should be stored for later use
        assert decomposer.config == mock_config

    def test_decomposer_has_required_methods(self):
        """Verify all required methods exist on PlanDecomposer."""
        decomposer = PlanDecomposer()

        # Public interface
        assert callable(decomposer.decompose)

        # Internal helpers
        assert callable(decomposer._build_context)
        assert callable(decomposer._call_soar)
        assert callable(decomposer._fallback_to_heuristics)


class TestPlanDecomposerSOARIntegration:
    """Tests for SOAR decompose_query integration."""

    @patch('aurora_cli.planning.decompose.LLMClient')
    @patch('aurora_cli.planning.decompose.decompose_query')
    def test_decompose_with_soar_success(self, mock_decompose_query, mock_llm_client):
        """Test successful SOAR decomposition."""
        # Setup mock LLM client
        mock_llm_client.return_value = Mock()

        # Setup mock SOAR response with proper structure
        mock_decomposition = Mock()
        mock_decomposition.subgoals = [
            {"id": "sg-1", "title": "Setup auth", "description": "Configure auth system", "agent": "@full-stack-dev"},
            {"id": "sg-2", "title": "Add tests", "description": "Write unit tests", "agent": "@qa-test-architect"},
        ]

        mock_result = Mock()
        mock_result.decomposition = mock_decomposition
        mock_decompose_query.return_value = mock_result

        # Mock SOAR_AVAILABLE flag
        with patch('aurora_cli.planning.decompose.SOAR_AVAILABLE', True):
            decomposer = PlanDecomposer()
            subgoals, source = decomposer.decompose("Implement OAuth2 authentication")

            assert len(subgoals) == 2
            assert source == "soar"
            assert subgoals[0].id == "sg-1"
            assert subgoals[0].title == "Setup auth"
            assert mock_decompose_query.called

    @patch('aurora_cli.planning.decompose.decompose_query')
    def test_decompose_soar_unavailable_fallback(self, mock_decompose_query):
        """Test fallback to heuristics when SOAR raises ImportError."""
        mock_decompose_query.side_effect = ImportError("SOAR module not found")

        decomposer = PlanDecomposer()
        subgoals, source = decomposer.decompose("Implement feature")

        assert source == "heuristic"
        # Should still return valid subgoals from heuristic
        assert isinstance(subgoals, list)

    @patch('aurora_cli.planning.decompose.decompose_query')
    def test_decompose_soar_timeout(self, mock_decompose_query):
        """Test timeout handling for SOAR calls."""
        mock_decompose_query.side_effect = TimeoutError("SOAR call timed out")

        decomposer = PlanDecomposer()
        subgoals, source = decomposer.decompose("Complex task")

        assert source == "heuristic"
        assert isinstance(subgoals, list)

    def test_decompose_caching(self):
        """Test that decomposition results are cached."""
        decomposer = PlanDecomposer()

        # First call - should hit SOAR (or heuristic)
        with patch('aurora_cli.planning.decompose.decompose_query') as mock_soar:
            mock_result = Mock()
            mock_result.subgoals = [{"id": "sg-1", "title": "Task 1", "description": "Desc"}]
            mock_result.complexity = "SIMPLE"
            mock_soar.return_value = mock_result

            subgoals1, source1 = decomposer.decompose("Test goal", Complexity.SIMPLE)

        # Second call with same goal - should use cache
        with patch('aurora_cli.planning.decompose.decompose_query') as mock_soar2:
            subgoals2, source2 = decomposer.decompose("Test goal", Complexity.SIMPLE)

            # SOAR should not be called again
            assert not mock_soar2.called

        # Results should be identical
        assert len(subgoals1) == len(subgoals2)
        assert source1 == source2


class TestContextSummaryBuilding:
    """Tests for context summary building (FR-2.2)."""

    def test_build_context_summary_with_code_chunks(self):
        """Test context summary format with code chunks."""
        decomposer = PlanDecomposer()

        context = {
            "code_chunks": [{"file": "a.py"}, {"file": "b.py"}, {"file": "c.py"}],
            "reasoning_chunks": [],
        }

        summary = decomposer._build_context_summary(context)

        assert "Available code context: 3 code chunks" in summary
        assert "covering relevant functions, classes, and modules" in summary
        assert len(summary) <= 500  # Limit to 500 characters

    def test_build_context_summary_with_reasoning_chunks(self):
        """Test context summary format with reasoning chunks."""
        decomposer = PlanDecomposer()

        context = {
            "code_chunks": [],
            "reasoning_chunks": [{"pattern": "decomp1"}, {"pattern": "decomp2"}],
        }

        summary = decomposer._build_context_summary(context)

        assert "Reasoning patterns: 2 previous successful" in summary
        assert "decompositions and solutions" in summary
        assert len(summary) <= 500

    def test_build_context_summary_with_both_chunk_types(self):
        """Test context summary with both code and reasoning chunks."""
        decomposer = PlanDecomposer()

        context = {
            "code_chunks": [{"file": "a.py"}, {"file": "b.py"}],
            "reasoning_chunks": [{"pattern": "decomp1"}],
        }

        summary = decomposer._build_context_summary(context)

        assert "Available code context: 2 code chunks" in summary
        assert "Reasoning patterns: 1 previous successful" in summary
        assert len(summary) <= 500

    def test_build_context_summary_empty(self):
        """Test context summary with no chunks returns special message."""
        decomposer = PlanDecomposer()

        context = {
            "code_chunks": [],
            "reasoning_chunks": [],
        }

        summary = decomposer._build_context_summary(context)

        assert summary == "No indexed context available. Using LLM general knowledge."

    def test_build_context_summary_missing_keys(self):
        """Test context summary handles missing keys gracefully."""
        decomposer = PlanDecomposer()

        # Empty context dict
        summary = decomposer._build_context_summary({})

        assert summary == "No indexed context available. Using LLM general knowledge."


class TestAvailableAgentsList:
    """Tests for available agents list loading (FR-2.3)."""

    @patch('aurora_cli.planning.decompose.ManifestManager')
    def test_load_available_agents(self, mock_manager_class):
        """Test loading available agents from manifest."""
        # Setup mock manifest with agents
        mock_agent1 = Mock()
        mock_agent1.id = "full-stack-dev"
        mock_agent2 = Mock()
        mock_agent2.id = "qa-test-architect"
        mock_agent3 = Mock()
        mock_agent3.id = "holistic-architect"

        mock_manifest = Mock()
        mock_manifest.agents = [mock_agent1, mock_agent2, mock_agent3]

        mock_manager = Mock()
        mock_manager.get_or_refresh.return_value = mock_manifest
        mock_manager_class.return_value = mock_manager

        decomposer = PlanDecomposer()
        agents = decomposer._load_available_agents()

        assert agents is not None
        assert "@full-stack-dev" in agents
        assert "@qa-test-architect" in agents
        assert "@holistic-architect" in agents
        assert len(agents) == 3

    @patch('aurora_cli.planning.decompose.ManifestManager')
    def test_load_available_agents_manifest_unavailable(self, mock_manager_class):
        """Test graceful handling when manifest unavailable."""
        # Simulate manifest load failure
        mock_manager = Mock()
        mock_manager.get_or_refresh.side_effect = Exception("Manifest not found")
        mock_manager_class.return_value = mock_manager

        decomposer = PlanDecomposer()
        agents = decomposer._load_available_agents()

        # Should return None gracefully
        assert agents is None

    @patch('aurora_cli.planning.decompose.ManifestManager')
    def test_load_available_agents_empty_manifest(self, mock_manager_class):
        """Test handling of empty manifest."""
        mock_manifest = Mock()
        mock_manifest.agents = []

        mock_manager = Mock()
        mock_manager.get_or_refresh.return_value = mock_manifest
        mock_manager_class.return_value = mock_manager

        decomposer = PlanDecomposer()
        agents = decomposer._load_available_agents()

        assert agents == []


class TestComplexityMapping:
    """Tests for complexity assessment and mapping (FR-2.4)."""

    @patch('aurora_cli.planning.decompose.decompose_query')
    @patch('aurora_cli.planning.decompose.LLMClient')
    def test_complexity_passed_to_soar(self, mock_llm_client, mock_decompose_query):
        """Test that complexity is correctly passed to SOAR."""
        # Setup mock
        mock_llm_client.return_value = Mock()
        mock_decomposition = Mock()
        mock_decomposition.subgoals = []
        mock_result = Mock()
        mock_result.decomposition = mock_decomposition
        mock_decompose_query.return_value = mock_result

        decomposer = PlanDecomposer()

        # Test each complexity level
        for complexity in [Complexity.SIMPLE, Complexity.MODERATE, Complexity.COMPLEX]:
            decomposer.decompose("Test goal", complexity=complexity)

            # Verify SOAR was called with correct complexity string
            call_args = mock_decompose_query.call_args
            assert call_args[1]['complexity'] == complexity.value

    def test_complexity_fallback_heuristic(self):
        """Test that heuristic decomposition uses complexity correctly."""
        decomposer = PlanDecomposer()

        # Test SIMPLE complexity
        subgoals_simple = decomposer._fallback_to_heuristics("Test goal", Complexity.SIMPLE)
        assert len(subgoals_simple) == 3  # Plan, Implement, Test

        # Test COMPLEX complexity
        subgoals_complex = decomposer._fallback_to_heuristics("Test goal", Complexity.COMPLEX)
        assert len(subgoals_complex) == 4  # Plan, Implement, Test, Document

        # Verify the extra documentation step for COMPLEX
        doc_subgoal = [sg for sg in subgoals_complex if "document" in sg.title.lower()]
        assert len(doc_subgoal) == 1

    @patch('aurora_cli.planning.decompose.decompose_query')
    @patch('aurora_cli.planning.decompose.LLMClient')
    def test_complexity_enum_value_mapping(self, mock_llm_client, mock_decompose_query):
        """Test that Complexity enum values map correctly to SOAR strings."""
        # Setup mock
        mock_llm_client.return_value = Mock()
        mock_decomposition = Mock()
        mock_decomposition.subgoals = []
        mock_result = Mock()
        mock_result.decomposition = mock_decomposition
        mock_decompose_query.return_value = mock_result

        decomposer = PlanDecomposer()

        # Verify enum values are lowercase strings (SOAR accepts both, but we use lowercase)
        assert Complexity.SIMPLE.value == "simple"
        assert Complexity.MODERATE.value == "moderate"
        assert Complexity.COMPLEX.value == "complex"

        # Test that decompose handles the mapping
        decomposer.decompose("Test", Complexity.SIMPLE)
        assert mock_decompose_query.called


class TestFileResolutionIntegration:
    """Tests for file path resolution integration (Task 3.6)."""

    @patch('aurora_cli.planning.decompose.FilePathResolver')
    @patch('aurora_cli.planning.decompose.decompose_query')
    @patch('aurora_cli.planning.decompose.LLMClient')
    def test_file_resolution_called_for_subgoals(
        self, mock_llm_client, mock_decompose_query, mock_resolver_class
    ):
        """Test that file resolution is called for each subgoal."""
        # Setup mocks
        mock_llm_client.return_value = Mock()

        # Mock SOAR decomposition with 2 subgoals
        mock_decomposition = Mock()
        mock_decomposition.subgoals = [
            {
                "id": "sg-1",
                "title": "Implement auth",
                "description": "Add authentication",
                "agent": "@full-stack-dev",
                "dependencies": [],
            },
            {
                "id": "sg-2",
                "title": "Add tests",
                "description": "Write tests for auth",
                "agent": "@qa-test-architect",
                "dependencies": ["sg-1"],
            },
        ]
        mock_result = Mock()
        mock_result.decomposition = mock_decomposition
        mock_decompose_query.return_value = mock_result

        # Mock file resolver
        from aurora_cli.planning.models import FileResolution
        mock_resolver = Mock()
        mock_resolver.resolve_for_subgoal.return_value = [
            FileResolution(
                path="src/auth.py",
                line_start=10,
                line_end=50,
                confidence=0.9,
            )
        ]
        mock_resolver.has_indexed_memory.return_value = True
        mock_resolver_class.return_value = mock_resolver

        decomposer = PlanDecomposer()

        # Act
        subgoals, file_resolutions, source = decomposer.decompose_with_files("Test goal")

        # Assert
        assert len(subgoals) == 2
        assert source == "soar"
        # File resolver should have been called for each subgoal
        assert mock_resolver.resolve_for_subgoal.call_count == 2
        # File resolutions should be keyed by subgoal ID
        assert "sg-1" in file_resolutions
        assert "sg-2" in file_resolutions
        assert len(file_resolutions["sg-1"]) == 1
        assert file_resolutions["sg-1"][0].path == "src/auth.py"

    @patch('aurora_cli.planning.decompose.FilePathResolver')
    def test_file_resolution_graceful_degradation(self, mock_resolver_class):
        """Test graceful degradation when memory not indexed."""
        # Mock file resolver with no indexed memory
        mock_resolver = Mock()
        mock_resolver.has_indexed_memory.return_value = False
        mock_resolver.resolve_for_subgoal.return_value = []
        mock_resolver_class.return_value = mock_resolver

        decomposer = PlanDecomposer()

        # Use heuristic fallback
        subgoals, file_resolutions, source = decomposer.decompose_with_files(
            "Test goal", complexity=Complexity.SIMPLE
        )

        # Assert - should still succeed
        assert len(subgoals) == 3
        assert source == "heuristic"
        # No file resolutions since memory not indexed
        assert len(file_resolutions) == 0 or all(
            len(files) == 0 for files in file_resolutions.values()
        )


class TestAgentRecommendationIntegration:
    """Tests for agent recommendation integration (Task 4.7)."""

    @patch('aurora_cli.planning.decompose.AgentRecommender')
    @patch('aurora_cli.planning.decompose.decompose_query')
    @patch('aurora_cli.planning.decompose.LLMClient')
    def test_agent_recommendation_called_for_subgoals(
        self, mock_llm_client, mock_decompose_query, mock_recommender_class
    ):
        """Test that agent recommendation is called for each subgoal."""
        # Setup mocks
        mock_llm_client.return_value = Mock()

        # Mock SOAR decomposition with 2 subgoals
        mock_decomposition = Mock()
        mock_decomposition.subgoals = [
            {
                "id": "sg-1",
                "title": "Implement auth",
                "description": "Add authentication",
                "agent": "@full-stack-dev",
                "dependencies": [],
            },
            {
                "id": "sg-2",
                "title": "Add tests",
                "description": "Write tests for auth",
                "agent": "@qa-test-architect",
                "dependencies": ["sg-1"],
            },
        ]
        mock_result = Mock()
        mock_result.decomposition = mock_decomposition
        mock_decompose_query.return_value = mock_result

        # Mock agent recommender
        from aurora_cli.planning.models import AgentGap
        mock_recommender = Mock()
        mock_recommender.recommend_for_subgoal.side_effect = [
            ("@full-stack-dev", 0.9),  # sg-1
            ("@qa-test-architect", 0.8),  # sg-2
        ]
        mock_recommender.verify_agent_exists.return_value = True
        mock_recommender.detect_gaps.return_value = []  # No gaps
        mock_recommender.get_fallback_agent.return_value = "@full-stack-dev"
        mock_recommender_class.return_value = mock_recommender

        decomposer = PlanDecomposer()

        # Act
        subgoals, agent_recommendations, agent_gaps, source = decomposer.decompose_with_agents("Test goal")

        # Assert
        assert len(subgoals) == 2
        assert source == "soar"
        # Agent recommender should have been called for each subgoal
        assert mock_recommender.recommend_for_subgoal.call_count == 2
        # Agent recommendations should be keyed by subgoal ID
        assert "sg-1" in agent_recommendations
        assert "sg-2" in agent_recommendations
        assert agent_recommendations["sg-1"] == ("@full-stack-dev", 0.9)
        assert agent_recommendations["sg-2"] == ("@qa-test-architect", 0.8)
        # Gaps should be empty for high-scoring matches
        assert len(agent_gaps) == 0

    @patch('aurora_cli.planning.decompose.AgentRecommender')
    def test_agent_gaps_detected(self, mock_recommender_class):
        """Test that agent gaps are detected for low-scoring matches."""
        # Mock agent recommender with low scores
        from aurora_cli.planning.models import AgentGap
        mock_gap = AgentGap(
            subgoal_id="sg-1",
            recommended_agent="@specialized-agent",
            agent_exists=False,
            fallback="@full-stack-dev",
            suggested_capabilities=["specialized", "task"],
        )

        mock_recommender = Mock()
        mock_recommender.recommend_for_subgoal.return_value = ("@specialized-agent", 0.3)
        mock_recommender.verify_agent_exists.return_value = False
        mock_recommender.detect_gaps.return_value = [mock_gap]
        mock_recommender.get_fallback_agent.return_value = "@full-stack-dev"
        mock_recommender_class.return_value = mock_recommender

        decomposer = PlanDecomposer()

        # Use heuristic fallback
        subgoals, agent_recommendations, agent_gaps, source = decomposer.decompose_with_agents(
            "Test goal", complexity=Complexity.SIMPLE
        )

        # Assert
        assert len(subgoals) == 3
        assert source == "heuristic"
        # Should have detected gaps
        assert len(agent_gaps) == 1
        assert agent_gaps[0].subgoal_id == "sg-1"
        assert agent_gaps[0].agent_exists is False
        assert agent_gaps[0].fallback == "@full-stack-dev"
