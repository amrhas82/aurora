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
    """Validate configuration values against the schema.

    Checks types, ranges, and enum constraints for all config sections.

    Args:
        config: Config dict to validate

    Returns:
        List of validation error messages (empty if valid)

    """
    errors = []

    # -- Top-level keys --
    known_sections = {
        "version", "mode", "storage", "llm", "context", "activation",
        "search", "escalation", "memory", "mcp", "budget", "agents",
        "logging", "planning", "soar", "spawner", "proactive_health_checks",
        "early_detection",
    }
    unknown = set(config.keys()) - known_sections
    if unknown:
        errors.append(f"Unknown top-level config sections: {sorted(unknown)}")

    # -- storage --
    storage = config.get("storage", {})
    if not isinstance(storage, dict):
        errors.append("storage must be a dict")
    else:
        if "type" in storage and storage["type"] not in ("sqlite",):
            errors.append(f"storage.type must be 'sqlite', got '{storage['type']}'")
        if "max_connections" in storage:
            val = storage["max_connections"]
            if not isinstance(val, int) or val < 1:
                errors.append(f"storage.max_connections must be a positive integer, got {val}")
        if "timeout_seconds" in storage:
            val = storage["timeout_seconds"]
            if not isinstance(val, (int, float)) or val <= 0:
                errors.append(f"storage.timeout_seconds must be positive, got {val}")

    # -- llm --
    llm = config.get("llm", {})
    if not isinstance(llm, dict):
        errors.append("llm must be a dict")
    else:
        if "provider" in llm and llm["provider"] != "anthropic":
            errors.append(f"llm.provider must be 'anthropic', got '{llm['provider']}'")
        temp = llm.get("temperature", 0.7)
        if not isinstance(temp, (int, float)) or not 0.0 <= temp <= 2.0:
            errors.append(f"llm.temperature must be 0.0-2.0, got {temp}")
        if "max_tokens" in llm:
            val = llm["max_tokens"]
            if not isinstance(val, int) or val < 1:
                errors.append(f"llm.max_tokens must be a positive integer, got {val}")
        if "timeout_seconds" in llm:
            val = llm["timeout_seconds"]
            if not isinstance(val, (int, float)) or val <= 0:
                errors.append(f"llm.timeout_seconds must be positive, got {val}")

    # -- escalation --
    escalation = config.get("escalation", {})
    if not isinstance(escalation, dict):
        errors.append("escalation must be a dict")
    else:
        threshold = escalation.get("threshold", 0.7)
        if not isinstance(threshold, (int, float)) or not 0.0 <= threshold <= 1.0:
            errors.append(f"escalation.threshold must be 0.0-1.0, got {threshold}")
        if "force_mode" in escalation and escalation["force_mode"] is not None:
            if escalation["force_mode"] not in ("direct", "aurora"):
                errors.append(
                    f"escalation.force_mode must be 'direct', 'aurora', or null, "
                    f"got '{escalation['force_mode']}'"
                )

    # -- logging --
    log = config.get("logging", {})
    if not isinstance(log, dict):
        errors.append("logging must be a dict")
    else:
        level = log.get("level", "INFO")
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if level not in valid_levels:
            errors.append(f"logging.level must be one of {valid_levels}, got '{level}'")
        if "max_size_mb" in log:
            val = log["max_size_mb"]
            if not isinstance(val, (int, float)) or val <= 0:
                errors.append(f"logging.max_size_mb must be positive, got {val}")
        if "max_files" in log:
            val = log["max_files"]
            if not isinstance(val, int) or val < 1:
                errors.append(f"logging.max_files must be a positive integer, got {val}")

    # -- search --
    search = config.get("search", {})
    if not isinstance(search, dict):
        errors.append("search must be a dict")
    else:
        score = search.get("min_semantic_score", 0.7)
        if not isinstance(score, (int, float)) or not 0.0 <= score <= 1.0:
            errors.append(f"search.min_semantic_score must be 0.0-1.0, got {score}")

    # -- budget --
    budget = config.get("budget", {})
    if not isinstance(budget, dict):
        errors.append("budget must be a dict")
    else:
        if "limit" in budget:
            val = budget["limit"]
            if not isinstance(val, (int, float)) or val < 0:
                errors.append(f"budget.limit must be non-negative, got {val}")

    # -- soar --
    soar = config.get("soar", {})
    if not isinstance(soar, dict):
        errors.append("soar must be a dict")
    else:
        if "default_model" in soar:
            if soar["default_model"] not in ("sonnet", "opus"):
                errors.append(
                    f"soar.default_model must be 'sonnet' or 'opus', got '{soar['default_model']}'"
                )

    # -- spawner --
    spawner = config.get("spawner", {})
    if not isinstance(spawner, dict):
        errors.append("spawner must be a dict")
    else:
        if "max_concurrent" in spawner:
            val = spawner["max_concurrent"]
            if not isinstance(val, int) or val < 1:
                errors.append(f"spawner.max_concurrent must be a positive integer, got {val}")
        if "stagger_delay" in spawner:
            val = spawner["stagger_delay"]
            if not isinstance(val, (int, float)) or val < 0:
                errors.append(f"spawner.stagger_delay must be non-negative, got {val}")

    # -- memory --
    memory = config.get("memory", {})
    if not isinstance(memory, dict):
        errors.append("memory must be a dict")
    else:
        if "chunk_size" in memory:
            val = memory["chunk_size"]
            if not isinstance(val, int) or val < 100:
                errors.append(f"memory.chunk_size must be >= 100, got {val}")
        if "overlap" in memory:
            val = memory["overlap"]
            if not isinstance(val, int) or val < 0:
                errors.append(f"memory.overlap must be >= 0, got {val}")

    # -- mcp --
    mcp = config.get("mcp", {})
    if not isinstance(mcp, dict):
        errors.append("mcp must be a dict")
    else:
        if "max_results" in mcp:
            val = mcp["max_results"]
            if not isinstance(val, int) or val < 1:
                errors.append(f"mcp.max_results must be a positive integer, got {val}")

    # -- agents --
    agents = config.get("agents", {})
    if not isinstance(agents, dict):
        errors.append("agents must be a dict")
    else:
        if "refresh_interval_days" in agents:
            val = agents["refresh_interval_days"]
            if not isinstance(val, int) or val < 1:
                errors.append(f"agents.refresh_interval_days must be a positive integer, got {val}")
        if "fallback_mode" in agents:
            if agents["fallback_mode"] not in ("llm_only", "tool_only", "hybrid"):
                errors.append(
                    f"agents.fallback_mode must be 'llm_only', 'tool_only', or 'hybrid', "
                    f"got '{agents['fallback_mode']}'"
                )

    # -- context.code.hybrid_weights --
    context = config.get("context", {})
    if isinstance(context, dict):
        code = context.get("code", {})
        if isinstance(code, dict):
            weights = code.get("hybrid_weights", {})
            if isinstance(weights, dict):
                for wkey in ("activation", "semantic"):
                    if wkey in weights:
                        val = weights[wkey]
                        if not isinstance(val, (int, float)) or not 0.0 <= val <= 1.0:
                            errors.append(
                                f"context.code.hybrid_weights.{wkey} must be 0.0-1.0, got {val}"
                            )
                if "top_k" in weights:
                    val = weights["top_k"]
                    if not isinstance(val, int) or val < 1:
                        errors.append(
                            f"context.code.hybrid_weights.top_k must be a positive integer, got {val}"
                        )
            if "max_file_size_kb" in code:
                val = code["max_file_size_kb"]
                if not isinstance(val, (int, float)) or val <= 0:
                    errors.append(f"context.code.max_file_size_kb must be positive, got {val}")

    # -- proactive_health_checks --
    phc = config.get("proactive_health_checks", {})
    if not isinstance(phc, dict):
        errors.append("proactive_health_checks must be a dict")
    else:
        for key in ("check_interval", "no_output_threshold"):
            if key in phc:
                val = phc[key]
                if not isinstance(val, (int, float)) or val <= 0:
                    errors.append(f"proactive_health_checks.{key} must be positive, got {val}")
        if "failure_threshold" in phc:
            val = phc["failure_threshold"]
            if not isinstance(val, int) or val < 1:
                errors.append(
                    f"proactive_health_checks.failure_threshold must be a positive integer, got {val}"
                )

    # -- early_detection --
    ed = config.get("early_detection", {})
    if not isinstance(ed, dict):
        errors.append("early_detection must be a dict")
    else:
        for key in ("check_interval", "stall_threshold"):
            if key in ed:
                val = ed[key]
                if not isinstance(val, (int, float)) or val <= 0:
                    errors.append(f"early_detection.{key} must be positive, got {val}")
        if "min_output_bytes" in ed:
            val = ed["min_output_bytes"]
            if not isinstance(val, int) or val < 0:
                errors.append(f"early_detection.min_output_bytes must be non-negative, got {val}")
        if "memory_limit_mb" in ed and ed["memory_limit_mb"] is not None:
            val = ed["memory_limit_mb"]
            if not isinstance(val, (int, float)) or val <= 0:
                errors.append(f"early_detection.memory_limit_mb must be positive, got {val}")

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
