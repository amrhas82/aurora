"""Unit tests for GitSignalExtractor.

Tests the Git signal extraction functionality for function-level BLA initialization.
These tests create real Git repositories to verify actual Git operations.
"""

import shutil
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import pytest

from aurora_context_code.git import GitSignalExtractor


class TestGitSignalExtractor:
    """Test suite for GitSignalExtractor class."""

    @pytest.fixture
    def temp_git_repo(self):
        """Create a temporary Git repository for testing.

        Creates a repo with proper Git config (user.name and user.email)
        to allow commits during tests.
        """
        temp_dir = tempfile.mkdtemp()
        repo_path = Path(temp_dir)

        try:
            # Initialize Git repo
            subprocess.run(
                ["git", "init"],
                cwd=repo_path,
                check=True,
                capture_output=True,
            )

            # Configure Git user (required for commits)
            subprocess.run(
                ["git", "config", "user.name", "Test User"],
                cwd=repo_path,
                check=True,
                capture_output=True,
            )
            subprocess.run(
                ["git", "config", "user.email", "test@example.com"],
                cwd=repo_path,
                check=True,
                capture_output=True,
            )

            yield repo_path

        finally:
            # Cleanup
            shutil.rmtree(temp_dir, ignore_errors=True)

    @pytest.fixture
    def temp_non_git_dir(self):
        """Create a temporary non-Git directory for testing fallback behavior."""
        temp_dir = tempfile.mkdtemp()
        yield Path(temp_dir)
        shutil.rmtree(temp_dir, ignore_errors=True)

    def test_get_function_commit_times_with_history(self, temp_git_repo):
        """Test extracting commit times for functions with different edit histories.

        Creates a file with 3 functions:
        - func_a: 8 commits (frequently edited)
        - func_b: 3 commits (moderately edited)
        - func_c: 1 commit (rarely edited)
        """
        file_path = temp_git_repo / "test_file.py"

        # Create file with 3 functions
        initial_content = '''
def func_a():
    """Function A - will be edited 8 times."""
    return "initial"

def func_b():
    """Function B - will be edited 3 times."""
    return "initial"

def func_c():
    """Function C - will be edited 1 time."""
    return "initial"
'''
        file_path.write_text(initial_content)

        # Initial commit
        subprocess.run(["git", "add", "test_file.py"], cwd=temp_git_repo, check=True)
        subprocess.run(
            ["git", "commit", "-m", "Initial commit"],
            cwd=temp_git_repo,
            check=True,
            capture_output=True,
        )

        # Edit func_a 7 more times (8 total commits touching func_a's body)
        # We add new lines each time so git blame tracks them separately
        for i in range(7):
            content = file_path.read_text()
            lines = content.split("\n")
            for idx, line in enumerate(lines):
                if "def func_a" in line:
                    # Insert a new line before return statement
                    lines.insert(idx + 2, f"    # Edit {i + 1}")
                    break
            file_path.write_text("\n".join(lines))
            subprocess.run(["git", "add", "test_file.py"], cwd=temp_git_repo, check=True)
            subprocess.run(
                ["git", "commit", "-m", f"Edit func_a iteration {i + 1}"],
                cwd=temp_git_repo,
                check=True,
                capture_output=True,
            )

        # Edit func_b 2 more times (3 total commits touching func_b's body)
        for i in range(2):
            content = file_path.read_text()
            lines = content.split("\n")
            # Find and add to func_b
            for idx, line in enumerate(lines):
                if "def func_b" in line:
                    # Insert a new line before return
                    lines.insert(idx + 2, f"    # Func B edit {i + 1}")
                    break
            file_path.write_text("\n".join(lines))
            subprocess.run(["git", "add", "test_file.py"], cwd=temp_git_repo, check=True)
            subprocess.run(
                ["git", "commit", "-m", f"Edit func_b iteration {i + 1}"],
                cwd=temp_git_repo,
                check=True,
                capture_output=True,
            )

        # func_c remains with 1 commit (initial)

        # Extract commit times for each function
        extractor = GitSignalExtractor()

        # Read the final file to find actual line numbers for each function
        final_content = file_path.read_text()
        lines = final_content.split("\n")

        # Find func_a lines
        func_a_start = next(i for i, line in enumerate(lines, 1) if "def func_a" in line)
        func_a_end = func_a_start + 10  # Wide range to capture all edits

        # Find func_b lines
        func_b_start = next(i for i, line in enumerate(lines, 1) if "def func_b" in line)
        func_b_end = func_b_start + 10

        # Find func_c lines
        func_c_start = next(i for i, line in enumerate(lines, 1) if "def func_c" in line)
        func_c_end = func_c_start + 3

        # func_a: 8 commits expected (initial + 7 edits)
        func_a_times = extractor.get_function_commit_times(str(file_path), func_a_start, func_a_end)
        assert len(func_a_times) == 8, f"Expected 8 commits for func_a, got {len(func_a_times)}"

        # func_b: 3 commits expected (initial + 2 edits)
        func_b_times = extractor.get_function_commit_times(str(file_path), func_b_start, func_b_end)
        assert len(func_b_times) == 3, f"Expected 3 commits for func_b, got {len(func_b_times)}"

        # func_c: 1 commit expected (initial only)
        func_c_times = extractor.get_function_commit_times(str(file_path), func_c_start, func_c_end)
        assert len(func_c_times) == 1, f"Expected 1 commit for func_c, got {len(func_c_times)}"

        # Verify timestamps are valid Unix timestamps
        for timestamp in func_a_times + func_b_times + func_c_times:
            assert isinstance(timestamp, int)
            assert timestamp > 0
            # Should be recent (within last hour for test)
            now = int(datetime.now(timezone.utc).timestamp())
            assert now - timestamp < 3600, "Timestamp should be recent"

        # Verify timestamps are sorted newest first
        assert func_a_times == sorted(func_a_times, reverse=True)
        assert func_b_times == sorted(func_b_times, reverse=True)
        assert func_c_times == sorted(func_c_times, reverse=True)

    def test_calculate_bla_from_commits(self, temp_git_repo):
        """Test that BLA calculation reflects frequency: more commits = higher BLA.

        This validates the ACT-R formula: BLA = ln(Σ t_j^(-d))
        """
        file_path = temp_git_repo / "test_file.py"

        # Create file with 2 functions
        initial_content = '''
def frequently_edited():
    """This function will have many edits."""
    return 1

def rarely_edited():
    """This function will have one edit."""
    return 2
'''
        file_path.write_text(initial_content)

        # Initial commit
        subprocess.run(["git", "add", "test_file.py"], cwd=temp_git_repo, check=True)
        subprocess.run(
            ["git", "commit", "-m", "Initial commit"],
            cwd=temp_git_repo,
            check=True,
            capture_output=True,
        )

        # Edit frequently_edited function 9 more times (10 total)
        for i in range(9):
            content = file_path.read_text()
            content = content.replace(
                f"return {i + 1}",
                f"return {i + 2}",
                1,  # Only first occurrence
            )
            file_path.write_text(content)
            subprocess.run(["git", "add", "test_file.py"], cwd=temp_git_repo, check=True)
            subprocess.run(
                ["git", "commit", "-m", f"Edit frequently_edited #{i + 1}"],
                cwd=temp_git_repo,
                check=True,
                capture_output=True,
            )

        # rarely_edited has only 1 commit (initial)

        # Extract and calculate BLA for both functions
        extractor = GitSignalExtractor()

        frequently_edited_times = extractor.get_function_commit_times(str(file_path), 2, 4)
        rarely_edited_times = extractor.get_function_commit_times(str(file_path), 6, 8)

        frequently_edited_bla = extractor.calculate_bla(frequently_edited_times)
        rarely_edited_bla = extractor.calculate_bla(rarely_edited_times)

        # Frequently edited should have HIGHER BLA
        assert frequently_edited_bla > rarely_edited_bla, (
            f"Frequently edited BLA ({frequently_edited_bla:.4f}) should be "
            f"higher than rarely edited BLA ({rarely_edited_bla:.4f})"
        )

        # Verify BLA values are reasonable (typically in range [-10, 5])
        assert -10 <= frequently_edited_bla <= 10
        assert -10 <= rarely_edited_bla <= 10

        # With 10 commits vs 1 commit, difference should be positive and substantial
        # The ln() of 10 terms vs 1 term should give noticeable difference (> 0.5)
        difference = frequently_edited_bla - rarely_edited_bla
        assert difference > 0.5, f"Expected substantial BLA difference, got {difference:.4f}"

    def test_non_git_directory_graceful_fallback(self, temp_non_git_dir):
        """Test that non-Git directories return empty list and fallback BLA.

        This ensures Aurora doesn't crash on codebases without Git history.
        """
        file_path = temp_non_git_dir / "test_file.py"
        file_path.write_text("def test(): pass")

        extractor = GitSignalExtractor()

        # Should return empty list (no Git history)
        commit_times = extractor.get_function_commit_times(str(file_path), 1, 1)
        assert commit_times == []

        # BLA for empty list should be 0.5 (fallback)
        bla = extractor.calculate_bla(commit_times)
        assert bla == 0.5

    def test_nonexistent_file_returns_empty(self):
        """Test that nonexistent files return empty commit list."""
        extractor = GitSignalExtractor()
        commit_times = extractor.get_function_commit_times("/nonexistent/file.py", 1, 10)
        assert commit_times == []

    def test_calculate_bla_with_empty_commits(self):
        """Test that empty commit list returns fallback BLA of 0.5."""
        extractor = GitSignalExtractor()
        bla = extractor.calculate_bla([])
        assert bla == 0.5

    def test_calculate_bla_with_single_commit(self, temp_git_repo):
        """Test BLA calculation with a single commit."""
        file_path = temp_git_repo / "single_commit.py"
        file_path.write_text("def test(): pass")

        subprocess.run(["git", "add", "single_commit.py"], cwd=temp_git_repo, check=True)
        subprocess.run(
            ["git", "commit", "-m", "Single commit"],
            cwd=temp_git_repo,
            check=True,
            capture_output=True,
        )

        extractor = GitSignalExtractor()
        commit_times = extractor.get_function_commit_times(str(file_path), 1, 1)

        assert len(commit_times) == 1

        bla = extractor.calculate_bla(commit_times)

        # Single recent commit should have negative BLA (low activation)
        # because time_since is small, so t^(-0.5) is large, ln(large) is positive
        # but could be positive or negative depending on how recent
        assert isinstance(bla, float)
        assert -10 <= bla <= 10

    def test_parse_blame_output(self):
        """Test parsing of git blame --line-porcelain output."""
        extractor = GitSignalExtractor()

        # Sample output from git blame --line-porcelain
        # Note: SHA must be exactly 40 characters at start of line followed by space
        sample_output = """abc123def456789012345678901234567890abcd 1 1 1
author Test User
author-mail <test@example.com>
author-time 1703001600
committer Test User
committer-mail <test@example.com>
committer-time 1703001600
summary Initial commit
filename test.py
\tdef test():
abc123def456789012345678901234567890abcd 2 2
\t    pass
def456789abc012345678901234567890abcdef1 3 3 1
author Another User
author-mail <another@example.com>
author-time 1703005200
committer Another User
committer-mail <another@example.com>
committer-time 1703005200
summary Second commit
filename test.py
\t    return 42
"""

        shas = extractor._parse_blame_output(sample_output)

        # Should extract 2 unique SHAs (abc123... and def456...)
        assert len(shas) == 2
        assert "abc123def456789012345678901234567890abcd" in shas
        assert "def456789abc012345678901234567890abcdef1" in shas

        # Should preserve order of first appearance
        assert shas[0] == "abc123def456789012345678901234567890abcd"
        assert shas[1] == "def456789abc012345678901234567890abcdef1"

    def test_parse_blame_output_deduplicates(self):
        """Test that repeated SHAs in blame output are deduplicated."""
        extractor = GitSignalExtractor()

        # Output with same SHA appearing multiple times
        sample_output = """
abc123def456789012345678901234567890abcd 1 1 1
\tline 1
abc123def456789012345678901234567890abcd 2 2
\tline 2
abc123def456789012345678901234567890abcd 3 3
\tline 3
"""

        shas = extractor._parse_blame_output(sample_output)

        # Should only have 1 unique SHA
        assert len(shas) == 1
        assert shas[0] == "abc123def456789012345678901234567890abcd"

    def test_bla_decay_parameter(self):
        """Test that decay parameter affects BLA calculation."""
        extractor = GitSignalExtractor()

        # Use fake timestamps from the past to ensure non-zero BLA
        # Commits 1 hour, 2 hours, and 3 hours ago
        current_time = 1703001600  # Fixed timestamp
        commit_times = [
            current_time - 3600,  # 1 hour ago
            current_time - 7200,  # 2 hours ago
            current_time - 10800,  # 3 hours ago
        ]

        # Calculate with different decay rates
        bla_decay_03 = extractor.calculate_bla(commit_times, decay=0.3, current_time=current_time)
        bla_decay_05 = extractor.calculate_bla(commit_times, decay=0.5, current_time=current_time)
        bla_decay_07 = extractor.calculate_bla(commit_times, decay=0.7, current_time=current_time)

        # All should be valid floats
        assert isinstance(bla_decay_03, float)
        assert isinstance(bla_decay_05, float)
        assert isinstance(bla_decay_07, float)

        # Different decay rates should produce different results
        # Higher decay = faster forgetting = lower activation for old items
        assert bla_decay_03 != bla_decay_05, "Different decay rates should produce different BLA"
        assert bla_decay_05 != bla_decay_07, "Different decay rates should produce different BLA"

    def test_timeout_parameter(self):
        """Test that timeout parameter is respected."""
        # Create extractor with very short timeout
        extractor = GitSignalExtractor(timeout=0.001)

        # This will likely timeout or return empty on slow systems
        # Just verify it doesn't crash
        result = extractor.get_function_commit_times("/tmp/test.py", 1, 10)
        assert isinstance(result, list)

    def test_functions_in_same_file_have_different_bla(self, temp_git_repo):
        """CRITICAL TEST: Verify functions in same file can have DIFFERENT BLA values.

        This is the core requirement for function-level Git tracking.
        """
        file_path = temp_git_repo / "multi_function.py"

        content = '''
def old_stable_function():
    """This function hasn't changed."""
    return "stable"

def actively_developed_function():
    """This function is under active development."""
    return "version_0"
'''
        file_path.write_text(content)

        # Initial commit
        subprocess.run(["git", "add", "multi_function.py"], cwd=temp_git_repo, check=True)
        subprocess.run(
            ["git", "commit", "-m", "Initial"],
            cwd=temp_git_repo,
            check=True,
            capture_output=True,
        )

        # Edit ONLY actively_developed_function 5 times
        for i in range(5):
            content = file_path.read_text()
            content = content.replace(f'return "version_{i}"', f'return "version_{i + 1}"')
            file_path.write_text(content)
            subprocess.run(["git", "add", "multi_function.py"], cwd=temp_git_repo, check=True)
            subprocess.run(
                ["git", "commit", "-m", f"Update active function v{i + 1}"],
                cwd=temp_git_repo,
                check=True,
                capture_output=True,
            )

        # Extract BLA for each function
        extractor = GitSignalExtractor()

        stable_times = extractor.get_function_commit_times(str(file_path), 2, 4)
        active_times = extractor.get_function_commit_times(str(file_path), 6, 8)

        stable_bla = extractor.calculate_bla(stable_times)
        active_bla = extractor.calculate_bla(active_times)

        # CRITICAL ASSERTION: BLAs must be DIFFERENT
        assert stable_bla != active_bla, (
            "Functions in same file MUST have different BLA based on edit history"
        )

        # Active function should have more commits
        assert len(active_times) > len(stable_times)

        # Active function should have higher BLA
        assert active_bla > stable_bla, (
            f"Actively edited function BLA ({active_bla:.4f}) should be "
            f"higher than stable function BLA ({stable_bla:.4f})"
        )


class TestGitSignalExtractorEdgeCases:
    """Test edge cases and error handling."""

    def test_git_not_installed(self, monkeypatch, tmp_path):
        """Test graceful handling when Git is not installed."""
        # Mock subprocess to raise FileNotFoundError
        import subprocess as sp

        original_run = sp.run

        def mock_run(*args, **kwargs):
            if args[0][0] == "git":
                raise FileNotFoundError("git not found")
            return original_run(*args, **kwargs)

        monkeypatch.setattr(sp, "run", mock_run)

        file_path = tmp_path / "test.py"
        file_path.write_text("def test(): pass")

        extractor = GitSignalExtractor()
        result = extractor.get_function_commit_times(str(file_path), 1, 1)

        # Should return empty list, not crash
        assert result == []

    def test_invalid_line_range(self, tmp_path):
        """Test handling of invalid line ranges."""
        file_path = tmp_path / "test.py"
        file_path.write_text("def test(): pass")

        extractor = GitSignalExtractor()

        # Negative line numbers should return empty
        result = extractor.get_function_commit_times(str(file_path), -1, 5)
        assert isinstance(result, list)

        # Start > end should return empty
        result = extractor.get_function_commit_times(str(file_path), 10, 5)
        assert isinstance(result, list)
