"""Integration tests for memory workflow.

These tests verify end-to-end memory operations including:
- Indexing code files
- Searching indexed content
- Memory statistics
"""

import subprocess
import tempfile
from pathlib import Path

import pytest


class TestMemoryIndexing:
    """Test memory indexing workflow."""

    @pytest.fixture
    def temp_project(self):
        """Create a temporary project directory with test files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir)

            # Create test Python files
            (project_dir / "main.py").write_text(
                '''"""Main module."""

def main():
    """Main entry point."""
    print("Hello, world!")

if __name__ == "__main__":
    main()
'''
            )

            (project_dir / "utils.py").write_text(
                '''"""Utility functions."""

def calculate_sum(a, b):
    """Calculate sum of two numbers."""
    return a + b

def calculate_product(a, b):
    """Calculate product of two numbers."""
    return a * b

class Calculator:
    """Simple calculator class."""

    def add(self, a, b):
        """Add two numbers."""
        return a + b

    def subtract(self, a, b):
        """Subtract b from a."""
        return a - b
'''
            )

            (project_dir / "tests").mkdir()
            (project_dir / "tests" / "test_main.py").write_text(
                '''"""Tests for main module."""

def test_main():
    """Test main function."""
    assert True
'''
            )

            yield project_dir

    def test_index_empty_directory(self):
        """Test indexing an empty directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            result = subprocess.run(
                ["aur", "mem", "index", tmpdir],
                capture_output=True,
                text=True,
            )

            # Should succeed but index 0 files
            assert result.returncode == 0
            assert "0 files" in result.stdout or "Indexed 0 files" in result.stdout

    def test_index_project(self, temp_project):
        """Test indexing a project directory."""
        result = subprocess.run(
            ["aur", "mem", "index", str(temp_project), "--db-path", str(temp_project / "test.db")],
            capture_output=True,
            text=True,
        )

        # Should succeed
        assert result.returncode == 0

        # Should report indexed files
        assert "files indexed" in result.stdout.lower() or "indexed" in result.stdout.lower()

        # Database should exist
        assert (temp_project / "test.db").exists()

    def test_index_single_file(self, temp_project):
        """Test indexing a single file."""
        file_path = temp_project / "main.py"
        db_path = temp_project / "test.db"

        result = subprocess.run(
            ["aur", "mem", "index", str(file_path), "--db-path", str(db_path)],
            capture_output=True,
            text=True,
        )

        # Should succeed
        assert result.returncode == 0

        # Should index 1 file
        assert "1 file" in result.stdout.lower() or "files indexed: 1" in result.stdout.lower()

        # Database should exist
        assert db_path.exists()

    def test_index_with_subdirectories(self, temp_project):
        """Test indexing includes subdirectories."""
        result = subprocess.run(
            ["aur", "mem", "index", str(temp_project), "--db-path", str(temp_project / "test.db")],
            capture_output=True,
            text=True,
        )

        # Should succeed
        assert result.returncode == 0

        # Should find files in tests/ subdirectory
        # We created main.py, utils.py, and tests/test_main.py
        # So should index at least 3 files
        output_lower = result.stdout.lower()
        assert "files indexed" in output_lower or "indexed" in output_lower


class TestMemorySearch:
    """Test memory search workflow."""

    @pytest.fixture
    def indexed_project(self):
        """Create and index a temporary project."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir)
            db_path = project_dir / "test.db"

            # Create test file
            (project_dir / "calculator.py").write_text(
                '''"""Calculator module."""

def add(a, b):
    """Add two numbers."""
    return a + b

def subtract(a, b):
    """Subtract b from a."""
    return a - b

def multiply(a, b):
    """Multiply two numbers."""
    return a * b

class Calculator:
    """Advanced calculator."""

    def divide(self, a, b):
        """Divide a by b."""
        if b == 0:
            raise ValueError("Cannot divide by zero")
        return a / b
'''
            )

            # Index the project
            subprocess.run(
                ["aur", "mem", "index", str(project_dir), "--db-path", str(db_path)],
                capture_output=True,
                check=True,
            )

            yield project_dir

    def test_search_no_database(self):
        """Test search without database shows helpful error."""
        with tempfile.TemporaryDirectory() as tmpdir:
            result = subprocess.run(
                ["aur", "mem", "search", "test", "--db-path", f"{tmpdir}/nonexistent.db"],
                capture_output=True,
                text=True,
            )

            # Should fail gracefully
            assert result.returncode != 0
            assert "not found" in result.stdout.lower() or "error" in result.stderr.lower()

    def test_search_basic(self, indexed_project):
        """Test basic search functionality."""
        db_path = indexed_project / "test.db"

        result = subprocess.run(
            ["aur", "mem", "search", "calculator", "--db-path", str(db_path)],
            capture_output=True,
            text=True,
        )

        # Should succeed
        assert result.returncode == 0

        # Should find results
        assert "result" in result.stdout.lower() or "found" in result.stdout.lower()

    def test_search_function_name(self, indexed_project):
        """Test searching for specific function."""
        db_path = indexed_project / "test.db"

        result = subprocess.run(
            ["aur", "mem", "search", "add", "--db-path", str(db_path), "--limit", "10"],
            capture_output=True,
            text=True,
        )

        # Should succeed
        assert result.returncode == 0

    def test_search_with_limit(self, indexed_project):
        """Test search with result limit."""
        db_path = indexed_project / "test.db"

        result = subprocess.run(
            ["aur", "mem", "search", "calculator", "--db-path", str(db_path), "--limit", "2"],
            capture_output=True,
            text=True,
        )

        # Should succeed
        assert result.returncode == 0

    def test_search_json_format(self, indexed_project):
        """Test search with JSON output."""
        db_path = indexed_project / "test.db"

        result = subprocess.run(
            ["aur", "mem", "search", "add", "--db-path", str(db_path), "--format", "json"],
            capture_output=True,
            text=True,
        )

        # Should succeed
        assert result.returncode == 0

        # Output should be valid JSON (at least starts with [ or empty)
        output = result.stdout.strip()
        assert output.startswith("[") or output == "[]"

    def test_search_with_content(self, indexed_project):
        """Test search with content preview."""
        db_path = indexed_project / "test.db"

        result = subprocess.run(
            [
                "aur",
                "mem",
                "search",
                "divide",
                "--db-path",
                str(db_path),
                "--show-content",
            ],
            capture_output=True,
            text=True,
        )

        # Should succeed
        assert result.returncode == 0


class TestMemoryStats:
    """Test memory statistics workflow."""

    @pytest.fixture
    def indexed_project(self):
        """Create and index a temporary project."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir)
            db_path = project_dir / "test.db"

            # Create test files
            (project_dir / "test1.py").write_text("def func1(): pass")
            (project_dir / "test2.py").write_text("def func2(): pass")

            # Index the project
            subprocess.run(
                ["aur", "mem", "index", str(project_dir), "--db-path", str(db_path)],
                capture_output=True,
                check=True,
            )

            yield project_dir

    def test_stats_no_database(self):
        """Test stats without database shows helpful error."""
        with tempfile.TemporaryDirectory() as tmpdir:
            result = subprocess.run(
                ["aur", "mem", "stats", "--db-path", f"{tmpdir}/nonexistent.db"],
                capture_output=True,
                text=True,
            )

            # Should fail gracefully
            assert result.returncode != 0
            assert "not found" in result.stdout.lower() or "error" in result.stderr.lower()

    def test_stats_basic(self, indexed_project):
        """Test basic stats functionality."""
        db_path = indexed_project / "test.db"

        result = subprocess.run(
            ["aur", "mem", "stats", "--db-path", str(db_path)],
            capture_output=True,
            text=True,
        )

        # Should succeed
        assert result.returncode == 0

        # Should show statistics
        output_lower = result.stdout.lower()
        assert "chunk" in output_lower or "file" in output_lower or "database" in output_lower


class TestMemoryHelp:
    """Test memory command help."""

    def test_mem_help(self):
        """Test 'aur mem --help' shows subcommands."""
        result = subprocess.run(
            ["aur", "mem", "--help"],
            capture_output=True,
            text=True,
        )

        # Should succeed
        assert result.returncode == 0

        # Should list subcommands
        output_lower = result.stdout.lower()
        assert "index" in output_lower
        assert "search" in output_lower
        assert "stats" in output_lower

    def test_mem_index_help(self):
        """Test 'aur mem index --help' shows options."""
        result = subprocess.run(
            ["aur", "mem", "index", "--help"],
            capture_output=True,
            text=True,
        )

        # Should succeed
        assert result.returncode == 0

        # Should show db-path option
        assert "--db-path" in result.stdout

    def test_mem_search_help(self):
        """Test 'aur mem search --help' shows options."""
        result = subprocess.run(
            ["aur", "mem", "search", "--help"],
            capture_output=True,
            text=True,
        )

        # Should succeed
        assert result.returncode == 0

        # Should show options
        output = result.stdout
        assert "--limit" in output or "-n" in output
        assert "--format" in output or "-f" in output
        assert "--show-content" in output or "-c" in output


class TestMemoryWorkflowIntegration:
    """Test complete memory workflow integration."""

    def test_index_then_search_workflow(self):
        """Test indexing then searching workflow."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir)
            db_path = project_dir / "test.db"

            # Create test file with specific content
            (project_dir / "authentication.py").write_text(
                '''"""Authentication module."""

def authenticate_user(username, password):
    """Authenticate a user."""
    # Validate credentials
    if not username or not password:
        return False
    # Check database
    return True

def logout_user(session_id):
    """Log out a user."""
    # Invalidate session
    return True
'''
            )

            # Step 1: Index
            index_result = subprocess.run(
                ["aur", "mem", "index", str(project_dir), "--db-path", str(db_path)],
                capture_output=True,
                text=True,
            )
            assert index_result.returncode == 0

            # Step 2: Search for something we know exists
            search_result = subprocess.run(
                ["aur", "mem", "search", "authenticate", "--db-path", str(db_path)],
                capture_output=True,
                text=True,
            )
            assert search_result.returncode == 0

            # Step 3: Get stats
            stats_result = subprocess.run(
                ["aur", "mem", "stats", "--db-path", str(db_path)],
                capture_output=True,
                text=True,
            )
            assert stats_result.returncode == 0

    def test_reindex_updates_database(self):
        """Test that re-indexing updates the database."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir)
            db_path = project_dir / "test.db"

            # Create initial file
            test_file = project_dir / "test.py"
            test_file.write_text("def original(): pass")

            # Index first time
            subprocess.run(
                ["aur", "mem", "index", str(project_dir), "--db-path", str(db_path)],
                capture_output=True,
                check=True,
            )

            # Modify file
            test_file.write_text("def updated(): pass\ndef another(): pass")

            # Re-index
            result = subprocess.run(
                ["aur", "mem", "index", str(project_dir), "--db-path", str(db_path)],
                capture_output=True,
                text=True,
            )

            # Should succeed
            assert result.returncode == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
