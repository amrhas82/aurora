"""Budget management commands for AURORA CLI.

This module provides commands for managing budget limits, viewing spending,
and resetting budget tracking.
"""

from pathlib import Path

import click
from rich.console import Console
from rich.table import Table

from aurora_cli.config import Config
from aurora_cli.errors import handle_errors
from aurora_core.budget.tracker import CostTracker


console = Console()


@click.group(name="budget", invoke_without_command=True)
@click.pass_context
def budget_group(ctx: click.Context) -> None:
    """Manage API usage budget and view spending history.

    Track your LLM API costs and enforce budget limits to avoid overspending.

    \b
    Examples:
        aur budget              # Show current budget status
        aur budget set 20.00    # Set budget to $20
        aur budget reset        # Reset spending to zero
        aur budget history      # Show query history
    """
    # If no subcommand provided, show budget status (default behavior)
    if ctx.invoked_subcommand is None:
        ctx.invoke(show_command)


@budget_group.command(name="show")
@handle_errors
def show_command() -> None:
    """Show current budget status and spending (default command).

    Displays:
    - Monthly budget limit
    - Total spent this period
    - Remaining budget
    - Percentage consumed
    """
    try:
        # Load configuration
        config = Config()

        # Get tracker path from config or use default
        budget_path = Path(config.budget_tracker_path).expanduser()
        budget_limit = config.budget_limit

        # Initialize tracker
        tracker = CostTracker(monthly_limit_usd=budget_limit, tracker_path=budget_path)

        # Get status
        status = tracker.get_status()

        # Display budget summary
        console.print("\n[bold]Budget Status[/]")

        table = Table(show_header=False, box=None, padding=(0, 2))
        table.add_column("Item", style="cyan", no_wrap=True)
        table.add_column("Value", style="white")

        # Format values
        limit = status["limit_usd"]
        spent = status["consumed_usd"]
        remaining = status["remaining_usd"]
        percent = status["percent_consumed"]

        table.add_row("Period", status["period"])
        table.add_row("Budget", f"${limit:.2f}")
        table.add_row("Spent", f"${spent:.4f}")
        table.add_row("Remaining", f"${remaining:.4f}")

        # Color-code percentage based on consumption level
        if percent >= 100:
            percent_display = f"[red]{percent:.1f}%[/]"
        elif percent >= 80:
            percent_display = f"[yellow]{percent:.1f}%[/]"
        else:
            percent_display = f"[green]{percent:.1f}%[/]"

        table.add_row("Consumed", percent_display)
        table.add_row("Queries", str(status["total_entries"]))

        console.print(table)
        console.print()

        # Show warnings if needed
        if status["at_hard_limit"]:
            console.print("[bold red]⚠ Budget limit reached![/] Queries will be blocked.")
            console.print("[dim]  Use 'aur budget set <amount>' to increase budget[/]\n")
        elif status["at_soft_limit"]:
            console.print("[bold yellow]⚠ Approaching budget limit[/]")
            console.print("[dim]  Consider increasing budget or resetting spending[/]\n")

    except Exception as e:
        console.print(f"\n[bold red]Error:[/] Failed to load budget status: {e}\n", style="red")
        raise click.Abort()


@budget_group.command(name="set")
@click.argument("amount", type=float)
@handle_errors
def set_command(amount: float) -> None:
    """Set monthly budget limit.

    Args:
        amount: Budget limit in USD (e.g., 10.00)

    \b
    Examples:
        aur budget set 20.00    # Set budget to $20
        aur budget set 5.50     # Set budget to $5.50

    """
    if amount <= 0:
        console.print("\n[bold red]Error:[/] Budget amount must be positive\n", style="red")
        raise click.Abort()

    try:
        # Load configuration
        from aurora_cli.config import load_config, save_config

        config_dict = load_config()
        config = Config(config_dict)

        # Get tracker path
        budget_path = Path(config.budget_tracker_path).expanduser()

        # Initialize tracker with old limit
        tracker = CostTracker(monthly_limit_usd=config.budget_limit, tracker_path=budget_path)

        # Set new budget
        tracker.set_budget(amount)

        # Update config dict
        config_dict.setdefault("budget", {})["limit"] = amount

        # Save config back to file
        save_config(config_dict)

        console.print(f"\n[bold green]✓[/] Budget limit set to [bold]${amount:.2f}[/] per month\n")

    except Exception as e:
        console.print(f"\n[bold red]Error:[/] Failed to set budget: {e}\n", style="red")
        raise click.Abort()


@budget_group.command(name="reset")
@click.option("--confirm", is_flag=True, help="Skip confirmation prompt")
@handle_errors
def reset_command(confirm: bool) -> None:
    """Reset spending to zero (clears all entries for current period).

    This keeps your budget limit but clears the spending history
    for the current month.

    \b
    Examples:
        aur budget reset          # Reset with confirmation
        aur budget reset --confirm  # Reset without confirmation
    """
    if not confirm:
        response = click.confirm(
            "\nThis will reset spending to $0.00 for the current period. Continue?",
            default=False,
        )
        if not response:
            console.print("\n[dim]Reset cancelled[/]\n")
            return

    try:
        # Load configuration
        config = Config()

        # Get tracker path
        budget_path = Path(config.budget_tracker_path).expanduser()
        budget_limit = config.budget_limit

        # Initialize tracker
        tracker = CostTracker(monthly_limit_usd=budget_limit, tracker_path=budget_path)

        # Get current spending before reset
        old_spent = tracker.get_total_spent()

        # Reset spending
        tracker.reset_spending()

        console.print(
            f"\n[bold green]✓[/] Spending reset from [bold]${old_spent:.4f}[/] to [bold]$0.00[/]\n",
        )
        console.print(f"[dim]Budget limit remains: ${budget_limit:.2f}[/]\n")

    except Exception as e:
        console.print(f"\n[bold red]Error:[/] Failed to reset spending: {e}\n", style="red")
        raise click.Abort()


@budget_group.command(name="history")
@click.option("--limit", "-n", type=int, default=20, help="Number of entries to show (default: 20)")
@click.option("--all", "show_all", is_flag=True, help="Show all entries")
@handle_errors
def history_command(limit: int, show_all: bool) -> None:
    """Show query history with costs and timestamps.

    \b
    Options:
        --limit, -n: Number of recent entries to show (default: 20)
        --all: Show all entries

    \b
    Examples:
        aur budget history           # Show last 20 queries
        aur budget history --limit 50  # Show last 50 queries
        aur budget history --all     # Show all queries
    """
    try:
        # Load configuration
        config = Config()

        # Get tracker path
        budget_path = Path(config.budget_tracker_path).expanduser()
        budget_limit = config.budget_limit

        # Initialize tracker
        tracker = CostTracker(monthly_limit_usd=budget_limit, tracker_path=budget_path)

        # Get history
        history = tracker.get_history()

        if not history:
            console.print("\n[dim]No query history found[/]\n")
            return

        # Determine how many entries to show
        if show_all:
            entries_to_show = history
        else:
            entries_to_show = history[-limit:] if len(history) > limit else history

        # Display history table
        console.print(
            f"\n[bold]Query History[/] (showing {len(entries_to_show)} of {len(history)} entries)",
        )

        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("Timestamp", style="cyan", no_wrap=True)
        table.add_column("Query", style="white", max_width=50)
        table.add_column("Cost", justify="right", style="green")
        table.add_column("Status", justify="center", style="white")

        # Add rows (most recent last)
        for entry in entries_to_show:
            # Format timestamp
            timestamp = entry["timestamp"][:19]  # Remove milliseconds

            # Truncate long queries
            query = entry["query"]
            if len(query) > 50:
                query = query[:47] + "..."

            # Format cost
            cost = entry["cost"]
            cost_str = f"${cost:.4f}" if cost > 0 else "$0.00"

            # Format status with color
            status = entry["status"]
            if status == "success":
                status_display = "[green]✓[/]"
            elif status == "blocked":
                status_display = "[red]✗[/]"
            else:
                status_display = status

            table.add_row(timestamp, query, cost_str, status_display)

        console.print(table)

        # Show summary
        total_cost = sum(entry["cost"] for entry in history)
        console.print(f"\n[bold]Total:[/] ${total_cost:.4f}\n")

    except Exception as e:
        console.print(f"\n[bold red]Error:[/] Failed to load history: {e}\n", style="red")
        raise click.Abort()


# Export the group for registration in main CLI
__all__ = ["budget_group"]
