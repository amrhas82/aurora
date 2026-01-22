"""Heartbeat mechanism for agent execution monitoring.

Provides real-time status tracking, progress signals, and health checks for
spawned agent processes through a thread-safe event stream.
"""

import asyncio
import threading
import time
from collections import deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, AsyncIterator, Callable


class HeartbeatEventType(Enum):
    """Types of heartbeat events."""

    STARTED = "started"  # Process spawned
    STDOUT = "stdout"  # Output received
    STDERR = "stderr"  # Error output received
    PROGRESS = "progress"  # Progress update
    TIMEOUT_WARNING = "timeout_warning"  # Approaching timeout
    COMPLETED = "completed"  # Process finished
    FAILED = "failed"  # Process failed
    KILLED = "killed"  # Process killed by monitor


@dataclass
class HeartbeatEvent:
    """Single heartbeat event with timestamp and metadata."""

    event_type: HeartbeatEventType
    timestamp: float
    task_id: str
    agent_id: str | None = None
    message: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def elapsed_since(self, start_time: float) -> float:
        """Get elapsed time since start in seconds."""
        return self.timestamp - start_time

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "event_type": self.event_type.value,
            "timestamp": self.timestamp,
            "task_id": self.task_id,
            "agent_id": self.agent_id,
            "message": self.message,
            "metadata": self.metadata,
        }


class HeartbeatEmitter:
    """Thread-safe heartbeat event emitter for agent execution.

    Collects events during execution and provides async iteration.
    Uses thread-safe queue for cross-thread event emission.
    """

    def __init__(self, task_id: str, buffer_size: int = 1000):
        """Initialize emitter.

        Args:
            task_id: Unique identifier for this execution
            buffer_size: Maximum events to buffer

        """
        self.task_id = task_id
        self.buffer_size = buffer_size
        self._queue: deque[HeartbeatEvent] = deque(maxlen=buffer_size)
        self._lock = threading.Lock()
        self._started = False
        self._start_time: float | None = None
        self._last_activity: float | None = None
        self._subscribers: list[Callable[[HeartbeatEvent], None]] = []

    def emit(
        self,
        event_type: HeartbeatEventType,
        agent_id: str | None = None,
        message: str | None = None,
        **metadata: Any,
    ) -> None:
        """Emit a heartbeat event (thread-safe).

        Args:
            event_type: Type of event
            agent_id: Optional agent identifier
            message: Optional message text
            **metadata: Additional metadata

        """
        timestamp = time.time()

        with self._lock:
            if not self._started:
                self._started = True
                self._start_time = timestamp

            # Track activity for timeout detection
            if event_type in (HeartbeatEventType.STDOUT, HeartbeatEventType.PROGRESS):
                self._last_activity = timestamp

            event = HeartbeatEvent(
                event_type=event_type,
                timestamp=timestamp,
                task_id=self.task_id,
                agent_id=agent_id,
                message=message,
                metadata=metadata,
            )

            self._queue.append(event)

            # Notify subscribers
            for subscriber in self._subscribers:
                try:
                    subscriber(event)
                except Exception:
                    pass  # Don't let subscriber errors break emission

    def subscribe(self, callback: Callable[[HeartbeatEvent], None]) -> None:
        """Subscribe to real-time events.

        Args:
            callback: Function called for each event (must be thread-safe)

        """
        with self._lock:
            self._subscribers.append(callback)

    def get_all_events(self) -> list[HeartbeatEvent]:
        """Get all buffered events (thread-safe).

        Returns:
            List of events in chronological order

        """
        with self._lock:
            return list(self._queue)

    def get_latest_event(self) -> HeartbeatEvent | None:
        """Get most recent event (thread-safe).

        Returns:
            Latest event or None if no events

        """
        with self._lock:
            return self._queue[-1] if self._queue else None

    def seconds_since_start(self) -> float:
        """Get seconds since first event.

        Returns:
            Elapsed seconds or 0.0 if not started

        """
        with self._lock:
            if not self._start_time:
                return 0.0
            return time.time() - self._start_time

    def seconds_since_activity(self) -> float:
        """Get seconds since last activity event.

        Returns:
            Seconds since activity or total runtime if no activity

        """
        with self._lock:
            if not self._last_activity:
                return self.seconds_since_start()
            return time.time() - self._last_activity

    async def stream(self, poll_interval: float = 0.1) -> AsyncIterator[HeartbeatEvent]:
        """Stream events as async iterator.

        Args:
            poll_interval: Seconds between polls

        Yields:
            HeartbeatEvent objects as they arrive

        """
        seen_count = 0
        while True:
            with self._lock:
                events = list(self._queue)

            # Yield new events
            for event in events[seen_count:]:
                yield event
                seen_count += 1

            await asyncio.sleep(poll_interval)


class HeartbeatMonitor:
    """Monitors heartbeat stream for timeout and health issues.

    Watches for:
    - Total timeout (no completion within limit)
    - Activity timeout (no stdout/progress for extended period)
    - Warning signals before timeout
    """

    def __init__(
        self,
        emitter: HeartbeatEmitter,
        total_timeout: int = 300,
        activity_timeout: int = 120,
        warning_threshold: float = 0.8,
    ):
        """Initialize monitor.

        Args:
            emitter: Heartbeat emitter to monitor
            total_timeout: Maximum total execution seconds
            activity_timeout: Maximum seconds without activity
            warning_threshold: Fraction of timeout before warning (0.0-1.0)

        """
        self.emitter = emitter
        self.total_timeout = total_timeout
        self.activity_timeout = activity_timeout
        self.warning_threshold = warning_threshold
        self._warned = False

    def check_health(self) -> tuple[bool, str | None]:
        """Check execution health.

        Returns:
            (is_healthy, reason) tuple

        """
        elapsed = self.emitter.seconds_since_start()
        idle = self.emitter.seconds_since_activity()

        # Check total timeout
        if elapsed > self.total_timeout:
            return False, f"Total timeout exceeded ({self.total_timeout}s)"

        # Check activity timeout
        if idle > self.activity_timeout:
            return False, f"No activity for {self.activity_timeout}s"

        # Emit warning if approaching timeout
        if not self._warned and elapsed > (self.total_timeout * self.warning_threshold):
            self._warned = True
            self.emitter.emit(
                HeartbeatEventType.TIMEOUT_WARNING,
                message=f"Approaching timeout: {elapsed:.1f}/{self.total_timeout}s",
            )

        return True, None

    async def monitor_until_complete(self, check_interval: float = 2.0) -> tuple[bool, str | None]:
        """Monitor execution until completion or timeout.

        Args:
            check_interval: Seconds between health checks

        Returns:
            (success, error_reason) tuple

        """
        while True:
            # Check for completion
            latest = self.emitter.get_latest_event()
            if latest and latest.event_type in (
                HeartbeatEventType.COMPLETED,
                HeartbeatEventType.FAILED,
                HeartbeatEventType.KILLED,
            ):
                return latest.event_type == HeartbeatEventType.COMPLETED, None

            # Check health
            healthy, reason = self.check_health()
            if not healthy:
                return False, reason

            await asyncio.sleep(check_interval)


def create_heartbeat_emitter(task_id: str) -> HeartbeatEmitter:
    """Factory function for creating heartbeat emitters.

    Args:
        task_id: Unique task identifier

    Returns:
        Configured HeartbeatEmitter instance

    """
    return HeartbeatEmitter(task_id=task_id)


def create_heartbeat_monitor(emitter: HeartbeatEmitter, timeout: int = 300) -> HeartbeatMonitor:
    """Factory function for creating heartbeat monitors.

    Args:
        emitter: Heartbeat emitter to monitor
        timeout: Maximum execution seconds

    Returns:
        Configured HeartbeatMonitor instance

    """
    return HeartbeatMonitor(
        emitter=emitter,
        total_timeout=timeout,
        activity_timeout=min(120, timeout // 2),  # Half of total or 120s
        warning_threshold=0.8,
    )
