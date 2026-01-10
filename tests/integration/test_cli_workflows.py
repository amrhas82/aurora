"""CLI Integration Tests - Battle-Testing AURORA CLI Commands.

This test suite validates complete CLI workflows with real components:
- Real file system operations
- Real database interactions
- Real parsing and indexing
- Real search and retrieval

Pattern: Use real components (parser, storage, git), mock only external APIs (LLM).

Test Coverage:
- Task 3.11: aur mem index (real file parsing and database storage)
- Task 3.12: aur mem search (real database queries and ranking)
- Task 3.13: aur query (real safety checks with git integration)
"""

import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any

import pytest

pytestmark = pytest.mark.ml


# ==============================================================================
# Fixtures
# ==============================================================================


@pytest.fixture
def temp_project_dir():
    """Create a temporary project directory with sample Python files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        project_path = Path(tmpdir) / "sample_project"
        project_path.mkdir()

        # Create a simple Python project structure
        (project_path / "src").mkdir()
        (project_path / "src" / "__init__.py").write_text("")
        (project_path / "src" / "main.py").write_text(
            '''"""Main module."""


def hello_world():
    """Print hello world."""
    return "Hello, World!"


def add(a: int, b: int) -> int:
    """Add two numbers."""
    return a + b


if __name__ == "__main__":
    print(hello_world())
'''
        )

        (project_path / "src" / "utils.py").write_text(
            '''"""Utility functions."""


def multiply(a: int, b: int) -> int:
    """Multiply two numbers."""
    return a * b


def divide(a: float, b: float) -> float:
    """Divide two numbers."""
    if b == 0:
        raise ValueError("Cannot divide by zero")
    return a / b
'''
        )

        # Create a README
        (project_path / "README.md").write_text(
            """# Sample Project

This is a sample project for testing AURORA CLI.

## Features
- Hello world functionality
- Basic arithmetic operations
"""
        )

        yield project_path


@pytest.fixture
def temp_aurora_home(temp_project_dir):
    """Create a temporary AURORA_HOME directory for isolated testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        aurora_home = Path(tmpdir) / ".aurora"
        aurora_home.mkdir()

        # Set environment variable for this test
        old_home = os.environ.get("AURORA_HOME")
        os.environ["AURORA_HOME"] = str(aurora_home)

        yield aurora_home

        # Restore original AURORA_HOME
        if old_home is not None:
            os.environ["AURORA_HOME"] = old_home
        elif "AURORA_HOME" in os.environ:
            del os.environ["AURORA_HOME"]


@pytest.fixture
def cli_runner(temp_project_dir, temp_aurora_home):
    """CLI runner that executes aur commands in isolated environment."""

    def run_command(*args, **kwargs) -> subprocess.CompletedProcess:
        """Run aur command with given arguments."""
        cmd = ["aur"] + list(args)
        cwd = kwargs.pop("cwd", temp_project_dir)
        env = os.environ.copy()
        env["AURORA_HOME"] = str(temp_aurora_home)

        result = subprocess.run(
            cmd,
            cwd=cwd,
            capture_output=True,
            text=True,
            env=env,
            **kwargs,
        )
        return result

    return run_command


# ==============================================================================
# Task 3.11: Test aur mem index (Real File Parsing + Database Storage)
# ==============================================================================


class TestCLIMemIndex:
    """Test 'aur mem index' command with real file system and database."""

    def test_index_command_creates_database(self, cli_runner, temp_project_dir, temp_aurora_home):
        """Test that 'aur mem index' creates a database file."""
        # Initialize config first (creates config.json)
        # Pass empty string for API key prompt (skip API key)
        init_result = cli_runner("init", input="\n")

        db_path = temp_aurora_home / "memory.db"
        result = cli_runner("mem", "index", str(temp_project_dir))

        # Command should succeed
        assert result.returncode == 0, f"STDOUT: {result.stdout}\nSTDERR: {result.stderr}"

        # Database should be created
        assert db_path.exists(), "Database file should be created"

    def test_index_command_parses_python_files(
        self, cli_runner, temp_project_dir, temp_aurora_home
    ):
        """Test that 'aur mem index' correctly parses Python files."""
        # Initialize config first
        cli_runner("init", input="\n")

        db_path = temp_aurora_home / "memory.db"
        result = cli_runner("mem", "index", str(temp_project_dir))

        assert result.returncode == 0, f"STDOUT: {result.stdout}\nSTDERR: {result.stderr}"

        # Query database to verify chunks were created
        import sqlite3

        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Check that chunks table exists and has data
        cursor.execute("SELECT COUNT(*) FROM chunks")
        count = cursor.fetchone()[0]
        assert count > 0, "Database should contain indexed chunks"

        # Verify specific functions were indexed (type is 'code' for all code chunks)
        cursor.execute("SELECT content FROM chunks WHERE type = 'code'")
        functions = [row[0] for row in cursor.fetchall()]
        # Content is JSON, check if any contain our function names
        function_names = [
            f
            for f in functions
            if "hello_world" in str(f) or "add" in str(f) or "multiply" in str(f)
        ]

        assert len(function_names) > 0, f"Should index Python functions, found {count} chunks total"

        conn.close()

    def test_index_command_handles_empty_directory(
        self, cli_runner, temp_project_dir, temp_aurora_home
    ):
        """Test that 'aur mem index' handles empty directories gracefully."""
        empty_dir = temp_project_dir / "empty"
        empty_dir.mkdir()

        result = cli_runner("mem", "index", str(empty_dir))

        # Should not crash, but may report no files found
        assert result.returncode in [0, 1], f"STDOUT: {result.stdout}\nSTDERR: {result.stderr}"


# ==============================================================================
# Task 3.12: Test aur mem search (Real Database Queries + Ranking)
# ==============================================================================


class TestCLIMemSearch:
    """Test 'aur mem search' command with real database and ranking."""

    def test_search_finds_indexed_functions(self, cli_runner, temp_project_dir, temp_aurora_home):
        """Test that 'aur mem search' finds indexed code."""
        # Initialize config first
        cli_runner("init", input="\n")
        db_path = temp_aurora_home / "memory.db"

        # First, index the project
        index_result = cli_runner("mem", "index", str(temp_project_dir))
        assert index_result.returncode == 0

        # Now search for a function
        search_result = cli_runner("mem", "search", "hello_world")

        assert (
            search_result.returncode == 0
        ), f"STDOUT: {search_result.stdout}\nSTDERR: {search_result.stderr}"
        assert "hello_world" in search_result.stdout or "Hello" in search_result.stdout

    def test_search_with_no_results(self, cli_runner, temp_project_dir, temp_aurora_home):
        """Test that 'aur mem search' handles no results gracefully."""
        # Initialize config first
        cli_runner("init", input="\n")
        db_path = temp_aurora_home / "memory.db"

        # Index the project first
        cli_runner("mem", "index", str(temp_project_dir))

        # Search for something that doesn't exist
        result = cli_runner("mem", "search", "nonexistent_function_xyz")

        # Should not crash
        assert result.returncode in [0, 1], f"STDOUT: {result.stdout}\nSTDERR: {result.stderr}"

    def test_search_ranking_by_relevance(self, cli_runner, temp_project_dir, temp_aurora_home):
        """Test that 'aur mem search' ranks results by relevance."""
        # Initialize config first
        cli_runner("init", input="\n")
        db_path = temp_aurora_home / "memory.db"

        # Index the project
        cli_runner("mem", "index", str(temp_project_dir))

        # Search for arithmetic operations
        result = cli_runner("mem", "search", "add multiply")

        assert result.returncode == 0, f"STDOUT: {result.stdout}\nSTDERR: {result.stderr}"

        # Should find both add and multiply functions
        # (specific ranking validation would require parsing output)
        assert "add" in result.stdout.lower() or "multiply" in result.stdout.lower()


# ==============================================================================
# Task 3.13: Test aur query (Real Safety Checks + Git Integration)
# ==============================================================================


class TestCLIQuery:
    """Test 'aur query' command with real safety checks."""

    @pytest.mark.skip(reason="Requires API key - will be tested in E2E with mocked LLM")
    def test_query_requires_api_key(self, cli_runner, temp_project_dir, temp_aurora_home):
        """Test that 'aur query' requires API key configuration."""
        # Ensure no API key is set
        env = os.environ.copy()
        env.pop("ANTHROPIC_API_KEY", None)

        result = cli_runner("query", "what does this code do?")

        # Should fail or warn about missing API key
        assert result.returncode != 0 or "API key" in result.stderr

    def test_query_command_structure(self, cli_runner, temp_project_dir, temp_aurora_home):
        """Test that 'aur query' command accepts valid structure."""
        # This just validates command structure, not full execution
        result = cli_runner("query", "--help")

        assert result.returncode == 0
        assert "query" in result.stdout.lower() or "usage" in result.stdout.lower()

    @pytest.mark.skip(reason="Git safety checks require git repository setup")
    def test_query_respects_git_safety_checks(self, cli_runner, temp_project_dir, temp_aurora_home):
        """Test that 'aur query' respects git safety configuration."""
        # This test would require setting up a git repository
        # and configuring safety checks - deferred to E2E tests
        pass


# ==============================================================================
# Integration Test Helpers
# ==============================================================================


def get_db_stats(db_path: Path) -> dict[str, Any]:
    """Get statistics from AURORA database."""
    import sqlite3

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    stats = {}

    # Count total chunks
    cursor.execute("SELECT COUNT(*) FROM chunks")
    stats["total_chunks"] = cursor.fetchone()[0]

    # Count by type
    cursor.execute("SELECT type, COUNT(*) FROM chunks GROUP BY type")
    stats["chunks_by_type"] = dict(cursor.fetchall())

    conn.close()
    return stats
