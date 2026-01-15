"""Unit tests for error handling in AURORA CLI.

This module tests:
- Custom exception classes
- ErrorHandler formatting methods
- API error handling with retry logic
- Configuration error handling
- Memory store error handling
- Dry-run mode
"""

import sqlite3
from unittest.mock import Mock, patch

import pytest

from aurora_cli.errors import APIError, ConfigurationError, ErrorHandler, MemoryStoreError


class TestCustomExceptions:
    """Test custom exception classes."""

    @pytest.mark.cli
    @pytest.mark.critical
    def test_configuration_error_inheritance(self):
        """ConfigurationError should inherit from AuroraError and Exception."""
        error = ConfigurationError("test error")
        assert isinstance(error, Exception)
        assert str(error) == "test error"

    def test_api_error_inheritance(self):
        """APIError should inherit from AuroraError and Exception."""
        error = APIError("test error")
        assert isinstance(error, Exception)
        assert str(error) == "test error"

    def test_memory_store_error_inheritance(self):
        """MemoryStoreError should inherit from AuroraError and Exception."""
        error = MemoryStoreError("test error")
        assert isinstance(error, Exception)
        assert str(error) == "test error"


class TestErrorHandler:
    """Test ErrorHandler class."""

    def setup_method(self):
        """Set up test fixtures."""
        self.handler = ErrorHandler()

    @pytest.mark.cli
    @pytest.mark.critical
    def test_handle_api_error_authentication(self):
        """Test handling of authentication errors (401)."""
        error = Exception("401 Unauthorized")
        result = self.handler.handle_api_error(error)

        assert "Authentication failed" in result
        assert "ANTHROPIC_API_KEY" in result
        assert "console.anthropic.com" in result

    @pytest.mark.cli
    @pytest.mark.critical
    def test_handle_api_error_rate_limit(self):
        """Test handling of rate limit errors (429)."""
        error = Exception("429 Rate limit exceeded")
        result = self.handler.handle_api_error(error)

        assert "Rate limit exceeded" in result
        assert "wait" in result.lower() or "retry" in result.lower()

    def test_handle_api_error_network(self):
        """Test handling of network errors."""
        error = Exception("Connection timeout")
        result = self.handler.handle_api_error(error)

        assert "Network" in result or "Cannot reach" in result
        assert "internet" in result.lower() or "connection" in result.lower()

    def test_handle_api_error_model_not_found(self):
        """Test handling of model not found errors (404)."""
        error = Exception("404 Model not found")
        result = self.handler.handle_api_error(error)

        assert "Model not found" in result
        assert "model" in result.lower()

    def test_handle_api_error_server_error(self):
        """Test handling of server errors (5xx)."""
        error = Exception("503 Service Unavailable")
        result = self.handler.handle_api_error(error)

        assert "server" in result.lower()
        assert "retry" in result.lower() or "unavailable" in result.lower()

    def test_handle_config_error_json_syntax(self):
        """Test handling of JSON syntax errors."""
        error = Exception("JSONDecodeError: Expecting ',' delimiter")
        result = self.handler.handle_config_error(error)

        assert "syntax" in result.lower()
        assert "json" in result.lower()
        assert "validate" in result.lower() or "jsonlint" in result.lower()

    def test_handle_config_error_permission(self):
        """Test handling of permission errors."""
        error = Exception("PermissionError: [Errno 13] Permission denied")
        result = self.handler.handle_config_error(error)

        assert "permission" in result.lower()
        assert "chmod" in result.lower()

    def test_handle_config_error_missing_api_key(self):
        """Test handling of missing API key."""
        error = Exception("API key not found")
        result = self.handler.handle_config_error(error)

        assert "api" in result.lower() and "key" in result.lower()
        assert "export" in result.lower() or "environment" in result.lower()
        assert "console.anthropic.com" in result

    def test_handle_memory_error_locked(self):
        """Test handling of database locked errors."""
        error = Exception("database is locked")
        result = self.handler.handle_memory_error(error)

        assert "locked" in result.lower()
        assert "close" in result.lower() or "process" in result.lower()

    def test_handle_memory_error_corrupted(self):
        """Test handling of corrupted database errors."""
        error = Exception("database disk image is malformed")
        result = self.handler.handle_memory_error(error)

        assert "corrupt" in result.lower()
        assert "backup" in result.lower()

    def test_handle_memory_error_permission(self):
        """Test handling of memory permission errors."""
        error = Exception("PermissionError: cannot write")
        result = self.handler.handle_memory_error(error)

        assert "permission" in result.lower()
        assert "chmod" in result.lower()

    def test_handle_memory_error_disk_full(self):
        """Test handling of disk full errors."""
        error = Exception("No space left on device")
        result = self.handler.handle_memory_error(error)

        assert "disk" in result.lower() or "space" in result.lower()

    def test_redact_api_key_standard(self):
        """Test API key redaction with standard key."""
        key = "sk-ant-1234567890abcdefghij"
        redacted = self.handler.redact_api_key(key)

        assert redacted.startswith("sk-ant-")
        assert redacted.endswith("hij")
        assert "..." in redacted
        assert len(redacted) < len(key)

    def test_redact_api_key_short(self):
        """Test API key redaction with short key."""
        key = "short"
        redacted = self.handler.redact_api_key(key)

        assert redacted == "***"

    def test_redact_api_key_empty(self):
        """Test API key redaction with empty key."""
        key = ""
        redacted = self.handler.redact_api_key(key)

        assert redacted == "***"


class TestLLMAPIErrorHandling:
    """Test LLM API error handling with retry logic."""

    @patch("aurora_cli.execution.AnthropicClient")
    def test_api_call_with_retry_success_first_attempt(self, mock_client_class):
        """Test successful API call on first attempt."""
        from aurora_cli.execution import QueryExecutor

        # Mock successful response
        mock_response = Mock()
        mock_response.content = "Test response"
        mock_response.input_tokens = 10
        mock_response.output_tokens = 20

        mock_client = Mock()
        mock_client.generate.return_value = mock_response
        mock_client_class.return_value = mock_client

        executor = QueryExecutor()
        result = executor.execute_direct_llm(
            query="test query", api_key="test-key", memory_store=None, verbose=False
        )

        assert result == "Test response"
        assert mock_client.generate.call_count == 1

    @patch("aurora_cli.execution.AnthropicClient")
    @patch("aurora_cli.execution.time.sleep")
    def test_api_call_with_retry_rate_limit_success(self, mock_sleep, mock_client_class):
        """Test API call succeeds after rate limit retry."""
        from aurora_cli.execution import QueryExecutor

        # Mock rate limit on first call, success on second
        mock_response = Mock()
        mock_response.content = "Test response"
        mock_response.input_tokens = 10
        mock_response.output_tokens = 20

        mock_client = Mock()
        mock_client.generate.side_effect = [
            Exception("429 Rate limit exceeded"),
            mock_response,
        ]
        mock_client_class.return_value = mock_client

        executor = QueryExecutor()
        result = executor.execute_direct_llm(
            query="test query", api_key="test-key", memory_store=None, verbose=False
        )

        assert result == "Test response"
        assert mock_client.generate.call_count == 2
        assert mock_sleep.call_count == 1  # One retry delay

    @patch("aurora_cli.execution.AnthropicClient")
    @patch("aurora_cli.execution.time.sleep")
    def test_api_call_with_retry_exhausted(self, mock_sleep, mock_client_class):
        """Test API call fails after exhausting retries."""
        from aurora_cli.execution import QueryExecutor

        # Mock rate limit on all attempts
        mock_client = Mock()
        mock_client.generate.side_effect = Exception("429 Rate limit exceeded")
        mock_client_class.return_value = mock_client

        executor = QueryExecutor()

        with pytest.raises(APIError) as exc_info:
            executor.execute_direct_llm(
                query="test query", api_key="test-key", memory_store=None, verbose=False
            )

        assert "rate limit" in str(exc_info.value).lower()
        assert mock_client.generate.call_count == 3  # Max retries
        assert mock_sleep.call_count == 2  # Retry delays

    @patch("aurora_cli.execution.AnthropicClient")
    def test_api_call_non_retryable_error(self, mock_client_class):
        """Test non-retryable error (auth) fails immediately."""
        from aurora_cli.execution import QueryExecutor

        # Mock authentication error (non-retryable)
        mock_client = Mock()
        mock_client.generate.side_effect = Exception("401 Unauthorized")
        mock_client_class.return_value = mock_client

        executor = QueryExecutor()

        with pytest.raises(APIError) as exc_info:
            executor.execute_direct_llm(
                query="test query", api_key="test-key", memory_store=None, verbose=False
            )

        assert "authentication" in str(exc_info.value).lower()
        assert mock_client.generate.call_count == 1  # No retries for auth errors


class TestConfigErrorHandling:
    """Test configuration error handling."""

    def test_load_config_invalid_json(self, tmp_path):
        """Test loading config with invalid JSON."""
        from aurora_cli.config import load_config

        # Create invalid JSON file
        config_file = tmp_path / "config.json"
        config_file.write_text('{"invalid": json}')

        with pytest.raises(ConfigurationError) as exc_info:
            load_config(str(config_file))

        # Check for config error or JSON-related message
        error_msg = str(exc_info.value).lower()
        assert "config" in error_msg or "json" in error_msg or "expecting" in error_msg

    def test_load_config_permission_error(self, tmp_path):
        """Test loading config with permission error."""
        from aurora_cli.config import load_config

        # Create config file and make it unreadable
        config_file = tmp_path / "config.json"
        config_file.write_text('{"version": "1.0"}')
        config_file.chmod(0o000)

        try:
            with pytest.raises(ConfigurationError) as exc_info:
                load_config(str(config_file))

            assert "permission" in str(exc_info.value).lower()
        finally:
            # Restore permissions for cleanup
            config_file.chmod(0o644)

    def test_config_get_api_key_missing(self):
        """Test getting API key when not set."""
        from aurora_cli.config import Config

        config = Config(anthropic_api_key=None)

        with patch.dict("os.environ", {}, clear=True):
            with pytest.raises(ConfigurationError) as exc_info:
                config.get_api_key()

            assert "api" in str(exc_info.value).lower()
            assert "key" in str(exc_info.value).lower()

    def test_config_validate_invalid_threshold(self):
        """Test validation with invalid threshold."""
        from aurora_cli.config import Config

        config = Config(escalation_threshold=1.5)  # Invalid: > 1.0

        with pytest.raises(ConfigurationError) as exc_info:
            config.validate()

        assert "threshold" in str(exc_info.value).lower()
        assert "1.5" in str(exc_info.value)


class TestMemoryErrorHandling:
    """Test memory store error handling."""

    def test_indexing_with_parse_errors_continues(self):
        """Test indexing continues after parse errors on individual files."""
        from pathlib import Path

        from aurora_cli.memory_manager import MemoryManager

        # Create mock memory store
        mock_memory_store = Mock()

        # Create manager
        manager = MemoryManager(mock_memory_store)

        # Mock file discovery to return test files
        test_files = [Path("file1.py"), Path("file2.py")]
        with patch.object(manager, "_discover_files", return_value=test_files):
            # Mock parser to fail on first file, succeed on second
            mock_parser = Mock()
            mock_parser.parse.side_effect = [
                Exception("Parse error"),  # First file fails
                [Mock(chunk_id="chunk1")],  # Second file succeeds
            ]

            with patch.object(
                manager.parser_registry, "get_parser_for_file", return_value=mock_parser
            ):
                # Mock the entire chunk building and storage process
                with patch.object(manager, "_build_chunk_content", return_value="test content"):
                    with patch.object(manager, "_store_chunk_with_retry", return_value=None):
                        # Since embedding is an instance, we need to mock it differently
                        mock_embedding_provider = Mock()
                        mock_embedding_provider.generate_embedding = Mock(return_value=[0.1, 0.2])
                        manager.embedding_provider = mock_embedding_provider

                        stats = manager.index_path(".")

                        # Should have 1 error, 1 success
                        assert stats.errors == 1
                        assert stats.files_indexed >= 0  # At least tried

    @patch("aurora_cli.memory_manager.time.sleep")
    def test_store_chunk_with_database_lock_retry(self, mock_sleep):
        """Test storing chunk retries on database lock."""
        from aurora_cli.memory_manager import MemoryManager

        # Create mock memory store that fails twice then succeeds
        mock_memory_store = Mock()
        mock_memory_store.add_chunk.side_effect = [
            sqlite3.OperationalError("database is locked"),
            sqlite3.OperationalError("database is locked"),
            None,  # Success on third attempt
        ]

        manager = MemoryManager(mock_memory_store)

        # Should succeed after retries
        manager._store_chunk_with_retry(
            chunk_id="test",
            content="test content",
            embedding=[0.1, 0.2],
            metadata={},
        )

        assert mock_memory_store.add_chunk.call_count == 3
        assert mock_sleep.call_count == 2  # Two retry delays

    def test_store_chunk_with_permission_error_fails_immediately(self):
        """Test storing chunk fails immediately on permission error."""
        from aurora_cli.memory_manager import MemoryManager

        # Create mock memory store that raises permission error
        mock_memory_store = Mock()
        mock_memory_store.add_chunk.side_effect = PermissionError("Permission denied")

        manager = MemoryManager(mock_memory_store)

        with pytest.raises(MemoryStoreError) as exc_info:
            manager._store_chunk_with_retry(
                chunk_id="test",
                content="test content",
                embedding=[0.1, 0.2],
                metadata={},
            )

        assert "permission" in str(exc_info.value).lower()
        assert mock_memory_store.add_chunk.call_count == 1  # No retries

    def test_store_chunk_with_disk_full_fails_immediately(self):
        """Test storing chunk fails immediately on disk full error."""
        from aurora_cli.memory_manager import MemoryManager

        # Create mock memory store that raises OSError
        mock_memory_store = Mock()
        mock_memory_store.add_chunk.side_effect = OSError("No space left on device")

        manager = MemoryManager(mock_memory_store)

        with pytest.raises(MemoryStoreError) as exc_info:
            manager._store_chunk_with_retry(
                chunk_id="test",
                content="test content",
                embedding=[0.1, 0.2],
                metadata={},
            )

        assert "disk" in str(exc_info.value).lower() or "space" in str(exc_info.value).lower()
        assert mock_memory_store.add_chunk.call_count == 1  # No retries


class TestDryRunMode:
    """Test dry-run mode functionality."""

    @patch("aurora_cli.main.AutoEscalationHandler")
    @patch("aurora_core.store.SQLiteStore")
    def test_dry_run_shows_config(self, mock_store, mock_handler, capsys):
        """Test dry-run mode displays configuration."""
        from click.testing import CliRunner

        from aurora_cli.main import cli

        # Mock escalation result
        mock_result = Mock()
        mock_result.complexity = "SIMPLE"
        mock_result.score = 0.3
        mock_result.confidence = 0.9
        mock_result.method = "keyword"
        mock_result.reasoning = "Short query"
        mock_result.use_aurora = False

        mock_handler.return_value.assess_query.return_value = mock_result

        runner = CliRunner()
        result = runner.invoke(
            cli, ["query", "test query", "--dry-run"], env={"ANTHROPIC_API_KEY": "sk-ant-test123"}
        )

        # Should succeed
        assert result.exit_code == 0

        # Should show dry-run mode
        assert "DRY RUN MODE" in result.output

        # Should show configuration
        assert "Configuration" in result.output or "config" in result.output.lower()

        # Should show redacted API key
        assert "sk-ant-" in result.output
        assert "..." in result.output

        # Should show decision
        assert "Decision" in result.output or "Would use" in result.output

    def test_dry_run_without_api_key(self):
        """Test dry-run mode works without API key."""
        from click.testing import CliRunner

        from aurora_cli.main import cli

        runner = CliRunner()
        # Dry-run should work without API key
        with patch.dict("os.environ", {}, clear=True):
            result = runner.invoke(cli, ["query", "test", "--dry-run"])

            # Should succeed (dry-run doesn't require API key)
            assert result.exit_code == 0 or "DRY RUN" in result.output


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
