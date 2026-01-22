"""Global configuration management for Aurora.

Provides functions to get global config paths and manage configuration following
XDG Base Directory Specification.
"""

import json
import os
import platform as platform_module
from pathlib import Path
from typing import Any

# Constants
GLOBAL_CONFIG_DIR_NAME = "aurora"
GLOBAL_CONFIG_FILE_NAME = "config.json"
GLOBAL_DATA_DIR_NAME = "aurora"

# Default configuration
DEFAULT_CONFIG: dict[str, Any] = {"feature_flags": {}}


def get_global_config_dir() -> Path:
    """Get the global configuration directory path.

    Follows XDG Base Directory Specification:
    - All platforms: $XDG_CONFIG_HOME/aurora/ if XDG_CONFIG_HOME is set
    - Unix/macOS fallback: ~/.config/aurora/
    - Windows fallback: %APPDATA%/aurora/

    Returns:
        Path to global config directory

    """
    # XDG_CONFIG_HOME takes precedence on all platforms
    xdg_config_home = os.environ.get("XDG_CONFIG_HOME")
    if xdg_config_home:
        return Path(xdg_config_home) / GLOBAL_CONFIG_DIR_NAME

    system = platform_module.system()

    if system == "Windows":
        # Windows: use %APPDATA%
        app_data = os.environ.get("APPDATA")
        if app_data:
            return Path(app_data) / GLOBAL_CONFIG_DIR_NAME
        # Fallback
        return Path.home() / "AppData" / "Roaming" / GLOBAL_CONFIG_DIR_NAME

    # Unix/macOS fallback: ~/.config
    return Path.home() / ".config" / GLOBAL_CONFIG_DIR_NAME


def get_global_data_dir() -> Path:
    """Get the global data directory path.

    Used for user data like schema overrides. Follows XDG Base Directory Specification:
    - All platforms: $XDG_DATA_HOME/aurora/ if XDG_DATA_HOME is set
    - Unix/macOS fallback: ~/.local/share/aurora/
    - Windows fallback: %LOCALAPPDATA%/aurora/

    Returns:
        Path to global data directory

    """
    # XDG_DATA_HOME takes precedence on all platforms
    xdg_data_home = os.environ.get("XDG_DATA_HOME")
    if xdg_data_home:
        return Path(xdg_data_home) / GLOBAL_DATA_DIR_NAME

    system = platform_module.system()

    if system == "Windows":
        # Windows: use %LOCALAPPDATA%
        local_app_data = os.environ.get("LOCALAPPDATA")
        if local_app_data:
            return Path(local_app_data) / GLOBAL_DATA_DIR_NAME
        # Fallback
        return Path.home() / "AppData" / "Local" / GLOBAL_DATA_DIR_NAME

    # Unix/macOS fallback: ~/.local/share
    return Path.home() / ".local" / "share" / GLOBAL_DATA_DIR_NAME


def get_global_config() -> dict[str, Any]:
    """Get the global configuration.

    Reads from the global config file, creating it with defaults if it doesn't exist.

    Returns:
        Global configuration dictionary

    """
    config_dir = get_global_config_dir()
    config_file = config_dir / GLOBAL_CONFIG_FILE_NAME

    # Create config directory if it doesn't exist
    config_dir.mkdir(parents=True, exist_ok=True)

    # If config file doesn't exist, create it with defaults
    if not config_file.exists():
        save_global_config(DEFAULT_CONFIG)
        return DEFAULT_CONFIG.copy()

    # Read existing config
    try:
        with config_file.open("r", encoding="utf-8") as f:
            config: dict[str, Any] = json.load(f)
        return config
    except (OSError, json.JSONDecodeError):
        # If config is corrupt, return defaults
        return DEFAULT_CONFIG.copy()


def save_global_config(config: dict[str, Any]) -> None:
    """Save the global configuration.

    Args:
        config: Configuration dictionary to save

    Raises:
        IOError: If unable to write config file

    """
    config_dir = get_global_config_dir()
    config_file = config_dir / GLOBAL_CONFIG_FILE_NAME

    # Create config directory if it doesn't exist
    config_dir.mkdir(parents=True, exist_ok=True)

    # Write config file
    with config_file.open("w", encoding="utf-8") as f:
        json.dump(config, f, indent=2)
