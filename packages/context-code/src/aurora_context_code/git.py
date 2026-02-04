"""Git signal extraction for ACT-R Base-Level Activation (BLA) initialization.

This module provides the GitSignalExtractor class for extracting Git commit
history at the FUNCTION level. It uses file-level blame caching for efficiency:
instead of running `git blame -L` for each function, it runs `git blame` once
per file and caches per-line attribution. Function-level data is sliced from
the cache in O(1) time.

This optimization reduces git operations from O(functions) to O(files),
typically a 5-10x speedup for codebases with multiple functions per file.

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
import os
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)


class GitSignalExtractor:
    """Extracts Git commit history for specific line ranges (functions).

    Uses file-level blame caching for efficiency: runs `git blame` once per file
    and caches per-line attribution. Function-level data is then sliced from
    the cache, eliminating redundant git operations.

    Performance: O(files) git operations instead of O(functions).

    The implementation ensures that each function's BLA is calculated based
    on its individual edit history, not the file-level history.
    """

    def __init__(self, timeout: int = 30):
        """Initialize the Git signal extractor.

        Args:
            timeout: Timeout in seconds for Git commands (default 30, increased for full-file blame)

        """
        self.timeout = timeout
        self.available = True

        # File-level blame cache: {file_path: {line_num: (sha, timestamp)}}
        # This eliminates redundant git blame calls for functions in the same file
        self._file_blame_cache: dict[str, dict[int, tuple[str, int]]] = {}

        # Commit timestamp cache: {sha: timestamp}
        # Avoids repeated `git show` calls for the same commit
        self._commit_timestamp_cache: dict[str, int] = {}

        # Track which repo we're working in (for cwd in git commands)
        self._repo_root: Path | None = None

        # Check if Git should be disabled via environment variable
        if os.getenv("AURORA_SKIP_GIT"):
            self.available = False
            logger.warning(
                "Git disabled via AURORA_SKIP_GIT - BLA will use default activation (0.5)\n"
                "→ Unset AURORA_SKIP_GIT to enable Git-based activation",
            )

    def _get_repo_root(self, file_path: Path) -> Path | None:
        """Find the git repository root for a file."""
        if self._repo_root is not None:
            return self._repo_root

        try:
            result = subprocess.run(
                ["git", "rev-parse", "--show-toplevel"],
                capture_output=True,
                text=True,
                timeout=5,
                cwd=file_path.parent,
            )
            if result.returncode == 0:
                self._repo_root = Path(result.stdout.strip())
                return self._repo_root
        except Exception:
            pass
        return None

    def _get_file_blame(self, file_path: Path) -> dict[int, tuple[str, int]]:
        """Get blame data for entire file, with caching.

        Runs `git blame --line-porcelain <file>` once and parses into a dict
        mapping line numbers to (sha, timestamp) tuples.

        Args:
            file_path: Absolute path to the file

        Returns:
            Dict mapping line_num -> (sha, timestamp)
            Returns empty dict on error

        """
        file_key = str(file_path)

        # Return cached data if available
        if file_key in self._file_blame_cache:
            return self._file_blame_cache[file_key]

        # Initialize empty cache entry (will be populated or remain empty on error)
        self._file_blame_cache[file_key] = {}

        try:
            repo_root = self._get_repo_root(file_path)
            if repo_root is None:
                logger.debug(f"Not a git repo: {file_path}")
                return {}

            # Run git blame for ENTIRE file (no -L flag) - this is the key optimization
            result = subprocess.run(
                ["git", "blame", "--line-porcelain", str(file_path)],
                capture_output=True,
                text=True,
                timeout=self.timeout,
                cwd=repo_root,
            )

            if result.returncode != 0:
                logger.debug(f"Git blame failed for {file_path}: {result.stderr}")
                return {}

            # Parse the porcelain output into per-line data
            blame_data = self._parse_full_file_blame(result.stdout, repo_root)
            self._file_blame_cache[file_key] = blame_data

            logger.debug(f"Cached blame for {file_path.name}: {len(blame_data)} lines")
            return blame_data

        except subprocess.TimeoutExpired:
            logger.warning(f"Git blame timeout for {file_path}")
            return {}
        except FileNotFoundError:
            logger.debug("Git not found in PATH")
            return {}
        except Exception as e:
            logger.warning(f"Error getting blame for {file_path}: {e}")
            return {}

    def _parse_full_file_blame(self, output: str, _repo_root: Path) -> dict[int, tuple[str, int]]:
        r"""Parse git blame --line-porcelain output for entire file.

        The format repeats for each line:
            <sha> <orig_line> <final_line> [<num_lines>]
            author <name>
            author-mail <email>
            author-time <timestamp>
            author-tz <tz>
            committer <name>
            committer-mail <email>
            committer-time <timestamp>
            committer-tz <tz>
            summary <message>
            [previous <sha> <filename>]
            [boundary]
            filename <filename>
            \t<line_content>

        We extract: final_line -> (sha, author-time)

        Args:
            output: Raw git blame --line-porcelain output
            repo_root: Repository root for git show calls

        Returns:
            Dict mapping line_num -> (sha, timestamp)

        """
        blame_data: dict[int, tuple[str, int]] = {}

        # Split into blocks (each block starts with a SHA line)
        current_sha: str | None = None
        current_line: int | None = None
        current_timestamp: int | None = None

        for line in output.split("\n"):
            # SHA line: starts with 40 hex chars
            sha_match = re.match(r"^([0-9a-f]{40})\s+\d+\s+(\d+)", line)
            if sha_match:
                # Save previous block if complete
                if current_sha and current_line and current_timestamp:
                    blame_data[current_line] = (current_sha, current_timestamp)

                current_sha = sha_match.group(1)
                current_line = int(sha_match.group(2))
                current_timestamp = None

                # Check commit timestamp cache first
                if current_sha in self._commit_timestamp_cache:
                    current_timestamp = self._commit_timestamp_cache[current_sha]
                continue

            # Author time line
            if line.startswith("author-time ") and current_sha:
                try:
                    timestamp = int(line.split(" ", 1)[1])
                    current_timestamp = timestamp
                    # Cache for future use
                    self._commit_timestamp_cache[current_sha] = timestamp
                except (ValueError, IndexError):
                    pass

        # Don't forget the last block
        if current_sha and current_line and current_timestamp:
            blame_data[current_line] = (current_sha, current_timestamp)

        return blame_data

    def get_function_commit_times(
        self,
        file_path: str,
        line_start: int,
        line_end: int,
    ) -> list[int]:
        """Get commit timestamps for a specific function's line range.

        Uses file-level blame cache: runs `git blame` once per file, then slices
        the cached data for the function's line range. This is O(line_range) after
        the initial O(file_size) blame, vs O(git_blame) for each function.

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
        # Check if Git is available
        if not self.available:
            return []

        path = Path(file_path).resolve()

        # Check if file exists
        if not path.exists():
            logger.debug(f"File not found: {file_path}")
            return []

        # Get full file blame (cached)
        blame_data = self._get_file_blame(path)

        if not blame_data:
            return []

        # Slice the blame data for this function's line range
        # Collect unique (sha, timestamp) pairs for the line range
        commits_seen: set[str] = set()
        timestamps: list[int] = []

        for line_num in range(line_start, line_end + 1):
            if line_num in blame_data:
                sha, timestamp = blame_data[line_num]
                if sha not in commits_seen:
                    commits_seen.add(sha)
                    timestamps.append(timestamp)

        # Sort newest first
        timestamps.sort(reverse=True)

        logger.debug(
            f"Extracted {len(timestamps)} commits for {path.name}:{line_start}-{line_end} (from cache)",
        )

        return timestamps

    def clear_cache(self) -> None:
        """Clear all caches. Useful when indexing a new directory."""
        self._file_blame_cache.clear()
        self._commit_timestamp_cache.clear()
        self._repo_root = None

    def _parse_blame_output(self, output: str) -> list[str]:
        """Parse git blame --line-porcelain output to extract unique commit SHAs.

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
        """Get Unix timestamp for a specific commit.

        Uses cache first, falls back to `git show -s --format=%ct {sha}`.

        Args:
            sha: Commit SHA (40-char hex string)
            repo_dir: Directory of the Git repository

        Returns:
            Unix timestamp (seconds since epoch) or None if command fails

        """
        # Check cache first
        if sha in self._commit_timestamp_cache:
            return self._commit_timestamp_cache[sha]

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
            timestamp = int(timestamp_str)

            # Cache for future use
            self._commit_timestamp_cache[sha] = timestamp
            return timestamp

        except (subprocess.TimeoutExpired, ValueError, FileNotFoundError) as e:
            logger.debug(f"Error getting timestamp for {sha}: {e}")
            return None

    def calculate_bla(
        self,
        commit_times: list[int],
        decay: float = 0.5,
        current_time: int | None = None,
    ) -> float:
        """Calculate Base-Level Activation (BLA) from commit timestamps.

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

        # Calculate BLA as natural log of sum
        if power_law_sum > 0:
            bla = math.log(power_law_sum)
        else:
            # Fallback if sum is zero (shouldn't happen)
            bla = 0.5

        logger.debug(
            f"Calculated BLA={bla:.4f} from {len(commit_times)} commits (power_sum={power_law_sum:.6f})",
        )

        return bla


__all__ = ["GitSignalExtractor"]
