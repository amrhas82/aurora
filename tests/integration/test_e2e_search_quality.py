"""End-to-end search quality test with MRR validation.

Tests BM25 tri-hybrid search quality by:
1. Indexing a subset of Aurora codebase
2. Running 20 queries with known ground truth
3. Validating Mean Reciprocal Rank (MRR) >= 0.85

This validates that BM25 + Semantic + Activation hybrid retrieval
produces high-quality search results with exact matches ranking first.
"""

import tempfile
from pathlib import Path
from typing import List, Tuple

import pytest

from aurora_cli.memory_manager import MemoryManager
from aurora_context_code.semantic import EmbeddingProvider
from aurora_core.store.sqlite import SQLiteStore

pytestmark = pytest.mark.ml  # Requires ML dependencies


# Ground truth: (query, expected_top_result_name)
# expected_top_result_name should appear in top-3 results
SEARCH_QUERIES = [
    # BM25 exact match tests - identifier search
    ("SOAROrchestrator", "SOAROrchestrator"),
    ("process_query", "process_query"),
    ("HybridRetriever", "HybridRetriever"),
    ("retrieve_context", "retrieve_context"),
    ("assess_retrieval_quality", "assess_retrieval_quality"),
    # CamelCase splitting tests
    ("getUserData", "get_user_data"),  # Should find via CamelCase tokenization
    ("ProcessQuery", "process_query"),
    # Semantic concept search (should find related functions)
    ("calculate activation score", "calculate_activation"),
    ("embed text with model", "generate_embeddings"),
    ("verify context quality", "assess_retrieval_quality"),
    # Class method search
    ("SQLiteStore save", "save_chunk"),
    ("MemoryManager index", "index_path"),
    # Architecture concepts
    ("SOAR orchestration pipeline", "SOAROrchestrator"),
    ("hybrid search retrieval", "HybridRetriever"),
    # Domain-specific terms
    ("activation frequency recency", "calculate_activation"),
    ("semantic similarity search", "semantic_search"),
    ("BM25 scoring algorithm", "BM25Scorer"),
    ("code chunk parsing", "parse_file"),
    # Multi-word exact matches
    ("retrieval quality assessment", "assess_retrieval_quality"),
    ("context window management", "manage_context"),
]


def calculate_mrr(results: list[tuple[str, list[str]]]) -> float:
    """Calculate Mean Reciprocal Rank.

    Args:
        results: List of (query, result_names) tuples

    Returns:
        MRR score between 0 and 1
    """
    reciprocal_ranks = []

    for query, expected_name in SEARCH_QUERIES:
        # Find matching result tuple
        result_tuple = next((r for r in results if r[0] == query), None)
        if not result_tuple:
            reciprocal_ranks.append(0.0)
            continue

        result_names = result_tuple[1]

        # Find rank of expected result (1-indexed)
        try:
            rank = result_names.index(expected_name) + 1
            reciprocal_ranks.append(1.0 / rank)
        except ValueError:
            # Expected result not in top results
            reciprocal_ranks.append(0.0)

    return sum(reciprocal_ranks) / len(reciprocal_ranks) if reciprocal_ranks else 0.0


class TestEndToEndSearchQuality:
    """Test end-to-end search quality with MRR validation."""

    @pytest.fixture
    def temp_db(self, tmp_path):
        """Create temporary database."""
        db_path = tmp_path / "search_quality.db"
        return str(db_path)

    @pytest.fixture
    def memory_store(self, temp_db):
        """Create SQLite store."""
        store = SQLiteStore(db_path=temp_db)
        yield store
        store.close()

    @pytest.fixture
    def memory_manager(self, memory_store):
        """Create MemoryManager with real components."""
        embedding_provider = EmbeddingProvider()
        return MemoryManager(memory_store=memory_store, embedding_provider=embedding_provider)

    @pytest.fixture
    def aurora_subset(self) -> Path:
        """Return path to Aurora codebase subset for indexing.

        Uses key modules that contain search test targets:
        - aurora_soar (SOAROrchestrator, process_query, retrieve_context)
        - aurora_context_code (HybridRetriever, BM25Scorer)
        - aurora_core (SQLiteStore, chunks)
        - aurora_cli (MemoryManager)
        """
        repo_root = Path("/home/hamr/PycharmProjects/aurora")
        assert repo_root.exists(), "Aurora repo root not found"

        # Index these key packages
        packages_to_index = [
            repo_root / "packages/soar/src/aurora_soar",
            repo_root / "packages/context-code/src/aurora_context_code",
            repo_root / "packages/core/src/aurora_core",
            repo_root / "packages/cli/src/aurora_cli",
        ]

        # Verify all paths exist
        for path in packages_to_index:
            assert path.exists(), f"Package path not found: {path}"

        return repo_root / "packages"

    def test_index_aurora_subset(self, memory_manager, aurora_subset):
        """Test indexing Aurora codebase subset."""
        # Index the packages directory
        stats = memory_manager.index_path(aurora_subset)

        # Verify indexing succeeded
        assert stats.files_indexed > 50, f"Should index 50+ files, got {stats.files_indexed}"
        assert stats.chunks_created > 200, f"Should create 200+ chunks, got {stats.chunks_created}"
        # Allow small number of errors from large markdown files
        assert stats.errors <= 5, f"Should have ≤5 errors, got {stats.errors}"

    def test_search_quality_mrr(self, memory_manager, memory_store, aurora_subset):
        """Test search quality with MRR >= 0.85."""
        # Step 1: Index Aurora subset
        stats = memory_manager.index_path(aurora_subset)
        assert stats.chunks_created > 0, "Must have indexed chunks"

        # Step 2: Run all search queries and collect results
        results: list[tuple[str, list[str]]] = []

        for query, expected_name in SEARCH_QUERIES:
            # Search with default top_k=10
            search_results = memory_manager.search(query=query, top_k=10, complexity="MEDIUM")

            # Extract result names (function/class/method names)
            result_names = [r.name for r in search_results]
            results.append((query, result_names))

        # Step 3: Calculate MRR
        mrr = calculate_mrr(results)

        # Step 4: Print diagnostic info for failing queries
        if mrr < 0.85:
            print("\n=== MRR DIAGNOSTIC ===")
            print(f"MRR: {mrr:.3f} (target: >= 0.85)")
            print("\nFailing queries:")

            for query, expected_name in SEARCH_QUERIES:
                result_tuple = next((r for r in results if r[0] == query), None)
                if not result_tuple:
                    print(f"  ❌ {query} → NO RESULTS")
                    continue

                result_names = result_tuple[1]

                if expected_name not in result_names[:3]:
                    print(f"  ❌ {query}")
                    print(f"     Expected: {expected_name}")
                    print(f"     Got top-3: {result_names[:3]}")
                else:
                    rank = result_names.index(expected_name) + 1
                    print(f"  ✓ {query} → rank {rank}")

        # Assert MRR meets threshold
        assert mrr >= 0.85, (
            f"MRR {mrr:.3f} below threshold 0.85. " f"BM25 tri-hybrid search quality insufficient."
        )

    def test_exact_match_top_rank(self, memory_manager, memory_store, aurora_subset):
        """Test that exact identifier matches rank first."""
        # Index codebase
        stats = memory_manager.index_path(aurora_subset)
        assert stats.chunks_created > 0, "Must have indexed chunks"

        # Test exact matches - these MUST be rank 1
        exact_match_queries = [
            ("SOAROrchestrator", "SOAROrchestrator"),
            ("HybridRetriever", "HybridRetriever"),
            ("process_query", "process_query"),
            ("retrieve_context", "retrieve_context"),
        ]

        failures = []
        for query, expected_name in exact_match_queries:
            results = memory_manager.search(query=query, top_k=5, complexity="MEDIUM")

            if not results:
                failures.append(f"{query}: no results")
                continue

            top_result = results[0]
            if top_result.name != expected_name:
                failures.append(
                    f"{query}: expected '{expected_name}' at rank 1, " f"got '{top_result.name}'"
                )

        assert not failures, "Exact match queries must rank target at position 1:\n" + "\n".join(
            failures
        )

    def test_camelcase_splitting_works(self, memory_manager, memory_store, aurora_subset):
        """Test that CamelCase queries find snake_case functions."""
        # Index codebase
        stats = memory_manager.index_path(aurora_subset)
        assert stats.chunks_created > 0, "Must have indexed chunks"

        # These queries use CamelCase but should find snake_case functions
        # via BM25 tokenization
        camelcase_queries = [
            ("ProcessQuery", "process_query"),
            ("RetrieveContext", "retrieve_context"),
            ("SaveChunk", "save_chunk"),
        ]

        for query, expected_name in camelcase_queries:
            results = memory_manager.search(query=query, top_k=10, complexity="MEDIUM")
            result_names = [r.name for r in results]

            assert expected_name in result_names[:5], (
                f"CamelCase query '{query}' should find '{expected_name}' in top-5. "
                f"Got: {result_names[:5]}"
            )

    def test_semantic_concept_search(self, memory_manager, memory_store, aurora_subset):
        """Test semantic search finds conceptually related functions."""
        # Index codebase
        stats = memory_manager.index_path(aurora_subset)
        assert stats.chunks_created > 0, "Must have indexed chunks"

        # These are concept searches - semantic similarity should help
        concept_queries = [
            ("calculate activation score", "activation"),  # Should find activation-related
            ("embed text with model", "embed"),  # Should find embedding-related
            ("verify context quality", "verify"),  # Should find verification-related
        ]

        for query, expected_substring in concept_queries:
            results = memory_manager.search(query=query, top_k=10, complexity="MEDIUM")
            result_names = [r.name.lower() for r in results]

            # Check if any result name contains expected substring
            matches = [name for name in result_names if expected_substring in name]

            assert len(matches) > 0, (
                f"Semantic query '{query}' should find results containing '{expected_substring}'. "
                f"Got names: {result_names[:5]}"
            )

    def test_staged_retrieval_coverage(self, memory_manager, memory_store, aurora_subset):
        """Test that staged retrieval (BM25 → tri-hybrid) provides good coverage."""
        # Index codebase
        stats = memory_manager.index_path(aurora_subset)
        assert stats.chunks_created > 0, "Must have indexed chunks"

        # Generic query should return diverse results
        query = "process query"
        results = memory_manager.search(query=query, top_k=20, complexity="MEDIUM")

        # Verify result diversity
        assert len(results) >= 10, "Should return at least 10 results for generic query"

        # Check that results span multiple files (not all from one file)
        file_paths = set(r.file_path for r in results)
        assert (
            len(file_paths) >= 3
        ), f"Results should span multiple files, got {len(file_paths)} files"

        # Check that results span multiple element types
        element_types = set(r.element_type for r in results)
        assert len(element_types) >= 2, f"Results should span multiple types, got {element_types}"
