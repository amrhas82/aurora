"""Tests for retrieve.py Store type compatibility."""

from unittest.mock import MagicMock, patch


def test_store_compatibility():
    """Test that retrieve phase accepts Store type and works with SQLiteStore.

    The retrieve phase should accept the base Store type for flexibility,
    but internally it uses MemoryRetriever which expects SQLiteStore.
    This test verifies the type conversion works correctly.
    """
    # Create a mock store that behaves like SQLiteStore
    mock_store = MagicMock()
    mock_store.db_path = ":memory:"

    # Mock MemoryRetriever - it's imported from aurora_cli.memory.retrieval inside the function
    with patch("aurora_cli.memory.retrieval.MemoryRetriever") as mock_retriever_class:
        mock_retriever = MagicMock()
        mock_retriever.has_indexed_memory.return_value = False
        mock_retriever_class.return_value = mock_retriever

        from aurora_soar.phases.retrieve import retrieve_context

        # This should not raise TypeError about Store vs SQLiteStore
        result = retrieve_context(
            query="test query",
            store=mock_store,
            complexity="simple",
        )

        # Verify MemoryRetriever was called with the store
        mock_retriever_class.assert_called_once()
        call_kwargs = mock_retriever_class.call_args[1]
        assert "store" in call_kwargs

        # Verify result structure
        assert "code_chunks" in result
        assert "reasoning_chunks" in result
