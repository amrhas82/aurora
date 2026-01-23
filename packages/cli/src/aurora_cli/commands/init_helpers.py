"""Helper functions for unified init command.

This module provides helper functions for the unified `aur init` command,
extracted and adapted from init_planning.py for reuse in the new unified flow.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import List  # noqa: F401

import click
import questionary
from rich.console import Console

from aurora_cli.configurators import ToolRegistry
from aurora_cli.configurators.slash import SlashCommandRegistry
from aurora_cli.templates.headless import PROMPT_TEMPLATE, SCRATCHPAD_TEMPLATE

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
    """Detect which tools are already configured by checking for slash command files.

    Args:
        project_path: Path to project root

    Returns:
        Dictionary mapping SlashCommandRegistry tool IDs to configured status

    """
    configured = {}

    # Check each slash command configurator
    for configurator in SlashCommandRegistry.get_all():
        tool_id = configurator.tool_id

        # Check if any slash command file exists for this tool
        # We check the first command (search) as a representative
        try:
            search_path = configurator.get_relative_path("search")
            slash_file = project_path / search_path

            is_configured = False
            if slash_file.exists():
                content = slash_file.read_text(encoding="utf-8")
                # Check for Aurora markers
                is_configured = (
                    "<!-- AURORA:START -->" in content and "<!-- AURORA:END -->" in content
                )

            configured[tool_id] = is_configured
        except (KeyError, Exception):
            # If tool doesn't support slash commands, mark as not configured
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


def get_configured_tool_ids(project_path: Path) -> list[str]:
    """Get list of tool IDs that are configured in the project.

    Used by agent discovery to scan only paths for configured tools.
    Checks slash command configuration for all 20 supported tools.

    Args:
        project_path: Path to project root

    Returns:
        List of configured tool IDs (e.g., ['claude', 'cursor'])

    """
    # Use slash tool detection which covers all 20 tools
    configured = detect_configured_slash_tools(project_path)
    return [tool_id for tool_id, is_configured in configured.items() if is_configured]


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
            # Check ANY target file for this tool (not just first)
            targets = configurator.get_targets()
            for target in targets:
                file_path = project_path / target.path

                if file_path.exists():
                    try:
                        content = file_path.read_text(encoding="utf-8")
                        if "<!-- AURORA:START -->" in content and "<!-- AURORA:END -->" in content:
                            is_configured = True
                            break  # Found one configured file, that's enough
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
    - .aurora/headless

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

    # Create headless directory for autonomous experiments
    (aurora_dir / "headless").mkdir(parents=True, exist_ok=True)

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
    if pytest_ini.exists() or (
        pyproject_path.exists() and "[tool.pytest" in pyproject_path.read_text()
    ):
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
    tech_stack_section = (
        metadata["tech_stack"]
        if metadata["tech_stack"]
        else "[No tech stack detected - fill in manually]"
    )

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


def create_headless_templates(project_path: Path) -> None:
    """Create headless mode template files in .aurora/headless/.

    Creates:
    - prompt.md.template - Example prompt structure (from centralized template)
    - scratchpad.md - Initial scratchpad state (from centralized template)
    - README.md - Usage instructions for headless mode

    Does NOT overwrite if files already exist.

    Args:
        project_path: Path to project root

    """
    aurora_dir = project_path / AURORA_DIR_NAME
    headless_dir = aurora_dir / "headless"
    headless_dir.mkdir(parents=True, exist_ok=True)

    # Create prompt template from centralized template
    prompt_template_path = headless_dir / "prompt.md.template"
    if not prompt_template_path.exists():
        # Use centralized template but replace {goal} placeholder for user template
        prompt_content = PROMPT_TEMPLATE.replace("{goal}", "[Describe what you want to achieve]")
        # Add optional sections for user template
        prompt_content += """
# Success Criteria
- [ ] Criterion 1
- [ ] Criterion 2
- [ ] Criterion 3

# Constraints (Optional)
- Constraint 1 (e.g., "Don't modify production code")
- Constraint 2 (e.g., "Use existing test framework")

# Context (Optional)
Additional context about the task, relevant files, or background information...
"""
        prompt_template_path.write_text(prompt_content, encoding="utf-8")

    # Create scratchpad from centralized template
    scratchpad_path = headless_dir / "scratchpad.md"
    if not scratchpad_path.exists():
        scratchpad_path.write_text(SCRATCHPAD_TEMPLATE, encoding="utf-8")

    # Create README
    readme = headless_dir / "README.md"
    if not readme.exists():
        readme_content = """# Headless Mode

Autonomous Claude execution loop - let Claude work on a goal until done.

## Quick Start

1. Copy the template to create your prompt:
   ```bash
   cp prompt.md.template prompt.md
   ```

2. Edit `prompt.md` with your goal

3. Run headless mode:
   ```bash
   aur headless -t claude --max=10
   ```

## How It Works

1. Claude reads your prompt (goal + instructions)
2. Claude works autonomously, rewriting scratchpad.md with current state
3. Loop checks for `STATUS: DONE` in scratchpad
4. Exits early when done, or after max iterations

## Commands

```bash
# Form 1: Default prompt (.aurora/headless/prompt.md)
aur headless --max=10

# Form 2: Custom prompt file
aur headless -p my-task.md --max=10

# Form 3: With test backpressure
aur headless --test-cmd "pytest tests/" --max=15

# Allow running on main branch (dangerous)
aur headless --allow-main
```

## Files

- `prompt.md.template` - Example prompt structure
- `prompt.md` - Your task definition (copy from template)
- `scratchpad.md` - Claude's state (rewritten each iteration)

## Key Concepts

### Scratchpad Rewrite (Not Append)
Claude rewrites scratchpad.md each iteration with current state only.
This keeps context bounded and prevents history accumulation.

### STATUS: DONE
When Claude completes the goal, it sets `STATUS: DONE` in scratchpad.
The loop detects this and exits early.

### Backpressure (Optional)
Use `--test-cmd` to run tests after each iteration.
If tests fail, Claude sees the failure next iteration.

## Safety Features

- **Git branch check**: Prevents running on main/master by default
- **Max iterations**: Prevents runaway execution
- **Scratchpad state**: Visible progress tracking

## Scratchpad Format

```markdown
# Scratchpad

## STATUS: IN_PROGRESS  (or DONE when complete)

## Completed
- Task 1
- Task 2

## Current Task
Working on X...

## Blockers
(none)

## Next Steps
- Step 1
- Step 2
```
"""
        readme.write_text(readme_content, encoding="utf-8")


async def prompt_tool_selection(configured_tools: dict[str, bool]) -> list[str]:
    """Prompt user to select tools for configuration with grouped UI.

    Uses SlashCommandRegistry to get all 20 available AI coding tools.
    Shows a two-step process: selection and review.

    Args:
        configured_tools: Dictionary mapping tool IDs to configured status

    Returns:
        List of selected tool IDs

    """
    while True:
        # Build checkbox choices with grouped sections
        choices = []

        # Header for all native providers
        choices.append(
            questionary.Separator(
                "\nNatively supported providers (✔ Aurora custom slash commands available)",
            ),
        )

        # Add all tools sorted alphabetically
        for configurator in sorted(
            SlashCommandRegistry.get_all(),
            key=lambda c: c.name,
        ):
            tool_id = configurator.tool_id
            tool_name = configurator.name
            is_configured = configured_tools.get(tool_id, False)

            if is_configured:
                label = f"  {tool_name} (already configured)"
            else:
                label = f"  {tool_name}"

            choices.append(
                questionary.Choice(
                    title=label,
                    value=tool_id,
                    checked=is_configured,
                ),
            )

        # Show selection prompt
        console.print()
        console.print("[bold cyan]Welcome to Aurora![/]")
        console.print("[bold]Select AI coding tools[/]")
        console.print()

        selected = await questionary.checkbox(
            "Select tools to configure:",
            choices=choices,
            instruction="(↑↓ navigate, space=toggle, a=all, enter=confirm)",
            style=questionary.Style(
                [
                    ("selected", "fg:cyan bold"),
                    ("pointer", "fg:cyan bold"),
                    ("highlighted", "fg:cyan"),
                    ("checkbox", "fg:white"),
                    ("separator", "fg:white dim"),
                ],
            ),
        ).ask_async()

        if not selected:
            return []

        # Show review step
        console.print()
        console.print("[bold cyan]Welcome to Aurora![/]")
        console.print("[bold]Review selections[/]")
        console.print()

        # Display selected tools
        tool_names = []
        for tool_id in sorted(selected):
            configurator = SlashCommandRegistry.get(tool_id)
            if configurator:
                tool_names.append(configurator.name)
                console.print(f"  ▌ {configurator.name}")

        console.print()

        # Confirm or adjust
        confirm = await questionary.confirm(
            "Press Enter to confirm or n to adjust",
            default=True,
            auto_enter=False,
        ).ask_async()

        if confirm:
            return selected

        # User wants to adjust - loop back to selection
        console.print()
        console.print("[dim]Adjusting selections...[/]")
        console.print()


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

        # Use SlashCommandRegistry name if available, for consistent display
        # This prevents duplicate entries like "Claude" and "Claude Code"
        slash_configurator = SlashCommandRegistry.get(tool_id)
        display_name = slash_configurator.name if slash_configurator else configurator.name

        # Track as updated only if it existed AND had markers
        if has_markers:
            updated.append(display_name)
        else:
            created.append(display_name)

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
            console.print(
                f"[green]✓[/] Step 1: Planning setup [dim](last modified: {mtime_str})[/]",
            )
        elif plans_active.exists():
            # Directory exists but no project.md
            console.print(
                "[yellow]●[/] Step 1: Planning setup [dim](incomplete - missing project.md)[/]",
            )
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
    # Use slash command detection (new system) instead of old TOOL_OPTIONS
    slash_configured = detect_configured_slash_tools(project_path)
    configured_tool_ids = [
        tool_id for tool_id, is_configured in slash_configured.items() if is_configured
    ]
    tool_count = len(configured_tool_ids)

    if tool_count > 0:
        # Get tool display names
        tool_names = []
        for tool_id in sorted(configured_tool_ids):
            configurator = SlashCommandRegistry.get(tool_id)
            if configurator:
                tool_names.append(configurator.name)

        tools_str = ", ".join(tool_names)
        console.print(f"[green]✓[/] Step 3: Tools configured [dim]({tools_str})[/]")
    else:
        if aurora_exists:
            console.print("[yellow]●[/] Step 3: Tool configuration [dim](not complete)[/]")
        else:
            console.print("[yellow]●[/] Step 3: Tool configuration [dim](0 tools found)[/]")

    console.print()


def prompt_rerun_options() -> str:
    """Prompt user for re-run option when initialization already exists.

    Displays menu with 5 options:
    1. Re-run all steps
    2. Select specific steps
    3. Configure tools only
    4. Refresh agent discovery
    5. Exit without changes

    Returns:
        One of: "all", "selective", "config", "agents", "exit"

    """
    console.print()
    console.print("[bold cyan]Aurora is already initialized in this project.[/]")
    console.print()
    console.print("What would you like to do?")
    console.print("  [bold]1.[/] Re-run all steps")
    console.print("  [bold]2.[/] Select specific steps to re-run")
    console.print("  [bold]3.[/] Configure tools only")
    console.print("  [bold]4.[/] Refresh agent discovery")
    console.print("  [bold]5.[/] Exit without changes")
    console.print()

    while True:
        choice = click.prompt("Choose an option", type=str, default="5")

        if choice == "1":
            return "all"
        if choice == "2":
            return "selective"
        if choice == "3":
            return "config"
        if choice == "4":
            return "agents"
        if choice == "5":
            return "exit"
        console.print(f"[yellow]Invalid choice: {choice}. Please enter 1, 2, 3, 4, or 5.[/]")
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
        "Select steps to re-run:",
        choices=choices,
        instruction="(space=toggle, enter=confirm)",
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
) -> tuple[list[str], list[str], list[str], list[str]]:
    """Configure MCP servers for tools that support MCP.

    Only configures MCP for tools that:
    1. Were selected by the user (in tool_ids)
    2. Have MCP support (registered in MCPConfigRegistry)

    After configuration, validates each MCP config file with soft failures
    (warnings instead of errors).

    Args:
        project_path: Path to project root
        tool_ids: List of tool IDs selected by user (may include non-MCP tools)

    Returns:
        Tuple of (created_tools, updated_tools, skipped_tools, validation_warnings):
        - created_tools: Tools where MCP config was newly created
        - updated_tools: Tools where MCP config was updated
        - skipped_tools: Tools in tool_ids that don't support MCP
        - validation_warnings: List of validation warning messages

    """
    from aurora_cli.configurators.mcp import MCPConfigRegistry

    created: list[str] = []
    updated: list[str] = []
    skipped: list[str] = []
    validation_warnings: list[str] = []

    if not tool_ids:
        return created, updated, skipped, validation_warnings

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

        # Use SlashCommandRegistry name for consistent display
        # This prevents "Claude Code" vs "Claude" mismatch
        slash_configurator = SlashCommandRegistry.get(tool_id)
        display_name = slash_configurator.name if slash_configurator else configurator.name

        if result.success:
            if was_configured:
                updated.append(display_name)
            else:
                created.append(display_name)

            # Log any warnings from configuration
            for warning in result.warnings:
                console.print(f"  [yellow]⚠[/] {display_name}: {warning}")

            # Validate the configuration after creation/update
            config_path = configurator.get_config_path(project_path)
            success, warnings = _validate_mcp_config(config_path, project_path)

            # Add tool-prefixed validation warnings
            for warning in warnings:
                validation_warnings.append(f"{display_name}: {warning}")
        else:
            console.print(f"  [red]✗[/] {display_name}: {result.message}")

    return created, updated, skipped, validation_warnings


def get_mcp_capable_from_selection(tool_ids: list[str]) -> list[str]:
    """Filter tool IDs to only those that support MCP.

    Args:
        tool_ids: List of all selected tool IDs

    Returns:
        List of tool IDs that have MCP support

    """
    from aurora_cli.configurators.mcp import MCPConfigRegistry

    return [tid for tid in tool_ids if MCPConfigRegistry.supports_mcp(tid)]


def _validate_mcp_config(config_path: Path, _project_path: Path) -> tuple[bool, list[str]]:
    """Validate MCP configuration file with soft failures.

    Performs validation checks:
    1. JSON syntax validation
    2. Aurora MCP server presence check
    3. Server command/path validation

    This function uses soft failures - returns warnings instead of raising
    exceptions to allow init to complete even with configuration issues.

    Args:
        config_path: Path to MCP configuration file
        _project_path: Path to project root (reserved for future use)

    Returns:
        Tuple of (success: bool, warnings: list[str])
        - success: False if critical validation failed, True if config is valid
        - warnings: List of warning messages for non-fatal issues

    """
    warnings: list[str] = []

    # Check if file exists
    if not config_path.exists():
        return False, [f"MCP config file not found: {config_path}"]

    # Read and parse JSON
    try:
        content = config_path.read_text(encoding="utf-8")

        # Handle empty file
        if not content.strip():
            return False, ["MCP config file is empty"]

        config = json.loads(content)
    except json.JSONDecodeError as e:
        return False, [f"MCP config has invalid JSON syntax: {e}"]
    except OSError as e:
        return False, [f"Failed to read MCP config: {e}"]

    # Check for Aurora MCP server
    aurora_config = None
    if "mcpServers" in config and "aurora" in config["mcpServers"]:
        aurora_config = config["mcpServers"]["aurora"]
    elif "aurora" in config:
        aurora_config = config["aurora"]

    if not aurora_config:
        warnings.append("Aurora MCP server not found in configuration")
        return True, warnings  # Not critical - may be intentional

    # Validate server command format
    command = aurora_config.get("command", "")
    args = aurora_config.get("args", [])

    valid_command = False
    if command == "aurora-mcp":
        valid_command = True
    elif command == "python3" and "-m" in args and "aurora_mcp.server" in args:
        valid_command = True

    if not valid_command and command:
        warnings.append(f"Aurora MCP server has unexpected command format: {command}")

    # Note: We don't validate actual tool availability here as that would
    # require importing aurora_mcp which may not be installed yet.
    # That validation is done in 'aur doctor' command instead.

    return True, warnings
