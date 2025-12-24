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
    logging_file: str = "~/.aurora/aurora.log"
    mcp_always_on: bool = False
    mcp_log_file: str = "~/.aurora/mcp.log"
    mcp_max_results: int = 10

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
            raise ConfigurationError(
                f"llm_provider must be 'anthropic', got '{self.llm_provider}'"
            )

        # Validate force mode if set
        if self.escalation_force_mode is not None:
            if self.escalation_force_mode not in ["direct", "aurora"]:
                raise ConfigurationError(
                    f"escalation_force_mode must be 'direct' or 'aurora', got '{self.escalation_force_mode}'"
                )

        # Validate numeric ranges
        if self.llm_temperature < 0.0 or self.llm_temperature > 1.0:
            raise ConfigurationError(
                f"llm_temperature must be 0.0-1.0, got {self.llm_temperature}"
            )

        if self.llm_max_tokens < 1:
            raise ConfigurationError(
                f"llm_max_tokens must be positive, got {self.llm_max_tokens}"
            )

        if self.memory_chunk_size < 100:
            raise ConfigurationError(
                f"memory_chunk_size must be >= 100, got {self.memory_chunk_size}"
            )

        if self.memory_overlap < 0:
            raise ConfigurationError(
                f"memory_overlap must be >= 0, got {self.memory_overlap}"
            )

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

        # Warn about non-existent paths (don't fail, just warn)
        for path in self.memory_index_paths:
            expanded_path = Path(path).expanduser()
            if not expanded_path.exists():
                print(f"Warning: Path '{path}' does not exist")


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
        "file": "~/.aurora/aurora.log",
    },
    "mcp": {
        "always_on": False,
        "log_file": "~/.aurora/mcp.log",
        "max_results": 10,
    },
}


def load_config(path: str | None = None) -> Config:
    """Load configuration from file with environment variable overrides.

    Search order (if path not provided):
    1. Current directory: ./aurora.config.json
    2. Home directory: ~/.aurora/config.json
    3. Use built-in defaults

    Environment variables take precedence over file values:
    - ANTHROPIC_API_KEY → anthropic_api_key
    - AURORA_ESCALATION_THRESHOLD → escalation_threshold
    - AURORA_LOGGING_LEVEL → logging_level

    Args:
        path: Optional explicit path to config file

    Returns:
        Config instance with loaded values

    Raises:
        ConfigurationError: If config file has invalid syntax or values
    """
    config_data: dict[str, Any] = {}
    config_source = "defaults"

    # Search for config file if path not provided
    if path is None:
        search_paths = [
            Path("./aurora.config.json"),
            Path.home() / ".aurora" / "config.json",
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
                with open(config_path, "r") as f:
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
        "logging_level": config_data.get("logging", {}).get(
            "level", defaults["logging"]["level"]
        ),
        "logging_file": config_data.get("logging", {}).get("file", defaults["logging"]["file"]),
        "mcp_always_on": config_data.get("mcp", {}).get(
            "always_on", defaults["mcp"]["always_on"]
        ),
        "mcp_log_file": config_data.get("mcp", {}).get("log_file", defaults["mcp"]["log_file"]),
        "mcp_max_results": config_data.get("mcp", {}).get(
            "max_results", defaults["mcp"]["max_results"]
        ),
    }

    # Apply environment variable overrides
    if "ANTHROPIC_API_KEY" in os.environ:
        flat_config["anthropic_api_key"] = os.environ["ANTHROPIC_API_KEY"]

    if "AURORA_ESCALATION_THRESHOLD" in os.environ:
        try:
            flat_config["escalation_threshold"] = float(
                os.environ["AURORA_ESCALATION_THRESHOLD"]
            )
        except ValueError:
            raise ConfigurationError(
                f"AURORA_ESCALATION_THRESHOLD must be a number, got '{os.environ['AURORA_ESCALATION_THRESHOLD']}'"
            )

    if "AURORA_LOGGING_LEVEL" in os.environ:
        flat_config["logging_level"] = os.environ["AURORA_LOGGING_LEVEL"].upper()

    # Create Config instance
    config = Config(**flat_config)

    # Validate configuration
    config.validate()

    # Log which config source was used
    print(f"Configuration loaded from: {config_source}")

    return config
