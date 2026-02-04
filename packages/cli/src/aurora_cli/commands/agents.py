"""Agent discovery CLI commands for AURORA CLI.

This module implements the 'aur agents' command group for discovering
and managing AI coding assistant agents:
- aur agents list: List all discovered agents grouped by category
- aur agents search: Search agents by keyword
- aur agents show: Display full details for a specific agent
- aur agents refresh: Force regenerate the agent manifest

Usage:
    aur agents list [--category eng|qa|product|general]
    aur agents search "keyword"
    aur agents show agent-id
    aur agents refresh
"""

from __future__ import annotations

import logging
import time
from difflib import SequenceMatcher
from pathlib import Path
from typing import TYPE_CHECKING

import click
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

from aurora_cli.agent_discovery import (
    AgentCategory,
    AgentInfo,
    AgentManifest,
    AgentScanner,
    ManifestManager,
)
from aurora_cli.config import Config
from aurora_cli.errors import handle_errors

if TYPE_CHECKING:
    pass

__all__ = ["agents_group"]

logger = logging.getLogger(__name__)
console = Console()


def get_manifest_path(config: Config | None = None) -> Path:
    """Get the manifest path from config.

    Args:
        config: Optional Config instance (loads default if not provided)

    Returns:
        Path to the agent manifest file

    """
    if config is None:
        # Load config silently for path lookup
        import io
        import sys

        old_stdout = sys.stdout
        sys.stdout = io.StringIO()
        try:
            config = Config()
        finally:
            sys.stdout = old_stdout

    return Path(config.get_manifest_path())


def get_manifest(force_refresh: bool = False, config: Config | None = None) -> AgentManifest:
    """Get the agent manifest, refreshing if necessary.

    Args:
        force_refresh: Force regeneration even if manifest is fresh
        config: Optional Config instance (loads default if not provided)

    Returns:
        AgentManifest with discovered agents

    """
    if config is None:
        # Load config silently
        import io
        import sys

        old_stdout = sys.stdout
        sys.stdout = io.StringIO()
        try:
            config = Config()
        finally:
            sys.stdout = old_stdout

    manifest_path = get_manifest_path(config)

    # Create scanner with config discovery paths
    scanner = AgentScanner(config.agents_discovery_paths)
    manager = ManifestManager(scanner=scanner)

    if force_refresh:
        manifest = manager.generate()
        manager.save(manifest, manifest_path)
        return manifest

    return manager.get_or_refresh(
        manifest_path,
        auto_refresh=config.agents_auto_refresh,
        refresh_interval_hours=config.agents_refresh_interval_hours,
    )


@click.group(name="agents")
def agents_group() -> None:
    r"""Agent discovery and management commands.

    Discovers agents from tools configured in the current project.
    Agent sources are determined by tool configuration during 'aur init'.

    \b
    Commands:
        list     - List agents for project-configured tools
        search   - Search agents by keyword
        show     - Display full details for an agent
        refresh  - Force regenerate the agent manifest

    \b
    Examples:
        aur agents list                    # List agents for configured tools
        aur agents list --all              # List agents from all tools
        aur agents list --category qa      # List only QA agents
        aur agents search "test"           # Search for test-related agents
        aur agents show quality-assurance  # Show agent details
        aur agents refresh                 # Force manifest refresh

    \b
    Tip: Run 'aur init' and select option [4] to refresh agent discovery.
    """


def _get_project_manifest(
    project_path: Path,
) -> tuple[AgentManifest, str] | None:
    """Get manifest for project-configured tools only.

    Args:
        project_path: Path to the project directory

    Returns:
        Tuple of (manifest, tool_context) if successful, None if no tools configured

    """
    from aurora_cli.commands.init_helpers import get_configured_tool_ids
    from aurora_cli.configurators.slash.paths import get_tool_paths

    configured_tool_ids = get_configured_tool_ids(project_path)

    if not configured_tool_ids:
        console.print(
            "\n[yellow]No tools configured in this project.[/]\n"
            "Run [cyan]aur init[/] to configure tools and discover agents.\n"
            "\n[dim]Tip: Use [cyan]aur agents list --all[/] to see all agents.[/]",
        )
        return None

    # Get agent paths for configured tools
    selected_agent_paths = []
    for tool_id in configured_tool_ids:
        tool_paths = get_tool_paths(tool_id)
        if tool_paths and tool_paths.agents:
            selected_agent_paths.append(tool_paths.agents)

    if not selected_agent_paths:
        console.print(
            "\n[yellow]No agent directories found for configured tools.[/]\n"
            "Run [cyan]aur init[/] and select option [4] to refresh agent discovery.",
        )
        return None

    # Create scanner with project-specific paths
    scanner = AgentScanner(selected_agent_paths)
    manager = ManifestManager(scanner=scanner)
    manifest = manager.generate()
    tool_context = ", ".join(configured_tool_ids)

    return manifest, tool_context


def _display_empty_manifest_message(show_all: bool, tool_context: str) -> None:
    """Display message when no agents are found.

    Args:
        show_all: Whether --all flag was used
        tool_context: Description of tools being searched

    """
    if show_all:
        console.print(
            "\n[yellow]No agents found.[/]\n"
            "Add agent files to tool-specific directories like ~/.claude/agents/",
        )
    else:
        console.print(
            f"\n[yellow]No agents found for configured tools ({tool_context}).[/]\n"
            "Add agent files to the appropriate directories or use [cyan]--all[/] to search everywhere.",
        )


def _filter_and_display_agents(
    manifest: AgentManifest,
    category: str | None,
    output_format: str,
) -> bool:
    """Filter agents by category and display them.

    Args:
        manifest: Agent manifest to filter and display
        category: Category filter (None for all)
        output_format: Output format ('rich', 'simple', 'plan')

    Returns:
        True if agents were displayed, False if category was empty

    """
    if category:
        cat_enum = AgentCategory(category)
        agents = manifest.get_agents_by_category(cat_enum)

        if not agents:
            console.print(f"\n[yellow]No agents found in category '{category}'[/]\n")
            return False

        _display_agents_list(
            {cat_enum: agents},
            output_format,
            total=len(agents),
        )
    else:
        # Group all agents by category
        agents_by_category = {cat: manifest.get_agents_by_category(cat) for cat in AgentCategory}

        _display_agents_list(
            agents_by_category,
            output_format,
            total=manifest.stats.total,
        )

    return True


def _display_options_hint(show_all: bool) -> None:
    """Display available command options hint.

    Args:
        show_all: Whether --all flag was used

    """
    console.print()
    console.print("[dim]Options:[/]")
    console.print("[dim]  aur agents search <keyword>    Search agents by keyword[/]")
    console.print("[dim]  aur agents show <agent-id>     Show agent details[/]")
    if not show_all:
        console.print("[dim]  aur agents list --all          Show agents from all tools[/]")
    console.print("[dim]  aur init -> option [4]          Refresh agent discovery[/]")


@agents_group.command(name="list")
@click.option(
    "--category",
    "-c",
    type=click.Choice(["eng", "qa", "product", "general"]),
    default=None,
    help="Filter agents by category",
)
@click.option(
    "--format",
    "-f",
    "output_format",
    type=click.Choice(["rich", "simple", "plan"]),
    default="rich",
    help="Output format: rich (default), simple (plain text), plan (for plan.md)",
)
@click.option(
    "--all",
    "-a",
    "show_all",
    is_flag=True,
    default=False,
    help="Show agents from all tools (not just project-configured tools)",
)
@handle_errors
def list_command(category: str | None, output_format: str, show_all: bool) -> None:
    r"""List discovered agents for configured tools.

    By default, shows agents only from tools configured in the current project.
    Use --all to show agents from all discovery paths. Uses extracted helper
    functions to reduce complexity.

    \b
    Examples:
        # List agents for project-configured tools
        aur agents list

        \b
        # List all agents from all tools
        aur agents list --all

        \b
        # List only engineering agents
        aur agents list --category eng

        \b
        # Simple output (no Rich formatting)
        aur agents list --format simple
    """
    start_time = time.time()
    project_path = Path.cwd()

    # Get manifest based on scope
    if show_all:
        manifest = get_manifest()
        tool_context = "all tools"
    else:
        result = _get_project_manifest(project_path)
        if result is None:
            return
        manifest, tool_context = result

    # Handle empty manifest
    if manifest.stats.total == 0:
        _display_empty_manifest_message(show_all, tool_context)
        return

    # Filter and display agents
    if not _filter_and_display_agents(manifest, category, output_format):
        return

    # Show timing info for slow operations
    elapsed = time.time() - start_time
    if elapsed > 0.5:
        console.print(f"\n[dim]Completed in {elapsed:.2f}s[/]")

    # Show available options hint
    _display_options_hint(show_all)


@agents_group.command(name="search")
@click.argument("keyword")
@click.option(
    "--limit",
    "-n",
    type=int,
    default=10,
    help="Maximum number of results (default: 10)",
)
@handle_errors
def search_command(keyword: str, limit: int) -> None:
    r"""Search agents by keyword.

    Searches across agent id, role, goal, skills, examples, and when_to_use
    fields. Results are ranked by match quality:
    1. Exact match in id
    2. Partial match in role
    3. Partial match in other fields

    KEYWORD is the search term to match against agent metadata.

    \b
    Examples:
        # Search for test-related agents
        aur agents search "test"

        \b
        # Search with more results
        aur agents search "code review" --limit 20
    """
    manifest = get_manifest()

    if manifest.stats.total == 0:
        console.print("\n[yellow]No agents indexed. Run 'aur agents refresh' first.[/]\n")
        return

    # Perform search
    results = _search_agents(manifest, keyword, limit)

    if not results:
        console.print(f"\n[yellow]No agents found matching '{keyword}'[/]\n")
        return

    # Display results
    console.print(f"\n[bold green]Found {len(results)} agent(s) matching '{keyword}'[/]\n")

    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("Agent ID", style="cyan", width=25)
    table.add_column("Category", style="green", width=10)
    table.add_column("Role", style="white", width=30)
    table.add_column("Match", style="yellow", width=20)

    for agent, match_info in results:
        table.add_row(
            agent.id,
            agent.category.value,
            _truncate(agent.role, 30),
            match_info,
        )

    console.print(table)
    console.print()


@agents_group.command(name="show")
@click.argument("agent_id")
@handle_errors
def show_command(agent_id: str) -> None:
    r"""Display full details for a specific agent.

    Shows comprehensive agent information including:
    - Role and goal
    - Category
    - Skills list
    - Examples
    - When to use guidance
    - Dependencies
    - Source file location

    AGENT_ID is the kebab-case identifier of the agent (e.g., 'quality-assurance').

    \b
    Examples:
        aur agents show quality-assurance
        aur agents show code-developer
    """
    manifest = get_manifest()

    agent = manifest.get_agent(agent_id)

    if agent is None:
        # Try to find similar agents
        suggestions = _find_similar_agents(manifest, agent_id)

        error_msg = f"\n[red]Agent '{agent_id}' not found.[/]\n"
        if suggestions:
            error_msg += "\nDid you mean:\n"
            for suggestion in suggestions[:3]:
                error_msg += f"  - {suggestion.id}\n"

        console.print(error_msg)
        raise click.Abort()

    # Display agent details
    _display_agent_details(agent)


@agents_group.command(name="refresh")
@handle_errors
def refresh_command() -> None:
    r"""Force regenerate the agent manifest.

    Scans all agent source directories and rebuilds the manifest cache.
    Use this after adding, modifying, or removing agent files.

    \b
    Examples:
        aur agents refresh
    """
    console.print("\n[bold]Refreshing agent manifest...[/]\n")

    start_time = time.time()

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("Scanning agent sources...", total=None)

        manifest = get_manifest(force_refresh=True)

        progress.update(task, description="Complete!")

    elapsed = time.time() - start_time

    # Display summary
    summary_lines = [
        "[bold green]Manifest refreshed successfully[/]\n",
        f"Agents found: [cyan]{manifest.stats.total}[/]",
        f"Sources scanned: [cyan]{len(manifest.sources)}[/]",
        f"Malformed files: [yellow]{manifest.stats.malformed_files}[/]",
        f"Duration: [cyan]{elapsed:.2f}s[/]",
    ]

    if manifest.stats.by_category:
        summary_lines.append("\nAgents by category:")
        for cat, count in sorted(manifest.stats.by_category.items()):
            if count > 0:
                summary_lines.append(f"  {cat}: [cyan]{count}[/]")

    console.print(
        Panel.fit(
            "\n".join(summary_lines),
            title="Refresh Summary",
            border_style="green",
        ),
    )
    console.print()


def _display_agents_list(
    agents_by_category: dict[AgentCategory, list[AgentInfo]],
    output_format: str,
    total: int,
) -> None:
    """Display agents grouped by category.

    Args:
        agents_by_category: Dictionary mapping category to agent list
        output_format: 'rich', 'simple', or 'plan'
        total: Total agent count for header

    """
    # Plan format: clean output for plan.md (no headers, just @agent - goal)
    if output_format == "plan":
        all_agents = []
        for agents in agents_by_category.values():
            all_agents.extend(agents)
        for agent in sorted(all_agents, key=lambda a: a.id):
            # Full description, no truncation
            print(f"@{agent.id} - {agent.goal}")
        return

    console.print(f"\n[bold]Discovered {total} agent(s)[/]\n")

    # Category display order and colors
    category_styles = {
        AgentCategory.ENG: ("Engineering", "blue"),
        AgentCategory.QA: ("Quality Assurance", "green"),
        AgentCategory.PRODUCT: ("Product", "magenta"),
        AgentCategory.GENERAL: ("General", "white"),
    }

    for category, agents in agents_by_category.items():
        if not agents:
            continue

        cat_name, cat_color = category_styles.get(
            category,
            (category.value.title(), "white"),
        )

        if output_format == "rich":
            console.print(f"[bold {cat_color}]{cat_name}[/] ({len(agents)})")
            for agent in sorted(agents, key=lambda a: a.id):
                # Full description, no truncation
                console.print(f"  [cyan]@{agent.id}[/] - {agent.goal}")
            console.print()
        else:
            # Simple format - full description
            print(f"\n{cat_name} ({len(agents)})")
            for agent in sorted(agents, key=lambda a: a.id):
                print(f"  @{agent.id} - {agent.goal}")


def _display_agent_details(agent: AgentInfo) -> None:
    """Display full agent details in a rich panel.

    Args:
        agent: AgentInfo to display

    """
    # Build content sections
    sections = []

    # Header with role
    sections.append(f"[bold white]{agent.role}[/]")
    sections.append(f"[dim]Category: {agent.category.value}[/]")
    sections.append("")

    # Goal
    sections.append("[bold cyan]Goal[/]")
    sections.append(agent.goal)
    sections.append("")

    # Skills
    if agent.skills:
        sections.append("[bold cyan]Skills[/]")
        for skill in agent.skills:
            sections.append(f"  - {skill}")
        sections.append("")

    # When to use
    if agent.when_to_use:
        sections.append("[bold cyan]When to Use[/]")
        sections.append(agent.when_to_use)
        sections.append("")

    # Examples
    if agent.examples:
        sections.append("[bold cyan]Examples[/]")
        for example in agent.examples:
            sections.append(f"  - {example}")
        sections.append("")

    # Dependencies
    if agent.dependencies:
        sections.append("[bold cyan]Dependencies[/]")
        for dep in agent.dependencies:
            sections.append(f"  - {dep}")
        sections.append("")

    # Source file
    if agent.source_file:
        sections.append(f"[dim]Source: {agent.source_file}[/]")

    console.print()
    console.print(
        Panel.fit(
            "\n".join(sections),
            title=f"[bold green]{agent.id}[/]",
            border_style="green",
        ),
    )
    console.print()


def _search_agents(
    manifest: AgentManifest,
    keyword: str,
    limit: int,
) -> list[tuple[AgentInfo, str]]:
    """Search agents by keyword with ranking.

    Args:
        manifest: Agent manifest to search
        keyword: Search keyword
        limit: Maximum results

    Returns:
        List of (agent, match_info) tuples sorted by relevance

    """
    keyword_lower = keyword.lower()
    results: list[tuple[AgentInfo, str, int]] = []  # (agent, match_info, score)

    for agent in manifest.agents:
        score = 0
        match_info = ""

        # Exact match in id (highest priority)
        if keyword_lower == agent.id.lower():
            score = 100
            match_info = "exact id match"
        elif keyword_lower in agent.id.lower():
            score = 80
            match_info = "partial id match"
        # Match in role
        elif keyword_lower in agent.role.lower():
            score = 70
            match_info = "in role"
        # Match in goal
        elif keyword_lower in agent.goal.lower():
            score = 60
            match_info = "in goal"
        # Match in skills
        elif any(keyword_lower in skill.lower() for skill in agent.skills):
            matched_skills = [s for s in agent.skills if keyword_lower in s.lower()]
            score = 50
            match_info = f"skill: {matched_skills[0]}"
        # Match in when_to_use
        elif agent.when_to_use and keyword_lower in agent.when_to_use.lower():
            score = 40
            match_info = "in when_to_use"
        # Match in examples
        elif any(keyword_lower in ex.lower() for ex in agent.examples):
            score = 30
            match_info = "in examples"

        if score > 0:
            results.append((agent, match_info, score))

    # Sort by score descending
    results.sort(key=lambda x: (-x[2], x[0].id))

    return [(agent, match_info) for agent, match_info, _ in results[:limit]]


def _find_similar_agents(
    manifest: AgentManifest,
    agent_id: str,
) -> list[AgentInfo]:
    """Find agents with similar IDs for suggestions.

    Args:
        manifest: Agent manifest to search
        agent_id: ID that wasn't found

    Returns:
        List of similar agents (up to 5)

    """
    agent_id_lower = agent_id.lower()
    similarities: list[tuple[AgentInfo, float]] = []

    for agent in manifest.agents:
        ratio = SequenceMatcher(None, agent_id_lower, agent.id.lower()).ratio()
        if ratio > 0.4:  # Threshold for similarity
            similarities.append((agent, ratio))

    # Sort by similarity descending
    similarities.sort(key=lambda x: -x[1])

    return [agent for agent, _ in similarities[:5]]


def _truncate(text: str, max_length: int) -> str:
    """Truncate text with ellipsis.

    Args:
        text: Text to truncate
        max_length: Maximum length

    Returns:
        Truncated text

    """
    if len(text) <= max_length:
        return text
    return text[: max_length - 3] + "..."
