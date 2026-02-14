"""Spawn command - Execute tasks from task files or prompts.

This command loads tasks from a markdown file (default: tasks.md) or decomposes
a natural language prompt into tasks, then executes them. Supports dependency-aware
wave execution and output persistence.

Examples:
    # Execute tasks.md in current directory
    aur spawn

    # Execute specific task file
    aur spawn path/to/tasks.md

    # Decompose a prompt into tasks and execute
    aur spawn "Create a hello world Python script with tests"

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

from aurora_spawner import spawn_parallel_tracked
from aurora_spawner.models import SpawnTask
from implement.models import ParsedTask
from implement.parser import TaskParser
from implement.persistence import SpawnRunStore
from implement.topo_sort import topological_sort_tasks

console = Console()
logger = logging.getLogger(__name__)


@click.command(name="spawn")
@click.argument(
    "input_arg",
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
    "--verbose/--quiet",
    "-v/-q",
    default=True,
    help="Show detailed output during execution (default: on)",
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
    input_arg: str,
    parallel: bool,
    sequential: bool,
    verbose: bool,
    dry_run: bool,
    yes: bool,
    max_concurrent: int,
    stagger_delay: float,
    policy: str,
    no_fallback: bool,
) -> None:
    """Execute tasks from a markdown task file or a prompt.

    INPUT_ARG can be a path to a tasks.md file (default: tasks.md) or a
    natural language prompt that will be decomposed into tasks.

    Tasks can specify agents and dependencies via sub-bullets:

        - [ ] 1. My task description
          - Agent: @agent-name
          - Depends: 1.0, 2.0

    By default, tasks are executed in parallel with max_concurrent=4.
    Use --sequential to force one-at-a-time execution.
    Tasks with dependencies are automatically executed in waves.

    """
    try:
        input_path = Path(input_arg)
        is_file_mode = input_path.exists()

        if is_file_mode:
            # File mode: load tasks from file
            tasks, tasks_md_content = _load_from_file(input_path)
        else:
            # Check if default tasks.md doesn't exist and input looks like a file path
            if input_arg == "tasks.md":
                raise FileNotFoundError(f"Task file not found: {input_arg}")

            # Prompt mode: decompose prompt into tasks
            tasks, tasks_md_content = _load_from_prompt(input_arg)

        if not tasks:
            console.print("[yellow]No tasks found.[/]")
            return

        source = str(input_path) if is_file_mode else "prompt"
        console.print(f"[cyan]Loaded {len(tasks)} tasks from {source}[/]")

        # Check for dependencies
        has_deps = any(t.depends_on for t in tasks)

        if dry_run:
            _display_dry_run(tasks, has_deps)
            return

        # Check policies for potentially destructive operations
        _check_policies(tasks, yes)

        # Show execution preview (unless --yes)
        if not yes:
            from aurora_cli.execution import ExecutionPreview, ReviewDecision

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

        # Setup persistence
        store = SpawnRunStore()
        run_dir = store.create_run(tasks_md_content)

        # Load previous results for re-runs (skip already completed tasks)
        completed_outputs: dict[str, str] = {}
        if is_file_mode:
            prev = store.load_previous_results(tasks_md_content)
            if prev:
                completed_outputs = prev
                console.print(f"[dim]Found {len(prev)} previous results for re-run[/]")

        # Filter out already-completed tasks
        pending_tasks = [t for t in tasks if not t.completed and t.id not in completed_outputs]

        if not pending_tasks:
            console.print("[green]All tasks already completed.[/]")
            store.finalize_run(run_dir, total=len(tasks), completed=len(tasks), failed=0)
            return

        # Determine execution mode
        use_parallel = parallel and not sequential

        try:
            if has_deps:
                console.print(
                    f"[cyan]Executing {len(pending_tasks)} tasks in dependency waves...[/]"
                )
                result = asyncio.run(
                    _execute_waves(
                        pending_tasks,
                        verbose,
                        completed_outputs=completed_outputs,
                        store=store,
                        run_dir=run_dir,
                        max_concurrent=max_concurrent,
                        stagger_delay=stagger_delay,
                        policy_name=policy,
                        fallback_to_llm=not no_fallback,
                    ),
                )
            elif use_parallel:
                console.print(
                    f"[cyan]Executing {len(pending_tasks)} tasks in parallel "
                    f"(max_concurrent={max_concurrent}, policy={policy}, stagger={stagger_delay}s)...[/]",
                )
                result = asyncio.run(
                    _execute_parallel(
                        pending_tasks,
                        verbose,
                        store=store,
                        run_dir=run_dir,
                        max_concurrent=max_concurrent,
                        stagger_delay=stagger_delay,
                        policy_name=policy,
                        fallback_to_llm=not no_fallback,
                    ),
                )
            else:
                console.print("[cyan]Executing tasks sequentially...[/]")
                result = asyncio.run(
                    _execute_sequential(
                        pending_tasks,
                        verbose,
                        store=store,
                        run_dir=run_dir,
                        policy_name=policy,
                        fallback_to_llm=not no_fallback,
                    ),
                )
        except KeyboardInterrupt:
            console.print("\n[yellow]Execution interrupted by user.[/]")
            raise click.Abort()

        # Finalize persistence
        store.finalize_run(
            run_dir,
            total=result["total"],
            completed=result["completed"],
            failed=result["failed"],
        )

        # Display summary
        console.print(f"\n[bold green]Completed:[/] {result['completed']}/{result['total']}")
        if result["failed"] > 0:
            console.print(f"[bold red]Failed:[/] {result['failed']}")
        console.print(f"[dim]Run saved to: {run_dir}[/]")

    except click.Abort:
        raise
    except Exception as e:
        logger.error(f"Spawn command failed: {e}", exc_info=True)
        console.print(f"\n[bold red]Error:[/] {e}", style="red")
        raise click.Abort()


def _load_from_file(file_path: Path) -> tuple[list[ParsedTask], str]:
    """Load tasks from a markdown file.

    Returns:
        Tuple of (parsed tasks, raw file content)

    """
    content = file_path.read_text()
    tasks = load_tasks(file_path)
    return tasks, content


def _load_from_prompt(prompt: str) -> tuple[list[ParsedTask], str]:
    """Decompose a prompt into tasks via LLM.

    Returns:
        Tuple of (parsed tasks, generated tasks.md content)

    """
    from aurora_cli.llm.cli_pipe_client import CLIPipeLLMClient
    from implement.decompose import decompose_prompt_to_tasks_md

    console.print("[cyan]Decomposing prompt into tasks...[/]")

    # Discover available agents
    available_agents = _discover_agents()

    llm_client = CLIPipeLLMClient()
    tasks_md = decompose_prompt_to_tasks_md(llm_client, prompt, available_agents)

    console.print("[dim]Generated tasks.md:[/]")
    console.print(tasks_md)

    # Parse the generated markdown
    parser = TaskParser()
    tasks = parser.parse(tasks_md)
    return tasks, tasks_md


def _discover_agents() -> list[str]:
    """Discover available agent names from agent files."""
    try:
        from aurora_cli.agent_discovery.parser import AgentParser
        from aurora_cli.agent_discovery.scanner import AgentScanner

        scanner = AgentScanner()
        parser = AgentParser()
        agents = []
        for agent_path in scanner.scan_all_sources():
            try:
                agent = parser.parse_file(agent_path)
                if agent and agent.name:
                    agents.append(agent.name)
            except Exception:
                continue
        return agents
    except Exception:
        return []


def _display_dry_run(tasks: list[ParsedTask], has_deps: bool) -> None:
    """Display dry-run output with optional dependency wave info."""
    console.print("[yellow]Dry-run mode: tasks validated but not executed.[/]")

    if has_deps:
        try:
            waves = topological_sort_tasks(tasks)
            for i, wave in enumerate(waves):
                console.print(f"\n  [bold]Wave {i + 1}:[/]")
                for task in wave:
                    status = "[x]" if task.completed else "[ ]"
                    deps = f" (depends: {', '.join(task.depends_on)})" if task.depends_on else ""
                    console.print(
                        f"    {status} {task.id}. {task.description} (agent: {task.agent}){deps}"
                    )
        except ValueError as e:
            console.print(f"  [red]Dependency error: {e}[/]")
    else:
        for task in tasks:
            status = "[x]" if task.completed else "[ ]"
            console.print(f"  {status} {task.id}. {task.description} (agent: {task.agent})")


def _check_policies(tasks: list[ParsedTask], yes: bool) -> None:
    """Check policies for potentially destructive operations."""
    from aurora_cli.policies import Operation, OperationType, PoliciesEngine, PolicyAction

    try:
        policies = PoliciesEngine()

        for task in tasks:
            desc_lower = task.description.lower()

            if any(kw in desc_lower for kw in ["delete", "remove", "rm ", "del "]):
                op = Operation(type=OperationType.FILE_DELETE, target=task.description, count=1)
                result = policies.check_operation(op)

                if result.action == PolicyAction.DENY:
                    console.print(f"[red]Policy violation:[/] {result.reason}")
                    console.print(f"[red]Task blocked:[/] {task.description}")
                    raise click.Abort()
                if result.action == PolicyAction.PROMPT and not yes:
                    console.print(f"[yellow]Warning:[/] {result.reason}")
                    console.print(f"[yellow]Task:[/] {task.description}")
                    if not click.confirm("Proceed with this task?"):
                        console.print("[yellow]Execution cancelled by user.[/]")
                        raise click.Abort()

    except click.Abort:
        raise
    except Exception as e:
        logger.warning(f"Policy check failed: {e}, proceeding without policy enforcement")


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
                f"Task missing required fields: task {task.id} has empty or missing description",
            )

    return tasks


async def _execute_waves(
    tasks: list[ParsedTask],
    verbose: bool,
    completed_outputs: dict[str, str],
    store: SpawnRunStore,
    run_dir: Path,
    max_concurrent: int = 4,
    stagger_delay: float = 5.0,
    policy_name: str = "patient",
    fallback_to_llm: bool = True,
) -> dict[str, int]:
    """Execute tasks in dependency-ordered waves.

    Uses topological sort to group tasks into waves. Within each wave,
    tasks run in parallel. Between waves, completed outputs are forwarded
    as context to dependent tasks.

    """
    waves = topological_sort_tasks(tasks)

    total = len(tasks)
    completed = 0
    failed = 0

    for wave_idx, wave in enumerate(waves):
        if verbose:
            wave_ids = ", ".join(t.id for t in wave)
            console.print(f"\n[cyan]Wave {wave_idx + 1}/{len(waves)}: tasks [{wave_ids}][/]")

        # Inject dependency context into task prompts
        wave_tasks = []
        for task in wave:
            prompt = task.description
            dep_context = _build_dependency_context(task, completed_outputs)
            if dep_context:
                prompt = f"{dep_context}\n\n{prompt}"

            wave_tasks.append(
                SpawnTask(
                    prompt=prompt,
                    agent=task.agent if task.agent != "self" else None,
                    policy_name=policy_name,
                )
            )

        # Progress callback
        def on_progress(msg: str):
            if verbose:
                console.print(f"[dim]{msg}[/]")

        # Execute wave
        results, metadata = await spawn_parallel_tracked(
            tasks=wave_tasks,
            max_concurrent=max_concurrent,
            stagger_delay=stagger_delay,
            policy_name=policy_name,
            on_progress=on_progress if verbose else None,
            fallback_to_llm=fallback_to_llm,
        )

        # Process results
        for i, result in enumerate(results):
            task = wave[i]
            output = getattr(result, "output", "") or ""

            if result.success:
                completed += 1
                completed_outputs[task.id] = output
                store.save_task_result(run_dir, task.id, success=True, output=output)
                if verbose:
                    fallback_note = " (fallback)" if getattr(result, "fallback", False) else ""
                    console.print(f"[green]✓[/] Task {task.id}: Success{fallback_note}")
            else:
                failed += 1
                error = getattr(result, "error", "Unknown error") or "Unknown error"
                store.save_task_result(run_dir, task.id, success=False, error=error)
                if verbose:
                    console.print(f"[red]✗[/] Task {task.id}: Failed - {error}")

    return {"total": total, "completed": completed, "failed": failed}


def _build_dependency_context(task: ParsedTask, completed_outputs: dict[str, str]) -> str:
    """Build context string from completed dependency outputs."""
    if not task.depends_on:
        return ""

    parts = []
    for dep_id in task.depends_on:
        if dep_id in completed_outputs:
            output = completed_outputs[dep_id]
            if output:
                parts.append(f"[Task {dep_id}] output:\n{output}")

    if not parts:
        return ""

    return "Context from completed dependencies:\n" + "\n\n".join(parts)


async def _execute_parallel(
    tasks: list[ParsedTask],
    verbose: bool,
    store: SpawnRunStore,
    run_dir: Path,
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

    # Display verbose results and persist
    if verbose:
        console.print("")
    for i, result in enumerate(results):
        task_id = tasks[i].id
        output = getattr(result, "output", "") or ""
        if result.success:
            store.save_task_result(run_dir, task_id, success=True, output=output)
            if verbose:
                fallback_note = " (fallback)" if getattr(result, "fallback", False) else ""
                console.print(f"[green]✓[/] Task {task_id}: Success{fallback_note}")
        else:
            error = getattr(result, "error", "Unknown error") or "Unknown error"
            store.save_task_result(run_dir, task_id, success=False, error=error)
            if verbose:
                console.print(f"[red]✗[/] Task {task_id}: Failed - {error}")

    # Show metadata summary
    if verbose:
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
    store: SpawnRunStore,
    run_dir: Path,
    policy_name: str = "patient",
    fallback_to_llm: bool = True,
) -> dict[str, int]:
    """Execute tasks sequentially using spawn_parallel_tracked().

    Uses the same infrastructure as parallel execution but with max_concurrent=1
    and no stagger delay.

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

    # Display verbose results and persist
    if verbose:
        console.print("")
    for i, result in enumerate(results):
        task_id = tasks[i].id
        output = getattr(result, "output", "") or ""
        if result.success:
            store.save_task_result(run_dir, task_id, success=True, output=output)
            if verbose:
                fallback_note = " (fallback)" if getattr(result, "fallback", False) else ""
                console.print(f"[green]✓[/] Task {task_id}: Success{fallback_note}")
        else:
            error = getattr(result, "error", "Unknown error") or "Unknown error"
            store.save_task_result(run_dir, task_id, success=False, error=error)
            if verbose:
                console.print(f"[red]✗[/] Task {task_id}: Failed - {error}")

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
    return asyncio.run(
        _execute_parallel(tasks, verbose=False, store=SpawnRunStore(), run_dir=Path("."))
    )
