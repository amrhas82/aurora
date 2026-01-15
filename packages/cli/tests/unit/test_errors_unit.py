"""Unit tests for CLI error handling utilities.

Tests the ErrorHandler class for formatting and handling various error types
with actionable recovery messages.

Pattern: Direct function calls with mocked exceptions (no subprocess, no @patch decorators).
"""

import json

from aurora_cli.errors import (
    APIError,
    AuroraError,
    ConfigurationError,
    ErrorHandler,
    MemoryStoreError,
)


class TestCustomExceptions:
    """Test custom exception classes."""

    def test_aurora_error_base_exception(self):
        """Test AuroraError is base exception for all CLI errors."""
        error = AuroraError("test error")
        assert str(error) == "test error"
        assert isinstance(error, Exception)

    def test_configuration_error_inherits_aurora_error(self):
        """Test ConfigurationError inherits from AuroraError."""
        error = ConfigurationError("config invalid")
        assert str(error) == "config invalid"
        assert isinstance(error, AuroraError)
        assert isinstance(error, Exception)

    def test_api_error_inherits_aurora_error(self):
        """Test APIError inherits from AuroraError."""
        error = APIError("API call failed")
        assert str(error) == "API call failed"
        assert isinstance(error, AuroraError)

    def test_memory_store_error_inherits_aurora_error(self):
        """Test MemoryStoreError inherits from AuroraError."""
        error = MemoryStoreError("database corrupted")
        assert str(error) == "database corrupted"
        assert isinstance(error, AuroraError)


class TestFormatError:
    """Test ErrorHandler.format_error() method."""

    def test_format_error_basic(self):
        """Test basic error formatting without context."""
        error = ValueError("something went wrong")
        result = ErrorHandler.format_error(error)

        assert "ValueError" in result
        assert "something went wrong" in result
        assert "[bold red]Error[/]" in result

    def test_format_error_with_context(self):
        """Test error formatting with context."""
        error = KeyError("missing_key")
        result = ErrorHandler.format_error(error, context="config loading")

        assert "KeyError" in result
        assert "missing_key" in result
        assert "in config loading" in result

    def test_format_error_preserves_error_type(self):
        """Test error type name is included in formatted output."""
        error = RuntimeError("runtime issue")
        result = ErrorHandler.format_error(error)

        assert "RuntimeError" in result


class TestHandleApiError:
    """Test ErrorHandler.handle_api_error() for API errors."""

    def test_handle_api_error_authentication_401(self):
        """Test handling 401 authentication errors."""
        error = Exception("401 Unauthorized: Invalid API key")
        result = ErrorHandler.handle_api_error(error)

        assert "Authentication failed" in result
        assert "ANTHROPIC_API_KEY" in result
        assert "console.anthropic.com" in result

    def test_handle_api_error_rate_limit_429(self):
        """Test handling 429 rate limit errors."""
        error = Exception("429 Too Many Requests - rate limit exceeded")
        result = ErrorHandler.handle_api_error(error)

        assert "Rate limit exceeded" in result
        assert "Wait a few seconds" in result

    def test_handle_api_error_network_connection(self):
        """Test handling network connection errors."""
        error = Exception("Connection timeout: Could not reach api.anthropic.com")
        result = ErrorHandler.handle_api_error(error)

        assert "Cannot reach Anthropic API" in result
        assert "ping api.anthropic.com" in result

    def test_handle_api_error_model_not_found_404(self):
        """Test handling 404 model not found errors."""
        error = Exception("404 Not Found: Model 'invalid-model' does not exist")
        result = ErrorHandler.handle_api_error(error)

        assert "Model not found" in result
        assert "claude-3-5-sonnet" in result

    def test_handle_api_error_server_error_500(self):
        """Test handling 500 server errors."""
        error = Exception("500 Internal Server Error")
        result = ErrorHandler.handle_api_error(error)

        assert "server error" in result
        assert "status.anthropic.com" in result

    def test_handle_api_error_generic(self):
        """Test handling generic API errors."""
        error = Exception("Unknown API error occurred")
        result = ErrorHandler.handle_api_error(error, operation="query execution")

        assert "query execution failed" in result
        assert "Unknown API error occurred" in result


class TestHandleConfigError:
    """Test ErrorHandler.handle_config_error() for configuration errors."""

    def test_handle_config_error_permission_denied(self):
        """Test handling PermissionError for config files."""
        error = PermissionError("Permission denied: ~/.aurora/config.json")
        result = ErrorHandler.handle_config_error(error)

        assert "Cannot read configuration file" in result
        assert "chmod 600" in result

    def test_handle_config_error_json_decode_error(self):
        """Test handling JSON decode errors."""
        error = json.JSONDecodeError("Expecting value", "{invalid", 0)
        result = ErrorHandler.handle_config_error(error)

        assert "Config file syntax error" in result
        assert "jsonlint" in result or "json.tool" in result

    def test_handle_config_error_file_not_found(self):
        """Test handling missing config file errors."""
        error = FileNotFoundError("No such file or directory: ~/.aurora/config.json")
        result = ErrorHandler.handle_config_error(error)

        assert "Configuration file not found" in result
        assert "aur init" in result

    def test_handle_config_error_invalid_threshold_value(self):
        """Test handling invalid config value errors."""
        error = ValueError("threshold must be between 0 and 1, got 1.5")
        result = ErrorHandler.handle_config_error(error)

        assert "Invalid configuration value" in result
        assert "threshold" in result

    def test_handle_config_error_missing_api_key(self):
        """Test handling missing API key errors."""
        error = ValueError("API key not found in config or environment")
        result = ErrorHandler.handle_config_error(error)

        assert "ANTHROPIC_API_KEY not found" in result
        assert "export ANTHROPIC_API_KEY" in result

    def test_handle_config_error_generic(self):
        """Test handling generic config errors."""
        error = Exception("Unknown configuration error")
        result = ErrorHandler.handle_config_error(error, config_path="/custom/config.json")

        assert "Configuration error" in result
        assert "aur init" in result
        assert "/custom/config.json" in result


class TestHandleMemoryError:
    """Test ErrorHandler.handle_memory_error() for memory store errors."""

    def test_handle_memory_error_database_locked(self):
        """Test handling database locked errors."""
        error = Exception("database is locked")
        result = ErrorHandler.handle_memory_error(error)

        assert "Memory store is locked" in result
        assert "Another AURORA process" in result

    def test_handle_memory_error_corrupted_database(self):
        """Test handling corrupted database errors."""
        error = Exception("database disk image is malformed")
        result = ErrorHandler.handle_memory_error(error)

        assert "Memory store is corrupted" in result
        assert "Backup current database" in result

    def test_handle_memory_error_permission_denied(self):
        """Test handling permission denied errors."""
        error = Exception("permission denied: cannot write to ~/.aurora/memory.db")
        result = ErrorHandler.handle_memory_error(error)

        assert "Cannot write to memory store" in result
        assert "chmod 700" in result

    def test_handle_memory_error_disk_full(self):
        """Test handling disk full errors."""
        error = Exception("disk full: no space left on device")
        result = ErrorHandler.handle_memory_error(error)

        assert "Disk full" in result
        assert "du -sh" in result

    def test_handle_memory_error_parse_error(self):
        """Test handling parse errors (non-fatal)."""
        error = Exception("SyntaxError: invalid syntax in file.py")
        result = ErrorHandler.handle_memory_error(error, operation="indexing files")

        assert "Parse error during indexing files" in result
        assert "non-fatal" in result

    def test_handle_memory_error_generic(self):
        """Test handling generic memory errors."""
        error = Exception("Unknown memory store error")
        result = ErrorHandler.handle_memory_error(error)

        assert "memory operation failed" in result
        assert "aur mem index" in result


class TestHandleEmbeddingError:
    """Test ErrorHandler.handle_embedding_error() for embedding/ML errors."""

    def test_handle_embedding_error_missing_module(self):
        """Test handling missing ML dependencies."""
        error = ImportError("No module named 'sentence_transformers'")
        result = ErrorHandler.handle_embedding_error(error)

        assert "ML dependencies not installed" in result
        assert "pip install 'aurora[ml]'" in result

    def test_handle_embedding_error_model_download_failed(self):
        """Test handling model download errors."""
        error = Exception("connection timeout while downloading model")
        result = ErrorHandler.handle_embedding_error(error)

        assert "Cannot download embedding model" in result
        assert "sentence_transformers" in result

    def test_handle_embedding_error_insufficient_memory(self):
        """Test handling memory/GPU errors."""
        error = Exception("CUDA out of memory")
        result = ErrorHandler.handle_embedding_error(error)

        assert "Insufficient memory for embeddings" in result
        assert "CPU-only mode" in result

    def test_handle_embedding_error_generic(self):
        """Test handling generic embedding errors."""
        error = Exception("Unknown embedding error")
        result = ErrorHandler.handle_embedding_error(error)

        assert "generating embeddings failed" in result
        assert "pip install 'aurora[ml]'" in result


class TestHandlePathError:
    """Test ErrorHandler.handle_path_error() for file/path errors."""

    def test_handle_path_error_file_not_found(self):
        """Test handling file not found errors."""
        error = FileNotFoundError("No such file or directory: /path/to/file.py")
        result = ErrorHandler.handle_path_error(error, "/path/to/file.py")

        assert "Path not found" in result
        assert "/path/to/file.py" in result

    def test_handle_path_error_permission_denied(self):
        """Test handling permission denied errors."""
        error = PermissionError("Permission denied: /root/file.py")
        result = ErrorHandler.handle_path_error(error, "/root/file.py", operation="reading file")

        assert "Permission denied" in result
        assert "chmod 644" in result
        assert "reading file" in result

    def test_handle_path_error_is_a_directory(self):
        """Test handling 'is a directory' errors."""
        error = IsADirectoryError("Is a directory: /path/to/dir")
        result = ErrorHandler.handle_path_error(error, "/path/to/dir")

        assert "Expected file, found directory" in result
        assert "aur mem index" in result

    def test_handle_path_error_not_a_directory(self):
        """Test handling 'not a directory' errors."""
        error = NotADirectoryError("Not a directory: /path/to/file.py")
        result = ErrorHandler.handle_path_error(error, "/path/to/file.py")

        assert "Expected directory, found file" in result

    def test_handle_path_error_generic(self):
        """Test handling generic path errors."""
        error = Exception("Unknown path error")
        result = ErrorHandler.handle_path_error(error, "/some/path", operation="processing")

        assert "processing failed" in result
        assert "/some/path" in result


class TestRedactApiKey:
    """Test ErrorHandler.redact_api_key() for safe API key display."""

    def test_redact_api_key_standard_format(self):
        """Test redacting standard Anthropic API key."""
        key = "sk-ant-1234567890abcdefghijklmnopqrstuvwxyz"
        result = ErrorHandler.redact_api_key(key)

        assert result == "sk-ant-...xyz"
        assert "1234567890" not in result

    def test_redact_api_key_short_key(self):
        """Test redacting short keys (< 10 chars)."""
        key = "short"
        result = ErrorHandler.redact_api_key(key)

        assert result == "***"

    def test_redact_api_key_empty_string(self):
        """Test redacting empty string."""
        key = ""
        result = ErrorHandler.redact_api_key(key)

        assert result == "***"

    def test_redact_api_key_preserves_prefix_and_suffix(self):
        """Test redacted key shows first 7 and last 3 characters."""
        key = "sk-ant-api-key-1234567890-abc"
        result = ErrorHandler.redact_api_key(key)

        assert result.startswith("sk-ant-")
        assert result.endswith("abc")
        assert "..." in result
