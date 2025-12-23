"""Unit tests for memory command.

This module tests the memory command functionality including:
- Query parsing and keyword extraction
- HybridRetriever integration
- Result formatting
- Command-line options
- Error handling
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import Mock, patch

from aurora_cli.commands.memory import (
    _format_score,
    _truncate_content,
    _truncate_path,
    extract_keywords,
    format_memory_results,
    memory_command,
)
from click.testing import CliRunner


class TestKeywordExtraction:
    """Tests for keyword extraction from queries."""

    def test_extract_keywords_basic(self):
        """Test basic keyword extraction."""
        query = "How to calculate the total price?"
        keywords = extract_keywords(query)
        assert "calculate" in keywords
        assert "total" in keywords
        assert "price" in keywords

    def test_extract_keywords_removes_stop_words(self):
        """Test that stop words are removed."""
        query = "What is the function of authentication?"
        keywords = extract_keywords(query)
        assert "function" in keywords
        assert "authentication" in keywords
        # Stop words should be removed
        assert "what" not in keywords
        assert "is" not in keywords
        assert "the" not in keywords
        assert "of" not in keywords

    def test_extract_keywords_removes_short_words(self):
        """Test that short words (<=2 chars) are removed."""
        query = "I am in a database"
        keywords = extract_keywords(query)
        assert "database" in keywords
        # Short words should be removed
        assert "a" not in keywords
        assert "in" not in keywords
        assert "am" not in keywords

    def test_extract_keywords_deduplicates(self):
        """Test that duplicate keywords are removed."""
        query = "Calculate calculate CALCULATE the total"
        keywords = extract_keywords(query)
        assert keywords.count("calculate") == 1
        assert "total" in keywords

    def test_extract_keywords_empty_query(self):
        """Test extraction from empty query."""
        keywords = extract_keywords("")
        assert keywords == []

    def test_extract_keywords_preserves_order(self):
        """Test that first occurrence order is preserved."""
        query = "refactor function class method"
        keywords = extract_keywords(query)
        assert keywords.index("refactor") < keywords.index("function")
        assert keywords.index("function") < keywords.index("class")
        assert keywords.index("class") < keywords.index("method")


class TestResultFormatting:
    """Tests for memory result formatting."""

    def test_format_score_high(self):
        """Test score formatting for high scores (>= 0.7)."""
        text = _format_score(0.8)
        assert "green" in text.style
        assert "0.800" in str(text)

    def test_format_score_medium(self):
        """Test score formatting for medium scores (0.4-0.7)."""
        text = _format_score(0.5)
        assert "yellow" in text.style
        assert "0.500" in str(text)

    def test_format_score_low(self):
        """Test score formatting for low scores (< 0.4)."""
        text = _format_score(0.2)
        assert "red" in text.style
        assert "0.200" in str(text)

    def test_format_score_bold(self):
        """Test score formatting with bold style."""
        text = _format_score(0.8, bold=True)
        assert "bold" in text.style
        assert "green" in text.style

    def test_truncate_path_short(self):
        """Test path truncation when path is short enough."""
        path = "/short/path.py"
        result = _truncate_path(path, 50)
        assert result == path

    def test_truncate_path_long(self):
        """Test path truncation for long paths."""
        path = "/very/long/path/to/some/deeply/nested/file.py"
        result = _truncate_path(path, 20)
        assert result.startswith("...")
        assert result.endswith("file.py")
        assert len(result) <= 20

    def test_truncate_path_filename_only(self):
        """Test path truncation when only filename fits."""
        path = "/path/verylongfilename.py"
        result = _truncate_path(path, 15)
        assert "..." in result
        assert "filename.py" in result or "verylongfi" in result

    def test_truncate_content_short(self):
        """Test content truncation when content is short enough."""
        content = "Short content"
        result = _truncate_content(content, 50)
        assert result == content

    def test_truncate_content_long(self):
        """Test content truncation for long content."""
        content = "This is a very long content that needs to be truncated at some point"
        result = _truncate_content(content, 30)
        assert len(result) <= 30
        assert result.endswith("...")

    def test_truncate_content_word_boundary(self):
        """Test content truncation at word boundary."""
        content = "This is a long sentence with many words"
        result = _truncate_content(content, 20)
        assert result.endswith("...")
        # Should break at word boundary if possible
        assert not result[:-3].endswith(" ")  # No trailing space before ellipsis

    def test_format_memory_results_basic(self):
        """Test basic result formatting without content."""
        results = [
            {
                "chunk_id": "abc123",
                "content": "def calculate():\n    pass",
                "activation_score": 0.8,
                "semantic_score": 0.6,
                "hybrid_score": 0.72,
                "metadata": {
                    "type": "function",
                    "name": "calculate",
                    "file_path": "/path/to/file.py",
                },
            }
        ]
        table = format_memory_results(results, show_content=False)
        assert table is not None
        assert "Memory Search Results" in table.title

    def test_format_memory_results_with_content(self):
        """Test result formatting with content preview."""
        results = [
            {
                "chunk_id": "abc123",
                "content": "def calculate():\n    pass",
                "activation_score": 0.8,
                "semantic_score": 0.6,
                "hybrid_score": 0.72,
                "metadata": {
                    "type": "function",
                    "name": "calculate",
                    "file_path": "/path/to/file.py",
                },
            }
        ]
        table = format_memory_results(results, show_content=True, max_content_length=100)
        assert table is not None
        # Should have additional "Context" column
        assert len(table.columns) > 6  # More columns when showing content

    def test_format_memory_results_empty(self):
        """Test formatting with empty results."""
        table = format_memory_results([], show_content=False)
        assert table is not None
        assert len(table.rows) == 0


class TestMemoryCommand:
    """Tests for memory command CLI integration."""

    def test_memory_command_help(self):
        """Test memory command help text."""
        runner = CliRunner()
        result = runner.invoke(memory_command, ["--help"])
        assert result.exit_code == 0
        assert "Search AURORA memory" in result.output
        assert "--max-results" in result.output
        assert "--type" in result.output
        assert "--min-activation" in result.output

    @patch("aurora_cli.commands.memory.SQLiteStore")
    @patch("aurora_cli.commands.memory.ActivationEngine")
    @patch("aurora_cli.commands.memory.EmbeddingProvider")
    @patch("aurora_cli.commands.memory.HybridRetriever")
    def test_memory_command_basic_search(
        self, mock_retriever_cls, mock_provider_cls, mock_engine_cls, mock_store_cls
    ):
        """Test basic memory search."""
        # Setup mocks
        mock_store = Mock()
        mock_store_cls.return_value = mock_store

        mock_engine = Mock()
        mock_engine_cls.return_value = mock_engine

        mock_provider = Mock()
        mock_provider_cls.return_value = mock_provider

        mock_retriever = Mock()
        mock_retriever_cls.return_value = mock_retriever
        mock_retriever.retrieve.return_value = [
            {
                "chunk_id": "test123",
                "content": "def test(): pass",
                "activation_score": 0.8,
                "semantic_score": 0.6,
                "hybrid_score": 0.72,
                "metadata": {
                    "type": "function",
                    "name": "test",
                    "file_path": "/test.py",
                },
            }
        ]

        # Run command
        runner = CliRunner()
        with runner.isolated_filesystem():
            # Create dummy database file
            Path("aurora.db").touch()

            result = runner.invoke(
                memory_command,
                ["test function", "--db-path", "aurora.db"]
            )

        assert result.exit_code == 0
        assert "Found 1 results" in result.output
        mock_retriever.retrieve.assert_called_once()

    @patch("aurora_cli.commands.memory.SQLiteStore")
    @patch("aurora_cli.commands.memory.ActivationEngine")
    @patch("aurora_cli.commands.memory.EmbeddingProvider")
    @patch("aurora_cli.commands.memory.HybridRetriever")
    def test_memory_command_with_options(
        self, mock_retriever_cls, mock_provider_cls, mock_engine_cls, mock_store_cls
    ):
        """Test memory command with all options."""
        # Setup mocks
        mock_store = Mock()
        mock_store_cls.return_value = mock_store

        mock_engine = Mock()
        mock_engine_cls.return_value = mock_engine

        mock_provider = Mock()
        mock_provider_cls.return_value = mock_provider

        mock_retriever = Mock()
        mock_retriever_cls.return_value = mock_retriever
        mock_retriever.retrieve.return_value = [
            {
                "chunk_id": "test123",
                "content": "def test(): pass",
                "activation_score": 0.9,
                "semantic_score": 0.8,
                "hybrid_score": 0.86,
                "metadata": {
                    "type": "function",
                    "name": "test",
                    "file_path": "/test.py",
                },
            }
        ]

        # Run command with options
        runner = CliRunner()
        with runner.isolated_filesystem():
            Path("aurora.db").touch()

            result = runner.invoke(
                memory_command,
                [
                    "test",
                    "--db-path", "aurora.db",
                    "--max-results", "5",
                    "--type", "function",
                    "--min-activation", "0.5",
                    "--show-content",
                ]
            )

        assert result.exit_code == 0
        mock_retriever.retrieve.assert_called_with("test", top_k=5)

    def test_memory_command_no_database(self):
        """Test memory command when database doesn't exist."""
        runner = CliRunner()
        with runner.isolated_filesystem():
            result = runner.invoke(
                memory_command,
                ["test", "--db-path", "nonexistent.db"]
            )

        assert result.exit_code != 0
        assert "Database not found" in result.output

    @patch("aurora_cli.commands.memory.SQLiteStore")
    @patch("aurora_cli.commands.memory.ActivationEngine")
    @patch("aurora_cli.commands.memory.EmbeddingProvider")
    @patch("aurora_cli.commands.memory.HybridRetriever")
    def test_memory_command_no_results(
        self, mock_retriever_cls, mock_provider_cls, mock_engine_cls, mock_store_cls
    ):
        """Test memory command when no results found."""
        # Setup mocks
        mock_store = Mock()
        mock_store_cls.return_value = mock_store

        mock_engine = Mock()
        mock_engine_cls.return_value = mock_engine

        mock_provider = Mock()
        mock_provider_cls.return_value = mock_provider

        mock_retriever = Mock()
        mock_retriever_cls.return_value = mock_retriever
        mock_retriever.retrieve.return_value = []

        # Run command
        runner = CliRunner()
        with runner.isolated_filesystem():
            Path("aurora.db").touch()

            result = runner.invoke(
                memory_command,
                ["nonexistent query", "--db-path", "aurora.db"]
            )

        assert result.exit_code == 0
        assert "No results found" in result.output

    @patch("aurora_cli.commands.memory.SQLiteStore")
    @patch("aurora_cli.commands.memory.ActivationEngine")
    @patch("aurora_cli.commands.memory.EmbeddingProvider")
    @patch("aurora_cli.commands.memory.HybridRetriever")
    def test_memory_command_type_filter(
        self, mock_retriever_cls, mock_provider_cls, mock_engine_cls, mock_store_cls
    ):
        """Test memory command with type filtering."""
        # Setup mocks
        mock_store = Mock()
        mock_store_cls.return_value = mock_store

        mock_engine = Mock()
        mock_engine_cls.return_value = mock_engine

        mock_provider = Mock()
        mock_provider_cls.return_value = mock_provider

        mock_retriever = Mock()
        mock_retriever_cls.return_value = mock_retriever
        mock_retriever.retrieve.return_value = [
            {
                "chunk_id": "func1",
                "content": "def func1(): pass",
                "activation_score": 0.8,
                "semantic_score": 0.6,
                "hybrid_score": 0.72,
                "metadata": {"type": "function", "name": "func1", "file_path": "/test.py"},
            },
            {
                "chunk_id": "class1",
                "content": "class Class1: pass",
                "activation_score": 0.7,
                "semantic_score": 0.5,
                "hybrid_score": 0.62,
                "metadata": {"type": "class", "name": "Class1", "file_path": "/test.py"},
            },
        ]

        # Run command with type filter
        runner = CliRunner()
        with runner.isolated_filesystem():
            Path("aurora.db").touch()

            result = runner.invoke(
                memory_command,
                ["test", "--db-path", "aurora.db", "--type", "function"]
            )

        assert result.exit_code == 0
        # Should only show 1 result (function, not class)
        assert "Found 1 results" in result.output

    @patch("aurora_cli.commands.memory.SQLiteStore")
    @patch("aurora_cli.commands.memory.ActivationEngine")
    @patch("aurora_cli.commands.memory.EmbeddingProvider")
    @patch("aurora_cli.commands.memory.HybridRetriever")
    def test_memory_command_activation_filter(
        self, mock_retriever_cls, mock_provider_cls, mock_engine_cls, mock_store_cls
    ):
        """Test memory command with activation threshold filtering."""
        # Setup mocks
        mock_store = Mock()
        mock_store_cls.return_value = mock_store

        mock_engine = Mock()
        mock_engine_cls.return_value = mock_engine

        mock_provider = Mock()
        mock_provider_cls.return_value = mock_provider

        mock_retriever = Mock()
        mock_retriever_cls.return_value = mock_retriever
        mock_retriever.retrieve.return_value = [
            {
                "chunk_id": "high",
                "content": "high activation",
                "activation_score": 0.9,
                "semantic_score": 0.6,
                "hybrid_score": 0.78,
                "metadata": {"type": "function", "name": "high", "file_path": "/test.py"},
            },
            {
                "chunk_id": "low",
                "content": "low activation",
                "activation_score": 0.3,
                "semantic_score": 0.8,
                "hybrid_score": 0.50,
                "metadata": {"type": "function", "name": "low", "file_path": "/test.py"},
            },
        ]

        # Run command with activation filter
        runner = CliRunner()
        with runner.isolated_filesystem():
            Path("aurora.db").touch()

            result = runner.invoke(
                memory_command,
                ["test", "--db-path", "aurora.db", "--min-activation", "0.5"]
            )

        assert result.exit_code == 0
        # Should only show 1 result (high activation >= 0.5)
        assert "Found 1 results" in result.output
