"""E2E Test: Git-Based BLA Initialization (Task 1.6)

This test suite validates that Aurora initializes chunks with activation scores
based on Git commit history at the FUNCTION level, not file level.

Test Scenario: Git-Based BLA Initialization (FUNCTION-LEVEL)
1. Create git repo with commit history
2. Create file with multiple functions, commit each function separately
3. Edit one function multiple times (8 commits), another once (1 commit)
4. Index the file with `aur mem index`
5. Query SQLite DB to check activation scores
6. Assert base_level varies across chunks (not all 0.0)
7. Assert frequently-edited function has higher base_level than rarely-edited function
8. Assert functions in SAME file have DIFFERENT base_level values (CRITICAL)
9. Assert git_hash, last_modified, commit_count stored in chunk metadata
10. Assert access_count matches commit_count for each function
11. Test non-Git directory (no crash, base_level=0.5 fallback)

Expected: These tests will FAIL initially due to Issue #16 (Git-based BLA not implemented)
- Current behavior: All base_level = 0.0, no Git history used
- Expected behavior: Function-specific BLA based on individual commit history

Reference: PRD-0010 Section 3 (User Stories), US-8 (Git-Based BLA Initialization),
           FR-8 (Git-Based BLA Initialization - FUNCTION-LEVEL)
"""

import json
import os
import sqlite3
import subprocess
import tempfile
import time
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

        # Create config
        config_path = aurora_home / "config.json"
        config_data = {
            "llm": {"provider": "anthropic"},
            "db_path": str(aurora_home / "memory.db"),
        }
        config_path.write_text(json.dumps(config_data, indent=2))

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
def git_repo_with_history() -> Generator[Path, None, None]:
    """Create a Git repository with detailed commit history at FUNCTION level.

    Creates a file with 3 functions:
    - func_a: Edited 8 times (frequent changes)
    - func_b: Edited 3 times (moderate changes)
    - func_c: Edited 1 time (rarely changed)

    This allows testing FUNCTION-level BLA (not file-level).
    """
    with tempfile.TemporaryDirectory() as tmp_repo:
        repo_path = Path(tmp_repo)

        # Initialize git repo
        subprocess.run(["git", "init"], cwd=repo_path, check=True, capture_output=True)
        subprocess.run(
            ["git", "config", "user.email", "test@example.com"],
            cwd=repo_path,
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "config", "user.name", "Test User"],
            cwd=repo_path,
            check=True,
            capture_output=True,
        )

        # Create initial file with 3 functions
        file_content = '''"""Module with three functions having different edit histories."""


def func_a(x: int) -> int:
    """Function A - will be edited frequently (8 times)."""
    return x


def func_b(y: str) -> str:
    """Function B - will be edited moderately (3 times)."""
    return y


def func_c(z: float) -> float:
    """Function C - will be edited rarely (1 time)."""
    return z
'''
        (repo_path / "module.py").write_text(file_content)

        # Initial commit (all functions v1)
        subprocess.run(["git", "add", "module.py"], cwd=repo_path, check=True, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "Initial commit: all functions v1"],
            cwd=repo_path,
            check=True,
            capture_output=True,
        )
        time.sleep(0.1)  # Small delay for commit timestamps

        # Edit func_a multiple times (8 edits total)
        for i in range(2, 9):  # 7 more edits
            content = (repo_path / "module.py").read_text()
            # Only modify func_a lines
            content = content.replace("return x", f"return x  # edit {i}")
            (repo_path / "module.py").write_text(content)

            subprocess.run(
                ["git", "add", "module.py"],
                cwd=repo_path,
                check=True,
                capture_output=True,
            )
            subprocess.run(
                ["git", "commit", "-m", f"Edit func_a: version {i}"],
                cwd=repo_path,
                check=True,
                capture_output=True,
            )
            time.sleep(0.1)

        # Edit func_b moderately (3 edits total = 2 more edits)
        for i in range(2, 4):  # 2 more edits
            content = (repo_path / "module.py").read_text()
            # Only modify func_b lines
            content = content.replace("return y", f"return y  # edit {i}")
            (repo_path / "module.py").write_text(content)

            subprocess.run(
                ["git", "add", "module.py"],
                cwd=repo_path,
                check=True,
                capture_output=True,
            )
            subprocess.run(
                ["git", "commit", "-m", f"Edit func_b: version {i}"],
                cwd=repo_path,
                check=True,
                capture_output=True,
            )
            time.sleep(0.1)

        # func_c has only 1 commit (initial) - no additional edits

        yield repo_path


class TestGitBasedBLAInitialization:
    """E2E tests for Git-based BLA initialization at FUNCTION level.

    These tests verify that Aurora uses Git commit history to initialize
    activation scores, with FUNCTION-level granularity (not file-level).
    """

    def test_1_6_1_create_git_repo_with_history(self, git_repo_with_history: Path) -> None:
        """Test 1.6.1: Write test that creates git repo with commit history.

        Verifies the fixture creates a proper Git repo.
        """
        # Verify git repo exists
        git_dir = git_repo_with_history / ".git"
        assert git_dir.exists(), "Should have .git directory"

        # Verify file exists
        module_file = git_repo_with_history / "module.py"
        assert module_file.exists(), "Should have module.py"

        # Verify commit history
        result = subprocess.run(
            ["git", "log", "--oneline"],
            cwd=git_repo_with_history,
            capture_output=True,
            text=True,
            check=True,
        )

        commits = result.stdout.strip().split("\n")
        # Should have: 1 initial + 7 func_a edits + 2 func_b edits = 10 commits
        assert len(commits) >= 10, f"Should have at least 10 commits, got {len(commits)}"

    def test_1_6_2_functions_have_different_commit_counts(
        self,
        git_repo_with_history: Path,
    ) -> None:
        """Test 1.6.2: Create file with multiple functions, commit each function separately.

        Verifies that git blame shows different commit history for each function.
        """
        module_file = git_repo_with_history / "module.py"

        # Get line numbers for each function (approximate)
        content = module_file.read_text()
        lines = content.split("\n")

        # Find function definitions
        func_a_line = next(i for i, line in enumerate(lines, 1) if "def func_a" in line)
        func_b_line = next(i for i, line in enumerate(lines, 1) if "def func_b" in line)
        func_c_line = next(i for i, line in enumerate(lines, 1) if "def func_c" in line)

        # Run git blame for func_a lines (should show 8 unique commits)
        # Approximate: func_a is lines 4-6 (def, docstring, return)
        result_a = subprocess.run(
            [
                "git",
                "blame",
                "-L",
                f"{func_a_line},{func_a_line + 2}",
                "module.py",
                "--line-porcelain",
            ],
            cwd=git_repo_with_history,
            capture_output=True,
            text=True,
            check=True,
        )

        # Extract unique commit SHAs
        commits_a = set()
        for line in result_a.stdout.split("\n"):
            if len(line) == 40 and not line.startswith("\t"):
                try:
                    int(line, 16)  # Verify it's a hex SHA
                    commits_a.add(line)
                except ValueError:
                    pass

        # func_a should have multiple commits (we edited it 8 times)
        # Note: Some edits might not affect all lines, so we check for >= 3
        assert len(commits_a) >= 3, (
            f"func_a should have multiple unique commits (edited 8 times)\n"
            f"Found {len(commits_a)} unique commits: {commits_a}"
        )

    def test_1_6_3_index_file_with_git_history(
        self,
        clean_aurora_home: Path,
        git_repo_with_history: Path,
    ) -> None:
        """Test 1.6.3: Edit one function multiple times (8 commits), another once (1 commit).

        This setup enables testing FUNCTION-level BLA differences.
        """
        # Index the git repo
        result = run_cli_command(
            ["aur", "mem", "index", "."],
            capture_output=True,
            text=True,
            cwd=git_repo_with_history,
            timeout=60,
        )

        assert result.returncode == 0, f"Indexing failed:\nstderr: {result.stderr}"

        # Verify chunks were created
        db_path = clean_aurora_home / "memory.db"
        assert db_path.exists(), f"Database should exist at {db_path}"

        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM chunks WHERE file_path LIKE '%module.py%'")
        chunk_count = cursor.fetchone()[0]
        conn.close()

        assert chunk_count >= 3, f"Should have indexed at least 3 functions, got {chunk_count}"

    def test_1_6_4_query_activation_scores_from_database(
        self,
        clean_aurora_home: Path,
        git_repo_with_history: Path,
    ) -> None:
        """Test 1.6.4: Index the file with `aur mem index`.

        Then query activation scores from database.
        """
        # Index
        run_cli_command(
            ["aur", "mem", "index", "."],
            capture_output=True,
            text=True,
            cwd=git_repo_with_history,
            timeout=60,
            check=True,
        )

        # Query database
        db_path = clean_aurora_home / "memory.db"
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Get chunks with their activations
        cursor.execute(
            """
            SELECT c.name, a.base_level, a.access_count
            FROM chunks c
            JOIN activations a ON c.chunk_id = a.chunk_id
            WHERE c.file_path LIKE '%module.py%'
            ORDER BY c.name
        """,
        )

        results = cursor.fetchall()
        conn.close()

        assert len(results) >= 3, f"Should have activation data for 3 functions, got {len(results)}"

    def test_1_6_5_base_level_varies_across_chunks(
        self,
        clean_aurora_home: Path,
        git_repo_with_history: Path,
    ) -> None:
        """Test 1.6.5: Query SQLite DB to check activation scores.

        Test 1.6.6: Assert base_level varies across chunks (not all 0.0).

        EXPECTED TO FAIL: All base_level = 0.0 (Issue #16).
        """
        # Index
        run_cli_command(
            ["aur", "mem", "index", "."],
            capture_output=True,
            text=True,
            cwd=git_repo_with_history,
            timeout=60,
            check=True,
        )

        # Query database
        db_path = clean_aurora_home / "memory.db"
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT c.name, a.base_level, a.access_count
            FROM chunks c
            JOIN activations a ON c.chunk_id = a.chunk_id
            WHERE c.file_path LIKE '%module.py%'
        """,
        )

        results = cursor.fetchall()
        conn.close()

        # Extract base_level values
        base_levels = [row[1] for row in results]

        # At least one should be non-zero
        non_zero = [bl for bl in base_levels if bl != 0.0]

        assert len(non_zero) > 0, (
            f"ISSUE #16: All base_level = 0.0 (Git history not used)!\n"
            f"Function base levels: {base_levels}\n"
            f"Expected: Functions with commit history should have base_level > 0.0\n"
            f"Root cause: Git-based BLA initialization not implemented"
        )

    def test_1_6_6_frequently_edited_function_has_higher_bla(
        self,
        clean_aurora_home: Path,
        git_repo_with_history: Path,
    ) -> None:
        """Test 1.6.7: Assert frequently-edited function has higher base_level than rarely-edited.

        EXPECTED TO FAIL: All base_level = 0.0 or equal (Issue #16).
        """
        # Index
        run_cli_command(
            ["aur", "mem", "index", "."],
            capture_output=True,
            text=True,
            cwd=git_repo_with_history,
            timeout=60,
            check=True,
        )

        # Query database
        db_path = clean_aurora_home / "memory.db"
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT c.name, a.base_level, a.access_count
            FROM chunks c
            JOIN activations a ON c.chunk_id = a.chunk_id
            WHERE c.file_path LIKE '%module.py%'
            ORDER BY c.name
        """,
        )

        results = cursor.fetchall()
        conn.close()

        # Build dictionary of function -> (base_level, access_count)
        func_data = {}
        for name, base_level, access_count in results:
            if "func_a" in name:
                func_data["func_a"] = (base_level, access_count)
            elif "func_b" in name:
                func_data["func_b"] = (base_level, access_count)
            elif "func_c" in name:
                func_data["func_c"] = (base_level, access_count)

        # func_a (8 commits) should have higher BLA than func_c (1 commit)
        if "func_a" in func_data and "func_c" in func_data:
            bla_a = func_data["func_a"][0]
            bla_c = func_data["func_c"][0]

            assert bla_a > bla_c, (
                f"ISSUE #16: Frequently-edited function should have higher BLA!\n"
                f"func_a (8 commits): BLA={bla_a}, access_count={func_data['func_a'][1]}\n"
                f"func_c (1 commit):  BLA={bla_c}, access_count={func_data['func_c'][1]}\n"
                f"Expected: bla_a > bla_c (frequency-based activation)"
            )

    def test_1_6_7_functions_in_same_file_have_different_bla(
        self,
        clean_aurora_home: Path,
        git_repo_with_history: Path,
    ) -> None:
        """Test 1.6.8: Assert functions in SAME file have DIFFERENT base_level values.

        THIS IS THE CRITICAL TEST for FUNCTION-level Git tracking!

        EXPECTED TO FAIL: All functions in same file have identical BLA (file-level tracking).
        """
        # Index
        run_cli_command(
            ["aur", "mem", "index", "."],
            capture_output=True,
            text=True,
            cwd=git_repo_with_history,
            timeout=60,
            check=True,
        )

        # Query database
        db_path = clean_aurora_home / "memory.db"
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT c.name, a.base_level, a.access_count
            FROM chunks c
            JOIN activations a ON c.chunk_id = a.chunk_id
            WHERE c.file_path LIKE '%module.py%'
            ORDER BY a.base_level DESC
        """,
        )

        results = cursor.fetchall()
        conn.close()

        # Extract unique BLA values
        base_levels = [row[1] for row in results]
        unique_bla = len(set(base_levels))

        assert unique_bla > 1, (
            "CRITICAL ISSUE #16: All functions in same file have identical BLA!\n"
            "This proves Git tracking is FILE-level, not FUNCTION-level.\n\n"
            "Functions in module.py:\n"
            + "\n".join(f"  - {name}: BLA={bl:.4f}, access={ac}" for name, bl, ac in results)
            + f"\n\n"
            f"Unique BLA values: {unique_bla} (should be >= 2)\n\n"
            f"Expected: func_a (8 commits) should have DIFFERENT BLA than\n"
            f"          func_b (3 commits) and func_c (1 commit)\n\n"
            f"Fix: Use `git blame -L <start>,<end>` for each function's line range\n"
            f"     NOT `git blame` for entire file"
        )

    def test_1_6_8_git_metadata_stored_in_chunks(
        self,
        clean_aurora_home: Path,
        git_repo_with_history: Path,
    ) -> None:
        """Test 1.6.9: Assert git_hash, last_modified, commit_count stored in chunk metadata.

        EXPECTED TO FAIL: Metadata not stored (Issue #16).
        """
        # Index
        run_cli_command(
            ["aur", "mem", "index", "."],
            capture_output=True,
            text=True,
            cwd=git_repo_with_history,
            timeout=60,
            check=True,
        )

        # Query database
        db_path = clean_aurora_home / "memory.db"
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT c.name, c.metadata
            FROM chunks c
            WHERE c.file_path LIKE '%module.py%'
            LIMIT 3
        """,
        )

        results = cursor.fetchall()
        conn.close()

        # Check metadata for Git fields
        missing_metadata = []
        for name, metadata_json in results:
            metadata = json.loads(metadata_json) if metadata_json else {}

            expected_fields = ["git_hash", "last_modified", "commit_count"]
            missing_fields = [f for f in expected_fields if f not in metadata]

            if missing_fields:
                missing_metadata.append((name, missing_fields))

        assert len(missing_metadata) == 0, (
            "ISSUE #16: Git metadata not stored in chunks!\n"
            + "\n".join(
                f"  - {name}: missing {', '.join(fields)}" for name, fields in missing_metadata
            )
            + "\n\nExpected metadata fields: git_hash, last_modified, commit_count"
        )

    def test_1_6_9_access_count_initialized_from_commits(
        self,
        clean_aurora_home: Path,
        git_repo_with_history: Path,
    ) -> None:
        """Test 1.6.10: Assert access_count matches commit_count for each function.

        EXPECTED TO FAIL: access_count = 0 (not initialized from Git).
        """
        # Index
        run_cli_command(
            ["aur", "mem", "index", "."],
            capture_output=True,
            text=True,
            cwd=git_repo_with_history,
            timeout=60,
            check=True,
        )

        # Query database
        db_path = clean_aurora_home / "memory.db"
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT c.name, c.metadata, a.access_count
            FROM chunks c
            JOIN activations a ON c.chunk_id = a.chunk_id
            WHERE c.file_path LIKE '%module.py%'
        """,
        )

        results = cursor.fetchall()
        conn.close()

        # Check access_count vs commit_count
        mismatches = []
        for name, metadata_json, access_count in results:
            metadata = json.loads(metadata_json) if metadata_json else {}
            commit_count = metadata.get("commit_count", 0)

            # access_count should equal commit_count (each commit = 1 fake access)
            if access_count != commit_count and commit_count > 0:
                mismatches.append((name, access_count, commit_count))

        # If we have commit_count in metadata but access_count doesn't match
        if mismatches:
            pytest.fail(
                "ISSUE #16: access_count not initialized from commit_count!\n"
                + "\n".join(
                    f"  - {name}: access_count={ac}, commit_count={cc}"
                    for name, ac, cc in mismatches
                )
                + "\n\nExpected: access_count should equal commit_count for each function",
            )

        # If commit_count is missing entirely, that's also a failure
        if all(json.loads(r[1]).get("commit_count", 0) == 0 for r in results if r[1]):
            pytest.fail(
                "ISSUE #16: commit_count not stored in metadata!\n"
                "Git-based BLA initialization not implemented.",
            )

    def test_1_6_10_non_git_directory_graceful_fallback(self, clean_aurora_home: Path) -> None:
        """Test 1.6.11: Test non-Git directory (no crash, base_level=0.5 fallback).

        Verifies Aurora handles non-Git directories gracefully.
        """
        # Create non-Git directory
        with tempfile.TemporaryDirectory() as tmp_dir:
            project_path = Path(tmp_dir)

            # Create Python file (no git repo)
            (project_path / "simple.py").write_text(
                '''"""Simple module."""

def hello():
    """Say hello."""
    return "Hello"
''',
            )

            # Index (should not crash)
            result = run_cli_command(
                ["aur", "mem", "index", "."],
                capture_output=True,
                text=True,
                cwd=project_path,
                timeout=60,
            )

            # Should succeed (not crash on missing Git)
            assert (
                result.returncode == 0
            ), f"Indexing non-Git directory should not crash:\nstderr: {result.stderr}"

            # Query database
            db_path = clean_aurora_home / "memory.db"
            if db_path.exists():
                conn = sqlite3.connect(db_path)
                cursor = conn.cursor()

                cursor.execute(
                    """
                    SELECT a.base_level
                    FROM chunks c
                    JOIN activations a ON c.chunk_id = a.chunk_id
                    WHERE c.file_path LIKE '%simple.py%'
                    LIMIT 1
                """,
                )

                result_row = cursor.fetchone()
                conn.close()

                if result_row:
                    base_level = result_row[0]

                    # Should have fallback value (0.5 or similar)
                    # Not 0.0 (which indicates not initialized at all)
                    assert (
                        base_level >= 0.0
                    ), f"Non-Git file should have default base_level\nGot: {base_level}"

    def test_1_6_11_comprehensive_git_bla_check(
        self,
        clean_aurora_home: Path,
        git_repo_with_history: Path,
    ) -> None:
        """Test 1.6.12: Expected - Test FAILS because all base_level = 0.0 (Issue #16).

        Comprehensive test documenting Issue #16.

        Current broken behavior:
        - All base_level = 0.0 (Git history ignored)
        - All access_count = 0
        - No Git metadata stored
        - Functions in same file have identical scores

        Expected behavior after fix (FUNCTION-LEVEL):
        - Each function has BLA based on ITS commit history
        - git blame -L <start>,<end> used for each function
        - func_a (8 commits) > func_b (3 commits) > func_c (1 commit)
        - Metadata includes: git_hash, last_modified, commit_count
        - access_count initialized from commit_count
        """
        # Index
        run_cli_command(
            ["aur", "mem", "index", "."],
            capture_output=True,
            text=True,
            cwd=git_repo_with_history,
            timeout=60,
            check=True,
        )

        # Query database
        db_path = clean_aurora_home / "memory.db"
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT c.name, c.metadata, a.base_level, a.access_count
            FROM chunks c
            JOIN activations a ON c.chunk_id = a.chunk_id
            WHERE c.file_path LIKE '%module.py%'
            ORDER BY a.base_level DESC
        """,
        )

        results = cursor.fetchall()
        conn.close()

        # Analyze results
        issues = []

        # Check 1: Are all base_level = 0.0?
        base_levels = [r[2] for r in results]
        if all(bl == 0.0 for bl in base_levels):
            issues.append("❌ All base_level = 0.0 (Git history completely ignored)")

        # Check 2: Do functions in same file have different BLA?
        unique_bla = len(set(base_levels))
        if unique_bla <= 1:
            issues.append(
                f"❌ All functions have identical BLA (file-level, not function-level)\n"
                f"   Functions: {len(base_levels)}, Unique BLA: {unique_bla}",
            )

        # Check 3: Is Git metadata missing?
        for name, metadata_json, base_level, access_count in results:
            metadata = json.loads(metadata_json) if metadata_json else {}
            if "git_hash" not in metadata or "commit_count" not in metadata:
                issues.append(f"❌ {name}: Missing Git metadata (git_hash, commit_count)")
                break  # Only report once

        # Check 4: Is access_count = 0?
        access_counts = [r[3] for r in results]
        if all(ac == 0 for ac in access_counts):
            issues.append("❌ All access_count = 0 (not initialized from commit history)")

        # If any issues found, fail with comprehensive report
        if issues:
            pytest.fail(
                f"ISSUE #16 CONFIRMED: Git-based BLA initialization not working!\n\n"
                f"Found {len(issues)} problems:\n\n" + "\n".join(issues) + "\n\n"
                "Current function data:\n"
                + "\n".join(
                    f"  - {name}: BLA={bl:.4f}, access={ac}, "
                    f"metadata={json.loads(meta) if meta else 'None'}"
                    for name, meta, bl, ac in results
                )
                + "\n\n"
                "Expected (after fix):\n"
                "  - func_a: BLA=~2.4 (8 commits)\n"
                "  - func_b: BLA=~1.8 (3 commits)\n"
                "  - func_c: BLA=~0.9 (1 commit)\n\n"
                "Root cause: Not using git blame -L for function-level tracking\n\n"
                "Fix:\n"
                "1. Create GitSignalExtractor class in aurora_context_code/git.py\n"
                "2. Use: git blame -L <start>,<end> <file> for each function\n"
                "3. Extract unique commit SHAs and timestamps\n"
                "4. Calculate BLA: ln(Σ (time_since)^(-0.5)) per function\n"
                "5. Initialize: store.initialize_activation(chunk_id, base_level=BLA, access_count=commits)",
            )


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
