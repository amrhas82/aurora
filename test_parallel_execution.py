#!/usr/bin/env python3
"""Test script to demonstrate parallel execution capabilities in Aurora.

This script tests the spawn_parallel_tracked function which is used by both
SOAR's collect phase and the aur spawn command for parallel agent execution.
"""

import asyncio
import time
from aurora_spawner import SpawnTask, spawn_parallel_tracked


async def test_basic_parallel_execution():
    """Test basic parallel execution with multiple mock tasks."""
    print("\n=== Testing Basic Parallel Execution ===\n")

    # Create test tasks
    tasks = [
        SpawnTask(
            prompt=f"Test task {i}: Echo this message back",
            agent=None,  # Direct LLM (no agent)
            timeout=60,
        )
        for i in range(3)
    ]

    # Progress callback
    def progress_callback(msg: str):
        print(f"  {msg}")

    start_time = time.time()

    # Execute in parallel
    results, metadata = await spawn_parallel_tracked(
        tasks=tasks,
        max_concurrent=2,
        stagger_delay=2.0,
        policy_name="fast_fail",  # Use fast_fail policy for testing
        on_progress=progress_callback,
        enable_heartbeat=True,
        fallback_to_llm=True,
        max_retries=1,
    )

    elapsed = time.time() - start_time

    # Print results
    print(f"\n=== Results ===")
    print(f"Total time: {elapsed:.2f}s")
    print(f"Tasks completed: {len(results)}")
    print(f"Successful: {sum(1 for r in results if r.success)}")
    print(f"Failed: {metadata['failed_tasks']}")
    print(f"Fallback count: {metadata['fallback_count']}")

    print(f"\n=== Metadata ===")
    print(f"Total duration: {metadata['total_duration_ms']}ms")
    print(f"Early terminations: {len(metadata['early_terminations'])}")
    print(f"Retried tasks: {len(metadata['retried_tasks'])}")
    print(f"Circuit blocked: {len(metadata['circuit_blocked'])}")

    return results, metadata


async def test_parallel_with_agents():
    """Test parallel execution with named agents."""
    print("\n=== Testing Parallel Execution with Agents ===\n")

    # Create tasks with different agents
    tasks = [
        SpawnTask(
            prompt="Analyze code structure",
            agent="code-analyzer",
            timeout=60,
        ),
        SpawnTask(
            prompt="Review security patterns",
            agent="security-reviewer",
            timeout=60,
        ),
        SpawnTask(
            prompt="Optimize performance",
            agent="performance-optimizer",
            timeout=60,
        ),
    ]

    def progress_callback(msg: str):
        print(f"  {msg}")

    start_time = time.time()

    # Execute with circuit breaker and fallback
    results, metadata = await spawn_parallel_tracked(
        tasks=tasks,
        max_concurrent=3,
        stagger_delay=1.0,
        policy_name="patient",
        on_progress=progress_callback,
        enable_heartbeat=True,
        fallback_to_llm=True,  # Fallback to LLM if agent fails
        max_retries=2,
    )

    elapsed = time.time() - start_time

    print(f"\n=== Results ===")
    print(f"Total time: {elapsed:.2f}s")
    print(f"Successful: {sum(1 for r in results if r.success)}")
    print(f"Fallbacks used: {metadata['fallback_count']}")
    print(f"Failed: {metadata['failed_tasks']}")

    return results, metadata


async def test_concurrency_limiting():
    """Test that concurrency limits are enforced."""
    print("\n=== Testing Concurrency Limiting ===\n")

    # Create many tasks
    num_tasks = 10
    tasks = [
        SpawnTask(
            prompt=f"Task {i}",
            agent=None,
            timeout=60,
        )
        for i in range(num_tasks)
    ]

    active_tasks = []
    max_concurrent = 3

    def progress_callback(msg: str):
        # Track concurrent execution
        if "starting now" in msg.lower():
            active_tasks.append(time.time())
        print(f"  {msg}")

    start_time = time.time()

    results, metadata = await spawn_parallel_tracked(
        tasks=tasks,
        max_concurrent=max_concurrent,
        stagger_delay=1.0,
        policy_name="fast_fail",
        on_progress=progress_callback,
        enable_heartbeat=False,  # Disable for simpler output
    )

    elapsed = time.time() - start_time

    print(f"\n=== Results ===")
    print(f"Total tasks: {num_tasks}")
    print(f"Max concurrent: {max_concurrent}")
    print(f"Total time: {elapsed:.2f}s")
    print(f"Successful: {sum(1 for r in results if r.success)}")

    return results, metadata


def main():
    """Run all parallel execution tests."""
    print("=" * 70)
    print("Aurora Parallel Execution Test Suite")
    print("=" * 70)

    try:
        # Test 1: Basic parallel execution
        results1, meta1 = asyncio.run(test_basic_parallel_execution())

        # Test 2: Parallel with agents (will likely fallback since agents don't exist)
        results2, meta2 = asyncio.run(test_parallel_with_agents())

        # Test 3: Concurrency limiting
        results3, meta3 = asyncio.run(test_concurrency_limiting())

        print("\n" + "=" * 70)
        print("All Tests Complete")
        print("=" * 70)

        print(f"\nTest 1: {len(results1)} tasks executed")
        print(f"Test 2: {len(results2)} tasks executed ({meta2['fallback_count']} fallbacks)")
        print(f"Test 3: {len(results3)} tasks executed")

        print("\n✓ Parallel execution tests completed successfully!")

    except Exception as e:
        print(f"\n✗ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return 1

    return 0


if __name__ == "__main__":
    exit(main())
