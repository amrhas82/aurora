"""Health monitoring command for Aurora CLI.

Displays agent health metrics, failure detection latency, and circuit breaker status.
"""

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from aurora_spawner.circuit_breaker import get_circuit_breaker
from aurora_spawner.observability import get_health_monitor


@click.group(name="health")
def health_cmd():
    """View agent health metrics and failure detection statistics."""


@health_cmd.command(name="status")
@click.option("--agent", help="Filter by agent ID")
@click.option("--json", "output_json", is_flag=True, help="Output as JSON")
def health_status(agent: str | None, output_json: bool):
    """Display health status for all agents or a specific agent.

    Shows execution counts, failure rates, detection latency, and recovery rates.
    """
    console = Console()
    health_monitor = get_health_monitor()

    if output_json:
        import json

        if agent:
            metrics = health_monitor.get_agent_health(agent)
            data = {
                "agent_id": metrics.agent_id,
                "total_executions": metrics.total_executions,
                "successful_executions": metrics.successful_executions,
                "failed_executions": metrics.failed_executions,
                "failure_rate": metrics.failure_rate,
                "avg_execution_time": metrics.avg_execution_time,
                "avg_detection_latency": metrics.avg_detection_latency,
                "recovery_rate": metrics.recovery_rate,
                "circuit_open_count": metrics.circuit_open_count,
            }
        else:
            data = health_monitor.get_summary()

        click.echo(json.dumps(data, indent=2))
        return

    # Rich table output
    if agent:
        metrics = health_monitor.get_agent_health(agent)
        _display_agent_metrics(console, metrics)
    else:
        all_metrics = health_monitor.get_all_agent_health()
        if not all_metrics:
            console.print("[yellow]No agent health data available[/yellow]")
            return

        _display_summary_table(console, all_metrics)

        # Display aggregate stats
        summary = health_monitor.get_summary()
        _display_aggregate_stats(console, summary)


@health_cmd.command(name="latency")
@click.option("--json", "output_json", is_flag=True, help="Output as JSON")
def failure_latency(output_json: bool):
    """Display failure detection latency statistics.

    Shows percentile distribution of time-to-detection for failures.
    """
    console = Console()
    health_monitor = get_health_monitor()
    stats = health_monitor.get_detection_latency_stats()

    if output_json:
        import json

        click.echo(json.dumps(stats, indent=2))
        return

    # Rich panel output
    table = Table(title="Failure Detection Latency", show_header=True, header_style="bold cyan")
    table.add_column("Metric", style="cyan")
    table.add_column("Value (seconds)", justify="right", style="green")

    table.add_row("Minimum", f"{stats['min']:.2f}")
    table.add_row("Average", f"{stats['avg']:.2f}")
    table.add_row("P50 (Median)", f"{stats['p50']:.2f}")
    table.add_row("P95", f"{stats['p95']:.2f}")
    table.add_row("P99", f"{stats['p99']:.2f}")
    table.add_row("Maximum", f"{stats['max']:.2f}")

    console.print(table)

    # Alert if P95 is high
    if stats["p95"] > 30.0:
        console.print("\n[yellow]⚠ P95 latency exceeds 30s threshold[/yellow]")


@health_cmd.command(name="failures")
@click.option("--agent", help="Filter by agent ID")
@click.option("--limit", default=10, help="Number of recent failures to show")
@click.option("--json", "output_json", is_flag=True, help="Output as JSON")
def recent_failures(agent: str | None, limit: int, output_json: bool):
    """Display recent failure events with detection latency."""
    console = Console()
    health_monitor = get_health_monitor()
    failures = health_monitor.get_failure_events(agent_id=agent, limit=limit)

    if output_json:
        import datetime
        import json

        data = [
            {
                "agent_id": f.agent_id,
                "task_id": f.task_id,
                "timestamp": datetime.datetime.fromtimestamp(f.timestamp).isoformat(),
                "reason": f.reason.value,
                "detection_latency": f.detection_latency,
                "error_message": f.error_message,
                "retry_attempt": f.retry_attempt,
                "recovered": f.recovered,
                "recovery_time": f.recovery_time,
            }
            for f in failures
        ]
        click.echo(json.dumps(data, indent=2))
        return

    if not failures:
        console.print("[green]No recent failures[/green]")
        return

    # Rich table output
    table = Table(
        title=f"Recent Failures (Last {limit})",
        show_header=True,
        header_style="bold red",
    )
    table.add_column("Timestamp", style="dim")
    table.add_column("Agent", style="cyan")
    table.add_column("Reason", style="yellow")
    table.add_column("Latency (s)", justify="right", style="red")
    table.add_column("Status", style="green")

    import datetime

    for failure in failures:
        ts = datetime.datetime.fromtimestamp(failure.timestamp).strftime("%Y-%m-%d %H:%M:%S")
        status = "✓ Recovered" if failure.recovered else "✗ Failed"
        status_style = "green" if failure.recovered else "red"

        table.add_row(
            ts,
            failure.agent_id,
            failure.reason.value,
            f"{failure.detection_latency:.2f}",
            Text(status, style=status_style),
        )

    console.print(table)


@health_cmd.command(name="circuits")
@click.option("--json", "output_json", is_flag=True, help="Output as JSON")
def circuit_status(output_json: bool):
    """Display circuit breaker status for all agents."""
    console = Console()
    circuit_breaker = get_circuit_breaker()
    status = circuit_breaker.get_status()

    if output_json:
        import json

        click.echo(json.dumps(status, indent=2))
        return

    if not status:
        console.print("[green]All circuits closed (healthy)[/green]")
        return

    # Rich table output
    table = Table(title="Circuit Breaker Status", show_header=True, header_style="bold magenta")
    table.add_column("Agent", style="cyan")
    table.add_column("State", style="yellow")
    table.add_column("Failures", justify="right", style="red")
    table.add_column("Last Failure", style="dim")

    import datetime

    for agent_id, circuit_info in status.items():
        state = circuit_info["state"]
        state_style = {
            "closed": "green",
            "open": "red",
            "half_open": "yellow",
        }.get(state, "white")

        last_failure = circuit_info.get("last_failure", 0)
        if last_failure:
            last_failure_str = datetime.datetime.fromtimestamp(last_failure).strftime(
                "%Y-%m-%d %H:%M:%S",
            )
        else:
            last_failure_str = "N/A"

        table.add_row(
            agent_id,
            Text(state.upper(), style=state_style),
            str(circuit_info["failure_count"]),
            last_failure_str,
        )

    console.print(table)


def _display_agent_metrics(console: Console, metrics):
    """Display detailed metrics for a single agent."""
    success_rate = (1.0 - metrics.failure_rate) * 100 if metrics.total_executions > 0 else 0.0

    table = Table(title=f"Agent Health: {metrics.agent_id}", show_header=False)
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="white")

    table.add_row("Total Executions", str(metrics.total_executions))
    table.add_row("Successful", f"{metrics.successful_executions} ({success_rate:.1f}%)")
    table.add_row("Failed", str(metrics.failed_executions))
    table.add_row("Avg Execution Time", f"{metrics.avg_execution_time:.2f}s")
    table.add_row("Avg Detection Latency", f"{metrics.avg_detection_latency:.2f}s")
    table.add_row("Recovery Rate", f"{metrics.recovery_rate * 100:.1f}%")
    table.add_row("Circuit Opens", str(metrics.circuit_open_count))

    console.print(table)


def _display_summary_table(console: Console, all_metrics: dict):
    """Display summary table for all agents."""
    table = Table(title="Agent Health Summary", show_header=True, header_style="bold cyan")
    table.add_column("Agent", style="cyan")
    table.add_column("Executions", justify="right", style="white")
    table.add_column("Success Rate", justify="right", style="green")
    table.add_column("Avg Latency (s)", justify="right", style="yellow")
    table.add_column("Recovery", justify="right", style="blue")
    table.add_column("Circuits", justify="right", style="red")

    for agent_id, metrics in sorted(all_metrics.items()):
        if metrics.total_executions == 0:
            continue

        success_rate = (1.0 - metrics.failure_rate) * 100
        success_style = "green" if success_rate >= 90 else "yellow" if success_rate >= 70 else "red"

        table.add_row(
            agent_id,
            str(metrics.total_executions),
            Text(f"{success_rate:.1f}%", style=success_style),
            f"{metrics.avg_detection_latency:.2f}",
            f"{metrics.recovery_rate * 100:.1f}%",
            str(metrics.circuit_open_count),
        )

    console.print(table)


def _display_aggregate_stats(console: Console, summary: dict):
    """Display aggregate statistics across all agents."""
    panel_content = f"""
Total Agents: {summary["total_agents"]}
Total Executions: {summary["total_executions"]}
Total Failures: {summary["total_failures"]}
Avg Failure Rate: {summary["avg_failure_rate"] * 100:.1f}%
Avg Detection Latency: {summary["avg_detection_latency"]:.2f}s
Avg Recovery Rate: {summary["avg_recovery_rate"] * 100:.1f}%

Detection Latency P95: {summary["detection_latency_stats"]["p95"]:.2f}s
Detection Latency P99: {summary["detection_latency_stats"]["p99"]:.2f}s
    """.strip()

    panel = Panel(
        panel_content,
        title="Aggregate Health Metrics",
        border_style="cyan",
    )
    console.print(panel)
