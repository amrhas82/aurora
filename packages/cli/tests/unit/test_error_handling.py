"""Unit tests for error handling in AURORA CLI.

Tests the error handling decorator and ErrorHandler methods to ensure
clean error messages are shown by default and stack traces with --debug.
"""

from unittest.mock import MagicMock, patch

import click
import pytest

from aurora_cli.errors import (
    APIError,
    BudgetExceededError,
    ConfigurationError,
    ErrorHandler,
    MemoryStoreError,
    handle_errors,
)


class TestErrorHandler:
    """Test ErrorHandler class methods."""

    def test_handle_api_error_authentication(self) -> None:
        """Test API error handling for authentication failures."""
        error = APIError("401 Unauthorized")
        handler = ErrorHandler()

        result = handler.handle_api_error(error)

        assert "[API]" in result
        assert "Authentication failed" in result
        assert "ANTHROPIC_API_KEY" in result
        assert "https://console.anthropic.com" in result

    def test_handle_api_error_rate_limit(self) -> None:
        """Test API error handling for rate limit errors."""
        error = APIError("429 Rate limit exceeded")
        handler = ErrorHandler()

        result = handler.handle_api_error(error)

        assert "[API]" in result
        assert "Rate limit exceeded" in result
        assert "Too many requests" in result

    def test_handle_api_error_network(self) -> None:
        """Test API error handling for network errors."""
        error = APIError("Connection timeout")
        handler = ErrorHandler()

        result = handler.handle_api_error(error)

        assert "[Network]" in result
        assert "Cannot reach Anthropic API" in result
        assert "ping api.anthropic.com" in result

    def test_handle_config_error_missing_file(self) -> None:
        """Test config error handling for missing file."""
        error = ConfigurationError("No such file or directory")
        handler = ErrorHandler()

        result = handler.handle_config_error(error)

        assert "[Config]" in result
        assert "not found" in result
        assert "aur init" in result

    def test_handle_config_error_invalid_api_key(self) -> None:
        """Test config error handling for missing API key."""
        error = ConfigurationError("API key not found")
        handler = ErrorHandler()

        result = handler.handle_config_error(error)

        assert "[Config]" in result
        assert "ANTHROPIC_API_KEY" in result
        assert "export ANTHROPIC_API_KEY" in result

    def test_handle_budget_error_with_details(self) -> None:
        """Test budget error handling with spending details."""
        error = BudgetExceededError("Budget exceeded")
        handler = ErrorHandler()

        result = handler.handle_budget_error(error, spent=10.50, limit=10.00)

        assert "[Budget]" in result
        assert "Budget limit exceeded" in result
        assert "$10.50" in result  # Spent amount
        assert "$10.00" in result  # Limit
        assert "aur budget set" in result
        assert "aur budget history" in result

    def test_handle_memory_error_locked(self) -> None:
        """Test memory error handling for locked database."""
        error = MemoryStoreError("Database is locked")
        handler = ErrorHandler()

        result = handler.handle_memory_error(error)

        assert "[Memory]" in result
        assert "locked" in result
        assert "Another AURORA process" in result

    def test_handle_memory_error_corrupted(self) -> None:
        """Test memory error handling for corrupted database."""
        error = MemoryStoreError("Database malformed")
        handler = ErrorHandler()

        result = handler.handle_memory_error(error)

        assert "[Memory]" in result
        assert "corrupted" in result
        assert "rm ~/.aurora/memory.db" in result

    def test_redact_api_key(self) -> None:
        """Test API key redaction for safe display."""
        handler = ErrorHandler()

        # Test normal key
        key = "sk-ant-1234567890abcdef"
        redacted = handler.redact_api_key(key)
        assert redacted == "sk-ant-...def"

        # Test short key
        short_key = "abc"
        redacted_short = handler.redact_api_key(short_key)
        assert redacted_short == "***"

        # Test empty key
        empty = handler.redact_api_key("")
        assert empty == "***"


class TestErrorHandlingDecorator:
    """Test the handle_errors decorator."""

    def test_decorator_without_debug_shows_clean_message(self) -> None:
        """Test that decorator shows clean error message without debug mode."""

        @handle_errors
        def test_function() -> None:
            raise ConfigurationError("Test configuration error")

        # Create context without debug flag
        ctx = click.Context(click.Command("test"))
        ctx.obj = {"debug": False}

        # Mock console output
        with patch("aurora_cli.errors.Console") as mock_console_class:
            mock_console = MagicMock()
            mock_console_class.return_value = mock_console

            with patch("aurora_cli.errors.click.get_current_context") as mock_get_ctx:
                mock_get_ctx.return_value = ctx

                with pytest.raises(SystemExit) as exc_info:
                    test_function()

                # Should exit with code 1
                assert exc_info.value.code == 1

                # Should print clean error message (not full stack trace)
                calls = mock_console.print.call_args_list
                assert len(calls) > 0
                error_output = str(calls[0])
                assert "[Config]" in error_output or "Error" in error_output

    def test_decorator_with_debug_shows_stack_trace(self) -> None:
        """Test that decorator shows stack trace with debug mode."""

        @handle_errors
        def test_function() -> None:
            raise ConfigurationError("Test configuration error")

        # Create context with debug flag
        ctx = click.Context(click.Command("test"))
        ctx.obj = {"debug": True}

        # Mock console and traceback
        with patch("aurora_cli.errors.Console") as mock_console_class:
            mock_console = MagicMock()
            mock_console_class.return_value = mock_console

            with patch("aurora_cli.errors.traceback.print_exc") as mock_traceback:
                with patch("aurora_cli.errors.click.get_current_context") as mock_get_ctx:
                    mock_get_ctx.return_value = ctx

                    with pytest.raises(SystemExit) as exc_info:
                        test_function()

                    # Should exit with code 1
                    assert exc_info.value.code == 1

                    # Should print stack trace
                    mock_traceback.assert_called_once()

                    # Should print debug mode message
                    calls = mock_console.print.call_args_list
                    debug_output = " ".join(str(call) for call in calls)
                    assert "debug mode" in debug_output.lower()

    def test_decorator_handles_budget_error(self) -> None:
        """Test that decorator properly handles BudgetExceededError."""

        @handle_errors
        def test_function() -> None:
            raise BudgetExceededError("Budget limit exceeded")

        ctx = click.Context(click.Command("test"))
        ctx.obj = {"debug": False}

        with patch("aurora_cli.errors.Console") as mock_console_class:
            mock_console = MagicMock()
            mock_console_class.return_value = mock_console

            with patch("aurora_cli.errors.click.get_current_context") as mock_get_ctx:
                mock_get_ctx.return_value = ctx

                with pytest.raises(SystemExit):
                    test_function()

                # Should call handle_budget_error
                calls = mock_console.print.call_args_list
                assert len(calls) > 0
                output = str(calls[0])
                assert "Budget" in output or "budget" in output

    def test_decorator_handles_api_error(self) -> None:
        """Test that decorator properly handles APIError."""

        @handle_errors
        def test_function() -> None:
            raise APIError("401 Unauthorized")

        ctx = click.Context(click.Command("test"))
        ctx.obj = {"debug": False}

        with patch("aurora_cli.errors.Console") as mock_console_class:
            mock_console = MagicMock()
            mock_console_class.return_value = mock_console

            with patch("aurora_cli.errors.click.get_current_context") as mock_get_ctx:
                mock_get_ctx.return_value = ctx

                with pytest.raises(SystemExit):
                    test_function()

                # Should call handle_api_error
                calls = mock_console.print.call_args_list
                assert len(calls) > 0
                output = str(calls[0])
                assert "API" in output or "api" in output

    def test_decorator_reraises_click_abort(self) -> None:
        """Test that decorator re-raises click.Abort."""

        @handle_errors
        def test_function() -> None:
            raise click.Abort()

        ctx = click.Context(click.Command("test"))
        ctx.obj = {"debug": False}

        with patch("aurora_cli.errors.click.get_current_context") as mock_get_ctx:
            mock_get_ctx.return_value = ctx

            # Should re-raise click.Abort, not catch it
            with pytest.raises(click.Abort):
                test_function()

    def test_decorator_handles_generic_error(self) -> None:
        """Test that decorator handles generic exceptions."""

        @handle_errors
        def test_function() -> None:
            raise ValueError("Generic error message")

        ctx = click.Context(click.Command("test"))
        ctx.obj = {"debug": False}

        with patch("aurora_cli.errors.Console") as mock_console_class:
            mock_console = MagicMock()
            mock_console_class.return_value = mock_console

            with patch("aurora_cli.errors.click.get_current_context") as mock_get_ctx:
                mock_get_ctx.return_value = ctx

                with pytest.raises(SystemExit):
                    test_function()

                # Should show generic error with --debug suggestion
                calls = mock_console.print.call_args_list
                assert len(calls) > 0
                output = str(calls[0])
                assert "--debug" in output

    def test_decorator_without_context_object(self) -> None:
        """Test that decorator works when context.obj is None."""

        @handle_errors
        def test_function() -> None:
            raise ValueError("Test error")

        # Create context without obj
        ctx = click.Context(click.Command("test"))
        ctx.obj = None

        with patch("aurora_cli.errors.Console") as mock_console_class:
            mock_console = MagicMock()
            mock_console_class.return_value = mock_console

            with patch("aurora_cli.errors.click.get_current_context") as mock_get_ctx:
                mock_get_ctx.return_value = ctx

                with pytest.raises(SystemExit):
                    test_function()

                # Should still work and show clean error
                calls = mock_console.print.call_args_list
                assert len(calls) > 0


class TestErrorMessages:
    """Test error message formatting and content."""

    def test_budget_error_includes_solutions(self) -> None:
        """Test that budget error includes actionable solutions."""
        handler = ErrorHandler()
        error = BudgetExceededError("Exceeded limit")

        result = handler.handle_budget_error(error, spent=15.0, limit=10.0)

        # Should include multiple solutions
        assert "aur budget set" in result
        assert "aur budget history" in result
        assert "aur budget reset" in result
        assert "--force-direct" in result

    def test_api_error_includes_console_link(self) -> None:
        """Test that API auth error includes console link."""
        handler = ErrorHandler()
        error = APIError("401 Unauthorized")

        result = handler.handle_api_error(error)

        assert "https://console.anthropic.com" in result

    def test_config_error_includes_init_command(self) -> None:
        """Test that config error suggests aur init."""
        handler = ErrorHandler()
        error = ConfigurationError("Config not found")

        result = handler.handle_config_error(error)

        assert "aur init" in result

    def test_memory_error_includes_recovery_steps(self) -> None:
        """Test that memory error includes recovery steps."""
        handler = ErrorHandler()
        error = MemoryStoreError("Database corrupted")

        result = handler.handle_memory_error(error)

        # Should include backup and reset steps
        assert "backup" in result.lower() or "rm" in result
        assert "aur mem index" in result
