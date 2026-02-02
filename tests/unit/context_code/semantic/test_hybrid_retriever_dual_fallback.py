"""Unit tests for HybridRetriever BM25+Activation dual-hybrid fallback.

Tests verify that fallback mode works correctly when embeddings unavailable:
- Fallback triggered when no embedding provider
- Fallback triggered when embedding generation fails
- Weights normalized correctly (sum to 1.0)
- WARNING log emitted with clear instructions
- Edge case: zero weights handled gracefully
"""

import logging
from unittest.mock import MagicMock

from aurora_context_code.semantic.hybrid_retriever import HybridConfig, HybridRetriever


# Mock classes for testing
class MockStore:
    """Mock storage backend."""

    def __init__(self, db_path):
        self.db_path = db_path

    def get_all_chunks(self):
        """Return empty list for testing."""
        return []

    def retrieve_by_activation(self, min_activation=0.0, limit=100, include_embeddings=True):
        """Return mock chunks for testing."""
        return [MockChunk(f"chunk-{i}") for i in range(min(limit, 10))]

    def get_access_stats_batch(self, chunk_ids):
        """Return mock access stats for testing."""
        return {cid: {"access_count": 5, "last_accessed": "2024-01-01"} for cid in chunk_ids}


class MockActivationEngine:
    """Mock activation engine."""

    def __init__(self):
        pass


class MockEmbeddingProvider:
    """Mock embedding provider."""

    def __init__(self):
        pass

    def embed_query(self, query):
        """Return mock embedding."""
        return [0.1] * 384


class MockChunk:
    """Mock chunk object."""

    def __init__(self, chunk_id):
        self.id = chunk_id
        self.activation = 0.5
        self.name = f"name_{chunk_id}"
        self.signature = f"def {chunk_id}():"
        self.content = f"content for {chunk_id}"
        self.embedding = [0.2] * 384  # Mock embedding


def test_fallback_triggered_when_no_provider(tmp_path):
    """Test that dual-hybrid fallback is triggered when provider=None.

    Task 2.6.1: Verify fallback is triggered when no embedding provider available.
    """
    db_path = str(tmp_path / "test.db")
    config = HybridConfig(enable_bm25_persistence=False, bm25_weight=0.3, activation_weight=0.3)

    # Create mock dependencies (no embedding provider)
    store = MockStore(db_path)
    engine = MockActivationEngine()

    # Create retriever without embedding provider
    retriever = HybridRetriever(store, engine, embedding_provider=None, config=config)

    # Call retrieve() - should trigger fallback
    results = retriever.retrieve("test query", top_k=5)

    # Verify results returned (not empty)
    assert len(results) > 0, "Fallback should return results"

    # Verify all results have semantic_score=0.0 (no embeddings)
    for result in results:
        assert result["semantic_score"] == 0.0, "Semantic score should be 0.0 in fallback mode"
        # BM25 and activation scores should be present
        assert "bm25_score" in result
        assert "activation_score" in result
        assert "hybrid_score" in result


def test_fallback_triggered_when_embed_fails(tmp_path):
    """Test that dual-hybrid fallback is triggered when embed_query() fails.

    Task 2.6.2: Verify fallback is triggered when embedding generation fails.
    """
    db_path = str(tmp_path / "test.db")
    config = HybridConfig(
        fallback_to_activation=True,  # Enable fallback on error
        enable_bm25_persistence=False,
        bm25_weight=0.3,
        activation_weight=0.3,
    )

    # Create mock dependencies
    store = MockStore(db_path)
    engine = MockActivationEngine()
    mock_provider = MagicMock()
    mock_provider.embed_query.side_effect = RuntimeError("Model load failed")

    # Create retriever with failing provider
    retriever = HybridRetriever(store, engine, mock_provider, config)

    # Call retrieve() - should trigger fallback (no exception)
    results = retriever.retrieve("test query", top_k=5)

    # Verify results returned (fallback worked)
    assert len(results) > 0, "Fallback should return results even when embeddings fail"

    # Verify all results have semantic_score=0.0 (fallback mode)
    for result in results:
        assert result["semantic_score"] == 0.0, "Semantic score should be 0.0 in fallback mode"


def test_fallback_normalizes_weights_correctly(tmp_path):
    """Test that weights are normalized to sum to 1.0 in fallback.

    Task 2.6.3: Verify weight normalization logic.
    Example: (0.3, 0.3, 0.4) -> (0.5, 0.5, 0.0) in fallback
    """
    db_path = str(tmp_path / "test.db")
    config = HybridConfig(
        enable_bm25_persistence=False,
        bm25_weight=0.3,
        activation_weight=0.3,
        semantic_weight=0.4,  # Should be redistributed to bm25 and activation
    )

    # Create mock dependencies (no embedding provider)
    store = MockStore(db_path)
    engine = MockActivationEngine()

    # Create retriever without embedding provider
    retriever = HybridRetriever(store, engine, embedding_provider=None, config=config)

    # Call retrieve() - should trigger fallback
    results = retriever.retrieve("test query", top_k=5)

    # Expected weights after redistribution:
    # bm25_dual = 0.3 / (0.3 + 0.3) = 0.5
    # activation_dual = 0.3 / (0.3 + 0.3) = 0.5

    # Verify by checking hybrid_score formula matches expected weights
    for result in results:
        # Calculate expected hybrid score: 0.5*bm25 + 0.5*activation
        expected_hybrid = 0.5 * result["bm25_score"] + 0.5 * result["activation_score"]

        # Allow small floating-point tolerance
        assert abs(result["hybrid_score"] - expected_hybrid) < 1e-6, (
            f"Hybrid score {result['hybrid_score']} does not match expected "
            f"{expected_hybrid} (should be 0.5*bm25 + 0.5*activation)"
        )


def test_fallback_logs_warning(tmp_path, caplog):
    """Test that WARNING log is emitted with fallback instructions.

    Task 2.6.4: Verify WARNING log with clear user instructions.
    """
    db_path = str(tmp_path / "test.db")
    config = HybridConfig(enable_bm25_persistence=False, bm25_weight=0.3)

    # Create mock dependencies (no embedding provider)
    store = MockStore(db_path)
    engine = MockActivationEngine()

    # Create retriever without embedding provider
    retriever = HybridRetriever(store, engine, embedding_provider=None, config=config)

    # Call retrieve() with WARNING logging enabled
    with caplog.at_level(logging.WARNING, logger="aurora_context_code.semantic.hybrid_retriever"):
        results = retriever.retrieve("test query", top_k=5)

    # Verify WARNING log was emitted
    warning_messages = [
        record.message for record in caplog.records if record.levelno == logging.WARNING
    ]
    assert len(warning_messages) > 0, "WARNING log should be emitted in fallback mode"

    # Verify log message contains key information
    combined_warnings = " ".join(warning_messages)
    assert "BM25+Activation fallback" in combined_warnings, (
        "Log should mention BM25+Activation fallback mode"
    )
    assert "85%" in combined_warnings, "Log should mention estimated quality"
    assert "pip install sentence-transformers" in combined_warnings, (
        "Log should include recovery instructions"
    )


def test_fallback_handles_edge_case_zero_weights(tmp_path, caplog):
    """Test fallback when both BM25 and activation weights are 0.

    Task 2.6.5: Verify edge case handling when both weights are 0.
    Should fall back to activation-only (100%).
    """
    db_path = str(tmp_path / "test.db")
    config = HybridConfig(
        enable_bm25_persistence=False,
        bm25_weight=0.0,  # Zero weight
        activation_weight=0.0,  # Zero weight
        semantic_weight=1.0,  # All semantic (unavailable)
    )

    # Create mock dependencies (no embedding provider)
    store = MockStore(db_path)
    engine = MockActivationEngine()

    # Create retriever without embedding provider
    retriever = HybridRetriever(store, engine, embedding_provider=None, config=config)

    # Call retrieve() with WARNING logging enabled
    with caplog.at_level(logging.WARNING, logger="aurora_context_code.semantic.hybrid_retriever"):
        results = retriever.retrieve("test query", top_k=5)

    # Verify results returned (edge case handled gracefully)
    assert len(results) > 0, "Fallback should handle zero weights gracefully"

    # Verify WARNING about zero weights was logged
    warning_messages = [
        record.message for record in caplog.records if record.levelno == logging.WARNING
    ]
    combined_warnings = " ".join(warning_messages)
    assert "Both BM25 and activation weights are 0" in combined_warnings, (
        "Log should warn about zero weights edge case"
    )

    # Verify hybrid score equals activation score (100% activation fallback)
    for result in results:
        expected_hybrid = result["activation_score"]
        assert abs(result["hybrid_score"] - expected_hybrid) < 1e-6, (
            f"Hybrid score {result['hybrid_score']} should equal activation score "
            f"{expected_hybrid} when both weights are 0"
        )


def test_fallback_returns_correct_result_format(tmp_path):
    """Test that fallback returns results in tri-hybrid format.

    Task 2.6.6: Verify result format matches tri-hybrid (compatibility).
    """
    db_path = str(tmp_path / "test.db")
    config = HybridConfig(enable_bm25_persistence=False, bm25_weight=0.3)

    # Create mock dependencies (no embedding provider)
    store = MockStore(db_path)
    engine = MockActivationEngine()

    # Create retriever without embedding provider
    retriever = HybridRetriever(store, engine, embedding_provider=None, config=config)

    # Call retrieve()
    results = retriever.retrieve("test query", top_k=5)

    # Verify all results have required keys (tri-hybrid format)
    required_keys = {
        "chunk_id",
        "content",
        "bm25_score",
        "activation_score",
        "semantic_score",
        "hybrid_score",
        "metadata",
    }

    for result in results:
        assert set(result.keys()) == required_keys, (
            f"Result keys {set(result.keys())} do not match expected {required_keys}"
        )

        # Verify score types and ranges
        assert isinstance(result["bm25_score"], (int, float))
        assert isinstance(result["activation_score"], (int, float))
        assert isinstance(result["semantic_score"], (int, float))
        assert isinstance(result["hybrid_score"], (int, float))

        # Verify semantic_score is 0.0 (fallback mode)
        assert result["semantic_score"] == 0.0
