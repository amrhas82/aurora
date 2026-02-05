"""Observability infrastructure for agent health monitoring.

Provides structured logging, metrics collection, and performance tracking
for agent execution, failure detection, and recovery.

Features proactive health checking with:
- Background monitoring thread for early failure detection
- Configurable check intervals and failure thresholds
- Process health verification (output activity, resource usage)
- Early termination triggers before timeout
"""

import logging
import threading
import time
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable


logger = logging.getLogger(__name__)


class FailureReason(Enum):
    """Categorization of agent failure reasons."""

    TIMEOUT = "timeout"
    ERROR_PATTERN = "error_pattern"
    NO_ACTIVITY = "no_activity"
    CIRCUIT_OPEN = "circuit_open"
    CRASH = "crash"
    KILLED = "killed"
    RATE_LIMIT = "rate_limit"
    UNKNOWN = "unknown"


@dataclass
class FailureEvent:
    """Records a single agent failure event."""

    agent_id: str
    task_id: str
    timestamp: float
    reason: FailureReason
    detection_latency: float  # Seconds from start to detection
    error_message: str | None = None
    retry_attempt: int = 0
    recovered: bool = False
    recovery_time: float | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class HealthMetrics:
    """Health monitoring metrics for an agent."""

    agent_id: str
    total_executions: int = 0
    successful_executions: int = 0
    failed_executions: int = 0
    total_execution_time: float = 0.0
    avg_execution_time: float = 0.0
    failure_rate: float = 0.0
    avg_detection_latency: float = 0.0
    recovery_rate: float = 0.0
    circuit_open_count: int = 0
    last_success_time: float | None = None
    last_failure_time: float | None = None
    proactive_checks: int = 0  # Number of proactive health checks performed
    early_detections: int = 0  # Failures detected proactively before timeout


@dataclass
class ProactiveHealthConfig:
    """Configuration for proactive health checking."""

    enabled: bool = True  # Enable metrics collection
    check_interval: float = 5.0  # Check every 5 seconds
    no_output_threshold: float = 300.0  # Alert if no output for 5 minutes (matches agent timeout)
    failure_threshold: int = 3  # Consecutive check failures before alert
    check_stderr_patterns: bool = True  # Monitor stderr for error patterns
    check_process_alive: bool = True  # Verify process is still running
    terminate_on_failure: bool = False  # Let policy timeouts control termination


@dataclass
class ActiveExecution:
    """Tracks an active agent execution for proactive monitoring."""

    task_id: str
    agent_id: str
    start_time: float
    last_output_time: float
    consecutive_failures: int = 0
    stdout_size: int = 0
    stderr_size: int = 0
    should_terminate: bool = False
    termination_reason: str | None = None


class AgentHealthMonitor:
    """Monitors agent health and collects failure detection metrics.

    Tracks:
    - Execution success/failure rates
    - Failure detection latency
    - Recovery rates and times
    - Circuit breaker activations
    - Time-to-detection metrics
    - Proactive health checks during execution
    """

    def __init__(self, proactive_config: ProactiveHealthConfig | None = None):
        """Initialize health monitor.

        Args:
            proactive_config: Optional configuration for proactive health checking

        """
        self._agent_metrics: dict[str, HealthMetrics] = defaultdict(
            lambda: HealthMetrics(agent_id=""),
        )
        self._failure_events: list[FailureEvent] = []
        self._detection_latencies: list[float] = []
        self._recovery_times: list[float] = []
        self._start_times: dict[str, float] = {}  # task_id -> start_time

        # Proactive health checking
        self._proactive_config = proactive_config or ProactiveHealthConfig()
        self._active_executions: dict[str, ActiveExecution] = {}
        self._health_check_thread: threading.Thread | None = None
        self._health_check_stop_event = threading.Event()
        self._health_check_callbacks: dict[str, Callable[[str, str], None]] = {}
        self._lock = threading.Lock()

    def start_proactive_monitoring(self) -> None:
        """Start background thread for proactive health checking."""
        if not self._proactive_config.enabled:
            return

        if self._health_check_thread is not None and self._health_check_thread.is_alive():
            return

        self._health_check_stop_event.clear()
        self._health_check_thread = threading.Thread(
            target=self._health_check_loop,
            daemon=True,
            name="HealthCheckMonitor",
        )
        self._health_check_thread.start()
        logger.info("Proactive health monitoring started")

    def stop_proactive_monitoring(self) -> None:
        """Stop background health checking thread."""
        if self._health_check_thread is None:
            return

        self._health_check_stop_event.set()
        self._health_check_thread.join(timeout=2.0)
        self._health_check_thread = None
        logger.info("Proactive health monitoring stopped")

    def register_execution_for_monitoring(
        self,
        task_id: str,
        agent_id: str,
        termination_callback: Callable[[str, str], None] | None = None,
    ) -> None:
        """Register an active execution for proactive monitoring.

        Args:
            task_id: Unique task identifier
            agent_id: Agent identifier
            termination_callback: Optional callback to trigger early termination
                Signature: callback(task_id, reason)

        """
        if not self._proactive_config.enabled:
            return

        now = time.time()
        with self._lock:
            self._active_executions[task_id] = ActiveExecution(
                task_id=task_id,
                agent_id=agent_id,
                start_time=now,
                last_output_time=now,
            )

            if termination_callback:
                self._health_check_callbacks[task_id] = termination_callback

        logger.debug(f"Registered task {task_id} for proactive monitoring")

    def update_execution_activity(
        self,
        task_id: str,
        stdout_size: int = 0,
        stderr_size: int = 0,
    ) -> None:
        """Update execution activity metrics (called when output is received).

        Args:
            task_id: Unique task identifier
            stdout_size: Current size of stdout in bytes
            stderr_size: Current size of stderr in bytes

        """
        if not self._proactive_config.enabled:
            return

        with self._lock:
            if task_id in self._active_executions:
                execution = self._active_executions[task_id]
                if stdout_size > execution.stdout_size or stderr_size > execution.stderr_size:
                    execution.last_output_time = time.time()
                    execution.stdout_size = stdout_size
                    execution.stderr_size = stderr_size
                    execution.consecutive_failures = 0  # Reset failure counter on activity

    def unregister_execution(self, task_id: str) -> None:
        """Remove execution from active monitoring.

        Args:
            task_id: Unique task identifier

        """
        with self._lock:
            self._active_executions.pop(task_id, None)
            self._health_check_callbacks.pop(task_id, None)

    def _health_check_loop(self) -> None:
        """Background thread that performs periodic health checks."""
        while not self._health_check_stop_event.is_set():
            try:
                self._perform_health_checks()
            except Exception as e:
                logger.error(f"Health check loop error: {e}", exc_info=True)

            self._health_check_stop_event.wait(self._proactive_config.check_interval)

    def _perform_health_checks(self) -> None:
        """Perform health checks on all active executions."""
        now = time.time()
        executions_to_check = []

        with self._lock:
            executions_to_check = list(self._active_executions.values())

        for execution in executions_to_check:
            try:
                self._check_execution_health(execution, now)
            except Exception as e:
                logger.error(
                    f"Health check failed for task {execution.task_id}: {e}",
                    exc_info=True,
                )

    def _check_execution_health(self, execution: ActiveExecution, now: float) -> None:
        """Check health of a single execution.

        Args:
            execution: Active execution to check
            now: Current timestamp

        """
        metrics = self._agent_metrics[execution.agent_id]
        metrics.proactive_checks += 1

        time_since_output = now - execution.last_output_time
        elapsed = now - execution.start_time

        # Check for no output threshold
        if time_since_output > self._proactive_config.no_output_threshold:
            execution.consecutive_failures += 1
            # Only warn if termination is enabled, otherwise use debug level
            # (warning is only useful if we're going to take action)
            if self._proactive_config.terminate_on_failure:
                log_fn = logger.warning if execution.consecutive_failures == 1 else logger.debug
            else:
                log_fn = logger.debug
            log_fn(
                f"No output for {time_since_output:.0f}s (check {execution.consecutive_failures})",
                extra={
                    "agent_id": execution.agent_id,
                    "task_id": execution.task_id,
                    "time_since_output": time_since_output,
                    "threshold": self._proactive_config.no_output_threshold,
                    "consecutive_failures": execution.consecutive_failures,
                    "event": "health_check.no_output",
                },
            )

            # Trigger early termination if threshold exceeded
            if execution.consecutive_failures >= self._proactive_config.failure_threshold:
                reason = (
                    f"No output for {time_since_output:.0f}s "
                    f"({execution.consecutive_failures} consecutive check failures)"
                )
                self._trigger_early_termination(execution, reason, metrics)

        # Log periodic health check
        logger.debug(
            "Health check performed",
            extra={
                "agent_id": execution.agent_id,
                "task_id": execution.task_id,
                "elapsed": elapsed,
                "time_since_output": time_since_output,
                "consecutive_failures": execution.consecutive_failures,
                "event": "health_check.performed",
            },
        )

    def _trigger_early_termination(
        self,
        execution: ActiveExecution,
        reason: str,
        metrics: HealthMetrics,
    ) -> None:
        """Trigger early termination for an execution.

        Args:
            execution: Active execution to terminate
            reason: Reason for termination
            metrics: Agent metrics to update

        """
        # Skip if termination is disabled - just track metrics silently
        if not self._proactive_config.terminate_on_failure:
            metrics.early_detections += 1
            logger.debug(
                f"Health check issue detected (termination disabled): {reason}",
                extra={
                    "agent_id": execution.agent_id,
                    "task_id": execution.task_id,
                    "reason": reason,
                    "event": "health_check.issue_detected",
                },
            )
            return

        with self._lock:
            if execution.should_terminate:
                return  # Already triggered

            execution.should_terminate = True
            execution.termination_reason = reason

            # Update metrics
            metrics.early_detections += 1

            logger.error(
                "Early termination triggered by proactive health check",
                extra={
                    "agent_id": execution.agent_id,
                    "task_id": execution.task_id,
                    "reason": reason,
                    "elapsed": time.time() - execution.start_time,
                    "event": "health_check.early_termination",
                },
            )

            # Invoke termination callback if registered
            callback = self._health_check_callbacks.get(execution.task_id)
            if callback:
                try:
                    callback(execution.task_id, reason)
                except Exception as e:
                    logger.error(f"Termination callback failed: {e}", exc_info=True)

    def should_terminate(self, task_id: str) -> tuple[bool, str | None]:
        """Check if a task should be terminated by proactive health check.

        Args:
            task_id: Unique task identifier

        Returns:
            Tuple of (should_terminate, reason)

        Note:
            Termination is disabled - policy timeouts in spawner main loop
            are the single source of truth for timeout decisions.

        """
        # Disabled: Let SpawnPolicy.timeout_policy control all timeouts
        # The spawner's main loop (spawner.py:259-278) handles this properly
        if not self._proactive_config.terminate_on_failure:
            return False, None

        with self._lock:
            execution = self._active_executions.get(task_id)
            if execution:
                return execution.should_terminate, execution.termination_reason
            return False, None

    def record_execution_start(
        self,
        task_id: str,
        agent_id: str,
        policy_name: str | None = None,
    ) -> None:
        """Record the start of an agent execution.

        Args:
            task_id: Unique task identifier
            agent_id: Agent identifier
            policy_name: Optional policy name being used

        """
        start_time = time.time()
        self._start_times[task_id] = start_time

        logger.info(
            "Agent execution started",
            extra={
                "agent_id": agent_id,
                "task_id": task_id,
                "timestamp": start_time,
                "policy_name": policy_name,
                "event": "execution.started",
            },
        )

        # Start proactive monitoring if enabled
        if self._proactive_config.enabled:
            self.start_proactive_monitoring()
            self.register_execution_for_monitoring(task_id, agent_id)

    def record_execution_success(self, task_id: str, agent_id: str, output_size: int = 0) -> None:
        """Record successful agent execution.

        Args:
            task_id: Unique task identifier
            agent_id: Agent identifier
            output_size: Size of output in bytes

        """
        end_time = time.time()
        start_time = self._start_times.get(task_id)
        execution_time = end_time - start_time if start_time else 0.0

        metrics = self._agent_metrics[agent_id]
        metrics.agent_id = agent_id
        metrics.total_executions += 1
        metrics.successful_executions += 1
        metrics.total_execution_time += execution_time
        metrics.avg_execution_time = metrics.total_execution_time / metrics.total_executions
        metrics.failure_rate = metrics.failed_executions / metrics.total_executions
        metrics.last_success_time = end_time

        logger.info(
            "Agent execution succeeded",
            extra={
                "agent_id": agent_id,
                "task_id": task_id,
                "timestamp": end_time,
                "execution_time": execution_time,
                "output_size": output_size,
                "success_rate": 1.0 - metrics.failure_rate,
                "event": "execution.success",
            },
        )

        # Clean up
        self._start_times.pop(task_id, None)
        self.unregister_execution(task_id)

    def record_execution_failure(
        self,
        task_id: str,
        agent_id: str,
        reason: FailureReason,
        error_message: str | None = None,
        retry_attempt: int = 0,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Record agent execution failure with detection latency.

        Args:
            task_id: Unique task identifier
            agent_id: Agent identifier
            reason: Categorized failure reason
            error_message: Optional error description
            retry_attempt: Current retry attempt number
            metadata: Additional context

        """
        end_time = time.time()
        start_time = self._start_times.get(task_id, end_time)
        detection_latency = end_time - start_time

        # Record failure event
        failure_event = FailureEvent(
            agent_id=agent_id,
            task_id=task_id,
            timestamp=end_time,
            reason=reason,
            detection_latency=detection_latency,
            error_message=error_message,
            retry_attempt=retry_attempt,
            metadata=metadata or {},
        )
        self._failure_events.append(failure_event)
        self._detection_latencies.append(detection_latency)

        # Update agent metrics
        metrics = self._agent_metrics[agent_id]
        metrics.agent_id = agent_id
        metrics.total_executions += 1
        metrics.failed_executions += 1
        metrics.failure_rate = metrics.failed_executions / metrics.total_executions
        metrics.last_failure_time = end_time

        # Update average detection latency
        if self._detection_latencies:
            metrics.avg_detection_latency = sum(self._detection_latencies) / len(
                self._detection_latencies,
            )

        # Use DEBUG level for all failures - progress callbacks handle user-facing output
        # Observability module is for metrics, not user feedback
        log_level = logging.DEBUG

        # Build log message with error details
        log_msg = f"Agent {agent_id} failed"
        if error_message:
            # Extract first line of error, truncate if too long
            error_line = error_message.split("\n")[0][:100]
            log_msg += f": {error_line}"

        logger.log(
            log_level,
            log_msg,
            extra={
                "agent_id": agent_id,
                "task_id": task_id,
                "timestamp": end_time,
                "reason": reason.value,
                "detection_latency": detection_latency,
                "detection_latency_ms": detection_latency * 1000,
                "error_message": error_message,
                "retry_attempt": retry_attempt,
                "failure_rate": metrics.failure_rate,
                "avg_detection_latency": metrics.avg_detection_latency,
                "event": "execution.failure",
            },
        )

        # Log high detection latency (>30s) for metrics - not a problem with patient policy
        if detection_latency > 30.0:
            logger.debug(
                f"Detection latency: {detection_latency:.0f}s",
                extra={
                    "agent_id": agent_id,
                    "task_id": task_id,
                    "detection_latency": detection_latency,
                    "detection_latency_ms": detection_latency * 1000,
                    "threshold": 30.0,
                    "threshold_ms": 30000,
                    "exceeded_by_ms": (detection_latency - 30.0) * 1000,
                    "event": "detection.latency.high",
                    "severity": "high" if detection_latency > 60.0 else "medium",
                },
            )

        # Clean up
        self._start_times.pop(task_id, None)
        self.unregister_execution(task_id)

    def record_recovery(self, task_id: str, agent_id: str, recovery_time: float) -> None:
        """Record successful recovery after failure.

        Args:
            task_id: Unique task identifier
            agent_id: Agent identifier
            recovery_time: Time taken to recover (seconds)

        """
        self._recovery_times.append(recovery_time)

        # Update most recent failure event for this task
        for event in reversed(self._failure_events):
            if event.task_id == task_id and event.agent_id == agent_id:
                event.recovered = True
                event.recovery_time = recovery_time
                break

        # Update metrics
        metrics = self._agent_metrics[agent_id]
        recovery_count = sum(1 for e in self._failure_events if e.recovered)
        failure_count = len(self._failure_events)
        metrics.recovery_rate = recovery_count / failure_count if failure_count > 0 else 0.0

        logger.info(
            "Agent recovered from failure",
            extra={
                "agent_id": agent_id,
                "task_id": task_id,
                "recovery_time": recovery_time,
                "recovery_rate": metrics.recovery_rate,
                "event": "execution.recovery",
            },
        )

    def record_circuit_open(self, agent_id: str, reason: str) -> None:
        """Record circuit breaker opening.

        Args:
            agent_id: Agent identifier
            reason: Reason for circuit opening

        """
        metrics = self._agent_metrics[agent_id]
        metrics.agent_id = agent_id
        metrics.circuit_open_count += 1

        logger.error(
            "Circuit breaker opened",
            extra={
                "agent_id": agent_id,
                "reason": reason,
                "open_count": metrics.circuit_open_count,
                "failure_rate": metrics.failure_rate,
                "event": "circuit.opened",
            },
        )

    def record_circuit_close(self, agent_id: str) -> None:
        """Record circuit breaker closing.

        Args:
            agent_id: Agent identifier

        """
        logger.info(
            "Circuit breaker closed",
            extra={
                "agent_id": agent_id,
                "event": "circuit.closed",
            },
        )

    def get_agent_health(self, agent_id: str) -> HealthMetrics:
        """Get health metrics for a specific agent.

        Args:
            agent_id: Agent identifier

        Returns:
            HealthMetrics for the agent

        """
        metrics = self._agent_metrics[agent_id]
        metrics.agent_id = agent_id
        return metrics

    def get_all_agent_health(self) -> dict[str, HealthMetrics]:
        """Get health metrics for all agents.

        Returns:
            Dictionary mapping agent_id to HealthMetrics

        """
        return dict(self._agent_metrics)

    def get_detection_latency_stats(self) -> dict[str, float]:
        """Get failure detection latency statistics.

        Returns:
            Dictionary with latency statistics (avg, p50, p95, p99)

        """
        if not self._detection_latencies:
            return {
                "avg": 0.0,
                "p50": 0.0,
                "p95": 0.0,
                "p99": 0.0,
                "min": 0.0,
                "max": 0.0,
            }

        sorted_latencies = sorted(self._detection_latencies)
        n = len(sorted_latencies)

        return {
            "avg": sum(sorted_latencies) / n,
            "p50": sorted_latencies[int(n * 0.50)],
            "p95": sorted_latencies[int(n * 0.95)],
            "p99": sorted_latencies[min(int(n * 0.99), n - 1)],
            "min": sorted_latencies[0],
            "max": sorted_latencies[-1],
        }

    def get_failure_events(
        self,
        agent_id: str | None = None,
        limit: int | None = None,
    ) -> list[FailureEvent]:
        """Get failure events, optionally filtered by agent.

        Args:
            agent_id: Optional agent filter
            limit: Optional limit on number of events

        Returns:
            List of failure events (most recent first)

        """
        events = self._failure_events
        if agent_id:
            events = [e for e in events if e.agent_id == agent_id]

        events = sorted(events, key=lambda e: e.timestamp, reverse=True)

        if limit:
            events = events[:limit]

        return events

    def get_summary(self) -> dict[str, Any]:
        """Get overall health summary across all agents.

        Returns:
            Dictionary with aggregate health metrics and failure categorization

        """
        all_metrics = list(self._agent_metrics.values())

        if not all_metrics:
            return {
                "total_agents": 0,
                "total_executions": 0,
                "total_failures": 0,
                "avg_failure_rate": 0.0,
                "avg_detection_latency": 0.0,
                "avg_detection_latency_ms": 0.0,
                "avg_recovery_rate": 0.0,
                "failure_by_reason": {},
                "circuit_breaker_status": {
                    "total_opens": 0,
                    "agents_with_open_circuits": [],
                },
            }

        total_executions = sum(m.total_executions for m in all_metrics)
        total_failures = sum(m.failed_executions for m in all_metrics)
        total_circuit_opens = sum(m.circuit_open_count for m in all_metrics)

        # Categorize failures by reason
        failure_by_reason: dict[str, int] = {}
        for event in self._failure_events:
            reason = event.reason.value
            failure_by_reason[reason] = failure_by_reason.get(reason, 0) + 1

        # Identify agents with recent circuit opens
        agents_with_circuits = [m.agent_id for m in all_metrics if m.circuit_open_count > 0]

        detection_stats = self.get_detection_latency_stats()

        return {
            "total_agents": len(all_metrics),
            "total_executions": total_executions,
            "total_failures": total_failures,
            "avg_failure_rate": total_failures / total_executions if total_executions > 0 else 0.0,
            "avg_detection_latency": detection_stats["avg"],
            "avg_detection_latency_ms": detection_stats["avg"] * 1000,
            "avg_recovery_rate": sum(m.recovery_rate for m in all_metrics) / len(all_metrics),
            "detection_latency_stats": detection_stats,
            "failure_by_reason": failure_by_reason,
            "circuit_breaker_status": {
                "total_opens": total_circuit_opens,
                "agents_with_open_circuits": agents_with_circuits,
                "affected_agent_count": len(agents_with_circuits),
            },
        }


# Global singleton instance
_global_health_monitor: AgentHealthMonitor | None = None


def get_health_monitor() -> AgentHealthMonitor:
    """Get the global health monitor singleton.

    Returns:
        Global AgentHealthMonitor instance

    """
    global _global_health_monitor
    if _global_health_monitor is None:
        _global_health_monitor = AgentHealthMonitor()
    return _global_health_monitor


def reset_health_monitor(config: ProactiveHealthConfig | None = None) -> AgentHealthMonitor:
    """Reset the global health monitor singleton with new configuration.

    Use this at the start of execution to ensure fresh state and
    apply updated configuration.

    Args:
        config: Optional new configuration for the health monitor

    Returns:
        Fresh AgentHealthMonitor instance

    """
    global _global_health_monitor
    if _global_health_monitor is not None:
        _global_health_monitor.stop_proactive_monitoring()
    _global_health_monitor = AgentHealthMonitor(config)
    return _global_health_monitor


def configure_structured_logging(
    level: int = logging.INFO,
    include_context: bool = True,
    json_format: bool = False,
) -> None:
    """Configure structured logging for agent observability.

    Args:
        level: Logging level (default: INFO)
        include_context: Whether to include contextual fields in logs
        json_format: Whether to output logs in JSON format (default: False for human readability)

    """
    import json

    class StructuredFormatter(logging.Formatter):
        """Formatter for structured logs with JSON or human-readable output."""

        def __init__(self, json_format: bool = False):
            super().__init__()
            self.json_format = json_format

        def format(self, record: logging.LogRecord) -> str:
            log_data = {
                "timestamp": self.formatTime(record),
                "level": record.levelname,
                "logger": record.name,
                "message": record.getMessage(),
            }

            # Add contextual fields if present
            extra_fields = {}
            if include_context and hasattr(record, "agent_id"):
                log_data["agent_id"] = record.agent_id
            if include_context and hasattr(record, "task_id"):
                log_data["task_id"] = record.task_id
            if include_context and hasattr(record, "event"):
                log_data["event"] = record.event

            # Add all extra fields
            for key, value in record.__dict__.items():
                if key not in [
                    "name",
                    "msg",
                    "args",
                    "created",
                    "filename",
                    "funcName",
                    "levelname",
                    "levelno",
                    "lineno",
                    "module",
                    "msecs",
                    "message",
                    "pathname",
                    "process",
                    "processName",
                    "relativeCreated",
                    "thread",
                    "threadName",
                    "exc_info",
                    "exc_text",
                    "stack_info",
                ]:
                    extra_fields[key] = value

            if self.json_format:
                # JSON output for log aggregation systems
                log_data.update(extra_fields)
                return json.dumps(log_data)
            # Human-readable output for development
            base_msg = f"[{log_data['timestamp']}] {log_data['level']} {log_data['logger']}: {log_data['message']}"

            # Add key metrics to base message for failure events
            if extra_fields.get("event") == "execution.failure":
                metrics = []
                if "detection_latency_ms" in extra_fields:
                    metrics.append(f"latency={extra_fields['detection_latency_ms']:.0f}ms")
                if "reason" in extra_fields:
                    metrics.append(f"reason={extra_fields['reason']}")
                if "retry_attempt" in extra_fields:
                    metrics.append(f"retry={extra_fields['retry_attempt']}")
                if metrics:
                    base_msg += f" ({', '.join(metrics)})"

            # Add structured fields as key-value pairs if present
            if extra_fields:
                # Filter to most important fields for readability
                important_fields = ["agent_id", "task_id", "event"]
                structured = ", ".join(
                    f"{k}={v}"
                    for k, v in extra_fields.items()
                    if k in important_fields and k not in log_data
                )
                if structured:
                    base_msg += f" [{structured}]"

            return base_msg

    # Configure root logger
    handler = logging.StreamHandler()
    handler.setFormatter(StructuredFormatter(json_format=json_format))

    root_logger = logging.getLogger("aurora_spawner")
    root_logger.setLevel(level)
    # Clear existing handlers to avoid duplicates
    root_logger.handlers.clear()
    root_logger.addHandler(handler)
