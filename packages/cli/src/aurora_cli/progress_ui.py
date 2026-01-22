"""Real-time progress UI for agent execution monitoring.

Displays live heartbeat events from spawned agents with status indicators,
progress bars, and execution timeline.
"""

import asyncio
import time
from dataclasses import dataclass
from typing import Any

from rich.console import Console
from rich.live import Live
from rich.table import Table
from rich.text import Text

from aurora_spawner.heartbeat import HeartbeatEmitter, HeartbeatEvent, HeartbeatEventType


@dataclass
class AgentStatus:
    """Track status of a single agent execution."""

    task_id: str
    agent_id: str
    state: str = "idle"
    start_time: float | None = None
    last_activity: float | None = None
    output_bytes: int = 0
    error_bytes: int = 0
    events_count: int = 0
    message: str | None = None


class ProgressUI:
    """Real-time progress display for agent execution."""

    def __init__(self, console: Console | None = None):
        """Initialize progress UI.

        Args:
            console: Rich console instance (creates default if None)

        """
        self.console = console or Console()
        self.agents: dict[str, AgentStatus] = {}
        self._live: Live | None = None
        self._running = False

    def _get_state_icon(self, state: str) -> tuple[str, str]:
        """Get icon and color for state.

        Args:
            state: Agent state

        Returns:
            (icon, color) tuple

        """
        icons = {
            "idle": ("⏸", "dim"),
            "started": ("▶", "cyan"),
            "running": ("⚙", "blue"),
            "progress": ("📊", "yellow"),
            "completed": ("✓", "green"),
            "failed": ("✗", "red"),
            "killed": ("🔪", "red"),
            "warning": ("⚠", "yellow"),
        }
        return icons.get(state, ("?", "white"))

    def _format_elapsed(self, seconds: float) -> str:
        """Format elapsed time as human-readable string.

        Args:
            seconds: Elapsed seconds

        Returns:
            Formatted string (e.g., "2m 30s")

        """
        if seconds < 60:
            return f"{seconds:.1f}s"
        minutes = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{minutes}m {secs:02d}s"

    def _build_table(self) -> Table:
        """Build Rich table with current agent statuses.

        Returns:
            Rich Table object

        """
        table = Table(title="Agent Execution Monitor", expand=True)
        table.add_column("Agent", style="cyan", no_wrap=True)
        table.add_column("Status", style="bold")
        table.add_column("Elapsed", justify="right")
        table.add_column("Output", justify="right")
        table.add_column("Message", overflow="fold")

        now = time.time()
        for agent_id in sorted(self.agents.keys()):
            status = self.agents[agent_id]
            icon, color = self._get_state_icon(status.state)

            # Format elapsed time
            elapsed = ""
            if status.start_time:
                elapsed_secs = now - status.start_time
                elapsed = self._format_elapsed(elapsed_secs)

            # Format output size
            output_info = ""
            if status.output_bytes > 0:
                kb = status.output_bytes / 1024
                output_info = f"{kb:.1f}KB"

            # Format message
            message = status.message or ""
            if len(message) > 60:
                message = message[:57] + "..."

            # Build status text
            status_text = Text()
            status_text.append(icon + " ", style=color)
            status_text.append(status.state, style=color)

            table.add_row(agent_id, status_text, elapsed, output_info, message)

        return table

    def handle_event(self, event: HeartbeatEvent) -> None:
        """Handle incoming heartbeat event.

        Args:
            event: Heartbeat event to process

        """
        agent_id = event.agent_id or "llm"

        # Initialize status if first event
        if agent_id not in self.agents:
            self.agents[agent_id] = AgentStatus(
                task_id=event.task_id,
                agent_id=agent_id,
                start_time=event.timestamp,
            )

        status = self.agents[agent_id]
        status.events_count += 1
        status.message = event.message

        # Update state based on event type
        if event.event_type == HeartbeatEventType.STARTED:
            status.state = "started"
            status.start_time = event.timestamp
        elif event.event_type == HeartbeatEventType.STDOUT:
            status.state = "running"
            status.last_activity = event.timestamp
            status.output_bytes += event.metadata.get("bytes", 0)
        elif event.event_type == HeartbeatEventType.STDERR:
            status.state = "running"
            status.error_bytes += event.metadata.get("bytes", 0)
        elif event.event_type == HeartbeatEventType.PROGRESS:
            status.state = "progress"
            status.last_activity = event.timestamp
        elif event.event_type == HeartbeatEventType.TIMEOUT_WARNING:
            status.state = "warning"
        elif event.event_type == HeartbeatEventType.COMPLETED:
            status.state = "completed"
        elif event.event_type == HeartbeatEventType.FAILED:
            status.state = "failed"
        elif event.event_type == HeartbeatEventType.KILLED:
            status.state = "killed"

    async def monitor_emitter(self, emitter: HeartbeatEmitter, poll_interval: float = 0.2) -> None:
        """Monitor heartbeat emitter and update display.

        Args:
            emitter: Heartbeat emitter to monitor
            poll_interval: Seconds between display updates

        """
        self._running = True

        # Subscribe to real-time events
        emitter.subscribe(self.handle_event)

        with Live(self._build_table(), console=self.console, refresh_per_second=4) as live:
            self._live = live
            try:
                while self._running:
                    live.update(self._build_table())
                    await asyncio.sleep(poll_interval)
            finally:
                self._live = None

    def stop(self) -> None:
        """Stop monitoring."""
        self._running = False

    def get_summary(self) -> dict[str, Any]:
        """Get execution summary statistics.

        Returns:
            Dictionary with counts and timing

        """
        total = len(self.agents)
        completed = sum(1 for a in self.agents.values() if a.state == "completed")
        failed = sum(1 for a in self.agents.values() if a.state in ("failed", "killed"))
        running = sum(1 for a in self.agents.values() if a.state in ("running", "progress"))

        return {
            "total": total,
            "completed": completed,
            "failed": failed,
            "running": running,
            "total_output_bytes": sum(a.output_bytes for a in self.agents.values()),
            "total_events": sum(a.events_count for a in self.agents.values()),
        }


class MultiAgentProgressUI:
    """Progress UI for monitoring multiple agents simultaneously."""

    def __init__(self, console: Console | None = None):
        """Initialize multi-agent progress UI.

        Args:
            console: Rich console instance

        """
        self.console = console or Console()
        self.emitters: dict[str, HeartbeatEmitter] = {}
        self.statuses: dict[str, AgentStatus] = {}
        self._live: Live | None = None
        self._running = False

    def add_emitter(self, task_id: str, emitter: HeartbeatEmitter) -> None:
        """Add heartbeat emitter to monitor.

        Args:
            task_id: Unique task identifier
            emitter: Heartbeat emitter to monitor

        """
        self.emitters[task_id] = emitter
        # Subscribe to events
        emitter.subscribe(lambda event: self._handle_event(task_id, event))

    def _handle_event(self, task_id: str, event: HeartbeatEvent) -> None:
        """Handle event from any emitter.

        Args:
            task_id: Task identifier
            event: Heartbeat event

        """
        agent_id = event.agent_id or "llm"
        key = f"{task_id}:{agent_id}"

        if key not in self.statuses:
            self.statuses[key] = AgentStatus(
                task_id=task_id,
                agent_id=agent_id,
                start_time=event.timestamp,
            )

        status = self.statuses[key]
        status.events_count += 1
        status.message = event.message

        # Update state
        if event.event_type == HeartbeatEventType.STARTED:
            status.state = "started"
        elif event.event_type == HeartbeatEventType.STDOUT:
            status.state = "running"
            status.output_bytes += event.metadata.get("bytes", 0)
        elif event.event_type == HeartbeatEventType.COMPLETED:
            status.state = "completed"
        elif event.event_type == HeartbeatEventType.FAILED:
            status.state = "failed"
        elif event.event_type == HeartbeatEventType.KILLED:
            status.state = "killed"

    def _build_table(self) -> Table:
        """Build Rich table with all agent statuses.

        Returns:
            Rich Table object

        """
        table = Table(title="Multi-Agent Execution Monitor", expand=True)
        table.add_column("Task ID", style="dim")
        table.add_column("Agent", style="cyan")
        table.add_column("Status", style="bold")
        table.add_column("Elapsed", justify="right")
        table.add_column("Events", justify="right")

        now = time.time()
        for key in sorted(self.statuses.keys()):
            status = self.statuses[key]

            # State icon
            icons = {
                "started": "▶",
                "running": "⚙",
                "completed": "✓",
                "failed": "✗",
                "killed": "🔪",
            }
            icon = icons.get(status.state, "?")

            # Elapsed time
            elapsed = ""
            if status.start_time:
                elapsed_secs = now - status.start_time
                elapsed = f"{elapsed_secs:.1f}s"

            table.add_row(
                status.task_id[:8],
                status.agent_id,
                f"{icon} {status.state}",
                elapsed,
                str(status.events_count),
            )

        return table

    async def monitor(self, poll_interval: float = 0.2) -> None:
        """Monitor all emitters and display progress.

        Args:
            poll_interval: Seconds between display updates

        """
        self._running = True

        with Live(self._build_table(), console=self.console, refresh_per_second=4) as live:
            self._live = live
            try:
                while self._running:
                    live.update(self._build_table())
                    await asyncio.sleep(poll_interval)
            finally:
                self._live = None

    def stop(self) -> None:
        """Stop monitoring."""
        self._running = False
