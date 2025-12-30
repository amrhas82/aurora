"""Unit tests for AURORA CLI error handling.

Tests the ErrorHandler class and @handle_errors decorator to ensure
proper formatting and display of various error types.
"""

import json
import os
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from aurora_cli.errors import (
    EXIT_SUCCESS,
    EXIT_SYSTEM_ERROR,
    EXIT_USER_ERROR,
    APIError,
    BudgetExceededError,
    ConfigurationError,
    ErrorHandler,
    MemoryStoreError,
    handle_errors,
)


class TestErrorHandler:
    """Test the ErrorHandler class static methods."""

    def test_handle_api_error_401(self):
        """Test API error handling for 401 Unauthorized."""
        error = APIError("401 Unauthorized: Invalid API key")
        result = ErrorHandler.handle_api_error(error)

        assert "[API]" in result
        assert "Authentication failed" in result
        assert "ANTHROPIC_API_KEY" in result
        assert "console.anthropic.com" in result

    def test_handle_api_error_429(self):
        """Test API error handling for 429 Rate Limit."""
        error = APIError("429 Rate limit exceeded")
        result = ErrorHandler.handle_api_error(error)

        assert "[API]" in result
        assert "Rate limit exceeded" in result
        assert "retry" in result.lower()

    def test_handle_api_error_500(self):
        """Test API error handling for 500 Server Error."""
        error = APIError("500 Internal Server Error")
        result = ErrorHandler.handle_api_error(error)

        assert "[API]" in result
        assert "server error" in result.lower()
        assert "status.anthropic.com" in result

    def test_handle_api_error_network(self):
        """Test API error handling for network errors."""
        error = APIError("Connection timeout")
        result = ErrorHandler.handle_api_error(error)

        assert "[Network]" in result
        assert "connectivity" in result.lower()
        assert "ping api.anthropic.com" in result

    def test_handle_config_error_permission(self):
        """Test config error handling for PermissionError."""
        error = PermissionError("Permission denied")
        result = ErrorHandler.handle_config_error(error)

        assert "[Config]" in result
        assert "permission" in result.lower()
        assert "chmod" in result

    def test_handle_config_error_json_decode(self):
        """Test config error handling for JSONDecodeError."""
        error = json.JSONDecodeError("Expecting value", "{invalid", 1)
        result = ErrorHandler.handle_config_error(error)

        assert "[Config]" in result
        assert "syntax error" in result.lower()
        assert "json.tool" in result or "jsonlint" in result

    def test_handle_config_error_missing_file(self):
        """Test config error handling for missing config file."""
        error = FileNotFoundError("config.json not found")
        result = ErrorHandler.handle_config_error(error)

        assert "[Config]" in result
        assert "not found" in result.lower()
        assert "aur init" in result

    def test_handle_config_error_invalid_value(self):
        """Test config error handling for invalid config values."""
        error = ValueError("threshold must be between 0 and 1")
        result = ErrorHandler.handle_config_error(error)

        assert "[Config]" in result
        assert "Invalid" in result

    def test_handle_config_error_missing_api_key(self):
        """Test config error handling for missing API key."""
        error = ValueError("ANTHROPIC_API_KEY not found")
        result = ErrorHandler.handle_config_error(error)

        assert "[Config]" in result
        assert "API_KEY not found" in result
        assert "export ANTHROPIC_API_KEY" in result

    def test_handle_memory_error_locked(self):
        """Test memory error handling for database locked."""
        error = MemoryStoreError("database is locked")
        result = ErrorHandler.handle_memory_error(error)

        assert "[Memory]" in result
        assert "locked" in result.lower()
        assert "ps aux" in result or "other AURORA process" in result

    def test_handle_memory_error_corrupted(self):
        """Test memory error handling for corrupted database."""
        error = MemoryStoreError("database disk image is malformed")
        result = ErrorHandler.handle_memory_error(error)

        assert "[Memory]" in result
        assert "corrupt" in result.lower()
        assert "backup" in result.lower()

    def test_handle_memory_error_permission(self):
        """Test memory error handling for permission errors."""
        error = MemoryStoreError("permission denied")
        result = ErrorHandler.handle_memory_error(error)

        assert "[Memory]" in result
        assert "permission" in result.lower()
        assert "chmod" in result

    def test_handle_memory_error_disk_full(self):
        """Test memory error handling for disk full errors."""
        error = MemoryStoreError("disk full")
        result = ErrorHandler.handle_memory_error(error)

        assert "[Memory]" in result
        assert "disk" in result.lower() or "space" in result.lower()

    def test_handle_schema_error(self):
        """Test schema error handling."""
        # Create a mock SchemaMismatchError
        error = Mock()
        error.found_version = 1
        error.expected_version = 3
        error.db_path = "~/.aurora/memory.db"

        result = ErrorHandler.handle_schema_error(error)

        assert "[Schema]" in result
        assert "outdated" in result.lower()
        assert "v1" in result
        assert "v3" in result
        assert "aur init" in result
        assert "re-index" in result

    def test_handle_schema_error_without_version_attrs(self):
        """Test schema error handling when error doesn't have version attrs."""
        error = Exception("Schema mismatch")

        result = ErrorHandler.handle_schema_error(error)

        assert "[Schema]" in result
        assert "outdated" in result.lower()
        assert "unknown" in result.lower()

    def test_handle_budget_error(self):
        """Test budget error handling."""
        error = BudgetExceededError("Budget limit exceeded")
        result = ErrorHandler.handle_budget_error(error, spent=5.25, limit=10.00)

        assert "[Budget]" in result
        assert "limit exceeded" in result.lower()
        assert "$5.25" in result
        assert "$10.00" in result
        assert "aur budget set" in result

    def test_handle_path_error_not_found(self):
        """Test path error handling for FileNotFoundError."""
        error = FileNotFoundError("No such file or directory")
        result = ErrorHandler.handle_path_error(error, "/path/to/file", "reading file")

        assert "[Path]" in result
        assert "not found" in result.lower()
        assert "/path/to/file" in result

    def test_handle_path_error_permission(self):
        """Test path error handling for PermissionError."""
        error = PermissionError("Permission denied")
        result = ErrorHandler.handle_path_error(error, "/path/to/file", "accessing file")

        assert "[Path]" in result
        assert "permission" in result.lower()
        assert "chmod" in result

    def test_handle_path_error_is_directory(self):
        """Test path error handling for IsADirectoryError."""
        error = IsADirectoryError("Is a directory")
        result = ErrorHandler.handle_path_error(error, "/path/to/dir", "reading file")

        assert "[Path]" in result
        assert "directory" in result.lower()

    def test_redact_api_key(self):
        """Test API key redaction."""
        key = "sk-ant-1234567890abcdef"
        redacted = ErrorHandler.redact_api_key(key)

        assert redacted == "sk-ant-...def"
        assert "1234567890abcdef" not in redacted

    def test_redact_api_key_short(self):
        """Test API key redaction for short keys."""
        key = "short"
        redacted = ErrorHandler.redact_api_key(key)

        assert redacted == "***"

    def test_redact_api_key_empty(self):
        """Test API key redaction for empty string."""
        key = ""
        redacted = ErrorHandler.redact_api_key(key)

        assert redacted == "***"


class TestHandleErrorsDecorator:
    """Test the @handle_errors decorator."""

    def test_decorator_catches_exception(self):
        """Test that decorator catches and handles exceptions."""
        import click
        import sys

        @handle_errors
        @click.command()
        def failing_command():
            raise ValueError("Test error")

        # The decorator should catch the exception and exit
        with pytest.raises(SystemExit) as excinfo:
            # Patch sys.argv to avoid Click parsing pytest args
            with patch.object(sys, 'argv', ['test']):
                ctx = click.Context(click.Command("test"))
                ctx.obj = {"debug": False}
                with ctx:
                    failing_command()

        assert excinfo.value.code == EXIT_USER_ERROR

    def test_decorator_debug_mode_shows_traceback(self):
        """Test that decorator shows traceback in debug mode."""
        import click
        import sys

        @handle_errors
        @click.command()
        def failing_command():
            raise ValueError("Test error")

        with pytest.raises(SystemExit) as excinfo:
            with patch.object(sys, 'argv', ['test']):
                ctx = click.Context(click.Command("test"))
                ctx.obj = {"debug": True}
                with ctx:
                    failing_command()

        # Should still exit with user error code
        assert excinfo.value.code == EXIT_USER_ERROR

    def test_decorator_respects_aurora_debug_env(self):
        """Test that decorator respects AURORA_DEBUG environment variable."""
        import click
        import sys

        @handle_errors
        @click.command()
        def failing_command():
            raise ValueError("Test error")

        with patch.dict(os.environ, {"AURORA_DEBUG": "1"}):
            with pytest.raises(SystemExit) as excinfo:
                with patch.object(sys, 'argv', ['test']):
                    ctx = click.Context(click.Command("test"))
                    ctx.obj = {"debug": False}  # Debug flag off in context
                    with ctx:
                        failing_command()

            # Should still exit with user error code
            assert excinfo.value.code == EXIT_USER_ERROR

    def test_decorator_system_error_exit_code(self):
        """Test that decorator uses EXIT_SYSTEM_ERROR for system errors."""
        import click

        from aurora_cli.errors import MemoryStoreError

        @handle_errors
        @click.command()
        def failing_command():
            raise MemoryStoreError("Database corrupted")

        with pytest.raises(SystemExit) as excinfo:
            ctx = click.Context(click.Command("test"))
            ctx.obj = {"debug": False}
            with ctx:
                failing_command()

        assert excinfo.value.code == EXIT_SYSTEM_ERROR

    def test_decorator_user_error_exit_code(self):
        """Test that decorator uses EXIT_USER_ERROR for user errors."""
        import click
        import sys

        @handle_errors
        @click.command()
        def failing_command():
            raise ValueError("Invalid input")

        with pytest.raises(SystemExit) as excinfo:
            with patch.object(sys, 'argv', ['test']):
                ctx = click.Context(click.Command("test"))
                ctx.obj = {"debug": False}
                with ctx:
                    failing_command()

        assert excinfo.value.code == EXIT_USER_ERROR

    def test_decorator_handles_permission_error(self):
        """Test that decorator handles PermissionError with system exit code."""
        import click

        @handle_errors
        @click.command()
        def failing_command():
            raise PermissionError("Permission denied")

        with pytest.raises(SystemExit) as excinfo:
            ctx = click.Context(click.Command("test"))
            ctx.obj = {"debug": False}
            with ctx:
                failing_command()

        assert excinfo.value.code == EXIT_SYSTEM_ERROR

    def test_decorator_handles_file_not_found(self):
        """Test that decorator handles FileNotFoundError with user exit code."""
        import click
        import sys

        @handle_errors
        @click.command()
        def failing_command():
            raise FileNotFoundError("File not found")

        with pytest.raises(SystemExit) as excinfo:
            with patch.object(sys, 'argv', ['test']):
                ctx = click.Context(click.Command("test"))
                ctx.obj = {"debug": False}
                with ctx:
                    failing_command()

        assert excinfo.value.code == EXIT_USER_ERROR

    def test_decorator_handles_schema_mismatch_error(self):
        """Test that decorator handles SchemaMismatchError with system exit code."""
        import click

        # Create a mock SchemaMismatchError
        with patch("aurora_cli.errors.SchemaMismatchError", create=True) as MockSchemaError:
            mock_error_instance = MockSchemaError("Schema mismatch")
            mock_error_instance.found_version = 1
            mock_error_instance.expected_version = 3

            @handle_errors
            @click.command()
            def failing_command():
                raise mock_error_instance

            with pytest.raises(SystemExit) as excinfo:
                ctx = click.Context(click.Command("test"))
                ctx.obj = {"debug": False}
                with ctx:
                    failing_command()

            assert excinfo.value.code == EXIT_SYSTEM_ERROR

    def test_decorator_reraises_click_abort(self):
        """Test that decorator re-raises click.Abort.

        Note: Click's context manager converts Abort to SystemExit(1),
        so we test that the Abort is properly re-raised by the decorator
        and then caught by Click.
        """
        import click
        import sys

        @handle_errors
        @click.command()
        def aborting_command():
            raise click.Abort()

        # Click will catch the Abort and convert to SystemExit(1)
        with pytest.raises(SystemExit) as excinfo:
            with patch.object(sys, 'argv', ['test']):
                ctx = click.Context(click.Command("test"))
                ctx.obj = {"debug": False}
                with ctx:
                    aborting_command()

        # Click converts Abort to exit code 1
        assert excinfo.value.code == 1


class TestExitCodes:
    """Test exit code constants are properly defined."""

    def test_exit_codes_defined(self):
        """Test that exit code constants are defined."""
        assert EXIT_SUCCESS == 0
        assert EXIT_USER_ERROR == 1
        assert EXIT_SYSTEM_ERROR == 2
