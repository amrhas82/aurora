"""Unit tests for MemoryManager class."""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest

from aurora_cli.memory_manager import (
    SKIP_DIRS,
    IndexStats,
    MemoryManager,
    MemoryStats,
    SearchResult,
)


class TestMemoryManager:
    """Test suite for MemoryManager class."""

    @pytest.fixture
    def mock_store(self):
        """Create a mock memory store."""
        store = MagicMock()
        store.add_chunk = MagicMock()
        store.search_keyword = MagicMock(return_value=[])
        return store

    @pytest.fixture
    def mock_parser_registry(self):
        """Create a mock parser registry."""
        registry = MagicMock()
        return registry

    @pytest.fixture
    def mock_embedding_provider(self):
        """Create a mock embedding provider."""
        provider = MagicMock()
        provider.embed = MagicMock(return_value=[0.1, 0.2, 0.3])
        return provider

    @pytest.fixture
    def memory_manager(self, mock_store, mock_parser_registry, mock_embedding_provider):
        """Create a MemoryManager instance with mocked dependencies."""
        return MemoryManager(
            memory_store=mock_store,
            parser_registry=mock_parser_registry,
            embedding_provider=mock_embedding_provider,
        )

    @pytest.mark.cli
    @pytest.mark.critical
    def test_init(self, mock_store, mock_parser_registry, mock_embedding_provider):
        """Test MemoryManager initialization."""
        manager = MemoryManager(
            memory_store=mock_store,
            parser_registry=mock_parser_registry,
            embedding_provider=mock_embedding_provider,
        )

        assert manager.memory_store == mock_store
        assert manager.parser_registry == mock_parser_registry
        assert manager.embedding_provider == mock_embedding_provider

    def test_init_with_defaults(self, mock_store):
        """Test MemoryManager initialization with default registry and provider."""
        with patch("aurora_cli.memory_manager.get_global_registry") as mock_registry:
            with patch("aurora_cli.memory_manager.EmbeddingProvider") as mock_provider:
                manager = MemoryManager(memory_store=mock_store)

                assert manager.memory_store == mock_store
                mock_registry.assert_called_once()
                mock_provider.assert_called_once()

    def test_discover_files(self, memory_manager, tmp_path):
        """Test file discovery."""
        # Create test directory structure
        (tmp_path / "test1.py").touch()
        (tmp_path / "test2.py").touch()
        (tmp_path / "subdir").mkdir()
        (tmp_path / "subdir" / "test3.py").touch()
        (tmp_path / "__pycache__").mkdir()
        (tmp_path / "__pycache__" / "test4.py").touch()

        # Mock parser registry to recognize .py files
        memory_manager.parser_registry.get_parser_for_file = lambda f: f.suffix == ".py"

        # Discover files
        files = memory_manager._discover_files(tmp_path)

        # Should find test1.py, test2.py, and subdir/test3.py
        # Should skip __pycache__/test4.py
        assert len(files) == 3
        file_names = {f.name for f in files}
        assert "test1.py" in file_names
        assert "test2.py" in file_names
        assert "test3.py" in file_names

    def test_should_skip_path(self, memory_manager):
        """Test path skipping logic."""
        # Should skip paths with SKIP_DIRS
        assert memory_manager._should_skip_path(Path(".git/objects"))
        assert memory_manager._should_skip_path(Path("node_modules/package"))
        assert memory_manager._should_skip_path(Path("__pycache__/module.py"))

        # Should not skip normal paths
        assert not memory_manager._should_skip_path(Path("src/main.py"))
        assert not memory_manager._should_skip_path(Path("tests/test_main.py"))

    def test_detect_language(self, memory_manager):
        """Test language detection from file extension."""
        # Mock parser registry
        mock_parser = MagicMock()
        mock_parser.language = "python"
        memory_manager.parser_registry.get_parser_for_file = lambda f: (
            mock_parser if f.suffix == ".py" else None
        )

        # Test with parser available
        assert memory_manager._detect_language(Path("test.py")) == "python"

        # Test fallback for extensions without parser
        assert memory_manager._detect_language(Path("test.js")) == "javascript"
        assert memory_manager._detect_language(Path("test.rs")) == "rust"
        assert memory_manager._detect_language(Path("test.unknown")) == "unknown"

    def test_build_chunk_content(self, memory_manager):
        """Test building content string from code chunk."""
        # Create mock chunk
        mock_chunk = MagicMock()
        mock_chunk.signature = "def test_function(x, y):"
        mock_chunk.docstring = "Test function docstring"
        mock_chunk.element_type = "function"
        mock_chunk.name = "test_function"

        content = memory_manager._build_chunk_content(mock_chunk)

        assert "def test_function(x, y):" in content
        assert "Test function docstring" in content
        assert "function test_function" in content

    def test_build_chunk_content_minimal(self, memory_manager):
        """Test building content with minimal chunk data."""
        mock_chunk = MagicMock()
        mock_chunk.signature = None
        mock_chunk.docstring = None
        mock_chunk.element_type = "function"
        mock_chunk.name = "minimal_function"

        content = memory_manager._build_chunk_content(mock_chunk)

        assert "function minimal_function" in content

    @pytest.mark.cli
    @pytest.mark.critical
    def test_index_path_nonexistent(self, memory_manager):
        """Test indexing nonexistent path raises error."""
        with pytest.raises(ValueError, match="Path does not exist"):
            memory_manager.index_path("/nonexistent/path")

    def test_index_path_single_file(self, memory_manager, tmp_path):
        """Test indexing a single file."""
        # Create test file
        test_file = tmp_path / "test.py"
        test_file.write_text("def hello(): pass")

        # Mock parser
        mock_parser = MagicMock()
        mock_chunk = MagicMock()
        mock_chunk.chunk_id = "test-id"
        mock_chunk.element_type = "function"
        mock_chunk.name = "hello"
        mock_chunk.file_path = str(test_file)
        mock_chunk.line_start = 1
        mock_chunk.line_end = 1
        mock_chunk.signature = "def hello():"
        mock_chunk.docstring = None
        mock_chunk.language = "python"
        mock_chunk.complexity_score = 0.1
        mock_parser.parse = MagicMock(return_value=[mock_chunk])

        memory_manager.parser_registry.get_parser_for_file = lambda f: mock_parser

        # Index file
        stats = memory_manager.index_path(test_file)

        # Verify results
        assert isinstance(stats, IndexStats)
        assert stats.files_indexed == 1
        assert stats.chunks_created == 1
        assert stats.errors == 0
        assert stats.duration_seconds > 0

        # Verify store was called
        memory_manager.memory_store.add_chunk.assert_called_once()

    def test_index_path_directory(self, memory_manager, tmp_path):
        """Test indexing a directory."""
        # Create test files
        (tmp_path / "test1.py").write_text("def func1(): pass")
        (tmp_path / "test2.py").write_text("def func2(): pass")
        (tmp_path / "subdir").mkdir()
        (tmp_path / "subdir" / "test3.py").write_text("def func3(): pass")

        # Mock parser
        mock_parser = MagicMock()

        def mock_parse(file_path):
            mock_chunk = MagicMock()
            mock_chunk.chunk_id = f"test-{file_path.name}"
            mock_chunk.element_type = "function"
            mock_chunk.name = file_path.stem
            mock_chunk.file_path = str(file_path)
            mock_chunk.line_start = 1
            mock_chunk.line_end = 1
            mock_chunk.signature = f"def {file_path.stem}():"
            mock_chunk.docstring = None
            mock_chunk.language = "python"
            mock_chunk.complexity_score = 0.1
            return [mock_chunk]

        mock_parser.parse = mock_parse
        memory_manager.parser_registry.get_parser_for_file = lambda f: (
            mock_parser if f.suffix == ".py" else None
        )

        # Index directory
        stats = memory_manager.index_path(tmp_path)

        # Verify results
        assert stats.files_indexed == 3
        assert stats.chunks_created == 3
        assert stats.errors == 0

    def test_index_path_with_progress_callback(self, memory_manager, tmp_path):
        """Test indexing with progress callback."""
        # Create test file
        test_file = tmp_path / "test.py"
        test_file.write_text("def hello(): pass")

        # Mock parser
        mock_parser = MagicMock()
        mock_chunk = MagicMock()
        mock_chunk.chunk_id = "test-id"
        mock_chunk.element_type = "function"
        mock_chunk.name = "hello"
        mock_chunk.file_path = str(test_file)
        mock_chunk.line_start = 1
        mock_chunk.line_end = 1
        mock_chunk.signature = "def hello():"
        mock_chunk.docstring = None
        mock_chunk.language = "python"
        mock_chunk.complexity_score = 0.1
        mock_parser.parse = MagicMock(return_value=[mock_chunk])

        memory_manager.parser_registry.get_parser_for_file = lambda f: mock_parser

        # Mock progress callback
        progress_calls = []

        def progress_callback(current, total):
            progress_calls.append((current, total))

        # Index file
        memory_manager.index_path(test_file, progress_callback=progress_callback)

        # Verify progress callback was called
        assert len(progress_calls) > 0
        # Final call should be (1, 1)
        assert progress_calls[-1] == (1, 1)

    def test_index_path_parse_error(self, memory_manager, tmp_path):
        """Test indexing handles parse errors gracefully."""
        # Create test files
        (tmp_path / "good.py").write_text("def good(): pass")
        (tmp_path / "bad.py").write_text("def bad(): pass")

        # Mock parser that fails on bad.py
        mock_parser = MagicMock()

        def mock_parse(file_path):
            if "bad" in file_path.name:
                raise Exception("Parse error")
            mock_chunk = MagicMock()
            mock_chunk.chunk_id = "test-id"
            mock_chunk.element_type = "function"
            mock_chunk.name = "good"
            mock_chunk.file_path = str(file_path)
            mock_chunk.line_start = 1
            mock_chunk.line_end = 1
            mock_chunk.signature = "def good():"
            mock_chunk.docstring = None
            mock_chunk.language = "python"
            mock_chunk.complexity_score = 0.1
            return [mock_chunk]

        mock_parser.parse = mock_parse
        memory_manager.parser_registry.get_parser_for_file = lambda f: mock_parser

        # Index directory
        stats = memory_manager.index_path(tmp_path)

        # Should index good.py but record error for bad.py
        assert stats.files_indexed == 1
        assert stats.errors == 1

    @pytest.mark.cli
    def test_search(self, memory_manager):
        """Test memory search."""
        # Mock HybridRetriever
        mock_retriever_class = MagicMock()
        mock_retriever = MagicMock()
        mock_retriever.retrieve = MagicMock(
            return_value=[
                {
                    "chunk_id": "test-id-1",
                    "content": "def test1(): pass",
                    "activation_score": 0.8,
                    "semantic_score": 0.9,
                    "hybrid_score": 0.85,
                    "metadata": {
                        "type": "function",
                        "name": "test1",
                        "file_path": "/test.py",
                        "line_start": 1,
                        "line_end": 1,
                    },
                }
            ]
        )
        mock_retriever_class.return_value = mock_retriever

        with patch("aurora_cli.memory_manager.HybridRetriever", mock_retriever_class):
            with patch("aurora_cli.memory_manager.ActivationEngine"):
                results = memory_manager.search("test query", limit=5)

        # Verify results
        assert len(results) == 1
        assert isinstance(results[0], SearchResult)
        assert results[0].chunk_id == "test-id-1"
        assert results[0].file_path == "/test.py"
        assert results[0].line_range == (1, 1)
        assert results[0].hybrid_score == 0.85

    def test_search_error(self, memory_manager):
        """Test search handles errors."""
        # Mock HybridRetriever to raise error
        with patch(
            "aurora_cli.memory_manager.HybridRetriever",
            side_effect=Exception("Search error"),
        ):
            with pytest.raises(RuntimeError, match="Failed to search memory"):
                memory_manager.search("test query")

    def test_get_stats(self, memory_manager):
        """Test getting memory statistics."""
        # Mock database size
        memory_manager.memory_store.db_path = "/tmp/test.db"

        # Mock helper methods
        memory_manager._count_total_chunks = lambda: 100
        memory_manager._count_unique_files = lambda: 10
        memory_manager._get_language_distribution = lambda: {"python": 80, "javascript": 20}
        memory_manager._get_database_size = lambda: 2.5

        # Get stats
        stats = memory_manager.get_stats()

        # Verify results
        assert isinstance(stats, MemoryStats)
        assert stats.total_chunks == 100
        assert stats.total_files == 10
        assert stats.languages == {"python": 80, "javascript": 20}
        assert stats.database_size_mb == 2.5

    def test_get_stats_error(self, memory_manager):
        """Test get_stats handles errors."""
        # Mock helper method to raise error
        memory_manager._count_total_chunks = Mock(side_effect=Exception("Stats error"))

        with pytest.raises(RuntimeError, match="Failed to get memory stats"):
            memory_manager.get_stats()

    def test_count_total_chunks(self, memory_manager):
        """Test counting total chunks."""
        # This is currently a stub that returns 0
        count = memory_manager._count_total_chunks()
        assert count == 0

    def test_count_unique_files(self, memory_manager):
        """Test counting unique files."""
        # This is currently a stub that returns 0
        count = memory_manager._count_unique_files()
        assert count == 0

    def test_get_language_distribution(self, memory_manager):
        """Test getting language distribution."""
        # This is currently a stub that returns {}
        dist = memory_manager._get_language_distribution()
        assert dist == {}

    def test_get_database_size(self, memory_manager, tmp_path):
        """Test getting database size."""
        # Create temp file
        db_file = tmp_path / "test.db"
        db_file.write_text("test data")

        # Mock store with db_path
        memory_manager.memory_store.db_path = str(db_file)

        # Get size
        size = memory_manager._get_database_size()

        # Should return size in MB
        assert size > 0
        assert size < 1  # Small file, less than 1MB

    def test_get_database_size_no_path(self, memory_manager):
        """Test getting database size when store has no db_path."""
        # No db_path attribute
        if hasattr(memory_manager.memory_store, "db_path"):
            delattr(memory_manager.memory_store, "db_path")

        size = memory_manager._get_database_size()
        assert size == 0.0


class TestSkipDirs:
    """Test SKIP_DIRS constant."""

    def test_skip_dirs_contains_common_dirs(self):
        """Test that SKIP_DIRS contains common directories to skip."""
        assert ".git" in SKIP_DIRS
        assert "node_modules" in SKIP_DIRS
        assert "__pycache__" in SKIP_DIRS
        assert "venv" in SKIP_DIRS
        assert ".pytest_cache" in SKIP_DIRS


class TestDataClasses:
    """Test data classes."""

    def test_index_stats(self):
        """Test IndexStats dataclass."""
        stats = IndexStats(
            files_indexed=10,
            chunks_created=50,
            duration_seconds=5.2,
            errors=2,
        )

        assert stats.files_indexed == 10
        assert stats.chunks_created == 50
        assert stats.duration_seconds == 5.2
        assert stats.errors == 2

    def test_search_result(self):
        """Test SearchResult dataclass."""
        result = SearchResult(
            chunk_id="test-id",
            file_path="/test.py",
            line_range=(1, 10),
            content="test content",
            activation_score=0.8,
            semantic_score=0.9,
            hybrid_score=0.85,
            metadata={"type": "function"},
        )

        assert result.chunk_id == "test-id"
        assert result.file_path == "/test.py"
        assert result.line_range == (1, 10)
        assert result.content == "test content"
        assert result.activation_score == 0.8
        assert result.semantic_score == 0.9
        assert result.hybrid_score == 0.85
        assert result.metadata == {"type": "function"}

    def test_memory_stats(self):
        """Test MemoryStats dataclass."""
        stats = MemoryStats(
            total_chunks=100,
            total_files=10,
            languages={"python": 80, "javascript": 20},
            database_size_mb=2.5,
        )

        assert stats.total_chunks == 100
        assert stats.total_files == 10
        assert stats.languages == {"python": 80, "javascript": 20}
        assert stats.database_size_mb == 2.5
