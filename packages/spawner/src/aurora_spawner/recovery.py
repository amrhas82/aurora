"""Agent recovery configuration for spawner.

Simple recovery flow with configurable retry policies for parallel agent execution.

Strategies:
- RETRY_SAME: Retry same agent with backoff before failing
- FALLBACK_ONLY: Skip retries, go directly to LLM fallback
- RETRY_THEN_FALLBACK: Retry agent, then fallback to LLM (default)
- NO_RECOVERY: No retries or fallback, fail immediately

Features:
- Configurable retry policies with exponential backoff
- Error classification for smart recovery decisions
- Recovery metrics tracking
- Per-agent policy overrides
- Config-based policy loading
- Simple state machine for recovery flow tracking
"""

import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable

logger = logging.getLogger(__name__)


class RecoveryState(Enum):
    """States for recovery state machine."""

    INITIAL = "initial"  # Not started
    EXECUTING = "executing"  # Running task
    RETRY_PENDING = "retry_pending"  # Waiting for retry
    RETRYING = "retrying"  # Retry in progress
    FALLBACK_PENDING = "fallback_pending"  # About to fallback
    FALLBACK_EXECUTING = "fallback_executing"  # Fallback in progress
    SUCCEEDED = "succeeded"  # Task completed successfully
    FAILED = "failed"  # All recovery exhausted
    CIRCUIT_OPEN = "circuit_open"  # Circuit breaker prevented execution


@dataclass
class RecoveryStateTransition:
    """Records a state transition for observability."""

    from_state: RecoveryState
    to_state: RecoveryState
    timestamp: float
    reason: str | None = None
    attempt: int = 0
    error: str | None = None


@dataclass
class TaskRecoveryState:
    """Tracks recovery state for a single task.

    Simple state machine with transitions:
    - INITIAL -> EXECUTING (start)
    - EXECUTING -> SUCCEEDED (success)
    - EXECUTING -> RETRY_PENDING (failure, retries remaining)
    - EXECUTING -> FALLBACK_PENDING (failure, no retries, fallback enabled)
    - EXECUTING -> FAILED (failure, no retries, no fallback)
    - RETRY_PENDING -> RETRYING (after delay)
    - RETRYING -> SUCCEEDED (success)
    - RETRYING -> RETRY_PENDING (failure, retries remaining)
    - RETRYING -> FALLBACK_PENDING (failure, no retries)
    - RETRYING -> FAILED (failure, no fallback)
    - FALLBACK_PENDING -> FALLBACK_EXECUTING (start fallback)
    - FALLBACK_EXECUTING -> SUCCEEDED (success)
    - FALLBACK_EXECUTING -> FAILED (failure)
    - INITIAL -> CIRCUIT_OPEN (circuit breaker open)
    - CIRCUIT_OPEN -> FALLBACK_PENDING (fallback enabled)
    - CIRCUIT_OPEN -> FAILED (no fallback)
    """

    task_id: str
    agent_id: str
    state: RecoveryState = RecoveryState.INITIAL
    attempt: int = 0
    max_retries: int = 2
    fallback_enabled: bool = True
    start_time: float = field(default_factory=time.time)
    transitions: list[RecoveryStateTransition] = field(default_factory=list)
    last_error: str | None = None
    used_fallback: bool = False

    def transition(
        self,
        to_state: RecoveryState,
        reason: str | None = None,
        error: str | None = None,
    ) -> None:
        """Record state transition.

        Args:
            to_state: Target state
            reason: Optional reason for transition
            error: Optional error message

        """
        transition = RecoveryStateTransition(
            from_state=self.state,
            to_state=to_state,
            timestamp=time.time(),
            reason=reason,
            attempt=self.attempt,
            error=error,
        )
        self.transitions.append(transition)
        self.state = to_state
        if error:
            self.last_error = error

        logger.debug(
            f"Recovery state: {transition.from_state.value} -> {transition.to_state.value}",
            extra={
                "task_id": self.task_id,
                "agent_id": self.agent_id,
                "from_state": transition.from_state.value,
                "to_state": transition.to_state.value,
                "attempt": self.attempt,
                "reason": reason,
                "event": "recovery.state_transition",
            },
        )

    def start(self) -> None:
        """Start task execution."""
        self.transition(RecoveryState.EXECUTING, reason="start")

    def succeed(self) -> None:
        """Mark task as succeeded."""
        self.transition(RecoveryState.SUCCEEDED, reason="success")

    def fail(self, error: str | None = None) -> RecoveryState:
        """Handle execution failure, returns next state.

        Args:
            error: Error message from failure

        Returns:
            The new state after failure handling

        """
        self.attempt += 1

        # Check if retries remaining
        if self.attempt <= self.max_retries:
            self.transition(RecoveryState.RETRY_PENDING, reason="retry_available", error=error)
            return self.state

        # No retries, check fallback
        if self.fallback_enabled:
            self.transition(RecoveryState.FALLBACK_PENDING, reason="retries_exhausted", error=error)
            return self.state

        # No recovery options
        self.transition(RecoveryState.FAILED, reason="no_recovery_options", error=error)
        return self.state

    def start_retry(self) -> None:
        """Start retry attempt."""
        if self.state != RecoveryState.RETRY_PENDING:
            raise ValueError(f"Cannot retry from state {self.state}")
        self.transition(RecoveryState.RETRYING, reason=f"retry_attempt_{self.attempt}")

    def start_fallback(self) -> None:
        """Start fallback execution."""
        if self.state not in (RecoveryState.FALLBACK_PENDING, RecoveryState.CIRCUIT_OPEN):
            raise ValueError(f"Cannot fallback from state {self.state}")
        self.used_fallback = True
        self.transition(RecoveryState.FALLBACK_EXECUTING, reason="fallback_start")

    def circuit_open(self) -> RecoveryState:
        """Handle circuit breaker open.

        Returns:
            The new state after circuit open handling

        """
        if self.fallback_enabled:
            self.transition(RecoveryState.CIRCUIT_OPEN, reason="circuit_breaker_open")
            return self.state
        self.transition(RecoveryState.FAILED, reason="circuit_open_no_fallback")
        return self.state

    @property
    def is_terminal(self) -> bool:
        """Check if state is terminal (no more transitions possible)."""
        return self.state in (RecoveryState.SUCCEEDED, RecoveryState.FAILED)

    @property
    def elapsed_time(self) -> float:
        """Get elapsed time since start."""
        return time.time() - self.start_time

    @property
    def recovery_path(self) -> list[str]:
        """Get human-readable recovery path."""
        path = []
        for t in self.transitions:
            if t.to_state == RecoveryState.RETRYING:
                path.append(f"retry:{t.attempt}")
            elif t.to_state == RecoveryState.FALLBACK_EXECUTING:
                path.append("fallback")
            elif t.to_state == RecoveryState.CIRCUIT_OPEN:
                path.append("circuit_open")
        return path

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "task_id": self.task_id,
            "agent_id": self.agent_id,
            "state": self.state.value,
            "attempt": self.attempt,
            "max_retries": self.max_retries,
            "fallback_enabled": self.fallback_enabled,
            "used_fallback": self.used_fallback,
            "elapsed_time": self.elapsed_time,
            "last_error": self.last_error,
            "recovery_path": self.recovery_path,
            "transitions": [
                {
                    "from": t.from_state.value,
                    "to": t.to_state.value,
                    "timestamp": t.timestamp,
                    "reason": t.reason,
                    "attempt": t.attempt,
                }
                for t in self.transitions
            ],
        }


class RecoveryStateMachine:
    """Manages recovery state for multiple tasks.

    Simple coordinator that tracks recovery state per task
    and integrates with circuit breaker for skip decisions.

    Example:
        >>> from aurora_spawner.recovery import RecoveryStateMachine, RecoveryPolicy
        >>> from aurora_spawner.circuit_breaker import get_circuit_breaker
        >>>
        >>> sm = RecoveryStateMachine(policy=RecoveryPolicy.default())
        >>> state = sm.create_task_state("task-1", "code-agent")
        >>> state.start()
        >>> # ... execute task ...
        >>> state.fail("Connection timeout")  # Returns RETRY_PENDING
        >>> state.start_retry()
        >>> # ... retry ...
        >>> state.succeed()

    """

    def __init__(
        self,
        policy: "RecoveryPolicy | None" = None,
        circuit_breaker: Any = None,
    ):
        """Initialize recovery state machine.

        Args:
            policy: Recovery policy (uses default if None)
            circuit_breaker: Optional circuit breaker (uses singleton if None)

        """
        self._policy = policy or RecoveryPolicy.default()
        self._circuit_breaker = circuit_breaker
        self._task_states: dict[str, TaskRecoveryState] = {}

    @property
    def circuit_breaker(self) -> Any:
        """Get circuit breaker (lazy initialization)."""
        if self._circuit_breaker is None:
            from aurora_spawner.circuit_breaker import get_circuit_breaker

            self._circuit_breaker = get_circuit_breaker()
        return self._circuit_breaker

    def create_task_state(
        self,
        task_id: str,
        agent_id: str,
        policy_override: "RecoveryPolicy | None" = None,
    ) -> TaskRecoveryState:
        """Create and register recovery state for a task.

        Args:
            task_id: Unique task identifier
            agent_id: Agent to execute task
            policy_override: Optional policy override for this task

        Returns:
            TaskRecoveryState for tracking

        """
        policy = policy_override or self._policy.get_for_agent(agent_id)

        state = TaskRecoveryState(
            task_id=task_id,
            agent_id=agent_id,
            max_retries=policy.max_retries,
            fallback_enabled=policy.fallback_to_llm,
        )

        self._task_states[task_id] = state
        return state

    def get_task_state(self, task_id: str) -> TaskRecoveryState | None:
        """Get recovery state for a task.

        Args:
            task_id: Task identifier

        Returns:
            TaskRecoveryState or None if not found

        """
        return self._task_states.get(task_id)

    def check_circuit_breaker(self, _task_id: str, agent_id: str) -> tuple[bool, str | None]:
        """Check if circuit breaker allows execution.

        Args:
            task_id: Task identifier
            agent_id: Agent identifier

        Returns:
            Tuple of (should_skip, reason)

        """
        return self.circuit_breaker.should_skip(agent_id)

    def record_success(self, agent_id: str) -> None:
        """Record success with circuit breaker.

        Args:
            agent_id: Agent that succeeded

        """
        self.circuit_breaker.record_success(agent_id)

    def record_failure(self, agent_id: str, failure_type: str | None = None) -> None:
        """Record failure with circuit breaker.

        Args:
            agent_id: Agent that failed
            failure_type: Type of failure for circuit breaker

        """
        self.circuit_breaker.record_failure(agent_id, failure_type=failure_type)

    def get_summary(self) -> dict[str, Any]:
        """Get summary of all task recovery states.

        Returns:
            Summary dictionary with counts by state

        """
        states = list(self._task_states.values())
        by_state = {}
        for s in states:
            by_state[s.state.value] = by_state.get(s.state.value, 0) + 1

        succeeded = sum(1 for s in states if s.state == RecoveryState.SUCCEEDED)
        failed = sum(1 for s in states if s.state == RecoveryState.FAILED)
        recovered = sum(1 for s in states if s.state == RecoveryState.SUCCEEDED and s.attempt > 1)
        used_fallback = sum(1 for s in states if s.used_fallback)

        return {
            "total_tasks": len(states),
            "succeeded": succeeded,
            "failed": failed,
            "recovered": recovered,
            "used_fallback": used_fallback,
            "by_state": by_state,
            "tasks": {task_id: state.to_dict() for task_id, state in self._task_states.items()},
        }

    def clear(self) -> None:
        """Clear all task states."""
        self._task_states.clear()


class ErrorCategory(Enum):
    """Error categories for recovery decision making."""

    TRANSIENT = "transient"  # Network issues, rate limits - worth retrying
    PERMANENT = "permanent"  # Auth failures, invalid config - don't retry
    TIMEOUT = "timeout"  # Timeout errors - may retry with longer timeout
    RESOURCE = "resource"  # Memory, quota - may retry after delay
    UNKNOWN = "unknown"  # Unclassified - use default behavior


# Default error patterns by category
DEFAULT_ERROR_PATTERNS: dict[ErrorCategory, list[str]] = {
    ErrorCategory.TRANSIENT: [
        r"rate.?limit",
        r"\b429\b",
        r"connection.?(refused|reset|error)",
        r"ECONNRESET",
        r"temporary.?failure",
        r"retry.?later",
        r"service.?unavailable",
        r"\b503\b",
    ],
    ErrorCategory.PERMANENT: [
        r"authentication.?failed",
        r"invalid.?api.?key",
        r"unauthorized",
        r"\b401\b",
        r"forbidden",
        r"\b403\b",
        r"model.?not.?(found|available)",
        r"invalid.?model",
        r"permission.?denied",
    ],
    ErrorCategory.TIMEOUT: [
        r"timed?.?out",
        r"deadline.?exceeded",
        r"no.?activity",
        r"context.?deadline",
    ],
    ErrorCategory.RESOURCE: [
        r"quota.?exceeded",
        r"out.?of.?memory",
        r"resource.?exhausted",
        r"too.?many.?requests",
        r"\b509\b",
    ],
}


@dataclass
class ErrorClassifier:
    """Classifies errors to guide recovery decisions.

    Example:
        >>> classifier = ErrorClassifier()
        >>> classifier.classify("Rate limit exceeded")
        <ErrorCategory.TRANSIENT: 'transient'>
        >>> classifier.classify("Invalid API key")
        <ErrorCategory.PERMANENT: 'permanent'>

    """

    patterns: dict[ErrorCategory, list[str]] = field(
        default_factory=lambda: dict(DEFAULT_ERROR_PATTERNS),
    )

    def classify(self, error_text: str) -> ErrorCategory:
        """Classify an error message.

        Args:
            error_text: Error message to classify

        Returns:
            ErrorCategory indicating error type

        """
        import re

        error_lower = error_text.lower()

        for category, patterns in self.patterns.items():
            for pattern in patterns:
                if re.search(pattern, error_lower, re.IGNORECASE):
                    return category

        return ErrorCategory.UNKNOWN

    def should_retry(self, category: ErrorCategory) -> bool:
        """Check if error category is worth retrying.

        Args:
            category: Error category

        Returns:
            True if retry is recommended

        """
        return category in (
            ErrorCategory.TRANSIENT,
            ErrorCategory.TIMEOUT,
            ErrorCategory.RESOURCE,
            ErrorCategory.UNKNOWN,
        )

    def add_pattern(self, category: ErrorCategory, pattern: str) -> None:
        """Add a custom error pattern.

        Args:
            category: Category to add pattern to
            pattern: Regex pattern to match

        """
        if category not in self.patterns:
            self.patterns[category] = []
        self.patterns[category].append(pattern)


@dataclass
class RecoveryMetrics:
    """Tracks recovery statistics for monitoring and tuning.

    Example:
        >>> metrics = RecoveryMetrics()
        >>> metrics.record_attempt("agent-1", success=True, retries=2)
        >>> metrics.success_rate("agent-1")
        100.0

    """

    # Per-agent tracking
    _attempts: dict[str, int] = field(default_factory=dict)
    _successes: dict[str, int] = field(default_factory=dict)
    _failures: dict[str, int] = field(default_factory=dict)
    _retries: dict[str, int] = field(default_factory=dict)
    _fallbacks: dict[str, int] = field(default_factory=dict)
    _recovery_times: dict[str, list[float]] = field(default_factory=dict)

    # Error category tracking
    _errors_by_category: dict[str, dict[ErrorCategory, int]] = field(default_factory=dict)

    def record_attempt(
        self,
        agent_id: str,
        success: bool,
        retries: int = 0,
        used_fallback: bool = False,
        recovery_time: float = 0.0,
        error_category: ErrorCategory | None = None,
    ) -> None:
        """Record a recovery attempt.

        Args:
            agent_id: Agent identifier
            success: Whether task ultimately succeeded
            retries: Number of retry attempts
            used_fallback: Whether fallback was used
            recovery_time: Total recovery time in seconds
            error_category: Category of error if failed

        """
        self._attempts[agent_id] = self._attempts.get(agent_id, 0) + 1
        self._retries[agent_id] = self._retries.get(agent_id, 0) + retries

        if success:
            self._successes[agent_id] = self._successes.get(agent_id, 0) + 1
        else:
            self._failures[agent_id] = self._failures.get(agent_id, 0) + 1
            if error_category:
                if agent_id not in self._errors_by_category:
                    self._errors_by_category[agent_id] = {}
                self._errors_by_category[agent_id][error_category] = (
                    self._errors_by_category[agent_id].get(error_category, 0) + 1
                )

        if used_fallback:
            self._fallbacks[agent_id] = self._fallbacks.get(agent_id, 0) + 1

        if recovery_time > 0:
            if agent_id not in self._recovery_times:
                self._recovery_times[agent_id] = []
            self._recovery_times[agent_id].append(recovery_time)

    def success_rate(self, agent_id: str | None = None) -> float:
        """Get success rate percentage.

        Args:
            agent_id: Specific agent, or None for overall rate

        Returns:
            Success rate as percentage (0-100)

        """
        if agent_id:
            attempts = self._attempts.get(agent_id, 0)
            successes = self._successes.get(agent_id, 0)
        else:
            attempts = sum(self._attempts.values())
            successes = sum(self._successes.values())

        if attempts == 0:
            return 0.0
        return (successes / attempts) * 100

    def recovery_rate(self, agent_id: str | None = None) -> float:
        """Get recovery rate (tasks recovered after initial failure).

        Args:
            agent_id: Specific agent, or None for overall rate

        Returns:
            Recovery rate as percentage

        """
        if agent_id:
            retries = self._retries.get(agent_id, 0)
            successes_with_retries = min(retries, self._successes.get(agent_id, 0))
        else:
            retries = sum(self._retries.values())
            successes_with_retries = min(retries, sum(self._successes.values()))

        if retries == 0:
            return 100.0  # All succeeded first try
        return (successes_with_retries / retries) * 100

    def avg_recovery_time(self, agent_id: str | None = None) -> float:
        """Get average recovery time in seconds.

        Args:
            agent_id: Specific agent, or None for overall average

        Returns:
            Average recovery time in seconds

        """
        if agent_id:
            times = self._recovery_times.get(agent_id, [])
        else:
            times = [t for times in self._recovery_times.values() for t in times]

        if not times:
            return 0.0
        return sum(times) / len(times)

    def to_dict(self) -> dict[str, Any]:
        """Convert metrics to dictionary."""
        return {
            "total_attempts": sum(self._attempts.values()),
            "total_successes": sum(self._successes.values()),
            "total_failures": sum(self._failures.values()),
            "total_retries": sum(self._retries.values()),
            "total_fallbacks": sum(self._fallbacks.values()),
            "overall_success_rate": self.success_rate(),
            "overall_recovery_rate": self.recovery_rate(),
            "avg_recovery_time": self.avg_recovery_time(),
            "by_agent": {
                agent_id: {
                    "attempts": self._attempts.get(agent_id, 0),
                    "successes": self._successes.get(agent_id, 0),
                    "failures": self._failures.get(agent_id, 0),
                    "retries": self._retries.get(agent_id, 0),
                    "fallbacks": self._fallbacks.get(agent_id, 0),
                    "success_rate": self.success_rate(agent_id),
                }
                for agent_id in self._attempts
            },
        }

    def reset(self) -> None:
        """Reset all metrics."""
        self._attempts.clear()
        self._successes.clear()
        self._failures.clear()
        self._retries.clear()
        self._fallbacks.clear()
        self._recovery_times.clear()
        self._errors_by_category.clear()


# Global metrics instance
_global_metrics: RecoveryMetrics | None = None


def get_recovery_metrics() -> RecoveryMetrics:
    """Get global recovery metrics instance."""
    global _global_metrics
    if _global_metrics is None:
        _global_metrics = RecoveryMetrics()
    return _global_metrics


def reset_recovery_metrics() -> None:
    """Reset global recovery metrics."""
    global _global_metrics
    if _global_metrics is not None:
        _global_metrics.reset()


class RecoveryStrategy(Enum):
    """Recovery strategy for failed agent executions."""

    RETRY_SAME = "retry_same"  # Retry same agent, no fallback
    FALLBACK_ONLY = "fallback_only"  # Skip retries, go to LLM
    RETRY_THEN_FALLBACK = "retry_then_fallback"  # Retry, then fallback (default)
    NO_RECOVERY = "no_recovery"  # Fail immediately


@dataclass
class RecoveryPolicy:
    """Recovery policy configuration for agent execution.

    Simple configuration for how to handle agent failures during parallel execution.

    Example - Default recovery (retry then fallback):
        >>> policy = RecoveryPolicy()
        >>> policy.max_retries
        2
        >>> policy.fallback_to_llm
        True

    Example - Aggressive retry without fallback:
        >>> policy = RecoveryPolicy.aggressive_retry()
        >>> policy.max_retries
        5
        >>> policy.fallback_to_llm
        False

    Example - Fast fallback for time-sensitive tasks:
        >>> policy = RecoveryPolicy.fast_fallback()
        >>> policy.max_retries
        0
        >>> policy.fallback_to_llm
        True
    """

    strategy: RecoveryStrategy = RecoveryStrategy.RETRY_THEN_FALLBACK
    max_retries: int = 2
    fallback_to_llm: bool = True
    base_delay: float = 1.0  # Base delay between retries (seconds)
    max_delay: float = 30.0  # Maximum delay cap
    backoff_factor: float = 2.0  # Exponential backoff multiplier
    jitter: bool = True  # Add randomness to prevent thundering herd
    circuit_breaker_enabled: bool = True  # Use circuit breaker

    # Recovery callbacks
    on_retry: Callable[[str, int, str], None] | None = None
    on_fallback: Callable[[str, str], None] | None = None
    on_recovery_failed: Callable[[str, str], None] | None = None

    # Per-agent overrides
    agent_overrides: dict[str, "RecoveryPolicy"] = field(default_factory=dict)

    # Error classifier for smart recovery decisions
    error_classifier: ErrorClassifier = field(default_factory=ErrorClassifier)

    # Metrics tracking
    track_metrics: bool = True

    def __post_init__(self) -> None:
        """Apply strategy presets to fields."""
        if self.strategy == RecoveryStrategy.RETRY_SAME:
            self.fallback_to_llm = False
        elif self.strategy == RecoveryStrategy.FALLBACK_ONLY:
            self.max_retries = 0
            self.fallback_to_llm = True
        elif self.strategy == RecoveryStrategy.NO_RECOVERY:
            self.max_retries = 0
            self.fallback_to_llm = False

    def get_for_agent(self, agent_id: str) -> "RecoveryPolicy":
        """Get recovery policy for specific agent, with overrides.

        Args:
            agent_id: Agent identifier

        Returns:
            RecoveryPolicy (override if exists, else self)

        """
        return self.agent_overrides.get(agent_id, self)

    def with_override(self, agent_id: str, **kwargs: Any) -> "RecoveryPolicy":
        """Create new policy with agent-specific override.

        Args:
            agent_id: Agent to override
            **kwargs: Override values

        Returns:
            New RecoveryPolicy with override applied

        """
        # Create override policy
        override_dict = {
            "strategy": self.strategy,
            "max_retries": self.max_retries,
            "fallback_to_llm": self.fallback_to_llm,
            "base_delay": self.base_delay,
            "max_delay": self.max_delay,
            "backoff_factor": self.backoff_factor,
            "jitter": self.jitter,
            "circuit_breaker_enabled": self.circuit_breaker_enabled,
        }
        override_dict.update(kwargs)
        override = RecoveryPolicy(**override_dict)

        # Copy current policy with new override
        new_overrides = dict(self.agent_overrides)
        new_overrides[agent_id] = override

        return RecoveryPolicy(
            strategy=self.strategy,
            max_retries=self.max_retries,
            fallback_to_llm=self.fallback_to_llm,
            base_delay=self.base_delay,
            max_delay=self.max_delay,
            backoff_factor=self.backoff_factor,
            jitter=self.jitter,
            circuit_breaker_enabled=self.circuit_breaker_enabled,
            on_retry=self.on_retry,
            on_fallback=self.on_fallback,
            on_recovery_failed=self.on_recovery_failed,
            agent_overrides=new_overrides,
        )

    def get_delay(self, attempt: int) -> float:
        """Calculate delay before retry attempt.

        Args:
            attempt: Zero-indexed retry attempt number

        Returns:
            Delay in seconds

        """
        delay = self.base_delay * (self.backoff_factor**attempt)
        delay = min(delay, self.max_delay)

        if self.jitter and delay > 0:
            import random

            jitter_amount = delay * 0.1  # +/- 10%
            delay += random.uniform(-jitter_amount, jitter_amount)

        return max(0.0, delay)

    @classmethod
    def default(cls) -> "RecoveryPolicy":
        """Default balanced recovery policy."""
        return cls(
            strategy=RecoveryStrategy.RETRY_THEN_FALLBACK,
            max_retries=2,
            fallback_to_llm=True,
            base_delay=1.0,
            max_delay=30.0,
            backoff_factor=2.0,
            jitter=True,
        )

    @classmethod
    def aggressive_retry(cls) -> "RecoveryPolicy":
        """Aggressive retry without fallback - for critical agent tasks."""
        return cls(
            strategy=RecoveryStrategy.RETRY_SAME,
            max_retries=5,
            fallback_to_llm=False,
            base_delay=0.5,
            max_delay=60.0,
            backoff_factor=2.0,
            jitter=True,
        )

    @classmethod
    def fast_fallback(cls) -> "RecoveryPolicy":
        """Fast fallback - skip retries for time-sensitive tasks."""
        return cls(
            strategy=RecoveryStrategy.FALLBACK_ONLY,
            max_retries=0,
            fallback_to_llm=True,
        )

    @classmethod
    def no_recovery(cls) -> "RecoveryPolicy":
        """No recovery - fail immediately on first error."""
        return cls(
            strategy=RecoveryStrategy.NO_RECOVERY,
            max_retries=0,
            fallback_to_llm=False,
        )

    @classmethod
    def patient(cls) -> "RecoveryPolicy":
        """Patient recovery - longer delays, more retries."""
        return cls(
            strategy=RecoveryStrategy.RETRY_THEN_FALLBACK,
            max_retries=3,
            fallback_to_llm=True,
            base_delay=2.0,
            max_delay=120.0,
            backoff_factor=3.0,
            jitter=True,
        )

    @classmethod
    def from_name(cls, name: str) -> "RecoveryPolicy":
        """Create policy from preset name.

        Args:
            name: One of: default, aggressive_retry, fast_fallback, no_recovery, patient

        Returns:
            RecoveryPolicy instance

        Raises:
            ValueError: If name is not a valid preset

        """
        presets = {
            "default": cls.default,
            "aggressive_retry": cls.aggressive_retry,
            "fast_fallback": cls.fast_fallback,
            "no_recovery": cls.no_recovery,
            "patient": cls.patient,
        }

        if name not in presets:
            raise ValueError(
                f"Unknown recovery preset '{name}'. Available: {', '.join(presets.keys())}",
            )

        return presets[name]()

    def should_retry_error(self, error_text: str) -> bool:
        """Check if error is worth retrying based on classification.

        Args:
            error_text: Error message to evaluate

        Returns:
            True if error is retriable

        """
        category = self.error_classifier.classify(error_text)
        return self.error_classifier.should_retry(category)

    def classify_error(self, error_text: str) -> ErrorCategory:
        """Classify an error message.

        Args:
            error_text: Error message to classify

        Returns:
            ErrorCategory

        """
        return self.error_classifier.classify(error_text)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "strategy": self.strategy.value,
            "max_retries": self.max_retries,
            "fallback_to_llm": self.fallback_to_llm,
            "base_delay": self.base_delay,
            "max_delay": self.max_delay,
            "backoff_factor": self.backoff_factor,
            "jitter": self.jitter,
            "circuit_breaker_enabled": self.circuit_breaker_enabled,
            "track_metrics": self.track_metrics,
            "agent_overrides": {
                agent: policy.to_dict() for agent, policy in self.agent_overrides.items()
            },
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "RecoveryPolicy":
        """Create policy from dictionary.

        Args:
            data: Dictionary with policy configuration

        Returns:
            RecoveryPolicy instance

        Example:
            >>> policy = RecoveryPolicy.from_dict({
            ...     "strategy": "retry_then_fallback",
            ...     "max_retries": 3,
            ...     "fallback_to_llm": True,
            ... })

        """
        # Parse strategy
        strategy_value = data.get("strategy", "retry_then_fallback")
        if isinstance(strategy_value, str):
            strategy = RecoveryStrategy(strategy_value)
        else:
            strategy = strategy_value

        # Parse agent overrides
        agent_overrides = {}
        for agent_id, override_data in data.get("agent_overrides", {}).items():
            if isinstance(override_data, dict):
                agent_overrides[agent_id] = cls.from_dict(override_data)

        return cls(
            strategy=strategy,
            max_retries=data.get("max_retries", 2),
            fallback_to_llm=data.get("fallback_to_llm", True),
            base_delay=data.get("base_delay", 1.0),
            max_delay=data.get("max_delay", 30.0),
            backoff_factor=data.get("backoff_factor", 2.0),
            jitter=data.get("jitter", True),
            circuit_breaker_enabled=data.get("circuit_breaker_enabled", True),
            track_metrics=data.get("track_metrics", True),
            agent_overrides=agent_overrides,
        )

    @classmethod
    def from_config(cls, config: dict[str, Any]) -> "RecoveryPolicy":
        """Create policy from Aurora config dictionary.

        Reads from config["spawner"]["recovery"] if present.

        Args:
            config: Aurora configuration dictionary

        Returns:
            RecoveryPolicy instance

        Example:
            >>> config = {
            ...     "spawner": {
            ...         "recovery": {
            ...             "max_retries": 3,
            ...             "fallback_to_llm": True,
            ...             "agent_overrides": {
            ...                 "slow-agent": {"max_retries": 5}
            ...             }
            ...         }
            ...     }
            ... }
            >>> policy = RecoveryPolicy.from_config(config)

        """
        recovery_config = config.get("spawner", {}).get("recovery", {})

        if not recovery_config:
            return cls.default()

        # Check for preset name
        if "preset" in recovery_config:
            base_policy = cls.from_name(recovery_config["preset"])
            # Apply any overrides on top of preset
            if len(recovery_config) > 1:
                override_data = {k: v for k, v in recovery_config.items() if k != "preset"}
                return base_policy._with_overrides(override_data)
            return base_policy

        return cls.from_dict(recovery_config)

    def _with_overrides(self, overrides: dict[str, Any]) -> "RecoveryPolicy":
        """Apply overrides to current policy.

        Args:
            overrides: Dictionary of override values

        Returns:
            New RecoveryPolicy with overrides applied

        """
        current = self.to_dict()
        current.update(overrides)
        return RecoveryPolicy.from_dict(current)


@dataclass
class RecoveryResult:
    """Result of recovery attempt for a single task."""

    task_index: int
    agent_id: str
    success: bool
    attempts: int  # Total attempts including initial
    used_fallback: bool
    final_error: str | None = None
    recovery_path: list[str] = field(default_factory=list)  # ["retry:1", "retry:2", "fallback"]

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "task_index": self.task_index,
            "agent_id": self.agent_id,
            "success": self.success,
            "attempts": self.attempts,
            "used_fallback": self.used_fallback,
            "final_error": self.final_error,
            "recovery_path": self.recovery_path,
        }


@dataclass
class RecoverySummary:
    """Summary of recovery outcomes for a batch of tasks."""

    total_tasks: int
    succeeded: int
    failed: int
    recovered: int  # Tasks that succeeded after retry/fallback
    used_fallback: int
    total_retry_attempts: int
    results: list[RecoveryResult] = field(default_factory=list)

    @property
    def success_rate(self) -> float:
        """Calculate success rate as percentage."""
        if self.total_tasks == 0:
            return 0.0
        return (self.succeeded / self.total_tasks) * 100

    @property
    def recovery_rate(self) -> float:
        """Calculate recovery rate (tasks recovered vs tasks that needed recovery)."""
        tasks_needing_recovery = self.recovered + self.failed
        if tasks_needing_recovery == 0:
            return 100.0  # All succeeded on first try
        return (self.recovered / tasks_needing_recovery) * 100

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "total_tasks": self.total_tasks,
            "succeeded": self.succeeded,
            "failed": self.failed,
            "recovered": self.recovered,
            "used_fallback": self.used_fallback,
            "total_retry_attempts": self.total_retry_attempts,
            "success_rate": self.success_rate,
            "recovery_rate": self.recovery_rate,
            "results": [r.to_dict() for r in self.results],
        }
