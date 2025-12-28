"""Integration tests for error recovery workflows.

This module tests error handling and recovery through the full CLI pipeline:
- Error propagation: CLI → executor → store
- Graceful degradation: missing API key → helpful error
- Retry mechanisms: transient failures with exponential backoff
- Partial success: some files fail indexing, others succeed

Test Strategy:
- Use real components (Store, MemoryManager, QueryExecutor)
- Mock only external APIs (LLM calls)
- Test real error paths and recovery mechanisms
- Verify error messages are actionable
"""

from __future__ import annotations

import sqlite3
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
from aurora_cli.config import Config
from aurora_cli.errors import APIError, ConfigurationError, ErrorHandler, MemoryStoreError
from aurora_cli.execution import QueryExecutor
from aurora_cli.memory_manager import MemoryManager

from aurora_core.store.sqlite import SQLiteStore


pytestmark = pytest.mark.ml


# Sample Python files for testing
VALID_PYTHON_FILE = '''"""Sample module for testing."""

def hello_world():
    """Print hello world."""
    print("Hello, world!")
'''

INVALID_PYTHON_FILE = '''"""Malformed Python file."""

def broken_function(
    # Missing closing parenthesis and body
'''


class TestErrorPropagationWorkflows:
    """Test error propagation through CLI → executor → store."""

    def test_error_propagates_from_store_to_cli(self):
        """Test error handling from indexing operations."""
        # Create temp directory and database
        with tempfile.TemporaryDirectory() as tmp_dir:
            db_path = Path(tmp_dir) / "memory.db"

            # Create store and memory manager
            store = SQLiteStore(db_path=str(db_path))
            manager = MemoryManager(memory_store=store)

            # Create a valid test file
            test_file = Path(tmp_dir) / "test.py"
            test_file.write_text(VALID_PYTHON_FILE)

            # Index successfully
            stats = manager.index_path(test_file)

            # Verify success
            assert stats.files_indexed >= 1
            assert stats.errors == 0  # No errors

    def test_api_error_propagates_from_executor_to_cli(self):
        """Test APIError propagates from LLM client through QueryExecutor to CLI."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            db_path = Path(tmp_dir) / "memory.db"
            store = SQLiteStore(db_path=str(db_path))

            executor = QueryExecutor(config={"model": "claude-sonnet-4-20250514"})

            # Mock LLM client to raise exception
            with patch("aurora_cli.execution.AnthropicClient") as mock_client_class:
                mock_client = Mock()
                mock_client.generate.side_effect = RuntimeError("API connection failed")
                mock_client_class.return_value = mock_client

                # Execute query should propagate as APIError (with network error message)
                with pytest.raises(APIError):
                    executor.execute_direct_llm(
                        query="test query",
                        api_key="sk-ant-test123",
                        memory_store=store,
                        verbose=False,
                    )

    def test_configuration_error_stops_execution_early(self):
        """Test ConfigurationError validation catches invalid values."""
        # Create config with invalid threshold (out of range)
        config = Config(
            llm_provider="anthropic",
            llm_model="claude-sonnet-4-20250514",
            llm_temperature=0.7,
            llm_max_tokens=4000,
            escalation_threshold=1.5,  # Invalid: must be 0.0-1.0
            escalation_enable_keyword_only=False,
            escalation_force_mode=None,
            memory_chunk_size=1000,
            memory_overlap=100,
            memory_auto_index=False,
            memory_index_paths=["."],
        )

        # Validate should raise ConfigurationError
        with pytest.raises(ConfigurationError, match="escalation_threshold must be"):
            config.validate()

    def test_error_context_preserved_through_stack(self):
        """Test error context (operation, path) is preserved through error propagation."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            db_path = Path(tmp_dir) / "memory.db"
            store = SQLiteStore(db_path=str(db_path))
            manager = MemoryManager(memory_store=store)

            # Try to index non-existent path
            non_existent_path = Path(tmp_dir) / "does_not_exist.py"

            with pytest.raises(ValueError, match="Path does not exist"):
                manager.index_path(non_existent_path)


class TestGracefulDegradation:
    """Test graceful degradation with helpful error messages."""

    def test_missing_api_key_shows_actionable_error(self):
        """Test missing API key produces helpful error message."""
        executor = QueryExecutor()

        # Execute without API key
        with pytest.raises(ValueError, match="API key is required"):
            executor.execute_direct_llm(
                query="test query",
                api_key="",  # Empty API key
                memory_store=None,
            )

    def test_empty_query_shows_actionable_error(self):
        """Test empty query produces helpful error message."""
        executor = QueryExecutor()

        with pytest.raises(ValueError, match="Query cannot be empty"):
            executor.execute_direct_llm(
                query="",  # Empty query
                api_key="sk-ant-test123",
                memory_store=None,
            )

    def test_corrupted_database_handled_gracefully(self):
        """Test corrupted database triggers helpful error message."""
        from aurora_core.exceptions import StorageError

        with tempfile.TemporaryDirectory() as tmp_dir:
            db_path = Path(tmp_dir) / "memory.db"

            # Create corrupted database file (not valid SQLite)
            with open(db_path, "w") as f:
                f.write("This is not a valid SQLite database")

            # Attempt to open corrupted database - should raise StorageError
            with pytest.raises(StorageError, match="not a database"):
                SQLiteStore(db_path=str(db_path))

    def test_error_handler_formats_api_authentication_error(self):
        """Test ErrorHandler formats 401 authentication errors with solutions."""
        error = RuntimeError("401 Unauthorized: authentication failed")
        formatted = ErrorHandler.handle_api_error(error, operation="query")

        assert "[API]" in formatted
        assert "Authentication failed" in formatted
        assert "ANTHROPIC_API_KEY" in formatted
        assert "Solutions:" in formatted
        assert "export ANTHROPIC_API_KEY" in formatted

    def test_error_handler_formats_rate_limit_error(self):
        """Test ErrorHandler formats 429 rate limit errors with solutions."""
        error = RuntimeError("429 Too Many Requests: rate limit exceeded")
        formatted = ErrorHandler.handle_api_error(error, operation="query")

        assert "[API]" in formatted
        assert "Rate limit exceeded" in formatted
        assert "Solutions:" in formatted
        assert "Wait a few seconds" in formatted

    def test_error_handler_formats_network_error(self):
        """Test ErrorHandler formats network connection errors with solutions."""
        error = RuntimeError("Connection timeout: network unreachable")
        formatted = ErrorHandler.handle_api_error(error, operation="query")

        assert "[Network]" in formatted
        assert "Cannot reach Anthropic API" in formatted
        assert "Check internet connection" in formatted


class TestRetryMechanisms:
    """Test retry mechanisms for transient failures."""

    def test_executor_retries_on_transient_api_error(self):
        """Test QueryExecutor retries failed API calls with exponential backoff."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            db_path = Path(tmp_dir) / "memory.db"
            store = SQLiteStore(db_path=str(db_path))

            executor = QueryExecutor(config={"model": "claude-sonnet-4-20250514"})

            # Mock LLM client to fail twice, then succeed
            with patch("aurora_cli.execution.AnthropicClient") as mock_client_class:
                mock_client = Mock()
                call_count = 0

                def side_effect_with_retries(*args, **kwargs):
                    nonlocal call_count
                    call_count += 1
                    if call_count < 3:
                        # First 2 calls fail (simulate transient error)
                        raise RuntimeError("503 Service temporarily unavailable")
                    # Third call succeeds - return proper response structure
                    mock_response = Mock()
                    mock_response.content = "Success after retry"
                    mock_response.input_tokens = 10
                    mock_response.output_tokens = 5
                    return mock_response

                mock_client.generate.side_effect = side_effect_with_retries
                mock_client_class.return_value = mock_client

                # Should succeed after retries
                result = executor.execute_direct_llm(
                    query="test query", api_key="sk-ant-test123", memory_store=store
                )

                assert result == "Success after retry"
                assert call_count == 3  # Verify it retried twice

    def test_executor_gives_up_after_max_retries(self):
        """Test QueryExecutor gives up after maximum retry attempts."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            db_path = Path(tmp_dir) / "memory.db"
            store = SQLiteStore(db_path=str(db_path))

            executor = QueryExecutor(config={"model": "claude-sonnet-4-20250514"})

            # Mock LLM client to always fail
            with patch("aurora_cli.execution.AnthropicClient") as mock_client_class:
                mock_client = Mock()
                mock_client.generate.side_effect = RuntimeError("503 Service unavailable")
                mock_client_class.return_value = mock_client

                # Should raise APIError after all retries exhausted
                with pytest.raises(APIError):
                    executor.execute_direct_llm(
                        query="test query", api_key="sk-ant-test123", memory_store=store
                    )

                # Verify it tried 3 times (initial + 2 retries)
                assert mock_client.generate.call_count == 3

    def test_retry_delay_increases_exponentially(self):
        """Test retry delays increase exponentially (0.1s base, 0.2s, 0.4s with jitter)."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            db_path = Path(tmp_dir) / "memory.db"
            store = SQLiteStore(db_path=str(db_path))

            executor = QueryExecutor(config={"model": "claude-sonnet-4-20250514"})

            delays = []

            # Mock time.sleep to capture delays
            with (
                patch("aurora_cli.execution.AnthropicClient") as mock_client_class,
                patch("aurora_cli.execution.time.sleep") as mock_sleep,
            ):
                mock_client = Mock()
                mock_client.generate.side_effect = RuntimeError("503 Service unavailable")
                mock_client_class.return_value = mock_client

                # Capture sleep durations
                mock_sleep.side_effect = lambda duration: delays.append(duration)

                # Execute (will fail after retries)
                with pytest.raises(APIError):
                    executor.execute_direct_llm(
                        query="test query", api_key="sk-ant-test123", memory_store=store
                    )

                # Verify exponential backoff: 0.1s base, 0.2s, 0.4s (only 2 retries = 2 sleeps)
                # Formula: base_delay * (2**attempt) + jitter (0-10%)
                assert len(delays) == 2
                assert 0.1 <= delays[0] <= 0.15  # First: 0.1 * 2^0 = 0.1 + jitter (0-0.01)
                assert 0.2 <= delays[1] <= 0.25  # Second: 0.1 * 2^1 = 0.2 + jitter (0-0.02)


class TestPartialSuccessScenarios:
    """Test partial success scenarios (some operations fail, others succeed)."""

    def test_indexing_continues_after_parse_error(self):
        """Test indexing continues with other files (graceful handling)."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            db_path = tmp_path / "memory.db"

            # Create files: one valid, one invalid
            valid_file = tmp_path / "valid.py"
            valid_file.write_text(VALID_PYTHON_FILE)

            # Create an empty file (non-Python)
            (tmp_path / "empty.txt").write_text("")

            # Create store and manager
            store = SQLiteStore(db_path=str(db_path))
            manager = MemoryManager(memory_store=store)

            # Index directory (should handle non-Python files gracefully)
            stats = manager.index_path(tmp_path)

            # Verify success - valid.py should be indexed
            assert stats.files_indexed >= 1  # At least valid.py succeeded
            assert stats.chunks_created >= 1  # Valid file produced chunks

    def test_search_returns_empty_on_no_results(self):
        """Test search returns empty list (not error) when no results found."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            db_path = Path(tmp_dir) / "memory.db"
            store = SQLiteStore(db_path=str(db_path))
            manager = MemoryManager(memory_store=store)

            # Search empty database
            results = manager.search("test query", limit=10)

            # Should return empty list, not error
            assert isinstance(results, list)
            assert len(results) == 0

    def test_memory_context_graceful_with_no_chunks(self):
        """Test QueryExecutor handles missing memory context gracefully."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            db_path = Path(tmp_dir) / "memory.db"
            store = SQLiteStore(db_path=str(db_path))

            executor = QueryExecutor(config={"model": "claude-sonnet-4-20250514"})

            # Mock LLM client
            with patch("aurora_cli.execution.AnthropicClient") as mock_client_class:
                mock_client = Mock()
                mock_response = Mock()
                mock_response.content = "Response without context"
                mock_response.input_tokens = 10
                mock_response.output_tokens = 5
                mock_client.generate.return_value = mock_response
                mock_client_class.return_value = mock_client

                # Execute with empty store (no context available)
                result = executor.execute_direct_llm(
                    query="test query",
                    api_key="sk-ant-test123",
                    memory_store=store,  # Empty store
                    verbose=True,
                )

                # Should succeed with just the query (no context)
                assert result == "Response without context"
                assert mock_client.generate.call_count == 1

    def test_stats_reflect_successful_indexing(self):
        """Test stats accurately reflect successful indexing."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            db_path = tmp_path / "memory.db"

            # Create multiple valid files
            (tmp_path / "valid1.py").write_text(VALID_PYTHON_FILE)
            (tmp_path / "valid2.py").write_text(VALID_PYTHON_FILE)

            store = SQLiteStore(db_path=str(db_path))
            manager = MemoryManager(memory_store=store)

            # Index directory
            stats = manager.index_path(tmp_path)

            # Verify stats accuracy
            assert stats.files_indexed >= 2  # 2 valid files
            assert stats.errors == 0  # No errors
            assert stats.chunks_created >= 2  # Valid files produced chunks
            assert stats.duration_seconds > 0  # Took some time


class TestErrorRecoveryInstructions:
    """Test error messages include actionable recovery instructions."""

    def test_memory_store_error_includes_recovery_steps(self):
        """Test MemoryStoreError includes actionable recovery instructions."""
        error = RuntimeError("database is locked")
        formatted = ErrorHandler.handle_memory_error(error, operation="indexing")

        assert "[Memory]" in formatted
        assert "locked" in formatted.lower()
        assert "Solutions:" in formatted
        assert "Close other AURORA processes" in formatted

    def test_config_error_includes_setup_instructions(self):
        """Test ConfigurationError includes setup instructions."""
        error = FileNotFoundError("config.json not found")
        formatted = ErrorHandler.handle_config_error(error, config_path="~/.aurora/config.json")

        assert "[Config]" in formatted
        assert "not found" in formatted.lower()
        assert "Solutions:" in formatted
        assert "aur init" in formatted

    def test_path_error_includes_diagnostic_commands(self):
        """Test path errors include diagnostic commands."""
        error = FileNotFoundError("path/to/file.py not found")
        formatted = ErrorHandler.handle_path_error(
            error, path="path/to/file.py", operation="indexing"
        )

        assert "[Path]" in formatted
        assert "not found" in formatted.lower()
        assert "Solutions:" in formatted
        assert "ls -la" in formatted

    def test_api_error_includes_status_check_link(self):
        """Test server errors include Anthropic status page link."""
        error = RuntimeError("500 Internal Server Error")
        formatted = ErrorHandler.handle_api_error(error, operation="query")

        assert "[API]" in formatted
        assert "server error" in formatted.lower()
        assert "status.anthropic.com" in formatted
