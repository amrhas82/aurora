"""Helper functions for spawn command checkpoint management."""

from __future__ import annotations

from pathlib import Path

from rich.console import Console
from rich.table import Table

from aurora_cli.execution import CheckpointManager, TaskState
from implement.models import ParsedTask

console = Console()


def list_checkpoints() -> None:
    """List all resumable checkpoints."""
    checkpoints = CheckpointManager.list_resumable()

    if not checkpoints:
        console.print("[yellow]No resumable checkpoints found.[/]")
        return

    # Create table
    table = Table(title="Resumable Checkpoints", show_header=True, header_style="bold cyan")
    table.add_column("Execution ID", style="cyan")
    table.add_column("Started", style="dim")
    table.add_column("Tasks", style="green")
    table.add_column("Status")

    for checkpoint in checkpoints:
        # Count task statuses
        total = len(checkpoint.tasks)
        completed = sum(1 for t in checkpoint.tasks if t.status == "completed")
        pending = sum(1 for t in checkpoint.tasks if t.status in ("pending", "in_progress"))

        status = f"{completed}/{total} done, {pending} remaining"
        if checkpoint.interrupted:
            status += " [yellow](interrupted)[/yellow]"

        table.add_row(
            checkpoint.execution_id,
            checkpoint.started_at[:19],  # Trim milliseconds
            str(total),
            status,
        )

    console.print(table)
    console.print(f"\n[dim]Resume with:[/] aur spawn --resume <execution-id>")


def clean_checkpoints(days: int) -> None:
    """Clean checkpoints older than specified days.

    Args:
        days: Age threshold in days
    """
    removed = CheckpointManager.clean_old_checkpoints(days)
    if removed > 0:
        console.print(f"[green]✓[/] Removed {removed} old checkpoint(s)")
    else:
        console.print("[dim]No old checkpoints to clean[/]")


def resume_from_checkpoint(execution_id: str) -> tuple[list[ParsedTask], str]:
    """Resume execution from checkpoint.

    Args:
        execution_id: Checkpoint execution ID

    Returns:
        Tuple of (tasks list, execution_id)

    Raises:
        ValueError: If checkpoint not found or invalid
    """
    mgr = CheckpointManager(execution_id)
    checkpoint = mgr.load()

    if not checkpoint:
        raise ValueError(f"Checkpoint not found: {execution_id}")

    # Convert TaskState back to ParsedTask
    # Note: This is a simplified conversion - in production you'd need
    # to reconstruct full ParsedTask objects from checkpoint metadata
    tasks = []
    for task_state in checkpoint.tasks:
        # Extract task info from metadata or description
        task_id = task_state.id
        description = task_state.metadata.get("description", "")
        agent = task_state.metadata.get("agent", "self")
        completed = task_state.status == "completed"

        task = ParsedTask(
            id=task_id,
            description=description,
            agent=agent,
            completed=completed,
        )
        tasks.append(task)

    # Show resume info
    resume_point = mgr.get_resume_point(checkpoint.tasks)
    console.print(f"[cyan]Found checkpoint from {checkpoint.started_at}[/]")
    console.print(
        f"[cyan]Progress: {resume_point}/{len(tasks)} tasks remaining[/]"
    )

    return tasks, execution_id


def create_task_states_from_tasks(tasks: list[ParsedTask]) -> list[TaskState]:
    """Convert ParsedTask list to TaskState list for checkpoint.

    Args:
        tasks: List of ParsedTask objects

    Returns:
        List of TaskState objects
    """
    task_states = []
    for task in tasks:
        state = TaskState(
            id=str(task.id),
            status="completed" if task.completed else "pending",
            result=None,
            error=None,
            started_at=None,
            completed_at=None,
            metadata={
                "description": task.description,
                "agent": task.agent or "self",
            },
        )
        task_states.append(state)

    return task_states
