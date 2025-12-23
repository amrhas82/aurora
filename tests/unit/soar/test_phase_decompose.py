"""Unit tests for decompose phase."""

from unittest.mock import MagicMock, patch

import pytest
from aurora_reasoning.decompose import DecompositionResult
from aurora_reasoning.prompts.examples import Complexity

from aurora_soar.phases.decompose import (
    DecomposePhaseResult,
    _build_context_summary,
    _compute_query_hash,
    clear_cache,
    decompose_query,
)


class TestComputeQueryHash:
    """Tests for _compute_query_hash function."""

    def test_same_query_same_hash(self):
        """Test that same query produces same hash."""
        hash1 = _compute_query_hash("test query", "SIMPLE")
        hash2 = _compute_query_hash("test query", "SIMPLE")
        assert hash1 == hash2

    def test_different_query_different_hash(self):
        """Test that different query produces different hash."""
        hash1 = _compute_query_hash("test query 1", "SIMPLE")
        hash2 = _compute_query_hash("test query 2", "SIMPLE")
        assert hash1 != hash2

    def test_different_complexity_different_hash(self):
        """Test that different complexity produces different hash."""
        hash1 = _compute_query_hash("test query", "SIMPLE")
        hash2 = _compute_query_hash("test query", "MEDIUM")
        assert hash1 != hash2


class TestBuildContextSummary:
    """Tests for _build_context_summary function."""

    def test_with_code_chunks_only(self):
        """Test summary with only code chunks."""
        context = {
            "code_chunks": [{"id": 1}, {"id": 2}, {"id": 3}],
            "reasoning_chunks": [],
        }
        summary = _build_context_summary(context)
        assert "3 code chunks" in summary
        assert "Reasoning patterns" not in summary

    def test_with_reasoning_chunks_only(self):
        """Test summary with only reasoning chunks."""
        context = {
            "code_chunks": [],
            "reasoning_chunks": [{"id": 1}, {"id": 2}],
        }
        summary = _build_context_summary(context)
        assert "2 previous successful" in summary
        assert "code context" not in summary

    def test_with_both_chunk_types(self):
        """Test summary with both chunk types."""
        context = {
            "code_chunks": [{"id": 1}],
            "reasoning_chunks": [{"id": 2}],
        }
        summary = _build_context_summary(context)
        assert "1 code chunks" in summary
        assert "1 previous successful" in summary

    def test_with_no_chunks(self):
        """Test summary with no chunks."""
        context = {
            "code_chunks": [],
            "reasoning_chunks": [],
        }
        summary = _build_context_summary(context)
        assert "No specific context" in summary


class TestDecomposePhaseResult:
    """Tests for DecomposePhaseResult class."""

    def test_to_dict(self):
        """Test conversion to dictionary."""
        decomposition = DecompositionResult(
            goal="Test",
            subgoals=[],
            execution_order=[],
            expected_tools=[],
        )
        result = DecomposePhaseResult(
            decomposition=decomposition,
            cached=True,
            query_hash="abc123",
            timing_ms=150.5,
        )

        data = result.to_dict()
        assert data["cached"] is True
        assert data["query_hash"] == "abc123"
        assert data["timing_ms"] == 150.5


@patch("aurora_reasoning.decompose.decompose_query")
class TestDecomposeQuery:
    """Tests for decompose_query function."""

    @pytest.fixture
    def mock_llm_client(self):
        """Create mock LLM client."""
        return MagicMock()

    @pytest.fixture
    def sample_decomposition(self):
        """Create sample decomposition result."""
        return DecompositionResult(
            goal="Test goal",
            subgoals=[
                {
                    "description": "Test subgoal",
                    "suggested_agent": "code-analyzer",
                    "is_critical": True,
                    "depends_on": [],
                }
            ],
            execution_order=[{"phase": 1, "parallelizable": [0], "sequential": []}],
            expected_tools=["code_reader"],
        )

    def test_decompose_simple_query(self, mock_reasoning_decompose, mock_llm_client, sample_decomposition):
        """Test decomposing a simple query."""
        clear_cache()  # Clear cache before test
        mock_reasoning_decompose.return_value = sample_decomposition

        context = {
            "code_chunks": [{"id": 1}],
            "reasoning_chunks": [],
        }

        result = decompose_query(
            query="Test query",
            context=context,
            complexity="SIMPLE",
            llm_client=mock_llm_client,
        )

        assert result.decomposition.goal == "Test goal"
        assert result.cached is False
        assert result.timing_ms > 0

        # Verify reasoning function was called
        mock_reasoning_decompose.assert_called_once()
        call_args = mock_reasoning_decompose.call_args
        assert call_args.kwargs["query"] == "Test query"
        assert call_args.kwargs["complexity"] == Complexity.SIMPLE

    def test_decompose_with_caching(self, mock_reasoning_decompose, mock_llm_client, sample_decomposition):
        """Test that identical queries are cached."""
        clear_cache()
        mock_reasoning_decompose.return_value = sample_decomposition

        context = {"code_chunks": [], "reasoning_chunks": []}

        # First call - should call reasoning
        result1 = decompose_query(
            query="Test query",
            context=context,
            complexity="MEDIUM",
            llm_client=mock_llm_client,
        )
        assert result1.cached is False
        assert mock_reasoning_decompose.call_count == 1

        # Second call with same query - should use cache
        result2 = decompose_query(
            query="Test query",
            context=context,
            complexity="MEDIUM",
            llm_client=mock_llm_client,
        )
        assert result2.cached is True
        assert mock_reasoning_decompose.call_count == 1  # Not called again

    def test_cache_disabled_with_retry_feedback(self, mock_reasoning_decompose, mock_llm_client, sample_decomposition):
        """Test that cache is bypassed when retry feedback is provided."""
        clear_cache()
        mock_reasoning_decompose.return_value = sample_decomposition

        context = {"code_chunks": [], "reasoning_chunks": []}

        # First call - populate cache
        result1 = decompose_query(
            query="Test query",
            context=context,
            complexity="MEDIUM",
            llm_client=mock_llm_client,
        )
        assert result1.cached is False

        # Second call with retry feedback - should not use cache
        result2 = decompose_query(
            query="Test query",
            context=context,
            complexity="MEDIUM",
            llm_client=mock_llm_client,
            retry_feedback="Fix the issues",
        )
        assert result2.cached is False
        assert mock_reasoning_decompose.call_count == 2

    def test_cache_disabled_by_parameter(self, mock_reasoning_decompose, mock_llm_client, sample_decomposition):
        """Test that cache can be disabled via parameter."""
        clear_cache()
        mock_reasoning_decompose.return_value = sample_decomposition

        context = {"code_chunks": [], "reasoning_chunks": []}

        # First call
        result1 = decompose_query(
            query="Test query",
            context=context,
            complexity="MEDIUM",
            llm_client=mock_llm_client,
        )
        assert result1.cached is False

        # Second call with use_cache=False
        result2 = decompose_query(
            query="Test query",
            context=context,
            complexity="MEDIUM",
            llm_client=mock_llm_client,
            use_cache=False,
        )
        assert result2.cached is False
        assert mock_reasoning_decompose.call_count == 2

    def test_context_summary_passed(self, mock_reasoning_decompose, mock_llm_client, sample_decomposition):
        """Test that context summary is built and passed."""
        clear_cache()
        mock_reasoning_decompose.return_value = sample_decomposition

        context = {
            "code_chunks": [{"id": 1}, {"id": 2}],
            "reasoning_chunks": [{"id": 3}],
        }

        decompose_query(
            query="Test query",
            context=context,
            complexity="MEDIUM",
            llm_client=mock_llm_client,
        )

        call_args = mock_reasoning_decompose.call_args
        context_summary = call_args.kwargs["context_summary"]
        assert "2 code chunks" in context_summary
        assert "1 previous successful" in context_summary

    def test_available_agents_passed(self, mock_reasoning_decompose, mock_llm_client, sample_decomposition):
        """Test that available agents are passed through."""
        clear_cache()
        mock_reasoning_decompose.return_value = sample_decomposition

        context = {"code_chunks": [], "reasoning_chunks": []}
        agents = ["code-analyzer", "test-runner"]

        decompose_query(
            query="Test query",
            context=context,
            complexity="COMPLEX",
            llm_client=mock_llm_client,
            available_agents=agents,
        )

        call_args = mock_reasoning_decompose.call_args
        assert call_args.kwargs["available_agents"] == agents

    def test_retry_feedback_passed(self, mock_reasoning_decompose, mock_llm_client, sample_decomposition):
        """Test that retry feedback is passed through."""
        clear_cache()
        mock_reasoning_decompose.return_value = sample_decomposition

        context = {"code_chunks": [], "reasoning_chunks": []}
        feedback = "Fix the issues identified"

        decompose_query(
            query="Test query",
            context=context,
            complexity="MEDIUM",
            llm_client=mock_llm_client,
            retry_feedback=feedback,
        )

        call_args = mock_reasoning_decompose.call_args
        assert call_args.kwargs["retry_feedback"] == feedback

    def test_invalid_complexity(self, mock_reasoning_decompose, mock_llm_client, sample_decomposition):
        """Test handling of invalid complexity level."""
        clear_cache()
        context = {"code_chunks": [], "reasoning_chunks": []}

        with pytest.raises(ValueError, match="Invalid complexity level"):
            decompose_query(
                query="Test query",
                context=context,
                complexity="INVALID",
                llm_client=mock_llm_client,
            )

    def test_clear_cache_function(self, mock_reasoning_decompose, mock_llm_client, sample_decomposition):
        """Test that clear_cache() works."""
        clear_cache()
        mock_reasoning_decompose.return_value = sample_decomposition

        context = {"code_chunks": [], "reasoning_chunks": []}

        # First call - populate cache
        result1 = decompose_query(
            query="Test query",
            context=context,
            complexity="MEDIUM",
            llm_client=mock_llm_client,
        )
        assert result1.cached is False

        # Clear cache
        clear_cache()

        # Second call - should not use cache
        result2 = decompose_query(
            query="Test query",
            context=context,
            complexity="MEDIUM",
            llm_client=mock_llm_client,
        )
        assert result2.cached is False
        assert mock_reasoning_decompose.call_count == 2
