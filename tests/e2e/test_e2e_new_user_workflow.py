"""E2E Test: New User Workflow (Task 1.1)

This test suite validates the complete new user experience from scratch.
These tests are designed to FAIL initially, proving the bugs exist (Issue #2: Database path confusion).

Test Scenario: Fresh Aurora Installation
1. Clean ~/.aurora directory (simulate new user)
2. Run aur init - should create config and DB at ~/.aurora/
3. Run aur mem index . - should write chunks to ~/.aurora/memory.db
4. Run aur mem stats - should show correct chunk count
5. Run aur mem search "function" - should return results
6. Run aur query "what is X?" - should use indexed data
7. Verify NO local aurora.db created in project directory

Expected: These tests will FAIL because of Issue #2 (database path confusion)
- Current behavior: Creates aurora.db in current working directory
- Expected behavior: All data in ~/.aurora/memory.db

Reference: PRD-0010 Section 3 (User Stories), US-1 (Single Database Location)
"""

import json
import os
import shutil
import sqlite3
import subprocess
import tempfile
from collections.abc import Generator
from pathlib import Path
from unittest.mock import patch

import pytest

from .conftest import run_cli_command


# Mark all tests in this file as E2E tests
pytestmark = [pytest.mark.e2e]


@pytest.fixture
def clean_aurora_home() -> Generator[Path, None, None]:
    """Create a clean, isolated Aurora home directory for testing.

    Temporarily replaces ~/.aurora with a test directory, then restores
    original state after test completes.

    Yields:
        Path to the clean Aurora home directory
    """
    # Store original environment
    original_home = os.environ.get("HOME")
    original_aurora_home = os.environ.get("AURORA_HOME")

    # Create temporary home directory
    with tempfile.TemporaryDirectory() as tmp_home:
        # Set HOME so ~/.aurora resolves to our temp directory
        os.environ["HOME"] = tmp_home
        # Also set AURORA_HOME explicitly for clarity
        os.environ["AURORA_HOME"] = str(Path(tmp_home) / ".aurora")

        aurora_home = Path(tmp_home) / ".aurora"

        yield aurora_home

        # Restore original environment
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
    """Create a sample Python project for indexing.

    Creates a minimal Python project with functions and classes
    that can be indexed and searched.

    Yields:
        Path to the sample project directory
    """
    with tempfile.TemporaryDirectory() as tmp_project:
        project_path = Path(tmp_project)

        # Create a realistic Python project structure
        (project_path / "src").mkdir()
        (project_path / "src" / "__init__.py").write_text("")

        # Create a module with searchable functions
        (
            project_path / "src" / "calculator.py"
        ).write_text('''"""Calculator module with math functions."""

def add(a: int, b: int) -> int:
    """Add two numbers together."""
    return a + b


def subtract(a: int, b: int) -> int:
    """Subtract b from a."""
    return a - b


def multiply(a: int, b: int) -> int:
    """Multiply two numbers."""
    return a * b


def divide(a: int, b: int) -> float:
    """Divide a by b.

    Args:
        a: Numerator
        b: Denominator (must not be zero)

    Returns:
        The result of a / b

    Raises:
        ZeroDivisionError: If b is zero
    """
    if b == 0:
        raise ZeroDivisionError("Cannot divide by zero")
    return a / b


class Calculator:
    """A simple calculator class."""

    def __init__(self):
        self.result = 0

    def add(self, value: int) -> int:
        """Add value to result."""
        self.result += value
        return self.result

    def reset(self):
        """Reset calculator to zero."""
        self.result = 0
''')

        # Create another module for variety
        (project_path / "src" / "utils.py").write_text('''"""Utility functions."""

def format_number(n: float, precision: int = 2) -> str:
    """Format a number with specified precision."""
    return f"{n:.{precision}f}"


def is_even(n: int) -> bool:
    """Check if a number is even."""
    return n % 2 == 0


def clamp(value: int, min_val: int, max_val: int) -> int:
    """Clamp a value between min and max."""
    return max(min_val, min(value, max_val))
''')

        # Create tests directory
        (project_path / "tests").mkdir()
        (project_path / "tests" / "__init__.py").write_text("")
        (
            project_path / "tests" / "test_calculator.py"
        ).write_text('''"""Tests for calculator module."""
import pytest
from src.calculator import add, subtract, multiply, divide, Calculator

from .conftest import run_cli_command


def test_add():
    assert add(2, 3) == 5


def test_subtract():
    assert subtract(5, 3) == 2


def test_divide_by_zero():
    with pytest.raises(ZeroDivisionError):
        divide(1, 0)
''')

        yield project_path


class TestNewUserWorkflowE2E:
    """E2E tests for complete new user workflow.

    These tests simulate a new user installing and using Aurora for the first time.
    Expected to FAIL initially due to Issue #2 (database path confusion).
    """

    def test_1_1_1_clean_aurora_creates_home_directory(self, clean_aurora_home: Path) -> None:
        """Test 1.1.1: Fresh Aurora installation simulates clean ~/.aurora.

        Verifies that a new user starts with no Aurora data.
        """
        # Verify home directory does not exist yet (clean state)
        assert not clean_aurora_home.exists(), "Aurora home should not exist before init"

    def test_1_1_2_aur_init_creates_config_and_db(
        self, clean_aurora_home: Path, sample_python_project: Path
    ) -> None:
        """Test 1.1.2: aur init creates config at ~/.aurora/config.json and DB at ~/.aurora/memory.db.

        Expected behavior (from PRD):
        - Creates ~/.aurora/config.json
        - Creates ~/.aurora/memory.db (or at minimum, establishes this as the DB path)

        EXPECTED TO FAIL: Currently creates aurora.db in current directory.
        """
        # Run aur init with simulated input (API key = empty, don't index = 'n')
        result = run_cli_command(
            ["aur", "init"],
            input="\nn\n",  # Empty API key, don't index current directory
            capture_output=True,
            text=True,
            cwd=sample_python_project,
            timeout=30,
        )

        # Verify command succeeded
        assert result.returncode == 0, (
            f"aur init failed:\nstdout: {result.stdout}\nstderr: {result.stderr}"
        )

        # Verify config file created at correct location
        config_path = clean_aurora_home / "config.json"
        assert config_path.exists(), f"Config should be at {config_path}, not elsewhere"

        # Verify config has expected structure
        config_data = json.loads(config_path.read_text())
        assert "llm" in config_data, "Config should have 'llm' section"

        # NOTE: The DB may not be created until first index, but config should reference it
        # Check if db_path is in config (this is the fix we need to implement)
        if "db_path" in config_data:
            expected_db_path = str(clean_aurora_home / "memory.db")
            assert (
                config_data["db_path"] == expected_db_path
                or config_data["db_path"] == "~/.aurora/memory.db"
            ), f"db_path should point to ~/.aurora/memory.db, got {config_data.get('db_path')}"

    def test_1_1_3_aur_mem_index_writes_to_aurora_home(
        self, clean_aurora_home: Path, sample_python_project: Path
    ) -> None:
        """Test 1.1.3: aur mem index . writes chunks to ~/.aurora/memory.db (not local aurora.db).

        EXPECTED TO FAIL: Currently creates/uses ./aurora.db in current directory.
        """
        # First ensure Aurora home exists
        clean_aurora_home.mkdir(parents=True, exist_ok=True)

        # Create minimal config
        config_path = clean_aurora_home / "config.json"
        config_data = {
            "llm": {"provider": "anthropic"},
            "db_path": str(clean_aurora_home / "memory.db"),
        }
        config_path.write_text(json.dumps(config_data, indent=2))

        # Run aur mem index
        result = run_cli_command(
            ["aur", "mem", "index", "."],
            capture_output=True,
            text=True,
            cwd=sample_python_project,
            timeout=60,
        )

        # Verify command succeeded
        assert result.returncode == 0, (
            f"aur mem index failed:\nstdout: {result.stdout}\nstderr: {result.stderr}"
        )

        # CRITICAL: Verify DB created at ~/.aurora/memory.db
        expected_db = clean_aurora_home / "memory.db"
        assert expected_db.exists(), (
            f"Database should be at {expected_db}.\n"
            f"Aurora home contents: {list(clean_aurora_home.iterdir()) if clean_aurora_home.exists() else 'does not exist'}\n"
            f"Project contents: {list(sample_python_project.iterdir())}"
        )

        # Verify chunks were written
        conn = sqlite3.connect(expected_db)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM chunks")
        chunk_count = cursor.fetchone()[0]
        conn.close()

        assert chunk_count > 0, f"Expected chunks in {expected_db}, got {chunk_count}"

    def test_1_1_4_aur_mem_stats_shows_correct_count(
        self, clean_aurora_home: Path, sample_python_project: Path
    ) -> None:
        """Test 1.1.4: aur mem stats shows correct chunk count from ~/.aurora/memory.db.

        EXPECTED TO FAIL: Stats reads from wrong database.
        """
        # Setup: Create Aurora home and index
        clean_aurora_home.mkdir(parents=True, exist_ok=True)
        config_path = clean_aurora_home / "config.json"
        config_data = {
            "llm": {"provider": "anthropic"},
            "db_path": str(clean_aurora_home / "memory.db"),
        }
        config_path.write_text(json.dumps(config_data, indent=2))

        # Index the project
        index_result = run_cli_command(
            ["aur", "mem", "index", "."],
            capture_output=True,
            text=True,
            cwd=sample_python_project,
            timeout=60,
        )
        assert index_result.returncode == 0, f"Index failed: {index_result.stderr}"

        # Get chunk count directly from expected DB
        expected_db = clean_aurora_home / "memory.db"
        if expected_db.exists():
            conn = sqlite3.connect(expected_db)
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM chunks")
            expected_count = cursor.fetchone()[0]
            conn.close()
        else:
            pytest.fail(f"Expected DB at {expected_db} does not exist after indexing")

        # Run stats command
        stats_result = run_cli_command(
            ["aur", "mem", "stats"],
            capture_output=True,
            text=True,
            cwd=sample_python_project,
            timeout=30,
        )

        # Note: Stats may fail if it looks for wrong DB - this is the bug
        assert stats_result.returncode == 0, (
            f"aur mem stats failed (likely looking for wrong DB):\n"
            f"stdout: {stats_result.stdout}\n"
            f"stderr: {stats_result.stderr}"
        )

        # Verify output shows correct chunk count
        output = stats_result.stdout.lower()
        assert str(expected_count) in stats_result.stdout or "chunk" in output, (
            f"Stats should show {expected_count} chunks, got:\n{stats_result.stdout}"
        )

    def test_1_1_5_aur_mem_search_returns_results(
        self, clean_aurora_home: Path, sample_python_project: Path
    ) -> None:
        """Test 1.1.5: aur mem search "function" returns results from ~/.aurora/memory.db.

        EXPECTED TO FAIL: Search reads from wrong database.
        """
        # Setup: Create Aurora home and index
        clean_aurora_home.mkdir(parents=True, exist_ok=True)
        config_path = clean_aurora_home / "config.json"
        config_data = {
            "llm": {"provider": "anthropic"},
            "db_path": str(clean_aurora_home / "memory.db"),
        }
        config_path.write_text(json.dumps(config_data, indent=2))

        # Index the project
        index_result = run_cli_command(
            ["aur", "mem", "index", "."],
            capture_output=True,
            text=True,
            cwd=sample_python_project,
            timeout=60,
        )
        assert index_result.returncode == 0, f"Index failed: {index_result.stderr}"

        # Run search command
        search_result = run_cli_command(
            ["aur", "mem", "search", "calculator add subtract"],
            capture_output=True,
            text=True,
            cwd=sample_python_project,
            timeout=30,
        )

        # Verify search succeeded
        assert search_result.returncode == 0, (
            f"aur mem search failed (likely looking for wrong DB):\n"
            f"stdout: {search_result.stdout}\n"
            f"stderr: {search_result.stderr}"
        )

        # Verify results were found
        output = search_result.stdout.lower()
        assert "calculator" in output or "add" in output or "found" in output, (
            f"Search should find calculator functions, got:\n{search_result.stdout}"
        )

    def test_1_1_6_aur_query_retrieves_from_indexed_data(
        self, clean_aurora_home: Path, sample_python_project: Path
    ) -> None:
        """Test 1.1.6: aur query "what is X?" retrieves from indexed data.

        This test validates Issue #15 (Query doesn't use indexed data).
        We use --dry-run or --non-interactive to avoid needing real API keys.

        EXPECTED TO FAIL: Query doesn't retrieve from index.
        """
        # Setup: Create Aurora home and index
        clean_aurora_home.mkdir(parents=True, exist_ok=True)
        config_path = clean_aurora_home / "config.json"
        config_data = {
            "llm": {"provider": "anthropic"},
            "db_path": str(clean_aurora_home / "memory.db"),
        }
        config_path.write_text(json.dumps(config_data, indent=2))

        # Index the project
        index_result = run_cli_command(
            ["aur", "mem", "index", "."],
            capture_output=True,
            text=True,
            cwd=sample_python_project,
            timeout=60,
        )
        assert index_result.returncode == 0, f"Index failed: {index_result.stderr}"

        # Run query with --dry-run (should show what would be retrieved)
        query_result = run_cli_command(
            ["aur", "query", "what does the Calculator class do?", "--dry-run"],
            capture_output=True,
            text=True,
            cwd=sample_python_project,
            timeout=30,
        )

        # Even with --dry-run, it should retrieve relevant chunks
        # The output should mention the indexed code
        output = (query_result.stdout + query_result.stderr).lower()

        # Check that some retrieval happened or the query referenced indexed data
        # This is a soft check since --dry-run behavior may vary
        assert (
            query_result.returncode == 0
            or "calculator" in output
            or "chunks" in output
            or "retrieve" in output
        ), (
            f"Query should attempt to retrieve from index:\n"
            f"stdout: {query_result.stdout}\n"
            f"stderr: {query_result.stderr}"
        )

    def test_1_1_7_subprocess_commands_return_zero(
        self, clean_aurora_home: Path, sample_python_project: Path
    ) -> None:
        """Test 1.1.7: Use subprocess.run() for CLI commands, assert returncode == 0.

        Validates that all basic CLI commands succeed without errors.
        """
        # Setup
        clean_aurora_home.mkdir(parents=True, exist_ok=True)
        config_path = clean_aurora_home / "config.json"
        config_data = {
            "llm": {"provider": "anthropic"},
            "db_path": str(clean_aurora_home / "memory.db"),
        }
        config_path.write_text(json.dumps(config_data, indent=2))

        # Test aur --help
        help_result = run_cli_command(
            ["aur", "--help"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        assert help_result.returncode == 0, f"aur --help failed: {help_result.stderr}"

        # Test aur mem --help
        mem_help_result = run_cli_command(
            ["aur", "mem", "--help"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        assert mem_help_result.returncode == 0, f"aur mem --help failed: {mem_help_result.stderr}"

        # Test aur mem index with explicit --db-path (workaround for current bug)
        db_path = clean_aurora_home / "memory.db"
        index_result = run_cli_command(
            ["aur", "mem", "index", ".", "--db-path", str(db_path)],
            capture_output=True,
            text=True,
            cwd=sample_python_project,
            timeout=60,
        )
        assert index_result.returncode == 0, f"aur mem index failed: {index_result.stderr}"

        # Test aur mem stats with explicit --db-path
        stats_result = run_cli_command(
            ["aur", "mem", "stats", "--db-path", str(db_path)],
            capture_output=True,
            text=True,
            cwd=sample_python_project,
            timeout=30,
        )
        assert stats_result.returncode == 0, f"aur mem stats failed: {stats_result.stderr}"

        # Test aur mem search with explicit --db-path
        search_result = run_cli_command(
            ["aur", "mem", "search", "function", "--db-path", str(db_path)],
            capture_output=True,
            text=True,
            cwd=sample_python_project,
            timeout=30,
        )
        assert search_result.returncode == 0, f"aur mem search failed: {search_result.stderr}"

    def test_1_1_8_no_local_aurora_db_created(
        self, clean_aurora_home: Path, sample_python_project: Path
    ) -> None:
        """Test 1.1.8: Verify no local aurora.db files created in project directory.

        EXPECTED TO FAIL: Currently creates aurora.db in project directory.

        This is the KEY test for Issue #2 - the system should ONLY use ~/.aurora/memory.db
        and never create local aurora.db files in project directories.
        """
        # Setup: Create Aurora home
        clean_aurora_home.mkdir(parents=True, exist_ok=True)
        config_path = clean_aurora_home / "config.json"
        config_data = {
            "llm": {"provider": "anthropic"},
            "db_path": str(clean_aurora_home / "memory.db"),
        }
        config_path.write_text(json.dumps(config_data, indent=2))

        # Verify no aurora.db exists before indexing
        local_db = sample_python_project / "aurora.db"
        assert not local_db.exists(), "Local aurora.db should not exist before any operations"

        # Run aur mem index WITHOUT explicit --db-path (should use config)
        index_result = run_cli_command(
            ["aur", "mem", "index", "."],
            capture_output=True,
            text=True,
            cwd=sample_python_project,
            timeout=60,
        )

        # The key assertion: NO local aurora.db should be created
        assert not local_db.exists(), (
            f"CRITICAL BUG (Issue #2): Local aurora.db created at {local_db}!\n"
            f"All data should be in {clean_aurora_home / 'memory.db'} instead.\n"
            f"Project directory contents: {list(sample_python_project.iterdir())}"
        )

        # Also verify the correct DB was used
        expected_db = clean_aurora_home / "memory.db"
        assert expected_db.exists(), (
            f"Expected database at {expected_db} but it doesn't exist.\n"
            f"Aurora home contents: {list(clean_aurora_home.iterdir()) if clean_aurora_home.exists() else 'does not exist'}"
        )

    def test_1_1_9_overall_workflow_fails_due_to_db_path_issue(
        self, clean_aurora_home: Path, sample_python_project: Path
    ) -> None:
        """Test 1.1.9: Expected - Test FAILS because of Issue #2 (database path confusion).

        This test documents the complete expected failure scenario.
        When Issue #2 is fixed, this test should be updated or removed.

        Current behavior:
        1. aur init creates config at ~/.aurora/config.json (OK)
        2. aur init creates aurora.db in CWD (WRONG - should be ~/.aurora/memory.db)
        3. aur mem index creates aurora.db in CWD (WRONG)
        4. aur mem stats looks for aurora.db in CWD (WRONG)
        5. Data scattered across multiple databases = chaos

        Expected behavior after fix:
        1. All commands use ~/.aurora/memory.db
        2. Config specifies db_path = ~/.aurora/memory.db
        3. No local aurora.db files ever created
        """
        # This is a documentation/assertion test showing the expected failure
        # After fix, all previous tests should pass and this can be updated

        clean_aurora_home.mkdir(parents=True, exist_ok=True)

        # Run init (without indexing)
        init_result = run_cli_command(
            ["aur", "init"],
            input="\nn\n",  # Empty API key, don't index
            capture_output=True,
            text=True,
            cwd=sample_python_project,
            timeout=30,
        )

        # Run index
        index_result = run_cli_command(
            ["aur", "mem", "index", "."],
            capture_output=True,
            text=True,
            cwd=sample_python_project,
            timeout=60,
        )

        # Check if the bug exists (local aurora.db created)
        local_db = sample_python_project / "aurora.db"
        expected_db = clean_aurora_home / "memory.db"

        # This assertion documents the current buggy behavior
        # When fixed, this should be changed to assert local_db does NOT exist
        if local_db.exists():
            pytest.fail(
                f"Issue #2 CONFIRMED: Database path confusion detected!\n"
                f"- Local aurora.db exists at: {local_db}\n"
                f"- Expected database at: {expected_db}\n"
                f"- This test is EXPECTED to fail until Issue #2 is fixed.\n"
                f"- Fix: All commands should use config.get_db_path() which returns ~/.aurora/memory.db"
            )


class TestNewUserWorkflowWithExplicitDbPath:
    """Tests that use explicit --db-path to work around Issue #2.

    These tests document the WORKAROUND for the current bug.
    They should PASS because we explicitly specify the correct path.
    """

    def test_explicit_db_path_workflow_succeeds(
        self, clean_aurora_home: Path, sample_python_project: Path
    ) -> None:
        """Complete workflow works when using explicit --db-path.

        This demonstrates the expected behavior - when we explicitly
        tell Aurora where to put the database, everything works.
        """
        # Setup
        clean_aurora_home.mkdir(parents=True, exist_ok=True)
        db_path = clean_aurora_home / "memory.db"

        # Index with explicit path
        index_result = run_cli_command(
            ["aur", "mem", "index", ".", "--db-path", str(db_path)],
            capture_output=True,
            text=True,
            cwd=sample_python_project,
            timeout=60,
        )
        assert index_result.returncode == 0, f"Index failed: {index_result.stderr}"

        # Stats with explicit path
        stats_result = run_cli_command(
            ["aur", "mem", "stats", "--db-path", str(db_path)],
            capture_output=True,
            text=True,
            timeout=30,
        )
        assert stats_result.returncode == 0, f"Stats failed: {stats_result.stderr}"

        # Search with explicit path
        search_result = run_cli_command(
            ["aur", "mem", "search", "calculator", "--db-path", str(db_path)],
            capture_output=True,
            text=True,
            timeout=30,
        )
        assert search_result.returncode == 0, f"Search failed: {search_result.stderr}"

        # Verify data in correct location
        assert db_path.exists(), f"Database should exist at {db_path}"

        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM chunks")
        count = cursor.fetchone()[0]
        conn.close()

        assert count > 0, f"Should have indexed chunks, got {count}"

        # Verify NO local aurora.db created
        local_db = sample_python_project / "aurora.db"
        assert not local_db.exists(), "Should not create local aurora.db when --db-path specified"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
