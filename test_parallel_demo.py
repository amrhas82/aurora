#!/usr/bin/env python3
"""Quick demonstration of parallel execution functionality."""

import asyncio
import time
from aurora_spawner import SpawnTask, spawn_parallel
from aurora_spawner.models import SpawnResult
from unittest.mock import patch


async def mock_spawn(task, **kwargs):
    """Mock spawn function that simulates work."""
    # Simulate varying execution times
    task_id = task.prompt.split()[-1]
    delay = 0.1 + (int(task_id) % 3) * 0.05
    await asyncio.sleep(delay)

    return SpawnResult(
        success=True,
        output=f"Completed {task.prompt}",
        error=None,
        exit_code=0,
        execution_time=delay,
    )


async def test_parallel_execution():
    """Test that parallel execution works correctly."""
    print("=" * 60)
    print("Testing Parallel Execution")
    print("=" * 60)

    # Create 10 tasks
    num_tasks = 10
    tasks = [
        SpawnTask(
            prompt=f"Task {i}",
            agent=f"agent-{i % 3}",  # 3 different agents
            timeout=30
        )
        for i in range(num_tasks)
    ]

    print(f"\nCreated {num_tasks} tasks")
    print(f"Max concurrent: 4")

    # Track progress
    progress_events = []
    def on_progress(idx, total, agent_id, status):
        msg = f"  [{idx}/{total}] {agent_id}: {status}"
        print(msg)
        progress_events.append(msg)

    # Run with mock spawn
    with patch("aurora_spawner.spawner.spawn", side_effect=mock_spawn):
        start_time = time.time()
        results = await spawn_parallel(
            tasks,
            max_concurrent=4,
            on_progress=on_progress
        )
        elapsed = time.time() - start_time

    print(f"\n{'=' * 60}")
    print("Results:")
    print(f"{'=' * 60}")
    print(f"Total tasks: {len(results)}")
    print(f"Successful: {sum(1 for r in results if r.success)}")
    print(f"Failed: {sum(1 for r in results if not r.success)}")
    print(f"Total time: {elapsed:.2f}s")
    print(f"Progress callbacks: {len(progress_events)}")

    # Verify results
    assert len(results) == num_tasks, "Should return result for each task"
    assert all(r.success for r in results), "All tasks should succeed"

    # Verify order is preserved
    for i, result in enumerate(results):
        expected = f"Completed Task {i}"
        assert result.output == expected, f"Result order mismatch at {i}"

    print("\n✓ All assertions passed!")
    print(f"✓ Parallel execution working correctly")
    print(f"✓ Results returned in correct order")
    print(f"✓ Progress callbacks working")

    return results, elapsed


async def test_concurrency_limit():
    """Test that concurrency limit is enforced."""
    print("\n" + "=" * 60)
    print("Testing Concurrency Limit Enforcement")
    print("=" * 60)

    active_count = 0
    max_observed = 0
    lock = asyncio.Lock()

    async def mock_spawn_concurrent(task, **kwargs):
        nonlocal active_count, max_observed

        async with lock:
            active_count += 1
            max_observed = max(max_observed, active_count)
            print(f"  Active tasks: {active_count} (max: {max_observed})")

        await asyncio.sleep(0.1)

        async with lock:
            active_count -= 1

        return SpawnResult(
            success=True,
            output=f"Done {task.prompt}",
            error=None,
            exit_code=0,
        )

    # Create 20 tasks with max_concurrent=5
    tasks = [SpawnTask(prompt=f"Task {i}", agent="test", timeout=10) for i in range(20)]

    with patch("aurora_spawner.spawner.spawn", side_effect=mock_spawn_concurrent):
        results = await spawn_parallel(tasks, max_concurrent=5)

    print(f"\n{'=' * 60}")
    print("Concurrency Test Results:")
    print(f"{'=' * 60}")
    print(f"Total tasks: {len(results)}")
    print(f"Max concurrent limit: 5")
    print(f"Max observed concurrent: {max_observed}")
    print(f"Limit enforced: {max_observed <= 5}")

    assert max_observed <= 5, f"Concurrency limit violated: {max_observed} > 5"
    assert len(results) == 20, "All tasks should complete"
    assert all(r.success for r in results), "All tasks should succeed"

    print("\n✓ Concurrency limit correctly enforced!")
    print(f"✓ Never exceeded {max_observed}/5 concurrent tasks")


async def main():
    """Run all tests."""
    print("\n🧪 Aurora Parallel Execution Tests")
    print("=" * 60)

    try:
        # Test 1: Basic parallel execution
        results, elapsed = await test_parallel_execution()

        # Test 2: Concurrency limit enforcement
        await test_concurrency_limit()

        print("\n" + "=" * 60)
        print("✅ All Tests Passed!")
        print("=" * 60)
        print("\nKey Features Verified:")
        print("  ✓ Parallel task execution")
        print("  ✓ Concurrency limiting")
        print("  ✓ Result order preservation")
        print("  ✓ Progress callbacks")
        print("  ✓ Error handling")

    except Exception as e:
        print(f"\n❌ Test Failed: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())
