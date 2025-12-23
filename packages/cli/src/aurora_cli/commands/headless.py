"""Headless mode command for autonomous experiment execution.

This module implements the `aur headless` command that runs autonomous
experiments without human intervention between iterations.

The command:
1. Validates git branch safety (requires "headless" branch by default)
2. Loads and validates experiment prompt
3. Initializes scratchpad for iteration tracking
4. Executes autonomous experiment loop
5. Tracks budget and enforces limits
6. Reports results and termination reason

Safety Features:
    - Git branch enforcement prevents running on main/master
    - Budget limits stop execution when costs exceed threshold
    - Max iterations prevent infinite loops
    - Scratchpad provides full audit trail

Usage:
    aur headless experiment.md                     # Basic usage
    aur headless experiment.md --budget 10.0       # Custom budget
    aur headless experiment.md --max-iter 20       # More iterations
    aur headless experiment.md --branch test-1     # Custom branch
    aur headless experiment.md --scratchpad log.md # Custom scratchpad
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table


__all__ = ["headless_command"]

console = Console()
logger = logging.getLogger(__name__)


@click.command(name="headless")
@click.argument(
    "prompt_path",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    required=True,
)
@click.option(
    "--scratchpad",
    "-s",
    type=click.Path(path_type=Path),
    default=None,
    help="Path to scratchpad file (default: <prompt_name>_scratchpad.md)",
)
@click.option(
    "--budget",
    "-b",
    type=float,
    default=5.0,
    help="Maximum budget in USD (default: 5.0)",
)
@click.option(
    "--max-iter",
    "-m",
    type=int,
    default=10,
    help="Maximum number of iterations (default: 10)",
)
@click.option(
    "--branch",
    type=str,
    default="headless",
    help="Required git branch for execution (default: headless)",
)
@click.option(
    "--allow-main",
    is_flag=True,
    default=False,
    help="DANGEROUS: Allow running on main/master branch",
)
@click.option(
    "--dry-run",
    is_flag=True,
    default=False,
    help="Validate configuration without executing",
)
@click.option(
    "--show-scratchpad",
    is_flag=True,
    default=False,
    help="Display scratchpad content after execution",
)
def headless_command(
    prompt_path: Path,
    scratchpad: Path | None,
    budget: float,
    max_iter: int,
    branch: str,
    allow_main: bool,
    dry_run: bool,
    show_scratchpad: bool,
) -> None:
    """Run autonomous experiment in headless mode.

    Executes an experiment defined in PROMPT_PATH without human intervention.
    The system iteratively works toward the goal defined in the prompt,
    tracking progress in a scratchpad file.

    \b
    PROMPT_PATH format:
        ## Goal
        What you want to achieve

        \b
        ## Success Criteria
        - Criterion 1
        - Criterion 2

        \b
        ## Constraints
        - Constraint 1
        - Constraint 2

        \b
        ## Context (optional)
        Additional context...

    \b
    Examples:
        # Basic usage
        aur headless experiment.md

        \b
        # Custom budget and iterations
        aur headless experiment.md --budget 10.0 --max-iter 20

        \b
        # Custom branch and scratchpad
        aur headless experiment.md --branch test-1 --scratchpad log.md

        \b
        # Dry run (validate without executing)
        aur headless experiment.md --dry-run

        \b
        # Show scratchpad after completion
        aur headless experiment.md --show-scratchpad

    \b
    Safety:
        By default, headless mode requires a "headless" branch (not main/master).
        Use --allow-main to override (not recommended for production).
    """
    try:
        # Import here to avoid slow startup for other commands
        from aurora_soar.headless import HeadlessConfig, HeadlessOrchestrator

        # Determine scratchpad path
        if scratchpad is None:
            scratchpad = prompt_path.parent / f"{prompt_path.stem}_scratchpad.md"

        # Display configuration
        console.print("\n[bold]Headless Mode Configuration:[/]")
        config_table = Table(show_header=False, box=None, padding=(0, 2))
        config_table.add_column("Key", style="cyan")
        config_table.add_column("Value", style="white")

        config_table.add_row("Prompt", str(prompt_path))
        config_table.add_row("Scratchpad", str(scratchpad))
        config_table.add_row("Budget", f"${budget:.2f}")
        config_table.add_row("Max Iterations", str(max_iter))
        config_table.add_row("Required Branch", branch)
        config_table.add_row("Allow Main", "⚠️  Yes (DANGEROUS)" if allow_main else "No")

        console.print(config_table)
        console.print()

        # Validate inputs
        if budget <= 0:
            console.print("[bold red]Error:[/] Budget must be positive", style="red")
            raise click.Abort()

        if max_iter <= 0:
            console.print("[bold red]Error:[/] Max iterations must be positive", style="red")
            raise click.Abort()

        # Create configuration
        config = HeadlessConfig(
            max_iterations=max_iter,
            budget_limit=budget,
            required_branch=branch,
            blocked_branches=[] if allow_main else ["main", "master"],
            auto_create_scratchpad=True,
            scratchpad_backup=True,
        )

        # Dry run mode - validate only
        if dry_run:
            console.print("[bold yellow]→[/] Dry run mode: validating configuration only")

            # Import SOAR orchestrator (or use mock for dry run)
            try:
                from aurora_soar.orchestrator import SOAROrchestrator

                # Create mock orchestrator for validation
                class MockSOAROrchestrator:
                    """Mock SOAR orchestrator for dry-run validation."""

                    def execute(self, query: str, **kwargs: Any) -> dict[str, Any]:
                        """Mock execute method."""
                        return {"response": "mock response", "cost": 0.0}

                soar = MockSOAROrchestrator()
            except ImportError:
                console.print(
                    "[yellow]Warning:[/] Could not import SOAROrchestrator, using mock"
                )

                # Use the same class definition (avoid redefinition)
                soar = MockSOAROrchestrator()

            # Create orchestrator (this validates git branch and prompt)
            orchestrator = HeadlessOrchestrator(
                prompt_path=prompt_path,
                scratchpad_path=scratchpad,
                soar_orchestrator=soar,
                config=config,
            )

            console.print("[bold green]✓[/] Configuration valid")
            console.print(f"[dim]Prompt: {prompt_path.name}[/]")
            console.print(f"[dim]Would create/use scratchpad: {scratchpad}[/]")
            console.print("\n[dim]Run without --dry-run to execute[/]")
            return

        # Real execution mode
        console.print("[bold blue]→[/] Starting headless execution...")
        console.print("[dim]Press Ctrl+C to abort (graceful termination)[/]\n")

        # Import SOAR orchestrator
        try:
            from aurora_soar.orchestrator import SOAROrchestrator

            # Create SOAR orchestrator
            # TODO: Load configuration from ~/.aurora/config.yaml or similar
            console.print("[yellow]Warning:[/] SOAR orchestrator creation not implemented")
            console.print("[dim]This would initialize SOAROrchestrator with proper config[/]")
            console.print("[dim]For now, aborting. Implement SOAR initialization first.[/]\n")
            raise click.Abort()

        except ImportError as e:
            console.print(
                f"[bold red]Error:[/] Could not import SOAROrchestrator: {e}",
                style="red",
            )
            console.print(
                "[dim]Ensure aurora-soar package is installed and accessible[/]"
            )
            raise click.Abort()

        # Create orchestrator
        orchestrator = HeadlessOrchestrator(
            prompt_path=prompt_path,
            scratchpad_path=scratchpad,
            soar_orchestrator=soar,
            config=config,
        )

        # Execute
        result = orchestrator.execute()

        # Display results
        console.print("\n" + "=" * 60)
        console.print("[bold]Headless Execution Complete[/]")
        console.print("=" * 60 + "\n")

        # Create results table
        results_table = Table(show_header=False, box=None, padding=(0, 2))
        results_table.add_column("Metric", style="cyan")
        results_table.add_column("Value", style="white")

        results_table.add_row("Goal Achieved", "✓ Yes" if result.goal_achieved else "✗ No")
        results_table.add_row("Termination Reason", result.termination_reason.value)
        results_table.add_row("Iterations", str(result.iterations))
        results_table.add_row("Total Cost", f"${result.total_cost:.2f}")
        results_table.add_row(
            "Duration", f"{result.duration_seconds:.1f}s"
        )
        results_table.add_row("Scratchpad", result.scratchpad_path)

        if result.error_message:
            results_table.add_row("Error", result.error_message)

        console.print(results_table)
        console.print()

        # Show scratchpad if requested
        if show_scratchpad and Path(result.scratchpad_path).exists():
            console.print("\n[bold]Scratchpad Content:[/]")
            with open(result.scratchpad_path) as f:
                scratchpad_content = f.read()
            console.print(
                Panel(
                    scratchpad_content,
                    title=f"📝 {Path(result.scratchpad_path).name}",
                    border_style="cyan",
                )
            )

        # Exit status based on goal achievement
        if not result.goal_achieved:
            console.print(
                "\n[yellow]Goal not achieved. See scratchpad for details.[/]"
            )
            # Don't exit with error code - this is expected behavior
        else:
            console.print(
                "\n[bold green]✓ Goal achieved successfully![/]"
            )

    except KeyboardInterrupt:
        console.print("\n\n[yellow]Interrupted by user. Exiting gracefully...[/]")
        raise click.Abort()

    except Exception as e:
        logger.error(f"Headless command failed: {e}", exc_info=True)
        console.print(f"\n[bold red]Error:[/] {e}", style="red")
        raise click.Abort()
