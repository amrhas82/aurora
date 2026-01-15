"""Observability infrastructure for agent health monitoring.

Provides structured logging, metrics collection, and performance tracking
for agent execution, failure detection, and recovery.
"""

import logging
import time
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class FailureReason(Enum):
    """Categorization of agent failure reasons."""

    TIMEOUT = "timeout"
    ERROR_PATTERN = "error_pattern"
    NO_ACTIVITY = "no_activity"
    CIRCUIT_OPEN = "circuit_open"
    CRASH = "crash"
    KILLED = "killed"
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


class AgentHealthMonitor:
    """Monitors agent health and collects failure detection metrics.

    Tracks:
    - Execution success/failure rates
    - Failure detection latency
    - Recovery rates and times
    - Circuit breaker activations
    - Time-to-detection metrics
    """

    def __init__(self):
        """Initialize health monitor."""
        self._agent_metrics: dict[str, HealthMetrics] = defaultdict(
            lambda: HealthMetrics(agent_id="")
        )
        self._failure_events: list[FailureEvent] = []
        self._detection_latencies: list[float] = []
        self._recovery_times: list[float] = []
        self._start_times: dict[str, float] = {}  # task_id -> start_time

    def record_execution_start(
        self, task_id: str, agent_id: str, policy_name: str | None = None
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

        # Clean up start time
        self._start_times.pop(task_id, None)

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
                self._detection_latencies
            )

        # Determine log level based on failure reason
        log_level = logging.ERROR if reason == FailureReason.CRASH else logging.WARNING

        logger.log(
            log_level,
            "Agent execution failed",
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

        # Alert on high detection latency (>30s indicates slow failure detection)
        if detection_latency > 30.0:
            logger.error(
                "High failure detection latency detected",
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

        # Clean up start time
        self._start_times.pop(task_id, None)

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
        self, agent_id: str | None = None, limit: int | None = None
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
            else:
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
