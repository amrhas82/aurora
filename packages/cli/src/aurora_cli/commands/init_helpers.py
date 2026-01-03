"""Helper functions for unified init command.

This module provides helper functions for the unified `aur init` command,
extracted and adapted from init_planning.py for reuse in the new unified flow.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import List

import click
import questionary
from rich.console import Console

from aurora_cli.configurators import TOOL_OPTIONS, ToolRegistry


console = Console()

AURORA_DIR_NAME = ".aurora"


def detect_git_repository(project_path: Path) -> bool:
    """Detect if project has git repository initialized.

    Args:
        project_path: Path to project root

    Returns:
        True if .git directory exists
    """
    git_dir = project_path / ".git"
    return git_dir.exists()


def prompt_git_init() -> bool:
    """Prompt user to initialize git repository.

    Displays benefits of using git with Aurora and asks for confirmation.

    Returns:
        True if user wants to initialize git, False otherwise
    """
    console.print()
    console.print("[yellow]Git repository not found.[/]")
    console.print()
    console.print("[bold]Benefits of using git with Aurora:[/]")
    console.print("  • Version control for plans and generated files")
    console.print("  • Easy rollback of planning iterations")
    console.print("  • Collaboration with team members")
    console.print()

    return click.confirm("Initialize git repository?", default=True)


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


def count_configured_tools(project_path: Path) -> int:
    """Count how many tools are currently configured.

    Args:
        project_path: Path to project root

    Returns:
        Number of configured tools
    """
    configured = detect_configured_tools(project_path)
    return sum(1 for is_configured in configured.values() if is_configured)


def create_directory_structure(project_path: Path) -> None:
    """Create Aurora directory structure for unified init.

    Creates:
    - .aurora/plans/active
    - .aurora/plans/archive
    - .aurora/logs
    - .aurora/cache

    Note: Does NOT create config/tools (legacy directory removed in unified init)

    Args:
        project_path: Path to project root
    """
    aurora_dir = project_path / AURORA_DIR_NAME

    # Create planning directories
    (aurora_dir / "plans" / "active").mkdir(parents=True, exist_ok=True)
    (aurora_dir / "plans" / "archive").mkdir(parents=True, exist_ok=True)

    # Create logs directory (NEW in unified init)
    (aurora_dir / "logs").mkdir(parents=True, exist_ok=True)

    # Create cache directory (NEW in unified init)
    (aurora_dir / "cache").mkdir(parents=True, exist_ok=True)

    # Note: config/tools directory NOT created (removed in unified init)


def detect_project_metadata(project_path: Path) -> dict:
    """Auto-detect project metadata from config files.

    Scans for:
    - Project name (from directory or git)
    - Python (from pyproject.toml)
    - JavaScript/TypeScript (from package.json)
    - Package managers (poetry, npm, yarn)
    - Testing frameworks (pytest, jest)

    Args:
        project_path: Path to project root

    Returns:
        Dictionary with keys: name, date, tech_stack (markdown string)
    """
    metadata = {
        "name": project_path.name,
        "date": datetime.now().strftime("%Y-%m-%d"),
        "tech_stack": "",
    }

    tech_stack_lines = []

    # Detect Python
    pyproject_path = project_path / "pyproject.toml"
    if pyproject_path.exists():
        try:
            import tomli

            with open(pyproject_path, "rb") as f:
                pyproject = tomli.load(f)

            # Detect Python version
            python_version = None
            if "tool" in pyproject and "poetry" in pyproject["tool"]:
                deps = pyproject["tool"]["poetry"].get("dependencies", {})
                if "python" in deps:
                    python_version = deps["python"]
                    # Clean up version string (^3.10 → 3.10)
                    python_version = python_version.replace("^", "").replace("~", "")

            if python_version:
                tech_stack_lines.append(f"- **Language**: Python {python_version} (detected)")
            else:
                tech_stack_lines.append("- **Language**: Python (detected)")

            # Detect Poetry
            if "tool" in pyproject and "poetry" in pyproject["tool"]:
                tech_stack_lines.append("- **Package Manager**: poetry (detected)")

        except Exception:
            # If tomli not available or parse fails, skip
            pass

    # Detect pytest
    pytest_ini = project_path / "pytest.ini"
    if pytest_ini.exists() or (pyproject_path.exists() and "[tool.pytest" in pyproject_path.read_text()):
        tech_stack_lines.append("- **Testing**: pytest (detected)")

    # Detect JavaScript/Node.js
    package_json = project_path / "package.json"
    if package_json.exists():
        try:
            with open(package_json) as f:
                package_data = json.load(f)

            tech_stack_lines.append("- **Runtime**: Node.js (detected)")

            # Detect package manager
            if (project_path / "yarn.lock").exists():
                tech_stack_lines.append("- **Package Manager**: yarn (detected)")
            elif (project_path / "pnpm-lock.yaml").exists():
                tech_stack_lines.append("- **Package Manager**: pnpm (detected)")
            elif (project_path / "package-lock.json").exists():
                tech_stack_lines.append("- **Package Manager**: npm (detected)")

            # Detect testing framework
            if "jest" in package_data.get("devDependencies", {}):
                tech_stack_lines.append("- **Testing**: jest (detected)")
            elif "vitest" in package_data.get("devDependencies", {}):
                tech_stack_lines.append("- **Testing**: vitest (detected)")

        except Exception:
            # If JSON parse fails, skip
            pass

    metadata["tech_stack"] = "\n".join(tech_stack_lines)
    return metadata


def create_project_md(project_path: Path) -> None:
    """Create project.md template with auto-detected metadata.

    Does NOT overwrite if file already exists (preserves custom content).

    Args:
        project_path: Path to project root
    """
    aurora_dir = project_path / AURORA_DIR_NAME
    project_md = aurora_dir / "project.md"

    # Don't overwrite existing file
    if project_md.exists():
        return

    # Detect project metadata
    metadata = detect_project_metadata(project_path)

    # Build template with detected metadata
    tech_stack_section = metadata["tech_stack"] if metadata["tech_stack"] else "[No tech stack detected - fill in manually]"

    template = f"""# Project Overview: {metadata["name"]}

<!-- Auto-detected by Aurora on {metadata["date"]} -->

## Description

[TODO: Add project description]

## Tech Stack

{tech_stack_section}

## Conventions

- **Code Style**: [e.g., Black, Ruff, PEP 8]
- **Testing**: [e.g., pytest, 90% coverage target]
- **Documentation**: [e.g., Google-style docstrings]
- **Git**: [e.g., conventional commits, feature branches]

## Architecture

[TODO: Brief system architecture overview]

## Key Directories

- `src/` - [Description]
- `tests/` - [Description]
- `docs/` - [Description]

## Notes

[TODO: Additional context for AI assistants]
"""

    project_md.write_text(template, encoding="utf-8")


async def prompt_tool_selection(configured_tools: dict[str, bool]) -> list[str]:
    """Prompt user to select tools for configuration.

    Args:
        configured_tools: Dictionary mapping tool IDs to configured status

    Returns:
        List of selected tool IDs
    """
    choices = []

    # Build checkbox choices
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
                checked=is_configured,  # Pre-check if already configured
            )
        )

    # Add Universal AGENTS.md option
    is_universal_configured = configured_tools.get("universal-agents.md", False)
    universal_label = "Universal AGENTS.md (for other tools)"
    if is_universal_configured:
        universal_label += " (already configured)"

    choices.append(
        questionary.Choice(
            title=universal_label,
            value="universal-agents-md",
            checked=True,  # Always checked by default
        )
    )

    # Show selection prompt
    console.print()
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


async def configure_tools(
    project_path: Path,
    selected_tool_ids: list[str],
) -> tuple[list[str], list[str]]:
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
        # Normalize ID
        if tool_id == "universal-agents-md":
            tool_id = "universal-agents.md"

        configurator = ToolRegistry.get(tool_id)
        if not configurator:
            continue

        config_file = project_path / configurator.config_file_name
        existed = config_file.exists()

        # Check if it's already configured (has markers)
        has_markers = False
        if existed:
            content = config_file.read_text(encoding="utf-8")
            has_markers = "<!-- AURORA:START -->" in content and "<!-- AURORA:END -->" in content

        await configurator.configure(project_path, AURORA_DIR_NAME)

        # Track as updated only if it existed AND had markers
        if has_markers:
            updated.append(configurator.name)
        else:
            created.append(configurator.name)

    return created, updated


def show_status_summary(project_path: Path) -> None:
    """Display current initialization status summary.

    Shows:
    - Step 1: Planning setup status (directories, project.md)
    - Step 2: Memory indexing status (chunk count if exists)
    - Step 3: Tool configuration status (tool count)

    Args:
        project_path: Path to project root
    """
    import sqlite3
    from datetime import datetime

    console.print()
    console.print("[bold cyan]Current Initialization Status:[/]")
    console.print()

    aurora_dir = project_path / AURORA_DIR_NAME

    # Check if .aurora exists
    aurora_exists = aurora_dir.exists()

    if not aurora_exists:
        console.print("[yellow]Aurora directory not found - project not initialized[/]")
        # Still check for tools even without .aurora
    else:
        # Step 1: Planning Setup
        plans_active = aurora_dir / "plans" / "active"
        project_md = aurora_dir / "project.md"

        if plans_active.exists() and project_md.exists():
            # Get modification time for context
            mtime = datetime.fromtimestamp(project_md.stat().st_mtime)
            mtime_str = mtime.strftime("%Y-%m-%d %H:%M")
            console.print(f"[green]✓[/] Step 1: Planning setup [dim](last modified: {mtime_str})[/]")
        elif plans_active.exists():
            # Directory exists but no project.md
            console.print("[yellow]●[/] Step 1: Planning setup [dim](incomplete - missing project.md)[/]")
        else:
            console.print("[yellow]●[/] Step 1: Planning setup [dim](not complete)[/]")

        # Step 2: Memory Indexing
        memory_db = aurora_dir / "memory.db"
        if memory_db.exists():
            try:
                # Count chunks in database
                conn = sqlite3.connect(str(memory_db))
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM chunks")
                chunk_count = cursor.fetchone()[0]
                conn.close()

                console.print(f"[green]✓[/] Step 2: Memory indexed [dim]({chunk_count} chunks)[/]")
            except Exception:
                # Database exists but can't be read
                console.print("[yellow]●[/] Step 2: Memory database exists but may be corrupted")
        else:
            console.print("[yellow]●[/] Step 2: Memory indexing [dim](not complete)[/]")

    # Step 3: Tool Configuration - always check, even without .aurora
    tool_count = count_configured_tools(project_path)
    if tool_count > 0:
        console.print(f"[green]✓[/] Step 3: Tools configured [dim]({tool_count} tools)[/]")
    else:
        if aurora_exists:
            console.print("[yellow]●[/] Step 3: Tool configuration [dim](not complete)[/]")
        else:
            console.print("[yellow]●[/] Step 3: Tool configuration [dim](0 tools found)[/]")

    console.print()


def prompt_rerun_options() -> str:
    """Prompt user for re-run option when initialization already exists.

    Displays menu with 4 options:
    1. Re-run all steps
    2. Select specific steps
    3. Configure tools only
    4. Exit without changes

    Returns:
        One of: "all", "selective", "config", "exit"
    """
    console.print()
    console.print("[bold cyan]Aurora is already initialized in this project.[/]")
    console.print()
    console.print("What would you like to do?")
    console.print("  [bold]1.[/] Re-run all steps")
    console.print("  [bold]2.[/] Select specific steps to re-run")
    console.print("  [bold]3.[/] Configure tools only")
    console.print("  [bold]4.[/] Exit without changes")
    console.print()

    while True:
        choice = click.prompt("Choose an option", type=str, default="4")

        if choice == "1":
            return "all"
        elif choice == "2":
            return "selective"
        elif choice == "3":
            return "config"
        elif choice == "4":
            return "exit"
        else:
            console.print(f"[yellow]Invalid choice: {choice}. Please enter 1, 2, 3, or 4.[/]")
            console.print()


def selective_step_selection() -> list[int]:
    """Prompt user to select specific initialization steps to re-run.

    Displays checkbox with 3 step options:
    - Step 1: Planning setup
    - Step 2: Memory indexing
    - Step 3: Tool configuration

    Returns:
        List of selected step numbers (e.g., [1, 3] or [])
    """
    choices = [
        {"name": "Step 1: Planning setup (git, directories, project.md)", "value": "1"},
        {"name": "Step 2: Memory indexing (index codebase)", "value": "2"},
        {"name": "Step 3: Tool configuration (Claude, Cursor, etc.)", "value": "3"},
    ]

    console.print()
    selected = questionary.checkbox(
        "Select steps to re-run (Space to select, Enter to confirm):",
        choices=choices,
    ).ask()

    if not selected:
        console.print("[yellow]No steps selected. Nothing will be changed.[/]")
        return []

    # Convert string values to integers
    return [int(step) for step in selected]
