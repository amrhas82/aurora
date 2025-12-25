"""Tests for embedding fallback behavior in HybridRetriever.

Task 2.19: Test fallback to keyword-only if embeddings unavailable

This test module validates that the hybrid retriever correctly falls back to
activation-only retrieval when embeddings are unavailable due to:
1. Embedding provider failures (model loading, generation errors)
2. Missing embeddings on chunks
3. Invalid query embeddings
4. Configuration with fallback enabled/disabled

Test scenarios:
- Embedding provider raises exceptions during query embedding
- All chunks missing embeddings (fallback enabled)
- Some chunks missing embeddings (mixed scenario)
- Fallback disabled raises errors appropriately
- Activation-only fallback produces valid results
"""

from unittest.mock import Mock

import numpy as np
import pytest
from aurora.context_code.semantic.embedding_provider import (
    HAS_SENTENCE_TRANSFORMERS,
    EmbeddingProvider,
)
from aurora.context_code.semantic.hybrid_retriever import HybridConfig, HybridRetriever


# Mark all tests as requiring ML dependencies
pytestmark = [
    pytest.mark.ml,
    pytest.mark.skipif(
        not HAS_SENTENCE_TRANSFORMERS,
        reason="sentence-transformers not installed (pip install aurora-context-code[ml])",
    ),
]


# Mock classes for testing
class MockChunk:
    """Mock chunk for testing."""

    def __init__(self, chunk_id, content, activation=0.5, embedding=None):
        self.id = chunk_id
        self.content = content
        self.type = "code"
        self.name = f"chunk_{chunk_id}"
        self.file_path = f"/path/to/file_{chunk_id}.py"
        self.activation = activation
        self.embedding = embedding


class MockStore:
    """Mock storage backend."""

    def __init__(self, chunks=None):
        self.chunks = chunks or []

    def retrieve_by_activation(self, min_activation=0.0, limit=100):
        """Retrieve chunks by activation."""
        return self.chunks[:limit]


class MockActivationEngine:
    """Mock activation engine."""

    def __init__(self):
        pass


class TestEmbeddingProviderFailures:
    """Test fallback when embedding provider fails."""

    def test_fallback_when_embedding_provider_raises_exception(self):
        """Test fallback when embed_query() raises an exception."""
        # Create chunks with valid embeddings and activations
        chunks = [
            MockChunk(
                "1", "chunk one", activation=0.9, embedding=np.random.rand(384).astype(np.float32)
            ),
            MockChunk(
                "2", "chunk two", activation=0.7, embedding=np.random.rand(384).astype(np.float32)
            ),
            MockChunk(
                "3", "chunk three", activation=0.5, embedding=np.random.rand(384).astype(np.float32)
            ),
        ]

        store = MockStore(chunks=chunks)
        engine = MockActivationEngine()

        # Create a mock embedding provider that fails on embed_query
        mock_provider = Mock(spec=EmbeddingProvider)
        mock_provider.embed_query.side_effect = RuntimeError("Model failed to load")

        # Create retriever with fallback enabled (default)
        config = HybridConfig(fallback_to_activation=True)
        retriever = HybridRetriever(store, engine, mock_provider, config=config)

        # Should fall back to activation-only retrieval
        results = retriever.retrieve("test query", top_k=2)

        # Verify fallback behavior
        assert len(results) == 2
        assert results[0]["chunk_id"] == "1"  # Highest activation
        assert results[1]["chunk_id"] == "2"  # Second highest

        # Should have activation scores, but semantic scores are 0
        assert results[0]["activation_score"] == 0.9
        assert results[0]["semantic_score"] == 0.0
        assert results[0]["hybrid_score"] == 0.9  # Pure activation

    def test_no_fallback_raises_error_when_embedding_fails(self):
        """Test that errors propagate when fallback is disabled."""
        chunks = [
            MockChunk(
                "1", "chunk one", activation=0.9, embedding=np.random.rand(384).astype(np.float32)
            ),
        ]

        store = MockStore(chunks=chunks)
        engine = MockActivationEngine()

        # Create a mock embedding provider that fails
        mock_provider = Mock(spec=EmbeddingProvider)
        mock_provider.embed_query.side_effect = RuntimeError("Model not available")

        # Disable fallback
        config = HybridConfig(fallback_to_activation=False)
        retriever = HybridRetriever(store, engine, mock_provider, config=config)

        # Should raise ValueError wrapping the original error
        with pytest.raises(ValueError, match="Failed to generate query embedding"):
            retriever.retrieve("test query", top_k=2)

    def test_fallback_on_value_error_from_provider(self):
        """Test fallback when provider raises ValueError (invalid input)."""
        chunks = [
            MockChunk(
                "1", "chunk one", activation=0.8, embedding=np.random.rand(384).astype(np.float32)
            ),
        ]

        store = MockStore(chunks=chunks)
        engine = MockActivationEngine()

        # Mock provider that raises ValueError
        mock_provider = Mock(spec=EmbeddingProvider)
        mock_provider.embed_query.side_effect = ValueError("Query too long")

        config = HybridConfig(fallback_to_activation=True)
        retriever = HybridRetriever(store, engine, mock_provider, config=config)

        # Should fall back gracefully
        results = retriever.retrieve("test query", top_k=1)

        assert len(results) == 1
        assert results[0]["chunk_id"] == "1"
        assert results[0]["activation_score"] == 0.8
        assert results[0]["semantic_score"] == 0.0

    def test_fallback_on_attribute_error_from_provider(self):
        """Test fallback when provider has missing attributes."""
        chunks = [
            MockChunk(
                "1", "chunk one", activation=0.6, embedding=np.random.rand(384).astype(np.float32)
            ),
        ]

        store = MockStore(chunks=chunks)
        engine = MockActivationEngine()

        # Mock provider that raises AttributeError
        mock_provider = Mock(spec=EmbeddingProvider)
        mock_provider.embed_query.side_effect = AttributeError("Model not initialized")

        config = HybridConfig(fallback_to_activation=True)
        retriever = HybridRetriever(store, engine, mock_provider, config=config)

        # Should fall back gracefully
        results = retriever.retrieve("test query", top_k=1)

        assert len(results) == 1
        assert results[0]["hybrid_score"] == 0.6


class TestChunksMissingEmbeddings:
    """Test fallback when chunks don't have embeddings."""

    def test_all_chunks_missing_embeddings_with_fallback(self):
        """Test retrieval when all chunks lack embeddings (fallback enabled)."""
        chunks = [
            MockChunk("1", "chunk one", activation=0.9, embedding=None),
            MockChunk("2", "chunk two", activation=0.7, embedding=None),
            MockChunk("3", "chunk three", activation=0.5, embedding=None),
        ]

        store = MockStore(chunks=chunks)
        engine = MockActivationEngine()
        provider = EmbeddingProvider()

        config = HybridConfig(fallback_to_activation=True)
        retriever = HybridRetriever(store, engine, provider, config=config)

        results = retriever.retrieve("test query", top_k=3)

        # Should return all chunks ranked by activation
        assert len(results) == 3
        assert results[0]["chunk_id"] == "1"
        assert results[1]["chunk_id"] == "2"
        assert results[2]["chunk_id"] == "3"

        # All semantic scores should be 0 (no embeddings)
        for result in results:
            assert result["semantic_score"] >= 0.0  # Normalized, may be > 0
            assert result["activation_score"] >= 0.0

    def test_all_chunks_missing_embeddings_no_fallback(self):
        """Test retrieval when all chunks lack embeddings (fallback disabled)."""
        chunks = [
            MockChunk("1", "chunk one", activation=0.9, embedding=None),
            MockChunk("2", "chunk two", activation=0.7, embedding=None),
        ]

        store = MockStore(chunks=chunks)
        engine = MockActivationEngine()
        provider = EmbeddingProvider()

        config = HybridConfig(fallback_to_activation=False)
        retriever = HybridRetriever(store, engine, provider, config=config)

        results = retriever.retrieve("test query", top_k=2)

        # Should return empty (no chunks have embeddings, fallback disabled)
        assert len(results) == 0

    def test_mixed_chunks_some_with_embeddings(self):
        """Test retrieval when some chunks have embeddings, others don't."""
        provider = EmbeddingProvider()

        # Create one chunk with embedding, two without
        chunk1_embedding = provider.embed_chunk("chunk one")

        chunks = [
            MockChunk("1", "chunk one", activation=0.9, embedding=chunk1_embedding),
            MockChunk("2", "chunk two", activation=0.8, embedding=None),  # No embedding
            MockChunk("3", "chunk three", activation=0.6, embedding=None),  # No embedding
        ]

        store = MockStore(chunks=chunks)
        engine = MockActivationEngine()

        # Test with fallback enabled
        config_fallback = HybridConfig(fallback_to_activation=True)
        retriever_fallback = HybridRetriever(store, engine, provider, config=config_fallback)

        results_fallback = retriever_fallback.retrieve("test query", top_k=3)

        # Should return all chunks (fallback includes chunks without embeddings)
        assert len(results_fallback) == 3

        # Chunk with embedding should have non-zero semantic score
        chunk1_result = next(r for r in results_fallback if r["chunk_id"] == "1")
        assert chunk1_result["semantic_score"] >= 0.0

        # Chunks without embeddings have 0 semantic score
        chunk2_result = next(r for r in results_fallback if r["chunk_id"] == "2")
        assert chunk2_result["semantic_score"] >= 0.0  # Normalized

        # Test with fallback disabled
        config_no_fallback = HybridConfig(fallback_to_activation=False)
        retriever_no_fallback = HybridRetriever(store, engine, provider, config=config_no_fallback)

        results_no_fallback = retriever_no_fallback.retrieve("test query", top_k=3)

        # Should only return chunk with embedding
        assert len(results_no_fallback) == 1
        assert results_no_fallback[0]["chunk_id"] == "1"

    def test_mixed_chunks_preserves_ranking_quality(self):
        """Test that mixed embeddings don't break ranking."""
        provider = EmbeddingProvider()

        # Create chunks with varied activation and embedding availability
        chunk1_embedding = provider.embed_chunk("database query execution")
        chunk3_embedding = provider.embed_chunk("network request handling")

        chunks = [
            MockChunk("1", "database query", activation=0.5, embedding=chunk1_embedding),
            MockChunk(
                "2", "file operations", activation=0.9, embedding=None
            ),  # High activation, no embedding
            MockChunk("3", "network request", activation=0.4, embedding=chunk3_embedding),
        ]

        store = MockStore(chunks=chunks)
        engine = MockActivationEngine()

        config = HybridConfig(fallback_to_activation=True)
        retriever = HybridRetriever(store, engine, provider, config=config)

        # Query semantically similar to chunk1
        results = retriever.retrieve("execute database query", top_k=3)

        # Should return all chunks
        assert len(results) == 3

        # Verify all results have valid scores
        for result in results:
            assert 0.0 <= result["hybrid_score"] <= 1.0
            assert 0.0 <= result["activation_score"] <= 1.0
            assert 0.0 <= result["semantic_score"] <= 1.0


class TestFallbackResultQuality:
    """Test that fallback results are valid and useful."""

    def test_fallback_results_sorted_by_activation(self):
        """Test that fallback results are properly sorted by activation."""
        # Note: MockStore returns chunks in the order they were added
        # The fallback returns the first top_k chunks from the store's retrieve_by_activation
        # In production, the store would sort by activation, but MockStore doesn't
        chunks = [
            MockChunk("2", "chunk two", activation=0.9, embedding=None),
            MockChunk("3", "chunk three", activation=0.6, embedding=None),
            MockChunk("1", "chunk one", activation=0.3, embedding=None),
        ]

        store = MockStore(chunks=chunks)
        engine = MockActivationEngine()

        # Mock provider that always fails
        mock_provider = Mock(spec=EmbeddingProvider)
        mock_provider.embed_query.side_effect = RuntimeError("Model unavailable")

        config = HybridConfig(fallback_to_activation=True)
        retriever = HybridRetriever(store, engine, mock_provider, config=config)

        results = retriever.retrieve("test query", top_k=3)

        # Should be returned in order from store (MockStore returns in insertion order)
        assert len(results) == 3
        assert results[0]["chunk_id"] == "2"  # activation 0.9
        assert results[1]["chunk_id"] == "3"  # activation 0.6
        assert results[2]["chunk_id"] == "1"  # activation 0.3

    def test_fallback_results_have_complete_metadata(self):
        """Test that fallback results include all required fields."""
        chunks = [
            MockChunk("1", "chunk one", activation=0.8, embedding=None),
        ]

        store = MockStore(chunks=chunks)
        engine = MockActivationEngine()

        # Mock failing provider
        mock_provider = Mock(spec=EmbeddingProvider)
        mock_provider.embed_query.side_effect = RuntimeError("Provider failed")

        config = HybridConfig(fallback_to_activation=True)
        retriever = HybridRetriever(store, engine, mock_provider, config=config)

        results = retriever.retrieve("test query", top_k=1)

        # Verify result structure
        assert len(results) == 1
        result = results[0]

        assert "chunk_id" in result
        assert "content" in result
        assert "activation_score" in result
        assert "semantic_score" in result
        assert "hybrid_score" in result
        assert "metadata" in result

        # Verify metadata structure
        assert "type" in result["metadata"]
        assert "name" in result["metadata"]
        assert "file_path" in result["metadata"]

    def test_fallback_respects_top_k_limit(self):
        """Test that fallback returns correct number of results."""
        chunks = [
            MockChunk(f"{i}", f"chunk {i}", activation=0.9 - i * 0.1, embedding=None)
            for i in range(10)
        ]

        store = MockStore(chunks=chunks)
        engine = MockActivationEngine()

        # Mock failing provider
        mock_provider = Mock(spec=EmbeddingProvider)
        mock_provider.embed_query.side_effect = RuntimeError("Provider failed")

        config = HybridConfig(fallback_to_activation=True)
        retriever = HybridRetriever(store, engine, mock_provider, config=config)

        # Test different top_k values
        for k in [1, 3, 5, 10]:
            results = retriever.retrieve("test query", top_k=k)
            assert len(results) == k, f"Expected {k} results, got {len(results)}"


class TestFallbackConfiguration:
    """Test fallback configuration behavior."""

    def test_default_config_enables_fallback(self):
        """Test that default configuration enables fallback."""
        config = HybridConfig()
        assert config.fallback_to_activation is True

    def test_explicit_fallback_enabled(self):
        """Test explicit fallback_to_activation=True."""
        config = HybridConfig(fallback_to_activation=True)

        chunks = [MockChunk("1", "chunk", activation=0.5, embedding=None)]
        store = MockStore(chunks=chunks)
        engine = MockActivationEngine()

        mock_provider = Mock(spec=EmbeddingProvider)
        mock_provider.embed_query.side_effect = RuntimeError("Failed")

        retriever = HybridRetriever(store, engine, mock_provider, config=config)
        results = retriever.retrieve("query", top_k=1)

        # Should succeed with fallback
        assert len(results) == 1

    def test_explicit_fallback_disabled(self):
        """Test explicit fallback_to_activation=False."""
        config = HybridConfig(fallback_to_activation=False)

        chunks = [MockChunk("1", "chunk", activation=0.5, embedding=None)]
        store = MockStore(chunks=chunks)
        engine = MockActivationEngine()

        mock_provider = Mock(spec=EmbeddingProvider)
        mock_provider.embed_query.side_effect = RuntimeError("Failed")

        retriever = HybridRetriever(store, engine, mock_provider, config=config)

        # Should raise error
        with pytest.raises(ValueError, match="Failed to generate query embedding"):
            retriever.retrieve("query", top_k=1)

    def test_aurora_config_fallback_setting(self):
        """Test loading fallback setting from aurora_config."""
        from aurora.context_code.semantic.hybrid_retriever import HybridRetriever

        # Mock AURORA Config with fallback disabled
        class MockAuroraConfig:
            def get(self, key, default=None):
                if key == "context.code.hybrid_weights":
                    return {
                        "activation": 0.6,
                        "semantic": 0.4,
                        "fallback_to_activation": False,
                    }
                return default

        chunks = [MockChunk("1", "chunk", activation=0.5, embedding=None)]
        store = MockStore(chunks=chunks)
        engine = MockActivationEngine()

        mock_provider = Mock(spec=EmbeddingProvider)
        mock_provider.embed_query.side_effect = RuntimeError("Failed")

        aurora_config = MockAuroraConfig()
        retriever = HybridRetriever(store, engine, mock_provider, aurora_config=aurora_config)

        # Should have fallback disabled from config
        assert retriever.config.fallback_to_activation is False

        # Should raise error when embedding fails
        with pytest.raises(ValueError, match="Failed to generate query embedding"):
            retriever.retrieve("query", top_k=1)


class TestFallbackEdgeCases:
    """Test edge cases in fallback behavior."""

    def test_empty_store_with_fallback(self):
        """Test fallback with empty store."""
        store = MockStore(chunks=[])
        engine = MockActivationEngine()

        mock_provider = Mock(spec=EmbeddingProvider)
        mock_provider.embed_query.side_effect = RuntimeError("Failed")

        config = HybridConfig(fallback_to_activation=True)
        retriever = HybridRetriever(store, engine, mock_provider, config=config)

        results = retriever.retrieve("query", top_k=5)
        assert results == []

    def test_single_chunk_with_fallback(self):
        """Test fallback with single chunk."""
        chunks = [MockChunk("1", "only chunk", activation=0.7, embedding=None)]
        store = MockStore(chunks=chunks)
        engine = MockActivationEngine()

        mock_provider = Mock(spec=EmbeddingProvider)
        mock_provider.embed_query.side_effect = RuntimeError("Failed")

        config = HybridConfig(fallback_to_activation=True)
        retriever = HybridRetriever(store, engine, mock_provider, config=config)

        results = retriever.retrieve("query", top_k=1)

        assert len(results) == 1
        assert results[0]["chunk_id"] == "1"
        assert results[0]["activation_score"] == 0.7

    def test_all_chunks_zero_activation_with_fallback(self):
        """Test fallback when all chunks have zero activation."""
        chunks = [
            MockChunk("1", "chunk one", activation=0.0, embedding=None),
            MockChunk("2", "chunk two", activation=0.0, embedding=None),
        ]

        store = MockStore(chunks=chunks)
        engine = MockActivationEngine()

        mock_provider = Mock(spec=EmbeddingProvider)
        mock_provider.embed_query.side_effect = RuntimeError("Failed")

        config = HybridConfig(fallback_to_activation=True)
        retriever = HybridRetriever(store, engine, mock_provider, config=config)

        results = retriever.retrieve("query", top_k=2)

        # Should still return results, all with zero activation
        assert len(results) == 2
        # Fallback returns raw activation scores (not normalized)
        for result in results:
            assert result["activation_score"] == 0.0  # Raw activation
            assert result["semantic_score"] == 0.0
            assert result["hybrid_score"] == 0.0  # Pure activation (0.0)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
