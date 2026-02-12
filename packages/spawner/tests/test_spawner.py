"""Tests for spawn(), spawn_parallel(), and spawn_sequential() functions."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from aurora_spawner.models import SpawnResult, SpawnTask
from aurora_spawner.spawner import spawn, spawn_parallel, spawn_sequential


def _mock_process(stdout=b"", stderr=b"", returncode=0):
    """Create a mock subprocess with standard stdin/stdout/stderr wiring."""
    proc = AsyncMock()
    proc.communicate = AsyncMock(return_value=(stdout, stderr))
    proc.returncode = returncode
    proc.stdin = MagicMock()
    proc.stdin.write = MagicMock()
    proc.stdin.drain = AsyncMock()
    proc.stdin.close = MagicMock()
    return proc


def _patch_exec(mock_process):
    """Patch asyncio.create_subprocess_exec and shutil.which together."""
    return (
        patch("asyncio.create_subprocess_exec", return_value=mock_process),
        patch("shutil.which", return_value="/usr/bin/claude"),
    )


class TestSpawn:
    """Tests for spawn() -- process creation, result collection, error handling."""

    @pytest.mark.asyncio
    async def test_spawn_success(self):
        proc = _mock_process(stdout=b"success output")
        p1, p2 = _patch_exec(proc)
        with p1, p2:
            result = await spawn(SpawnTask(prompt="test prompt"))

        assert result.success is True
        assert result.output == "success output"
        assert result.error == ""
        assert result.exit_code == 0

    @pytest.mark.asyncio
    async def test_spawn_failure_nonzero_exit(self):
        proc = _mock_process(stderr=b"error message", returncode=1)
        p1, p2 = _patch_exec(proc)
        with p1, p2:
            result = await spawn(SpawnTask(prompt="test prompt"))

        assert result.success is False
        assert result.error == "error message"
        assert result.exit_code == 1

    @pytest.mark.asyncio
    async def test_spawn_timeout(self):
        async def slow_communicate():
            await asyncio.sleep(10)
            return (b"", b"")

        proc = _mock_process()
        proc.communicate = slow_communicate
        proc.kill = MagicMock()

        p1, p2 = _patch_exec(proc)
        with p1, p2:
            result = await spawn(SpawnTask(prompt="test prompt", timeout=1))

        assert result.success is False
        assert "timeout" in result.error.lower() or "timed out" in result.error.lower()

    @pytest.mark.asyncio
    async def test_spawn_tool_not_found(self):
        with patch("shutil.which", return_value=None):
            with pytest.raises(ValueError, match="Tool.*not found"):
                await spawn(SpawnTask(prompt="test prompt"), tool="nonexistent")

    @pytest.mark.asyncio
    async def test_spawn_builds_correct_command(self):
        proc = _mock_process(stdout=b"output")
        p1, p2 = _patch_exec(proc)
        with p1 as mock_exec, p2:
            await spawn(SpawnTask(prompt="test prompt"))

        call_args = mock_exec.call_args[0]
        assert call_args[0] == "claude"
        assert "-p" in call_args
        assert "--model" in call_args


class TestSpawnParallel:
    """Tests for spawn_parallel() -- concurrency, ordering, error handling."""

    @pytest.mark.asyncio
    async def test_spawn_parallel_empty_list(self):
        results = await spawn_parallel([])
        assert results == []

    @pytest.mark.asyncio
    async def test_spawn_parallel_multiple_tasks(self):
        tasks = [SpawnTask(prompt=f"task {i}") for i in range(3)]
        call_count = 0

        async def mock_spawn(task, **kwargs):
            nonlocal call_count
            call_count += 1
            await asyncio.sleep(0.01)
            return SpawnResult(
                success=True, output=f"output {call_count}", error=None, exit_code=0
            )

        with patch("aurora_spawner.spawner.spawn", side_effect=mock_spawn):
            results = await spawn_parallel(tasks)

        assert len(results) == 3
        assert all(r.success for r in results)

    @pytest.mark.asyncio
    async def test_spawn_parallel_respects_max_concurrent(self):
        tasks = [SpawnTask(prompt=f"task {i}") for i in range(10)]
        max_concurrent_running = 0
        current_running = 0

        async def mock_spawn(task, **kwargs):
            nonlocal max_concurrent_running, current_running
            current_running += 1
            max_concurrent_running = max(max_concurrent_running, current_running)
            await asyncio.sleep(0.01)
            current_running -= 1
            return SpawnResult(
                success=True, output="output", error=None, exit_code=0
            )

        with patch("aurora_spawner.spawner.spawn", side_effect=mock_spawn):
            await spawn_parallel(tasks, max_concurrent=3)

        assert max_concurrent_running <= 3

    @pytest.mark.asyncio
    async def test_spawn_parallel_continues_on_failure(self):
        tasks = [SpawnTask(prompt=f"task {i}") for i in range(3)]
        call_index = 0

        async def mock_spawn(task, **kwargs):
            nonlocal call_index
            call_index += 1
            if call_index == 2:
                return SpawnResult(
                    success=False, output="", error="Task 2 failed", exit_code=1
                )
            return SpawnResult(
                success=True, output=f"output {call_index}", error=None, exit_code=0
            )

        with patch("aurora_spawner.spawner.spawn", side_effect=mock_spawn):
            results = await spawn_parallel(tasks)

        assert len(results) == 3
        assert results[0].success is True
        assert results[1].success is False
        assert results[2].success is True

    @pytest.mark.asyncio
    async def test_spawn_parallel_preserves_order(self):
        tasks = [
            SpawnTask(prompt="task A"),
            SpawnTask(prompt="task B"),
            SpawnTask(prompt="task C"),
        ]

        async def mock_spawn(task, **kwargs):
            delay = {"A": 0.03, "B": 0.01, "C": 0.02}
            letter = task.prompt[-1]
            await asyncio.sleep(delay.get(letter, 0.01))
            return SpawnResult(
                success=True, output=task.prompt, error=None, exit_code=0
            )

        with patch("aurora_spawner.spawner.spawn", side_effect=mock_spawn):
            results = await spawn_parallel(tasks)

        assert results[0].output == "task A"
        assert results[1].output == "task B"
        assert results[2].output == "task C"


class TestSpawnSequential:
    """Tests for spawn_sequential() -- ordering, context passing, error handling."""

    @pytest.mark.asyncio
    async def test_spawn_sequential_empty_list(self):
        results = await spawn_sequential([])
        assert results == []

    @pytest.mark.asyncio
    async def test_spawn_sequential_multiple_tasks(self):
        tasks = [SpawnTask(prompt=f"task {i}") for i in range(1, 4)]
        execution_order = []

        async def mock_spawn(task, **kwargs):
            execution_order.append(task.prompt)
            return SpawnResult(
                success=True, output=f"result", error=None, exit_code=0
            )

        with patch("aurora_spawner.spawner.spawn", side_effect=mock_spawn):
            results = await spawn_sequential(tasks, pass_context=False)

        assert execution_order == ["task 1", "task 2", "task 3"]
        assert len(results) == 3

    @pytest.mark.asyncio
    async def test_spawn_sequential_context_accumulation(self):
        tasks = [SpawnTask(prompt=f"task {i}") for i in range(1, 4)]
        received_prompts = []

        async def mock_spawn(task, **kwargs):
            received_prompts.append(task.prompt)
            return SpawnResult(
                success=True,
                output=f"output {len(received_prompts)}",
                error=None,
                exit_code=0,
            )

        with patch("aurora_spawner.spawner.spawn", side_effect=mock_spawn):
            await spawn_sequential(tasks, pass_context=True)

        assert received_prompts[0] == "task 1"
        assert "task 2" in received_prompts[1]
        assert "Previous context:" in received_prompts[1]
        assert "output 1" in received_prompts[1]
        assert "task 3" in received_prompts[2]
        assert "output 1" in received_prompts[2]
        assert "output 2" in received_prompts[2]

    @pytest.mark.asyncio
    async def test_spawn_sequential_no_context_when_disabled(self):
        tasks = [SpawnTask(prompt=f"task {i}") for i in range(1, 3)]
        received_prompts = []

        async def mock_spawn(task, **kwargs):
            received_prompts.append(task.prompt)
            return SpawnResult(
                success=True, output="output", error=None, exit_code=0
            )

        with patch("aurora_spawner.spawner.spawn", side_effect=mock_spawn):
            await spawn_sequential(tasks, pass_context=False)

        assert received_prompts[0] == "task 1"
        assert received_prompts[1] == "task 2"
        assert "Previous context:" not in received_prompts[1]

    @pytest.mark.asyncio
    async def test_spawn_sequential_stops_on_failure_when_critical(self):
        tasks = [SpawnTask(prompt=f"task {i}") for i in range(1, 4)]
        call_count = 0

        async def mock_spawn(task, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 2:
                return SpawnResult(
                    success=False, output="", error="Task failed", exit_code=1
                )
            return SpawnResult(
                success=True, output="output", error=None, exit_code=0
            )

        with patch("aurora_spawner.spawner.spawn", side_effect=mock_spawn):
            results = await spawn_sequential(tasks, stop_on_failure=True)

        assert len(results) == 2
        assert results[0].success is True
        assert results[1].success is False


class TestSpawnWithRetryAndFallback:
    """Tests for spawn_with_retry_and_fallback() -- retry, fallback, error handling."""

    @pytest.mark.asyncio
    async def test_success_on_first_attempt(self):
        from aurora_spawner.spawner import spawn_with_retry_and_fallback

        async def mock_spawn(t, **kwargs):
            return SpawnResult(
                success=True, output="success output", error=None, exit_code=0
            )

        with patch("aurora_spawner.spawner.spawn", side_effect=mock_spawn):
            result = await spawn_with_retry_and_fallback(
                SpawnTask(prompt="test prompt", agent="test-agent")
            )

        assert result.success is True
        assert result.output == "success output"
        assert result.fallback is False
        assert result.retry_count == 0

    @pytest.mark.asyncio
    async def test_success_on_retry(self):
        from aurora_spawner.spawner import spawn_with_retry_and_fallback

        call_count = 0

        async def mock_spawn(t, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return SpawnResult(
                    success=False, output="", error="Temporary failure", exit_code=1
                )
            return SpawnResult(
                success=True, output="retry success", error=None, exit_code=0
            )

        with patch("aurora_spawner.spawner.spawn", side_effect=mock_spawn):
            result = await spawn_with_retry_and_fallback(
                SpawnTask(prompt="test prompt", agent="test-agent")
            )

        assert result.success is True
        assert result.output == "retry success"
        assert result.fallback is False
        assert result.retry_count == 1
        assert call_count == 2

    @pytest.mark.asyncio
    async def test_fallback_after_two_failures(self):
        from aurora_spawner.spawner import spawn_with_retry_and_fallback

        call_count = 0

        async def mock_spawn(t, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count <= 2:
                return SpawnResult(
                    success=False, output="", error=f"Failure {call_count}", exit_code=1
                )
            return SpawnResult(
                success=True, output="fallback llm output", error=None, exit_code=0
            )

        with patch("aurora_spawner.spawner.spawn", side_effect=mock_spawn):
            result = await spawn_with_retry_and_fallback(
                SpawnTask(prompt="test prompt", agent="failing-agent")
            )

        assert result.success is True
        assert result.output == "fallback llm output"
        assert result.fallback is True
        assert result.retry_count == 2
        assert call_count == 3

    @pytest.mark.asyncio
    async def test_timeout_triggers_retry(self):
        from aurora_spawner.spawner import spawn_with_retry_and_fallback

        call_count = 0

        async def mock_spawn(t, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return SpawnResult(
                    success=False,
                    output="",
                    error="Process timed out after 10 seconds",
                    exit_code=-1,
                )
            return SpawnResult(
                success=True, output="retry success", error=None, exit_code=0
            )

        with patch("aurora_spawner.spawner.spawn", side_effect=mock_spawn):
            result = await spawn_with_retry_and_fallback(
                SpawnTask(prompt="test prompt", agent="test-agent", timeout=10)
            )

        assert result.success is True
        assert result.retry_count == 1
        assert call_count == 2
