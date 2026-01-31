"""Unit tests for AURORA CLI configuration management."""

import json
import os

import pytest

from aurora_cli.config import Config, ConfigurationError, load_config


class TestConfigDataclass:
    """Test Config dataclass functionality."""

    def test_default_values(self):
        """Test that Config has correct default values."""
        config = Config()

        assert config.version == "1.1.0"
        assert config.llm_provider == "anthropic"
        assert config.anthropic_api_key is None
        assert config.llm_model == "claude-3-5-sonnet-20241022"
        assert config.llm_temperature == 0.7
        assert config.llm_max_tokens == 4096
        assert config.escalation_threshold == 0.7
        assert config.escalation_enable_keyword_only is False
        assert config.escalation_force_mode is None
        assert config.memory_auto_index is True
        assert config.memory_index_paths == ["."]
        assert config.memory_chunk_size == 1000
        assert config.memory_overlap == 200
        assert config.logging_level == "INFO"
        assert config.logging_file == "~/.aurora/aurora.log"

    def test_get_api_key_from_config(self):
        """Test getting API key from config file."""
        config = Config(anthropic_api_key="sk-ant-test123")
        assert config.get_api_key() == "sk-ant-test123"

    def test_get_api_key_from_env(self, monkeypatch):
        """Test that environment variable overrides config file."""
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-env456")
        config = Config(anthropic_api_key="sk-ant-test123")
        assert config.get_api_key() == "sk-ant-env456"

    def test_get_api_key_env_strips_whitespace(self, monkeypatch):
        """Test that API key from environment is stripped."""
        monkeypatch.setenv("ANTHROPIC_API_KEY", "  sk-ant-test123  ")
        config = Config()
        assert config.get_api_key() == "sk-ant-test123"

    def test_get_api_key_config_strips_whitespace(self):
        """Test that API key from config is stripped."""
        config = Config(anthropic_api_key="  sk-ant-test123  ")
        assert config.get_api_key() == "sk-ant-test123"

    def test_get_api_key_missing_raises_error(self):
        """Test that missing API key raises ConfigurationError."""
        config = Config()
        with pytest.raises(ConfigurationError) as exc_info:
            config.get_api_key()

        error_message = str(exc_info.value)
        assert "ANTHROPIC_API_KEY not found" in error_message
        assert "export ANTHROPIC_API_KEY" in error_message
        assert "aur init" in error_message
        assert "https://console.anthropic.com" in error_message

    def test_get_api_key_empty_string_raises_error(self):
        """Test that empty API key raises ConfigurationError."""
        config = Config(anthropic_api_key="")
        with pytest.raises(ConfigurationError):
            config.get_api_key()

    def test_validate_valid_config(self):
        """Test validation passes for valid config."""
        config = Config()
        config.validate()  # Should not raise

    def test_validate_threshold_too_high(self):
        """Test validation fails for threshold > 1.0."""
        config = Config(escalation_threshold=1.5)
        with pytest.raises(ConfigurationError) as exc_info:
            config.validate()
        assert "escalation_threshold must be 0.0-1.0" in str(exc_info.value)

    def test_validate_threshold_negative(self):
        """Test validation fails for negative threshold."""
        config = Config(escalation_threshold=-0.1)
        with pytest.raises(ConfigurationError) as exc_info:
            config.validate()
        assert "escalation_threshold must be 0.0-1.0" in str(exc_info.value)

    def test_validate_invalid_provider(self):
        """Test validation fails for invalid provider."""
        config = Config(llm_provider="openai")
        with pytest.raises(ConfigurationError) as exc_info:
            config.validate()
        assert "llm_provider must be 'anthropic'" in str(exc_info.value)

    def test_validate_invalid_force_mode(self):
        """Test validation fails for invalid force mode."""
        config = Config(escalation_force_mode="invalid")
        with pytest.raises(ConfigurationError) as exc_info:
            config.validate()
        assert "escalation_force_mode must be 'direct' or 'aurora'" in str(exc_info.value)

    def test_validate_temperature_too_high(self):
        """Test validation fails for temperature > 1.0."""
        config = Config(llm_temperature=1.5)
        with pytest.raises(ConfigurationError) as exc_info:
            config.validate()
        assert "llm_temperature must be 0.0-1.0" in str(exc_info.value)

    def test_validate_temperature_negative(self):
        """Test validation fails for negative temperature."""
        config = Config(llm_temperature=-0.1)
        with pytest.raises(ConfigurationError) as exc_info:
            config.validate()
        assert "llm_temperature must be 0.0-1.0" in str(exc_info.value)

    def test_validate_max_tokens_zero(self):
        """Test validation fails for zero max_tokens."""
        config = Config(llm_max_tokens=0)
        with pytest.raises(ConfigurationError) as exc_info:
            config.validate()
        assert "llm_max_tokens must be positive" in str(exc_info.value)

    def test_validate_chunk_size_too_small(self):
        """Test validation fails for chunk size < 100."""
        config = Config(memory_chunk_size=50)
        with pytest.raises(ConfigurationError) as exc_info:
            config.validate()
        assert "memory_chunk_size must be >= 100" in str(exc_info.value)

    def test_validate_negative_overlap(self):
        """Test validation fails for negative overlap."""
        config = Config(memory_overlap=-10)
        with pytest.raises(ConfigurationError) as exc_info:
            config.validate()
        assert "memory_overlap must be >= 0" in str(exc_info.value)

    def test_validate_invalid_logging_level(self):
        """Test validation fails for invalid logging level."""
        config = Config(logging_level="INVALID")
        with pytest.raises(ConfigurationError) as exc_info:
            config.validate()
        assert "logging_level must be one of" in str(exc_info.value)

    def test_validate_mcp_max_results_zero(self):
        """Test validation fails for zero mcp_max_results."""
        config = Config(mcp_max_results=0)
        with pytest.raises(ConfigurationError) as exc_info:
            config.validate()
        assert "mcp_max_results must be positive" in str(exc_info.value)

    def test_validate_mcp_max_results_negative(self):
        """Test validation fails for negative mcp_max_results."""
        config = Config(mcp_max_results=-5)
        with pytest.raises(ConfigurationError) as exc_info:
            config.validate()
        assert "mcp_max_results must be positive" in str(exc_info.value)

    def test_validate_warns_nonexistent_path(self, capsys, tmp_path):
        """Test validation warns about non-existent paths."""
        nonexistent_path = str(tmp_path / "does_not_exist")
        config = Config(memory_index_paths=[nonexistent_path])
        config.validate()

        captured = capsys.readouterr()
        assert f"Warning: Path '{nonexistent_path}' does not exist" in captured.out


class TestLoadConfig:
    """Test load_config function."""

    def test_load_config_defaults(self, tmp_path, monkeypatch, capsys):
        """Test loading config with defaults (no file, no env vars)."""
        # Mock home directory to avoid picking up real config
        fake_home = tmp_path / "fake_home"
        fake_home.mkdir()
        monkeypatch.setenv("HOME", str(fake_home))

        # Change to temp directory where no config exists
        work_dir = tmp_path / "work"
        work_dir.mkdir()
        monkeypatch.chdir(work_dir)

        # Clear any env vars
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        monkeypatch.delenv("AURORA_ESCALATION_THRESHOLD", raising=False)
        monkeypatch.delenv("AURORA_LOGGING_LEVEL", raising=False)

        config = load_config()

        # Should use defaults
        assert config.llm_provider == "anthropic"
        assert config.llm_model == "claude-3-5-sonnet-20241022"
        assert config.escalation_threshold == 0.7

        # Should print that it used defaults
        captured = capsys.readouterr()
        assert "defaults" in captured.out.lower()

    def test_load_config_from_file(self, tmp_path, monkeypatch, capsys):
        """Test loading config from file."""
        # Create config file
        config_path = tmp_path / "aurora.config.json"
        config_data = {
            "version": "1.1.0",
            "llm": {
                "provider": "anthropic",
                "anthropic_api_key": "sk-ant-file123",
                "model": "claude-3-opus-20240229",
                "temperature": 0.8,
                "max_tokens": 2048,
            },
            "escalation": {
                "threshold": 0.5,
                "enable_keyword_only": True,
                "force_mode": None,
            },
            "memory": {
                "auto_index": False,
                "index_paths": ["/test/path"],
                "chunk_size": 500,
                "overlap": 100,
            },
            "logging": {"level": "DEBUG", "file": "/tmp/aurora.log"},
        }

        with open(config_path, "w") as f:
            json.dump(config_data, f)

        # Change to temp directory
        monkeypatch.chdir(tmp_path)

        config = load_config()

        # Should use file values
        assert config.anthropic_api_key == "sk-ant-file123"
        assert config.llm_model == "claude-3-opus-20240229"
        assert config.llm_temperature == 0.8
        assert config.llm_max_tokens == 2048
        assert config.escalation_threshold == 0.5
        assert config.escalation_enable_keyword_only is True
        assert config.memory_auto_index is False
        assert config.memory_index_paths == ["/test/path"]
        assert config.memory_chunk_size == 500
        assert config.memory_overlap == 100
        assert config.logging_level == "DEBUG"
        assert config.logging_file == "/tmp/aurora.log"

        # Should print file path
        captured = capsys.readouterr()
        assert str(config_path) in captured.out

    def test_load_config_env_overrides_file(self, tmp_path, monkeypatch, _capsys):
        """Test that environment variables override file values."""
        # Create config file
        config_path = tmp_path / "aurora.config.json"
        config_data = {
            "version": "1.1.0",
            "llm": {"provider": "anthropic", "anthropic_api_key": "sk-ant-file123"},
            "escalation": {"threshold": 0.5},
            "logging": {"level": "DEBUG"},
        }

        with open(config_path, "w") as f:
            json.dump(config_data, f)

        # Set environment variables
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-env456")
        monkeypatch.setenv("AURORA_ESCALATION_THRESHOLD", "0.8")
        monkeypatch.setenv("AURORA_LOGGING_LEVEL", "warning")

        # Change to temp directory
        monkeypatch.chdir(tmp_path)

        config = load_config()

        # Env vars should override file
        assert config.get_api_key() == "sk-ant-env456"  # From env, not file
        assert config.escalation_threshold == 0.8  # From env, not 0.5
        assert config.logging_level == "WARNING"  # From env (uppercased), not DEBUG

    def test_load_config_explicit_path(self, tmp_path, capsys):
        """Test loading config from explicit path."""
        # Create config in non-standard location
        config_path = tmp_path / "custom_config.json"
        config_data = {
            "version": "1.1.0",
            "llm": {"provider": "anthropic", "model": "custom-model"},
        }

        with open(config_path, "w") as f:
            json.dump(config_data, f)

        config = load_config(path=str(config_path))

        assert config.llm_model == "custom-model"

        captured = capsys.readouterr()
        assert str(config_path) in captured.out

    def test_load_config_invalid_json(self, tmp_path, monkeypatch):
        """Test loading config with invalid JSON syntax."""
        # Create invalid JSON file
        config_path = tmp_path / "aurora.config.json"
        with open(config_path, "w") as f:
            f.write('{"invalid": json}')  # Missing quotes around json

        monkeypatch.chdir(tmp_path)

        with pytest.raises(ConfigurationError) as exc_info:
            load_config()

        error_message = str(exc_info.value)
        assert "Config file syntax error" in error_message
        assert "jsonlint" in error_message

    def test_load_config_permission_error(self, tmp_path, monkeypatch):
        """Test loading config with permission denied."""
        # Create config file
        config_path = tmp_path / "aurora.config.json"
        config_data = {"version": "1.1.0"}

        with open(config_path, "w") as f:
            json.dump(config_data, f)

        # Make file unreadable
        os.chmod(config_path, 0o000)

        try:
            monkeypatch.chdir(tmp_path)

            with pytest.raises(ConfigurationError) as exc_info:
                load_config()

            error_message = str(exc_info.value)
            assert "Cannot read" in error_message
            assert "Check file permissions" in error_message
            assert "chmod 600" in error_message
        finally:
            # Restore permissions for cleanup
            os.chmod(config_path, 0o600)

    def test_load_config_generic_file_error(self, tmp_path, monkeypatch):
        """Test loading config with generic file error (e.g., IO error)."""
        from unittest.mock import patch

        # Mock Path.exists to return True but open() to raise OSError
        config_path = tmp_path / "aurora.config.json"

        # Create a real file so exists() returns True
        config_data = {"version": "1.1.0"}
        with open(config_path, "w") as f:
            json.dump(config_data, f)

        monkeypatch.chdir(tmp_path)

        # Mock open to raise a generic OSError (simulating disk full, IO error, etc.)
        with patch("builtins.open", side_effect=OSError("Disk full")):
            with pytest.raises(ConfigurationError) as exc_info:
                load_config()

            error_message = str(exc_info.value)
            # Should contain helpful error message from ErrorHandler
            assert "Config file error" in error_message or "Disk full" in error_message

    def test_load_config_invalid_threshold_env(self, monkeypatch):
        """Test loading config with invalid threshold from environment."""
        monkeypatch.setenv("AURORA_ESCALATION_THRESHOLD", "not_a_number")

        with pytest.raises(ConfigurationError) as exc_info:
            load_config()

        error_message = str(exc_info.value)
        assert "AURORA_ESCALATION_THRESHOLD must be a number" in error_message

    def test_load_config_search_home_directory(self, tmp_path, monkeypatch, capsys):
        """Test that load_config searches ~/.aurora/config.json."""
        # Create home directory config
        home_dir = tmp_path / "home"
        home_dir.mkdir()
        config_dir = home_dir / ".aurora"
        config_dir.mkdir()
        config_path = config_dir / "config.json"

        config_data = {"version": "1.1.0", "llm": {"model": "home-model"}}

        with open(config_path, "w") as f:
            json.dump(config_data, f)

        # Mock home directory
        monkeypatch.setenv("HOME", str(home_dir))
        # Change to a different directory
        monkeypatch.chdir(tmp_path)

        config = load_config()

        assert config.llm_model == "home-model"

        captured = capsys.readouterr()
        assert str(config_path) in captured.out

    def test_load_config_current_directory_precedence(self, tmp_path, monkeypatch, capsys):
        """Test that current directory config takes precedence over home directory."""
        # Create home directory config
        home_dir = tmp_path / "home"
        home_dir.mkdir()
        home_config_dir = home_dir / ".aurora"
        home_config_dir.mkdir()
        home_config_path = home_config_dir / "config.json"

        home_config_data = {"version": "1.1.0", "llm": {"model": "home-model"}}

        with open(home_config_path, "w") as f:
            json.dump(home_config_data, f)

        # Create current directory config
        current_dir = tmp_path / "current"
        current_dir.mkdir()
        current_config_path = current_dir / "aurora.config.json"

        current_config_data = {"version": "1.1.0", "llm": {"model": "current-model"}}

        with open(current_config_path, "w") as f:
            json.dump(current_config_data, f)

        # Mock home directory and change to current directory
        monkeypatch.setenv("HOME", str(home_dir))
        monkeypatch.chdir(current_dir)

        config = load_config()

        # Should use current directory config
        assert config.llm_model == "current-model"

        captured = capsys.readouterr()
        assert str(current_config_path) in captured.out

    def test_load_config_partial_file(self, tmp_path, monkeypatch, _capsys):
        """Test loading config with partial file (missing keys use defaults)."""
        # Create config with only some values
        config_path = tmp_path / "aurora.config.json"
        config_data = {
            "llm": {"model": "custom-model"},
            # Missing most other fields
        }

        with open(config_path, "w") as f:
            json.dump(config_data, f)

        monkeypatch.chdir(tmp_path)

        config = load_config()

        # Should use custom value
        assert config.llm_model == "custom-model"

        # Should use defaults for missing values
        assert config.llm_provider == "anthropic"
        assert config.escalation_threshold == 0.7
        assert config.memory_auto_index is True


class TestConfigPrecedence:
    """Test configuration precedence: CLI flags > Env vars > Config file > Defaults."""

    def test_precedence_env_over_file(self, tmp_path, monkeypatch):
        """Test environment variable takes precedence over config file."""
        # Create config file
        config_path = tmp_path / "aurora.config.json"
        config_data = {"llm": {"anthropic_api_key": "sk-ant-file123"}}

        with open(config_path, "w") as f:
            json.dump(config_data, f)

        # Set env var
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-env456")
        monkeypatch.chdir(tmp_path)

        config = load_config()

        # Env var should win
        assert config.get_api_key() == "sk-ant-env456"

    def test_precedence_file_over_defaults(self, tmp_path, monkeypatch):
        """Test config file takes precedence over defaults."""
        # Create config file
        config_path = tmp_path / "aurora.config.json"
        config_data = {"escalation": {"threshold": 0.9}}

        with open(config_path, "w") as f:
            json.dump(config_data, f)

        monkeypatch.chdir(tmp_path)

        config = load_config()

        # File value should win over default (0.7)
        assert config.escalation_threshold == 0.9


class TestConfigEdgeCases:
    """Test edge cases and additional scenarios."""

    def test_config_with_all_mcp_fields(self, tmp_path, monkeypatch):
        """Test loading config with all MCP fields specified."""
        config_path = tmp_path / "aurora.config.json"
        config_data = {
            "mcp": {
                "always_on": True,
                "log_file": "/custom/mcp.log",
                "max_results": 50,
            },
        }

        with open(config_path, "w") as f:
            json.dump(config_data, f)

        monkeypatch.chdir(tmp_path)

        config = load_config()

        assert config.mcp_always_on is True
        assert config.mcp_log_file == "/custom/mcp.log"
        assert config.mcp_max_results == 50

    def test_config_with_valid_force_modes(self):
        """Test Config accepts valid force modes."""
        # Test 'direct' mode
        config_direct = Config(escalation_force_mode="direct")
        config_direct.validate()  # Should not raise

        # Test 'aurora' mode
        config_aurora = Config(escalation_force_mode="aurora")
        config_aurora.validate()  # Should not raise

    def test_config_with_all_valid_logging_levels(self):
        """Test Config accepts all valid logging levels."""
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]

        for level in valid_levels:
            config = Config(logging_level=level)
            config.validate()  # Should not raise

    def test_validate_boundary_values(self):
        """Test validation with boundary values."""
        # Minimum valid values
        config_min = Config(
            escalation_threshold=0.0,
            llm_temperature=0.0,
            llm_max_tokens=1,
            memory_chunk_size=100,
            memory_overlap=0,
            mcp_max_results=1,
        )
        config_min.validate()  # Should not raise

        # Maximum valid values
        config_max = Config(
            escalation_threshold=1.0,
            llm_temperature=1.0,
        )
        config_max.validate()  # Should not raise

    def test_load_config_empty_nested_sections(self, tmp_path, monkeypatch):
        """Test loading config with empty nested sections uses defaults."""
        config_path = tmp_path / "aurora.config.json"
        config_data = {
            "llm": {},
            "escalation": {},
            "memory": {},
            "logging": {},
            "mcp": {},
        }

        with open(config_path, "w") as f:
            json.dump(config_data, f)

        monkeypatch.chdir(tmp_path)

        config = load_config()

        # Should use defaults for all empty sections
        assert config.llm_provider == "anthropic"
        assert config.escalation_threshold == 0.7
        assert config.memory_auto_index is True
        assert config.logging_level == "INFO"
        assert config.mcp_always_on is False

    def test_get_api_key_with_whitespace_only(self):
        """Test that whitespace-only API key is treated as missing."""
        config = Config(anthropic_api_key="   ")
        with pytest.raises(ConfigurationError):
            config.get_api_key()

    def test_get_api_key_env_empty_falls_back_to_config(self, monkeypatch):
        """Test that empty env var falls back to config value."""
        # Set empty env var
        monkeypatch.setenv("ANTHROPIC_API_KEY", "   ")
        config = Config(anthropic_api_key="sk-ant-config123")

        # Empty env var should be ignored, use config
        assert config.get_api_key() == "sk-ant-config123"
