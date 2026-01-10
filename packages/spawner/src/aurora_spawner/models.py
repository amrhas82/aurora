"""Models for aurora-spawner package."""

from dataclasses import dataclass
from typing import Any


@dataclass
class SpawnTask:
    """Task definition for spawning a subprocess."""

    prompt: str
    agent: str | None = None
    timeout: int = 300

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "prompt": self.prompt,
            "agent": self.agent,
            "timeout": self.timeout,
        }


@dataclass
class SpawnResult:
    """Result from spawning a subprocess."""

    success: bool
    output: str
    error: str | None
    exit_code: int

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "success": self.success,
            "output": self.output,
            "error": self.error,
            "exit_code": self.exit_code,
        }
