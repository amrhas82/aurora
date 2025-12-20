"""
Custom exception hierarchy for the AURORA framework.

This module defines all custom exceptions used throughout AURORA, organized
in a clear hierarchy for proper error handling and user-friendly messaging.
"""

from typing import Optional


class AuroraError(Exception):
    """
    Base exception for all AURORA-specific errors.

    All custom exceptions in the AURORA framework inherit from this base class,
    allowing for catch-all error handling when needed.
    """

    def __init__(self, message: str, details: Optional[str] = None):
        """
        Initialize an AURORA error.

        Args:
            message: User-friendly error message
            details: Optional technical details for debugging
        """
        self.message = message
        self.details = details
        super().__init__(message)

    def __str__(self) -> str:
        if self.details:
            return f"{self.message}\nDetails: {self.details}"
        return self.message


class StorageError(AuroraError):
    """
    Raised when storage operations fail.

    Examples:
        - Database connection failures
        - Write/read errors
        - Transaction rollback failures
        - Disk space issues
    """
    pass


class ParseError(AuroraError):
    """
    Raised when code parsing fails.

    Examples:
        - Invalid syntax in source file
        - Unsupported language
        - Tree-sitter parsing failures
        - Malformed AST structures
    """
    pass


class ConfigurationError(AuroraError):
    """
    Raised when configuration is invalid or missing.

    Examples:
        - Missing required configuration keys
        - Invalid configuration values
        - Schema validation failures
        - Conflicting configuration settings
    """
    pass


class ValidationError(AuroraError):
    """
    Raised when data validation fails.

    Examples:
        - Invalid chunk structure
        - Out-of-range values
        - Missing required fields
        - Type mismatches
    """
    pass


class ChunkNotFoundError(StorageError):
    """
    Raised when a requested chunk cannot be found in storage.

    This is a specialized storage error for missing chunks, allowing
    callers to distinguish between "not found" and other storage failures.
    """

    def __init__(self, chunk_id: str):
        """
        Initialize a chunk not found error.

        Args:
            chunk_id: The ID of the chunk that was not found
        """
        message = f"Chunk not found: {chunk_id}"
        super().__init__(message)
        self.chunk_id = chunk_id


class FatalError(AuroraError):
    """
    Raised when a fatal error occurs that requires immediate termination.

    Examples:
        - Storage corruption
        - Critical configuration missing
        - System resource exhaustion

    These errors should fail fast with recovery instructions.
    """

    def __init__(self, message: str, recovery_hint: Optional[str] = None):
        """
        Initialize a fatal error.

        Args:
            message: User-friendly error message
            recovery_hint: Optional hint for how to recover
        """
        details = f"Recovery: {recovery_hint}" if recovery_hint else None
        super().__init__(message, details)
        self.recovery_hint = recovery_hint


__all__ = [
    'AuroraError',
    'StorageError',
    'ParseError',
    'ConfigurationError',
    'ValidationError',
    'ChunkNotFoundError',
    'FatalError',
]
