"""Error handling utilities for AURORA CLI.

This module defines custom exceptions and error handling utilities
for providing actionable error messages to users.
"""

import functools
import os
import sys
import traceback
from collections.abc import Callable
from pathlib import Path
from typing import Any, TypeVar

import click
from rich.console import Console

F = TypeVar("F", bound=Callable[..., Any])

# Exit code constants
EXIT_SUCCESS = 0
EXIT_USER_ERROR = 1
EXIT_SYSTEM_ERROR = 2


class AuroraError(Exception):
    """Base exception for all AURORA CLI errors."""


class BudgetExceededError(AuroraError):
    """Raised when budget limit is exceeded."""


class ConfigurationError(AuroraError):
    """Raised when configuration is invalid or missing."""


class APIError(AuroraError):
    """Raised when LLM API calls fail."""


class MemoryStoreError(AuroraError):
    """Raised when memory store operations fail."""


class ErrorHandler:
    """Handles formatting and presenting errors to users."""

    @staticmethod
    def format_error(error: Exception, context: str = "") -> str:
        """Format an error with context and actionable guidance.

        Args:
            error: The exception to format
            context: Additional context about where the error occurred

        Returns:
            Formatted error message string

        """
        error_type = type(error).__name__
        error_msg = str(error)

        formatted = f"[bold red]Error[/]: {error_type}"
        if context:
            formatted += f" in {context}"
        formatted += f"\n\n{error_msg}"

        return formatted

    @staticmethod
    def format_error_with_solution(problem: str, solution: str) -> str:
        """Format error with one-line problem and one-line solution.

        Args:
            problem: One-line description of the problem
            solution: One-line description of how to fix it

        Returns:
            Formatted error message string

        """
        return f"{problem}\n{solution}"

    @staticmethod
    def suggest_doctor_check() -> str:
        """Suggest running doctor command for diagnostics.

        Returns:
            Formatted suggestion message

        """
        return "Run 'aur doctor' for diagnostics"

    @staticmethod
    def handle_api_error(error: Exception, operation: str = "API call") -> str:
        """Handle and format API errors with actionable messages.

        Args:
            error: The API exception
            operation: What operation was being attempted

        Returns:
            Formatted error message with recovery steps

        """
        error_str = str(error).lower()

        # Authentication errors
        if "401" in error_str or "unauthorized" in error_str or "authentication" in error_str:
            return (
                "[bold red][API][/] Authentication failed.\n\n"
                "[yellow]Cause:[/] Invalid or missing ANTHROPIC_API_KEY.\n\n"
                "[green]Solutions:[/]\n"
                "  1. Check environment variable:\n"
                "     [cyan]export ANTHROPIC_API_KEY=sk-ant-...[/]\n"
                "  2. Update config file:\n"
                "     [cyan]aur init[/]\n"
                "  3. Get your API key at:\n"
                "     [cyan]https://console.anthropic.com[/]"
            )

        # Rate limit errors
        if "429" in error_str or "rate limit" in error_str:
            return (
                "[bold red][API][/] Rate limit exceeded.\n\n"
                "[yellow]Cause:[/] Too many requests to Anthropic API.\n\n"
                "[green]Solutions:[/]\n"
                "  1. Wait a few seconds and retry\n"
                "  2. Upgrade your API tier for higher limits\n"
                "  3. Use [cyan]--force-direct[/] to skip AURORA overhead"
            )

        # Network errors
        if (
            "connection" in error_str
            or "timeout" in error_str
            or "network" in error_str
            or "dns" in error_str
        ):
            return (
                "[bold red][Network][/] Cannot reach Anthropic API.\n\n"
                "[yellow]Cause:[/] Network connectivity issue.\n\n"
                "[green]Solutions:[/]\n"
                "  1. Check internet connection:\n"
                "     [cyan]ping api.anthropic.com[/]\n"
                "  2. Check firewall/proxy settings\n"
                "  3. Try again in a few moments"
            )

        # Model not found
        if "404" in error_str or "not found" in error_str or "model" in error_str:
            return (
                "[bold red][API][/] Model not found.\n\n"
                "[yellow]Cause:[/] Specified model does not exist or is not accessible.\n\n"
                "[green]Solutions:[/]\n"
                "  1. Check model name in config:\n"
                "     [cyan]~/.aurora/config.json[/]\n"
                "  2. Use default model:\n"
                "     [cyan]claude-3-5-sonnet-20241022[/]\n"
                "  3. See available models at:\n"
                "     [cyan]https://docs.anthropic.com/models[/]"
            )

        # Server errors
        if "500" in error_str or "502" in error_str or "503" in error_str or "server" in error_str:
            return (
                "[bold red][API][/] Anthropic server error.\n\n"
                "[yellow]Cause:[/] Temporary server issue (not your fault).\n\n"
                "[green]Solutions:[/]\n"
                "  1. Retry automatically enabled (3 attempts)\n"
                "  2. Try again in a few minutes\n"
                "  3. Check status: [cyan]https://status.anthropic.com[/]"
            )

        # Generic API error
        return (
            f"[bold red][API][/] {operation} failed.\n\n"
            f"[yellow]Error:[/] {error}\n\n"
            "[green]Solutions:[/]\n"
            "  1. Check your internet connection\n"
            "  2. Verify API key is valid\n"
            "  3. Try again in a few moments"
        )

    @staticmethod
    def handle_config_error(error: Exception, config_path: str = "~/.aurora/config.json") -> str:
        """Handle and format configuration errors with setup instructions.

        Args:
            error: The configuration exception
            config_path: Path to the config file

        Returns:
            Formatted error message with setup instructions

        """
        import json

        error_str = str(error).lower()

        # Check exception type first (more reliable than string matching)

        # Permission errors - check type first!
        if isinstance(error, PermissionError):
            return (
                "[bold red][Config][/] Cannot read configuration file.\n\n"
                f"[yellow]File:[/] {config_path}\n"
                "[yellow]Cause:[/] Check file permissions.\n\n"
                "[green]Solutions:[/]\n"
                "  1. Fix file permissions with chmod 600:\n"
                f"     [cyan]chmod 600 {config_path}[/]\n"
                "  2. Fix directory permissions:\n"
                "     [cyan]chmod 700 ~/.aurora/[/]\n"
                "  3. Recreate config:\n"
                "     [cyan]aur init[/]"
            )

        # JSON decode errors - check type first!
        if isinstance(error, json.JSONDecodeError):
            return (
                "[bold red][Config][/] Config file syntax error.\n\n"
                f"[yellow]File:[/] {config_path}\n"
                f"[yellow]Error:[/] {error}\n\n"
                "[green]Solutions:[/]\n"
                "  1. Validate JSON syntax with jsonlint:\n"
                f"     [cyan]python -m json.tool {config_path}[/]\n"
                "  2. Recreate config file:\n"
                "     [cyan]aur init[/]\n"
                "  3. Use online JSON validator:\n"
                "     [cyan]https://jsonlint.com[/]"
            )

        # Missing config file
        if (
            "no such file" in error_str
            or "file not found" in error_str
            or "does not exist" in error_str
        ):
            return (
                "[bold red][Config][/] Configuration file not found.\n\n"
                f"[yellow]File:[/] {config_path}\n\n"
                "[green]Solutions:[/]\n"
                "  1. Run interactive setup:\n"
                "     [cyan]aur init[/]\n"
                "  2. Create minimal config manually:\n"
                f"     [cyan]mkdir -p ~/.aurora && cat > {config_path} << 'EOF'\n"
                "     {\n"
                '       "llm": {"provider": "anthropic", "model": "claude-3-5-sonnet-20241022"},\n'
                '       "escalation": {"threshold": 0.7}\n'
                "     }\n"
                "     EOF[/]\n"
                "  3. Set ANTHROPIC_API_KEY environment variable:\n"
                "     [cyan]export ANTHROPIC_API_KEY=sk-ant-...[/]"
            )

        # Invalid values
        if "threshold" in error_str or "must be" in error_str:
            return (
                "[bold red][Config][/] Invalid configuration value.\n\n"
                f"[yellow]Error:[/] {error}\n\n"
                "[green]Solutions:[/]\n"
                "  1. Edit config file manually:\n"
                f"     [cyan]nano {config_path}[/]\n"
                "  2. Recreate with defaults:\n"
                "     [cyan]aur init[/]\n"
                "  3. See example config:\n"
                "     [cyan]https://docs.aurora.ai/config[/]"
            )

        # Missing API key
        if "api" in error_str and "key" in error_str:
            return (
                "[bold red][Config][/] ANTHROPIC_API_KEY not found.\n\n"
                "[yellow]Cause:[/] AURORA needs an API key to connect to LLM.\n\n"
                "[green]Solutions:[/]\n"
                "  1. Set environment variable:\n"
                "     [cyan]export ANTHROPIC_API_KEY=sk-ant-...[/]\n"
                "  2. Run interactive setup:\n"
                "     [cyan]aur init[/]\n"
                "  3. Get your API key at:\n"
                "     [cyan]https://console.anthropic.com[/]"
            )

        # Generic config error
        return (
            "[bold red][Config][/] Configuration error.\n\n"
            f"[yellow]Error:[/] {error}\n\n"
            "[green]Solutions:[/]\n"
            "  1. Run setup wizard:\n"
            "     [cyan]aur init[/]\n"
            f"  2. Check config file:\n"
            f"     [cyan]{config_path}[/]\n"
            "  3. Use environment variables"
        )

    @staticmethod
    def handle_memory_error(error: Exception, operation: str = "memory operation") -> str:
        """Handle and format memory store errors with recovery steps.

        Args:
            error: The memory store exception
            operation: What memory operation was being attempted

        Returns:
            Formatted error message with recovery steps

        """
        error_str = str(error).lower()

        # Database locked
        if "locked" in error_str or "busy" in error_str:
            return (
                "[bold red][Memory][/] Memory store is locked.\n\n"
                "[yellow]Cause:[/] Another AURORA process is using the database.\n\n"
                "[green]Solutions:[/]\n"
                "  1. Close other AURORA processes:\n"
                "     [cyan]ps aux | grep aur[/]\n"
                "  2. Wait a few seconds and retry\n"
                "  3. If stuck, remove lock file:\n"
                "     [cyan]rm ~/.aurora/memory.db-wal[/]"
            )

        # Corrupted database
        if "corrupt" in error_str or "malformed" in error_str or "database" in error_str:
            return (
                "[bold red][Memory][/] Memory store is corrupted.\n\n"
                "[yellow]Cause:[/] Database file may be damaged.\n\n"
                "[green]Solutions:[/]\n"
                "  1. Backup current database:\n"
                "     [cyan]cp ~/.aurora/memory.db ~/.aurora/memory.db.backup[/]\n"
                "  2. Reset memory store:\n"
                "     [cyan]rm ~/.aurora/memory.db[/]\n"
                "  3. Re-index your codebase:\n"
                "     [cyan]aur mem index .[/]"
            )

        # Permission errors
        if "permission" in error_str or "access" in error_str:
            return (
                "[bold red][Memory][/] Cannot write to memory store.\n\n"
                "[yellow]Cause:[/] Insufficient file permissions.\n\n"
                "[green]Solutions:[/]\n"
                "  1. Fix directory permissions:\n"
                "     [cyan]chmod 700 ~/.aurora/[/]\n"
                "  2. Fix database permissions:\n"
                "     [cyan]chmod 600 ~/.aurora/memory.db[/]\n"
                "  3. Check disk space:\n"
                "     [cyan]df -h[/]"
            )

        # Disk full
        if "disk" in error_str or "space" in error_str or "full" in error_str:
            return (
                "[bold red][Memory][/] Disk full.\n\n"
                "[yellow]Cause:[/] Not enough disk space for operation.\n\n"
                "[green]Solutions:[/]\n"
                "  1. Free up disk space (~50MB needed)\n"
                "  2. Check disk usage:\n"
                "     [cyan]du -sh ~/.aurora/[/]\n"
                "  3. Clean old databases:\n"
                "     [cyan]rm ~/.aurora/*.db.backup[/]"
            )

        # Parse errors (non-fatal for indexing)
        if "parse" in error_str or "syntax" in error_str:
            return (
                f"[bold yellow][Memory][/] Parse error during {operation}.\n\n"
                f"[yellow]Error:[/] {error}\n\n"
                "[green]Note:[/] This is usually non-fatal.\n"
                "Indexing continues with remaining files."
            )

        # No index found
        if "no index" in error_str or "not indexed" in error_str or "no results" in error_str:
            return (
                "[bold red][Memory][/] No index found.\n\n"
                "[green]Solution:[/] Run 'aur mem index .' to create one"
            )

        # Generic memory error
        return (
            f"[bold red][Memory][/] {operation} failed.\n\n"
            f"[yellow]Error:[/] {error}\n\n"
            "[green]Solutions:[/]\n"
            "  1. Check indexing details:\n"
            "     [cyan]aur mem stats[/]\n"
            "  2. Check logs for details\n"
            "  3. Report issue on GitHub if problem persists\n\n"
            "[dim]For more help:[/]\n"
            "  1. Check database file:\n"
            "     [cyan]ls -lh ~/.aurora/memory.db[/]\n"
            "  2. Try re-indexing:\n"
            "     [cyan]aur mem index .[/]\n"
            "  3. Reset if needed:\n"
            "     [cyan]rm ~/.aurora/memory.db[/]"
        )

    @staticmethod
    def handle_embedding_error(error: Exception, operation: str = "generating embeddings") -> str:
        """Handle and format embedding/ML errors with setup instructions.

        Args:
            error: The embedding exception
            operation: What operation was being attempted

        Returns:
            Formatted error message with recovery steps

        """
        error_str = str(error).lower()

        # Missing model/package
        if "no module" in error_str or "import" in error_str or "not found" in error_str:
            return (
                "[bold red][Embeddings][/] ML dependencies not installed.\n\n"
                "[yellow]Cause:[/] sentence-transformers package is required for embeddings.\n\n"
                "[green]Solutions:[/]\n"
                "  1. Install ML dependencies:\n"
                "     [cyan]pip install 'aurora[ml]'[/]\n"
                "  2. Or install manually:\n"
                "     [cyan]pip install sentence-transformers torch[/]\n"
                "  3. First time: Model will download (~90MB)\n"
                "     [cyan]Model: sentence-transformers/all-MiniLM-L6-v2[/]"
            )

        # Model download errors
        if "download" in error_str or "connection" in error_str or "timeout" in error_str:
            return (
                "[bold red][Embeddings][/] Cannot download embedding model.\n\n"
                "[yellow]Cause:[/] Network issue downloading sentence-transformers model.\n\n"
                "[green]Solutions:[/]\n"
                "  1. Check internet connection\n"
                "  2. Retry - model downloads once:\n"
                "     [cyan]~/.cache/torch/sentence_transformers/[/]\n"
                "  3. Manual download:\n"
                "     [cyan]python -c 'from sentence_transformers import SentenceTransformer; "
                'SentenceTransformer("all-MiniLM-L6-v2")\'[/]'
            )

        # Memory/GPU errors
        if "memory" in error_str or "cuda" in error_str or "device" in error_str:
            return (
                "[bold red][Embeddings][/] Insufficient memory for embeddings.\n\n"
                "[yellow]Cause:[/] Not enough RAM or GPU memory.\n\n"
                "[green]Solutions:[/]\n"
                "  1. Close memory-intensive applications\n"
                "  2. Use CPU-only mode (automatic fallback)\n"
                "  3. Reduce chunk size in config:\n"
                "     [cyan]memory.chunk_size: 500[/] (default: 1000)"
            )

        # Generic embedding error
        return (
            f"[bold red][Embeddings][/] {operation} failed.\n\n"
            f"[yellow]Error:[/] {error}\n\n"
            "[green]Solutions:[/]\n"
            "  1. Ensure ML dependencies installed:\n"
            "     [cyan]pip install 'aurora[ml]'[/]\n"
            "  2. Clear model cache if corrupted:\n"
            "     [cyan]rm -rf ~/.cache/torch/sentence_transformers/[/]\n"
            "  3. Try again after clearing cache"
        )

    @staticmethod
    def handle_path_error(error: Exception, path: str, operation: str = "accessing path") -> str:
        """Handle and format file/path errors with recovery steps.

        Args:
            error: The path exception
            path: Path that caused the error
            operation: What operation was being attempted

        Returns:
            Formatted error message with recovery steps

        """
        error_str = str(error).lower()

        # File/directory not found
        if "no such file" in error_str or "not found" in error_str or "does not exist" in error_str:
            return (
                f"[bold red][Path][/] Path not found.\n\n"
                f"[yellow]Path:[/] {path}\n"
                f"[yellow]Operation:[/] {operation}\n\n"
                "[green]Solutions:[/]\n"
                "  1. Check path spelling:\n"
                f"     [cyan]ls -la {path}[/]\n"
                "  2. Use absolute path:\n"
                f"     [cyan]{Path(path).resolve()}[/]\n"
                "  3. Check current directory:\n"
                "     [cyan]pwd[/]"
            )

        # Permission denied
        if "permission" in error_str or "access" in error_str:
            return (
                f"[bold red][Path][/] Permission denied.\n\n"
                f"[yellow]Path:[/] {path}\n"
                f"[yellow]Operation:[/] {operation}\n\n"
                "[green]Solutions:[/]\n"
                "  1. Check file permissions:\n"
                f"     [cyan]ls -la {path}[/]\n"
                "  2. Fix permissions:\n"
                f"     [cyan]chmod 644 {path}[/]\n"
                "  3. Run as different user or use sudo if appropriate"
            )

        # Is a directory (expected file)
        if "is a directory" in error_str:
            return (
                f"[bold red][Path][/] Expected file, found directory.\n\n"
                f"[yellow]Path:[/] {path}\n\n"
                "[green]Solutions:[/]\n"
                "  1. Provide specific file path:\n"
                f"     [cyan]{path}/filename.py[/]\n"
                "  2. List directory contents:\n"
                f"     [cyan]ls {path}[/]\n"
                "  3. Index entire directory:\n"
                f"     [cyan]aur mem index {path}[/]"
            )

        # Not a directory (expected directory)
        if "not a directory" in error_str:
            return (
                f"[bold red][Path][/] Expected directory, found file.\n\n"
                f"[yellow]Path:[/] {path}\n\n"
                "[green]Solutions:[/]\n"
                "  1. Use parent directory:\n"
                f"     [cyan]{Path(path).parent}[/]\n"
                "  2. Check path is correct:\n"
                f"     [cyan]ls -la {path}[/]"
            )

        # Generic path error
        return (
            f"[bold red][Path][/] {operation} failed.\n\n"
            f"[yellow]Path:[/] {path}\n"
            f"[yellow]Error:[/] {error}\n\n"
            "[green]Solutions:[/]\n"
            "  1. Check path exists and is accessible\n"
            "  2. Verify file/directory permissions\n"
            "  3. Use absolute path to avoid confusion"
        )

    @staticmethod
    def handle_schema_error(
        error: Exception,
        db_path: str | None = None,
    ) -> str:
        """Handle and format schema mismatch errors with recovery steps.

        Args:
            error: The schema mismatch exception
            db_path: Path to the database file (if known)

        Returns:
            Formatted error message with recovery steps

        """
        # Try to extract version info from the error if it's a SchemaMismatchError
        found_version = getattr(error, "found_version", "unknown")
        expected_version = getattr(error, "expected_version", "unknown")
        error_db_path = getattr(error, "db_path", None) or db_path or "~/.aurora/memory.db"

        return (
            "[bold red][Schema][/] Database schema outdated.\n\n"
            f"[yellow]Database:[/] {error_db_path}\n"
            f"[yellow]Found version:[/] v{found_version}\n"
            f"[yellow]Required version:[/] v{expected_version}\n\n"
            "[yellow]Cause:[/] Database was created with an older version of AURORA.\n\n"
            "[green]Solutions:[/]\n"
            "  1. Run setup to reset database:\n"
            "     [cyan]aur init[/]\n"
            "  2. After reset, re-index your codebase:\n"
            "     [cyan]aur mem index .[/]\n"
            "  3. Manual backup before reset:\n"
            f"     [cyan]cp {error_db_path} {error_db_path}.backup[/]\n"
            "  4. Manual reset (delete database):\n"
            f"     [cyan]rm {error_db_path}[/]"
        )

    @staticmethod
    def handle_budget_error(
        _error: Exception,
        spent: float = 0.0,
        limit: float = 0.0,
        operation: str = "query execution",
    ) -> str:
        """Handle and format budget errors with spending details.

        Args:
            _error: The budget exception (reserved for future error-specific handling)
            spent: Current spending amount
            limit: Budget limit
            operation: What operation was being attempted

        Returns:
            Formatted error message with spending details

        """
        remaining = max(0.0, limit - spent)

        return (
            "[bold red][Budget][/] Budget limit exceeded.\n\n"
            f"[yellow]Operation:[/] {operation}\n"
            f"[yellow]Spent:[/] ${spent:.4f}\n"
            f"[yellow]Budget:[/] ${limit:.2f}\n"
            f"[yellow]Remaining:[/] ${remaining:.4f}\n\n"
            "[green]Solutions:[/]\n"
            "  1. Increase budget limit:\n"
            "     [cyan]aur budget set <amount>[/]\n"
            "  2. Check spending history:\n"
            "     [cyan]aur budget history[/]\n"
            "  3. Reset spending for new period:\n"
            "     [cyan]aur budget reset[/]\n"
            "  4. Use --force-direct for lower-cost queries:\n"
            '     [cyan]aur query "question" --force-direct[/]'
        )

    @staticmethod
    def redact_api_key(key: str) -> str:
        """Redact API key for safe display.

        Shows first 7 characters and last 3 characters, masks the middle.

        Args:
            key: The API key to redact

        Returns:
            Redacted API key string

        Example:
            >>> redact_api_key("sk-ant-1234567890abcdef")
            'sk-ant-...def'

        """
        if not key or len(key) < 10:
            return "***"

        return f"{key[:7]}...{key[-3:]}"


def handle_errors(f: F) -> F:
    """Decorator to handle errors gracefully in CLI commands.

    This decorator catches exceptions and formats them appropriately based on
    the debug mode setting in the click context. In debug mode, full stack traces
    are shown. Otherwise, clean error messages are displayed with suggestions.

    Usage:
        @handle_errors
        @click.command()
        @click.pass_context
        def my_command(ctx: click.Context) -> None:
            # Command implementation
            pass

    Args:
        f: Function to wrap with error handling

    Returns:
        Wrapped function with error handling

    """

    @functools.wraps(f)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        # Get click context and debug flag
        ctx = click.get_current_context(silent=True)
        debug_mode = False
        if ctx and ctx.obj and isinstance(ctx.obj, dict):
            debug_mode = ctx.obj.get("debug", False)

        # Also check AURORA_DEBUG environment variable
        if not debug_mode:
            debug_mode = os.environ.get("AURORA_DEBUG") == "1"

        try:
            return f(*args, **kwargs)
        except click.Abort:
            # Re-raise click abort (used for controlled exits)
            raise
        except Exception as e:
            console = Console()
            error_handler = ErrorHandler()

            # In debug mode, show full stack trace
            if debug_mode:
                console.print("\n[bold red]Error occurred (debug mode):[/]")
                console.print(f"[yellow]{type(e).__name__}:[/] {e}\n")
                console.print("[dim]Stack trace:[/]")
                traceback.print_exc()
                console.print(
                    "\n[dim]Note: Use without --debug flag to see user-friendly error messages[/]\n",
                )
                sys.exit(EXIT_USER_ERROR)

            # Otherwise, show clean error message
            error_msg = None
            exit_code = EXIT_USER_ERROR  # Default to user error

            # Import SchemaMismatchError for schema error handling
            try:
                from aurora_core.exceptions import SchemaMismatchError, StorageError
            except ImportError:
                SchemaMismatchError = None
                StorageError = None

            # Determine error type and format appropriately
            if SchemaMismatchError and isinstance(e, SchemaMismatchError):
                error_msg = error_handler.handle_schema_error(e)
                exit_code = EXIT_SYSTEM_ERROR
            elif isinstance(e, BudgetExceededError):
                # Try to extract budget info from error message or default to 0
                error_msg = error_handler.handle_budget_error(e)
                exit_code = EXIT_USER_ERROR
            elif isinstance(e, APIError):
                error_msg = error_handler.handle_api_error(e)
                exit_code = EXIT_USER_ERROR
            elif isinstance(e, ConfigurationError):
                error_msg = error_handler.handle_config_error(e)
                exit_code = EXIT_USER_ERROR
            elif isinstance(e, MemoryStoreError):
                error_msg = error_handler.handle_memory_error(e)
                exit_code = EXIT_SYSTEM_ERROR
            elif StorageError and isinstance(e, StorageError):
                error_msg = error_handler.handle_memory_error(e)
                exit_code = EXIT_SYSTEM_ERROR
            elif isinstance(e, PermissionError):
                error_msg = error_handler.handle_path_error(
                    e,
                    str(getattr(e, "filename", "unknown")),
                    "accessing file",
                )
                exit_code = EXIT_SYSTEM_ERROR
            elif isinstance(e, FileNotFoundError):
                error_msg = error_handler.handle_path_error(
                    e,
                    str(getattr(e, "filename", "unknown")),
                    "accessing file",
                )
                exit_code = EXIT_USER_ERROR
            elif isinstance(e, ValueError):
                # Value errors are typically user input errors
                error_msg = (
                    f"[bold red]Error:[/] Invalid value\n\n"
                    f"[yellow]{e}[/]\n\n"
                    "[green]Solutions:[/]\n"
                    "  1. Check command arguments and values\n"
                    "  2. See command help: [cyan]aur <command> --help[/]\n"
                    "  3. Run with --debug flag for details:\n"
                    f"     [cyan]aur --debug {' '.join(sys.argv[1:])}[/]"
                )
                exit_code = EXIT_USER_ERROR
            else:
                # Check error message for clues
                error_str = str(e).lower()
                if "schema" in error_str:
                    error_msg = error_handler.handle_schema_error(e)
                    exit_code = EXIT_SYSTEM_ERROR
                elif "api" in error_str or "anthropic" in error_str:
                    error_msg = error_handler.handle_api_error(e)
                    exit_code = EXIT_USER_ERROR
                elif "budget" in error_str or "limit" in error_str:
                    error_msg = error_handler.handle_budget_error(e)
                    exit_code = EXIT_USER_ERROR
                elif "config" in error_str:
                    error_msg = error_handler.handle_config_error(e)
                    exit_code = EXIT_USER_ERROR
                elif "memory" in error_str or "database" in error_str:
                    error_msg = error_handler.handle_memory_error(e)
                    exit_code = EXIT_SYSTEM_ERROR
                else:
                    # Generic error
                    error_msg = (
                        f"[bold red]Error:[/] {type(e).__name__}\n\n"
                        f"[yellow]{e}[/]\n\n"
                        "[green]Solutions:[/]\n"
                        "  1. Check command syntax and arguments\n"
                        "  2. Verify configuration: [cyan]aur init[/]\n"
                        "  3. Run with --debug flag for detailed error:\n"
                        f"     [cyan]aur --debug {' '.join(sys.argv[1:])}[/]"
                    )
                    exit_code = EXIT_USER_ERROR

            console.print(f"\n{error_msg}\n")
            sys.exit(exit_code)

    return wrapper  # type: ignore[return-value]
