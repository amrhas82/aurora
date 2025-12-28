"""Unit tests for aurora_cli.memory_manager MemoryManager class.

This module tests the MemoryManager class for file indexing, searching,
and stats retrieval using direct function calls with mocking.
IMPORTANT: These are UNIT tests - they use mocks, NOT subprocess.run().
"""

from __future__ import annotations

import sqlite3
import time
from pathlib import Path
from unittest.mock import Mock, call, patch

import numpy as np
import pytest
from aurora_cli.errors import MemoryStoreError
from aurora_cli.memory_manager import (
    IndexStats,
    MemoryManager,
    MemoryStats,
    SearchResult,
)

from aurora_core.chunks import CodeChunk


class TestMemoryManagerInit:
    """Test MemoryManager initialization."""

    def test_init_with_store_only(self) -> None:
        """Test MemoryManager.__init__() with only memory_store."""
        mock_store = Mock()
        manager = MemoryManager(memory_store=mock_store)

        assert manager.memory_store is mock_store
        assert manager.parser_registry is not None
        assert manager.embedding_provider is not None
        assert manager.error_handler is not None

    @patch("aurora_cli.memory_manager.get_global_registry")
    def test_init_with_custom_parser_registry(
        self, mock_get_registry: Mock
    ) -> None:
        """Test MemoryManager.__init__() with custom parser_registry."""
        mock_store = Mock()
        mock_registry = Mock()
        manager = MemoryManager(
            memory_store=mock_store, parser_registry=mock_registry
        )

        assert manager.memory_store is mock_store
        assert manager.parser_registry is mock_registry
        # Should not call get_global_registry when custom registry provided
        mock_get_registry.assert_not_called()

    @patch("aurora_cli.memory_manager.EmbeddingProvider")
    def test_init_with_custom_embedding_provider(
        self, mock_provider_class: Mock
    ) -> None:
        """Test MemoryManager.__init__() with custom embedding_provider."""
        mock_store = Mock()
        mock_provider = Mock()
        manager = MemoryManager(
            memory_store=mock_store, embedding_provider=mock_provider
        )

        assert manager.memory_store is mock_store
        assert manager.embedding_provider is mock_provider
        # Should not create new provider when custom provider provided
        mock_provider_class.assert_not_called()


class TestIndexPath:
    """Test index_path method."""

    def test_index_path_with_nonexistent_path(self) -> None:
        """Test index_path() raises ValueError for nonexistent path."""
        mock_store = Mock()
        manager = MemoryManager(memory_store=mock_store)

        with pytest.raises(ValueError, match="Path does not exist"):
            manager.index_path("/nonexistent/path/to/file.py")

    def test_index_path_with_single_file(self, tmp_path: Path) -> None:
        """Test index_path() with single Python file."""
        # Create test file
        test_file = tmp_path / "test.py"
        test_file.write_text("def foo(): pass")

        # Setup mocks
        mock_store = Mock()
        mock_registry = Mock()
        mock_parser = Mock()
        mock_embedding_provider = Mock()

        # Create test chunk
        chunk = CodeChunk(
            chunk_id="chunk1",
            file_path=str(test_file),
            element_type="function",
            name="foo",
            line_start=1,
            line_end=1,
            signature="def foo():",
        )

        # Configure mocks
        mock_registry.get_parser_for_file.return_value = mock_parser
        mock_parser.parse.return_value = [chunk]
        mock_embedding = np.array([0.1, 0.2, 0.3])
        mock_embedding_provider.embed_chunk.return_value = mock_embedding

        # Execute
        manager = MemoryManager(
            memory_store=mock_store,
            parser_registry=mock_registry,
            embedding_provider=mock_embedding_provider,
        )
        stats = manager.index_path(test_file)

        # Verify
        assert stats.files_indexed == 1
        assert stats.chunks_created == 1
        assert stats.errors == 0
        assert stats.duration_seconds > 0
        mock_store.save_chunk.assert_called_once()

    def test_index_path_with_directory(self, tmp_path: Path) -> None:
        """Test index_path() with directory containing multiple files."""
        # Create test files
        file1 = tmp_path / "test1.py"
        file1.write_text("def foo(): pass")
        file2 = tmp_path / "test2.py"
        file2.write_text("def bar(): pass")

        # Setup mocks
        mock_store = Mock()
        mock_registry = Mock()
        mock_parser = Mock()
        mock_embedding_provider = Mock()

        chunk1 = CodeChunk(
            chunk_id="chunk1",
            file_path=str(file1),
            element_type="function",
            name="foo",
            line_start=1,
            line_end=1,
            signature="def foo():",
        )
        chunk2 = CodeChunk(
            chunk_id="chunk2",
            file_path=str(file2),
            element_type="function",
            name="bar",
            line_start=1,
            line_end=1,
            signature="def bar():",
        )

        # Configure mocks
        mock_registry.get_parser_for_file.return_value = mock_parser
        mock_parser.parse.side_effect = [[chunk1], [chunk2]]
        mock_embedding = np.array([0.1, 0.2, 0.3])
        mock_embedding_provider.embed_chunk.return_value = mock_embedding

        # Execute
        manager = MemoryManager(
            memory_store=mock_store,
            parser_registry=mock_registry,
            embedding_provider=mock_embedding_provider,
        )
        stats = manager.index_path(tmp_path)

        # Verify
        assert stats.files_indexed == 2
        assert stats.chunks_created == 2
        assert stats.errors == 0
        assert mock_store.save_chunk.call_count == 2

    def test_index_path_with_progress_callback(self, tmp_path: Path) -> None:
        """Test index_path() calls progress_callback during indexing."""
        # Create test file
        test_file = tmp_path / "test.py"
        test_file.write_text("def foo(): pass")

        # Setup mocks
        mock_store = Mock()
        mock_registry = Mock()
        mock_parser = Mock()
        mock_embedding_provider = Mock()
        mock_callback = Mock()

        chunk = CodeChunk(
            chunk_id="chunk1",
            file_path=str(test_file),
            element_type="function",
            name="foo",
            line_start=1,
            line_end=1,
            signature="def foo():",
        )

        mock_registry.get_parser_for_file.return_value = mock_parser
        mock_parser.parse.return_value = [chunk]
        mock_embedding = np.array([0.1, 0.2, 0.3])
        mock_embedding_provider.embed_chunk.return_value = mock_embedding

        # Execute
        manager = MemoryManager(
            memory_store=mock_store,
            parser_registry=mock_registry,
            embedding_provider=mock_embedding_provider,
        )
        manager.index_path(test_file, progress_callback=mock_callback)

        # Verify progress callback was called (at least at start and end)
        assert mock_callback.call_count >= 2
        # Final callback should be (total_files, total_files)
        final_call = mock_callback.call_args_list[-1]
        assert final_call == call(1, 1)

    def test_index_path_skips_files_without_parser(self, tmp_path: Path) -> None:
        """Test index_path() skips files with no parser."""
        # Create test files
        py_file = tmp_path / "test.py"
        py_file.write_text("def foo(): pass")
        txt_file = tmp_path / "readme.txt"
        txt_file.write_text("This is a readme")

        # Setup mocks
        mock_store = Mock()
        mock_registry = Mock()
        mock_parser = Mock()
        mock_embedding_provider = Mock()

        chunk = CodeChunk(
            chunk_id="chunk1",
            file_path=str(py_file),
            element_type="function",
            name="foo",
            line_start=1,
            line_end=1,
            signature="def foo():",
        )

        # Only Python files have a parser
        def get_parser_side_effect(file_path: Path) -> Mock | None:
            if file_path.suffix == ".py":
                return mock_parser
            return None

        mock_registry.get_parser_for_file.side_effect = get_parser_side_effect
        mock_parser.parse.return_value = [chunk]
        mock_embedding = np.array([0.1, 0.2, 0.3])
        mock_embedding_provider.embed_chunk.return_value = mock_embedding

        # Execute
        manager = MemoryManager(
            memory_store=mock_store,
            parser_registry=mock_registry,
            embedding_provider=mock_embedding_provider,
        )
        stats = manager.index_path(tmp_path)

        # Verify only Python file was indexed
        assert stats.files_indexed == 1
        assert stats.chunks_created == 1

    def test_index_path_handles_parser_errors(self, tmp_path: Path) -> None:
        """Test index_path() handles parser errors gracefully."""
        # Create test files
        good_file = tmp_path / "good.py"
        good_file.write_text("def foo(): pass")
        bad_file = tmp_path / "bad.py"
        bad_file.write_text("def bar(: pass")  # Syntax error

        # Setup mocks
        mock_store = Mock()
        mock_registry = Mock()
        mock_parser = Mock()
        mock_embedding_provider = Mock()

        chunk = CodeChunk(
            chunk_id="chunk1",
            file_path=str(good_file),
            element_type="function",
            name="foo",
            line_start=1,
            line_end=1,
            signature="def foo():",
        )

        # Configure mocks - bad_file raises error
        mock_registry.get_parser_for_file.return_value = mock_parser

        def parse_side_effect(file_path: Path) -> list[CodeChunk]:
            if "bad" in str(file_path):
                raise SyntaxError("Invalid syntax")
            return [chunk]

        mock_parser.parse.side_effect = parse_side_effect
        mock_embedding = np.array([0.1, 0.2, 0.3])
        mock_embedding_provider.embed_chunk.return_value = mock_embedding

        # Execute
        manager = MemoryManager(
            memory_store=mock_store,
            parser_registry=mock_registry,
            embedding_provider=mock_embedding_provider,
        )
        stats = manager.index_path(tmp_path)

        # Verify good file indexed, bad file counted as error
        assert stats.files_indexed == 1
        assert stats.chunks_created == 1
        assert stats.errors == 1

    def test_index_path_handles_empty_file(self, tmp_path: Path) -> None:
        """Test index_path() handles files with no chunks."""
        # Create empty file
        empty_file = tmp_path / "empty.py"
        empty_file.write_text("")

        # Setup mocks
        mock_store = Mock()
        mock_registry = Mock()
        mock_parser = Mock()
        mock_embedding_provider = Mock()

        # Parser returns empty chunk list
        mock_registry.get_parser_for_file.return_value = mock_parser
        mock_parser.parse.return_value = []

        # Execute
        manager = MemoryManager(
            memory_store=mock_store,
            parser_registry=mock_registry,
            embedding_provider=mock_embedding_provider,
        )
        stats = manager.index_path(empty_file)

        # Verify no chunks created
        assert stats.files_indexed == 0
        assert stats.chunks_created == 0
        assert stats.errors == 0
        mock_store.save_chunk.assert_not_called()

    def test_index_path_propagates_memory_store_error(
        self, tmp_path: Path
    ) -> None:
        """Test index_path() propagates MemoryStoreError immediately."""
        # Create test file
        test_file = tmp_path / "test.py"
        test_file.write_text("def foo(): pass")

        # Setup mocks
        mock_store = Mock()
        mock_registry = Mock()
        mock_parser = Mock()
        mock_embedding_provider = Mock()

        chunk = CodeChunk(
            chunk_id="chunk1",
            file_path=str(test_file),
            element_type="function",
            name="foo",
            line_start=1,
            line_end=1,
            signature="def foo():",
        )

        mock_registry.get_parser_for_file.return_value = mock_parser
        mock_parser.parse.return_value = [chunk]
        mock_embedding = np.array([0.1, 0.2, 0.3])
        mock_embedding_provider.embed_chunk.return_value = mock_embedding

        # Store raises MemoryStoreError
        mock_store.save_chunk.side_effect = MemoryStoreError(
            "Database connection failed"
        )

        # Execute
        manager = MemoryManager(
            memory_store=mock_store,
            parser_registry=mock_registry,
            embedding_provider=mock_embedding_provider,
        )

        # Should propagate MemoryStoreError
        with pytest.raises(MemoryStoreError):
            manager.index_path(test_file)


class TestSearch:
    """Test search method."""

    @patch("aurora_context_code.semantic.hybrid_retriever.HybridRetriever")
    @patch("aurora_core.activation.ActivationEngine")
    def test_search_with_results(
        self, mock_activation_class: Mock, mock_retriever_class: Mock
    ) -> None:
        """Test search() returns SearchResult objects."""
        # Setup mocks
        mock_store = Mock()
        mock_activation = Mock()
        mock_activation_class.return_value = mock_activation
        mock_retriever = Mock()
        mock_retriever_class.return_value = mock_retriever

        # Mock search results
        mock_retriever.retrieve.return_value = [
            {
                "chunk_id": "chunk1",
                "content": "def foo(): pass",
                "activation_score": 0.8,
                "semantic_score": 0.9,
                "hybrid_score": 0.85,
                "metadata": {
                    "file_path": "/path/to/file.py",
                    "line_start": 1,
                    "line_end": 1,
                },
            }
        ]

        # Execute
        manager = MemoryManager(memory_store=mock_store)
        results = manager.search("test query", limit=5)

        # Verify
        assert len(results) == 1
        assert isinstance(results[0], SearchResult)
        assert results[0].chunk_id == "chunk1"
        assert results[0].content == "def foo(): pass"
        assert results[0].file_path == "/path/to/file.py"
        assert results[0].activation_score == 0.8
        assert results[0].semantic_score == 0.9
        assert results[0].hybrid_score == 0.85

        # Verify retriever called with correct params
        mock_retriever.retrieve.assert_called_once_with("test query", top_k=5)

    @patch("aurora_context_code.semantic.hybrid_retriever.HybridRetriever")
    @patch("aurora_core.activation.ActivationEngine")
    def test_search_with_no_results(
        self, mock_activation_class: Mock, mock_retriever_class: Mock
    ) -> None:
        """Test search() with no matching results."""
        # Setup mocks
        mock_store = Mock()
        mock_retriever = Mock()
        mock_retriever_class.return_value = mock_retriever

        # Mock empty results
        mock_retriever.retrieve.return_value = []

        # Execute
        manager = MemoryManager(memory_store=mock_store)
        results = manager.search("no match query", limit=10)

        # Verify empty list
        assert results == []

    @patch("aurora_context_code.semantic.hybrid_retriever.HybridRetriever")
    @patch("aurora_core.activation.ActivationEngine")
    def test_search_handles_missing_metadata(
        self, mock_activation_class: Mock, mock_retriever_class: Mock
    ) -> None:
        """Test search() handles results with missing metadata gracefully."""
        # Setup mocks
        mock_store = Mock()
        mock_retriever = Mock()
        mock_retriever_class.return_value = mock_retriever

        # Mock results with minimal metadata
        mock_retriever.retrieve.return_value = [
            {
                "chunk_id": "chunk1",
                "content": "code here",
                "activation_score": 0.5,
                "semantic_score": 0.6,
                "hybrid_score": 0.55,
                "metadata": {},  # Empty metadata
            }
        ]

        # Execute
        manager = MemoryManager(memory_store=mock_store)
        results = manager.search("query", limit=5)

        # Verify defaults used for missing metadata
        assert len(results) == 1
        assert results[0].file_path == ""
        assert results[0].line_range == (0, 0)

    @patch("aurora_context_code.semantic.hybrid_retriever.HybridRetriever")
    @patch("aurora_core.activation.ActivationEngine")
    def test_search_propagates_memory_store_error(
        self, mock_activation_class: Mock, mock_retriever_class: Mock
    ) -> None:
        """Test search() propagates MemoryStoreError."""
        # Setup mocks
        mock_store = Mock()
        mock_retriever = Mock()
        mock_retriever_class.return_value = mock_retriever

        # Retriever raises MemoryStoreError
        mock_retriever.retrieve.side_effect = MemoryStoreError("Search failed")

        # Execute
        manager = MemoryManager(memory_store=mock_store)

        with pytest.raises(MemoryStoreError, match="Search failed"):
            manager.search("query")

    @patch("aurora_context_code.semantic.hybrid_retriever.HybridRetriever")
    @patch("aurora_core.activation.ActivationEngine")
    def test_search_wraps_generic_errors(
        self, mock_activation_class: Mock, mock_retriever_class: Mock
    ) -> None:
        """Test search() wraps generic errors in MemoryStoreError."""
        # Setup mocks
        mock_store = Mock()
        mock_retriever = Mock()
        mock_retriever_class.return_value = mock_retriever

        # Retriever raises generic error
        mock_retriever.retrieve.side_effect = RuntimeError("Unexpected error")

        # Execute
        manager = MemoryManager(memory_store=mock_store)

        with pytest.raises(MemoryStoreError):
            manager.search("query")


class TestGetStats:
    """Test get_stats method."""

    def test_get_stats_with_database_size(self, tmp_path: Path) -> None:
        """Test get_stats() calculates database size correctly."""
        # Create mock database file
        db_path = tmp_path / "test.db"
        db_path.write_bytes(b"x" * 1024 * 1024)  # 1 MB

        # Setup mock store with db_path
        mock_store = Mock()
        mock_store.db_path = str(db_path)

        # Execute
        manager = MemoryManager(memory_store=mock_store)
        stats = manager.get_stats()

        # Verify database size calculated
        assert isinstance(stats, MemoryStats)
        assert stats.database_size_mb == pytest.approx(1.0, rel=0.1)

    def test_get_stats_with_no_database_file(self) -> None:
        """Test get_stats() handles missing database file."""
        # Setup mock store without db_path
        mock_store = Mock()
        # Remove db_path attribute
        del mock_store.db_path

        # Execute
        manager = MemoryManager(memory_store=mock_store)
        stats = manager.get_stats()

        # Verify defaults
        assert stats.database_size_mb == 0.0

    def test_get_stats_returns_memory_stats(self) -> None:
        """Test get_stats() returns MemoryStats dataclass."""
        mock_store = Mock()
        # Remove db_path to avoid file system check
        del mock_store.db_path

        manager = MemoryManager(memory_store=mock_store)
        stats = manager.get_stats()

        assert isinstance(stats, MemoryStats)
        assert isinstance(stats.total_chunks, int)
        assert isinstance(stats.total_files, int)
        assert isinstance(stats.languages, dict)
        assert isinstance(stats.database_size_mb, float)


class TestDiscoverFiles:
    """Test _discover_files helper method."""

    def test_discover_files_in_directory(self, tmp_path: Path) -> None:
        """Test _discover_files() finds all parseable files."""
        # Create test files
        py_file1 = tmp_path / "test1.py"
        py_file1.write_text("def foo(): pass")
        py_file2 = tmp_path / "subdir" / "test2.py"
        py_file2.parent.mkdir()
        py_file2.write_text("def bar(): pass")
        txt_file = tmp_path / "readme.txt"
        txt_file.write_text("readme")

        # Setup mocks
        mock_store = Mock()
        mock_registry = Mock()

        # Only .py files have parser
        def get_parser_side_effect(file_path: Path) -> Mock | None:
            if file_path.suffix == ".py":
                return Mock()
            return None

        mock_registry.get_parser_for_file.side_effect = get_parser_side_effect

        # Execute
        manager = MemoryManager(
            memory_store=mock_store, parser_registry=mock_registry
        )
        files = manager._discover_files(tmp_path)

        # Verify only Python files discovered
        assert len(files) == 2
        assert all(f.suffix == ".py" for f in files)

    def test_discover_files_skips_skip_dirs(self, tmp_path: Path) -> None:
        """Test _discover_files() skips SKIP_DIRS."""
        # Create files in skip directories
        git_dir = tmp_path / ".git"
        git_dir.mkdir()
        git_file = git_dir / "config"
        git_file.write_text("git config")

        node_dir = tmp_path / "node_modules"
        node_dir.mkdir()
        node_file = node_dir / "package.json"
        node_file.write_text("{}")

        cache_dir = tmp_path / "__pycache__"
        cache_dir.mkdir()
        cache_file = cache_dir / "module.pyc"
        cache_file.write_text("compiled")

        # Create valid file
        valid_file = tmp_path / "test.py"
        valid_file.write_text("def foo(): pass")

        # Setup mocks
        mock_store = Mock()
        mock_registry = Mock()
        mock_registry.get_parser_for_file.return_value = Mock()

        # Execute
        manager = MemoryManager(
            memory_store=mock_store, parser_registry=mock_registry
        )
        files = manager._discover_files(tmp_path)

        # Verify only valid file found
        assert len(files) == 1
        assert files[0] == valid_file


class TestBuildChunkContent:
    """Test _build_chunk_content helper method."""

    def test_build_chunk_content_with_all_fields(self) -> None:
        """Test _build_chunk_content() includes signature, docstring, and name."""
        mock_store = Mock()
        manager = MemoryManager(memory_store=mock_store)

        chunk = Mock()
        chunk.signature = "def foo(x: int) -> str:"
        chunk.docstring = "This is a docstring"
        chunk.element_type = "function"
        chunk.name = "foo"

        content = manager._build_chunk_content(chunk)

        assert "def foo(x: int) -> str:" in content
        assert "This is a docstring" in content
        assert "function foo" in content

    def test_build_chunk_content_with_missing_docstring(self) -> None:
        """Test _build_chunk_content() handles missing docstring."""
        mock_store = Mock()
        manager = MemoryManager(memory_store=mock_store)

        chunk = Mock()
        chunk.signature = "def bar():"
        chunk.docstring = None
        chunk.element_type = "function"
        chunk.name = "bar"

        content = manager._build_chunk_content(chunk)

        assert "def bar():" in content
        assert "function bar" in content


class TestSaveChunkWithRetry:
    """Test _save_chunk_with_retry helper method."""

    def test_save_chunk_with_retry_success_first_attempt(self) -> None:
        """Test _save_chunk_with_retry() succeeds on first attempt."""
        mock_store = Mock()
        manager = MemoryManager(memory_store=mock_store)

        chunk = Mock()
        manager._save_chunk_with_retry(chunk)

        # Verify save called once
        mock_store.save_chunk.assert_called_once_with(chunk)

    def test_save_chunk_with_retry_handles_database_locked(self) -> None:
        """Test _save_chunk_with_retry() retries on database locked error."""
        mock_store = Mock()
        manager = MemoryManager(memory_store=mock_store)

        chunk = Mock()

        # First call raises locked error, second succeeds
        mock_store.save_chunk.side_effect = [
            sqlite3.OperationalError("database is locked"),
            None,
        ]

        # Execute - should succeed after retry
        manager._save_chunk_with_retry(chunk, max_retries=3)

        # Verify save called twice (first failed, second succeeded)
        assert mock_store.save_chunk.call_count == 2

    @patch("aurora_cli.memory_manager.time.sleep")
    def test_save_chunk_with_retry_uses_exponential_backoff(
        self, mock_sleep: Mock
    ) -> None:
        """Test _save_chunk_with_retry() uses exponential backoff."""
        mock_store = Mock()
        manager = MemoryManager(memory_store=mock_store)

        chunk = Mock()

        # Raise locked error 3 times, then succeed
        mock_store.save_chunk.side_effect = [
            sqlite3.OperationalError("database is locked"),
            sqlite3.OperationalError("database is locked"),
            sqlite3.OperationalError("database is locked"),
            None,
        ]

        # Execute
        manager._save_chunk_with_retry(chunk, max_retries=5)

        # Verify exponential backoff: 0.1, 0.2, 0.4 seconds
        assert mock_sleep.call_count == 3
        sleep_times = [call[0][0] for call in mock_sleep.call_args_list]
        assert sleep_times[0] == pytest.approx(0.1, rel=0.01)
        assert sleep_times[1] == pytest.approx(0.2, rel=0.01)
        assert sleep_times[2] == pytest.approx(0.4, rel=0.01)

    def test_save_chunk_with_retry_raises_after_max_retries(self) -> None:
        """Test _save_chunk_with_retry() raises MemoryStoreError after max retries."""
        mock_store = Mock()
        manager = MemoryManager(memory_store=mock_store)

        chunk = Mock()

        # Always raise locked error
        mock_store.save_chunk.side_effect = sqlite3.OperationalError(
            "database is locked"
        )

        # Execute - should raise after retries exhausted
        with pytest.raises(MemoryStoreError):
            manager._save_chunk_with_retry(chunk, max_retries=3)

        # Verify tried 3 times
        assert mock_store.save_chunk.call_count == 3

    def test_save_chunk_with_retry_handles_permission_error(self) -> None:
        """Test _save_chunk_with_retry() raises immediately on permission error."""
        mock_store = Mock()
        manager = MemoryManager(memory_store=mock_store)

        chunk = Mock()

        # Raise permission error (non-retryable)
        mock_store.save_chunk.side_effect = PermissionError("Access denied")

        # Execute - should raise immediately without retry
        with pytest.raises(MemoryStoreError):
            manager._save_chunk_with_retry(chunk, max_retries=3)

        # Verify only tried once (no retry)
        mock_store.save_chunk.assert_called_once()

    def test_save_chunk_with_retry_handles_os_error(self) -> None:
        """Test _save_chunk_with_retry() raises immediately on OS error."""
        mock_store = Mock()
        manager = MemoryManager(memory_store=mock_store)

        chunk = Mock()

        # Raise OS error (disk full)
        mock_store.save_chunk.side_effect = OSError("No space left on device")

        # Execute - should raise immediately without retry
        with pytest.raises(MemoryStoreError):
            manager._save_chunk_with_retry(chunk, max_retries=3)

        # Verify only tried once (no retry)
        mock_store.save_chunk.assert_called_once()

    def test_save_chunk_with_retry_handles_non_lock_operational_error(
        self,
    ) -> None:
        """Test _save_chunk_with_retry() raises immediately on non-lock OperationalError."""
        mock_store = Mock()
        manager = MemoryManager(memory_store=mock_store)

        chunk = Mock()

        # Raise non-lock operational error
        mock_store.save_chunk.side_effect = sqlite3.OperationalError(
            "syntax error"
        )

        # Execute - should raise immediately without retry
        with pytest.raises(MemoryStoreError):
            manager._save_chunk_with_retry(chunk, max_retries=3)

        # Verify only tried once (no retry for non-lock errors)
        mock_store.save_chunk.assert_called_once()


class TestDetectLanguage:
    """Test _detect_language helper method."""

    def test_detect_language_from_parser(self) -> None:
        """Test _detect_language() uses parser's language."""
        mock_store = Mock()
        mock_registry = Mock()
        mock_parser = Mock()
        mock_parser.language = "python"

        mock_registry.get_parser_for_file.return_value = mock_parser

        manager = MemoryManager(
            memory_store=mock_store, parser_registry=mock_registry
        )
        language = manager._detect_language(Path("test.py"))

        assert language == "python"

    def test_detect_language_fallback_to_extension(self) -> None:
        """Test _detect_language() falls back to extension mapping."""
        mock_store = Mock()
        mock_registry = Mock()
        mock_registry.get_parser_for_file.return_value = None

        manager = MemoryManager(
            memory_store=mock_store, parser_registry=mock_registry
        )

        assert manager._detect_language(Path("test.py")) == "python"
        assert manager._detect_language(Path("test.js")) == "javascript"
        assert manager._detect_language(Path("test.rs")) == "rust"
        assert manager._detect_language(Path("test.unknown")) == "unknown"


class TestShouldSkipPath:
    """Test _should_skip_path helper method."""

    def test_should_skip_path_with_skip_dir(self) -> None:
        """Test _should_skip_path() returns True for SKIP_DIRS."""
        mock_store = Mock()
        manager = MemoryManager(memory_store=mock_store)

        assert manager._should_skip_path(Path(".git/config"))
        assert manager._should_skip_path(Path("node_modules/package.json"))
        assert manager._should_skip_path(Path("__pycache__/module.pyc"))
        assert manager._should_skip_path(Path("project/.git/hooks/pre-commit"))

    def test_should_skip_path_with_valid_path(self) -> None:
        """Test _should_skip_path() returns False for valid paths."""
        mock_store = Mock()
        manager = MemoryManager(memory_store=mock_store)

        assert not manager._should_skip_path(Path("src/main.py"))
        assert not manager._should_skip_path(Path("tests/test_foo.py"))
        assert not manager._should_skip_path(Path("README.md"))
