"""
SQLite-based storage implementation for AURORA chunks.

This module provides a production-ready storage backend using SQLite with:
- Thread-safe connection pooling
- Transaction support with automatic rollback
- JSON validation and error handling
- Relationship graph traversal for spreading activation
"""

import sqlite3
import json
import threading
from pathlib import Path
from typing import List, Optional, Dict, Any
from datetime import datetime
from contextlib import contextmanager

from aurora_core.store.base import Store
from aurora_core.store.schema import get_init_statements
from aurora_core.types import ChunkID
from aurora_core.exceptions import (
    StorageError,
    ChunkNotFoundError,
    ValidationError,
)

# Forward reference for type checking
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from aurora_core.chunks.base import Chunk


class SQLiteStore(Store):
    """
    SQLite-based storage implementation with connection pooling.

    This implementation provides thread-safe storage with:
    - Connection per thread (thread-local storage)
    - Automatic schema initialization
    - Transaction support with rollback on errors
    - JSON serialization/deserialization
    - Relationship graph traversal

    Args:
        db_path: Path to SQLite database file (":memory:" for in-memory)
        timeout: Connection timeout in seconds (default: 5.0)
        wal_mode: Enable Write-Ahead Logging for better concurrency (default: True)
    """

    def __init__(
        self,
        db_path: str = "~/.aurora/memory.db",
        timeout: float = 5.0,
        wal_mode: bool = True
    ):
        """Initialize SQLite store with connection pooling."""
        # Expand user home directory in path
        self.db_path = str(Path(db_path).expanduser())
        self.timeout = timeout
        self.wal_mode = wal_mode

        # Thread-local storage for connections (one connection per thread)
        self._local = threading.local()

        # Create database directory if it doesn't exist
        if self.db_path != ":memory:":
            Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)

        # Initialize schema on first connection
        self._init_schema()

    def _get_connection(self) -> sqlite3.Connection:
        """
        Get or create a connection for the current thread.

        Returns:
            Thread-local SQLite connection
        """
        if not hasattr(self._local, 'connection') or self._local.connection is None:
            try:
                conn = sqlite3.connect(
                    self.db_path,
                    timeout=self.timeout,
                    check_same_thread=False
                )
                conn.row_factory = sqlite3.Row  # Enable column access by name

                # Enable WAL mode for better concurrency
                if self.wal_mode and self.db_path != ":memory:":
                    conn.execute("PRAGMA journal_mode=WAL")

                # Enable foreign keys
                conn.execute("PRAGMA foreign_keys=ON")

                self._local.connection = conn
            except sqlite3.Error as e:
                raise StorageError(
                    f"Failed to connect to database: {self.db_path}",
                    details=str(e)
                )

        return self._local.connection

    def _init_schema(self) -> None:
        """Initialize database schema if not exists."""
        conn = self._get_connection()
        try:
            for statement in get_init_statements():
                conn.execute(statement)
            conn.commit()
        except sqlite3.Error as e:
            raise StorageError(
                "Failed to initialize database schema",
                details=str(e)
            )

    @contextmanager
    def _transaction(self):
        """
        Context manager for database transactions with automatic rollback.

        Usage:
            with store._transaction():
                # Database operations here
                pass
        """
        conn = self._get_connection()
        try:
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise StorageError(
                "Transaction failed and was rolled back",
                details=str(e)
            )

    def save_chunk(self, chunk: 'Chunk') -> bool:
        """
        Save a chunk to storage with validation.

        Args:
            chunk: The chunk to save

        Returns:
            True if save was successful

        Raises:
            StorageError: If storage operation fails
            ValidationError: If chunk validation fails
        """
        # Validate chunk before saving
        try:
            chunk.validate()
        except ValueError as e:
            raise ValidationError(
                f"Chunk validation failed: {chunk.id}",
                details=str(e)
            )

        # Serialize chunk to JSON
        try:
            chunk_json = chunk.to_json()
        except Exception as e:
            raise ValidationError(
                f"Failed to serialize chunk: {chunk.id}",
                details=str(e)
            )

        with self._transaction() as conn:
            try:
                # Insert or replace chunk
                conn.execute(
                    """
                    INSERT OR REPLACE INTO chunks (id, type, content, metadata, updated_at)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        chunk.id,
                        chunk.type,
                        json.dumps(chunk_json.get('content', {})),
                        json.dumps(chunk_json.get('metadata', {})),
                        datetime.utcnow().isoformat()
                    )
                )

                # Initialize activation record if not exists
                conn.execute(
                    """
                    INSERT OR IGNORE INTO activations (chunk_id, base_level, last_access, access_count)
                    VALUES (?, ?, ?, ?)
                    """,
                    (
                        chunk.id,
                        0.0,  # Initial activation
                        datetime.utcnow().isoformat(),
                        0
                    )
                )

                return True
            except sqlite3.Error as e:
                raise StorageError(
                    f"Failed to save chunk: {chunk.id}",
                    details=str(e)
                )

    def get_chunk(self, chunk_id: ChunkID) -> Optional['Chunk']:
        """
        Retrieve a chunk by ID.

        Args:
            chunk_id: The chunk ID to retrieve

        Returns:
            The chunk if found, None otherwise

        Raises:
            StorageError: If storage operation fails
        """
        conn = self._get_connection()
        try:
            cursor = conn.execute(
                """
                SELECT id, type, content, metadata, created_at, updated_at
                FROM chunks
                WHERE id = ?
                """,
                (chunk_id,)
            )
            row = cursor.fetchone()

            if row is None:
                return None

            # Deserialize chunk (will be implemented when Chunk classes are ready)
            # For now, return the raw data as a dict
            # TODO: Implement proper deserialization once Chunk.from_json is available
            return self._deserialize_chunk(dict(row))

        except sqlite3.Error as e:
            raise StorageError(
                f"Failed to retrieve chunk: {chunk_id}",
                details=str(e)
            )

    def _deserialize_chunk(self, row_data: Dict[str, Any]) -> Optional['Chunk']:
        """
        Deserialize a chunk from database row.

        This is a placeholder that will be completed when Chunk classes
        are fully implemented.

        Args:
            row_data: Dictionary containing chunk data from database

        Returns:
            Deserialized Chunk object or None
        """
        # TODO: Implement proper deserialization based on chunk type
        # For now, return None as chunks aren't fully implemented yet
        return None

    def update_activation(self, chunk_id: ChunkID, delta: float) -> None:
        """
        Update activation score for a chunk.

        Args:
            chunk_id: The chunk to update
            delta: Amount to add to current activation

        Raises:
            StorageError: If storage operation fails
            ChunkNotFoundError: If chunk doesn't exist
        """
        with self._transaction() as conn:
            try:
                # Update activation and access metadata
                cursor = conn.execute(
                    """
                    UPDATE activations
                    SET base_level = base_level + ?,
                        last_access = ?,
                        access_count = access_count + 1
                    WHERE chunk_id = ?
                    """,
                    (delta, datetime.utcnow().isoformat(), chunk_id)
                )

                if cursor.rowcount == 0:
                    raise ChunkNotFoundError(str(chunk_id))

            except sqlite3.Error as e:
                raise StorageError(
                    f"Failed to update activation for chunk: {chunk_id}",
                    details=str(e)
                )

    def retrieve_by_activation(
        self,
        min_activation: float,
        limit: int
    ) -> List['Chunk']:
        """
        Retrieve chunks by activation threshold.

        Args:
            min_activation: Minimum activation score
            limit: Maximum number of chunks to return

        Returns:
            List of chunks ordered by activation (highest first)

        Raises:
            StorageError: If storage operation fails
        """
        conn = self._get_connection()
        try:
            cursor = conn.execute(
                """
                SELECT c.id, c.type, c.content, c.metadata, c.created_at, c.updated_at
                FROM chunks c
                JOIN activations a ON c.id = a.chunk_id
                WHERE a.base_level >= ?
                ORDER BY a.base_level DESC
                LIMIT ?
                """,
                (min_activation, limit)
            )

            chunks = []
            for row in cursor:
                chunk = self._deserialize_chunk(dict(row))
                if chunk is not None:
                    chunks.append(chunk)

            return chunks

        except sqlite3.Error as e:
            raise StorageError(
                "Failed to retrieve chunks by activation",
                details=str(e)
            )

    def add_relationship(
        self,
        from_id: ChunkID,
        to_id: ChunkID,
        rel_type: str,
        weight: float = 1.0
    ) -> bool:
        """
        Add a relationship between chunks.

        Args:
            from_id: Source chunk ID
            to_id: Target chunk ID
            rel_type: Relationship type
            weight: Relationship strength

        Returns:
            True if relationship was added

        Raises:
            StorageError: If storage operation fails
            ChunkNotFoundError: If either chunk doesn't exist
        """
        with self._transaction() as conn:
            try:
                # Verify both chunks exist
                cursor = conn.execute(
                    "SELECT COUNT(*) as cnt FROM chunks WHERE id IN (?, ?)",
                    (from_id, to_id)
                )
                count = cursor.fetchone()['cnt']
                if count < 2:
                    raise ChunkNotFoundError(
                        f"One or both chunks not found: {from_id}, {to_id}"
                    )

                # Insert relationship
                conn.execute(
                    """
                    INSERT INTO relationships (from_chunk, to_chunk, relationship_type, weight)
                    VALUES (?, ?, ?, ?)
                    """,
                    (from_id, to_id, rel_type, weight)
                )

                return True

            except sqlite3.Error as e:
                raise StorageError(
                    f"Failed to add relationship: {from_id} -> {to_id}",
                    details=str(e)
                )

    def get_related_chunks(
        self,
        chunk_id: ChunkID,
        max_depth: int = 2
    ) -> List['Chunk']:
        """
        Get related chunks via relationship graph traversal.

        Args:
            chunk_id: Starting chunk ID
            max_depth: Maximum traversal depth

        Returns:
            List of related chunks within max_depth hops

        Raises:
            StorageError: If storage operation fails
            ChunkNotFoundError: If starting chunk doesn't exist
        """
        conn = self._get_connection()

        # Use recursive CTE for graph traversal
        query = """
        WITH RECURSIVE related(chunk_id, depth) AS (
            -- Base case: direct relationships
            SELECT to_chunk, 1
            FROM relationships
            WHERE from_chunk = ?

            UNION

            -- Recursive case: follow relationships up to max_depth
            SELECT r.to_chunk, rel.depth + 1
            FROM relationships r
            JOIN related rel ON r.from_chunk = rel.chunk_id
            WHERE rel.depth < ?
        )
        SELECT DISTINCT c.id, c.type, c.content, c.metadata, c.created_at, c.updated_at
        FROM chunks c
        JOIN related r ON c.id = r.chunk_id
        """

        try:
            cursor = conn.execute(query, (chunk_id, max_depth))
            chunks = []
            for row in cursor:
                chunk = self._deserialize_chunk(dict(row))
                if chunk is not None:
                    chunks.append(chunk)

            return chunks

        except sqlite3.Error as e:
            raise StorageError(
                f"Failed to retrieve related chunks for: {chunk_id}",
                details=str(e)
            )

    def close(self) -> None:
        """
        Close database connection and cleanup.

        Raises:
            StorageError: If cleanup fails
        """
        if hasattr(self._local, 'connection') and self._local.connection is not None:
            try:
                self._local.connection.close()
                self._local.connection = None
            except sqlite3.Error as e:
                raise StorageError(
                    "Failed to close database connection",
                    details=str(e)
                )


__all__ = ['SQLiteStore']
