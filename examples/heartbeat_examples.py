"""Comprehensive examples of Aurora's heartbeat monitoring system.

This module demonstrates various heartbeat patterns for agent execution monitoring.
"""

import asyncio
import logging
from typing import Any

from aurora_spawner import (
    HeartbeatEventType,
    create_heartbeat_emitter,
    create_heartbeat_monitor,
    spawn,
    spawn_parallel,
    spawn_with_retry_and_fallback,
)
from aurora_spawner.models import SpawnTask

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def example_basic_heartbeat():
    """Example 1: Basic heartbeat emission and event inspection."""
    print("\n=== Example 1: Basic Heartbeat ===\n")

    # Create emitter
    task_id = "basic-task-001"
    emitter = create_heartbeat_emitter(task_id)

    # Create task
    task = SpawnTask(
        prompt="Write a simple Python function to calculate factorial",
        agent=None,  # Use LLM directly
        timeout=60,
    )

    # Spawn with heartbeat
    print(f"Executing task: {task_id}")
    result = await spawn(task, heartbeat_emitter=emitter)

    # Inspect events
    events = emitter.get_all_events()
    print(f"\nReceived {len(events)} events:")
    for event in events:
        elapsed = event.elapsed_since(emitter._start_time or 0)
        print(f"  [{elapsed:6.2f}s] {event.event_type.value:15s} | {event.message}")

    print(f"\nTask {'succeeded' if result.success else 'failed'}")
    print(f"Execution time: {emitter.seconds_since_start():.1f}s")


async def example_realtime_subscription():
    """Example 2: Real-time event subscription with live updates."""
    print("\n=== Example 2: Real-Time Subscription ===\n")

    emitter = create_heartbeat_emitter("realtime-task-002")

    # Subscribe to events
    def on_event(event):
        elapsed = event.elapsed_since(emitter._start_time or 0) if emitter._start_time else 0
        prefix = {
            HeartbeatEventType.STARTED: "🚀",
            HeartbeatEventType.STDOUT: "📝",
            HeartbeatEventType.STDERR: "⚠️",
            HeartbeatEventType.PROGRESS: "⏳",
            HeartbeatEventType.COMPLETED: "✅",
            HeartbeatEventType.FAILED: "❌",
            HeartbeatEventType.KILLED: "🛑",
        }.get(event.event_type, "•")

        print(f"{prefix} [{elapsed:6.2f}s] {event.event_type.value:15s} | {event.message}")

    emitter.subscribe(on_event)

    # Execute task
    task = SpawnTask(
        prompt="List the files in the current directory and explain each one",
        agent=None,
        timeout=120,
    )

    print("Monitoring execution in real-time...\n")
    result = await spawn(task, heartbeat_emitter=emitter)

    print(f"\n{'Success!' if result.success else 'Failed.'}")


async def example_timeout_monitoring():
    """Example 3: Health monitoring with timeout detection."""
    print("\n=== Example 3: Timeout Monitoring ===\n")

    emitter = create_heartbeat_emitter("timeout-task-003")
    monitor = create_heartbeat_monitor(emitter, timeout=60)

    task = SpawnTask(
        prompt="Perform a comprehensive security audit of the codebase",
        agent="security-auditor",
        timeout=60,
    )

    print("Starting monitored execution...\n")

    # Start execution in background
    exec_task = asyncio.create_task(spawn(task, heartbeat_emitter=emitter))

    # Monitor until complete or timeout
    success, error = await monitor.monitor_until_complete(check_interval=2.0)

    if not success:
        print(f"❌ Execution monitoring failed: {error}")
        exec_task.cancel()
        try:
            await exec_task
        except asyncio.CancelledError:
            pass
        return

    # Wait for result
    result = await exec_task
    print(f"✅ Execution completed successfully")


async def example_health_checks():
    """Example 4: Periodic health checks during execution."""
    print("\n=== Example 4: Periodic Health Checks ===\n")

    emitter = create_heartbeat_emitter("health-task-004")
    monitor = create_heartbeat_monitor(
        emitter, total_timeout=300, activity_timeout=120, warning_threshold=0.8
    )

    task = SpawnTask(
        prompt="Refactor the authentication module for better security",
        agent="refactoring-specialist",
        timeout=300,
    )

    print("Starting execution with periodic health checks...\n")

    # Start execution
    exec_task = asyncio.create_task(spawn(task, heartbeat_emitter=emitter))

    # Periodic health checks
    check_count = 0
    while not exec_task.done():
        healthy, reason = monitor.check_health()

        check_count += 1
        elapsed = emitter.seconds_since_start()
        idle = emitter.seconds_since_activity()

        print(f"Health check #{check_count}: ", end="")
        if healthy:
            print(
                f"✓ Healthy | Runtime: {elapsed:.1f}s | Idle: {idle:.1f}s"
            )
        else:
            print(f"✗ Unhealthy - {reason}")
            exec_task.cancel()
            break

        await asyncio.sleep(5)

    # Get result
    try:
        result = await exec_task
        print(f"\n{'✅' if result.success else '❌'} Execution finished")
    except asyncio.CancelledError:
        print("\n🛑 Execution cancelled due to health check failure")


async def example_event_streaming():
    """Example 5: Streaming events as async iterator."""
    print("\n=== Example 5: Event Streaming ===\n")

    emitter = create_heartbeat_emitter("stream-task-005")

    task = SpawnTask(
        prompt="Generate unit tests for the spawner module",
        agent="test-generator",
        timeout=180,
    )

    print("Streaming events in real-time...\n")

    # Start execution
    exec_task = asyncio.create_task(spawn(task, heartbeat_emitter=emitter))

    # Stream events as they arrive
    event_count = 0
    async for event in emitter.stream(poll_interval=0.1):
        event_count += 1
        elapsed = event.elapsed_since(emitter._start_time or 0) if emitter._start_time else 0

        # Format based on event type
        if event.event_type == HeartbeatEventType.STDOUT:
            bytes_count = event.metadata.get("bytes", 0)
            print(f"📝 [{elapsed:6.2f}s] Output received: {bytes_count} bytes")
        elif event.event_type == HeartbeatEventType.STDERR:
            bytes_count = event.metadata.get("bytes", 0)
            print(f"⚠️  [{elapsed:6.2f}s] Error output: {bytes_count} bytes")
        elif event.event_type in (
            HeartbeatEventType.COMPLETED,
            HeartbeatEventType.FAILED,
            HeartbeatEventType.KILLED,
        ):
            print(f"🏁 [{elapsed:6.2f}s] {event.event_type.value}: {event.message}")
            break
        else:
            print(f"•  [{elapsed:6.2f}s] {event.event_type.value}: {event.message}")

    result = await exec_task
    print(f"\nStreamed {event_count} events")
    print(f"{'✅' if result.success else '❌'} Execution finished")


async def example_activity_tracking():
    """Example 6: Activity metrics and idle detection."""
    print("\n=== Example 6: Activity Tracking ===\n")

    emitter = create_heartbeat_emitter("activity-task-006")

    task = SpawnTask(
        prompt="Analyze code complexity and suggest improvements",
        agent="code-analyzer",
        timeout=240,
    )

    print("Tracking execution activity...\n")

    # Start execution
    exec_task = asyncio.create_task(spawn(task, heartbeat_emitter=emitter))

    # Monitor activity
    last_report = 0
    while not exec_task.done():
        elapsed = emitter.seconds_since_start()
        idle = emitter.seconds_since_activity()

        # Report every 10 seconds
        if elapsed - last_report >= 10:
            status = "⚡ Active" if idle < 30 else "💤 Idle"
            print(f"{status} | Runtime: {elapsed:.1f}s | Idle: {idle:.1f}s")
            last_report = elapsed

        await asyncio.sleep(2)

    result = await exec_task
    total_time = emitter.seconds_since_start()
    print(f"\n{'✅' if result.success else '❌'} Completed in {total_time:.1f}s")


async def example_custom_metadata():
    """Example 7: Custom event metadata for domain-specific tracking."""
    print("\n=== Example 7: Custom Metadata ===\n")

    emitter = create_heartbeat_emitter("metadata-task-007")

    # Subscribe to extract custom metadata
    def on_progress_event(event):
        if event.event_type == HeartbeatEventType.PROGRESS:
            current = event.metadata.get("file_count", 0)
            total = event.metadata.get("total_files", 0)
            current_file = event.metadata.get("current_file", "unknown")

            if total > 0:
                percent = (current / total) * 100
                print(f"📊 Progress: {current}/{total} ({percent:.0f}%) - {current_file}")

    emitter.subscribe(on_progress_event)

    # Simulate task with custom progress events
    task = SpawnTask(
        prompt="Review all Python files and check for common issues",
        agent="code-reviewer",
        timeout=180,
    )

    print("Executing with custom progress tracking...\n")

    # Note: In real usage, these events would be emitted by the agent
    # Here we demonstrate the structure
    result = await spawn(task, heartbeat_emitter=emitter)

    print(f"\n{'✅' if result.success else '❌'} Review completed")


async def example_parallel_with_heartbeats():
    """Example 8: Parallel execution with individual heartbeat tracking."""
    print("\n=== Example 8: Parallel Execution Monitoring ===\n")

    # Create tasks
    tasks = [
        SpawnTask(prompt=f"Analyze module {i}", agent="analyzer", timeout=60)
        for i in range(3)
    ]

    # Create emitters for each task
    emitters = [create_heartbeat_emitter(f"parallel-task-{i}") for i in range(len(tasks))]

    # Subscribe to all emitters
    for i, emitter in enumerate(emitters):
        task_id = f"Task {i + 1}"

        def make_subscriber(tid):
            def subscriber(event):
                if event.event_type in (
                    HeartbeatEventType.STARTED,
                    HeartbeatEventType.COMPLETED,
                    HeartbeatEventType.FAILED,
                ):
                    print(f"[{tid}] {event.event_type.value}: {event.message}")

            return subscriber

        emitter.subscribe(make_subscriber(task_id))

    print("Starting parallel execution with individual monitoring...\n")

    # Note: Current spawn_parallel doesn't support per-task emitters
    # This is a future enhancement - for now we show the structure
    print("⚠️  Per-task heartbeats in spawn_parallel is a planned enhancement\n")

    # Workaround: Execute tasks individually but concurrently
    async def spawn_with_emitter(task, emitter):
        return await spawn(task, heartbeat_emitter=emitter)

    results = await asyncio.gather(
        *[spawn_with_emitter(task, emitter) for task, emitter in zip(tasks, emitters)]
    )

    # Report summary
    print("\n📊 Execution Summary:")
    for i, (result, emitter) in enumerate(zip(results, emitters)):
        elapsed = emitter.seconds_since_start()
        status = "✅" if result.success else "❌"
        print(f"  {status} Task {i + 1}: {elapsed:.1f}s")


async def example_retry_with_monitoring():
    """Example 9: Retry logic with heartbeat monitoring."""
    print("\n=== Example 9: Retry with Heartbeat Monitoring ===\n")

    emitter = create_heartbeat_emitter("retry-task-009")

    task = SpawnTask(
        prompt="Deploy the application to staging environment",
        agent="deployment-agent",  # May fail, will retry
        timeout=120,
    )

    def on_progress(attempt: int, max_attempts: int, status: str):
        print(f"🔄 Attempt {attempt}/{max_attempts}: {status}")

    print("Starting execution with retry monitoring...\n")

    # Note: Need to add heartbeat_emitter parameter to spawn_with_retry_and_fallback
    result = await spawn_with_retry_and_fallback(
        task,
        on_progress=on_progress,
        max_retries=2,
        fallback_to_llm=True,
        # heartbeat_emitter=emitter,  # Future enhancement
    )

    if result.fallback:
        print(f"\n⚠️  Fell back to LLM after {result.retry_count} attempts")
    elif result.retry_count > 0:
        print(f"\n✅ Succeeded on attempt {result.retry_count + 1}")
    else:
        print(f"\n✅ Succeeded on first attempt")

    print(f"{'✅' if result.success else '❌'} Execution finished")


async def main():
    """Run all examples."""
    examples = [
        ("Basic Heartbeat", example_basic_heartbeat),
        ("Real-Time Subscription", example_realtime_subscription),
        ("Timeout Monitoring", example_timeout_monitoring),
        ("Periodic Health Checks", example_health_checks),
        ("Event Streaming", example_event_streaming),
        ("Activity Tracking", example_activity_tracking),
        ("Custom Metadata", example_custom_metadata),
        ("Parallel Execution", example_parallel_with_heartbeats),
        ("Retry with Monitoring", example_retry_with_monitoring),
    ]

    print("=" * 60)
    print("Aurora Heartbeat Monitoring Examples")
    print("=" * 60)

    for name, example_func in examples:
        try:
            await example_func()
        except Exception as e:
            print(f"\n❌ Example '{name}' failed: {e}\n")
        await asyncio.sleep(1)

    print("\n" + "=" * 60)
    print("All examples completed")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
