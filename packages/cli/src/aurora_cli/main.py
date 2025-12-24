"""AURORA CLI main entry point.

This module provides the main command-line interface for AURORA,
including memory commands, headless mode, and auto-escalation.
"""

from __future__ import annotations

import logging
import os
from typing import Any

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from aurora_cli.commands.headless import headless_command
from aurora_cli.commands.memory import memory_command
from aurora_cli.escalation import AutoEscalationHandler, EscalationConfig
from aurora_cli.execution import QueryExecutor


__all__ = ["cli"]

console = Console()
logger = logging.getLogger(__name__)


@click.group()
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
@click.version_option(version="0.1.0", prog_name="aurora")
def cli(verbose: bool, debug: bool) -> None:
    """AURORA: Adaptive Unified Reasoning and Orchestration Architecture.

    A cognitive architecture framework for intelligent context management,
    reasoning, and agent orchestration.

    \b
    Examples:
        aur mem "authentication"              # Search memory
        aur --headless prompt.md              # Run headless mode
        aur query "How to calculate totals?"  # Query with auto-escalation
    """
    # Configure logging
    if debug:
        logging.basicConfig(level=logging.DEBUG)
    elif verbose:
        logging.basicConfig(level=logging.INFO)
    else:
        logging.basicConfig(level=logging.WARNING)


# Register commands
cli.add_command(headless_command)
cli.add_command(memory_command)


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
def query_command(
    query_text: str,
    force_aurora: bool,
    force_direct: bool,
    threshold: float,
    show_reasoning: bool,
    verbose: bool,
) -> None:
    """Execute a query with automatic escalation.

    The system automatically chooses between:
    - Direct LLM: Fast, low-cost (for simple queries)
    - AURORA: Full SOAR pipeline (for complex queries)

    The decision is based on query complexity assessment.

    \b
    Examples:
        # Simple query (likely uses direct LLM)
        aur query "What is a function?"

        \b
        # Complex query (likely uses AURORA)
        aur query "Refactor the authentication system to use OAuth2"

        \b
        # Force AURORA mode
        aur query "Explain classes" --force-aurora

        \b
        # Show escalation reasoning
        aur query "Design a microservices architecture" --show-reasoning
    """
    try:
        # Get API key from environment
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            console.print(
                "\n[bold red]Error:[/] ANTHROPIC_API_KEY environment variable not set.\n",
                style="red",
            )
            console.print("Please set your API key:")
            console.print("  export ANTHROPIC_API_KEY=sk-ant-...")
            console.print("\nGet your API key at: https://console.anthropic.com")
            raise click.Abort()

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

        # Create query executor
        executor_config = {
            "model": "claude-sonnet-4-20250514",
            "temperature": 0.7,
            "max_tokens": 500,
        }
        executor = QueryExecutor(config=executor_config)

        # Execute query based on escalation decision
        phase_trace = None
        if result.use_aurora:
            console.print("[bold blue]→[/] Using AURORA (full pipeline)")

            # Note: For Phase 2, we'll use direct LLM as fallback
            # Full AURORA integration requires memory store setup (Phase 4)
            console.print("[dim]Note: Using direct LLM (AURORA requires memory store setup)[/]")

            response = executor.execute_direct_llm(
                query=query_text,
                api_key=api_key,
                memory_store=None,
                verbose=verbose,
            )

            # TODO: Full AURORA execution (Phase 4)
            # from aurora_core.store.memory import MemoryStore
            # memory_store = MemoryStore(...)
            # result = executor.execute_aurora(
            #     query=query_text,
            #     api_key=api_key,
            #     memory_store=memory_store,
            #     verbose=verbose,
            # )
            # if verbose and isinstance(result, tuple):
            #     response, phase_trace = result
            # else:
            #     response = result
        else:
            console.print("[bold green]→[/] Using Direct LLM (fast mode)")
            response = executor.execute_direct_llm(
                query=query_text,
                api_key=api_key,
                memory_store=None,
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
    except Exception as e:
        logger.error(f"Query command failed: {e}", exc_info=True)
        console.print(f"\n[bold red]Error:[/] {e}", style="red")
        raise click.Abort()


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

    console.print(f"\n[bold]Summary:[/]")
    console.print(f"  Total Duration: {total_duration:.2f}s")
    console.print(f"  Estimated Cost: ${total_cost:.4f}")
    console.print(f"  Confidence: {confidence:.2f}")
    console.print(f"  Overall Score: {overall_score:.2f}")


if __name__ == "__main__":
    cli()
