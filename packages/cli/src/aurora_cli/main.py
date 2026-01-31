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
from aurora_cli.commands.goals import goals_command
from aurora_cli.commands.headless import headless_command
from aurora_cli.commands.init import init_command
from aurora_cli.commands.memory import memory_group
from aurora_cli.commands.plan import plan_group
from aurora_cli.commands.query import query_command
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
@click.version_option(version="0.10.1")
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
        aur --verify                          # Verify installation

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
cli.add_command(goals_command)
cli.add_command(headless_command)
cli.add_command(init_command)
cli.add_command(memory_group)
cli.add_command(plan_group)
cli.add_command(query_command)
cli.add_command(soar_command)
cli.add_command(spawn_command)
cli.add_command(version_command)


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
            f"✗ Python version: {py_version.major}.{py_version.minor}.{py_version.micro} [red](requires >= 3.10)[/]",
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
            "[bold yellow]⚠ AURORA partially installed - some optional features unavailable[/]\n",
        )
        sys.exit(1)
    else:
        console.print("[bold red]✗ AURORA has critical issues - please reinstall[/]\n")
        sys.exit(2)


if __name__ == "__main__":
    cli()
