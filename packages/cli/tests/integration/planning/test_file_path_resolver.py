"""Unit tests for FilePathResolver class.

Tests memory-based file path resolution for subgoals.
"""

from pathlib import Path
from unittest.mock import Mock

import pytest

from aurora_cli.config import Config
from aurora_cli.planning.memory import FilePathResolver
from aurora_cli.planning.models import FileResolution, Subgoal
from aurora_core.store.sqlite import SQLiteStore


class TestFilePathResolver:
    """Test suite for FilePathResolver."""

    def test_resolver_initialization(self, tmp_path: Path) -> None:
        """Test FilePathResolver can be instantiated with config."""
        # Arrange
        db_path = tmp_path / "test.db"
        store = SQLiteStore(str(db_path))
        config = Config()

        # Act
        resolver = FilePathResolver(store=store, config=config)

        # Assert
        assert resolver is not None
        assert hasattr(resolver, "resolve_for_subgoal")
        assert hasattr(resolver, "has_indexed_memory")
        assert hasattr(resolver, "format_path_with_confidence")

    def test_resolver_initialization_defaults(self) -> None:
        """Test FilePathResolver can be instantiated with defaults."""
        # Act
        resolver = FilePathResolver()

        # Assert
        assert resolver is not None

    def test_resolve_paths_with_indexed_memory(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Test file path resolution when memory is indexed."""
        # Arrange
        db_path = tmp_path / "test.db"
        store = SQLiteStore(str(db_path))
        resolver = FilePathResolver(store=store)

        # Mock the retriever to return predictable chunks
        mock_chunk1 = Mock()
        mock_chunk1.file_path = "src/auth/oauth.py"
        mock_chunk1.line_start = 10
        mock_chunk1.line_end = 50
        mock_chunk1.score = 0.92

        mock_chunk2 = Mock()
        mock_chunk2.file_path = "src/auth/tokens.py"
        mock_chunk2.line_start = 5
        mock_chunk2.line_end = 30
        mock_chunk2.score = 0.78

        mock_retriever = Mock()
        mock_retriever.retrieve.return_value = [mock_chunk1, mock_chunk2]
        mock_retriever.has_indexed_memory.return_value = True

        # Patch the retriever creation
        monkeypatch.setattr(
            "aurora_cli.planning.memory.MemoryRetriever",
            lambda store, config: mock_retriever,
        )

        # Create new resolver to use patched retriever
        resolver = FilePathResolver(store=store)

        subgoal = Subgoal(
            id="sg-1",
            title="Implement OAuth2 authentication",
            description="Add OAuth2 authentication flow",
            recommended_agent="@code-developer",
        )

        # Act
        resolutions = resolver.resolve_for_subgoal(subgoal, limit=5)

        # Assert
        assert len(resolutions) == 2
        assert resolutions[0].path == "src/auth/oauth.py"
        assert resolutions[0].line_start == 10
        assert resolutions[0].line_end == 50
        assert resolutions[0].confidence == 0.92
        assert resolutions[1].path == "src/auth/tokens.py"
        assert resolutions[1].confidence == 0.78

    def test_line_range_extraction(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test line numbers are extracted correctly from chunks."""
        # Arrange
        db_path = tmp_path / "test.db"
        store = SQLiteStore(str(db_path))

        mock_chunk = Mock()
        mock_chunk.file_path = "src/test.py"
        mock_chunk.line_start = 100
        mock_chunk.line_end = 200
        mock_chunk.score = 0.85

        mock_retriever = Mock()
        mock_retriever.retrieve.return_value = [mock_chunk]
        mock_retriever.has_indexed_memory.return_value = True

        monkeypatch.setattr(
            "aurora_cli.planning.memory.MemoryRetriever",
            lambda store, config: mock_retriever,
        )

        resolver = FilePathResolver(store=store)
        subgoal = Subgoal(
            id="sg-1",
            title="Test subgoal",
            description="Test description for subgoal",
            recommended_agent="@dev",
        )

        # Act
        resolutions = resolver.resolve_for_subgoal(subgoal)

        # Assert
        assert resolutions[0].line_start == 100
        assert resolutions[0].line_end == 200

    def test_resolve_paths_memory_not_indexed(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Test graceful degradation when memory not indexed."""
        # Arrange
        db_path = tmp_path / "test.db"
        store = SQLiteStore(str(db_path))

        mock_retriever = Mock()
        mock_retriever.has_indexed_memory.return_value = False

        monkeypatch.setattr(
            "aurora_cli.planning.memory.MemoryRetriever",
            lambda store, config: mock_retriever,
        )

        resolver = FilePathResolver(store=store)
        subgoal = Subgoal(
            id="sg-1",
            title="Implement OAuth2",
            description="Add OAuth2 authentication flow",
            recommended_agent="@dev",
        )

        # Act
        resolutions = resolver.resolve_for_subgoal(subgoal)

        # Assert - should return generic paths with low confidence
        assert len(resolutions) > 0
        # Generic paths should be marked with needs_resolution or low confidence
        for res in resolutions:
            assert res.confidence < 0.6  # Low confidence marker

    def test_confidence_score_formatting(self) -> None:
        """Test confidence score formatting for display."""
        # Arrange
        resolver = FilePathResolver()

        high_conf = FileResolution(path="src/auth.py", line_start=10, line_end=50, confidence=0.95)
        medium_conf = FileResolution(
            path="src/auth.py",
            line_start=10,
            line_end=50,
            confidence=0.75,
        )
        low_conf = FileResolution(path="src/auth.py", line_start=10, line_end=50, confidence=0.45)

        # Act
        high_str = resolver.format_path_with_confidence(high_conf)
        medium_str = resolver.format_path_with_confidence(medium_conf)
        low_str = resolver.format_path_with_confidence(low_conf)

        # Assert
        assert "src/auth.py" in high_str
        assert "lines 10-50" in high_str
        assert "(suggested)" not in high_str  # High confidence has no annotation

        assert "src/auth.py" in medium_str
        assert "(suggested)" in medium_str  # Medium has suggestion annotation

        assert "src/auth.py" in low_str
        assert "(low confidence)" in low_str  # Low has warning annotation

    def test_graceful_degradation(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """Test plan still generates when memory not indexed."""
        # Arrange
        db_path = tmp_path / "test.db"
        store = SQLiteStore(str(db_path))

        mock_retriever = Mock()
        mock_retriever.has_indexed_memory.return_value = False

        monkeypatch.setattr(
            "aurora_cli.planning.memory.MemoryRetriever",
            lambda store, config: mock_retriever,
        )

        resolver = FilePathResolver(store=store)
        subgoal = Subgoal(
            id="sg-1",
            title="Test subgoal",
            description="Test description for subgoal",
            recommended_agent="@dev",
        )

        # Act
        resolutions = resolver.resolve_for_subgoal(subgoal)

        # Assert - should not raise, should return something
        assert resolutions is not None
        # Should log warning
        assert "Memory not indexed" in caplog.text or "not indexed" in caplog.text.lower()

    def test_has_indexed_memory(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test has_indexed_memory delegates to retriever."""
        # Arrange
        db_path = tmp_path / "test.db"
        store = SQLiteStore(str(db_path))

        mock_retriever = Mock()
        mock_retriever.has_indexed_memory.return_value = True

        monkeypatch.setattr(
            "aurora_cli.planning.memory.MemoryRetriever",
            lambda store, config: mock_retriever,
        )

        resolver = FilePathResolver(store=store)

        # Act
        result = resolver.has_indexed_memory()

        # Assert
        assert result is True
        mock_retriever.has_indexed_memory.assert_called_once()

    def test_format_path_with_confidence_no_line_numbers(self) -> None:
        """Test formatting when line numbers not available."""
        # Arrange
        resolver = FilePathResolver()
        resolution = FileResolution(
            path="src/test.py",
            line_start=None,
            line_end=None,
            confidence=0.85,
        )

        # Act
        result = resolver.format_path_with_confidence(resolution)

        # Assert
        assert "src/test.py" in result
        assert "lines" not in result  # No line numbers to display
