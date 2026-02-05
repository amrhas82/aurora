"""Circuit breaker pattern for agent spawning.

Tracks agent failures and skips known-broken agents to fail fast.

States:
- CLOSED: Normal operation, allow spawns
- OPEN: Agent failing, skip spawns for reset_timeout seconds
- HALF_OPEN: Testing if agent recovered, allow one spawn
"""

import logging
import time
from dataclasses import dataclass
from enum import Enum
from typing import Any


logger = logging.getLogger(__name__)


class CircuitState(Enum):
    """Circuit breaker states."""

    CLOSED = "closed"  # Normal - allow requests
    OPEN = "open"  # Failing - skip requests
    HALF_OPEN = "half_open"  # Testing - allow one request


@dataclass
class AgentCircuit:
    """Circuit state for a single agent."""

    state: CircuitState = CircuitState.CLOSED
    failure_count: int = 0
    last_failure_time: float = 0.0
    last_attempt_time: float = 0.0


class CircuitBreaker:
    """Circuit breaker for agent spawning with fast-fail semantics.

    Features:
    - Immediate failure detection before spawning
    - Failure velocity tracking for progressive circuit opening
    - Time-windowed failure analysis (recent failures matter more)
    - Graduated thresholds: warning -> half-open -> open
    - Fast-fail on repeated failures (no waiting for timeout)
    - Adhoc agent detection with specialized failure handling

    Tracks failures per agent and opens circuit after threshold failures.
    After reset_timeout, allows one test request (half-open).
    Success closes circuit, failure reopens it.

    Adhoc agents (dynamically generated) get more lenient treatment:
    - Higher failure threshold before circuit opens
    - Inference failures tracked separately from execution failures
    - Longer fast-fail window to allow retry backoff

    Example:
        >>> cb = CircuitBreaker(failure_threshold=2, reset_timeout=120)
        >>> cb.should_skip("agent-1")
        (False, "")
        >>> cb.record_failure("agent-1")
        >>> cb.record_failure("agent-1")
        >>> cb.should_skip("agent-1")
        (True, "Circuit open: 2 failures in last 120s")

    """

    def __init__(
        self,
        failure_threshold: int = 2,
        reset_timeout: float = 120.0,
        failure_window: float = 300.0,
        fast_fail_threshold: int = 2,  # Increased from 1 to 2 (requires 3 failures)
        adhoc_failure_threshold: int = 4,
        adhoc_fast_fail_window: float = 30.0,
    ):
        """Initialize circuit breaker.

        Args:
            failure_threshold: Number of failures to open circuit
            reset_timeout: Seconds before trying half-open state
            failure_window: Time window for counting recent failures (seconds)
            fast_fail_threshold: Consecutive failures to trigger immediate open (default: 2)
            adhoc_failure_threshold: Higher threshold for adhoc agents (default: 4)
            adhoc_fast_fail_window: Longer window for adhoc fast-fail detection (default: 30s)

        """
        self.failure_threshold = failure_threshold
        self.reset_timeout = reset_timeout
        self.failure_window = failure_window
        self.fast_fail_threshold = fast_fail_threshold
        self.adhoc_failure_threshold = adhoc_failure_threshold
        self.adhoc_fast_fail_window = adhoc_fast_fail_window
        self._circuits: dict[str, AgentCircuit] = {}
        self._failure_history: dict[str, list[float]] = {}  # agent_id -> timestamps
        self._adhoc_agents: set[str] = set()  # Track which agents are adhoc
        self._failure_types: dict[str, list[str]] = {}  # agent_id -> failure types

        # Permanent error types that should trigger fast-fail
        # These errors won't be fixed by retrying - agent/config is broken
        self._permanent_error_types = {
            "auth_error",  # Invalid API key, unauthorized
            "forbidden",  # 403 - insufficient permissions
            "invalid_model",  # Model identifier doesn't exist
            "invalid_request",  # 400 - malformed request
            "not_found",  # 404 - endpoint/resource doesn't exist
        }

    def _get_circuit(self, agent_id: str) -> AgentCircuit:
        """Get or create circuit for agent."""
        if agent_id not in self._circuits:
            self._circuits[agent_id] = AgentCircuit()
        return self._circuits[agent_id]

    def _is_adhoc_agent(self, agent_id: str) -> bool:
        """Check if agent is adhoc (dynamically generated).

        Adhoc agents are identified by naming patterns:
        - Contains 'adhoc' in name (case-insensitive)
        - Explicitly marked via mark_as_adhoc()
        - Contains 'generated' in name

        Args:
            agent_id: Agent identifier

        Returns:
            True if agent is adhoc

        """
        if agent_id in self._adhoc_agents:
            return True

        agent_lower = agent_id.lower()
        adhoc_indicators = ["adhoc", "ad-hoc", "generated", "dynamic", "inferred"]
        return any(indicator in agent_lower for indicator in adhoc_indicators)

    def mark_as_adhoc(self, agent_id: str) -> None:
        """Explicitly mark an agent as adhoc for specialized handling.

        Args:
            agent_id: Agent identifier to mark as adhoc

        """
        self._adhoc_agents.add(agent_id)
        logger.info(f"Agent '{agent_id}' marked as adhoc - using lenient circuit breaker policy")

    def record_failure(
        self,
        agent_id: str,
        fast_fail: bool = True,
        failure_type: str | None = None,
    ) -> None:
        """Record a failure for an agent with fast-fail logic and adhoc-aware handling.

        Args:
            agent_id: The agent that failed
            fast_fail: If True, open circuit immediately on consecutive failures
            failure_type: Type of failure (inference, timeout, error_pattern, crash, etc.)

        """
        # Rate limit failures should NOT trigger circuit breaker or fast-fail
        # The agent isn't broken - API quota is exhausted (external constraint)
        # Check this FIRST before tracking any failure state
        is_rate_limit = failure_type == "rate_limit"
        if is_rate_limit:
            logger.warning(
                f"Agent '{agent_id}' hit rate limit (quota exhausted) - "
                f"not opening circuit breaker (agent not broken, API quota issue)",
            )
            return  # Early exit - don't track as circuit breaker failure

        now = time.time()
        circuit = self._get_circuit(agent_id)
        circuit.failure_count += 1
        circuit.last_failure_time = now

        # Track failure type
        if failure_type:
            if agent_id not in self._failure_types:
                self._failure_types[agent_id] = []
            self._failure_types[agent_id].append(failure_type)
            # Keep only recent failure types (last 10)
            self._failure_types[agent_id] = self._failure_types[agent_id][-10:]

        # Track failure in history
        if agent_id not in self._failure_history:
            self._failure_history[agent_id] = []
        self._failure_history[agent_id].append(now)

        # Clean old failures outside window
        cutoff = now - self.failure_window
        self._failure_history[agent_id] = [t for t in self._failure_history[agent_id] if t > cutoff]

        recent_failures = len(self._failure_history[agent_id])

        # Determine if adhoc agent (use lenient policy)
        is_adhoc = self._is_adhoc_agent(agent_id)
        effective_threshold = self.adhoc_failure_threshold if is_adhoc else self.failure_threshold
        fast_fail_window = self.adhoc_fast_fail_window if is_adhoc else 10.0

        # Inference failures for adhoc agents should NOT trigger fast-fail
        # (allow retry backoff to work)
        is_inference_failure = failure_type == "inference"
        if is_adhoc and is_inference_failure:
            logger.debug(
                f"Adhoc agent '{agent_id}' inference failure #{recent_failures} "
                f"(threshold: {effective_threshold}, no fast-fail for inference)",
            )
            fast_fail = False

        # Only fast-fail on PERMANENT errors (auth, invalid model, etc.)
        # Transient errors (timeouts, 500s) should allow retries
        is_permanent_error = failure_type in self._permanent_error_types
        if not is_permanent_error and failure_type not in [None, "inference"]:
            logger.debug(
                f"Agent '{agent_id}' transient failure (type: {failure_type}) - "
                f"allowing retries (no fast-fail)",
            )
            fast_fail = False

        # Fast-fail logic: detect rapid consecutive failures WITH permanent errors
        if fast_fail and recent_failures >= self.fast_fail_threshold:
            # Check failure velocity - if multiple failures in short time, open immediately
            if len(self._failure_history[agent_id]) >= 2:
                time_between_failures = now - self._failure_history[agent_id][-2]
                if time_between_failures < fast_fail_window:
                    if circuit.state != CircuitState.OPEN:
                        agent_type = "adhoc agent" if is_adhoc else "agent"
                        logger.error(
                            f"Circuit OPEN (fast-fail) for {agent_type} '{agent_id}': "
                            f"{recent_failures} failures in {self.failure_window:.0f}s window, "
                            f"last 2 within {time_between_failures:.1f}s "
                            f"(fast-fail window: {fast_fail_window:.0f}s)",
                        )
                    circuit.state = CircuitState.OPEN
                    return

        # Standard threshold logic with adhoc-aware threshold
        if recent_failures >= effective_threshold:
            if circuit.state != CircuitState.OPEN:
                agent_type = "adhoc agent" if is_adhoc else "agent"
                logger.warning(
                    f"Circuit OPEN for {agent_type} '{agent_id}': "
                    f"{recent_failures} failures in {self.failure_window:.0f}s "
                    f"(threshold: {effective_threshold})",
                )
            circuit.state = CircuitState.OPEN

    def record_success(self, agent_id: str) -> None:
        """Record a success for an agent, closing the circuit.

        Args:
            agent_id: The agent that succeeded

        """
        circuit = self._get_circuit(agent_id)
        if circuit.state != CircuitState.CLOSED:
            logger.info(f"Circuit CLOSED for agent '{agent_id}': recovered")
        circuit.state = CircuitState.CLOSED
        circuit.failure_count = 0

        # Clear failure history on success
        if agent_id in self._failure_history:
            self._failure_history[agent_id].clear()

    def is_open(self, agent_id: str) -> bool:
        """Check if circuit is open (should skip).

        Args:
            agent_id: The agent to check

        Returns:
            True if circuit is open and agent should be skipped

        """
        skip, _ = self.should_skip(agent_id)
        return skip

    def should_skip(self, agent_id: str) -> tuple[bool, str]:
        """Check if agent should be skipped due to open circuit.

        Also handles state transitions:
        - OPEN -> HALF_OPEN after reset_timeout
        - HALF_OPEN allows one attempt

        Args:
            agent_id: The agent to check

        Returns:
            Tuple of (should_skip, reason)

        """
        circuit = self._get_circuit(agent_id)
        now = time.time()

        if circuit.state == CircuitState.CLOSED:
            return False, ""

        if circuit.state == CircuitState.OPEN:
            # Check if reset timeout elapsed
            elapsed = now - circuit.last_failure_time
            if elapsed >= self.reset_timeout:
                logger.info(
                    f"Circuit HALF_OPEN for agent '{agent_id}': testing after {elapsed:.0f}s",
                )
                circuit.state = CircuitState.HALF_OPEN
                circuit.last_attempt_time = now
                return False, ""  # Allow test request
            remaining = self.reset_timeout - elapsed
            return (
                True,
                f"Circuit open: {circuit.failure_count} failures, retry in {remaining:.0f}s",
            )

        if circuit.state == CircuitState.HALF_OPEN:
            # Only allow one test request
            if now - circuit.last_attempt_time < 1.0:
                # Already testing, skip additional requests
                return True, "Circuit half-open: test in progress"
            circuit.last_attempt_time = now
            return False, ""  # Allow test request

        return False, ""

    def reset(self, agent_id: str) -> None:
        """Reset circuit for an agent (manual override).

        Args:
            agent_id: The agent to reset

        """
        if agent_id in self._circuits:
            logger.info(f"Circuit RESET for agent '{agent_id}'")
            del self._circuits[agent_id]

    def reset_all(self) -> None:
        """Reset all circuits."""
        logger.info("All circuits RESET")
        self._circuits.clear()

    def get_failure_velocity(self, agent_id: str) -> float:
        """Calculate failure rate (failures per minute) for an agent.

        Args:
            agent_id: Agent to check

        Returns:
            Failures per minute over the failure window

        """
        if agent_id not in self._failure_history:
            return 0.0

        now = time.time()
        cutoff = now - self.failure_window
        recent_failures = [t for t in self._failure_history[agent_id] if t > cutoff]

        if len(recent_failures) < 2:
            return 0.0

        # Calculate failures per minute
        time_span = now - recent_failures[0]
        if time_span < 1.0:
            time_span = 1.0  # Avoid division by zero

        return (len(recent_failures) / time_span) * 60.0

    def get_health_status(self, agent_id: str) -> dict[str, Any]:
        """Get detailed health status including predictive signals.

        Args:
            agent_id: Agent to check

        Returns:
            Dict with health metrics and risk indicators

        """
        circuit = self._get_circuit(agent_id)
        now = time.time()
        cutoff = now - self.failure_window

        recent_failures = []
        if agent_id in self._failure_history:
            recent_failures = [t for t in self._failure_history[agent_id] if t > cutoff]

        failure_velocity = self.get_failure_velocity(agent_id)

        # Risk assessment
        risk_level = "low"
        if circuit.state == CircuitState.OPEN:
            risk_level = "critical"
        elif circuit.state == CircuitState.HALF_OPEN:
            risk_level = "high"
        elif len(recent_failures) >= self.failure_threshold - 1:
            risk_level = "medium"

        return {
            "agent_id": agent_id,
            "state": circuit.state.value,
            "failure_count": circuit.failure_count,
            "recent_failures": len(recent_failures),
            "failure_velocity": failure_velocity,
            "last_failure_time": circuit.last_failure_time,
            "time_since_last_failure": (
                now - circuit.last_failure_time if circuit.last_failure_time > 0 else None
            ),
            "risk_level": risk_level,
            "can_execute": circuit.state == CircuitState.CLOSED
            or circuit.state == CircuitState.HALF_OPEN,
        }

    def get_status(self) -> dict[str, dict]:
        """Get status of all circuits with enhanced metrics.

        Returns:
            Dict mapping agent_id to circuit status

        """
        return {
            agent_id: self.get_health_status(agent_id)
            for agent_id, circuit in self._circuits.items()
        }


# Module-level singleton
_default_circuit_breaker: CircuitBreaker | None = None


def get_circuit_breaker() -> CircuitBreaker:
    """Get the default circuit breaker singleton.

    Returns:
        The default CircuitBreaker instance

    """
    global _default_circuit_breaker
    if _default_circuit_breaker is None:
        _default_circuit_breaker = CircuitBreaker()
    return _default_circuit_breaker
