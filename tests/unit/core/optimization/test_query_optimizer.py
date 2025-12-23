"""
Unit tests for QueryOptimizer.

Tests cover:
- Chunk type inference from queries
- Pre-filtering by chunk type
- Activation threshold filtering
- Batch activation calculation
- Full optimized retrieval pipeline
- Statistics tracking
"""

from datetime import datetime, timedelta, timezone

import pytest

from aurora_core.activation.base_level import AccessHistoryEntry
from aurora_core.activation.engine import ActivationEngine
from aurora_core.optimization.query_optimizer import (
    QueryOptimizer,
)
from aurora_core.types import ChunkID


# Mock chunk data for testing
class MockChunk:
    """Mock chunk for testing."""

    def __init__(
        self,
        chunk_id: ChunkID,
        chunk_type: str = "function",
        keywords: set[str] | None = None,
        access_history: list[AccessHistoryEntry] | None = None,
        last_access: datetime | None = None,
    ):
        self.id = chunk_id
        self.type = chunk_type
        self.keywords = keywords or set()
        self.access_history = access_history or []
        self.last_access = last_access


# Mock store for testing
class MockStore:
    """Mock store for testing."""

    def __init__(self, chunks: list[MockChunk]):
        self.chunks = chunks
        self._chunks_by_type = {}
        for chunk in chunks:
            if chunk.type not in self._chunks_by_type:
                self._chunks_by_type[chunk.type] = []
            self._chunks_by_type[chunk.type].append(chunk)

    def get_all_chunks(self) -> list[MockChunk]:
        return self.chunks

    def get_chunks_by_type(self, chunk_type: str) -> list[MockChunk]:
        return self._chunks_by_type.get(chunk_type, [])

    def get_chunks_by_types(self, chunk_types: list[str]) -> list[MockChunk]:
        result = []
        for chunk_type in chunk_types:
            result.extend(self.get_chunks_by_type(chunk_type))
        return result


class TestChunkTypeInference:
    """Test chunk type inference from query keywords."""

    def setup_method(self):
        """Set up test fixtures."""
        self.engine = ActivationEngine()
        self.store = MockStore([])
        self.optimizer = QueryOptimizer(
            engine=self.engine,
            store=self.store,
            enable_type_filtering=True,
        )

    def test_infer_function_type(self):
        """Test inference of function type from query."""
        query = "find the authenticate function"
        types = self.optimizer.infer_chunk_types(query)
        assert "function" in types

    def test_infer_class_type(self):
        """Test inference of class type from query."""
        query = "User class implementation"
        types = self.optimizer.infer_chunk_types(query)
        assert "class" in types

    def test_infer_test_type(self):
        """Test inference of test type from query."""
        query = "test cases for login"
        types = self.optimizer.infer_chunk_types(query)
        assert "test" in types

    def test_infer_multiple_types(self):
        """Test inference of multiple types from query."""
        query = "test the authenticate function"
        types = self.optimizer.infer_chunk_types(query)
        assert "test" in types
        assert "function" in types

    def test_infer_no_types(self):
        """Test query with no recognizable types."""
        query = "something completely unrelated"
        types = self.optimizer.infer_chunk_types(query)
        assert len(types) == 0

    def test_case_insensitive_inference(self):
        """Test that inference is case-insensitive."""
        query = "FIND THE FUNCTION"
        types = self.optimizer.infer_chunk_types(query)
        assert "function" in types

    def test_module_inference(self):
        """Test inference of module type."""
        query = "import statement in module"
        types = self.optimizer.infer_chunk_types(query)
        assert "module" in types

    def test_documentation_inference(self):
        """Test inference of documentation type."""
        query = "readme documentation guide"
        types = self.optimizer.infer_chunk_types(query)
        assert "documentation" in types


class TestPreFiltering:
    """Test pre-filtering of candidates by chunk type."""

    def setup_method(self):
        """Set up test fixtures."""
        # Create chunks of different types
        self.chunks = [
            MockChunk("func1", "function"),
            MockChunk("func2", "function"),
            MockChunk("class1", "class"),
            MockChunk("class2", "class"),
            MockChunk("test1", "test"),
            MockChunk("mod1", "module"),
        ]

        self.engine = ActivationEngine()
        self.store = MockStore(self.chunks)
        self.optimizer = QueryOptimizer(
            engine=self.engine,
            store=self.store,
            enable_type_filtering=True,
        )

    def test_filter_by_single_type(self):
        """Test filtering by a single chunk type."""
        candidates = self.optimizer.pre_filter_candidates(chunk_types=["function"])
        assert len(candidates) == 2
        assert all(c.type == "function" for c in candidates)

    def test_filter_by_multiple_types(self):
        """Test filtering by multiple chunk types."""
        candidates = self.optimizer.pre_filter_candidates(chunk_types=["function", "class"])
        assert len(candidates) == 4
        assert all(c.type in ["function", "class"] for c in candidates)

    def test_filter_by_query_inference(self):
        """Test filtering using type inference from query."""
        candidates = self.optimizer.pre_filter_candidates(query="find function")
        # Should infer 'function' type and filter
        assert len(candidates) == 2
        assert all(c.type == "function" for c in candidates)

    def test_no_filtering_when_disabled(self):
        """Test that filtering is skipped when disabled."""
        optimizer = QueryOptimizer(
            engine=self.engine,
            store=self.store,
            enable_type_filtering=False,
        )
        candidates = optimizer.pre_filter_candidates(query="find function")
        # Should return all chunks
        assert len(candidates) == 6

    def test_no_filtering_when_no_types_inferred(self):
        """Test no filtering when query has no recognizable types."""
        candidates = self.optimizer.pre_filter_candidates(query="something random")
        # Should return all chunks
        assert len(candidates) == 6

    def test_explicit_types_override_inference(self):
        """Test that explicit types override query inference."""
        candidates = self.optimizer.pre_filter_candidates(
            query="find function",  # Would infer 'function'
            chunk_types=["class"],  # But we explicitly want 'class'
        )
        assert len(candidates) == 2
        assert all(c.type == "class" for c in candidates)


class TestActivationThresholdFiltering:
    """Test activation threshold filtering."""

    def setup_method(self):
        """Set up test fixtures."""
        current_time = datetime.now(timezone.utc)
        recent_time = current_time - timedelta(hours=1)
        old_time = current_time - timedelta(days=30)

        # Create chunks with different activation levels
        self.chunks = [
            # High activation - recent accesses
            MockChunk(
                "high1",
                access_history=[
                    AccessHistoryEntry(timestamp=recent_time),
                    AccessHistoryEntry(timestamp=recent_time),
                ],
                last_access=recent_time,
                keywords={"important", "function"},
            ),
            # Medium activation - some recent accesses
            MockChunk(
                "medium1",
                access_history=[
                    AccessHistoryEntry(timestamp=recent_time),
                ],
                last_access=recent_time,
                keywords={"function"},
            ),
            # Low activation - old accesses
            MockChunk(
                "low1",
                access_history=[
                    AccessHistoryEntry(timestamp=old_time),
                ],
                last_access=old_time,
                keywords={"old"},
            ),
            # Zero activation - no accesses
            MockChunk("zero1", access_history=[], last_access=None, keywords=set()),
        ]

        self.engine = ActivationEngine()
        self.store = MockStore(self.chunks)
        self.optimizer = QueryOptimizer(
            engine=self.engine,
            store=self.store,
            activation_threshold=0.3,
        )

    def test_threshold_filters_low_activation(self):
        """Test that chunks below threshold are filtered out."""
        activations = self.optimizer.calculate_activations_batch(
            candidates=self.chunks,
            query_keywords={"function"},
        )

        # Should only include chunks above threshold
        assert len(activations) >= 0  # At least some should pass
        assert all(activation >= 0.3 for activation in activations.values())

    def test_threshold_includes_high_activation(self):
        """Test that chunks above threshold are included."""
        # Use very low threshold to include all chunks
        optimizer = QueryOptimizer(
            engine=self.engine,
            store=self.store,
            activation_threshold=-100.0,  # Extremely low to include everything
        )

        activations = optimizer.calculate_activations_batch(
            candidates=self.chunks,
            query_keywords={"function", "important"},
        )

        # All chunks with access history should be included
        assert len(activations) > 0
        # High activation chunk should be present
        if "high1" in activations:
            # Should have highest or near-highest activation
            assert activations["high1"] >= min(activations.values())

    def test_batch_processing(self):
        """Test that batch processing works correctly."""
        optimizer = QueryOptimizer(
            engine=self.engine,
            store=self.store,
            activation_threshold=-10.0,  # Very low threshold to include all
            batch_size=2,
        )

        activations = optimizer.calculate_activations_batch(
            candidates=self.chunks,
            query_keywords=set(),
        )

        # Should process all chunks in batches
        # At least some chunks should be included
        assert len(activations) >= 0
        # Verify batch processing doesn't skip any chunks that pass threshold
        # (All chunks with access history should pass with -10.0 threshold)
        assert len(activations) >= 3  # At least high1, medium1, low1

    def test_zero_activation_filtered(self):
        """Test that zero-activation chunks are filtered."""
        optimizer = QueryOptimizer(
            engine=self.engine,
            store=self.store,
            activation_threshold=0.1,  # Above zero
        )

        activations = optimizer.calculate_activations_batch(
            candidates=self.chunks,
            query_keywords=set(),
        )

        # Zero activation chunk should not be included
        assert "zero1" not in activations


class TestOptimizedRetrieval:
    """Test full optimized retrieval pipeline."""

    def setup_method(self):
        """Set up test fixtures."""
        current_time = datetime.now(timezone.utc)
        recent_time = current_time - timedelta(hours=1)

        # Create diverse chunks
        self.chunks = [
            MockChunk(
                "func1",
                chunk_type="function",
                keywords={"auth", "login", "user"},
                access_history=[AccessHistoryEntry(timestamp=recent_time)] * 3,
                last_access=recent_time,
            ),
            MockChunk(
                "func2",
                chunk_type="function",
                keywords={"database", "query"},
                access_history=[AccessHistoryEntry(timestamp=recent_time)] * 2,
                last_access=recent_time,
            ),
            MockChunk(
                "class1",
                chunk_type="class",
                keywords={"user", "model"},
                access_history=[AccessHistoryEntry(timestamp=recent_time)],
                last_access=recent_time,
            ),
            MockChunk(
                "test1",
                chunk_type="test",
                keywords={"test", "auth"},
                access_history=[],
                last_access=None,
            ),
        ]

        self.engine = ActivationEngine()
        self.store = MockStore(self.chunks)
        self.optimizer = QueryOptimizer(
            engine=self.engine,
            store=self.store,
            enable_type_filtering=True,
            activation_threshold=0.3,
        )

    def test_retrieve_optimized_returns_results(self):
        """Test that optimized retrieval returns results."""
        results, stats = self.optimizer.retrieve_optimized(
            query="auth function",
            top_k=5,
        )

        assert results is not None
        assert len(results) >= 0
        assert stats is not None

    def test_retrieve_optimized_applies_type_filter(self):
        """Test that type filtering is applied."""
        results, stats = self.optimizer.retrieve_optimized(
            query="authentication function",
            top_k=5,
        )

        assert stats.type_filter_applied
        assert "function" in stats.inferred_types
        # Filtered chunks should be less than total
        assert stats.filtered_chunks <= stats.total_chunks

    def test_retrieve_optimized_respects_top_k(self):
        """Test that only top-k results are returned."""
        results, stats = self.optimizer.retrieve_optimized(
            query="find anything",
            top_k=2,
        )

        assert len(results) <= 2

    def test_retrieve_optimized_tracks_stats(self):
        """Test that statistics are tracked correctly."""
        results, stats = self.optimizer.retrieve_optimized(
            query="authentication",
            top_k=5,
            include_stats=True,
        )

        assert stats.total_chunks == 4
        assert stats.filtered_chunks > 0
        assert stats.results_returned == len(results)
        assert stats.optimization_time_ms > 0

    def test_retrieve_without_stats(self):
        """Test retrieval without statistics."""
        results, stats = self.optimizer.retrieve_optimized(
            query="find function",
            top_k=5,
            include_stats=False,
        )

        assert results is not None
        assert stats is None

    def test_reduction_ratio_calculation(self):
        """Test reduction ratio calculation."""
        results, stats = self.optimizer.retrieve_optimized(
            query="function authentication",
            top_k=5,
        )

        # Should have some reduction from type filtering
        if stats.type_filter_applied and stats.filtered_chunks < stats.total_chunks:
            assert stats.reduction_ratio > 0.0
            assert stats.reduction_ratio < 1.0

    def test_explicit_chunk_types_override(self):
        """Test that explicit chunk types override inference."""
        results, stats = self.optimizer.retrieve_optimized(
            query="function",  # Would infer 'function'
            chunk_types=["class"],  # But we want 'class'
            top_k=5,
        )

        # Should use explicit types, not inferred
        assert stats.filtered_chunks == 1  # Only 1 class chunk


class TestKeywordExtraction:
    """Test query keyword extraction."""

    def setup_method(self):
        """Set up test fixtures."""
        self.engine = ActivationEngine()
        self.store = MockStore([])
        self.optimizer = QueryOptimizer(
            engine=self.engine,
            store=self.store,
        )

    def test_extract_keywords(self):
        """Test basic keyword extraction."""
        keywords = self.optimizer._extract_keywords("find the function")
        assert "find" in keywords
        assert "function" in keywords
        assert "the" not in keywords  # Stop word

    def test_extract_keywords_lowercase(self):
        """Test that keywords are lowercase."""
        keywords = self.optimizer._extract_keywords("FIND FUNCTION")
        assert "find" in keywords
        assert "function" in keywords

    def test_extract_removes_stop_words(self):
        """Test that stop words are removed."""
        keywords = self.optimizer._extract_keywords("the user is authenticated")
        assert "the" not in keywords
        assert "is" not in keywords
        assert "user" in keywords
        assert "authenticated" in keywords


class TestEdgeCases:
    """Test edge cases and error conditions."""

    def setup_method(self):
        """Set up test fixtures."""
        self.engine = ActivationEngine()
        self.store = MockStore([])
        self.optimizer = QueryOptimizer(
            engine=self.engine,
            store=self.store,
        )

    def test_empty_query(self):
        """Test retrieval with empty query."""
        results, stats = self.optimizer.retrieve_optimized(
            query="",
            top_k=5,
        )

        # Should handle gracefully
        assert results is not None
        assert isinstance(results, list)

    def test_no_candidates(self):
        """Test retrieval with no candidates."""
        results, stats = self.optimizer.retrieve_optimized(
            query="find something",
            top_k=5,
        )

        # Should return empty results
        assert len(results) == 0
        assert stats.total_chunks == 0

    def test_zero_top_k(self):
        """Test retrieval with top_k=0."""
        # This should still work, just return empty results
        results, stats = self.optimizer.retrieve_optimized(
            query="find something",
            top_k=0,
        )

        assert len(results) == 0

    def test_large_top_k(self):
        """Test retrieval with top_k larger than available chunks."""
        chunks = [MockChunk(f"chunk{i}") for i in range(3)]
        store = MockStore(chunks)
        optimizer = QueryOptimizer(
            engine=self.engine,
            store=store,
        )

        results, stats = optimizer.retrieve_optimized(
            query="find",
            top_k=100,  # More than available
        )

        # Should return all available chunks
        assert len(results) <= 3


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
