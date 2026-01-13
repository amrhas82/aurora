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

import json
import logging
import os
import shutil
import subprocess
from pathlib import Path
from typing import TYPE_CHECKING

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from aurora_cli.config import load_config
from aurora_cli.errors import handle_errors
from aurora_cli.llm.cli_pipe_client import CLIPipeLLMClient
from aurora_cli.planning.core import (
    archive_plan,
    create_plan,
    init_planning_directory,
    list_plans,
    show_plan,
)

if TYPE_CHECKING:
    pass

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
    config = load_config()

    # Resolve tool: CLI flag → env → config → default
    if tool is None:
        tool = os.environ.get(
            "AURORA_GOALS_TOOL",
            (
                config.goals_default_tool
                if config and hasattr(config, "goals_default_tool")
                else "claude"
            ),
        )

    # Resolve model: CLI flag → env → config → default
    if model is None:
        env_model = os.environ.get("AURORA_GOALS_MODEL")
        if env_model and env_model.lower() in ("sonnet", "opus"):
            model = env_model.lower()
        elif config and hasattr(config, "goals_default_model") and config.goals_default_model:
            model = config.goals_default_model
        else:
            model = "sonnet"  # Final default

    # Validate tool exists in PATH
    if not shutil.which(tool):
        console.print(f"[red]Error: CLI tool '{tool}' not found in PATH[/]")
        console.print(f"[dim]Install the tool or set a different one with --tool flag[/]")
        raise click.Abort()

    if verbose:
        console.print(f"[dim]Using tool: {tool} (model: {model})[/]")

    # Create CLI-agnostic LLM client
    try:
        llm_client = CLIPipeLLMClient(tool=tool, model=model)
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

    # Rich output
    console.print(f"\n[bold green]Plan created: {plan.plan_id}[/]")
    console.print("=" * 60)
    console.print(f"Goal:        {plan.goal}")
    console.print(f"Complexity:  {plan.complexity.value}")
    console.print(f"Subgoals:    {len(plan.subgoals)}")
    console.print(f"Location:    {result.plan_dir}/")

    console.print("\n[bold]Subgoals:[/]")
    # Display with gap detection: ideal_agent vs assigned_agent comparison
    for i, sg in enumerate(plan.subgoals, 1):
        console.print(f"  {i}. {sg.title}")

        # Gap detection: ideal != assigned
        is_gap = sg.ideal_agent != sg.assigned_agent

        if is_gap:
            # Gap detected - show both ideal and assigned
            console.print(f"     [yellow]Ideal:[/] {sg.ideal_agent}")
            if sg.ideal_agent_desc:
                console.print(f"       [dim]{sg.ideal_agent_desc}[/]")
            console.print(f"     [cyan]Available:[/] {sg.assigned_agent}")
            console.print(f"     [red]Status: GAP - create {sg.ideal_agent}[/]")
        else:
            # Matched - ideal == assigned
            console.print(f"     [cyan]{sg.assigned_agent}[/] [green]MATCHED[/]")

        if sg.dependencies:
            console.print(f"     [dim]Depends on: {', '.join(sg.dependencies)}[/]")

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
