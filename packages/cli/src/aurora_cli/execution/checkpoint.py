"""Checkpoint manager for resumable execution."""

from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from aurora_core.paths import get_aurora_dir


logger = logging.getLogger(__name__)


@dataclass
class TaskState:
    """State of a single task in execution."""

    id: str
    status: str  # pending, in_progress, completed, failed, skipped
    result: str | None = None
    error: str | None = None
    started_at: str | None = None
    completed_at: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class CheckpointState:
    """Complete state of an execution for resume."""

    execution_id: str
    plan_id: str | None
    started_at: str
    tasks: list[TaskState]
    last_checkpoint: str
    interrupted: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)


class CheckpointManager:
    """Manage execution checkpoints for resume functionality."""

    def __init__(self, execution_id: str, plan_id: str | None = None):
        """Initialize checkpoint manager.

        Args:
            execution_id: Unique execution identifier
            plan_id: Optional plan identifier
        """
        self.execution_id = execution_id
        self.plan_id = plan_id
        self.checkpoint_dir = self._get_checkpoint_dir()
        self.checkpoint_path = self.checkpoint_dir / f"{execution_id}.json"

        # Create checkpoint directory if needed
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)

    def _get_checkpoint_dir(self) -> Path:
        """Get checkpoint directory path.

        Returns:
            Path to .aurora/checkpoints/
        """
        aurora_dir = get_aurora_dir()
        return aurora_dir / "checkpoints"

    def save(self, tasks: list[TaskState]) -> None:
        """Save current state to checkpoint file.

        Args:
            tasks: List of task states
        """
        try:
            state = CheckpointState(
                execution_id=self.execution_id,
                plan_id=self.plan_id,
                started_at=self._get_started_at(tasks),
                tasks=tasks,
                last_checkpoint=self._timestamp(),
                interrupted=False,
            )

            with open(self.checkpoint_path, "w") as f:
                json.dump(self._to_dict(state), f, indent=2)

            logger.debug(f"Saved checkpoint to {self.checkpoint_path}")

        except Exception as e:
            logger.warning(f"Failed to save checkpoint: {e}")

    def load(self, execution_id: str | None = None) -> CheckpointState | None:
        """Load checkpoint if exists.

        Args:
            execution_id: Execution ID to load. If None, uses self.execution_id

        Returns:
            CheckpointState if found, None otherwise
        """
        exec_id = execution_id or self.execution_id
        checkpoint_path = self.checkpoint_dir / f"{exec_id}.json"

        if not checkpoint_path.exists():
            return None

        try:
            with open(checkpoint_path) as f:
                data = json.load(f)

            return self._from_dict(data)

        except Exception as e:
            logger.warning(f"Failed to load checkpoint from {checkpoint_path}: {e}")
            return None

    def mark_interrupted(self) -> None:
        """Mark execution as interrupted (Ctrl+C handler)."""
        # Load current state
        state = self.load()
        if state:
            state.interrupted = True
            state.last_checkpoint = self._timestamp()

            with open(self.checkpoint_path, "w") as f:
                json.dump(self._to_dict(state), f, indent=2)

            logger.info(f"Marked execution {self.execution_id} as interrupted")

    def get_resume_point(self, tasks: list[TaskState] | None = None) -> int:
        """Return index of first non-completed task.

        Args:
            tasks: Optional task list. If None, loads from checkpoint.

        Returns:
            Index of first pending/failed task, or len(tasks) if all done
        """
        if tasks is None:
            state = self.load()
            if not state:
                return 0
            tasks = state.tasks

        for i, task in enumerate(tasks):
            if task.status not in ("completed", "skipped"):
                return i

        return len(tasks)

    @classmethod
    def list_resumable(cls) -> list[CheckpointState]:
        """List all checkpoints that can be resumed.

        Returns:
            List of CheckpointState objects
        """
        checkpoint_dir = cls._get_checkpoint_dir_static()
        if not checkpoint_dir.exists():
            return []

        resumable = []
        for checkpoint_file in checkpoint_dir.glob("*.json"):
            try:
                with open(checkpoint_file) as f:
                    data = json.load(f)

                state = cls._from_dict_static(data)
                # Only include if not fully completed
                if any(t.status not in ("completed", "skipped") for t in state.tasks):
                    resumable.append(state)

            except Exception as e:
                logger.warning(f"Failed to load checkpoint {checkpoint_file}: {e}")
                continue

        return sorted(resumable, key=lambda s: s.last_checkpoint, reverse=True)

    @classmethod
    def clean_old_checkpoints(cls, days: int = 7) -> int:
        """Remove checkpoint files older than specified days.

        Args:
            days: Age threshold in days

        Returns:
            Number of files removed
        """
        checkpoint_dir = cls._get_checkpoint_dir_static()
        if not checkpoint_dir.exists():
            return 0

        cutoff_time = time.time() - (days * 24 * 60 * 60)
        removed_count = 0

        for checkpoint_file in checkpoint_dir.glob("*.json"):
            try:
                if checkpoint_file.stat().st_mtime < cutoff_time:
                    checkpoint_file.unlink()
                    removed_count += 1
                    logger.debug(f"Removed old checkpoint: {checkpoint_file}")
            except Exception as e:
                logger.warning(f"Failed to remove {checkpoint_file}: {e}")

        logger.info(f"Cleaned {removed_count} old checkpoint(s)")
        return removed_count

    def _timestamp(self) -> str:
        """Get current timestamp in ISO format.

        Returns:
            ISO formatted timestamp
        """
        from datetime import datetime

        return datetime.utcnow().isoformat() + "Z"

    def _get_started_at(self, tasks: list[TaskState]) -> str:
        """Get earliest started_at timestamp from tasks.

        Args:
            tasks: List of task states

        Returns:
            ISO formatted timestamp
        """
        for task in tasks:
            if task.started_at:
                return task.started_at
        return self._timestamp()

    def _to_dict(self, state: CheckpointState) -> dict[str, Any]:
        """Convert CheckpointState to dict for JSON serialization.

        Args:
            state: CheckpointState object

        Returns:
            Dict representation
        """
        return {
            "execution_id": state.execution_id,
            "plan_id": state.plan_id,
            "started_at": state.started_at,
            "tasks": [
                {
                    "id": t.id,
                    "status": t.status,
                    "result": t.result,
                    "error": t.error,
                    "started_at": t.started_at,
                    "completed_at": t.completed_at,
                    "metadata": t.metadata,
                }
                for t in state.tasks
            ],
            "last_checkpoint": state.last_checkpoint,
            "interrupted": state.interrupted,
            "metadata": state.metadata,
        }

    def _from_dict(self, data: dict[str, Any]) -> CheckpointState:
        """Convert dict to CheckpointState.

        Args:
            data: Dict representation

        Returns:
            CheckpointState object
        """
        return CheckpointState(
            execution_id=data["execution_id"],
            plan_id=data.get("plan_id"),
            started_at=data["started_at"],
            tasks=[
                TaskState(
                    id=t["id"],
                    status=t["status"],
                    result=t.get("result"),
                    error=t.get("error"),
                    started_at=t.get("started_at"),
                    completed_at=t.get("completed_at"),
                    metadata=t.get("metadata", {}),
                )
                for t in data["tasks"]
            ],
            last_checkpoint=data["last_checkpoint"],
            interrupted=data.get("interrupted", False),
            metadata=data.get("metadata", {}),
        )

    @classmethod
    def _get_checkpoint_dir_static(cls) -> Path:
        """Static version of _get_checkpoint_dir for class methods."""
        aurora_dir = get_aurora_dir()
        return aurora_dir / "checkpoints"

    @classmethod
    def _from_dict_static(cls, data: dict[str, Any]) -> CheckpointState:
        """Static version of _from_dict for class methods."""
        return CheckpointState(
            execution_id=data["execution_id"],
            plan_id=data.get("plan_id"),
            started_at=data["started_at"],
            tasks=[
                TaskState(
                    id=t["id"],
                    status=t["status"],
                    result=t.get("result"),
                    error=t.get("error"),
                    started_at=t.get("started_at"),
                    completed_at=t.get("completed_at"),
                    metadata=t.get("metadata", {}),
                )
                for t in data["tasks"]
            ],
            last_checkpoint=data["last_checkpoint"],
            interrupted=data.get("interrupted", False),
            metadata=data.get("metadata", {}),
        )
