"""Custom exception hierarchy for the AURORA framework.

This module defines all custom exceptions used throughout AURORA, organized
in a clear hierarchy for proper error handling and user-friendly messaging.
"""


class AuroraError(Exception):
    """Base exception for all AURORA-specific errors.

    All custom exceptions in the AURORA framework inherit from this base class,
    allowing for catch-all error handling when needed.
    """

    def __init__(self, message: str, details: str | None = None):
        """Initialize an AURORA error.

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
    """Raised when storage operations fail.

    Examples:
        - Database connection failures
        - Write/read errors
        - Transaction rollback failures
        - Disk space issues

    """


class ParseError(AuroraError):
    """Raised when code parsing fails.

    Examples:
        - Invalid syntax in source file
        - Unsupported language
        - Tree-sitter parsing failures
        - Malformed AST structures

    """


class ConfigurationError(AuroraError):
    """Raised when configuration is invalid or missing.

    Examples:
        - Missing required configuration keys
        - Invalid configuration values
        - Schema validation failures
        - Conflicting configuration settings

    """


class ValidationError(AuroraError):
    """Raised when data validation fails.

    Examples:
        - Invalid chunk structure
        - Out-of-range values
        - Missing required fields
        - Type mismatches

    """


class ChunkNotFoundError(StorageError):
    """Raised when a requested chunk cannot be found in storage.

    This is a specialized storage error for missing chunks, allowing
    callers to distinguish between "not found" and other storage failures.
    """

    def __init__(self, chunk_id: str):
        """Initialize a chunk not found error.

        Args:
            chunk_id: The ID of the chunk that was not found

        """
        message = f"Chunk not found: {chunk_id}"
        super().__init__(message)
        self.chunk_id = chunk_id


class SchemaMismatchError(StorageError):
    """Raised when the database schema version does not match the expected version.

    This error indicates that the database was created with an older version
    of AURORA and needs to be migrated or reset before use.

    Examples:
        - Old database with 7-column chunks table vs new 9-column schema
        - Missing schema_version table in legacy databases
        - Schema version in database lower than current SCHEMA_VERSION

    """

    def __init__(
        self,
        found_version: int,
        expected_version: int,
        db_path: str | None = None,
    ):
        """Initialize a schema mismatch error.

        Args:
            found_version: The schema version found in the database
            expected_version: The schema version required by the application
            db_path: Optional path to the database file

        """
        self.found_version = found_version
        self.expected_version = expected_version
        self.db_path = db_path

        message = f"Database schema outdated (v{found_version} found, v{expected_version} required)"
        details = (
            "The database was created with an older version of AURORA. "
            "Run 'aur init' to reset the database and re-index your codebase."
        )
        if db_path:
            details += f"\nDatabase path: {db_path}"

        super().__init__(message, details)


class FatalError(AuroraError):
    """Raised when a fatal error occurs that requires immediate termination.

    Examples:
        - Storage corruption
        - Critical configuration missing
        - System resource exhaustion

    These errors should fail fast with recovery instructions.

    """

    def __init__(self, message: str, recovery_hint: str | None = None):
        """Initialize a fatal error.

        Args:
            message: User-friendly error message
            recovery_hint: Optional hint for how to recover

        """
        details = f"Recovery: {recovery_hint}" if recovery_hint else None
        super().__init__(message, details)
        self.recovery_hint = recovery_hint


class BudgetExceededError(AuroraError):
    """Raised when a query would exceed budget limits.

    Examples:
        - Monthly budget limit reached
        - Single query exceeds cost threshold
        - Cost estimation indicates budget overrun

    These errors allow the system to gracefully reject expensive queries.

    """

    def __init__(
        self,
        message: str,
        consumed_usd: float,
        limit_usd: float,
        estimated_cost: float,
    ):
        """Initialize a budget exceeded error.

        Args:
            message: User-friendly error message
            consumed_usd: Amount of budget already consumed
            limit_usd: Budget limit
            estimated_cost: Estimated cost of the rejected query

        """
        super().__init__(message)
        self.consumed_usd = consumed_usd
        self.limit_usd = limit_usd
        self.estimated_cost = estimated_cost


__all__ = [
    "AuroraError",
    "StorageError",
    "ParseError",
    "ConfigurationError",
    "ValidationError",
    "ChunkNotFoundError",
    "SchemaMismatchError",
    "FatalError",
    "BudgetExceededError",
]
