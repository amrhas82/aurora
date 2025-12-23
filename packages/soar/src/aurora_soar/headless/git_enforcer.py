"""
Git Branch Enforcement for Headless Mode

This module provides safety mechanisms to prevent headless mode from executing on
protected branches (main/master). Headless mode performs autonomous operations that
should only run in isolated experiment branches.

Safety Philosophy:
    Headless mode gives AURORA autonomous control, which is powerful but risky on
    production branches. By requiring a dedicated "headless" branch (or custom branch),
    we create a safety boundary that prevents accidental damage to main development work.

Usage:
    from aurora_soar.headless import GitEnforcer, GitEnforcerConfig

    # Default: requires "headless" branch, blocks main/master
    enforcer = GitEnforcer()
    enforcer.validate()  # Raises GitBranchError if on wrong branch

    # Custom configuration
    config = GitEnforcerConfig(
        required_branch="experiment-123",
        blocked_branches=["main", "master", "develop"],
        allow_detached_head=False
    )
    enforcer = GitEnforcer(config)
    enforcer.validate()
"""

import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


class GitBranchError(Exception):
    """
    Raised when git branch validation fails.

    This exception indicates that headless mode cannot run because the current
    git state is unsafe (e.g., on main branch, detached HEAD, no git repo).
    """

    pass


@dataclass
class GitEnforcerConfig:
    """
    Configuration for git branch enforcement.

    Attributes:
        required_branch: Specific branch name required (e.g., "headless").
                        If None, any non-blocked branch is allowed.
        blocked_branches: List of branch names that are forbidden.
                         Default: ["main", "master"]
        allow_detached_head: Whether to allow execution in detached HEAD state.
                            Default: False (safer)
        repo_path: Path to git repository. Default: None (use current directory)
    """

    required_branch: str | None = "headless"
    blocked_branches: list[str] = field(default_factory=lambda: ["main", "master"])
    allow_detached_head: bool = False
    repo_path: Path | None = None


class GitEnforcer:
    """
    Enforces git branch safety constraints for headless mode.

    The GitEnforcer validates that the current git branch meets safety requirements
    before allowing headless mode to execute. This prevents autonomous operations
    from running on protected branches like main or master.

    Key Validations:
        1. Repository exists and is a valid git repo
        2. Current branch is not in blocked_branches list
        3. If required_branch set, current branch matches it
        4. Not in detached HEAD state (unless explicitly allowed)

    Examples:
        # Basic usage with defaults (requires "headless" branch)
        >>> enforcer = GitEnforcer()
        >>> enforcer.validate()  # OK if on "headless" branch

        # Custom branch requirement
        >>> config = GitEnforcerConfig(required_branch="experiment-1")
        >>> enforcer = GitEnforcer(config)
        >>> enforcer.validate()

        # Block multiple branches, no specific requirement
        >>> config = GitEnforcerConfig(
        ...     required_branch=None,
        ...     blocked_branches=["main", "master", "develop", "production"]
        ... )
        >>> enforcer = GitEnforcer(config)
        >>> enforcer.validate()  # OK on any other branch

        # Get current branch without validation
        >>> enforcer = GitEnforcer()
        >>> branch = enforcer.get_current_branch()
        >>> print(f"Current branch: {branch}")
    """

    def __init__(self, config: GitEnforcerConfig | None = None):
        """
        Initialize GitEnforcer with configuration.

        Args:
            config: GitEnforcerConfig instance. If None, uses default config
                   (requires "headless" branch, blocks main/master).
        """
        self.config = config or GitEnforcerConfig()

    def get_current_branch(self) -> str:
        """
        Get the name of the current git branch.

        Returns:
            Current branch name (e.g., "headless", "main").

        Raises:
            GitBranchError: If not in a git repository, in detached HEAD state,
                          or git command fails.

        Examples:
            >>> enforcer = GitEnforcer()
            >>> branch = enforcer.get_current_branch()
            >>> print(branch)
            'headless'
        """
        try:
            # Use rev-parse to get current branch name
            result = subprocess.run(
                ["git", "rev-parse", "--abbrev-ref", "HEAD"],
                cwd=self.config.repo_path,
                capture_output=True,
                text=True,
                check=True,
                timeout=5,
            )

            branch = result.stdout.strip()

            # Check for detached HEAD
            if branch == "HEAD":
                raise GitBranchError(
                    "Cannot run headless mode in detached HEAD state. "
                    "Please checkout a branch first (e.g., 'git checkout headless')."
                )

            return branch

        except subprocess.CalledProcessError as e:
            # Git command failed - likely not in a git repository
            stderr = e.stderr.strip() if e.stderr else "unknown error"
            raise GitBranchError(
                f"Failed to get current git branch: {stderr}. "
                "Ensure you are in a git repository."
            ) from e

        except subprocess.TimeoutExpired as e:
            raise GitBranchError(
                "Git command timed out. Check git installation and repository state."
            ) from e

        except FileNotFoundError as e:
            raise GitBranchError(
                "Git command not found. Please ensure git is installed and in PATH."
            ) from e

    def is_git_repository(self) -> bool:
        """
        Check if the current directory is inside a git repository.

        Returns:
            True if inside a git repository, False otherwise.

        Examples:
            >>> enforcer = GitEnforcer()
            >>> if enforcer.is_git_repository():
            ...     print("In git repo")
            ... else:
            ...     print("Not in git repo")
        """
        try:
            subprocess.run(
                ["git", "rev-parse", "--git-dir"],
                cwd=self.config.repo_path,
                capture_output=True,
                check=True,
                timeout=5,
            )
            return True
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError):
            return False

    def validate(self) -> None:
        """
        Validate that current git state meets safety requirements.

        This is the main entry point for git branch enforcement. Call this before
        starting headless mode to ensure it's safe to proceed.

        Raises:
            GitBranchError: If validation fails for any reason:
                - Not in a git repository
                - On a blocked branch (e.g., main, master)
                - Not on required branch (if specified)
                - In detached HEAD state (unless allowed)

        Examples:
            >>> enforcer = GitEnforcer()
            >>> try:
            ...     enforcer.validate()
            ...     print("Safe to run headless mode")
            ... except GitBranchError as e:
            ...     print(f"Cannot run: {e}")

            >>> # Example error: on main branch
            >>> enforcer.validate()
            GitBranchError: Cannot run headless mode on blocked branch 'main'.
            Blocked branches: main, master
            Please switch to the 'headless' branch first.
        """
        # 1. Check if in a git repository
        if not self.is_git_repository():
            raise GitBranchError(
                "Not in a git repository. Headless mode requires git for safety tracking. "
                "Initialize with 'git init' or run in a git repository."
            )

        # 2. Get current branch (also checks for detached HEAD)
        try:
            current_branch = self.get_current_branch()
        except GitBranchError:
            # Re-raise with additional context if detached HEAD not allowed
            if not self.config.allow_detached_head:
                raise
            # If detached HEAD is allowed, we still can't proceed without a branch name
            raise GitBranchError(
                "Detached HEAD state detected. Headless mode requires a named branch "
                "for safety and tracking. Please checkout a branch."
            )

        # 3. Check if on a blocked branch
        if current_branch in self.config.blocked_branches:
            blocked_list = ", ".join(self.config.blocked_branches)
            required_msg = (
                f"Please switch to the '{self.config.required_branch}' branch first."
                if self.config.required_branch
                else "Please switch to a non-protected branch for experiments."
            )

            raise GitBranchError(
                f"Cannot run headless mode on blocked branch '{current_branch}'. "
                f"Blocked branches: {blocked_list}\n"
                f"{required_msg}\n\n"
                f"Command: git checkout {self.config.required_branch or '<experiment-branch>'}"
            )

        # 4. If specific branch required, verify we're on it
        if self.config.required_branch and current_branch != self.config.required_branch:
            raise GitBranchError(
                f"Headless mode requires branch '{self.config.required_branch}', "
                f"but currently on '{current_branch}'. "
                f"Please switch branches first.\n\n"
                f"Command: git checkout {self.config.required_branch}\n"
                f"(Create if needed: git checkout -b {self.config.required_branch})"
            )

        # All validations passed
        # Could log success here if we had logging configured

    def get_validation_status(self) -> dict[str, Any]:
        """
        Get detailed validation status without raising exceptions.

        Useful for diagnostic purposes or for displaying status to users before
        attempting to run headless mode.

        Returns:
            Dictionary with validation status:
                - is_git_repo: bool
                - current_branch: str or None
                - is_valid: bool
                - error_message: str or None

        Examples:
            >>> enforcer = GitEnforcer()
            >>> status = enforcer.get_validation_status()
            >>> print(status)
            {
                'is_git_repo': True,
                'current_branch': 'main',
                'is_valid': False,
                'error_message': "Cannot run headless mode on blocked branch 'main'..."
            }
        """
        status: dict[str, Any] = {
            "is_git_repo": False,
            "current_branch": None,
            "is_valid": False,
            "error_message": None,
        }

        # Check git repository
        status["is_git_repo"] = self.is_git_repository()
        if not status["is_git_repo"]:
            status["error_message"] = "Not in a git repository"
            return status

        # Get current branch
        try:
            status["current_branch"] = self.get_current_branch()
        except GitBranchError as e:
            status["error_message"] = str(e)
            return status

        # Validate
        try:
            self.validate()
            status["is_valid"] = True
        except GitBranchError as e:
            status["error_message"] = str(e)

        return status
