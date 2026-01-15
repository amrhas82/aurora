"""Tests for task progress utilities."""

from aurora_planning.utils.task_progress import (
    TaskProgress,
    count_tasks_from_content,
    format_task_status,
    get_task_progress_for_plan,
)


class TestCountTasksFromContent:
    """Tests for counting tasks from markdown content."""

    def test_count_tasks_with_checkboxes(self):
        """Test counting tasks with checkbox syntax."""
        content = """# Tasks

- [ ] Task 1
- [x] Task 2 (completed)
- [ ] Task 3
- [x] Task 4 (completed)
"""
        progress = count_tasks_from_content(content)

        assert progress.total == 4
        assert progress.completed == 2

    def test_count_tasks_with_asterisk_bullets(self):
        """Test counting tasks with asterisk bullet points."""
        content = """# Tasks

* [ ] Task A
* [x] Task B
* [ ] Task C
"""
        progress = count_tasks_from_content(content)

        assert progress.total == 3
        assert progress.completed == 1

    def test_count_tasks_empty_content(self):
        """Test counting tasks in empty content."""
        content = ""
        progress = count_tasks_from_content(content)

        assert progress.total == 0
        assert progress.completed == 0

    def test_count_tasks_no_tasks(self):
        """Test counting tasks when no tasks present."""
        content = """# Notes

This is just a document with no tasks.

- Regular bullet point
- Another point
"""
        progress = count_tasks_from_content(content)

        assert progress.total == 0
        assert progress.completed == 0

    def test_count_tasks_case_insensitive(self):
        """Test that X is case insensitive for completed tasks."""
        content = """- [X] Uppercase X
- [x] Lowercase x
- [ ] Not done
"""
        progress = count_tasks_from_content(content)

        assert progress.total == 3
        assert progress.completed == 2


class TestGetTaskProgressForPlan:
    """Tests for getting task progress from plan directory."""

    def test_get_progress_from_tasks_file(self, tmp_path):
        """Test getting progress from tasks.md file."""
        plan_dir = tmp_path / "plans" / "test-plan"
        plan_dir.mkdir(parents=True)
        tasks_file = plan_dir / "tasks.md"
        tasks_file.write_text(
            """# Tasks

- [x] Setup
- [x] Implement
- [ ] Test
- [ ] Deploy
"""
        )

        progress = get_task_progress_for_plan(str(tmp_path / "plans"), "test-plan")

        assert progress.total == 4
        assert progress.completed == 2

    def test_get_progress_missing_tasks_file(self, tmp_path):
        """Test getting progress when tasks.md doesn't exist."""
        plan_dir = tmp_path / "plans" / "no-tasks"
        plan_dir.mkdir(parents=True)
        # No tasks.md created

        progress = get_task_progress_for_plan(str(tmp_path / "plans"), "no-tasks")

        assert progress.total == 0
        assert progress.completed == 0


class TestFormatTaskStatus:
    """Tests for formatting task status strings."""

    def test_format_no_tasks(self):
        """Test formatting when no tasks."""
        progress = TaskProgress(total=0, completed=0)
        status = format_task_status(progress)
        assert status == "No tasks"

    def test_format_complete(self):
        """Test formatting when all tasks complete."""
        progress = TaskProgress(total=5, completed=5)
        status = format_task_status(progress)
        assert "Complete" in status

    def test_format_in_progress(self):
        """Test formatting when tasks in progress."""
        progress = TaskProgress(total=10, completed=3)
        status = format_task_status(progress)
        assert "3/10" in status
        assert "task" in status.lower()
