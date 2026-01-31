"""Timeout and retry policy configuration for spawner.

Provides configurable policies for:
- Timeout thresholds (initial, progressive, maximum)
- Retry strategies (exponential backoff, fixed delay, immediate)
- Early termination conditions
- Policy presets for common scenarios
"""

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable

logger = logging.getLogger(__name__)


class RetryStrategy(Enum):
    """Retry strategy for failed spawns."""

    IMMEDIATE = "immediate"  # No delay between retries
    FIXED_DELAY = "fixed_delay"  # Fixed delay between retries
    EXPONENTIAL_BACKOFF = "exponential_backoff"  # Exponential backoff with jitter
    LINEAR_BACKOFF = "linear_backoff"  # Linear increase in delay


class TimeoutMode(Enum):
    """Timeout behavior mode."""

    FIXED = "fixed"  # Single fixed timeout
    PROGRESSIVE = "progressive"  # Start short, extend if activity detected
    ADAPTIVE = "adaptive"  # Adjust based on historical execution time


@dataclass
class RetryPolicy:
    """Retry policy configuration.

    Example:
        >>> policy = RetryPolicy(
        ...     max_attempts=3,
        ...     strategy=RetryStrategy.EXPONENTIAL_BACKOFF,
        ...     base_delay=1.0,
        ...     max_delay=60.0,
        ...     backoff_factor=2.0,
        ...     jitter=True
        ... )
        >>> policy.get_delay(0)  # First retry
        1.0
        >>> policy.get_delay(1)  # Second retry (2^1 * 1.0 = 2.0 + jitter)
        2.123

    """

    max_attempts: int = 3
    strategy: RetryStrategy = RetryStrategy.EXPONENTIAL_BACKOFF
    base_delay: float = 1.0  # Base delay in seconds
    max_delay: float = 60.0  # Maximum delay in seconds
    backoff_factor: float = 2.0  # Multiplier for exponential/linear backoff
    jitter: bool = True  # Add randomness to prevent thundering herd
    jitter_factor: float = 0.1  # ±10% jitter
    retry_on_timeout: bool = True  # Retry on timeout errors
    retry_on_error_patterns: bool = True  # Retry on matched error patterns
    circuit_breaker_enabled: bool = True  # Use circuit breaker to skip known failures

    def get_delay(self, attempt: int) -> float:
        """Calculate delay before retry attempt.

        Args:
            attempt: Zero-indexed retry attempt number

        Returns:
            Delay in seconds before next retry

        """
        if self.strategy == RetryStrategy.IMMEDIATE:
            delay = 0.0

        elif self.strategy == RetryStrategy.FIXED_DELAY:
            delay = self.base_delay

        elif self.strategy == RetryStrategy.EXPONENTIAL_BACKOFF:
            delay = self.base_delay * (self.backoff_factor**attempt)

        elif self.strategy == RetryStrategy.LINEAR_BACKOFF:
            delay = self.base_delay * (1 + self.backoff_factor * attempt)

        else:
            delay = 0.0

        # Cap at max_delay
        delay = min(delay, self.max_delay)

        # Add jitter if enabled
        if self.jitter and delay > 0:
            import random

            jitter_amount = delay * self.jitter_factor
            delay += random.uniform(-jitter_amount, jitter_amount)

        return max(0.0, delay)

    def should_retry(self, attempt: int, error_type: str | None = None) -> tuple[bool, str]:
        """Check if should retry given attempt number and error type.

        Args:
            attempt: Zero-indexed retry attempt number
            error_type: Type of error (e.g., "timeout", "error_pattern", "api_error")

        Returns:
            Tuple of (should_retry, reason)

        """
        if attempt >= self.max_attempts:
            return False, f"Max attempts ({self.max_attempts}) reached"

        if error_type == "timeout" and not self.retry_on_timeout:
            return False, "Retry on timeout disabled"

        if error_type == "error_pattern" and not self.retry_on_error_patterns:
            return False, "Retry on error patterns disabled"

        # Rate limits: Don't retry (quota won't reset for hours)
        if error_type == "rate_limit":
            return False, "Rate limit exceeded - quota exhausted, retries would fail"

        return True, ""


@dataclass
class TimeoutPolicy:
    """Timeout policy configuration.

    Example - Fixed timeout:
        >>> policy = TimeoutPolicy(mode=TimeoutMode.FIXED, timeout=300)

    Example - Progressive timeout:
        >>> policy = TimeoutPolicy(
        ...     mode=TimeoutMode.PROGRESSIVE,
        ...     initial_timeout=60,
        ...     max_timeout=300,
        ...     extension_threshold=10
        ... )
    """

    mode: TimeoutMode = TimeoutMode.PROGRESSIVE
    timeout: float = 300.0  # Fixed timeout (FIXED mode) or max timeout (others)
    initial_timeout: float = 60.0  # Initial timeout for PROGRESSIVE mode
    max_timeout: float = 300.0  # Maximum timeout for PROGRESSIVE/ADAPTIVE modes
    extension_threshold: float = 10.0  # Activity threshold in seconds for extension
    activity_check_interval: float = 0.5  # Check for activity every N seconds
    no_activity_timeout: float = 30.0  # Timeout if no activity for N seconds
    enable_heartbeat_extension: bool = True  # Extend timeout on heartbeat events

    # Adaptive mode parameters
    history_window: int = 10  # Number of recent executions to track
    percentile: float = 0.90  # Use 90th percentile as timeout estimate
    min_samples: int = 3  # Minimum samples before using adaptive timeout

    def get_initial_timeout(self) -> float:
        """Get initial timeout based on mode."""
        if self.mode == TimeoutMode.FIXED:
            return self.timeout
        if self.mode == TimeoutMode.PROGRESSIVE:
            return self.initial_timeout
        if self.mode == TimeoutMode.ADAPTIVE:
            # Start with initial timeout until we have history
            return self.initial_timeout
        return self.timeout

    def should_extend(self, _elapsed: float, last_activity: float, current_timeout: float) -> bool:
        """Check if timeout should be extended.

        Args:
            _elapsed: Total elapsed time since spawn start (reserved for future policy logic)
            last_activity: Time since last activity (stdout/stderr)
            current_timeout: Current timeout value

        Returns:
            True if timeout should be extended

        """
        if self.mode != TimeoutMode.PROGRESSIVE:
            return False

        # Don't extend beyond max
        if current_timeout >= self.max_timeout:
            return False

        # Extend if activity detected recently
        if last_activity < self.extension_threshold:
            return True

        return False

    def get_extended_timeout(self, current_timeout: float) -> float:
        """Get extended timeout value.

        Args:
            current_timeout: Current timeout value

        Returns:
            New extended timeout value

        """
        # Extend by 50% or to max, whichever is smaller
        extended = current_timeout * 1.5
        return min(extended, self.max_timeout)


@dataclass
class TerminationPolicy:
    """Early termination policy configuration.

    Controls when to kill a process early based on various signals:
    - Error patterns in stderr
    - Resource limits exceeded
    - No activity timeout
    - Custom termination predicates
    """

    enabled: bool = True
    kill_on_error_patterns: bool = True  # Kill immediately on error pattern match
    kill_on_no_activity: bool = True  # Kill if no activity for no_activity_timeout
    error_patterns: list[str] = field(
        default_factory=lambda: [
            r"rate.?limit",
            r"\b429\b",
            r"connection.?(refused|reset|error)",
            r"ECONNRESET",
            r"API.?error",
            r"authentication.?failed",
            r"model.?not.?available",
            r"quota.?exceeded",
            r"invalid.?api.?key",
            r"unauthorized",
            r"forbidden",
        ],
    )
    custom_predicates: list[Callable[[str, str], bool]] = field(default_factory=list)

    def should_terminate(
        self,
        stdout: str,
        stderr: str,
        _elapsed: float,
        _last_activity: float,
    ) -> tuple[bool, str]:
        """Check if process should be terminated early.

        Args:
            stdout: Current stdout content
            stderr: Current stderr content
            _elapsed: Total elapsed time (reserved for future termination logic)
            _last_activity: Time since last activity (reserved for future termination logic)

        Returns:
            Tuple of (should_terminate, reason)

        """
        if not self.enabled:
            return False, ""

        # Check error patterns in stderr
        if self.kill_on_error_patterns and stderr:
            import re

            for pattern in self.error_patterns:
                if re.search(pattern, stderr, re.IGNORECASE):
                    return True, f"Error pattern detected: {pattern}"

        # Check custom predicates
        for predicate in self.custom_predicates:
            if predicate(stdout, stderr):
                return True, "Custom termination condition met"

        return False, ""


@dataclass
class SpawnPolicy:
    """Complete spawn policy combining timeout, retry, and termination policies.

    Example - Production policy:
        >>> policy = SpawnPolicy.production()
        >>> policy.timeout_policy.mode
        <TimeoutMode.PROGRESSIVE: 'progressive'>
        >>> policy.retry_policy.max_attempts
        3

    Example - Fast fail policy:
        >>> policy = SpawnPolicy.fast_fail()
        >>> policy.timeout_policy.timeout
        60.0
        >>> policy.retry_policy.max_attempts
        1
    """

    name: str = "default"
    timeout_policy: TimeoutPolicy = field(default_factory=TimeoutPolicy)
    retry_policy: RetryPolicy = field(default_factory=RetryPolicy)
    termination_policy: TerminationPolicy = field(default_factory=TerminationPolicy)

    @classmethod
    def default(cls) -> "SpawnPolicy":
        """Default balanced policy."""
        return cls(
            name="default",
            timeout_policy=TimeoutPolicy(
                mode=TimeoutMode.PROGRESSIVE,
                initial_timeout=60.0,
                max_timeout=300.0,
                extension_threshold=10.0,
                no_activity_timeout=30.0,
            ),
            retry_policy=RetryPolicy(
                max_attempts=3,
                strategy=RetryStrategy.EXPONENTIAL_BACKOFF,
                base_delay=1.0,
                max_delay=60.0,
                backoff_factor=2.0,
                jitter=True,
            ),
            termination_policy=TerminationPolicy(
                enabled=True,
                kill_on_error_patterns=True,
                kill_on_no_activity=True,
            ),
        )

    @classmethod
    def production(cls) -> "SpawnPolicy":
        """Production policy: patient timeouts, robust retries."""
        return cls(
            name="production",
            timeout_policy=TimeoutPolicy(
                mode=TimeoutMode.PROGRESSIVE,
                initial_timeout=120.0,
                max_timeout=600.0,
                extension_threshold=15.0,
                no_activity_timeout=60.0,
            ),
            retry_policy=RetryPolicy(
                max_attempts=3,
                strategy=RetryStrategy.EXPONENTIAL_BACKOFF,
                base_delay=2.0,
                max_delay=120.0,
                backoff_factor=2.0,
                jitter=True,
            ),
            termination_policy=TerminationPolicy(
                enabled=True,
                kill_on_error_patterns=True,
                kill_on_no_activity=False,  # More patient in production
            ),
        )

    @classmethod
    def fast_fail(cls) -> "SpawnPolicy":
        """Fast fail policy: short timeouts, minimal retries."""
        return cls(
            name="fast_fail",
            timeout_policy=TimeoutPolicy(
                mode=TimeoutMode.FIXED,
                timeout=60.0,
                no_activity_timeout=15.0,
            ),
            retry_policy=RetryPolicy(
                max_attempts=1,
                strategy=RetryStrategy.IMMEDIATE,
                retry_on_timeout=False,
                retry_on_error_patterns=False,
            ),
            termination_policy=TerminationPolicy(
                enabled=True,
                kill_on_error_patterns=True,
                kill_on_no_activity=True,
            ),
        )

    @classmethod
    def patient(cls) -> "SpawnPolicy":
        """Patient policy: longer timeouts for agent execution that requires thinking."""
        return cls(
            name="patient",
            timeout_policy=TimeoutPolicy(
                mode=TimeoutMode.PROGRESSIVE,
                initial_timeout=120.0,  # 2 minutes initial
                max_timeout=600.0,  # 10 minutes max
                extension_threshold=10.0,
                no_activity_timeout=120.0,  # 2 minutes - agents can think without output
            ),
            retry_policy=RetryPolicy(
                max_attempts=2,  # One retry
                strategy=RetryStrategy.EXPONENTIAL_BACKOFF,
                base_delay=2.0,
                max_delay=30.0,
                backoff_factor=2.0,
            ),
            termination_policy=TerminationPolicy(
                enabled=True,
                kill_on_error_patterns=True,  # Still fail fast on errors
                kill_on_no_activity=False,  # Let LLMs think without killing
            ),
        )

    @classmethod
    def development(cls) -> "SpawnPolicy":
        """Development policy: very patient, useful for debugging."""
        return cls(
            name="development",
            timeout_policy=TimeoutPolicy(
                mode=TimeoutMode.FIXED,
                timeout=1800.0,  # 30 minutes
                no_activity_timeout=300.0,  # 5 minutes
            ),
            retry_policy=RetryPolicy(
                max_attempts=1,
                strategy=RetryStrategy.IMMEDIATE,
                circuit_breaker_enabled=False,  # Allow repeated attempts for debugging
            ),
            termination_policy=TerminationPolicy(
                enabled=False,  # Let developer observe failures
            ),
        )

    @classmethod
    def test(cls) -> "SpawnPolicy":
        """Test policy: short timeouts, no retries, fast feedback."""
        return cls(
            name="test",
            timeout_policy=TimeoutPolicy(
                mode=TimeoutMode.FIXED,
                timeout=30.0,
                no_activity_timeout=10.0,
            ),
            retry_policy=RetryPolicy(
                max_attempts=1,
                strategy=RetryStrategy.IMMEDIATE,
                retry_on_timeout=False,
                retry_on_error_patterns=False,
                circuit_breaker_enabled=False,
            ),
            termination_policy=TerminationPolicy(
                enabled=True,
                kill_on_error_patterns=True,
                kill_on_no_activity=True,
            ),
        )

    @classmethod
    def from_name(cls, name: str) -> "SpawnPolicy":
        """Create policy from preset name.

        Args:
            name: One of: default, production, fast_fail, patient, development, test

        Returns:
            SpawnPolicy instance

        Raises:
            ValueError: If name is not a valid preset

        """
        presets = {
            "default": cls.default,
            "production": cls.production,
            "fast_fail": cls.fast_fail,
            "patient": cls.patient,
            "development": cls.development,
            "test": cls.test,
        }

        if name not in presets:
            raise ValueError(
                f"Unknown policy preset '{name}'. Available: {', '.join(presets.keys())}",
            )

        return presets[name]()

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "name": self.name,
            "timeout": {
                "mode": self.timeout_policy.mode.value,
                "timeout": self.timeout_policy.timeout,
                "initial_timeout": self.timeout_policy.initial_timeout,
                "max_timeout": self.timeout_policy.max_timeout,
                "extension_threshold": self.timeout_policy.extension_threshold,
                "no_activity_timeout": self.timeout_policy.no_activity_timeout,
            },
            "retry": {
                "max_attempts": self.retry_policy.max_attempts,
                "strategy": self.retry_policy.strategy.value,
                "base_delay": self.retry_policy.base_delay,
                "max_delay": self.retry_policy.max_delay,
                "backoff_factor": self.retry_policy.backoff_factor,
                "jitter": self.retry_policy.jitter,
            },
            "termination": {
                "enabled": self.termination_policy.enabled,
                "kill_on_error_patterns": self.termination_policy.kill_on_error_patterns,
                "kill_on_no_activity": self.termination_policy.kill_on_no_activity,
            },
        }
