"""Planning CLI commands for AURORA CLI.

This module implements the 'aur plan' command group for managing
development plans:
- aur plan init: Initialize planning directory structure
- aur plan list: List active or archived plans
- aur plan view: Display plan details with file status
- aur plan archive: Archive a completed plan

Usage:
    aur plan init [--path <dir>]
    aur plan list [--archived] [--all] [--format rich|json]
    aur plan view <plan_id> [--archived] [--format rich|json]
    aur plan archive <plan_id> [--yes]
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import TYPE_CHECKING

import click
from rich.console import Console
from rich.table import Table

from aurora_cli.config import Config
from aurora_cli.errors import handle_errors
from aurora_cli.planning.core import (
    archive_plan,
    create_plan,
    init_planning_directory,
    list_plans,
    show_plan,
)

if TYPE_CHECKING:
    pass

__all__ = ["plan_group"]

logger = logging.getLogger(__name__)
console = Console()


@click.group(name="plan")
def plan_group() -> None:
    r"""Plan management commands.

    Create, list, view, and archive development plans.

    Plans use a four-file structure:
    - plan.md: Human-readable plan overview
    - prd.md: Product requirements document
    - tasks.md: Implementation task list
    - agents.json: Machine-readable plan data

    \b
    Commands:
        init     - Initialize planning directory
        list     - List active or archived plans
        view     - Display plan details
        archive  - Archive a completed plan

    \b
    Examples:
        aur plan init                    # Initialize planning
        aur plan list                    # List active plans
        aur plan view 0001-oauth-auth    # View plan details
        aur plan archive 0001-oauth      # Archive completed plan
    r"""


@plan_group.command(name="create")
@click.argument("goal")
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
def create_command(
    goal: str,
    context_files: tuple[Path, ...],
    no_decompose: bool,
    output_format: str,
    no_auto_init: bool,
    yes: bool,
    non_interactive: bool,
) -> None:
    r"""Create a new plan with SOAR-based goal decomposition.

    Analyzes the GOAL and decomposes it into subgoals with
    recommended agents. Creates the four-file plan structure:
    - plan.md: Human-readable plan overview
    - prd.md: Product requirements document (template)
    - tasks.md: Implementation task list
    - agents.json: Machine-readable plan data

    GOAL should be a clear description of what you want to achieve.
    Minimum 10 characters, maximum 500 characters.

    \b
    Examples:
        # Create authentication plan
        aur plan create "Implement OAuth2 authentication with JWT tokens"

        \b
        # Create with context files
        aur plan create "Add caching layer" --context src/api.py --context src/config.py

        \b
        # Skip decomposition (single task)
        aur plan create "Fix bug in login form" --no-decompose

        \b
        # JSON output
        aur plan create "Add user dashboard" --format json
    r"""
    # Load config to ensure project-local paths are used
    config = Config()

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

    result = create_plan(
        goal=goal,
        context_files=list(context_files) if context_files else None,
        auto_decompose=not no_decompose,
        config=config,
        yes=yes or non_interactive,
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

    # Rich output
    console.print(f"\n[bold green]Plan created: {plan.plan_id}[/]")
    console.print("=" * 60)
    console.print(f"Goal:        {plan.goal}")
    console.print(f"Complexity:  {plan.complexity.value}")
    console.print(f"Subgoals:    {len(plan.subgoals)}")
    console.print(f"Location:    {result.plan_dir}/")

    console.print("\n[bold]Subgoals:[/]")
    for i, sg in enumerate(plan.subgoals, 1):
        console.print(f"  {i}. {sg.title} ({sg.assigned_agent})")
        if sg.dependencies:
            console.print(f"     [dim]Depends on: {', '.join(sg.dependencies)}[/]")

    if result.warnings:
        console.print("\n[yellow]Warnings:[/]")
        for warning in result.warnings:
            console.print(f"  - {warning}")

    console.print("\n[bold]Files created (4 total):[/]")
    # Base files
    for fname in ["plan.md", "prd.md", "tasks.md", "agents.json"]:
        console.print(f"  [green][/] {fname}")

    console.print("\n[bold]Next steps:[/]")
    console.print(f"1. Review plan:    aur plan view {plan.plan_id}")
    console.print(f"2. Edit PRD:       {result.plan_dir}/prd.md")
    console.print("3. Start work:     Follow tasks.md checklist")
    console.print(f"4. Archive:        aur plan archive {plan.plan_id}")


@plan_group.command(name="init")
@click.option(
    "--path",
    "-p",
    type=click.Path(),
    default=None,
    help="Custom directory path (default: ~/.aurora/plans)",
)
@click.option(
    "--force",
    is_flag=True,
    default=False,
    help="Force reinitialize even if exists",
)
@handle_errors
def init_command(path: str | None, force: bool) -> None:
    r"""Initialize planning directory structure.

    Creates the planning directory with:
    - active/ - Directory for active plans
    - archive/ - Directory for archived plans
    - templates/ - Directory for custom templates
    - manifest.json - Manifest for fast listing

    \b
    Examples:
        # Initialize with default path
        aur plan init

        \b
        # Initialize at custom path
        aur plan init --path ~/my-project/.plans

        \b
        # Force reinitialize
        aur plan init --force
    r"""
    result = init_planning_directory(
        path=Path(path) if path else None,
        force=force,
    )

    if result.warning:
        console.print(f"[yellow]{result.warning}[/]")
    elif result.error:
        console.print(f"[red]{result.error}[/]")
        raise click.Abort()
    else:
        console.print(f"[green]{result.message}[/]")
        console.print(f"  - Active plans: {result.path}/active/")
        console.print(f"  - Archived plans: {result.path}/archive/")
        console.print('\n[bold]Ready to create plans with:[/] /aur:plan "goal"')


@plan_group.command(name="list")
@click.option(
    "--archived",
    is_flag=True,
    default=False,
    help="Show archived plans only",
)
@click.option(
    "--all",
    "all_plans",
    is_flag=True,
    default=False,
    help="Show all plans (active and archived)",
)
@click.option(
    "--format",
    "-f",
    "output_format",
    type=click.Choice(["rich", "json"]),
    default="rich",
    help="Output format (default: rich)",
)
@handle_errors
def list_command(archived: bool, all_plans: bool, output_format: str) -> None:
    r"""List plans with filtering options.

    By default, shows only active plans. Use --archived to see
    archived plans, or --all to see both.

    \b
    Examples:
        # List active plans
        aur plan list

        \b
        # List archived plans only
        aur plan list --archived

        \b
        # List all plans
        aur plan list --all

        \b
        # JSON output for scripting
        aur plan list --format json
    r"""
    config = Config()
    result = list_plans(archived=archived, all_plans=all_plans, config=config)

    if result.warning:
        console.print(f"[yellow]{result.warning}[/]")
        return

    if output_format == "json":
        data = [
            {
                "plan_id": p.plan_id,
                "goal": p.goal,
                "status": p.status,
                "created_at": p.created_at.isoformat(),
                "subgoals": p.subgoal_count,
                "agent_gaps": p.agent_gaps,
            }
            for p in result.plans
        ]
        console.print(json.dumps(data, indent=2))
        return

    if not result.plans:
        label = "archived" if archived else "active"
        console.print(f"[yellow]No {label} plans found.[/]")
        if not archived:
            console.print('Create a plan with: /aur:plan "your goal"')
        return

    # Rich table output
    label = "All" if all_plans else ("Archived" if archived else "Active")
    table = Table(title=f"{label} Plans ({len(result.plans)} total)")
    table.add_column("ID", style="cyan")
    table.add_column("Goal", style="white", max_width=40)
    table.add_column("Created", style="green")
    table.add_column("Status", style="blue")
    table.add_column("Subgoals", justify="right")
    table.add_column("Agents", style="yellow")

    for p in result.plans:
        agent_status = (
            "[green]All found[/]" if p.agent_gaps == 0 else f"[yellow]{p.agent_gaps} gap(s)[/]"
        )
        status_style = "[green]active[/]" if p.status == "active" else "[dim]archived[/]"
        table.add_row(
            p.plan_id,
            p.goal,
            p.created_at.strftime("%Y-%m-%d"),
            status_style,
            str(p.subgoal_count),
            agent_status,
        )

    console.print(table)

    if result.errors:
        console.print("\n[dim red]Warnings:[/]")
        for error in result.errors:
            console.print(f"  [dim red]{error}[/]")


@plan_group.command(name="view")
@click.argument("plan_id")
@click.option(
    "--archived",
    is_flag=True,
    default=False,
    help="Search in archived plans",
)
@click.option(
    "--format",
    "-f",
    "output_format",
    type=click.Choice(["rich", "json"]),
    default="rich",
    help="Output format (default: rich)",
)
@handle_errors
def view_command(plan_id: str, archived: bool, output_format: str) -> None:
    r"""Display detailed plan information.

    Shows comprehensive plan details including:
    - Goal and complexity
    - All subgoals with agent assignments
    - Agent gap warnings
    - File status for all plan files

    PLAN_ID can be a full ID or partial match.

    \b
    Examples:
        # View plan by full ID
        aur plan view 0001-oauth-auth

        \b
        # View plan by partial ID
        aur plan view oauth

        \b
        # View archived plan
        aur plan view 0001-oauth --archived

        \b
        # JSON output
        aur plan view 0001-oauth --format json
    r"""
    config = Config()
    result = show_plan(plan_id, archived=archived, config=config)

    if not result.success:
        console.print(f"[red]{result.error}[/]")
        raise click.Abort()

    plan = result.plan
    if plan is None:
        console.print("[red]Plan data is missing[/]")
        raise click.Abort()

    if output_format == "json":
        # Use print() not console.print() to avoid line wrapping
        print(plan.model_dump_json(indent=2))
        return

    # Rich panel output
    console.print(f"\n[bold]Plan: {plan.plan_id}[/]")
    console.print("=" * 60)
    console.print(f"Goal:        {plan.goal}")
    console.print(f"Created:     {plan.created_at.strftime('%Y-%m-%d %H:%M:%S')}")
    console.print(f"Status:      {plan.status.value}")
    console.print(f"Complexity:  {plan.complexity.value}")
    console.print(f"Context:     {', '.join(plan.context_sources) or 'None'}")

    console.print(f"\n[bold]Subgoals ({len(plan.subgoals)}):[/]")
    console.print("-" * 60)

    for i, sg in enumerate(plan.subgoals, 1):
        console.print(f"\n{i}. {sg.title} ({sg.assigned_agent})")
        console.print(f"   {sg.description}")
        deps = ", ".join(sg.dependencies) if sg.dependencies else "None"
        console.print(f"   [dim]Dependencies: {deps}[/]")

        # Show ideal agent if different from assigned (gap detection)
        if hasattr(sg, "ideal_agent") and sg.ideal_agent and sg.ideal_agent != sg.assigned_agent:
            console.print(f"   [yellow]Ideal agent: {sg.ideal_agent}[/]")

    if result.files_status:
        console.print("\n[bold]Files:[/]")
        for fname, exists in result.files_status.items():
            status = "[green][/]" if exists else "[red][/]"
            console.print(f"  {status} {fname}")

    console.print("\n[bold]Next Steps:[/]")
    console.print("1. Review plan for accuracy")
    console.print(f"2. Execute: /aur:implement {plan.plan_id}")
    console.print(f"3. Archive: aur plan archive {plan.plan_id}")


@plan_group.command(name="archive")
@click.argument("plan_id")
@click.option(
    "--yes",
    "-y",
    is_flag=True,
    default=False,
    help="Skip confirmation prompt",
)
@handle_errors
def archive_command(plan_id: str, yes: bool) -> None:
    r"""Archive a completed plan.

    Moves the plan from active/ to archive/ with timestamp prefix.
    Updates plan status and records duration from creation.

    PLAN_ID can be a full ID or partial match.

    \b
    Examples:
        # Archive with confirmation
        aur plan archive 0001-oauth-auth

        \b
        # Archive without confirmation
        aur plan archive 0001-oauth -y
    r"""
    # Confirmation unless --yes
    config = Config()

    if not yes:
        if not click.confirm(f"Archive plan '{plan_id}'? This will move files to archive/"):
            console.print("[yellow]Archive cancelled.[/]")
            return

    result = archive_plan(plan_id, config=config)

    if not result.success:
        console.print(f"[red]{result.error}[/]")
        raise click.Abort()

    if result.plan is None:
        console.print("[red]Archive succeeded but plan data is missing[/]")
        return

    console.print(f"\n[bold green]Plan archived: {result.plan.plan_id}[/]")
    console.print(f"\nArchived to: {result.target_dir}/")
    console.print(f"Duration: {result.duration_days} days")
    console.print("\nFiles archived (4 total):")
    for fname in ["plan.md", "prd.md", "tasks.md", "agents.json"]:
        console.print(f"  [green][/] {fname}")

    console.print("\nView archived plans: aur plan list --archived")
