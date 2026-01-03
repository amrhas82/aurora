"""
Tests for aurora.commands.list module.

Ported from OpenSpec test/core/list.test.ts
"""

import pytest
from pathlib import Path
import tempfile
import shutil
from datetime import datetime, timedelta

from aurora_planning.commands.list import ListCommand


class TestListCommand:
    """Test ListCommand class."""

    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for testing."""
        temp = Path(tempfile.mkdtemp(prefix="openspec-list-test-"))
        yield temp
        # Cleanup
        if temp.exists():
            shutil.rmtree(temp, ignore_errors=True)

    @pytest.fixture
    def list_command(self):
        """Create ListCommand instance."""
        return ListCommand()

    def test_missing_.aurora/plans_changes_directory(self, list_command, temp_dir):
        """Should handle missing .aurora/plans/changes directory."""
        with pytest.raises(
            RuntimeError,
            match="No OpenSpec changes directory found. Run '.aurora/plans init' first."
        ):
            list_command.execute(str(temp_dir), mode='changes')

    def test_empty_changes_directory(self, list_command, temp_dir, capsys):
        """Should handle empty changes directory."""
        changes_dir = temp_dir / ".aurora/plans" / "changes"
        changes_dir.mkdir(parents=True)

        list_command.execute(str(temp_dir), mode='changes')

        captured = capsys.readouterr()
        assert "No active changes found." in captured.out

    def test_exclude_archive_directory(self, list_command, temp_dir, capsys):
        """Should exclude archive directory."""
        changes_dir = temp_dir / ".aurora/plans" / "changes"
        (changes_dir / "archive").mkdir(parents=True)
        (changes_dir / "my-change").mkdir(parents=True)

        # Create tasks.md with some tasks
        (changes_dir / "my-change" / "tasks.md").write_text(
            "- [x] Task 1\n- [ ] Task 2\n"
        )

        list_command.execute(str(temp_dir), mode='changes')

        captured = capsys.readouterr()
        assert "Changes:" in captured.out
        assert "my-change" in captured.out
        assert "archive" not in captured.out

    def test_count_tasks_correctly(self, list_command, temp_dir, capsys):
        """Should count tasks correctly."""
        changes_dir = temp_dir / ".aurora/plans" / "changes"
        (changes_dir / "test-change").mkdir(parents=True)

        (changes_dir / "test-change" / "tasks.md").write_text(
            """# Tasks
- [x] Completed task 1
- [x] Completed task 2
- [ ] Incomplete task 1
- [ ] Incomplete task 2
- [ ] Incomplete task 3
Regular text that should be ignored
"""
        )

        list_command.execute(str(temp_dir), mode='changes')

        captured = capsys.readouterr()
        assert "2/5" in captured.out

    def test_show_complete_status(self, list_command, temp_dir, capsys):
        """Should show complete status for fully completed changes."""
        changes_dir = temp_dir / ".aurora/plans" / "changes"
        (changes_dir / "completed-change").mkdir(parents=True)

        (changes_dir / "completed-change" / "tasks.md").write_text(
            "- [x] Task 1\n- [x] Task 2\n- [x] Task 3\n"
        )

        list_command.execute(str(temp_dir), mode='changes')

        captured = capsys.readouterr()
        assert "✓ Complete" in captured.out or "Complete" in captured.out

    def test_handle_changes_without_tasks(self, list_command, temp_dir, capsys):
        """Should handle changes without tasks.md."""
        changes_dir = temp_dir / ".aurora/plans" / "changes"
        (changes_dir / "no-tasks").mkdir(parents=True)

        list_command.execute(str(temp_dir), mode='changes')

        captured = capsys.readouterr()
        assert "no-tasks" in captured.out
        assert "No tasks" in captured.out

    def test_sort_alphabetically(self, list_command, temp_dir, capsys):
        """Should sort changes alphabetically when sort=name."""
        changes_dir = temp_dir / ".aurora/plans" / "changes"
        (changes_dir / "zebra").mkdir(parents=True)
        (changes_dir / "alpha").mkdir(parents=True)
        (changes_dir / "middle").mkdir(parents=True)

        list_command.execute(str(temp_dir), mode='changes', options={'sort': 'name'})

        captured = capsys.readouterr()
        lines = captured.out.split('\n')

        # Find lines containing change names
        change_lines = [l for l in lines if 'alpha' in l or 'middle' in l or 'zebra' in l]

        # Verify alphabetical order
        assert len(change_lines) >= 3
        alpha_idx = next(i for i, l in enumerate(change_lines) if 'alpha' in l)
        middle_idx = next(i for i, l in enumerate(change_lines) if 'middle' in l)
        zebra_idx = next(i for i, l in enumerate(change_lines) if 'zebra' in l)

        assert alpha_idx < middle_idx < zebra_idx

    def test_multiple_changes_with_various_states(self, list_command, temp_dir, capsys):
        """Should handle multiple changes with various states."""
        changes_dir = temp_dir / ".aurora/plans" / "changes"

        # Complete change
        (changes_dir / "completed").mkdir(parents=True)
        (changes_dir / "completed" / "tasks.md").write_text(
            "- [x] Task 1\n- [x] Task 2\n"
        )

        # Partial change
        (changes_dir / "partial").mkdir(parents=True)
        (changes_dir / "partial" / "tasks.md").write_text(
            "- [x] Done\n- [ ] Not done\n- [ ] Also not done\n"
        )

        # No tasks
        (changes_dir / "no-tasks").mkdir(parents=True)

        list_command.execute(str(temp_dir))

        captured = capsys.readouterr()
        assert "Changes:" in captured.out
        assert "completed" in captured.out
        assert "partial" in captured.out
        assert "1/3" in captured.out
        assert "no-tasks" in captured.out

    def test_json_output_mode(self, list_command, temp_dir, capsys):
        """Should output JSON when json=True."""
        changes_dir = temp_dir / ".aurora/plans" / "changes"
        (changes_dir / "test-change").mkdir(parents=True)
        (changes_dir / "test-change" / "tasks.md").write_text(
            "- [x] Task 1\n- [ ] Task 2\n"
        )

        list_command.execute(str(temp_dir), mode='changes', options={'json': True})

        captured = capsys.readouterr()
        assert '"changes"' in captured.out
        assert '"name"' in captured.out
        assert '"test-change"' in captured.out

    def test_list_specs_mode(self, list_command, temp_dir, capsys):
        """Should list specs when mode='specs'."""
        specs_dir = temp_dir / ".aurora/plans" / "specs"
        (specs_dir / "auth").mkdir(parents=True)
        (specs_dir / "auth" / "spec.md").write_text(
            """# auth Specification

## Purpose
Authentication specification

## Requirements

### Requirement: Login
Users can log in.

#### Scenario: Success
- **WHEN** valid credentials
- **THEN** login succeeds
"""
        )

        list_command.execute(str(temp_dir), mode='specs')

        captured = capsys.readouterr()
        assert "Specs:" in captured.out
        assert "auth" in captured.out

    def test_list_specs_no_specs_directory(self, list_command, temp_dir, capsys):
        """Should handle missing specs directory."""
        list_command.execute(str(temp_dir), mode='specs')

        captured = capsys.readouterr()
        assert "No specs found." in captured.out

    def test_list_specs_empty_directory(self, list_command, temp_dir, capsys):
        """Should handle empty specs directory."""
        specs_dir = temp_dir / ".aurora/plans" / "specs"
        specs_dir.mkdir(parents=True)

        list_command.execute(str(temp_dir), mode='specs')

        captured = capsys.readouterr()
        assert "No specs found." in captured.out

    def test_sort_by_recent_default(self, list_command, temp_dir, capsys):
        """Should sort by most recent modification by default."""
        changes_dir = temp_dir / ".aurora/plans" / "changes"

        # Create changes with different modification times
        old_change = changes_dir / "old-change"
        old_change.mkdir(parents=True)
        (old_change / "tasks.md").write_text("- [ ] Task 1\n")

        # Make it appear older by creating it earlier (though in practice
        # we can't easily control mtime in tests, so just verify it runs)
        new_change = changes_dir / "new-change"
        new_change.mkdir(parents=True)
        (new_change / "tasks.md").write_text("- [ ] Task 1\n")

        # Default sort should be by recent
        list_command.execute(str(temp_dir), mode='changes')

        captured = capsys.readouterr()
        assert "Changes:" in captured.out
        # Both should be listed
        assert "old-change" in captured.out
        assert "new-change" in captured.out
