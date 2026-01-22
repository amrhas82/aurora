"""Planning-specific configuration for Aurora Planning System.

This module provides configuration for the Aurora planning directory structure,
which is separate from the global Aurora configuration.

Default locations:
- Plans directory: ~/.aurora/plans/
- Templates directory: <package>/templates/
- Environment overrides: AURORA_PLANS_DIR, AURORA_TEMPLATE_DIR
"""

import os
from pathlib import Path


def get_plans_dir() -> Path:
    """Get the planning directory path.

    Priority:
    1. AURORA_PLANS_DIR environment variable
    2. Current project's .aurora/plans/ if it exists
    3. ./.aurora/plans/ (default, project-local)

    Returns:
        Path to plans directory

    Raises:
        ValueError: If plans directory is not writable

    """
    # Check environment variable first
    env_plans_dir = os.environ.get("AURORA_PLANS_DIR")
    if env_plans_dir:
        plans_dir = Path(env_plans_dir).expanduser().resolve()
        if not plans_dir.exists():
            plans_dir.mkdir(parents=True, exist_ok=True)
        return plans_dir

    # Check for local project .aurora/plans/
    cwd = Path.cwd()
    local_plans_dir = cwd / ".aurora" / "plans"
    if local_plans_dir.exists() and local_plans_dir.is_dir():
        return local_plans_dir

    # Default to ./.aurora/plans/ (project-local)
    default_plans_dir = Path.cwd() / ".aurora" / "plans"
    if not default_plans_dir.exists():
        default_plans_dir.mkdir(parents=True, exist_ok=True)

    return default_plans_dir


def get_template_dir() -> Path:
    """Get the templates directory path.

    Priority:
    1. AURORA_TEMPLATE_DIR environment variable
    2. <package>/templates/ (bundled templates)

    Returns:
        Path to templates directory

    Raises:
        FileNotFoundError: If templates directory doesn't exist

    """
    # Check environment variable first
    env_template_dir = os.environ.get("AURORA_TEMPLATE_DIR")
    if env_template_dir:
        template_dir = Path(env_template_dir).expanduser().resolve()
        if not template_dir.exists():
            raise FileNotFoundError(
                f"AURORA_TEMPLATE_DIR set to {template_dir}, but directory doesn't exist",
            )
        return template_dir

    # Use bundled templates
    package_dir = Path(__file__).parent
    template_dir = package_dir / "templates"

    if not template_dir.exists():
        raise FileNotFoundError(
            f"Bundled templates not found at {template_dir}. Package may be corrupted.",
        )

    return template_dir


def validate_plans_dir(plans_dir: Path | None = None) -> bool:
    """Validate that plans directory exists and is writable.

    Args:
        plans_dir: Path to validate. If None, uses get_plans_dir()

    Returns:
        True if valid, False otherwise

    """
    if plans_dir is None:
        try:
            plans_dir = get_plans_dir()
        except Exception:
            return False

    if not plans_dir.exists():
        return False

    if not plans_dir.is_dir():
        return False

    # Test writability by attempting to create a temporary file
    test_file = plans_dir / ".aurora_write_test"
    try:
        test_file.touch()
        test_file.unlink()
        return True
    except (OSError, PermissionError):
        return False


def init_plans_directory(base_dir: Path | None = None) -> Path:
    """Initialize the Aurora planning directory structure.

    Creates:
    - <base_dir>/plans/active/
    - <base_dir>/plans/archive/
    - <base_dir>/config/tools/ (for tool configurations)

    Args:
        base_dir: Base directory (default: current directory's .aurora)

    Returns:
        Path to created plans directory

    Raises:
        OSError: If unable to create directories

    """
    if base_dir is None:
        base_dir = Path.cwd() / ".aurora"

    plans_dir = base_dir / "plans"
    (plans_dir / "active").mkdir(parents=True, exist_ok=True)
    (plans_dir / "archive").mkdir(parents=True, exist_ok=True)

    config_dir = base_dir / "config" / "tools"
    config_dir.mkdir(parents=True, exist_ok=True)

    return plans_dir


# Configuration defaults
PLANNING_CONFIG = {
    "base_dir": "~/.aurora/plans",
    "template_dir": "<package>/templates",
    "auto_increment": True,
    "archive_on_complete": False,
    "manifest_file": "manifest.json",
}


def get_config_value(key: str, default: str | None = None) -> str:
    """Get a planning configuration value.

    Args:
        key: Configuration key (e.g., 'base_dir', 'auto_increment')
        default: Default value if key not found

    Returns:
        Configuration value

    Raises:
        KeyError: If key not found and no default provided

    """
    if key in PLANNING_CONFIG:
        return PLANNING_CONFIG[key]
    if default is not None:
        return default
    raise KeyError(f"Configuration key '{key}' not found")
