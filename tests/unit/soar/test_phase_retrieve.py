"""Unit tests for Phase 2: Context Retrieval."""

from unittest.mock import Mock

import pytest

from aurora_soar.phases.retrieve import (
    ACTIVATION_THRESHOLD,
    RETRIEVAL_BUDGETS,
    filter_by_activation,
    retrieve_context,
)


class TestRetrievalBudgets:
    """Tests for retrieval budget allocation."""

    def test_budget_simple(self):
        """Test SIMPLE complexity gets 5 chunks."""
        assert RETRIEVAL_BUDGETS["SIMPLE"] == 5

    def test_budget_medium(self):
        """Test MEDIUM complexity gets 10 chunks."""
        assert RETRIEVAL_BUDGETS["MEDIUM"] == 10

    def test_budget_complex(self):
        """Test COMPLEX complexity gets 15 chunks."""
        assert RETRIEVAL_BUDGETS["COMPLEX"] == 15

    def test_budget_critical(self):
        """Test CRITICAL complexity gets 20 chunks."""
        assert RETRIEVAL_BUDGETS["CRITICAL"] == 20


class TestRetrieveContext:
    """Tests for context retrieval function."""

    def test_retrieve_simple_query(self):
        """Test retrieval for SIMPLE query respects budget."""
        # Mock store
        mock_store = Mock()
        mock_chunks = [Mock(id=f"chunk{i}", metadata={"chunk_type": "CodeChunk"}) for i in range(3)]
        mock_store.retrieve_by_activation.return_value = mock_chunks
        mock_store.get_activation.return_value = 0.0  # All low activation

        result = retrieve_context("test query", "SIMPLE", mock_store)

        # Should call store with SIMPLE budget (5)
        mock_store.retrieve_by_activation.assert_called_once_with(min_activation=0.0, limit=5)

        assert result["total_retrieved"] == 3
        assert result["budget"] == 5
        assert result["budget_used"] == 3
        assert len(result["code_chunks"]) == 3
        assert len(result["reasoning_chunks"]) == 0

    def test_retrieve_medium_query(self):
        """Test retrieval for MEDIUM query respects budget."""
        mock_store = Mock()
        mock_chunks = [Mock(id=f"chunk{i}", metadata={"chunk_type": "CodeChunk"}) for i in range(8)]
        mock_store.retrieve_by_activation.return_value = mock_chunks
        mock_store.get_activation.return_value = 0.0

        result = retrieve_context("test query", "MEDIUM", mock_store)

        # Should call store with MEDIUM budget (10)
        mock_store.retrieve_by_activation.assert_called_once_with(min_activation=0.0, limit=10)

        assert result["budget"] == 10
        assert result["total_retrieved"] == 8

    def test_retrieve_complex_query(self):
        """Test retrieval for COMPLEX query respects budget."""
        mock_store = Mock()
        mock_chunks = [
            Mock(id=f"chunk{i}", metadata={"chunk_type": "CodeChunk"}) for i in range(15)
        ]
        mock_store.retrieve_by_activation.return_value = mock_chunks
        mock_store.get_activation.return_value = 0.0

        result = retrieve_context("test query", "COMPLEX", mock_store)

        mock_store.retrieve_by_activation.assert_called_once_with(min_activation=0.0, limit=15)

        assert result["budget"] == 15
        assert result["total_retrieved"] == 15

    def test_retrieve_critical_query(self):
        """Test retrieval for CRITICAL query respects budget."""
        mock_store = Mock()
        mock_chunks = [
            Mock(id=f"chunk{i}", metadata={"chunk_type": "CodeChunk"}) for i in range(20)
        ]
        mock_store.retrieve_by_activation.return_value = mock_chunks
        mock_store.get_activation.return_value = 0.0

        result = retrieve_context("test query", "CRITICAL", mock_store)

        mock_store.retrieve_by_activation.assert_called_once_with(min_activation=0.0, limit=20)

        assert result["budget"] == 20
        assert result["total_retrieved"] == 20

    def test_retrieve_unknown_complexity_defaults_to_medium(self):
        """Test unknown complexity defaults to MEDIUM budget."""
        mock_store = Mock()
        mock_store.retrieve_by_activation.return_value = []

        result = retrieve_context("test query", "UNKNOWN", mock_store)

        # Should default to MEDIUM (10)
        mock_store.retrieve_by_activation.assert_called_once_with(min_activation=0.0, limit=10)

        assert result["budget"] == 10

    def test_retrieve_separates_chunk_types(self):
        """Test that code and reasoning chunks are separated."""
        mock_store = Mock()

        # Create mixed chunks
        code_chunk1 = Mock(id="code1", metadata={"chunk_type": "CodeChunk"})
        code_chunk2 = Mock(id="code2", metadata={"chunk_type": "CodeChunk"})
        reasoning_chunk1 = Mock(id="reason1", metadata={"chunk_type": "ReasoningChunk"})
        reasoning_chunk2 = Mock(id="reason2", metadata={"chunk_type": "ReasoningChunk"})

        mock_store.retrieve_by_activation.return_value = [
            code_chunk1,
            reasoning_chunk1,
            code_chunk2,
            reasoning_chunk2,
        ]
        mock_store.get_activation.return_value = 0.0

        result = retrieve_context("test query", "MEDIUM", mock_store)

        assert len(result["code_chunks"]) == 2
        assert len(result["reasoning_chunks"]) == 2
        assert result["total_retrieved"] == 4

    def test_retrieve_handles_unknown_chunk_type(self):
        """Test that unknown chunk types default to code_chunks."""
        mock_store = Mock()

        unknown_chunk = Mock(id="unknown", metadata={"chunk_type": "UnknownChunk"})
        mock_store.retrieve_by_activation.return_value = [unknown_chunk]
        mock_store.get_activation.return_value = 0.0

        result = retrieve_context("test query", "SIMPLE", mock_store)

        # Unknown types should go to code_chunks
        assert len(result["code_chunks"]) == 1
        assert len(result["reasoning_chunks"]) == 0

    def test_retrieve_handles_missing_chunk_type(self):
        """Test chunks without chunk_type metadata use class name."""
        mock_store = Mock()

        # Chunk with no chunk_type but class name contains "Code"
        chunk = Mock(id="chunk1", metadata={})
        chunk.__class__.__name__ = "CodeChunk"

        mock_store.retrieve_by_activation.return_value = [chunk]
        mock_store.get_activation.return_value = 0.0

        result = retrieve_context("test query", "SIMPLE", mock_store)

        assert len(result["code_chunks"]) == 1
        assert len(result["reasoning_chunks"]) == 0

    def test_retrieve_includes_timing_metadata(self):
        """Test that retrieval includes timing information."""
        mock_store = Mock()
        mock_store.retrieve_by_activation.return_value = []

        result = retrieve_context("test query", "SIMPLE", mock_store)

        assert "retrieval_time_ms" in result
        assert isinstance(result["retrieval_time_ms"], float)
        assert result["retrieval_time_ms"] >= 0

    def test_retrieve_handles_store_error(self):
        """Test graceful handling of store errors."""
        mock_store = Mock()
        mock_store.retrieve_by_activation.side_effect = Exception("Store failure")

        result = retrieve_context("test query", "SIMPLE", mock_store)

        # Should return empty result with error
        assert result["total_retrieved"] == 0
        assert len(result["code_chunks"]) == 0
        assert len(result["reasoning_chunks"]) == 0
        assert "error" in result
        assert "Store failure" in result["error"]

    def test_retrieve_empty_store(self):
        """Test retrieval from empty store."""
        mock_store = Mock()
        mock_store.retrieve_by_activation.return_value = []

        result = retrieve_context("test query", "MEDIUM", mock_store)

        assert result["total_retrieved"] == 0
        assert result["budget"] == 10
        assert result["budget_used"] == 0
        assert len(result["code_chunks"]) == 0
        assert len(result["reasoning_chunks"]) == 0

    def test_retrieve_fewer_chunks_than_budget(self):
        """Test when store has fewer chunks than budget."""
        mock_store = Mock()
        # Only 3 chunks available but budget is 10
        mock_chunks = [Mock(id=f"chunk{i}", metadata={"chunk_type": "CodeChunk"}) for i in range(3)]
        mock_store.retrieve_by_activation.return_value = mock_chunks
        mock_store.get_activation.return_value = 0.0

        result = retrieve_context("test query", "MEDIUM", mock_store)

        assert result["budget"] == 10
        assert result["budget_used"] == 3  # Only got 3
        assert result["total_retrieved"] == 3


class TestBudgetAllocationLogic:
    """Tests specifically for budget allocation correctness."""

    @pytest.mark.parametrize(
        "complexity,expected_budget",
        [
            ("SIMPLE", 5),
            ("MEDIUM", 10),
            ("COMPLEX", 15),
            ("CRITICAL", 20),
        ],
    )
    def test_correct_budget_by_complexity(self, complexity, expected_budget):
        """Test each complexity level gets correct budget."""
        mock_store = Mock()
        mock_store.retrieve_by_activation.return_value = []

        result = retrieve_context("test", complexity, mock_store)

        assert result["budget"] == expected_budget
        # Verify the call was made with correct limit
        call_args = mock_store.retrieve_by_activation.call_args
        assert call_args[1]["limit"] == expected_budget

    def test_budget_progression_makes_sense(self):
        """Test that budgets increase appropriately with complexity."""
        assert RETRIEVAL_BUDGETS["SIMPLE"] < RETRIEVAL_BUDGETS["MEDIUM"]
        assert RETRIEVAL_BUDGETS["MEDIUM"] < RETRIEVAL_BUDGETS["COMPLEX"]
        assert RETRIEVAL_BUDGETS["COMPLEX"] < RETRIEVAL_BUDGETS["CRITICAL"]


class TestActivationFiltering:
    """Tests for activation threshold filtering (Task 3.46)."""

    def test_filter_by_activation_counts_high_quality(self):
        """Test filter_by_activation correctly counts chunks above threshold."""
        # Create chunks with different activation scores
        chunk1 = Mock(activation=0.5)  # High quality
        chunk2 = Mock(activation=0.7)  # High quality
        chunk3 = Mock(activation=0.2)  # Low quality
        chunks = [chunk1, chunk2, chunk3]

        all_chunks, high_quality_count = filter_by_activation(chunks)

        assert all_chunks == chunks  # All chunks preserved
        assert high_quality_count == 2  # Only 2 above 0.3

    def test_filter_by_activation_no_high_quality(self):
        """Test when all chunks are below threshold."""
        chunk1 = Mock(activation=0.1)
        chunk2 = Mock(activation=0.2)
        chunk3 = Mock(activation=0.0)
        chunks = [chunk1, chunk2, chunk3]

        all_chunks, high_quality_count = filter_by_activation(chunks)

        assert all_chunks == chunks
        assert high_quality_count == 0

    def test_filter_by_activation_all_high_quality(self):
        """Test when all chunks are above threshold."""
        chunk1 = Mock(activation=0.5)
        chunk2 = Mock(activation=0.8)
        chunk3 = Mock(activation=0.3)  # Exactly at threshold
        chunks = [chunk1, chunk2, chunk3]

        all_chunks, high_quality_count = filter_by_activation(chunks)

        assert all_chunks == chunks
        assert high_quality_count == 3  # All 3 are >= 0.3

    def test_filter_by_activation_boundary_case(self):
        """Test chunks exactly at the 0.3 threshold."""
        chunk1 = Mock(activation=0.3)  # Exactly at threshold
        chunk2 = Mock(activation=0.29)  # Just below
        chunks = [chunk1, chunk2]

        all_chunks, high_quality_count = filter_by_activation(chunks)

        assert high_quality_count == 1  # Only chunk1 qualifies

    def test_filter_by_activation_handles_none(self):
        """Test handling of chunks with None activation."""
        chunk1 = Mock(activation=None)
        chunk2 = Mock(activation=0.5)
        chunks = [chunk1, chunk2]

        all_chunks, high_quality_count = filter_by_activation(chunks)

        assert high_quality_count == 1  # Only chunk2 counts

    def test_filter_by_activation_empty_list(self):
        """Test filtering empty chunk list."""
        all_chunks, high_quality_count = filter_by_activation([])

        assert all_chunks == []
        assert high_quality_count == 0


class TestRetrieveWithActivationFiltering:
    """Tests for retrieve_context with high_quality_count field (Task 3.46)."""

    def test_retrieve_includes_high_quality_count(self):
        """Test that retrieve_context returns high_quality_count."""
        mock_store = Mock()

        # Create chunks with mixed activation scores
        chunk1 = Mock(id="chunk1", metadata={"chunk_type": "CodeChunk"}, activation=0.5)
        chunk2 = Mock(id="chunk2", metadata={"chunk_type": "CodeChunk"}, activation=0.2)
        chunk3 = Mock(id="chunk3", metadata={"chunk_type": "CodeChunk"}, activation=0.8)

        mock_store.retrieve_by_activation.return_value = [chunk1, chunk2, chunk3]
        mock_store.get_activation.side_effect = [0.5, 0.2, 0.8]  # Return respective activations

        result = retrieve_context("test query", "SIMPLE", mock_store)

        assert "high_quality_count" in result
        assert result["high_quality_count"] == 2  # chunk1 and chunk3 are >= 0.3
        assert result["total_retrieved"] == 3  # All 3 chunks returned

    def test_retrieve_all_high_quality_chunks(self):
        """Test when all retrieved chunks are high quality."""
        mock_store = Mock()

        chunk1 = Mock(id="chunk1", metadata={"chunk_type": "CodeChunk"}, activation=0.5)
        chunk2 = Mock(id="chunk2", metadata={"chunk_type": "CodeChunk"}, activation=0.6)
        chunk3 = Mock(id="chunk3", metadata={"chunk_type": "CodeChunk"}, activation=0.7)

        mock_store.retrieve_by_activation.return_value = [chunk1, chunk2, chunk3]
        mock_store.get_activation.side_effect = [0.5, 0.6, 0.7]

        result = retrieve_context("test query", "SIMPLE", mock_store)

        assert result["high_quality_count"] == 3
        assert result["high_quality_count"] == result["total_retrieved"]

    def test_retrieve_no_high_quality_chunks(self):
        """Test when all retrieved chunks are low quality."""
        mock_store = Mock()

        chunk1 = Mock(id="chunk1", metadata={"chunk_type": "CodeChunk"}, activation=0.1)
        chunk2 = Mock(id="chunk2", metadata={"chunk_type": "CodeChunk"}, activation=0.2)

        mock_store.retrieve_by_activation.return_value = [chunk1, chunk2]
        mock_store.get_activation.side_effect = [0.1, 0.2]

        result = retrieve_context("test query", "SIMPLE", mock_store)

        assert result["high_quality_count"] == 0
        assert result["total_retrieved"] == 2

    def test_retrieve_mixed_quality_chunks(self):
        """Test correct separation of high/low quality chunks."""
        mock_store = Mock()

        # 5 chunks: 2 high quality, 3 low quality
        chunks = [
            Mock(id="chunk1", metadata={"chunk_type": "CodeChunk"}, activation=0.5),  # High
            Mock(id="chunk2", metadata={"chunk_type": "CodeChunk"}, activation=0.1),  # Low
            Mock(id="chunk3", metadata={"chunk_type": "CodeChunk"}, activation=0.2),  # Low
            Mock(id="chunk4", metadata={"chunk_type": "CodeChunk"}, activation=0.8),  # High
            Mock(id="chunk5", metadata={"chunk_type": "CodeChunk"}, activation=0.25),  # Low
        ]

        mock_store.retrieve_by_activation.return_value = chunks
        mock_store.get_activation.side_effect = [0.5, 0.1, 0.2, 0.8, 0.25]

        result = retrieve_context("test query", "MEDIUM", mock_store)

        assert result["high_quality_count"] == 2
        assert result["total_retrieved"] == 5

    def test_retrieve_error_includes_high_quality_count_zero(self):
        """Test that error case includes high_quality_count = 0."""
        mock_store = Mock()
        mock_store.retrieve_by_activation.side_effect = Exception("Store error")

        result = retrieve_context("test query", "SIMPLE", mock_store)

        assert result["high_quality_count"] == 0
        assert result["total_retrieved"] == 0
        assert "error" in result
