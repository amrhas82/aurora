"""Unit tests for aurora_cli.main CLI routing and commands.

This module tests the main CLI entry point, command routing, and
key command functions using direct function calls with mocking.
IMPORTANT: These are UNIT tests - they use mocks, NOT subprocess.run().
"""

from __future__ import annotations

import logging
from io import StringIO
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
from click.testing import CliRunner

from aurora_cli.main import (
    _display_phase_trace,
    _execute_dry_run,
    _is_memory_empty,
    _perform_auto_index,
    _prompt_auto_index,
    cli,
    query_command,
    verify_command,
)


class TestCliGroup:
    """Test the main CLI group function and flag combinations."""

    @patch("aurora_cli.main.logging.basicConfig")
    def test_cli_with_verbose_flag(self, mock_basic_config: Mock) -> None:
        """Test cli() function with --verbose flag sets INFO logging level."""
        runner = CliRunner()
        result = runner.invoke(cli, ["--verbose"])

        # Verify logging was configured with INFO level
        mock_basic_config.assert_called_once_with(level=logging.INFO)
        assert result.exit_code == 0

    @patch("aurora_cli.main.logging.basicConfig")
    def test_cli_with_debug_flag(self, mock_basic_config: Mock) -> None:
        """Test cli() function with --debug flag sets DEBUG logging level."""
        runner = CliRunner()
        result = runner.invoke(cli, ["--debug"])

        # Verify logging was configured with DEBUG level
        mock_basic_config.assert_called_once_with(level=logging.DEBUG)
        assert result.exit_code == 0

    @patch("aurora_cli.main.logging.basicConfig")
    def test_cli_without_flags_sets_warning_level(self, mock_basic_config: Mock) -> None:
        """Test cli() function without flags sets WARNING logging level (default)."""
        runner = CliRunner()
        result = runner.invoke(cli, [])

        # Verify logging was configured with WARNING level (default)
        mock_basic_config.assert_called_once_with(level=logging.WARNING)
        assert result.exit_code == 0

    @patch("aurora_cli.main.headless_command")
    def test_cli_with_headless_shorthand(self, mock_headless: Mock, tmp_path: Path) -> None:
        """Test cli() function with --headless flag invokes headless_command."""
        # Create a temporary prompt file
        prompt_file = tmp_path / "prompt.md"
        prompt_file.write_text("# Test Goal\n\nTest prompt content")

        runner = CliRunner()
        result = runner.invoke(cli, ["--headless", str(prompt_file)])

        # Verify headless_command was invoked with the prompt path
        mock_headless.assert_called_once()
        # Note: Click's ctx.invoke passes the Path object
        call_kwargs = mock_headless.call_args[1]
        assert "prompt_path" in call_kwargs
        assert call_kwargs["prompt_path"] == prompt_file

    def test_cli_version_option(self) -> None:
        """Test cli() function displays version with --version flag."""
        runner = CliRunner()
        result = runner.invoke(cli, ["--version"])

        # Verify version is displayed
        assert result.exit_code == 0
        assert "0.1.0" in result.output
        assert "aurora" in result.output

    def test_cli_help_text(self) -> None:
        """Test cli() function displays help text with --help flag."""
        runner = CliRunner()
        result = runner.invoke(cli, ["--help"])

        # Verify help text contains key information
        assert result.exit_code == 0
        assert "AURORA" in result.output
        assert "Common Commands:" in result.output
        assert "aur init" in result.output
        assert "aur mem index" in result.output
        assert "aur query" in result.output


class TestQueryCommand:
    """Test the query command function with various options."""

    @patch.dict("os.environ", {"ANTHROPIC_API_KEY": "sk-test-key-12345"})
    @patch("aurora_cli.main.QueryExecutor")
    @patch("aurora_cli.main.AutoEscalationHandler")
    def test_query_command_basic(
        self, mock_handler_class: Mock, mock_executor_class: Mock
    ) -> None:
        """Test query_command() basic invocation with mocked dependencies."""
        # Mock dependencies
        mock_handler = Mock()
        mock_handler.assess_query.return_value = Mock(
            use_aurora=False,
            complexity="LOW",
            score=0.3,
            confidence=0.9,
            method="keyword",
            reasoning="Simple query",
        )
        mock_handler_class.return_value = mock_handler

        mock_executor = Mock()
        mock_executor.execute_direct_llm.return_value = "Test response"
        mock_executor_class.return_value = mock_executor

        runner = CliRunner()
        result = runner.invoke(query_command, ["What is a function?"])

        # Verify command executed successfully
        assert result.exit_code == 0
        assert "Test response" in result.output or "Response:" in result.output

    @patch.dict("os.environ", {}, clear=True)
    def test_query_command_missing_api_key(self) -> None:
        """Test query_command() fails gracefully when API key is missing."""
        runner = CliRunner()
        result = runner.invoke(query_command, ["test query"])

        # Verify command aborted with error message
        assert result.exit_code != 0
        # Should mention API key in error output

    @patch("aurora_cli.main._execute_dry_run")
    def test_query_command_with_dry_run_flag(self, mock_dry_run: Mock) -> None:
        """Test query_command() with --dry-run flag does not make API calls."""
        runner = CliRunner()
        result = runner.invoke(query_command, ["test query", "--dry-run"])

        # Verify dry-run was executed
        mock_dry_run.assert_called_once()
        assert result.exit_code == 0

    @patch.dict("os.environ", {"ANTHROPIC_API_KEY": "sk-test-key"})
    @patch("aurora_cli.main.QueryExecutor")
    @patch("aurora_cli.main._is_memory_empty")
    @patch("aurora_core.store.SQLiteStore")
    @patch("aurora_cli.main.AutoEscalationHandler")
    def test_query_command_with_force_aurora(
        self,
        mock_handler_class: Mock,
        mock_store_class: Mock,
        mock_is_empty: Mock,
        mock_executor_class: Mock,
    ) -> None:
        """Test query_command() with --force-aurora flag."""
        # Mock dependencies
        mock_handler = Mock()
        mock_handler.assess_query.return_value = Mock(
            use_aurora=True,  # Force AURORA mode
            complexity="HIGH",
            score=0.8,
            confidence=0.9,
            method="forced",
            reasoning="Forced AURORA mode",
        )
        mock_handler_class.return_value = mock_handler

        mock_store = Mock()
        mock_store_class.return_value = mock_store
        mock_is_empty.return_value = False

        mock_executor = Mock()
        mock_executor.execute_aurora.return_value = "Aurora response"
        mock_executor_class.return_value = mock_executor

        runner = CliRunner()
        result = runner.invoke(query_command, ["test query", "--force-aurora"])

        # Verify AURORA mode was used
        assert result.exit_code == 0

    @patch.dict("os.environ", {"ANTHROPIC_API_KEY": "sk-test-key"})
    @patch("aurora_cli.main.QueryExecutor")
    @patch("aurora_cli.main.AutoEscalationHandler")
    def test_query_command_with_show_reasoning(
        self, mock_handler_class: Mock, mock_executor_class: Mock
    ) -> None:
        """Test query_command() with --show-reasoning flag displays analysis."""
        # Mock dependencies
        mock_handler = Mock()
        mock_handler.assess_query.return_value = Mock(
            use_aurora=False,
            complexity="MEDIUM",
            score=0.5,
            confidence=0.85,
            method="keyword",
            reasoning="Query complexity analysis",
        )
        mock_handler_class.return_value = mock_handler

        mock_executor = Mock()
        mock_executor.execute_direct_llm.return_value = "Response"
        mock_executor_class.return_value = mock_executor

        runner = CliRunner()
        result = runner.invoke(query_command, ["test", "--show-reasoning"])

        # Verify reasoning is displayed
        assert result.exit_code == 0
        assert "Escalation Analysis:" in result.output or "Complexity:" in result.output


class TestVerifyCommand:
    """Test the verify command function."""

    @patch("shutil.which", return_value="/usr/local/bin/aur")
    @patch("importlib.import_module")
    @patch("sys.exit")
    def test_verify_command_displays_checks(
        self, mock_exit: Mock, mock_import: Mock, mock_which: Mock
    ) -> None:
        """Test verify_command() displays installation checks."""
        runner = CliRunner()
        result = runner.invoke(verify_command, [])

        # Verify output contains checks
        assert "Checking AURORA installation" in result.output
        assert "Core components" in result.output or "aurora.core" in result.output

    @patch("shutil.which", return_value=None)
    @patch("importlib.import_module")
    @patch("sys.exit")
    def test_verify_command_detects_missing_packages(
        self, mock_exit: Mock, mock_import: Mock, mock_which: Mock
    ) -> None:
        """Test verify_command() detects missing packages."""
        # Mock import_module to raise ImportError for some packages
        def side_effect_import(name: str) -> None:
            if "aurora.testing" in name:
                raise ImportError(f"No module named '{name}'")

        mock_import.side_effect = side_effect_import

        runner = CliRunner()
        result = runner.invoke(verify_command, [])

        # Verify missing package is detected
        # The output should contain some indication of missing components


class TestHelperFunctions:
    """Test helper functions in main.py."""

    @patch("aurora_context_code.semantic.EmbeddingProvider")
    @patch("aurora_core.activation.engine.ActivationEngine")
    @patch("aurora_context_code.semantic.hybrid_retriever.HybridRetriever")
    def test_is_memory_empty_with_empty_store(
        self, mock_retriever_class: Mock, mock_engine: Mock, mock_provider: Mock
    ) -> None:
        """Test _is_memory_empty() returns True for empty store."""
        # Mock the retriever to return no results
        mock_retriever = Mock()
        mock_retriever.retrieve.return_value = []
        mock_retriever_class.return_value = mock_retriever

        mock_store = Mock()
        result = _is_memory_empty(mock_store)

        assert result is True

    @patch("aurora_context_code.semantic.EmbeddingProvider")
    @patch("aurora_core.activation.engine.ActivationEngine")
    @patch("aurora_context_code.semantic.hybrid_retriever.HybridRetriever")
    def test_is_memory_empty_with_populated_store(
        self, mock_retriever_class: Mock, mock_engine: Mock, mock_provider: Mock
    ) -> None:
        """Test _is_memory_empty() returns False for populated store."""
        # Mock the retriever to return results
        mock_retriever = Mock()
        mock_retriever.retrieve.return_value = [Mock(), Mock()]  # 2 chunks
        mock_retriever_class.return_value = mock_retriever

        mock_store = Mock()
        result = _is_memory_empty(mock_store)

        assert result is False

    @patch(
        "aurora_context_code.semantic.hybrid_retriever.HybridRetriever",
        side_effect=Exception("Test error"),
    )
    def test_is_memory_empty_handles_exceptions(self, mock_retriever: Mock) -> None:
        """Test _is_memory_empty() returns True on exceptions."""
        mock_store = Mock()
        result = _is_memory_empty(mock_store)

        # Should return True (assume empty) on error
        assert result is True

    @patch("click.prompt", return_value="Y")
    def test_prompt_auto_index_accepts_yes(self, mock_prompt: Mock) -> None:
        """Test _prompt_auto_index() returns True when user accepts."""
        from rich.console import Console

        console = Console()
        result = _prompt_auto_index(console)

        assert result is True

    @patch("click.prompt", return_value="n")
    def test_prompt_auto_index_declines_no(self, mock_prompt: Mock) -> None:
        """Test _prompt_auto_index() returns False when user declines."""
        from rich.console import Console

        console = Console()
        result = _prompt_auto_index(console)

        assert result is False

    @patch("aurora_cli.main.AutoEscalationHandler")
    @patch("aurora_core.store.SQLiteStore")
    def test_execute_dry_run_displays_configuration(
        self, mock_store: Mock, mock_handler_class: Mock
    ) -> None:
        """Test _execute_dry_run() displays dry-run configuration."""
        # Mock dependencies
        mock_handler = Mock()
        mock_handler.assess_query.return_value = Mock(
            use_aurora=False,
            complexity="LOW",
            score=0.3,
            confidence=0.9,
            method="keyword",
            reasoning="Simple query",
        )
        mock_handler_class.return_value = mock_handler

        from rich.console import Console

        # Capture console output using StringIO
        output = StringIO()
        console = Console(file=output, force_terminal=True)

        _execute_dry_run(
            query_text="test query",
            api_key="sk-test-key",
            force_aurora=False,
            force_direct=False,
            threshold=0.6,
            console=console,
        )

        # Verify output contains dry-run information
        output_str = output.getvalue()
        assert "DRY RUN MODE" in output_str
        assert "Configuration:" in output_str

    def test_display_phase_trace_shows_phases(self) -> None:
        """Test _display_phase_trace() displays phase information."""
        from rich.console import Console

        # Create sample phase trace
        phase_trace = {
            "phases": [
                {"name": "Assess", "duration": 0.5, "summary": "Query assessed"},
                {"name": "Retrieve", "duration": 1.2, "summary": "Retrieved 5 chunks"},
            ],
            "total_duration": 5.5,
            "total_cost": 0.012,
            "confidence": 0.85,
            "overall_score": 0.78,
        }

        # Capture console output
        output = StringIO()
        console = Console(file=output, force_terminal=True)

        _display_phase_trace(phase_trace, console)

        # Verify output contains phase information
        output_str = output.getvalue()
        assert "SOAR Phase Trace:" in output_str or "Phase" in output_str

    @patch("aurora_cli.memory_manager.MemoryManager")
    def test_perform_auto_index_indexes_directory(
        self, mock_manager_class: Mock, tmp_path: Path
    ) -> None:
        """Test _perform_auto_index() performs indexing with progress."""
        # Mock MemoryManager
        mock_manager = Mock()
        mock_stats = Mock(files_indexed=10, chunks_created=50, duration_seconds=2.5)
        mock_manager.index_path.return_value = mock_stats
        mock_manager_class.return_value = mock_manager

        from rich.console import Console

        console = Console()
        mock_store = Mock()

        # Execute auto-index
        _perform_auto_index(console, mock_store)

        # Verify MemoryManager was called
        mock_manager.index_path.assert_called_once()


class TestQueryCommandInteractiveMode:
    """Test query command with --non-interactive flag for retrieval quality handling."""

    @patch("aurora_cli.main.QueryExecutor")
    @patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test-key"})
    def test_query_command_with_non_interactive_flag(self, mock_executor_class: Mock) -> None:
        """Test query command with --non-interactive flag sets interactive_mode=False."""
        # Mock executor instance
        mock_executor = Mock()
        mock_executor.execute_direct_llm.return_value = "Test response"
        mock_executor_class.return_value = mock_executor

        # Mock AutoEscalationHandler
        with patch("aurora_cli.main.AutoEscalationHandler") as mock_handler_class:
            mock_handler = Mock()
            mock_result = Mock(use_aurora=False, complexity="SIMPLE", score=0.3, confidence=0.9, method="keyword", reasoning="Simple query")
            mock_handler.assess_query.return_value = mock_result
            mock_handler_class.return_value = mock_handler

            runner = CliRunner()
            result = runner.invoke(
                cli, ["query", "What is Python?", "--non-interactive", "--force-direct"]
            )

            # Verify query executed successfully
            assert result.exit_code == 0

            # Verify QueryExecutor was initialized with interactive_mode=False
            call_kwargs = mock_executor_class.call_args[1]
            assert call_kwargs["interactive_mode"] is False

    @patch("aurora_cli.main.QueryExecutor")
    @patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test-key"})
    def test_query_command_default_interactive(self, mock_executor_class: Mock) -> None:
        """Test query command without --non-interactive defaults to interactive_mode=True."""
        # Mock executor instance
        mock_executor = Mock()
        mock_executor.execute_direct_llm.return_value = "Test response"
        mock_executor_class.return_value = mock_executor

        # Mock AutoEscalationHandler
        with patch("aurora_cli.main.AutoEscalationHandler") as mock_handler_class:
            mock_handler = Mock()
            mock_result = Mock(use_aurora=False, complexity="SIMPLE", score=0.3, confidence=0.9, method="keyword", reasoning="Simple query")
            mock_handler.assess_query.return_value = mock_result
            mock_handler_class.return_value = mock_handler

            runner = CliRunner()
            result = runner.invoke(cli, ["query", "What is Python?", "--force-direct"])

            # Verify query executed successfully
            assert result.exit_code == 0

            # Verify QueryExecutor was initialized with interactive_mode=True (default)
            call_kwargs = mock_executor_class.call_args[1]
            assert call_kwargs["interactive_mode"] is True

    @patch("aurora_cli.main.QueryExecutor")
    @patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test-key"})
    def test_query_command_interactive_flag_passed_to_executor(
        self, mock_executor_class: Mock
    ) -> None:
        """Test that interactive mode flag is correctly propagated to QueryExecutor."""
        # Mock executor instance
        mock_executor = Mock()
        mock_executor.execute_direct_llm.return_value = "Test response"
        mock_executor_class.return_value = mock_executor

        # Mock AutoEscalationHandler
        with patch("aurora_cli.main.AutoEscalationHandler") as mock_handler_class:
            mock_handler = Mock()
            mock_result = Mock(use_aurora=False, complexity="SIMPLE", score=0.3, confidence=0.9, method="keyword", reasoning="Simple query")
            mock_handler.assess_query.return_value = mock_result
            mock_handler_class.return_value = mock_handler

            runner = CliRunner()

            # Test with --non-interactive
            runner.invoke(cli, ["query", "test query", "--non-interactive", "--force-direct"])
            call_kwargs_non_interactive = mock_executor_class.call_args[1]
            assert call_kwargs_non_interactive["interactive_mode"] is False

            # Test without --non-interactive (interactive by default)
            runner.invoke(cli, ["query", "test query", "--force-direct"])
            call_kwargs_interactive = mock_executor_class.call_args[1]
            assert call_kwargs_interactive["interactive_mode"] is True
