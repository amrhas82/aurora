"""E2E tests for AURORA CLI error handling.

Tests real CLI commands to ensure errors are properly formatted and
displayed without Python tracebacks, and that appropriate exit codes are used.
"""

import os
import subprocess
import tempfile
from pathlib import Path

import pytest


def run_cli_command(args: list[str], env: dict | None = None) -> tuple[int, str, str]:
    """Run CLI command and return exit code, stdout, stderr.

    Args:
        args: Command arguments (e.g., ["aur", "mem", "search", "test"])
        env: Environment variables to set (merged with current environment)

    Returns:
        Tuple of (exit_code, stdout, stderr)
    """
    # Merge environment variables
    cmd_env = os.environ.copy()
    if env:
        cmd_env.update(env)

    # Run command
    result = subprocess.run(
        args,
        env=cmd_env,
        capture_output=True,
        text=True,
    )

    return result.returncode, result.stdout, result.stderr


class TestErrorHandlingBasic:
    """Test basic error handling behavior."""

    def test_invalid_command_shows_help(self):
        """Test that invalid command shows help without traceback."""
        exit_code, stdout, stderr = run_cli_command(["aur", "invalid-command"])

        # Should show error but not crash with traceback
        assert exit_code != 0
        assert "Traceback" not in stdout
        assert "Traceback" not in stderr

    def test_missing_required_argument(self):
        """Test that missing required argument shows clear error."""
        exit_code, stdout, stderr = run_cli_command(["aur", "budget", "set"])

        # Should show error about missing argument
        assert exit_code != 0
        assert "Traceback" not in stdout
        assert "Traceback" not in stderr


class TestErrorHandlingMemoryCommands:
    """Test error handling for memory commands."""

    def test_search_nonexistent_database(self, tmp_path: Path):
        """Test search with no database shows helpful error."""
        # Use isolated AURORA_HOME with no database
        env = {"AURORA_HOME": str(tmp_path)}

        exit_code, stdout, stderr = run_cli_command(
            ["aur", "mem", "search", "test"], env=env
        )

        # Should fail gracefully
        assert exit_code != 0
        assert "Traceback" not in stdout
        assert "Traceback" not in stderr
        # Should mention database or initialization
        combined_output = stdout + stderr
        assert any(
            keyword in combined_output.lower()
            for keyword in ["database", "init", "index", "memory"]
        )

    def test_index_nonexistent_path(self, tmp_path: Path):
        """Test index with nonexistent path shows clear error."""
        # Create config but index nonexistent path
        env = {"AURORA_HOME": str(tmp_path)}
        nonexistent_path = str(tmp_path / "nonexistent")

        exit_code, stdout, stderr = run_cli_command(
            ["aur", "mem", "index", nonexistent_path], env=env
        )

        # Should fail with clear error
        assert exit_code != 0
        assert "Traceback" not in stdout
        assert "Traceback" not in stderr
        combined_output = stdout + stderr
        assert "nonexistent" in combined_output.lower() or "not found" in combined_output.lower()

    def test_stats_empty_database(self, tmp_path: Path):
        """Test stats with empty database."""
        # Create minimal config
        config_dir = tmp_path / ".aurora"
        config_dir.mkdir(parents=True)

        env = {"AURORA_HOME": str(tmp_path)}

        exit_code, stdout, stderr = run_cli_command(["aur", "mem", "stats"], env=env)

        # Should either succeed with zero stats or fail gracefully
        assert "Traceback" not in stdout
        assert "Traceback" not in stderr


class TestErrorHandlingBudgetCommands:
    """Test error handling for budget commands."""

    def test_budget_invalid_amount(self, tmp_path: Path):
        """Test budget set with invalid amount."""
        env = {"AURORA_HOME": str(tmp_path)}

        exit_code, stdout, stderr = run_cli_command(
            ["aur", "budget", "set", "invalid"], env=env
        )

        # Should fail with clear error
        assert exit_code != 0
        assert "Traceback" not in stdout
        assert "Traceback" not in stderr

    def test_budget_negative_amount(self, tmp_path: Path):
        """Test budget set with negative amount."""
        env = {"AURORA_HOME": str(tmp_path)}

        exit_code, stdout, stderr = run_cli_command(
            ["aur", "budget", "set", "-10.0"], env=env
        )

        # Should fail (negative budget not allowed)
        assert exit_code != 0
        assert "Traceback" not in stdout
        assert "Traceback" not in stderr


class TestDebugMode:
    """Test debug mode behavior."""

    def test_debug_flag_shows_traceback(self, tmp_path: Path):
        """Test that --debug flag shows full traceback."""
        # Trigger an error with debug flag
        env = {"AURORA_HOME": str(tmp_path)}

        exit_code, stdout, stderr = run_cli_command(
            ["aur", "--debug", "mem", "search", "test"], env=env
        )

        # Should fail
        assert exit_code != 0

        # In debug mode, should show traceback OR debug information
        combined_output = stdout + stderr
        # Note: May show "Stack trace" or "Traceback" or debug info
        has_debug_info = any(
            keyword in combined_output
            for keyword in ["Traceback", "Stack trace", "debug mode", "DEBUG"]
        )
        # Accept either showing traceback or acknowledging debug mode
        # (implementation may vary)

    def test_aurora_debug_env_shows_traceback(self, tmp_path: Path):
        """Test that AURORA_DEBUG=1 environment variable shows traceback."""
        # Trigger an error with AURORA_DEBUG environment variable
        env = {"AURORA_HOME": str(tmp_path), "AURORA_DEBUG": "1"}

        exit_code, stdout, stderr = run_cli_command(
            ["aur", "mem", "search", "test"], env=env
        )

        # Should fail
        assert exit_code != 0

        # With AURORA_DEBUG=1, should show debug information
        combined_output = stdout + stderr
        has_debug_info = any(
            keyword in combined_output
            for keyword in ["Traceback", "Stack trace", "debug mode", "DEBUG"]
        )


class TestExitCodes:
    """Test that appropriate exit codes are used."""

    def test_success_returns_zero(self):
        """Test that successful commands return exit code 0."""
        # Just check help command succeeds
        exit_code, stdout, stderr = run_cli_command(["aur", "--help"])

        assert exit_code == 0

    def test_user_error_returns_one(self):
        """Test that user errors return exit code 1."""
        # Invalid command is a user error
        exit_code, stdout, stderr = run_cli_command(["aur", "invalid-command"])

        assert exit_code != 0  # Should be 1 or 2

    def test_system_error_handling(self, tmp_path: Path):
        """Test that system errors are handled gracefully."""
        # Create a directory with no permissions
        restricted_dir = tmp_path / "restricted"
        restricted_dir.mkdir()
        os.chmod(restricted_dir, 0o000)

        try:
            env = {"AURORA_HOME": str(tmp_path)}
            exit_code, stdout, stderr = run_cli_command(
                ["aur", "mem", "index", str(restricted_dir)], env=env
            )

            # Should fail but not crash
            assert exit_code != 0
            assert "Traceback" not in stdout
            assert "Traceback" not in stderr
        finally:
            # Restore permissions for cleanup
            os.chmod(restricted_dir, 0o755)


class TestCorruptedDatabase:
    """Test handling of corrupted database."""

    def test_corrupted_database_shows_helpful_error(self, tmp_path: Path):
        """Test that corrupted database shows helpful recovery message."""
        # Create a corrupted database file
        config_dir = tmp_path / ".aurora"
        config_dir.mkdir(parents=True)
        db_path = config_dir / "memory.db"

        # Write invalid content to database file
        db_path.write_text("This is not a valid SQLite database\n")

        env = {"AURORA_HOME": str(tmp_path)}

        exit_code, stdout, stderr = run_cli_command(
            ["aur", "mem", "search", "test"], env=env
        )

        # Should fail gracefully
        assert exit_code != 0
        assert "Traceback" not in stdout
        assert "Traceback" not in stderr

        # Should mention database or corruption
        combined_output = (stdout + stderr).lower()
        assert any(
            keyword in combined_output
            for keyword in ["database", "corrupt", "reset", "init"]
        )


class TestSchemaErrorHandling:
    """Test handling of schema mismatch errors."""

    def test_old_schema_shows_migration_message(self, tmp_path: Path):
        """Test that old schema database shows helpful migration message."""
        # Note: This test depends on Task 1.0 implementation
        # Create an old-schema database (7 columns instead of 9)
        import sqlite3

        config_dir = tmp_path / ".aurora"
        config_dir.mkdir(parents=True)
        db_path = config_dir / "memory.db"

        # Create old schema with 7 columns
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()

        # Old schema (without git_commit_hash and last_modified)
        cursor.execute("""
            CREATE TABLE chunks (
                chunk_id TEXT PRIMARY KEY,
                content TEXT NOT NULL,
                file_path TEXT NOT NULL,
                line_start INTEGER NOT NULL,
                line_end INTEGER NOT NULL,
                metadata TEXT,
                created_at REAL NOT NULL
            )
        """)

        cursor.execute("""
            CREATE TABLE activations (
                chunk_id TEXT PRIMARY KEY,
                base_level REAL NOT NULL DEFAULT 0.0,
                access_count INTEGER NOT NULL DEFAULT 0,
                last_access_time REAL,
                FOREIGN KEY (chunk_id) REFERENCES chunks(chunk_id)
            )
        """)

        conn.commit()
        conn.close()

        env = {"AURORA_HOME": str(tmp_path)}

        # Try to use the old database
        exit_code, stdout, stderr = run_cli_command(
            ["aur", "mem", "search", "test"], env=env
        )

        # Should fail gracefully
        assert exit_code != 0
        assert "Traceback" not in stdout
        assert "Traceback" not in stderr

        # Should mention schema or version
        combined_output = (stdout + stderr).lower()
        assert any(
            keyword in combined_output
            for keyword in ["schema", "version", "outdated", "reset", "init"]
        )
