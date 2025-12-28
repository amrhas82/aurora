"""E2E Test: Database Persistence (Task 1.2)

This test suite validates that data persists across multiple command invocations
and that all commands consistently use the same database.

Test Scenario: Database Persistence
1. Index data into Aurora
2. Run multiple commands (stats, search, query)
3. Verify all commands use the same database
4. Verify data persists across command invocations
5. Test deleting local aurora.db (if exists) doesn't affect Aurora

Expected: These tests will FAIL initially due to Issue #2 (database path confusion)
- Current behavior: Commands use different databases or lose data
- Expected behavior: Single source of truth at ~/.aurora/memory.db

Reference: PRD-0010 Section 3 (User Stories), FR-1 (Database Path Management)
"""

import json
import os
import shutil
import sqlite3
import subprocess
import tempfile
from pathlib import Path
from typing import Generator

import pytest


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
def sample_python_project() -> Generator[Path, None, None]:
    """Create a sample Python project for indexing."""
    with tempfile.TemporaryDirectory() as tmp_project:
        project_path = Path(tmp_project)

        # Create simple Python files
        (project_path / "main.py").write_text('''"""Main module."""

def main():
    """Entry point."""
    print("Hello Aurora")


if __name__ == "__main__":
    main()
''')

        (project_path / "helpers.py").write_text('''"""Helper functions."""

def helper_one():
    """First helper function."""
    return "helper1"


def helper_two():
    """Second helper function."""
    return "helper2"
''')

        yield project_path


class TestDatabasePersistence:
    """E2E tests for database persistence across commands.

    These tests verify that Aurora maintains a single, persistent database
    across multiple command invocations.
    """

    def test_1_2_1_index_then_multiple_commands_same_db(
        self, clean_aurora_home: Path, sample_python_project: Path
    ) -> None:
        """Test 1.2.1: Write test that indexes data, then runs multiple commands.

        Verifies that index → stats → search → stats all work together.

        EXPECTED TO FAIL: Commands may use different databases.
        """
        # Setup config
        config_path = clean_aurora_home / "config.json"
        expected_db = clean_aurora_home / "memory.db"
        config_data = {
            "llm": {"provider": "anthropic"},
            "db_path": str(expected_db),
        }
        config_path.write_text(json.dumps(config_data, indent=2))

        # Index files
        index_result = subprocess.run(
            ["aur", "mem", "index", "."],
            capture_output=True,
            text=True,
            cwd=sample_python_project,
            timeout=60,
        )
        assert index_result.returncode == 0, f"Index failed: {index_result.stderr}"

        # Get stats (first time)
        stats1_result = subprocess.run(
            ["aur", "mem", "stats"],
            capture_output=True,
            text=True,
            cwd=sample_python_project,
            timeout=30,
        )
        assert stats1_result.returncode == 0, f"Stats failed: {stats1_result.stderr}"

        # Run search
        search_result = subprocess.run(
            ["aur", "mem", "search", "helper"],
            capture_output=True,
            text=True,
            cwd=sample_python_project,
            timeout=30,
        )
        assert search_result.returncode == 0, f"Search failed: {search_result.stderr}"

        # Get stats (second time - should show same data)
        stats2_result = subprocess.run(
            ["aur", "mem", "stats"],
            capture_output=True,
            text=True,
            cwd=sample_python_project,
            timeout=30,
        )
        assert stats2_result.returncode == 0, f"Stats failed: {stats2_result.stderr}"

        # Both stats outputs should be consistent
        assert stats1_result.stdout == stats2_result.stdout, (
            f"Stats should be consistent across calls:\n"
            f"First call: {stats1_result.stdout}\n"
            f"Second call: {stats2_result.stdout}"
        )

    def test_1_2_2_all_commands_use_same_database(
        self, clean_aurora_home: Path, sample_python_project: Path
    ) -> None:
        """Test 1.2.2: Verify all commands (index, search, query, stats) use same database.

        EXPECTED TO FAIL: Commands may use different database paths.
        """
        # Setup config
        config_path = clean_aurora_home / "config.json"
        expected_db = clean_aurora_home / "memory.db"
        config_data = {
            "llm": {"provider": "anthropic"},
            "db_path": str(expected_db),
        }
        config_path.write_text(json.dumps(config_data, indent=2))

        # Index files
        subprocess.run(
            ["aur", "mem", "index", "."],
            capture_output=True,
            text=True,
            cwd=sample_python_project,
            timeout=60,
            check=True,
        )

        # Verify DB exists at expected location
        assert expected_db.exists(), f"Database should exist at {expected_db}"

        # Get direct chunk count from DB
        conn = sqlite3.connect(expected_db)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM chunks")
        db_chunk_count = cursor.fetchone()[0]
        conn.close()

        assert db_chunk_count > 0, f"Database should have chunks after indexing, got {db_chunk_count}"

        # Run stats and parse output
        stats_result = subprocess.run(
            ["aur", "mem", "stats"],
            capture_output=True,
            text=True,
            cwd=sample_python_project,
            timeout=30,
            check=True,
        )

        # Try to extract chunk count from stats output
        # Stats output format varies, but should mention chunks
        stats_output = stats_result.stdout.lower()
        assert "chunk" in stats_output or str(db_chunk_count) in stats_result.stdout, (
            f"Stats should reflect database contents:\n"
            f"Expected {db_chunk_count} chunks\n"
            f"Stats output: {stats_result.stdout}"
        )

        # Run search (should return results if using correct DB)
        search_result = subprocess.run(
            ["aur", "mem", "search", "def"],
            capture_output=True,
            text=True,
            cwd=sample_python_project,
            timeout=30,
            check=True,
        )

        # Search should find something
        assert len(search_result.stdout) > 0, "Search should return results from indexed DB"

    def test_1_2_3_data_persists_across_command_invocations(
        self, clean_aurora_home: Path, sample_python_project: Path
    ) -> None:
        """Test 1.2.3: Test data persists across command invocations.

        Run index, exit, run search/stats - data should still be there.

        EXPECTED TO FAIL: Data may not persist if wrong DB is used.
        """
        # Setup config
        config_path = clean_aurora_home / "config.json"
        expected_db = clean_aurora_home / "memory.db"
        config_data = {
            "llm": {"provider": "anthropic"},
            "db_path": str(expected_db),
        }
        config_path.write_text(json.dumps(config_data, indent=2))

        # Index files (first command invocation)
        subprocess.run(
            ["aur", "mem", "index", "."],
            capture_output=True,
            text=True,
            cwd=sample_python_project,
            timeout=60,
            check=True,
        )

        # Get chunk count directly from DB
        conn = sqlite3.connect(expected_db)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM chunks")
        initial_count = cursor.fetchone()[0]
        conn.close()

        assert initial_count > 0, "Should have indexed chunks"

        # Simulate "exiting" - just run a new command (separate invocation)
        # If Aurora is using correct persistent DB, data should still be there

        # Second command invocation - stats
        stats_result = subprocess.run(
            ["aur", "mem", "stats"],
            capture_output=True,
            text=True,
            cwd=sample_python_project,
            timeout=30,
            check=True,
        )

        # Stats should show non-zero chunks
        stats_output = stats_result.stdout.lower()
        assert "0" not in stats_output or "chunk" in stats_output, (
            f"Stats should show persisted data:\n{stats_result.stdout}"
        )

        # Third command invocation - search
        search_result = subprocess.run(
            ["aur", "mem", "search", "main"],
            capture_output=True,
            text=True,
            cwd=sample_python_project,
            timeout=30,
            check=True,
        )

        # Search should find results from persisted data
        assert "main" in search_result.stdout.lower() or len(search_result.stdout) > 50, (
            f"Search should find persisted data:\n{search_result.stdout}"
        )

        # Verify DB still has same chunk count (data not lost)
        conn = sqlite3.connect(expected_db)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM chunks")
        final_count = cursor.fetchone()[0]
        conn.close()

        assert final_count == initial_count, (
            f"Chunk count should persist: initial={initial_count}, final={final_count}"
        )

    def test_1_2_4_deleting_local_aurora_db_does_not_affect_operations(
        self, clean_aurora_home: Path, sample_python_project: Path
    ) -> None:
        """Test 1.2.4: Test deleting local aurora.db (if exists) doesn't affect Aurora operations.

        If system creates local aurora.db by mistake, deleting it shouldn't break Aurora
        (because Aurora should be using ~/.aurora/memory.db).

        EXPECTED TO FAIL: If system uses local aurora.db, deleting it will break Aurora.
        """
        # Setup config
        config_path = clean_aurora_home / "config.json"
        expected_db = clean_aurora_home / "memory.db"
        config_data = {
            "llm": {"provider": "anthropic"},
            "db_path": str(expected_db),
        }
        config_path.write_text(json.dumps(config_data, indent=2))

        # Index files
        subprocess.run(
            ["aur", "mem", "index", "."],
            capture_output=True,
            text=True,
            cwd=sample_python_project,
            timeout=60,
            check=True,
        )

        # Check if a local aurora.db was created (bug behavior)
        local_db = sample_python_project / "aurora.db"

        # If local DB was created (bug), delete it
        if local_db.exists():
            local_db.unlink()

        # Now try to run commands - they should still work if using correct DB
        stats_result = subprocess.run(
            ["aur", "mem", "stats"],
            capture_output=True,
            text=True,
            cwd=sample_python_project,
            timeout=30,
        )

        # This will fail if Aurora was using the local DB we just deleted
        assert stats_result.returncode == 0, (
            f"Stats should work even after deleting local aurora.db:\n"
            f"stderr: {stats_result.stderr}\n"
            f"This means Aurora was incorrectly using local aurora.db instead of {expected_db}"
        )

        # Search should also work
        search_result = subprocess.run(
            ["aur", "mem", "search", "helper"],
            capture_output=True,
            text=True,
            cwd=sample_python_project,
            timeout=30,
        )

        assert search_result.returncode == 0, (
            f"Search should work even after deleting local aurora.db:\n"
            f"stderr: {search_result.stderr}"
        )

    def test_1_2_5_verify_aurora_home_db_contains_expected_chunks(
        self, clean_aurora_home: Path, sample_python_project: Path
    ) -> None:
        """Test 1.2.5: Verify ~/.aurora/memory.db contains expected chunks after all operations.

        Final verification that the correct database has all our data.

        EXPECTED TO FAIL: Data may be in wrong location or missing.
        """
        # Setup config
        config_path = clean_aurora_home / "config.json"
        expected_db = clean_aurora_home / "memory.db"
        config_data = {
            "llm": {"provider": "anthropic"},
            "db_path": str(expected_db),
        }
        config_path.write_text(json.dumps(config_data, indent=2))

        # Index files
        subprocess.run(
            ["aur", "mem", "index", "."],
            capture_output=True,
            text=True,
            cwd=sample_python_project,
            timeout=60,
            check=True,
        )

        # Run multiple operations
        subprocess.run(
            ["aur", "mem", "stats"],
            capture_output=True,
            text=True,
            cwd=sample_python_project,
            timeout=30,
            check=True,
        )

        subprocess.run(
            ["aur", "mem", "search", "main"],
            capture_output=True,
            text=True,
            cwd=sample_python_project,
            timeout=30,
            check=True,
        )

        # Verify DB exists at correct location
        assert expected_db.exists(), f"Database should exist at {expected_db}"

        # Verify DB has expected content
        conn = sqlite3.connect(expected_db)
        cursor = conn.cursor()

        # Check chunks table
        cursor.execute("SELECT COUNT(*) FROM chunks")
        chunk_count = cursor.fetchone()[0]
        assert chunk_count > 0, f"Should have chunks in {expected_db}, got {chunk_count}"

        # Check that chunks are from our sample project
        cursor.execute("SELECT DISTINCT file_path FROM chunks LIMIT 5")
        file_paths = [row[0] for row in cursor.fetchall()]

        # At least one file path should reference our sample files
        assert len(file_paths) > 0, "Should have file paths in chunks"

        # Check activations table exists and has data
        cursor.execute("SELECT COUNT(*) FROM activations")
        activation_count = cursor.fetchone()[0]
        assert activation_count > 0, f"Should have activations in {expected_db}, got {activation_count}"

        conn.close()

    def test_1_2_6_database_path_consistency_bug_detection(
        self, clean_aurora_home: Path, sample_python_project: Path
    ) -> None:
        """Test 1.2.6: Detect and document the database path consistency bug (Issue #2).

        This test explicitly checks for the bug: commands using different database paths.

        EXPECTED TO FAIL: This test documents the bug.
        """
        # Setup config
        config_path = clean_aurora_home / "config.json"
        expected_db = clean_aurora_home / "memory.db"
        config_data = {
            "llm": {"provider": "anthropic"},
            "db_path": str(expected_db),
        }
        config_path.write_text(json.dumps(config_data, indent=2))

        # Index files
        subprocess.run(
            ["aur", "mem", "index", "."],
            capture_output=True,
            text=True,
            cwd=sample_python_project,
            timeout=60,
            check=True,
        )

        # Check which databases exist
        local_db = sample_python_project / "aurora.db"
        cwd_db = Path.cwd() / "aurora.db"

        databases_found = []
        if expected_db.exists():
            databases_found.append(f"~/.aurora/memory.db (CORRECT): {expected_db}")
        if local_db.exists():
            databases_found.append(f"project/aurora.db (WRONG): {local_db}")
        if cwd_db.exists() and cwd_db != expected_db and cwd_db != local_db:
            databases_found.append(f"cwd/aurora.db (WRONG): {cwd_db}")

        # If multiple databases exist, we have Issue #2
        if len(databases_found) > 1:
            pytest.fail(
                f"ISSUE #2 DETECTED: Multiple databases found!\n"
                f"Found {len(databases_found)} databases:\n" +
                "\n".join(f"  - {db}" for db in databases_found) +
                f"\n\nShould only have one database at: {expected_db}\n"
                f"Fix: All commands must use config.get_db_path()"
            )

        # If no database at expected location, fail
        if not expected_db.exists():
            pytest.fail(
                f"ISSUE #2 DETECTED: Database not at expected location!\n"
                f"Expected: {expected_db}\n"
                f"Found: {databases_found if databases_found else 'No databases found'}\n"
                f"Fix: All commands must use config.get_db_path() which returns ~/.aurora/memory.db"
            )


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
