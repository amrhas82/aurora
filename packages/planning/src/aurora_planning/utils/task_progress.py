"""Task progress tracking utilities.

Parse and track task completion from tasks.md files.
"""

import re
from dataclasses import dataclass
from pathlib import Path

# Regex patterns for task checkboxes
TASK_PATTERN = re.compile(r"^[-*]\s+\[[\sx]\]", re.IGNORECASE)
COMPLETED_TASK_PATTERN = re.compile(r"^[-*]\s+\[x\]", re.IGNORECASE)


@dataclass
class TaskProgress:
    """Task completion progress.

    Attributes:
        total: Total number of tasks
        completed: Number of completed tasks

    """

    total: int
    completed: int

    @property
    def percent(self) -> float:
        """Get completion percentage."""
        if self.total == 0:
            return 0.0
        return (self.completed / self.total) * 100


def count_tasks_from_content(content: str) -> TaskProgress:
    """Count tasks from markdown content.

    Looks for checkbox syntax: `- [ ]` or `- [x]` (with - or * bullets).

    Args:
        content: Markdown content to parse

    Returns:
        TaskProgress with total and completed counts

    """
    lines = content.split("\n")
    total = 0
    completed = 0

    for line in lines:
        if TASK_PATTERN.match(line):
            total += 1
            if COMPLETED_TASK_PATTERN.match(line):
                completed += 1

    return TaskProgress(total=total, completed=completed)


def get_task_progress_for_plan(plans_dir: str, plan_name: str) -> TaskProgress:
    """Get task progress for a specific plan.

    Args:
        plans_dir: Path to plans directory
        plan_name: Name of the plan

    Returns:
        TaskProgress for the plan (empty if no tasks.md)

    """
    tasks_path = Path(plans_dir) / plan_name / "tasks.md"

    try:
        content = tasks_path.read_text(encoding="utf-8")
        return count_tasks_from_content(content)
    except (OSError, FileNotFoundError):
        return TaskProgress(total=0, completed=0)


def format_task_status(progress: TaskProgress) -> str:
    """Format task progress as a status string.

    Args:
        progress: TaskProgress to format

    Returns:
        Human-readable status string

    """
    if progress.total == 0:
        return "No tasks"

    if progress.completed == progress.total:
        return "✓ Complete"

    return f"{progress.completed}/{progress.total} tasks"
