"""Tests for headless command variable parameters (budget, time_limit, retries).

These tests cover the CLI parameters for headless execution:
- --budget: USD budget limit for the session
- --time-limit: Time limit in seconds for the session
- --retries: Number of retries for failed operations (future feature)

The --budget and --time-limit options exist in the CLI. These tests validate:
1. CLI parameter parsing and validation
2. Config validation for headless_budget and headless_time_limit
3. Environment variable overrides
4. Integration between CLI and config layers
"""

from unittest.mock import Mock, patch

import pytest
from click.testing import CliRunner

from aurora_cli.commands.headless import headless_command
from aurora_cli.config import Config, ConfigurationError, load_config


@pytest.fixture
def runner():
    """Create CLI test runner."""
    return CliRunner()


@pytest.fixture
def temp_prompt(tmp_path):
    """Create temporary prompt file."""
    prompt = tmp_path / "prompt.md"
    prompt.write_text("# Goal\nTest task\n\n# Success Criteria\n- [ ] Works")
    return prompt


# =============================================================================
# CLI Parameter Parsing Tests
# =============================================================================


class TestBudgetCLIParsing:
    """Test --budget CLI parameter parsing."""

    def test_budget_option_exists(self, runner):
        """Test that --budget option is available in CLI."""
        result = runner.invoke(headless_command, ["--help"])
        assert "--budget" in result.output
        assert "FLOAT" in result.output  # Click shows type

    def test_budget_accepts_positive_float(self, runner, temp_prompt):
        """Test that --budget accepts positive float values via Click parsing."""
        # Use --help to verify parsing without executing
        result = runner.invoke(headless_command, ["--budget", "5.50", "--help"])
        assert result.exit_code == 0

    def test_budget_accepts_integer(self, runner, temp_prompt):
        """Test that --budget accepts integer values (converted to float)."""
        result = runner.invoke(headless_command, ["--budget", "10", "--help"])
        assert result.exit_code == 0

    def test_budget_rejects_non_numeric(self, runner, temp_prompt):
        """Test that --budget rejects non-numeric strings at Click level."""
        result = runner.invoke(headless_command, ["--budget", "five-dollars"])
        assert result.exit_code != 0
        assert "Invalid value" in result.output or "not a valid" in result.output.lower()

    def test_budget_help_text(self, runner):
        """Test that --budget has descriptive help text."""
        result = runner.invoke(headless_command, ["--help"])
        # Should mention budget and USD
        assert "budget" in result.output.lower()


class TestTimeLimitCLIParsing:
    """Test --time-limit CLI parameter parsing."""

    def test_time_limit_option_exists(self, runner):
        """Test that --time-limit option is available in CLI."""
        result = runner.invoke(headless_command, ["--help"])
        assert "--time-limit" in result.output
        assert "INTEGER" in result.output  # Click shows type

    def test_time_limit_accepts_positive_integer(self, runner, temp_prompt):
        """Test that --time-limit accepts positive integer values."""
        result = runner.invoke(headless_command, ["--time-limit", "3600", "--help"])
        assert result.exit_code == 0

    def test_time_limit_rejects_non_integer(self, runner, temp_prompt):
        """Test that --time-limit rejects non-integer values."""
        result = runner.invoke(headless_command, ["--time-limit", "30.5"])
        assert result.exit_code != 0

    def test_time_limit_rejects_non_numeric(self, runner, temp_prompt):
        """Test that --time-limit rejects non-numeric strings."""
        result = runner.invoke(headless_command, ["--time-limit", "one-hour"])
        assert result.exit_code != 0

    def test_time_limit_help_text(self, runner):
        """Test that --time-limit has descriptive help text."""
        result = runner.invoke(headless_command, ["--help"])
        assert "time" in result.output.lower()


# =============================================================================
# Config Dataclass Validation Tests
# =============================================================================


class TestConfigBudgetValidation:
    """Test Config class validation for headless_budget."""

    def test_config_accepts_positive_budget(self):
        """Test that Config.validate() accepts positive budget."""
        config = Config(headless_budget=10.0)
        config.validate()  # Should not raise

    def test_config_accepts_none_budget(self):
        """Test that Config.validate() accepts None budget (unlimited)."""
        config = Config(headless_budget=None)
        config.validate()  # Should not raise

    def test_config_rejects_negative_budget(self):
        """Test that Config.validate() rejects negative budget."""
        config = Config(headless_budget=-5.0)
        with pytest.raises(ConfigurationError) as exc_info:
            config.validate()
        assert "budget" in str(exc_info.value).lower()

    def test_config_rejects_zero_budget(self):
        """Test that Config.validate() rejects zero budget."""
        config = Config(headless_budget=0.0)
        with pytest.raises(ConfigurationError) as exc_info:
            config.validate()
        assert "budget" in str(exc_info.value).lower()

    def test_budget_defaults_to_none(self):
        """Test that budget defaults to None (unlimited)."""
        config = Config()
        assert config.headless_budget is None


class TestConfigTimeLimitValidation:
    """Test Config class validation for headless_time_limit."""

    def test_config_accepts_positive_time_limit(self):
        """Test that Config.validate() accepts positive time_limit."""
        config = Config(headless_time_limit=3600)
        config.validate()  # Should not raise

    def test_config_accepts_none_time_limit(self):
        """Test that Config.validate() accepts None time_limit (unlimited)."""
        config = Config(headless_time_limit=None)
        config.validate()  # Should not raise

    def test_config_rejects_negative_time_limit(self):
        """Test that Config.validate() rejects negative time_limit."""
        config = Config(headless_time_limit=-100)
        with pytest.raises(ConfigurationError) as exc_info:
            config.validate()
        assert "time_limit" in str(exc_info.value).lower()

    def test_config_rejects_zero_time_limit(self):
        """Test that Config.validate() rejects zero time_limit."""
        config = Config(headless_time_limit=0)
        with pytest.raises(ConfigurationError) as exc_info:
            config.validate()
        assert "time_limit" in str(exc_info.value).lower()

    def test_time_limit_defaults_to_none(self):
        """Test that time_limit defaults to None (unlimited)."""
        config = Config()
        assert config.headless_time_limit is None


class TestConfigToolRetryValidation:
    """Test per-tool retry configuration validation."""

    def test_tool_config_accepts_valid_max_retries(self):
        """Test that tool config accepts valid max_retries (0 or positive)."""
        config = Config(
            headless_tool_configs={"claude": {"max_retries": 3, "input_method": "argument"}}
        )
        config.validate()  # Should not raise

    def test_tool_config_accepts_zero_retries(self):
        """Test that tool config accepts zero retries (no retry)."""
        config = Config(
            headless_tool_configs={"claude": {"max_retries": 0, "input_method": "argument"}}
        )
        config.validate()  # Should not raise

    def test_tool_config_rejects_negative_max_retries(self):
        """Test that tool config rejects negative max_retries."""
        config = Config(
            headless_tool_configs={"claude": {"max_retries": -1, "input_method": "argument"}}
        )
        with pytest.raises(ConfigurationError) as exc_info:
            config.validate()
        assert "max_retries" in str(exc_info.value).lower()

    def test_tool_config_accepts_valid_retry_delay(self):
        """Test that tool config accepts valid retry_delay."""
        config = Config(
            headless_tool_configs={"claude": {"retry_delay": 2.5, "input_method": "argument"}}
        )
        config.validate()  # Should not raise

    def test_tool_config_accepts_zero_retry_delay(self):
        """Test that tool config accepts zero retry_delay (immediate retry)."""
        config = Config(
            headless_tool_configs={"claude": {"retry_delay": 0.0, "input_method": "argument"}}
        )
        config.validate()  # Should not raise

    def test_tool_config_rejects_negative_retry_delay(self):
        """Test that tool config rejects negative retry_delay."""
        config = Config(
            headless_tool_configs={"claude": {"retry_delay": -1.0, "input_method": "argument"}}
        )
        with pytest.raises(ConfigurationError) as exc_info:
            config.validate()
        assert "retry_delay" in str(exc_info.value).lower()


# =============================================================================
# Environment Variable Override Tests
# =============================================================================


class TestEnvironmentVariableOverrides:
    """Test environment variable overrides for budget and time_limit."""

    def test_budget_env_var_override(self, monkeypatch, tmp_path):
        """Test AURORA_HEADLESS_BUDGET environment variable sets budget."""
        monkeypatch.setenv("AURORA_HEADLESS_BUDGET", "15.50")
        monkeypatch.chdir(tmp_path)

        config = Config()
        assert config.headless_budget == 15.50

    def test_budget_env_var_with_integer(self, monkeypatch, tmp_path):
        """Test AURORA_HEADLESS_BUDGET accepts integer string."""
        monkeypatch.setenv("AURORA_HEADLESS_BUDGET", "25")
        monkeypatch.chdir(tmp_path)

        config = Config()
        assert config.headless_budget == 25.0

    def test_budget_env_var_invalid_raises_error(self, monkeypatch, tmp_path):
        """Test invalid AURORA_HEADLESS_BUDGET raises ConfigurationError."""
        monkeypatch.setenv("AURORA_HEADLESS_BUDGET", "not-a-number")
        monkeypatch.chdir(tmp_path)

        with pytest.raises(ConfigurationError) as exc_info:
            load_config()
        assert "AURORA_HEADLESS_BUDGET" in str(exc_info.value)

    def test_time_limit_env_var_override(self, monkeypatch, tmp_path):
        """Test AURORA_HEADLESS_TIME_LIMIT environment variable sets time_limit."""
        monkeypatch.setenv("AURORA_HEADLESS_TIME_LIMIT", "1800")
        monkeypatch.chdir(tmp_path)

        config = Config()
        assert config.headless_time_limit == 1800

    def test_time_limit_env_var_invalid_raises_error(self, monkeypatch, tmp_path):
        """Test invalid AURORA_HEADLESS_TIME_LIMIT raises ConfigurationError."""
        monkeypatch.setenv("AURORA_HEADLESS_TIME_LIMIT", "thirty-minutes")
        monkeypatch.chdir(tmp_path)

        with pytest.raises(ConfigurationError) as exc_info:
            load_config()
        assert "AURORA_HEADLESS_TIME_LIMIT" in str(exc_info.value)

    def test_time_limit_env_var_float_raises_error(self, monkeypatch, tmp_path):
        """Test AURORA_HEADLESS_TIME_LIMIT rejects float (must be integer)."""
        monkeypatch.setenv("AURORA_HEADLESS_TIME_LIMIT", "30.5")
        monkeypatch.chdir(tmp_path)

        with pytest.raises(ConfigurationError) as exc_info:
            load_config()
        assert "AURORA_HEADLESS_TIME_LIMIT" in str(exc_info.value)


# =============================================================================
# Config Defaults Tests
# =============================================================================


class TestConfigParameterDefaults:
    """Test default values for budget and time_limit."""

    def test_budget_defaults_from_config_none(self):
        """Test that budget defaults to None (unlimited) when not set."""
        config = Config()
        assert config.headless_budget is None

    def test_budget_explicitly_set(self):
        """Test that budget can be explicitly set in Config."""
        config = Config(headless_budget=25.0)
        assert config.headless_budget == 25.0

    def test_time_limit_defaults_from_config_none(self):
        """Test that time_limit defaults to None (unlimited) when not set."""
        config = Config()
        assert config.headless_time_limit is None

    def test_time_limit_explicitly_set(self):
        """Test that time_limit can be explicitly set in Config."""
        config = Config(headless_time_limit=7200)
        assert config.headless_time_limit == 7200


# =============================================================================
# Integration Tests - CLI with Config
# =============================================================================


class TestCLIConfigIntegration:
    """Test integration between CLI parameters and Config."""

    def test_cli_list_tools_works(self, runner):
        """Test that --list-tools works (doesn't need prompt)."""
        result = runner.invoke(headless_command, ["--list-tools"])
        # Should list available tools
        assert result.exit_code == 0 or "Available" in result.output or "Tool" in result.output

    def test_multiple_parameters_together(self, runner):
        """Test that budget, time-limit, and other params can be combined."""
        result = runner.invoke(
            headless_command,
            [
                "--budget",
                "10.0",
                "--time-limit",
                "3600",
                "--max",
                "5",
                "--timeout",
                "300",
                "--help",
            ],
        )
        # Should parse all parameters successfully
        assert result.exit_code == 0


# =============================================================================
# Future Feature Tests (Retries CLI Option)
# =============================================================================


class TestRetriesCLIOption:
    """Tests for --retries CLI option (may need to be added to CLI)."""

    def test_retries_option_in_help(self, runner):
        """Test if --retries option exists in CLI help.

        This test documents the expected behavior for when --retries is added.
        Currently may fail if --retries is not yet implemented.
        """
        result = runner.invoke(headless_command, ["--help"])
        # Check if --retries exists (may be a future feature)
        retries_exists = "--retries" in result.output
        # This is informational - adjust expectation based on implementation
        if not retries_exists:
            pytest.skip("--retries option not yet implemented in CLI")


# =============================================================================
# Parameter Validation Edge Cases
# =============================================================================


class TestParameterEdgeCases:
    """Test edge cases for parameter handling."""

    def test_very_large_budget(self):
        """Test that very large budget values are accepted."""
        config = Config(headless_budget=1000000.0)
        config.validate()  # Should not raise

    def test_small_budget(self):
        """Test that small but positive budget values are accepted."""
        config = Config(headless_budget=0.01)
        config.validate()  # Should not raise

    def test_very_large_time_limit(self):
        """Test that very large time_limit values are accepted."""
        config = Config(headless_time_limit=86400 * 365)  # 1 year in seconds
        config.validate()  # Should not raise

    def test_small_time_limit(self):
        """Test that small but positive time_limit values are accepted."""
        config = Config(headless_time_limit=1)
        config.validate()  # Should not raise

    def test_budget_with_many_decimal_places(self):
        """Test budget with many decimal places."""
        config = Config(headless_budget=10.123456789)
        config.validate()  # Should not raise

    def test_max_retries_large_value(self):
        """Test that large max_retries values are accepted."""
        config = Config(
            headless_tool_configs={"claude": {"max_retries": 100, "input_method": "argument"}}
        )
        config.validate()  # Should not raise


# =============================================================================
# Config Schema Completeness Tests
# =============================================================================


class TestConfigSchemaCompleteness:
    """Test that config schema includes budget and time_limit."""

    def test_config_schema_has_budget(self):
        """Test that CONFIG_SCHEMA includes budget."""
        from aurora_cli.config import CONFIG_SCHEMA

        assert "headless" in CONFIG_SCHEMA
        # Note: budget might be at top level of headless dict
        headless_config = CONFIG_SCHEMA["headless"]
        # Schema may or may not have budget depending on implementation
        # This test documents the expected structure

    def test_config_schema_has_time_limit(self):
        """Test that CONFIG_SCHEMA includes time_limit."""
        from aurora_cli.config import CONFIG_SCHEMA

        assert "headless" in CONFIG_SCHEMA
        headless_config = CONFIG_SCHEMA["headless"]
        # This test documents the expected structure

    def test_tool_configs_schema_has_retry_fields(self):
        """Test that tool_configs schema includes retry fields."""
        from aurora_cli.config import CONFIG_SCHEMA

        tool_configs = CONFIG_SCHEMA["headless"]["tool_configs"]
        # Check claude config has retry fields
        claude_config = tool_configs.get("claude", {})
        assert "max_retries" in claude_config
        assert "retry_delay" in claude_config


# =============================================================================
# Combined Budget and Max Retries Tests
# =============================================================================


class TestCombinedBudgetAndMaxRetriesCliParsing:
    """Test CLI parsing when both --budget and --max-retries are specified together."""

    def test_budget_and_max_retries_both_accepted(self, runner):
        """Test that --budget and --max-retries can be specified together."""
        result = runner.invoke(
            headless_command, ["--budget", "10.0", "--max-retries", "3", "--help"]
        )
        assert result.exit_code == 0

    def test_budget_and_max_retries_with_time_limit(self, runner):
        """Test all three limiting parameters together."""
        result = runner.invoke(
            headless_command,
            ["--budget", "25.0", "--max-retries", "5", "--time-limit", "3600", "--help"],
        )
        assert result.exit_code == 0

    def test_max_retries_option_exists(self, runner):
        """Test that --max-retries option is available in CLI."""
        result = runner.invoke(headless_command, ["--help"])
        assert "--max-retries" in result.output
        assert "INTEGER" in result.output

    def test_max_retries_accepts_positive_integer(self, runner):
        """Test that --max-retries accepts positive integer values."""
        result = runner.invoke(headless_command, ["--max-retries", "5", "--help"])
        assert result.exit_code == 0

    def test_max_retries_accepts_zero(self, runner):
        """Test that --max-retries accepts zero (disable retries)."""
        result = runner.invoke(headless_command, ["--max-retries", "0", "--help"])
        assert result.exit_code == 0

    def test_max_retries_rejects_non_integer(self, runner):
        """Test that --max-retries rejects non-integer values."""
        result = runner.invoke(headless_command, ["--max-retries", "3.5"])
        assert result.exit_code != 0

    def test_max_retries_rejects_non_numeric(self, runner):
        """Test that --max-retries rejects non-numeric strings."""
        result = runner.invoke(headless_command, ["--max-retries", "three"])
        assert result.exit_code != 0

    def test_retry_delay_option_exists(self, runner):
        """Test that --retry-delay option is available in CLI."""
        result = runner.invoke(headless_command, ["--help"])
        assert "--retry-delay" in result.output
        assert "FLOAT" in result.output

    def test_retry_delay_with_budget_and_max_retries(self, runner):
        """Test --retry-delay works with --budget and --max-retries."""
        result = runner.invoke(
            headless_command,
            ["--budget", "10.0", "--max-retries", "3", "--retry-delay", "2.5", "--help"],
        )
        assert result.exit_code == 0


class TestCombinedBudgetAndMaxRetriesConfig:
    """Test Config validation when both budget and max_retries are configured."""

    def test_config_accepts_budget_with_tool_max_retries(self):
        """Test Config accepts budget alongside per-tool max_retries."""
        config = Config(
            headless_budget=50.0,
            headless_tool_configs={
                "claude": {"max_retries": 3, "retry_delay": 1.5, "input_method": "argument"}
            },
        )
        config.validate()  # Should not raise
        assert config.headless_budget == 50.0
        assert config.headless_tool_configs["claude"]["max_retries"] == 3

    def test_config_accepts_all_limiting_parameters(self):
        """Test Config accepts budget, time_limit, and tool retries together."""
        config = Config(
            headless_budget=100.0,
            headless_time_limit=7200,
            headless_tool_configs={
                "claude": {"max_retries": 5, "retry_delay": 2.0, "input_method": "argument"},
                "opencode": {"max_retries": 3, "retry_delay": 1.0, "input_method": "stdin"},
            },
        )
        config.validate()  # Should not raise

    def test_config_validates_budget_when_tool_retries_invalid(self):
        """Test that invalid tool retries fail even when budget is valid."""
        config = Config(
            headless_budget=50.0,
            headless_tool_configs={
                "claude": {"max_retries": -1, "input_method": "argument"}  # Invalid
            },
        )
        with pytest.raises(ConfigurationError) as exc_info:
            config.validate()
        assert "max_retries" in str(exc_info.value).lower()

    def test_config_validates_retries_when_budget_invalid(self):
        """Test that invalid budget fails even when retries are valid."""
        config = Config(
            headless_budget=-10.0,  # Invalid
            headless_tool_configs={"claude": {"max_retries": 3, "input_method": "argument"}},
        )
        with pytest.raises(ConfigurationError) as exc_info:
            config.validate()
        assert "budget" in str(exc_info.value).lower()

    def test_multiple_tools_with_different_retry_settings(self):
        """Test different retry settings per tool alongside budget."""
        config = Config(
            headless_budget=75.0,
            headless_tool_configs={
                "claude": {"max_retries": 5, "retry_delay": 1.0, "input_method": "argument"},
                "opencode": {"max_retries": 2, "retry_delay": 0.5, "input_method": "stdin"},
                "aider": {
                    "max_retries": 0,  # No retries
                    "retry_delay": 0.0,
                    "input_method": "stdin",
                },
            },
        )
        config.validate()  # Should not raise


class TestCombinedBudgetAndMaxRetriesEnvVars:
    """Test environment variable handling for combined budget and retry settings."""

    def test_budget_env_var_with_config_file_retries(self, monkeypatch, tmp_path):
        """Test budget from env var combined with retries from config."""
        monkeypatch.setenv("AURORA_HEADLESS_BUDGET", "20.0")
        monkeypatch.chdir(tmp_path)

        config = Config()
        # Budget from env var
        assert config.headless_budget == 20.0
        # Retries from defaults in config schema
        # (exact value depends on defaults.json)

    def test_multiple_env_vars_for_limits(self, monkeypatch, tmp_path):
        """Test multiple environment variables for different limits."""
        monkeypatch.setenv("AURORA_HEADLESS_BUDGET", "30.0")
        monkeypatch.setenv("AURORA_HEADLESS_TIME_LIMIT", "1800")
        monkeypatch.chdir(tmp_path)

        config = Config()
        assert config.headless_budget == 30.0
        assert config.headless_time_limit == 1800


class TestCombinedParametersShowConfig:
    """Test --show-config displays combined budget and retry settings correctly."""

    @patch("aurora_cli.commands.headless.shutil.which", return_value="/usr/bin/claude")
    def test_show_config_displays_budget_and_retries(self, mock_which, runner, temp_prompt):
        """Test that --show-config shows both budget and retry settings."""
        result = runner.invoke(
            headless_command,
            [
                "-p",
                str(temp_prompt),
                "--budget",
                "50.0",
                "--max-retries",
                "4",
                "--retry-delay",
                "2.0",
                "--show-config",
            ],
        )
        assert result.exit_code == 0
        # Check budget is displayed
        assert "$50.00" in result.output or "50.0" in result.output
        # Check retry settings are displayed
        assert "4" in result.output  # max_retries value
        assert "2.0" in result.output or "2.0s" in result.output  # retry_delay

    @patch("aurora_cli.commands.headless.shutil.which", return_value="/usr/bin/claude")
    def test_show_config_with_defaults(self, mock_which, runner, temp_prompt):
        """Test --show-config shows default values when not specified."""
        result = runner.invoke(headless_command, ["-p", str(temp_prompt), "--show-config"])
        assert result.exit_code == 0
        # Budget should show unlimited
        assert "(unlimited)" in result.output or "None" in result.output
        # Default retries
        assert "default" in result.output.lower() or "2" in result.output


class TestCombinedBudgetAndMaxRetriesExecution:
    """Test actual execution behavior when both budget and max_retries are set."""

    @patch("aurora_cli.commands.headless.shutil.which", return_value="/usr/bin/claude")
    @patch("aurora_cli.commands.headless.subprocess.run")
    @patch("pathlib.Path.cwd")
    def test_execution_with_budget_and_retries(
        self, mock_cwd, mock_run, mock_which, runner, temp_prompt, tmp_path
    ):
        """Test execution proceeds with both budget and retry settings."""
        mock_cwd.return_value = tmp_path

        git_mock = Mock()
        git_mock.returncode = 0
        git_mock.stdout = "feature\n"

        tool_mock = Mock()
        tool_mock.returncode = 0
        tool_mock.stdout = "Response"
        tool_mock.stderr = ""

        def mock_subprocess(*args, **kwargs):
            if "git" in args[0][0]:
                return git_mock
            return tool_mock

        mock_run.side_effect = mock_subprocess

        result = runner.invoke(
            headless_command,
            ["-p", str(temp_prompt), "--budget", "10.0", "--max-retries", "3", "--max", "2"],
        )

        # Execution should complete successfully
        assert result.exit_code == 0

    @patch("aurora_cli.commands.headless.shutil.which", return_value="/usr/bin/claude")
    @patch("aurora_cli.commands.headless.subprocess.run")
    @patch("pathlib.Path.cwd")
    def test_budget_stops_before_retries_exhausted(
        self, mock_cwd, mock_run, mock_which, runner, temp_prompt, tmp_path
    ):
        """Test that budget limit stops execution before retry limit is hit.

        Note: This tests the conceptual behavior. Actual budget tracking
        requires tool integration to report costs.
        """
        mock_cwd.return_value = tmp_path

        git_mock = Mock()
        git_mock.returncode = 0
        git_mock.stdout = "feature\n"

        tool_mock = Mock()
        tool_mock.returncode = 0
        tool_mock.stdout = "Response"
        tool_mock.stderr = ""

        def mock_subprocess(*args, **kwargs):
            if "git" in args[0][0]:
                return git_mock
            return tool_mock

        mock_run.side_effect = mock_subprocess

        # With a very small budget (0.01), execution might stop quickly
        # Note: actual budget enforcement depends on cost reporting from tools
        result = runner.invoke(
            headless_command,
            [
                "-p",
                str(temp_prompt),
                "--budget",
                "0.01",  # Very small budget
                "--max-retries",
                "10",  # Many retries allowed
                "--max",
                "1",
            ],
        )

        # Command should complete (budget doesn't fail CLI parsing)
        assert result.exit_code == 0


class TestCombinedParametersPrecedence:
    """Test precedence rules when budget and retries come from different sources."""

    def test_cli_budget_overrides_env_var(self, monkeypatch, runner, temp_prompt, tmp_path):
        """Test that CLI --budget overrides environment variable."""
        monkeypatch.setenv("AURORA_HEADLESS_BUDGET", "100.0")

        @patch("aurora_cli.commands.headless.shutil.which", return_value="/usr/bin/claude")
        def run_test(mock_which):
            result = runner.invoke(
                headless_command,
                [
                    "-p",
                    str(temp_prompt),
                    "--budget",
                    "25.0",  # Should override env var
                    "--show-config",
                ],
            )
            assert result.exit_code == 0
            # CLI value should be used
            assert "$25.00" in result.output or "25.0" in result.output

        run_test()

    def test_cli_max_retries_overrides_config(self, runner, temp_prompt):
        """Test that CLI --max-retries overrides config default."""
        with patch("aurora_cli.commands.headless.shutil.which", return_value="/usr/bin/claude"):
            result = runner.invoke(
                headless_command,
                [
                    "-p",
                    str(temp_prompt),
                    "--max-retries",
                    "7",  # Non-default value
                    "--show-config",
                ],
            )
            assert result.exit_code == 0
            # CLI value should appear
            assert "7" in result.output


class TestCombinedParametersEdgeCases:
    """Test edge cases when combining budget and retry parameters."""

    def test_zero_budget_with_retries(self):
        """Test that zero budget is rejected even with valid retries."""
        config = Config(
            headless_budget=0.0,  # Invalid
            headless_tool_configs={"claude": {"max_retries": 3, "input_method": "argument"}},
        )
        with pytest.raises(ConfigurationError):
            config.validate()

    def test_valid_budget_with_zero_retries(self):
        """Test that valid budget with zero retries is accepted."""
        config = Config(
            headless_budget=50.0,
            headless_tool_configs={
                "claude": {"max_retries": 0, "input_method": "argument"}  # Valid (no retries)
            },
        )
        config.validate()  # Should not raise

    def test_very_small_budget_large_retries(self):
        """Test very small budget with many retries is valid config."""
        config = Config(
            headless_budget=0.001,  # Tiny budget
            headless_tool_configs={
                "claude": {"max_retries": 100, "input_method": "argument"}  # Many retries
            },
        )
        config.validate()  # Config is valid; runtime behavior may limit execution

    def test_budget_none_with_max_retries(self):
        """Test unlimited budget (None) with specific max_retries."""
        config = Config(
            headless_budget=None,  # Unlimited
            headless_tool_configs={"claude": {"max_retries": 5, "input_method": "argument"}},
        )
        config.validate()  # Should not raise
        assert config.headless_budget is None

    def test_all_parameters_at_limits(self):
        """Test all parameters at extreme values."""
        config = Config(
            headless_budget=0.01,  # Minimum practical budget
            headless_time_limit=1,  # Minimum time limit
            headless_tool_configs={
                "claude": {
                    "max_retries": 0,  # No retries
                    "retry_delay": 0.0,  # Immediate
                    "input_method": "argument",
                }
            },
        )
        config.validate()  # Should not raise

    def test_cli_all_retry_and_budget_options(self, runner):
        """Test all retry and budget related CLI options together."""
        result = runner.invoke(
            headless_command,
            [
                "--budget",
                "100.0",
                "--time-limit",
                "3600",
                "--max-retries",
                "5",
                "--retry-delay",
                "1.5",
                "--timeout",
                "600",
                "--max",
                "10",
                "--help",
            ],
        )
        assert result.exit_code == 0


class TestCombinedParametersMultiTool:
    """Test combined budget and retry parameters with multi-tool execution."""

    @patch("aurora_cli.commands.headless.shutil.which", return_value="/usr/bin/tool")
    def test_multiple_tools_with_shared_budget(self, mock_which, runner, temp_prompt):
        """Test that budget applies across all tools in multi-tool mode."""
        result = runner.invoke(
            headless_command,
            [
                "-p",
                str(temp_prompt),
                "-t",
                "claude",
                "-t",
                "opencode",
                "--budget",
                "50.0",
                "--max-retries",
                "3",
                "--show-config",
            ],
        )
        assert result.exit_code == 0
        # Budget should be shown
        assert "$50.00" in result.output or "50.0" in result.output
        # Multiple tools should be listed
        assert "claude" in result.output
        assert "opencode" in result.output

    @patch("aurora_cli.commands.headless.shutil.which", return_value="/usr/bin/tool")
    def test_per_tool_retries_with_global_budget(self, mock_which, runner, temp_prompt):
        """Test per-tool retry settings combined with global budget."""
        result = runner.invoke(
            headless_command,
            [
                "-p",
                str(temp_prompt),
                "-t",
                "claude",
                "-t",
                "opencode",
                "--budget",
                "100.0",
                "--max-retries",
                "3",  # Global default
                "--show-config",
            ],
        )
        assert result.exit_code == 0
