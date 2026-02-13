"""Tests for HybridRetriever class.

Tests include:
- Hybrid scoring with configurable weights
- Chunk-type-aware weight selection (code vs KB)
- Validation of weight constraints (sum to 1.0, range [0, 1])
- Fallback behavior when embeddings unavailable
- Integration with activation engine and embedding provider
"""

import pytest

from aurora_context_code.semantic.embedding_provider import EmbeddingProvider
from aurora_context_code.semantic.hybrid_retriever import (
    HybridConfig,
    HybridRetriever,
    _CODE_WEIGHTS,
    _KB_WEIGHTS,
)


# Mock classes for testing
class MockChunk:
    """Mock chunk for testing."""

    def __init__(self, chunk_id, content, activation=0.5, embeddings=None):
        self.id = chunk_id
        self.content = content
        self.type = "code"
        self.name = f"chunk_{chunk_id}"
        self.file_path = f"/path/to/file_{chunk_id}.py"
        self.activation = activation
        self.embeddings = embeddings


class MockStore:
    """Mock storage backend."""

    def __init__(self, chunks=None):
        self.chunks = chunks or []

    def retrieve_by_activation(self, _min_activation=0.0, limit=100):
        """Retrieve chunks by activation."""
        return self.chunks[:limit]


class MockActivationEngine:
    """Mock activation engine."""

    def __init__(self):
        pass



class TestHybridConfig:
    """Test HybridConfig validation."""

    def test_default_config(self):
        """Test default configuration values (tri-hybrid mode)."""
        config = HybridConfig()

        # Tri-hybrid defaults: 30% BM25, 30% activation, 40% semantic
        assert config.bm25_weight == 0.3
        assert config.activation_weight == 0.3
        assert config.semantic_weight == 0.4
        assert config.activation_top_k == 500  # Increased from 100 for better recall
        assert config.fallback_to_activation is True
        # Cache defaults
        assert config.enable_query_cache is True
        assert config.query_cache_size == 100
        assert config.query_cache_ttl_seconds == 1800

    def test_custom_weights(self):
        """Test custom weight configuration (dual-hybrid mode)."""
        config = HybridConfig(
            bm25_weight=0.0,
            activation_weight=0.7,
            semantic_weight=0.3,
        )

        assert config.bm25_weight == 0.0
        assert config.activation_weight == 0.7
        assert config.semantic_weight == 0.3

    def test_weights_must_sum_to_one(self):
        """Test that weights must sum to 1.0."""
        with pytest.raises(ValueError, match="Weights must sum to 1.0"):
            HybridConfig(bm25_weight=0.3, activation_weight=0.5, semantic_weight=0.6)

    def test_weights_must_be_in_range(self):
        """Test that weights must be in [0, 1]."""
        with pytest.raises(ValueError, match="activation_weight must be in"):
            HybridConfig(bm25_weight=0.0, activation_weight=1.5, semantic_weight=-0.5)

    def test_top_k_must_be_positive(self):
        """Test that top_k must be >= 1."""
        with pytest.raises(ValueError, match="activation_top_k must be >= 1"):
            HybridConfig(activation_top_k=0)

    def test_weights_close_to_one(self):
        """Test that weights can have small floating point errors."""
        # Should not raise (1e-9 tolerance)
        config = HybridConfig(
            bm25_weight=0.0,
            activation_weight=0.6000000001,
            semantic_weight=0.3999999999,
        )
        assert config.activation_weight == 0.6000000001


class TestHybridRetrieverInit:
    """Test HybridRetriever initialization and configuration loading."""

    def test_default_initialization(self):
        """Test initialization with default configuration (tri-hybrid mode)."""
        store = MockStore()
        engine = MockActivationEngine()
        provider = EmbeddingProvider()

        retriever = HybridRetriever(store, engine, provider)

        # Tri-hybrid defaults
        assert retriever.config.bm25_weight == 0.3
        assert retriever.config.activation_weight == 0.3
        assert retriever.config.semantic_weight == 0.4
        assert retriever.config.activation_top_k == 500
        # Cache should be enabled by default
        assert retriever._query_cache is not None

    def test_explicit_config_initialization(self):
        """Test initialization with explicit HybridConfig (dual-hybrid mode)."""
        store = MockStore()
        engine = MockActivationEngine()
        provider = EmbeddingProvider()
        config = HybridConfig(
            bm25_weight=0.0,
            activation_weight=0.7,
            semantic_weight=0.3,
            activation_top_k=50,
        )

        retriever = HybridRetriever(store, engine, provider, config=config)

        assert retriever.config.bm25_weight == 0.0
        assert retriever.config.activation_weight == 0.7
        assert retriever.config.semantic_weight == 0.3
        assert retriever.config.activation_top_k == 50



class TestHybridRetrieverRetrieve:
    """Test HybridRetriever retrieve() method."""

    def test_retrieve_validates_query(self):
        """Test that retrieve validates query parameter."""
        store = MockStore()
        engine = MockActivationEngine()
        provider = EmbeddingProvider()

        retriever = HybridRetriever(store, engine, provider)

        with pytest.raises(ValueError, match="Query cannot be empty"):
            retriever.retrieve("", top_k=5)

        with pytest.raises(ValueError, match="Query cannot be empty"):
            retriever.retrieve("   ", top_k=5)

    def test_retrieve_validates_top_k(self):
        """Test that retrieve validates top_k parameter."""
        store = MockStore()
        engine = MockActivationEngine()
        provider = EmbeddingProvider()

        retriever = HybridRetriever(store, engine, provider)

        with pytest.raises(ValueError, match="top_k must be >= 1"):
            retriever.retrieve("test query", top_k=0)

class TestHybridRetrieverNormalization:
    """Test score normalization."""

    def test_normalize_scores_basic(self):
        """Test basic score normalization."""
        store = MockStore()
        engine = MockActivationEngine()
        provider = EmbeddingProvider()

        retriever = HybridRetriever(store, engine, provider)

        scores = [0.2, 0.5, 0.8, 1.0]
        normalized = retriever._normalize_scores(scores)

        assert len(normalized) == 4
        assert min(normalized) == 0.0  # Min maps to 0
        assert max(normalized) == 1.0  # Max maps to 1
        assert all(0.0 <= s <= 1.0 for s in normalized)

    def test_normalize_scores_equal(self):
        """Test normalization with all equal scores preserves original values.

        When all scores are equal, normalization should preserve the original
        values rather than mapping them all to 1.0. This prevents misleading
        results where [0.0, 0.0, 0.0] becomes [1.0, 1.0, 1.0].
        """
        store = MockStore()
        engine = MockActivationEngine()
        provider = EmbeddingProvider()

        retriever = HybridRetriever(store, engine, provider)

        # Test with non-zero equal scores
        scores = [0.5, 0.5, 0.5, 0.5]
        normalized = retriever._normalize_scores(scores)
        assert normalized == [0.5, 0.5, 0.5, 0.5]

        # Test with zero scores - should NOT inflate to 1.0
        zero_scores = [0.0, 0.0, 0.0]
        zero_normalized = retriever._normalize_scores(zero_scores)
        assert zero_normalized == [0.0, 0.0, 0.0]

    def test_normalize_scores_empty(self):
        """Test normalization with empty list."""
        store = MockStore()
        engine = MockActivationEngine()
        provider = EmbeddingProvider()

        retriever = HybridRetriever(store, engine, provider)

        normalized = retriever._normalize_scores([])
        assert normalized == []


class TestChunkTypeAwareWeights:
    """Test chunk-type-aware hybrid scoring weights."""

    def test_code_chunks_use_code_weights(self):
        """Code chunks should use BM25-heavy weights."""
        assert _CODE_WEIGHTS == (0.5, 0.3, 0.2)

        # Simulate scoring: BM25=1.0, activation=0.5, semantic=0.5
        bm25_w, act_w, sem_w = _CODE_WEIGHTS
        score = bm25_w * 1.0 + act_w * 0.5 + sem_w * 0.5
        assert score == pytest.approx(0.75)

    def test_kb_chunks_use_kb_weights(self):
        """KB chunks should use semantic-heavy weights."""
        assert _KB_WEIGHTS == (0.3, 0.3, 0.4)

        # Same raw scores but different weights
        bm25_w, act_w, sem_w = _KB_WEIGHTS
        score = bm25_w * 1.0 + act_w * 0.5 + sem_w * 0.5
        assert score == pytest.approx(0.65)

    def test_code_chunk_scores_higher_on_bm25(self):
        """Code chunk should score higher than KB when BM25 dominates."""
        # BM25 high, semantic low — code weights should win
        bm25, activation, semantic = 0.9, 0.5, 0.1

        code_score = _CODE_WEIGHTS[0] * bm25 + _CODE_WEIGHTS[1] * activation + _CODE_WEIGHTS[2] * semantic
        kb_score = _KB_WEIGHTS[0] * bm25 + _KB_WEIGHTS[1] * activation + _KB_WEIGHTS[2] * semantic

        assert code_score > kb_score

    def test_kb_chunk_scores_higher_on_semantic(self):
        """KB chunk should score higher than code when semantic dominates."""
        # Semantic high, BM25 low — KB weights should win
        bm25, activation, semantic = 0.1, 0.5, 0.9

        code_score = _CODE_WEIGHTS[0] * bm25 + _CODE_WEIGHTS[1] * activation + _CODE_WEIGHTS[2] * semantic
        kb_score = _KB_WEIGHTS[0] * bm25 + _KB_WEIGHTS[1] * activation + _KB_WEIGHTS[2] * semantic

        assert kb_score > code_score


class TestHybridRetrieverFallback:
    """Test fallback behavior when embeddings unavailable."""

    pass
