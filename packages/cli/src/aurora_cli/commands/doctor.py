"""Doctor command implementation for AURORA CLI.

This module implements the 'aur doctor' command for health checks and diagnostics.
"""

from __future__ import annotations

import logging

import click
from rich.console import Console

from aurora_cli.config import Config
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
@click.option("--fix-ml", is_flag=True, help="Download embedding model and verify ML setup")
def doctor_command(fix: bool, fix_ml: bool) -> None:
    r"""Run health checks and diagnostics.

    Checks the health of your AURORA installation across six categories:
    - Core System: CLI version, database, API keys, permissions
    - Code Analysis: tree-sitter parser, index age, chunk quality
    - Search & Retrieval: vector store, Git BLA, cache size, embeddings
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

        \b
        # Download embedding model and verify ML setup
        aur doctor --fix-ml
    """
    # Handle --fix-ml flag first (standalone operation)
    if fix_ml:
        _handle_fix_ml()
        return

    try:
        # Load configuration (using Config class for backward compat)
        config = Config()

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

        # MCP Functional checks - DEPRECATED
        # MCP tools have been deprecated in favor of slash commands
        # Use: /aur:search, /aur:get, aur soar "question"

        # Calculate summary
        pass_count = sum(1 for r in all_results if r[0] == "pass")
        warning_count = sum(1 for r in all_results if r[0] == "warning")
        fail_count = sum(1 for r in all_results if r[0] == "fail")

        # Display summary
        _display_summary(pass_count, warning_count, fail_count)

        # Handle --fix flag if requested
        if fix and (fail_count > 0 or warning_count > 0):
            _handle_auto_fix(
                core_checks,
                code_checks,
                search_checks,
                config_checks,
                tool_checks,
                mcp_checks,
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


def _collect_issues(
    checks_list: list[object],
) -> tuple[list[dict], list[dict]]:
    """Collect fixable and manual issues from health check instances.

    Args:
        checks_list: List of health check instances to collect issues from

    Returns:
        Tuple of (fixable_issues, manual_issues) lists

    """
    fixable_issues: list[dict] = []
    manual_issues: list[dict] = []

    for checks in checks_list:
        if hasattr(checks, "get_fixable_issues"):
            fixable_issues.extend(checks.get_fixable_issues())
        if hasattr(checks, "get_manual_issues"):
            manual_issues.extend(checks.get_manual_issues())

    return fixable_issues, manual_issues


def _display_fixable_issues(issues: list[dict]) -> None:
    """Display fixable issues list.

    Args:
        issues: List of fixable issue dictionaries with 'name' key

    """
    if not issues:
        return

    console.print(f"[bold]Fixable issues ({len(issues)}):[/]")
    for issue in issues:
        console.print(f"  - {issue['name']}")
    console.print()


def _display_manual_issues(issues: list[dict]) -> None:
    """Display manual issues list with solutions.

    Args:
        issues: List of manual issue dictionaries with 'name' and 'solution' keys

    """
    if not issues:
        return

    console.print(f"[bold]Manual fixes needed ({len(issues)}):[/]")
    for issue in issues:
        console.print(f"  - {issue['name']}")
        console.print(f"    Solution: {issue['solution']}")
    console.print()


def _apply_fixes(issues: list[dict]) -> int:
    """Apply fixes for all fixable issues.

    Args:
        issues: List of issue dictionaries with 'name' and 'fix_func' keys

    Returns:
        Count of successfully fixed issues

    """
    fixed_count = 0
    for issue in issues:
        try:
            console.print(f"  Fixing [yellow]{issue['name']}[/]...", end=" ")
            issue["fix_func"]()
            console.print("[green]OK[/]")
            fixed_count += 1
        except Exception as e:
            console.print(f"[red]FAILED[/] ({e})")
            logger.error(f"Failed to fix {issue['name']}: {e}", exc_info=True)

    return fixed_count


def _handle_auto_fix(
    core_checks: CoreSystemChecks,
    code_checks: CodeAnalysisChecks,
    search_checks: SearchRetrievalChecks,
    config_checks: ConfigurationChecks,
    tool_checks: ToolIntegrationChecks,
    mcp_checks: MCPFunctionalChecks,
) -> None:
    """Handle auto-fix functionality.

    Orchestrates the collection, display, and application of fixes for
    health check issues. Uses extracted helpers to reduce complexity.

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

    # Collect issues from all check categories
    checks_list = [core_checks, code_checks, search_checks, config_checks, tool_checks, mcp_checks]
    fixable_issues, manual_issues = _collect_issues(checks_list)

    # Display issues
    _display_fixable_issues(fixable_issues)
    _display_manual_issues(manual_issues)

    # Prompt and apply fixes if there are fixable issues
    if fixable_issues:
        plural = "s" if len(fixable_issues) != 1 else ""
        if click.confirm(f"Fix {len(fixable_issues)} issue{plural} automatically?"):
            console.print()
            console.print("[bold cyan]Applying fixes...[/]")
            fixed_count = _apply_fixes(fixable_issues)
            console.print()
            console.print(f"[bold]Fixed {fixed_count} of {len(fixable_issues)} issues[/]")
        else:
            console.print("Skipping automatic fixes.")


def _handle_fix_ml() -> None:
    """Download embedding model and verify ML setup.

    This function:
    1. Checks if sentence-transformers is installed
    2. Checks if embedding model is already cached
    3. Downloads the model if not cached
    4. Provides clear feedback and next steps

    """
    console.print("\n[bold cyan]ML Setup: Embedding Model Download[/]\n")

    # 1. Check sentence-transformers installed
    try:
        import sentence_transformers  # noqa: F401
    except ImportError:
        console.print("[bold red]Error:[/] sentence-transformers package not installed\n")
        console.print("[bold]Solution:[/]")
        console.print("  1. Install the package:")
        console.print("     [cyan]pip install sentence-transformers[/]")
        console.print("  2. Or reinstall aurora-context-code:")
        console.print("     [cyan]pip install -e packages/context-code[/]\n")
        raise click.Abort()

    console.print("[green]✓[/] sentence-transformers is installed")

    # 2. Check if model is already cached
    from aurora_context_code.semantic.model_utils import (
        DEFAULT_MODEL,
        get_model_cache_path,
        is_model_cached,
    )

    model_name = DEFAULT_MODEL
    cache_path = get_model_cache_path(model_name)

    if is_model_cached(model_name):
        console.print(f"[green]✓[/] Embedding model already cached at:")
        console.print(f"    [dim]{cache_path}[/]\n")
        console.print("[bold green]ML setup complete![/] You can now:")
        console.print("  • Index your codebase: [cyan]aur mem index .[/]")
        console.print("  • Initialize projects: [cyan]aur init[/]")
        console.print("  • Run SOAR queries: [cyan]aur soar \"your question\"[/]\n")
        return

    # 3. Download the model with progress
    console.print(f"[yellow]Embedding model not cached[/]")
    console.print(f"[dim]Model: {model_name}[/]")
    console.print(f"[dim]Cache: {cache_path}[/]\n")

    from aurora_context_code.semantic.model_utils import MLDependencyError, validate_ml_ready

    try:
        validate_ml_ready(model_name=model_name, console=console)
        console.print("\n[bold green]✓ ML setup complete![/]\n")
        console.print("[bold]Next steps:[/]")
        console.print("  • Index your codebase: [cyan]aur mem index .[/]")
        console.print("  • Initialize projects: [cyan]aur init[/]")
        console.print("  • Run SOAR queries: [cyan]aur soar \"your question\"[/]\n")
    except MLDependencyError as e:
        console.print(f"\n[bold red]✗ Model download failed[/]\n")
        console.print(str(e))
        console.print()
        raise click.Abort()


if __name__ == "__main__":
    doctor_command()
