#!/usr/bin/env python3
"""Example: Real-time agent execution monitoring with heartbeat.

Demonstrates:
1. Creating heartbeat emitters for agent tracking
2. Subscribing to real-time events
3. Using ProgressUI for live display
4. Monitoring health and timeouts
5. Multi-agent concurrent monitoring
"""

import asyncio

from rich.console import Console

from aurora_cli.progress_ui import MultiAgentProgressUI, ProgressUI
from aurora_spawner.heartbeat import (
    HeartbeatEventType,
    create_heartbeat_emitter,
    create_heartbeat_monitor,
)
from aurora_spawner.models import SpawnTask
from aurora_spawner.spawner import spawn_parallel


async def example_single_agent_monitoring():
    """Monitor a single agent execution with live UI."""
    console = Console()
    console.print("[bold cyan]Example: Single Agent Monitoring[/]")

    # Create emitter
    emitter = create_heartbeat_emitter("task-001")

    # Create monitor for timeout detection
    create_heartbeat_monitor(emitter, timeout=60)

    # Create UI
    ui = ProgressUI(console=console)

    # Subscribe UI to emitter events
    emitter.subscribe(ui.handle_event)

    # Simulate execution with events
    async def simulate_execution():
        emitter.emit(HeartbeatEventType.STARTED, agent_id="test-agent", message="Spawning...")
        await asyncio.sleep(1)

        for i in range(10):
            emitter.emit(
                HeartbeatEventType.STDOUT,
                agent_id="test-agent",
                message=f"Processing step {i+1}",
                bytes=1024,
            )
            await asyncio.sleep(0.5)

        emitter.emit(HeartbeatEventType.COMPLETED, agent_id="test-agent", message="Task completed")

    # Run simulation and monitoring concurrently
    ui_task = asyncio.create_task(ui.monitor_emitter(emitter))
    exec_task = asyncio.create_task(simulate_execution())

    # Wait for execution
    await exec_task
    await asyncio.sleep(1)
    ui.stop()
    await ui_task

    # Show summary
    summary = ui.get_summary()
    console.print(f"\n[green]Summary:[/] {summary}")


async def example_multi_agent_parallel():
    """Monitor multiple agents executing in parallel."""
    console = Console()
    console.print("\n[bold cyan]Example: Multi-Agent Parallel Execution[/]")

    # Create tasks
    tasks = [
        SpawnTask(prompt="Analyze code", agent="analyzer", timeout=30),
        SpawnTask(prompt="Generate tests", agent="test-generator", timeout=30),
        SpawnTask(prompt="Review security", agent="security-auditor", timeout=30),
    ]

    # Create emitters
    emitters = {}
    for i, task in enumerate(tasks):
        task_id = f"task-{i:03d}"
        emitter = create_heartbeat_emitter(task_id)
        emitters[task_id] = emitter

    # Create multi-agent UI
    ui = MultiAgentProgressUI(console=console)
    for task_id, emitter in emitters.items():
        ui.add_emitter(task_id, emitter)

    # Start monitoring
    ui_task = asyncio.create_task(ui.monitor())

    # Execute tasks with heartbeat tracking
    # Note: In real usage, pass heartbeat_emitter to spawn()
    results = await spawn_parallel(tasks, max_concurrent=3)

    await asyncio.sleep(1)
    ui.stop()
    await ui_task

    # Show results
    success_count = sum(1 for r in results if r.success)
    console.print(f"\n[green]Completed:[/] {success_count}/{len(tasks)}")


async def example_timeout_detection():
    """Demonstrate timeout and activity monitoring."""
    console = Console()
    console.print("\n[bold cyan]Example: Timeout Detection[/]")

    # Create emitter and monitor (short timeout for demo)
    emitter = create_heartbeat_emitter("timeout-test")
    monitor = create_heartbeat_monitor(emitter, timeout=10)

    # Simulate slow execution
    async def slow_execution():
        emitter.emit(HeartbeatEventType.STARTED, agent_id="slow-agent", message="Starting...")
        await asyncio.sleep(3)

        # Some activity
        emitter.emit(
            HeartbeatEventType.STDOUT, agent_id="slow-agent", message="Working...", bytes=512
        )
        await asyncio.sleep(8)

        # This will trigger timeout
        console.print("[yellow]Task exceeded timeout...[/]")

    # Monitor health
    async def check_health():
        while True:
            healthy, reason = monitor.check_health()
            if not healthy:
                console.print(f"[red]Health check failed:[/] {reason}")
                emitter.emit(
                    HeartbeatEventType.KILLED, agent_id="slow-agent", message=f"Killed: {reason}"
                )
                break
            await asyncio.sleep(1)

    exec_task = asyncio.create_task(slow_execution())
    health_task = asyncio.create_task(check_health())

    await asyncio.gather(exec_task, health_task)


async def example_event_streaming():
    """Stream and filter heartbeat events."""
    console = Console()
    console.print("\n[bold cyan]Example: Event Streaming[/]")

    emitter = create_heartbeat_emitter("stream-test")

    # Emit various events
    async def emit_events():
        events = [
            (HeartbeatEventType.STARTED, "Agent started"),
            (HeartbeatEventType.STDOUT, "Line 1"),
            (HeartbeatEventType.STDOUT, "Line 2"),
            (HeartbeatEventType.PROGRESS, "50% complete"),
            (HeartbeatEventType.STDOUT, "Line 3"),
            (HeartbeatEventType.COMPLETED, "Done"),
        ]

        for event_type, message in events:
            emitter.emit(event_type, agent_id="streamer", message=message)
            await asyncio.sleep(0.5)

    # Stream and filter events
    async def stream_events():
        seen = 0
        async for event in emitter.stream(poll_interval=0.1):
            # Filter for STDOUT only
            if event.event_type == HeartbeatEventType.STDOUT:
                console.print(f"[dim]Output:[/] {event.message}")

            seen += 1
            if seen >= 6:
                break

    await asyncio.gather(emit_events(), stream_events())


async def example_health_monitoring_api():
    """Use heartbeat for health monitoring API."""
    console = Console()
    console.print("\n[bold cyan]Example: Health Monitoring API[/]")

    emitter = create_heartbeat_emitter("health-api-test")

    # Emit some events
    emitter.emit(HeartbeatEventType.STARTED, agent_id="api-agent", message="Starting")
    await asyncio.sleep(0.5)
    emitter.emit(HeartbeatEventType.STDOUT, agent_id="api-agent", message="Output", bytes=2048)

    # Check health metrics
    console.print(f"[cyan]Elapsed:[/] {emitter.seconds_since_start():.2f}s")
    console.print(f"[cyan]Since activity:[/] {emitter.seconds_since_activity():.2f}s")
    console.print(f"[cyan]Event count:[/] {len(emitter.get_all_events())}")

    # Get latest event
    latest = emitter.get_latest_event()
    if latest:
        console.print(f"[cyan]Latest:[/] {latest.event_type.value} - {latest.message}")


async def main():
    """Run all examples."""
    console = Console()

    try:
        await example_single_agent_monitoring()
        await example_multi_agent_parallel()
        await example_timeout_detection()
        await example_event_streaming()
        await example_health_monitoring_api()

        console.print("\n[bold green]All examples completed![/]")

    except KeyboardInterrupt:
        console.print("\n[yellow]Examples interrupted[/]")


if __name__ == "__main__":
    asyncio.run(main())
