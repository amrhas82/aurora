"""
SQLite-based storage implementation for AURORA chunks.

This module provides a production-ready storage backend using SQLite with:
- Thread-safe connection pooling
- Transaction support with automatic rollback
- JSON validation and error handling
- Relationship graph traversal for spreading activation
"""

import json
import sqlite3
import threading
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path

# Forward reference for type checking
from typing import TYPE_CHECKING, Any, Optional, cast

from aurora_core.exceptions import (
    ChunkNotFoundError,
    StorageError,
    ValidationError,
)
from aurora_core.store.base import Store
from aurora_core.store.schema import get_init_statements
from aurora_core.types import ChunkID


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

        return cast(sqlite3.Connection, self._local.connection)

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
    def _transaction(self) -> Iterator[sqlite3.Connection]:
        """
        Context manager for database transactions with automatic rollback.

        Usage:
            with store._transaction():
                # Database operations here
                pass

        Yields:
            SQLite connection with transaction support
        """
        conn = self._get_connection()
        try:
            yield conn
            conn.commit()
        except ChunkNotFoundError:
            # Re-raise domain exceptions without wrapping
            conn.rollback()
            raise
        except ValidationError:
            # Re-raise domain exceptions without wrapping
            conn.rollback()
            raise
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
                # Get embeddings if available (optional field for semantic retrieval)
                embeddings = getattr(chunk, 'embeddings', None)

                # Insert or replace chunk
                conn.execute(
                    """
                    INSERT OR REPLACE INTO chunks (id, type, content, metadata, embeddings, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        chunk.id,
                        chunk.type,
                        json.dumps(chunk_json.get('content', {})),
                        json.dumps(chunk_json.get('metadata', {})),
                        embeddings,  # BLOB - numpy array bytes or None
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
                SELECT id, type, content, metadata, embeddings, created_at, updated_at
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

    def _deserialize_chunk(self, row_data: dict[str, Any]) -> Optional['Chunk']:
        """
        Deserialize a chunk from database row.

        Args:
            row_data: Dictionary containing chunk data from database

        Returns:
            Deserialized Chunk object or None

        Raises:
            StorageError: If deserialization fails
        """
        from aurora_core.chunks import CodeChunk, ReasoningChunk

        try:
            # Parse JSON fields
            content = json.loads(row_data['content'])
            metadata = json.loads(row_data['metadata'])

            # Reconstruct full JSON structure for from_json()
            full_data = {
                'id': row_data['id'],
                'type': row_data['type'],
                'content': content,
                'metadata': metadata
            }

            # Deserialize based on chunk type
            chunk_type = row_data['type']
            if chunk_type == 'code':
                chunk = CodeChunk.from_json(full_data)
            elif chunk_type == 'reasoning':
                chunk = ReasoningChunk.from_json(full_data)
            else:
                raise StorageError(
                    f"Unknown chunk type: {chunk_type}",
                    details=f"Cannot deserialize chunk {row_data['id']}"
                )

            # Restore embeddings if present (BLOB field for semantic retrieval)
            if 'embeddings' in row_data and row_data['embeddings'] is not None:
                chunk.embeddings = row_data['embeddings']

            return chunk

        except (KeyError, json.JSONDecodeError, ValueError) as e:
            raise StorageError(
                f"Failed to deserialize chunk: {row_data.get('id', 'unknown')}",
                details=str(e)
            )

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
    ) -> list['Chunk']:
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
                SELECT c.id, c.type, c.content, c.metadata, c.embeddings, c.created_at, c.updated_at
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
    ) -> list['Chunk']:
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

        # First check if the starting chunk exists
        try:
            cursor = conn.execute("SELECT id FROM chunks WHERE id = ?", (chunk_id,))
            if cursor.fetchone() is None:
                raise ChunkNotFoundError(str(chunk_id))
        except sqlite3.Error as e:
            raise StorageError(
                f"Failed to verify chunk existence: {chunk_id}",
                details=str(e)
            )

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
        SELECT DISTINCT c.id, c.type, c.content, c.metadata, c.embeddings, c.created_at, c.updated_at
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

    def record_access(
        self,
        chunk_id: ChunkID,
        access_time: Optional[datetime] = None,
        context: Optional[str] = None
    ) -> None:
        """
        Record an access to a chunk for ACT-R activation tracking.

        This method updates the chunk's access history in the activations table,
        which is used to calculate Base-Level Activation (BLA) based on frequency
        and recency of access.

        Args:
            chunk_id: The chunk that was accessed
            access_time: Timestamp of access (defaults to current time)
            context: Optional context information (e.g., query keywords)

        Raises:
            StorageError: If storage operation fails
            ChunkNotFoundError: If chunk_id does not exist
        """
        conn = self._get_connection()
        if access_time is None:
            access_time = datetime.now()

        try:
            # First check if chunk exists
            cursor = conn.execute("SELECT id FROM chunks WHERE id = ?", (chunk_id,))
            if cursor.fetchone() is None:
                raise ChunkNotFoundError(str(chunk_id))

            # Get current access history from activations table
            cursor = conn.execute(
                "SELECT access_history FROM activations WHERE chunk_id = ?",
                (chunk_id,)
            )
            row = cursor.fetchone()

            if row is None:
                # First access - initialize activation record
                access_history = [{"timestamp": access_time.isoformat(), "context": context}]
                conn.execute(
                    """INSERT INTO activations (chunk_id, base_level, last_access, access_count, access_history)
                       VALUES (?, 0.0, ?, 1, ?)""",
                    (chunk_id, access_time, json.dumps(access_history))
                )
            else:
                # Subsequent access - update existing record
                access_history = json.loads(row['access_history']) if row['access_history'] else []
                access_history.append({"timestamp": access_time.isoformat(), "context": context})

                # Update activations table
                conn.execute(
                    """UPDATE activations
                       SET access_count = access_count + 1,
                           last_access = ?,
                           access_history = ?
                       WHERE chunk_id = ?""",
                    (access_time, json.dumps(access_history), chunk_id)
                )

            # Update chunks table timestamps
            conn.execute(
                """UPDATE chunks
                   SET last_access = ?,
                       first_access = COALESCE(first_access, ?)
                   WHERE id = ?""",
                (access_time, access_time, chunk_id)
            )

            conn.commit()

        except sqlite3.Error as e:
            conn.rollback()
            raise StorageError(
                f"Failed to record access for chunk: {chunk_id}",
                details=str(e)
            )

    def get_access_history(
        self,
        chunk_id: ChunkID,
        limit: Optional[int] = None
    ) -> list[dict]:
        """
        Retrieve access history for a chunk.

        Returns a list of access records, most recent first.

        Args:
            chunk_id: The chunk whose history to retrieve
            limit: Maximum number of records to return (None = all)

        Returns:
            List of access records with 'timestamp' and optional 'context' keys

        Raises:
            StorageError: If storage operation fails
            ChunkNotFoundError: If chunk_id does not exist
        """
        conn = self._get_connection()

        try:
            # First check if chunk exists
            cursor = conn.execute("SELECT id FROM chunks WHERE id = ?", (chunk_id,))
            if cursor.fetchone() is None:
                raise ChunkNotFoundError(str(chunk_id))

            # Get access history from activations table
            cursor = conn.execute(
                "SELECT access_history FROM activations WHERE chunk_id = ?",
                (chunk_id,)
            )
            row = cursor.fetchone()

            if row is None or not row['access_history']:
                return []

            access_history = json.loads(row['access_history'])

            # Sort by timestamp, most recent first
            access_history.sort(key=lambda x: x['timestamp'], reverse=True)

            # Apply limit if specified
            if limit is not None:
                access_history = access_history[:limit]

            return access_history

        except sqlite3.Error as e:
            raise StorageError(
                f"Failed to retrieve access history for chunk: {chunk_id}",
                details=str(e)
            )

    def get_access_stats(self, chunk_id: ChunkID) -> dict:
        """
        Get access statistics for a chunk.

        Provides quick access to summary statistics without retrieving
        the full access history.

        Args:
            chunk_id: The chunk to get statistics for

        Returns:
            Dictionary with keys:
                - access_count: Total number of accesses
                - last_access: Timestamp of most recent access (or None)
                - first_access: Timestamp of first access (or None)
                - created_at: Timestamp of chunk creation

        Raises:
            StorageError: If storage operation fails
            ChunkNotFoundError: If chunk_id does not exist
        """
        conn = self._get_connection()

        try:
            # Get stats from both chunks and activations tables
            cursor = conn.execute(
                """SELECT
                       c.created_at,
                       c.first_access,
                       c.last_access,
                       COALESCE(a.access_count, 0) as access_count
                   FROM chunks c
                   LEFT JOIN activations a ON c.id = a.chunk_id
                   WHERE c.id = ?""",
                (chunk_id,)
            )
            row = cursor.fetchone()

            if row is None:
                raise ChunkNotFoundError(str(chunk_id))

            return {
                'access_count': row['access_count'],
                'last_access': row['last_access'],
                'first_access': row['first_access'],
                'created_at': row['created_at']
            }

        except sqlite3.Error as e:
            raise StorageError(
                f"Failed to retrieve access stats for chunk: {chunk_id}",
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
