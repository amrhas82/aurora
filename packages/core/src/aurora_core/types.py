"""Shared type definitions for the AURORA Core package.

This module provides type aliases and base types used throughout the AURORA
framework for consistency and type safety.
"""

from datetime import datetime
from typing import Any, NewType


# Type aliases for improved readability and type safety
ChunkID = NewType("ChunkID", str)
"""Unique identifier for a chunk. Format: <type>_<hash> (e.g., 'code_abc123')"""

Activation = float
"""Activation score for a chunk, representing its relevance/importance (0.0-1.0)"""

# Base type for serializable chunk data
ChunkData = dict[str, Any]
"""JSON-compatible dictionary representing serialized chunk data"""

# Type alias for timestamps
Timestamp = datetime
"""UTC timestamp for tracking chunk creation/modification times"""

__all__ = [
    "ChunkID",
    "Activation",
    "ChunkData",
    "Timestamp",
]
