"""Doctor command implementation for AURORA CLI.

This module implements the 'aur doctor' command for health checks and diagnostics.
"""

from __future__ import annotations

import logging

import click
from rich.console import Console
from rich.table import Table
from rich.text import Text

from aurora_cli.config import load_config
from aurora_cli.health_checks import (
    CodeAnalysisChecks,
    ConfigurationChecks,
    CoreSystemChecks,
    MCPFunctionalChecks,
    SearchRetrievalChecks,
    ToolIntegrationChecks,
)

__all__ = ["doctor_command"]

logger = logging.getLogger(__name__)
console = Console()


@click.command(name="doctor")
@click.option("--fix", is_flag=True, help="Automatically fix issues where possible")
def doctor_command(fix: bool) -> None:
    """Run health checks and diagnostics.

    Checks the health of your AURORA installation across six categories:
    - Core System: CLI version, database, API keys, permissions
    - Code Analysis: tree-sitter parser, index age, chunk quality
    - Search & Retrieval: vector store, Git BLA, cache size
    - Configuration: config file, Git repo, MCP server
    - Tool Integration: slash commands, MCP servers
    - MCP Functional: MCP config validation, SOAR phases, memory database

    \b
    Exit Codes:
        0 - All checks passed
        1 - Some warnings (non-critical issues)
        2 - Some failures (critical issues)

    \b
    Examples:
        # Run health checks
        aur doctor

        \b
        # Run health checks with auto-repair
        aur doctor --fix
    """
    try:
        # Load configuration
        config = load_config()

        # Create health check instances
        core_checks = CoreSystemChecks(config)
        code_checks = CodeAnalysisChecks(config)
        search_checks = SearchRetrievalChecks(config)
        config_checks = ConfigurationChecks(config)
        tool_checks = ToolIntegrationChecks(config)
        mcp_checks = MCPFunctionalChecks(config)

        # Run all checks
        console.print("\n[bold cyan]Running AURORA health checks...[/]\n")

        all_results = []

        # Core System checks
        console.print("[bold]CORE SYSTEM[/]")
        core_results = core_checks.run_checks()
        all_results.extend(core_results)
        _display_results(core_results)
        console.print()

        # Code Analysis checks
        console.print("[bold]CODE ANALYSIS[/]")
        code_results = code_checks.run_checks()
        all_results.extend(code_results)
        _display_results(code_results)
        console.print()

        # Search & Retrieval checks
        console.print("[bold]SEARCH & RETRIEVAL[/]")
        search_results = search_checks.run_checks()
        all_results.extend(search_results)
        _display_results(search_results)
        console.print()

        # Configuration checks
        console.print("[bold]CONFIGURATION[/]")
        config_results = config_checks.run_checks()
        all_results.extend(config_results)
        _display_results(config_results)
        console.print()

        # Tool Integration checks
        console.print("[bold]TOOL INTEGRATION[/]")
        tool_results = tool_checks.run_checks()
        all_results.extend(tool_results)
        _display_results(tool_results)
        console.print()

        # MCP Functional checks - DEPRECATED (commented out)
        # MCP tools have been deprecated in favor of slash commands
        # Use: /aur:search, /aur:get, aur soar "question"
        # Uncomment below to re-enable MCP checks if needed
        # console.print("[bold]MCP FUNCTIONAL[/]")
        # mcp_results = mcp_checks.run_checks()
        # all_results.extend(mcp_results)
        # _display_results(mcp_results)
        # console.print()

        # Calculate summary
        pass_count = sum(1 for r in all_results if r[0] == "pass")
        warning_count = sum(1 for r in all_results if r[0] == "warning")
        fail_count = sum(1 for r in all_results if r[0] == "fail")

        # Display summary
        _display_summary(pass_count, warning_count, fail_count)

        # Handle --fix flag if requested
        if fix and (fail_count > 0 or warning_count > 0):
            _handle_auto_fix(
                core_checks, code_checks, search_checks, config_checks, tool_checks, mcp_checks
            )

        # Determine exit code
        if fail_count > 0:
            raise click.exceptions.Exit(2)
        elif warning_count > 0:
            raise click.exceptions.Exit(1)
        else:
            raise click.exceptions.Exit(0)

    except click.exceptions.Exit:
        # Re-raise Exit exceptions (don't catch them)
        raise
    except Exception as e:
        logger.error(f"Doctor command failed: {e}", exc_info=True)
        console.print(f"\n[bold red]Error running health checks:[/] {e}", style="red")
        console.print("\nRun 'aur doctor' again or report this issue on GitHub.")
        raise click.Abort()


def _display_results(results: list[tuple[str, str, dict]]) -> None:
    """Display health check results.

    Args:
        results: List of (status, message, details) tuples
    """
    for status, message, details in results:
        # Choose icon and color based on status
        if status == "pass":
            icon = "✓"
            color = "green"
        elif status == "warning":
            icon = "⚠"
            color = "yellow"
        else:  # fail
            icon = "✗"
            color = "red"

        # Display result
        console.print(f"  [{color}]{icon}[/] {message}")


def _display_summary(pass_count: int, warning_count: int, fail_count: int) -> None:
    """Display summary line.

    Args:
        pass_count: Number of passed checks
        warning_count: Number of warnings
        fail_count: Number of failures
    """
    console.print("[bold]Summary:[/]")

    # Build summary text with colors
    parts = []
    if pass_count > 0:
        parts.append(f"[green]{pass_count} passed[/]")
    if warning_count > 0:
        parts.append(f"[yellow]{warning_count} warning{'s' if warning_count != 1 else ''}[/]")
    if fail_count > 0:
        parts.append(f"[red]{fail_count} failed[/]")

    summary = ", ".join(parts)
    console.print(f"  {summary}")


def _handle_auto_fix(
    core_checks: CoreSystemChecks,
    code_checks: CodeAnalysisChecks,
    search_checks: SearchRetrievalChecks,
    config_checks: ConfigurationChecks,
    tool_checks: ToolIntegrationChecks,
    mcp_checks: MCPFunctionalChecks,
) -> None:
    """Handle auto-fix functionality.

    Args:
        core_checks: Core system health checks instance
        code_checks: Code analysis health checks instance
        search_checks: Search & retrieval health checks instance
        config_checks: Configuration health checks instance
        tool_checks: Tool integration health checks instance
        mcp_checks: MCP functional health checks instance
    """
    console.print()
    console.print("[bold cyan]Analyzing fixable issues...[/]")
    console.print()

    # Collect fixable and manual issues from all check categories
    fixable_issues = []
    manual_issues = []

    for checks in [core_checks, code_checks, search_checks, config_checks, tool_checks, mcp_checks]:
        if hasattr(checks, "get_fixable_issues"):
            fixable_issues.extend(checks.get_fixable_issues())
        if hasattr(checks, "get_manual_issues"):
            manual_issues.extend(checks.get_manual_issues())

    # Display fixable issues
    if fixable_issues:
        console.print(f"[bold]Fixable issues ({len(fixable_issues)}):[/]")
        for issue in fixable_issues:
            console.print(f"  • {issue['name']}")
        console.print()

    # Display manual issues
    if manual_issues:
        console.print(f"[bold]Manual fixes needed ({len(manual_issues)}):[/]")
        for issue in manual_issues:
            console.print(f"  • {issue['name']}")
            console.print(f"    Solution: {issue['solution']}")
        console.print()

    # Prompt user for confirmation if there are fixable issues
    if fixable_issues:
        if click.confirm(
            f"Fix {len(fixable_issues)} issue{'s' if len(fixable_issues) != 1 else ''} automatically?"
        ):
            console.print()
            console.print("[bold cyan]Applying fixes...[/]")

            fixed_count = 0
            for issue in fixable_issues:
                try:
                    console.print(f"  Fixing [yellow]{issue['name']}[/]...", end=" ")
                    issue["fix_func"]()
                    console.print("[green]✓[/]")
                    fixed_count += 1
                except Exception as e:
                    console.print(f"[red]✗[/] ({e})")
                    logger.error(f"Failed to fix {issue['name']}: {e}", exc_info=True)

            console.print()
            console.print(f"[bold]Fixed {fixed_count} of {len(fixable_issues)} issues[/]")
        else:
            console.print("Skipping automatic fixes.")


if __name__ == "__main__":
    doctor_command()
