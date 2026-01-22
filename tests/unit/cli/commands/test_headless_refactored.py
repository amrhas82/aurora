"""Unit tests for refactored headless command helper functions.

These tests verify the extracted helper functions work correctly
after refactoring headless_command to reduce complexity.
"""

from unittest.mock import MagicMock, patch

import pytest

from aurora_cli.commands.headless import (
    _apply_cli_tool_overrides,
    _apply_config_defaults,
    _check_git_safety,
    _check_tools_exist,
    _resolve_prompt,
    _validate_headless_params,
)


class TestApplyConfigDefaults:
    """Tests for _apply_config_defaults function."""

    def test_uses_cli_values_when_provided(self):
        """Test that CLI values override config defaults."""
        config = MagicMock()
        config.headless_tools = ["default_tool"]
        config.headless_max_iterations = 10
        config.headless_strategy = "first_success"
        config.headless_parallel = False
        config.headless_timeout = 300
        config.headless_budget = None
        config.headless_time_limit = None
        config.headless_tool_configs = {}
        config.headless_routing_rules = []

        result = _apply_config_defaults(
            config=config,
            tools=("cli_tool",),
            max_iter=20,
            strategy="voting",
            parallel=True,
            timeout=600,
            budget=5.0,
            time_limit=3600,
        )

        assert result["tools_list"] == ["cli_tool"]
        assert result["max_iter"] == 20
        assert result["strategy"] == "voting"
        assert result["parallel"] is True
        assert result["timeout"] == 600
        assert result["budget"] == 5.0
        assert result["time_limit"] == 3600

    def test_uses_config_defaults_when_cli_not_provided(self):
        """Test that config defaults are used when CLI args are None."""
        config = MagicMock()
        config.headless_tools = ["config_tool"]
        config.headless_max_iterations = 15
        config.headless_strategy = "all_complete"
        config.headless_parallel = True
        config.headless_timeout = 450
        config.headless_budget = 10.0
        config.headless_time_limit = 1800
        config.headless_tool_configs = {"config_tool": {"enabled": True}}
        config.headless_routing_rules = [{"pattern": "*"}]

        result = _apply_config_defaults(
            config=config,
            tools=None,
            max_iter=None,
            strategy=None,
            parallel=None,
            timeout=None,
            budget=None,
            time_limit=None,
        )

        assert result["tools_list"] == ["config_tool"]
        assert result["max_iter"] == 15
        assert result["strategy"] == "all_complete"
        assert result["parallel"] is True
        assert result["timeout"] == 450
        assert result["budget"] == 10.0
        assert result["time_limit"] == 1800


class TestApplyCliToolOverrides:
    """Tests for _apply_cli_tool_overrides function."""

    def test_applies_model_to_claude(self):
        """Test that --model flag adds model to claude tool."""
        tools_list = ["claude"]
        overrides = _apply_cli_tool_overrides(
            tools_list=tools_list,
            model="opus-4",
            tool_flags={},
            tool_env={},
            max_retries=None,
            retry_delay=None,
        )

        assert "claude" in overrides
        assert overrides["claude"]["extra_flags"] == ["--model", "opus-4"]

    def test_applies_tool_flags_to_specific_tool(self):
        """Test that --tool-flags applies to specific tool."""
        tools_list = ["claude", "opencode"]
        overrides = _apply_cli_tool_overrides(
            tools_list=tools_list,
            model=None,
            tool_flags={"claude": ["--verbose"]},
            tool_env={},
            max_retries=None,
            retry_delay=None,
        )

        assert "claude" in overrides
        assert "--verbose" in overrides["claude"]["extra_flags"]
        assert "opencode" not in overrides

    def test_applies_all_tool_flags_to_all_tools(self):
        """Test that _all tool flags apply to all tools."""
        tools_list = ["claude", "opencode"]
        overrides = _apply_cli_tool_overrides(
            tools_list=tools_list,
            model=None,
            tool_flags={"_all": ["--debug"]},
            tool_env={},
            max_retries=None,
            retry_delay=None,
        )

        assert "claude" in overrides
        assert "opencode" in overrides
        assert "--debug" in overrides["claude"]["extra_flags"]
        assert "--debug" in overrides["opencode"]["extra_flags"]

    def test_applies_tool_env(self):
        """Test that --tool-env applies environment variables."""
        tools_list = ["claude"]
        overrides = _apply_cli_tool_overrides(
            tools_list=tools_list,
            model=None,
            tool_flags={},
            tool_env={"claude": {"ANTHROPIC_MODEL": "opus"}},
            max_retries=None,
            retry_delay=None,
        )

        assert "claude" in overrides
        assert overrides["claude"]["env"] == {"ANTHROPIC_MODEL": "opus"}

    def test_applies_retry_settings(self):
        """Test that retry settings apply to all tools."""
        tools_list = ["claude", "opencode"]
        overrides = _apply_cli_tool_overrides(
            tools_list=tools_list,
            model=None,
            tool_flags={},
            tool_env={},
            max_retries=3,
            retry_delay=2.0,
        )

        assert overrides["claude"]["max_retries"] == 3
        assert overrides["claude"]["retry_delay"] == 2.0
        assert overrides["opencode"]["max_retries"] == 3
        assert overrides["opencode"]["retry_delay"] == 2.0


class TestValidateHeadlessParams:
    """Tests for _validate_headless_params function."""

    def test_valid_params_pass(self):
        """Test that valid parameters don't raise errors."""
        errors = _validate_headless_params(
            max_retries=3,
            retry_delay=1.0,
            budget=10.0,
            time_limit=3600,
            timeout=600,
        )
        assert errors == []

    def test_negative_max_retries_rejected(self):
        """Test that negative max_retries returns error."""
        errors = _validate_headless_params(
            max_retries=-1,
            retry_delay=None,
            budget=None,
            time_limit=None,
            timeout=None,
        )
        assert len(errors) == 1
        assert "max-retries" in errors[0].lower()

    def test_negative_retry_delay_rejected(self):
        """Test that negative retry_delay returns error."""
        errors = _validate_headless_params(
            max_retries=None,
            retry_delay=-1.0,
            budget=None,
            time_limit=None,
            timeout=None,
        )
        assert len(errors) == 1
        assert "retry-delay" in errors[0].lower()

    def test_zero_budget_rejected(self):
        """Test that zero budget returns error."""
        errors = _validate_headless_params(
            max_retries=None,
            retry_delay=None,
            budget=0,
            time_limit=None,
            timeout=None,
        )
        assert len(errors) == 1
        assert "budget" in errors[0].lower()

    def test_zero_time_limit_rejected(self):
        """Test that zero time_limit returns error."""
        errors = _validate_headless_params(
            max_retries=None,
            retry_delay=None,
            budget=None,
            time_limit=0,
            timeout=None,
        )
        assert len(errors) == 1
        assert "time-limit" in errors[0].lower()

    def test_zero_timeout_rejected(self):
        """Test that zero timeout returns error."""
        errors = _validate_headless_params(
            max_retries=None,
            retry_delay=None,
            budget=None,
            time_limit=None,
            timeout=0,
        )
        assert len(errors) == 1
        assert "timeout" in errors[0].lower()

    def test_multiple_errors_collected(self):
        """Test that multiple validation errors are collected."""
        errors = _validate_headless_params(
            max_retries=-1,
            retry_delay=-1.0,
            budget=0,
            time_limit=0,
            timeout=0,
        )
        assert len(errors) == 5


class TestResolvePrompt:
    """Tests for _resolve_prompt function."""

    def test_reads_from_stdin(self):
        """Test that prompt is read from stdin when use_stdin is True."""
        with patch("sys.stdin") as mock_stdin:
            mock_stdin.isatty.return_value = False
            mock_stdin.read.return_value = "stdin prompt"

            prompt, source = _resolve_prompt(
                use_stdin=True,
                prompt_path=None,
            )

            assert prompt == "stdin prompt"
            assert source == "stdin"

    def test_reads_from_file(self, tmp_path):
        """Test that prompt is read from file."""
        prompt_file = tmp_path / "prompt.md"
        prompt_file.write_text("file prompt")

        prompt, source = _resolve_prompt(
            use_stdin=False,
            prompt_path=prompt_file,
        )

        assert prompt == "file prompt"
        assert source == str(prompt_file)

    def test_stdin_tty_raises_error(self):
        """Test that stdin from TTY raises error."""
        with patch("sys.stdin") as mock_stdin:
            mock_stdin.isatty.return_value = True

            with pytest.raises(ValueError, match="stdin"):
                _resolve_prompt(use_stdin=True, prompt_path=None)

    def test_empty_stdin_raises_error(self):
        """Test that empty stdin raises error."""
        with patch("sys.stdin") as mock_stdin:
            mock_stdin.isatty.return_value = False
            mock_stdin.read.return_value = ""

            with pytest.raises(ValueError, match="[Ee]mpty"):
                _resolve_prompt(use_stdin=True, prompt_path=None)

    def test_missing_file_raises_error(self, tmp_path):
        """Test that missing prompt file raises error."""
        missing_file = tmp_path / "nonexistent.md"

        with pytest.raises(FileNotFoundError):
            _resolve_prompt(use_stdin=False, prompt_path=missing_file)


class TestCheckToolsExist:
    """Tests for _check_tools_exist function."""

    def test_returns_empty_when_all_exist(self):
        """Test that empty list returned when all tools exist."""
        with patch("shutil.which", return_value="/usr/bin/tool"):
            missing = _check_tools_exist(["claude", "opencode"])
            assert missing == []

    def test_returns_missing_tools(self):
        """Test that missing tools are returned."""
        with patch("shutil.which", side_effect=lambda t: None if t == "missing" else "/bin/found"):
            missing = _check_tools_exist(["found", "missing"])
            assert missing == ["missing"]


class TestCheckGitSafety:
    """Tests for _check_git_safety function."""

    def test_main_branch_returns_error(self):
        """Test that main branch returns error."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(stdout="main\n", returncode=0)
            error = _check_git_safety(allow_main=False)
            assert error is not None
            assert "main" in error.lower()

    def test_master_branch_returns_error(self):
        """Test that master branch returns error."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(stdout="master\n", returncode=0)
            error = _check_git_safety(allow_main=False)
            assert error is not None
            assert "main" in error.lower() or "master" in error.lower()

    def test_feature_branch_passes(self):
        """Test that feature branch passes."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(stdout="feature/test\n", returncode=0)
            error = _check_git_safety(allow_main=False)
            assert error is None

    def test_allow_main_bypasses_check(self):
        """Test that allow_main=True bypasses check."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(stdout="main\n", returncode=0)
            error = _check_git_safety(allow_main=True)
            assert error is None

    def test_non_git_repo_passes(self):
        """Test that non-git repo passes (no error)."""
        with patch("subprocess.run") as mock_run:
            from subprocess import CalledProcessError

            mock_run.side_effect = CalledProcessError(128, "git")
            error = _check_git_safety(allow_main=False)
            assert error is None
