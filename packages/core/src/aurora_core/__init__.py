"""AURORA Core Package

Provides foundational components for the AURORA framework including:
- Storage layer (SQLite and in-memory implementations)
- Chunk types (CodeChunk, ReasoningChunk)
- Chunk type registry (extension and context-based type determination)
- Context management interfaces
- Configuration system
"""

from aurora_core.chunk_types import (
    CONTEXT_TYPE_MAP,
    EXTENSION_TYPE_MAP,
    VALID_TYPES,
    get_chunk_type,
)

__version__ = "0.1.0"

__all__ = [
    "EXTENSION_TYPE_MAP",
    "CONTEXT_TYPE_MAP",
    "VALID_TYPES",
    "get_chunk_type",
]
