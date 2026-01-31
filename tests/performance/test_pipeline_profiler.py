"""Pipeline profiler for measuring time spent in each search component.

This module profiles the memory search pipeline to measure time spent in:
- BM25 keyword retrieval (tokenization, index building, scoring)
- ACT-R activation retrieval (database query, chunk deserialization)
- Semantic similarity (query embedding, cosine similarity computation)
- Score normalization and hybrid scoring

Usage:
    pytest tests/performance/test_pipeline_profiler.py -v -s

Output includes:
- Per-component timing breakdowns
- Percentage of total search time per component
- Recommendations for optimization
"""

import json
import time
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Generator
from unittest.mock import MagicMock

import numpy as np
import pytest

pytestmark = [pytest.mark.performance]


@dataclass
class TimingStats:
    """Statistics for a timing measurement."""

    name: str
    total_ms: float = 0.0
    calls: int = 0
    min_ms: float = float("inf")
    max_ms: float = 0.0
    samples: list[float] = field(default_factory=list)

    def record(self, duration_ms: float) -> None:
        """Record a timing sample."""
        self.total_ms += duration_ms
        self.calls += 1
        self.min_ms = min(self.min_ms, duration_ms)
        self.max_ms = max(self.max_ms, duration_ms)
        self.samples.append(duration_ms)

    @property
    def avg_ms(self) -> float:
        """Average duration in milliseconds."""
        return self.total_ms / self.calls if self.calls > 0 else 0.0

    @property
    def median_ms(self) -> float:
        """Median duration in milliseconds."""
        if not self.samples:
            return 0.0
        sorted_samples = sorted(self.samples)
        mid = len(sorted_samples) // 2
        if len(sorted_samples) % 2 == 0:
            return (sorted_samples[mid - 1] + sorted_samples[mid]) / 2
        return sorted_samples[mid]

    def summary(self) -> str:
        """Return a summary string."""
        if self.calls == 0:
            return f"{self.name}: no samples"
        return (
            f"{self.name}: total={self.total_ms:.2f}ms, "
            f"calls={self.calls}, avg={self.avg_ms:.2f}ms, "
            f"median={self.median_ms:.2f}ms, "
            f"min={self.min_ms:.2f}ms, max={self.max_ms:.2f}ms"
        )


class PipelineProfiler:
    """Profiler for search pipeline components."""

    def __init__(self):
        self.timings: dict[str, TimingStats] = {}
        self.search_start: float = 0.0
        self.search_end: float = 0.0

    def _get_stats(self, name: str) -> TimingStats:
        """Get or create timing stats for a component."""
        if name not in self.timings:
            self.timings[name] = TimingStats(name=name)
        return self.timings[name]

    @contextmanager
    def measure(self, name: str) -> Generator[None, None, None]:
        """Context manager to measure a code section."""
        start = time.perf_counter()
        try:
            yield
        finally:
            duration_ms = (time.perf_counter() - start) * 1000
            self._get_stats(name).record(duration_ms)

    def start_search(self) -> None:
        """Mark the start of a search operation."""
        self.search_start = time.perf_counter()

    def end_search(self) -> None:
        """Mark the end of a search operation."""
        self.search_end = time.perf_counter()

    @property
    def total_search_ms(self) -> float:
        """Total search time in milliseconds."""
        return (self.search_end - self.search_start) * 1000

    def report(self) -> str:
        """Generate a profiling report."""
        lines = [
            "\n" + "=" * 70,
            "PIPELINE PROFILER REPORT",
            "=" * 70,
            f"\nTotal search time: {self.total_search_ms:.2f}ms\n",
            "-" * 70,
            "Component Breakdown:",
            "-" * 70,
        ]

        # Sort by total time descending
        sorted_stats = sorted(
            self.timings.values(),
            key=lambda s: s.total_ms,
            reverse=True,
        )

        for stats in sorted_stats:
            pct = (stats.total_ms / self.total_search_ms * 100) if self.total_search_ms > 0 else 0
            lines.append(f"\n{stats.name}:")
            lines.append(f"  Total: {stats.total_ms:>8.2f}ms ({pct:>5.1f}%)")
            lines.append(f"  Calls: {stats.calls:>8}")
            lines.append(f"  Avg:   {stats.avg_ms:>8.2f}ms")
            lines.append(f"  Min:   {stats.min_ms:>8.2f}ms")
            lines.append(f"  Max:   {stats.max_ms:>8.2f}ms")

        lines.append("\n" + "=" * 70)
        return "\n".join(lines)

    def to_dict(self) -> dict[str, Any]:
        """Export profiling data as dictionary."""
        return {
            "total_search_ms": self.total_search_ms,
            "components": {
                name: {
                    "total_ms": stats.total_ms,
                    "calls": stats.calls,
                    "avg_ms": stats.avg_ms,
                    "min_ms": stats.min_ms if stats.min_ms != float("inf") else 0,
                    "max_ms": stats.max_ms,
                    "pct_of_total": (
                        (stats.total_ms / self.total_search_ms * 100)
                        if self.total_search_ms > 0
                        else 0
                    ),
                }
                for name, stats in self.timings.items()
            },
        }


@pytest.fixture
def profiled_store(tmp_path: Path) -> Generator[tuple[Any, PipelineProfiler], None, None]:
    """Create a store with test data and a profiler."""
    from aurora_core.chunks import CodeChunk
    from aurora_core.store.sqlite import SQLiteStore

    db_path = tmp_path / "test_memory.db"
    store = SQLiteStore(str(db_path))
    profiler = PipelineProfiler()

    # Add test chunks with embeddings
    for i in range(100):  # 100 chunks for realistic profiling
        # Use absolute path as required by CodeChunk
        file_path = str(tmp_path / f"module_{i // 10}" / f"file_{i}.py")
        chunk = CodeChunk(
            chunk_id=f"chunk-{i}",
            file_path=file_path,
            element_type="function",
            name=f"test_function_{i}",
            line_start=i * 10 + 1,
            line_end=i * 10 + 10,
            signature=f"def test_function_{i}(arg1, arg2):",
            docstring=f"Test function {i} for authentication, validation, and user session management.",
            language="python",
        )
        # Add a fake embedding (384-dim float32)
        chunk.embeddings = np.random.randn(384).astype(np.float32).tobytes()
        store.save_chunk(chunk)

        # Set some activation scores
        with store._transaction() as conn:
            conn.execute(
                "UPDATE activations SET base_level = ? WHERE chunk_id = ?",
                (np.random.uniform(-1, 2), chunk.id),
            )

    yield store, profiler
    store.close()


class TestActivationRetrieval:
    """Profile ACT-R activation retrieval component."""

    def test_profile_activation_retrieval(
        self,
        profiled_store: tuple[Any, PipelineProfiler],
    ):
        """Profile time spent in activation-based retrieval."""
        store, profiler = profiled_store

        # Warm up
        store.retrieve_by_activation(min_activation=0.0, limit=10)

        profiler.start_search()

        # Profile activation retrieval
        with profiler.measure("activation_retrieval"):
            candidates = store.retrieve_by_activation(min_activation=0.0, limit=500)

        profiler.end_search()

        print(profiler.report())

        assert len(candidates) > 0
        # Activation retrieval should be fast (<100ms for 500 chunks)
        assert (
            profiler.timings["activation_retrieval"].total_ms < 100
        ), f"Activation retrieval too slow: {profiler.timings['activation_retrieval'].total_ms:.2f}ms"


class TestBM25Components:
    """Profile BM25 keyword retrieval components."""

    def test_profile_bm25_tokenization(self):
        """Profile BM25 tokenization performance."""
        from aurora_context_code.semantic.bm25_scorer import tokenize

        profiler = PipelineProfiler()

        test_texts = [
            "getUserAuthenticationToken",
            "validate_user_session_context",
            "HTTPRequestHandler.process_api_request",
            "def authenticate(user, password): return verify_credentials(user, password)",
            "class UserSessionManager: def __init__(self): self.sessions = {}",
        ] * 100  # 500 total tokenizations

        profiler.start_search()

        for text in test_texts:
            with profiler.measure("bm25_tokenization"):
                tokenize(text)

        profiler.end_search()

        print(profiler.report())

        avg_ms = profiler.timings["bm25_tokenization"].avg_ms
        assert avg_ms < 1.0, f"BM25 tokenization too slow: {avg_ms:.3f}ms per call"

    def test_profile_bm25_index_building(self, profiled_store: tuple[Any, PipelineProfiler]):
        """Profile BM25 index building performance."""
        from aurora_context_code.semantic.bm25_scorer import BM25Scorer

        store, profiler = profiled_store
        candidates = store.retrieve_by_activation(min_activation=0.0, limit=500)

        # Prepare documents for indexing
        documents = []
        for chunk in candidates:
            content = ""
            if hasattr(chunk, "name"):
                content += chunk.name + " "
            if hasattr(chunk, "signature"):
                content += (chunk.signature or "") + " "
            if hasattr(chunk, "docstring"):
                content += chunk.docstring or ""
            documents.append((chunk.id, content))

        profiler.start_search()

        with profiler.measure("bm25_index_build"):
            scorer = BM25Scorer(k1=1.5, b=0.75)
            scorer.build_index(documents)

        profiler.end_search()

        print(profiler.report())

        build_time = profiler.timings["bm25_index_build"].total_ms
        assert build_time < 200, f"BM25 index build too slow: {build_time:.2f}ms"

    def test_profile_bm25_scoring(self, profiled_store: tuple[Any, PipelineProfiler]):
        """Profile BM25 scoring performance."""
        from aurora_context_code.semantic.bm25_scorer import BM25Scorer

        store, profiler = profiled_store
        candidates = store.retrieve_by_activation(min_activation=0.0, limit=100)

        # Build index first
        documents = []
        for chunk in candidates:
            content = ""
            if hasattr(chunk, "name"):
                content += chunk.name + " "
            if hasattr(chunk, "signature"):
                content += (chunk.signature or "") + " "
            if hasattr(chunk, "docstring"):
                content += chunk.docstring or ""
            documents.append((chunk.id, content))

        scorer = BM25Scorer(k1=1.5, b=0.75)
        scorer.build_index(documents)

        query = "authentication user session"

        profiler.start_search()

        # Score all candidates
        for doc_id, doc_content in documents:
            with profiler.measure("bm25_score_single"):
                scorer.score(query, doc_content)

        profiler.end_search()

        print(profiler.report())

        avg_ms = profiler.timings["bm25_score_single"].avg_ms
        assert avg_ms < 1.0, f"BM25 scoring too slow: {avg_ms:.3f}ms per document"


class TestSemanticComponents:
    """Profile semantic similarity components."""

    def test_profile_cosine_similarity(self, profiled_store: tuple[Any, PipelineProfiler]):
        """Profile cosine similarity computation."""
        from aurora_context_code.semantic.embedding_provider import cosine_similarity

        store, profiler = profiled_store

        # Generate random embeddings for testing
        query_embedding = np.random.randn(384).astype(np.float32)
        chunk_embeddings = [np.random.randn(384).astype(np.float32) for _ in range(100)]

        profiler.start_search()

        for chunk_embedding in chunk_embeddings:
            with profiler.measure("cosine_similarity"):
                cosine_similarity(query_embedding, chunk_embedding)

        profiler.end_search()

        print(profiler.report())

        avg_ms = profiler.timings["cosine_similarity"].avg_ms
        assert avg_ms < 0.1, f"Cosine similarity too slow: {avg_ms:.3f}ms per call"

    def test_profile_embedding_bytes_conversion(self):
        """Profile embedding bytes-to-array conversion."""
        profiler = PipelineProfiler()

        # Simulate stored embeddings (bytes)
        stored_embeddings = [np.random.randn(384).astype(np.float32).tobytes() for _ in range(100)]

        profiler.start_search()

        for embedding_bytes in stored_embeddings:
            with profiler.measure("embedding_bytes_to_array"):
                np.frombuffer(embedding_bytes, dtype=np.float32)

        profiler.end_search()

        print(profiler.report())

        avg_ms = profiler.timings["embedding_bytes_to_array"].avg_ms
        assert avg_ms < 0.01, f"Bytes conversion too slow: {avg_ms:.4f}ms per call"


class TestFullPipelineProfile:
    """Profile the complete search pipeline with detailed breakdown."""

    def test_profile_hybrid_retriever(self, profiled_store: tuple[Any, PipelineProfiler]):
        """Profile the full HybridRetriever.retrieve() method."""
        from aurora_context_code.semantic.bm25_scorer import BM25Scorer
        from aurora_context_code.semantic.embedding_provider import cosine_similarity

        store, profiler = profiled_store

        # Create mock embedding provider that returns quickly
        mock_provider = MagicMock()
        mock_provider.embed_query.return_value = np.random.randn(384).astype(np.float32)

        query = "authentication user session validation"
        top_k = 10
        activation_top_k = 500
        stage1_top_k = 100

        profiler.start_search()

        # Phase 1: Activation Retrieval
        with profiler.measure("phase1_activation_retrieval"):
            candidates = store.retrieve_by_activation(
                min_activation=0.0,
                limit=activation_top_k,
            )

        # Phase 2: Query Embedding
        with profiler.measure("phase2_query_embedding"):
            query_embedding = mock_provider.embed_query(query)

        # Phase 3: BM25 Index Building
        with profiler.measure("phase3_bm25_prepare_docs"):
            documents = []
            for chunk in candidates:
                content = ""
                if hasattr(chunk, "name"):
                    content += chunk.name + " "
                if hasattr(chunk, "signature"):
                    content += (chunk.signature or "") + " "
                if hasattr(chunk, "docstring"):
                    content += chunk.docstring or ""
                documents.append((chunk.id, content))

        with profiler.measure("phase3_bm25_index_build"):
            bm25_scorer = BM25Scorer(k1=1.5, b=0.75)
            bm25_scorer.build_index(documents)

        # Phase 4: BM25 Filtering (Stage 1)
        with profiler.measure("phase4_bm25_scoring"):
            scored_candidates = []
            for chunk, (doc_id, doc_content) in zip(candidates, documents):
                bm25_score = bm25_scorer.score(query, doc_content)
                scored_candidates.append((bm25_score, chunk, doc_content))

        with profiler.measure("phase4_bm25_sort"):
            scored_candidates.sort(key=lambda x: x[0], reverse=True)
            stage1_candidates = scored_candidates[:stage1_top_k]

        # Phase 5: Semantic Similarity (Stage 2 re-ranking)
        with profiler.measure("phase5_semantic_similarity"):
            results = []
            for bm25_score, chunk, doc_content in stage1_candidates:
                activation_score = getattr(chunk, "activation", 0.0)

                # Get chunk embedding
                chunk_embedding = getattr(chunk, "embeddings", None)
                if chunk_embedding is not None and isinstance(chunk_embedding, bytes):
                    chunk_embedding = np.frombuffer(chunk_embedding, dtype=np.float32)

                if chunk_embedding is not None:
                    semantic_score = cosine_similarity(query_embedding, chunk_embedding)
                    semantic_score = (semantic_score + 1.0) / 2.0
                else:
                    semantic_score = 0.0

                results.append(
                    {
                        "chunk": chunk,
                        "bm25_score": bm25_score,
                        "activation_score": activation_score,
                        "semantic_score": semantic_score,
                    }
                )

        # Phase 6: Score Normalization and Hybrid Scoring
        with profiler.measure("phase6_score_normalization"):
            # Normalize scores
            def normalize_scores(scores):
                if not scores:
                    return []
                min_s, max_s = min(scores), max(scores)
                if max_s - min_s < 1e-9:
                    return list(scores)
                return [(s - min_s) / (max_s - min_s) for s in scores]

            bm25_scores = [r["bm25_score"] for r in results]
            activation_scores = [r["activation_score"] for r in results]
            semantic_scores = [r["semantic_score"] for r in results]

            bm25_norm = normalize_scores(bm25_scores)
            activation_norm = normalize_scores(activation_scores)
            semantic_norm = normalize_scores(semantic_scores)

        with profiler.measure("phase6_hybrid_scoring"):
            # Weights: BM25=0.3, Activation=0.3, Semantic=0.4
            for i, result in enumerate(results):
                hybrid_score = (
                    0.3 * bm25_norm[i] + 0.3 * activation_norm[i] + 0.4 * semantic_norm[i]
                )
                result["hybrid_score"] = hybrid_score

        # Phase 7: Final Sort and Top-K
        with profiler.measure("phase7_final_sort"):
            results.sort(key=lambda x: x["hybrid_score"], reverse=True)
            final_results = results[:top_k]

        profiler.end_search()

        print(profiler.report())

        # Export data for analysis
        profile_data = profiler.to_dict()
        print("\nProfile Data (JSON):")
        print(json.dumps(profile_data, indent=2))

        # Assertions
        assert len(final_results) == top_k
        assert (
            profiler.total_search_ms < 500
        ), f"Total search too slow: {profiler.total_search_ms:.2f}ms"


class TestAccessRecordingPerformance:
    """Profile access recording which happens after search."""

    def test_profile_access_recording(self, profiled_store: tuple[Any, PipelineProfiler]):
        """Profile the record_access() overhead."""
        from datetime import datetime, timezone

        store, profiler = profiled_store

        # Get some chunk IDs to record access for
        candidates = store.retrieve_by_activation(min_activation=0.0, limit=10)
        chunk_ids = [c.id for c in candidates]

        profiler.start_search()

        for chunk_id in chunk_ids:
            with profiler.measure("record_access"):
                store.record_access(
                    chunk_id=chunk_id,
                    access_time=datetime.now(timezone.utc),
                    context="test query",
                )

        profiler.end_search()

        print(profiler.report())

        avg_ms = profiler.timings["record_access"].avg_ms
        # Access recording should be <20ms per chunk
        assert avg_ms < 20, f"Access recording too slow: {avg_ms:.2f}ms per chunk"


class TestScalabilityProfile:
    """Profile pipeline at different scales."""

    @pytest.mark.parametrize("num_chunks", [50, 100, 250, 500])
    def test_profile_at_scale(self, tmp_path: Path, num_chunks: int):
        """Profile search performance at different database sizes."""
        from aurora_context_code.semantic.bm25_scorer import BM25Scorer
        from aurora_context_code.semantic.embedding_provider import cosine_similarity
        from aurora_core.chunks import CodeChunk
        from aurora_core.store.sqlite import SQLiteStore

        db_path = tmp_path / f"test_{num_chunks}.db"
        store = SQLiteStore(str(db_path))
        profiler = PipelineProfiler()

        # Create chunks
        for i in range(num_chunks):
            # Use absolute path as required by CodeChunk
            file_path = str(tmp_path / f"file_{i}.py")
            chunk = CodeChunk(
                chunk_id=f"chunk-{i}",
                file_path=file_path,
                element_type="function",
                name=f"function_{i}",
                line_start=1,
                line_end=10,
                docstring=f"Function {i} for user authentication and session management",
                language="python",
            )
            chunk.embeddings = np.random.randn(384).astype(np.float32).tobytes()
            store.save_chunk(chunk)

        query = "authentication session"
        query_embedding = np.random.randn(384).astype(np.float32)

        profiler.start_search()

        # Activation retrieval
        with profiler.measure(f"activation_{num_chunks}"):
            candidates = store.retrieve_by_activation(min_activation=0.0, limit=num_chunks)

        # BM25
        documents = [(c.id, c.docstring or "") for c in candidates]
        with profiler.measure(f"bm25_index_{num_chunks}"):
            scorer = BM25Scorer()
            scorer.build_index(documents)

        with profiler.measure(f"bm25_score_{num_chunks}"):
            for doc_id, content in documents:
                scorer.score(query, content)

        # Semantic
        with profiler.measure(f"semantic_{num_chunks}"):
            for chunk in candidates:
                if hasattr(chunk, "embeddings") and chunk.embeddings:
                    emb = np.frombuffer(chunk.embeddings, dtype=np.float32)
                    cosine_similarity(query_embedding, emb)

        profiler.end_search()

        print(f"\n{'=' * 50}")
        print(f"SCALE TEST: {num_chunks} chunks")
        print(f"{'=' * 50}")
        print(profiler.report())

        store.close()

        # Linear scaling check
        assert (
            profiler.total_search_ms < num_chunks * 2
        ), f"Search scales poorly: {profiler.total_search_ms:.2f}ms for {num_chunks} chunks"


class TestQueryCacheProfile:
    """Profile query embedding cache effectiveness."""

    def test_profile_query_cache_hit(self):
        """Profile cache hit performance."""
        from aurora_context_code.semantic.hybrid_retriever import QueryEmbeddingCache

        profiler = PipelineProfiler()
        cache = QueryEmbeddingCache(capacity=100, ttl_seconds=1800)

        # Pre-populate cache
        test_query = "user authentication session"
        test_embedding = np.random.randn(384).astype(np.float32)
        cache.set(test_query, test_embedding)

        profiler.start_search()

        # Measure cache hits
        for _ in range(100):
            with profiler.measure("cache_hit"):
                result = cache.get(test_query)
                assert result is not None

        profiler.end_search()

        print(profiler.report())

        avg_ms = profiler.timings["cache_hit"].avg_ms
        # Cache hits should be <0.1ms (100 microseconds)
        assert avg_ms < 0.1, f"Cache hit too slow: {avg_ms:.4f}ms"

    def test_profile_query_cache_miss(self):
        """Profile cache miss performance."""
        from aurora_context_code.semantic.hybrid_retriever import QueryEmbeddingCache

        profiler = PipelineProfiler()
        cache = QueryEmbeddingCache(capacity=100, ttl_seconds=1800)

        profiler.start_search()

        # Measure cache misses
        for i in range(100):
            with profiler.measure("cache_miss"):
                result = cache.get(f"unique query {i}")
                assert result is None

        profiler.end_search()

        print(profiler.report())

        avg_ms = profiler.timings["cache_miss"].avg_ms
        # Cache misses should be <0.1ms (100 microseconds)
        assert avg_ms < 0.1, f"Cache miss too slow: {avg_ms:.4f}ms"


def run_comprehensive_profile():
    """Run all profiling tests and generate a summary report."""
    import subprocess
    import sys

    result = subprocess.run(
        [sys.executable, "-m", "pytest", __file__, "-v", "-s", "--tb=short"],
        capture_output=False,
    )
    return result.returncode


if __name__ == "__main__":
    run_comprehensive_profile()
