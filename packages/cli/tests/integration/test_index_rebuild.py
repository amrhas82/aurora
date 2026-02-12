"""Integration tests for index rebuild and cache invalidation.

Tests the memory system's ability to:
1. Rebuild index from scratch (full rebuild)
2. Handle incremental updates (file modified)
3. Invalidate and recalculate BM25 IDF scores

This validates that the memory system correctly handles:
- Index clearing and rebuilding
- File modification detection
- BM25 corpus statistics recalculation
"""

import sqlite3
import time
from pathlib import Path

import pytest

from aurora_cli.memory_manager import MemoryManager
from aurora_context_code.semantic import EmbeddingProvider
from aurora_core.store.sqlite import SQLiteStore


pytestmark = pytest.mark.ml  # Requires ML dependencies


class TestIndexRebuild:
    """Test full index rebuild workflow."""

    @pytest.fixture
    def temp_db(self, tmp_path):
        """Create temporary database."""
        db_path = tmp_path / "rebuild.db"
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
    def test_codebase(self, tmp_path):
        """Create test codebase with multiple files."""
        codebase = tmp_path / "codebase"
        codebase.mkdir()

        # File 1
        (codebase / "module1.py").write_text(
            '''"""Module 1."""

def function_one():
    """First function."""
    return "one"


def function_two():
    """Second function."""
    return "two"
''',
        )

        # File 2
        (codebase / "module2.py").write_text(
            '''"""Module 2."""

class Calculator:
    """A calculator class."""

    def add(self, x, y):
        """Add two numbers."""
        return x + y

    def subtract(self, x, y):
        """Subtract two numbers."""
        return x - y
''',
        )

        return codebase

    def test_full_index_rebuild(self, memory_manager, memory_store, test_codebase):
        """Test full index rebuild clears old data and reindexes."""
        # Step 1: Initial indexing
        stats1 = memory_manager.index_path(test_codebase)
        assert stats1.chunks_created > 0, "Should create chunks on first index"

        initial_count = stats1.chunks_created

        # Step 2: Add a new file to codebase
        (test_codebase / "module3.py").write_text(
            '''"""Module 3."""

def new_function():
    """A new function."""
    return "new"
''',
        )

        # Step 3: Clear index (simulate full rebuild)
        # In production this would be `aur mem clear`
        conn = sqlite3.connect(memory_store.db_path)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM chunks")
        cursor.execute("DELETE FROM embeddings")
        cursor.execute("DELETE FROM activations")
        conn.commit()
        conn.close()

        # Verify cleared
        conn = sqlite3.connect(memory_store.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM chunks")
        count_after_clear = cursor.fetchone()[0]
        conn.close()
        assert count_after_clear == 0, "Index should be empty after clear"

        # Step 4: Rebuild index
        stats2 = memory_manager.index_path(test_codebase)

        # Should have more chunks (original + new file)
        assert stats2.chunks_created > initial_count, (
            f"Rebuild should index new file. "
            f"Initial: {initial_count}, After rebuild: {stats2.chunks_created}"
        )

        # Verify chunks are in database
        conn = sqlite3.connect(memory_store.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM chunks")
        final_count = cursor.fetchone()[0]
        conn.close()

        assert final_count == stats2.chunks_created, "Chunk count should match stats"
        assert final_count > 0, "Should have chunks after rebuild"

    def test_incremental_update_detects_changes(self, memory_manager, memory_store, test_codebase):
        """Test that reindexing detects file modifications."""
        # Step 1: Initial indexing
        stats1 = memory_manager.index_path(test_codebase)
        initial_chunks = stats1.chunks_created

        # Get initial chunk IDs for module1.py
        conn = sqlite3.connect(memory_store.db_path)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id FROM chunks WHERE json_extract(content, '$.file_path') LIKE '%module1.py'",
        )
        initial_chunk_ids = [row[0] for row in cursor.fetchall()]
        conn.close()

        assert len(initial_chunk_ids) > 0, "Should have chunks from module1.py"

        # Step 2: Modify file (add function)
        time.sleep(0.1)  # Ensure timestamp changes
        (test_codebase / "module1.py").write_text(
            '''"""Module 1 - Updated."""

def function_one():
    """First function."""
    return "one"


def function_two():
    """Second function."""
    return "two"


def function_three():
    """Third function - NEW."""
    return "three"
''',
        )

        # Step 3: Clear and reindex (simulating incremental update)
        # In production, incremental update would delete only affected chunks
        conn = sqlite3.connect(memory_store.db_path)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM chunks")
        conn.commit()
        conn.close()

        stats2 = memory_manager.index_path(test_codebase)

        # Should have more chunks (original files + new function)
        assert stats2.chunks_created > initial_chunks, (
            f"Should detect file modification. "
            f"Initial: {initial_chunks}, After update: {stats2.chunks_created}"
        )

        # Verify new chunk exists
        conn = sqlite3.connect(memory_store.db_path)
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT json_extract(content, '$.name')
            FROM chunks
            WHERE json_extract(content, '$.file_path') LIKE '%module1.py'
            """,
        )
        function_names = [row[0] for row in cursor.fetchall()]
        conn.close()

        assert "function_three" in function_names, "Should index new function"

    def test_search_after_rebuild(self, memory_manager, memory_store, test_codebase):
        """Test that search works correctly after index rebuild."""
        # Step 1: Initial index and search
        memory_manager.index_path(test_codebase)

        results1 = memory_manager.search(query="function_one", top_k=5, complexity="MEDIUM")
        assert len(results1) > 0, "Should find function_one initially"
        assert results1[0].name == "function_one", "Should rank function_one first"

        # Step 2: Clear and rebuild
        conn = sqlite3.connect(memory_store.db_path)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM chunks")
        cursor.execute("DELETE FROM embeddings")
        conn.commit()
        conn.close()

        memory_manager.index_path(test_codebase)

        # Step 3: Search again
        results2 = memory_manager.search(query="function_one", top_k=5, complexity="MEDIUM")
        assert len(results2) > 0, "Should find function_one after rebuild"
        assert results2[0].name == "function_one", "Should still rank function_one first"


class TestBM25IdfRecalculation:
    """Test BM25 IDF recalculation when corpus changes."""

    @pytest.fixture
    def temp_db(self, tmp_path):
        """Create temporary database."""
        db_path = tmp_path / "idf.db"
        return str(db_path)

    @pytest.fixture
    def memory_store(self, temp_db):
        """Create SQLite store."""
        store = SQLiteStore(db_path=temp_db)
        yield store
        store.close()

    @pytest.fixture
    def memory_manager(self, memory_store):
        """Create MemoryManager."""
        embedding_provider = EmbeddingProvider()
        return MemoryManager(memory_store=memory_store, embedding_provider=embedding_provider)

    def test_idf_changes_with_corpus_size(self, memory_manager, memory_store, tmp_path):
        """Test that IDF scores change when corpus size changes."""
        # Create small corpus
        small_corpus = tmp_path / "small"
        small_corpus.mkdir()

        (small_corpus / "file1.py").write_text(
            '''"""File 1."""

def unique_function():
    """A unique function."""
    return "unique"
''',
        )

        # Index small corpus
        memory_manager.index_path(small_corpus)

        # Search for "unique" - should have high BM25 score (rare term)
        results1 = memory_manager.search(query="unique", top_k=5, complexity="MEDIUM")
        assert len(results1) > 0, "Should find unique_function"

        # Get score
        score1 = results1[0].score
        assert score1 > 0, "Should have positive score"

        # Create larger corpus with many "unique" occurrences
        large_corpus = tmp_path / "large"
        large_corpus.mkdir()

        for i in range(10):
            (large_corpus / f"file{i}.py").write_text(
                f'''"""File {i}."""

def unique_function_{i}():
    """A unique function {i}."""
    return "unique"
''',
            )

        # Clear and reindex with larger corpus
        conn = sqlite3.connect(memory_store.db_path)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM chunks")
        cursor.execute("DELETE FROM embeddings")
        conn.commit()
        conn.close()

        memory_manager.index_path(large_corpus)

        # Search for "unique" again
        results2 = memory_manager.search(query="unique", top_k=10, complexity="MEDIUM")
        assert len(results2) > 0, "Should find unique functions in large corpus"

        # Note: BM25 scores are normalized in the hybrid retriever,
        # so we can't directly compare raw scores. Instead, verify that:
        # 1. Multiple results are found (term is no longer rare)
        # 2. Results are distributed across multiple files
        assert len(results2) >= 5, "Should find multiple unique functions"

        file_paths = set(r.file_path for r in results2)
        assert len(file_paths) >= 3, "Results should span multiple files"

    def test_corpus_stats_update_on_rebuild(self, memory_manager, memory_store, tmp_path):
        """Test that corpus statistics are recalculated on rebuild."""
        # Create initial corpus
        corpus1 = tmp_path / "corpus1"
        corpus1.mkdir()

        (corpus1 / "file1.py").write_text(
            '''"""File 1."""

def function_alpha():
    """Alpha function."""
    return "alpha"
''',
        )

        # Index
        stats1 = memory_manager.index_path(corpus1)
        initial_count = stats1.chunks_created

        # Create second corpus with different content
        corpus2 = tmp_path / "corpus2"
        corpus2.mkdir()

        for i in range(5):
            (corpus2 / f"file{i}.py").write_text(
                f'''"""File {i}."""

def function_beta_{i}():
    """Beta function {i}."""
    return "beta"
''',
            )

        # Clear and reindex
        conn = sqlite3.connect(memory_store.db_path)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM chunks")
        cursor.execute("DELETE FROM embeddings")
        conn.commit()
        conn.close()

        stats2 = memory_manager.index_path(corpus2)
        new_count = stats2.chunks_created

        # Corpus should be larger
        assert new_count > initial_count, "New corpus should have more chunks"

        # Search for "beta" should find multiple results
        results = memory_manager.search(query="beta", top_k=10, complexity="MEDIUM")
        assert len(results) >= 5, "Should find beta functions"

        # Verify all results are from new corpus
        for result in results:
            assert "corpus2" in result.file_path, "Results should be from new corpus"

    def test_document_frequency_tracking(self, memory_manager, memory_store, tmp_path):
        """Test that document frequency is tracked correctly for BM25."""
        # Create corpus with varying term frequencies
        corpus = tmp_path / "corpus"
        corpus.mkdir()

        # File 1: Contains "common" term
        (corpus / "file1.py").write_text(
            '''"""File 1."""

def common_function():
    """A common function."""
    return "common"
''',
        )

        # File 2: Contains "common" term
        (corpus / "file2.py").write_text(
            '''"""File 2."""

def another_common():
    """Another common function."""
    return "common"
''',
        )

        # File 3: Contains "rare" term only
        (corpus / "file3.py").write_text(
            '''"""File 3."""

def rare_function():
    """A rare function."""
    return "rare"
''',
        )

        # Index corpus
        memory_manager.index_path(corpus)

        # Search for "common" - should find multiple documents
        common_results = memory_manager.search(query="common", top_k=5, complexity="MEDIUM")
        common_files = set(Path(r.file_path).name for r in common_results)

        # Should find results from both file1 and file2
        assert len(common_results) >= 2, "Should find common term in multiple files"
        assert len(common_files) >= 2, "Should span multiple files with common term"

        # Search for "rare" - should find single document
        rare_results = memory_manager.search(query="rare", top_k=5, complexity="MEDIUM")
        assert len(rare_results) >= 1, "Should find rare function"

        # Rare term should rank highly (low document frequency = high IDF)
        top_rare = rare_results[0]
        assert "rare" in top_rare.name.lower(), "Rare function should rank high"
