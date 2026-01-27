"""SQLite-based storage implementation for AURORA chunks.

This module provides a production-ready storage backend using SQLite with:
- Thread-safe connection pooling
- Transaction support with automatic rollback
- JSON validation and error handling
- Relationship graph traversal for spreading activation
"""

import json
import shutil
import sqlite3
import threading
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

# Forward reference for type checking
from typing import TYPE_CHECKING, Any, Optional, cast

from aurora_core.exceptions import (
    ChunkNotFoundError,
    SchemaMismatchError,
    StorageError,
    ValidationError,
)
from aurora_core.store.base import Store
from aurora_core.store.connection_pool import get_connection_pool
from aurora_core.store.schema import get_init_statements
from aurora_core.types import ChunkID

if TYPE_CHECKING:
    from aurora_core.chunks.base import Chunk


class SQLiteStore(Store):
    """SQLite-based storage implementation with connection pooling.

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
        wal_mode: bool = True,
    ):
        """Initialize SQLite store with connection pooling."""
        # Expand user home directory in path
        self.db_path = str(Path(db_path).expanduser())
        self.timeout = timeout
        self.wal_mode = wal_mode

        # Thread-local storage for connections (one connection per thread)
        self._local = threading.local()

        # Track if schema has been initialized for this database
        self._schema_initialized = False
        self._schema_lock = threading.Lock()

        # Create database directory if it doesn't exist
        if self.db_path != ":memory:":
            Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)

        # Defer schema initialization until first use
        # This speeds up Store creation by avoiding immediate DB checks

    def _get_connection(self) -> sqlite3.Connection:
        """Get or create a connection for the current thread.

        Uses connection pooling for improved performance and deferred schema init.

        Returns:
            Thread-local SQLite connection

        """
        if not hasattr(self._local, "connection") or self._local.connection is None:
            # Try to get pooled connection first
            pool = get_connection_pool()
            conn, is_new = pool.get_connection(
                self.db_path,
                timeout=self.timeout,
                wal_mode=self.wal_mode,
                schema_initialized=self._schema_initialized,
            )

            self._local.connection = conn

            # Initialize schema if needed (must happen after connection is set)
            if not self._schema_initialized:
                with self._schema_lock:
                    if not self._schema_initialized:
                        self._init_schema()
                        self._schema_initialized = True

        return cast(sqlite3.Connection, self._local.connection)

    def _init_schema(self) -> None:
        """Initialize database schema if not exists.

        This method first checks if an existing database has a compatible schema.
        If the database exists but has an incompatible (older) schema, it raises
        SchemaMismatchError to allow the caller to handle migration or reset.

        Raises:
            SchemaMismatchError: If database has incompatible schema version
            StorageError: If schema initialization fails

        """
        conn = self._get_connection()

        # Check for existing incompatible schema before attempting CREATE statements
        # This prevents confusing errors when old schema tables conflict with new DDL
        try:
            self._check_schema_compatibility()
        except SchemaMismatchError:
            # Re-raise to let caller handle (CLI will prompt for reset)
            raise

        try:
            for statement in get_init_statements():
                conn.execute(statement)
            conn.commit()
        except sqlite3.Error as e:
            raise StorageError("Failed to initialize database schema", details=str(e))

    def _detect_schema_version(self) -> tuple[int, int]:
        """Detect the schema version of an existing database.

        This method determines the schema version by:
        1. Checking the schema_version table if it exists
        2. Falling back to column count detection for legacy databases

        Returns:
            Tuple of (detected_version, column_count) where:
            - detected_version: The schema version (0 if unknown legacy)
            - column_count: Number of columns in chunks table

        Raises:
            StorageError: If the chunks table doesn't exist or query fails

        """
        from aurora_core.store.schema import SCHEMA_VERSION

        conn = self._get_connection()

        try:
            # First, check if schema_version table exists and has a version
            cursor = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='schema_version'",
            )
            if cursor.fetchone() is not None:
                cursor = conn.execute(
                    "SELECT version FROM schema_version ORDER BY version DESC LIMIT 1",
                )
                row = cursor.fetchone()
                if row is not None:
                    # Get column count for completeness
                    cursor = conn.execute("PRAGMA table_info(chunks)")
                    columns = cursor.fetchall()
                    return (int(row[0]), len(columns))

            # No schema_version table - check if chunks table exists
            cursor = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='chunks'",
            )
            if cursor.fetchone() is None:
                # No chunks table - this is a fresh database
                return (SCHEMA_VERSION, 0)

            # Get column count from chunks table for legacy detection
            cursor = conn.execute("PRAGMA table_info(chunks)")
            columns = cursor.fetchall()
            column_count = len(columns)

            # Determine version based on column count
            # Current schema (v3) has 9 columns: id, type, content, metadata, embeddings,
            #   created_at, updated_at, first_access, last_access
            # Legacy schemas had fewer columns (e.g., 7 columns without first_access/last_access)
            if column_count >= 9:
                return (SCHEMA_VERSION, column_count)
            if column_count == 7:
                # Legacy schema without first_access/last_access
                return (1, column_count)
            # Unknown legacy schema
            return (0, column_count)

        except sqlite3.Error as e:
            raise StorageError("Failed to detect schema version", details=str(e))

    def _check_schema_compatibility(self) -> None:
        """Check if the database schema is compatible with current version.

        This method should be called before attempting to use an existing database.
        It raises SchemaMismatchError if the database has an incompatible schema,
        allowing the caller to handle migration or reset.

        Raises:
            SchemaMismatchError: If database schema version is incompatible
            StorageError: If schema detection fails

        """
        from aurora_core.store.schema import SCHEMA_VERSION

        detected_version, column_count = self._detect_schema_version()

        # If column_count is 0, this is a fresh database - no check needed
        if column_count == 0:
            return

        # If detected version matches expected, we're good
        if detected_version == SCHEMA_VERSION:
            return

        # Schema mismatch - raise error with details
        raise SchemaMismatchError(
            found_version=detected_version,
            expected_version=SCHEMA_VERSION,
            db_path=self.db_path if self.db_path != ":memory:" else None,
        )

    @contextmanager
    def _transaction(self) -> Iterator[sqlite3.Connection]:
        """Context manager for database transactions with automatic rollback.

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
            raise StorageError("Transaction failed and was rolled back", details=str(e))

    def save_chunk(self, chunk: "Chunk") -> bool:
        """Save a chunk to storage with validation.

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
            raise ValidationError(f"Chunk validation failed: {chunk.id}", details=str(e))

        # Serialize chunk to JSON
        try:
            chunk_json = chunk.to_json()
        except Exception as e:
            raise ValidationError(f"Failed to serialize chunk: {chunk.id}", details=str(e))

        with self._transaction() as conn:
            try:
                # Get embeddings if available (optional field for semantic retrieval)
                embeddings = getattr(chunk, "embeddings", None)

                # Insert or replace chunk
                conn.execute(
                    """
                    INSERT OR REPLACE INTO chunks (id, type, content, metadata, embeddings, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        chunk.id,
                        chunk.type,
                        json.dumps(chunk_json.get("content", {})),
                        json.dumps(chunk_json.get("metadata", {})),
                        embeddings,  # BLOB - numpy array bytes or None
                        datetime.now(timezone.utc).isoformat(),
                    ),
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
                        datetime.now(timezone.utc).isoformat(),
                        0,
                    ),
                )

                return True
            except sqlite3.Error as e:
                raise StorageError(f"Failed to save chunk: {chunk.id}", details=str(e))

    def get_chunk(self, chunk_id: ChunkID) -> Optional["Chunk"]:
        """Retrieve a chunk by ID.

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
                (chunk_id,),
            )
            row = cursor.fetchone()

            if row is None:
                return None

            # Deserialize chunk (will be implemented when Chunk classes are ready)
            # For now, return the raw data as a dict
            # TODO: Implement proper deserialization once Chunk.from_json is available
            return self._deserialize_chunk(dict(row))

        except sqlite3.Error as e:
            raise StorageError(f"Failed to retrieve chunk: {chunk_id}", details=str(e))

    def _deserialize_chunk(self, row_data: dict[str, Any]) -> Optional["Chunk"]:
        """Deserialize a chunk from database row.

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
            content = json.loads(row_data["content"])
            metadata = json.loads(row_data["metadata"])

            # Reconstruct full JSON structure for from_json()
            full_data = {
                "id": row_data["id"],
                "type": row_data["type"],
                "content": content,
                "metadata": metadata,
            }

            # Deserialize based on chunk type
            chunk_type = row_data["type"]
            chunk: Chunk
            if chunk_type in ("code", "kb"):
                # Both code and kb (knowledge base/markdown) use CodeChunk structure
                chunk = CodeChunk.from_json(full_data)
            elif chunk_type == "reasoning":
                chunk = ReasoningChunk.from_json(full_data)
            else:
                # Skip truly unknown chunk types gracefully
                import logging

                logging.getLogger(__name__).debug(
                    f"Skipping unknown chunk type '{chunk_type}': {row_data['id']}",
                )
                return None

            # Restore embeddings if present (BLOB field for semantic retrieval)
            if "embeddings" in row_data and row_data["embeddings"] is not None:
                if hasattr(chunk, "embeddings"):
                    chunk.embeddings = row_data["embeddings"]

            return chunk

        except (KeyError, json.JSONDecodeError, ValueError) as e:
            raise StorageError(
                f"Failed to deserialize chunk: {row_data.get('id', 'unknown')}",
                details=str(e),
            )

    def update_activation(self, chunk_id: ChunkID, delta: float) -> None:
        """Update activation score for a chunk.

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
                    (delta, datetime.now(timezone.utc).isoformat(), chunk_id),
                )

                if cursor.rowcount == 0:
                    raise ChunkNotFoundError(str(chunk_id))

            except sqlite3.Error as e:
                raise StorageError(
                    f"Failed to update activation for chunk: {chunk_id}",
                    details=str(e),
                )

    def get_activation(self, chunk_id: ChunkID) -> float:
        """Get the current activation score for a chunk.

        Args:
            chunk_id: The chunk ID to query

        Returns:
            Current activation score (base_level) for the chunk, or 0.0 if not found

        Raises:
            StorageError: If storage operation fails

        """
        conn = self._get_connection()
        try:
            cursor = conn.execute(
                """
                SELECT base_level
                FROM activations
                WHERE chunk_id = ?
                """,
                (chunk_id,),
            )
            row = cursor.fetchone()
            if row is None:
                return 0.0
            return float(row[0])

        except sqlite3.Error as e:
            raise StorageError(f"Failed to get activation for chunk: {chunk_id}", details=str(e))

    def get_chunk_count(self) -> int:
        """Get the total number of chunks in storage.

        This is a fast operation that uses COUNT(*) on the chunks table,
        avoiding the need to load chunk data or embeddings.

        Returns:
            Number of chunks stored

        Raises:
            StorageError: If storage operation fails

        """
        conn = self._get_connection()
        try:
            cursor = conn.execute("SELECT COUNT(*) FROM chunks")
            row = cursor.fetchone()
            return row[0] if row else 0
        except sqlite3.Error as e:
            raise StorageError("Failed to get chunk count", details=str(e))

    def retrieve_by_activation(
        self,
        min_activation: float,
        limit: int,
        include_embeddings: bool = True,
        chunk_type: str | None = None,
    ) -> list["Chunk"]:
        """Retrieve chunks by activation threshold.

        Args:
            min_activation: Minimum activation score (can be negative in ACT-R)
            limit: Maximum number of chunks to return
            include_embeddings: Whether to include embedding vectors (default True).
                Set to False for faster retrieval when embeddings aren't needed (e.g., BM25 filtering).
            chunk_type: Optional filter by chunk type ('code' or 'kb').

        Returns:
            List of chunks ordered by activation (highest first)

        Raises:
            StorageError: If storage operation fails

        """
        conn = self._get_connection()
        try:
            # Note: In ACT-R, base_level can be negative (it's log-odds)
            # Default min_activation of 0.0 would filter out valid chunks
            # Use -float('inf') if min_activation is 0.0 to get all chunks
            actual_min = min_activation if min_activation != 0.0 else -float("inf")

            # Build WHERE clause
            where_clause = "a.base_level >= ?"
            params: list = [actual_min]
            if chunk_type:
                where_clause += " AND c.type = ?"
                params.append(chunk_type)
            params.append(limit)

            # Optimize query by excluding embeddings when not needed
            # Each embedding is ~1.5KB, so this saves significant I/O for large result sets
            if include_embeddings:
                cursor = conn.execute(
                    f"""
                    SELECT c.id, c.type, c.content, c.metadata, c.embeddings, c.created_at, c.updated_at,
                           a.base_level AS activation
                    FROM chunks c
                    JOIN activations a ON c.id = a.chunk_id
                    WHERE {where_clause}
                    ORDER BY a.base_level DESC
                    LIMIT ?
                    """,
                    params,
                )
            else:
                # Exclude embeddings for faster retrieval (BM25-only filtering)
                cursor = conn.execute(
                    f"""
                    SELECT c.id, c.type, c.content, c.metadata, NULL as embeddings, c.created_at, c.updated_at,
                           a.base_level AS activation
                    FROM chunks c
                    JOIN activations a ON c.id = a.chunk_id
                    WHERE {where_clause}
                    ORDER BY a.base_level DESC
                    LIMIT ?
                    """,
                    params,
                )

            chunks = []
            for row in cursor:
                row_dict = dict(row)
                # Extract activation before deserialization
                activation_value = row_dict.pop("activation", 0.0)
                chunk = self._deserialize_chunk(row_dict)
                if chunk is not None:
                    # Attach activation score to chunk object
                    chunk.activation = activation_value  # type: ignore[attr-defined]
                    chunks.append(chunk)

            return chunks

        except sqlite3.Error as e:
            raise StorageError("Failed to retrieve chunks by activation", details=str(e))

    def fetch_embeddings_for_chunks(self, chunk_ids: list[ChunkID]) -> dict[ChunkID, bytes]:
        """Fetch embeddings only for specified chunks.

        This is used for two-phase retrieval optimization:
        1. First retrieve chunks without embeddings (fast)
        2. After BM25 filtering, fetch embeddings only for top candidates

        Args:
            chunk_ids: List of chunk IDs to fetch embeddings for

        Returns:
            Dictionary mapping chunk_id to embedding bytes

        Raises:
            StorageError: If storage operation fails

        """
        if not chunk_ids:
            return {}

        conn = self._get_connection()
        try:
            # Use parameterized query with proper placeholder count
            placeholders = ",".join("?" * len(chunk_ids))
            cursor = conn.execute(
                f"""
                SELECT id, embeddings
                FROM chunks
                WHERE id IN ({placeholders})
                AND embeddings IS NOT NULL
                """,
                chunk_ids,
            )

            return {row["id"]: row["embeddings"] for row in cursor if row["embeddings"]}

        except sqlite3.Error as e:
            raise StorageError("Failed to fetch embeddings", details=str(e))

    def add_relationship(
        self,
        from_id: ChunkID,
        to_id: ChunkID,
        rel_type: str,
        weight: float = 1.0,
    ) -> bool:
        """Add a relationship between chunks.

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
                    (from_id, to_id),
                )
                count = cursor.fetchone()["cnt"]
                if count < 2:
                    raise ChunkNotFoundError(f"One or both chunks not found: {from_id}, {to_id}")

                # Insert relationship
                conn.execute(
                    """
                    INSERT INTO relationships (from_chunk, to_chunk, relationship_type, weight)
                    VALUES (?, ?, ?, ?)
                    """,
                    (from_id, to_id, rel_type, weight),
                )

                return True

            except sqlite3.Error as e:
                raise StorageError(
                    f"Failed to add relationship: {from_id} -> {to_id}",
                    details=str(e),
                )

    def get_related_chunks(self, chunk_id: ChunkID, max_depth: int = 2) -> list["Chunk"]:
        """Get related chunks via relationship graph traversal.

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
            raise StorageError(f"Failed to verify chunk existence: {chunk_id}", details=str(e))

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
            raise StorageError(f"Failed to retrieve related chunks for: {chunk_id}", details=str(e))

    def record_access(
        self,
        chunk_id: ChunkID,
        access_time: datetime | None = None,
        context: str | None = None,
    ) -> None:
        """Record an access to a chunk for ACT-R activation tracking.

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
        from aurora_core.activation.base_level import AccessHistoryEntry, calculate_bla

        conn = self._get_connection()
        if access_time is None:
            access_time = datetime.now(timezone.utc)

        try:
            # First check if chunk exists
            cursor = conn.execute("SELECT id FROM chunks WHERE id = ?", (chunk_id,))
            if cursor.fetchone() is None:
                raise ChunkNotFoundError(str(chunk_id))

            # Get current access history from activations table
            cursor = conn.execute(
                "SELECT access_history FROM activations WHERE chunk_id = ?",
                (chunk_id,),
            )
            row = cursor.fetchone()

            if row is None:
                # First access - initialize activation record
                access_history = [{"timestamp": access_time.isoformat(), "context": context}]

                # Calculate initial BLA (single access)
                history_entries = [AccessHistoryEntry(timestamp=access_time)]
                new_base_level = calculate_bla(
                    history_entries,
                    decay_rate=0.5,
                    current_time=access_time,
                )

                conn.execute(
                    """INSERT INTO activations (chunk_id, base_level, last_access, access_count, access_history)
                       VALUES (?, ?, ?, 1, ?)""",
                    (chunk_id, new_base_level, access_time, json.dumps(access_history)),
                )
            else:
                # Subsequent access - update existing record
                access_history = json.loads(row["access_history"]) if row["access_history"] else []
                access_history.append({"timestamp": access_time.isoformat(), "context": context})

                # Recalculate BLA based on updated access history
                history_entries = [
                    AccessHistoryEntry(
                        timestamp=datetime.fromisoformat(
                            str(entry["timestamp"]).replace("Z", "+00:00"),
                        ),
                    )
                    for entry in access_history
                    if entry.get("timestamp")
                ]
                new_base_level = calculate_bla(
                    history_entries,
                    decay_rate=0.5,
                    current_time=access_time,
                )

                # Update activations table with new base_level
                conn.execute(
                    """UPDATE activations
                       SET access_count = access_count + 1,
                           last_access = ?,
                           access_history = ?,
                           base_level = ?
                       WHERE chunk_id = ?""",
                    (access_time, json.dumps(access_history), new_base_level, chunk_id),
                )

            # Update chunks table timestamps
            conn.execute(
                """UPDATE chunks
                   SET last_access = ?,
                       first_access = COALESCE(first_access, ?)
                   WHERE id = ?""",
                (access_time, access_time, chunk_id),
            )

            conn.commit()

        except sqlite3.Error as e:
            conn.rollback()
            raise StorageError(f"Failed to record access for chunk: {chunk_id}", details=str(e))

    def get_access_history(
        self,
        chunk_id: ChunkID,
        limit: int | None = None,
    ) -> list[dict[str, Any]]:
        """Retrieve access history for a chunk.

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
                (chunk_id,),
            )
            row = cursor.fetchone()

            if row is None or not row["access_history"]:
                return []

            access_history: list[dict[Any, Any]] = json.loads(row["access_history"])

            # Sort by timestamp, most recent first
            access_history.sort(key=lambda x: x["timestamp"], reverse=True)

            # Apply limit if specified
            if limit is not None:
                access_history = access_history[:limit]

            return access_history

        except sqlite3.Error as e:
            raise StorageError(
                f"Failed to retrieve access history for chunk: {chunk_id}",
                details=str(e),
            )

    def get_access_stats(self, chunk_id: ChunkID) -> dict[str, Any]:
        """Get access statistics for a chunk.

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
                (chunk_id,),
            )
            row = cursor.fetchone()

            if row is None:
                raise ChunkNotFoundError(str(chunk_id))

            return {
                "access_count": row["access_count"],
                "last_access": row["last_access"],
                "first_access": row["first_access"],
                "created_at": row["created_at"],
            }

        except sqlite3.Error as e:
            raise StorageError(
                f"Failed to retrieve access stats for chunk: {chunk_id}",
                details=str(e),
            )

    def get_access_stats_batch(
        self,
        chunk_ids: list[ChunkID],
    ) -> dict[ChunkID, dict[str, Any]]:
        """Get access statistics for multiple chunks in a single query.

        This is an optimized batch method that avoids N+1 query issues.
        Uses a single SQL query with IN clause instead of multiple queries.

        Args:
            chunk_ids: List of chunk IDs to get statistics for

        Returns:
            Dictionary mapping chunk_id to stats dictionary

        Raises:
            StorageError: If storage operation fails

        """
        if not chunk_ids:
            return {}

        conn = self._get_connection()
        results: dict[ChunkID, dict[str, Any]] = {}

        try:
            # Use parameterized query with proper placeholder count
            placeholders = ",".join("?" * len(chunk_ids))
            cursor = conn.execute(
                f"""SELECT
                       c.id,
                       c.created_at,
                       c.first_access,
                       c.last_access,
                       COALESCE(a.access_count, 0) as access_count
                   FROM chunks c
                   LEFT JOIN activations a ON c.id = a.chunk_id
                   WHERE c.id IN ({placeholders})""",
                chunk_ids,
            )

            for row in cursor:
                results[row["id"]] = {
                    "access_count": row["access_count"],
                    "last_access": row["last_access"],
                    "first_access": row["first_access"],
                    "created_at": row["created_at"],
                }

            return results

        except sqlite3.Error as e:
            raise StorageError("Failed to retrieve batch access stats", details=str(e))

    def close(self) -> None:
        """Close database connection and cleanup.

        Raises:
            StorageError: If cleanup fails

        """
        if hasattr(self._local, "connection") and self._local.connection is not None:
            try:
                self._local.connection.close()
                self._local.connection = None
            except sqlite3.Error as e:
                raise StorageError("Failed to close database connection", details=str(e))

    def reset_database(self) -> bool:
        """Reset the database by deleting and recreating it with current schema.

        This method:
        1. Closes existing connections
        2. Deletes the database file
        3. Reinitializes with the current schema

        Returns:
            True if reset was successful

        Raises:
            StorageError: If reset operation fails

        """
        if self.db_path == ":memory:":
            # For in-memory databases, just reinitialize
            self._local.connection = None
            self._init_schema()
            return True

        try:
            # Close existing connection
            self.close()

            # Delete the database file
            db_file = Path(self.db_path)
            if db_file.exists():
                db_file.unlink()

            # Also remove WAL and SHM files if they exist
            wal_file = Path(f"{self.db_path}-wal")
            shm_file = Path(f"{self.db_path}-shm")
            if wal_file.exists():
                wal_file.unlink()
            if shm_file.exists():
                shm_file.unlink()

            # Reinitialize with current schema
            self._init_schema()
            return True

        except OSError as e:
            raise StorageError(
                f"Failed to reset database: {self.db_path}",
                details=str(e),
            )


def backup_database(db_path: str) -> str:
    """Create a backup of the database file.

    Creates a copy of the database file with a timestamp suffix.
    Format: {db_path}.bak.{timestamp}

    Args:
        db_path: Path to the database file to backup

    Returns:
        Path to the backup file

    Raises:
        StorageError: If backup operation fails

    """
    db_file = Path(db_path)

    if not db_file.exists():
        raise StorageError(
            "Cannot backup database: file not found",
            details=f"Path: {db_path}",
        )

    # Generate timestamp for backup filename
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    backup_path = f"{db_path}.bak.{timestamp}"

    try:
        # Use shutil.copy2 to preserve metadata
        shutil.copy2(db_path, backup_path)
        return backup_path
    except OSError as e:
        raise StorageError(
            "Failed to create database backup",
            details=f"Source: {db_path}, Destination: {backup_path}, Error: {e}",
        )


__all__ = ["SQLiteStore", "backup_database"]
