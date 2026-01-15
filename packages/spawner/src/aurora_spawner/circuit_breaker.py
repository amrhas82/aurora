"""Circuit breaker pattern for agent spawning.

Tracks agent failures and skips known-broken agents to fail fast.

States:
- CLOSED: Normal operation, allow spawns
- OPEN: Agent failing, skip spawns for reset_timeout seconds
- HALF_OPEN: Testing if agent recovered, allow one spawn
"""

import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, Tuple


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
    """Circuit breaker for agent spawning.

    Tracks failures per agent and opens circuit after threshold failures.
    After reset_timeout, allows one test request (half-open).
    Success closes circuit, failure reopens it.

    Example:
        >>> cb = CircuitBreaker(failure_threshold=2, reset_timeout=120)
        >>> cb.should_skip("agent-1")
        (False, "")
        >>> cb.record_failure("agent-1")
        >>> cb.record_failure("agent-1")
        >>> cb.should_skip("agent-1")
        (True, "Circuit open: 2 failures in last 120s")
    """

    def __init__(self, failure_threshold: int = 2, reset_timeout: float = 120.0):
        """Initialize circuit breaker.

        Args:
            failure_threshold: Number of failures to open circuit
            reset_timeout: Seconds before trying half-open state
        """
        self.failure_threshold = failure_threshold
        self.reset_timeout = reset_timeout
        self._circuits: dict[str, AgentCircuit] = {}

    def _get_circuit(self, agent_id: str) -> AgentCircuit:
        """Get or create circuit for agent."""
        if agent_id not in self._circuits:
            self._circuits[agent_id] = AgentCircuit()
        return self._circuits[agent_id]

    def record_failure(self, agent_id: str) -> None:
        """Record a failure for an agent.

        Args:
            agent_id: The agent that failed
        """
        circuit = self._get_circuit(agent_id)
        circuit.failure_count += 1
        circuit.last_failure_time = time.time()

        if circuit.failure_count >= self.failure_threshold:
            if circuit.state != CircuitState.OPEN:
                logger.warning(
                    f"Circuit OPEN for agent '{agent_id}': " f"{circuit.failure_count} failures"
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
                    f"Circuit HALF_OPEN for agent '{agent_id}': " f"testing after {elapsed:.0f}s"
                )
                circuit.state = CircuitState.HALF_OPEN
                circuit.last_attempt_time = now
                return False, ""  # Allow test request
            else:
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

    def get_status(self) -> dict[str, dict]:
        """Get status of all circuits.

        Returns:
            Dict mapping agent_id to circuit status
        """
        return {
            agent_id: {
                "state": circuit.state.value,
                "failure_count": circuit.failure_count,
                "last_failure": circuit.last_failure_time,
            }
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
