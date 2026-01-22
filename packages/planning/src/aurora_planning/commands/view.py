"""View command for Aurora planning system.

Ported from OpenSpec src/core/view.ts
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from aurora_planning.parsers.markdown import MarkdownParser


@dataclass
class ChangeInfo:
    """Information about a change with task progress."""

    name: str
    progress: dict[str, int]  # {'total': int, 'completed': int}


@dataclass
class SpecInfo:
    """Information about a specification."""

    name: str
    requirement_count: int


class ViewCommand:
    """Command to display OpenSpec dashboard."""

    def execute(self, target_path: str = ".") -> None:
        """Execute the view command.

        Args:
            target_path: Target directory path (default: current directory)

        """
        target = Path(target_path)
        openspec_dir = target / ".aurora/plans"

        if not openspec_dir.exists():
            print("No openspec directory found")
            return

        print("\nOpenSpec Dashboard\n")
        print("=" * 60)

        # Get changes and specs data
        changes_data = self._get_changes_data(openspec_dir)
        specs_data = self._get_specs_data(openspec_dir)

        # Display summary metrics
        self._display_summary(changes_data, specs_data)

        # Display draft changes
        if changes_data["draft"]:
            print("\nDraft Changes")
            print("-" * 60)
            for change in changes_data["draft"]:
                print(f"  ○ {change['name']}")

        # Display active changes
        if changes_data["active"]:
            print("\nActive Changes")
            print("-" * 60)
            for change in changes_data["active"]:
                progress_bar = self._create_progress_bar(
                    change["progress"]["completed"],
                    change["progress"]["total"],
                )
                percentage = (
                    round((change["progress"]["completed"] / change["progress"]["total"]) * 100)
                    if change["progress"]["total"] > 0
                    else 0
                )
                name_padded = change["name"].ljust(30)
                print(f"  ◉ {name_padded} {progress_bar} {percentage}%")

        # Display completed changes
        if changes_data["completed"]:
            print("\nCompleted Changes")
            print("-" * 60)
            for change in changes_data["completed"]:
                print(f"  ✓ {change['name']}")

        # Display specifications
        if specs_data:
            print("\nSpecifications")
            print("-" * 60)

            # Sort specs by requirement count (descending)
            specs_data_sorted = sorted(
                specs_data,
                key=lambda s: s["requirement_count"],
                reverse=True,
            )

            for spec in specs_data_sorted:
                req_label = "requirement" if spec["requirement_count"] == 1 else "requirements"
                name_padded = spec["name"].ljust(30)
                print(f"  ▪ {name_padded} {spec['requirement_count']} {req_label}")

        print("\n" + "=" * 60)
        print("\nUse 'openspec list --changes' or 'openspec list --specs' for detailed views")

    def _get_changes_data(self, openspec_dir: Path) -> dict[str, list[dict[str, Any]]]:
        """Get changes data categorized by status."""
        changes_dir = openspec_dir / "changes"

        if not changes_dir.exists():
            return {"draft": [], "active": [], "completed": []}

        draft: list[dict[str, Any]] = []
        active: list[dict[str, Any]] = []
        completed: list[dict[str, Any]] = []

        try:
            entries = list(changes_dir.iterdir())
        except OSError:
            return {"draft": [], "active": [], "completed": []}

        for entry in entries:
            if entry.is_dir() and entry.name != "archive":
                progress = self._get_task_progress(changes_dir, entry.name)

                if progress["total"] == 0:
                    # No tasks defined yet - still in planning/draft phase
                    draft.append({"name": entry.name})
                elif progress["completed"] == progress["total"]:
                    # All tasks complete
                    completed.append({"name": entry.name})
                else:
                    # Has tasks but not all complete
                    active.append({"name": entry.name, "progress": progress})

        # Sort all categories by name for deterministic ordering
        draft.sort(key=lambda c: c["name"])

        # Sort active changes by completion percentage (ascending) and then by name
        def sort_key(change: dict[str, Any]) -> tuple[float, str]:
            progress = change["progress"]
            percentage = progress["completed"] / progress["total"] if progress["total"] > 0 else 0
            return (percentage, change["name"])

        active.sort(key=sort_key)
        completed.sort(key=lambda c: c["name"])

        return {"draft": draft, "active": active, "completed": completed}

    def _get_specs_data(self, openspec_dir: Path) -> list[dict[str, Any]]:
        """Get specifications data."""
        specs_dir = openspec_dir / "specs"

        if not specs_dir.exists():
            return []

        specs: list[dict[str, Any]] = []

        try:
            entries = list(specs_dir.iterdir())
        except OSError:
            return []

        for entry in entries:
            if entry.is_dir():
                spec_file = entry / "spec.md"

                if spec_file.exists():
                    try:
                        content = spec_file.read_text()
                        parser = MarkdownParser(content)
                        spec = parser.parse_capability(entry.name)
                        requirement_count = len(spec.requirements)
                        specs.append({"name": entry.name, "requirement_count": requirement_count})
                    except Exception:
                        # If spec cannot be parsed, include with 0 count
                        specs.append({"name": entry.name, "requirement_count": 0})

        return specs

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

    def _display_summary(
        self,
        changes_data: dict[str, list[dict[str, Any]]],
        specs_data: list[dict[str, Any]],
    ) -> None:
        """Display summary metrics."""
        _ = (
            len(changes_data["draft"])
            + len(changes_data["active"])
            + len(changes_data["completed"])
        )
        total_specs = len(specs_data)
        total_requirements = sum(spec["requirement_count"] for spec in specs_data)

        # Calculate total task progress
        total_tasks = 0
        completed_tasks = 0

        for change in changes_data["active"]:
            total_tasks += change["progress"]["total"]
            completed_tasks += change["progress"]["completed"]

        print("Summary:")
        print(f"  ● Specifications: {total_specs} specs, {total_requirements} requirements")

        if changes_data["draft"]:
            print(f"  ● Draft Changes: {len(changes_data['draft'])}")

        print(f"  ● Active Changes: {len(changes_data['active'])} in progress")
        print(f"  ● Completed Changes: {len(changes_data['completed'])}")

        if total_tasks > 0:
            overall_progress = round((completed_tasks / total_tasks) * 100)
            print(
                f"  ● Task Progress: {completed_tasks}/{total_tasks} ({overall_progress}% complete)",
            )

    def _create_progress_bar(self, completed: int, total: int, width: int = 20) -> str:
        """Create a text-based progress bar."""
        if total == 0:
            return "[" + "─" * width + "]"

        percentage = completed / total
        filled = round(percentage * width)
        empty = width - filled

        filled_bar = "█" * filled
        empty_bar = "░" * empty

        return f"[{filled_bar}{empty_bar}]"
