"""Load tests for adhoc agent spawning in SOAR pipeline.

Validates fixes against real-world parallel spawning scenarios including:
- High concurrency with adhoc (agent=None) spawns
- Mixed adhoc and named agent spawns
- Resource exhaustion scenarios
- Circuit breaker behavior under load
- Early detection under concurrent load
"""

import asyncio
import time
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from aurora_spawner.models import SpawnResult, SpawnTask
from aurora_spawner.spawner import spawn_parallel
from aurora_spawner.timeout_policy import SpawnPolicy


class TestAdhocAgentLoadScenarios:
    """Load tests for adhoc (agent=None) spawning scenarios."""

    @pytest.mark.asyncio
    async def test_high_concurrency_adhoc_agents(self):
        """Test high concurrency with adhoc agents (real-world SOAR collect phase)."""
        # Simulate 20 adhoc agent spawns (typical SOAR decomposition)
        num_tasks = 20
        tasks = [
            SpawnTask(
                prompt=f"Analyze requirement {i}",
                agent=None,  # Adhoc agent
                timeout=30,
                policy_name="test",
            )
            for i in range(num_tasks)
        ]

        # Mock spawn to simulate fast completion (avoid real spawns)
        async def mock_spawn_adhoc(task, **kwargs):
            # Simulate variable execution time (0.1-0.5s)
            await asyncio.sleep(0.1 + (hash(task.prompt) % 5) * 0.1)
            return SpawnResult(
                success=True,
                output=f"Analysis for {task.prompt}",
                error=None,
                exit_code=0,
                execution_time=0.2,
            )

        with patch("aurora_spawner.spawner.spawn", side_effect=mock_spawn_adhoc):
            start_time = time.time()
            results = await spawn_parallel(
                tasks,
                max_concurrent=10,  # SOAR default
            )
            elapsed = time.time() - start_time

        # Verify all completed successfully
        assert len(results) == num_tasks
        assert all(r.success for r in results)

        # Verify parallel execution (should take ~0.5s for 2 batches, not 20*0.2=4s)
        assert elapsed < 2.0, f"Parallel execution too slow: {elapsed:.2f}s"

    @pytest.mark.asyncio
    async def test_mixed_adhoc_and_named_agents(self):
        """Test mixed adhoc (LLM) and named agent spawning."""
        # Simulate mixed agent scenario: 10 adhoc, 5 named agents
        tasks = []

        # 10 adhoc agents (agent=None)
        for i in range(10):
            tasks.append(
                SpawnTask(
                    prompt=f"Adhoc task {i}",
                    agent=None,
                    timeout=30,
                    policy_name="test",
                )
            )

        # 5 named agents
        for i in range(5):
            tasks.append(
                SpawnTask(
                    prompt=f"Named task {i}",
                    agent=f"agent-{i % 3}",  # 3 different agents
                    timeout=30,
                    policy_name="test",
                )
            )

        # Mock spawn with different behavior for adhoc vs named
        async def mock_spawn_mixed(task, **kwargs):
            await asyncio.sleep(0.1)
            if task.agent is None:
                # Adhoc agents succeed fast
                return SpawnResult(
                    success=True,
                    output=f"Adhoc result: {task.prompt}",
                    error=None,
                    exit_code=0,
                    execution_time=0.1,
                )
            else:
                # Named agents may fail and fallback
                return SpawnResult(
                    success=True,
                    output=f"Named result: {task.prompt}",
                    error=None,
                    exit_code=0,
                    execution_time=0.1,
                    fallback=False,
                    original_agent=task.agent,
                )

        with patch("aurora_spawner.spawner.spawn", side_effect=mock_spawn_mixed):
            results = await spawn_parallel(tasks, max_concurrent=10)

        assert len(results) == 15
        assert all(r.success for r in results)

        # Verify adhoc results
        adhoc_results = results[:10]
        assert all("Adhoc result" in r.output for r in adhoc_results)

        # Verify named results
        named_results = results[10:]
        assert all("Named result" in r.output for r in named_results)

    @pytest.mark.asyncio
    async def test_adhoc_agents_with_early_failures(self):
        """Test adhoc agents with early failure detection."""
        # Simulate scenario where some adhoc agents fail early
        num_tasks = 15
        tasks = [
            SpawnTask(
                prompt=f"Task {i}",
                agent=None,
                timeout=30,
                policy_name="test",
            )
            for i in range(num_tasks)
        ]

        # Mock spawn: 20% fail with rate limit, rest succeed
        async def mock_spawn_with_failures(task, **kwargs):
            task_id = hash(task.prompt)
            await asyncio.sleep(0.1)

            # 20% failure rate (rate limit)
            if task_id % 5 == 0:
                return SpawnResult(
                    success=False,
                    output="",
                    error="Rate limit exceeded",
                    exit_code=-1,
                    termination_reason="Error pattern matched: rate limit",
                    execution_time=0.1,  # Fast failure
                )
            else:
                return SpawnResult(
                    success=True,
                    output=f"Success: {task.prompt}",
                    error=None,
                    exit_code=0,
                    execution_time=0.2,
                )

        with patch("aurora_spawner.spawner.spawn", side_effect=mock_spawn_with_failures):
            start_time = time.time()
            results = await spawn_parallel(tasks, max_concurrent=10)
            elapsed = time.time() - start_time

        # Verify results
        assert len(results) == num_tasks
        success_count = sum(1 for r in results if r.success)
        failure_count = sum(1 for r in results if not r.success)

        # Expect ~20% failure rate (3 failures out of 15)
        # Allow wider range due to hash-based randomness
        assert failure_count >= 2 and failure_count <= 6
        assert success_count >= 9 and success_count <= 13

        # Verify failures detected early (not waiting for timeout)
        failed_results = [r for r in results if not r.success]
        for result in failed_results:
            assert result.execution_time < 1.0, "Failure should be detected quickly"
            assert "rate limit" in result.termination_reason.lower()

        # Verify total time is reasonable (failures don't block successes)
        assert elapsed < 2.0, f"Early failures should not block pipeline: {elapsed:.2f}s"

    @pytest.mark.asyncio
    async def test_adhoc_agents_under_resource_pressure(self):
        """Test adhoc spawning under simulated resource pressure."""
        # Simulate high concurrency with limited resources
        num_tasks = 50
        max_concurrent = 5  # Limited concurrency

        tasks = [
            SpawnTask(
                prompt=f"Resource-intensive task {i}",
                agent=None,
                timeout=30,
                policy_name="test",
            )
            for i in range(num_tasks)
        ]

        # Mock spawn with variable delays (simulating resource contention)
        spawn_count = 0

        async def mock_spawn_resource_pressure(task, **kwargs):
            nonlocal spawn_count
            spawn_count += 1

            # Simulate resource pressure: slower as more tasks spawn
            delay = 0.05 + (spawn_count % 10) * 0.01
            await asyncio.sleep(delay)

            return SpawnResult(
                success=True,
                output=f"Completed: {task.prompt}",
                error=None,
                exit_code=0,
                execution_time=delay,
            )

        with patch("aurora_spawner.spawner.spawn", side_effect=mock_spawn_resource_pressure):
            start_time = time.time()
            results = await spawn_parallel(tasks, max_concurrent=max_concurrent)
            elapsed = time.time() - start_time

        # Verify all completed
        assert len(results) == num_tasks
        assert all(r.success for r in results)
        assert spawn_count == num_tasks

        # Verify respects concurrency limit
        # With max_concurrent=5, 50 tasks should take ~10 batches
        # Each batch ~0.05-0.15s -> total ~1-2s
        assert elapsed < 5.0, f"Resource-limited execution too slow: {elapsed:.2f}s"

    @pytest.mark.asyncio
    async def test_adhoc_agents_with_stalls(self):
        """Test adhoc agents with stall detection (no output progress)."""
        # Simulate scenario where some adhoc agents stall
        num_tasks = 10
        tasks = [
            SpawnTask(
                prompt=f"Task {i}",
                agent=None,
                timeout=30,
                policy_name="test",
            )
            for i in range(num_tasks)
        ]

        # Mock spawn: 30% stall (no output), rest succeed
        async def mock_spawn_with_stalls(task, **kwargs):
            task_id = hash(task.prompt)

            # 30% stall rate
            if task_id % 3 == 0:
                # Simulate stall detection (early termination after no-activity timeout)
                await asyncio.sleep(0.2)  # Simulated detection time
                return SpawnResult(
                    success=False,
                    output="",
                    error="Process stalled",
                    exit_code=-1,
                    termination_reason="No activity for 10 seconds",
                    execution_time=0.2,  # Fast detection via test policy
                )
            else:
                await asyncio.sleep(0.1)
                return SpawnResult(
                    success=True,
                    output=f"Success: {task.prompt}",
                    error=None,
                    exit_code=0,
                    execution_time=0.1,
                )

        with patch("aurora_spawner.spawner.spawn", side_effect=mock_spawn_with_stalls):
            start_time = time.time()
            results = await spawn_parallel(tasks, max_concurrent=5)
            elapsed = time.time() - start_time

        # Verify results
        assert len(results) == num_tasks
        stall_failures = [
            r for r in results if not r.success and "activity" in r.termination_reason.lower()
        ]

        # Expect ~30% stall rate (3 failures out of 10)
        # Allow wider range due to hash-based randomness
        assert len(stall_failures) >= 1 and len(stall_failures) <= 5

        # Verify stalls detected quickly (not waiting for full timeout)
        for result in stall_failures:
            assert result.execution_time < 1.0, "Stall should be detected via no-activity timeout"

        # Verify pipeline doesn't hang
        assert elapsed < 2.0, f"Stall detection should prevent hanging: {elapsed:.2f}s"

    @pytest.mark.asyncio
    async def test_adhoc_agents_with_circuit_breaker_disabled(self):
        """Test that adhoc agents don't trigger circuit breaker (expected behavior)."""
        # Circuit breaker only applies to named agents, not adhoc (agent=None)
        num_tasks = 20
        tasks = [
            SpawnTask(
                prompt=f"Adhoc task {i}",
                agent=None,  # Adhoc agents don't use circuit breaker
                timeout=30,
                policy_name="default",  # Has circuit breaker enabled
            )
            for i in range(num_tasks)
        ]

        # Mock spawn: consistent failures (would normally trip circuit breaker for named agents)
        async def mock_spawn_consistent_failures(task, **kwargs):
            await asyncio.sleep(0.05)
            # All fail with same error
            return SpawnResult(
                success=False,
                output="",
                error="API connection error",
                exit_code=-1,
                termination_reason="Error pattern matched: connection error",
                execution_time=0.05,
            )

        with patch("aurora_spawner.spawner.spawn", side_effect=mock_spawn_consistent_failures):
            results = await spawn_parallel(tasks, max_concurrent=10)

        # Verify all attempted (not skipped by circuit breaker)
        assert len(results) == num_tasks
        assert all(not r.success for r in results)

        # Verify no tasks were skipped (circuit breaker doesn't apply to adhoc)
        # All results have termination_reason, not "Circuit breaker" messages
        for result in results:
            assert "circuit" not in result.error.lower()

    @pytest.mark.asyncio
    async def test_bulk_adhoc_spawning_performance(self):
        """Test performance characteristics of bulk adhoc agent spawning."""
        # Simulate realistic SOAR collect phase: 30 adhoc agents
        num_tasks = 30
        max_concurrent = 10

        tasks = [
            SpawnTask(
                prompt=f"Analyze aspect {i} of the question",
                agent=None,
                timeout=30,
                policy_name="test",
            )
            for i in range(num_tasks)
        ]

        # Mock spawn with realistic timing (0.2-0.5s per spawn)
        async def mock_spawn_realistic(task, **kwargs):
            # Simulate realistic LLM response time
            delay = 0.2 + (hash(task.prompt) % 4) * 0.1
            await asyncio.sleep(delay)

            return SpawnResult(
                success=True,
                output=f"Analysis result for {task.prompt[:30]}...",
                error=None,
                exit_code=0,
                execution_time=delay,
            )

        with patch("aurora_spawner.spawner.spawn", side_effect=mock_spawn_realistic):
            start_time = time.time()
            results = await spawn_parallel(tasks, max_concurrent=max_concurrent)
            elapsed = time.time() - start_time

        # Verify all completed
        assert len(results) == num_tasks
        assert all(r.success for r in results)

        # Performance validation:
        # 30 tasks, max_concurrent=10 -> 3 batches
        # Each batch: 0.2-0.5s -> total: 0.6-1.5s (not 30*0.2=6s sequential)
        assert elapsed < 2.5, f"Bulk spawning too slow: {elapsed:.2f}s (expected <2.5s)"
        assert elapsed > 0.5, f"Bulk spawning too fast (mocking issue?): {elapsed:.2f}s"

        # Verify parallelism: actual time should be ~1/3 of sequential time
        avg_task_time = sum(r.execution_time for r in results) / len(results)
        sequential_time = avg_task_time * num_tasks
        parallelism_ratio = sequential_time / elapsed

        # Should achieve at least 5x speedup with max_concurrent=10
        assert parallelism_ratio >= 5.0, f"Poor parallelism: {parallelism_ratio:.1f}x speedup"

    @pytest.mark.asyncio
    async def test_adhoc_agents_progressive_timeout_under_load(self):
        """Test progressive timeout behavior with adhoc agents under concurrent load."""
        # Simulate scenario where some adhoc agents produce output slowly
        num_tasks = 15
        tasks = [
            SpawnTask(
                prompt=f"Slow task {i}",
                agent=None,
                timeout=60,
                policy_name="patient",  # Uses progressive timeout
            )
            for i in range(num_tasks)
        ]

        # Mock spawn: some produce output gradually (should extend timeout)
        async def mock_spawn_progressive(task, **kwargs):
            task_id = hash(task.prompt)

            # 40% are slow but produce output (timeout should extend)
            if task_id % 5 < 2:
                # Simulate gradual output over 2s
                await asyncio.sleep(2.0)
                return SpawnResult(
                    success=True,
                    output=f"Slow result: {task.prompt}",
                    error=None,
                    exit_code=0,
                    execution_time=2.0,
                    timeout_extended=True,  # Progressive timeout extended
                )
            else:
                # Fast completion
                await asyncio.sleep(0.2)
                return SpawnResult(
                    success=True,
                    output=f"Fast result: {task.prompt}",
                    error=None,
                    exit_code=0,
                    execution_time=0.2,
                    timeout_extended=False,
                )

        with patch("aurora_spawner.spawner.spawn", side_effect=mock_spawn_progressive):
            start_time = time.time()
            results = await spawn_parallel(tasks, max_concurrent=5)
            elapsed = time.time() - start_time

        # Verify all completed
        assert len(results) == num_tasks
        assert all(r.success for r in results)

        # Verify some had timeout extended
        extended_count = sum(1 for r in results if r.timeout_extended)
        # Allow wider range due to hash-based randomness: ~40% of 15
        assert extended_count >= 3 and extended_count <= 10

        # Verify pipeline completes in reasonable time
        # With max_concurrent=5, 3 batches, slowest tasks ~2s -> total ~6-8s
        assert elapsed < 10.0, f"Progressive timeout too slow: {elapsed:.2f}s"


class TestAdhocAgentEdgeCases:
    """Edge cases and error scenarios for adhoc agent spawning."""

    @pytest.mark.asyncio
    async def test_empty_adhoc_task_list(self):
        """Test handling of empty task list."""
        results = await spawn_parallel([], max_concurrent=10)
        assert results == []

    @pytest.mark.asyncio
    async def test_single_adhoc_agent(self):
        """Test single adhoc agent spawn."""
        task = SpawnTask(
            prompt="Single adhoc task",
            agent=None,
            timeout=30,
            policy_name="test",
        )

        async def mock_spawn_single(task, **kwargs):
            await asyncio.sleep(0.1)
            return SpawnResult(
                success=True,
                output="Single result",
                error=None,
                exit_code=0,
                execution_time=0.1,
            )

        with patch("aurora_spawner.spawner.spawn", side_effect=mock_spawn_single):
            results = await spawn_parallel([task], max_concurrent=10)

        assert len(results) == 1
        assert results[0].success
        assert results[0].output == "Single result"

    @pytest.mark.asyncio
    async def test_adhoc_agents_all_fail(self):
        """Test scenario where all adhoc agents fail."""
        num_tasks = 10
        tasks = [
            SpawnTask(
                prompt=f"Task {i}",
                agent=None,
                timeout=30,
                policy_name="test",
            )
            for i in range(num_tasks)
        ]

        # Mock spawn: all fail immediately
        async def mock_spawn_all_fail(task, **kwargs):
            await asyncio.sleep(0.05)
            return SpawnResult(
                success=False,
                output="",
                error="Simulated failure",
                exit_code=-1,
                termination_reason="Error pattern matched: API unavailable",
                execution_time=0.05,
            )

        with patch("aurora_spawner.spawner.spawn", side_effect=mock_spawn_all_fail):
            start_time = time.time()
            results = await spawn_parallel(tasks, max_concurrent=10)
            elapsed = time.time() - start_time

        # Verify all failed
        assert len(results) == num_tasks
        assert all(not r.success for r in results)

        # Verify fast failure (not waiting for timeouts)
        assert elapsed < 1.0, f"All failures should be detected quickly: {elapsed:.2f}s"

    @pytest.mark.asyncio
    async def test_adhoc_agent_exception_handling(self):
        """Test exception handling in adhoc agent spawning."""
        num_tasks = 5
        tasks = [
            SpawnTask(
                prompt=f"Task {i}",
                agent=None,
                timeout=30,
                policy_name="test",
            )
            for i in range(num_tasks)
        ]

        # Mock spawn: raise exception on some tasks
        async def mock_spawn_with_exceptions(task, **kwargs):
            task_id = hash(task.prompt)

            # 40% raise exception (simulating crash/error)
            if task_id % 5 < 2:
                raise RuntimeError("Simulated spawn exception")
            else:
                await asyncio.sleep(0.1)
                return SpawnResult(
                    success=True,
                    output=f"Success: {task.prompt}",
                    error=None,
                    exit_code=0,
                    execution_time=0.1,
                )

        with patch("aurora_spawner.spawner.spawn", side_effect=mock_spawn_with_exceptions):
            results = await spawn_parallel(tasks, max_concurrent=5)

        # Verify all tasks have results (exceptions converted to failed results)
        assert len(results) == num_tasks

        # Count failures (exceptions should be caught and converted)
        failure_count = sum(1 for r in results if not r.success)
        success_count = sum(1 for r in results if r.success)

        # Expect ~40% failures (2 out of 5)
        assert failure_count >= 1 and failure_count <= 3
        assert success_count >= 2 and success_count <= 4

        # Verify failed results contain exception info
        failed_results = [r for r in results if not r.success]
        for result in failed_results:
            assert result.exit_code == -1
            assert "exception" in result.error.lower() or result.error != ""
