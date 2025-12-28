"""Unit tests for aurora_cli.commands.memory CLI commands.

This module tests the memory management commands (index, search, stats)
using direct function calls with mocking.
IMPORTANT: These are UNIT tests - they use mocks, NOT subprocess.run().
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import Mock, patch

import pytest
from aurora_cli.commands.memory import (
    _display_json_results,
    _display_rich_results,
    _format_score,
    _truncate_text,
    index_command,
    memory_group,
    search_command,
    stats_command,
)
from aurora_cli.errors import MemoryStoreError
from aurora_cli.memory_manager import IndexStats, MemoryStats, SearchResult
from click.testing import CliRunner


class TestIndexCommand:
    """Test the index_command function."""

    @patch("aurora_cli.commands.memory.MemoryManager")
    @patch("aurora_cli.commands.memory.SQLiteStore")
    @pytest.mark.cli
    def test_index_command_with_default_path(
        self, mock_store_class: Mock, mock_manager_class: Mock, tmp_path: Path
    ) -> None:
        """Test index_command() with default path (current directory)."""
        # Setup mocks
        mock_store = Mock()
        mock_store_class.return_value = mock_store
        mock_manager = Mock()
        mock_manager_class.return_value = mock_manager

        # Mock indexing stats
        stats = IndexStats(
            files_indexed=5,
            chunks_created=20,
            duration_seconds=1.5,
            errors=0,
        )
        mock_manager.index_path.return_value = stats

        # Run command
        runner = CliRunner()
        with runner.isolated_filesystem(temp_dir=tmp_path):
            result = runner.invoke(index_command, ["."])
            # Capture the current working directory inside isolated_filesystem
            expected_db_path = str(Path.cwd() / "aurora.db")

        # Verify success
        assert result.exit_code == 0
        assert "Indexing complete" in result.output
        assert "Files indexed: 5" in result.output
        assert "Chunks created: 20" in result.output

        # Verify store was initialized with correct path
        mock_store_class.assert_called_once_with(expected_db_path)

        # Verify indexing was called with correct path
        mock_manager.index_path.assert_called_once()
        call_args = mock_manager.index_path.call_args
        assert call_args[0][0] == Path(".")

        # Verify store was closed
        mock_store.close.assert_called_once()

    @patch("aurora_cli.commands.memory.MemoryManager")
    @patch("aurora_cli.commands.memory.SQLiteStore")
    @pytest.mark.cli
    def test_index_command_with_custom_db_path(
        self, mock_store_class: Mock, mock_manager_class: Mock, tmp_path: Path
    ) -> None:
        """Test index_command() with custom --db-path option."""
        # Setup mocks
        mock_store = Mock()
        mock_store_class.return_value = mock_store
        mock_manager = Mock()
        mock_manager_class.return_value = mock_manager

        stats = IndexStats(
            files_indexed=3,
            chunks_created=10,
            duration_seconds=0.8,
            errors=0,
        )
        mock_manager.index_path.return_value = stats

        # Run command with custom db-path
        runner = CliRunner()
        custom_db = tmp_path / "custom.db"
        with runner.isolated_filesystem(temp_dir=tmp_path):
            result = runner.invoke(index_command, [".", "--db-path", str(custom_db)])

        # Verify success
        assert result.exit_code == 0

        # Verify store was initialized with custom path
        mock_store_class.assert_called_once_with(str(custom_db))

    @patch("aurora_cli.commands.memory.MemoryManager")
    @patch("aurora_cli.commands.memory.SQLiteStore")
    @pytest.mark.cli
    def test_index_command_with_specific_file(
        self, mock_store_class: Mock, mock_manager_class: Mock, tmp_path: Path
    ) -> None:
        """Test index_command() with specific file path instead of directory."""
        # Setup mocks
        mock_store = Mock()
        mock_store_class.return_value = mock_store
        mock_manager = Mock()
        mock_manager_class.return_value = mock_manager

        stats = IndexStats(
            files_indexed=1,
            chunks_created=3,
            duration_seconds=0.2,
            errors=0,
        )
        mock_manager.index_path.return_value = stats

        # Create a test file
        test_file = tmp_path / "test.py"
        test_file.write_text("def hello(): pass")

        # Run command
        runner = CliRunner()
        result = runner.invoke(index_command, [str(test_file)])

        # Verify success
        assert result.exit_code == 0
        assert "Files indexed: 1" in result.output
        assert "Chunks created: 3" in result.output

    @patch("aurora_cli.commands.memory.MemoryManager")
    @patch("aurora_cli.commands.memory.SQLiteStore")
    def test_index_command_shows_progress(
        self, mock_store_class: Mock, mock_manager_class: Mock, tmp_path: Path
    ) -> None:
        """Test index_command() displays progress bar during indexing."""
        # Setup mocks
        mock_store = Mock()
        mock_store_class.return_value = mock_store
        mock_manager = Mock()
        mock_manager_class.return_value = mock_manager

        # Capture progress callback and simulate updates
        def capture_callback(path, progress_callback=None):
            if progress_callback:
                # Simulate progress updates
                progress_callback(0, 10)
                progress_callback(5, 10)
                progress_callback(10, 10)
            return IndexStats(
                files_indexed=10,
                chunks_created=40,
                duration_seconds=2.0,
                errors=0,
            )

        mock_manager.index_path.side_effect = capture_callback

        # Run command
        runner = CliRunner()
        with runner.isolated_filesystem(temp_dir=tmp_path):
            result = runner.invoke(index_command, ["."])

        # Verify success
        assert result.exit_code == 0

    @patch("aurora_cli.commands.memory.MemoryManager")
    @patch("aurora_cli.commands.memory.SQLiteStore")
    def test_index_command_with_errors(
        self, mock_store_class: Mock, mock_manager_class: Mock, tmp_path: Path
    ) -> None:
        """Test index_command() displays error count from indexing."""
        # Setup mocks
        mock_store = Mock()
        mock_store_class.return_value = mock_store
        mock_manager = Mock()
        mock_manager_class.return_value = mock_manager

        # Return stats with errors
        stats = IndexStats(
            files_indexed=8,
            chunks_created=25,
            duration_seconds=1.8,
            errors=2,
        )
        mock_manager.index_path.return_value = stats

        # Run command
        runner = CliRunner()
        with runner.isolated_filesystem(temp_dir=tmp_path):
            result = runner.invoke(index_command, ["."])

        # Verify error count is displayed
        assert result.exit_code == 0
        assert "Errors: 2" in result.output

    @patch("aurora_cli.commands.memory.MemoryManager")
    @patch("aurora_cli.commands.memory.SQLiteStore")
    def test_index_command_handles_memory_store_error(
        self, mock_store_class: Mock, mock_manager_class: Mock, tmp_path: Path
    ) -> None:
        """Test index_command() handles MemoryStoreError gracefully."""
        # Setup mocks to raise MemoryStoreError
        mock_store_class.side_effect = MemoryStoreError("Database connection failed")

        # Run command
        runner = CliRunner()
        with runner.isolated_filesystem(temp_dir=tmp_path):
            result = runner.invoke(index_command, ["."])

        # Verify error handling
        assert result.exit_code == 1
        assert "Database connection failed" in result.output

    @patch("aurora_cli.commands.memory.MemoryManager")
    @patch("aurora_cli.commands.memory.SQLiteStore")
    @patch("aurora_cli.commands.memory.ErrorHandler")
    def test_index_command_handles_unexpected_error(
        self, mock_error_handler_class: Mock, mock_store_class: Mock, mock_manager_class: Mock, tmp_path: Path
    ) -> None:
        """Test index_command() handles unexpected exceptions with ErrorHandler."""
        # Setup mocks to raise unexpected error
        mock_store_class.side_effect = RuntimeError("Unexpected error")

        # Mock ErrorHandler
        mock_error_handler = Mock()
        mock_error_handler.handle_memory_error.return_value = "Formatted error message"
        mock_error_handler_class.return_value = mock_error_handler

        # Run command
        runner = CliRunner()
        with runner.isolated_filesystem(temp_dir=tmp_path):
            result = runner.invoke(index_command, ["."])

        # Verify error handling
        assert result.exit_code == 1
        assert "Formatted error message" in result.output
        mock_error_handler.handle_memory_error.assert_called_once()


class TestSearchCommand:
    """Test the search_command function."""

    @patch("aurora_cli.commands.memory.MemoryManager")
    @patch("aurora_cli.commands.memory.SQLiteStore")
    def test_search_command_with_results(
        self, mock_store_class: Mock, mock_manager_class: Mock, tmp_path: Path
    ) -> None:
        """Test search_command() with successful search results."""
        # Setup mocks
        mock_store = Mock()
        mock_store_class.return_value = mock_store
        mock_manager = Mock()
        mock_manager_class.return_value = mock_manager

        # Create mock search results
        results = [
            SearchResult(
                chunk_id="chunk1",
                file_path="test.py",
                line_range=(10, 20),
                content="def test_function(): pass",
                activation_score=0.8,
                semantic_score=0.7,
                hybrid_score=0.75,
                metadata={"type": "function", "name": "test_function"},
            ),
            SearchResult(
                chunk_id="chunk2",
                file_path="main.py",
                line_range=(5, 15),
                content="class TestClass: pass",
                activation_score=0.6,
                semantic_score=0.5,
                hybrid_score=0.55,
                metadata={"type": "class", "name": "TestClass"},
            ),
        ]
        mock_manager.search.return_value = results

        # Create database file
        db_path = tmp_path / "aurora.db"
        db_path.touch()

        # Run command
        runner = CliRunner()
        with runner.isolated_filesystem(temp_dir=tmp_path):
            # Create DB in isolated filesystem
            Path("aurora.db").touch()
            result = runner.invoke(search_command, ["authentication"])

        # Verify success
        assert result.exit_code == 0
        assert "Found 2 results" in result.output
        assert "test_function" in result.output
        assert "TestClass" in result.output

        # Verify search was called with correct parameters
        mock_manager.search.assert_called_once_with("authentication", limit=5)

        # Verify store was closed
        mock_store.close.assert_called_once()

    @patch("aurora_cli.commands.memory.MemoryManager")
    @patch("aurora_cli.commands.memory.SQLiteStore")
    def test_search_command_with_custom_limit(
        self, mock_store_class: Mock, mock_manager_class: Mock, tmp_path: Path
    ) -> None:
        """Test search_command() with custom --limit option."""
        # Setup mocks
        mock_store = Mock()
        mock_store_class.return_value = mock_store
        mock_manager = Mock()
        mock_manager_class.return_value = mock_manager
        mock_manager.search.return_value = []

        # Create database file
        db_path = tmp_path / "aurora.db"
        db_path.touch()

        # Run command with custom limit
        runner = CliRunner()
        with runner.isolated_filesystem(temp_dir=tmp_path):
            Path("aurora.db").touch()
            result = runner.invoke(search_command, ["test", "--limit", "10"])

        # Verify search was called with custom limit
        mock_manager.search.assert_called_once_with("test", limit=10)

    @patch("aurora_cli.commands.memory.MemoryManager")
    @patch("aurora_cli.commands.memory.SQLiteStore")
    def test_search_command_with_no_results(
        self, mock_store_class: Mock, mock_manager_class: Mock, tmp_path: Path
    ) -> None:
        """Test search_command() with no search results found."""
        # Setup mocks
        mock_store = Mock()
        mock_store_class.return_value = mock_store
        mock_manager = Mock()
        mock_manager_class.return_value = mock_manager
        mock_manager.search.return_value = []

        # Create database file
        db_path = tmp_path / "aurora.db"
        db_path.touch()

        # Run command
        runner = CliRunner()
        with runner.isolated_filesystem(temp_dir=tmp_path):
            Path("aurora.db").touch()
            result = runner.invoke(search_command, ["nonexistent"])

        # Verify no results message
        assert result.exit_code == 0
        assert "No results found" in result.output
        assert "Broadening your search query" in result.output

    @patch("aurora_cli.commands.memory.MemoryManager")
    @patch("aurora_cli.commands.memory.SQLiteStore")
    def test_search_command_with_json_format(
        self, mock_store_class: Mock, mock_manager_class: Mock, tmp_path: Path
    ) -> None:
        """Test search_command() with --format json option."""
        # Setup mocks
        mock_store = Mock()
        mock_store_class.return_value = mock_store
        mock_manager = Mock()
        mock_manager_class.return_value = mock_manager

        # Create mock search results
        results = [
            SearchResult(
                chunk_id="chunk1",
                file_path="test.py",
                line_range=(10, 20),
                content="def test(): pass",
                activation_score=0.8,
                semantic_score=0.7,
                hybrid_score=0.75,
                metadata={"type": "function", "name": "test"},
            ),
        ]
        mock_manager.search.return_value = results

        # Create database file
        db_path = tmp_path / "aurora.db"
        db_path.touch()

        # Run command with JSON format
        runner = CliRunner()
        with runner.isolated_filesystem(temp_dir=tmp_path):
            Path("aurora.db").touch()
            result = runner.invoke(search_command, ["test", "--format", "json"])

        # Verify JSON output
        assert result.exit_code == 0
        assert '"chunk_id": "chunk1"' in result.output
        assert '"file_path": "test.py"' in result.output
        assert '"line_start": 10' in result.output
        assert '"line_end": 20' in result.output

    @patch("aurora_cli.commands.memory.MemoryManager")
    @patch("aurora_cli.commands.memory.SQLiteStore")
    def test_search_command_with_show_content(
        self, mock_store_class: Mock, mock_manager_class: Mock, tmp_path: Path
    ) -> None:
        """Test search_command() with --show-content flag."""
        # Setup mocks
        mock_store = Mock()
        mock_store_class.return_value = mock_store
        mock_manager = Mock()
        mock_manager_class.return_value = mock_manager

        results = [
            SearchResult(
                chunk_id="chunk1",
                file_path="test.py",
                line_range=(10, 20),
                content="def test_content(): return 'preview'",
                activation_score=0.8,
                semantic_score=0.7,
                hybrid_score=0.75,
                metadata={"type": "function", "name": "test_content"},
            ),
        ]
        mock_manager.search.return_value = results

        # Create database file
        db_path = tmp_path / "aurora.db"
        db_path.touch()

        # Run command with show-content
        runner = CliRunner()
        with runner.isolated_filesystem(temp_dir=tmp_path):
            Path("aurora.db").touch()
            result = runner.invoke(search_command, ["test", "--show-content"])

        # Verify content is shown (display_rich_results will be called with show_content=True)
        assert result.exit_code == 0

    @patch("aurora_cli.commands.memory.ErrorHandler")
    def test_search_command_with_missing_database(
        self, mock_error_handler_class: Mock, tmp_path: Path
    ) -> None:
        """Test search_command() with missing database file."""
        # Mock ErrorHandler
        mock_error_handler = Mock()
        mock_error_handler.handle_path_error.return_value = "Database not found error"
        mock_error_handler_class.return_value = mock_error_handler

        # Run command (no database exists)
        runner = CliRunner()
        with runner.isolated_filesystem(temp_dir=tmp_path):
            result = runner.invoke(search_command, ["test"])

        # Verify error handling
        assert result.exit_code == 1
        assert "Database not found error" in result.output or "Hint:" in result.output

    @patch("aurora_cli.commands.memory.MemoryManager")
    @patch("aurora_cli.commands.memory.SQLiteStore")
    def test_search_command_with_custom_db_path(
        self, mock_store_class: Mock, mock_manager_class: Mock, tmp_path: Path
    ) -> None:
        """Test search_command() with custom --db-path option."""
        # Setup mocks
        mock_store = Mock()
        mock_store_class.return_value = mock_store
        mock_manager = Mock()
        mock_manager_class.return_value = mock_manager
        mock_manager.search.return_value = []

        # Create custom database file
        custom_db = tmp_path / "custom.db"
        custom_db.touch()

        # Run command with custom db-path
        runner = CliRunner()
        result = runner.invoke(search_command, ["test", "--db-path", str(custom_db)])

        # Verify store was initialized with custom path
        mock_store_class.assert_called_once_with(str(custom_db))

    @patch("aurora_cli.commands.memory.MemoryManager")
    @patch("aurora_cli.commands.memory.SQLiteStore")
    def test_search_command_handles_memory_store_error(
        self, mock_store_class: Mock, mock_manager_class: Mock, tmp_path: Path
    ) -> None:
        """Test search_command() handles MemoryStoreError gracefully."""
        # Create database file
        db_path = tmp_path / "aurora.db"
        db_path.touch()

        # Setup mocks to raise MemoryStoreError
        mock_store_class.side_effect = MemoryStoreError("Search failed")

        # Run command
        runner = CliRunner()
        with runner.isolated_filesystem(temp_dir=tmp_path):
            Path("aurora.db").touch()
            result = runner.invoke(search_command, ["test"])

        # Verify error handling
        assert result.exit_code == 1
        assert "Search failed" in result.output


class TestStatsCommand:
    """Test the stats_command function."""

    @patch("aurora_cli.commands.memory.MemoryManager")
    @patch("aurora_cli.commands.memory.SQLiteStore")
    def test_stats_command_with_populated_database(
        self, mock_store_class: Mock, mock_manager_class: Mock, tmp_path: Path
    ) -> None:
        """Test stats_command() with populated database."""
        # Setup mocks
        mock_store = Mock()
        mock_store_class.return_value = mock_store
        mock_manager = Mock()
        mock_manager_class.return_value = mock_manager

        # Create mock stats
        stats = MemoryStats(
            total_chunks=150,
            total_files=25,
            database_size_mb=2.5,
            languages={"python": 120, "javascript": 30},
        )
        mock_manager.get_stats.return_value = stats

        # Create database file
        db_path = tmp_path / "aurora.db"
        db_path.touch()

        # Run command
        runner = CliRunner()
        with runner.isolated_filesystem(temp_dir=tmp_path):
            Path("aurora.db").touch()
            result = runner.invoke(stats_command, [])

        # Verify success
        assert result.exit_code == 0
        assert "150" in result.output  # total_chunks
        assert "25" in result.output   # total_files
        assert "2.5" in result.output  # database_size_mb
        assert "python" in result.output
        assert "javascript" in result.output

        # Verify store was closed
        mock_store.close.assert_called_once()

    @patch("aurora_cli.commands.memory.MemoryManager")
    @patch("aurora_cli.commands.memory.SQLiteStore")
    def test_stats_command_with_empty_database(
        self, mock_store_class: Mock, mock_manager_class: Mock, tmp_path: Path
    ) -> None:
        """Test stats_command() with empty database (no indexed files)."""
        # Setup mocks
        mock_store = Mock()
        mock_store_class.return_value = mock_store
        mock_manager = Mock()
        mock_manager_class.return_value = mock_manager

        # Create mock stats for empty database
        stats = MemoryStats(
            total_chunks=0,
            total_files=0,
            database_size_mb=0.01,
            languages={},
        )
        mock_manager.get_stats.return_value = stats

        # Create database file
        db_path = tmp_path / "aurora.db"
        db_path.touch()

        # Run command
        runner = CliRunner()
        with runner.isolated_filesystem(temp_dir=tmp_path):
            Path("aurora.db").touch()
            result = runner.invoke(stats_command, [])

        # Verify success with zero stats
        assert result.exit_code == 0

    def test_stats_command_with_missing_database(self, tmp_path: Path) -> None:
        """Test stats_command() with missing database file."""
        # Run command (no database exists)
        runner = CliRunner()
        with runner.isolated_filesystem(temp_dir=tmp_path):
            result = runner.invoke(stats_command, [])

        # Verify error handling
        assert result.exit_code == 1
        assert "Database not found" in result.output
        assert "aur mem index" in result.output

    @patch("aurora_cli.commands.memory.MemoryManager")
    @patch("aurora_cli.commands.memory.SQLiteStore")
    def test_stats_command_with_custom_db_path(
        self, mock_store_class: Mock, mock_manager_class: Mock, tmp_path: Path
    ) -> None:
        """Test stats_command() with custom --db-path option."""
        # Setup mocks
        mock_store = Mock()
        mock_store_class.return_value = mock_store
        mock_manager = Mock()
        mock_manager_class.return_value = mock_manager

        stats = MemoryStats(
            total_chunks=50,
            total_files=10,
            database_size_mb=1.0,
            languages={"python": 50},
        )
        mock_manager.get_stats.return_value = stats

        # Create custom database file
        custom_db = tmp_path / "custom.db"
        custom_db.touch()

        # Run command with custom db-path
        runner = CliRunner()
        result = runner.invoke(stats_command, ["--db-path", str(custom_db)])

        # Verify store was initialized with custom path
        mock_store_class.assert_called_once_with(str(custom_db))

    @patch("aurora_cli.commands.memory.MemoryManager")
    @patch("aurora_cli.commands.memory.SQLiteStore")
    def test_stats_command_handles_memory_store_error(
        self, mock_store_class: Mock, mock_manager_class: Mock, tmp_path: Path
    ) -> None:
        """Test stats_command() handles MemoryStoreError gracefully."""
        # Create database file
        db_path = tmp_path / "aurora.db"
        db_path.touch()

        # Setup mocks to raise MemoryStoreError
        mock_store_class.side_effect = MemoryStoreError("Stats retrieval failed")

        # Run command
        runner = CliRunner()
        with runner.isolated_filesystem(temp_dir=tmp_path):
            Path("aurora.db").touch()
            result = runner.invoke(stats_command, [])

        # Verify error handling
        assert result.exit_code == 1
        assert "Stats retrieval failed" in result.output


class TestHelperFunctions:
    """Test helper functions for display and formatting."""

    def test_truncate_text_short_text(self) -> None:
        """Test _truncate_text() with text shorter than max_length."""
        text = "short text"
        result = _truncate_text(text, 20)
        assert result == "short text"

    def test_truncate_text_long_text(self) -> None:
        """Test _truncate_text() with text longer than max_length."""
        text = "this is a very long text that should be truncated"
        result = _truncate_text(text, 20)
        assert len(result) == 20
        assert result.endswith("...")
        assert result == "this is a very lo..."

    def test_truncate_text_exact_length(self) -> None:
        """Test _truncate_text() with text exactly at max_length."""
        text = "exactly twenty chars"
        result = _truncate_text(text, 20)
        assert result == text

    def test_format_score_high(self) -> None:
        """Test _format_score() with high score (>= 0.7) renders green."""
        score_text = _format_score(0.85)
        assert "0.850" in str(score_text)
        assert "green" in str(score_text.style)

    def test_format_score_medium(self) -> None:
        """Test _format_score() with medium score (0.4-0.7) renders yellow."""
        score_text = _format_score(0.5)
        assert "0.500" in str(score_text)
        assert "yellow" in str(score_text.style)

    def test_format_score_low(self) -> None:
        """Test _format_score() with low score (< 0.4) renders red."""
        score_text = _format_score(0.2)
        assert "0.200" in str(score_text)
        assert "red" in str(score_text.style)

    @patch("aurora_cli.commands.memory.console")
    def test_display_rich_results_with_no_results(self, mock_console: Mock) -> None:
        """Test _display_rich_results() with empty results list."""
        _display_rich_results([], "test query", show_content=False)

        # Verify "No results found" message was printed
        print_calls = [str(call) for call in mock_console.print.call_args_list]
        assert any("No results found" in str(call) for call in print_calls)

    @patch("aurora_cli.commands.memory.console")
    def test_display_rich_results_with_results(self, mock_console: Mock) -> None:
        """Test _display_rich_results() with search results."""
        results = [
            SearchResult(
                chunk_id="chunk1",
                file_path="/path/to/test.py",
                line_range=(10, 20),
                content="def test(): pass",
                activation_score=0.8,
                semantic_score=0.7,
                hybrid_score=0.75,
                metadata={"type": "function", "name": "test"},
            ),
        ]

        _display_rich_results(results, "test query", show_content=False)

        # Verify results were printed
        assert mock_console.print.call_count >= 2  # Header + table + stats

    @patch("aurora_cli.commands.memory.console")
    def test_display_json_results(self, mock_console: Mock) -> None:
        """Test _display_json_results() outputs valid JSON."""
        results = [
            SearchResult(
                chunk_id="chunk1",
                file_path="test.py",
                line_range=(10, 20),
                content="def test(): pass",
                activation_score=0.8,
                semantic_score=0.7,
                hybrid_score=0.75,
                metadata={"type": "function", "name": "test"},
            ),
        ]

        _display_json_results(results)

        # Verify JSON was printed
        mock_console.print.assert_called_once()
        json_output = mock_console.print.call_args[0][0]
        assert "chunk_id" in json_output
        assert "chunk1" in json_output


class TestMemoryGroup:
    """Test the memory_group Click group."""

    def test_memory_group_help(self) -> None:
        """Test memory_group displays help text."""
        runner = CliRunner()
        result = runner.invoke(memory_group, ["--help"])

        # Verify help text
        assert result.exit_code == 0
        assert "Memory management commands" in result.output
        assert "index" in result.output
        assert "search" in result.output
        assert "stats" in result.output

    def test_memory_group_has_subcommands(self) -> None:
        """Test memory_group has expected subcommands."""
        assert "index" in memory_group.commands
        assert "search" in memory_group.commands
        assert "stats" in memory_group.commands
