"""
Git signal extraction for ACT-R Base-Level Activation (BLA) initialization.

This module provides the GitSignalExtractor class for extracting Git commit
history at the FUNCTION level using `git blame -L` to track individual function
edit history. This enables accurate BLA initialization based on how frequently
each function has been modified.

The key insight: Functions in the same file can have VERY different edit histories.
A frequently-edited function should have higher initial activation than a
rarely-touched function in the same file.

Usage:
    >>> extractor = GitSignalExtractor()
    >>> commit_times = extractor.get_function_commit_times(
    ...     file_path="/path/to/file.py",
    ...     line_start=10,
    ...     line_end=25
    ... )
    >>> bla = extractor.calculate_bla(commit_times)
    >>> print(f"Base-Level Activation: {bla:.4f}")
"""

import logging
import math
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)


class GitSignalExtractor:
    """
    Extracts Git commit history for specific line ranges (functions).

    This class uses `git blame -L <start>,<end>` to get the commit history
    for a specific function, then calculates Base-Level Activation (BLA)
    using the ACT-R formula.

    The implementation ensures that each function's BLA is calculated based
    on its individual edit history, not the file-level history.
    """

    def __init__(self, timeout: int = 10):
        """
        Initialize the Git signal extractor.

        Args:
            timeout: Timeout in seconds for Git commands (default 10)
        """
        self.timeout = timeout

    def get_function_commit_times(
        self, file_path: str, line_start: int, line_end: int
    ) -> list[int]:
        """
        Get commit timestamps for a specific function's line range.

        Uses `git blame -L {start},{end} {file} --line-porcelain` to extract
        unique commits that touched this function, then retrieves timestamps
        for each commit using `git show -s --format=%ct`.

        Args:
            file_path: Path to the file (relative or absolute)
            line_start: Starting line number (1-indexed, inclusive)
            line_end: Ending line number (1-indexed, inclusive)

        Returns:
            List of Unix timestamps (seconds since epoch) sorted newest first.
            Returns empty list if:
            - File is not in a Git repository
            - Git command fails
            - No commits found

        Examples:
            >>> extractor = GitSignalExtractor()
            >>> times = extractor.get_function_commit_times("file.py", 10, 25)
            >>> print(f"Function has {len(times)} commits")
        """
        path = Path(file_path).resolve()

        # Check if file exists
        if not path.exists():
            logger.debug(f"File not found: {file_path}")
            return []

        try:
            # Run git blame to get commits for this line range
            result = subprocess.run(
                [
                    "git",
                    "blame",
                    "-L",
                    f"{line_start},{line_end}",
                    str(path),
                    "--line-porcelain",
                ],
                capture_output=True,
                text=True,
                timeout=self.timeout,
                cwd=path.parent,
            )

            if result.returncode != 0:
                # Not a Git repo or other error
                logger.debug(
                    f"Git blame failed for {file_path}:{line_start}-{line_end}: {result.stderr}"
                )
                return []

            # Parse output to extract unique commit SHAs
            commit_shas = self._parse_blame_output(result.stdout)

            if not commit_shas:
                logger.debug(f"No commits found for {file_path}:{line_start}-{line_end}")
                return []

            # Get timestamp for each commit
            timestamps = []
            for sha in commit_shas:
                timestamp = self._get_commit_timestamp(sha, path.parent)
                if timestamp is not None:
                    timestamps.append(timestamp)

            # Sort newest first
            timestamps.sort(reverse=True)

            logger.debug(
                f"Extracted {len(timestamps)} commits for {path.name}:{line_start}-{line_end}"
            )

            return timestamps

        except subprocess.TimeoutExpired:
            logger.warning(f"Git blame timeout for {file_path}:{line_start}-{line_end}")
            return []
        except FileNotFoundError:
            logger.debug(f"Git not found in PATH")
            return []
        except Exception as e:
            logger.warning(f"Error extracting Git history for {file_path}: {e}")
            return []

    def _parse_blame_output(self, output: str) -> list[str]:
        """
        Parse git blame --line-porcelain output to extract unique commit SHAs.

        The --line-porcelain format outputs commit info on lines starting with
        a 40-character hex SHA. We extract these and deduplicate.

        Args:
            output: Raw output from git blame --line-porcelain

        Returns:
            List of unique commit SHAs (40-char hex strings) in order of first appearance
        """
        sha_pattern = re.compile(r"^([0-9a-f]{40})\s", re.MULTILINE)
        matches = sha_pattern.findall(output)

        # Preserve order but deduplicate
        seen = set()
        unique_shas = []
        for sha in matches:
            if sha not in seen:
                seen.add(sha)
                unique_shas.append(sha)

        return unique_shas

    def _get_commit_timestamp(self, sha: str, repo_dir: Path) -> int | None:
        """
        Get Unix timestamp for a specific commit.

        Uses `git show -s --format=%ct {sha}` to get the commit timestamp.

        Args:
            sha: Commit SHA (40-char hex string)
            repo_dir: Directory of the Git repository

        Returns:
            Unix timestamp (seconds since epoch) or None if command fails
        """
        try:
            result = subprocess.run(
                ["git", "show", "-s", "--format=%ct", sha],
                capture_output=True,
                text=True,
                timeout=self.timeout,
                cwd=repo_dir,
            )

            if result.returncode != 0:
                logger.debug(f"Failed to get timestamp for commit {sha}")
                return None

            timestamp_str = result.stdout.strip()
            return int(timestamp_str)

        except (subprocess.TimeoutExpired, ValueError, FileNotFoundError) as e:
            logger.debug(f"Error getting timestamp for {sha}: {e}")
            return None

    def calculate_bla(
        self, commit_times: list[int], decay: float = 0.5, current_time: int | None = None
    ) -> float:
        """
        Calculate Base-Level Activation (BLA) from commit timestamps.

        Uses the ACT-R formula:
            BLA = ln(Σ t_j^(-d))

        Where:
            - t_j: time since j-th commit (in seconds)
            - d: decay rate (default 0.5, standard ACT-R value)
            - Σ: sum over all commits

        Args:
            commit_times: List of Unix timestamps (seconds since epoch)
            decay: Decay rate parameter (default 0.5)
            current_time: Current time as Unix timestamp (defaults to now)

        Returns:
            BLA value (float, typically in range [-10, 5])
            Returns 0.5 for empty commit_times (non-Git fallback)

        Examples:
            >>> extractor = GitSignalExtractor()
            >>> # Function edited 8 times
            >>> times = [1703001600, 1702996800, 1702992000, ...]
            >>> bla = extractor.calculate_bla(times)
            >>> print(f"BLA: {bla:.4f}")  # Higher value due to frequency

            >>> # Function edited once
            >>> times = [1703001600]
            >>> bla = extractor.calculate_bla(times)
            >>> print(f"BLA: {bla:.4f}")  # Lower value
        """
        if not commit_times:
            # Fallback for non-Git or untracked files
            return 0.5

        if current_time is None:
            current_time = int(datetime.now(timezone.utc).timestamp())

        # Calculate power law sum: Σ t_j^(-d)
        power_law_sum = 0.0

        for commit_time in commit_times:
            # Calculate time since commit in seconds
            time_since = current_time - commit_time

            # Prevent division by zero or negative time
            if time_since <= 0:
                time_since = 1  # Treat as just committed (1 second ago)

            # Add power law term: t^(-d)
            power_law_sum += math.pow(time_since, -decay)

        # BLA = ln(sum)
        if power_law_sum > 0:
            bla = math.log(power_law_sum)
        else:
            # Fallback if sum is zero (shouldn't happen)
            bla = 0.5

        logger.debug(
            f"Calculated BLA={bla:.4f} from {len(commit_times)} commits (power_sum={power_law_sum:.6f})"
        )

        return bla


__all__ = ["GitSignalExtractor"]
