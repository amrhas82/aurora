"""Unit tests for Phase 2: Context Retrieval."""

from unittest.mock import Mock

import pytest
from aurora.soar.phases.retrieve import (
    RETRIEVAL_BUDGETS,
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
        mock_chunks = [Mock(metadata={"chunk_type": "CodeChunk"}) for _ in range(3)]
        mock_store.retrieve_by_activation.return_value = mock_chunks

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
        mock_chunks = [Mock(metadata={"chunk_type": "CodeChunk"}) for _ in range(8)]
        mock_store.retrieve_by_activation.return_value = mock_chunks

        result = retrieve_context("test query", "MEDIUM", mock_store)

        # Should call store with MEDIUM budget (10)
        mock_store.retrieve_by_activation.assert_called_once_with(min_activation=0.0, limit=10)

        assert result["budget"] == 10
        assert result["total_retrieved"] == 8

    def test_retrieve_complex_query(self):
        """Test retrieval for COMPLEX query respects budget."""
        mock_store = Mock()
        mock_chunks = [Mock(metadata={"chunk_type": "CodeChunk"}) for _ in range(15)]
        mock_store.retrieve_by_activation.return_value = mock_chunks

        result = retrieve_context("test query", "COMPLEX", mock_store)

        mock_store.retrieve_by_activation.assert_called_once_with(min_activation=0.0, limit=15)

        assert result["budget"] == 15
        assert result["total_retrieved"] == 15

    def test_retrieve_critical_query(self):
        """Test retrieval for CRITICAL query respects budget."""
        mock_store = Mock()
        mock_chunks = [Mock(metadata={"chunk_type": "CodeChunk"}) for _ in range(20)]
        mock_store.retrieve_by_activation.return_value = mock_chunks

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
        code_chunk1 = Mock(metadata={"chunk_type": "CodeChunk"})
        code_chunk2 = Mock(metadata={"chunk_type": "CodeChunk"})
        reasoning_chunk1 = Mock(metadata={"chunk_type": "ReasoningChunk"})
        reasoning_chunk2 = Mock(metadata={"chunk_type": "ReasoningChunk"})

        mock_store.retrieve_by_activation.return_value = [
            code_chunk1,
            reasoning_chunk1,
            code_chunk2,
            reasoning_chunk2,
        ]

        result = retrieve_context("test query", "MEDIUM", mock_store)

        assert len(result["code_chunks"]) == 2
        assert len(result["reasoning_chunks"]) == 2
        assert result["total_retrieved"] == 4

    def test_retrieve_handles_unknown_chunk_type(self):
        """Test that unknown chunk types default to code_chunks."""
        mock_store = Mock()

        unknown_chunk = Mock(metadata={"chunk_type": "UnknownChunk"})
        mock_store.retrieve_by_activation.return_value = [unknown_chunk]

        result = retrieve_context("test query", "SIMPLE", mock_store)

        # Unknown types should go to code_chunks
        assert len(result["code_chunks"]) == 1
        assert len(result["reasoning_chunks"]) == 0

    def test_retrieve_handles_missing_chunk_type(self):
        """Test chunks without chunk_type metadata use class name."""
        mock_store = Mock()

        # Chunk with no chunk_type but class name contains "Code"
        chunk = Mock(metadata={})
        chunk.__class__.__name__ = "CodeChunk"

        mock_store.retrieve_by_activation.return_value = [chunk]

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
        mock_chunks = [Mock(metadata={"chunk_type": "CodeChunk"}) for _ in range(3)]
        mock_store.retrieve_by_activation.return_value = mock_chunks

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
