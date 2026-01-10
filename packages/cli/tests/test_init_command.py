"""Unit tests for AURORA CLI init command."""

import json
import os
from pathlib import Path

import pytest
from click.testing import CliRunner

from aurora_cli.commands.init import init_command


class TestInitCommand:
    """Test init command functionality."""

    def test_init_creates_config_file(self, tmp_path, monkeypatch):
        """Test that init creates config file in ~/.aurora/config.json."""
        # Mock home directory
        home_dir = tmp_path / "home"
        home_dir.mkdir()
        monkeypatch.setenv("HOME", str(home_dir))

        runner = CliRunner()
        result = runner.invoke(
            init_command,
            input="sk-ant-test123\nn\n",  # API key, don't index
        )

        assert result.exit_code == 0
        assert "✓" in result.output
        assert "Configuration created" in result.output

        # Verify config file was created
        config_path = home_dir / ".aurora" / "config.json"
        assert config_path.exists()

        # Verify config content
        with open(config_path) as f:
            config = json.load(f)

        assert config["llm"]["anthropic_api_key"] == "sk-ant-test123"
        assert config["version"] == "1.1.0"

    def test_init_creates_directory(self, tmp_path, monkeypatch):
        """Test that init creates ~/.aurora directory if it doesn't exist."""
        # Mock home directory
        home_dir = tmp_path / "home"
        home_dir.mkdir()
        monkeypatch.setenv("HOME", str(home_dir))

        # Verify directory doesn't exist yet
        config_dir = home_dir / ".aurora"
        assert not config_dir.exists()

        runner = CliRunner()
        result = runner.invoke(init_command, input="\nn\n")  # Skip API key, don't index

        assert result.exit_code == 0

        # Verify directory was created
        assert config_dir.exists()
        assert config_dir.is_dir()

    def test_init_without_api_key(self, tmp_path, monkeypatch):
        """Test init without providing API key."""
        # Mock home directory
        home_dir = tmp_path / "home"
        home_dir.mkdir()

        # Clear any existing API key in environment
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        monkeypatch.setenv("HOME", str(home_dir))

        runner = CliRunner()
        # Use empty string (just press enter) for API key
        result = runner.invoke(init_command, input="\nn\n")  # Empty API key, don't index

        assert result.exit_code == 0

        # Verify config file was created
        config_path = home_dir / ".aurora" / "config.json"
        assert config_path.exists()

        # Verify API key is None (empty string was provided)
        with open(config_path) as f:
            config = json.load(f)

        # Empty string input should result in None in config
        assert config["llm"]["anthropic_api_key"] is None

    def test_init_with_api_key(self, tmp_path, monkeypatch):
        """Test init with API key provided."""
        # Mock home directory
        home_dir = tmp_path / "home"
        home_dir.mkdir()
        monkeypatch.setenv("HOME", str(home_dir))

        runner = CliRunner()
        result = runner.invoke(
            init_command,
            input="sk-ant-valid123\nn\n",  # API key, don't index
        )

        assert result.exit_code == 0

        # Verify config file has API key
        config_path = home_dir / ".aurora" / "config.json"
        with open(config_path) as f:
            config = json.load(f)

        assert config["llm"]["anthropic_api_key"] == "sk-ant-valid123"

    def test_init_warns_invalid_api_key_format(self, tmp_path, monkeypatch):
        """Test init warns about invalid API key format."""
        # Mock home directory
        home_dir = tmp_path / "home"
        home_dir.mkdir()
        monkeypatch.setenv("HOME", str(home_dir))

        runner = CliRunner()
        result = runner.invoke(
            init_command,
            input="invalid-key\ny\nn\n",  # Invalid key, continue anyway
        )

        assert result.exit_code == 0
        assert "Warning" in result.output
        assert "sk-ant-" in result.output

    def test_init_aborts_on_invalid_key_rejection(self, tmp_path, monkeypatch):
        """Test init aborts when user rejects invalid API key."""
        # Mock home directory
        home_dir = tmp_path / "home"
        home_dir.mkdir()
        monkeypatch.setenv("HOME", str(home_dir))

        runner = CliRunner()
        result = runner.invoke(
            init_command,
            input="invalid-key\nn\n",  # Invalid key, don't continue
        )

        assert "Aborted" in result.output

        # Config should not be created
        config_path = home_dir / ".aurora" / "config.json"
        assert not config_path.exists()

    def test_init_config_already_exists_overwrite_no(self, tmp_path, monkeypatch):
        """Test init when config exists and user chooses not to overwrite."""
        # Mock home directory
        home_dir = tmp_path / "home"
        home_dir.mkdir()
        config_dir = home_dir / ".aurora"
        config_dir.mkdir()
        config_path = config_dir / "config.json"

        # Create existing config
        existing_config = {"llm": {"anthropic_api_key": "sk-ant-existing"}}
        with open(config_path, "w") as f:
            json.dump(existing_config, f)

        monkeypatch.setenv("HOME", str(home_dir))

        runner = CliRunner()
        result = runner.invoke(init_command, input="n\n")  # Don't overwrite

        assert result.exit_code == 0
        assert "Keeping existing config" in result.output

        # Verify config unchanged
        with open(config_path) as f:
            config = json.load(f)

        assert config["llm"]["anthropic_api_key"] == "sk-ant-existing"

    def test_init_config_already_exists_overwrite_yes(self, tmp_path, monkeypatch):
        """Test init when config exists and user chooses to overwrite."""
        # Mock home directory
        home_dir = tmp_path / "home"
        home_dir.mkdir()
        config_dir = home_dir / ".aurora"
        config_dir.mkdir()
        config_path = config_dir / "config.json"

        # Create existing config
        existing_config = {"llm": {"anthropic_api_key": "sk-ant-existing"}}
        with open(config_path, "w") as f:
            json.dump(existing_config, f)

        monkeypatch.setenv("HOME", str(home_dir))

        runner = CliRunner()
        result = runner.invoke(
            init_command,
            input="y\nsk-ant-new123\nn\n",  # Overwrite, new key, don't index
        )

        assert result.exit_code == 0
        assert "Configuration created" in result.output

        # Verify config updated
        with open(config_path) as f:
            config = json.load(f)

        assert config["llm"]["anthropic_api_key"] == "sk-ant-new123"

    def test_init_file_permissions(self, tmp_path, monkeypatch):
        """Test that init sets secure file permissions (0600)."""
        # Mock home directory
        home_dir = tmp_path / "home"
        home_dir.mkdir()
        monkeypatch.setenv("HOME", str(home_dir))

        runner = CliRunner()
        result = runner.invoke(
            init_command,
            input="sk-ant-test123\nn\n",  # API key, don't index
        )

        assert result.exit_code == 0

        # Check file permissions
        config_path = home_dir / ".aurora" / "config.json"
        stat_info = os.stat(config_path)
        permissions = stat_info.st_mode & 0o777

        # Should be 0600 (user read/write only)
        assert permissions == 0o600

    def test_init_permission_error_on_directory_create(self, tmp_path, monkeypatch):
        """Test init handles permission error when creating directory."""
        # Mock home directory
        home_dir = tmp_path / "home"
        home_dir.mkdir()
        monkeypatch.setenv("HOME", str(home_dir))

        # Make home directory read-only
        os.chmod(home_dir, 0o444)

        try:
            runner = CliRunner()
            result = runner.invoke(init_command, input="sk-ant-test123\nn\n")

            # Command may fail with permission error
            # Just check that error handling is present
            assert "Error" in result.output or "Permission" in str(result.exception)
        finally:
            # Restore permissions for cleanup
            os.chmod(home_dir, 0o755)

    def test_init_permission_error_on_file_write(self, tmp_path, monkeypatch):
        """Test init handles permission error when writing config file."""
        # Mock home directory
        home_dir = tmp_path / "home"
        home_dir.mkdir()
        config_dir = home_dir / ".aurora"
        config_dir.mkdir()
        monkeypatch.setenv("HOME", str(home_dir))

        # Make config directory read-only
        os.chmod(config_dir, 0o444)

        try:
            runner = CliRunner()
            result = runner.invoke(init_command, input="sk-ant-test123\nn\n")

            # Command may fail with permission error
            # Just check that error handling is present
            assert "Error" in result.output or "Permission" in str(result.exception)
        finally:
            # Restore permissions for cleanup
            os.chmod(config_dir, 0o755)

    def test_init_with_indexing(self, tmp_path, monkeypatch):
        """Test init with directory indexing (Phase 4 implemented)."""
        # Mock home directory
        home_dir = tmp_path / "home"
        home_dir.mkdir()
        monkeypatch.setenv("HOME", str(home_dir))

        runner = CliRunner()
        result = runner.invoke(
            init_command,
            input="sk-ant-test123\ny\n",  # API key, yes to indexing
        )

        assert result.exit_code == 0
        assert "configuration created" in result.output.lower()

        # Since Phase 4 is now implemented, indexing should work
        # May show "no python files found" if directory is empty, which is fine
        assert (
            "indexing" in result.output.lower() or "no python files found" in result.output.lower()
        )

    def test_init_skip_indexing(self, tmp_path, monkeypatch):
        """Test init skipping directory indexing."""
        # Mock home directory
        home_dir = tmp_path / "home"
        home_dir.mkdir()
        monkeypatch.setenv("HOME", str(home_dir))

        runner = CliRunner()
        result = runner.invoke(
            init_command,
            input="sk-ant-test123\nn\n",  # API key, no to indexing
        )

        assert result.exit_code == 0
        assert "Configuration created" in result.output

        # Should not mention indexing
        assert "Indexing files" not in result.output

    def test_init_displays_summary(self, tmp_path, monkeypatch):
        """Test that init displays summary information."""
        # Mock home directory
        home_dir = tmp_path / "home"
        home_dir.mkdir()
        monkeypatch.setenv("HOME", str(home_dir))

        runner = CliRunner()
        result = runner.invoke(
            init_command,
            input="sk-ant-test123\nn\n",  # API key, don't index
        )

        assert result.exit_code == 0

        # Check for summary sections
        assert "AURORA CLI initialized successfully" in result.output
        assert "Config file:" in result.output
        assert "API key: Configured" in result.output
        assert "Next steps:" in result.output
        assert "aur query" in result.output

    def test_init_displays_no_api_key_in_summary(self, tmp_path, monkeypatch):
        """Test that init summary shows when API key is not configured."""
        # Mock home directory
        home_dir = tmp_path / "home"
        home_dir.mkdir()
        monkeypatch.setenv("HOME", str(home_dir))

        runner = CliRunner()
        result = runner.invoke(init_command, input="\nn\n")  # Skip API key

        assert result.exit_code == 0

        # Check for no API key message
        assert "API key: Not configured" in result.output
        assert "ANTHROPIC_API_KEY" in result.output

    def test_init_config_structure(self, tmp_path, monkeypatch):
        """Test that init creates config with correct structure."""
        # Mock home directory
        home_dir = tmp_path / "home"
        home_dir.mkdir()
        monkeypatch.setenv("HOME", str(home_dir))

        runner = CliRunner()
        result = runner.invoke(
            init_command,
            input="sk-ant-test123\nn\n",  # API key, don't index
        )

        assert result.exit_code == 0

        # Verify config structure
        config_path = home_dir / ".aurora" / "config.json"
        with open(config_path) as f:
            config = json.load(f)

        # Check top-level keys
        assert "version" in config
        assert "llm" in config
        assert "escalation" in config
        assert "memory" in config
        assert "logging" in config

        # Check nested structure
        assert "provider" in config["llm"]
        assert "anthropic_api_key" in config["llm"]
        assert "model" in config["llm"]
        assert "temperature" in config["llm"]
        assert "max_tokens" in config["llm"]

        assert "threshold" in config["escalation"]
        assert "enable_keyword_only" in config["escalation"]
        assert "force_mode" in config["escalation"]

        assert "auto_index" in config["memory"]
        assert "index_paths" in config["memory"]
        assert "chunk_size" in config["memory"]
        assert "overlap" in config["memory"]

        assert "level" in config["logging"]
        assert "file" in config["logging"]

    def test_init_config_has_default_values(self, tmp_path, monkeypatch):
        """Test that init creates config with sensible default values."""
        # Mock home directory
        home_dir = tmp_path / "home"
        home_dir.mkdir()
        monkeypatch.setenv("HOME", str(home_dir))

        runner = CliRunner()
        result = runner.invoke(init_command, input="\nn\n")  # Skip API key

        assert result.exit_code == 0

        # Verify default values
        config_path = home_dir / ".aurora" / "config.json"
        with open(config_path) as f:
            config = json.load(f)

        assert config["version"] == "1.1.0"
        assert config["llm"]["provider"] == "anthropic"
        assert config["llm"]["model"] == "claude-3-5-sonnet-20241022"
        assert config["llm"]["temperature"] == 0.7
        assert config["llm"]["max_tokens"] == 4096
        assert config["escalation"]["threshold"] == 0.7
        assert config["escalation"]["enable_keyword_only"] is False
        assert config["escalation"]["force_mode"] is None
        assert config["memory"]["auto_index"] is True
        assert config["memory"]["index_paths"] == ["."]
        assert config["memory"]["chunk_size"] == 1000
        assert config["memory"]["overlap"] == 200
        assert config["logging"]["level"] == "INFO"
        assert config["logging"]["file"] == "~/.aurora/aurora.log"
