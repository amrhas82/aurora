"""
Tests for aurora.commands.view module.

Ported from OpenSpec test/core/view.test.ts
"""

import pytest
from pathlib import Path
import tempfile
import shutil
import re

from aurora_planning.commands.view import ViewCommand


def strip_ansi(text: str) -> str:
    """Remove ANSI color codes from text."""
    ansi_escape = re.compile(r'\x1b\[[0-9;]*m')
    return ansi_escape.sub('', text)


class TestViewCommand:
    """Test ViewCommand class."""

    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for testing."""
        temp = Path(tempfile.mkdtemp(prefix="openspec-view-test-"))
        yield temp
        # Cleanup
        if temp.exists():
            shutil.rmtree(temp, ignore_errors=True)

    @pytest.fixture
    def view_command(self):
        """Create ViewCommand instance."""
        return ViewCommand()

    def test_shows_changes_with_no_tasks_in_draft_section(self, view_command, temp_dir, capsys):
        """Should show changes with no tasks in Draft section, not Completed."""
        changes_dir = temp_dir / ".aurora/plans" / "changes"
        changes_dir.mkdir(parents=True)

        # Empty change (no tasks.md) - should show in Draft
        (changes_dir / "empty-change").mkdir(parents=True)

        # Change with tasks.md but no tasks - should show in Draft
        (changes_dir / "no-tasks-change").mkdir(parents=True)
        (changes_dir / "no-tasks-change" / "tasks.md").write_text(
            "# Tasks\n\nNo tasks yet."
        )

        # Change with all tasks complete - should show in Completed
        (changes_dir / "completed-change").mkdir(parents=True)
        (changes_dir / "completed-change" / "tasks.md").write_text(
            "- [x] Done task\n"
        )

        view_command.execute(str(temp_dir))

        captured = capsys.readouterr()
        output = strip_ansi(captured.out)

        # Draft section should contain empty and no-tasks changes
        assert "Draft Changes" in output
        assert "empty-change" in output
        assert "no-tasks-change" in output

        # Completed section should only contain changes with all tasks done
        assert "Completed Changes" in output
        assert "completed-change" in output

        # Verify empty-change and no-tasks-change are in Draft section (marked with ○)
        draft_lines = [line for line in output.split('\n') if '○' in line]
        draft_names = [line.strip().replace('○ ', '').strip() for line in draft_lines]
        assert "empty-change" in draft_names
        assert "no-tasks-change" in draft_names

        # Verify completed-change is in Completed section (marked with ✓)
        completed_lines = [line for line in output.split('\n') if '✓' in line]
        completed_names = [line.strip().replace('✓ ', '').strip() for line in completed_lines]
        assert "completed-change" in completed_names
        assert "empty-change" not in completed_names
        assert "no-tasks-change" not in completed_names

    def test_sorts_active_changes_by_completion_percentage_ascending(
        self, view_command, temp_dir, capsys
    ):
        """Should sort active changes by completion percentage ascending with deterministic tie-breakers."""
        changes_dir = temp_dir / ".aurora/plans" / "changes"
        changes_dir.mkdir(parents=True)

        # gamma-change: 2/3 = 66.67%
        (changes_dir / "gamma-change").mkdir(parents=True)
        (changes_dir / "gamma-change" / "tasks.md").write_text(
            "- [x] Done\n- [x] Also done\n- [ ] Not done\n"
        )

        # beta-change: 1/2 = 50%
        (changes_dir / "beta-change").mkdir(parents=True)
        (changes_dir / "beta-change" / "tasks.md").write_text(
            "- [x] Task 1\n- [ ] Task 2\n"
        )

        # delta-change: 1/2 = 50% (same as beta, should come after alphabetically)
        (changes_dir / "delta-change").mkdir(parents=True)
        (changes_dir / "delta-change" / "tasks.md").write_text(
            "- [x] Task 1\n- [ ] Task 2\n"
        )

        # alpha-change: 0/2 = 0%
        (changes_dir / "alpha-change").mkdir(parents=True)
        (changes_dir / "alpha-change" / "tasks.md").write_text(
            "- [ ] Task 1\n- [ ] Task 2\n"
        )

        view_command.execute(str(temp_dir))

        captured = capsys.readouterr()
        output = strip_ansi(captured.out)

        # Get active changes lines (marked with ◉)
        active_lines = [line for line in output.split('\n') if '◉' in line]

        # Extract change names from active lines
        active_order = []
        for line in active_lines:
            # Split on bullet and extract name before progress bar
            after_bullet = line.split('◉')[1] if '◉' in line else ''
            # Extract the name (before the progress bar [)
            name = after_bullet.split('[')[0].strip() if '[' in after_bullet else ''
            if name:
                active_order.append(name)

        # Expected order: 0% (alpha), 50% (beta, delta alphabetically), 66.67% (gamma)
        assert active_order == [
            "alpha-change",
            "beta-change",
            "delta-change",
            "gamma-change"
        ]
