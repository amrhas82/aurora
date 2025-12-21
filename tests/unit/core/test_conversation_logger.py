"""Unit tests for ConversationLogger."""

import asyncio
import json
import re
from datetime import datetime
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from aurora_core.logging import ConversationLogger, VerbosityLevel


class TestConversationLogger:
    """Tests for ConversationLogger."""

    @pytest.fixture
    def temp_log_dir(self, tmp_path):
        """Create temporary log directory."""
        return tmp_path / "logs" / "conversations"

    @pytest.fixture
    def logger(self, temp_log_dir):
        """Create logger instance with temp directory."""
        return ConversationLogger(base_path=temp_log_dir, enabled=True)

    @pytest.fixture
    def sample_phase_data(self):
        """Sample phase data for testing."""
        return {
            "assess": {
                "complexity": "MEDIUM",
                "confidence": 0.85,
                "method": "llm",
            },
            "retrieve": {
                "chunks_retrieved": 10,
                "sources": ["code", "docs"],
            },
            "decompose": {
                "subgoals": [
                    {"id": "sg1", "description": "Parse config"},
                    {"id": "sg2", "description": "Validate schema"},
                ],
            },
        }

    @pytest.fixture
    def sample_execution_summary(self):
        """Sample execution summary for testing."""
        return {
            "duration_ms": 1500,
            "overall_score": 0.82,
            "cached": False,
            "cost_usd": 0.0042,
            "tokens_used": {"input": 1200, "output": 350},
        }

    # Test 1-2: Basic initialization
    def test_initialization_default_path(self):
        """Test logger initializes with default path."""
        logger = ConversationLogger()

        expected_path = Path.home() / ".aurora" / "logs" / "conversations"
        assert logger.base_path == expected_path
        assert logger.enabled is True

    def test_initialization_custom_path(self, temp_log_dir):
        """Test logger initializes with custom path."""
        logger = ConversationLogger(base_path=temp_log_dir, enabled=False)

        assert logger.base_path == temp_log_dir
        assert logger.enabled is False

    # Test 3-6: Keyword extraction
    def test_extract_keywords_simple(self, logger):
        """Test keyword extraction from simple query."""
        query = "How do I parse a JSON file?"
        keywords = logger._extract_keywords(query)

        assert len(keywords) == 2
        assert "parse" in keywords
        assert "json" in keywords

    def test_extract_keywords_filters_stop_words(self, logger):
        """Test stop words are filtered out."""
        query = "What is the best way to handle errors?"
        keywords = logger._extract_keywords(query)

        # Should not contain stop words: what, is, the, to
        stop_words = {"what", "is", "the", "to"}
        for keyword in keywords:
            assert keyword not in stop_words

    def test_extract_keywords_handles_special_chars(self, logger):
        """Test keyword extraction handles special characters."""
        query = "Parse JSON & validate XML!"
        keywords = logger._extract_keywords(query)

        assert "parse" in keywords
        assert "json" in keywords

    def test_extract_keywords_empty_query(self, logger):
        """Test keyword extraction with empty query."""
        query = "   "
        keywords = logger._extract_keywords(query)

        assert keywords == []

    # Test 7-10: Filename generation
    def test_generate_filename_with_keywords(self, logger):
        """Test filename generation with extracted keywords."""
        query = "How to parse configuration files?"
        filename = logger._generate_filename(query)

        # Should be: parse-configuration-YYYY-MM-DD.md
        assert filename.endswith(".md")
        assert "parse" in filename
        assert "configuration" in filename
        assert datetime.now().strftime("%Y-%m-%d") in filename

    def test_generate_filename_fallback(self, logger):
        """Test filename generation falls back to 'query' if no keywords."""
        query = "???"
        filename = logger._generate_filename(query)

        assert filename.startswith("query-")
        assert filename.endswith(".md")

    def test_generate_filename_format(self, logger):
        """Test filename follows correct format."""
        query = "Parse JSON files"
        filename = logger._generate_filename(query)

        # Format: keyword1-keyword2-YYYY-MM-DD.md
        pattern = r"^[a-z0-9]+-[a-z0-9]+-\d{4}-\d{2}-\d{2}\.md$"
        assert re.match(pattern, filename)

    def test_generate_filename_consistent(self, logger):
        """Test filename generation is consistent within same day."""
        query = "Parse JSON files"
        filename1 = logger._generate_filename(query)
        filename2 = logger._generate_filename(query)

        assert filename1 == filename2

    # Test 11-13: Unique path handling
    def test_get_unique_path_no_collision(self, logger, temp_log_dir):
        """Test unique path when file doesn't exist."""
        path = temp_log_dir / "test.md"
        unique_path = logger._get_unique_path(path)

        assert unique_path == path

    def test_get_unique_path_with_collision(self, logger, temp_log_dir):
        """Test unique path when file exists."""
        path = temp_log_dir / "test.md"
        temp_log_dir.mkdir(parents=True)
        path.write_text("existing")

        unique_path = logger._get_unique_path(path)

        assert unique_path == temp_log_dir / "test-2.md"

    def test_get_unique_path_multiple_collisions(self, logger, temp_log_dir):
        """Test unique path with multiple collisions."""
        temp_log_dir.mkdir(parents=True)
        (temp_log_dir / "test.md").write_text("existing")
        (temp_log_dir / "test-2.md").write_text("existing")
        (temp_log_dir / "test-3.md").write_text("existing")

        path = temp_log_dir / "test.md"
        unique_path = logger._get_unique_path(path)

        assert unique_path == temp_log_dir / "test-4.md"

    # Test 14-17: Markdown formatting
    def test_format_log_structure(
        self, logger, sample_phase_data, sample_execution_summary
    ):
        """Test log format has correct structure."""
        content = logger._format_log(
            query="Test query",
            query_id="test-123",
            phase_data=sample_phase_data,
            execution_summary=sample_execution_summary,
        )

        # Check all major sections present
        assert "# SOAR Conversation Log" in content
        assert "**Query ID**: test-123" in content
        assert "**User Query**: Test query" in content
        assert "## Phase: Assess" in content
        assert "## Phase: Retrieve" in content
        assert "## Phase: Decompose" in content
        assert "## Execution Summary" in content

    def test_format_log_json_blocks(
        self, logger, sample_phase_data, sample_execution_summary
    ):
        """Test JSON blocks are properly formatted."""
        content = logger._format_log(
            query="Test query",
            query_id="test-123",
            phase_data=sample_phase_data,
            execution_summary=sample_execution_summary,
        )

        # Should contain JSON code blocks
        assert "```json" in content
        assert "```" in content

        # Extract and validate JSON blocks
        json_blocks = re.findall(r"```json\n(.*?)\n```", content, re.DOTALL)
        assert len(json_blocks) >= 3  # At least 3 phases

        for block in json_blocks:
            # Should be valid JSON
            json.loads(block)

    def test_format_log_execution_summary(
        self, logger, sample_phase_data, sample_execution_summary
    ):
        """Test execution summary is formatted correctly."""
        content = logger._format_log(
            query="Test query",
            query_id="test-123",
            phase_data=sample_phase_data,
            execution_summary=sample_execution_summary,
        )

        # Check summary fields (with markdown formatting)
        assert "**Duration**: 1500ms" in content
        assert "**Overall Score**: 0.82" in content
        assert "**Cached**: False" in content
        assert "**Cost**: $0.0042" in content
        assert "**Tokens Used**:" in content

    def test_format_log_with_metadata(
        self, logger, sample_phase_data, sample_execution_summary
    ):
        """Test log includes optional metadata."""
        metadata = {"extra_field": "extra_value"}

        content = logger._format_log(
            query="Test query",
            query_id="test-123",
            phase_data=sample_phase_data,
            execution_summary=sample_execution_summary,
            metadata=metadata,
        )

        assert "## Metadata" in content
        assert "extra_field" in content

    # Test 18-20: Log interaction
    def test_log_interaction_creates_file(
        self, logger, sample_phase_data, sample_execution_summary
    ):
        """Test log_interaction creates log file."""
        # Mock async write to make it synchronous for testing
        with patch.object(logger, "_write_async", new_callable=AsyncMock) as mock_write:
            log_path = logger.log_interaction(
                query="Test query",
                query_id="test-123",
                phase_data=sample_phase_data,
                execution_summary=sample_execution_summary,
            )

            assert log_path is not None
            assert log_path.name.endswith(".md")
            mock_write.assert_called_once()

    def test_log_interaction_disabled(
        self, temp_log_dir, sample_phase_data, sample_execution_summary
    ):
        """Test log_interaction returns None when disabled."""
        logger = ConversationLogger(base_path=temp_log_dir, enabled=False)

        log_path = logger.log_interaction(
            query="Test query",
            query_id="test-123",
            phase_data=sample_phase_data,
            execution_summary=sample_execution_summary,
        )

        assert log_path is None

    def test_log_interaction_creates_directory(
        self, logger, sample_phase_data, sample_execution_summary
    ):
        """Test log_interaction creates year/month directories."""
        with patch.object(logger, "_write_async", new_callable=AsyncMock):
            logger.log_interaction(
                query="Test query",
                query_id="test-123",
                phase_data=sample_phase_data,
                execution_summary=sample_execution_summary,
            )

            # Check directory structure
            now = datetime.now()
            expected_dir = logger.base_path / now.strftime("%Y") / now.strftime("%m")
            assert expected_dir.exists()

    # Test 21-22: Async writing
    @pytest.mark.asyncio
    async def test_write_async_success(self, logger, temp_log_dir):
        """Test async file writing succeeds."""
        temp_log_dir.mkdir(parents=True)
        log_path = temp_log_dir / "test.md"
        content = "Test content"

        await logger._write_async(log_path, content)

        assert log_path.exists()
        assert log_path.read_text() == content

    @pytest.mark.asyncio
    async def test_write_async_error_handling(self, logger, capsys):
        """Test async write handles errors gracefully."""
        # Try to write to invalid path
        invalid_path = Path("/invalid/path/test.md")
        content = "Test content"

        await logger._write_async(invalid_path, content)

        # Should log warning to stderr
        captured = capsys.readouterr()
        assert "Warning: Failed to write log file" in captured.err

    # Test 23: Log rotation
    def test_rotate_logs(self, logger, temp_log_dir):
        """Test log rotation archives old files."""
        # Create test log files in current month directory
        log_dir = logger._get_log_directory()
        log_dir.mkdir(parents=True)

        for i in range(5):
            log_file = log_dir / f"test-{i}.md"
            log_file.write_text(f"Content {i}")

        # Rotate with limit of 3
        logger.rotate_logs(max_files_per_month=3)

        # Check archive directory created
        archive_dir = temp_log_dir / "archive"
        assert archive_dir.exists()

        # Check files were archived
        remaining_files = list(log_dir.glob("*.md"))
        archived_files = list(archive_dir.glob("*.md"))

        assert len(remaining_files) == 3
        assert len(archived_files) == 2

    # Test 24: Error handling
    def test_log_interaction_error_handling(
        self, logger, sample_phase_data, sample_execution_summary, capsys
    ):
        """Test log_interaction handles errors gracefully."""
        # Mock _format_log to raise exception
        with patch.object(logger, "_format_log", side_effect=Exception("Test error")):
            log_path = logger.log_interaction(
                query="Test query",
                query_id="test-123",
                phase_data=sample_phase_data,
                execution_summary=sample_execution_summary,
            )

            assert log_path is None

            # Should log warning to stderr
            captured = capsys.readouterr()
            assert "Warning: Failed to write conversation log" in captured.err

    # Test 25: VerbosityLevel enum
    def test_verbosity_level_enum(self):
        """Test VerbosityLevel enum values."""
        assert VerbosityLevel.QUIET == "quiet"
        assert VerbosityLevel.NORMAL == "normal"
        assert VerbosityLevel.VERBOSE == "verbose"
        assert VerbosityLevel.JSON == "json"

    # Test 26: Log re-parsing
    def test_log_can_be_reparsed(
        self, logger, sample_phase_data, sample_execution_summary, temp_log_dir
    ):
        """Test generated log can be re-parsed (JSON blocks valid)."""
        content = logger._format_log(
            query="Test query",
            query_id="test-123",
            phase_data=sample_phase_data,
            execution_summary=sample_execution_summary,
        )

        # Extract JSON blocks
        json_blocks = re.findall(r"```json\n(.*?)\n```", content, re.DOTALL)

        # All blocks should be valid JSON
        for block in json_blocks:
            parsed = json.loads(block)
            assert isinstance(parsed, dict)

        # Extract phase data
        assess_match = re.search(
            r"## Phase: Assess\n\n```json\n(.*?)\n```", content, re.DOTALL
        )
        assert assess_match
        assess_data = json.loads(assess_match.group(1))
        assert assess_data["complexity"] == "MEDIUM"

    # Test 27-28: Directory structure
    def test_get_log_directory_structure(self, logger):
        """Test log directory follows YYYY/MM structure."""
        log_dir = logger._get_log_directory()
        now = datetime.now()

        expected_dir = logger.base_path / now.strftime("%Y") / now.strftime("%m")
        assert log_dir == expected_dir

    def test_log_directory_changes_by_month(self, logger):
        """Test log directory changes with date."""
        # Get current directory
        dir1 = logger._get_log_directory()

        # Mock different date
        with patch("aurora_core.logging.conversation_logger.datetime") as mock_dt:
            mock_dt.now.return_value = datetime(2025, 6, 15)
            mock_dt.strftime = datetime.strftime  # Keep strftime working
            dir2 = logger._get_log_directory()

        # Directories should be different
        assert dir1 != dir2

    # Test 29: Integration test
    def test_full_logging_workflow(
        self, logger, sample_phase_data, sample_execution_summary
    ):
        """Test complete logging workflow."""
        with patch.object(logger, "_write_async", new_callable=AsyncMock) as mock_write:
            # Log interaction
            log_path = logger.log_interaction(
                query="How to parse JSON files?",
                query_id="test-456",
                phase_data=sample_phase_data,
                execution_summary=sample_execution_summary,
            )

            # Verify path
            assert log_path is not None
            assert "parse-json" in log_path.name or "json-files" in log_path.name

            # Verify write was called
            mock_write.assert_called_once()
            call_args = mock_write.call_args
            written_path = call_args[0][0]
            written_content = call_args[0][1]

            # Verify content
            assert "**Query ID**: test-456" in written_content
            assert "**User Query**: How to parse JSON files?" in written_content
            assert "## Phase: Assess" in written_content
            assert "**Duration**: 1500ms" in written_content

    # Test 30: Edge cases
    def test_log_interaction_with_special_characters(
        self, logger, sample_phase_data, sample_execution_summary
    ):
        """Test logging handles special characters in query."""
        query = "Parse 'JSON' & validate <XML>!"

        with patch.object(logger, "_write_async", new_callable=AsyncMock):
            log_path = logger.log_interaction(
                query=query,
                query_id="test-789",
                phase_data=sample_phase_data,
                execution_summary=sample_execution_summary,
            )

            assert log_path is not None

    def test_log_interaction_with_empty_phases(
        self, logger, sample_execution_summary
    ):
        """Test logging with empty phase data."""
        with patch.object(logger, "_write_async", new_callable=AsyncMock):
            log_path = logger.log_interaction(
                query="Test query",
                query_id="test-999",
                phase_data={},
                execution_summary=sample_execution_summary,
            )

            assert log_path is not None
