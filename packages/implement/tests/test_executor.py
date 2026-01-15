"""Tests for TaskExecutor.

TDD RED Phase: These tests should fail initially until TaskExecutor is implemented.
"""

import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from implement.executor import ExecutionResult, TaskExecutor
from implement.models import ParsedTask


def test_executor_init():
    """TaskExecutor accepts optional config."""
    executor = TaskExecutor()
    assert executor is not None

    executor_with_config = TaskExecutor(config={"tool": "claude"})
    assert executor_with_config is not None


@pytest.mark.asyncio
async def test_execute_returns_results():
    """Execute returns list of execution results."""
    tasks = [
        ParsedTask(id="1", description="Test task", agent="self"),
    ]

    with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
        f.write("- [ ] 1. Test task\n")
        tasks_file = Path(f.name)

    try:
        executor = TaskExecutor()
        results = await executor.execute(tasks, tasks_file)

        assert isinstance(results, list)
        assert len(results) == 1
        assert isinstance(results[0], ExecutionResult)
    finally:
        tasks_file.unlink()


@pytest.mark.asyncio
async def test_execute_skips_completed():
    """Already completed tasks are skipped."""
    tasks = [
        ParsedTask(id="1", description="Completed task", agent="self", completed=True),
        ParsedTask(id="2", description="Incomplete task", agent="self", completed=False),
    ]

    with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
        f.write("- [x] 1. Completed task\n- [ ] 2. Incomplete task\n")
        tasks_file = Path(f.name)

    try:
        executor = TaskExecutor()
        results = await executor.execute(tasks, tasks_file)

        # Only one task should be executed (the incomplete one)
        executed_results = [r for r in results if not r.skipped]
        assert len(executed_results) == 1
        assert executed_results[0].task_id == "2"
    finally:
        tasks_file.unlink()


@pytest.mark.asyncio
async def test_execute_self_task():
    """agent='self' executes directly (no external spawn)."""
    tasks = [
        ParsedTask(id="1", description="Self-executed task", agent="self"),
    ]

    with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
        f.write("- [ ] 1. Self-executed task\n")
        tasks_file = Path(f.name)

    try:
        executor = TaskExecutor()
        results = await executor.execute(tasks, tasks_file)

        assert len(results) == 1
        assert results[0].success is True
        assert results[0].task_id == "1"
        # Self-execution is a placeholder for now
        assert "self" in results[0].output.lower() or "placeholder" in results[0].output.lower()
    finally:
        tasks_file.unlink()


@pytest.mark.asyncio
async def test_execute_agent_task():
    """agent!='self' spawns subagent via spawner."""
    from aurora_spawner.models import SpawnResult

    tasks = [
        ParsedTask(id="1", description="Agent task", agent="full-stack-dev"),
    ]

    with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
        f.write("- [ ] 1. Agent task\n<!-- agent: full-stack-dev -->\n")
        tasks_file = Path(f.name)

    try:
        # Mock the spawner to return a SpawnResult
        mock_result = SpawnResult(
            success=True,
            output="Task completed by agent",
            error=None,
            exit_code=0,
        )

        with patch("implement.executor.spawn", return_value=mock_result) as mock_spawn:
            executor = TaskExecutor()
            results = await executor.execute(tasks, tasks_file)

            assert len(results) == 1
            assert results[0].success is True
            mock_spawn.assert_called_once()
    finally:
        tasks_file.unlink()


@pytest.mark.asyncio
async def test_execute_marks_complete_on_success():
    """Task marked [x] after successful execution."""
    tasks = [
        ParsedTask(id="1", description="Task to complete", agent="self"),
    ]

    with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
        f.write("- [ ] 1. Task to complete\n")
        tasks_file = Path(f.name)

    try:
        executor = TaskExecutor()
        await executor.execute(tasks, tasks_file)

        # Read the file and verify task is marked complete
        content = tasks_file.read_text()
        assert "- [x] 1. Task to complete" in content
    finally:
        tasks_file.unlink()


@pytest.mark.asyncio
async def test_execute_handles_failure():
    """Failed execution does not mark complete."""
    from aurora_spawner.models import SpawnResult

    tasks = [
        ParsedTask(id="1", description="Failing task", agent="failing-agent"),
    ]

    with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
        f.write("- [ ] 1. Failing task\n<!-- agent: failing-agent -->\n")
        tasks_file = Path(f.name)

    try:
        # Mock the spawner to return failure
        mock_result = SpawnResult(
            success=False,
            output="",
            error="Agent failed",
            exit_code=1,
        )

        with patch("implement.executor.spawn", return_value=mock_result):
            executor = TaskExecutor()
            results = await executor.execute(tasks, tasks_file)

            assert len(results) == 1
            assert results[0].success is False

            # Verify task is NOT marked complete
            content = tasks_file.read_text()
            assert "- [ ] 1. Failing task" in content
            assert "- [x]" not in content
    finally:
        tasks_file.unlink()


@pytest.mark.asyncio
async def test_execute_sequential_order():
    """Tasks executed in order."""
    tasks = [
        ParsedTask(id="1", description="First task", agent="self"),
        ParsedTask(id="2", description="Second task", agent="self"),
        ParsedTask(id="3", description="Third task", agent="self"),
    ]

    with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
        f.write("- [ ] 1. First task\n- [ ] 2. Second task\n- [ ] 3. Third task\n")
        tasks_file = Path(f.name)

    try:
        executor = TaskExecutor()
        results = await executor.execute(tasks, tasks_file)

        assert len(results) == 3
        assert results[0].task_id == "1"
        assert results[1].task_id == "2"
        assert results[2].task_id == "3"
    finally:
        tasks_file.unlink()


def test_build_agent_prompt():
    """Agent prompt includes task description and context."""
    executor = TaskExecutor()
    task = ParsedTask(id="1", description="Implement feature X", agent="full-stack-dev")

    prompt = executor._build_agent_prompt(task)

    assert "Implement feature X" in prompt
    assert "full-stack-dev" in prompt or "agent" in prompt.lower()


def test_agent_dispatch_prompt_format():
    """Agent dispatch uses Task tool format."""
    executor = TaskExecutor()
    task = ParsedTask(id="1", description="Build UI component", agent="ux-expert", model="sonnet")

    prompt = executor._build_agent_prompt(task)

    # Should include task description
    assert "Build UI component" in prompt
    # Should reference agent
    assert "ux-expert" in prompt or "agent" in prompt.lower()
