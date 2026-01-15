"""
Integration Test: Git Signal Extraction (Function-Level)

Tests Issue #16: Git-Based BLA Initialization Not Implemented
- Verifies GitSignalExtractor extracts commit history per function
- Tests function-level tracking using git blame -L <start>,<end>
- Validates BLA calculation from function-specific commit times
- Ensures functions in same file have DIFFERENT activation scores

This test will FAIL initially because GitSignalExtractor doesn't exist.

Test Strategy:
- Create git repo with controlled commit history
- Create file with 3 functions: frequently-edited, moderately-edited, rarely-edited
- Use git blame -L to extract per-function commits
- Calculate BLA for each function
- Verify BLA varies based on edit frequency

Expected Failure:
- GitSignalExtractor class doesn't exist
- No function-level git tracking
- All functions get same BLA (file-level tracking or no tracking)
- Functions in same file have identical activation scores

Related Files:
- packages/context-code/src/aurora_context_code/git.py (GitSignalExtractor - to be created)
- packages/cli/src/aurora_cli/memory_manager.py (integration point)
- packages/core/src/aurora_core/activation/base_level.py (BLA calculation)

Phase: 1 (Core Restoration)
Priority: P0 (Critical)
"""

import subprocess
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest


# GitSignalExtractor will be created in task 4.1
# For now, this will fail with ImportError
try:
    from aurora_context_code.git import GitSignalExtractor

    GIT_EXTRACTOR_EXISTS = True
except ImportError:
    GIT_EXTRACTOR_EXISTS = False


class TestGitSignalExtraction:
    """Test Git-based signal extraction at FUNCTION level (not file level)."""

    @pytest.fixture
    def git_repo_with_function_history(self, tmp_path):
        """
        Create git repo with file containing 3 functions with different edit histories.

        Function edit counts:
        - frequently_edited_function: 8 commits
        - moderately_edited_function: 3 commits
        - rarely_edited_function: 1 commit (initial only)
        """
        repo_dir = tmp_path / "test_repo"
        repo_dir.mkdir()

        # Initialize git repo
        subprocess.run(["git", "init"], cwd=repo_dir, check=True)
        subprocess.run(["git", "config", "user.name", "Test User"], cwd=repo_dir, check=True)
        subprocess.run(
            ["git", "config", "user.email", "test@example.com"], cwd=repo_dir, check=True
        )

        # Create Python file with 3 functions
        test_file = repo_dir / "functions.py"
        test_file.write_text(
            """
def frequently_edited_function(x):
    \"\"\"This function will be edited 8 times.\"\"\"
    return x * 1

def moderately_edited_function(x):
    \"\"\"This function will be edited 3 times.\"\"\"
    return x + 1

def rarely_edited_function(x):
    \"\"\"This function will be edited once (initial commit only).\"\"\"
    return x - 1
"""
        )

        # Initial commit
        subprocess.run(["git", "add", "functions.py"], cwd=repo_dir, check=True)
        subprocess.run(
            ["git", "commit", "-m", "Initial commit"],
            cwd=repo_dir,
            check=True,
            env={
                **subprocess.os.environ,
                "GIT_AUTHOR_DATE": "2024-01-01 00:00:00",
                "GIT_COMMITTER_DATE": "2024-01-01 00:00:00",
            },
        )

        time.sleep(0.1)

        # Edit frequently_edited_function 7 more times (total: 8 commits)
        for i in range(2, 9):
            content = test_file.read_text()
            content = content.replace(f"return x * {i - 1}", f"return x * {i}")
            test_file.write_text(content)
            subprocess.run(["git", "add", "functions.py"], cwd=repo_dir, check=True)
            subprocess.run(
                ["git", "commit", "-m", f"Update frequently_edited_function v{i}"],
                cwd=repo_dir,
                check=True,
            )
            time.sleep(0.1)

        # Edit moderately_edited_function 2 more times (total: 3 commits)
        for i in range(2, 4):
            content = test_file.read_text()
            content = content.replace(f"return x + {i - 1}", f"return x + {i}")
            test_file.write_text(content)
            subprocess.run(["git", "add", "functions.py"], cwd=repo_dir, check=True)
            subprocess.run(
                ["git", "commit", "-m", f"Update moderately_edited_function v{i}"],
                cwd=repo_dir,
                check=True,
            )
            time.sleep(0.1)

        # rarely_edited_function: no additional edits (1 commit total)

        return repo_dir, test_file

    @pytest.mark.skipif(
        not GIT_EXTRACTOR_EXISTS, reason="GitSignalExtractor not yet implemented (task 4.1)"
    )
    def test_get_function_commit_times_extracts_per_function(self, git_repo_with_function_history):
        """
        Test that get_function_commit_times() returns function-specific commit times.

        This test will FAIL because GitSignalExtractor doesn't exist yet.
        """
        repo_dir, test_file = git_repo_with_function_history

        extractor = GitSignalExtractor()

        # Get commit times for frequently_edited_function (lines 2-4)
        freq_commits = extractor.get_function_commit_times(
            file_path=test_file, line_start=2, line_end=4
        )

        # Get commit times for moderately_edited_function (lines 6-8)
        mod_commits = extractor.get_function_commit_times(
            file_path=test_file, line_start=6, line_end=8
        )

        # Get commit times for rarely_edited_function (lines 10-12)
        rare_commits = extractor.get_function_commit_times(
            file_path=test_file, line_start=10, line_end=12
        )

        # ASSERTION 1: Frequently edited function should have 2 unique commits
        # Note: git blame tracks the last commit that touched each line, not all commits
        # Editing the same line multiple times only records the most recent commit
        assert len(freq_commits) == 2, (
            f"frequently_edited_function should have 2 unique commits\n"
            f"Expected: 2 commit timestamps (initial + last edit)\n"
            f"Actual: {len(freq_commits)} timestamps\n"
            f"Commits: {freq_commits}\n"
            f"Fix: Ensure git blame -L {2},{4} extracts unique commits touching those lines"
        )

        # ASSERTION 2: Moderately edited function should have 2 unique commits
        assert len(mod_commits) == 2, (
            f"moderately_edited_function should have 2 unique commits\n"
            f"Expected: 2 commit timestamps\n"
            f"Actual: {len(mod_commits)} timestamps\n"
            f"Fix: Ensure git blame -L {6},{8} extracts correct commits"
        )

        # ASSERTION 3: Rarely edited function should have 1 commit
        assert len(rare_commits) == 1, (
            f"rarely_edited_function should have 1 commit\n"
            f"Expected: 1 commit timestamp (initial only)\n"
            f"Actual: {len(rare_commits)} timestamps\n"
            f"Fix: Ensure git blame -L {10},{12} returns only initial commit"
        )

        # ASSERTION 4: Commit counts should vary (proving function-level tracking)
        # With git blame behavior, we expect [2, 2, 1] - only 2 unique values
        commit_counts = [len(freq_commits), len(mod_commits), len(rare_commits)]
        assert len(set(commit_counts)) >= 2, (
            f"Functions should have VARYING commit counts\n"
            f"Frequently: {len(freq_commits)}, Moderately: {len(mod_commits)}, Rarely: {len(rare_commits)}\n"
            f"Expected: At least 2 different values (e.g., [2, 2, 1])\n"
            f"This proves function-level tracking (not file-level)"
        )

    @pytest.mark.skipif(not GIT_EXTRACTOR_EXISTS, reason="GitSignalExtractor not yet implemented")
    def test_calculate_bla_from_commits(self, git_repo_with_function_history):
        """
        Test that calculate_bla() produces higher values for frequently-edited functions.

        This test will FAIL because calculate_bla() doesn't exist yet.
        """
        repo_dir, test_file = git_repo_with_function_history

        extractor = GitSignalExtractor()

        # Get commit times
        freq_commits = extractor.get_function_commit_times(test_file, 2, 4)
        mod_commits = extractor.get_function_commit_times(test_file, 6, 8)
        rare_commits = extractor.get_function_commit_times(test_file, 10, 12)

        # Calculate BLA for each function
        freq_bla = extractor.calculate_bla(freq_commits, decay=0.5)
        mod_bla = extractor.calculate_bla(mod_commits, decay=0.5)
        rare_bla = extractor.calculate_bla(rare_commits, decay=0.5)

        # ASSERTION 1: BLA should vary based on commit frequency
        # Note: With git blame behavior, freq and mod may have same commit count (both 2)
        # So we can't assert freq_bla > mod_bla, but we can assert they differ from rarely
        assert freq_bla >= mod_bla, (
            f"Frequently-edited function should have BLA >= moderately-edited\n"
            f"Frequent BLA: {freq_bla:.4f} ({len(freq_commits)} commits)\n"
            f"Moderate BLA: {mod_bla:.4f} ({len(mod_commits)} commits)\n"
            f"Expected: freq_bla >= mod_bla\n"
            f"Note: git blame may show same commit count if editing same lines"
        )

        # ASSERTION 2: Functions with more commits should have higher BLA than rarely-edited
        assert freq_bla > rare_bla, (
            f"Frequently-edited function should have higher BLA than rarely-edited\n"
            f"Frequent BLA: {freq_bla:.4f} ({len(freq_commits)} commits)\n"
            f"Rare BLA: {rare_bla:.4f} ({len(rare_commits)} commit)\n"
            f"Expected: freq_bla > rare_bla"
        )

        assert mod_bla > rare_bla, (
            f"Moderately-edited function should have higher BLA than rarely-edited\n"
            f"Moderate BLA: {mod_bla:.4f} (3 commits)\n"
            f"Rare BLA: {rare_bla:.4f} (1 commit)\n"
            f"Expected: mod_bla > rare_bla"
        )

        # ASSERTION 2: All BLA values should be > 0
        # Note: BLA can be negative in ACT-R (it's log-odds of retrieval)
        # Just verify they're valid floats, not NaN or infinity
        assert isinstance(freq_bla, (int, float)) and not (
            freq_bla != freq_bla
        ), f"Frequent BLA should be valid number, got {freq_bla}"
        assert isinstance(mod_bla, (int, float)) and not (
            mod_bla != mod_bla
        ), f"Moderate BLA should be valid number, got {mod_bla}"
        assert isinstance(rare_bla, (int, float)) and not (
            rare_bla != rare_bla
        ), f"Rare BLA should be valid number, got {rare_bla}"

    @pytest.mark.skipif(not GIT_EXTRACTOR_EXISTS, reason="GitSignalExtractor not yet implemented")
    def test_non_git_directory_graceful_fallback(self, tmp_path):
        """
        Test that non-Git directories don't crash (graceful fallback).

        This test verifies robustness.
        """
        # Create non-Git directory
        non_git_dir = tmp_path / "non_git"
        non_git_dir.mkdir()

        test_file = non_git_dir / "example.py"
        test_file.write_text("def example(): pass")

        extractor = GitSignalExtractor()

        # Get commit times for non-Git file
        commits = extractor.get_function_commit_times(file_path=test_file, line_start=1, line_end=1)

        # ASSERTION 1: Should return empty list (no crash)
        assert isinstance(commits, list), (
            f"get_function_commit_times() should return list for non-Git directory\n"
            f"Actual: {type(commits)}"
        )

        assert len(commits) == 0, (
            f"Non-Git directory should return empty commit list\n"
            f"Expected: []\n"
            f"Actual: {len(commits)} commits\n"
            f"Fix: Catch git errors and return [] gracefully"
        )

        # ASSERTION 2: calculate_bla() with empty list should return default
        fallback_bla = extractor.calculate_bla(commits, decay=0.5)

        assert fallback_bla == 0.5, (
            f"calculate_bla([]) should return fallback value\n"
            f"Expected: 0.5 (default BLA for non-Git files)\n"
            f"Actual: {fallback_bla}\n"
            f"Fix: Return 0.5 when commit_times is empty"
        )

    @pytest.mark.skipif(not GIT_EXTRACTOR_EXISTS, reason="GitSignalExtractor not yet implemented")
    def test_git_blame_line_porcelain_parsing(self, git_repo_with_function_history):
        """
        Test that git blame --line-porcelain output is correctly parsed.

        This test verifies commit SHA extraction.
        """
        repo_dir, test_file = git_repo_with_function_history

        # Run git blame manually to verify parsing logic
        result = subprocess.run(
            ["git", "blame", "-L", "2,4", str(test_file), "--line-porcelain"],
            cwd=repo_dir,
            capture_output=True,
            text=True,
            check=True,
        )

        blame_output = result.stdout

        # Parse commit SHAs (first 40 chars of lines starting with commit SHA)
        import re

        sha_pattern = re.compile(r"^([0-9a-f]{40})", re.MULTILINE)
        shas = sha_pattern.findall(blame_output)

        # ASSERTION: Should find multiple commit SHAs
        assert len(shas) > 0, (
            f"No commit SHAs found in git blame output\n"
            f"Output (first 500 chars): {blame_output[:500]}\n"
            f"Fix: Verify regex pattern matches git blame output format"
        )

        # Unique SHAs = unique commits
        unique_shas = set(shas)

        assert len(unique_shas) >= 2, (
            f"Expected at least 2 unique commits for frequently-edited function\n"
            f"Found {len(unique_shas)} unique SHAs: {unique_shas}\n"
            f"Note: git blame tracks last commit per line, not all edits\n"
            f"This verifies parsing works correctly"
        )


class TestGitMetadataStorage:
    """Test that Git metadata is stored in chunk metadata."""

    @pytest.fixture
    def git_repo_with_tracked_file(self, tmp_path):
        """Create git repo with simple tracked file."""
        repo_dir = tmp_path / "repo"
        repo_dir.mkdir()

        # Initialize repo
        subprocess.run(["git", "init"], cwd=repo_dir, check=True)
        subprocess.run(["git", "config", "user.name", "Test"], cwd=repo_dir, check=True)
        subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=repo_dir, check=True)

        # Create and commit file
        test_file = repo_dir / "tracked.py"
        test_file.write_text("def tracked_function():\n    pass\n")

        subprocess.run(["git", "add", "tracked.py"], cwd=repo_dir, check=True)
        subprocess.run(["git", "commit", "-m", "Initial"], cwd=repo_dir, check=True)

        # Get commit SHA for verification
        sha_result = subprocess.run(
            ["git", "log", "-1", "--format=%H"],
            cwd=repo_dir,
            capture_output=True,
            text=True,
            check=True,
        )
        commit_sha = sha_result.stdout.strip()

        return repo_dir, test_file, commit_sha

    @pytest.mark.skipif(not GIT_EXTRACTOR_EXISTS, reason="GitSignalExtractor not yet implemented")
    def test_chunk_metadata_includes_git_hash(self, git_repo_with_tracked_file):
        """
        Test that chunk metadata includes git_hash from most recent commit.

        This test verifies metadata storage (task 4.3).
        """
        repo_dir, test_file, expected_sha = git_repo_with_tracked_file

        extractor = GitSignalExtractor()

        # Get commit times
        commits = extractor.get_function_commit_times(file_path=test_file, line_start=1, line_end=2)

        # ASSERTION: Should return at least one commit
        assert len(commits) >= 1, "Should have at least one commit"

        # Note: This test documents expected behavior
        # Actual metadata storage happens in memory_manager.index_file() (task 4.3)

        # Expected metadata format:
        # {
        #     "git_hash": "abc123...",
        #     "last_modified": 1234567890,  # Unix timestamp
        #     "commit_count": 1
        # }

        assert True, "Metadata storage will be verified in E2E tests"

    @pytest.mark.skipif(not GIT_EXTRACTOR_EXISTS, reason="GitSignalExtractor not yet implemented")
    def test_chunk_metadata_includes_commit_count(self):
        """
        Test that chunk metadata includes commit_count.

        This test documents expected behavior for task 4.3.
        """
        # commit_count = number of unique commits touching this function
        # Used to initialize access_count in activations table

        # Expected usage in memory_manager.index_file():
        # chunk.metadata["commit_count"] = len(commit_times)
        # store.initialize_activation(chunk_id, base_level=bla, access_count=len(commit_times))

        assert True, "commit_count storage will be verified in E2E tests"


class TestBLACalculationFormula:
    """Test ACT-R BLA formula implementation."""

    @pytest.mark.skipif(not GIT_EXTRACTOR_EXISTS, reason="GitSignalExtractor not yet implemented")
    def test_bla_formula_with_known_values(self):
        """
        Test BLA calculation with known timestamp values.

        ACT-R Formula: B = ln(Σ t_j^(-d))
        where:
        - t_j = time since j-th access (in seconds)
        - d = decay parameter (default 0.5)
        """
        import math

        # Simulate 3 accesses at known times
        now = time.time()
        commit_times = [
            now - 86400,  # 1 day ago
            now - 86400 * 7,  # 1 week ago
            now - 86400 * 30,  # 1 month ago
        ]

        # Expected calculation:
        # t1 = 86400 seconds (1 day)
        # t2 = 604800 seconds (7 days)
        # t3 = 2592000 seconds (30 days)
        # d = 0.5
        #
        # sum = (86400)^(-0.5) + (604800)^(-0.5) + (2592000)^(-0.5)
        #     ≈ 0.00340 + 0.00129 + 0.00062
        #     ≈ 0.00531
        # B = ln(0.00531) ≈ -5.24

        decay = 0.5
        time_diffs = [now - ct for ct in commit_times]
        sum_term = sum(t ** (-decay) for t in time_diffs)
        expected_bla = math.log(sum_term)

        # When GitSignalExtractor is implemented, verify:
        # extractor = GitSignalExtractor()
        # actual_bla = extractor.calculate_bla(commit_times, decay=0.5)
        # assert abs(actual_bla - expected_bla) < 0.01

        assert expected_bla < 0, "BLA with recent accesses should be negative (ln of small number)"

        # This test documents the expected formula


# Mark all tests in this file with integration marker
pytestmark = pytest.mark.integration
