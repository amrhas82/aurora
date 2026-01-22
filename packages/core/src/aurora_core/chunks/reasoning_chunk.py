"""ReasoningChunk implementation for Phase 2 (SOAR Pipeline).

This module provides the full ReasoningChunk implementation for storing
reasoning patterns, decompositions, and execution traces in ACT-R memory.
"""

from dataclasses import dataclass, field
from typing import Any

from aurora_core.chunks.base import Chunk


@dataclass
class ReasoningChunk(Chunk):
    """Represents a reasoning pattern or decision trace.

    Attributes:
        pattern: Query pattern that triggered this reasoning (e.g., "implement feature X")
        complexity: Query complexity level (SIMPLE, MEDIUM, COMPLEX, CRITICAL)
        subgoals: List of subgoals in the decomposition
        execution_order: Execution order with parallelizable/sequential groups
        tools_used: List of tool types used during execution
        tool_sequence: Ordered list of tool invocations
        success_score: Overall success score [0.0, 1.0]
        metadata: Additional metadata (timing, agent info, etc.)

    """

    pattern: str = ""
    complexity: str = "SIMPLE"
    subgoals: list[dict[str, Any]] = field(default_factory=list)
    execution_order: list[dict[str, Any]] = field(default_factory=list)
    tools_used: list[str] = field(default_factory=list)
    tool_sequence: list[dict[str, Any]] = field(default_factory=list)
    success_score: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)

    def __init__(
        self,
        chunk_id: str,
        pattern: str,
        complexity: str = "SIMPLE",
        subgoals: list[dict[str, Any]] | None = None,
        execution_order: list[dict[str, Any]] | None = None,
        tools_used: list[str] | None = None,
        tool_sequence: list[dict[str, Any]] | None = None,
        success_score: float = 0.0,
        metadata: dict[str, Any] | None = None,
    ):
        """Initialize a ReasoningChunk.

        Args:
            chunk_id: Unique identifier for this chunk
            pattern: Query pattern that triggered this reasoning
            complexity: Query complexity level (SIMPLE, MEDIUM, COMPLEX, CRITICAL)
            subgoals: List of subgoals in the decomposition
            execution_order: Execution order with parallelizable/sequential groups
            tools_used: List of tool types used
            tool_sequence: Ordered list of tool invocations
            success_score: Overall success score [0.0, 1.0]
            metadata: Additional metadata

        """
        super().__init__(chunk_id=chunk_id, chunk_type="soar")

        self.pattern = pattern
        self.complexity = complexity
        self.subgoals = subgoals if subgoals is not None else []
        self.execution_order = execution_order if execution_order is not None else []
        self.tools_used = tools_used if tools_used is not None else []
        self.tool_sequence = tool_sequence if tool_sequence is not None else []
        self.success_score = success_score
        self.metadata = metadata if metadata is not None else {}

        # Validate on construction
        self.validate()

    def to_json(self) -> dict[str, Any]:
        """Serialize chunk to JSON-compatible dict.

        Returns:
            Dictionary in the format expected by the storage layer

        """
        return {
            "id": self.id,
            "type": "reasoning",
            "content": {
                "pattern": self.pattern,
                "complexity": self.complexity,
                "subgoals": self.subgoals,
                "execution_order": self.execution_order,
                "tools_used": self.tools_used,
                "tool_sequence": self.tool_sequence,
                "success_score": self.success_score,
            },
            "metadata": {
                "created_at": self.created_at.isoformat(),
                "last_modified": self.updated_at.isoformat(),
                **self.metadata,  # Include custom metadata
            },
        }

    @classmethod
    def from_json(cls, data: dict[str, Any]) -> "ReasoningChunk":
        """Deserialize chunk from JSON dict.

        Args:
            data: Dictionary containing chunk data

        Returns:
            Reconstructed ReasoningChunk instance

        Raises:
            ValueError: If required fields are missing

        """
        try:
            content = data["content"]
            metadata_dict = data.get("metadata", {})

            # Extract custom metadata (exclude standard fields)
            custom_metadata = {
                k: v for k, v in metadata_dict.items() if k not in ["created_at", "last_modified"]
            }

            return cls(
                chunk_id=data["id"],
                pattern=content.get("pattern", ""),
                complexity=content.get("complexity", "SIMPLE"),
                subgoals=content.get("subgoals", []),
                execution_order=content.get("execution_order", []),
                tools_used=content.get("tools_used", []),
                tool_sequence=content.get("tool_sequence", []),
                success_score=content.get("success_score", 0.0),
                metadata=custom_metadata,
            )

        except KeyError as e:
            raise ValueError(f"Missing required field in JSON data: {e}")
        except Exception as e:
            raise ValueError(f"Failed to deserialize ReasoningChunk: {e}")

    def validate(self) -> bool:
        """Validate chunk structure.

        Returns:
            True if valid

        Raises:
            ValueError: If validation fails

        """
        # Validate success_score range
        if not (0.0 <= self.success_score <= 1.0):
            raise ValueError(f"success_score must be in [0.0, 1.0], got {self.success_score}")

        # Validate pattern is not empty
        if not self.pattern or not self.pattern.strip():
            raise ValueError("pattern must not be empty")

        # Validate complexity level
        valid_complexities = ["SIMPLE", "MEDIUM", "COMPLEX", "CRITICAL"]
        if self.complexity not in valid_complexities:
            raise ValueError(
                f"complexity must be one of {valid_complexities}, got {self.complexity}",
            )

        # Validate subgoals structure
        if not isinstance(self.subgoals, list):
            raise ValueError(f"subgoals must be a list, got {type(self.subgoals)}")

        # Validate execution_order structure
        if not isinstance(self.execution_order, list):
            raise ValueError(f"execution_order must be a list, got {type(self.execution_order)}")

        # Validate tools_used is a list
        if not isinstance(self.tools_used, list):
            raise ValueError(f"tools_used must be a list, got {type(self.tools_used)}")

        # Validate tool_sequence is a list
        if not isinstance(self.tool_sequence, list):
            raise ValueError(f"tool_sequence must be a list, got {type(self.tool_sequence)}")

        return True

    def __repr__(self) -> str:
        """Return string representation."""
        return (
            f"ReasoningChunk(id={self.id}, pattern='{self.pattern[:50]}...', "
            f"complexity={self.complexity}, success_score={self.success_score:.2f}, "
            f"subgoals={len(self.subgoals)}, tools={len(self.tools_used)})"
        )


__all__ = ["ReasoningChunk"]
