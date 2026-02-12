"""Integration tests for HybridRetriever fallback paths and BM25 scorer.

Tests BM25Scorer indexing/scoring, HybridConfig validation,
tokenizer code-awareness, and HybridRetriever fallback behavior
when embeddings are unavailable.
"""

import math

import numpy as np
import pytest

from aurora_context_code.semantic.bm25_scorer import BM25Scorer, tokenize
from aurora_context_code.semantic.hybrid_retriever import HybridConfig, HybridRetriever
from aurora_core.activation import ActivationEngine
from aurora_core.chunks.code_chunk import CodeChunk
from aurora_core.store.sqlite import SQLiteStore


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_chunk(chunk_id, name, docstring="", file_path="/test/file.py"):
    return CodeChunk(
        chunk_id=chunk_id,
        file_path=file_path,
        element_type="function",
        name=name,
        line_start=1,
        line_end=10,
        docstring=docstring,
    )


class DummyEmbeddingProvider:
    """Deterministic embedding provider for testing."""

    def embed_query(self, text):
        np.random.seed(hash(text) % 2**31)
        return np.random.randn(384).astype(np.float32)

    def embed_chunk(self, text):
        return self.embed_query(text)

    def embed_batch(self, texts, batch_size=32):
        return np.array([self.embed_query(t) for t in texts])


# ---------------------------------------------------------------------------
# BM25Scorer tests
# ---------------------------------------------------------------------------

class TestBM25Scorer:
    """Tests for BM25Scorer."""

    def test_build_index_basic(self):
        scorer = BM25Scorer()
        docs = [
            ("d1", "authenticate user login"),
            ("d2", "user session management"),
            ("d3", "database connection pool"),
        ]
        scorer.build_index(docs)

        assert scorer.corpus_size == 3
        assert scorer.avg_doc_length > 0
        assert len(scorer.idf) > 0

    def test_score_matching_terms(self):
        scorer = BM25Scorer()
        docs = [
            ("d1", "authenticate user login"),
            ("d2", "user session management"),
        ]
        scorer.build_index(docs)

        score = scorer.score("authenticate", "authenticate user login")
        assert score > 0

    def test_score_no_matching_terms(self):
        scorer = BM25Scorer()
        docs = [("d1", "authenticate user")]
        scorer.build_index(docs)

        score = scorer.score("database", "authenticate user")
        assert score == 0.0

    def test_matching_doc_scores_higher(self):
        scorer = BM25Scorer()
        docs = [
            ("d1", "authenticate user login"),
            ("d2", "database connection pool"),
        ]
        scorer.build_index(docs)

        score_match = scorer.score("authenticate", "authenticate user login")
        score_no_match = scorer.score("authenticate", "database connection pool")

        assert score_match > score_no_match

    def test_save_and_load_index(self, tmp_path):
        scorer = BM25Scorer()
        docs = [("d1", "test document"), ("d2", "another document")]
        scorer.build_index(docs)

        index_path = tmp_path / "bm25.pkl"
        scorer.save_index(index_path)

        scorer2 = BM25Scorer()
        scorer2.load_index(index_path)

        # Should produce same scores
        s1 = scorer.score("test", "test document")
        s2 = scorer2.score("test", "test document")
        assert abs(s1 - s2) < 1e-6

    def test_empty_corpus(self):
        scorer = BM25Scorer()
        scorer.build_index([])
        assert scorer.corpus_size == 0
        assert scorer.avg_doc_length == 0.0


class TestTokenizer:
    """Tests for code-aware tokenizer."""

    def test_camel_case(self):
        tokens = tokenize("getUserData")
        assert "get" in tokens
        assert "user" in tokens
        assert "data" in tokens

    def test_snake_case(self):
        tokens = tokenize("user_manager")
        assert "user" in tokens
        assert "manager" in tokens

    def test_simple_words(self):
        tokens = tokenize("authenticate user")
        assert "authenticate" in tokens
        assert "user" in tokens

    def test_empty_string(self):
        tokens = tokenize("")
        assert tokens == []


# ---------------------------------------------------------------------------
# HybridConfig tests
# ---------------------------------------------------------------------------

class TestHybridConfig:
    """Tests for HybridConfig validation."""

    def test_default_weights_valid(self):
        config = HybridConfig()
        total = config.bm25_weight + config.activation_weight + config.semantic_weight
        assert abs(total - 1.0) < 1e-6

    def test_weights_must_sum_to_one(self):
        with pytest.raises(ValueError, match="sum to 1.0"):
            HybridConfig(bm25_weight=0.5, activation_weight=0.5, semantic_weight=0.5)

    def test_negative_weight_rejected(self):
        with pytest.raises(ValueError):
            HybridConfig(bm25_weight=-0.1, activation_weight=0.5, semantic_weight=0.6)

    def test_dual_hybrid_config(self):
        config = HybridConfig(bm25_weight=0.0, activation_weight=0.6, semantic_weight=0.4)
        assert config.bm25_weight == 0.0

    def test_invalid_mmr_lambda(self):
        with pytest.raises(ValueError, match="mmr_lambda"):
            HybridConfig(mmr_lambda=1.5)

    def test_invalid_stage1_top_k(self):
        with pytest.raises(ValueError, match="stage1_top_k"):
            HybridConfig(stage1_top_k=0)


# ---------------------------------------------------------------------------
# HybridRetriever integration tests
# ---------------------------------------------------------------------------

@pytest.fixture
def populated_store(tmp_path):
    """Store with several chunks for retrieval testing."""
    store = SQLiteStore(str(tmp_path / "test.db"))

    chunks = [
        make_chunk("c1", "authenticate_user", docstring="authenticate user verify credentials username password"),
        make_chunk("c2", "create_session", docstring="create login session token for user"),
        make_chunk("c3", "database_connect", docstring="establish database connection pool host port"),
        make_chunk("c4", "parse_config", docstring="read configuration file yaml path"),
        make_chunk("c5", "run_migrations", docstring="execute database schema migrations"),
    ]

    for chunk in chunks:
        store.save_chunk(chunk)
        # Give them some embeddings
        emb = DummyEmbeddingProvider().embed_chunk(chunk.docstring or chunk.name)
        chunk.embeddings = emb.tobytes()
        store.save_chunk(chunk)  # Update with embeddings

    yield store
    store.close()


class TestHybridRetrieverFallbacks:
    """Tests for HybridRetriever fallback paths."""

    def test_retrieve_without_embedding_provider(self, populated_store):
        """When no embedding provider, should fall back to BM25+Activation."""
        engine = ActivationEngine()
        config = HybridConfig(
            bm25_weight=0.5,
            activation_weight=0.5,
            semantic_weight=0.0,
            enable_bm25_persistence=False,
        )
        retriever = HybridRetriever(populated_store, engine, None, config)

        results = retriever.retrieve("authenticate", top_k=3)
        assert len(results) > 0

    def test_retrieve_empty_store(self, tmp_path):
        """Empty store should return empty results."""
        store = SQLiteStore(str(tmp_path / "empty.db"))
        engine = ActivationEngine()
        config = HybridConfig(enable_bm25_persistence=False)
        provider = DummyEmbeddingProvider()
        retriever = HybridRetriever(store, engine, provider, config)

        results = retriever.retrieve("anything", top_k=5)
        assert results == []
        store.close()

    def test_retrieve_with_dummy_embeddings(self, populated_store):
        """Full tri-hybrid path with dummy embeddings."""
        engine = ActivationEngine()
        config = HybridConfig(enable_bm25_persistence=False)
        provider = DummyEmbeddingProvider()
        retriever = HybridRetriever(populated_store, engine, provider, config)

        results = retriever.retrieve("authenticate user", top_k=3)
        assert len(results) > 0
        assert all("hybrid_score" in r for r in results)
        assert all("bm25_score" in r for r in results)

    def test_empty_query_raises(self, populated_store):
        engine = ActivationEngine()
        config = HybridConfig(enable_bm25_persistence=False)
        provider = DummyEmbeddingProvider()
        retriever = HybridRetriever(populated_store, engine, provider, config)

        with pytest.raises(ValueError, match="empty"):
            retriever.retrieve("", top_k=5)

    def test_results_have_expected_keys(self, populated_store):
        engine = ActivationEngine()
        config = HybridConfig(enable_bm25_persistence=False)
        provider = DummyEmbeddingProvider()
        retriever = HybridRetriever(populated_store, engine, provider, config)

        results = retriever.retrieve("database", top_k=2)
        if results:
            r = results[0]
            assert "chunk_id" in r
            assert "hybrid_score" in r
            assert "bm25_score" in r
            assert "semantic_score" in r
            assert "activation_score" in r

    def test_top_k_respected(self, populated_store):
        engine = ActivationEngine()
        config = HybridConfig(enable_bm25_persistence=False)
        provider = DummyEmbeddingProvider()
        retriever = HybridRetriever(populated_store, engine, provider, config)

        results = retriever.retrieve("database", top_k=1)
        assert len(results) <= 1

    def test_results_ordered_by_hybrid_score(self, populated_store):
        engine = ActivationEngine()
        config = HybridConfig(enable_bm25_persistence=False)
        provider = DummyEmbeddingProvider()
        retriever = HybridRetriever(populated_store, engine, provider, config)

        results = retriever.retrieve("database connection", top_k=5)
        if len(results) >= 2:
            scores = [r["hybrid_score"] for r in results]
            assert scores == sorted(scores, reverse=True)
