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

    @patch('aurora_cli.planning.decompose.decompose_query')
    def test_decompose_with_soar_success(self, mock_decompose_query):
        """Test successful SOAR decomposition."""
        # Setup mock SOAR response
        mock_result = Mock()
        mock_result.subgoals = [
            {"id": "sg-1", "title": "Setup auth", "description": "Configure auth system"},
            {"id": "sg-2", "title": "Add tests", "description": "Write unit tests"},
        ]
        mock_result.complexity = "MODERATE"
        mock_decompose_query.return_value = mock_result

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
