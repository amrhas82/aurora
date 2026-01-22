"""Task models for implement package.

ParsedTask extends the basic task tracking pattern from TaskProgress
with agent and model metadata for task execution.
"""

from dataclasses import dataclass
from typing import Any


@dataclass
class ParsedTask:
    """A parsed task from tasks.md with execution metadata.

    Extends basic task tracking with agent and model fields for dispatching
    tasks to specific agents with specific models.

    Attributes:
        id: Task identifier (e.g., "1", "1.1", "2.3")
        description: Task description text
        agent: Agent to execute task (default: "self" for direct execution)
        model: Model to use for execution (default: None, uses agent's default)
        completed: Whether task is completed (default: False)

    """

    id: str
    description: str
    agent: str = "self"
    model: str | None = None
    completed: bool = False

    def to_dict(self) -> dict[str, Any]:
        """Convert ParsedTask to dictionary representation.

        Returns:
            Dictionary with all task fields

        """
        return {
            "id": self.id,
            "description": self.description,
            "agent": self.agent,
            "model": self.model,
            "completed": self.completed,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ParsedTask":
        """Create ParsedTask from dictionary representation.

        Args:
            data: Dictionary with task fields (id and description required,
                  others optional with defaults)

        Returns:
            ParsedTask instance

        Raises:
            KeyError: If required fields (id, description) are missing

        """
        return cls(
            id=data["id"],
            description=data["description"],
            agent=data.get("agent", "self"),
            model=data.get("model"),
            completed=data.get("completed", False),
        )
