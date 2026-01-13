"""Spawn command - Execute tasks from task files in parallel.

This command loads tasks from a markdown file (default: tasks.md) and executes
them in parallel using the aurora-spawner package. Tasks can specify which agent
should handle them via HTML comment metadata.

Examples:
    # Execute tasks.md in current directory
    aur spawn

    # Execute specific task file
    aur spawn path/to/tasks.md

    # Execute sequentially instead of parallel
    aur spawn --sequential

    # Dry-run to validate without executing
    aur spawn --dry-run

    # Show verbose output
    aur spawn --verbose
"""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from typing import Any

import click
from rich.console import Console

from aurora_spawner import spawn_parallel
from aurora_spawner.models import SpawnTask
from implement.models import ParsedTask
from implement.parser import TaskParser

console = Console()
logger = logging.getLogger(__name__)


@click.command(name="spawn")
@click.argument(
    "task_file",
    type=click.Path(exists=False, path_type=Path),
    default="tasks.md",
    required=False,
)
@click.option(
    "--parallel/--no-parallel",
    default=True,
    help="Execute tasks in parallel (default: True)",
)
@click.option(
    "--sequential",
    is_flag=True,
    help="Force sequential execution (overrides --parallel)",
)
@click.option(
    "--verbose",
    "-v",
    is_flag=True,
    help="Show detailed output during execution",
)
@click.option(
    "--dry-run",
    is_flag=True,
    help="Parse and validate tasks without executing them",
)
def spawn_command(
    task_file: Path,
    parallel: bool,
    sequential: bool,
    verbose: bool,
    dry_run: bool,
) -> None:
    """Execute tasks from a markdown task file.

    Loads tasks from TASK_FILE (default: tasks.md) and executes them using
    the aurora-spawner package. Tasks can specify agents via HTML comments:

        - [ ] 1. My task description
        <!-- agent: agent-name -->

    By default, tasks are executed in parallel with max_concurrent=5.
    Use --sequential to force one-at-a-time execution.

    Args:
        task_file: Path to task file (default: tasks.md)
        parallel: Execute in parallel (default: True)
        sequential: Force sequential execution
        verbose: Show detailed output
        dry_run: Validate without executing
    """
    try:
        # Load tasks from file
        tasks = load_tasks(task_file)

        if not tasks:
            console.print("[yellow]No tasks found in file.[/]")
            return

        console.print(f"[cyan]Loaded {len(tasks)} tasks from {task_file}[/]")

        if dry_run:
            console.print("[yellow]Dry-run mode: tasks validated but not executed.[/]")
            for task in tasks:
                status = "[x]" if task.completed else "[ ]"
                console.print(f"  {status} {task.id}. {task.description} (agent: {task.agent})")
            return

        # Determine execution mode
        use_parallel = parallel and not sequential

        if use_parallel:
            console.print("[cyan]Executing tasks in parallel...[/]")
            result = asyncio.run(_execute_parallel(tasks, verbose))
        else:
            console.print("[cyan]Executing tasks sequentially...[/]")
            result = asyncio.run(_execute_sequential(tasks, verbose))

        # Display summary
        console.print(f"\n[bold green]Completed:[/] {result['completed']}/{result['total']}")
        if result["failed"] > 0:
            console.print(f"[bold red]Failed:[/] {result['failed']}")

    except click.Abort:
        raise
    except Exception as e:
        logger.error(f"Spawn command failed: {e}", exc_info=True)
        console.print(f"\n[bold red]Error:[/] {e}", style="red")
        raise click.Abort()


def load_tasks(file_path: Path) -> list[ParsedTask]:
    """Load tasks from markdown file.

    Args:
        file_path: Path to task file

    Returns:
        List of ParsedTask objects

    Raises:
        FileNotFoundError: If task file doesn't exist
        ValueError: If tasks are malformed
    """
    if not file_path.exists():
        raise FileNotFoundError(f"Task file not found: {file_path}")

    content = file_path.read_text()
    parser = TaskParser()
    tasks = parser.parse(content)

    if not tasks:
        return []

    # Validate all tasks have required fields
    for task in tasks:
        if not task.id or not task.description or not task.description.strip():
            raise ValueError(
                f"Task missing required fields: task {task.id} has empty or missing description"
            )

    return tasks


async def _execute_parallel(tasks: list[ParsedTask], verbose: bool) -> dict[str, int]:
    """Execute tasks in parallel.

    Args:
        tasks: List of tasks to execute
        verbose: Show detailed output

    Returns:
        Execution summary with total, completed, failed counts
    """
    if not tasks:
        return {"total": 0, "completed": 0, "failed": 0}

    # Convert ParsedTask to SpawnTask
    spawn_tasks = []
    for task in tasks:
        spawn_task = SpawnTask(
            prompt=task.description,
            agent=task.agent if task.agent != "self" else None,
            timeout=300,  # 5 minutes default
        )
        spawn_tasks.append(spawn_task)

    # Execute in parallel with max_concurrent=5
    if verbose:
        console.print(
            f"[cyan]Spawning {len(spawn_tasks)} tasks in parallel (max_concurrent=5)...[/]"
        )

    results = await spawn_parallel(spawn_tasks, max_concurrent=5)

    # Count results
    total = len(results)
    completed = sum(1 for r in results if r.success)
    failed = total - completed

    if verbose:
        for i, result in enumerate(results):
            task_id = tasks[i].id
            if result.success:
                console.print(f"[green]✓[/] Task {task_id}: Success")
            else:
                console.print(f"[red]✗[/] Task {task_id}: Failed - {result.error}")

    return {"total": total, "completed": completed, "failed": failed}


async def _execute_sequential(tasks: list[ParsedTask], verbose: bool) -> dict[str, int]:
    """Execute tasks sequentially.

    Args:
        tasks: List of tasks to execute
        verbose: Show detailed output

    Returns:
        Execution summary with total, completed, failed counts
    """
    if not tasks:
        return {"total": 0, "completed": 0, "failed": 0}

    # For sequential execution, use spawn_parallel with max_concurrent=1
    spawn_tasks = []
    for task in tasks:
        spawn_task = SpawnTask(
            prompt=task.description,
            agent=task.agent if task.agent != "self" else None,
            timeout=300,
        )
        spawn_tasks.append(spawn_task)

    if verbose:
        console.print(f"[cyan]Spawning {len(spawn_tasks)} tasks sequentially...[/]")

    results = await spawn_parallel(spawn_tasks, max_concurrent=1)

    # Count results
    total = len(results)
    completed = sum(1 for r in results if r.success)
    failed = total - completed

    if verbose:
        for i, result in enumerate(results):
            task_id = tasks[i].id
            if result.success:
                console.print(f"[green]✓[/] Task {task_id}: Success")
            else:
                console.print(f"[red]✗[/] Task {task_id}: Failed - {result.error}")

    return {"total": total, "completed": completed, "failed": failed}


def execute_tasks_parallel(tasks: list[ParsedTask]) -> dict[str, int]:
    """Execute tasks in parallel (synchronous wrapper).

    Args:
        tasks: List of tasks to execute

    Returns:
        Execution summary with total, completed, failed counts
    """
    return asyncio.run(_execute_parallel(tasks, verbose=False))
