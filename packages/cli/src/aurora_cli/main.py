"""AURORA CLI main entry point.

This module provides the main command-line interface for AURORA,
including memory commands, headless mode, and auto-escalation.
"""

from __future__ import annotations

import logging
from pathlib import Path

import click
from rich.console import Console

from aurora_cli.commands.agents import agents_group
from aurora_cli.commands.budget import budget_group
from aurora_cli.commands.doctor import doctor_command
from aurora_cli.commands.friction import friction_group
from aurora_cli.commands.goals import goals_command
from aurora_cli.commands.headless import headless_command
from aurora_cli.commands.init import init_command
from aurora_cli.commands.memory import memory_group
from aurora_cli.commands.plan import plan_group
from aurora_cli.commands.soar import soar_command
from aurora_cli.commands.spawn import spawn_command
from aurora_cli.commands.version import version_command


__all__ = ["cli"]

console = Console()
logger = logging.getLogger(__name__)


def _show_first_run_welcome_if_needed() -> None:
    """Show welcome message on first run.

    Checks for the presence of a .aurora directory and config file.
    If neither exists, displays a welcome message guiding the user to run 'aur init'.
    """
    from aurora_cli.config import _get_aurora_home

    aurora_home = _get_aurora_home()
    config_path = aurora_home / "config.json"

    # Only show welcome if neither directory nor config exists
    if not aurora_home.exists() or not config_path.exists():
        console.print("\n[bold cyan]Welcome to AURORA![/]\n")
        console.print("AURORA is not yet initialized on this system.\n")
        console.print("[bold]Get started:[/]")
        console.print("  1. Run [cyan]aur init[/] to set up configuration")
        console.print("  2. Run [cyan]aur doctor[/] to verify your setup")
        console.print("  3. Run [cyan]aur version[/] to check your installation\n")
        console.print("For help with any command, use [cyan]aur <command> --help[/]\n")


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
@click.version_option(version="0.11.2")
@click.pass_context
def cli(ctx: click.Context, verbose: bool, debug: bool, headless: Path | None) -> None:
    r"""AURORA: Adaptive Unified Reasoning and Orchestration Architecture.

    A cognitive architecture framework for intelligent context management,
    reasoning, and agent orchestration.

    \b
    Common Commands:
        aur init                              # Initialize configuration
        aur doctor                            # Run health checks
        aur version                           # Show version info
        aur mem index .                       # Index current directory
        aur mem search "authentication"       # Search indexed code

    \b
    Examples:
        # Quick start
        aur init
        aur mem index packages/

        \b
        # Health checks and diagnostics
        aur doctor                            # Check system health
        aur doctor --fix                      # Auto-repair issues

        \b
        # Headless mode (both syntaxes work)
        aur --headless prompt.md
        aur headless prompt.md

        \b
        # Get help for any command
        aur mem --help
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

    # Show first-run welcome message if this is the first time running
    if ctx.invoked_subcommand is None and headless is None:
        _show_first_run_welcome_if_needed()

    # Handle --headless flag by invoking headless command
    if headless is not None:
        # Invoke the headless command with the provided file path
        # This maps `aur --headless file.md` to `aur headless file.md`
        ctx.invoke(headless_command, prompt_path=headless)


# Register commands
cli.add_command(agents_group)
cli.add_command(budget_group)
cli.add_command(doctor_command)
cli.add_command(friction_group)
cli.add_command(goals_command)
cli.add_command(headless_command)
cli.add_command(init_command)
cli.add_command(memory_group)
cli.add_command(plan_group)
cli.add_command(soar_command)
cli.add_command(spawn_command)
cli.add_command(version_command)


if __name__ == "__main__":
    cli()
