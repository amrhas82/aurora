"""Unit tests for HybridRetriever lazy BM25 index loading.

Tests verify that BM25 index is loaded lazily on first retrieve() call
rather than eagerly in __init__(), improving retriever creation time.

Test scenarios:
- BM25 index not loaded during __init__()
- BM25 index loaded on first retrieve() call
- Subsequent retrieve() calls reuse loaded index
- Thread-safety: concurrent retrieve() calls load index exactly once
"""

import threading
import time
from pathlib import Path
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

    def retrieve_by_activation(
        self, min_activation=0.0, limit=100, include_embeddings=True, chunk_type=None
    ):
        """Return mock chunks for testing."""
        return [MockChunk(f"chunk-{i}") for i in range(min(limit, 10))]

    def get_access_stats_batch(self, chunk_ids):
        """Return mock access stats for testing."""
        return {cid: {"access_count": 5, "last_accessed": "2024-01-01"} for cid in chunk_ids}


class MockActivationEngine:
    """Mock activation engine."""

    def __init__(self):
        pass

    def get_top_activated_chunks(self, query, top_k):
        """Return mock chunks for testing."""
        return [MockChunk(f"chunk-{i}") for i in range(top_k)]


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


def test_lazy_loading_not_triggered_on_init(tmp_path):
    """Test that BM25 index is NOT loaded during __init__().

    Task 1.4.1: Verify lazy loading - index not loaded until first retrieve().
    """
    db_path = str(tmp_path / "test.db")
    config = HybridConfig(enable_bm25_persistence=True, bm25_weight=0.3)

    # Create mock dependencies
    store = MockStore(db_path)
    engine = MockActivationEngine()
    provider = MockEmbeddingProvider()

    # Create retriever (should NOT load BM25 index)
    retriever = HybridRetriever(store, engine, provider, config)

    # Verify index is NOT loaded
    assert retriever._bm25_index_loaded is False, "BM25 index should not be loaded on __init__()"
    assert retriever.bm25_scorer is None, "BM25 scorer should be None on __init__()"


def test_lazy_loading_triggered_on_first_retrieve(tmp_path):
    """Test that BM25 index is loaded on first retrieve() call.

    Task 1.4.2: Verify lazy loading - index loaded on first retrieve().
    """
    db_path = str(tmp_path / "test.db")

    # Create a mock BM25 index file
    bm25_index_path = Path(db_path).parent / "indexes" / "bm25_index.pkl"
    bm25_index_path.parent.mkdir(parents=True, exist_ok=True)

    config = HybridConfig(
        enable_bm25_persistence=True,
        bm25_weight=0.3,
        bm25_index_path=str(bm25_index_path),
    )

    # Create mock dependencies
    store = MockStore(db_path)
    engine = MockActivationEngine()
    provider = MockEmbeddingProvider()

    # Create retriever (should NOT load BM25 index yet)
    retriever = HybridRetriever(store, engine, provider, config)
    assert retriever._bm25_index_loaded is False

    # Mock _try_load_bm25_index to simulate successful load
    original_try_load = retriever._try_load_bm25_index

    def mock_try_load():
        """Mock successful BM25 index load."""
        retriever._bm25_index_loaded = True
        retriever.bm25_scorer = MagicMock()

    retriever._try_load_bm25_index = mock_try_load

    # Call retrieve() - should trigger lazy loading
    try:
        retriever.retrieve("test query", top_k=5)
    except Exception:
        # Ignore errors from retrieve() - we only care about lazy loading
        pass

    # Verify index was loaded
    assert retriever._bm25_index_loaded is True, "BM25 index should be loaded on first retrieve()"
    assert retriever.bm25_scorer is not None, "BM25 scorer should be set on first retrieve()"


def test_lazy_loading_reuses_index_on_subsequent_calls(tmp_path):
    """Test that BM25 index is reused (not reloaded) on subsequent calls.

    Task 1.4.3: Verify lazy loading - subsequent calls reuse loaded index.
    """
    db_path = str(tmp_path / "test.db")
    config = HybridConfig(enable_bm25_persistence=True, bm25_weight=0.3)

    # Create mock dependencies
    store = MockStore(db_path)
    engine = MockActivationEngine()
    provider = MockEmbeddingProvider()

    # Create retriever
    retriever = HybridRetriever(store, engine, provider, config)

    # Mock _try_load_bm25_index to track calls
    load_count = {"count": 0}

    def mock_try_load():
        """Mock successful BM25 index load and count calls."""
        load_count["count"] += 1
        retriever._bm25_index_loaded = True
        retriever.bm25_scorer = MagicMock()

    retriever._try_load_bm25_index = mock_try_load

    # Call retrieve() multiple times
    for i in range(3):
        try:
            retriever.retrieve(f"test query {i}", top_k=5)
        except Exception:
            # Ignore errors from retrieve() - we only care about lazy loading
            pass

    # Verify _try_load_bm25_index was called exactly once
    assert load_count["count"] == 1, "BM25 index should be loaded exactly once (not reloaded)"


def test_lazy_loading_thread_safety(tmp_path):
    """Test that BM25 index is loaded exactly once with concurrent calls.

    Task 1.4.4: Verify thread-safety - concurrent retrieve() calls load index once.
    """
    db_path = str(tmp_path / "test.db")
    config = HybridConfig(enable_bm25_persistence=True, bm25_weight=0.3)

    # Create mock dependencies
    store = MockStore(db_path)
    engine = MockActivationEngine()
    provider = MockEmbeddingProvider()

    # Create retriever
    retriever = HybridRetriever(store, engine, provider, config)

    # Mock _try_load_bm25_index to track calls and simulate delay
    load_count = {"count": 0}

    def mock_try_load():
        """Mock successful BM25 index load with delay to expose race conditions."""
        load_count["count"] += 1
        time.sleep(0.01)  # Small delay to increase chance of race condition
        retriever._bm25_index_loaded = True
        retriever.bm25_scorer = MagicMock()

    retriever._try_load_bm25_index = mock_try_load

    # Define search function for threads
    def search():
        """Execute retrieve() in thread."""
        try:
            retriever.retrieve("test query", top_k=5)
        except Exception:
            # Ignore errors from retrieve() - we only care about lazy loading
            pass

    # Launch 10 concurrent threads
    threads = [threading.Thread(target=search) for _ in range(10)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    # Verify _try_load_bm25_index was called exactly once (not 10 times)
    assert load_count["count"] == 1, (
        f"BM25 index should be loaded exactly once (got {load_count['count']} calls). "
        f"This indicates a thread-safety issue with lazy loading."
    )
    assert (
        retriever._bm25_index_loaded is True
    ), "BM25 index should be loaded after concurrent calls"
