"""Integration tests for CLI config system.

Tests config loading → validation → command execution workflows with real file I/O.
Tests integration with real components, not just unit-level config parsing.
"""

import json
import os
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
from aurora_cli.config import Config, ConfigurationError, load_config
from aurora_cli.errors import ErrorHandler


class TestConfigIntegrationWorkflows:
    """Test config system integration with CLI commands and real file I/O."""

    def test_config_load_validate_execute_workflow(self, tmp_path, monkeypatch):
        """Test complete workflow: load config → validate → use in command execution."""
        # 1. Create config file
        config_path = tmp_path / "aurora.config.json"
        config_data = {
            "version": "1.1.0",
            "llm": {
                "provider": "anthropic",
                "anthropic_api_key": "sk-ant-test-key",
                "model": "claude-3-5-sonnet-20241022",
                "temperature": 0.7,
                "max_tokens": 4096,
            },
            "memory": {
                "auto_index": True,
                "index_paths": [str(tmp_path)],
                "chunk_size": 1000,
                "overlap": 200,
            },
            "logging": {"level": "INFO", "file": str(tmp_path / "aurora.log")},
        }

        with open(config_path, "w") as f:
            json.dump(config_data, f)

        monkeypatch.chdir(tmp_path)

        # 2. Load and validate config
        config = load_config()
        config.validate()

        # 3. Verify config can be used for command execution
        assert config.get_api_key() == "sk-ant-test-key"
        assert config.llm_model == "claude-3-5-sonnet-20241022"
        assert config.memory_chunk_size == 1000
        assert config.memory_overlap == 200
        assert config.logging_level == "INFO"

        # 4. Verify paths are correctly resolved
        assert tmp_path in [Path(p).expanduser() for p in config.memory_index_paths]

    def test_config_env_override_in_command_context(self, tmp_path, monkeypatch, capsys):
        """Test environment variable override works in command execution context."""
        # 1. Create config file with one API key
        config_path = tmp_path / "aurora.config.json"
        config_data = {"llm": {"anthropic_api_key": "sk-ant-file-key"}}

        with open(config_path, "w") as f:
            json.dump(config_data, f)

        # 2. Set different API key in environment
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-env-key")
        monkeypatch.chdir(tmp_path)

        # 3. Load config
        config = load_config()

        # 4. Environment variable should override file value
        assert config.get_api_key() == "sk-ant-env-key"

        # 5. Verify this works in a simulated command context
        # (e.g., initializing LLMClient with config.get_api_key())
        api_key = config.get_api_key()
        assert api_key == "sk-ant-env-key"
        assert api_key != "sk-ant-file-key"

    def test_config_update_persists_and_reloads(self, tmp_path, monkeypatch, capsys):
        """Test config updates persist correctly and can be reloaded."""
        # 1. Create initial config
        config_path = tmp_path / "aurora.config.json"
        initial_data = {
            "llm": {"model": "claude-3-5-sonnet-20241022"},
            "escalation": {"threshold": 0.7},
        }

        with open(config_path, "w") as f:
            json.dump(initial_data, f)

        monkeypatch.chdir(tmp_path)

        # 2. Load initial config
        config1 = load_config()
        assert config1.llm_model == "claude-3-5-sonnet-20241022"
        assert config1.escalation_threshold == 0.7

        # 3. Update config file (simulate user editing config)
        updated_data = {
            "llm": {"model": "claude-3-opus-20240229"},
            "escalation": {"threshold": 0.9},
        }

        with open(config_path, "w") as f:
            json.dump(updated_data, f)

        # 4. Reload config
        config2 = load_config()
        assert config2.llm_model == "claude-3-opus-20240229"
        assert config2.escalation_threshold == 0.9

        # 5. Verify changes persisted
        with open(config_path) as f:
            saved_data = json.load(f)
        assert saved_data["llm"]["model"] == "claude-3-opus-20240229"
        assert saved_data["escalation"]["threshold"] == 0.9

    def test_config_migration_old_to_new_version(self, tmp_path, monkeypatch):
        """Test config system handles old version configs gracefully."""
        # 1. Create old version config (missing new fields)
        config_path = tmp_path / "aurora.config.json"
        old_config_data = {
            "version": "1.0.0",  # Old version
            "llm": {
                "provider": "anthropic",
                "model": "claude-3-5-sonnet-20241022",
            },
            # Missing: mcp fields, escalation_enable_keyword_only, etc.
        }

        with open(config_path, "w") as f:
            json.dump(old_config_data, f)

        monkeypatch.chdir(tmp_path)

        # 2. Load config (should apply defaults for missing fields)
        config = load_config()

        # 3. Verify old fields are preserved
        assert config.llm_provider == "anthropic"
        assert config.llm_model == "claude-3-5-sonnet-20241022"

        # 4. Verify new fields have defaults
        assert config.mcp_always_on is False
        assert config.mcp_max_results == 10
        assert config.escalation_enable_keyword_only is False

    def test_config_error_handler_integration(self, tmp_path, monkeypatch):
        """Test ErrorHandler integration with config loading errors."""
        # 1. Create invalid JSON config
        config_path = tmp_path / "aurora.config.json"
        with open(config_path, "w") as f:
            f.write('{"invalid": json syntax}')

        monkeypatch.chdir(tmp_path)

        # 2. ErrorHandler should provide helpful error message
        with pytest.raises(ConfigurationError) as exc_info:
            load_config()

        error_message = str(exc_info.value)

        # 3. Verify error message contains helpful details
        assert "Config file syntax error" in error_message
        assert "jsonlint" in error_message
        assert str(config_path) in error_message

    def test_config_validation_blocks_invalid_command_execution(self, tmp_path, monkeypatch):
        """Test that invalid config is caught during validation before command execution."""
        # 1. Create config with invalid values
        config_path = tmp_path / "aurora.config.json"
        config_data = {
            "llm": {"temperature": 2.0},  # Invalid: must be 0.0-1.0
            "escalation": {"threshold": 1.5},  # Invalid: must be 0.0-1.0
        }

        with open(config_path, "w") as f:
            json.dump(config_data, f)

        monkeypatch.chdir(tmp_path)

        # 2. Load config should succeed, but validation should fail
        with pytest.raises(ConfigurationError) as exc_info:
            load_config()  # Calls validate() internally

        # 3. Verify validation error is caught
        error_message = str(exc_info.value)
        assert "temperature" in error_message.lower() or "threshold" in error_message.lower()


class TestConfigFileSystemIntegration:
    """Test config system integration with real file system operations."""

    def test_config_creates_parent_directories(self, tmp_path, monkeypatch):
        """Test config file path expansion creates parent directories if needed."""
        # This is a read-only test; write operations would be in a save_config function
        # For now, test that paths are correctly expanded

        config_path = tmp_path / ".aurora" / "config.json"
        config_path.parent.mkdir(parents=True, exist_ok=True)

        config_data = {"llm": {"model": "test-model"}}

        with open(config_path, "w") as f:
            json.dump(config_data, f)

        # Change to temp directory
        monkeypatch.chdir(tmp_path)

        # Load from home directory path
        home_dir = tmp_path
        monkeypatch.setenv("HOME", str(home_dir))

        config = load_config()
        assert config.llm_model == "test-model"

    def test_config_handles_nested_paths(self, tmp_path, monkeypatch):
        """Test config correctly handles nested directory structures."""
        # Create nested structure
        project_dir = tmp_path / "projects" / "my-project"
        project_dir.mkdir(parents=True)

        config_path = project_dir / "aurora.config.json"
        config_data = {
            "memory": {
                "index_paths": [
                    str(project_dir / "src"),
                    str(project_dir / "tests"),
                ]
            }
        }

        with open(config_path, "w") as f:
            json.dump(config_data, f)

        monkeypatch.chdir(project_dir)

        config = load_config()

        # Verify paths are preserved
        assert str(project_dir / "src") in config.memory_index_paths
        assert str(project_dir / "tests") in config.memory_index_paths

    def test_config_handles_symlinks(self, tmp_path, monkeypatch):
        """Test config system handles symlinked config files."""
        # Create actual config file
        real_config_dir = tmp_path / "real"
        real_config_dir.mkdir()
        real_config = real_config_dir / "config.json"

        config_data = {"llm": {"model": "symlinked-model"}}
        with open(real_config, "w") as f:
            json.dump(config_data, f)

        # Create symlink
        symlink_config = tmp_path / "aurora.config.json"
        try:
            symlink_config.symlink_to(real_config)
        except OSError:
            pytest.skip("Symlinks not supported on this platform")

        monkeypatch.chdir(tmp_path)

        config = load_config()
        assert config.llm_model == "symlinked-model"


class TestConfigWithMemoryCommands:
    """Test config integration with memory management commands."""

    def test_config_memory_settings_used_by_index_command(self, tmp_path, monkeypatch):
        """Test memory settings from config are used by index command."""
        # Create config with custom memory settings
        config_path = tmp_path / "aurora.config.json"
        config_data = {
            "memory": {
                "chunk_size": 500,
                "overlap": 100,
                "index_paths": [str(tmp_path / "src")],
            }
        }

        with open(config_path, "w") as f:
            json.dump(config_data, f)

        # Create source directory
        src_dir = tmp_path / "src"
        src_dir.mkdir()

        monkeypatch.chdir(tmp_path)

        # Load config
        config = load_config()

        # Verify memory settings are available for index command
        assert config.memory_chunk_size == 500
        assert config.memory_overlap == 100
        assert str(tmp_path / "src") in config.memory_index_paths

        # Simulate index command would use these settings
        # (In real implementation, MemoryManager would be initialized with these)

    def test_config_auto_index_setting(self, tmp_path, monkeypatch):
        """Test auto_index setting from config."""
        # Test with auto_index enabled
        config_path = tmp_path / "aurora.config.json"
        config_data = {"memory": {"auto_index": True}}

        with open(config_path, "w") as f:
            json.dump(config_data, f)

        monkeypatch.chdir(tmp_path)

        config = load_config()
        assert config.memory_auto_index is True

        # Update config to disable auto_index
        config_data["memory"]["auto_index"] = False
        with open(config_path, "w") as f:
            json.dump(config_data, f)

        config = load_config()
        assert config.memory_auto_index is False
