"""
Integration tests for configuration system.

Tests end-to-end configuration loading scenarios including:
- Integration with other components (Store, Context, Agent Registry)
- Real file system operations
- Configuration lifecycle
- Multi-environment scenarios
"""

import json
import os
from pathlib import Path

import pytest
from aurora_core.config.loader import Config
from aurora_core.exceptions import ConfigurationError


class TestConfigurationIntegration:
    """Test configuration integration with full system."""

    def test_full_config_load_workflow(self, tmp_path: Path) -> None:
        """Test complete configuration loading workflow."""
        # 1. Create project structure
        project_dir = tmp_path / "test_project"
        project_dir.mkdir()

        # 2. Create project config
        project_config = project_dir / ".aurora" / "config.json"
        project_config.parent.mkdir(parents=True)
        project_config.write_text(
            json.dumps(
                {
                    "storage": {"type": "sqlite", "path": ".aurora/memory.db"},
                    "logging": {"level": "DEBUG"},
                }
            )
        )

        # 3. Load config
        config = Config.load(project_path=project_dir)

        # 4. Verify merged configuration
        assert config.get("version") == "1.1.0"  # From global config or defaults
        assert config.get("storage.type") == "sqlite"  # From project
        assert config.get("logging.level") == "DEBUG"  # From project

        # 5. Verify path expansion works
        storage_path = config.storage_path()
        assert storage_path.is_absolute()
        assert storage_path.parent.exists() or storage_path.parent == project_dir / ".aurora"

    def test_multi_file_configuration(self, tmp_path: Path, monkeypatch) -> None:
        """Test loading configuration from multiple files."""
        # Setup home directory mock
        home_dir = tmp_path / "home"
        home_dir.mkdir()

        def mock_home():
            return home_dir

        monkeypatch.setattr("pathlib.Path.home", mock_home)

        # Create global config
        global_config = home_dir / ".aurora" / "config.json"
        global_config.parent.mkdir(parents=True)
        global_config.write_text(
            json.dumps(
                {
                    "llm": {
                        "reasoning_provider": "openai",
                        "reasoning_model": "gpt-4",
                        "api_key_env": "OPENAI_API_KEY",
                    }
                }
            )
        )

        # Create project config
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        project_config = project_dir / ".aurora" / "config.json"
        project_config.parent.mkdir(parents=True)
        project_config.write_text(json.dumps({"storage": {"path": "/tmp/project.db"}}))

        # Load config
        config = Config.load(project_path=project_dir)

        # Verify merge from both files
        assert config.get("llm.reasoning_provider") == "openai"  # From global
        assert config.get("storage.path") == "/tmp/project.db"  # From project
        assert config.get("version") == "1.1.0"  # From defaults

    def test_environment_override_integration(self, tmp_path: Path, monkeypatch) -> None:
        """Test environment variables override file configuration."""
        # Set environment variables
        monkeypatch.setenv("AURORA_STORAGE_PATH", "/env/override.db")
        monkeypatch.setenv("AURORA_LOG_LEVEL", "ERROR")

        # Create project config with different values
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        project_config = project_dir / ".aurora" / "config.json"
        project_config.parent.mkdir(parents=True)
        project_config.write_text(
            json.dumps({"storage": {"path": "/project/config.db"}, "logging": {"level": "DEBUG"}})
        )

        # Load config
        config = Config.load(project_path=project_dir)

        # Environment should win
        assert config.get("storage.path") == "/env/override.db"
        assert config.get("logging.level") == "ERROR"

    def test_cli_override_has_highest_priority(self, tmp_path: Path, monkeypatch) -> None:
        """Test CLI overrides have highest priority over all other sources."""
        # Set environment variable
        monkeypatch.setenv("AURORA_STORAGE_PATH", "/env/path.db")

        # Create project config
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        project_config = project_dir / ".aurora" / "config.json"
        project_config.parent.mkdir(parents=True)
        project_config.write_text(json.dumps({"storage": {"path": "/project/path.db"}}))

        # Load with CLI override
        cli_overrides = {"storage.path": "/cli/path.db"}
        config = Config.load(project_path=project_dir, cli_overrides=cli_overrides)

        # CLI should win
        assert config.get("storage.path") == "/cli/path.db"

    def test_config_with_real_paths(self, tmp_path: Path) -> None:
        """Test configuration with real filesystem paths."""
        # Create actual directories
        project_dir = tmp_path / "project"
        project_dir.mkdir()

        storage_dir = project_dir / ".aurora"
        storage_dir.mkdir()

        logs_dir = project_dir / ".aurora" / "logs"
        logs_dir.mkdir()

        # Create config with relative paths
        project_config = project_dir / ".aurora" / "config.json"
        project_config.write_text(
            json.dumps(
                {
                    "storage": {"type": "sqlite", "path": ".aurora/memory.db"},
                    "logging": {"path": ".aurora/logs/"},
                }
            )
        )

        # Load config
        config = Config.load(project_path=project_dir)

        # Verify paths are expanded and absolute
        storage_path = config.storage_path()
        assert storage_path.is_absolute()
        assert storage_path.parent.exists()

        log_path = Path(config.get("logging.path"))
        assert log_path.is_absolute()
        assert log_path.exists()

    def test_invalid_config_fails_gracefully(self, tmp_path: Path) -> None:
        """Test invalid configuration provides clear error messages."""
        project_dir = tmp_path / "project"
        project_dir.mkdir()

        # Create invalid config
        project_config = project_dir / ".aurora" / "config.json"
        project_config.parent.mkdir(parents=True)
        project_config.write_text(
            json.dumps(
                {
                    "storage": {
                        "type": "invalid_type",  # Invalid enum value
                        "path": "~/.aurora/memory.db",
                    }
                }
            )
        )

        # Should raise clear error
        with pytest.raises(ConfigurationError) as exc_info:
            Config.load(project_path=project_dir)

        # Error message should be helpful
        error_msg = str(exc_info.value)
        assert "invalid" in error_msg.lower() or "enum" in error_msg.lower()

    def test_minimal_config_with_api_key(self, tmp_path: Path, monkeypatch) -> None:
        """Test minimal configuration with API key from environment."""
        # Set API key in environment
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test-key")

        # Create minimal project config
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        project_config = project_dir / ".aurora" / "config.json"
        project_config.parent.mkdir(parents=True)
        project_config.write_text(json.dumps({"storage": {"type": "memory", "path": ":memory:"}}))

        # Load config
        config = Config.load(project_path=project_dir)

        # Verify config loaded successfully
        assert config.get("version") == "1.1.0"  # From global config or defaults
        llm_config = config.llm_config()
        assert llm_config["api_key_env"] == "ANTHROPIC_API_KEY"

        # API key should be accessible from environment
        assert os.environ.get("ANTHROPIC_API_KEY") == "sk-ant-test-key"

    def test_config_reloading(self, tmp_path: Path) -> None:
        """Test configuration can be reloaded to pick up changes."""
        project_dir = tmp_path / "project"
        project_dir.mkdir()

        project_config = project_dir / ".aurora" / "config.json"
        project_config.parent.mkdir(parents=True)

        # Initial config
        project_config.write_text(json.dumps({"logging": {"level": "INFO"}}))

        config1 = Config.load(project_path=project_dir)
        assert config1.get("logging.level") == "INFO"

        # Update config file
        project_config.write_text(json.dumps({"logging": {"level": "DEBUG"}}))

        # Reload
        config2 = Config.load(project_path=project_dir)
        assert config2.get("logging.level") == "DEBUG"

    def test_config_validation_comprehensive(self, tmp_path: Path) -> None:
        """Test comprehensive configuration validation."""
        project_dir = tmp_path / "project"
        project_dir.mkdir()

        # Create fully valid config
        project_config = project_dir / ".aurora" / "config.json"
        project_config.parent.mkdir(parents=True)
        project_config.write_text(
            json.dumps(
                {
                    "version": "1.0",
                    "mode": "standalone",
                    "storage": {
                        "type": "sqlite",
                        "path": "~/.aurora/memory.db",
                        "max_connections": 10,
                        "timeout_seconds": 5,
                    },
                    "llm": {
                        "reasoning_provider": "anthropic",
                        "reasoning_model": "claude-3-5-sonnet-20241022",
                        "api_key_env": "ANTHROPIC_API_KEY",
                        "timeout_seconds": 30,
                    },
                    "context": {
                        "code": {
                            "enabled": True,
                            "languages": ["python"],
                            "max_file_size_kb": 500,
                            "cache_ttl_hours": 24,
                        }
                    },
                    "agents": {
                        "discovery_paths": [".aurora/agents.json"],
                        "refresh_interval_days": 15,
                        "fallback_mode": "llm_only",
                    },
                    "logging": {
                        "level": "INFO",
                        "path": "~/.aurora/logs/",
                        "max_size_mb": 100,
                        "max_files": 10,
                    },
                }
            )
        )

        # Load and validate
        config = Config.load(project_path=project_dir)
        assert config.validate() is True

        # Verify all sections present
        assert config.get("version") is not None
        assert config.get("storage") is not None
        assert config.get("llm") is not None
        assert config.get("context") is not None
        assert config.get("agents") is not None
        assert config.get("logging") is not None


class TestConfigWithComponents:
    """Test configuration integration with other system components."""

    def test_config_provides_storage_settings(self, tmp_path: Path) -> None:
        """Test configuration provides settings for storage component."""
        project_dir = tmp_path / "project"
        project_dir.mkdir()

        project_config = project_dir / ".aurora" / "config.json"
        project_config.parent.mkdir(parents=True)
        project_config.write_text(
            json.dumps(
                {
                    "storage": {
                        "type": "sqlite",
                        "path": ".aurora/test.db",
                        "max_connections": 5,
                        "timeout_seconds": 10,
                    }
                }
            )
        )

        config = Config.load(project_path=project_dir)

        # Components can extract their settings
        storage_type = config.get("storage.type")
        storage_path = config.storage_path()
        max_conn = config.get("storage.max_connections")
        timeout = config.get("storage.timeout_seconds")

        assert storage_type == "sqlite"
        assert storage_path.is_absolute()
        assert max_conn == 5
        assert timeout == 10

    def test_config_provides_llm_settings(self, tmp_path: Path) -> None:
        """Test configuration provides settings for LLM component."""
        project_dir = tmp_path / "project"
        project_dir.mkdir()

        config = Config.load(project_path=project_dir)

        llm_config = config.llm_config()

        # LLM component can use these settings
        assert "reasoning_provider" in llm_config
        assert "reasoning_model" in llm_config
        assert "api_key_env" in llm_config
        assert "timeout_seconds" in llm_config

    def test_config_provides_context_settings(self, tmp_path: Path) -> None:
        """Test configuration provides settings for context providers."""
        project_dir = tmp_path / "project"
        project_dir.mkdir()

        project_config = project_dir / ".aurora" / "config.json"
        project_config.parent.mkdir(parents=True)
        project_config.write_text(
            json.dumps(
                {
                    "context": {
                        "code": {
                            "enabled": True,
                            "languages": ["python", "javascript"],
                            "max_file_size_kb": 1000,
                            "cache_ttl_hours": 48,
                        }
                    }
                }
            )
        )

        config = Config.load(project_path=project_dir)

        # Context provider can extract its settings
        code_enabled = config.get("context.code.enabled")
        languages = config.get("context.code.languages")
        max_size = config.get("context.code.max_file_size_kb")
        cache_ttl = config.get("context.code.cache_ttl_hours")

        assert code_enabled is True
        assert languages == ["python", "javascript"]
        assert max_size == 1000
        assert cache_ttl == 48
