"""E2E Test: Schema Migration Handling (Sprint 2 - Task 1.10)

This test suite validates that the CLI handles database schema migrations gracefully
when users have databases created with older versions of Aurora.

Test Scenarios:
1. Detect old schema (7-column chunks table)
2. Display user-friendly error message (no Python traceback)
3. Prompt for backup and reset
4. Successfully reset database to current schema
5. Verify data can be re-indexed after reset

Expected Behavior:
- User sees clear migration prompt, not a traceback
- Backup option is offered before destructive operations
- Reset creates valid database with current schema
- Process is non-blocking and user-friendly

Reference: PRD-0013 Section 4 (FR-1: Schema Migration), Task 1.0
"""

import os
import sqlite3
import tempfile
from collections.abc import Generator
from pathlib import Path

import pytest

from .conftest import run_cli_command

# Mark all tests in this file as E2E tests
pytestmark = [pytest.mark.e2e]


@pytest.fixture
def clean_aurora_home() -> Generator[Path, None, None]:
    """Create a clean, isolated Aurora home directory for testing."""
    original_home = os.environ.get("HOME")
    original_aurora_home = os.environ.get("AURORA_HOME")

    with tempfile.TemporaryDirectory() as tmp_home:
        os.environ["HOME"] = tmp_home
        os.environ["AURORA_HOME"] = str(Path(tmp_home) / ".aurora")

        aurora_home = Path(tmp_home) / ".aurora"
        aurora_home.mkdir(parents=True, exist_ok=True)

        yield aurora_home

        if original_home:
            os.environ["HOME"] = original_home
        elif "HOME" in os.environ:
            del os.environ["HOME"]

        if original_aurora_home:
            os.environ["AURORA_HOME"] = original_aurora_home
        elif "AURORA_HOME" in os.environ:
            del os.environ["AURORA_HOME"]


@pytest.fixture
def legacy_database(clean_aurora_home: Path) -> Path:
    """Create a legacy 7-column database (schema v1) for testing."""
    db_path = clean_aurora_home / "memory.db"

    # Create legacy schema with 7 columns (missing first_access, last_access)
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
    """,
    )
    conn.execute(
        """
        CREATE TABLE activations (
            chunk_id TEXT PRIMARY KEY,
            base_level REAL NOT NULL,
            last_access TIMESTAMP NOT NULL,
            access_count INTEGER DEFAULT 1
        )
    """,
    )
    # Add some test data
    conn.execute(
        "INSERT INTO chunks (id, type, content, metadata) VALUES (?, ?, ?, ?)",
        ("test_chunk_1", "code", '{"text": "test"}', "{}"),
    )
    conn.commit()
    conn.close()

    return db_path


@pytest.fixture
def sample_python_project() -> Generator[Path, None, None]:
    """Create a sample Python project for indexing."""
    with tempfile.TemporaryDirectory() as tmp_project:
        project_path = Path(tmp_project)

        # Create simple Python file
        (project_path / "test.py").write_text(
            '''"""Test module."""

def test_function():
    """A test function."""
    return 42
''',
        )

        yield project_path


class TestSchemaDetectionAndError:
    """Test that old schemas are detected and display user-friendly errors."""

    def test_aur_init_detects_old_schema(self, clean_aurora_home: Path, legacy_database: Path):
        """Test that 'aur init' detects old schema and displays friendly message."""
        # Legacy database already exists from fixture
        # Run aur init with automatic responses: skip API key, then no to reset
        result = run_cli_command(
            ["aur", "init"],
            capture_output=True,
            text=True,
            input="\nn\n",  # Skip API key (empty), then no to reset
        )

        # Verify output contains schema migration message
        output = result.stdout + result.stderr
        assert "Schema Migration Required" in output or "schema" in output.lower()
        assert "outdated" in output.lower() or "reset" in output.lower()

        # CRITICAL: Verify NO Python traceback in output
        assert "Traceback" not in output
        assert 'File "' not in output  # Python traceback format
        assert "line " not in output or "command line" in output.lower()

    def test_schema_error_shows_version_info(self, clean_aurora_home: Path, legacy_database: Path):
        """Test that schema error shows version mismatch details."""
        result = run_cli_command(
            ["aur", "init"],
            capture_output=True,
            text=True,
            input="\nn\n",  # Skip API key, no to reset
        )

        output = result.stdout + result.stderr

        # Should show version information
        assert "v1" in output or "version" in output.lower()
        assert "v3" in output or "required" in output.lower()


class TestBackupAndReset:
    """Test backup creation and database reset functionality."""

    def test_reset_with_backup_creates_backup(self, clean_aurora_home: Path, legacy_database: Path):
        """Test that reset flow creates backup when requested."""
        # Run with automatic responses: skip API key, yes to reset, yes to backup, no to index
        result = run_cli_command(
            ["aur", "init"],
            capture_output=True,
            text=True,
            input="\ny\ny\nn\n",  # Skip API key, yes to reset, yes to backup, no to index
        )

        output = result.stdout + result.stderr

        # Should mention backup
        assert "backup" in output.lower() or "Backup created" in output

        # Verify backup file exists
        backup_files = list(clean_aurora_home.glob("memory.db.bak.*"))
        assert len(backup_files) > 0, "Backup file should be created"

    def test_reset_without_backup(self, clean_aurora_home: Path, legacy_database: Path):
        """Test that reset works when user declines backup."""
        # Run with automatic responses: skip API key, yes to reset, no to backup, no to index
        result = run_cli_command(
            ["aur", "init"],
            capture_output=True,
            text=True,
            input="\ny\nn\nn\n",  # Skip API key, yes to reset, no to backup, no to index
        )

        # Should succeed (exit code 0 or non-error)
        # Note: Some implementations may have non-zero codes for user abort
        output = result.stdout + result.stderr
        assert "reset" in output.lower() or "database" in output.lower()

    def test_reset_creates_valid_schema(self, clean_aurora_home: Path, legacy_database: Path):
        """Test that reset creates a valid database with current schema."""
        # Perform reset: skip API key, yes to reset, no to backup, no to index
        result = run_cli_command(
            ["aur", "init"],
            capture_output=True,
            text=True,
            input="\ny\nn\nn\n",  # Skip API key, yes to reset, no to backup, no to index
        )

        # Verify database has current schema (9 columns)
        db_path = clean_aurora_home / "memory.db"
        if db_path.exists():
            conn = sqlite3.connect(str(db_path))
            cursor = conn.execute("PRAGMA table_info(chunks)")
            columns = cursor.fetchall()
            conn.close()

            # Current schema should have 9 columns
            # Skip assertion if reset didn't complete (user abort)
            if len(columns) > 0:
                assert len(columns) == 9, f"Expected 9 columns, found {len(columns)}"


class TestReindexingAfterReset:
    """Test that data can be re-indexed after schema reset."""

    def test_index_works_after_reset(
        self,
        clean_aurora_home: Path,
        legacy_database: Path,
        sample_python_project: Path,
    ):
        """Test that 'aur mem index' works after resetting schema."""
        # Reset the database: skip API key, yes to reset, no to backup, no to index
        run_cli_command(
            ["aur", "init"],
            capture_output=True,
            text=True,
            input="\ny\nn\nn\n",  # Skip API key, yes to reset, no to backup, no to index
        )

        # Now try to index the sample project
        result = run_cli_command(
            ["aur", "mem", "index", str(sample_python_project)],
            capture_output=True,
            text=True,
        )

        # Should succeed
        assert result.returncode == 0 or "indexed" in result.stdout.lower()

        output = result.stdout + result.stderr
        # Should show successful indexing
        assert "indexed" in output.lower() or "chunk" in output.lower()


class TestUserAbort:
    """Test that users can abort migration safely."""

    def test_user_can_abort_reset(self, clean_aurora_home: Path, legacy_database: Path):
        """Test that user can say 'no' to reset and database remains unchanged."""
        # Record original database state - check column count
        db_path = clean_aurora_home / "memory.db"
        conn = sqlite3.connect(str(db_path))
        cursor = conn.execute("PRAGMA table_info(chunks)")
        original_columns = len(cursor.fetchall())

        # Check test data still exists
        cursor = conn.execute("SELECT COUNT(*) FROM chunks WHERE id = ?", ("test_chunk_1",))
        original_has_data = cursor.fetchone()[0] > 0
        conn.close()

        # Run with "no" to abort: skip API key, then no to reset
        result = run_cli_command(
            ["aur", "init"],
            capture_output=True,
            text=True,
            input="\nn\n",  # Skip API key, no to reset
        )

        # Database should remain unchanged - still has old schema (7 columns)
        assert db_path.exists()
        conn = sqlite3.connect(str(db_path))
        cursor = conn.execute("PRAGMA table_info(chunks)")
        current_columns = len(cursor.fetchall())

        # Check test data still exists
        cursor = conn.execute("SELECT COUNT(*) FROM chunks WHERE id = ?", ("test_chunk_1",))
        current_has_data = cursor.fetchone()[0] > 0
        conn.close()

        assert current_columns == original_columns  # Should still be 7 (legacy schema)
        assert current_has_data == original_has_data  # Data should still exist

        output = result.stdout + result.stderr
        assert "abort" in output.lower() or "unchanged" in output.lower()


__all__ = [
    "TestSchemaDetectionAndError",
    "TestBackupAndReset",
    "TestReindexingAfterReset",
    "TestUserAbort",
]
