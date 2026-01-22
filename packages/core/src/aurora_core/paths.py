"""Path resolution utilities for AURORA.

Provides consistent path resolution across all modules:
- Project-local paths (./.aurora/) when in a project context
- Global paths (~/.aurora/) only for budget tracking

RULE: Everything is project-local EXCEPT budget_tracker.json
"""

from pathlib import Path


def get_aurora_dir() -> Path:
    """Get the project-local .aurora directory (strict mode).

    Resolution:
    - If ./.aurora exists → use project-local
    - Otherwise → raise error (user must run 'aur init' first)

    Returns:
        Path to .aurora directory

    Raises:
        RuntimeError: If .aurora directory doesn't exist in current project

    Example:
        # In /home/user/myproject with .aurora/ folder
        >>> get_aurora_dir()
        Path('/home/user/myproject/.aurora')

        # In /tmp with no .aurora/ folder
        >>> get_aurora_dir()
        RuntimeError: Project not initialized...

    """
    # Check for project-local .aurora
    project_aurora = Path.cwd() / ".aurora"
    if project_aurora.exists() and project_aurora.is_dir():
        return project_aurora

    # Fail with helpful error message
    raise RuntimeError(
        "Project not initialized. Run 'aur init' first to create .aurora directory.\n"
        f"Current directory: {Path.cwd()}\n"
        "This ensures all project artifacts are stored locally, not globally.",
    )


def get_db_path() -> Path:
    """Get the path to memory.db (always project-local if project exists).

    Returns:
        Path to memory.db

    """
    return get_aurora_dir() / "memory.db"


def get_logs_dir() -> Path:
    """Get the path to logs directory (always project-local if project exists).

    Returns:
        Path to logs directory

    """
    return get_aurora_dir() / "logs"


def get_conversations_dir() -> Path:
    """Get the path to conversation logs directory.

    Returns:
        Path to conversations directory

    """
    return get_logs_dir() / "conversations"


def get_budget_tracker_path() -> Path:
    """Get the path to budget_tracker.json (ALWAYS global - never project-local).

    Budget tracking is intentionally global because:
    - Users have one budget across all projects
    - Prevents accidental overspend by project isolation

    Returns:
        Path to global budget_tracker.json

    """
    return Path.home() / ".aurora" / "budget_tracker.json"


def ensure_aurora_dir() -> Path:
    """Ensure project-local .aurora directory exists and return its path.

    Creates ./.aurora directory if it doesn't exist.
    Use this for initialization code (like 'aur init').

    Returns:
        Path to .aurora directory (always project-local ./.aurora)

    """
    # Always use project-local .aurora (never global)
    project_aurora = Path.cwd() / ".aurora"
    project_aurora.mkdir(parents=True, exist_ok=True)
    return project_aurora


def is_project_mode() -> bool:
    """Check if running in project mode (has ./.aurora directory).

    Returns:
        True if project-local .aurora exists

    """
    return (Path.cwd() / ".aurora").exists()
