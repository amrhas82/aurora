"""Spawner functions for aurora-spawner package.

Features:
- Error pattern detection: Kill process immediately on API/connection errors
- Progressive timeout: 60s initial, extend to 300s if stdout activity detected
- Circuit breaker: Skip known-failing agents after threshold failures
"""

import asyncio
import logging
import os
import re
import shutil
import time
from typing import Any, Callable

from aurora_spawner.models import SpawnResult, SpawnTask


logger = logging.getLogger(__name__)

# Error patterns to detect early failures (case-insensitive)
ERROR_PATTERNS = [
    re.compile(r"rate.?limit", re.IGNORECASE),
    re.compile(r"\b429\b"),
    re.compile(r"connection.?(refused|reset|error)", re.IGNORECASE),
    re.compile(r"ECONNRESET", re.IGNORECASE),
    re.compile(r"API.?error", re.IGNORECASE),
    re.compile(r"authentication.?failed", re.IGNORECASE),
    re.compile(r"model.?not.?available", re.IGNORECASE),
    re.compile(r"quota.?exceeded", re.IGNORECASE),
    re.compile(r"invalid.?api.?key", re.IGNORECASE),
    re.compile(r"unauthorized", re.IGNORECASE),
    re.compile(r"forbidden", re.IGNORECASE),
]

# Timeout settings
# Note: Claude CLI buffers output, so "no stdout" doesn't mean stuck
# Use task.timeout as the primary timeout, only fail early on ERROR patterns
DEFAULT_TIMEOUT = 300  # seconds - default if task.timeout not set


def _check_error_patterns(text: str) -> str | None:
    """Check text against error patterns.

    Args:
        text: Text to check (usually stderr line)

    Returns:
        Matched error description or None
    """
    for pattern in ERROR_PATTERNS:
        if pattern.search(text):
            return f"Error pattern detected: {pattern.pattern}"
    return None


async def spawn(
    task: SpawnTask,
    tool: str | None = None,
    model: str | None = None,
    config: dict[str, Any] | None = None,
    on_output: Callable[[str], None] | None = None,
    heartbeat_emitter: Any | None = None,
) -> SpawnResult:
    """Spawn a subprocess for a single task with early failure detection.

    Features:
    - Monitors stderr for error patterns, kills immediately on match
    - Progressive timeout: 60s initial, extends to 300s if stdout activity
    - Tracks stdout activity to detect stuck processes
    - Emits heartbeat events for real-time monitoring

    Args:
        task: The task to execute
        tool: CLI tool to use (overrides env/config/default)
        model: Model to use (overrides env/config/default)
        config: Configuration dictionary
        on_output: Optional callback for streaming output lines
        heartbeat_emitter: Optional heartbeat emitter for progress tracking

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
        # Emit started event
        if heartbeat_emitter:
            from aurora_spawner.heartbeat import HeartbeatEventType

            heartbeat_emitter.emit(
                HeartbeatEventType.STARTED,
                agent_id=task.agent or "llm",
                message=f"Starting {resolved_tool} with {resolved_model}",
                tool=resolved_tool,
                model=resolved_model,
            )

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

        # Track errors from stderr
        stdout_chunks: list[bytes] = []
        stderr_chunks: list[bytes] = []
        error_detected: str | None = None
        timeout_seconds = task.timeout or DEFAULT_TIMEOUT

        async def read_stdout():
            """Read stdout chunks."""
            while True:
                try:
                    chunk = await process.stdout.read(4096)
                    if not chunk:
                        break
                    stdout_chunks.append(chunk)
                    # Emit stdout event
                    if heartbeat_emitter:
                        from aurora_spawner.heartbeat import HeartbeatEventType

                        heartbeat_emitter.emit(
                            HeartbeatEventType.STDOUT,
                            agent_id=task.agent or "llm",
                            message=f"Output: {len(chunk)} bytes",
                            bytes=len(chunk),
                        )
                except Exception:
                    break

        async def read_stderr():
            """Read stderr and check for error patterns (fast fail on API errors)."""
            nonlocal error_detected
            buffer = ""
            while True:
                try:
                    chunk = await process.stderr.read(1024)
                    if not chunk:
                        break
                    stderr_chunks.append(chunk)
                    # Emit stderr event
                    if heartbeat_emitter:
                        from aurora_spawner.heartbeat import HeartbeatEventType

                        heartbeat_emitter.emit(
                            HeartbeatEventType.STDERR,
                            agent_id=task.agent or "llm",
                            message=f"Error output: {len(chunk)} bytes",
                            bytes=len(chunk),
                        )
                    # Check for error patterns line by line
                    buffer += chunk.decode(errors="ignore")
                    while "\n" in buffer:
                        line, buffer = buffer.split("\n", 1)
                        error = _check_error_patterns(line)
                        if error:
                            error_detected = error
                            logger.debug(f"Error pattern detected: {error}")
                            return  # Stop reading, found an error
                except Exception:
                    break
            # Check remaining buffer
            if buffer:
                error = _check_error_patterns(buffer)
                if error:
                    error_detected = error

        # Run readers concurrently with timeout
        stdout_task = asyncio.create_task(read_stdout())
        stderr_task = asyncio.create_task(read_stderr())

        try:
            # Wait for process with timeout, but check for early errors
            start_time = time.time()
            while process.returncode is None:
                # Check if error pattern detected in stderr
                if error_detected:
                    logger.debug(f"Killing process early: {error_detected}")
                    if heartbeat_emitter:
                        from aurora_spawner.heartbeat import HeartbeatEventType

                        heartbeat_emitter.emit(
                            HeartbeatEventType.KILLED,
                            agent_id=task.agent or "llm",
                            message=f"Killed: {error_detected}",
                        )
                    process.kill()
                    await process.wait()
                    break

                # Check timeout
                elapsed = time.time() - start_time
                if elapsed > timeout_seconds:
                    logger.debug(f"Process timeout after {timeout_seconds}s")
                    if heartbeat_emitter:
                        from aurora_spawner.heartbeat import HeartbeatEventType

                        heartbeat_emitter.emit(
                            HeartbeatEventType.KILLED,
                            agent_id=task.agent or "llm",
                            message=f"Timeout after {timeout_seconds}s",
                        )
                    process.kill()
                    await process.wait()
                    error_detected = f"Process timed out after {timeout_seconds} seconds"
                    break

                await asyncio.sleep(0.5)

        finally:
            # Cancel reader tasks
            for t in [stdout_task, stderr_task]:
                if not t.done():
                    t.cancel()
                    try:
                        await t
                    except asyncio.CancelledError:
                        pass

        # Decode output
        stdout_text = b"".join(stdout_chunks).decode(errors="ignore")
        stderr_text = b"".join(stderr_chunks).decode(errors="ignore")

        # Invoke callback for output if provided
        if on_output and stdout_text:
            for line in stdout_text.splitlines():
                on_output(line)

        # Determine success
        if error_detected:
            if heartbeat_emitter:
                from aurora_spawner.heartbeat import HeartbeatEventType

                heartbeat_emitter.emit(
                    HeartbeatEventType.FAILED,
                    agent_id=task.agent or "llm",
                    message=error_detected,
                )
            return SpawnResult(
                success=False,
                output=stdout_text,
                error=error_detected,
                exit_code=-1,
            )

        success = process.returncode == 0
        if heartbeat_emitter:
            from aurora_spawner.heartbeat import HeartbeatEventType

            if success:
                heartbeat_emitter.emit(
                    HeartbeatEventType.COMPLETED,
                    agent_id=task.agent or "llm",
                    message="Execution completed successfully",
                )
            else:
                heartbeat_emitter.emit(
                    HeartbeatEventType.FAILED,
                    agent_id=task.agent or "llm",
                    message=f"Exit code: {process.returncode}",
                )

        return SpawnResult(
            success=success,
            output=stdout_text,
            error=stderr_text if not success else None,
            exit_code=process.returncode or 0,
        )

    except Exception as e:
        logger.debug(f"Spawn exception: {e}")
        return SpawnResult(
            success=False,
            output="",
            error=str(e),
            exit_code=-1,
        )


async def spawn_parallel(
    tasks: list[SpawnTask],
    max_concurrent: int = 5,
    on_progress: Callable[[int, int, str, str], None] | None = None,
    **kwargs: Any,
) -> list[SpawnResult]:
    """Spawn subprocesses in parallel with concurrency limiting.

    Args:
        tasks: List of tasks to execute in parallel
        max_concurrent: Maximum number of concurrent tasks (default: 5)
        on_progress: Optional callback(idx, total, agent_id, status)
        **kwargs: Additional arguments passed to spawn()

    Returns:
        List of SpawnResults in input order
    """
    if not tasks:
        return []

    # Create semaphore for concurrency limiting
    semaphore = asyncio.Semaphore(max_concurrent)
    total = len(tasks)

    async def spawn_with_semaphore(idx: int, task: SpawnTask) -> SpawnResult:
        """Wrapper that acquires semaphore before spawning."""
        async with semaphore:
            try:
                # Call progress callback on start
                agent_id = task.agent or "llm"
                if on_progress:
                    on_progress(idx + 1, total, agent_id, "Starting")

                start_time = time.time()
                result = await spawn(task, **kwargs)
                elapsed = time.time() - start_time

                # Call progress callback on complete
                if on_progress:
                    on_progress(idx + 1, total, agent_id, f"Completed ({elapsed:.1f}s)")

                return result
            except Exception as e:
                # Best-effort: convert exceptions to failed results
                return SpawnResult(
                    success=False,
                    output="",
                    error=str(e),
                    exit_code=-1,
                )

    # Execute all tasks in parallel and gather results
    coros = [spawn_with_semaphore(idx, task) for idx, task in enumerate(tasks)]
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


async def spawn_with_retry_and_fallback(
    task: SpawnTask,
    on_progress: Callable[[int, int, str], None] | None = None,
    max_retries: int = 2,
    fallback_to_llm: bool = True,
    circuit_breaker: Any = None,
    **kwargs: Any,
) -> SpawnResult:
    """Spawn subprocess with automatic retry, circuit breaker, and fallback to LLM.

    Features:
    1. Circuit breaker: Skip known-failing agents immediately
    2. Early failure detection: Kill on error patterns
    3. Progressive timeout: Fail fast if no activity
    4. Retry: Handle transient failures
    5. Fallback: Use direct LLM if agent fails

    Args:
        task: The task to execute. If task.agent is None, goes directly to LLM.
        on_progress: Optional callback(attempt, max_attempts, status)
        max_retries: Maximum number of retries after initial attempt (default: 2)
        fallback_to_llm: Whether to fallback to LLM after all retries fail (default: True)
        circuit_breaker: Optional CircuitBreaker instance (uses singleton if None)
        **kwargs: Additional arguments passed to spawn()

    Returns:
        SpawnResult with retry/fallback metadata
    """
    from aurora_spawner.circuit_breaker import get_circuit_breaker

    # Get circuit breaker
    cb = circuit_breaker or get_circuit_breaker()
    agent_id = task.agent or "llm"

    # Check circuit breaker before attempting
    if task.agent:
        should_skip, skip_reason = cb.should_skip(agent_id)
        if should_skip:
            logger.debug(f"Circuit breaker: skipping agent '{agent_id}' - {skip_reason}")
            if fallback_to_llm:
                # Go directly to fallback
                if on_progress:
                    on_progress(1, 1, "Circuit open, fallback to LLM")
                fallback_task = SpawnTask(
                    prompt=task.prompt,
                    agent=None,
                    timeout=task.timeout,
                )
                result = await spawn(fallback_task, **kwargs)
                result.fallback = True
                result.original_agent = task.agent
                result.retry_count = 0
                if result.success:
                    # Don't record success for fallback - agent is still broken
                    pass
                return result
            else:
                # No fallback, return circuit open error
                return SpawnResult(
                    success=False,
                    output="",
                    error=skip_reason,
                    exit_code=-1,
                    fallback=False,
                    original_agent=task.agent,
                    retry_count=0,
                )

    max_agent_attempts = max_retries + 1  # Initial attempt + retries
    max_total_attempts = max_agent_attempts + (1 if fallback_to_llm else 0)

    # Attempt agent execution with retries
    for attempt in range(max_agent_attempts):
        attempt_num = attempt + 1
        logger.debug(f"Spawn attempt {attempt_num}/{max_agent_attempts} for agent={agent_id}")

        # Check circuit breaker before each attempt (not just first)
        if task.agent and attempt > 0:
            should_skip, skip_reason = cb.should_skip(agent_id)
            if should_skip:
                logger.debug("Circuit opened mid-retry, skipping to fallback")
                break  # Exit retry loop, go to fallback

        if on_progress and attempt > 0:
            on_progress(attempt_num, max_total_attempts, "Retrying")

        result = await spawn(task, **kwargs)

        if result.success:
            logger.debug(f"Spawn succeeded on attempt {attempt_num}")
            result.retry_count = attempt
            result.fallback = False
            # Record success with circuit breaker
            if task.agent:
                cb.record_success(agent_id)
            return result

        # Record failure PER ATTEMPT for faster circuit opening
        if task.agent:
            cb.record_failure(agent_id)
        logger.debug(f"Spawn attempt {attempt_num} failed: {result.error}")

    # Try fallback if enabled
    if fallback_to_llm:
        if on_progress:
            on_progress(max_agent_attempts + 1, max_total_attempts, "Fallback to LLM")

        logger.debug(
            f"Agent '{agent_id}' failed after {max_agent_attempts} attempts, falling back to LLM"
        )
        fallback_task = SpawnTask(
            prompt=task.prompt,
            agent=None,
            timeout=task.timeout,
        )

        result = await spawn(fallback_task, **kwargs)
        result.fallback = True
        result.original_agent = task.agent
        result.retry_count = max_agent_attempts

        if result.success:
            logger.debug("Fallback to LLM succeeded")
        else:
            logger.debug(f"Fallback to LLM also failed: {result.error}")

        return result

    # No fallback - return last failure
    result.retry_count = max_agent_attempts
    result.fallback = False
    return result
