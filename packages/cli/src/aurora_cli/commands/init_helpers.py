"""Helper functions for unified init command.

This module provides helper functions for the unified `aur init` command,
extracted and adapted from init_planning.py for reuse in the new unified flow.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import List

import click
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
