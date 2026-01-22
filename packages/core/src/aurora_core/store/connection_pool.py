"""Connection pooling for SQLite to improve startup performance.

This module provides a simple connection pool that reuses database connections
across Store instances, eliminating redundant schema checks and pragma execution.
"""

import sqlite3
import threading

from aurora_core.exceptions import StorageError


class ConnectionPool:
    """Thread-safe connection pool for SQLite databases.

    Maintains a pool of validated connections that can be reused,
    avoiding redundant schema checks and pragma execution.
    """

    def __init__(self, max_connections: int = 10):
        """Initialize connection pool.

        Args:
            max_connections: Maximum number of pooled connections per database

        """
        self._pools: dict[str, list[sqlite3.Connection]] = {}
        self._locks: dict[str, threading.Lock] = {}
        self._max_connections = max_connections
        self._global_lock = threading.Lock()

    def get_connection(
        self,
        db_path: str,
        timeout: float = 5.0,
        wal_mode: bool = True,
        schema_initialized: bool = False,
    ) -> tuple[sqlite3.Connection, bool]:
        """Get or create a connection from the pool.

        Args:
            db_path: Database file path
            timeout: Connection timeout in seconds
            wal_mode: Enable WAL mode
            schema_initialized: Whether schema is already initialized

        Returns:
            Tuple of (connection, is_new) where is_new indicates if connection was just created

        Raises:
            StorageError: If connection fails

        """
        # Get or create pool lock for this database
        with self._global_lock:
            if db_path not in self._locks:
                self._locks[db_path] = threading.Lock()
                self._pools[db_path] = []
            pool_lock = self._locks[db_path]

        # Try to get existing connection from pool
        with pool_lock:
            if self._pools[db_path]:
                conn = self._pools[db_path].pop()
                # Verify connection is still valid
                try:
                    conn.execute("SELECT 1")
                    return conn, False
                except sqlite3.Error:
                    # Connection is stale, create new one
                    try:
                        conn.close()
                    except:
                        pass

        # Create new connection
        try:
            conn = sqlite3.connect(db_path, timeout=timeout, check_same_thread=False)
            conn.row_factory = sqlite3.Row

            # Enable WAL mode for better concurrency (skip if already initialized)
            if wal_mode and db_path != ":memory:" and not schema_initialized:
                conn.execute("PRAGMA journal_mode=WAL")

            # Enable foreign keys
            conn.execute("PRAGMA foreign_keys=ON")

            # ========== QUERY OPTIMIZATION PRAGMAS ==========
            # These settings improve query performance for read-heavy workloads

            # Synchronous=NORMAL: Good balance between safety and speed
            # FULL is safest but slower, OFF is fastest but risky
            conn.execute("PRAGMA synchronous=NORMAL")

            # Cache size: Increase page cache (default is ~2MB, we use ~8MB)
            # Negative value = KB instead of pages
            conn.execute("PRAGMA cache_size=-8000")

            # Memory-mapped I/O: Enable for faster reads (256MB max)
            # This allows SQLite to bypass the filesystem cache
            if db_path != ":memory:":
                conn.execute("PRAGMA mmap_size=268435456")

            # Temp store: Keep temp tables in memory for faster joins
            conn.execute("PRAGMA temp_store=MEMORY")

            return conn, True

        except sqlite3.Error as e:
            raise StorageError(f"Failed to connect to database: {db_path}", details=str(e))

    def return_connection(self, db_path: str, conn: sqlite3.Connection) -> None:
        """Return a connection to the pool for reuse.

        Args:
            db_path: Database file path
            conn: Connection to return

        """
        with self._global_lock:
            if db_path not in self._locks:
                # Pool was cleared, close connection
                try:
                    conn.close()
                except:
                    pass
                return
            pool_lock = self._locks[db_path]

        with pool_lock:
            # Only pool if under limit
            if len(self._pools[db_path]) < self._max_connections:
                self._pools[db_path].append(conn)
            else:
                # Pool full, close connection
                try:
                    conn.close()
                except:
                    pass

    def clear_pool(self, db_path: str | None = None) -> None:
        """Clear connections from pool.

        Args:
            db_path: Database to clear, or None to clear all

        """
        with self._global_lock:
            if db_path:
                # Clear specific database
                if db_path in self._pools:
                    pool = self._pools.pop(db_path)
                    self._locks.pop(db_path)
                    for conn in pool:
                        try:
                            conn.close()
                        except:
                            pass
            else:
                # Clear all pools
                for pool in self._pools.values():
                    for conn in pool:
                        try:
                            conn.close()
                        except:
                            pass
                self._pools.clear()
                self._locks.clear()


# Global connection pool instance
_global_pool: ConnectionPool | None = None
_pool_lock = threading.Lock()


def get_connection_pool() -> ConnectionPool:
    """Get the global connection pool instance.

    Returns:
        Global ConnectionPool instance

    """
    global _global_pool

    if _global_pool is None:
        with _pool_lock:
            if _global_pool is None:
                _global_pool = ConnectionPool()

    return _global_pool


def clear_connection_pool(db_path: str | None = None) -> None:
    """Clear the global connection pool.

    Args:
        db_path: Database to clear, or None to clear all

    """
    pool = get_connection_pool()
    pool.clear_pool(db_path)


__all__ = ["ConnectionPool", "get_connection_pool", "clear_connection_pool"]
