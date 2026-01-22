"""CodeChunk implementation for representing parsed code elements.

This module provides the CodeChunk class for representing functions, classes,
and methods parsed from source code files.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from aurora_core.chunks.base import Chunk


@dataclass
class CodeChunk(Chunk):
    """Represents a parsed code element (function, class, method).

    This chunk type stores information about code elements extracted from
    source files, including location, dependencies, and complexity metrics.

    Attributes:
        file_path: Absolute path to source file
        element_type: Type of code element ("function", "class", "method")
        name: Name of the function/class/method
        line_start: Starting line number (1-indexed)
        line_end: Ending line number (inclusive)
        signature: Function signature if applicable
        docstring: Extracted docstring if present
        dependencies: List of chunk IDs this element depends on
        complexity_score: Cyclomatic complexity normalized to [0.0, 1.0]
        language: Programming language ("python", "typescript", "go", etc.)

    """

    file_path: str
    element_type: str
    name: str
    line_start: int
    line_end: int
    signature: str | None = None
    docstring: str | None = None
    dependencies: list[str] = field(default_factory=list)
    complexity_score: float = 0.0
    language: str = "python"
    embeddings: bytes | None = None
    metadata: dict[str, Any] | None = None

    def __init__(
        self,
        chunk_id: str,
        file_path: str,
        element_type: str,
        name: str,
        line_start: int,
        line_end: int,
        signature: str | None = None,
        docstring: str | None = None,
        dependencies: list[str] | None = None,
        complexity_score: float = 0.0,
        language: str = "python",
        embeddings: bytes | None = None,
        metadata: dict[str, Any] | None = None,
    ):
        """Initialize a CodeChunk.

        Args:
            chunk_id: Unique identifier for this chunk
            file_path: Absolute path to source file
            element_type: Type of element ("function", "class", "method")
            name: Name of the code element
            line_start: Starting line number (must be > 0)
            line_end: Ending line number (must be >= line_start)
            signature: Function signature (optional)
            docstring: Docstring text (optional)
            dependencies: List of chunk IDs this depends on
            complexity_score: Cyclomatic complexity (0.0-1.0)
            language: Programming language identifier

        Raises:
            ValueError: If validation fails

        """
        # Initialize base class
        super().__init__(chunk_id=chunk_id, chunk_type="code")

        # Set fields
        self.file_path = file_path
        self.element_type = element_type
        self.name = name
        self.line_start = line_start
        self.line_end = line_end
        self.signature = signature
        self.docstring = docstring
        self.dependencies = dependencies if dependencies is not None else []
        self.complexity_score = complexity_score
        self.language = language
        self.embeddings = embeddings
        self.metadata = metadata

        # Validate on construction
        self.validate()

    def to_json(self) -> dict[str, Any]:
        """Serialize chunk to JSON-compatible dict.

        Follows the schema defined in PRD Section 4.2.2.

        Returns:
            Dictionary in the format expected by the storage layer

        """
        # Base metadata
        metadata_dict = {
            "language": self.language,
            "created_at": self.created_at.isoformat(),
            "last_modified": self.updated_at.isoformat(),
        }

        # Include git metadata if available (commit_count, git_hash, last_modified timestamp)
        if hasattr(self, "metadata") and self.metadata:
            # Add git-specific metadata fields
            if "commit_count" in self.metadata:
                metadata_dict["commit_count"] = self.metadata["commit_count"]
            if "git_hash" in self.metadata:
                metadata_dict["git_hash"] = self.metadata["git_hash"]
            if "last_modified" in self.metadata:  # Git timestamp
                metadata_dict["git_last_modified"] = self.metadata["last_modified"]

        return {
            "id": self.id,
            "type": "code",
            "content": {
                "file": self.file_path,
                "function": self.name,
                "line_start": self.line_start,
                "line_end": self.line_end,
                "signature": self.signature,
                "docstring": self.docstring,
                "dependencies": self.dependencies,
                "ast_summary": {
                    "complexity": self.complexity_score,
                    "element_type": self.element_type,
                },
            },
            "metadata": metadata_dict,
        }

    @classmethod
    def from_json(cls, data: dict[str, Any]) -> "CodeChunk":
        """Deserialize chunk from JSON dict.

        Args:
            data: Dictionary containing chunk data in storage format

        Returns:
            Reconstructed CodeChunk instance

        Raises:
            ValueError: If required fields are missing or invalid

        """
        try:
            content = data["content"]
            metadata = data.get("metadata", {})
            ast_summary = content.get("ast_summary", {})

            # Create instance
            chunk = cls.__new__(cls)

            # Set base class fields
            chunk.id = data["id"]
            chunk.type = data["type"]

            # Parse timestamps if present
            if "created_at" in metadata:
                chunk.created_at = datetime.fromisoformat(metadata["created_at"])
            else:
                chunk.created_at = datetime.now(timezone.utc)

            if "last_modified" in metadata:
                chunk.updated_at = datetime.fromisoformat(metadata["last_modified"])
            else:
                chunk.updated_at = datetime.now(timezone.utc)

            # Set CodeChunk-specific fields
            chunk.file_path = content["file"]
            chunk.name = content["function"]
            chunk.line_start = content["line_start"]
            chunk.line_end = content["line_end"]
            chunk.signature = content.get("signature")
            chunk.docstring = content.get("docstring")
            chunk.dependencies = content.get("dependencies", [])
            chunk.complexity_score = ast_summary.get("complexity", 0.0)
            chunk.element_type = ast_summary.get("element_type", "function")
            chunk.language = metadata.get("language", "python")

            # Restore git metadata if present
            chunk.metadata = {}
            if "commit_count" in metadata:
                chunk.metadata["commit_count"] = metadata["commit_count"]
            if "git_hash" in metadata:
                chunk.metadata["git_hash"] = metadata["git_hash"]
            if "git_last_modified" in metadata:
                chunk.metadata["last_modified"] = metadata["git_last_modified"]

            # Validate reconstructed chunk
            chunk.validate()

            return chunk

        except KeyError as e:
            raise ValueError(f"Missing required field in JSON data: {e}")
        except Exception as e:
            raise ValueError(f"Failed to deserialize CodeChunk: {e}")

    def validate(self) -> bool:
        """Validate chunk structure and data.

        Validation rules:
        - line_start must be > 0
        - line_end must be >= line_start
        - file_path must be absolute
        - complexity_score must be in [0.0, 1.0]
        - element_type must be valid
        - name must not be empty

        Returns:
            True if valid

        Raises:
            ValueError: If validation fails with descriptive message

        """
        # Validate line numbers
        if self.line_start <= 0:
            raise ValueError(f"line_start must be > 0, got {self.line_start}")

        if self.line_end < self.line_start:
            raise ValueError(
                f"line_end ({self.line_end}) must be >= line_start ({self.line_start})",
            )

        # Validate file path is absolute
        if not Path(self.file_path).is_absolute():
            raise ValueError(
                f"file_path must be absolute, got '{self.file_path}'. "
                f"Convert relative paths to absolute before creating CodeChunk.",
            )

        # Validate complexity score range
        if not (0.0 <= self.complexity_score <= 1.0):
            raise ValueError(f"complexity_score must be in [0.0, 1.0], got {self.complexity_score}")

        # Validate element type
        valid_types = {"function", "class", "method", "knowledge", "document"}
        if self.element_type not in valid_types:
            raise ValueError(
                f"element_type must be one of {valid_types}, got '{self.element_type}'",
            )

        # Validate name is not empty
        if not self.name or not self.name.strip():
            raise ValueError("name must not be empty")

        # Validate language is not empty
        if not self.language or not self.language.strip():
            raise ValueError("language must not be empty")

        return True

    def __repr__(self) -> str:
        """Return detailed string representation."""
        return (
            f"CodeChunk(id={self.id}, file={self.file_path}, "
            f"element={self.element_type}, name={self.name}, "
            f"lines={self.line_start}-{self.line_end})"
        )


__all__ = ["CodeChunk"]
