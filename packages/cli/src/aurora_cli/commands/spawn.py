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

import click
from rich.console import Console

from aurora_cli.commands.spawn_helpers import clean_checkpoints as _clean_checkpoints_impl
from aurora_cli.commands.spawn_helpers import list_checkpoints as _list_checkpoints_impl
from aurora_cli.commands.spawn_helpers import resume_from_checkpoint as _resume_from_checkpoint_impl
from aurora_spawner import spawn_parallel, spawn_parallel_tracked
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
@click.option(
    "--yes",
    "-y",
    is_flag=True,
    help="Skip execution preview prompt",
)
@click.option(
    "--resume",
    type=str,
    default=None,
    help="Resume from checkpoint by execution ID",
)
@click.option(
    "--list-checkpoints",
    is_flag=True,
    help="List resumable checkpoints and exit",
)
@click.option(
    "--clean-checkpoints",
    type=int,
    default=None,
    metavar="DAYS",
    help="Clean checkpoints older than DAYS and exit",
)
@click.option(
    "--no-checkpoint",
    is_flag=True,
    help="Disable checkpoint creation",
)
@click.option(
    "--max-concurrent",
    type=int,
    default=4,
    help="Maximum concurrent tasks (default: 4)",
)
@click.option(
    "--stagger-delay",
    type=float,
    default=5.0,
    help="Delay between task starts in seconds (default: 5.0)",
)
@click.option(
    "--policy",
    type=click.Choice(["default", "patient", "fast_fail", "production", "development"]),
    default="patient",
    help="Spawn timeout policy (default: patient)",
)
@click.option(
    "--no-fallback",
    is_flag=True,
    help="Disable LLM fallback on agent failure",
)
def spawn_command(
    task_file: Path,
    parallel: bool,
    sequential: bool,
    verbose: bool,
    dry_run: bool,
    yes: bool,
    resume: str | None,
    list_checkpoints: bool,
    clean_checkpoints: int | None,
    no_checkpoint: bool,
    max_concurrent: int,
    stagger_delay: float,
    policy: str,
    no_fallback: bool,
) -> None:
    """Execute tasks from a markdown task file with checkpoint support.

    Loads tasks from TASK_FILE (default: tasks.md) and executes them using
    the aurora-spawner package. Tasks can specify agents via HTML comments:

        - [ ] 1. My task description
        <!-- agent: agent-name -->

    By default, tasks are executed in parallel with max_concurrent=5.
    Use --sequential to force one-at-a-time execution.

    Supports checkpoints for resume after interruption:
        aur spawn --resume <execution-id>
        aur spawn --list-checkpoints
        aur spawn --clean-checkpoints 7

    Args:
        task_file: Path to task file (default: tasks.md)
        parallel: Execute in parallel (default: True)
        sequential: Force sequential execution
        verbose: Show detailed output
        dry_run: Validate without executing
        yes: Skip execution preview prompt
        resume: Resume from checkpoint ID
        list_checkpoints: List resumable checkpoints
        clean_checkpoints: Clean old checkpoints (days)
        no_checkpoint: Disable checkpoint creation
        max_concurrent: Maximum concurrent tasks (default: 4)
        stagger_delay: Delay between task starts in seconds (default: 5.0)
        policy: Spawn timeout policy preset (default: patient)
        no_fallback: Disable LLM fallback on agent failure
    """
    try:
        from aurora_cli.execution import CheckpointManager

        # Handle utility flags first
        if list_checkpoints:
            _list_checkpoints()
            return

        if clean_checkpoints is not None:
            _clean_checkpoints(clean_checkpoints)
            return

        # Load or resume tasks
        if resume:
            tasks, execution_id = _resume_from_checkpoint(resume)
            console.print(f"[cyan]Resuming execution: {execution_id}[/]")
        else:
            # Load tasks from file
            tasks = load_tasks(task_file)
            execution_id = f"spawn-{int(__import__('time').time() * 1000)}"

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

        # Check policies for potentially destructive operations
        from aurora_cli.policies import Operation, OperationType, PoliciesEngine, PolicyAction

        try:
            policies = PoliciesEngine()

            # Scan tasks for keywords that might indicate destructive operations
            for task in tasks:
                desc_lower = task.description.lower()

                # Check for file deletion keywords
                if any(kw in desc_lower for kw in ["delete", "remove", "rm ", "del "]):
                    op = Operation(type=OperationType.FILE_DELETE, target=task.description, count=1)
                    result = policies.check_operation(op)

                    if result.action == PolicyAction.DENY:
                        console.print(f"[red]Policy violation:[/] {result.reason}")
                        console.print(f"[red]Task blocked:[/] {task.description}")
                        return
                    elif result.action == PolicyAction.PROMPT and not yes:
                        console.print(f"[yellow]Warning:[/] {result.reason}")
                        console.print(f"[yellow]Task:[/] {task.description}")
                        if not click.confirm("Proceed with this task?"):
                            console.print("[yellow]Execution cancelled by user.[/]")
                            return

        except Exception as e:
            logger.warning(f"Policy check failed: {e}, proceeding without policy enforcement")

        # Show execution preview (unless --yes or resuming)
        if not yes and not resume:
            from aurora_cli.execution import ExecutionPreview, ReviewDecision

            # Convert tasks to preview format
            preview_tasks = [
                {"description": t.description, "agent_id": t.agent or "llm", "task": t.description}
                for t in tasks
            ]

            preview = ExecutionPreview(preview_tasks)
            preview.display()
            decision = preview.prompt()

            if decision == ReviewDecision.ABORT:
                console.print("[yellow]Execution cancelled by user.[/]")
                return

        # Initialize checkpoint manager (unless disabled)
        checkpoint_mgr = None
        if not no_checkpoint:
            checkpoint_mgr = CheckpointManager(execution_id, plan_id=None)
            console.print(f"[dim]Checkpoint: {execution_id}[/]")

        # Determine execution mode
        use_parallel = parallel and not sequential

        try:
            if use_parallel:
                console.print(
                    f"[cyan]Executing {len(tasks)} tasks in parallel "
                    f"(max_concurrent={max_concurrent}, policy={policy}, stagger={stagger_delay}s)...[/]"
                )
                result = asyncio.run(
                    _execute_parallel(
                        tasks,
                        verbose,
                        checkpoint_mgr=checkpoint_mgr,
                        max_concurrent=max_concurrent,
                        stagger_delay=stagger_delay,
                        policy_name=policy,
                        fallback_to_llm=not no_fallback,
                    )
                )
            else:
                console.print("[cyan]Executing tasks sequentially...[/]")
                result = asyncio.run(
                    _execute_sequential(
                        tasks,
                        verbose,
                        checkpoint_mgr=checkpoint_mgr,
                        policy_name=policy,
                        fallback_to_llm=not no_fallback,
                    )
                )
        except KeyboardInterrupt:
            if checkpoint_mgr:
                checkpoint_mgr.mark_interrupted()
                console.print(
                    f"\n[yellow]Interrupted. Resume with:[/] aur spawn --resume {execution_id}"
                )
            raise click.Abort()

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


async def _execute_parallel(
    tasks: list[ParsedTask],
    verbose: bool,
    checkpoint_mgr=None,
    max_concurrent: int = 4,
    stagger_delay: float = 5.0,
    policy_name: str = "patient",
    fallback_to_llm: bool = True,
) -> dict[str, int]:
    """Execute tasks in parallel using spawn_parallel_tracked().

    Uses the same mature spawning infrastructure as aur soar:
    - Stagger delays between task starts
    - Per-task heartbeat monitoring
    - Global timeout calculation
    - Circuit breaker pre-checks
    - Retry with fallback to LLM

    Args:
        tasks: List of tasks to execute
        verbose: Show detailed output
        checkpoint_mgr: Optional CheckpointManager for progress tracking
        max_concurrent: Maximum concurrent tasks (default: 4)
        stagger_delay: Delay between task starts in seconds (default: 5.0)
        policy_name: Spawn policy preset (default: "patient")
        fallback_to_llm: Fall back to LLM on agent failure (default: True)

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
            policy_name=policy_name,
        )
        spawn_tasks.append(spawn_task)

    # Progress callback
    def on_progress(msg: str):
        if verbose:
            console.print(f"[dim]{msg}[/]")

    # Execute with spawn_parallel_tracked (shared with aur soar)
    results, metadata = await spawn_parallel_tracked(
        tasks=spawn_tasks,
        max_concurrent=max_concurrent,
        stagger_delay=stagger_delay,
        policy_name=policy_name,
        on_progress=on_progress if verbose else None,
        fallback_to_llm=fallback_to_llm,
    )

    # Display verbose results
    if verbose:
        console.print("")
        for i, result in enumerate(results):
            task_id = tasks[i].id
            if result.success:
                fallback_note = " (fallback)" if getattr(result, "fallback", False) else ""
                console.print(f"[green]✓[/] Task {task_id}: Success{fallback_note}")
            else:
                console.print(f"[red]✗[/] Task {task_id}: Failed - {result.error}")

        # Show metadata summary
        if metadata.get("fallback_count", 0) > 0:
            console.print(f"[yellow]Fallbacks used: {metadata['fallback_count']}[/]")
        if metadata.get("circuit_blocked"):
            console.print(f"[yellow]Circuit blocked: {len(metadata['circuit_blocked'])} tasks[/]")

    return {
        "total": metadata["total_tasks"],
        "completed": metadata["total_tasks"] - metadata["failed_tasks"],
        "failed": metadata["failed_tasks"],
    }


async def _execute_sequential(
    tasks: list[ParsedTask],
    verbose: bool,
    checkpoint_mgr=None,
    policy_name: str = "patient",
    fallback_to_llm: bool = True,
) -> dict[str, int]:
    """Execute tasks sequentially using spawn_parallel_tracked().

    Uses the same infrastructure as parallel execution but with max_concurrent=1
    and no stagger delay.

    Args:
        tasks: List of tasks to execute
        verbose: Show detailed output
        checkpoint_mgr: Optional CheckpointManager for progress tracking
        policy_name: Spawn policy preset (default: "patient")
        fallback_to_llm: Fall back to LLM on agent failure (default: True)

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
            policy_name=policy_name,
        )
        spawn_tasks.append(spawn_task)

    # Progress callback
    def on_progress(msg: str):
        if verbose:
            console.print(f"[dim]{msg}[/]")

    # Execute sequentially (max_concurrent=1, no stagger)
    results, metadata = await spawn_parallel_tracked(
        tasks=spawn_tasks,
        max_concurrent=1,
        stagger_delay=0.0,  # No stagger for sequential
        policy_name=policy_name,
        on_progress=on_progress if verbose else None,
        fallback_to_llm=fallback_to_llm,
    )

    # Display verbose results
    if verbose:
        console.print("")
        for i, result in enumerate(results):
            task_id = tasks[i].id
            if result.success:
                fallback_note = " (fallback)" if getattr(result, "fallback", False) else ""
                console.print(f"[green]✓[/] Task {task_id}: Success{fallback_note}")
            else:
                console.print(f"[red]✗[/] Task {task_id}: Failed - {result.error}")

    return {
        "total": metadata["total_tasks"],
        "completed": metadata["total_tasks"] - metadata["failed_tasks"],
        "failed": metadata["failed_tasks"],
    }


def execute_tasks_parallel(tasks: list[ParsedTask]) -> dict[str, int]:
    """Execute tasks in parallel (synchronous wrapper).

    Args:
        tasks: List of tasks to execute

    Returns:
        Execution summary with total, completed, failed counts
    """
    return asyncio.run(_execute_parallel(tasks, verbose=False))


def _list_checkpoints() -> None:
    """List all resumable checkpoints."""
    _list_checkpoints_impl()


def _clean_checkpoints(days: int) -> None:
    """Clean checkpoints older than specified days."""
    _clean_checkpoints_impl(days)


def _resume_from_checkpoint(execution_id: str) -> tuple[list[ParsedTask], str]:
    """Resume execution from checkpoint."""
    return _resume_from_checkpoint_impl(execution_id)
