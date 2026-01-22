"""Base chunk interface for AURORA knowledge representation.

This module defines the abstract Chunk base class that all concrete chunk
types must implement.
"""

from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Any


class Chunk(ABC):
    """Base class for all AURORA chunks.

    A chunk represents a unit of knowledge in the AURORA system, such as:
    - Code elements (functions, classes, methods) - type: "code"
    - Knowledge documents (markdown, docs) - type: "kb"
    - SOAR reasoning patterns - type: "soar"

    All chunks must have a unique ID, type, and support serialization.
    """

    def __init__(self, chunk_id: str, chunk_type: str):
        """Initialize a chunk.

        Args:
            chunk_id: Unique identifier for this chunk
            chunk_type: Type of chunk ("code", "kb", "soar")

        """
        self.id = chunk_id
        self.type = chunk_type
        self.created_at = datetime.now(timezone.utc)
        self.updated_at = datetime.now(timezone.utc)

    @abstractmethod
    def to_json(self) -> dict[str, Any]:
        """Serialize chunk to JSON-compatible dict.

        Returns:
            Dictionary containing all chunk data in JSON-serializable format

        """

    @classmethod
    @abstractmethod
    def from_json(cls, data: dict[str, Any]) -> "Chunk":
        """Deserialize chunk from JSON dict.

        Args:
            data: Dictionary containing chunk data

        Returns:
            Reconstructed Chunk instance

        """

    @abstractmethod
    def validate(self) -> bool:
        """Validate chunk structure and data.

        Returns:
            True if valid

        Raises:
            ValueError: If chunk structure is invalid with descriptive message

        """

    def __repr__(self) -> str:
        """Return string representation of chunk."""
        return f"{self.__class__.__name__}(id={self.id}, type={self.type})"

    def __eq__(self, other: Any) -> bool:
        """Check equality based on chunk ID."""
        if not isinstance(other, Chunk):
            return False
        return self.id == other.id

    def __hash__(self) -> int:
        """Hash based on chunk ID for use in sets/dicts."""
        return hash(self.id)


__all__ = ["Chunk"]
