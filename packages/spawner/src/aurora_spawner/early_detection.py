"""Early failure detection system with non-blocking health checks.

Provides configurable early detection mechanisms that run independently
of the main execution loop, allowing detection without waiting for full timeout.

Features:
- Non-blocking async health checks
- Configurable detection thresholds
- Pattern-based error detection
- Resource usage monitoring
- Stall detection (no output progress)
"""

import asyncio
import logging
import time
from dataclasses import dataclass
from typing import Callable


logger = logging.getLogger(__name__)


@dataclass
class EarlyDetectionConfig:
    """Configuration for early failure detection.

    Attributes:
        enabled: Enable early detection (default: True)
        check_interval: Interval between health checks in seconds (default: 2.0)
        stall_threshold: No output/activity threshold in seconds (default: 15.0)
        min_output_bytes: Minimum output bytes before considering stalled (default: 100)
        stderr_pattern_check: Enable stderr pattern matching (default: True)
        memory_limit_mb: Optional memory limit for process (default: None)
        callback_on_detection: Optional callback when failure detected

    """

    enabled: bool = True
    check_interval: float = 5.0  # Check every 5 seconds
    stall_threshold: float = 120.0  # 120 seconds without output (match patient policy)
    min_output_bytes: int = 100  # Must have at least 100 bytes before stall check
    stderr_pattern_check: bool = True
    memory_limit_mb: int | None = None  # Optional memory limit
    callback_on_detection: Callable[[str, str], None] | None = None
    terminate_on_stall: bool = False  # Let SpawnPolicy timeouts control termination


@dataclass
class ExecutionState:
    """Tracks execution state for early detection.

    Attributes:
        task_id: Unique task identifier
        agent_id: Agent being executed
        start_time: Execution start timestamp
        last_activity_time: Last time output was received
        stdout_size: Total stdout bytes received
        stderr_size: Total stderr bytes received
        last_stdout_size: Stdout size at last check
        last_stderr_size: Stderr size at last check
        consecutive_stalls: Count of consecutive stall detections
        terminated: Whether early termination was triggered
        termination_reason: Reason for termination

    """

    task_id: str
    agent_id: str
    start_time: float
    last_activity_time: float
    stdout_size: int = 0
    stderr_size: int = 0
    last_stdout_size: int = 0
    last_stderr_size: int = 0
    consecutive_stalls: int = 0
    terminated: bool = False
    termination_reason: str | None = None


class EarlyDetectionMonitor:
    """Non-blocking monitor for early failure detection.

    Runs health checks independently and signals early termination
    when failures are detected before timeout.
    """

    def __init__(self, config: EarlyDetectionConfig | None = None):
        """Initialize early detection monitor.

        Args:
            config: Configuration for detection behavior

        """
        self.config = config or EarlyDetectionConfig()
        self._executions: dict[str, ExecutionState] = {}
        self._monitor_task: asyncio.Task | None = None
        self._stop_event = asyncio.Event()
        self._lock = asyncio.Lock()

    async def start_monitoring(self) -> None:
        """Start non-blocking health check monitoring."""
        if not self.config.enabled:
            logger.debug("Early detection disabled")
            return

        if self._monitor_task is not None and not self._monitor_task.done():
            logger.debug("Early detection monitor already active")
            return

        self._stop_event.clear()
        self._monitor_task = asyncio.create_task(self._monitor_loop())
        logger.info(
            f"Early detection started: check_interval={self.config.check_interval}s, "
            f"stall_threshold={self.config.stall_threshold}s",
        )

    async def stop_monitoring(self) -> None:
        """Stop health check monitoring."""
        if self._monitor_task is None:
            return

        self._stop_event.set()
        try:
            await asyncio.wait_for(self._monitor_task, timeout=2.0)
        except asyncio.TimeoutError:
            logger.warning("Monitor stop timeout, cancelling task")
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass

        self._monitor_task = None
        logger.info("Early detection stopped")

    async def register_execution(
        self,
        task_id: str,
        agent_id: str,
    ) -> None:
        """Register execution for monitoring.

        Args:
            task_id: Unique task identifier
            agent_id: Agent being executed

        """
        if not self.config.enabled:
            return

        now = time.time()
        async with self._lock:
            self._executions[task_id] = ExecutionState(
                task_id=task_id,
                agent_id=agent_id,
                start_time=now,
                last_activity_time=now,
            )
        logger.debug(f"Registered execution: task_id={task_id}, agent_id={agent_id}")

    async def update_activity(
        self,
        task_id: str,
        stdout_size: int = 0,
        stderr_size: int = 0,
    ) -> None:
        """Update execution activity metrics.

        Args:
            task_id: Unique task identifier
            stdout_size: Current stdout size in bytes
            stderr_size: Current stderr size in bytes

        """
        if not self.config.enabled:
            return

        async with self._lock:
            state = self._executions.get(task_id)
            if state is None:
                return

            # Update activity time if output grew
            if stdout_size > state.stdout_size or stderr_size > state.stderr_size:
                state.last_activity_time = time.time()
                state.consecutive_stalls = 0  # Reset stall counter

            state.stdout_size = stdout_size
            state.stderr_size = stderr_size

    async def unregister_execution(self, task_id: str) -> None:
        """Remove execution from monitoring.

        Args:
            task_id: Unique task identifier

        """
        async with self._lock:
            self._executions.pop(task_id, None)

    async def should_terminate(self, task_id: str) -> tuple[bool, str | None]:
        """Check if execution should be terminated early.

        Args:
            task_id: Unique task identifier

        Returns:
            Tuple of (should_terminate, reason)

        """
        if not self.config.enabled:
            return False, None

        async with self._lock:
            state = self._executions.get(task_id)
            if state is None:
                return False, None

            return state.terminated, state.termination_reason

    async def _monitor_loop(self) -> None:
        """Background monitoring loop for health checks."""
        while not self._stop_event.is_set():
            try:
                await self._perform_health_checks()
            except Exception as e:
                logger.error(f"Health check error: {e}", exc_info=True)

            try:
                await asyncio.wait_for(self._stop_event.wait(), timeout=self.config.check_interval)
                break  # Stop event was set
            except asyncio.TimeoutError:
                pass  # Continue monitoring

    async def _perform_health_checks(self) -> None:
        """Perform health checks on all active executions."""
        now = time.time()
        executions_to_check = []

        async with self._lock:
            executions_to_check = list(self._executions.values())

        for state in executions_to_check:
            try:
                await self._check_execution(state, now)
            except Exception as e:
                logger.error(f"Health check failed for task {state.task_id}: {e}", exc_info=True)

    async def _check_execution(self, state: ExecutionState, now: float) -> None:
        """Check health of single execution.

        Args:
            state: Execution state to check
            now: Current timestamp

        """
        if state.terminated:
            return  # Already terminated

        elapsed = now - state.start_time
        time_since_activity = now - state.last_activity_time

        # Check for stall (no output progress)
        if await self._check_stall(state, time_since_activity):
            return  # Termination triggered

        # Check output size changes
        async with self._lock:
            output_grew = (
                state.stdout_size > state.last_stdout_size
                or state.stderr_size > state.last_stderr_size
            )
            state.last_stdout_size = state.stdout_size
            state.last_stderr_size = state.stderr_size

        # Log periodic health status
        logger.debug(
            f"Health check: task_id={state.task_id}, agent_id={state.agent_id}, "
            f"elapsed={elapsed:.1f}s, time_since_activity={time_since_activity:.1f}s, "
            f"stdout={state.stdout_size}b, stderr={state.stderr_size}b, "
            f"output_grew={output_grew}",
        )

    async def _check_stall(
        self,
        state: ExecutionState,
        time_since_activity: float,
    ) -> bool:
        """Check if execution is stalled (no output progress).

        Args:
            state: Execution state
            time_since_activity: Seconds since last activity

        Returns:
            True if termination was triggered, False otherwise

        """
        # Only check stall if we've received some output
        if state.stdout_size < self.config.min_output_bytes:
            return False

        # Check if stalled beyond threshold
        if time_since_activity > self.config.stall_threshold:
            state.consecutive_stalls += 1

            # Trigger termination after 2 consecutive stall detections
            if state.consecutive_stalls >= 2:
                reason = (
                    f"Stalled: no output for {time_since_activity:.1f}s "
                    f"({state.consecutive_stalls} checks)"
                )
                await self._trigger_termination(state, reason)
                return True

            # Log as debug since termination is typically disabled
            logger.debug(
                f"Stall check: task_id={state.task_id}, "
                f"idle={time_since_activity:.0f}s, checks={state.consecutive_stalls}",
            )

        return False

    async def _trigger_termination(self, state: ExecutionState, reason: str) -> None:
        """Trigger early termination for execution.

        Args:
            state: Execution state
            reason: Reason for termination

        """
        # Skip actual termination if disabled - just log debug
        if not self.config.terminate_on_stall:
            logger.debug(f"Stall detected (termination disabled): {reason}")
            return

        async with self._lock:
            if state.terminated:
                return  # Already terminated

            state.terminated = True
            state.termination_reason = reason

        logger.error(
            f"Early termination triggered: task_id={state.task_id}, "
            f"agent_id={state.agent_id}, reason={reason}",
        )

        # Invoke callback if configured
        if self.config.callback_on_detection:
            try:
                self.config.callback_on_detection(state.task_id, reason)
            except Exception as e:
                logger.error(f"Termination callback failed: {e}", exc_info=True)


# Global singleton instance
_global_monitor: EarlyDetectionMonitor | None = None


def get_early_detection_monitor() -> EarlyDetectionMonitor:
    """Get global early detection monitor singleton.

    Returns:
        Global EarlyDetectionMonitor instance

    """
    global _global_monitor
    if _global_monitor is None:
        _global_monitor = EarlyDetectionMonitor()
    return _global_monitor


def reset_early_detection_monitor(
    config: EarlyDetectionConfig | None = None,
) -> EarlyDetectionMonitor:
    """Reset global monitor with new configuration.

    Args:
        config: Optional new configuration

    Returns:
        Fresh EarlyDetectionMonitor instance

    """
    global _global_monitor
    if _global_monitor is not None:
        # Stop existing monitor if running
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                asyncio.create_task(_global_monitor.stop_monitoring())
        except RuntimeError:
            pass

    _global_monitor = EarlyDetectionMonitor(config)
    return _global_monitor
