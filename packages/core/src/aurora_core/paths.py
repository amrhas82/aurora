"""
Path resolution utilities for AURORA.

Provides consistent path resolution across all modules:
- Project-local paths (./.aurora/) when in a project context
- Global paths (~/.aurora/) only for budget tracking

RULE: Everything is project-local EXCEPT budget_tracker.json
"""

from pathlib import Path
from typing import Literal


def get_aurora_dir() -> Path:
    """
    Get the correct .aurora directory (project-local or global).

    Resolution order:
    1. If ./.aurora exists → use project-local
    2. Otherwise → use ~/.aurora (global)

    Returns:
        Path to .aurora directory

    Example:
        # In /home/user/myproject with .aurora/ folder
        >>> get_aurora_dir()
        Path('/home/user/myproject/.aurora')

        # In /tmp with no .aurora/ folder
        >>> get_aurora_dir()
        Path('/home/user/.aurora')
    """
    # Check for project-local .aurora
    project_aurora = Path.cwd() / ".aurora"
    if project_aurora.exists() and project_aurora.is_dir():
        return project_aurora

    # Fall back to global
    return Path.home() / ".aurora"


def get_db_path() -> Path:
    """
    Get the path to memory.db (always project-local if project exists).

    Returns:
        Path to memory.db
    """
    return get_aurora_dir() / "memory.db"


def get_logs_dir() -> Path:
    """
    Get the path to logs directory (always project-local if project exists).

    Returns:
        Path to logs directory
    """
    return get_aurora_dir() / "logs"


def get_conversations_dir() -> Path:
    """
    Get the path to conversation logs directory.

    Returns:
        Path to conversations directory
    """
    return get_logs_dir() / "conversations"


def get_budget_tracker_path() -> Path:
    """
    Get the path to budget_tracker.json (ALWAYS global - never project-local).

    Budget tracking is intentionally global because:
    - Users have one budget across all projects
    - Prevents accidental overspend by project isolation

    Returns:
        Path to global budget_tracker.json
    """
    return Path.home() / ".aurora" / "budget_tracker.json"


def ensure_aurora_dir() -> Path:
    """
    Ensure .aurora directory exists and return its path.

    Creates the directory if it doesn't exist.

    Returns:
        Path to .aurora directory
    """
    aurora_dir = get_aurora_dir()
    aurora_dir.mkdir(parents=True, exist_ok=True)
    return aurora_dir


def is_project_mode() -> bool:
    """
    Check if running in project mode (has ./.aurora directory).

    Returns:
        True if project-local .aurora exists
    """
    return (Path.cwd() / ".aurora").exists()
