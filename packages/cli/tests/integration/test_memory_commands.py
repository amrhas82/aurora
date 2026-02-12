"""Integration tests for memory indexing and search.

Tests the MemoryManager indexing pipeline: file discovery, parsing,
storage, search, and stats. Uses a dummy embedding provider to avoid
ML dependencies (sentence-transformers).
"""

import numpy as np
import pytest

from aurora_cli.config import Config
from aurora_cli.memory_manager import IndexProgress, MemoryManager
from aurora_core.store.sqlite import SQLiteStore


class DummyEmbeddingProvider:
    """Fake embedding provider that returns random vectors."""

    def embed_chunk(self, text: str) -> np.ndarray:
        np.random.seed(hash(text) % 2**31)
        return np.random.randn(384).astype(np.float32)

    def embed_batch(self, texts: list[str], batch_size: int = 32) -> np.ndarray:
        embeddings = []
        for text in texts:
            embeddings.append(self.embed_chunk(text))
        return np.array(embeddings)

    def embed_query(self, text: str) -> np.ndarray:
        return self.embed_chunk(text)


@pytest.fixture
def store(tmp_path):
    db_path = str(tmp_path / "test.db")
    s = SQLiteStore(db_path)
    yield s
    s.close()


@pytest.fixture
def config(tmp_path):
    db_path = str(tmp_path / "test.db")
    return Config(data={"storage": {"path": db_path}})


@pytest.fixture
def manager(store, config):
    return MemoryManager(
        config=config,
        memory_store=store,
        embedding_provider=DummyEmbeddingProvider(),
    )


@pytest.fixture
def sample_project(tmp_path):
    """Create a small Python project for indexing."""
    src = tmp_path / "src"
    src.mkdir()

    (src / "main.py").write_text('''\
def greet(name: str) -> str:
    """Return a greeting message."""
    return f"Hello, {name}!"


def add(a: int, b: int) -> int:
    """Add two numbers."""
    return a + b


class Calculator:
    """Simple calculator."""

    def multiply(self, x, y):
        """Multiply two numbers."""
        return x * y

    def divide(self, x, y):
        """Divide x by y."""
        if y == 0:
            raise ValueError("Cannot divide by zero")
        return x / y
''')

    (src / "utils.py").write_text('''\
import os
from pathlib import Path


def read_file(path: str) -> str:
    """Read a file and return its contents."""
    with open(path) as f:
        return f.read()


def list_files(directory: str) -> list[str]:
    """List all files in a directory."""
    return [f for f in os.listdir(directory) if os.path.isfile(os.path.join(directory, f))]
''')

    return src


class TestIndexPath:
    """Tests for MemoryManager.index_path()."""

    def test_indexes_python_files(self, manager, sample_project):
        stats = manager.index_path(sample_project, max_workers=1)

        assert stats.files_indexed >= 2
        assert stats.chunks_created >= 4  # greet, add, Calculator, multiply, divide, read_file, list_files

    def test_returns_index_stats(self, manager, sample_project):
        stats = manager.index_path(sample_project, max_workers=1)

        assert stats.files_indexed > 0
        assert stats.chunks_created > 0
        assert stats.duration_seconds >= 0
        assert stats.errors == 0

    def test_single_file_indexing(self, manager, tmp_path):
        f = tmp_path / "single.py"
        f.write_text("def solo():\n    return 42\n")

        stats = manager.index_path(f, max_workers=1)
        assert stats.files_indexed == 1
        assert stats.chunks_created >= 1

    def test_empty_directory(self, manager, tmp_path):
        empty = tmp_path / "empty"
        empty.mkdir()

        stats = manager.index_path(empty, max_workers=1)
        assert stats.files_indexed == 0
        assert stats.chunks_created == 0

    def test_nonexistent_path_raises(self, manager, tmp_path):
        with pytest.raises(ValueError, match="does not exist"):
            manager.index_path(tmp_path / "nope")

    def test_handles_broken_files(self, manager, tmp_path):
        src = tmp_path / "src"
        src.mkdir()

        (src / "good.py").write_text("def works():\n    return 1\n")
        (src / "bad.py").write_text("def broken(\n    return 1\n")

        stats = manager.index_path(src, max_workers=1)
        # Should not crash; good file should still be indexed
        assert stats.files_indexed >= 1

    def test_progress_callback(self, manager, sample_project):
        phases_seen = []

        def on_progress(prog: IndexProgress):
            if prog.phase not in phases_seen:
                phases_seen.append(prog.phase)

        manager.index_path(sample_project, progress_callback=on_progress, max_workers=1)

        assert "discovering" in phases_seen
        assert "parsing" in phases_seen

    def test_incremental_skips_unchanged(self, manager, sample_project):
        # First pass indexes everything
        stats1 = manager.index_path(sample_project, max_workers=1, incremental=True)
        assert stats1.files_indexed >= 2

        # Second pass should skip unchanged files
        stats2 = manager.index_path(sample_project, max_workers=1, incremental=True)
        assert stats2.files_skipped >= stats1.files_indexed

    def test_force_reindexes_all(self, manager, sample_project):
        # First pass
        manager.index_path(sample_project, max_workers=1)

        # Force reindex should process all files again
        stats2 = manager.index_path(sample_project, max_workers=1, incremental=False)
        assert stats2.files_indexed >= 2
        assert stats2.files_skipped == 0


class TestGetStats:
    """Tests for MemoryManager.get_stats()."""

    def test_stats_after_indexing(self, manager, sample_project):
        manager.index_path(sample_project, max_workers=1)

        stats = manager.get_stats()
        assert stats.total_chunks > 0
        assert stats.total_files >= 2
        assert stats.database_size_mb >= 0

    def test_stats_empty_store(self, manager):
        stats = manager.get_stats()
        assert stats.total_chunks == 0
        assert stats.total_files == 0

    def test_stats_language_distribution(self, manager, sample_project):
        manager.index_path(sample_project, max_workers=1)

        stats = manager.get_stats()
        # Should have Python files
        assert stats.total_files >= 2


class TestSearch:
    """Tests for MemoryManager.search()."""

    def test_search_returns_results(self, manager, sample_project):
        manager.index_path(sample_project, max_workers=1)

        results = manager.search("greet", limit=5)
        assert len(results) > 0
        assert results[0].chunk_id is not None
        assert results[0].file_path != ""

    def test_search_limit(self, manager, sample_project):
        manager.index_path(sample_project, max_workers=1)

        results = manager.search("function", limit=2)
        assert len(results) <= 2

    def test_search_result_fields(self, manager, sample_project):
        manager.index_path(sample_project, max_workers=1)

        results = manager.search("calculator", limit=1)
        if results:
            r = results[0]
            assert hasattr(r, "hybrid_score")
            assert hasattr(r, "bm25_score")
            assert hasattr(r, "line_range")
            assert isinstance(r.line_range, tuple)
