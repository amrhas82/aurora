"""
Configuration loading and validation for AURORA.

Implements:
- Config class with typed access methods
- Override hierarchy: CLI > env > project > global > defaults
- Environment variable mapping (AURORA_* → config keys)
- Path expansion (~ and relative paths)
- JSON schema validation
- Secrets handling (API keys from env vars only)
"""

import json
import os
from copy import deepcopy
from pathlib import Path
from typing import Any, cast

import jsonschema

from aurora_core.config.schema import get_schema
from aurora_core.exceptions import ConfigurationError

# Environment variable to config key mapping
ENV_VAR_MAPPING = {
    "AURORA_STORAGE_PATH": "storage.path",
    "AURORA_STORAGE_TYPE": "storage.type",
    "AURORA_LLM_PROVIDER": "llm.reasoning_provider",
    "AURORA_LLM_MODEL": "llm.reasoning_model",
    "AURORA_API_KEY": "llm.api_key_env",
    "AURORA_LOG_LEVEL": "logging.level",
    "AURORA_LOG_PATH": "logging.path",
}


class Config:
    """
    Typed configuration access with validation.

    Provides:
    - Dot-notation access to nested config values
    - Type-safe accessor methods
    - Path expansion and validation
    - Schema-based validation
    """

    def __init__(self, data: dict[str, Any]) -> None:
        """
        Initialize configuration with validated data.

        Args:
            data: Configuration dictionary (already validated)
        """
        self._data = data

    @staticmethod
    def load(
        project_path: Path | None = None, cli_overrides: dict[str, Any] | None = None
    ) -> "Config":
        """
        Load configuration with override hierarchy.

        Override precedence (highest to lowest):
        1. CLI flags (cli_overrides parameter)
        2. Environment variables (AURORA_*)
        3. Project config (<project>/.aurora/config.json)
        4. Global config (~/.aurora/config.json)
        5. Package defaults (defaults.json)

        Args:
            project_path: Project directory to search for .aurora/config.json
            cli_overrides: CLI flag overrides (dot notation keys)

        Returns:
            Validated Config instance

        Raises:
            ConfigurationError: If configuration is invalid or cannot be loaded
        """
        # 1. Start with package defaults
        config = Config._load_defaults()

        # 2. Merge global config
        try:
            global_config_path = Path.home() / ".aurora" / "config.json"
            if global_config_path.exists():
                global_config = Config._load_json_file(global_config_path)
                config = Config._deep_merge(config, global_config)
        except (RuntimeError, OSError):
            # Path.home() might fail in tests or restricted environments
            pass

        # 3. Merge project config
        if project_path:
            project_config_path = project_path / ".aurora" / "config.json"
            if project_config_path.exists():
                project_config = Config._load_json_file(project_config_path)
                config = Config._deep_merge(config, project_config)

        # 4. Merge environment variables
        env_overrides = Config._load_env_vars()
        config = Config._merge_overrides(config, env_overrides)

        # 5. Merge CLI overrides
        if cli_overrides:
            config = Config._merge_overrides(config, cli_overrides)

        # 6. Validate against schema
        Config._validate_schema(config)

        # 7. Check for forbidden fields (API keys in config)
        Config._check_secrets(config)

        # 8. Expand paths
        config = Config._expand_paths(config, project_path)

        return Config(config)

    def get(self, key: str, default: Any = None) -> Any:
        """
        Get configuration value by dot-notation key.

        Args:
            key: Dot-notation key (e.g., 'storage.path')
            default: Default value if key not found

        Returns:
            Configuration value or default
        """
        keys = key.split(".")
        value = self._data

        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default

        return value

    def storage_path(self) -> Path:
        """
        Get storage path (expanded to absolute).

        Returns:
            Absolute path to storage file
        """
        path = self.get("storage.path")
        if path is None:
            raise ConfigurationError("storage.path not configured")
        return Path(path)

    def llm_config(self) -> dict[str, Any]:
        """
        Get complete LLM configuration.

        Returns:
            Dictionary with LLM settings
        """
        llm_config = self.get("llm", {})
        if not llm_config:
            raise ConfigurationError("llm configuration not found")
        return cast(dict[str, Any], llm_config)

    def validate(self) -> bool:
        """
        Validate configuration against schema.

        Returns:
            True if valid

        Raises:
            ConfigurationError: If configuration is invalid
        """
        Config._validate_schema(self._data)
        return True

    @staticmethod
    def _load_defaults() -> dict[str, Any]:
        """Load default configuration from package."""
        defaults_path = Path(__file__).parent / "defaults.json"
        return Config._load_json_file(defaults_path)

    @staticmethod
    def _load_json_file(path: Path) -> dict[str, Any]:
        """
        Load and parse JSON configuration file.

        Args:
            path: Path to JSON file

        Returns:
            Parsed configuration dictionary

        Raises:
            ConfigurationError: If file cannot be loaded or parsed
        """
        try:
            with open(path) as f:
                return cast(dict[str, Any], json.load(f))
        except json.JSONDecodeError as e:
            raise ConfigurationError(f"Failed to parse JSON configuration at {path}: {e}")
        except OSError as e:
            raise ConfigurationError(f"Failed to read configuration file at {path}: {e}")

    @staticmethod
    def _load_env_vars() -> dict[str, Any]:
        """
        Load configuration overrides from environment variables.

        Returns:
            Dictionary with dot-notation keys from AURORA_* env vars
        """
        overrides = {}
        for env_var, config_key in ENV_VAR_MAPPING.items():
            value = os.environ.get(env_var)
            if value is not None:
                overrides[config_key] = value
        return overrides

    @staticmethod
    def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
        """
        Deep merge two configuration dictionaries.

        Args:
            base: Base configuration
            override: Configuration to merge (takes precedence)

        Returns:
            Merged configuration
        """
        result = deepcopy(base)

        for key, value in override.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = Config._deep_merge(result[key], value)
            else:
                result[key] = deepcopy(value)

        return result

    @staticmethod
    def _merge_overrides(base: dict[str, Any], overrides: dict[str, Any]) -> dict[str, Any]:
        """
        Merge dot-notation overrides into configuration.

        Args:
            base: Base configuration
            overrides: Overrides with dot-notation keys

        Returns:
            Merged configuration
        """
        result = deepcopy(base)

        for key, value in overrides.items():
            keys = key.split(".")
            target = result

            # Navigate to parent
            for k in keys[:-1]:
                if k not in target:
                    target[k] = {}
                target = target[k]

            # Set value
            target[keys[-1]] = value

        return result

    @staticmethod
    def _validate_schema(config: dict[str, Any]) -> None:
        """
        Validate configuration against JSON schema.

        Args:
            config: Configuration to validate

        Raises:
            ConfigurationError: If validation fails
        """
        schema = get_schema()

        try:
            jsonschema.validate(config, schema)
        except jsonschema.ValidationError as e:
            # Extract useful error information
            path = " → ".join(str(p) for p in e.path) if e.path else "root"
            raise ConfigurationError(f"Configuration validation failed at '{path}': {e.message}")
        except jsonschema.SchemaError as e:
            raise ConfigurationError(f"Invalid configuration schema: {e.message}")

    @staticmethod
    def _check_secrets(config: dict[str, Any]) -> None:
        """
        Check that no secrets are directly in configuration.

        Args:
            config: Configuration to check

        Raises:
            ConfigurationError: If API keys or secrets found in config
        """
        # Check for forbidden 'api_key' field in llm config
        if "llm" in config and isinstance(config["llm"], dict):
            if "api_key" in config["llm"]:
                raise ConfigurationError(
                    "API keys must not be stored in configuration files. "
                    "Use 'api_key_env' to specify an environment variable name instead."
                )

    @staticmethod
    def _expand_paths(config: dict[str, Any], project_path: Path | None = None) -> dict[str, Any]:
        """
        Expand paths in configuration (~ and relative paths).

        Args:
            config: Configuration with paths to expand
            project_path: Project directory for relative path resolution

        Returns:
            Configuration with expanded paths
        """
        result = deepcopy(config)

        # Expand storage path
        if "storage" in result and "path" in result["storage"]:
            path = result["storage"]["path"]
            path = Config._expand_path(path, project_path)
            result["storage"]["path"] = str(path)

        # Expand logging path
        if "logging" in result and "path" in result["logging"]:
            path = result["logging"]["path"]
            path = Config._expand_path(path, project_path)
            result["logging"]["path"] = str(path)

        # Expand agent discovery paths
        if "agents" in result and "discovery_paths" in result["agents"]:
            expanded = []
            for path in result["agents"]["discovery_paths"]:
                expanded.append(str(Config._expand_path(path, project_path)))
            result["agents"]["discovery_paths"] = expanded

        return result

    @staticmethod
    def _expand_path(path: str, project_path: Path | None = None) -> Path:
        """
        Expand a single path (tilde and relative).

        Args:
            path: Path string to expand
            project_path: Project directory for relative path resolution

        Returns:
            Expanded absolute path
        """
        p = Path(path)

        # Expand tilde
        if str(p).startswith("~"):
            p = p.expanduser()

        # Convert relative to absolute
        if not p.is_absolute():
            p = project_path / p if project_path else Path.cwd() / p

        return p.resolve()
