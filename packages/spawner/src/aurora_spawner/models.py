"""Models for aurora-spawner package."""

from dataclasses import dataclass
from typing import Any


@dataclass
class SpawnTask:
    """Task definition for spawning a subprocess."""

    prompt: str
    agent: str | None = None
    timeout: int = 300
    policy_name: str | None = None  # Optional policy preset name
    display_name: str | None = None  # For progress display (e.g., ad-hoc agent names)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "prompt": self.prompt,
            "agent": self.agent,
            "timeout": self.timeout,
            "policy_name": self.policy_name,
            "display_name": self.display_name,
        }


@dataclass
class SpawnResult:
    """Result from spawning a subprocess."""

    success: bool
    output: str
    error: str | None
    exit_code: int
    fallback: bool = False
    original_agent: str | None = None
    retry_count: int = 0
    termination_reason: str | None = None  # Why process was terminated early
    timeout_extended: bool = False  # Whether timeout was extended
    execution_time: float = 0.0  # Actual execution time in seconds

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "success": self.success,
            "output": self.output,
            "error": self.error,
            "exit_code": self.exit_code,
            "fallback": self.fallback,
            "original_agent": self.original_agent,
            "retry_count": self.retry_count,
            "termination_reason": self.termination_reason,
            "timeout_extended": self.timeout_extended,
            "execution_time": self.execution_time,
        }
