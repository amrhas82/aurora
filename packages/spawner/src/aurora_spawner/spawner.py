"""Spawner functions for aurora-spawner package."""

import asyncio
import os
import shutil
from typing import Any, Callable

from aurora_spawner.models import SpawnResult, SpawnTask


async def spawn(
    task: SpawnTask,
    tool: str | None = None,
    model: str | None = None,
    config: dict[str, Any] | None = None,
    on_output: Callable[[str], None] | None = None,
) -> SpawnResult:
    """Spawn a subprocess for a single task.

    Args:
        task: The task to execute
        tool: CLI tool to use (overrides env/config/default)
        model: Model to use (overrides env/config/default)
        config: Configuration dictionary
        on_output: Optional callback for streaming output lines

    Returns:
        SpawnResult with execution details

    Raises:
        ValueError: If tool is not found in PATH
    """
    # Tool resolution: CLI flag -> env var -> config -> default
    resolved_tool = tool or os.environ.get("AURORA_SPAWN_TOOL")
    if not resolved_tool and config:
        resolved_tool = config.get("spawner", {}).get("tool")
    if not resolved_tool:
        resolved_tool = "claude"

    # Model resolution: CLI flag -> env var -> config -> default
    resolved_model = model or os.environ.get("AURORA_SPAWN_MODEL")
    if not resolved_model and config:
        resolved_model = config.get("spawner", {}).get("model")
    if not resolved_model:
        resolved_model = "sonnet"

    # Validate tool exists
    tool_path = shutil.which(resolved_tool)
    if not tool_path:
        raise ValueError(f"Tool '{resolved_tool}' not found in PATH")

    # Build command: [tool, "-p", "--model", model]
    cmd = [resolved_tool, "-p", "--model", resolved_model]

    # Add --agent flag if agent is specified
    if task.agent:
        cmd.extend(["--agent", task.agent])

    try:
        # Spawn subprocess
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        # Write prompt to stdin
        if process.stdin:
            process.stdin.write(task.prompt.encode())
            await process.stdin.drain()
            process.stdin.close()

        # Wait for completion with timeout
        try:
            stdout_data, stderr_data = await asyncio.wait_for(
                process.communicate(), timeout=task.timeout
            )
        except asyncio.TimeoutError:
            process.kill()
            await process.wait()
            return SpawnResult(
                success=False,
                output="",
                error=f"Process timed out after {task.timeout} seconds",
                exit_code=-1,
            )

        # Decode output
        stdout_text = stdout_data.decode() if stdout_data else ""
        stderr_text = stderr_data.decode() if stderr_data else ""

        # Invoke callback for output if provided
        if on_output and stdout_text:
            for line in stdout_text.splitlines():
                on_output(line)

        # Build result
        success = process.returncode == 0
        return SpawnResult(
            success=success,
            output=stdout_text,
            error=stderr_text,
            exit_code=process.returncode or 0,
        )

    except Exception as e:
        return SpawnResult(
            success=False,
            output="",
            error=str(e),
            exit_code=-1,
        )


async def spawn_parallel(
    tasks: list[SpawnTask], max_concurrent: int = 5, **kwargs: Any
) -> list[SpawnResult]:
    """Spawn subprocesses in parallel with concurrency limiting.

    Args:
        tasks: List of tasks to execute in parallel
        max_concurrent: Maximum number of concurrent tasks (default: 5)
        **kwargs: Additional arguments passed to spawn()

    Returns:
        List of SpawnResults in input order
    """
    if not tasks:
        return []

    # Create semaphore for concurrency limiting
    semaphore = asyncio.Semaphore(max_concurrent)

    async def spawn_with_semaphore(task: SpawnTask) -> SpawnResult:
        """Wrapper that acquires semaphore before spawning."""
        async with semaphore:
            try:
                return await spawn(task, **kwargs)
            except Exception as e:
                # Best-effort: convert exceptions to failed results
                return SpawnResult(
                    success=False,
                    output="",
                    error=str(e),
                    exit_code=-1,
                )

    # Execute all tasks in parallel and gather results
    coros = [spawn_with_semaphore(task) for task in tasks]
    results = await asyncio.gather(*coros, return_exceptions=False)

    return list(results)


async def spawn_sequential(
    tasks: list[SpawnTask], pass_context: bool = True, stop_on_failure: bool = False, **kwargs: Any
) -> list[SpawnResult]:
    """Spawn subprocesses sequentially with optional context passing.

    Args:
        tasks: List of tasks to execute sequentially
        pass_context: If True, accumulate outputs and pass to subsequent tasks
        stop_on_failure: If True, stop execution when a task fails
        **kwargs: Additional arguments passed to spawn()

    Returns:
        List of SpawnResults in execution order
    """
    if not tasks:
        return []

    results = []
    accumulated_context = ""

    for task in tasks:
        # Build prompt with accumulated context if enabled
        if pass_context and accumulated_context:
            modified_prompt = f"{task.prompt}\n\nPrevious context:\n{accumulated_context}"
            modified_task = SpawnTask(
                prompt=modified_prompt,
                agent=task.agent,
                timeout=task.timeout,
            )
        else:
            modified_task = task

        # Execute task
        result = await spawn(modified_task, **kwargs)
        results.append(result)

        # Accumulate context from successful tasks
        if pass_context and result.success and result.output:
            accumulated_context += result.output + "\n"

        # Stop on failure if requested
        if stop_on_failure and not result.success:
            break

    return results
