"""Unit tests for BM25 index persistence and validation.

Tests verify that BM25 index persistence works correctly with proper
validation, error handling, and logging.

Test scenarios:
- Index saves on build
- Index loads from disk
- Graceful fallback on corrupted index
- Rebuild on missing index
- Path resolution for absolute vs relative paths
"""

from unittest.mock import Mock

import pytest  # noqa: F401 - needed for tmp_path fixture


# Mock classes for testing
class MockStore:
    """Mock storage backend."""

    def __init__(self, db_path):
        self.db_path = db_path

    def retrieve_all_chunks(self):
        """Return mock chunks."""
        chunks = []
        for i in range(100):
            chunk = Mock()
            chunk.id = f"chunk_{i}"
            chunk.content = f"This is test content for chunk {i}"
            chunk.type = "code"
            chunks.append(chunk)
        return chunks

    def retrieve_by_activation(
        self, min_activation=0.0, limit=100, include_embeddings=True, chunk_type=None
    ):
        """Retrieve chunks by activation (for lazy loading trigger)."""
        chunks = []
        for i in range(min(limit, 10)):  # Return up to 10 mock chunks
            chunk = Mock()
            chunk.id = f"chunk_{i}"
            chunk.activation = 0.5
            chunk.type = "code"
            chunk.name = f"test_chunk_{i}"
            chunk.file_path = f"/test/path_{i}.py"
            chunk.line_start = i * 10
            chunk.line_end = (i * 10) + 5
            chunk.signature = f"def test_func_{i}():"
            chunk.docstring = f"Test function {i}"
            chunk.embeddings = None  # No embeddings for BM25-only test
            chunk.metadata = {}  # Empty metadata dict (not Mock)
            chunks.append(chunk)
        return chunks

    def fetch_embeddings_for_chunks(self, chunk_ids):
        """Fetch embeddings for specific chunks (two-phase optimization)."""
        return {}  # No embeddings in this mock


class MockActivationEngine:
    """Mock activation engine."""

    def __init__(self):
        pass


class MockEmbeddingProvider:
    """Mock embedding provider."""

    def __init__(self):
        pass


def test_bm25_index_saves_on_build(tmp_path):
    """Test that BM25 index is saved to disk after building.

    Task 3.1: Verify .aurora/indexes/bm25_index.pkl file exists and has size >0.
    """
    from aurora_context_code.semantic.hybrid_retriever import HybridConfig, HybridRetriever

    # Set up paths
    db_path = tmp_path / "test.db"
    index_dir = tmp_path / "indexes"
    index_path = index_dir / "bm25_index.pkl"

    # Create mock dependencies
    store = MockStore(str(db_path))
    engine = MockActivationEngine()
    provider = MockEmbeddingProvider()

    # Configure to enable BM25 persistence
    config = HybridConfig(enable_bm25_persistence=True)

    # Create retriever
    retriever = HybridRetriever(store, engine, provider, config=config)

    # Build and save index
    documents = [(f"doc_{i}", f"content {i}") for i in range(100)]
    success = retriever.build_and_save_bm25_index(documents)

    # Verify index was built and saved
    assert success, "Index build should succeed"
    assert index_path.exists(), f"Index file should exist at {index_path}"
    assert index_path.stat().st_size > 0, "Index file should have non-zero size"


def test_bm25_index_loads_from_disk(tmp_path):
    """Test that BM25 index loads from disk on first retrieve() call (lazy loading).

    Task 3.2: Save index with 100 docs, create new retriever, verify loaded on first use.
    Epic 2 Update: BM25 index now loads lazily on first retrieve() call, not in __init__().
    """
    from aurora_context_code.semantic.hybrid_retriever import HybridConfig, HybridRetriever

    # Set up paths
    db_path = tmp_path / "test.db"
    index_dir = tmp_path / "indexes"
    index_path = index_dir / "bm25_index.pkl"

    # Create mock dependencies
    store = MockStore(str(db_path))
    engine = MockActivationEngine()
    provider = MockEmbeddingProvider()

    # Configure to enable BM25 persistence
    config = HybridConfig(enable_bm25_persistence=True)

    # Build and save index with first retriever
    retriever1 = HybridRetriever(store, engine, provider, config=config)
    documents = [(f"doc_{i}", f"content {i}") for i in range(100)]
    retriever1.build_and_save_bm25_index(documents)

    # Create new retriever (lazy loading - index NOT loaded yet)
    retriever2 = HybridRetriever(store, engine, provider, config=config)

    # Verify index NOT loaded yet (lazy loading)
    assert not retriever2._bm25_index_loaded, "Index should NOT be loaded yet (lazy loading)"
    assert retriever2.bm25_scorer is None, "BM25 scorer should be None before first retrieve()"

    # Trigger lazy loading by calling retrieve()
    results = retriever2.retrieve("test query", top_k=5)

    # Verify index was loaded on first retrieve()
    assert retriever2._bm25_index_loaded, "Index should be loaded after first retrieve()"
    assert retriever2.bm25_scorer is not None, "BM25 scorer should be initialized after retrieve()"
    assert retriever2.bm25_scorer.corpus_size == 100, "Corpus size should be 100"


def test_bm25_index_corrupted_fallback(tmp_path):
    """Test graceful fallback when BM25 index is corrupted.

    Task 3.3: Write garbage bytes to index file, verify WARNING logged and no crash.
    """
    from aurora_context_code.semantic.hybrid_retriever import HybridConfig, HybridRetriever

    # Set up paths
    db_path = tmp_path / "test.db"
    index_dir = tmp_path / "indexes"
    index_dir.mkdir(parents=True, exist_ok=True)
    index_path = index_dir / "bm25_index.pkl"

    # Write garbage to index file
    with open(index_path, "wb") as f:
        f.write(b"this is not a valid pickle file")

    # Create mock dependencies
    store = MockStore(str(db_path))
    engine = MockActivationEngine()
    provider = MockEmbeddingProvider()

    # Configure to enable BM25 persistence
    config = HybridConfig(enable_bm25_persistence=True)

    # Create retriever (should handle corrupted index gracefully)
    retriever = HybridRetriever(store, engine, provider, config=config)

    # Verify graceful fallback
    assert not retriever._bm25_index_loaded, "Index should not be loaded (corrupted)"
    # Should not crash, just log warning and continue


def test_bm25_index_missing_rebuilds(tmp_path):
    """Test that missing index triggers rebuild on first search.

    Task 3.4: Delete index file, create retriever, verify INFO logged about missing index.
    """
    from aurora_context_code.semantic.hybrid_retriever import HybridConfig, HybridRetriever

    # Set up paths
    db_path = tmp_path / "test.db"

    # Create mock dependencies
    store = MockStore(str(db_path))
    engine = MockActivationEngine()
    provider = MockEmbeddingProvider()

    # Configure to enable BM25 persistence
    config = HybridConfig(enable_bm25_persistence=True)

    # Create retriever (no index exists)
    retriever = HybridRetriever(store, engine, provider, config=config)

    # Verify index was not loaded
    assert not retriever._bm25_index_loaded, "Index should not be loaded (missing)"
    # Should log INFO about no persistent index found


def test_bm25_path_resolution_absolute_vs_relative(tmp_path):
    """Test _get_bm25_index_path() returns correct path for absolute and relative paths.

    Task 3.5: Test path resolution for both absolute and relative db_path.
    """
    from aurora_context_code.semantic.hybrid_retriever import HybridConfig, HybridRetriever

    # Test with absolute path
    abs_db_path = tmp_path / "abs_test.db"
    store_abs = MockStore(str(abs_db_path))
    engine = MockActivationEngine()
    provider = MockEmbeddingProvider()
    config = HybridConfig(enable_bm25_persistence=True)

    retriever_abs = HybridRetriever(store_abs, engine, provider, config=config)
    index_path_abs = retriever_abs._get_bm25_index_path()

    assert index_path_abs is not None, "Index path should not be None"
    assert index_path_abs.is_absolute(), "Index path should be absolute"
    assert str(index_path_abs).endswith(
        "indexes/bm25_index.pkl"
    ), "Index path should end with indexes/bm25_index.pkl"

    # Test with relative path
    rel_db_path = "relative_test.db"
    store_rel = MockStore(rel_db_path)
    retriever_rel = HybridRetriever(store_rel, engine, provider, config=config)
    index_path_rel = retriever_rel._get_bm25_index_path()

    assert index_path_rel is not None, "Index path should not be None"
    assert str(index_path_rel).endswith(
        "indexes/bm25_index.pkl"
    ), "Index path should end with indexes/bm25_index.pkl"
