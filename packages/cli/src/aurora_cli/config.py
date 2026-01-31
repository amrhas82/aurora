"""Configuration management for AURORA CLI.

Simple config system:
- defaults.json (package defaults)
- ~/.aurora/config.json (user overrides)
- Environment variable overrides

Config is a plain dict with nested structure matching the JSON files.
"""

import copy
import json
import logging
import os
from pathlib import Path
from typing import Any

from aurora_cli.errors import ConfigurationError


logger = logging.getLogger(__name__)

# Path to package defaults
DEFAULTS_FILE = Path(__file__).parent / "defaults.json"


# Load CONFIG_SCHEMA for backward compatibility
# This loads defaults at import time - tests and other code may reference this
def _load_config_schema() -> dict[str, Any]:
    """Load defaults as CONFIG_SCHEMA for backward compat."""
    try:
        with open(DEFAULTS_FILE) as f:
            return json.load(f)
    except FileNotFoundError:
        return {}


CONFIG_SCHEMA = _load_config_schema()

# List of supported AI coding tools
AI_TOOLS: list[dict[str, str | bool]] = [
    {"name": "Amazon Q", "value": "amazon-q", "available": True},
    {"name": "Antigravity", "value": "antigravity", "available": True},
    {"name": "Auggie", "value": "auggie", "available": True},
    {"name": "Claude Code", "value": "claude", "available": True},
    {"name": "Cline", "value": "cline", "available": True},
    {"name": "Codex", "value": "codex", "available": True},
    {"name": "CodeBuddy", "value": "codebuddy", "available": True},
    {"name": "CoStrict", "value": "costrict", "available": True},
    {"name": "Crush", "value": "crush", "available": True},
    {"name": "Cursor", "value": "cursor", "available": True},
    {"name": "Factory", "value": "factory", "available": True},
    {"name": "Gemini CLI", "value": "gemini", "available": True},
    {"name": "GitHub Copilot", "value": "github-copilot", "available": True},
    {"name": "iFlow", "value": "iflow", "available": True},
    {"name": "Kilo Code", "value": "kilocode", "available": True},
    {"name": "OpenCode", "value": "opencode", "available": True},
    {"name": "Qoder", "value": "qoder", "available": True},
    {"name": "Qwen Code", "value": "qwen", "available": True},
    {"name": "RooCode", "value": "roocode", "available": True},
    {"name": "Windsurf", "value": "windsurf", "available": True},
]


def _deep_merge(base: dict, override: dict) -> dict:
    """Deep merge override into base dict."""
    result = copy.deepcopy(base)
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = copy.deepcopy(value)
    return result


def _get_aurora_home() -> Path:
    """Get Aurora home directory, respecting AURORA_HOME env var."""
    aurora_home_env = os.environ.get("AURORA_HOME")
    if aurora_home_env:
        return Path(aurora_home_env)
    return Path.home() / ".aurora"


def _apply_env_overrides(config: dict) -> None:
    """Apply environment variable overrides to config (mutates in place)."""
    # API key
    if "ANTHROPIC_API_KEY" in os.environ:
        config.setdefault("llm", {})["api_key"] = os.environ["ANTHROPIC_API_KEY"]

    # Escalation
    if "AURORA_ESCALATION_THRESHOLD" in os.environ:
        try:
            config.setdefault("escalation", {})["threshold"] = float(
                os.environ["AURORA_ESCALATION_THRESHOLD"],
            )
        except ValueError:
            raise ConfigurationError(
                f"AURORA_ESCALATION_THRESHOLD must be a number, got '{os.environ['AURORA_ESCALATION_THRESHOLD']}'",
            )

    # Logging
    if "AURORA_LOGGING_LEVEL" in os.environ:
        config.setdefault("logging", {})["level"] = os.environ["AURORA_LOGGING_LEVEL"].upper()

    # Planning
    if "AURORA_PLANS_DIR" in os.environ:
        config.setdefault("planning", {})["base_dir"] = os.environ["AURORA_PLANS_DIR"]

    if "AURORA_TEMPLATE_DIR" in os.environ:
        config.setdefault("planning", {})["template_dir"] = os.environ["AURORA_TEMPLATE_DIR"]

    # SOAR
    if "AURORA_SOAR_TOOL" in os.environ:
        config.setdefault("soar", {})["default_tool"] = os.environ["AURORA_SOAR_TOOL"]

    if "AURORA_SOAR_MODEL" in os.environ:
        val = os.environ["AURORA_SOAR_MODEL"].lower()
        if val in ("sonnet", "opus"):
            config.setdefault("soar", {})["default_model"] = val
        else:
            raise ConfigurationError(f"AURORA_SOAR_MODEL must be 'sonnet' or 'opus', got '{val}'")

    # Headless
    if "AURORA_HEADLESS_TOOLS" in os.environ:
        config.setdefault("headless", {})["tools"] = [
            t.strip() for t in os.environ["AURORA_HEADLESS_TOOLS"].split(",") if t.strip()
        ]

    if "AURORA_HEADLESS_TIMEOUT" in os.environ:
        try:
            config.setdefault("headless", {})["timeout"] = int(
                os.environ["AURORA_HEADLESS_TIMEOUT"],
            )
        except ValueError:
            raise ConfigurationError("AURORA_HEADLESS_TIMEOUT must be an integer")

    if "AURORA_HEADLESS_BUDGET" in os.environ:
        try:
            config.setdefault("headless", {})["budget"] = float(
                os.environ["AURORA_HEADLESS_BUDGET"],
            )
        except ValueError:
            raise ConfigurationError(
                f"AURORA_HEADLESS_BUDGET must be a number, got '{os.environ['AURORA_HEADLESS_BUDGET']}'",
            )

    if "AURORA_HEADLESS_TIME_LIMIT" in os.environ:
        try:
            val = os.environ["AURORA_HEADLESS_TIME_LIMIT"]
            # Must be integer (seconds), not float
            if "." in val:
                raise ConfigurationError(
                    f"AURORA_HEADLESS_TIME_LIMIT must be an integer, got '{val}'",
                )
            config.setdefault("headless", {})["time_limit"] = int(val)
        except ValueError:
            raise ConfigurationError(
                f"AURORA_HEADLESS_TIME_LIMIT must be an integer, got '{os.environ['AURORA_HEADLESS_TIME_LIMIT']}'",
            )


def load_config(path: str | Path | None = None) -> dict[str, Any]:
    """Load configuration: defaults + user overrides + env vars.

    Args:
        path: Optional explicit path to config file

    Returns:
        Config dict with nested structure

    Search order (if path not provided):
    1. Project mode (./.aurora exists): ./.aurora/config.json
    2. Global mode: ~/.aurora/config.json

    """
    # Load package defaults
    with open(DEFAULTS_FILE) as f:
        config = json.load(f)

    # Find user config file
    if path is None:
        if Path("./.aurora").exists():
            # Project mode
            user_config_path = Path("./.aurora/config.json")
        else:
            # Global mode
            user_config_path = _get_aurora_home() / "config.json"
    else:
        user_config_path = Path(path).expanduser()

    # Merge user config if exists
    if user_config_path.exists():
        try:
            with open(user_config_path) as f:
                user_config = json.load(f)
            config = _deep_merge(config, user_config)
        except json.JSONDecodeError as e:
            logger.warning(f"Invalid JSON in {user_config_path}: {e}, using defaults")
        except Exception as e:
            logger.warning(f"Failed to load {user_config_path}: {e}, using defaults")

    # Apply environment variable overrides
    _apply_env_overrides(config)

    return config


def save_config(config: dict[str, Any], path: str | Path | None = None) -> None:
    """Save configuration to file.

    Args:
        config: Config dict to save
        path: Optional path (defaults to ~/.aurora/config.json)

    """
    if path is None:
        path = _get_aurora_home() / "config.json"
    else:
        path = Path(path).expanduser()

    path.parent.mkdir(parents=True, exist_ok=True)

    with open(path, "w") as f:
        json.dump(config, f, indent=2)


def validate_config(config: dict[str, Any]) -> list[str]:
    """Validate configuration values.

    Args:
        config: Config dict to validate

    Returns:
        List of validation error messages (empty if valid)

    """
    errors = []

    # Escalation threshold
    threshold = config.get("escalation", {}).get("threshold", 0.7)
    if not 0.0 <= threshold <= 1.0:
        errors.append(f"escalation.threshold must be 0.0-1.0, got {threshold}")

    # LLM temperature
    temp = config.get("llm", {}).get("temperature", 0.7)
    if not 0.0 <= temp <= 2.0:
        errors.append(f"llm.temperature must be 0.0-2.0, got {temp}")

    # Logging level
    level = config.get("logging", {}).get("level", "INFO")
    valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
    if level not in valid_levels:
        errors.append(f"logging.level must be one of {valid_levels}, got '{level}'")

    # Headless strategy
    strategy = config.get("headless", {}).get("strategy", "first_success")
    valid_strategies = ["first_success", "all_complete", "voting", "best_score", "merge"]
    if strategy not in valid_strategies:
        errors.append(f"headless.strategy must be one of {valid_strategies}, got '{strategy}'")

    # Search score
    score = config.get("search", {}).get("min_semantic_score", 0.7)
    if not 0.0 <= score <= 1.0:
        errors.append(f"search.min_semantic_score must be 0.0-1.0, got {score}")

    # Headless budget (must be positive if set)
    budget = config.get("headless", {}).get("budget")
    if budget is not None and budget <= 0:
        errors.append(f"headless.budget must be positive, got {budget}")

    # Headless time_limit (must be positive if set)
    time_limit = config.get("headless", {}).get("time_limit")
    if time_limit is not None and time_limit <= 0:
        errors.append(f"headless.time_limit must be positive, got {time_limit}")

    # Tool configs validation
    tool_configs = config.get("headless", {}).get("tool_configs", {})
    for tool_name, tool_config in tool_configs.items():
        max_retries = tool_config.get("max_retries")
        if max_retries is not None and max_retries < 0:
            errors.append(
                f"headless.tool_configs.{tool_name}.max_retries must be non-negative, got {max_retries}",
            )
        retry_delay = tool_config.get("retry_delay")
        if retry_delay is not None and retry_delay < 0:
            errors.append(
                f"headless.tool_configs.{tool_name}.retry_delay must be non-negative, got {retry_delay}",
            )

    return errors


# ============================================================================
# Helper functions for common config access patterns
# ============================================================================


def get_db_path(config: dict[str, Any]) -> str:
    """Get expanded database path."""
    path = config.get("storage", {}).get("path", "./.aurora/memory.db")
    return str(Path(path).expanduser().resolve())


def get_api_key(config: dict[str, Any]) -> str | None:
    """Get API key from config or environment."""
    # Check for key stored in config (not recommended but supported)
    key = config.get("llm", {}).get("api_key")
    if key:
        return key

    # Check environment variable
    env_var = config.get("llm", {}).get("api_key_env", "ANTHROPIC_API_KEY")
    return os.environ.get(env_var)


def get_planning_base_dir(config: dict[str, Any]) -> str:
    """Get expanded planning base directory."""
    path = config.get("planning", {}).get("base_dir", "./.aurora/plans")
    return str(Path(path).expanduser().resolve())


def get_planning_template_dir(config: dict[str, Any]) -> str | None:
    """Get expanded planning template directory (None for package default)."""
    path = config.get("planning", {}).get("template_dir")
    if path is None:
        return None
    return str(Path(path).expanduser().resolve())


def get_manifest_path(config: dict[str, Any]) -> str:
    """Get expanded agent manifest path."""
    path = config.get("agents", {}).get("manifest_path", "./.aurora/cache/agent_manifest.json")
    return str(Path(path).expanduser().resolve())


def get_budget_tracker_path(config: dict[str, Any]) -> str:
    """Get expanded budget tracker path."""
    path = config.get("budget", {}).get("tracker_path", "~/.aurora/budget_tracker.json")
    return str(Path(path).expanduser().resolve())


# ============================================================================
# Backward compatibility - Config class wrapping dict
# ============================================================================


class Config:
    """Config wrapper for backward compatibility.

    Wraps a config dict and provides attribute access for common fields.
    New code should use the dict directly via load_config().
    """

    def __init__(self, data: dict[str, Any] | None = None, **kwargs):
        """Initialize with config dict or load from file.

        Args:
            data: Config dict. If None, loads from file.
            **kwargs: Legacy field overrides (e.g., db_path="...")

        """
        if data is None:
            data = load_config()
        self._data = data

        # Apply legacy kwargs as overrides
        if "db_path" in kwargs:
            self._data.setdefault("storage", {})["path"] = kwargs["db_path"]
        if "headless_budget" in kwargs:
            self._data.setdefault("headless", {})["budget"] = kwargs["headless_budget"]
        if "headless_time_limit" in kwargs:
            self._data.setdefault("headless", {})["time_limit"] = kwargs["headless_time_limit"]
        if "headless_tool_configs" in kwargs:
            self._data.setdefault("headless", {})["tool_configs"] = kwargs["headless_tool_configs"]

    def __getitem__(self, key: str) -> Any:
        """Dict-style access: config["budget"]."""
        return self._data[key]

    def get(self, key: str, default: Any = None) -> Any:
        """Dict-style get with default: config.get("budget", {})."""
        return self._data.get(key, default)

    # Common attribute accessors for backward compatibility
    @property
    def db_path(self) -> str:
        return self._data.get("storage", {}).get("path", "./.aurora/memory.db")

    @property
    def embedding_model(self) -> str:
        return self._data.get("search", {}).get(
            "embedding_model",
            "sentence-transformers/all-MiniLM-L6-v2",
        )

    @property
    def search_min_semantic_score(self) -> float:
        return self._data.get("search", {}).get("min_semantic_score", 0.7)

    @property
    def budget_limit(self) -> float:
        return self._data.get("budget", {}).get("limit", 10.0)

    @property
    def budget_tracker_path(self) -> str:
        return self._data.get("budget", {}).get("tracker_path", "~/.aurora/budget_tracker.json")

    @property
    def headless_tool_configs(self) -> dict:
        return self._data.get("headless", {}).get("tool_configs", {})

    @property
    def agents_discovery_paths(self) -> list[str]:
        """Get agent discovery paths, falling back to all tools from registry.

        Returns paths from config if specified, otherwise returns all 20 tool
        paths from the centralized paths.py registry.
        """
        paths = self._data.get("agents", {}).get("discovery_paths", [])
        if not paths:
            # Default to all tool paths from registry
            from aurora_cli.configurators.slash.paths import get_all_agent_paths
            paths = get_all_agent_paths()
        return paths

    @property
    def agents_manifest_path(self) -> str:
        return self._data.get("agents", {}).get(
            "manifest_path",
            "./.aurora/cache/agent_manifest.json",
        )

    @property
    def planning_base_dir(self) -> str:
        return self._data.get("planning", {}).get("base_dir", "./.aurora/plans")

    @property
    def planning_template_dir(self) -> str | None:
        return self._data.get("planning", {}).get("template_dir")

    @property
    def soar_default_tool(self) -> str:
        return self._data.get("soar", {}).get("default_tool", "claude")

    @property
    def soar_default_model(self) -> str:
        return self._data.get("soar", {}).get("default_model", "sonnet")

    @property
    def headless_tools(self) -> list[str]:
        return self._data.get("headless", {}).get("tools", ["claude"])

    @property
    def headless_strategy(self) -> str:
        return self._data.get("headless", {}).get("strategy", "first_success")

    @property
    def headless_parallel(self) -> bool:
        return self._data.get("headless", {}).get("parallel", True)

    @property
    def headless_max_iterations(self) -> int:
        return self._data.get("headless", {}).get("max_iterations", 10)

    @property
    def headless_timeout(self) -> int:
        return self._data.get("headless", {}).get("timeout", 600)

    @property
    def headless_budget(self) -> float | None:
        return self._data.get("headless", {}).get("budget")

    @property
    def headless_time_limit(self) -> int | None:
        return self._data.get("headless", {}).get("time_limit")

    @property
    def headless_routing_rules(self) -> list[dict]:
        return self._data.get("headless", {}).get("routing_rules", [])

    @property
    def agents_auto_refresh(self) -> bool:
        return self._data.get("agents", {}).get("auto_refresh", True)

    @property
    def agents_refresh_interval_hours(self) -> int:
        # Convert from days in defaults.json to hours for legacy compat
        days = self._data.get("agents", {}).get("refresh_interval_days", 1)
        return days * 24

    # Helper methods
    def get_db_path(self) -> str:
        return get_db_path(self._data)

    def get_api_key(self) -> str | None:
        return get_api_key(self._data)

    def get_planning_base_dir(self) -> str:
        return get_planning_base_dir(self._data)

    def get_planning_template_dir(self) -> str | None:
        return get_planning_template_dir(self._data)

    def get_manifest_path(self) -> str:
        return get_manifest_path(self._data)

    def validate(self) -> None:
        """Validate config, raise ConfigurationError if invalid."""
        errors = validate_config(self._data)
        if errors:
            raise ConfigurationError("\n".join(errors))
