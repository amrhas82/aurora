"""Spawner functions for aurora-spawner package.

Features:
- Error pattern detection: Kill process immediately on API/connection errors
- Progressive timeout: 60s initial, extend to 300s if stdout activity detected
- Circuit breaker: Skip known-failing agents after threshold failures
- Configurable timeout policies with adaptive extension
- Retry policies with exponential backoff and jitter
"""

import asyncio
import logging
import os
import shutil
import time
from typing import Any, Callable

from aurora_spawner.models import SpawnResult, SpawnTask
from aurora_spawner.observability import FailureReason, get_health_monitor
from aurora_spawner.timeout_policy import SpawnPolicy

logger = logging.getLogger(__name__)

# Default timeout for backwards compatibility
DEFAULT_TIMEOUT = 300  # seconds - default if task.timeout not set


async def spawn(
    task: SpawnTask,
    tool: str | None = None,
    model: str | None = None,
    config: dict[str, Any] | None = None,
    on_output: Callable[[str], None] | None = None,
    heartbeat_emitter: Any | None = None,
    policy: SpawnPolicy | None = None,
) -> SpawnResult:
    """Spawn a subprocess for a single task with early failure detection.

    Features:
    - Monitors stderr for error patterns, kills immediately on match
    - Configurable timeout policies (fixed, progressive, adaptive)
    - Tracks stdout activity to detect stuck processes
    - Emits heartbeat events for real-time monitoring
    - Early termination based on configurable predicates

    Args:
        task: The task to execute
        tool: CLI tool to use (overrides env/config/default)
        model: Model to use (overrides env/config/default)
        config: Configuration dictionary
        on_output: Optional callback for streaming output lines
        heartbeat_emitter: Optional heartbeat emitter for progress tracking
        policy: Optional spawn policy (defaults to policy from task or default policy)

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

    # Resolve policy: parameter -> task.policy_name -> default
    if policy is None:
        if task.policy_name:
            policy = SpawnPolicy.from_name(task.policy_name)
        else:
            policy = SpawnPolicy.default()

    # Validate tool exists
    tool_path = shutil.which(resolved_tool)
    if not tool_path:
        raise ValueError(f"Tool '{resolved_tool}' not found in PATH")

    # Build command: [tool, "-p", "--model", model]
    cmd = [resolved_tool, "-p", "--model", resolved_model]

    # Add --agent flag if agent is specified
    if task.agent:
        cmd.extend(["--agent", task.agent])

    # Track execution metrics
    start_time = time.time()
    timeout_extended = False

    # Record execution start for health monitoring
    health_monitor = get_health_monitor()
    task_id = getattr(task, "task_id", None) or f"task_{id(task)}"
    agent_id = task.agent or "llm"
    health_monitor.record_execution_start(task_id, agent_id, policy.name)

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
        termination_reason: str | None = None

        # Initialize timeout based on policy
        current_timeout = policy.timeout_policy.get_initial_timeout()
        last_activity_time = time.time()

        async def read_stdout():
            """Read stdout chunks and track activity."""
            nonlocal last_activity_time
            while True:
                try:
                    chunk = await process.stdout.read(4096)
                    if not chunk:
                        break
                    stdout_chunks.append(chunk)
                    last_activity_time = time.time()

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
            """Read stderr and check for error patterns."""
            nonlocal termination_reason, last_activity_time
            buffer = ""
            while True:
                try:
                    chunk = await process.stderr.read(1024)
                    if not chunk:
                        break
                    stderr_chunks.append(chunk)
                    last_activity_time = time.time()

                    # Emit stderr event
                    if heartbeat_emitter:
                        from aurora_spawner.heartbeat import HeartbeatEventType

                        heartbeat_emitter.emit(
                            HeartbeatEventType.STDERR,
                            agent_id=task.agent or "llm",
                            message=f"Error output: {len(chunk)} bytes",
                            bytes=len(chunk),
                        )

                    # Update buffer for termination checks
                    buffer += chunk.decode(errors="ignore")

                except Exception:
                    break

        # Run readers concurrently with timeout
        stdout_task = asyncio.create_task(read_stdout())
        stderr_task = asyncio.create_task(read_stderr())

        try:
            # Wait for process with timeout and early termination checks
            time.time()
            while process.returncode is None:
                now = time.time()
                elapsed = now - start_time
                time_since_activity = now - last_activity_time

                # Get current stdout/stderr for termination checks
                stdout_so_far = b"".join(stdout_chunks).decode(errors="ignore")
                stderr_so_far = b"".join(stderr_chunks).decode(errors="ignore")

                # Check early termination conditions
                should_terminate, reason = policy.termination_policy.should_terminate(
                    stdout_so_far, stderr_so_far, elapsed, time_since_activity
                )

                if should_terminate:
                    logger.debug(f"Early termination: {reason}")
                    termination_reason = reason
                    if heartbeat_emitter:
                        from aurora_spawner.heartbeat import HeartbeatEventType

                        heartbeat_emitter.emit(
                            HeartbeatEventType.KILLED,
                            agent_id=task.agent or "llm",
                            message=f"Terminated: {reason}",
                        )
                    process.kill()
                    await process.wait()
                    break

                # Check no activity timeout
                if (
                    policy.termination_policy.kill_on_no_activity
                    and time_since_activity > policy.timeout_policy.no_activity_timeout
                ):
                    logger.debug(
                        f"No activity for {time_since_activity:.1f}s "
                        f"(threshold: {policy.timeout_policy.no_activity_timeout}s)"
                    )
                    termination_reason = f"No activity for {time_since_activity:.0f} seconds"
                    if heartbeat_emitter:
                        from aurora_spawner.heartbeat import HeartbeatEventType

                        heartbeat_emitter.emit(
                            HeartbeatEventType.KILLED,
                            agent_id=task.agent or "llm",
                            message=f"Timeout: {termination_reason}",
                        )
                    process.kill()
                    await process.wait()
                    break

                # Check if timeout should be extended (progressive mode)
                if policy.timeout_policy.should_extend(
                    elapsed, time_since_activity, current_timeout
                ):
                    new_timeout = policy.timeout_policy.get_extended_timeout(current_timeout)
                    logger.debug(
                        f"Extending timeout: {current_timeout:.0f}s -> {new_timeout:.0f}s "
                        f"(activity detected: {time_since_activity:.1f}s ago)"
                    )
                    current_timeout = new_timeout
                    timeout_extended = True

                # Check absolute timeout
                if elapsed > current_timeout:
                    logger.debug(f"Process timeout after {current_timeout:.0f}s")
                    termination_reason = f"Process timed out after {current_timeout:.0f} seconds"
                    if heartbeat_emitter:
                        from aurora_spawner.heartbeat import HeartbeatEventType

                        heartbeat_emitter.emit(
                            HeartbeatEventType.KILLED,
                            agent_id=task.agent or "llm",
                            message=termination_reason,
                        )
                    process.kill()
                    await process.wait()
                    break

                # Sleep for activity check interval
                await asyncio.sleep(policy.timeout_policy.activity_check_interval)

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
        execution_time = time.time() - start_time

        # Invoke callback for output if provided
        if on_output and stdout_text:
            for line in stdout_text.splitlines():
                on_output(line)

        # Determine success
        if termination_reason:
            if heartbeat_emitter:
                from aurora_spawner.heartbeat import HeartbeatEventType

                heartbeat_emitter.emit(
                    HeartbeatEventType.FAILED,
                    agent_id=task.agent or "llm",
                    message=termination_reason,
                )

            # Determine failure reason for health monitoring
            failure_reason = FailureReason.UNKNOWN
            if "timed out" in termination_reason.lower():
                failure_reason = FailureReason.TIMEOUT
            elif "no activity" in termination_reason.lower():
                failure_reason = FailureReason.NO_ACTIVITY
            elif "error pattern" in termination_reason.lower():
                failure_reason = FailureReason.ERROR_PATTERN
            elif "killed" in termination_reason.lower():
                failure_reason = FailureReason.KILLED

            # Record failure with detection latency
            health_monitor.record_execution_failure(
                task_id=task_id,
                agent_id=agent_id,
                reason=failure_reason,
                error_message=termination_reason,
                metadata={
                    "detection_time": execution_time,
                    "timeout_extended": timeout_extended,
                    "policy": policy.name,
                },
            )

            return SpawnResult(
                success=False,
                output=stdout_text,
                error=termination_reason,
                exit_code=-1,
                termination_reason=termination_reason,
                timeout_extended=timeout_extended,
                execution_time=execution_time,
            )

        success = process.returncode == 0
        if heartbeat_emitter:
            from aurora_spawner.heartbeat import HeartbeatEventType

            if success:
                heartbeat_emitter.emit(
                    HeartbeatEventType.COMPLETED,
                    agent_id=task.agent or "llm",
                    message=f"Completed in {execution_time:.1f}s",
                )
            else:
                heartbeat_emitter.emit(
                    HeartbeatEventType.FAILED,
                    agent_id=task.agent or "llm",
                    message=f"Exit code: {process.returncode}",
                )

        # Record execution outcome for health monitoring
        if success:
            health_monitor.record_execution_success(
                task_id=task_id, agent_id=agent_id, output_size=len(stdout_text.encode())
            )
        else:
            health_monitor.record_execution_failure(
                task_id=task_id,
                agent_id=agent_id,
                reason=FailureReason.CRASH,
                error_message=stderr_text,
                metadata={
                    "exit_code": process.returncode,
                    "execution_time": execution_time,
                },
            )

        return SpawnResult(
            success=success,
            output=stdout_text,
            error=stderr_text if not success else None,
            exit_code=process.returncode or 0,
            timeout_extended=timeout_extended,
            execution_time=execution_time,
        )

    except Exception as e:
        logger.debug(f"Spawn exception: {e}")
        execution_time = time.time() - start_time

        # Record exception failure
        health_monitor.record_execution_failure(
            task_id=task_id,
            agent_id=agent_id,
            reason=FailureReason.CRASH,
            error_message=str(e),
            metadata={"exception_type": type(e).__name__},
        )

        return SpawnResult(
            success=False,
            execution_time=execution_time,
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
    max_retries: int | None = None,
    fallback_to_llm: bool = True,
    circuit_breaker: Any = None,
    policy: SpawnPolicy | None = None,
    **kwargs: Any,
) -> SpawnResult:
    """Spawn subprocess with automatic retry, circuit breaker, and fallback to LLM.

    Features:
    1. Circuit breaker: Skip known-failing agents immediately
    2. Early failure detection: Kill on error patterns
    3. Progressive timeout: Fail fast if no activity
    4. Retry with backoff: Handle transient failures with configurable strategy
    5. Fallback: Use direct LLM if agent fails

    Args:
        task: The task to execute. If task.agent is None, goes directly to LLM.
        on_progress: Optional callback(attempt, max_attempts, status)
        max_retries: Maximum number of retries after initial attempt (overrides policy if provided)
        fallback_to_llm: Whether to fallback to LLM after all retries fail (default: True)
        circuit_breaker: Optional CircuitBreaker instance (uses singleton if None)
        policy: Optional spawn policy (uses task.policy_name or default if None)
        **kwargs: Additional arguments passed to spawn()

    Returns:
        SpawnResult with retry/fallback metadata
    """
    import asyncio

    from aurora_spawner.circuit_breaker import get_circuit_breaker

    # Get circuit breaker
    cb = circuit_breaker or get_circuit_breaker()
    agent_id = task.agent or "llm"

    # Resolve policy
    if policy is None:
        if task.policy_name:
            policy = SpawnPolicy.from_name(task.policy_name)
        else:
            policy = SpawnPolicy.default()

    # Override max_retries if provided
    effective_max_retries = (
        max_retries if max_retries is not None else (policy.retry_policy.max_attempts - 1)
    )

    # Check circuit breaker before attempting
    if task.agent and policy.retry_policy.circuit_breaker_enabled:
        should_skip, skip_reason = cb.should_skip(agent_id)
        if should_skip:
            logger.debug(f"Circuit breaker: skipping agent '{agent_id}' - {skip_reason}")

            # Record circuit open event
            health_monitor = get_health_monitor()
            health_monitor.record_circuit_open(agent_id, skip_reason)
            if fallback_to_llm:
                # Go directly to fallback
                if on_progress:
                    on_progress(1, 1, "Circuit open, fallback to LLM")
                fallback_task = SpawnTask(
                    prompt=task.prompt,
                    agent=None,
                    timeout=task.timeout,
                    policy_name=task.policy_name,
                )
                result = await spawn(fallback_task, policy=policy, **kwargs)
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

    max_agent_attempts = effective_max_retries + 1  # Initial attempt + retries
    max_total_attempts = max_agent_attempts + (1 if fallback_to_llm else 0)

    # Attempt agent execution with retries and backoff
    last_result = None
    for attempt in range(max_agent_attempts):
        attempt_num = attempt + 1
        logger.debug(f"Spawn attempt {attempt_num}/{max_agent_attempts} for agent={agent_id}")

        # Check circuit breaker before each attempt (not just first)
        if task.agent and attempt > 0 and policy.retry_policy.circuit_breaker_enabled:
            should_skip, skip_reason = cb.should_skip(agent_id)
            if should_skip:
                logger.debug("Circuit opened mid-retry, skipping to fallback")
                break  # Exit retry loop, go to fallback

        # Apply retry delay with backoff and jitter
        if attempt > 0:
            delay = policy.retry_policy.get_delay(attempt - 1)
            if delay > 0:
                logger.debug(f"Retry delay: {delay:.2f}s")
                if on_progress:
                    on_progress(
                        attempt_num, max_total_attempts, f"Waiting {delay:.1f}s before retry"
                    )
                await asyncio.sleep(delay)

        if on_progress and attempt > 0:
            on_progress(attempt_num, max_total_attempts, "Retrying")

        result = await spawn(task, policy=policy, **kwargs)
        last_result = result

        if result.success:
            logger.debug(f"Spawn succeeded on attempt {attempt_num}")
            result.retry_count = attempt
            result.fallback = False
            # Record success with circuit breaker
            if task.agent and policy.retry_policy.circuit_breaker_enabled:
                cb.record_success(agent_id)
                # Record circuit close if this was a recovery
                if attempt > 0:
                    health_monitor = get_health_monitor()
                    health_monitor.record_circuit_close(agent_id)
                    health_monitor.record_recovery(
                        task_id=f"task_{id(task)}",
                        agent_id=agent_id,
                        recovery_time=result.execution_time,
                    )
            return result

        # Determine error type for retry decision
        error_type = None
        if result.termination_reason:
            if "timed out" in result.termination_reason.lower():
                error_type = "timeout"
            elif "error pattern" in result.termination_reason.lower():
                error_type = "error_pattern"

        # Check if should retry
        should_retry, retry_reason = policy.retry_policy.should_retry(attempt, error_type)
        if not should_retry:
            logger.debug(f"Not retrying: {retry_reason}")
            # Record failure with circuit breaker
            if task.agent and policy.retry_policy.circuit_breaker_enabled:
                cb.record_failure(agent_id)
            break

        # Record failure PER ATTEMPT for faster circuit opening
        if task.agent and policy.retry_policy.circuit_breaker_enabled:
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
            policy_name=task.policy_name,
        )

        result = await spawn(fallback_task, policy=policy, **kwargs)
        result.fallback = True
        result.original_agent = task.agent
        result.retry_count = max_agent_attempts

        if result.success:
            logger.debug("Fallback to LLM succeeded")
        else:
            logger.debug(f"Fallback to LLM also failed: {result.error}")

        return result

    # No fallback - return last failure
    if last_result:
        last_result.retry_count = max_agent_attempts
        last_result.fallback = False
        return last_result

    # Shouldn't reach here, but handle gracefully
    return SpawnResult(
        success=False,
        output="",
        error="No attempts completed",
        exit_code=-1,
        retry_count=max_agent_attempts,
        fallback=False,
    )
