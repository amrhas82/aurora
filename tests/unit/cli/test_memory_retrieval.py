"""Unit tests for MemoryRetriever module.

Tests the shared memory retrieval API for AURORA CLI including:
- Hybrid retrieval
- Context file loading
- Prompt formatting
- Context strategy logic
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

import pytest

from aurora_cli.memory.retrieval import MemoryRetriever, _detect_language
from aurora_core.chunks import CodeChunk


@pytest.fixture
def mock_config() -> MagicMock:
    """Create a mock Config object."""
    config = MagicMock()
    config.search_min_semantic_score = 0.7
    config.get_db_path.return_value = "/tmp/test.db"
    return config


@pytest.fixture
def mock_store() -> MagicMock:
    """Create a mock SQLiteStore object."""
    return MagicMock()


@pytest.fixture
def sample_chunks() -> list[CodeChunk]:
    """Create sample CodeChunk objects for testing."""
    return [
        CodeChunk(
            chunk_id="chunk1",
            file_path="/src/auth.py",
            element_type="function",
            name="authenticate",
            line_start=10,
            line_end=15,
            docstring="def authenticate(user, password):\n    pass",
            language="python",
        ),
        CodeChunk(
            chunk_id="chunk2",
            file_path="/src/users.py",
            element_type="class",
            name="UserManager",
            line_start=1,
            line_end=20,
            docstring="class UserManager:\n    pass",
            language="python",
        ),
    ]


class TestMemoryRetrieverInit:
    """Tests for MemoryRetriever initialization."""

    def test_init_stores_config_and_store(
        self, mock_store: MagicMock, mock_config: MagicMock
    ) -> None:
        """Stores config and store references."""
        retriever = MemoryRetriever(mock_store, mock_config)

        assert retriever._store == mock_store
        assert retriever._config == mock_config
        assert retriever._retriever is None  # Lazy loaded

    def test_init_with_config_only(self, mock_config: MagicMock) -> None:
        """Can initialize with only config (for file-only usage)."""
        retriever = MemoryRetriever(config=mock_config)

        assert retriever._store is None
        assert retriever._config == mock_config

    def test_init_with_no_args(self) -> None:
        """Can initialize with no arguments."""
        retriever = MemoryRetriever()

        assert retriever._store is None
        assert retriever._config is None


class TestMemoryRetrieverHasIndexedMemory:
    """Tests for has_indexed_memory method."""

    def test_returns_false_when_no_store(self, mock_config: MagicMock) -> None:
        """Returns False when no store is configured."""
        retriever = MemoryRetriever(config=mock_config)
        result = retriever.has_indexed_memory()

        assert result is False

    def test_returns_true_when_chunks_exist(
        self, mock_store: MagicMock, mock_config: MagicMock, sample_chunks: list[CodeChunk]
    ) -> None:
        """Returns True when store has chunks."""
        with patch.object(MemoryRetriever, "_get_retriever") as mock_get_retriever:
            mock_hybrid = MagicMock()
            mock_hybrid.retrieve.return_value = sample_chunks[:1]
            mock_get_retriever.return_value = mock_hybrid

            retriever = MemoryRetriever(mock_store, mock_config)
            result = retriever.has_indexed_memory()

            assert result is True

    def test_returns_false_when_no_chunks(
        self, mock_store: MagicMock, mock_config: MagicMock
    ) -> None:
        """Returns False when store is empty."""
        with patch.object(MemoryRetriever, "_get_retriever") as mock_get_retriever:
            mock_hybrid = MagicMock()
            mock_hybrid.retrieve.return_value = []
            mock_get_retriever.return_value = mock_hybrid

            retriever = MemoryRetriever(mock_store, mock_config)
            result = retriever.has_indexed_memory()

            assert result is False

    def test_returns_false_on_error(self, mock_store: MagicMock, mock_config: MagicMock) -> None:
        """Returns False on retrieval error."""
        with patch.object(MemoryRetriever, "_get_retriever") as mock_get_retriever:
            mock_hybrid = MagicMock()
            mock_hybrid.retrieve.side_effect = Exception("DB error")
            mock_get_retriever.return_value = mock_hybrid

            retriever = MemoryRetriever(mock_store, mock_config)
            result = retriever.has_indexed_memory()

            assert result is False


class TestMemoryRetrieverRetrieve:
    """Tests for retrieve method."""

    def test_retrieves_chunks(
        self, mock_store: MagicMock, mock_config: MagicMock, sample_chunks: list[CodeChunk]
    ) -> None:
        """Retrieves chunks using hybrid retriever."""
        with patch.object(MemoryRetriever, "_get_retriever") as mock_get_retriever:
            mock_hybrid = MagicMock()
            mock_hybrid.retrieve.return_value = sample_chunks
            mock_get_retriever.return_value = mock_hybrid

            retriever = MemoryRetriever(mock_store, mock_config)
            result = retriever.retrieve("authentication", limit=10)

            assert len(result) == 2
            mock_hybrid.retrieve.assert_called_once()

    def test_uses_config_threshold(self, mock_store: MagicMock, mock_config: MagicMock) -> None:
        """Uses config semantic threshold by default."""
        mock_config.search_min_semantic_score = 0.5

        with patch.object(MemoryRetriever, "_get_retriever") as mock_get_retriever:
            mock_hybrid = MagicMock()
            mock_hybrid.retrieve.return_value = []
            mock_get_retriever.return_value = mock_hybrid

            retriever = MemoryRetriever(mock_store, mock_config)
            retriever.retrieve("test")

            call_kwargs = mock_hybrid.retrieve.call_args.kwargs
            assert call_kwargs["semantic_threshold"] == 0.5

    def test_overrides_threshold(self, mock_store: MagicMock, mock_config: MagicMock) -> None:
        """Allows threshold override."""
        mock_config.search_min_semantic_score = 0.5

        with patch.object(MemoryRetriever, "_get_retriever") as mock_get_retriever:
            mock_hybrid = MagicMock()
            mock_hybrid.retrieve.return_value = []
            mock_get_retriever.return_value = mock_hybrid

            retriever = MemoryRetriever(mock_store, mock_config)
            retriever.retrieve("test", min_semantic_score=0.3)

            call_kwargs = mock_hybrid.retrieve.call_args.kwargs
            assert call_kwargs["semantic_threshold"] == 0.3

    def test_returns_empty_on_error(self, mock_store: MagicMock, mock_config: MagicMock) -> None:
        """Returns empty list on retrieval error."""
        with patch.object(MemoryRetriever, "_get_retriever") as mock_get_retriever:
            mock_hybrid = MagicMock()
            mock_hybrid.retrieve.side_effect = Exception("Error")
            mock_get_retriever.return_value = mock_hybrid

            retriever = MemoryRetriever(mock_store, mock_config)
            result = retriever.retrieve("test")

            assert result == []


class TestMemoryRetrieverLoadContextFiles:
    """Tests for load_context_files method."""

    def test_loads_existing_files(
        self, tmp_path: Path, mock_store: MagicMock, mock_config: MagicMock
    ) -> None:
        """Loads content from existing files."""
        test_file = tmp_path / "test.py"
        test_file.write_text("def hello():\n    pass")

        retriever = MemoryRetriever(mock_store, mock_config)
        chunks = retriever.load_context_files([test_file])

        assert len(chunks) == 1
        assert "def hello()" in chunks[0].docstring
        assert chunks[0].language == "python"

    def test_skips_missing_files(
        self,
        tmp_path: Path,
        mock_store: MagicMock,
        mock_config: MagicMock,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """Skips and warns for missing files."""
        missing_file = tmp_path / "nonexistent.py"

        retriever = MemoryRetriever(mock_store, mock_config)

        with caplog.at_level(logging.WARNING):
            chunks = retriever.load_context_files([missing_file])

        assert len(chunks) == 0
        assert "not found" in caplog.text

    def test_skips_directories(
        self,
        tmp_path: Path,
        mock_store: MagicMock,
        mock_config: MagicMock,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """Skips and warns for directories."""
        retriever = MemoryRetriever(mock_store, mock_config)

        with caplog.at_level(logging.WARNING):
            chunks = retriever.load_context_files([tmp_path])

        assert len(chunks) == 0
        assert "not a file" in caplog.text

    def test_loads_multiple_files(
        self, tmp_path: Path, mock_store: MagicMock, mock_config: MagicMock
    ) -> None:
        """Loads multiple files."""
        file1 = tmp_path / "file1.py"
        file1.write_text("# File 1")
        file2 = tmp_path / "file2.js"
        file2.write_text("// File 2")

        retriever = MemoryRetriever(mock_store, mock_config)
        chunks = retriever.load_context_files([file1, file2])

        assert len(chunks) == 2


class TestMemoryRetrieverFormatForPrompt:
    """Tests for format_for_prompt method."""

    def test_formats_chunks(
        self, mock_store: MagicMock, mock_config: MagicMock, sample_chunks: list[CodeChunk]
    ) -> None:
        """Formats chunks with headers and code blocks."""
        retriever = MemoryRetriever(mock_store, mock_config)
        formatted = retriever.format_for_prompt(sample_chunks)

        assert "### File: /src/auth.py" in formatted
        assert "lines 10-15" in formatted
        assert "```python" in formatted
        assert "def authenticate" in formatted

    def test_returns_empty_for_no_chunks(
        self, mock_store: MagicMock, mock_config: MagicMock
    ) -> None:
        """Returns empty string for empty chunk list."""
        retriever = MemoryRetriever(mock_store, mock_config)
        formatted = retriever.format_for_prompt([])

        assert formatted == ""


class TestMemoryRetrieverGetContext:
    """Tests for get_context method."""

    def test_uses_context_files_when_provided(
        self, tmp_path: Path, mock_store: MagicMock, mock_config: MagicMock
    ) -> None:
        """Uses context files when provided (priority 1)."""
        test_file = tmp_path / "context.py"
        test_file.write_text("# Context")

        retriever = MemoryRetriever(mock_store, mock_config)
        chunks, error = retriever.get_context("query", context_files=[test_file])

        assert len(chunks) == 1
        assert error == ""

    def test_uses_indexed_memory_when_no_files(
        self, mock_store: MagicMock, mock_config: MagicMock, sample_chunks: list[CodeChunk]
    ) -> None:
        """Uses indexed memory when no context files (priority 2)."""
        with patch.object(MemoryRetriever, "_get_retriever") as mock_get_retriever:
            mock_hybrid = MagicMock()
            mock_hybrid.retrieve.return_value = sample_chunks
            mock_get_retriever.return_value = mock_hybrid

            retriever = MemoryRetriever(mock_store, mock_config)
            chunks, error = retriever.get_context("query")

            assert len(chunks) == 2
            assert error == ""

    def test_returns_error_when_no_context(
        self, mock_store: MagicMock, mock_config: MagicMock
    ) -> None:
        """Returns error when no context available."""
        with patch.object(MemoryRetriever, "_get_retriever") as mock_get_retriever:
            mock_hybrid = MagicMock()
            mock_hybrid.retrieve.return_value = []
            mock_get_retriever.return_value = mock_hybrid

            retriever = MemoryRetriever(mock_store, mock_config)
            chunks, error = retriever.get_context("query")

            assert len(chunks) == 0
            assert "No context available" in error


class TestDetectLanguage:
    """Tests for _detect_language helper function."""

    def test_detects_python(self) -> None:
        """Detects Python files."""
        assert _detect_language(Path("test.py")) == "python"

    def test_detects_javascript(self) -> None:
        """Detects JavaScript files."""
        assert _detect_language(Path("test.js")) == "javascript"
        assert _detect_language(Path("test.jsx")) == "javascript"

    def test_detects_typescript(self) -> None:
        """Detects TypeScript files."""
        assert _detect_language(Path("test.ts")) == "typescript"
        assert _detect_language(Path("test.tsx")) == "typescript"

    def test_detects_markdown(self) -> None:
        """Detects Markdown files."""
        assert _detect_language(Path("README.md")) == "markdown"

    def test_defaults_to_text(self) -> None:
        """Defaults to text for unknown extensions."""
        assert _detect_language(Path("file.xyz")) == "text"

    def test_case_insensitive(self) -> None:
        """Handles case variations."""
        assert _detect_language(Path("test.PY")) == "python"
        assert _detect_language(Path("test.Py")) == "python"
