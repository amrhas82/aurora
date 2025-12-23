"""AURORA CLI main entry point.

This module provides the main command-line interface for AURORA,
including memory commands, headless mode, and auto-escalation.
"""

from __future__ import annotations

import logging

import click
from rich.console import Console

from aurora_cli.commands.headless import headless_command
from aurora_cli.commands.memory import memory_command
from aurora_cli.escalation import AutoEscalationHandler, EscalationConfig


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
def query_command(
    query_text: str,
    force_aurora: bool,
    force_direct: bool,
    threshold: float,
    show_reasoning: bool,
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

        # Execute query based on escalation decision
        if result.use_aurora:
            console.print("[bold blue]→[/] Using AURORA (full pipeline)")
            console.print("[dim]Note: AURORA execution not yet implemented in CLI[/]")
            console.print("[dim]This would call: aurora_orchestrator.execute(query)[/]")
            # TODO: Implement AURORA orchestrator call
            # from aurora_soar.orchestrator import SOAROrchestrator
            # orchestrator = SOAROrchestrator(...)
            # response = orchestrator.execute(query_text)
        else:
            console.print("[bold green]→[/] Using Direct LLM (fast mode)")
            console.print("[dim]Note: Direct LLM execution not yet implemented in CLI[/]")
            console.print("[dim]This would call: llm_client.generate(query)[/]")
            # TODO: Implement direct LLM call
            # from aurora_reasoning.llm_client import LLMClient
            # llm = LLMClient(...)
            # response = llm.generate(query_text)

        console.print(f"\n[dim]Query: {query_text}[/]")

    except Exception as e:
        logger.error(f"Query command failed: {e}", exc_info=True)
        console.print(f"\n[bold red]Error:[/] {e}", style="red")
        raise click.Abort()


if __name__ == "__main__":
    cli()
