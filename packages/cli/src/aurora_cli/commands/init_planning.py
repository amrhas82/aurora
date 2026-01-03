"""Enhanced initialization command with tool configuration.

This module provides a comprehensive initialization flow for Aurora planning
with 3-step interactive wizard for tool selection and configuration.
"""

import asyncio
from pathlib import Path
from typing import List, Optional

import click
import questionary
from rich.console import Console
from rich.panel import Panel

from aurora_cli.configurators import ToolRegistry, TOOL_OPTIONS
from aurora_cli.errors import handle_errors

console = Console()

AURORA_DIR_NAME = ".aurora"


def detect_existing_setup(project_path: Path) -> bool:
    """Detect if .aurora directory already exists.

    Args:
        project_path: Path to project root

    Returns:
        True if .aurora directory exists
    """
    aurora_dir = project_path / AURORA_DIR_NAME
    return aurora_dir.exists()


def detect_configured_tools(project_path: Path) -> dict[str, bool]:
    """Detect which tools are already configured.

    Args:
        project_path: Path to project root

    Returns:
        Dictionary mapping tool IDs to configured status
    """
    configured = {}
    for tool_option in TOOL_OPTIONS:
        tool_id = tool_option["value"]
        configurator = ToolRegistry.get(tool_id)
        if configurator:
            config_file = project_path / configurator.config_file_name
            # Check if file exists and contains Aurora markers
            is_configured = False
            if config_file.exists():
                content = config_file.read_text(encoding="utf-8")
                is_configured = "<!-- AURORA:START -->" in content and "<!-- AURORA:END -->" in content
            configured[tool_id] = is_configured
        else:
            configured[tool_id] = False

    return configured


def display_welcome_banner(extend_mode: bool) -> None:
    """Display welcome banner.

    Args:
        extend_mode: Whether this is extending existing setup
    """
    console.print()
    if extend_mode:
        console.print("[bold cyan]Aurora Planning System - Extend Setup[/]")
        console.print("[dim]Detected existing .aurora directory[/]")
    else:
        console.print("[bold cyan]Aurora Planning System - Initial Setup[/]")
        console.print("[dim]Configure AI coding tools for Aurora planning[/]")
    console.print()


async def prompt_tool_selection(
    configured_tools: dict[str, bool],
    extend_mode: bool,
) -> List[str]:
    """Prompt user to select tools interactively.

    Args:
        configured_tools: Dictionary of tool IDs to configured status
        extend_mode: Whether this is extending existing setup

    Returns:
        List of selected tool IDs
    """
    # Build choices
    choices = []
    for tool_option in TOOL_OPTIONS:
        tool_id = tool_option["value"]
        tool_name = tool_option["name"]
        is_configured = configured_tools.get(tool_id, False)

        if is_configured:
            label = f"{tool_name} (already configured)"
        else:
            label = tool_name

        choices.append(
            questionary.Choice(
                title=label,
                value=tool_id,
                checked=is_configured if extend_mode else False,
            )
        )

    # Add Universal AGENTS.md option
    choices.append(
        questionary.Choice(
            title="Universal AGENTS.md (for other tools)",
            value="universal-agents-md",
            checked=True,  # Always checked by default
        )
    )

    # Show selection prompt
    console.print("[bold]Step 2/3: Select Tools[/]")
    console.print("[dim]Select which AI coding tools you want to configure:[/]")
    console.print()

    selected = await questionary.checkbox(
        "Select tools (space to toggle, enter to continue):",
        choices=choices,
        style=questionary.Style(
            [
                ("selected", "fg:cyan bold"),
                ("pointer", "fg:cyan bold"),
                ("highlighted", "fg:cyan"),
                ("checkbox", "fg:white"),
            ]
        ),
    ).ask_async()

    return selected if selected else []


def display_selection_review(selected_tool_ids: List[str]) -> bool:
    """Display selected tools for review.

    Args:
        selected_tool_ids: List of selected tool IDs

    Returns:
        True if user confirms, False to go back
    """
    console.print()
    console.print("[bold]Step 3/3: Review Selections[/]")
    console.print()

    if not selected_tool_ids:
        console.print("[yellow]No tools selected.[/]")
        console.print("[dim]You can still use Aurora planning commands without tool integration.[/]")
    else:
        console.print("[bold]Selected tools:[/]")
        for tool_id in selected_tool_ids:
            # Find tool name
            tool_name = None
            if tool_id == "universal-agents-md":
                tool_name = "Universal AGENTS.md"
            else:
                for opt in TOOL_OPTIONS:
                    if opt["value"] == tool_id:
                        tool_name = opt["name"]
                        break

            if tool_name:
                console.print(f"  [cyan]▌[/] {tool_name}")

    console.print()
    return click.confirm("Proceed with this configuration?", default=True)


async def configure_tools(
    project_path: Path,
    selected_tool_ids: List[str],
) -> tuple[List[str], List[str]]:
    """Configure selected tools.

    Args:
        project_path: Path to project root
        selected_tool_ids: List of selected tool IDs

    Returns:
        Tuple of (created tools, updated tools)
    """
    created = []
    updated = []

    for tool_id in selected_tool_ids:
        if tool_id == "universal-agents-md":
            tool_id = "universal-agents.md"

        configurator = ToolRegistry.get(tool_id)
        if not configurator:
            continue

        config_file = project_path / configurator.config_file_name
        existed = config_file.exists()

        await configurator.configure(project_path, AURORA_DIR_NAME)

        if existed:
            updated.append(configurator.name)
        else:
            created.append(configurator.name)

    return created, updated


def create_directory_structure(project_path: Path) -> None:
    """Create Aurora directory structure.

    Args:
        project_path: Path to project root
    """
    aurora_dir = project_path / AURORA_DIR_NAME

    # Create main directories
    (aurora_dir / "plans" / "active").mkdir(parents=True, exist_ok=True)
    (aurora_dir / "plans" / "archive").mkdir(parents=True, exist_ok=True)
    (aurora_dir / "config" / "tools").mkdir(parents=True, exist_ok=True)

    # Create project.md template
    project_md = aurora_dir / "project.md"
    if not project_md.exists():
        project_md.write_text(
            """# Project Overview

<!-- Fill in details about your project -->

## Description

[Brief description of your project]

## Tech Stack

- **Language**: [e.g., Python 3.10]
- **Framework**: [e.g., FastAPI, Django, Flask]
- **Database**: [e.g., PostgreSQL, MongoDB]
- **Tools**: [e.g., Docker, pytest, mypy]

## Conventions

- **Code Style**: [e.g., Black, Ruff, PEP 8]
- **Testing**: [e.g., pytest, 90% coverage target]
- **Documentation**: [e.g., Google-style docstrings]
- **Git**: [e.g., conventional commits, feature branches]

## Architecture

[Brief overview of your system architecture]

## Key Directories

- `src/` - [Description]
- `tests/` - [Description]
- `docs/` - [Description]

## Notes

[Any additional context for AI assistants]
""",
            encoding="utf-8",
        )


def display_success_message(
    created: List[str],
    updated: List[str],
    extend_mode: bool,
) -> None:
    """Display success message with next steps.

    Args:
        created: List of newly created tool names
        updated: List of updated tool names
        extend_mode: Whether this was extending existing setup
    """
    console.print()

    if extend_mode:
        console.print("[bold green]✓ Aurora planning configuration updated![/]")
    else:
        console.print("[bold green]✓ Aurora planning initialized successfully![/]")

    console.print()
    console.print("[bold]Tool Configuration:[/]")

    if created:
        console.print("  [green]Created:[/]")
        for tool in created:
            console.print(f"    [cyan]▌[/] {tool}")

    if updated:
        console.print("  [dim]Updated:[/]")
        for tool in updated:
            console.print(f"    [dim cyan]▌[/] {tool}[/]")

    if not created and not updated:
        console.print("  [dim]No tools configured[/]")

    # Next steps
    console.print()
    next_steps = [
        "[bold]1. Restart your IDE/tool[/]",
        "   [dim]Configuration changes require a restart[/]",
        "",
        "[bold]2. Fill in project.md[/]",
        "   [cyan].aurora/project.md[/]",
        "   [dim]Add project context for better AI assistance[/]",
        "",
        "[bold]3. Create your first plan[/]",
        "   [cyan]aur plan create \"Your goal here\"[/]",
        "",
        "[bold]4. List and view plans[/]",
        "   [cyan]aur plan list[/]",
        "   [cyan]aur plan view <plan-id>[/]",
    ]

    console.print(Panel("\n".join(next_steps), title="[bold]Next Steps[/]", border_style="green"))
    console.print()


@click.command(name="init-planning")
@click.option(
    "--tools",
    type=str,
    default=None,
    help="Comma-separated list of tools (non-interactive mode). Use 'all', 'none', or tool names.",
)
@click.option(
    "--path",
    type=click.Path(),
    default=None,
    help="Project path (default: current directory)",
)
@handle_errors
def init_planning_command(tools: Optional[str], path: Optional[str]) -> None:
    """Initialize Aurora planning with tool configuration.

    This command sets up the Aurora planning system with a 3-step
    interactive wizard:

    Step 1: Detects existing setup
    Step 2: Select tools to configure
    Step 3: Review and confirm

    \b
    Examples:
        # Interactive mode (recommended)
        aur init-planning

        \b
        # Non-interactive with specific tools
        aur init-planning --tools "claude-code,opencode"

        \b
        # Non-interactive with all tools
        aur init-planning --tools all

        \b
        # Non-interactive with no tools (directory setup only)
        aur init-planning --tools none
    """
    # Determine project path
    project_path = Path(path) if path else Path.cwd()

    # Step 1: Detect existing setup
    extend_mode = detect_existing_setup(project_path)
    configured_tools = detect_configured_tools(project_path)

    # Display welcome
    display_welcome_banner(extend_mode)

    # Non-interactive mode
    if tools is not None:
        selected_tool_ids = []
        if tools.lower() == "all":
            selected_tool_ids = [opt["value"] for opt in TOOL_OPTIONS]
            selected_tool_ids.append("universal-agents-md")
        elif tools.lower() != "none":
            selected_tool_ids = [t.strip() for t in tools.split(",")]

        console.print(f"[dim]Non-interactive mode: configuring {len(selected_tool_ids)} tools[/]")
        console.print()
    else:
        # Step 2: Interactive tool selection
        console.print("[bold]Step 1/3: Detect Setup[/]")
        if extend_mode:
            console.print("[cyan]✓[/] Found existing .aurora directory")
            console.print()
        else:
            console.print("[dim]No existing setup detected[/]")
            console.print()

        # Run async prompt
        selected_tool_ids = asyncio.run(prompt_tool_selection(configured_tools, extend_mode))

        if selected_tool_ids is None:
            console.print("[yellow]Setup cancelled.[/]")
            return

        # Step 3: Review
        if not display_selection_review(selected_tool_ids):
            console.print("[yellow]Setup cancelled.[/]")
            return

    # Create directory structure
    console.print()
    console.print("[dim]Creating directory structure...[/]")
    create_directory_structure(project_path)

    # Configure tools
    console.print("[dim]Configuring tools...[/]")
    created, updated = asyncio.run(configure_tools(project_path, selected_tool_ids))

    # Success message
    display_success_message(created, updated, extend_mode)


if __name__ == "__main__":
    init_planning_command()
