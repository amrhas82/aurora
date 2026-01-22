"""List command for Aurora planning system.

Ported from OpenSpec src/core/list.ts
"""

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Literal


@dataclass
class ChangeInfo:
    """Information about a change/plan."""

    name: str
    completed_tasks: int
    total_tasks: int
    last_modified: datetime


@dataclass
class SpecInfo:
    """Information about a specification."""

    id: str
    requirement_count: int


class ListCommand:
    """Command to list changes or specs."""

    def execute(
        self,
        target_path: str = ".",
        mode: Literal["changes", "specs"] = "changes",
        options: dict[str, Any] | None = None,
    ) -> None:
        """Execute the list command.

        Args:
            target_path: Target directory path (default: current directory)
            mode: List mode - 'changes' or 'specs' (default: 'changes')
            options: Optional dict with 'sort' ('recent' or 'name') and 'json' (bool)

        """
        if options is None:
            options = {}

        sort = options.get("sort", "recent")
        json_output = options.get("json", False)

        target = Path(target_path)

        if mode == "changes":
            self._list_changes(target, sort, json_output)
        else:
            self._list_specs(target)

    def _list_changes(self, target: Path, sort: str, json_output: bool) -> None:
        """List active changes."""
        changes_dir = target / ".aurora/plans" / "changes"

        # Check if changes directory exists
        if not changes_dir.exists():
            raise RuntimeError("No Aurora plans directory found. Run 'aur init' first.")

        # Get all directories in changes (excluding archive)
        try:
            entries = list(changes_dir.iterdir())
        except OSError as err:
            raise RuntimeError("No Aurora plans directory found. Run 'aur init' first.") from err

        change_dirs = sorted([e.name for e in entries if e.is_dir() and e.name != "archive"])

        if len(change_dirs) == 0:
            if json_output:
                print(json.dumps({"changes": []}))
            else:
                print("No active changes found.")
            return

        # Collect information about each change
        changes: list[ChangeInfo] = []

        for change_dir in change_dirs:
            progress = self._get_task_progress(changes_dir, change_dir)
            change_path = changes_dir / change_dir
            last_modified = self._get_last_modified(change_path)
            changes.append(
                ChangeInfo(
                    name=change_dir,
                    completed_tasks=progress["completed"],
                    total_tasks=progress["total"],
                    last_modified=last_modified,
                ),
            )

        # Sort by preference (default: recent first)
        if sort == "recent":
            changes.sort(key=lambda c: c.last_modified, reverse=True)
        else:
            changes.sort(key=lambda c: c.name)

        # JSON output for programmatic use
        if json_output:
            json_output_data = []
            for c in changes:
                status = (
                    "no-tasks"
                    if c.total_tasks == 0
                    else ("complete" if c.completed_tasks == c.total_tasks else "in-progress")
                )
                json_output_data.append(
                    {
                        "name": c.name,
                        "completedTasks": c.completed_tasks,
                        "totalTasks": c.total_tasks,
                        "lastModified": c.last_modified.isoformat(),
                        "status": status,
                    },
                )
            print(json.dumps({"changes": json_output_data}, indent=2))
            return

        # Display results
        print("Changes:")
        padding = "  "
        name_width = max(len(c.name) for c in changes)

        for change in changes:
            padded_name = change.name.ljust(name_width)
            status = self._format_task_status(change.total_tasks, change.completed_tasks)
            time_ago = self._format_relative_time(change.last_modified)
            print(f"{padding}{padded_name}     {status.ljust(12)}  {time_ago}")

    def _list_specs(self, target: Path) -> None:
        """List specifications."""
        specs_dir = target / ".aurora/plans" / "specs"

        if not specs_dir.exists():
            print("No specs found.")
            return

        try:
            entries = list(specs_dir.iterdir())
        except OSError:
            print("No specs found.")
            return

        spec_dirs = sorted([e.name for e in entries if e.is_dir()])

        if len(spec_dirs) == 0:
            print("No specs found.")
            return

        specs: list[SpecInfo] = []
        for spec_id in spec_dirs:
            spec_path = specs_dir / spec_id / "spec.md"
            try:
                content = spec_path.read_text()
                # Count requirements (lines starting with ### Requirement:)
                req_count = sum(
                    1 for line in content.split("\n") if line.strip().startswith("### Requirement:")
                )
                specs.append(SpecInfo(id=spec_id, requirement_count=req_count))
            except (FileNotFoundError, OSError):
                # If spec cannot be read, include with 0 count
                specs.append(SpecInfo(id=spec_id, requirement_count=0))

        specs.sort(key=lambda s: s.id)

        print("Specs:")
        padding = "  "
        name_width = max(len(s.id) for s in specs)

        for spec in specs:
            padded = spec.id.ljust(name_width)
            print(f"{padding}{padded}     requirements {spec.requirement_count}")

    def _get_task_progress(self, changes_dir: Path, change_name: str) -> dict[str, int]:
        """Get task progress for a change."""
        tasks_path = changes_dir / change_name / "tasks.md"

        if not tasks_path.exists():
            return {"total": 0, "completed": 0}

        try:
            content = tasks_path.read_text()
        except OSError:
            return {"total": 0, "completed": 0}

        lines = content.split("\n")
        total = 0
        completed = 0

        for line in lines:
            line = line.strip()
            if line.startswith("- ["):
                total += 1
                if line.startswith("- [x]") or line.startswith("- [X]"):
                    completed += 1

        return {"total": total, "completed": completed}

    def _format_task_status(self, total: int, completed: int) -> str:
        """Format task status string."""
        if total == 0:
            return "No tasks"

        if completed == total:
            return "✓ Complete"

        percent = int((completed / total) * 100) if total > 0 else 0
        return f"{completed}/{total} ({percent}%)"

    def _get_last_modified(self, dir_path: Path) -> datetime:
        """Get the most recent modification time of any file in a directory (recursive).
        Falls back to the directory's own mtime if no files are found.
        """
        latest: datetime | None = None

        def walk(current_dir: Path) -> None:
            nonlocal latest
            try:
                for entry in current_dir.iterdir():
                    if entry.is_dir():
                        walk(entry)
                    else:
                        mtime = datetime.fromtimestamp(entry.stat().st_mtime)
                        if latest is None or mtime > latest:
                            latest = mtime
            except (OSError, PermissionError):
                pass

        walk(dir_path)

        # If no files found, use the directory's own modification time
        if latest is None:
            try:
                latest = datetime.fromtimestamp(dir_path.stat().st_mtime)
            except OSError:
                latest = datetime.now()

        return latest

    def _format_relative_time(self, date: datetime) -> str:
        """Format a date as relative time (e.g., '2 hours ago', '3 days ago')."""
        now = datetime.now()
        diff = now - date
        diff_seconds = int(diff.total_seconds())

        if diff_seconds < 0:
            return "just now"

        diff_minutes = diff_seconds // 60
        diff_hours = diff_minutes // 60
        diff_days = diff_hours // 24

        if diff_days > 30:
            return date.strftime("%Y-%m-%d")
        if diff_days > 0:
            return f"{diff_days}d ago"
        if diff_hours > 0:
            return f"{diff_hours}h ago"
        if diff_minutes > 0:
            return f"{diff_minutes}m ago"
        return "just now"
