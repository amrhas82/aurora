"""Unit tests for CLI init command.

Tests the init_command function for AURORA configuration initialization
with validation, error handling, and user prompts.

Pattern: Direct click.testing.CliRunner with mocked dependencies.
"""

import json
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
from aurora_cli.commands.init import init_command
from click.testing import CliRunner


class TestInitCommandBasic:
    """Test basic init command behavior."""

    def test_init_command_creates_config_directory(self, tmp_path):
        """Test init command creates ~/.aurora directory."""
        runner = CliRunner()

        with runner.isolated_filesystem(temp_dir=tmp_path):
            # Mock home to use temp directory
            with patch("aurora_cli.commands.init.Path.home", return_value=tmp_path):
                runner.invoke(
                    init_command,
                    input="\n",  # Skip API key
                )

                config_dir = tmp_path / ".aurora"
                assert config_dir.exists()
                assert config_dir.is_dir()

    def test_init_command_creates_config_file(self, tmp_path):
        """Test init command creates config.json."""
        runner = CliRunner()

        with runner.isolated_filesystem(temp_dir=tmp_path):
            with patch("aurora_cli.commands.init.Path.home", return_value=tmp_path):
                runner.invoke(
                    init_command,
                    input="\nn\n",  # Skip API key, don't index
                )

                config_file = tmp_path / ".aurora" / "config.json"
                assert config_file.exists()

    def test_init_command_success_message(self, tmp_path):
        """Test init command shows success message."""
        runner = CliRunner()

        with runner.isolated_filesystem(temp_dir=tmp_path):
            with patch("aurora_cli.commands.init.Path.home", return_value=tmp_path):
                result = runner.invoke(
                    init_command,
                    input="\nn\n",  # Skip API key, don't index
                )

                assert "Configuration created" in result.output
                assert "initialized successfully" in result.output


class TestInitCommandExistingConfig:
    """Test init command with existing configuration."""

    def test_init_command_prompts_overwrite_existing_config(self, tmp_path):
        """Test init prompts to overwrite existing config."""
        runner = CliRunner()

        with runner.isolated_filesystem(temp_dir=tmp_path):
            with patch("aurora_cli.commands.init.Path.home", return_value=tmp_path):
                # Create existing config
                config_dir = tmp_path / ".aurora"
                config_dir.mkdir(parents=True, exist_ok=True)
                config_file = config_dir / "config.json"
                config_file.write_text('{"existing": "config"}')

                result = runner.invoke(
                    init_command,
                    input="n\n",  # Don't overwrite
                )

                assert "already exists" in result.output
                assert "Overwrite?" in result.output

    def test_init_command_keeps_existing_config_on_no(self, tmp_path):
        """Test init keeps existing config when user says no."""
        runner = CliRunner()

        with runner.isolated_filesystem(temp_dir=tmp_path):
            with patch("aurora_cli.commands.init.Path.home", return_value=tmp_path):
                # Create existing config
                config_dir = tmp_path / ".aurora"
                config_dir.mkdir(parents=True, exist_ok=True)
                config_file = config_dir / "config.json"
                config_file.write_text('{"existing": "config"}')

                result = runner.invoke(
                    init_command,
                    input="n\n",  # Don't overwrite
                )

                assert "Keeping existing config" in result.output
                # Config should be unchanged
                assert json.loads(config_file.read_text()) == {"existing": "config"}

    def test_init_command_overwrites_config_on_yes(self, tmp_path):
        """Test init overwrites config when user says yes."""
        runner = CliRunner()

        with runner.isolated_filesystem(temp_dir=tmp_path):
            with patch("aurora_cli.commands.init.Path.home", return_value=tmp_path):
                # Create existing config
                config_dir = tmp_path / ".aurora"
                config_dir.mkdir(parents=True, exist_ok=True)
                config_file = config_dir / "config.json"
                config_file.write_text('{"existing": "config"}')

                runner.invoke(
                    init_command,
                    input="y\n\nn\n",  # Yes overwrite, skip API key, no index
                )

                # Config should be new
                new_config = json.loads(config_file.read_text())
                assert "existing" not in new_config
                assert "llm" in new_config


class TestInitCommandApiKey:
    """Test init command API key handling."""

    def test_init_command_prompts_for_api_key(self, tmp_path):
        """Test init prompts for API key."""
        runner = CliRunner()

        with runner.isolated_filesystem(temp_dir=tmp_path):
            with patch("aurora_cli.commands.init.Path.home", return_value=tmp_path):
                result = runner.invoke(
                    init_command,
                    input="\nn\n",  # Skip API key, no index
                )

                assert "Anthropic API key" in result.output

    def test_init_command_accepts_valid_api_key(self, tmp_path):
        """Test init accepts valid API key."""
        runner = CliRunner()

        with runner.isolated_filesystem(temp_dir=tmp_path):
            with patch("aurora_cli.commands.init.Path.home", return_value=tmp_path):
                runner.invoke(
                    init_command,
                    input="sk-ant-test123\nn\n",  # Valid API key, no index
                )

                config_file = tmp_path / ".aurora" / "config.json"
                config = json.loads(config_file.read_text())
                assert config["llm"]["anthropic_api_key"] == "sk-ant-test123"

    def test_init_command_warns_invalid_api_key_format(self, tmp_path):
        """Test init warns about invalid API key format."""
        runner = CliRunner()

        with runner.isolated_filesystem(temp_dir=tmp_path):
            with patch("aurora_cli.commands.init.Path.home", return_value=tmp_path):
                result = runner.invoke(
                    init_command,
                    input="invalid-key\ny\nn\n",  # Invalid key, continue anyway, no index
                )

                assert "should start with 'sk-ant-'" in result.output
                assert "Warning" in result.output or "⚠" in result.output

    def test_init_command_aborts_on_invalid_key_rejection(self, tmp_path):
        """Test init aborts if user rejects invalid key."""
        runner = CliRunner()

        with runner.isolated_filesystem(temp_dir=tmp_path):
            with patch("aurora_cli.commands.init.Path.home", return_value=tmp_path):
                result = runner.invoke(
                    init_command,
                    input="invalid-key\nn\n",  # Invalid key, don't continue
                )

                assert "Aborted" in result.output


class TestInitCommandPermissionErrors:
    """Test init command error handling for permission errors."""

    def test_init_command_handles_directory_permission_error(self, tmp_path):
        """Test init handles permission error creating directory."""
        runner = CliRunner()

        with runner.isolated_filesystem(temp_dir=tmp_path):
            with patch("aurora_cli.commands.init.Path.home", return_value=tmp_path):
                # Mock mkdir to raise PermissionError
                with patch("pathlib.Path.mkdir", side_effect=PermissionError("Permission denied")):
                    result = runner.invoke(
                        init_command,
                        input="\nn\n",  # Skip API key, no index
                    )

                    assert "Permission denied" in result.output or "Cannot" in result.output

    def test_init_command_handles_file_write_permission_error(self, tmp_path):
        """Test init handles permission error writing config file."""
        runner = CliRunner()

        with runner.isolated_filesystem(temp_dir=tmp_path):
            with patch("aurora_cli.commands.init.Path.home", return_value=tmp_path):
                # Create directory but make file write fail
                config_dir = tmp_path / ".aurora"
                config_dir.mkdir(exist_ok=True)

                with patch("builtins.open", side_effect=PermissionError("Cannot write")):
                    result = runner.invoke(
                        init_command,
                        input="\nn\n",  # Skip API key, no index
                    )

                    assert result.exit_code == 0  # Exits gracefully, error handler called


class TestInitCommandConfigSchema:
    """Test init command creates valid config schema."""

    def test_init_command_creates_valid_json(self, tmp_path):
        """Test init creates valid JSON config."""
        runner = CliRunner()

        with runner.isolated_filesystem(temp_dir=tmp_path):
            with patch("aurora_cli.commands.init.Path.home", return_value=tmp_path):
                runner.invoke(
                    init_command,
                    input="\nn\n",  # Skip API key, no index
                )

                config_file = tmp_path / ".aurora" / "config.json"
                # Should not raise JSONDecodeError
                config = json.loads(config_file.read_text())
                assert isinstance(config, dict)

    def test_init_command_includes_llm_section(self, tmp_path):
        """Test init creates config with LLM section."""
        runner = CliRunner()

        with runner.isolated_filesystem(temp_dir=tmp_path):
            with patch("aurora_cli.commands.init.Path.home", return_value=tmp_path):
                runner.invoke(
                    init_command,
                    input="\nn\n",  # Skip API key, no index
                )

                config_file = tmp_path / ".aurora" / "config.json"
                config = json.loads(config_file.read_text())
                assert "llm" in config
                assert isinstance(config["llm"], dict)

    def test_init_command_includes_escalation_section(self, tmp_path):
        """Test init creates config with escalation section."""
        runner = CliRunner()

        with runner.isolated_filesystem(temp_dir=tmp_path):
            with patch("aurora_cli.commands.init.Path.home", return_value=tmp_path):
                runner.invoke(
                    init_command,
                    input="\nn\n",  # Skip API key, no index
                )

                config_file = tmp_path / ".aurora" / "config.json"
                config = json.loads(config_file.read_text())
                assert "escalation" in config
                assert isinstance(config["escalation"], dict)


class TestInitCommandFilePermissions:
    """Test init command sets secure file permissions."""

    def test_init_command_sets_secure_permissions(self, tmp_path):
        """Test init sets 0o600 permissions on config file."""
        runner = CliRunner()

        with runner.isolated_filesystem(temp_dir=tmp_path):
            with patch("aurora_cli.commands.init.Path.home", return_value=tmp_path):
                with patch("os.chmod") as mock_chmod:
                    runner.invoke(
                        init_command,
                        input="\nn\n",  # Skip API key, no index
                    )

                    # Verify chmod was called with 0o600
                    mock_chmod.assert_called()
                    args = mock_chmod.call_args[0]
                    assert args[1] == 0o600

    def test_init_command_handles_chmod_failure(self, tmp_path):
        """Test init handles chmod failure gracefully."""
        runner = CliRunner()

        with runner.isolated_filesystem(temp_dir=tmp_path):
            with patch("aurora_cli.commands.init.Path.home", return_value=tmp_path):
                with patch("os.chmod", side_effect=Exception("chmod failed")):
                    result = runner.invoke(
                        init_command,
                        input="\nn\n",  # Skip API key, no index
                    )

                    # Should show warning but not fail
                    assert "Warning" in result.output or "⚠" in result.output


class TestInitCommandIndexing:
    """Test init command optional indexing."""

    def test_init_command_prompts_for_indexing(self, tmp_path):
        """Test init prompts to index current directory."""
        runner = CliRunner()

        with runner.isolated_filesystem(temp_dir=tmp_path):
            with patch("aurora_cli.commands.init.Path.home", return_value=tmp_path):
                result = runner.invoke(
                    init_command,
                    input="\nn\n",  # Skip API key, decline indexing
                )

                assert "Index current directory" in result.output

    def test_init_command_skips_indexing_on_no(self, tmp_path):
        """Test init skips indexing when user says no."""
        runner = CliRunner()

        with runner.isolated_filesystem(temp_dir=tmp_path):
            with patch("aurora_cli.commands.init.Path.home", return_value=tmp_path):
                result = runner.invoke(
                    init_command,
                    input="\nn\n",  # Skip API key, decline indexing
                )

                # Should complete successfully without indexing
                assert "initialized successfully" in result.output
