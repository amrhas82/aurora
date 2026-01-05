"""
Unit tests for simplified Scratchpad manager.

Following TDD RED-GREEN-REFACTOR cycle:
- Task 3.1-3.5: RED phase - write failing tests
- Task 3.6-3.10: GREEN phase - implement to pass tests
- Task 3.11-3.12: REFACTOR phase - improve code quality
"""

import pytest
from pathlib import Path
from datetime import datetime
from aurora_soar.headless.scratchpad import Scratchpad, ScratchpadEntry, ExecutionStatus


class TestScratchpadInitialization:
    """Test Scratchpad initialization - Task 3.1."""

    def test_scratchpad_creates_new_file(self, tmp_path):
        """Test that Scratchpad creates a new file if it doesn't exist."""
        scratchpad_file = tmp_path / "scratchpad.md"

        assert not scratchpad_file.exists()

        scratchpad = Scratchpad(str(scratchpad_file))

        assert scratchpad_file.exists()
        assert scratchpad_file.is_file()

    def test_scratchpad_loads_existing_file(self, tmp_path):
        """Test that Scratchpad loads existing file without overwriting."""
        scratchpad_file = tmp_path / "existing_scratchpad.md"
        scratchpad_file.write_text("# Existing Content\n\nSome data")

        scratchpad = Scratchpad(str(scratchpad_file))

        content = scratchpad_file.read_text()
        assert "Existing Content" in content


class TestScratchpadAppendIteration:
    """Test Scratchpad appending iteration entries - Task 3.2."""

    def test_append_iteration_with_timestamp(self, tmp_path):
        """Test that appending iteration includes timestamp."""
        scratchpad_file = tmp_path / "scratchpad.md"
        scratchpad = Scratchpad(str(scratchpad_file))

        scratchpad.append_iteration(
            iteration=1,
            goal="Test goal",
            action="Test action",
            result="Test result"
        )

        content = scratchpad_file.read_text()
        assert "## Iteration 1" in content
        assert "Test goal" in content
        assert "Test action" in content
        assert "Test result" in content
        # Check timestamp format (ISO 8601)
        assert any(char in content for char in ['T', ':'])  # Basic timestamp check

    def test_append_multiple_iterations(self, tmp_path):
        """Test appending multiple iterations maintains order."""
        scratchpad_file = tmp_path / "scratchpad.md"
        scratchpad = Scratchpad(str(scratchpad_file))

        scratchpad.append_iteration(1, "Goal 1", "Action 1", "Result 1")
        scratchpad.append_iteration(2, "Goal 2", "Action 2", "Result 2")
        scratchpad.append_iteration(3, "Goal 3", "Action 3", "Result 3")

        content = scratchpad_file.read_text()

        # Check order is maintained
        idx_iter1 = content.find("Iteration 1")
        idx_iter2 = content.find("Iteration 2")
        idx_iter3 = content.find("Iteration 3")

        assert idx_iter1 < idx_iter2 < idx_iter3


class TestScratchpadReadEntries:
    """Test Scratchpad reading existing entries - Task 3.3."""

    def test_read_entries_from_scratchpad(self, tmp_path):
        """Test reading back entries from scratchpad."""
        scratchpad_file = tmp_path / "scratchpad.md"
        scratchpad = Scratchpad(str(scratchpad_file))

        scratchpad.append_iteration(1, "Goal A", "Action A", "Result A")
        scratchpad.append_iteration(2, "Goal B", "Action B", "Result B")

        entries = scratchpad.read_entries()

        assert len(entries) == 2
        assert entries[0].iteration == 1
        assert entries[0].goal == "Goal A"
        assert entries[1].iteration == 2
        assert entries[1].goal == "Goal B"

    def test_read_empty_scratchpad(self, tmp_path):
        """Test reading entries from empty scratchpad returns empty list."""
        scratchpad_file = tmp_path / "empty_scratchpad.md"
        scratchpad = Scratchpad(str(scratchpad_file))

        entries = scratchpad.read_entries()

        assert entries == []


class TestScratchpadStatusUpdate:
    """Test Scratchpad status updates - Task 3.4."""

    def test_update_status_changes_execution_state(self, tmp_path):
        """Test updating execution status."""
        scratchpad_file = tmp_path / "scratchpad.md"
        scratchpad = Scratchpad(str(scratchpad_file))

        scratchpad.update_status(ExecutionStatus.PENDING)
        assert scratchpad.get_current_status() == ExecutionStatus.PENDING

        scratchpad.update_status(ExecutionStatus.IN_PROGRESS)
        assert scratchpad.get_current_status() == ExecutionStatus.IN_PROGRESS

        scratchpad.update_status(ExecutionStatus.COMPLETED)
        assert scratchpad.get_current_status() == ExecutionStatus.COMPLETED

    def test_status_persisted_to_file(self, tmp_path):
        """Test that status updates are persisted to file."""
        scratchpad_file = tmp_path / "scratchpad.md"
        scratchpad = Scratchpad(str(scratchpad_file))

        scratchpad.update_status(ExecutionStatus.IN_PROGRESS)

        content = scratchpad_file.read_text()
        assert "IN_PROGRESS" in content or "In Progress" in content


class TestScratchpadTerminationSignal:
    """Test Scratchpad termination signals - Task 3.5."""

    def test_append_termination_signal_goal_achieved(self, tmp_path):
        """Test appending GOAL_ACHIEVED termination signal."""
        scratchpad_file = tmp_path / "scratchpad.md"
        scratchpad = Scratchpad(str(scratchpad_file))

        scratchpad.append_signal("GOAL_ACHIEVED", "All success criteria met")

        content = scratchpad_file.read_text()
        assert "GOAL_ACHIEVED" in content
        assert "All success criteria met" in content

    def test_append_termination_signal_budget_exceeded(self, tmp_path):
        """Test appending BUDGET_EXCEEDED termination signal."""
        scratchpad_file = tmp_path / "scratchpad.md"
        scratchpad = Scratchpad(str(scratchpad_file))

        scratchpad.append_signal("BUDGET_EXCEEDED", "Token budget limit reached")

        content = scratchpad_file.read_text()
        assert "BUDGET_EXCEEDED" in content
        assert "Token budget limit reached" in content


class TestScratchpadEntry:
    """Test ScratchpadEntry dataclass."""

    def test_scratchpad_entry_creation(self):
        """Test creating a ScratchpadEntry."""
        entry = ScratchpadEntry(
            iteration=1,
            timestamp=datetime.now(),
            goal="Test goal",
            action="Test action",
            result="Test result",
            status=ExecutionStatus.COMPLETED
        )

        assert entry.iteration == 1
        assert entry.goal == "Test goal"
        assert entry.action == "Test action"
        assert entry.result == "Test result"
        assert entry.status == ExecutionStatus.COMPLETED


class TestExecutionStatus:
    """Test ExecutionStatus enum."""

    def test_execution_status_values(self):
        """Test ExecutionStatus has required states."""
        assert ExecutionStatus.PENDING
        assert ExecutionStatus.IN_PROGRESS
        assert ExecutionStatus.COMPLETED
        assert ExecutionStatus.FAILED
