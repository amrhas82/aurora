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
    from rich.table import Table

    from aurora_cli.planning.results import PlanResult


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


__all__ = [
    "goals_command",
    "_resolve_tool_and_model",
    "_validate_goals_requirements",
    "_ensure_aurora_initialized",
    "_generate_goals_plan",
    "_display_goals_results",
]

logger = logging.getLogger(__name__)
console = Console()


def _resolve_tool_and_model(
    cli_tool: str | None,
    cli_model: str | None,
    config: Config,
) -> tuple[str, str]:
    """Resolve tool and model from CLI args, environment, or config.

    Resolution order for tool: CLI flag -> env var -> config default
    Resolution order for model: CLI flag -> env var (if valid) -> config default

    Args:
        cli_tool: Tool specified via --tool flag (or None)
        cli_model: Model specified via --model flag (or None)
        config: Aurora configuration object

    Returns:
        Tuple of (resolved_tool, resolved_model)
    """
    # Resolve tool: CLI flag → env → config → default
    if cli_tool is not None:
        tool = cli_tool
    else:
        tool = os.environ.get("AURORA_GOALS_TOOL", config.soar_default_tool)

    # Resolve model: CLI flag → env → config → default
    if cli_model is not None:
        model = cli_model
    else:
        env_model = os.environ.get("AURORA_GOALS_MODEL")
        if env_model and env_model.lower() in ("sonnet", "opus"):
            model = env_model.lower()
        else:
            model = config.soar_default_model

    return tool, model


def _validate_goals_requirements(tool: str) -> str | None:
    """Validate that required tool exists in PATH.

    Args:
        tool: Name of the CLI tool to validate

    Returns:
        Error message string if validation fails, None if validation passes
    """
    if not shutil.which(tool):
        return f"CLI tool '{tool}' not found in PATH"
    return None


def _ensure_aurora_initialized(_verbose: bool = False) -> None:
    """Ensure .aurora directory exists, creating it if needed.

    Args:
        _verbose: Whether to print verbose output (reserved for future use)
    """
    aurora_dir = Path.cwd() / ".aurora"
    if aurora_dir.exists():
        return

    console.print("[dim]Initializing Aurora directory structure...[/]")
    from aurora_cli.commands.init_helpers import create_directory_structure

    try:
        create_directory_structure(Path.cwd())
        console.print("[green]✓[/] Aurora initialized\n")
    except Exception as e:
        console.print(f"[yellow]Warning: Could not initialize Aurora: {e}[/]")
        console.print("[dim]Continuing with plan creation...[/]\n")


def _generate_goals_plan(
    goal: str,
    context_files: list[Path] | None,
    no_decompose: bool,
    config: Config,
    yes: bool,
    no_cache: bool = False,
) -> PlanResult:
    """Generate a goals plan using the SOAR pipeline.

    Args:
        goal: The goal description to decompose
        context_files: Optional list of context files
        no_decompose: If True, skip SOAR decomposition
        config: Aurora configuration object
        yes: Skip confirmation prompts if True
        no_cache: If True, skip cache and force fresh decomposition

    Returns:
        PlanResult from create_plan with success status and plan data
    """
    return create_plan(
        goal=goal,
        context_files=context_files,
        auto_decompose=not no_decompose,
        config=config,
        yes=yes,
        goals_only=True,  # aur goals creates ONLY goals.json per PRD-0026
        no_cache=no_cache,
    )


def _display_goals_results(
    result: PlanResult,
    output_format: str,
    _verbose: bool,
    yes: bool,
) -> str | None:
    """Display goals results in the specified format.

    Args:
        result: PlanResult from create_plan
        output_format: "json" or "rich"
        _verbose: Whether to show verbose output (reserved for future use)
        yes: Whether --yes flag was passed (skip editor prompt)

    Returns:
        JSON string if output_format is "json", None otherwise
    """
    plan = result.plan

    if output_format == "json":
        return plan.model_dump_json(indent=2)

    # Rich output - display tables and info
    plan_dir_path = Path(result.plan_dir)
    goals_file = plan_dir_path / "goals.json"

    # Show plan summary
    console.print("\n[bold]Plan directory:[/]")
    console.print(f"   {plan_dir_path}/")

    # Ask user to review (unless --yes flag)
    if not yes:
        review_response = click.prompt(
            "\nReview goals in editor? [y/N]",
            default="n",
            show_default=False,
            type=str,
        )

        if review_response.lower() in ("y", "yes"):
            editor = os.environ.get("EDITOR", "nano")
            try:
                subprocess.run([editor, str(goals_file)], check=False)
            except Exception as e:
                console.print(f"[yellow]Warning: Could not open editor: {e}[/]")
                console.print("[dim]Continuing without edit...[/]")

    # Display plan info
    console.print(f"\n[bold green]Plan created: {plan.plan_id}[/]")
    console.print(f"[dim]Location: {result.plan_dir}/[/]\n")

    # Count match qualities
    excellent_count, acceptable_count, insufficient_count = _count_match_qualities(plan.subgoals)

    # Build and display table
    table = _build_assignments_table(plan.subgoals)
    console.print(table)

    # Summary line
    total = len(plan.subgoals)
    console.print(
        f"\n[dim]Summary: {total} subgoals | "
        f"[green]{excellent_count} excellent[/], "
        f"[yellow]{acceptable_count} acceptable[/], "
        f"[red]{insufficient_count} spawned[/][/]",
    )

    # Display warnings if any
    if result.warnings:
        console.print("\n[yellow]Warnings:[/]")
        for warning in result.warnings:
            console.print(f"  - {warning}")

    # Display next steps
    console.print("\n[bold]Files created:[/]")
    console.print("  [green]✓[/] goals.json")

    console.print("\n[bold green]✅ Goals saved.[/]")
    console.print("\n[bold]Next steps:[/]")
    console.print(f"1. Review goals:   cat {result.plan_dir}/goals.json")
    console.print(
        "2. Generate PRD:   Run [bold]/plan[/] in Claude Code to create prd.md, tasks.md, specs/",
    )
    console.print("3. Start work:     aur implement or aur spawn tasks.md")

    return None


def _count_match_qualities(subgoals: list) -> tuple[int, int, int]:
    """Count subgoals by match quality.

    Args:
        subgoals: List of subgoal objects

    Returns:
        Tuple of (excellent_count, acceptable_count, insufficient_count)
    """
    excellent = 0
    acceptable = 0
    insufficient = 0

    for sg in subgoals:
        match_quality = getattr(sg, "match_quality", None)
        if hasattr(match_quality, "value"):
            match_quality = match_quality.value
        if not match_quality:
            match_quality = "excellent" if sg.ideal_agent == sg.assigned_agent else "acceptable"

        if match_quality == "excellent":
            excellent += 1
        elif match_quality == "acceptable":
            acceptable += 1
        else:
            insufficient += 1

    return excellent, acceptable, insufficient


def _build_assignments_table(subgoals: list) -> Table:
    """Build a Rich table of agent assignments.

    Args:
        subgoals: List of subgoal objects

    Returns:
        Rich Table object
    """
    from rich.table import Table as RichTable

    table = RichTable(title="Agent Assignments", show_header=True, header_style="bold")
    table.add_column("#", style="dim", width=3)
    table.add_column("Subgoal", min_width=30, max_width=50)
    table.add_column("Agent", style="cyan", min_width=18)
    table.add_column("Match", min_width=12)

    for i, sg in enumerate(subgoals, 1):
        match_quality = getattr(sg, "match_quality", None)
        if hasattr(match_quality, "value"):
            match_quality = match_quality.value
        if not match_quality:
            match_quality = "excellent" if sg.ideal_agent == sg.assigned_agent else "acceptable"

        if match_quality == "excellent":
            match_display = "[green]Excellent[/]"
        elif match_quality == "acceptable":
            match_display = "[yellow]Acceptable[/]"
        else:
            match_display = "[red]Spawned[/]"

        title_display = sg.title[:47] + "..." if len(sg.title) > 50 else sg.title
        table.add_row(str(i), title_display, sg.assigned_agent, match_display)

    return table


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
@click.option(
    "--no-cache",
    is_flag=True,
    default=False,
    help="Skip cache and force fresh decomposition",
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
    no_cache: bool,
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
    # Load config and start background model loading
    config = Config()
    _start_background_model_loading(verbose)

    # Resolve tool and model from CLI, env, or config
    resolved_tool, resolved_model = _resolve_tool_and_model(tool, model, config)

    # Validate tool exists
    validation_error = _validate_goals_requirements(resolved_tool)
    if validation_error:
        console.print(f"[red]Error: {validation_error}[/]")
        console.print("[dim]Install the tool or set a different one with --tool flag[/]")
        raise click.Abort()

    # Display header
    _display_header(goal, resolved_tool)

    if verbose:
        console.print(f"[dim]Using tool: {resolved_tool} (model: {resolved_model})[/]")

    # Validate LLM client
    try:
        _ = CLIPipeLLMClient(tool=resolved_tool, model=resolved_model)
    except ValueError as e:
        console.print(f"[red]Error creating LLM client: {e}[/]")
        raise click.Abort()

    # Auto-initialize if needed
    if not no_auto_init:
        _ensure_aurora_initialized(verbose)

    # Show decomposition progress
    if verbose and not no_decompose:
        _show_decomposition_progress(goal, resolved_tool, resolved_model)

    # Generate plan
    skip_confirm = yes or non_interactive
    result = _generate_goals_plan(
        goal=goal,
        context_files=list(context_files) if context_files else None,
        no_decompose=no_decompose,
        config=config,
        yes=skip_confirm,
        no_cache=no_cache,
    )

    # Show agent matching results in verbose mode
    if verbose and result.success and result.plan:
        _show_agent_matching_results(result.plan.subgoals)

    # Handle errors
    if not result.success:
        console.print(f"[red]{result.error}[/]")
        raise click.Abort()

    if result.plan is None:
        console.print("[red]Plan creation succeeded but plan data is missing[/]")
        raise click.Abort()

    # Display results
    json_output = _display_goals_results(
        result=result,
        output_format=output_format,
        _verbose=verbose,
        yes=skip_confirm,
    )

    if json_output is not None:
        print(json_output)


def _display_header(goal: str, tool: str) -> None:
    """Display the goals command header panel.

    Args:
        goal: The goal description
        tool: The resolved tool name
    """
    from rich.panel import Panel

    console.print()
    console.print(
        Panel(
            f"[cyan]{goal}[/]",
            title="[bold]Aurora Goals[/]",
            subtitle=f"[dim]Tool: {tool}[/]",
            border_style="blue",
        ),
    )


def _show_decomposition_progress(goal: str, tool: str, model: str) -> None:
    """Show decomposition progress message.

    Args:
        goal: The goal description
        tool: The tool being used
        model: The model being used
    """
    console.print("\n[bold]Decomposing goal into subgoals...[/]")
    console.print(f"   Goal: {goal}")
    console.print(f"   Using: {tool} ({model})")


def _show_agent_matching_results(subgoals: list) -> None:
    """Show agent matching results in verbose mode.

    Args:
        subgoals: List of subgoal objects
    """
    console.print("\n[bold]Agent matching results:[/]")
    for i, sg in enumerate(subgoals, 1):
        is_gap = sg.ideal_agent != sg.assigned_agent
        status = "!" if is_gap else "+"
        color = "yellow" if is_gap else "green"
        console.print(
            f"   {status} sg-{i}: {sg.assigned_agent} "
            f"([{color}]{'GAP' if is_gap else 'MATCHED'}[/{color}])",
        )
