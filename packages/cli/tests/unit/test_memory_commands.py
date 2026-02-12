"""Unit tests for aurora_cli.commands.memory CLI commands."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import Mock, patch

import pytest
from click.testing import CliRunner

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


class TestIndexCommand:
    """Test the index_command function."""

    @patch("aurora_cli.commands.memory.MemoryManager")
    @patch("aurora_cli.commands.memory.SQLiteStore")
    @pytest.mark.cli
    def test_index_command_success(
        self, mock_store_class: Mock, mock_manager_class: Mock, tmp_path: Path
    ) -> None:
        mock_store = Mock()
        mock_store_class.return_value = mock_store
        mock_manager = Mock()
        mock_manager_class.return_value = mock_manager
        mock_manager.index_path.return_value = IndexStats(
            files_indexed=5, chunks_created=20, duration_seconds=1.5, errors=0
        )

        runner = CliRunner()
        with runner.isolated_filesystem(temp_dir=tmp_path):
            result = runner.invoke(index_command, ["."])

        assert result.exit_code == 0
        assert "Indexing complete" in result.output
        assert "Files indexed: 5" in result.output
        mock_store.close.assert_called_once()

    @patch("aurora_cli.commands.memory.MemoryManager")
    @patch("aurora_cli.commands.memory.SQLiteStore")
    def test_index_command_shows_errors(
        self, mock_store_class: Mock, mock_manager_class: Mock, tmp_path: Path
    ) -> None:
        mock_store_class.return_value = Mock()
        mock_manager = Mock()
        mock_manager_class.return_value = mock_manager
        mock_manager.index_path.return_value = IndexStats(
            files_indexed=8, chunks_created=25, duration_seconds=1.8, errors=2
        )

        runner = CliRunner()
        with runner.isolated_filesystem(temp_dir=tmp_path):
            result = runner.invoke(index_command, ["."])

        assert result.exit_code == 0
        assert "Errors: 2" in result.output

    @patch("aurora_cli.commands.memory.MemoryManager")
    @patch("aurora_cli.commands.memory.SQLiteStore")
    def test_index_command_handles_store_error(
        self, mock_store_class: Mock, _mock_manager: Mock, tmp_path: Path
    ) -> None:
        mock_store_class.side_effect = MemoryStoreError("Database connection failed")

        runner = CliRunner()
        with runner.isolated_filesystem(temp_dir=tmp_path):
            result = runner.invoke(index_command, ["."])

        assert result.exit_code == 1
        assert "Database connection failed" in result.output


class TestSearchCommand:
    """Test the search_command function."""

    @patch("aurora_cli.commands.memory.MemoryManager")
    @patch("aurora_cli.commands.memory.SQLiteStore")
    def test_search_with_results(
        self, mock_store_class: Mock, mock_manager_class: Mock, tmp_path: Path
    ) -> None:
        mock_store = Mock()
        mock_store_class.return_value = mock_store
        mock_manager = Mock()
        mock_manager_class.return_value = mock_manager
        mock_manager.search.return_value = [
            SearchResult(
                chunk_id="chunk1", file_path="test.py", line_range=(10, 20),
                content="def test_function(): pass", activation_score=0.8,
                semantic_score=0.7, hybrid_score=0.75,
                metadata={"type": "function", "name": "test_function"},
            ),
        ]

        runner = CliRunner()
        with runner.isolated_filesystem(temp_dir=tmp_path):
            Path("aurora.db").touch()
            result = runner.invoke(search_command, ["authentication"])

        assert result.exit_code == 0
        assert "Found 1 result" in result.output
        mock_store.close.assert_called_once()

    @patch("aurora_cli.commands.memory.MemoryManager")
    @patch("aurora_cli.commands.memory.SQLiteStore")
    def test_search_no_results(
        self, mock_store_class: Mock, mock_manager_class: Mock, tmp_path: Path
    ) -> None:
        mock_store_class.return_value = Mock()
        mock_manager = Mock()
        mock_manager_class.return_value = mock_manager
        mock_manager.search.return_value = []

        runner = CliRunner()
        with runner.isolated_filesystem(temp_dir=tmp_path):
            Path("aurora.db").touch()
            result = runner.invoke(search_command, ["nonexistent"])

        assert result.exit_code == 0
        assert "No results found" in result.output

    @patch("aurora_cli.commands.memory.MemoryManager")
    @patch("aurora_cli.commands.memory.SQLiteStore")
    def test_search_handles_store_error(
        self, mock_store_class: Mock, _mock_manager: Mock, tmp_path: Path
    ) -> None:
        mock_store_class.side_effect = MemoryStoreError("Search failed")

        runner = CliRunner()
        with runner.isolated_filesystem(temp_dir=tmp_path):
            Path("aurora.db").touch()
            result = runner.invoke(search_command, ["test"])

        assert result.exit_code == 1
        assert "Search failed" in result.output


class TestStatsCommand:
    """Test the stats_command function."""

    @patch("aurora_cli.commands.memory.MemoryManager")
    @patch("aurora_cli.commands.memory.SQLiteStore")
    def test_stats_with_data(
        self, mock_store_class: Mock, mock_manager_class: Mock, tmp_path: Path
    ) -> None:
        mock_store = Mock()
        mock_store_class.return_value = mock_store
        mock_manager = Mock()
        mock_manager_class.return_value = mock_manager
        mock_manager.get_stats.return_value = MemoryStats(
            total_chunks=150, total_files=25, database_size_mb=2.5,
            languages={"python": 120, "javascript": 30},
        )

        runner = CliRunner()
        with runner.isolated_filesystem(temp_dir=tmp_path):
            Path("aurora.db").touch()
            result = runner.invoke(stats_command, [])

        assert result.exit_code == 0
        assert "150" in result.output
        assert "python" in result.output
        mock_store.close.assert_called_once()

    def test_stats_missing_database(self, tmp_path: Path) -> None:
        runner = CliRunner()
        with runner.isolated_filesystem(temp_dir=tmp_path):
            result = runner.invoke(stats_command, [])

        assert result.exit_code == 1
        assert "Database not found" in result.output

    @patch("aurora_cli.commands.memory.MemoryManager")
    @patch("aurora_cli.commands.memory.SQLiteStore")
    def test_stats_handles_store_error(
        self, mock_store_class: Mock, _mock_manager: Mock, tmp_path: Path
    ) -> None:
        mock_store_class.side_effect = MemoryStoreError("Stats retrieval failed")

        runner = CliRunner()
        with runner.isolated_filesystem(temp_dir=tmp_path):
            Path("aurora.db").touch()
            result = runner.invoke(stats_command, [])

        assert result.exit_code == 1
        assert "Stats retrieval failed" in result.output


class TestHelperFunctions:
    """Test helper functions for display and formatting."""

    def test_truncate_text_short(self) -> None:
        assert _truncate_text("short", 20) == "short"

    def test_truncate_text_long(self) -> None:
        result = _truncate_text("this is a very long text that should be truncated", 20)
        assert len(result) == 20
        assert result.endswith("...")

    def test_format_score_colors(self) -> None:
        high = _format_score(0.85)
        assert "green" in str(high.style)
        med = _format_score(0.5)
        assert "yellow" in str(med.style)
        low = _format_score(0.2)
        assert "red" in str(low.style)

    @patch("aurora_cli.commands.memory.console")
    def test_display_json_results(self, mock_console: Mock) -> None:
        results = [
            SearchResult(
                chunk_id="chunk1", file_path="test.py", line_range=(10, 20),
                content="def test(): pass", activation_score=0.8,
                semantic_score=0.7, hybrid_score=0.75,
                metadata={"type": "function", "name": "test"},
            ),
        ]
        _display_json_results(results)
        json_output = mock_console.print.call_args[0][0]
        assert "chunk1" in json_output
