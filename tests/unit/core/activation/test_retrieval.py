"""
Unit tests for Activation-Based Retrieval.

Tests the ActivationRetriever and BatchRetriever classes including:
- RetrievalConfig and RetrievalResult models
- Activation-based filtering and ranking
- Threshold-based filtering
- Top-N retrieval
- Batch retrieval optimization
- Retrieval with relationship graphs
- Activation calculation and explanation
- Edge cases (empty candidates, no spreading, zero keywords)
"""

from datetime import datetime, timedelta, timezone

import pytest
from aurora.core.types import ChunkID

from aurora_core.activation.base_level import AccessHistoryEntry
from aurora_core.activation.engine import ActivationEngine
from aurora_core.activation.retrieval import (
    ActivationRetriever,
    BatchRetriever,
    RetrievalConfig,
    RetrievalResult,
)
from aurora_core.activation.spreading import RelationshipGraph


# Mock implementation of ChunkData for testing
class MockChunk:
    """Mock chunk implementation for testing retrieval."""

    def __init__(
        self,
        chunk_id: ChunkID,
        access_history: list[AccessHistoryEntry] | None = None,
        last_access: datetime | None = None,
        keywords: set[str] | None = None,
    ):
        self._id = chunk_id
        self._access_history = access_history or []
        self._last_access = last_access
        self._keywords = keywords or set()

    @property
    def id(self) -> ChunkID:
        return self._id

    @property
    def access_history(self) -> list[AccessHistoryEntry]:
        return self._access_history

    @property
    def last_access(self) -> datetime | None:
        return self._last_access

    @property
    def keywords(self) -> set[str]:
        return self._keywords


class TestRetrievalConfig:
    """Test RetrievalConfig model."""
    @pytest.mark.core

    def test_default_config(self):
        """Test default configuration values."""
        config = RetrievalConfig()
        assert config.threshold == 0.3
        assert config.max_results == 10
        assert config.include_components is False
        assert config.sort_by_activation is True
    @pytest.mark.core

    def test_custom_config(self):
        """Test custom configuration values."""
        config = RetrievalConfig(
            threshold=0.5, max_results=20, include_components=True, sort_by_activation=False
        )
        assert config.threshold == 0.5
        assert config.max_results == 20
        assert config.include_components is True
        assert config.sort_by_activation is False
    @pytest.mark.core

    def test_max_results_validation(self):
        """Test max_results must be at least 1."""
        # Valid values
        RetrievalConfig(max_results=1)
        RetrievalConfig(max_results=100)

        # Invalid value
        with pytest.raises(Exception):
            RetrievalConfig(max_results=0)

    def test_threshold_can_be_negative(self):
        """Test threshold can be negative for permissive retrieval."""
        config = RetrievalConfig(threshold=-1.0)
        assert config.threshold == -1.0


class TestRetrievalResult:
    """Test RetrievalResult model."""

    def test_default_result(self):
        """Test creating result with default values."""
        result = RetrievalResult(chunk_id="chunk_1", activation=0.75)
        assert result.chunk_id == "chunk_1"
        assert result.activation == 0.75
        assert result.components is None
        assert result.rank == 0

    def test_result_with_components(self):
        """Test creating result with component breakdown."""
        from aurora_core.activation.engine import ActivationComponents

        components = ActivationComponents(
            bla=1.5, spreading=0.5, context_boost=0.3, decay=-0.2, total=2.1
        )

        result = RetrievalResult(chunk_id="chunk_2", activation=2.1, components=components, rank=1)

        assert result.chunk_id == "chunk_2"
        assert result.activation == 2.1
        assert result.components is not None
        assert result.components.bla == 1.5
        assert result.rank == 1

    def test_result_rank_update(self):
        """Test that result rank can be updated."""
        result = RetrievalResult(chunk_id="chunk_3", activation=0.5, rank=0)

        assert result.rank == 0
        result.rank = 3
        assert result.rank == 3


class TestActivationRetriever:
    """Test ActivationRetriever functionality."""

    def test_retriever_initialization_default(self):
        """Test retriever initializes with default config."""
        engine = ActivationEngine()
        retriever = ActivationRetriever(engine)

        assert retriever.engine is engine
        assert retriever.config.threshold == 0.3
        assert retriever.config.max_results == 10

    def test_retriever_initialization_custom_config(self):
        """Test retriever initializes with custom config."""
        engine = ActivationEngine()
        config = RetrievalConfig(threshold=0.5, max_results=5)
        retriever = ActivationRetriever(engine, config)

        assert retriever.config.threshold == 0.5
        assert retriever.config.max_results == 5

    def test_retrieve_empty_candidates(self):
        """Test retrieving with no candidates."""
        engine = ActivationEngine()
        retriever = ActivationRetriever(engine)

        results = retriever.retrieve(candidates=[])
        assert len(results) == 0

    def test_retrieve_single_chunk_above_threshold(self):
        """Test retrieving single chunk above threshold."""
        engine = ActivationEngine()
        retriever = ActivationRetriever(engine)
        now = datetime.now(timezone.utc)

        # Create chunk with recent access (high activation)
        chunk = MockChunk(
            chunk_id="chunk_1",
            access_history=[AccessHistoryEntry(timestamp=now - timedelta(hours=1))],
            last_access=now - timedelta(hours=1),
            keywords={"database", "query"},
        )

        results = retriever.retrieve(
            candidates=[chunk],
            query_keywords={"database"},
            threshold=-10.0,  # Low threshold to ensure retrieval
            current_time=now,
        )

        assert len(results) == 1
        assert results[0].chunk_id == "chunk_1"
        assert results[0].rank == 1
        # Activation can be negative for recent but not frequently accessed chunks
        assert isinstance(results[0].activation, float)

    def test_retrieve_filters_below_threshold(self):
        """Test that chunks below threshold are filtered out."""
        engine = ActivationEngine()
        retriever = ActivationRetriever(engine)
        now = datetime.now(timezone.utc)

        # Create chunk with old access (low activation)
        chunk = MockChunk(
            chunk_id="chunk_1",
            access_history=[AccessHistoryEntry(timestamp=now - timedelta(days=365))],
            last_access=now - timedelta(days=365),
            keywords={"old", "unused"},
        )

        results = retriever.retrieve(
            candidates=[chunk],
            threshold=0.3,  # High threshold
            current_time=now,
        )

        # Chunk should be filtered out due to low activation
        assert len(results) == 0

    def test_retrieve_sorts_by_activation(self):
        """Test that results are sorted by activation (descending)."""
        engine = ActivationEngine()
        retriever = ActivationRetriever(engine)
        now = datetime.now(timezone.utc)

        # Create chunks with different activation levels
        chunk_high = MockChunk(
            chunk_id="chunk_high",
            access_history=[
                AccessHistoryEntry(timestamp=now - timedelta(hours=1)),
                AccessHistoryEntry(timestamp=now - timedelta(hours=2)),
            ],
            last_access=now - timedelta(hours=1),
            keywords={"database", "optimize"},
        )

        chunk_medium = MockChunk(
            chunk_id="chunk_medium",
            access_history=[AccessHistoryEntry(timestamp=now - timedelta(days=1))],
            last_access=now - timedelta(days=1),
            keywords={"database"},
        )

        chunk_low = MockChunk(
            chunk_id="chunk_low",
            access_history=[AccessHistoryEntry(timestamp=now - timedelta(days=7))],
            last_access=now - timedelta(days=7),
            keywords=set(),
        )

        results = retriever.retrieve(
            candidates=[chunk_low, chunk_high, chunk_medium],
            query_keywords={"database", "optimize"},
            threshold=-10.0,  # Low threshold to include all
            current_time=now,
        )

        # Should be sorted by activation (high, medium, low)
        assert len(results) == 3
        assert results[0].chunk_id == "chunk_high"
        assert results[1].chunk_id == "chunk_medium"
        assert results[2].chunk_id == "chunk_low"

        # Check ranks are assigned correctly
        assert results[0].rank == 1
        assert results[1].rank == 2
        assert results[2].rank == 3

        # Verify activation ordering
        assert results[0].activation >= results[1].activation
        assert results[1].activation >= results[2].activation

    def test_retrieve_respects_max_results(self):
        """Test that max_results limits the number of returned chunks."""
        engine = ActivationEngine()
        config = RetrievalConfig(max_results=2)
        retriever = ActivationRetriever(engine, config)
        now = datetime.now(timezone.utc)

        # Create 5 chunks
        chunks = [
            MockChunk(
                chunk_id=f"chunk_{i}",
                access_history=[AccessHistoryEntry(timestamp=now - timedelta(hours=i))],
                last_access=now - timedelta(hours=i),
                keywords={"test"},
            )
            for i in range(1, 6)
        ]

        results = retriever.retrieve(candidates=chunks, threshold=-10.0, current_time=now)

        # Should return only 2 results
        assert len(results) == 2
        assert results[0].rank == 1
        assert results[1].rank == 2

    def test_retrieve_with_spreading_scores(self):
        """Test retrieval with pre-calculated spreading scores."""
        engine = ActivationEngine()
        retriever = ActivationRetriever(engine)
        now = datetime.now(timezone.utc)

        chunk = MockChunk(
            chunk_id="chunk_1",
            access_history=[AccessHistoryEntry(timestamp=now - timedelta(days=30))],
            last_access=now - timedelta(days=30),
            keywords=set(),
        )

        # Without spreading, activation is low
        results_no_spreading = retriever.retrieve(
            candidates=[chunk], spreading_scores={}, threshold=-10.0, current_time=now
        )

        # With spreading, activation is boosted
        results_with_spreading = retriever.retrieve(
            candidates=[chunk], spreading_scores={"chunk_1": 1.5}, threshold=-10.0, current_time=now
        )

        # Spreading should increase activation
        assert len(results_with_spreading) >= 1
        assert len(results_no_spreading) >= 1
        assert results_with_spreading[0].activation > results_no_spreading[0].activation

    def test_retrieve_include_components(self):
        """Test retrieval with component breakdown included."""
        engine = ActivationEngine()
        config = RetrievalConfig(include_components=True)
        retriever = ActivationRetriever(engine, config)
        now = datetime.now(timezone.utc)

        chunk = MockChunk(
            chunk_id="chunk_1",
            access_history=[AccessHistoryEntry(timestamp=now - timedelta(hours=1))],
            last_access=now - timedelta(hours=1),
            keywords={"database", "query"},
        )

        results = retriever.retrieve(
            candidates=[chunk], query_keywords={"database"}, threshold=-10.0, current_time=now
        )

        assert len(results) == 1
        assert results[0].components is not None
        assert results[0].components.bla is not None
        assert results[0].components.context_boost is not None

    def test_retrieve_without_components(self):
        """Test retrieval without component breakdown."""
        engine = ActivationEngine()
        config = RetrievalConfig(include_components=False)
        retriever = ActivationRetriever(engine, config)
        now = datetime.now(timezone.utc)

        chunk = MockChunk(
            chunk_id="chunk_1",
            access_history=[AccessHistoryEntry(timestamp=now - timedelta(hours=1))],
            last_access=now - timedelta(hours=1),
            keywords={"test"},
        )

        results = retriever.retrieve(candidates=[chunk], threshold=-10.0, current_time=now)

        assert len(results) == 1
        assert results[0].components is None


class TestActivationRetrieverWithGraph:
    """Test ActivationRetriever with relationship graph."""

    def test_retrieve_with_graph_no_sources(self):
        """Test retrieval with graph but no source chunks."""
        engine = ActivationEngine()
        retriever = ActivationRetriever(engine)
        now = datetime.now(timezone.utc)

        graph = RelationshipGraph()
        graph.add_relationship("chunk_a", "chunk_b", "calls")

        chunk = MockChunk(
            chunk_id="chunk_b",
            access_history=[AccessHistoryEntry(timestamp=now - timedelta(hours=1))],
            last_access=now - timedelta(hours=1),
            keywords={"test"},
        )

        results = retriever.retrieve_with_graph(
            candidates=[chunk],
            source_chunks=None,  # No sources
            relationship_graph=graph,
            threshold=-10.0,
            current_time=now,
        )

        # Should still retrieve, but without spreading
        assert len(results) == 1

    def test_retrieve_with_graph_and_sources(self):
        """Test retrieval with graph and source chunks."""
        engine = ActivationEngine()
        retriever = ActivationRetriever(engine)
        now = datetime.now(timezone.utc)

        # Create relationship graph
        graph = RelationshipGraph()
        graph.add_relationship("chunk_a", "chunk_b", "calls")
        graph.add_relationship("chunk_b", "chunk_c", "calls")

        chunks = [
            MockChunk(
                chunk_id="chunk_b",
                access_history=[AccessHistoryEntry(timestamp=now - timedelta(days=10))],
                last_access=now - timedelta(days=10),
                keywords=set(),
            ),
            MockChunk(
                chunk_id="chunk_c",
                access_history=[AccessHistoryEntry(timestamp=now - timedelta(days=10))],
                last_access=now - timedelta(days=10),
                keywords=set(),
            ),
        ]

        results = retriever.retrieve_with_graph(
            candidates=chunks,
            source_chunks=["chunk_a"],
            relationship_graph=graph,
            threshold=-10.0,
            current_time=now,
        )

        # Both chunks should be retrieved, chunk_b should have higher activation
        assert len(results) == 2
        assert results[0].chunk_id == "chunk_b"  # Closer to source
        assert results[1].chunk_id == "chunk_c"  # Further from source

    def test_retrieve_with_graph_no_graph(self):
        """Test retrieval with source chunks but no graph."""
        engine = ActivationEngine()
        retriever = ActivationRetriever(engine)
        now = datetime.now(timezone.utc)

        chunk = MockChunk(
            chunk_id="chunk_1",
            access_history=[AccessHistoryEntry(timestamp=now - timedelta(hours=1))],
            last_access=now - timedelta(hours=1),
            keywords={"test"},
        )

        results = retriever.retrieve_with_graph(
            candidates=[chunk],
            source_chunks=["chunk_a"],
            relationship_graph=None,  # No graph
            threshold=-10.0,
            current_time=now,
        )

        # Should still work, but no spreading activation
        assert len(results) == 1


class TestActivationRetrieverTopN:
    """Test top-N retrieval functionality."""

    def test_retrieve_top_n_no_threshold(self):
        """Test top-N retrieval ignores threshold."""
        engine = ActivationEngine()
        retriever = ActivationRetriever(engine)
        now = datetime.now(timezone.utc)

        # Create chunks with varying (low) activation
        chunks = [
            MockChunk(
                chunk_id=f"chunk_{i}",
                access_history=[AccessHistoryEntry(timestamp=now - timedelta(days=365))],
                last_access=now - timedelta(days=365),
                keywords=set(),
            )
            for i in range(5)
        ]

        results = retriever.retrieve_top_n(candidates=chunks, n=3, current_time=now)

        # Should return top 3, even though all have low activation
        assert len(results) == 3

    def test_retrieve_top_n_fewer_than_n(self):
        """Test top-N when candidates < n."""
        engine = ActivationEngine()
        retriever = ActivationRetriever(engine)
        now = datetime.now(timezone.utc)

        chunks = [
            MockChunk(
                chunk_id="chunk_1",
                access_history=[AccessHistoryEntry(timestamp=now - timedelta(hours=1))],
                last_access=now - timedelta(hours=1),
                keywords={"test"},
            )
        ]

        results = retriever.retrieve_top_n(candidates=chunks, n=5, current_time=now)

        # Should return only 1 result (all available)
        assert len(results) == 1

    def test_retrieve_top_n_with_spreading(self):
        """Test top-N retrieval with spreading scores."""
        engine = ActivationEngine()
        retriever = ActivationRetriever(engine)
        now = datetime.now(timezone.utc)

        chunks = [
            MockChunk(chunk_id=f"chunk_{i}", access_history=[], keywords=set()) for i in range(3)
        ]

        spreading_scores = {
            "chunk_0": 1.0,
            "chunk_1": 0.5,
            "chunk_2": 0.2,
        }

        results = retriever.retrieve_top_n(
            candidates=chunks, spreading_scores=spreading_scores, n=3, current_time=now
        )

        # Should be sorted by spreading (since no other activation)
        assert len(results) == 3
        assert results[0].chunk_id == "chunk_0"
        assert results[1].chunk_id == "chunk_1"
        assert results[2].chunk_id == "chunk_2"


class TestActivationCalculations:
    """Test activation calculation methods."""

    def test_calculate_activations_for_all_candidates(self):
        """Test calculating activations for all candidates without filtering."""
        engine = ActivationEngine()
        retriever = ActivationRetriever(engine)
        now = datetime.now(timezone.utc)

        chunks = [
            MockChunk(
                chunk_id="chunk_1",
                access_history=[AccessHistoryEntry(timestamp=now - timedelta(hours=1))],
                last_access=now - timedelta(hours=1),
                keywords={"database"},
            ),
            MockChunk(
                chunk_id="chunk_2",
                access_history=[AccessHistoryEntry(timestamp=now - timedelta(days=30))],
                last_access=now - timedelta(days=30),
                keywords={"network"},
            ),
        ]

        activations = retriever.calculate_activations(
            candidates=chunks, query_keywords={"database"}, current_time=now
        )

        # Should return activations for both chunks
        assert len(activations) == 2
        assert "chunk_1" in activations
        assert "chunk_2" in activations

        # chunk_1 should have higher activation
        assert activations["chunk_1"].total > activations["chunk_2"].total

    def test_calculate_activations_with_spreading(self):
        """Test calculating activations with spreading scores."""
        engine = ActivationEngine()
        retriever = ActivationRetriever(engine)
        now = datetime.now(timezone.utc)

        chunk = MockChunk(chunk_id="chunk_1", access_history=[], keywords=set())

        spreading_scores = {"chunk_1": 0.8}

        activations = retriever.calculate_activations(
            candidates=[chunk], spreading_scores=spreading_scores, current_time=now
        )

        assert "chunk_1" in activations
        assert activations["chunk_1"].spreading == 0.8


class TestExplainRetrieval:
    """Test retrieval explanation functionality."""

    def test_explain_retrieval_above_threshold(self):
        """Test explaining why a chunk was retrieved."""
        engine = ActivationEngine()
        config = RetrievalConfig(threshold=-10.0)  # Low threshold
        retriever = ActivationRetriever(engine, config)
        now = datetime.now(timezone.utc)

        chunk = MockChunk(
            chunk_id="chunk_1",
            access_history=[
                AccessHistoryEntry(timestamp=now - timedelta(hours=1)),
                AccessHistoryEntry(timestamp=now - timedelta(hours=2)),
            ],
            last_access=now - timedelta(hours=1),
            keywords={"database", "query"},
        )

        explanation = retriever.explain_retrieval(
            chunk=chunk, query_keywords={"database"}, spreading_score=0.5, current_time=now
        )

        assert explanation["chunk_id"] == "chunk_1"
        assert explanation["above_threshold"] is True
        assert "activation" in explanation
        assert "components" in explanation
        assert "threshold" in explanation
        assert "explanation" in explanation
        assert "retrieved" in explanation["explanation"].lower()

    def test_explain_retrieval_below_threshold(self):
        """Test explaining why a chunk was filtered out."""
        engine = ActivationEngine()
        config = RetrievalConfig(threshold=5.0)  # Very high threshold
        retriever = ActivationRetriever(engine, config)
        now = datetime.now(timezone.utc)

        chunk = MockChunk(
            chunk_id="chunk_1",
            access_history=[AccessHistoryEntry(timestamp=now - timedelta(days=365))],
            last_access=now - timedelta(days=365),
            keywords=set(),
        )

        explanation = retriever.explain_retrieval(
            chunk=chunk, spreading_score=0.0, current_time=now
        )

        assert explanation["chunk_id"] == "chunk_1"
        assert explanation["above_threshold"] is False
        assert "filtered out" in explanation["explanation"].lower()


class TestBatchRetriever:
    """Test BatchRetriever for large-scale retrieval."""

    def test_batch_retriever_initialization(self):
        """Test batch retriever initialization."""
        engine = ActivationEngine()
        retriever = BatchRetriever(engine, batch_size=50)

        assert retriever.retriever is not None
        assert retriever.batch_size == 50

    def test_batch_retriever_small_dataset(self):
        """Test batch retriever with dataset smaller than batch size."""
        engine = ActivationEngine()
        retriever = BatchRetriever(engine, batch_size=100)
        now = datetime.now(timezone.utc)

        chunks = [
            MockChunk(
                chunk_id=f"chunk_{i}",
                access_history=[AccessHistoryEntry(timestamp=now - timedelta(hours=i))],
                last_access=now - timedelta(hours=i),
                keywords={"test"},
            )
            for i in range(10)
        ]

        results = retriever.retrieve_batched(candidates=chunks, threshold=-10.0, current_time=now)

        # Should process all chunks in single batch
        assert len(results) == 10

    def test_batch_retriever_large_dataset(self):
        """Test batch retriever with dataset larger than batch size."""
        engine = ActivationEngine()
        retriever = BatchRetriever(engine, batch_size=10)
        now = datetime.now(timezone.utc)

        chunks = [
            MockChunk(
                chunk_id=f"chunk_{i}",
                access_history=[AccessHistoryEntry(timestamp=now - timedelta(hours=i))],
                last_access=now - timedelta(hours=i),
                keywords={"test"},
            )
            for i in range(25)  # 3 batches (10, 10, 5)
        ]

        results = retriever.retrieve_batched(
            candidates=chunks, threshold=-10.0, max_results=15, current_time=now
        )

        # Should return top 15 across all batches
        assert len(results) == 15

        # Should be sorted by activation
        for i in range(len(results) - 1):
            assert results[i].activation >= results[i + 1].activation

    def test_batch_retriever_respects_max_results(self):
        """Test batch retriever respects max_results limit."""
        engine = ActivationEngine()
        retriever = BatchRetriever(engine, batch_size=5)
        now = datetime.now(timezone.utc)

        chunks = [
            MockChunk(
                chunk_id=f"chunk_{i}",
                access_history=[AccessHistoryEntry(timestamp=now - timedelta(hours=i))],
                last_access=now - timedelta(hours=i),
                keywords={"test"},
            )
            for i in range(20)
        ]

        results = retriever.retrieve_batched(
            candidates=chunks, threshold=-10.0, max_results=5, current_time=now
        )

        assert len(results) == 5

    def test_batch_retriever_ranks_correctly(self):
        """Test batch retriever assigns ranks correctly across batches."""
        engine = ActivationEngine()
        retriever = BatchRetriever(engine, batch_size=3)
        now = datetime.now(timezone.utc)

        chunks = [
            MockChunk(
                chunk_id=f"chunk_{i}",
                access_history=[AccessHistoryEntry(timestamp=now - timedelta(hours=i))],
                last_access=now - timedelta(hours=i),
                keywords={"test"},
            )
            for i in range(10)
        ]

        results = retriever.retrieve_batched(candidates=chunks, threshold=-10.0, current_time=now)

        # Ranks should be sequential starting from 1
        for i, result in enumerate(results, start=1):
            assert result.rank == i


class TestRetrievalEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_retrieve_with_none_keywords(self):
        """Test retrieval with None keywords."""
        engine = ActivationEngine()
        retriever = ActivationRetriever(engine)
        now = datetime.now(timezone.utc)

        chunk = MockChunk(
            chunk_id="chunk_1",
            access_history=[AccessHistoryEntry(timestamp=now - timedelta(hours=1))],
            last_access=now - timedelta(hours=1),
            keywords={"test"},
        )

        results = retriever.retrieve(
            candidates=[chunk],
            query_keywords=None,  # No keywords
            threshold=-10.0,
            current_time=now,
        )

        # Should still work without context boost
        assert len(results) == 1

    def test_retrieve_with_empty_keywords(self):
        """Test retrieval with empty keyword sets."""
        engine = ActivationEngine()
        retriever = ActivationRetriever(engine)
        now = datetime.now(timezone.utc)

        chunk = MockChunk(
            chunk_id="chunk_1",
            access_history=[AccessHistoryEntry(timestamp=now - timedelta(hours=1))],
            last_access=now - timedelta(hours=1),
            keywords=set(),
        )

        results = retriever.retrieve(
            candidates=[chunk], query_keywords=set(), threshold=-10.0, current_time=now
        )

        # Should still work without context boost
        assert len(results) == 1

    def test_retrieve_chunk_never_accessed(self):
        """Test retrieving chunk with no access history."""
        engine = ActivationEngine()
        retriever = ActivationRetriever(engine)

        chunk = MockChunk(
            chunk_id="chunk_1", access_history=[], last_access=None, keywords={"test"}
        )

        results = retriever.retrieve(candidates=[chunk], query_keywords={"test"}, threshold=-10.0)

        # Should retrieve with default BLA
        assert len(results) == 1
        # Activation will be low due to default BLA
        assert results[0].activation < 0.0

    def test_retrieve_with_zero_threshold(self):
        """Test retrieval with threshold of 0.0."""
        engine = ActivationEngine()
        retriever = ActivationRetriever(engine)
        now = datetime.now(timezone.utc)

        chunk_positive = MockChunk(
            chunk_id="chunk_positive",
            access_history=[AccessHistoryEntry(timestamp=now - timedelta(hours=1))],
            last_access=now - timedelta(hours=1),
            keywords={"test"},
        )

        chunk_negative = MockChunk(
            chunk_id="chunk_negative",
            access_history=[AccessHistoryEntry(timestamp=now - timedelta(days=365))],
            last_access=now - timedelta(days=365),
            keywords=set(),
        )

        results = retriever.retrieve(
            candidates=[chunk_positive, chunk_negative], threshold=0.0, current_time=now
        )

        # Only chunks with positive activation should be retrieved
        assert all(r.activation >= 0.0 for r in results)

    def test_retrieve_override_config_threshold(self):
        """Test that retrieval threshold can be overridden."""
        engine = ActivationEngine()
        config = RetrievalConfig(threshold=5.0)  # Very high threshold
        retriever = ActivationRetriever(engine, config)
        now = datetime.now(timezone.utc)

        chunk = MockChunk(
            chunk_id="chunk_1",
            access_history=[AccessHistoryEntry(timestamp=now - timedelta(hours=1))],
            last_access=now - timedelta(hours=1),
            keywords={"test"},
        )

        # Override with lower threshold
        results = retriever.retrieve(candidates=[chunk], threshold=-10.0, current_time=now)

        # Should retrieve with overridden threshold
        assert len(results) == 1

    def test_retrieve_override_max_results(self):
        """Test that max_results can be overridden."""
        engine = ActivationEngine()
        config = RetrievalConfig(max_results=2)
        retriever = ActivationRetriever(engine, config)
        now = datetime.now(timezone.utc)

        chunks = [
            MockChunk(
                chunk_id=f"chunk_{i}",
                access_history=[AccessHistoryEntry(timestamp=now - timedelta(hours=i))],
                last_access=now - timedelta(hours=i),
                keywords={"test"},
            )
            for i in range(5)
        ]

        # Override with higher max
        results = retriever.retrieve(
            candidates=chunks, threshold=-10.0, max_results=4, current_time=now
        )

        # Should return 4 results
        assert len(results) == 4

    def test_retrieve_no_sorting(self):
        """Test retrieval with sorting disabled."""
        engine = ActivationEngine()
        config = RetrievalConfig(sort_by_activation=False)
        retriever = ActivationRetriever(engine, config)
        now = datetime.now(timezone.utc)

        chunks = [
            MockChunk(
                chunk_id="chunk_low",
                access_history=[AccessHistoryEntry(timestamp=now - timedelta(days=7))],
                last_access=now - timedelta(days=7),
                keywords=set(),
            ),
            MockChunk(
                chunk_id="chunk_high",
                access_history=[AccessHistoryEntry(timestamp=now - timedelta(hours=1))],
                last_access=now - timedelta(hours=1),
                keywords={"test"},
            ),
        ]

        results = retriever.retrieve(candidates=chunks, threshold=-10.0, current_time=now)

        # With sorting disabled, order might not be by activation
        # (depends on insertion order), but all should still be ranked
        assert len(results) == 2
        assert all(r.rank > 0 for r in results)

    def test_retrieve_identical_activations(self):
        """Test retrieval when chunks have identical activation."""
        engine = ActivationEngine()
        retriever = ActivationRetriever(engine)
        now = datetime.now(timezone.utc)

        # Create chunks with identical access patterns
        chunks = [
            MockChunk(
                chunk_id=f"chunk_{i}",
                access_history=[AccessHistoryEntry(timestamp=now - timedelta(hours=1))],
                last_access=now - timedelta(hours=1),
                keywords={"test"},
            )
            for i in range(3)
        ]

        results = retriever.retrieve(
            candidates=chunks, query_keywords={"test"}, threshold=-10.0, current_time=now
        )

        # All should be retrieved
        assert len(results) == 3

        # All should have same activation
        assert results[0].activation == pytest.approx(results[1].activation, abs=0.001)
        assert results[1].activation == pytest.approx(results[2].activation, abs=0.001)
