"""Goals CLI command for AURORA CLI.

This module implements the 'aur goals' command for goal decomposition
and planning. The goals command creates a goals.json file with subgoals
and agent assignments, which can then be used by the /plan skill to
generate PRD and tasks.

Usage:
    aur goals "Your goal description" [options]

Options:
    --tool, -t        CLI tool to use (default: from AURORA_GOALS_TOOL or config or 'claude')
    --model, -m       Model to use: sonnet or opus (default: from AURORA_GOALS_MODEL or config or 'sonnet')
    --verbose, -v     Show detailed output
    --yes, -y         Skip confirmation prompt
    --context, -c     Context files for informed decomposition
    --format, -f      Output format: rich or json

Examples:
    # Create goals with default settings
    aur goals "Implement OAuth2 authentication with JWT tokens"

    # Use specific tool and model
    aur goals "Add caching layer" --tool cursor --model opus

    # With context files
    aur goals "Refactor API layer" --context src/api.py --context src/config.py

    # Non-interactive mode
    aur goals "Add user dashboard" --yes
"""

from __future__ import annotations

import logging
import os
import shutil
import subprocess
from pathlib import Path
from typing import TYPE_CHECKING

import click
from rich.console import Console

from aurora_cli.config import Config
from aurora_cli.errors import handle_errors
from aurora_cli.llm.cli_pipe_client import CLIPipeLLMClient
from aurora_cli.planning.core import create_plan


if TYPE_CHECKING:
    pass


def _start_background_model_loading(verbose: bool = False) -> None:
    """Start loading the embedding model in the background.

    This is non-blocking - the model loads in a background thread while
    other initialization continues. When embeddings are actually needed,
    the code will wait for loading to complete (with a spinner if still loading).

    Uses lightweight cache checking to avoid importing torch/sentence-transformers
    until actually needed in the background thread.

    Args:
        verbose: Whether to enable verbose logging
    """
    try:
        # Use lightweight cache check that doesn't import torch
        from aurora_context_code.model_cache import is_model_cached_fast, start_background_loading

        # Only start background loading if model is cached
        # If not cached, we'll handle download later when actually needed
        if not is_model_cached_fast():
            logger.debug("Model not cached, skipping background load")
            return

        # Start loading in background thread (imports torch there, not here)
        start_background_loading()
        logger.debug("Background model loading started")

    except ImportError:
        # aurora_context_code not installed
        if verbose:
            logger.debug("Context code package not available")
    except Exception as e:
        logger.debug("Background model loading failed to start: %s", e)


__all__ = ["goals_command"]

logger = logging.getLogger(__name__)
console = Console()


@click.command(name="goals")
@click.argument("goal")
@click.option(
    "--tool",
    "-t",
    type=str,
    default=None,
    help="CLI tool to use (default: from AURORA_GOALS_TOOL or config or 'claude')",
)
@click.option(
    "--model",
    "-m",
    type=click.Choice(["sonnet", "opus"]),
    default=None,
    help="Model to use (default: from AURORA_GOALS_MODEL or config or 'sonnet')",
)
@click.option(
    "--verbose",
    "-v",
    is_flag=True,
    default=False,
    help="Show detailed output including memory search and decomposition details",
)
@click.option(
    "--context",
    "-c",
    "context_files",
    multiple=True,
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    help="Context files for informed decomposition. Can be used multiple times.",
)
@click.option(
    "--no-decompose",
    is_flag=True,
    default=False,
    help="Skip SOAR decomposition (create single-task plan)",
)
@click.option(
    "--format",
    "-f",
    "output_format",
    type=click.Choice(["rich", "json"]),
    default="rich",
    help="Output format (default: rich)",
)
@click.option(
    "--no-auto-init",
    is_flag=True,
    default=False,
    help="Disable automatic initialization if .aurora doesn't exist",
)
@click.option(
    "--yes",
    "-y",
    is_flag=True,
    default=False,
    help="Skip confirmation prompt and proceed with plan generation",
)
@click.option(
    "--non-interactive",
    is_flag=True,
    default=False,
    help="Non-interactive mode (alias for --yes)",
)
@handle_errors
def goals_command(
    goal: str,
    tool: str | None,
    model: str | None,
    verbose: bool,
    context_files: tuple[Path, ...],
    no_decompose: bool,
    output_format: str,
    no_auto_init: bool,
    yes: bool,
    non_interactive: bool,
) -> None:
    r"""Create goals with decomposition and agent matching.

    Analyzes the GOAL and decomposes it into subgoals with
    recommended agents. Creates goals.json in .aurora/plans/NNNN-slug/
    which can be used by /plan skill to generate PRD and tasks.

    GOAL should be a clear description of what you want to achieve.
    Minimum 10 characters, maximum 500 characters.

    \b
    Examples:
        # Create goals with default settings
        aur goals "Implement OAuth2 authentication with JWT tokens"

        \b
        # With context files
        aur goals "Add caching layer" --context src/api.py --context src/config.py

        \b
        # Skip decomposition (single task)
        aur goals "Fix bug in login form" --no-decompose

        \b
        # JSON output
        aur goals "Add user dashboard" --format json
    """
    # Load config to ensure project-local paths are used
    config = Config()

    # Start background model loading early (non-blocking)
    # The model will load in parallel with other initialization
    _start_background_model_loading(verbose)

    # Resolve tool: CLI flag → env → config → default
    if tool is None:
        tool = os.environ.get("AURORA_GOALS_TOOL", config.soar_default_tool)

    # Resolve model: CLI flag → env → config → default
    if model is None:
        env_model = os.environ.get("AURORA_GOALS_MODEL")
        if env_model and env_model.lower() in ("sonnet", "opus"):
            model = env_model.lower()
        else:
            model = config.soar_default_model

    # Validate tool exists in PATH
    if not shutil.which(tool):
        console.print(f"[red]Error: CLI tool '{tool}' not found in PATH[/]")
        console.print("[dim]Install the tool or set a different one with --tool flag[/]")
        raise click.Abort()

    # Display header with goal in a box (consistent with aur soar)
    from rich.panel import Panel

    console.print()
    console.print(
        Panel(
            f"[cyan]{goal}[/]",
            title="[bold]Aurora Goals[/]",
            subtitle=f"[dim]Tool: {tool}[/]",
            border_style="blue",
        )
    )

    if verbose:
        console.print(f"[dim]Using tool: {tool} (model: {model})[/]")

    # Validate LLM client can be created
    try:
        _ = CLIPipeLLMClient(tool=tool, model=model)
    except ValueError as e:
        console.print(f"[red]Error creating LLM client: {e}[/]")
        raise click.Abort()

    # Auto-initialize if .aurora doesn't exist
    if not no_auto_init:
        aurora_dir = Path.cwd() / ".aurora"
        if not aurora_dir.exists():
            console.print("[dim]Initializing Aurora directory structure...[/]")
            from aurora_cli.commands.init_helpers import create_directory_structure

            try:
                create_directory_structure(Path.cwd())
                console.print("[green]✓[/] Aurora initialized\n")
            except Exception as e:
                console.print(f"[yellow]Warning: Could not initialize Aurora: {e}[/]")
                console.print("[dim]Continuing with plan creation...[/]\n")

    # Show decomposition progress (Task 3.4)
    if verbose and not no_decompose:
        console.print("\n[bold]📋 Decomposing goal into subgoals...[/]")
        console.print(f"   Goal: {goal}")
        console.print(f"   Using: {tool} ({model})")

    result = create_plan(
        goal=goal,
        context_files=list(context_files) if context_files else None,
        auto_decompose=not no_decompose,
        config=config,
        yes=yes or non_interactive,
        goals_only=True,  # aur goals creates ONLY goals.json per PRD-0026
    )

    # Show agent matching results (Task 3.4)
    if verbose and result.success and result.plan:
        console.print("\n[bold]🤖 Agent matching results:[/]")
        for i, sg in enumerate(result.plan.subgoals, 1):
            # Gap detection: ideal != assigned
            is_gap = sg.ideal_agent != sg.assigned_agent
            status = "⚠️" if is_gap else "✓"
            color = "yellow" if is_gap else "green"
            console.print(
                f"   {status} sg-{i}: {sg.assigned_agent} "
                f"([{color}]{'GAP' if is_gap else 'MATCHED'}[/{color}])"
            )

    if not result.success:
        console.print(f"[red]{result.error}[/]")
        raise click.Abort()

    plan = result.plan
    if plan is None:
        console.print("[red]Plan creation succeeded but plan data is missing[/]")
        raise click.Abort()

    if output_format == "json":
        # Use print() not console.print() to avoid line wrapping
        print(plan.model_dump_json(indent=2))
        return

    # goals.json already written by create_plan() with goals_only=True
    plan_dir_path = Path(result.plan_dir)
    goals_file = plan_dir_path / "goals.json"

    # Show plan summary
    console.print("\n[bold]Plan directory:[/]")
    console.print(f"   {plan_dir_path}/")

    # Ask user to review (unless --yes flag)
    if not (yes or non_interactive):
        review_response = click.prompt(
            "\nReview goals in editor? [y/N]", default="n", show_default=False, type=str
        )

        if review_response.lower() in ("y", "yes"):
            # Open in editor
            editor = os.environ.get("EDITOR", "nano")
            try:
                subprocess.run([editor, str(goals_file)], check=False)
            except Exception as e:
                console.print(f"[yellow]Warning: Could not open editor: {e}[/]")
                console.print("[dim]Continuing without edit...[/]")

    # Goals-specific display: Agent Assignments table with match quality
    # This is the divergence point from aur soar - goals shows this table + editor
    from rich.table import Table

    console.print(f"\n[bold green]Plan created: {plan.plan_id}[/]")
    console.print(f"[dim]Location: {result.plan_dir}/[/]\n")

    # Count match qualities for summary
    excellent_count = 0
    acceptable_count = 0
    insufficient_count = 0

    # Build the Agent Assignments table
    table = Table(title="Agent Assignments", show_header=True, header_style="bold")
    table.add_column("#", style="dim", width=3)
    table.add_column("Subgoal", min_width=30, max_width=50)
    table.add_column("Agent", style="cyan", min_width=18)
    table.add_column("Match", min_width=12)

    for i, sg in enumerate(plan.subgoals, 1):
        # Get match quality (from SOAR's 3-tier matching)
        match_quality = getattr(sg, "match_quality", None)
        if hasattr(match_quality, "value"):
            match_quality = match_quality.value
        if not match_quality:
            # Fallback: infer from ideal vs assigned
            match_quality = "excellent" if sg.ideal_agent == sg.assigned_agent else "acceptable"

        # Count and format match indicator
        if match_quality == "excellent":
            excellent_count += 1
            match_display = "[green]Excellent[/]"
        elif match_quality == "acceptable":
            acceptable_count += 1
            match_display = "[yellow]Acceptable[/]"
        else:  # insufficient - agent will be spawned
            insufficient_count += 1
            match_display = "[red]Spawned[/]"

        # Truncate title if too long
        title_display = sg.title[:47] + "..." if len(sg.title) > 50 else sg.title

        table.add_row(str(i), title_display, sg.assigned_agent, match_display)

    console.print(table)

    # Summary line
    total = len(plan.subgoals)
    console.print(
        f"\n[dim]Summary: {total} subgoals | "
        f"[green]{excellent_count} excellent[/], "
        f"[yellow]{acceptable_count} acceptable[/], "
        f"[red]{insufficient_count} spawned[/][/]"
    )

    if result.warnings:
        console.print("\n[yellow]Warnings:[/]")
        for warning in result.warnings:
            console.print(f"  - {warning}")

    console.print("\n[bold]Files created:[/]")
    console.print("  [green]✓[/] goals.json")

    console.print("\n[bold green]✅ Goals saved.[/]")
    console.print("\n[bold]Next steps:[/]")
    console.print(f"1. Review goals:   cat {result.plan_dir}/goals.json")
    console.print(
        "2. Generate PRD:   Run [bold]/plan[/] in Claude Code to create prd.md, tasks.md, specs/"
    )
    console.print("3. Start work:     aur implement or aur spawn tasks.md")
