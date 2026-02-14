"""Output persistence for spawn runs.

Manages .aurora/spawn/runs/<timestamp>/ directories with per-task results
and run summaries. Supports re-run detection via SHA-256 hash of tasks.md content.
"""

import hashlib
import json
import logging
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)


class SpawnRunStore:
    """Manages spawn run output directories under .aurora/spawn/runs/."""

    def __init__(self, aurora_dir: Path | None = None):
        if aurora_dir is None:
            aurora_dir = Path(".aurora")
        self.runs_dir = aurora_dir / "spawn" / "runs"

    def create_run(self, tasks_md_content: str) -> Path:
        """Create a new run directory and write the tasks.md snapshot.

        Args:
            tasks_md_content: The tasks.md content for this run

        Returns:
            Path to the created run directory

        """
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
        run_dir = self.runs_dir / timestamp
        run_dir.mkdir(parents=True, exist_ok=True)
        (run_dir / "results").mkdir(exist_ok=True)

        (run_dir / "tasks.md").write_text(tasks_md_content)

        # Write metadata with content hash for re-run detection
        meta = {
            "created": timestamp,
            "tasks_hash": self._hash_content(tasks_md_content),
            "status": "running",
        }
        (run_dir / "meta.json").write_text(json.dumps(meta, indent=2))

        return run_dir

    def save_task_result(
        self,
        run_dir: Path,
        task_id: str,
        success: bool,
        output: str | None = None,
        error: str | None = None,
    ) -> None:
        """Persist a single task's result.

        Args:
            run_dir: Path to the run directory
            task_id: Task identifier
            success: Whether the task succeeded
            output: Task output text (if any)
            error: Error message (if any)

        """
        result = {
            "task_id": task_id,
            "success": success,
            "output": output or "",
            "error": error or "",
        }
        result_file = run_dir / "results" / f"task-{task_id}.json"
        result_file.write_text(json.dumps(result, indent=2))

    def finalize_run(
        self,
        run_dir: Path,
        total: int,
        completed: int,
        failed: int,
    ) -> None:
        """Mark a run as complete with summary stats.

        Args:
            run_dir: Path to the run directory
            total: Total number of tasks
            completed: Number of completed tasks
            failed: Number of failed tasks

        """
        summary = {
            "total": total,
            "completed": completed,
            "failed": failed,
            "status": "completed",
            "finished": datetime.now(timezone.utc).isoformat(),
        }
        (run_dir / "summary.json").write_text(json.dumps(summary, indent=2))

        # Update meta status
        meta_path = run_dir / "meta.json"
        if meta_path.exists():
            meta = json.loads(meta_path.read_text())
            meta["status"] = "completed"
            meta_path.write_text(json.dumps(meta, indent=2))

    def load_previous_results(self, tasks_md_content: str) -> dict[str, str] | None:
        """Find the latest completed run matching the tasks.md content hash.

        Returns completed task outputs keyed by task ID, or None if no match.

        Args:
            tasks_md_content: Current tasks.md content to match against

        Returns:
            Dict mapping task_id -> output for completed tasks, or None

        """
        if not self.runs_dir.exists():
            return None

        target_hash = self._hash_content(tasks_md_content)

        # Scan runs in reverse chronological order (newest first)
        run_dirs = sorted(self.runs_dir.iterdir(), reverse=True)
        for run_dir in run_dirs:
            if not run_dir.is_dir():
                continue
            meta_path = run_dir / "meta.json"
            if not meta_path.exists():
                continue

            try:
                meta = json.loads(meta_path.read_text())
            except (json.JSONDecodeError, OSError):
                continue

            if meta.get("tasks_hash") != target_hash:
                continue

            # Found matching run — load completed task outputs
            results_dir = run_dir / "results"
            if not results_dir.exists():
                continue

            outputs: dict[str, str] = {}
            for result_file in results_dir.glob("task-*.json"):
                try:
                    data = json.loads(result_file.read_text())
                    if data.get("success"):
                        outputs[data["task_id"]] = data.get("output", "")
                except (json.JSONDecodeError, OSError):
                    continue

            return outputs if outputs else None

        return None

    @staticmethod
    def _hash_content(content: str) -> str:
        """SHA-256 hash of content for matching."""
        return hashlib.sha256(content.encode()).hexdigest()
