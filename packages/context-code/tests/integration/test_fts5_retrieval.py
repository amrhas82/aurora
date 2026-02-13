"""Integration tests for FTS5-based hybrid retrieval.

Tests use real SQLiteStore + real HybridRetriever (no MockStore).
"""

import numpy as np
import pytest

from aurora_context_code.semantic.hybrid_retriever import HybridConfig, HybridRetriever
from aurora_core.store.sqlite import SQLiteStore


def _make_code_chunk(chunk_id, name, signature, docstring, file_path):
    """Create a minimal chunk object for testing."""
    from aurora_core.chunks import CodeChunk

    return CodeChunk(
        chunk_id=chunk_id,
        name=name,
        element_type="function",
        signature=signature,
        docstring=docstring,
        file_path=file_path,
        line_start=1,
        line_end=10,
        language="python",
    )


class MockActivationEngine:
    """Minimal activation engine for testing."""

    pass


class MockEmbeddingProvider:
    """Embedding provider that returns deterministic embeddings."""

    def embed_query(self, query):
        """Return a deterministic embedding based on query hash."""
        rng = np.random.RandomState(hash(query) % 2**31)
        return rng.randn(384).astype(np.float32)


class TestFTS5HybridRetrieval:
    """Test HybridRetriever with real SQLiteStore and FTS5."""

    def test_low_activation_chunk_surfaces_with_keyword_match(self, tmp_path):
        """A rarely-accessed chunk with exact keyword match should appear in results."""
        db_path = str(tmp_path / "test.db")
        store = SQLiteStore(db_path)

        # Create a chunk with low activation but exact keyword match
        chunk = _make_code_chunk(
            "code:guide.py:testing_guide",
            "testing_guide",
            "def testing_guide():",
            "Complete guide to testing including pytest fixtures and assertions.",
            "/test/TESTING_GUIDE.py",
        )
        # Give it a fake embedding
        embedding = np.random.randn(384).astype(np.float32)
        chunk.embeddings = embedding.tobytes()
        store.save_chunk(chunk)

        # Create retriever
        config = HybridConfig()
        retriever = HybridRetriever(
            store=store,
            activation_engine=MockActivationEngine(),
            embedding_provider=MockEmbeddingProvider(),
            config=config,
        )

        results = retriever.retrieve("testing guide", top_k=5)

        assert len(results) >= 1
        assert any("testing_guide" in r["chunk_id"] for r in results)

    def test_fts5_rank_contributes_to_scoring(self, tmp_path):
        """Chunks with better FTS5 rank should score higher (all else equal)."""
        db_path = str(tmp_path / "test.db")
        store = SQLiteStore(db_path)

        # Chunk with exact keyword match
        exact = _make_code_chunk(
            "code:auth.py:authenticate",
            "authenticate",
            "def authenticate(user, password):",
            "Authenticate user with password credentials.",
            "/test/auth.py",
        )
        exact.embeddings = np.random.randn(384).astype(np.float32).tobytes()
        store.save_chunk(exact)

        # Chunk with weak keyword relevance
        weak = _make_code_chunk(
            "code:db.py:connect",
            "connect",
            "def connect(host):",
            "Connect to database server.",
            "/test/db.py",
        )
        weak.embeddings = np.random.randn(384).astype(np.float32).tobytes()
        store.save_chunk(weak)

        config = HybridConfig()
        retriever = HybridRetriever(
            store=store,
            activation_engine=MockActivationEngine(),
            embedding_provider=MockEmbeddingProvider(),
            config=config,
        )

        results = retriever.retrieve("authenticate", top_k=5)

        # The exact match should rank first
        if len(results) >= 1:
            assert results[0]["chunk_id"] == "code:auth.py:authenticate"

    def test_fallback_to_activation_when_no_fts5(self, tmp_path, monkeypatch):
        """When store lacks retrieve_by_fts, should fall back to activation gate."""
        db_path = str(tmp_path / "test.db")
        store = SQLiteStore(db_path)

        chunk = _make_code_chunk(
            "code:test.py:func1",
            "func1",
            "def func1():",
            "A test function.",
            "/test/test.py",
        )
        chunk.embeddings = np.random.randn(384).astype(np.float32).tobytes()
        store.save_chunk(chunk)

        # Remove retrieve_by_fts to simulate old DB (monkeypatch auto-restores)
        monkeypatch.delattr(SQLiteStore, "retrieve_by_fts")

        config = HybridConfig()
        retriever = HybridRetriever(
            store=store,
            activation_engine=MockActivationEngine(),
            embedding_provider=MockEmbeddingProvider(),
            config=config,
        )

        # Should still work via activation fallback
        results = retriever.retrieve("func1", top_k=5)
        assert isinstance(results, list)
