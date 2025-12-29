"""AURORA CLI main entry point.

This module provides the main command-line interface for AURORA,
including memory commands, headless mode, and auto-escalation.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from aurora_cli.commands.budget import budget_group
from aurora_cli.commands.headless import headless_command
from aurora_cli.commands.init import init_command
from aurora_cli.commands.memory import memory_group
from aurora_cli.errors import APIError, ConfigurationError, ErrorHandler
from aurora_cli.escalation import AutoEscalationHandler, EscalationConfig
from aurora_cli.execution import QueryExecutor


__all__ = ["cli"]

console = Console()
logger = logging.getLogger(__name__)


@click.group(invoke_without_command=True)
@click.option(
    "--verbose",
    "-v",
    is_flag=True,
    default=False,
    help="Enable verbose logging",
)
@click.option(
    "--debug",
    is_flag=True,
    default=False,
    help="Enable debug logging",
)
@click.option(
    "--headless",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    default=None,
    help="Run headless mode with specified prompt file (shorthand for 'aur headless <file>')",
)
@click.version_option(version="0.1.0", prog_name="aurora")
@click.pass_context
def cli(ctx: click.Context, verbose: bool, debug: bool, headless: Path | None) -> None:
    """AURORA: Adaptive Unified Reasoning and Orchestration Architecture.

    A cognitive architecture framework for intelligent context management,
    reasoning, and agent orchestration.

    \b
    Common Commands:
        aur init                              # Initialize configuration
        aur mem index .                       # Index current directory
        aur mem search "authentication"       # Search indexed code
        aur query "your question"             # Query with auto-escalation
        aur --verify                          # Verify installation

    \b
    Examples:
        # Quick start
        aur init
        aur mem index packages/
        aur query "How does memory store work?"

        \b
        # Headless mode (both syntaxes work)
        aur --headless prompt.md
        aur headless prompt.md

        \b
        # Get help for any command
        aur mem --help
        aur query --help
    """
    # Store debug flag in context for error handler
    ctx.ensure_object(dict)
    ctx.obj["debug"] = debug
    ctx.obj["verbose"] = verbose

    # Configure logging
    if debug:
        logging.basicConfig(level=logging.DEBUG)
    elif verbose:
        logging.basicConfig(level=logging.INFO)
    else:
        logging.basicConfig(level=logging.WARNING)

    # Handle --headless flag by invoking headless command
    if headless is not None:
        # Invoke the headless command with the provided file path
        # This maps `aur --headless file.md` to `aur headless file.md`
        ctx.invoke(headless_command, prompt_path=headless)


# Register commands
cli.add_command(budget_group)
cli.add_command(headless_command)
cli.add_command(init_command)
cli.add_command(memory_group)


@cli.command(name="query")
@click.argument("query_text", type=str)
@click.option(
    "--force-aurora",
    is_flag=True,
    default=False,
    help="Force use of full AURORA pipeline (bypass auto-escalation)",
)
@click.option(
    "--force-direct",
    is_flag=True,
    default=False,
    help="Force use of direct LLM (bypass auto-escalation)",
)
@click.option(
    "--threshold",
    type=float,
    default=0.6,
    help="Complexity threshold for escalation (0.0-1.0, default: 0.6)",
)
@click.option(
    "--show-reasoning",
    is_flag=True,
    default=False,
    help="Show escalation reasoning and complexity assessment",
)
@click.option(
    "--verbose",
    is_flag=True,
    default=False,
    help="Show verbose output including phase trace for AURORA",
)
@click.option(
    "--dry-run",
    is_flag=True,
    default=False,
    help="Show what would be executed without making API calls",
)
@click.option(
    "--non-interactive",
    is_flag=True,
    default=False,
    help="Disable interactive prompts for weak retrieval matches (auto-continue)",
)
def query_command(
    query_text: str,
    force_aurora: bool,
    force_direct: bool,
    threshold: float,
    show_reasoning: bool,
    verbose: bool,
    dry_run: bool,
    non_interactive: bool,
) -> None:
    """Execute a query with automatic escalation.

    The system automatically chooses between:
    - Direct LLM: Fast, low-cost (for simple queries)
    - AURORA: Full SOAR pipeline (for complex queries)

    The decision is based on query complexity assessment.

    In interactive mode (default), the system will prompt you when retrieval
    quality is weak (poor groundedness or insufficient high-quality chunks).
    Use --non-interactive to auto-continue for automation/scripting.

    \b
    Examples:
        # Simple query (likely uses direct LLM)
        aur query "What is a function?"

        \b
        # Complex query (likely uses AURORA)
        aur query "Refactor the authentication system to use OAuth2"

        \b
        # Dry-run mode (test without API calls)
        aur query "How does authentication work?" --dry-run

        \b
        # Force AURORA mode with verbose output
        aur query "Explain classes" --force-aurora --verbose

        \b
        # Show escalation reasoning and complexity score
        aur query "Design a microservices architecture" --show-reasoning

        \b
        # Adjust escalation threshold (higher = more likely to use AURORA)
        aur query "Optimize database queries" --threshold 0.7

        \b
        # Non-interactive mode for automation (no prompts)
        aur query "Explain authentication" --non-interactive
    """
    try:
        error_handler = ErrorHandler()

        # Get API key from environment
        api_key_opt = os.environ.get("ANTHROPIC_API_KEY")

        # In dry-run mode, API key is optional (we won't make calls)
        if not api_key_opt and not dry_run:
            error = ConfigurationError("ANTHROPIC_API_KEY environment variable not set")
            error_msg = error_handler.handle_config_error(error)
            console.print(f"\n{error_msg}", style="red")
            raise click.Abort()

        # After validation, api_key is guaranteed to be str (or we're in dry-run mode)
        api_key: str = api_key_opt or ""  # Empty string in dry-run mode is fine

        # Handle dry-run mode - show what would be executed without API calls
        if dry_run:
            _execute_dry_run(
                query_text=query_text,
                api_key=api_key,
                force_aurora=force_aurora,
                force_direct=force_direct,
                threshold=threshold,
                console=console,
            )
            return

        # Create escalation config
        config = EscalationConfig(
            threshold=threshold,
            enable_keyword_only=True,  # Use keyword-only for speed
            force_aurora=force_aurora,
            force_direct=force_direct,
        )

        # Create handler
        handler = AutoEscalationHandler(config=config)

        # Assess query
        result = handler.assess_query(query_text)

        # Show reasoning if requested
        if show_reasoning:
            console.print("\n[bold]Escalation Analysis:[/]")
            console.print(f"  Query: {query_text}")
            console.print(f"  Complexity: [bold]{result.complexity}[/]")
            console.print(f"  Score: {result.score:.3f}")
            console.print(f"  Confidence: {result.confidence:.3f}")
            console.print(f"  Method: {result.method}")
            console.print(f"  Decision: [bold]{'AURORA' if result.use_aurora else 'Direct LLM'}[/]")
            console.print(f"  Reasoning: {result.reasoning}\n")

        # Check if memory store exists and prompt to index if empty
        from pathlib import Path

        from aurora_cli.config import load_config
        from aurora_core.store import SQLiteStore

        config = load_config()
        db_path = Path(config.get_db_path())
        memory_store = None

        # Initialize memory store for both AURORA and Direct LLM (Issue #15)
        # This allows Direct LLM to use indexed context for better responses
        if db_path.exists():
            memory_store = SQLiteStore(str(db_path))
            # Check if memory is empty (only prompt for AURORA or verbose mode)
            if (result.use_aurora or verbose) and _is_memory_empty(memory_store):
                should_index = _prompt_auto_index(console)
                if should_index:
                    _perform_auto_index(console, memory_store)
        elif result.use_aurora or verbose:
            # No database, prompt to create and index (only for AURORA or verbose)
            console.print("\n[yellow]No memory database found.[/]")
            should_index = _prompt_auto_index(console)
            if should_index:
                memory_store = SQLiteStore(str(db_path))
                _perform_auto_index(console, memory_store)

        # Create query executor with interactive mode setting
        # Interactive mode is enabled by default (when non_interactive=False)
        interactive_mode = not non_interactive
        executor_config = {
            "model": "claude-sonnet-4-20250514",
            "temperature": 0.7,
            "max_tokens": 500,
        }
        executor = QueryExecutor(config=executor_config, interactive_mode=interactive_mode)

        # Execute query based on escalation decision
        phase_trace = None
        if result.use_aurora:
            console.print("[bold blue]→[/] Using AURORA (full pipeline)")

            if memory_store is not None:
                # Full AURORA execution with memory
                if verbose:
                    exec_result = executor.execute_aurora(
                        query=query_text,
                        api_key=api_key,
                        memory_store=memory_store,
                        verbose=True,
                    )
                    # Type narrowing: verbose=True returns tuple
                    assert isinstance(exec_result, tuple), "Expected tuple when verbose=True"
                    response, phase_trace = exec_result
                else:
                    exec_result = executor.execute_aurora(
                        query=query_text,
                        api_key=api_key,
                        memory_store=memory_store,
                        verbose=False,
                    )
                    # Type narrowing: verbose=False returns str
                    assert isinstance(exec_result, str), "Expected str when verbose=False"
                    response = exec_result
            else:
                # Fallback to direct LLM if no memory
                console.print("[dim]Note: Using direct LLM (no memory store available)[/]")
                response = executor.execute_direct_llm(
                    query=query_text,
                    api_key=api_key,
                    memory_store=None,
                    verbose=verbose,
                )
        else:
            console.print("[bold green]→[/] Using Direct LLM (fast mode)")
            # Pass memory_store to direct LLM for context retrieval (Issue #15)
            response = executor.execute_direct_llm(
                query=query_text,
                api_key=api_key,
                memory_store=memory_store,
                verbose=verbose,
            )

        # Display phase trace if available (verbose mode with AURORA)
        if phase_trace is not None and verbose:
            _display_phase_trace(phase_trace, console)

        # Display response
        console.print("\n[bold]Response:[/]")
        console.print(Panel(response, border_style="green"))

    except click.Abort:
        raise
    except APIError as e:
        # API-specific error
        logger.error(f"Query command failed: {e}", exc_info=True)
        error_msg = error_handler.handle_api_error(e, "query execution")
        console.print(f"\n{error_msg}", style="red")
        raise click.Abort()
    except ConfigurationError as e:
        # Configuration error
        logger.error(f"Query command failed: {e}", exc_info=True)
        error_msg = error_handler.handle_config_error(e)
        console.print(f"\n{error_msg}", style="red")
        raise click.Abort()
    except Exception as e:
        # Unexpected error - try to provide helpful message
        logger.error(f"Query command failed: {e}", exc_info=True)
        error_str = str(e).lower()

        # Check if it's an API-related error
        if any(
            word in error_str for word in ["api", "anthropic", "auth", "rate", "token", "model"]
        ):
            error_msg = error_handler.handle_api_error(e, "query execution")
        else:
            # Generic error
            error_msg = f"[bold red]Error:[/] Query execution failed.\n\n[yellow]Error:[/] {e}\n\n[green]Suggestions:[/]\n  1. Check your query syntax\n  2. Verify ANTHROPIC_API_KEY is set\n  3. Try --dry-run to test without API calls"

        console.print(f"\n{error_msg}", style="red")
        raise click.Abort()


def _execute_dry_run(
    query_text: str,
    api_key: str | None,
    force_aurora: bool,
    force_direct: bool,
    threshold: float,
    console: Console,
) -> None:
    """Execute dry-run mode - show what would happen without API calls.

    Args:
        query_text: Query to analyze
        api_key: API key (may be None in dry-run)
        force_aurora: Whether AURORA is forced
        force_direct: Whether direct LLM is forced
        threshold: Escalation threshold
        console: Rich console for output
    """
    from pathlib import Path

    from aurora_cli.config import load_config
    from aurora_core.store import SQLiteStore

    error_handler = ErrorHandler()

    # Display dry-run header
    console.print("\n[bold yellow]DRY RUN MODE[/] - No API calls will be made\n")

    # Show configuration
    console.print("[bold]Configuration:[/]")
    config_table = Table(show_header=False, box=None)
    config_table.add_column("Key", style="cyan")
    config_table.add_column("Value", style="white")

    config_table.add_row("Provider", "anthropic")
    config_table.add_row("Model", "claude-sonnet-4-20250514")

    if api_key:
        redacted_key = error_handler.redact_api_key(api_key)
        config_table.add_row("API Key", f"{redacted_key} [green]✓[/]")
    else:
        config_table.add_row("API Key", "[red]Not set[/]")

    config_table.add_row("Threshold", f"{threshold}")

    console.print(config_table)

    # Check memory store
    console.print("\n[bold]Memory Store:[/]")
    config = load_config()
    db_path = Path(config.get_db_path())
    memory_chunks = 0

    if db_path.exists():
        try:
            memory_store = SQLiteStore(str(db_path))
            # Try to count chunks by querying the store
            from aurora_context_code.semantic import EmbeddingProvider
            from aurora_context_code.semantic.hybrid_retriever import HybridRetriever
            from aurora_core.activation.engine import ActivationEngine

            activation_engine = ActivationEngine()
            embedding_provider = EmbeddingProvider()
            retriever = HybridRetriever(memory_store, activation_engine, embedding_provider)
            results = retriever.retrieve("test", top_k=100)
            memory_chunks = len(results)
            console.print(f"  Database: {db_path} [green]✓[/]")
            console.print(f"  Chunks: ~{memory_chunks}")
        except Exception as e:
            console.print(f"  Database: {db_path} [yellow]⚠[/]")
            console.print(f"  Error: {e}")
    else:
        console.print(f"  Database: {db_path} [red]✗[/] (not found)")
        console.print("  Chunks: 0")

    # Run escalation assessment (no API call)
    console.print("\n[bold]Escalation Decision:[/]")

    config = EscalationConfig(
        threshold=threshold,
        enable_keyword_only=True,
        force_aurora=force_aurora,
        force_direct=force_direct,
    )
    handler = AutoEscalationHandler(config=config)
    result = handler.assess_query(query_text)

    decision_table = Table(show_header=False, box=None)
    decision_table.add_column("Metric", style="cyan")
    decision_table.add_column("Value", style="white")

    decision_table.add_row("Query", query_text)
    decision_table.add_row("Complexity", f"[bold]{result.complexity}[/]")
    decision_table.add_row("Score", f"{result.score:.3f}")
    decision_table.add_row("Confidence", f"{result.confidence:.3f}")
    decision_table.add_row("Method", result.method)

    if result.use_aurora:
        decision_table.add_row("Decision", "[bold blue]Would use: AURORA[/]")
    else:
        decision_table.add_row("Decision", "[bold green]Would use: Direct LLM[/]")

    decision_table.add_row("Reasoning", result.reasoning)

    console.print(decision_table)

    # Estimate cost
    console.print("\n[bold]Estimated Cost:[/]")
    if result.use_aurora:
        console.print("  ~$0.005-0.015 (AURORA with multiple phases)")
    else:
        console.print("  ~$0.002-0.005 (Direct LLM)")

    console.print("\n[bold yellow]Exiting without API calls[/]\n")


def _display_phase_trace(phase_trace: dict[str, Any], console: Console) -> None:
    """Display SOAR phase trace in formatted table.

    Args:
        phase_trace: Phase trace dictionary from executor
        console: Rich console for output
    """
    console.print("\n[bold]SOAR Phase Trace:[/]")

    # Create table
    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("Phase", style="cyan", no_wrap=True)
    table.add_column("Duration", justify="right", style="green")
    table.add_column("Summary", style="white")

    # Add phase rows
    for phase_info in phase_trace.get("phases", []):
        name = phase_info.get("name", "Unknown")
        duration = phase_info.get("duration", 0.0)
        summary = phase_info.get("summary", "")

        table.add_row(name, f"{duration:.2f}s", summary)

    console.print(table)

    # Display summary statistics
    total_duration = phase_trace.get("total_duration", 0.0)
    total_cost = phase_trace.get("total_cost", 0.0)
    confidence = phase_trace.get("confidence", 0.0)
    overall_score = phase_trace.get("overall_score", 0.0)

    console.print("\n[bold]Summary:[/]")
    console.print(f"  Total Duration: {total_duration:.2f}s")
    console.print(f"  Estimated Cost: ${total_cost:.4f}")
    console.print(f"  Confidence: {confidence:.2f}")
    console.print(f"  Overall Score: {overall_score:.2f}")


def _is_memory_empty(memory_store: Any) -> bool:
    """Check if memory store is empty.

    Args:
        memory_store: Store instance to check

    Returns:
        True if memory store has no chunks, False otherwise
    """
    try:
        # Try to get a count of chunks using HybridRetriever
        from aurora_context_code.semantic import EmbeddingProvider
        from aurora_context_code.semantic.hybrid_retriever import HybridRetriever
        from aurora_core.activation.engine import ActivationEngine

        activation_engine = ActivationEngine()
        embedding_provider = EmbeddingProvider()
        retriever = HybridRetriever(memory_store, activation_engine, embedding_provider)
        results = retriever.retrieve("test", top_k=1)
        return len(results) == 0
    except Exception:
        # If we can't check, assume empty
        return True


def _prompt_auto_index(console: Console) -> bool:
    """Prompt user to index current directory.

    Args:
        console: Rich console for output

    Returns:
        True if user wants to index, False otherwise
    """
    console.print("\n[yellow]Memory is empty. Index current directory?[/]")
    response = click.prompt(
        "This will index Python files in the current directory [Y/n]",
        default="Y",
        show_default=False,
    )
    return response.lower() in ("y", "yes", "")


def _perform_auto_index(console: Console, memory_store: Any) -> None:
    """Perform automatic indexing of current directory.

    Args:
        console: Rich console for output
        memory_store: Store instance for indexing (deprecated, uses config instead)
    """
    from pathlib import Path

    from rich.progress import BarColumn, Progress, SpinnerColumn, TextColumn

    from aurora_cli.config import load_config
    from aurora_cli.memory_manager import MemoryManager

    console.print("\n[bold]Indexing current directory...[/]")

    # Initialize memory manager with config
    config = load_config()
    manager = MemoryManager(config=config)

    # Create progress display
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        console=console,
    ) as progress:
        task_id = None

        def progress_callback(current: int, total: int) -> None:
            nonlocal task_id
            if task_id is None:
                task_id = progress.add_task(
                    "Indexing files",
                    total=total,
                )
            progress.update(task_id, completed=current)

        # Perform indexing
        stats = manager.index_path(Path.cwd(), progress_callback=progress_callback)

    # Display summary
    console.print(
        f"\n[bold green]✓[/] Indexed {stats.files_indexed} files, "
        f"{stats.chunks_created} chunks in {stats.duration_seconds:.2f}s\n"
    )


@cli.command(name="verify")
def verify_command() -> None:
    """Verify AURORA installation and dependencies.

    Checks that all components are properly installed and configured.
    """
    import sys
    from importlib import import_module
    from pathlib import Path
    from shutil import which

    console.print("\n[bold]Checking AURORA installation...[/]\n")

    all_ok = True
    has_warnings = False

    # Check 1: Core packages
    packages_to_check = [
        ("aurora.core", "Core components"),
        ("aurora.context_code", "Context & parsing"),
        ("aurora.soar", "SOAR orchestrator"),
        ("aurora.reasoning", "Reasoning engine"),
        ("aurora.cli", "CLI tools"),
        ("aurora.testing", "Testing utilities"),
    ]

    for package_name, description in packages_to_check:
        try:
            import_module(package_name)
            console.print(f"✓ {description} ({package_name})")
        except ImportError:
            console.print(f"✗ {description} ({package_name}) [red]MISSING[/]")
            all_ok = False

    # Check 2: CLI available
    console.print()
    aur_path = which("aur")
    if aur_path:
        console.print(f"✓ CLI available at {aur_path}")
    else:
        console.print("✗ CLI command 'aur' [red]NOT FOUND[/]")
        all_ok = False

    # Check 3: MCP server binary
    mcp_path = which("aurora-mcp")
    if mcp_path:
        console.print(f"✓ MCP server at {mcp_path}")
    else:
        console.print("⚠ MCP server 'aurora-mcp' [yellow]NOT FOUND[/] (will be added in Phase 3)")
        has_warnings = True

    # Check 4: Python version
    console.print()
    py_version = sys.version_info
    if py_version >= (3, 10):
        console.print(f"✓ Python version: {py_version.major}.{py_version.minor}.{py_version.micro}")
    else:
        console.print(
            f"✗ Python version: {py_version.major}.{py_version.minor}.{py_version.micro} [red](requires >= 3.10)[/]"
        )
        all_ok = False

    # Check 5: ML dependencies (embeddings)
    console.print()
    try:
        import_module("sentence_transformers")
        console.print("✓ ML dependencies (sentence-transformers)")
    except ImportError:
        console.print("⚠ ML dependencies [yellow]MISSING[/]")
        console.print("  Install with: pip install aurora[ml]")
        has_warnings = True

    # Check 6: Config file
    console.print()
    config_path = Path.home() / ".aurora" / "config.json"
    if config_path.exists():
        console.print(f"✓ Config file exists at {config_path}")
    else:
        console.print(f"⚠ Config file [yellow]NOT FOUND[/] at {config_path}")
        console.print("  Create with: aur init")
        has_warnings = True

    # Summary
    console.print()
    if all_ok and not has_warnings:
        console.print("[bold green]✓ AURORA is ready to use![/]\n")
        sys.exit(0)
    elif all_ok:
        console.print(
            "[bold yellow]⚠ AURORA partially installed - some optional features unavailable[/]\n"
        )
        sys.exit(1)
    else:
        console.print("[bold red]✗ AURORA has critical issues - please reinstall[/]\n")
        sys.exit(2)


if __name__ == "__main__":
    cli()
