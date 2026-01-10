"""Configuration management for AURORA CLI.

This module provides configuration loading, validation, and management with support for:
- Config file (~/.aurora/config.json or ./aurora.config.json)
- Environment variable overrides
- Validation with helpful error messages
- Secure API key handling
"""

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from aurora_cli.errors import ConfigurationError, ErrorHandler

# List of all 20 AI coding tools supported by Aurora slash command configurators.
# Each tool has:
#   - name: Human-readable display name
#   - value: Tool ID matching SlashCommandRegistry
#   - available: Always True (all tools are always available per PRD)
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


@dataclass
class Config:
    """AURORA CLI configuration.

    Configuration precedence (highest to lowest):
    1. Environment variables
    2. Config file values
    3. Default values
    """

    version: str = "1.1.0"
    llm_provider: str = "anthropic"
    anthropic_api_key: str | None = None
    llm_model: str = "claude-3-5-sonnet-20241022"
    llm_temperature: float = 0.7
    llm_max_tokens: int = 4096
    escalation_threshold: float = 0.7
    escalation_enable_keyword_only: bool = False
    escalation_force_mode: str | None = None  # "direct" or "aurora"
    memory_auto_index: bool = True
    memory_index_paths: list[str] = field(default_factory=lambda: ["."])
    memory_chunk_size: int = 1000
    memory_overlap: int = 200
    logging_level: str = "INFO"
    logging_file: str = "./.aurora/logs/aurora.log"
    mcp_always_on: bool = False
    mcp_log_file: str = "./.aurora/logs/mcp.log"
    mcp_max_results: int = 10
    db_path: str = "./.aurora/memory.db"  # Database path - project-specific
    budget_limit: float = 10.0  # Default budget limit in USD
    budget_tracker_path: str = "~/.aurora/budget_tracker.json"  # ONLY global file
    search_min_semantic_score: float = (
        0.70  # Minimum semantic score threshold (0.7 = cosine similarity > 0.4)
    )
    # Agent discovery configuration
    agents_auto_refresh: bool = True
    agents_refresh_interval_hours: int = 24
    agents_discovery_paths: list[str] = field(
        default_factory=lambda: [
            "~/.claude/agents",
            "~/.config/ampcode/agents",
            "~/.config/droid/agent",
            "~/.config/opencode/agent",
        ]
    )
    agents_manifest_path: str = "./.aurora/cache/agent_manifest.json"
    # Planning configuration
    planning_base_dir: str = "./.aurora/plans"
    planning_template_dir: str | None = None  # None = use package default
    planning_auto_increment: bool = True
    planning_archive_on_complete: bool = False
    # SOAR configuration
    soar_default_tool: str = "claude"  # Default CLI tool for aur soar
    soar_default_model: str = "sonnet"  # Default model (sonnet or opus)

    def get_db_path(self) -> str:
        """Get expanded absolute database path.

        Expands ~ to home directory and returns absolute path.

        Returns:
            Absolute path to database file

        Example:
            >>> config = Config(db_path="~/.aurora/memory.db")
            >>> config.get_db_path()
            '/home/user/.aurora/memory.db'
        """
        return str(Path(self.db_path).expanduser().resolve())

    def get_manifest_path(self) -> str:
        """Get expanded absolute agent manifest path.

        Expands ~ to home directory and returns absolute path.

        Returns:
            Absolute path to agent manifest file

        Example:
            >>> config = Config(agents_manifest_path="~/.aurora/cache/agent_manifest.json")
            >>> config.get_manifest_path()
            '/home/user/.aurora/cache/agent_manifest.json'
        """
        return str(Path(self.agents_manifest_path).expanduser().resolve())

    def get_plans_path(self) -> str:
        """Get expanded absolute plans directory path.

        Expands ~ to home directory and returns absolute path.

        Returns:
            Absolute path to plans directory

        Example:
            >>> config = Config(planning_base_dir="~/.aurora/plans")
            >>> config.get_plans_path()
            '/home/user/.aurora/plans'
        """
        return str(Path(self.planning_base_dir).expanduser().resolve())

    def get_planning_base_dir(self) -> str:
        """Get expanded absolute planning base directory path.

        Expands ~ to home directory and returns absolute path.

        Returns:
            Absolute path to planning base directory

        Example:
            >>> config = Config(planning_base_dir="~/.aurora/plans")
            >>> config.get_planning_base_dir()
            '/home/user/.aurora/plans'
        """
        return str(Path(self.planning_base_dir).expanduser().resolve())

    def get_planning_template_dir(self) -> str | None:
        """Get expanded absolute planning template directory path.

        If planning_template_dir is None, returns None (indicating use package default).
        Otherwise expands ~ to home directory and returns absolute path.

        Returns:
            Absolute path to template directory or None for package default

        Example:
            >>> config = Config(planning_template_dir="~/.aurora/templates")
            >>> config.get_planning_template_dir()
            '/home/user/.aurora/templates'
        """
        if self.planning_template_dir is None:
            return None
        return str(Path(self.planning_template_dir).expanduser().resolve())

    def get_api_key(self) -> str:
        """Get API key with environment variable override.

        Returns:
            API key string

        Raises:
            ConfigurationError: If no API key found in environment or config
        """
        # Check environment variable first
        env_key = os.environ.get("ANTHROPIC_API_KEY")
        if env_key and env_key.strip():
            return env_key.strip()

        # Fall back to config file
        if self.anthropic_api_key and self.anthropic_api_key.strip():
            return self.anthropic_api_key.strip()

        # No key found - raise helpful error with formatted message
        error_handler = ErrorHandler()
        error_msg = error_handler.handle_config_error(
            Exception("API key not found"), config_path="~/.aurora/config.json"
        )
        raise ConfigurationError(error_msg)

    def validate(self) -> None:
        """Validate configuration values.

        Raises:
            ConfigurationError: If any configuration values are invalid
        """
        # Validate escalation threshold
        if not 0.0 <= self.escalation_threshold <= 1.0:
            raise ConfigurationError(
                f"escalation_threshold must be 0.0-1.0, got {self.escalation_threshold}"
            )

        # Validate provider
        if self.llm_provider != "anthropic":
            raise ConfigurationError(f"llm_provider must be 'anthropic', got '{self.llm_provider}'")

        # Validate force mode if set
        if self.escalation_force_mode is not None:
            if self.escalation_force_mode not in ["direct", "aurora"]:
                raise ConfigurationError(
                    f"escalation_force_mode must be 'direct' or 'aurora', got '{self.escalation_force_mode}'"
                )

        # Validate numeric ranges
        if self.llm_temperature < 0.0 or self.llm_temperature > 1.0:
            raise ConfigurationError(f"llm_temperature must be 0.0-1.0, got {self.llm_temperature}")

        if self.llm_max_tokens < 1:
            raise ConfigurationError(f"llm_max_tokens must be positive, got {self.llm_max_tokens}")

        if self.memory_chunk_size < 100:
            raise ConfigurationError(
                f"memory_chunk_size must be >= 100, got {self.memory_chunk_size}"
            )

        if self.memory_overlap < 0:
            raise ConfigurationError(f"memory_overlap must be >= 0, got {self.memory_overlap}")

        # Validate logging level
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if self.logging_level not in valid_levels:
            raise ConfigurationError(
                f"logging_level must be one of {valid_levels}, got '{self.logging_level}'"
            )

        # Validate MCP configuration
        if self.mcp_max_results < 1:
            raise ConfigurationError(
                f"mcp_max_results must be positive, got {self.mcp_max_results}"
            )

        # Validate database path (just check it's a valid path format)
        if not self.db_path or not self.db_path.strip():
            raise ConfigurationError("db_path cannot be empty")

        # Validate budget limit
        if self.budget_limit < 0:
            raise ConfigurationError(f"budget_limit must be non-negative, got {self.budget_limit}")

        # Validate search threshold
        if not 0.0 <= self.search_min_semantic_score <= 1.0:
            raise ConfigurationError(
                f"search_min_semantic_score must be 0.0-1.0, got {self.search_min_semantic_score}"
            )

        # Warn about non-existent paths (don't fail, just warn)
        for path in self.memory_index_paths:
            expanded_path = Path(path).expanduser()
            if not expanded_path.exists():
                print(f"Warning: Path '{path}' does not exist")

        # Validate agent discovery configuration
        if self.agents_refresh_interval_hours < 1:
            raise ConfigurationError(
                f"agents_refresh_interval_hours must be >= 1, got {self.agents_refresh_interval_hours}"
            )

        if not self.agents_manifest_path or not self.agents_manifest_path.strip():
            raise ConfigurationError("agents_manifest_path cannot be empty")

        # Validate planning configuration
        if not self.planning_base_dir or not self.planning_base_dir.strip():
            raise ConfigurationError("planning_base_dir cannot be empty")

        # Check if planning_base_dir is writable (parent must exist)
        base_dir_path = Path(self.planning_base_dir).expanduser()
        if base_dir_path.exists():
            # Directory exists, check if writable
            if not os.access(base_dir_path, os.W_OK):
                raise ConfigurationError(
                    f"planning_base_dir is not writable: {self.planning_base_dir}"
                )
        else:
            # Directory doesn't exist, check if parent is writable
            parent_dir = base_dir_path.parent
            if parent_dir.exists() and not os.access(parent_dir, os.W_OK):
                raise ConfigurationError(
                    f"Cannot create planning_base_dir (parent not writable): {self.planning_base_dir}"
                )


# Default configuration schema
CONFIG_SCHEMA: dict[str, Any] = {
    "version": "1.1.0",
    "llm": {
        "provider": "anthropic",
        "anthropic_api_key": None,
        "model": "claude-3-5-sonnet-20241022",
        "temperature": 0.7,
        "max_tokens": 4096,
    },
    "escalation": {
        "threshold": 0.7,
        "enable_keyword_only": False,
        "force_mode": None,
    },
    "memory": {
        "auto_index": True,
        "index_paths": ["."],
        "chunk_size": 1000,
        "overlap": 200,
    },
    "logging": {
        "level": "INFO",
        "file": "./.aurora/logs/aurora.log",
    },
    "mcp": {
        "always_on": False,
        "log_file": "./.aurora/logs/mcp.log",
        "max_results": 10,
    },
    "database": {
        "path": "./.aurora/memory.db",
    },
    "budget": {
        "limit": 10.0,
        "tracker_path": "~/.aurora/budget_tracker.json",
    },
    "search": {
        "min_semantic_score": 0.70,  # 0.7 = cosine similarity > 0.4 (moderate match)
    },
    "agents": {
        "auto_refresh": True,
        "refresh_interval_hours": 24,
        "discovery_paths": [
            "~/.claude/agents",
            "~/.config/ampcode/agents",
            "~/.config/droid/agent",
            "~/.config/opencode/agent",
        ],
        "manifest_path": "./.aurora/cache/agent_manifest.json",
    },
    "planning": {
        "base_dir": "./.aurora/plans",
        "template_dir": None,  # None = use package default
        "auto_increment": True,
        "archive_on_complete": False,
    },
    "soar": {
        "default_tool": "claude",  # CLI tool for aur soar (claude, cursor, etc.)
        "default_model": "sonnet",  # Model to use (sonnet or opus)
    },
}


def _get_aurora_home() -> Path:
    """Get Aurora home directory, respecting AURORA_HOME environment variable.

    Returns:
        Path to Aurora home directory (default: ~/.aurora)
    """
    import os

    aurora_home_env = os.environ.get("AURORA_HOME")
    if aurora_home_env:
        return Path(aurora_home_env)
    return Path.home() / ".aurora"


def load_config(path: str | None = None) -> Config:
    """Load configuration from file with environment variable overrides.

    Search order (if path not provided):
    1. Project mode (./.aurora exists): ./.aurora/config.json or built-in defaults
    2. Global mode: ./aurora.config.json or ~/.aurora/config.json
    3. Use built-in defaults

    **Project Isolation**: When ./.aurora directory exists, Aurora operates in
    "project mode" and uses project-local paths (./.aurora/*) for all artifacts
    except budget_tracker.json (which remains global). This ensures complete
    project isolation and prevents interference with global configuration.

    Environment variables take precedence over file values:
    - AURORA_HOME → config file location
    - ANTHROPIC_API_KEY → anthropic_api_key
    - AURORA_ESCALATION_THRESHOLD → escalation_threshold
    - AURORA_LOGGING_LEVEL → logging_level
    - AURORA_PLANS_DIR → planning_base_dir
    - AURORA_TEMPLATE_DIR → planning_template_dir
    - AURORA_PLANNING_AUTO_INCREMENT → planning_auto_increment (true/false)
    - AURORA_PLANNING_ARCHIVE_ON_COMPLETE → planning_archive_on_complete (true/false)

    Args:
        path: Optional explicit path to config file

    Returns:
        Config instance with loaded values

    Raises:
        ConfigurationError: If config file has invalid syntax or values
    """
    config_data: dict[str, Any] = {}
    config_source = "defaults"

    # Check if we're in a project (has ./.aurora directory)
    in_project = Path("./.aurora").exists()

    # Search for config file if path not provided
    if path is None:
        if in_project:
            # Project mode: only check project-local config
            search_paths = [
                Path("./.aurora/config.json"),
            ]
        else:
            # Global mode: check current dir then global
            search_paths = [
                Path("./aurora.config.json"),
                _get_aurora_home() / "config.json",
            ]

        for search_path in search_paths:
            if search_path.exists():
                path = str(search_path)
                break

    # Load config file if found
    if path is not None:
        config_path = Path(path).expanduser().resolve()
        if config_path.exists():
            error_handler = ErrorHandler()
            try:
                with open(config_path) as f:
                    config_data = json.load(f)
                config_source = str(config_path)
            except json.JSONDecodeError as e:
                error_msg = error_handler.handle_config_error(e, config_path=str(config_path))
                raise ConfigurationError(error_msg) from e
            except PermissionError as e:
                error_msg = error_handler.handle_config_error(e, config_path=str(config_path))
                raise ConfigurationError(error_msg) from e
            except Exception as e:
                # Catch any other file-related errors (disk full, etc.)
                error_msg = error_handler.handle_config_error(e, config_path=str(config_path))
                raise ConfigurationError(error_msg) from e

    # Start with defaults
    defaults = CONFIG_SCHEMA.copy()

    # Merge nested config structure into flat structure
    flat_config = {
        "version": config_data.get("version", defaults["version"]),
        "llm_provider": config_data.get("llm", {}).get("provider", defaults["llm"]["provider"]),
        "anthropic_api_key": config_data.get("llm", {}).get(
            "anthropic_api_key", defaults["llm"]["anthropic_api_key"]
        ),
        "llm_model": config_data.get("llm", {}).get("model", defaults["llm"]["model"]),
        "llm_temperature": config_data.get("llm", {}).get(
            "temperature", defaults["llm"]["temperature"]
        ),
        "llm_max_tokens": config_data.get("llm", {}).get(
            "max_tokens", defaults["llm"]["max_tokens"]
        ),
        "escalation_threshold": config_data.get("escalation", {}).get(
            "threshold", defaults["escalation"]["threshold"]
        ),
        "escalation_enable_keyword_only": config_data.get("escalation", {}).get(
            "enable_keyword_only", defaults["escalation"]["enable_keyword_only"]
        ),
        "escalation_force_mode": config_data.get("escalation", {}).get(
            "force_mode", defaults["escalation"]["force_mode"]
        ),
        "memory_auto_index": config_data.get("memory", {}).get(
            "auto_index", defaults["memory"]["auto_index"]
        ),
        "memory_index_paths": config_data.get("memory", {}).get(
            "index_paths", defaults["memory"]["index_paths"]
        ),
        "memory_chunk_size": config_data.get("memory", {}).get(
            "chunk_size", defaults["memory"]["chunk_size"]
        ),
        "memory_overlap": config_data.get("memory", {}).get(
            "overlap", defaults["memory"]["overlap"]
        ),
        "logging_level": config_data.get("logging", {}).get("level", defaults["logging"]["level"]),
        "logging_file": config_data.get("logging", {}).get("file", defaults["logging"]["file"]),
        "mcp_always_on": config_data.get("mcp", {}).get("always_on", defaults["mcp"]["always_on"]),
        "mcp_log_file": config_data.get("mcp", {}).get("log_file", defaults["mcp"]["log_file"]),
        "mcp_max_results": config_data.get("mcp", {}).get(
            "max_results", defaults["mcp"]["max_results"]
        ),
        "db_path": config_data.get("database", {}).get("path", defaults["database"]["path"]),
        "budget_limit": config_data.get("budget", {}).get("limit", defaults["budget"]["limit"]),
        "budget_tracker_path": config_data.get("budget", {}).get(
            "tracker_path", defaults["budget"]["tracker_path"]
        ),
        "search_min_semantic_score": config_data.get("search", {}).get(
            "min_semantic_score", defaults["search"]["min_semantic_score"]
        ),
        # Agent discovery settings
        "agents_auto_refresh": config_data.get("agents", {}).get(
            "auto_refresh", defaults["agents"]["auto_refresh"]
        ),
        "agents_refresh_interval_hours": config_data.get("agents", {}).get(
            "refresh_interval_hours", defaults["agents"]["refresh_interval_hours"]
        ),
        "agents_discovery_paths": config_data.get("agents", {}).get(
            "discovery_paths", defaults["agents"]["discovery_paths"]
        ),
        "agents_manifest_path": config_data.get("agents", {}).get(
            "manifest_path", defaults["agents"]["manifest_path"]
        ),
        # Planning configuration
        "planning_base_dir": config_data.get("planning", {}).get(
            "base_dir", defaults["planning"]["base_dir"]
        ),
        "planning_template_dir": config_data.get("planning", {}).get(
            "template_dir", defaults["planning"]["template_dir"]
        ),
        "planning_auto_increment": config_data.get("planning", {}).get(
            "auto_increment", defaults["planning"]["auto_increment"]
        ),
        "planning_archive_on_complete": config_data.get("planning", {}).get(
            "archive_on_complete", defaults["planning"]["archive_on_complete"]
        ),
        # SOAR configuration
        "soar_default_tool": config_data.get("soar", {}).get(
            "default_tool", defaults["soar"]["default_tool"]
        ),
        "soar_default_model": config_data.get("soar", {}).get(
            "default_model", defaults["soar"]["default_model"]
        ),
    }

    # Apply environment variable overrides
    if "ANTHROPIC_API_KEY" in os.environ:
        flat_config["anthropic_api_key"] = os.environ["ANTHROPIC_API_KEY"]

    if "AURORA_ESCALATION_THRESHOLD" in os.environ:
        try:
            flat_config["escalation_threshold"] = float(os.environ["AURORA_ESCALATION_THRESHOLD"])
        except ValueError:
            raise ConfigurationError(
                f"AURORA_ESCALATION_THRESHOLD must be a number, got '{os.environ['AURORA_ESCALATION_THRESHOLD']}'"
            )

    if "AURORA_LOGGING_LEVEL" in os.environ:
        flat_config["logging_level"] = os.environ["AURORA_LOGGING_LEVEL"].upper()

    # Apply planning environment variable overrides
    if "AURORA_PLANS_DIR" in os.environ:
        flat_config["planning_base_dir"] = os.environ["AURORA_PLANS_DIR"]

    if "AURORA_TEMPLATE_DIR" in os.environ:
        flat_config["planning_template_dir"] = os.environ["AURORA_TEMPLATE_DIR"]

    if "AURORA_PLANNING_AUTO_INCREMENT" in os.environ:
        val = os.environ["AURORA_PLANNING_AUTO_INCREMENT"].lower()
        if val in ("true", "1", "yes"):
            flat_config["planning_auto_increment"] = True
        elif val in ("false", "0", "no"):
            flat_config["planning_auto_increment"] = False
        else:
            raise ConfigurationError(
                f"AURORA_PLANNING_AUTO_INCREMENT must be true/false, got '{os.environ['AURORA_PLANNING_AUTO_INCREMENT']}'"
            )

    if "AURORA_PLANNING_ARCHIVE_ON_COMPLETE" in os.environ:
        val = os.environ["AURORA_PLANNING_ARCHIVE_ON_COMPLETE"].lower()
        if val in ("true", "1", "yes"):
            flat_config["planning_archive_on_complete"] = True
        elif val in ("false", "0", "no"):
            flat_config["planning_archive_on_complete"] = False
        else:
            raise ConfigurationError(
                f"AURORA_PLANNING_ARCHIVE_ON_COMPLETE must be true/false, got '{os.environ['AURORA_PLANNING_ARCHIVE_ON_COMPLETE']}'"
            )

    # Apply SOAR environment variable overrides
    if "AURORA_SOAR_TOOL" in os.environ:
        flat_config["soar_default_tool"] = os.environ["AURORA_SOAR_TOOL"]

    if "AURORA_SOAR_MODEL" in os.environ:
        val = os.environ["AURORA_SOAR_MODEL"].lower()
        if val in ("sonnet", "opus"):
            flat_config["soar_default_model"] = val
        else:
            raise ConfigurationError(
                f"AURORA_SOAR_MODEL must be 'sonnet' or 'opus', got '{os.environ['AURORA_SOAR_MODEL']}'"
            )

    # Create Config instance
    config = Config(**flat_config)

    # Validate configuration
    config.validate()

    # Note: We don't print config source to avoid contaminating stdout
    # (especially important for JSON output mode in CLI commands)

    return config


def save_config(config: Config, path: str | None = None) -> None:
    """Save configuration to file.

    Args:
        config: Config instance to save
        path: Optional explicit path to config file (defaults to $AURORA_HOME/config.json or ~/.aurora/config.json)

    Raises:
        ConfigurationError: If cannot write to config file
    """
    if path is None:
        path = str(_get_aurora_home() / "config.json")

    config_path = Path(path).expanduser().resolve()

    # Convert Config dataclass to nested dict structure
    config_dict: dict[str, Any] = {
        "version": config.version,
        "llm": {
            "provider": config.llm_provider,
            "model": config.llm_model,
            "temperature": config.llm_temperature,
            "max_tokens": config.llm_max_tokens,
        },
        "escalation": {
            "threshold": config.escalation_threshold,
            "enable_keyword_only": config.escalation_enable_keyword_only,
            "force_mode": config.escalation_force_mode,
        },
        "memory": {
            "auto_index": config.memory_auto_index,
            "index_paths": config.memory_index_paths,
            "chunk_size": config.memory_chunk_size,
            "overlap": config.memory_overlap,
        },
        "logging": {
            "level": config.logging_level,
            "file": config.logging_file,
        },
        "mcp": {
            "always_on": config.mcp_always_on,
            "log_file": config.mcp_log_file,
            "max_results": config.mcp_max_results,
        },
        "database": {
            "path": config.db_path,
        },
        "budget": {
            "limit": config.budget_limit,
            "tracker_path": config.budget_tracker_path,
        },
        "search": {
            "min_semantic_score": config.search_min_semantic_score,
        },
        "agents": {
            "auto_refresh": config.agents_auto_refresh,
            "refresh_interval_hours": config.agents_refresh_interval_hours,
            "discovery_paths": config.agents_discovery_paths,
            "manifest_path": config.agents_manifest_path,
        },
        "planning": {
            "base_dir": config.planning_base_dir,
            "template_dir": config.planning_template_dir,
            "auto_increment": config.planning_auto_increment,
            "archive_on_complete": config.planning_archive_on_complete,
        },
        "soar": {
            "default_tool": config.soar_default_tool,
            "default_model": config.soar_default_model,
        },
    }

    # Only include API key if it's explicitly set in config (not just from env)
    if config.anthropic_api_key and config.anthropic_api_key != os.environ.get("ANTHROPIC_API_KEY"):
        config_dict["llm"]["anthropic_api_key"] = config.anthropic_api_key

    # Ensure directory exists
    config_path.parent.mkdir(parents=True, exist_ok=True)

    # Write config file
    try:
        with open(config_path, "w") as f:
            json.dump(config_dict, f, indent=2)
    except Exception as e:
        error_handler = ErrorHandler()
        error_msg = error_handler.handle_config_error(e, config_path=str(config_path))
        raise ConfigurationError(error_msg) from e
