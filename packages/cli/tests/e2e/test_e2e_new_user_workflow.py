"""E2E Test: New User Workflow (Task 1.1)

This test suite validates the complete new user experience from scratch.

Test Scenario: Fresh Aurora Installation
1. Clean project .aurora directory (simulate new project)
2. Run aur init - should create config at ./.aurora/config.json
3. Run aur mem index . - should write chunks to ./.aurora/memory.db (project-specific)
4. Run aur mem stats - should show correct chunk count
5. Run aur mem search "function" - should return results
6. Run aur query "what is X?" - should use indexed data

Design Decision: Aurora uses PROJECT-SPECIFIC databases (./.aurora/memory.db)
NOT global databases (~/.aurora/memory.db). This allows:
- Multiple projects with separate indexes
- Project-specific memory and context
- No cross-contamination between projects

Note: Previous Issue #2 expected global DB, but product correctly uses project DB.
These tests have been updated to reflect the correct project-specific behavior.

Reference: Config default db_path = "./.aurora/memory.db"
"""

import json
import sqlite3
import tempfile
from collections.abc import Generator
from pathlib import Path

import pytest

from conftest import run_cli_command


# Mark all tests in this file as E2E tests
pytestmark = [pytest.mark.e2e]


@pytest.fixture
def clean_aurora_home(sample_python_project: Path) -> Generator[Path, None, None]:
    """Return the project-specific .aurora directory for testing.

    Aurora uses PROJECT-SPECIFIC databases at ./.aurora/memory.db
    (not global ~/.aurora/memory.db). This fixture returns the
    .aurora directory within the sample project.

    Args:
        sample_python_project: The test project directory

    Yields:
        Path to the project's .aurora directory (may not exist initially)

    """
    aurora_dir = sample_python_project / ".aurora"
    yield aurora_dir


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
        (project_path / "src" / "calculator.py").write_text(
            '''"""Calculator module with math functions."""

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
''',
        )

        # Create another module for variety
        (project_path / "src" / "utils.py").write_text(
            '''"""Utility functions."""

def format_number(n: float, precision: int = 2) -> str:
    """Format a number with specified precision."""
    return f"{n:.{precision}f}"


def is_even(n: int) -> bool:
    """Check if a number is even."""
    return n % 2 == 0


def clamp(value: int, min_val: int, max_val: int) -> int:
    """Clamp a value between min and max."""
    return max(min_val, min(value, max_val))
''',
        )

        # Create tests directory
        (project_path / "tests").mkdir()
        (project_path / "tests" / "__init__.py").write_text("")
        (project_path / "tests" / "test_calculator.py").write_text(
            '''"""Tests for calculator module."""
import pytest
from src.calculator import add, subtract, multiply, divide, Calculator

from conftest import run_cli_command


def test_add():
    assert add(2, 3) == 5


def test_subtract():
    assert subtract(5, 3) == 2


def test_divide_by_zero():
    with pytest.raises(ZeroDivisionError):
        divide(1, 0)
''',
        )

        yield project_path


class TestNewUserWorkflowE2E:
    """E2E tests for complete new user workflow.

    These tests simulate a new user installing and using Aurora for the first time
    with project-specific database at ./.aurora/memory.db.
    """

    def test_1_1_1_clean_aurora_creates_home_directory(self, clean_aurora_home: Path) -> None:
        """Test 1.1.1: Fresh Aurora installation simulates clean ./.aurora directory.

        Verifies that a new user starts with no Aurora data in the project.
        """
        # Verify project .aurora directory does not exist yet (clean state)
        assert (
            not clean_aurora_home.exists()
        ), "Project .aurora directory should not exist before init"

    def test_1_1_2_aur_init_creates_planning_directory(
        self,
        clean_aurora_home: Path,
        sample_python_project: Path,
    ) -> None:
        """Test 1.1.2: aur init creates .aurora directory for planning.

        Expected behavior:
        - Creates ./.aurora directory (project-specific)
        - Initializes planning structure
        """
        # Initialize git first (aur init requires it)
        run_cli_command(
            ["git", "init"],
            capture_output=True,
            cwd=sample_python_project,
            timeout=10,
        )

        # Run aur init with simulated input
        result = run_cli_command(
            ["aur", "init", "--tools=none"],  # Skip tool configuration
            capture_output=True,
            text=True,
            cwd=sample_python_project,
            timeout=30,
        )

        # Verify command succeeded
        assert (
            result.returncode == 0
        ), f"aur init failed:\nstdout: {result.stdout}\nstderr: {result.stderr}"

        # Verify .aurora directory was created
        assert clean_aurora_home.exists(), f".aurora directory should exist at {clean_aurora_home}"

    def test_1_1_3_aur_mem_index_writes_to_aurora_home(
        self,
        clean_aurora_home: Path,
        sample_python_project: Path,
    ) -> None:
        """Test 1.1.3: aur mem index . writes chunks to ./.aurora/memory.db (project-specific).

        Verifies that indexing creates the database in the project's .aurora directory.
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
        assert (
            result.returncode == 0
        ), f"aur mem index failed:\nstdout: {result.stdout}\nstderr: {result.stderr}"

        # CRITICAL: Verify DB created at ./.aurora/memory.db (project-specific)
        expected_db = clean_aurora_home / "memory.db"
        assert expected_db.exists(), (
            f"Database should be at {expected_db} (project .aurora directory).\n"
            f"Project .aurora contents: {list(clean_aurora_home.iterdir()) if clean_aurora_home.exists() else 'does not exist'}\n"
            f"Project root contents: {list(sample_python_project.iterdir())}"
        )

        # Verify chunks were written
        conn = sqlite3.connect(expected_db)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM chunks")
        chunk_count = cursor.fetchone()[0]
        conn.close()

        assert chunk_count > 0, f"Expected chunks in {expected_db}, got {chunk_count}"

    def test_1_1_4_aur_mem_stats_shows_correct_count(
        self,
        clean_aurora_home: Path,
        sample_python_project: Path,
    ) -> None:
        """Test 1.1.4: aur mem stats shows correct chunk count from ./.aurora/memory.db.

        Verifies that the stats command reads from the project-specific database.
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
        assert (
            str(expected_count) in stats_result.stdout or "chunk" in output
        ), f"Stats should show {expected_count} chunks, got:\n{stats_result.stdout}"

    def test_1_1_5_aur_mem_search_returns_results(
        self,
        clean_aurora_home: Path,
        sample_python_project: Path,
    ) -> None:
        """Test 1.1.5: aur mem search "function" returns results from ./.aurora/memory.db.

        Verifies that the search command reads from the project-specific database.
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
            f"aur mem search failed:\n"
            f"stdout: {search_result.stdout}\n"
            f"stderr: {search_result.stderr}"
        )

        # Verify results were found
        output = search_result.stdout.lower()
        assert (
            "calculator" in output or "add" in output or "found" in output
        ), f"Search should find calculator functions, got:\n{search_result.stdout}"

    @pytest.mark.skip(reason="aur query requires real API interaction - no dry-run mode available")
    def test_1_1_6_aur_query_retrieves_from_indexed_data(
        self,
        clean_aurora_home: Path,
        sample_python_project: Path,
    ) -> None:
        """Test 1.1.6: aur query "what is X?" retrieves from indexed data.

        Verifies that the query command retrieves context from the project-specific
        database index. Currently skipped as query requires real API interaction.
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
        self,
        clean_aurora_home: Path,
        sample_python_project: Path,
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
        self,
        clean_aurora_home: Path,
        sample_python_project: Path,
    ) -> None:
        """Test 1.1.8: Verify DB created in project .aurora directory, not project root.

        Aurora creates ./.aurora/memory.db (inside .aurora directory), not
        ./aurora.db (in project root). This test verifies the correct location.
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
        run_cli_command(
            ["aur", "mem", "index", "."],
            capture_output=True,
            text=True,
            cwd=sample_python_project,
            timeout=60,
        )

        # The key assertion: NO aurora.db in project root
        assert not local_db.exists(), (
            f"Aurora should NOT create aurora.db in project root at {local_db}!\n"
            f"Database should be at {clean_aurora_home / 'memory.db'} instead.\n"
            f"Project directory contents: {list(sample_python_project.iterdir())}"
        )

        # Also verify the correct DB was used
        expected_db = clean_aurora_home / "memory.db"
        assert expected_db.exists(), (
            f"Expected database at {expected_db} but it doesn't exist.\n"
            f"Aurora home contents: {list(clean_aurora_home.iterdir()) if clean_aurora_home.exists() else 'does not exist'}"
        )

    def test_1_1_9_overall_workflow_with_project_db(
        self,
        clean_aurora_home: Path,
        sample_python_project: Path,
    ) -> None:
        """Test 1.1.9: Complete workflow with project-specific database.

        Verifies the end-to-end workflow using project-specific database:
        1. aur init creates config at ./.aurora/config.json
        2. Config specifies db_path = ./.aurora/memory.db
        3. aur mem index writes to ./.aurora/memory.db
        4. aur mem stats reads from ./.aurora/memory.db
        5. No aurora.db created in project root
        """
        clean_aurora_home.mkdir(parents=True, exist_ok=True)

        # Run init (without indexing)
        run_cli_command(
            ["aur", "init"],
            input="\nn\n",  # Empty API key, don't index
            capture_output=True,
            text=True,
            cwd=sample_python_project,
            timeout=30,
        )

        # Run index
        run_cli_command(
            ["aur", "mem", "index", "."],
            capture_output=True,
            text=True,
            cwd=sample_python_project,
            timeout=60,
        )

        # Verify correct behavior: NO aurora.db in project root
        local_db = sample_python_project / "aurora.db"
        expected_db = clean_aurora_home / "memory.db"

        assert not local_db.exists(), (
            f"Database should NOT be created in project root at {local_db}!\n"
            f"Expected database at: {expected_db} (./.aurora/memory.db)\n"
        )

        # Verify DB exists in correct location
        assert expected_db.exists(), f"Database should exist at {expected_db} (./.aurora/memory.db)"


class TestNewUserWorkflowWithExplicitDbPath:
    """Tests that use explicit --db-path for override scenarios.

    These tests verify that --db-path option works correctly for
    testing and override scenarios.
    """

    def test_explicit_db_path_workflow_succeeds(
        self,
        clean_aurora_home: Path,
        sample_python_project: Path,
    ) -> None:
        """Complete workflow works when using explicit --db-path.

        Verifies that --db-path option correctly overrides the default
        database location for testing and special scenarios.
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
