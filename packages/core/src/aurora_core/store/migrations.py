"""Schema migration utilities for AURORA storage.

This module provides utilities for managing database schema upgrades,
ensuring smooth transitions between versions without data loss.
"""

import sqlite3
from collections.abc import Callable
from pathlib import Path

from aurora_core.exceptions import StorageError
from aurora_core.store.schema import SCHEMA_VERSION


class Migration:
    """Represents a single schema migration.

    Args:
        from_version: Source schema version
        to_version: Target schema version
        upgrade_fn: Function that performs the migration
        description: Human-readable description of the migration

    """

    def __init__(
        self,
        from_version: int,
        to_version: int,
        upgrade_fn: Callable[[sqlite3.Connection], None],
        description: str,
    ):
        self.from_version = from_version
        self.to_version = to_version
        self.upgrade_fn = upgrade_fn
        self.description = description

    def apply(self, conn: sqlite3.Connection) -> None:
        """Apply this migration to a database connection.

        Args:
            conn: SQLite database connection

        Raises:
            StorageError: If migration fails

        """
        try:
            self.upgrade_fn(conn)
            conn.commit()
        except sqlite3.Error as e:
            conn.rollback()
            raise StorageError(
                f"Migration failed: v{self.from_version} -> v{self.to_version}",
                details=str(e),
            )


class MigrationManager:
    """Manages schema migrations for AURORA storage.

    This class tracks available migrations and applies them in order to
    upgrade a database from an older schema version to the current version.
    """

    def __init__(self) -> None:
        """Initialize migration manager."""
        self._migrations: list[Migration] = []
        self._register_migrations()

    def _register_migrations(self) -> None:
        """Register all available migrations.

        Add new migrations here as the schema evolves.
        """
        # Migration v1 -> v2: Add access history tracking
        self.add_migration(
            Migration(
                from_version=1,
                to_version=2,
                upgrade_fn=self._migrate_v1_to_v2,
                description="Add access history tracking (access_history JSON, first_access, last_access)",
            ),
        )

        # Migration v2 -> v3: Add embeddings support
        self.add_migration(
            Migration(
                from_version=2,
                to_version=3,
                upgrade_fn=self._migrate_v2_to_v3,
                description="Add embeddings column to chunks table for semantic retrieval",
            ),
        )

    def _migrate_v1_to_v2(self, conn: sqlite3.Connection) -> None:
        """Migrate from schema v1 to v2: Add access history tracking.

        Changes:
        - Add access_history JSON column to activations table
        - Add first_access and last_access columns to chunks table
        - Initialize access_history from existing last_access data
        """
        cursor = conn.cursor()

        # Add new columns to chunks table
        try:
            cursor.execute("ALTER TABLE chunks ADD COLUMN first_access TIMESTAMP")
        except sqlite3.OperationalError:
            pass  # Column may already exist

        try:
            cursor.execute("ALTER TABLE chunks ADD COLUMN last_access TIMESTAMP")
        except sqlite3.OperationalError:
            pass  # Column may already exist

        # Add access_history column to activations table
        try:
            cursor.execute("ALTER TABLE activations ADD COLUMN access_history JSON")
        except sqlite3.OperationalError:
            pass  # Column may already exist

        # Initialize access_history from existing last_access data
        # For each chunk with activation data, create an initial history entry
        cursor.execute(
            """
            UPDATE activations
            SET access_history = json_array(
                json_object(
                    'timestamp', last_access,
                    'context', NULL
                )
            )
            WHERE access_history IS NULL
        """,
        )

        # Copy last_access from activations to chunks table for consistency
        cursor.execute(
            """
            UPDATE chunks
            SET last_access = (
                SELECT last_access FROM activations WHERE activations.chunk_id = chunks.id
            ),
            first_access = (
                SELECT last_access FROM activations WHERE activations.chunk_id = chunks.id
            )
            WHERE id IN (SELECT chunk_id FROM activations)
        """,
        )

        conn.commit()

    def _migrate_v2_to_v3(self, conn: sqlite3.Connection) -> None:
        """Migrate from schema v2 to v3: Add embeddings support.

        Changes:
        - Add embeddings BLOB column to chunks table for storing embedding vectors
        """
        cursor = conn.cursor()

        # Add embeddings column to chunks table
        try:
            cursor.execute("ALTER TABLE chunks ADD COLUMN embeddings BLOB")
        except sqlite3.OperationalError:
            pass  # Column may already exist

        conn.commit()

    def add_migration(self, migration: Migration) -> None:
        """Register a migration.

        Args:
            migration: Migration to register

        """
        self._migrations.append(migration)

    def get_current_version(self, conn: sqlite3.Connection) -> int:
        """Get the current schema version from database.

        Args:
            conn: SQLite database connection

        Returns:
            Current schema version, or 0 if schema_version table doesn't exist

        """
        try:
            cursor = conn.execute(
                "SELECT version FROM schema_version ORDER BY version DESC LIMIT 1",
            )
            row = cursor.fetchone()
            return row[0] if row else 0
        except sqlite3.Error:
            # Table doesn't exist yet
            return 0

    def needs_migration(self, conn: sqlite3.Connection) -> bool:
        """Check if database needs migration.

        Args:
            conn: SQLite database connection

        Returns:
            True if database schema is older than current version

        """
        current_version = self.get_current_version(conn)
        return current_version < SCHEMA_VERSION

    def migrate(self, conn: sqlite3.Connection) -> None:
        """Migrate database to current schema version.

        This method applies all necessary migrations in order to bring
        the database up to the current schema version.

        Args:
            conn: SQLite database connection

        Raises:
            StorageError: If migration fails

        """
        current_version = self.get_current_version(conn)

        if current_version == SCHEMA_VERSION:
            # Already at current version
            return

        if current_version > SCHEMA_VERSION:
            raise StorageError(
                f"Database schema version {current_version} is newer than "
                f"supported version {SCHEMA_VERSION}. Please upgrade AURORA.",
            )

        # Find and apply migrations in order
        applicable_migrations = [
            m
            for m in self._migrations
            if m.from_version >= current_version and m.to_version <= SCHEMA_VERSION
        ]

        # Sort by from_version to ensure correct order
        applicable_migrations.sort(key=lambda m: m.from_version)

        for migration in applicable_migrations:
            print(f"Applying migration: {migration.description}")
            migration.apply(conn)

            # Update schema version
            conn.execute(
                "INSERT OR REPLACE INTO schema_version (version) VALUES (?)",
                (migration.to_version,),
            )
            conn.commit()

    def backup_database(self, db_path: str) -> str:
        """Create a backup of the database before migration.

        Args:
            db_path: Path to database file

        Returns:
            Path to backup file

        Raises:
            StorageError: If backup fails

        """
        if db_path == ":memory:":
            # Can't backup in-memory database
            return ":memory:"

        import shutil
        from datetime import datetime

        path = Path(db_path)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = path.parent / f"{path.stem}_backup_{timestamp}{path.suffix}"

        try:
            shutil.copy2(db_path, backup_path)
            return str(backup_path)
        except Exception as e:
            raise StorageError(f"Failed to backup database: {db_path}", details=str(e))

    def migrate_with_backup(
        self,
        conn: sqlite3.Connection,
        db_path: str | None = None,
    ) -> str | None:
        """Migrate database with automatic backup.

        Args:
            conn: SQLite database connection
            db_path: Path to database file (for backup)

        Returns:
            Path to backup file if backup was created, None otherwise

        Raises:
            StorageError: If migration fails

        """
        backup_path = None

        if db_path and self.needs_migration(conn):
            backup_path = self.backup_database(db_path)
            print(f"Database backed up to: {backup_path}")

        try:
            self.migrate(conn)
            return backup_path
        except Exception:
            if backup_path and backup_path != ":memory:":
                print(f"Migration failed. Restore from backup: {backup_path}")
            raise


# Global migration manager instance
_migration_manager = MigrationManager()


def get_migration_manager() -> MigrationManager:
    """Get the global migration manager instance.

    Returns:
        Global MigrationManager instance

    """
    return _migration_manager


__all__ = [
    "Migration",
    "MigrationManager",
    "get_migration_manager",
]
