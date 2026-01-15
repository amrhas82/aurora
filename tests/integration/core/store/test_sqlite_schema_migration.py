"""Unit tests for SQLite schema migration functionality.

These tests verify:
- Schema version detection from existing databases
- Schema compatibility checking
- Database backup functionality
- Database reset functionality
- SchemaMismatchError handling
"""

import sqlite3
from pathlib import Path

import pytest

from aurora_core.exceptions import SchemaMismatchError, StorageError
from aurora_core.store.schema import SCHEMA_VERSION
from aurora_core.store.sqlite import SQLiteStore, backup_database


class TestSchemaVersionDetection:
    """Tests for _detect_schema_version method."""

    def test_detect_current_schema_version(self, tmp_path):
        """Test detection of current schema version (v3)."""
        db_path = tmp_path / "current_schema.db"
        store = SQLiteStore(db_path=str(db_path))

        # Should detect current version
        version, column_count = store._detect_schema_version()

        assert version == SCHEMA_VERSION
        assert column_count == 9  # Current schema has 9 columns in chunks table

        store.close()

    def test_detect_legacy_7_column_schema(self, tmp_path):
        """Test detection of legacy 7-column schema (v1)."""
        db_path = tmp_path / "legacy_schema.db"

        # Create a legacy database with 7-column chunks table
        conn = sqlite3.connect(str(db_path))
        conn.execute(
            """
            CREATE TABLE chunks (
                id TEXT PRIMARY KEY,
                type TEXT NOT NULL,
                content JSON NOT NULL,
                metadata JSON,
                embeddings BLOB,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """
        )
        conn.execute(
            """
            CREATE TABLE activations (
                chunk_id TEXT PRIMARY KEY,
                base_level REAL NOT NULL,
                last_access TIMESTAMP NOT NULL,
                access_count INTEGER DEFAULT 1
            )
        """
        )
        conn.commit()
        conn.close()

        # Now open with SQLiteStore - should detect legacy schema
        # But first, we need to bypass the compatibility check
        # Create store without full init to test detection only
        store = SQLiteStore.__new__(SQLiteStore)
        store.db_path = str(db_path)
        store.timeout = 5.0
        store.wal_mode = True
        store._local = type("LocalStorage", (), {})()
        store._local.connection = None

        # Get connection manually
        conn = sqlite3.connect(str(db_path), timeout=5.0)
        conn.row_factory = sqlite3.Row
        store._local.connection = conn

        version, column_count = store._detect_schema_version()

        assert version == 1  # Legacy schema detected as v1
        assert column_count == 7  # 7 columns in legacy schema

        store.close()

    def test_detect_fresh_database(self, tmp_path):
        """Test detection for fresh database (no chunks table)."""
        db_path = tmp_path / "fresh.db"

        # Create empty database file
        conn = sqlite3.connect(str(db_path))
        conn.close()

        # Create store without full init
        store = SQLiteStore.__new__(SQLiteStore)
        store.db_path = str(db_path)
        store.timeout = 5.0
        store.wal_mode = True
        store._local = type("LocalStorage", (), {})()
        store._local.connection = None

        conn = sqlite3.connect(str(db_path), timeout=5.0)
        conn.row_factory = sqlite3.Row
        store._local.connection = conn

        version, column_count = store._detect_schema_version()

        # Fresh database should report current version with 0 columns
        assert version == SCHEMA_VERSION
        assert column_count == 0

        store.close()

    def test_detect_version_from_schema_version_table(self, tmp_path):
        """Test that schema_version table is used if present."""
        db_path = tmp_path / "with_version.db"

        # Create database with schema_version table
        conn = sqlite3.connect(str(db_path))
        conn.execute(
            """
            CREATE TABLE schema_version (
                version INTEGER PRIMARY KEY,
                applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """
        )
        conn.execute("INSERT INTO schema_version (version) VALUES (2)")
        conn.execute(
            """
            CREATE TABLE chunks (
                id TEXT PRIMARY KEY,
                type TEXT NOT NULL,
                content JSON NOT NULL,
                metadata JSON,
                embeddings BLOB,
                created_at TIMESTAMP,
                updated_at TIMESTAMP,
                first_access TIMESTAMP,
                last_access TIMESTAMP
            )
        """
        )
        conn.commit()
        conn.close()

        # Create store without full init
        store = SQLiteStore.__new__(SQLiteStore)
        store.db_path = str(db_path)
        store.timeout = 5.0
        store.wal_mode = True
        store._local = type("LocalStorage", (), {})()
        store._local.connection = None

        conn = sqlite3.connect(str(db_path), timeout=5.0)
        conn.row_factory = sqlite3.Row
        store._local.connection = conn

        version, column_count = store._detect_schema_version()

        assert version == 2  # Version from schema_version table
        assert column_count == 9

        store.close()


class TestSchemaCompatibilityCheck:
    """Tests for _check_schema_compatibility method."""

    def test_compatible_schema_passes(self, tmp_path):
        """Test that compatible schema passes without error."""
        db_path = tmp_path / "compatible.db"
        store = SQLiteStore(db_path=str(db_path))

        # Should not raise
        store._check_schema_compatibility()

        store.close()

    def test_incompatible_schema_raises_error(self, tmp_path):
        """Test that incompatible schema raises SchemaMismatchError."""
        db_path = tmp_path / "incompatible.db"

        # Create legacy database
        conn = sqlite3.connect(str(db_path))
        conn.execute(
            """
            CREATE TABLE chunks (
                id TEXT PRIMARY KEY,
                type TEXT NOT NULL,
                content JSON NOT NULL,
                metadata JSON,
                embeddings BLOB,
                created_at TIMESTAMP,
                updated_at TIMESTAMP
            )
        """
        )
        conn.commit()
        conn.close()

        # Opening SQLiteStore should raise SchemaMismatchError
        with pytest.raises(SchemaMismatchError) as exc_info:
            SQLiteStore(db_path=str(db_path))

        assert exc_info.value.found_version == 1
        assert exc_info.value.expected_version == SCHEMA_VERSION
        assert str(db_path) in str(exc_info.value.db_path) or exc_info.value.db_path is None

    def test_fresh_database_passes(self, tmp_path):
        """Test that fresh database (no existing tables) passes."""
        db_path = tmp_path / "fresh.db"

        # Should not raise - fresh database gets new schema
        store = SQLiteStore(db_path=str(db_path))
        store._check_schema_compatibility()

        store.close()


class TestBackupDatabase:
    """Tests for backup_database function."""

    def test_backup_creates_file(self, tmp_path):
        """Test that backup creates a backup file."""
        db_path = tmp_path / "original.db"

        # Create a test database
        conn = sqlite3.connect(str(db_path))
        conn.execute("CREATE TABLE test (id INTEGER)")
        conn.execute("INSERT INTO test VALUES (1)")
        conn.commit()
        conn.close()

        # Create backup
        backup_path = backup_database(str(db_path))

        assert Path(backup_path).exists()
        assert backup_path.startswith(str(db_path))
        assert ".bak." in backup_path

    def test_backup_contains_data(self, tmp_path):
        """Test that backup contains the original data."""
        db_path = tmp_path / "original.db"

        # Create a test database with data
        conn = sqlite3.connect(str(db_path))
        conn.execute("CREATE TABLE test (id INTEGER, value TEXT)")
        conn.execute("INSERT INTO test VALUES (1, 'test_value')")
        conn.commit()
        conn.close()

        # Create backup
        backup_path = backup_database(str(db_path))

        # Verify backup contains data
        backup_conn = sqlite3.connect(backup_path)
        cursor = backup_conn.execute("SELECT value FROM test WHERE id = 1")
        row = cursor.fetchone()
        backup_conn.close()

        assert row is not None
        assert row[0] == "test_value"

    def test_backup_nonexistent_file_raises(self, tmp_path):
        """Test that backing up non-existent file raises error."""
        db_path = tmp_path / "nonexistent.db"

        with pytest.raises(StorageError) as exc_info:
            backup_database(str(db_path))

        assert "file not found" in str(exc_info.value).lower()

    def test_backup_timestamp_format(self, tmp_path):
        """Test that backup filename has correct timestamp format."""
        db_path = tmp_path / "original.db"

        # Create test database
        conn = sqlite3.connect(str(db_path))
        conn.execute("CREATE TABLE test (id INTEGER)")
        conn.commit()
        conn.close()

        backup_path = backup_database(str(db_path))

        # Extract timestamp from filename
        # Format: original.db.bak.YYYYMMDD_HHMMSS
        parts = backup_path.split(".bak.")
        assert len(parts) == 2
        timestamp = parts[1]

        # Verify timestamp format (YYYYMMDD_HHMMSS)
        assert len(timestamp) == 15
        assert "_" in timestamp


class TestResetDatabase:
    """Tests for reset_database method."""

    def test_reset_creates_fresh_schema(self, tmp_path):
        """Test that reset creates a fresh database with current schema."""
        db_path = tmp_path / "to_reset.db"

        # Create initial store
        store = SQLiteStore(db_path=str(db_path))

        # Add some data
        conn = store._get_connection()
        conn.execute("INSERT INTO schema_version (version) VALUES (999)")
        conn.commit()

        # Reset the database
        result = store.reset_database()

        assert result is True

        # Verify fresh schema
        version, column_count = store._detect_schema_version()
        assert version == SCHEMA_VERSION
        assert column_count == 9

        store.close()

    def test_reset_removes_wal_files(self, tmp_path):
        """Test that reset removes WAL and SHM files."""
        db_path = tmp_path / "with_wal.db"

        # Create store (will create WAL file)
        store = SQLiteStore(db_path=str(db_path))
        store.close()

        # Manually create WAL and SHM files if not present
        wal_path = Path(f"{db_path}-wal")
        shm_path = Path(f"{db_path}-shm")
        wal_path.touch()
        shm_path.touch()

        assert wal_path.exists()
        assert shm_path.exists()

        # Create new store and reset
        store2 = SQLiteStore(db_path=str(db_path))
        store2.reset_database()
        store2.close()

        # WAL and SHM should be gone after reset and close
        # Note: New WAL files may be created when opening the store after reset,
        # but the old ones from before reset should be deleted
        # The test verifies that reset_database() cleans up the files
        assert not wal_path.exists()
        assert not shm_path.exists()

    def test_reset_memory_database(self):
        """Test that reset works for in-memory databases."""
        store = SQLiteStore(db_path=":memory:")

        # Add some data
        conn = store._get_connection()
        conn.execute("INSERT INTO schema_version (version) VALUES (999)")
        conn.commit()

        # Reset should work for in-memory
        result = store.reset_database()

        assert result is True

        # Verify schema is fresh
        version, _ = store._detect_schema_version()
        assert version == SCHEMA_VERSION

        store.close()


class TestSchemaMismatchError:
    """Tests for SchemaMismatchError exception."""

    def test_error_attributes(self):
        """Test that error has correct attributes."""
        error = SchemaMismatchError(
            found_version=1,
            expected_version=3,
            db_path="/path/to/db",
        )

        assert error.found_version == 1
        assert error.expected_version == 3
        assert error.db_path == "/path/to/db"

    def test_error_message_format(self):
        """Test that error message is user-friendly."""
        error = SchemaMismatchError(
            found_version=1,
            expected_version=3,
        )

        message = str(error)
        assert "v1" in message
        assert "v3" in message
        assert "outdated" in message.lower() or "required" in message.lower()

    def test_error_without_db_path(self):
        """Test that error works without db_path."""
        error = SchemaMismatchError(
            found_version=1,
            expected_version=3,
        )

        assert error.db_path is None
        # Should not raise when converting to string
        str(error)


__all__ = [
    "TestSchemaVersionDetection",
    "TestSchemaCompatibilityCheck",
    "TestBackupDatabase",
    "TestResetDatabase",
    "TestSchemaMismatchError",
]
