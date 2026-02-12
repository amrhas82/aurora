"""Unit tests for spawn_parallel edge cases and failure scenarios.

Tests concurrency limits, task ordering, exception handling, and
resource contention in the spawn_parallel function.
"""

import asyncio
import time
from unittest.mock import patch

import pytest

from aurora_spawner import SpawnResult, SpawnTask, spawn_parallel


class TestConcurrencyControl:
    """Test concurrency limiting and semaphore behavior."""

    @pytest.mark.asyncio
    async def test_max_concurrent_enforced(self):
        """Max concurrent limit is strictly enforced."""
        active_count = 0
        max_observed = 0
        lock = asyncio.Lock()

        async def mock_spawn(task, **kwargs):
            nonlocal active_count, max_observed
            async with lock:
                active_count += 1
                max_observed = max(max_observed, active_count)

            await asyncio.sleep(0.1)

            async with lock:
                active_count -= 1

            return SpawnResult(
                success=True,
                output="Done",
                error=None,
                exit_code=0,
            )

        tasks = [SpawnTask(prompt=f"Task {i}", agent="test", timeout=10) for i in range(20)]

        with patch("aurora_spawner.spawner.spawn", side_effect=mock_spawn):
            results = await spawn_parallel(tasks, max_concurrent=5)

            assert max_observed <= 5
            assert len(results) == 20
            assert all(r.success for r in results)

    @pytest.mark.asyncio
    async def test_single_concurrent_slot(self):
        """Works correctly with max_concurrent=1 (serial execution)."""
        execution_order = []

        async def mock_spawn(task, **kwargs):
            execution_order.append(task.prompt)
            await asyncio.sleep(0.05)
            return SpawnResult(
                success=True,
                output=task.prompt,
                error=None,
                exit_code=0,
            )

        tasks = [SpawnTask(prompt=f"Task {i}", agent="test", timeout=10) for i in range(5)]

        with patch("aurora_spawner.spawner.spawn", side_effect=mock_spawn):
            results = await spawn_parallel(tasks, max_concurrent=1)

            # Should complete in order with max_concurrent=1
            assert len(execution_order) == 5
            assert len(results) == 5
            assert all(r.success for r in results)

    @pytest.mark.asyncio
    async def test_zero_max_concurrent_raises(self):
        """Max concurrent of 0 raises ValueError."""
        tasks = [SpawnTask(prompt="Test", agent="test", timeout=10)]

        # asyncio.Semaphore(0) will raise ValueError
        with pytest.raises(ValueError):
            await spawn_parallel(tasks, max_concurrent=0)

    @pytest.mark.asyncio
    async def test_unlimited_concurrency(self):
        """Very high max_concurrent allows all tasks to run in parallel."""
        active_count = 0
        max_observed = 0
        lock = asyncio.Lock()

        async def mock_spawn(task, **kwargs):
            nonlocal active_count, max_observed
            async with lock:
                active_count += 1
                max_observed = max(max_observed, active_count)

            await asyncio.sleep(0.1)

            async with lock:
                active_count -= 1

            return SpawnResult(
                success=True,
                output="Done",
                error=None,
                exit_code=0,
            )

        tasks = [SpawnTask(prompt=f"Task {i}", agent="test", timeout=10) for i in range(10)]

        with patch("aurora_spawner.spawner.spawn", side_effect=mock_spawn):
            results = await spawn_parallel(tasks, max_concurrent=100)

            # All 10 tasks should run concurrently
            assert max_observed == 10
            assert len(results) == 10


class TestResultOrdering:
    """Test that results maintain input order."""

    @pytest.mark.asyncio
    async def test_results_match_input_order(self):
        """Results returned in same order as input tasks."""

        async def mock_spawn(task, **kwargs):
            # Random delays
            import random

            await asyncio.sleep(random.uniform(0.01, 0.1))
            return SpawnResult(
                success=True,
                output=task.prompt,
                error=None,
                exit_code=0,
            )

        tasks = [SpawnTask(prompt=f"Task {i}", agent="test", timeout=10) for i in range(20)]

        with patch("aurora_spawner.spawner.spawn", side_effect=mock_spawn):
            results = await spawn_parallel(tasks, max_concurrent=5)

            # Results should match input order despite random completion times
            assert len(results) == 20
            for i, result in enumerate(results):
                assert result.output == f"Task {i}"

    @pytest.mark.asyncio
    async def test_mixed_success_failure_order(self):
        """Mixed successes and failures maintain order."""

        async def mock_spawn(task, **kwargs):
            await asyncio.sleep(0.01)
            # Even indices succeed, odd fail
            idx = int(task.prompt.split()[-1])
            if idx % 2 == 0:
                return SpawnResult(
                    success=True,
                    output=task.prompt,
                    error=None,
                    exit_code=0,
                )
            return SpawnResult(
                success=False,
                output="",
                error=f"Failed {idx}",
                exit_code=-1,
            )

        tasks = [SpawnTask(prompt=f"Task {i}", agent="test", timeout=10) for i in range(10)]

        with patch("aurora_spawner.spawner.spawn", side_effect=mock_spawn):
            results = await spawn_parallel(tasks, max_concurrent=5)

            assert len(results) == 10
            for i, result in enumerate(results):
                if i % 2 == 0:
                    assert result.success
                    assert result.output == f"Task {i}"
                else:
                    assert not result.success
                    assert result.error == f"Failed {i}"


class TestExceptionHandling:
    """Test exception handling in parallel spawning."""

    @pytest.mark.asyncio
    async def test_exception_converts_to_failed_result(self):
        """Exceptions in spawn convert to failed SpawnResult."""

        async def mock_spawn(task, **kwargs):
            idx = int(task.prompt.split()[-1])
            if idx == 3:
                raise RuntimeError("Spawn failed unexpectedly")
            await asyncio.sleep(0.01)
            return SpawnResult(
                success=True,
                output=task.prompt,
                error=None,
                exit_code=0,
            )

        tasks = [SpawnTask(prompt=f"Task {i}", agent="test", timeout=10) for i in range(5)]

        with patch("aurora_spawner.spawner.spawn", side_effect=mock_spawn):
            results = await spawn_parallel(tasks, max_concurrent=5)

            # All tasks should have results
            assert len(results) == 5

            # Task 3 should be failed result
            assert not results[3].success
            assert "Spawn failed unexpectedly" in results[3].error

            # Others should succeed
            for i in [0, 1, 2, 4]:
                assert results[i].success

    @pytest.mark.asyncio
    async def test_multiple_exceptions_handled(self):
        """Multiple exceptions don't abort execution."""

        async def mock_spawn(task, **kwargs):
            idx = int(task.prompt.split()[-1])
            if idx in [1, 3, 5]:
                raise ValueError(f"Error {idx}")
            await asyncio.sleep(0.01)
            return SpawnResult(
                success=True,
                output=task.prompt,
                error=None,
                exit_code=0,
            )

        tasks = [SpawnTask(prompt=f"Task {i}", agent="test", timeout=10) for i in range(8)]

        with patch("aurora_spawner.spawner.spawn", side_effect=mock_spawn):
            results = await spawn_parallel(tasks, max_concurrent=4)

            assert len(results) == 8

            # Check failed indices
            for i in [1, 3, 5]:
                assert not results[i].success
                assert f"Error {i}" in results[i].error

            # Check success indices
            for i in [0, 2, 4, 6, 7]:
                assert results[i].success

    @pytest.mark.asyncio
    async def test_asyncio_cancellation(self):
        """Handles asyncio.CancelledError gracefully."""

        async def mock_spawn(task, **kwargs):
            idx = int(task.prompt.split()[-1])
            if idx == 2:
                raise asyncio.CancelledError()
            await asyncio.sleep(0.01)
            return SpawnResult(
                success=True,
                output=task.prompt,
                error=None,
                exit_code=0,
            )

        tasks = [SpawnTask(prompt=f"Task {i}", agent="test", timeout=10) for i in range(5)]

        with patch("aurora_spawner.spawner.spawn", side_effect=mock_spawn):
            # CancelledError should propagate, not be caught
            with pytest.raises(asyncio.CancelledError):
                await spawn_parallel(tasks, max_concurrent=5)


class TestProgressCallback:
    """Test on_progress callback functionality."""

    @pytest.mark.asyncio
    async def test_progress_callback_called(self):
        """Progress callback invoked for each task."""
        progress_events = []

        def on_progress(idx, total, agent_id, status):
            progress_events.append(
                {
                    "idx": idx,
                    "total": total,
                    "agent_id": agent_id,
                    "status": status,
                },
            )

        async def mock_spawn(task, **kwargs):
            await asyncio.sleep(0.05)
            return SpawnResult(
                success=True,
                output="Done",
                error=None,
                exit_code=0,
            )

        tasks = [SpawnTask(prompt=f"Task {i}", agent=f"agent-{i}", timeout=10) for i in range(3)]

        with patch("aurora_spawner.spawner.spawn", side_effect=mock_spawn):
            results = await spawn_parallel(
                tasks,
                max_concurrent=5,
                on_progress=on_progress,
            )

            # Should have start and complete for each task
            assert len(progress_events) >= 6  # 3 starts + 3 completes
            assert all(e["total"] == 3 for e in progress_events)

    @pytest.mark.asyncio
    async def test_progress_callback_exception_ignored(self):
        """Exception in progress callback doesn't abort execution."""

        def on_progress(idx, total, agent_id, status):
            if idx == 2:
                raise ValueError("Callback error")

        async def mock_spawn(task, **kwargs):
            await asyncio.sleep(0.01)
            return SpawnResult(
                success=True,
                output="Done",
                error=None,
                exit_code=0,
            )

        tasks = [SpawnTask(prompt=f"Task {i}", agent="test", timeout=10) for i in range(5)]

        with patch("aurora_spawner.spawner.spawn", side_effect=mock_spawn):
            # Should complete despite callback error
            results = await spawn_parallel(
                tasks,
                max_concurrent=5,
                on_progress=on_progress,
            )

            assert len(results) == 5
            assert all(r.success for r in results)


class TestEmptyAndEdgeCases:
    """Test empty inputs and edge cases."""

    @pytest.mark.asyncio
    async def test_empty_task_list(self):
        """Empty task list returns empty results."""
        results = await spawn_parallel([], max_concurrent=5)
        assert results == []

    @pytest.mark.asyncio
    async def test_single_task(self):
        """Single task works correctly."""

        async def mock_spawn(task, **kwargs):
            await asyncio.sleep(0.01)
            return SpawnResult(
                success=True,
                output="Single",
                error=None,
                exit_code=0,
            )

        tasks = [SpawnTask(prompt="Single task", agent="test", timeout=10)]

        with patch("aurora_spawner.spawner.spawn", side_effect=mock_spawn):
            results = await spawn_parallel(tasks, max_concurrent=5)

            assert len(results) == 1
            assert results[0].success
            assert results[0].output == "Single"

    @pytest.mark.asyncio
    async def test_all_tasks_fail(self):
        """All tasks failing handled correctly."""

        async def mock_spawn(task, **kwargs):
            await asyncio.sleep(0.01)
            return SpawnResult(
                success=False,
                output="",
                error="All failed",
                exit_code=-1,
            )

        tasks = [SpawnTask(prompt=f"Task {i}", agent="test", timeout=10) for i in range(5)]

        with patch("aurora_spawner.spawner.spawn", side_effect=mock_spawn):
            results = await spawn_parallel(tasks, max_concurrent=5)

            assert len(results) == 5
            assert all(not r.success for r in results)
            assert all(r.error == "All failed" for r in results)

    @pytest.mark.asyncio
    async def test_very_large_task_list(self):
        """Very large task list (1000+) handled efficiently."""

        async def mock_spawn(task, **kwargs):
            await asyncio.sleep(0.001)  # Very fast
            return SpawnResult(
                success=True,
                output=task.prompt,
                error=None,
                exit_code=0,
            )

        tasks = [SpawnTask(prompt=f"Task {i}", agent="test", timeout=10) for i in range(1000)]

        with patch("aurora_spawner.spawner.spawn", side_effect=mock_spawn):
            start = time.time()
            results = await spawn_parallel(tasks, max_concurrent=50)
            elapsed = time.time() - start

            assert len(results) == 1000
            assert all(r.success for r in results)
            # Should complete much faster than serial (1 second)
            # With 50 concurrent: ~20 batches * 0.001s = 0.02s + overhead
            assert elapsed < 2.0


class TestKwargsPassthrough:
    """Test that kwargs are passed through to spawn."""

    @pytest.mark.asyncio
    async def test_tool_and_model_passed(self):
        """Tool and model kwargs passed to spawn."""
        spawn_calls = []

        async def mock_spawn(task, tool=None, model=None, **kwargs):
            spawn_calls.append({"tool": tool, "model": model})
            await asyncio.sleep(0.01)
            return SpawnResult(
                success=True,
                output="Done",
                error=None,
                exit_code=0,
            )

        tasks = [SpawnTask(prompt=f"Task {i}", agent="test", timeout=10) for i in range(3)]

        with patch("aurora_spawner.spawner.spawn", side_effect=mock_spawn):
            results = await spawn_parallel(
                tasks,
                max_concurrent=5,
                tool="custom-tool",
                model="custom-model",
            )

            assert len(spawn_calls) == 3
            assert all(c["tool"] == "custom-tool" for c in spawn_calls)
            assert all(c["model"] == "custom-model" for c in spawn_calls)

    @pytest.mark.asyncio
    async def test_config_passed(self):
        """Config dict passed to spawn."""
        spawn_calls = []

        async def mock_spawn(task, config=None, **kwargs):
            spawn_calls.append(config)
            await asyncio.sleep(0.01)
            return SpawnResult(
                success=True,
                output="Done",
                error=None,
                exit_code=0,
            )

        test_config = {"key": "value", "spawner": {"timeout": 120}}
        tasks = [SpawnTask(prompt=f"Task {i}", agent="test", timeout=10) for i in range(3)]

        with patch("aurora_spawner.spawner.spawn", side_effect=mock_spawn):
            results = await spawn_parallel(
                tasks,
                max_concurrent=5,
                config=test_config,
            )

            assert len(spawn_calls) == 3
            assert all(c == test_config for c in spawn_calls)


class TestTimingAndPerformance:
    """Test timing characteristics and performance."""

    @pytest.mark.asyncio
    async def test_parallel_faster_than_serial(self):
        """Parallel execution is significantly faster than serial."""

        async def mock_spawn(task, **kwargs):
            await asyncio.sleep(0.1)  # 100ms per task
            return SpawnResult(
                success=True,
                output="Done",
                error=None,
                exit_code=0,
            )

        tasks = [SpawnTask(prompt=f"Task {i}", agent="test", timeout=10) for i in range(10)]

        with patch("aurora_spawner.spawner.spawn", side_effect=mock_spawn):
            start = time.time()
            results = await spawn_parallel(tasks, max_concurrent=5)
            parallel_time = time.time() - start

            # Serial time would be 10 * 0.1 = 1.0s
            # Parallel with 5 concurrent: 2 batches * 0.1 = 0.2s + overhead
            # Should be < 0.5s (much less than serial 1.0s)
            assert parallel_time < 0.5
            assert len(results) == 10

    @pytest.mark.asyncio
    async def test_respects_task_execution_time(self):
        """Tasks with varying durations all complete correctly."""

        async def mock_spawn(task, **kwargs):
            idx = int(task.prompt.split()[-1])
            # Varying durations: 0.01s, 0.02s, 0.03s, etc.
            await asyncio.sleep(0.01 * (idx + 1))
            return SpawnResult(
                success=True,
                output=task.prompt,
                error=None,
                exit_code=0,
            )

        tasks = [SpawnTask(prompt=f"Task {i}", agent="test", timeout=10) for i in range(5)]

        with patch("aurora_spawner.spawner.spawn", side_effect=mock_spawn):
            results = await spawn_parallel(tasks, max_concurrent=5)

            # All should complete despite varying durations
            assert len(results) == 5
            assert all(r.success for r in results)
            # Results should maintain order
            for i, result in enumerate(results):
                assert result.output == f"Task {i}"
