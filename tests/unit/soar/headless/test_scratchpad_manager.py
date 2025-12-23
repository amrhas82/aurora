"""
Unit tests for ScratchpadManager.

Tests scratchpad file management including:
- File existence and initialization
- Scratchpad entry creation and formatting
- Iteration appending with timestamps
- Status tracking and updates
- Termination signal detection
- Cost and iteration counting
- File size enforcement
- Summary generation
- Edge cases and error handling
"""

import re
import tempfile
from datetime import datetime
from pathlib import Path
from unittest.mock import Mock, patch, mock_open

import pytest

from aurora_soar.headless.scratchpad_manager import (
    ScratchpadManager,
    ScratchpadEntry,
    ScratchpadConfig,
    ScratchpadStatus,
    TerminationSignal,
)


class TestScratchpadEntry:
    """Test ScratchpadEntry dataclass."""

    def test_entry_creation(self):
        """Test creating ScratchpadEntry with all fields."""
        timestamp = datetime(2025, 1, 15, 10, 30, 0)
        entry = ScratchpadEntry(
            iteration=1,
            timestamp=timestamp,
            phase="Implementation",
            action="Created file.py",
            result="File created successfully",
            cost=0.05,
            notes="Need to add tests",
        )
        assert entry.iteration == 1
        assert entry.timestamp == timestamp
        assert entry.phase == "Implementation"
        assert entry.action == "Created file.py"
        assert entry.result == "File created successfully"
        assert entry.cost == 0.05
        assert entry.notes == "Need to add tests"

    def test_entry_minimal(self):
        """Test creating ScratchpadEntry with required fields only."""
        timestamp = datetime(2025, 1, 15, 10, 30, 0)
        entry = ScratchpadEntry(
            iteration=1,
            timestamp=timestamp,
            phase="Test",
            action="Action",
            result="Result",
            cost=0.01,
        )
        assert entry.notes is None

    def test_entry_to_markdown(self):
        """Test converting entry to markdown format."""
        timestamp = datetime(2025, 1, 15, 10, 30, 0)
        entry = ScratchpadEntry(
            iteration=1,
            timestamp=timestamp,
            phase="Implementation",
            action="Created file.py",
            result="File created",
            cost=0.05,
        )
        markdown = entry.to_markdown()

        assert "## Iteration 1 - 2025-01-15 10:30:00" in markdown
        assert "**Phase**: Implementation" in markdown
        assert "**Action**: Created file.py" in markdown
        assert "**Result**: File created" in markdown
        assert "**Cost**: $0.0500" in markdown
        assert markdown.endswith("\n")

    def test_entry_to_markdown_with_notes(self):
        """Test markdown conversion includes notes when present."""
        timestamp = datetime(2025, 1, 15, 10, 30, 0)
        entry = ScratchpadEntry(
            iteration=2,
            timestamp=timestamp,
            phase="Testing",
            action="Ran tests",
            result="All passed",
            cost=0.02,
            notes="Coverage is 95%",
        )
        markdown = entry.to_markdown()

        assert "**Notes**: Coverage is 95%" in markdown

    def test_entry_cost_formatting(self):
        """Test cost is formatted with 4 decimal places."""
        timestamp = datetime(2025, 1, 15, 10, 30, 0)
        entry = ScratchpadEntry(
            iteration=1,
            timestamp=timestamp,
            phase="Test",
            action="Action",
            result="Result",
            cost=0.123456,
        )
        markdown = entry.to_markdown()

        assert "**Cost**: $0.1235" in markdown


class TestScratchpadConfig:
    """Test ScratchpadConfig dataclass."""

    def test_config_defaults(self):
        """Test default configuration values."""
        config = ScratchpadConfig()
        assert config.auto_create is True
        assert config.backup_on_init is False
        assert config.include_timestamps is True
        assert config.max_file_size_mb == 10.0

    def test_config_custom_values(self):
        """Test configuration with custom values."""
        config = ScratchpadConfig(
            auto_create=False,
            backup_on_init=True,
            include_timestamps=False,
            max_file_size_mb=5.0,
        )
        assert config.auto_create is False
        assert config.backup_on_init is True
        assert config.include_timestamps is False
        assert config.max_file_size_mb == 5.0


class TestScratchpadManagerInit:
    """Test ScratchpadManager initialization."""

    def test_init_with_string_path(self):
        """Test initialization with string path."""
        manager = ScratchpadManager("/path/to/scratchpad.md")
        assert manager.scratchpad_path == Path("/path/to/scratchpad.md")
        assert isinstance(manager.config, ScratchpadConfig)

    def test_init_with_path_object(self):
        """Test initialization with Path object."""
        path = Path("/path/to/scratchpad.md")
        manager = ScratchpadManager(path)
        assert manager.scratchpad_path == path

    def test_init_with_custom_config(self):
        """Test initialization with custom config."""
        config = ScratchpadConfig(auto_create=False, max_file_size_mb=5.0)
        manager = ScratchpadManager("/path/to/scratchpad.md", config=config)
        assert manager.config.auto_create is False
        assert manager.config.max_file_size_mb == 5.0

    def test_init_converts_to_path(self):
        """Test path is always converted to Path object."""
        manager = ScratchpadManager("scratchpad.md")
        assert isinstance(manager.scratchpad_path, Path)


class TestFileExists:
    """Test file existence checking."""

    def test_exists_returns_false_when_missing(self):
        """Test exists() returns False when file doesn't exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "missing.md"
            manager = ScratchpadManager(path)
            assert manager.exists() is False

    def test_exists_returns_true_when_present(self):
        """Test exists() returns True when file exists."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "scratchpad.md"
            path.write_text("content")
            manager = ScratchpadManager(path)
            assert manager.exists() is True

    def test_exists_returns_false_for_directory(self):
        """Test exists() returns False for directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = ScratchpadManager(tmpdir)
            assert manager.exists() is False


class TestFileSize:
    """Test file size checking."""

    def test_get_file_size_mb_returns_zero_when_missing(self):
        """Test get_file_size_mb() returns 0.0 when file doesn't exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "missing.md"
            manager = ScratchpadManager(path)
            assert manager.get_file_size_mb() == 0.0

    def test_get_file_size_mb_calculates_correctly(self):
        """Test get_file_size_mb() calculates size correctly."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "scratchpad.md"
            # Write 1 KB of content
            content = "x" * 1024
            path.write_text(content)
            manager = ScratchpadManager(path)
            size_mb = manager.get_file_size_mb()
            # Should be approximately 0.001 MB (1 KB / 1024 KB)
            assert 0.0009 < size_mb < 0.0011

    def test_check_file_size_passes_under_limit(self):
        """Test _check_file_size() passes when under limit."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "scratchpad.md"
            path.write_text("small content")
            config = ScratchpadConfig(max_file_size_mb=10.0)
            manager = ScratchpadManager(path, config=config)
            # Should not raise
            manager._check_file_size()

    def test_check_file_size_raises_when_exceeded(self):
        """Test _check_file_size() raises when limit exceeded."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "scratchpad.md"
            # Write 2 KB of content
            content = "x" * 2048
            path.write_text(content)
            # Set limit to 0.001 MB (1 KB)
            config = ScratchpadConfig(max_file_size_mb=0.001)
            manager = ScratchpadManager(path, config=config)

            with pytest.raises(RuntimeError, match="Scratchpad file too large"):
                manager._check_file_size()


class TestInitialize:
    """Test scratchpad initialization."""

    def test_initialize_creates_file(self):
        """Test initialize() creates scratchpad file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "scratchpad.md"
            manager = ScratchpadManager(path)
            manager.initialize(goal="Test goal")

            assert path.exists()
            content = path.read_text()
            assert "# Experiment Scratchpad" in content

    def test_initialize_includes_goal(self):
        """Test initialize() includes goal in scratchpad."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "scratchpad.md"
            manager = ScratchpadManager(path)
            manager.initialize(goal="Implement feature X")

            content = path.read_text()
            assert "**Goal**: Implement feature X" in content

    def test_initialize_includes_timestamp(self):
        """Test initialize() includes timestamp."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "scratchpad.md"
            manager = ScratchpadManager(path)
            manager.initialize(goal="Test")

            content = path.read_text()
            assert "**Started**:" in content
            # Check timestamp format
            assert re.search(r"\*\*Started\*\*:\s*\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}", content)

    def test_initialize_sets_default_status(self):
        """Test initialize() sets status to IN_PROGRESS by default."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "scratchpad.md"
            manager = ScratchpadManager(path)
            manager.initialize(goal="Test")

            content = path.read_text()
            assert "**Status**: IN_PROGRESS" in content

    def test_initialize_with_custom_status(self):
        """Test initialize() with custom status."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "scratchpad.md"
            manager = ScratchpadManager(path)
            manager.initialize(goal="Test", status=ScratchpadStatus.GOAL_ACHIEVED)

            content = path.read_text()
            assert "**Status**: GOAL_ACHIEVED" in content

    def test_initialize_creates_backup_when_configured(self):
        """Test initialize() creates backup when backup_on_init is True."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "scratchpad.md"
            backup_path = Path(tmpdir) / "scratchpad.md.bak"

            # Create existing file
            path.write_text("existing content")

            config = ScratchpadConfig(backup_on_init=True)
            manager = ScratchpadManager(path, config=config)
            manager.initialize(goal="Test")

            assert backup_path.exists()
            assert backup_path.read_text() == "existing content"

    def test_initialize_overwrites_without_backup_by_default(self):
        """Test initialize() overwrites without backup by default."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "scratchpad.md"
            backup_path = Path(tmpdir) / "scratchpad.md.bak"

            # Create existing file
            path.write_text("existing content")

            manager = ScratchpadManager(path)
            manager.initialize(goal="New goal")

            assert not backup_path.exists()
            assert "New goal" in path.read_text()

    def test_initialize_raises_on_write_error(self):
        """Test initialize() raises RuntimeError on write failure."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Use a directory as the path to cause write error
            path = Path(tmpdir)
            manager = ScratchpadManager(path)

            with pytest.raises(RuntimeError, match="Failed to initialize scratchpad"):
                manager.initialize(goal="Test")


class TestRead:
    """Test scratchpad reading."""

    def test_read_returns_content(self):
        """Test read() returns file content."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "scratchpad.md"
            expected_content = "# Test Content\nLine 2"
            path.write_text(expected_content)

            manager = ScratchpadManager(path)
            content = manager.read()

            assert content == expected_content

    def test_read_raises_when_file_missing(self):
        """Test read() raises FileNotFoundError when file doesn't exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "missing.md"
            manager = ScratchpadManager(path)

            with pytest.raises(FileNotFoundError, match="Scratchpad file not found"):
                manager.read()

    def test_read_error_message_includes_path(self):
        """Test read() error message includes file path."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "missing.md"
            manager = ScratchpadManager(path)

            with pytest.raises(FileNotFoundError, match=str(path)):
                manager.read()

    def test_read_error_message_suggests_initialize(self):
        """Test read() error message suggests using initialize()."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "missing.md"
            manager = ScratchpadManager(path)

            with pytest.raises(FileNotFoundError, match="Initialize with manager.initialize"):
                manager.read()

    def test_read_handles_utf8_encoding(self):
        """Test read() handles UTF-8 encoding."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "scratchpad.md"
            content = "Unicode: 你好 🚀"
            path.write_text(content, encoding="utf-8")

            manager = ScratchpadManager(path)
            assert manager.read() == content

    def test_read_raises_runtime_error_on_read_failure(self):
        """Test read() raises RuntimeError on read failure."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "scratchpad.md"
            path.write_text("content")
            manager = ScratchpadManager(path)

            # Mock read_text to raise exception
            with patch.object(Path, "read_text", side_effect=OSError("Permission denied")):
                with pytest.raises(RuntimeError, match="Failed to read scratchpad"):
                    manager.read()


class TestAppend:
    """Test content appending."""

    def test_append_adds_content(self):
        """Test append() adds content to existing file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "scratchpad.md"
            path.write_text("Initial content\n")

            manager = ScratchpadManager(path)
            manager.append("New line\n")

            content = path.read_text()
            assert content == "Initial content\nNew line\n"

    def test_append_creates_file_when_auto_create_enabled(self):
        """Test append() creates file when auto_create is True."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "scratchpad.md"
            config = ScratchpadConfig(auto_create=True)
            manager = ScratchpadManager(path, config=config)

            manager.append("Content\n")

            assert path.exists()
            content = path.read_text()
            # Should have auto-created header + appended content
            assert "# Experiment Scratchpad" in content
            assert "Content\n" in content

    def test_append_raises_when_auto_create_disabled(self):
        """Test append() raises FileNotFoundError when auto_create is False."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "scratchpad.md"
            config = ScratchpadConfig(auto_create=False)
            manager = ScratchpadManager(path, config=config)

            with pytest.raises(FileNotFoundError, match="Scratchpad file not found"):
                manager.append("Content\n")

    def test_append_checks_file_size(self):
        """Test append() checks file size before appending."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "scratchpad.md"
            # Write content that exceeds limit
            path.write_text("x" * 2048)

            config = ScratchpadConfig(max_file_size_mb=0.001)  # 1 KB limit
            manager = ScratchpadManager(path, config=config)

            with pytest.raises(RuntimeError, match="Scratchpad file too large"):
                manager.append("More content\n")

    def test_append_handles_utf8_encoding(self):
        """Test append() handles UTF-8 encoding."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "scratchpad.md"
            path.write_text("Initial\n")

            manager = ScratchpadManager(path)
            manager.append("Unicode: 你好 🚀\n")

            content = path.read_text()
            assert "Unicode: 你好 🚀" in content

    def test_append_raises_runtime_error_on_write_failure(self):
        """Test append() raises RuntimeError on write failure."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "scratchpad.md"
            path.write_text("content")
            manager = ScratchpadManager(path)

            # Mock open to raise exception
            with patch("builtins.open", side_effect=OSError("Permission denied")):
                with pytest.raises(RuntimeError, match="Failed to append to scratchpad"):
                    manager.append("new content")


class TestAppendIteration:
    """Test iteration appending."""

    def test_append_iteration_adds_entry(self):
        """Test append_iteration() adds formatted entry."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "scratchpad.md"
            manager = ScratchpadManager(path)
            manager.initialize(goal="Test")

            manager.append_iteration(
                iteration=1,
                phase="Implementation",
                action="Created file.py",
                result="File created",
                cost=0.05,
            )

            content = path.read_text()
            assert "## Iteration 1" in content
            assert "**Phase**: Implementation" in content
            assert "**Action**: Created file.py" in content
            assert "**Result**: File created" in content
            assert "**Cost**: $0.0500" in content

    def test_append_iteration_includes_timestamp(self):
        """Test append_iteration() includes timestamp by default."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "scratchpad.md"
            manager = ScratchpadManager(path)
            manager.initialize(goal="Test")

            manager.append_iteration(
                iteration=1,
                phase="Test",
                action="Action",
                result="Result",
                cost=0.01,
            )

            content = path.read_text()
            # Check for timestamp in format "YYYY-MM-DD HH:MM:SS"
            assert re.search(r"## Iteration 1 - \d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}", content)

    def test_append_iteration_with_notes(self):
        """Test append_iteration() includes notes when provided."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "scratchpad.md"
            manager = ScratchpadManager(path)
            manager.initialize(goal="Test")

            manager.append_iteration(
                iteration=1,
                phase="Test",
                action="Action",
                result="Result",
                cost=0.01,
                notes="Important note",
            )

            content = path.read_text()
            assert "**Notes**: Important note" in content

    def test_append_iteration_multiple_entries(self):
        """Test appending multiple iterations."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "scratchpad.md"
            manager = ScratchpadManager(path)
            manager.initialize(goal="Test")

            manager.append_iteration(
                iteration=1,
                phase="Phase1",
                action="Action1",
                result="Result1",
                cost=0.01,
            )
            manager.append_iteration(
                iteration=2,
                phase="Phase2",
                action="Action2",
                result="Result2",
                cost=0.02,
            )

            content = path.read_text()
            assert "## Iteration 1" in content
            assert "## Iteration 2" in content
            assert "Action1" in content
            assert "Action2" in content


class TestUpdateStatus:
    """Test status updating."""

    def test_update_status_changes_status(self):
        """Test update_status() changes the status line."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "scratchpad.md"
            manager = ScratchpadManager(path)
            manager.initialize(goal="Test")

            manager.update_status(ScratchpadStatus.GOAL_ACHIEVED)

            content = path.read_text()
            assert "**Status**: GOAL_ACHIEVED" in content

    def test_update_status_preserves_other_content(self):
        """Test update_status() preserves other content."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "scratchpad.md"
            manager = ScratchpadManager(path)
            manager.initialize(goal="Test goal")
            manager.append_iteration(
                iteration=1,
                phase="Test",
                action="Action",
                result="Result",
                cost=0.01,
            )

            manager.update_status(ScratchpadStatus.BUDGET_EXCEEDED)

            content = path.read_text()
            assert "**Status**: BUDGET_EXCEEDED" in content
            assert "**Goal**: Test goal" in content
            assert "## Iteration 1" in content

    def test_update_status_multiple_changes(self):
        """Test multiple status updates."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "scratchpad.md"
            manager = ScratchpadManager(path)
            manager.initialize(goal="Test")

            manager.update_status(ScratchpadStatus.BLOCKED)
            content1 = path.read_text()
            assert "**Status**: BLOCKED" in content1

            manager.update_status(ScratchpadStatus.GOAL_ACHIEVED)
            content2 = path.read_text()
            assert "**Status**: GOAL_ACHIEVED" in content2
            # Should not have old status
            assert content2.count("**Status**:") == 1

    def test_update_status_raises_on_missing_file(self):
        """Test update_status() raises when file doesn't exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "missing.md"
            manager = ScratchpadManager(path)

            with pytest.raises(FileNotFoundError):
                manager.update_status(ScratchpadStatus.GOAL_ACHIEVED)

    def test_update_status_raises_runtime_error_on_write_failure(self):
        """Test update_status() raises RuntimeError on write failure."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "scratchpad.md"
            manager = ScratchpadManager(path)
            manager.initialize(goal="Test")

            # Mock write_text to raise exception
            with patch.object(Path, "write_text", side_effect=OSError("Permission denied")):
                with pytest.raises(RuntimeError, match="Failed to update status in scratchpad"):
                    manager.update_status(ScratchpadStatus.GOAL_ACHIEVED)


class TestGetStatus:
    """Test status parsing."""

    def test_get_status_returns_correct_status(self):
        """Test get_status() returns correct status."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "scratchpad.md"
            manager = ScratchpadManager(path)
            manager.initialize(goal="Test", status=ScratchpadStatus.IN_PROGRESS)

            status = manager.get_status()
            assert status == ScratchpadStatus.IN_PROGRESS

    def test_get_status_after_update(self):
        """Test get_status() returns updated status."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "scratchpad.md"
            manager = ScratchpadManager(path)
            manager.initialize(goal="Test")
            manager.update_status(ScratchpadStatus.GOAL_ACHIEVED)

            status = manager.get_status()
            assert status == ScratchpadStatus.GOAL_ACHIEVED

    def test_get_status_returns_none_when_missing(self):
        """Test get_status() returns None when file doesn't exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "missing.md"
            manager = ScratchpadManager(path)

            status = manager.get_status()
            assert status is None

    def test_get_status_returns_none_on_invalid_status(self):
        """Test get_status() returns None on invalid status value."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "scratchpad.md"
            path.write_text("**Status**: INVALID_STATUS")
            manager = ScratchpadManager(path)

            status = manager.get_status()
            assert status is None


class TestTerminationSignals:
    """Test termination signal detection."""

    def test_has_termination_signal_false_for_in_progress(self):
        """Test has_termination_signal() returns False for IN_PROGRESS."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "scratchpad.md"
            manager = ScratchpadManager(path)
            manager.initialize(goal="Test", status=ScratchpadStatus.IN_PROGRESS)

            assert manager.has_termination_signal() is False

    def test_has_termination_signal_true_for_goal_achieved(self):
        """Test has_termination_signal() returns True for GOAL_ACHIEVED."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "scratchpad.md"
            manager = ScratchpadManager(path)
            manager.initialize(goal="Test", status=ScratchpadStatus.GOAL_ACHIEVED)

            assert manager.has_termination_signal() is True

    def test_has_termination_signal_true_for_budget_exceeded(self):
        """Test has_termination_signal() returns True for BUDGET_EXCEEDED."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "scratchpad.md"
            manager = ScratchpadManager(path)
            manager.initialize(goal="Test", status=ScratchpadStatus.BUDGET_EXCEEDED)

            assert manager.has_termination_signal() is True

    def test_has_termination_signal_true_for_max_iterations(self):
        """Test has_termination_signal() returns True for MAX_ITERATIONS."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "scratchpad.md"
            manager = ScratchpadManager(path)
            manager.initialize(goal="Test", status=ScratchpadStatus.MAX_ITERATIONS)

            assert manager.has_termination_signal() is True

    def test_has_termination_signal_true_for_blocked(self):
        """Test has_termination_signal() returns True for BLOCKED."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "scratchpad.md"
            manager = ScratchpadManager(path)
            manager.initialize(goal="Test", status=ScratchpadStatus.BLOCKED)

            assert manager.has_termination_signal() is True

    def test_has_termination_signal_false_when_no_status(self):
        """Test has_termination_signal() returns False when status not found."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "scratchpad.md"
            path.write_text("No status line")
            manager = ScratchpadManager(path)

            assert manager.has_termination_signal() is False

    def test_get_termination_signal_returns_correct_signal(self):
        """Test get_termination_signal() returns correct TerminationSignal."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "scratchpad.md"
            manager = ScratchpadManager(path)
            manager.initialize(goal="Test", status=ScratchpadStatus.GOAL_ACHIEVED)

            signal = manager.get_termination_signal()
            assert signal == TerminationSignal.GOAL_ACHIEVED

    def test_get_termination_signal_none_for_in_progress(self):
        """Test get_termination_signal() returns None for IN_PROGRESS."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "scratchpad.md"
            manager = ScratchpadManager(path)
            manager.initialize(goal="Test", status=ScratchpadStatus.IN_PROGRESS)

            signal = manager.get_termination_signal()
            assert signal is None

    def test_get_termination_signal_none_when_no_status(self):
        """Test get_termination_signal() returns None when status is None."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "scratchpad.md"
            path.write_text("No status line")
            manager = ScratchpadManager(path)

            signal = manager.get_termination_signal()
            assert signal is None

    def test_get_termination_signal_maps_all_statuses(self):
        """Test get_termination_signal() maps all termination statuses."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "scratchpad.md"
            manager = ScratchpadManager(path)

            # Test BUDGET_EXCEEDED
            manager.initialize(goal="Test", status=ScratchpadStatus.BUDGET_EXCEEDED)
            assert manager.get_termination_signal() == TerminationSignal.BUDGET_EXCEEDED

            # Test MAX_ITERATIONS
            manager.update_status(ScratchpadStatus.MAX_ITERATIONS)
            assert manager.get_termination_signal() == TerminationSignal.MAX_ITERATIONS

            # Test BLOCKED
            manager.update_status(ScratchpadStatus.BLOCKED)
            assert manager.get_termination_signal() == TerminationSignal.BLOCKED


class TestIterationCounting:
    """Test iteration counting."""

    def test_get_iteration_count_zero_when_empty(self):
        """Test get_iteration_count() returns 0 for new scratchpad."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "scratchpad.md"
            manager = ScratchpadManager(path)
            manager.initialize(goal="Test")

            count = manager.get_iteration_count()
            assert count == 0

    def test_get_iteration_count_after_one_iteration(self):
        """Test get_iteration_count() returns 1 after one iteration."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "scratchpad.md"
            manager = ScratchpadManager(path)
            manager.initialize(goal="Test")
            manager.append_iteration(
                iteration=1,
                phase="Test",
                action="Action",
                result="Result",
                cost=0.01,
            )

            count = manager.get_iteration_count()
            assert count == 1

    def test_get_iteration_count_multiple_iterations(self):
        """Test get_iteration_count() counts multiple iterations."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "scratchpad.md"
            manager = ScratchpadManager(path)
            manager.initialize(goal="Test")

            for i in range(1, 6):
                manager.append_iteration(
                    iteration=i,
                    phase="Test",
                    action=f"Action {i}",
                    result=f"Result {i}",
                    cost=0.01,
                )

            count = manager.get_iteration_count()
            assert count == 5

    def test_get_iteration_count_zero_when_missing(self):
        """Test get_iteration_count() returns 0 when file doesn't exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "missing.md"
            manager = ScratchpadManager(path)

            count = manager.get_iteration_count()
            assert count == 0


class TestCostTracking:
    """Test cost calculation."""

    def test_get_total_cost_zero_when_empty(self):
        """Test get_total_cost() returns 0.0 for new scratchpad."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "scratchpad.md"
            manager = ScratchpadManager(path)
            manager.initialize(goal="Test")

            total = manager.get_total_cost()
            assert total == 0.0

    def test_get_total_cost_single_iteration(self):
        """Test get_total_cost() returns cost from single iteration."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "scratchpad.md"
            manager = ScratchpadManager(path)
            manager.initialize(goal="Test")
            manager.append_iteration(
                iteration=1,
                phase="Test",
                action="Action",
                result="Result",
                cost=0.05,
            )

            total = manager.get_total_cost()
            assert total == 0.05

    def test_get_total_cost_sums_multiple_iterations(self):
        """Test get_total_cost() sums costs from multiple iterations."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "scratchpad.md"
            manager = ScratchpadManager(path)
            manager.initialize(goal="Test")

            manager.append_iteration(
                iteration=1,
                phase="Test",
                action="Action1",
                result="Result1",
                cost=0.05,
            )
            manager.append_iteration(
                iteration=2,
                phase="Test",
                action="Action2",
                result="Result2",
                cost=0.03,
            )
            manager.append_iteration(
                iteration=3,
                phase="Test",
                action="Action3",
                result="Result3",
                cost=0.02,
            )

            total = manager.get_total_cost()
            assert total == 0.10

    def test_get_total_cost_handles_decimal_precision(self):
        """Test get_total_cost() handles decimal precision correctly."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "scratchpad.md"
            manager = ScratchpadManager(path)
            manager.initialize(goal="Test")

            manager.append_iteration(
                iteration=1,
                phase="Test",
                action="Action",
                result="Result",
                cost=0.123456,
            )

            total = manager.get_total_cost()
            # Should parse the formatted cost "$0.1235"
            assert abs(total - 0.1235) < 0.0001

    def test_get_total_cost_zero_when_missing(self):
        """Test get_total_cost() returns 0.0 when file doesn't exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "missing.md"
            manager = ScratchpadManager(path)

            total = manager.get_total_cost()
            assert total == 0.0


class TestSummary:
    """Test summary generation."""

    def test_get_summary_when_file_missing(self):
        """Test get_summary() when file doesn't exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "missing.md"
            manager = ScratchpadManager(path)

            summary = manager.get_summary()

            assert summary["exists"] is False
            assert summary["status"] is None
            assert summary["iteration_count"] == 0
            assert summary["total_cost"] == 0.0
            assert summary["file_size_mb"] == 0.0
            assert summary["has_termination_signal"] is False

    def test_get_summary_for_new_scratchpad(self):
        """Test get_summary() for newly initialized scratchpad."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "scratchpad.md"
            manager = ScratchpadManager(path)
            manager.initialize(goal="Test")

            summary = manager.get_summary()

            assert summary["exists"] is True
            assert summary["status"] == "IN_PROGRESS"
            assert summary["iteration_count"] == 0
            assert summary["total_cost"] == 0.0
            assert summary["file_size_mb"] > 0.0
            assert summary["has_termination_signal"] is False

    def test_get_summary_with_iterations(self):
        """Test get_summary() with multiple iterations."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "scratchpad.md"
            manager = ScratchpadManager(path)
            manager.initialize(goal="Test")

            manager.append_iteration(
                iteration=1,
                phase="Test",
                action="Action1",
                result="Result1",
                cost=0.05,
            )
            manager.append_iteration(
                iteration=2,
                phase="Test",
                action="Action2",
                result="Result2",
                cost=0.03,
            )

            summary = manager.get_summary()

            assert summary["exists"] is True
            assert summary["status"] == "IN_PROGRESS"
            assert summary["iteration_count"] == 2
            assert summary["total_cost"] == 0.08
            assert summary["has_termination_signal"] is False

    def test_get_summary_with_termination_signal(self):
        """Test get_summary() detects termination signal."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "scratchpad.md"
            manager = ScratchpadManager(path)
            manager.initialize(goal="Test", status=ScratchpadStatus.GOAL_ACHIEVED)

            summary = manager.get_summary()

            assert summary["status"] == "GOAL_ACHIEVED"
            assert summary["has_termination_signal"] is True

    def test_get_summary_includes_all_fields(self):
        """Test get_summary() includes all expected fields."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "scratchpad.md"
            manager = ScratchpadManager(path)
            manager.initialize(goal="Test")

            summary = manager.get_summary()

            expected_fields = {
                "exists",
                "status",
                "iteration_count",
                "total_cost",
                "file_size_mb",
                "has_termination_signal",
            }
            assert set(summary.keys()) == expected_fields


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_empty_goal(self):
        """Test initialization with empty goal."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "scratchpad.md"
            manager = ScratchpadManager(path)
            manager.initialize(goal="")

            content = path.read_text()
            assert "**Goal**: " in content

    def test_goal_with_special_characters(self):
        """Test goal with special characters."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "scratchpad.md"
            manager = ScratchpadManager(path)
            goal = "Test with $pecial Ch@rs & **markdown** `code`"
            manager.initialize(goal=goal)

            content = path.read_text()
            assert goal in content

    def test_large_cost_value(self):
        """Test handling of large cost values."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "scratchpad.md"
            manager = ScratchpadManager(path)
            manager.initialize(goal="Test")

            manager.append_iteration(
                iteration=1,
                phase="Test",
                action="Action",
                result="Result",
                cost=999.9999,
            )

            total = manager.get_total_cost()
            assert abs(total - 999.9999) < 0.0001

    def test_zero_cost(self):
        """Test handling of zero cost."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "scratchpad.md"
            manager = ScratchpadManager(path)
            manager.initialize(goal="Test")

            manager.append_iteration(
                iteration=1,
                phase="Test",
                action="Action",
                result="Result",
                cost=0.0,
            )

            total = manager.get_total_cost()
            assert total == 0.0

    def test_very_long_action_text(self):
        """Test handling of very long action text."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "scratchpad.md"
            manager = ScratchpadManager(path)
            manager.initialize(goal="Test")

            long_action = "A" * 10000
            manager.append_iteration(
                iteration=1,
                phase="Test",
                action=long_action,
                result="Result",
                cost=0.01,
            )

            content = path.read_text()
            assert long_action in content

    def test_unicode_in_entries(self):
        """Test handling of Unicode in entries."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "scratchpad.md"
            manager = ScratchpadManager(path)
            manager.initialize(goal="测试 Test 🚀")

            manager.append_iteration(
                iteration=1,
                phase="实施",
                action="创建文件",
                result="成功",
                cost=0.01,
                notes="注释 📝",
            )

            content = path.read_text()
            assert "测试 Test 🚀" in content
            assert "实施" in content
            assert "创建文件" in content
