"""Unit tests for CheckpointManager."""

import tempfile
import time
from pathlib import Path

import pytest

from aurora_cli.execution import CheckpointManager, CheckpointState, TaskState


@pytest.fixture
def temp_checkpoint_dir(monkeypatch, tmp_path):
    """Use temporary directory for checkpoints."""
    checkpoint_dir = tmp_path / "checkpoints"
    checkpoint_dir.mkdir()

    # Mock get_aurora_dir to return our temp dir
    def mock_get_aurora_dir():
        return tmp_path

    monkeypatch.setattr("aurora_cli.execution.checkpoint.get_aurora_dir", mock_get_aurora_dir)
    monkeypatch.setattr("aurora_core.paths.get_aurora_dir", mock_get_aurora_dir)

    return checkpoint_dir


class TestCheckpointManager:
    """Test CheckpointManager functionality."""

    def test_save_and_load_checkpoint(self, temp_checkpoint_dir):
        """Test saving and loading checkpoint."""
        execution_id = "test-exec-123"
        mgr = CheckpointManager(execution_id, plan_id="plan-001")

        # Create sample tasks
        tasks = [
            TaskState(id="task-1", status="completed", result="Success"),
            TaskState(id="task-2", status="in_progress"),
            TaskState(id="task-3", status="pending"),
        ]

        # Save checkpoint
        mgr.save(tasks)

        # Load checkpoint
        loaded = mgr.load()

        assert loaded is not None
        assert loaded.execution_id == execution_id
        assert loaded.plan_id == "plan-001"
        assert len(loaded.tasks) == 3
        assert loaded.tasks[0].id == "task-1"
        assert loaded.tasks[0].status == "completed"
        assert loaded.tasks[1].status == "in_progress"
        assert loaded.tasks[2].status == "pending"

    def test_load_nonexistent_checkpoint(self, temp_checkpoint_dir):
        """Test loading checkpoint that doesn't exist."""
        mgr = CheckpointManager("nonexistent-id")

        loaded = mgr.load()

        assert loaded is None

    def test_mark_interrupted(self, temp_checkpoint_dir):
        """Test marking execution as interrupted."""
        execution_id = "test-exec-456"
        mgr = CheckpointManager(execution_id)

        # Save initial checkpoint
        tasks = [TaskState(id="task-1", status="in_progress")]
        mgr.save(tasks)

        # Mark interrupted
        mgr.mark_interrupted()

        # Load and verify
        loaded = mgr.load()

        assert loaded is not None
        assert loaded.interrupted is True

    def test_get_resume_point_pending(self, temp_checkpoint_dir):
        """Test getting resume point with pending tasks."""
        tasks = [
            TaskState(id="task-1", status="completed"),
            TaskState(id="task-2", status="completed"),
            TaskState(id="task-3", status="pending"),
            TaskState(id="task-4", status="pending"),
        ]

        mgr = CheckpointManager("test-exec")
        resume_point = mgr.get_resume_point(tasks)

        # Should resume at index 2 (first pending task)
        assert resume_point == 2

    def test_get_resume_point_all_complete(self, temp_checkpoint_dir):
        """Test getting resume point when all tasks complete."""
        tasks = [
            TaskState(id="task-1", status="completed"),
            TaskState(id="task-2", status="completed"),
            TaskState(id="task-3", status="skipped"),
        ]

        mgr = CheckpointManager("test-exec")
        resume_point = mgr.get_resume_point(tasks)

        # Should return length (no tasks to resume)
        assert resume_point == 3

    def test_get_resume_point_failed_task(self, temp_checkpoint_dir):
        """Test getting resume point with failed task."""
        tasks = [
            TaskState(id="task-1", status="completed"),
            TaskState(id="task-2", status="failed"),
            TaskState(id="task-3", status="pending"),
        ]

        mgr = CheckpointManager("test-exec")
        resume_point = mgr.get_resume_point(tasks)

        # Should resume at index 1 (failed task)
        assert resume_point == 1

    def test_list_resumable_empty(self, temp_checkpoint_dir):
        """Test listing resumable checkpoints when none exist."""
        resumable = CheckpointManager.list_resumable()

        assert resumable == []

    def test_list_resumable_with_checkpoints(self, temp_checkpoint_dir):
        """Test listing resumable checkpoints."""
        # Create two checkpoints with incomplete tasks
        mgr1 = CheckpointManager("exec-1")
        mgr1.save(
            [
                TaskState(id="task-1", status="completed"),
                TaskState(id="task-2", status="pending"),
            ]
        )

        mgr2 = CheckpointManager("exec-2")
        mgr2.save(
            [
                TaskState(id="task-1", status="in_progress"),
            ]
        )

        # Create one fully completed checkpoint (should not be listed)
        mgr3 = CheckpointManager("exec-3")
        mgr3.save(
            [
                TaskState(id="task-1", status="completed"),
                TaskState(id="task-2", status="completed"),
            ]
        )

        resumable = CheckpointManager.list_resumable()

        # Should only list incomplete checkpoints
        assert len(resumable) == 2
        exec_ids = [c.execution_id for c in resumable]
        assert "exec-1" in exec_ids
        assert "exec-2" in exec_ids
        assert "exec-3" not in exec_ids

    def test_clean_old_checkpoints(self, temp_checkpoint_dir):
        """Test cleaning old checkpoints."""
        # Create old checkpoint by modifying mtime
        old_mgr = CheckpointManager("old-exec")
        old_mgr.save([TaskState(id="task-1", status="pending")])

        # Make it old (8 days ago)
        old_checkpoint = temp_checkpoint_dir / "old-exec.json"
        old_time = time.time() - (8 * 24 * 60 * 60)
        old_checkpoint.touch()
        import os

        os.utime(old_checkpoint, (old_time, old_time))

        # Create recent checkpoint
        recent_mgr = CheckpointManager("recent-exec")
        recent_mgr.save([TaskState(id="task-1", status="pending")])

        # Clean checkpoints older than 7 days
        removed = CheckpointManager.clean_old_checkpoints(days=7)

        # Should remove 1 checkpoint
        assert removed == 1
        assert not old_checkpoint.exists()
        assert (temp_checkpoint_dir / "recent-exec.json").exists()

    def test_task_state_with_metadata(self, temp_checkpoint_dir):
        """Test TaskState with metadata preservation."""
        execution_id = "test-exec-meta"
        mgr = CheckpointManager(execution_id)

        # Create task with metadata
        tasks = [
            TaskState(
                id="task-1",
                status="completed",
                result="All tests passed",
                started_at="2026-01-14T10:00:00Z",
                completed_at="2026-01-14T10:05:00Z",
                metadata={"duration_seconds": 300, "agent": "qa-expert"},
            )
        ]

        # Save and load
        mgr.save(tasks)
        loaded = mgr.load()

        assert loaded is not None
        task = loaded.tasks[0]
        assert task.result == "All tests passed"
        assert task.metadata["duration_seconds"] == 300
        assert task.metadata["agent"] == "qa-expert"
        assert task.started_at == "2026-01-14T10:00:00Z"
        assert task.completed_at == "2026-01-14T10:05:00Z"
