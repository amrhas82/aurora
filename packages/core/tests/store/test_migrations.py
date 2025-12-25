"""
Comprehensive test suite for database migration logic.

Tests cover:
- TD-P1-001: Migration v1→v2 with data preservation
- Rollback functionality on failures
- Error conditions (locked DB, permissions, disk full)
- Transaction atomicity
- Schema validation

Target: 80%+ coverage on migrations.py
"""

import json
import sqlite3
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from unittest import mock

import pytest

from aurora_core.exceptions import StorageError
from aurora_core.store.migrations import (
    Migration,
    MigrationManager,
    get_migration_manager,
)


class TestMigration:
    """Test the Migration class itself."""

    def test_migration_initialization(self):
        """Test Migration object initialization."""

        def dummy_upgrade(conn: sqlite3.Connection) -> None:
            pass

        migration = Migration(
            from_version=1,
            to_version=2,
            upgrade_fn=dummy_upgrade,
            description="Test migration",
        )

        assert migration.from_version == 1
        assert migration.to_version == 2
        assert migration.description == "Test migration"
        assert migration.upgrade_fn == dummy_upgrade

    def test_migration_apply_success(self):
        """Test successful migration application."""
        conn = sqlite3.connect(":memory:")

        def create_table(connection: sqlite3.Connection) -> None:
            connection.execute("CREATE TABLE test (id INTEGER PRIMARY KEY)")

        migration = Migration(
            from_version=0, to_version=1, upgrade_fn=create_table, description="Create test table"
        )

        migration.apply(conn)

        # Verify table was created
        cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='test'")
        assert cursor.fetchone() is not None

        conn.close()

    def test_migration_apply_failure_with_rollback(self):
        """Test migration failure triggers rollback."""
        conn = sqlite3.connect(":memory:")
        conn.execute("CREATE TABLE test (id INTEGER PRIMARY KEY)")

        def invalid_operation(connection: sqlite3.Connection) -> None:
            connection.execute("INSERT INTO test VALUES (1)")
            # This should fail - duplicate primary key
            connection.execute("INSERT INTO test VALUES (1)")

        migration = Migration(
            from_version=0,
            to_version=1,
            upgrade_fn=invalid_operation,
            description="Invalid migration",
        )

        with pytest.raises(StorageError) as exc_info:
            migration.apply(conn)

        assert "Migration failed: v0 -> v1" in str(exc_info.value)

        # Verify rollback - table should be empty
        cursor = conn.execute("SELECT COUNT(*) FROM test")
        count = cursor.fetchone()[0]
        assert count == 0, "Rollback should have undone all changes"

        conn.close()


class TestMigrationManagerBasics:
    """Test MigrationManager initialization and basic operations."""

    def test_manager_initialization(self):
        """Test MigrationManager initialization."""
        manager = MigrationManager()
        assert len(manager._migrations) > 0, "Should have registered migrations"

    def test_get_migration_manager_singleton(self):
        """Test global migration manager accessor."""
        manager1 = get_migration_manager()
        manager2 = get_migration_manager()
        assert manager1 is manager2, "Should return same instance"

    def test_add_migration(self):
        """Test adding custom migration."""
        manager = MigrationManager()
        initial_count = len(manager._migrations)

        def dummy_upgrade(conn: sqlite3.Connection) -> None:
            pass

        custom_migration = Migration(
            from_version=99, to_version=100, upgrade_fn=dummy_upgrade, description="Custom"
        )

        manager.add_migration(custom_migration)
        assert len(manager._migrations) == initial_count + 1

    def test_get_current_version_no_table(self):
        """Test get_current_version when schema_version table doesn't exist."""
        conn = sqlite3.connect(":memory:")
        manager = MigrationManager()

        version = manager.get_current_version(conn)
        assert version == 0, "Should return 0 when schema_version table doesn't exist"

        conn.close()

    def test_get_current_version_with_data(self):
        """Test get_current_version with existing schema_version table."""
        conn = sqlite3.connect(":memory:")
        conn.execute("CREATE TABLE schema_version (version INTEGER)")
        conn.execute("INSERT INTO schema_version (version) VALUES (2)")
        conn.commit()

        manager = MigrationManager()
        version = manager.get_current_version(conn)
        assert version == 2

        conn.close()

    def test_get_current_version_multiple_entries(self):
        """Test get_current_version returns highest version."""
        conn = sqlite3.connect(":memory:")
        conn.execute("CREATE TABLE schema_version (version INTEGER)")
        conn.execute("INSERT INTO schema_version (version) VALUES (1)")
        conn.execute("INSERT INTO schema_version (version) VALUES (3)")
        conn.execute("INSERT INTO schema_version (version) VALUES (2)")
        conn.commit()

        manager = MigrationManager()
        version = manager.get_current_version(conn)
        assert version == 3, "Should return highest version"

        conn.close()

    def test_needs_migration_true(self):
        """Test needs_migration returns True when database is outdated."""
        conn = sqlite3.connect(":memory:")
        conn.execute("CREATE TABLE schema_version (version INTEGER)")
        conn.execute("INSERT INTO schema_version (version) VALUES (1)")
        conn.commit()

        manager = MigrationManager()
        # Assuming SCHEMA_VERSION is > 1
        assert manager.needs_migration(conn) is True

        conn.close()

    def test_needs_migration_false(self):
        """Test needs_migration returns False when database is current."""
        from aurora.core.store.schema import SCHEMA_VERSION

        conn = sqlite3.connect(":memory:")
        conn.execute("CREATE TABLE schema_version (version INTEGER)")
        conn.execute(f"INSERT INTO schema_version (version) VALUES ({SCHEMA_VERSION})")
        conn.commit()

        manager = MigrationManager()
        assert manager.needs_migration(conn) is False

        conn.close()


class TestMigrationV1ToV2:
    """Test migration from v1 to v2 schema (TD-P1-001)."""

    def _create_v1_schema(self, conn: sqlite3.Connection) -> None:
        """Create a v1 schema database."""
        # V1 schema has chunks and activations tables without new columns
        conn.execute("""
            CREATE TABLE chunks (
                id TEXT PRIMARY KEY,
                content TEXT NOT NULL,
                metadata TEXT
            )
        """)

        conn.execute("""
            CREATE TABLE activations (
                chunk_id TEXT PRIMARY KEY,
                activation REAL NOT NULL,
                last_access TIMESTAMP,
                FOREIGN KEY (chunk_id) REFERENCES chunks (id)
            )
        """)

        conn.execute("CREATE TABLE schema_version (version INTEGER)")
        conn.execute("INSERT INTO schema_version (version) VALUES (1)")
        conn.commit()

    def test_v1_to_v2_migration_data_preservation(self):
        """Test v1→v2 migration preserves all data (TD-P1-001)."""
        conn = sqlite3.connect(":memory:")
        self._create_v1_schema(conn)

        # Insert 100 test chunks
        chunks = []
        for i in range(100):
            chunk_id = f"chunk_{i:03d}"
            content = f"Test content {i}"
            metadata = json.dumps({"line": i, "file": f"test{i}.py"})
            chunks.append((chunk_id, content, metadata))
            conn.execute("INSERT INTO chunks VALUES (?, ?, ?)", (chunk_id, content, metadata))

        # Insert 50 test activations
        timestamp = datetime.now(timezone.utc).isoformat()
        for i in range(50):
            chunk_id = f"chunk_{i:03d}"
            activation = float(i) / 50.0
            conn.execute(
                "INSERT INTO activations VALUES (?, ?, ?)", (chunk_id, activation, timestamp)
            )

        conn.commit()

        # Apply migration
        manager = MigrationManager()
        manager._migrate_v1_to_v2(conn)

        # Verify all 100 chunks preserved
        cursor = conn.execute("SELECT COUNT(*) FROM chunks")
        assert cursor.fetchone()[0] == 100, "All chunks should be preserved"

        # Verify all 50 activations preserved
        cursor = conn.execute("SELECT COUNT(*) FROM activations")
        assert cursor.fetchone()[0] == 50, "All activations should be preserved"

        # Verify chunk content integrity
        for chunk_id, original_content, original_metadata in chunks:
            cursor = conn.execute("SELECT content, metadata FROM chunks WHERE id = ?", (chunk_id,))
            row = cursor.fetchone()
            assert row is not None, f"Chunk {chunk_id} should exist"
            assert row[0] == original_content, "Content should be unchanged"
            assert row[1] == original_metadata, "Metadata should be unchanged"

        # Verify activation values preserved
        for i in range(50):
            chunk_id = f"chunk_{i:03d}"
            expected_activation = float(i) / 50.0
            cursor = conn.execute(
                "SELECT activation FROM activations WHERE chunk_id = ?", (chunk_id,)
            )
            row = cursor.fetchone()
            assert row is not None
            assert abs(row[0] - expected_activation) < 0.001, "Activation should be unchanged"

        conn.close()

    def test_v1_to_v2_new_columns_exist(self):
        """Test v1→v2 migration adds new columns correctly."""
        conn = sqlite3.connect(":memory:")
        self._create_v1_schema(conn)

        manager = MigrationManager()
        manager._migrate_v1_to_v2(conn)

        # Verify new columns in chunks table
        cursor = conn.execute("PRAGMA table_info(chunks)")
        columns = {row[1] for row in cursor.fetchall()}
        assert "first_access" in columns, "first_access column should be added"
        assert "last_access" in columns, "last_access column should be added"

        # Verify new column in activations table
        cursor = conn.execute("PRAGMA table_info(activations)")
        columns = {row[1] for row in cursor.fetchall()}
        assert "access_history" in columns, "access_history column should be added"

        conn.close()

    def test_v1_to_v2_access_history_initialization(self):
        """Test v1→v2 migration initializes access_history from last_access."""
        conn = sqlite3.connect(":memory:")
        self._create_v1_schema(conn)

        # Insert test data with specific timestamp
        test_timestamp = "2025-12-24T10:30:00Z"
        conn.execute("INSERT INTO chunks VALUES ('chunk_1', 'test', '{}')")
        conn.execute("INSERT INTO activations VALUES ('chunk_1', 0.5, ?)", (test_timestamp,))
        conn.commit()

        manager = MigrationManager()
        manager._migrate_v1_to_v2(conn)

        # Verify access_history was initialized
        cursor = conn.execute("SELECT access_history FROM activations WHERE chunk_id = 'chunk_1'")
        row = cursor.fetchone()
        assert row is not None
        assert row[0] is not None, "access_history should be initialized"

        # Parse and verify JSON structure
        history = json.loads(row[0])
        assert isinstance(history, list), "access_history should be a list"
        assert len(history) > 0, "access_history should have initial entry"
        assert "timestamp" in history[0], "Entry should have timestamp"

        conn.close()

    def test_v1_to_v2_empty_database(self):
        """Test v1→v2 migration on empty database."""
        conn = sqlite3.connect(":memory:")
        self._create_v1_schema(conn)

        manager = MigrationManager()
        manager._migrate_v1_to_v2(conn)

        # Verify no errors and tables still exist
        cursor = conn.execute("SELECT COUNT(*) FROM chunks")
        assert cursor.fetchone()[0] == 0

        cursor = conn.execute("SELECT COUNT(*) FROM activations")
        assert cursor.fetchone()[0] == 0

        conn.close()

    def test_v1_to_v2_with_null_metadata(self):
        """Test v1→v2 migration handles NULL values gracefully."""
        conn = sqlite3.connect(":memory:")
        self._create_v1_schema(conn)

        # Insert chunk with NULL metadata
        conn.execute("INSERT INTO chunks VALUES ('chunk_1', 'test', NULL)")
        conn.commit()

        manager = MigrationManager()
        manager._migrate_v1_to_v2(conn)

        # Verify migration succeeded and NULL preserved
        cursor = conn.execute("SELECT metadata FROM chunks WHERE id = 'chunk_1'")
        row = cursor.fetchone()
        assert row is not None
        assert row[0] is None, "NULL metadata should be preserved"

        conn.close()

    def test_v1_to_v2_idempotent(self):
        """Test v1→v2 migration is idempotent (can run multiple times safely)."""
        conn = sqlite3.connect(":memory:")
        self._create_v1_schema(conn)

        conn.execute("INSERT INTO chunks VALUES ('chunk_1', 'test', '{}')")
        conn.commit()

        manager = MigrationManager()

        # Run migration twice
        manager._migrate_v1_to_v2(conn)
        manager._migrate_v1_to_v2(conn)  # Should not fail

        # Verify data still correct
        cursor = conn.execute("SELECT COUNT(*) FROM chunks")
        assert cursor.fetchone()[0] == 1, "Should still have exactly 1 chunk"

        conn.close()


class TestMigrationRollback:
    """Test migration rollback functionality (Task 6.2)."""

    def test_rollback_on_constraint_violation(self):
        """Test rollback when migration violates constraints."""
        conn = sqlite3.connect(":memory:")
        conn.execute("CREATE TABLE test (id INTEGER PRIMARY KEY)")
        conn.execute("INSERT INTO test VALUES (1)")
        conn.commit()

        def failing_migration(connection: sqlite3.Connection) -> None:
            connection.execute("INSERT INTO test VALUES (2)")
            # This will fail - duplicate primary key
            connection.execute("INSERT INTO test VALUES (1)")

        migration = Migration(
            from_version=0, to_version=1, upgrade_fn=failing_migration, description="Failing"
        )

        with pytest.raises(StorageError):
            migration.apply(conn)

        # Verify rollback - only original row should exist
        cursor = conn.execute("SELECT COUNT(*) FROM test")
        assert cursor.fetchone()[0] == 1, "Rollback should restore original state"

        cursor = conn.execute("SELECT id FROM test")
        assert cursor.fetchone()[0] == 1, "Original row should still exist"

        conn.close()

    def test_transaction_atomicity(self):
        """Test migration is atomic - either fully applied or fully rolled back."""
        conn = sqlite3.connect(":memory:")
        conn.execute("CREATE TABLE test (value TEXT)")
        conn.commit()

        def partial_migration(connection: sqlite3.Connection) -> None:
            connection.execute("INSERT INTO test VALUES ('first')")
            connection.execute("INSERT INTO test VALUES ('second')")
            connection.execute("INSERT INTO test VALUES ('third')")
            # Fail after multiple inserts with a database error that will trigger rollback
            connection.execute("INSERT INTO test VALUES ('first')")
            # This constraint violation should trigger rollback
            connection.execute("CREATE TABLE test (id INTEGER)")  # This will fail - table exists

        migration = Migration(
            from_version=0, to_version=1, upgrade_fn=partial_migration, description="Atomic test"
        )

        with pytest.raises(StorageError):
            migration.apply(conn)

        # Verify complete rollback - table should be empty
        cursor = conn.execute("SELECT COUNT(*) FROM test")
        assert cursor.fetchone()[0] == 0, "All changes should be rolled back"

        conn.close()

    def test_error_message_includes_migration_details(self):
        """Test error message includes migration version and details."""
        conn = sqlite3.connect(":memory:")

        def failing_migration(connection: sqlite3.Connection) -> None:
            # Use a SQLite error instead of RuntimeError
            connection.execute("SELECT * FROM nonexistent_table")

        migration = Migration(
            from_version=5, to_version=6, upgrade_fn=failing_migration, description="Test"
        )

        with pytest.raises(StorageError) as exc_info:
            migration.apply(conn)

        error_msg = str(exc_info.value)
        assert "v5 -> v6" in error_msg, "Error should include version numbers"
        # Check for the sqlite error message
        assert "no such table" in error_msg.lower() or "table" in error_msg.lower(), (
            "Error should include original error details"
        )

        conn.close()


class TestMigrationErrorConditions:
    """Test migration error handling (Task 6.3)."""

    def test_database_locked_error(self):
        """Test migration handles database locked error."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            conn1 = sqlite3.connect(str(db_path))
            conn1.execute("CREATE TABLE schema_version (version INTEGER)")
            conn1.execute("INSERT INTO schema_version (version) VALUES (1)")
            conn1.commit()

            # Lock database with first connection
            conn1.execute("BEGIN EXCLUSIVE")

            # Try to migrate with second connection (should fail or timeout)
            conn2 = sqlite3.connect(str(db_path), timeout=0.1)

            def dummy_migration(conn: sqlite3.Connection) -> None:
                conn.execute("CREATE TABLE test (id INTEGER)")

            migration = Migration(
                from_version=1,
                to_version=2,
                upgrade_fn=dummy_migration,
                description="Test locked",
            )

            with pytest.raises((StorageError, sqlite3.OperationalError)):
                migration.apply(conn2)

            conn1.close()
            conn2.close()

    def test_permission_error_handling(self):
        """Test migration handles permission errors gracefully."""
        # This test is platform-dependent, so we'll mock the error
        conn = sqlite3.connect(":memory:")

        def permission_error_migration(connection: sqlite3.Connection) -> None:
            # Simulate permission error
            raise sqlite3.OperationalError("attempt to write a readonly database")

        migration = Migration(
            from_version=0,
            to_version=1,
            upgrade_fn=permission_error_migration,
            description="Permission test",
        )

        with pytest.raises(StorageError) as exc_info:
            migration.apply(conn)

        assert "readonly" in str(exc_info.value).lower()

        conn.close()

    def test_disk_full_error_handling(self):
        """Test migration handles disk full error."""
        conn = sqlite3.connect(":memory:")

        def disk_full_migration(connection: sqlite3.Connection) -> None:
            # Simulate disk full error
            raise sqlite3.OperationalError("database or disk is full")

        migration = Migration(
            from_version=0, to_version=1, upgrade_fn=disk_full_migration, description="Disk full"
        )

        with pytest.raises(StorageError) as exc_info:
            migration.apply(conn)

        error_msg = str(exc_info.value).lower()
        assert "disk" in error_msg or "full" in error_msg

        conn.close()


class TestMigrationManager:
    """Test full MigrationManager migrate() workflow."""

    def test_migrate_already_current(self):
        """Test migrate does nothing when already at current version."""
        from aurora.core.store.schema import SCHEMA_VERSION

        conn = sqlite3.connect(":memory:")
        conn.execute("CREATE TABLE schema_version (version INTEGER)")
        conn.execute(f"INSERT INTO schema_version (version) VALUES ({SCHEMA_VERSION})")
        conn.commit()

        manager = MigrationManager()
        manager.migrate(conn)  # Should not raise or modify anything

        version = manager.get_current_version(conn)
        assert version == SCHEMA_VERSION

        conn.close()

    def test_migrate_newer_version_raises_error(self):
        """Test migrate raises error when database is newer than supported."""
        conn = sqlite3.connect(":memory:")
        conn.execute("CREATE TABLE schema_version (version INTEGER)")
        conn.execute("INSERT INTO schema_version (version) VALUES (9999)")
        conn.commit()

        manager = MigrationManager()

        with pytest.raises(StorageError) as exc_info:
            manager.migrate(conn)

        error_msg = str(exc_info.value)
        assert "newer than supported" in error_msg or "upgrade AURORA" in error_msg

        conn.close()

    def test_migrate_sequential_application(self):
        """Test migrations are applied sequentially in correct order."""
        conn = sqlite3.connect(":memory:")
        conn.execute("CREATE TABLE schema_version (version INTEGER)")
        conn.execute("INSERT INTO schema_version (version) VALUES (0)")
        conn.commit()

        # Track migration order
        applied_migrations = []

        def track_migration(version: int):
            def migration_fn(connection: sqlite3.Connection) -> None:
                applied_migrations.append(version)

            return migration_fn

        manager = MigrationManager()
        # Clear existing migrations for this test
        manager._migrations = []

        # Add migrations in non-sequential order
        manager.add_migration(
            Migration(
                from_version=1, to_version=2, upgrade_fn=track_migration(2), description="v1->v2"
            )
        )
        manager.add_migration(
            Migration(
                from_version=0, to_version=1, upgrade_fn=track_migration(1), description="v0->v1"
            )
        )

        # Mock SCHEMA_VERSION to 2 for this test
        with mock.patch("aurora_core.store.migrations.SCHEMA_VERSION", 2):
            manager.migrate(conn)

        # Verify migrations applied in correct order
        assert applied_migrations == [1, 2], "Migrations should be applied in version order"

        conn.close()

    def test_backup_database_creates_backup(self):
        """Test backup_database creates a backup file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            conn = sqlite3.connect(str(db_path))
            conn.execute("CREATE TABLE test (id INTEGER)")
            conn.execute("INSERT INTO test VALUES (1)")
            conn.commit()
            conn.close()

            manager = MigrationManager()
            backup_path = manager.backup_database(str(db_path))

            assert Path(backup_path).exists(), "Backup file should exist"
            assert "backup" in backup_path, "Backup filename should contain 'backup'"

            # Verify backup contains data
            backup_conn = sqlite3.connect(backup_path)
            cursor = backup_conn.execute("SELECT COUNT(*) FROM test")
            assert cursor.fetchone()[0] == 1, "Backup should contain original data"
            backup_conn.close()

    def test_backup_database_memory_returns_memory(self):
        """Test backup_database handles in-memory databases."""
        manager = MigrationManager()
        backup_path = manager.backup_database(":memory:")
        assert backup_path == ":memory:", "Should return :memory: for in-memory DB"

    def test_migrate_with_backup_creates_backup(self):
        """Test migrate_with_backup creates backup before migration."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            conn = sqlite3.connect(str(db_path))

            # Create a minimal v1 schema that won't fail migration
            conn.execute("""
                CREATE TABLE chunks (
                    id TEXT PRIMARY KEY,
                    content TEXT NOT NULL,
                    metadata TEXT
                )
            """)
            conn.execute("""
                CREATE TABLE activations (
                    chunk_id TEXT PRIMARY KEY,
                    activation REAL NOT NULL,
                    last_access TIMESTAMP,
                    FOREIGN KEY (chunk_id) REFERENCES chunks (id)
                )
            """)
            conn.execute("CREATE TABLE schema_version (version INTEGER)")
            conn.execute("INSERT INTO schema_version (version) VALUES (1)")
            conn.commit()

            manager = MigrationManager()

            # Mock SCHEMA_VERSION to ensure migration is needed
            with mock.patch("aurora_core.store.migrations.SCHEMA_VERSION", 2):
                backup_path = manager.migrate_with_backup(conn, str(db_path))

            assert backup_path is not None, "Backup path should be returned"
            assert Path(backup_path).exists(), "Backup file should exist"

            conn.close()

    def test_migrate_with_backup_no_backup_if_not_needed(self):
        """Test migrate_with_backup skips backup if migration not needed."""
        from aurora.core.store.schema import SCHEMA_VERSION

        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            conn = sqlite3.connect(str(db_path))
            conn.execute("CREATE TABLE schema_version (version INTEGER)")
            conn.execute(f"INSERT INTO schema_version (version) VALUES ({SCHEMA_VERSION})")
            conn.commit()

            manager = MigrationManager()
            backup_path = manager.migrate_with_backup(conn, str(db_path))

            assert backup_path is None, "Should not create backup when migration not needed"

            conn.close()


class TestMigrationV2ToV3:
    """Test migration from v2 to v3 schema."""

    def _create_v2_schema(self, conn: sqlite3.Connection) -> None:
        """Create a v2 schema database."""
        conn.execute("""
            CREATE TABLE chunks (
                id TEXT PRIMARY KEY,
                content TEXT NOT NULL,
                metadata TEXT,
                first_access TIMESTAMP,
                last_access TIMESTAMP
            )
        """)

        conn.execute("""
            CREATE TABLE activations (
                chunk_id TEXT PRIMARY KEY,
                activation REAL NOT NULL,
                last_access TIMESTAMP,
                access_history JSON,
                FOREIGN KEY (chunk_id) REFERENCES chunks (id)
            )
        """)

        conn.execute("CREATE TABLE schema_version (version INTEGER)")
        conn.execute("INSERT INTO schema_version (version) VALUES (2)")
        conn.commit()

    def test_v2_to_v3_adds_embeddings_column(self):
        """Test v2→v3 migration adds embeddings column."""
        conn = sqlite3.connect(":memory:")
        self._create_v2_schema(conn)

        manager = MigrationManager()
        manager._migrate_v2_to_v3(conn)

        # Verify embeddings column exists
        cursor = conn.execute("PRAGMA table_info(chunks)")
        columns = {row[1] for row in cursor.fetchall()}
        assert "embeddings" in columns, "embeddings column should be added"

        conn.close()

    def test_v2_to_v3_preserves_existing_data(self):
        """Test v2→v3 migration preserves all existing data."""
        conn = sqlite3.connect(":memory:")
        self._create_v2_schema(conn)

        # Insert test data
        conn.execute("INSERT INTO chunks VALUES ('chunk_1', 'test', '{}', NULL, NULL)")
        conn.commit()

        manager = MigrationManager()
        manager._migrate_v2_to_v3(conn)

        # Verify data preserved
        cursor = conn.execute("SELECT id, content FROM chunks WHERE id = 'chunk_1'")
        row = cursor.fetchone()
        assert row is not None
        assert row[0] == "chunk_1"
        assert row[1] == "test"

        conn.close()

    def test_v2_to_v3_idempotent(self):
        """Test v2→v3 migration is idempotent."""
        conn = sqlite3.connect(":memory:")
        self._create_v2_schema(conn)

        manager = MigrationManager()

        # Run migration twice
        manager._migrate_v2_to_v3(conn)
        manager._migrate_v2_to_v3(conn)  # Should not fail

        # Verify schema correct
        cursor = conn.execute("PRAGMA table_info(chunks)")
        columns = [row[1] for row in cursor.fetchall()]
        # Count occurrences of embeddings - should appear once even after double migration
        embeddings_count = columns.count("embeddings")
        assert embeddings_count == 1, "embeddings column should only exist once"

        conn.close()
