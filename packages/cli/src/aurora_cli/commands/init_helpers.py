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
from aurora_cli.configurators.slash import SlashCommandRegistry


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


def detect_configured_slash_tools(project_path: Path) -> dict[str, bool]:
    """Detect which slash command tools are already configured.

    Checks for Aurora markers in expected file paths for all 20 AI coding tools
    in the SlashCommandRegistry. This enables "extend mode" where users can
    add new tools without reconfiguring existing ones.

    Special handling for Codex: checks global path (~/.codex/prompts/ or
    $CODEX_HOME/prompts/) instead of project-relative path.

    Args:
        project_path: Path to project root

    Returns:
        Dictionary mapping tool IDs to configured status (True if configured)
    """
    import os

    configured: dict[str, bool] = {}

    for configurator in SlashCommandRegistry.get_all():
        tool_id = configurator.tool_id
        is_configured = False

        # Special handling for Codex (uses global path)
        if tool_id == "codex":
            # Get global prompts directory (respects CODEX_HOME env var)
            codex_home = os.environ.get("CODEX_HOME", "").strip()
            if codex_home:
                prompts_dir = Path(codex_home) / "prompts"
            else:
                prompts_dir = Path.home() / ".codex" / "prompts"

            # Check for any Aurora-configured file
            plan_file = prompts_dir / "aurora-plan.md"
            if plan_file.exists():
                try:
                    content = plan_file.read_text(encoding="utf-8")
                    if "<!-- AURORA:START -->" in content and "<!-- AURORA:END -->" in content:
                        is_configured = True
                except Exception:
                    pass
        else:
            # Standard project-relative paths
            # Check the first target file for this tool (e.g., plan.md)
            targets = configurator.get_targets()
            if targets:
                # Use the first command file to check configuration
                first_target = targets[0]
                file_path = project_path / first_target.path

                if file_path.exists():
                    try:
                        content = file_path.read_text(encoding="utf-8")
                        if "<!-- AURORA:START -->" in content and "<!-- AURORA:END -->" in content:
                            is_configured = True
                    except Exception:
                        pass

        configured[tool_id] = is_configured

    return configured


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


def create_agents_md(project_path: Path) -> None:
    """Create .aurora/AGENTS.md with Aurora planning instructions.

    Creates the main AGENTS.md file inside .aurora/ directory with full
    Aurora planning instructions for AI coding assistants.

    Does NOT overwrite if file already exists (preserves custom content).

    Args:
        project_path: Path to project root
    """
    from aurora_cli.templates import get_agents_template

    aurora_dir = project_path / AURORA_DIR_NAME
    agents_md = aurora_dir / "AGENTS.md"

    # Don't overwrite existing file
    if agents_md.exists():
        return

    # Write the full AGENTS.md template
    agents_md.write_text(get_agents_template(), encoding="utf-8")


async def prompt_tool_selection(configured_tools: dict[str, bool]) -> list[str]:
    """Prompt user to select tools for configuration.

    Uses SlashCommandRegistry to get all 20 available AI coding tools.

    Args:
        configured_tools: Dictionary mapping tool IDs to configured status

    Returns:
        List of selected tool IDs
    """
    choices = []

    # Build checkbox choices from SlashCommandRegistry (all 20 tools)
    for configurator in SlashCommandRegistry.get_all():
        tool_id = configurator.tool_id
        tool_name = configurator.name
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
    """Configure selected tools (root config files like CLAUDE.md).

    Maps SlashCommandRegistry IDs to ToolRegistry IDs and configures
    the corresponding root configuration files.

    Args:
        project_path: Path to project root
        selected_tool_ids: List of selected tool IDs from SlashCommandRegistry

    Returns:
        Tuple of (created tools, updated tools)
    """
    # Map from SlashCommandRegistry ID to ToolRegistry ID
    # SlashCommandRegistry uses short IDs like "claude"
    # ToolRegistry uses longer IDs like "claude-code"
    TOOL_ID_MAP = {
        "claude": "claude-code",
        "universal-agents-md": "universal-agents.md",
        # Add more mappings as needed
    }

    created = []
    updated = []

    for tool_id in selected_tool_ids:
        # Map to ToolRegistry ID if needed
        registry_id = TOOL_ID_MAP.get(tool_id, tool_id)

        configurator = ToolRegistry.get(registry_id)
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


async def configure_slash_commands(
    project_path: Path,
    tool_ids: list[str],
) -> tuple[list[str], list[str]]:
    """Configure slash commands for selected tools using SlashCommandRegistry.

    Uses the new slash command configurator system with all 20 AI coding tools.

    Args:
        project_path: Path to project root
        tool_ids: List of tool IDs to configure (e.g., ["claude", "cursor", "gemini"])

    Returns:
        Tuple of (created_tools, updated_tools) - lists of tool names
    """
    created: list[str] = []
    updated: list[str] = []

    if not tool_ids:
        return created, updated

    for tool_id in tool_ids:
        configurator = SlashCommandRegistry.get(tool_id)
        if not configurator:
            # Skip invalid tool IDs
            continue

        # Check if any files already exist for this tool
        has_existing = False
        for target in configurator.get_targets():
            file_path = project_path / target.path
            if file_path.exists():
                has_existing = True
                break

        # Generate/update all slash command files for this tool
        configurator.generate_all(str(project_path), AURORA_DIR_NAME)

        # Track as updated if files existed, otherwise created
        if has_existing:
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


def detect_configured_mcp_tools(project_path: Path) -> dict[str, bool]:
    """Detect which MCP tools are already configured.

    Checks MCP configuration status for all MCP-capable tools
    (Claude, Cursor, Cline, Continue).

    Args:
        project_path: Path to project root

    Returns:
        Dictionary mapping tool IDs to configured status (True if configured)
    """
    from aurora_cli.configurators.mcp import MCPConfigRegistry

    configured: dict[str, bool] = {}

    for configurator in MCPConfigRegistry.get_all():
        tool_id = configurator.tool_id
        configured[tool_id] = configurator.is_configured(project_path)

    return configured


def count_configured_mcp_tools(project_path: Path) -> int:
    """Count how many MCP tools are currently configured.

    Args:
        project_path: Path to project root

    Returns:
        Number of configured MCP tools
    """
    configured = detect_configured_mcp_tools(project_path)
    return sum(1 for is_configured in configured.values() if is_configured)


async def configure_mcp_servers(
    project_path: Path,
    tool_ids: list[str],
) -> tuple[list[str], list[str], list[str]]:
    """Configure MCP servers for tools that support MCP.

    Only configures MCP for tools that:
    1. Were selected by the user (in tool_ids)
    2. Have MCP support (registered in MCPConfigRegistry)

    Args:
        project_path: Path to project root
        tool_ids: List of tool IDs selected by user (may include non-MCP tools)

    Returns:
        Tuple of (created_tools, updated_tools, skipped_tools):
        - created_tools: Tools where MCP config was newly created
        - updated_tools: Tools where MCP config was updated
        - skipped_tools: Tools in tool_ids that don't support MCP
    """
    from aurora_cli.configurators.mcp import MCPConfigRegistry

    created: list[str] = []
    updated: list[str] = []
    skipped: list[str] = []

    if not tool_ids:
        return created, updated, skipped

    for tool_id in tool_ids:
        configurator = MCPConfigRegistry.get(tool_id)

        if not configurator:
            # Tool doesn't support MCP (e.g., windsurf, codex)
            skipped.append(tool_id)
            continue

        # Check if already configured
        was_configured = configurator.is_configured(project_path)

        # Configure MCP server
        result = configurator.configure(project_path)

        if result.success:
            if was_configured:
                updated.append(configurator.name)
            else:
                created.append(configurator.name)

            # Log any warnings
            for warning in result.warnings:
                console.print(f"  [yellow]⚠[/] {configurator.name}: {warning}")
        else:
            console.print(f"  [red]✗[/] {configurator.name}: {result.message}")

    return created, updated, skipped


def get_mcp_capable_from_selection(tool_ids: list[str]) -> list[str]:
    """Filter tool IDs to only those that support MCP.

    Args:
        tool_ids: List of all selected tool IDs

    Returns:
        List of tool IDs that have MCP support
    """
    from aurora_cli.configurators.mcp import MCPConfigRegistry

    return [tid for tid in tool_ids if MCPConfigRegistry.supports_mcp(tid)]
