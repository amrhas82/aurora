"""End-to-end tests for spawn workflow with interruption and resume."""

import tempfile
from pathlib import Path

import pytest

from aurora_cli.execution import CheckpointManager, TaskState
from aurora_cli.commands.spawn_helpers import (
    create_task_states_from_tasks,
    list_checkpoints,
    resume_from_checkpoint,
)
from implement.models import ParsedTask


@pytest.fixture
def temp_aurora_dir(monkeypatch, tmp_path):
    """Use temporary directory for .aurora."""
    aurora_dir = tmp_path / ".aurora"
    aurora_dir.mkdir()
    checkpoints_dir = aurora_dir / "checkpoints"
    checkpoints_dir.mkdir()

    def mock_get_aurora_dir():
        return aurora_dir

    monkeypatch.setattr("aurora_cli.execution.checkpoint.get_aurora_dir", mock_get_aurora_dir)
    monkeypatch.setattr("aurora_core.paths.get_aurora_dir", mock_get_aurora_dir)
    monkeypatch.setattr("aurora_cli.commands.spawn_helpers.get_aurora_dir", mock_get_aurora_dir)

    return aurora_dir


@pytest.fixture
def sample_tasks():
    """Create sample tasks for testing."""
    return [
        ParsedTask(id="1", description="Task one", agent="agent1", completed=False),
        ParsedTask(id="2", description="Task two", agent="agent2", completed=False),
        ParsedTask(id="3", description="Task three", agent="agent3", completed=False),
        ParsedTask(id="4", description="Task four", agent="agent4", completed=False),
    ]


class TestSpawnWorkflowE2E:
    """End-to-end tests for complete spawn workflow."""

    def test_full_checkpoint_cycle(self, temp_aurora_dir, sample_tasks):
        """Test complete checkpoint create -> save -> load -> resume cycle."""
        execution_id = "e2e-test-001"

        # Step 1: Create checkpoint manager
        mgr = CheckpointManager(execution_id, plan_id=None)

        # Step 2: Start execution (save initial state)
        task_states = create_task_states_from_tasks(sample_tasks)
        mgr.save(task_states)

        # Verify checkpoint exists
        checkpoint_file = temp_aurora_dir / "checkpoints" / f"{execution_id}.json"
        assert checkpoint_file.exists()

        # Step 3: Simulate partial execution (complete 2 tasks)
        task_states[0].status = "completed"
        task_states[0].result = "Success"
        task_states[1].status = "completed"
        task_states[1].result = "Success"
        task_states[2].status = "in_progress"
        mgr.save(task_states)

        # Step 4: Simulate interruption
        mgr.mark_interrupted()

        # Step 5: Load checkpoint
        loaded = mgr.load()
        assert loaded is not None
        assert loaded.interrupted is True
        assert loaded.execution_id == execution_id

        # Step 6: Get resume point
        resume_point = mgr.get_resume_point(loaded.tasks)
        assert resume_point == 2  # Should resume at task 3 (in_progress)

        # Step 7: Resume execution (complete remaining tasks)
        for i in range(resume_point, len(loaded.tasks)):
            loaded.tasks[i].status = "completed"
            loaded.tasks[i].result = "Success"

        mgr.save(loaded.tasks)

        # Step 8: Verify all tasks completed
        final = mgr.load()
        assert all(t.status == "completed" for t in final.tasks)

    def test_list_checkpoints_workflow(self, temp_aurora_dir):
        """Test listing checkpoints in workflow."""
        # Create multiple checkpoints
        exec_ids = ["e2e-001", "e2e-002", "e2e-003"]

        for exec_id in exec_ids:
            mgr = CheckpointManager(exec_id)
            tasks = [
                TaskState(id="task-1", status="completed"),
                TaskState(id="task-2", status="pending"),
            ]
            mgr.save(tasks)

        # List checkpoints
        resumable = CheckpointManager.list_resumable()

        # Should list all incomplete checkpoints
        assert len(resumable) == 3
        listed_ids = [c.execution_id for c in resumable]
        for exec_id in exec_ids:
            assert exec_id in listed_ids

    def test_clean_old_checkpoints_workflow(self, temp_aurora_dir):
        """Test cleaning old checkpoints in workflow."""
        import os
        import time

        # Create old checkpoint
        old_mgr = CheckpointManager("old-checkpoint")
        old_mgr.save([TaskState(id="task-1", status="pending")])

        old_checkpoint = temp_aurora_dir / "checkpoints" / "old-checkpoint.json"
        old_time = time.time() - (8 * 24 * 60 * 60)  # 8 days ago
        os.utime(old_checkpoint, (old_time, old_time))

        # Create recent checkpoint
        recent_mgr = CheckpointManager("recent-checkpoint")
        recent_mgr.save([TaskState(id="task-1", status="pending")])

        # Clean old checkpoints
        removed = CheckpointManager.clean_old_checkpoints(days=7)

        # Verify old removed, recent kept
        assert removed == 1
        assert not old_checkpoint.exists()
        assert (temp_aurora_dir / "checkpoints" / "recent-checkpoint.json").exists()

    def test_resume_from_interrupted_execution(self, temp_aurora_dir, sample_tasks):
        """Test resuming from interrupted execution."""
        execution_id = "interrupted-exec"

        # Create and save checkpoint
        mgr = CheckpointManager(execution_id)
        task_states = create_task_states_from_tasks(sample_tasks)

        # Complete first 2 tasks
        task_states[0].status = "completed"
        task_states[1].status = "completed"
        mgr.save(task_states)

        # Mark as interrupted
        mgr.mark_interrupted()

        # Resume: load checkpoint and get resume point
        loaded = mgr.load()
        resume_point = mgr.get_resume_point(loaded.tasks)

        # Should resume from task 3
        assert resume_point == 2
        assert loaded.tasks[2].status == "pending"

        # Complete remaining tasks
        for i in range(resume_point, len(loaded.tasks)):
            loaded.tasks[i].status = "completed"

        mgr.save(loaded.tasks)

        # Verify completion
        final = mgr.load()
        completed_count = sum(1 for t in final.tasks if t.status == "completed")
        assert completed_count == len(sample_tasks)

    def test_task_metadata_preservation(self, temp_aurora_dir):
        """Test that task metadata is preserved through checkpoint cycle."""
        execution_id = "metadata-test"
        mgr = CheckpointManager(execution_id)

        # Create tasks with metadata
        tasks = [
            TaskState(
                id="task-1",
                status="completed",
                result="All tests passed",
                started_at="2026-01-14T10:00:00Z",
                completed_at="2026-01-14T10:05:00Z",
                metadata={
                    "description": "Run unit tests",
                    "agent": "qa-expert",
                    "duration_seconds": 300,
                    "exit_code": 0,
                },
            )
        ]

        # Save and load
        mgr.save(tasks)
        loaded = mgr.load()

        # Verify all metadata preserved
        task = loaded.tasks[0]
        assert task.id == "task-1"
        assert task.status == "completed"
        assert task.result == "All tests passed"
        assert task.metadata["description"] == "Run unit tests"
        assert task.metadata["agent"] == "qa-expert"
        assert task.metadata["duration_seconds"] == 300
        assert task.metadata["exit_code"] == 0
        assert task.started_at == "2026-01-14T10:00:00Z"
        assert task.completed_at == "2026-01-14T10:05:00Z"

    def test_multiple_resume_cycles(self, temp_aurora_dir, sample_tasks):
        """Test multiple interrupt-resume cycles."""
        execution_id = "multi-resume"
        mgr = CheckpointManager(execution_id)

        task_states = create_task_states_from_tasks(sample_tasks)
        mgr.save(task_states)

        # Cycle 1: Complete task 1, interrupt
        task_states[0].status = "completed"
        mgr.save(task_states)
        mgr.mark_interrupted()

        loaded = mgr.load()
        assert mgr.get_resume_point(loaded.tasks) == 1

        # Cycle 2: Complete task 2, interrupt
        task_states[1].status = "completed"
        mgr.save(task_states)
        mgr.mark_interrupted()

        loaded = mgr.load()
        assert mgr.get_resume_point(loaded.tasks) == 2

        # Cycle 3: Complete remaining tasks
        task_states[2].status = "completed"
        task_states[3].status = "completed"
        mgr.save(task_states)

        # Verify all completed
        final = mgr.load()
        assert all(t.status == "completed" for t in final.tasks)
        assert mgr.get_resume_point(final.tasks) == len(sample_tasks)
