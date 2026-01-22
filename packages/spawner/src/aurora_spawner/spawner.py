"""Spawner functions for aurora-spawner package.

Features:
- Error pattern detection: Kill process immediately on API/connection errors
- Progressive timeout: 60s initial, extend to 300s if stdout activity detected
- Circuit breaker: Skip known-failing agents after threshold failures
- Configurable timeout policies with adaptive extension
- Retry policies with exponential backoff and jitter
- Non-blocking early detection: Detect failures before timeout
"""

import asyncio
import logging
import os
import shutil
import time
from typing import Any, Callable

from aurora_spawner.early_detection import get_early_detection_monitor
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

    # Build command: [tool, "-p"]
    # Note: Don't pass --model to claude CLI - it generates invalid Bedrock model IDs
    # for aliases like "sonnet". Let the CLI use its default config instead.
    cmd = [resolved_tool, "-p"]

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

    # Start early detection monitoring
    early_monitor = get_early_detection_monitor()
    await early_monitor.start_monitoring()
    await early_monitor.register_execution(task_id, agent_id)

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

        # Write prompt to stdin and close
        if process.stdin:
            process.stdin.write(task.prompt.encode())
            process.stdin.write(b"\n")  # Ensure newline at end
            await process.stdin.drain()
            process.stdin.close()  # Close stdin to signal EOF
            await process.stdin.wait_closed()  # Wait for close to complete

        # Track errors from stderr
        stdout_chunks: list[bytes] = []
        stderr_chunks: list[bytes] = []
        termination_reason: str | None = None

        # Initialize timeout based on policy
        current_timeout = policy.timeout_policy.get_initial_timeout()
        last_activity_time = time.time()

        logger.debug(
            f"Spawn started: agent={agent_id}, timeout={current_timeout:.0f}s/{policy.timeout_policy.max_timeout:.0f}s",
        )

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

                    stdout_size = sum(len(c) for c in stdout_chunks)

                    # Update proactive health monitor with activity
                    health_monitor.update_execution_activity(task_id, stdout_size=stdout_size)

                    # Update early detection monitor with activity
                    await early_monitor.update_activity(task_id, stdout_size=stdout_size)

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

                    stderr_size = sum(len(c) for c in stderr_chunks)

                    # Update proactive health monitor with activity
                    health_monitor.update_execution_activity(task_id, stderr_size=stderr_size)

                    # Update early detection monitor with activity
                    await early_monitor.update_activity(task_id, stderr_size=stderr_size)

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
            while process.returncode is None:
                now = time.time()
                elapsed = now - start_time
                time_since_activity = now - last_activity_time

                # Check early detection monitor for non-blocking termination
                should_terminate_early, early_reason = await early_monitor.should_terminate(task_id)
                if should_terminate_early:
                    logger.debug(f"Early detection triggered termination: {early_reason}")
                    termination_reason = f"Early detection: {early_reason}"
                    if heartbeat_emitter:
                        from aurora_spawner.heartbeat import HeartbeatEventType

                        heartbeat_emitter.emit(
                            HeartbeatEventType.KILLED,
                            agent_id=task.agent or "llm",
                            message=f"Early detection: {early_reason}",
                        )
                    process.kill()
                    await process.wait()
                    break

                # Check proactive health monitor for early termination
                should_terminate_health, health_reason = health_monitor.should_terminate(task_id)
                if should_terminate_health:
                    logger.debug(f"Proactive health check triggered termination: {health_reason}")
                    termination_reason = f"Proactive health check: {health_reason}"
                    if heartbeat_emitter:
                        from aurora_spawner.heartbeat import HeartbeatEventType

                        heartbeat_emitter.emit(
                            HeartbeatEventType.KILLED,
                            agent_id=task.agent or "llm",
                            message=f"Health check terminated: {health_reason}",
                        )
                    process.kill()
                    await process.wait()
                    break

                # Get current stdout/stderr for termination checks
                stdout_so_far = b"".join(stdout_chunks).decode(errors="ignore")
                stderr_so_far = b"".join(stderr_chunks).decode(errors="ignore")

                # Check early termination conditions
                should_terminate, reason = policy.termination_policy.should_terminate(
                    stdout_so_far,
                    stderr_so_far,
                    elapsed,
                    time_since_activity,
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
                        f"(threshold: {policy.timeout_policy.no_activity_timeout}s)",
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
                    elapsed,
                    time_since_activity,
                    current_timeout,
                ):
                    new_timeout = policy.timeout_policy.get_extended_timeout(current_timeout)
                    logger.debug(
                        f"Extending timeout: {current_timeout:.0f}s -> {new_timeout:.0f}s "
                        f"(activity detected: {time_since_activity:.1f}s ago)",
                    )
                    current_timeout = new_timeout
                    timeout_extended = True

                # Check absolute timeout
                if elapsed > current_timeout:
                    logger.info(
                        f"Spawn timeout triggered: elapsed={elapsed:.0f}s > current_timeout={current_timeout:.0f}s",
                    )
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
            # Kill process if still running (handles external cancellation from global timeout)
            if process.returncode is None:
                process.kill()
                try:
                    await process.wait()
                except Exception:
                    pass

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
                task_id=task_id,
                agent_id=agent_id,
                output_size=len(stdout_text.encode()),
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
                agent_id = task.display_name or task.agent or "llm"
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


async def spawn_parallel_with_recovery(
    tasks: list[SpawnTask],
    max_concurrent: int = 5,
    max_retries: int | None = None,
    fallback_to_llm: bool | None = None,
    recovery_policy: Any | None = None,
    on_progress: Callable[[int, int, str, str], None] | None = None,
    on_recovery: Callable[[int, str, int, bool], None] | None = None,
    **kwargs: Any,
) -> list[SpawnResult]:
    """Spawn subprocesses in parallel with automatic recovery on failure.

    Simple agent recovery that retries failed tasks with exponential backoff
    and optionally falls back to direct LLM if agent fails.

    Args:
        tasks: List of tasks to execute in parallel
        max_concurrent: Maximum number of concurrent tasks (default: 5)
        max_retries: Maximum retry attempts per task (default: from recovery_policy or 2)
        fallback_to_llm: Fall back to direct LLM if agent fails (default: from recovery_policy or True)
        recovery_policy: RecoveryPolicy instance for fine-grained control (overrides max_retries/fallback_to_llm)
        on_progress: Optional callback(idx, total, agent_id, status)
        on_recovery: Optional callback(idx, agent_id, retry_count, used_fallback)
        **kwargs: Additional arguments passed to spawn()

    Returns:
        List of SpawnResults in input order with recovery metadata

    Example - Simple usage:
        >>> results = await spawn_parallel_with_recovery(
        ...     tasks=[SpawnTask(prompt="task1", agent="coder"), ...],
        ...     max_retries=2,
        ...     fallback_to_llm=True,
        ... )

    Example - Using RecoveryPolicy:
        >>> from aurora_spawner.recovery import RecoveryPolicy
        >>> policy = RecoveryPolicy.patient()
        >>> results = await spawn_parallel_with_recovery(
        ...     tasks=tasks,
        ...     recovery_policy=policy,
        ... )

    Example - Per-agent overrides:
        >>> policy = RecoveryPolicy.default().with_override("slow-agent", max_retries=5)
        >>> results = await spawn_parallel_with_recovery(tasks=tasks, recovery_policy=policy)

    """
    if not tasks:
        return []

    # Resolve recovery configuration
    from aurora_spawner.recovery import RecoveryPolicy as RP

    if recovery_policy is None:
        recovery_policy = RP.default()
    elif isinstance(recovery_policy, str):
        recovery_policy = RP.from_name(recovery_policy)

    semaphore = asyncio.Semaphore(max_concurrent)
    total = len(tasks)

    async def spawn_with_recovery(idx: int, task: SpawnTask) -> SpawnResult:
        """Spawn single task with recovery using existing retry infrastructure."""
        async with semaphore:
            agent_id = task.display_name or task.agent or "llm"

            # Get agent-specific policy
            agent_policy = recovery_policy.get_for_agent(agent_id)
            task_max_retries = max_retries if max_retries is not None else agent_policy.max_retries
            task_fallback = (
                fallback_to_llm if fallback_to_llm is not None else agent_policy.fallback_to_llm
            )

            if on_progress:
                on_progress(idx + 1, total, agent_id, "Starting")

            start_time = time.time()

            # Use existing retry+fallback mechanism
            result = await spawn_with_retry_and_fallback(
                task,
                max_retries=task_max_retries,
                fallback_to_llm=task_fallback,
                **kwargs,
            )

            elapsed = time.time() - start_time

            # Invoke policy callbacks
            if result.retry_count > 0 and agent_policy.on_retry:
                agent_policy.on_retry(agent_id, result.retry_count, result.error or "")
            if result.fallback and agent_policy.on_fallback:
                agent_policy.on_fallback(agent_id, result.error or "")
            if not result.success and agent_policy.on_recovery_failed:
                agent_policy.on_recovery_failed(agent_id, result.error or "")

            # Notify recovery if retries or fallback occurred
            if on_recovery and (result.retry_count > 0 or result.fallback):
                on_recovery(idx + 1, agent_id, result.retry_count, result.fallback)

            # Progress callback with status
            if on_progress:
                status = f"Completed ({elapsed:.1f}s)"
                if result.retry_count > 0:
                    status = f"Recovered after {result.retry_count} retries ({elapsed:.1f}s)"
                if result.fallback:
                    status = f"Fallback to LLM ({elapsed:.1f}s)"
                if not result.success:
                    status = f"Failed ({elapsed:.1f}s)"
                on_progress(idx + 1, total, agent_id, status)

            return result

    coros = [spawn_with_recovery(idx, task) for idx, task in enumerate(tasks)]
    results = await asyncio.gather(*coros, return_exceptions=False)

    return list(results)


async def spawn_parallel_with_state_tracking(
    tasks: list[SpawnTask],
    max_concurrent: int = 5,
    recovery_policy: Any | None = None,
    on_state_change: Callable[[str, str, str, str], None] | None = None,
    **kwargs: Any,
) -> tuple[list[SpawnResult], dict[str, Any]]:
    """Spawn subprocesses in parallel with full state machine tracking.

    Enhanced version of spawn_parallel_with_recovery that provides detailed
    state tracking for each task through a simple state machine. Useful for
    debugging, observability, and understanding recovery behavior.

    Args:
        tasks: List of tasks to execute in parallel
        max_concurrent: Maximum number of concurrent tasks (default: 5)
        recovery_policy: RecoveryPolicy instance for fine-grained control
        on_state_change: Optional callback(task_id, agent_id, from_state, to_state)
        **kwargs: Additional arguments passed to spawn()

    Returns:
        Tuple of (results list, state machine summary dict)

    State Machine Flow:
        INITIAL -> EXECUTING -> SUCCEEDED (happy path)
        INITIAL -> EXECUTING -> RETRY_PENDING -> RETRYING -> SUCCEEDED (with retry)
        INITIAL -> EXECUTING -> FALLBACK_PENDING -> FALLBACK_EXECUTING -> SUCCEEDED (with fallback)
        INITIAL -> CIRCUIT_OPEN -> FALLBACK_EXECUTING -> SUCCEEDED (circuit breaker bypass)

    Example:
        >>> from aurora_spawner import spawn_parallel_with_state_tracking, SpawnTask, RecoveryPolicy
        >>> tasks = [SpawnTask(prompt="task1", agent="coder"), ...]
        >>> results, summary = await spawn_parallel_with_state_tracking(
        ...     tasks,
        ...     recovery_policy=RecoveryPolicy.patient(),
        ...     on_state_change=lambda tid, aid, f, t: print(f"{aid}: {f} -> {t}"),
        ... )
        >>> print(f"Recovered: {summary['recovered']}, Failed: {summary['failed']}")

    """
    if not tasks:
        return [], {"total_tasks": 0}

    from aurora_spawner.recovery import RecoveryPolicy as RP
    from aurora_spawner.recovery import RecoveryState, RecoveryStateMachine

    if recovery_policy is None:
        recovery_policy = RP.default()
    elif isinstance(recovery_policy, str):
        recovery_policy = RP.from_name(recovery_policy)

    # Create state machine
    state_machine = RecoveryStateMachine(policy=recovery_policy)

    semaphore = asyncio.Semaphore(max_concurrent)

    async def spawn_with_state_tracking(idx: int, task: SpawnTask) -> SpawnResult:
        """Spawn single task with state machine tracking."""
        async with semaphore:
            task_id = f"task-{idx}"
            agent_id = task.display_name or task.agent or "llm"

            # Create task state
            task_state = state_machine.create_task_state(task_id, agent_id)

            def emit_state_change(from_state: str, to_state: str) -> None:
                if on_state_change:
                    on_state_change(task_id, agent_id, from_state, to_state)

            # Check circuit breaker first
            if task.agent:
                should_skip, skip_reason = state_machine.check_circuit_breaker(task_id, agent_id)
                if should_skip:
                    old_state = task_state.state.value
                    task_state.circuit_open()
                    emit_state_change(old_state, task_state.state.value)

                    if task_state.state == RecoveryState.CIRCUIT_OPEN:
                        # Go to fallback
                        old_state = task_state.state.value
                        task_state.start_fallback()
                        emit_state_change(old_state, task_state.state.value)

                        fallback_task = SpawnTask(
                            prompt=task.prompt,
                            agent=None,
                            timeout=task.timeout,
                            policy_name=task.policy_name,
                        )
                        result = await spawn(fallback_task, **kwargs)
                        result.fallback = True
                        result.original_agent = task.agent
                        result.retry_count = 0

                        old_state = task_state.state.value
                        if result.success:
                            task_state.succeed()
                        else:
                            task_state.transition(RecoveryState.FAILED, reason="fallback_failed")
                        emit_state_change(old_state, task_state.state.value)

                        return result
                    # No fallback, just failed
                    return SpawnResult(
                        success=False,
                        output="",
                        error=skip_reason,
                        exit_code=-1,
                        retry_count=0,
                    )

            # Start execution
            old_state = task_state.state.value
            task_state.start()
            emit_state_change(old_state, task_state.state.value)

            # Execute with state machine driven retry loop
            while not task_state.is_terminal:
                current_task = task

                # Check if we're in fallback mode
                if task_state.state == RecoveryState.FALLBACK_EXECUTING:
                    current_task = SpawnTask(
                        prompt=task.prompt,
                        agent=None,
                        timeout=task.timeout,
                        policy_name=task.policy_name,
                    )

                result = await spawn(current_task, **kwargs)

                if result.success:
                    old_state = task_state.state.value
                    task_state.succeed()
                    emit_state_change(old_state, task_state.state.value)

                    if task.agent:
                        state_machine.record_success(agent_id)

                    result.retry_count = task_state.attempt
                    result.fallback = task_state.used_fallback
                    if task_state.used_fallback:
                        result.original_agent = task.agent
                    return result

                # Handle failure
                old_state = task_state.state.value
                task_state.fail(result.error)
                emit_state_change(old_state, task_state.state.value)

                if task.agent:
                    state_machine.record_failure(agent_id)

                # Transition based on new state
                if task_state.state == RecoveryState.RETRY_PENDING:
                    # Calculate delay
                    delay = recovery_policy.get_delay(task_state.attempt - 1)
                    if delay > 0:
                        await asyncio.sleep(delay)

                    old_state = task_state.state.value
                    task_state.start_retry()
                    emit_state_change(old_state, task_state.state.value)

                elif task_state.state == RecoveryState.FALLBACK_PENDING:
                    old_state = task_state.state.value
                    task_state.start_fallback()
                    emit_state_change(old_state, task_state.state.value)

            # Terminal state - return final result
            return SpawnResult(
                success=task_state.state == RecoveryState.SUCCEEDED,
                output=result.output if result else "",
                error=task_state.last_error,
                exit_code=result.exit_code if result else -1,
                retry_count=task_state.attempt,
                fallback=task_state.used_fallback,
                original_agent=task.agent if task_state.used_fallback else None,
            )

    coros = [spawn_with_state_tracking(idx, task) for idx, task in enumerate(tasks)]
    results = await asyncio.gather(*coros, return_exceptions=False)

    return list(results), state_machine.get_summary()


async def spawn_sequential(
    tasks: list[SpawnTask],
    pass_context: bool = True,
    stop_on_failure: bool = False,
    **kwargs: Any,
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


async def spawn_parallel_tracked(
    tasks: list[SpawnTask],
    max_concurrent: int = 4,
    stagger_delay: float = 5.0,
    policy_name: str = "patient",
    on_progress: Callable[[str], None] | None = None,
    enable_heartbeat: bool = True,
    global_timeout_buffer: float = 120.0,
    fallback_to_llm: bool = True,
    max_retries: int = 2,
    **kwargs: Any,
) -> tuple[list[SpawnResult], dict[str, Any]]:
    """Spawn subprocesses in parallel with full tracking, staggering, and heartbeat.

    This is the mature spawning pattern used by both SOAR's collect phase and aur spawn.
    Single source of truth for advanced parallel spawning.

    Features:
    - Stagger delays between agent starts to avoid API burst limits
    - Per-task heartbeat monitoring for health tracking
    - Global timeout calculation based on waves and policy
    - Progress callbacks for visibility
    - Circuit breaker pre-checks for fast-fail
    - Retry with exponential backoff + LLM fallback
    - Execution metadata collection

    Args:
        tasks: List of SpawnTask to execute in parallel
        max_concurrent: Maximum concurrent agents (default: 4)
        stagger_delay: Delay between agent starts in seconds (default: 5.0)
        policy_name: Spawn policy preset name (default: "patient")
        on_progress: Optional callback for progress messages
        enable_heartbeat: Enable per-task heartbeat monitoring (default: True)
        global_timeout_buffer: Additional buffer for global timeout (default: 120s)
        fallback_to_llm: Fall back to LLM if agent fails (default: True)
        max_retries: Maximum retries per task (default: 2)
        **kwargs: Additional arguments passed to spawn()

    Returns:
        Tuple of (results list, execution metadata dict)

    Metadata includes:
        - total_duration_ms: Total execution time
        - early_terminations: List of early termination events
        - fallback_count: Number of LLM fallbacks used
        - retried_tasks: Tasks that required retries
        - circuit_blocked: Agents blocked by circuit breaker pre-spawn
        - heartbeat_metrics: Per-task heartbeat summaries

    """
    import math

    from aurora_spawner.circuit_breaker import get_circuit_breaker
    from aurora_spawner.heartbeat import (
        HeartbeatEventType,
        HeartbeatMonitor,
        create_heartbeat_emitter,
    )

    if not tasks:
        return [], {"total_duration_ms": 0, "total_tasks": 0}

    start_time = time.time()
    total_tasks = len(tasks)
    circuit_breaker = get_circuit_breaker()

    # Execution metadata
    metadata: dict[str, Any] = {
        "total_tasks": total_tasks,
        "failed_tasks": 0,
        "fallback_count": 0,
        "early_terminations": [],
        "retried_tasks": [],
        "circuit_blocked": [],
        "heartbeat_metrics": [],
    }

    # Get policy for timeout calculation
    policy = SpawnPolicy.from_name(policy_name)
    policy_max_timeout = policy.timeout_policy.max_timeout

    # Calculate global timeout
    # Must accommodate: waves * max_timeout + stagger + buffer
    stagger_delay_total = (total_tasks - 1) * stagger_delay
    num_waves = math.ceil(total_tasks / max_concurrent) if total_tasks > 0 else 1
    global_timeout = (num_waves * policy_max_timeout) + stagger_delay_total + global_timeout_buffer

    logger.info(
        f"spawn_parallel_tracked: tasks={total_tasks}, waves={num_waves}, "
        f"max_concurrent={max_concurrent}, policy={policy_name}, "
        f"global_timeout={global_timeout:.0f}s",
    )

    # Track progress
    completed_count = 0
    results: list[SpawnResult | None] = [None] * total_tasks  # Preserve order

    async def tracked_spawn(idx: int, task: SpawnTask) -> SpawnResult:
        """Spawn single task with stagger, heartbeat, and tracking."""
        nonlocal completed_count

        agent_id = task.display_name or task.agent or "llm"
        task_id = f"tracked_{idx}_{agent_id}"

        # Stagger delay to avoid API burst
        task_stagger = idx * stagger_delay
        if task_stagger > 0:
            if on_progress:
                on_progress(
                    f"  Task {idx + 1}/{total_tasks} ({agent_id}) starting in {task_stagger:.0f}s...",
                )
            await asyncio.sleep(task_stagger)

        if on_progress:
            on_progress(f"  Task {idx + 1}/{total_tasks} ({agent_id}) starting now")

        task_start = time.time()

        # Circuit breaker pre-check (skip for direct LLM)
        if task.agent:
            should_skip, skip_reason = circuit_breaker.should_skip(agent_id)
            if should_skip:
                logger.warning(f"Circuit breaker: skipping '{agent_id}' - {skip_reason}")
                metadata["circuit_blocked"].append(
                    {
                        "agent_id": agent_id,
                        "task_index": idx,
                        "reason": skip_reason,
                    },
                )

                if fallback_to_llm:
                    # Replace with LLM fallback
                    task = SpawnTask(
                        prompt=task.prompt,
                        agent=None,
                        timeout=task.timeout,
                        policy_name=task.policy_name,
                    )
                    metadata["fallback_count"] += 1
                else:
                    # Return failure immediately
                    return SpawnResult(
                        success=False,
                        output="",
                        error=f"Circuit breaker open: {skip_reason}",
                        exit_code=-1,
                    )

        # Setup heartbeat if enabled
        heartbeat = None
        if enable_heartbeat:
            heartbeat = create_heartbeat_emitter(task_id)
            monitor = HeartbeatMonitor(
                emitter=heartbeat,
                total_timeout=int(policy_max_timeout),
                activity_timeout=int(policy_max_timeout * 0.4),
                warning_threshold=0.8,
            )
            _ = monitor  # Available for external health checks

            # Subscribe to timeout warnings
            def on_warning(event):
                if event.event_type == HeartbeatEventType.TIMEOUT_WARNING and on_progress:
                    on_progress(
                        f"  [{completed_count}/{total_tasks}] {agent_id}: approaching timeout",
                    )

            heartbeat.subscribe(on_warning)

        try:
            # Progress callback for retries
            def retry_progress(attempt: int, max_attempts: int, status: str):
                if on_progress and attempt > 1:
                    on_progress(f"    [{agent_id}] Retry {attempt}/{max_attempts}: {status}")

            # Spawn with retry and fallback
            result = await spawn_with_retry_and_fallback(
                task,
                on_progress=retry_progress,
                max_retries=max_retries,
                fallback_to_llm=fallback_to_llm,
                heartbeat_emitter=heartbeat,
                policy=policy,
                **kwargs,
            )

            # Track completion
            completed_count += 1
            duration_ms = int((time.time() - task_start) * 1000)

            # Progress update
            if on_progress:
                used_fallback = getattr(result, "fallback", False)
                if result.success:
                    status = f"{agent_id} done" + (" (fallback)" if used_fallback else "")
                else:
                    status = f"{agent_id} failed"
                on_progress(f"  [{completed_count}/{total_tasks} done] {status}")

            # Track early termination
            if hasattr(result, "termination_reason") and result.termination_reason:
                metadata["early_terminations"].append(
                    {
                        "agent_id": agent_id,
                        "task_index": idx,
                        "reason": result.termination_reason,
                        "detection_time_ms": duration_ms,
                    },
                )

            # Track fallback usage
            if getattr(result, "fallback", False):
                metadata["fallback_count"] += 1

            # Track retries
            retry_count = getattr(result, "retry_count", 0)
            if retry_count > 0:
                metadata["retried_tasks"].append(
                    {
                        "agent_id": agent_id,
                        "task_index": idx,
                        "retries": retry_count,
                    },
                )

            # Track failure
            if not result.success:
                metadata["failed_tasks"] += 1

            # Collect heartbeat metrics
            if heartbeat:
                metadata["heartbeat_metrics"].append(
                    {
                        "task_index": idx,
                        "agent_id": agent_id,
                        "event_count": len(heartbeat.get_all_events()),
                        "elapsed_s": heartbeat.seconds_since_start(),
                        "idle_s": heartbeat.seconds_since_activity(),
                    },
                )

            return result

        except Exception as e:
            completed_count += 1
            metadata["failed_tasks"] += 1
            logger.error(f"Task {idx} ({agent_id}) failed: {e}")

            if on_progress:
                on_progress(
                    f"  [{completed_count}/{total_tasks} done] {agent_id} error: {str(e)[:50]}",
                )

            return SpawnResult(
                success=False,
                output="",
                error=str(e),
                exit_code=-1,
            )

    # Concurrency semaphore
    semaphore = asyncio.Semaphore(max_concurrent)

    async def rate_limited_spawn(idx: int, task: SpawnTask) -> SpawnResult:
        """Spawn with concurrency limiting."""
        async with semaphore:
            result = await tracked_spawn(idx, task)
            results[idx] = result  # Store in order
            return result

    # Create all tasks
    spawn_tasks = [asyncio.create_task(rate_limited_spawn(i, task)) for i, task in enumerate(tasks)]

    # Spinner for TTY - shows while tasks are running
    import sys

    show_spinner = sys.stdout.isatty()
    spinner_chars = "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"
    spinner_running = True

    async def spinner_task():
        """Show spinner while tasks are running."""
        spinner_idx = 0
        while spinner_running:
            if show_spinner and completed_count < total_tasks:
                active = total_tasks - completed_count
                elapsed = int(time.time() - start_time)
                spinner = spinner_chars[spinner_idx % len(spinner_chars)]
                sys.stdout.write(f"\r  {spinner} Working... {active} active ({elapsed}s)")
                sys.stdout.flush()
                spinner_idx += 1
            await asyncio.sleep(0.1)
        # Clear spinner line
        if show_spinner:
            sys.stdout.write("\r" + " " * 50 + "\r")
            sys.stdout.flush()

    spinner = asyncio.create_task(spinner_task()) if show_spinner else None

    # Wait with global timeout
    try:
        done, pending = await asyncio.wait(
            spawn_tasks,
            timeout=global_timeout,
            return_when=asyncio.ALL_COMPLETED,
        )

        # Handle timeout - cancel pending
        if pending:
            logger.warning(
                f"Global timeout ({global_timeout:.0f}s) hit, {len(pending)} tasks pending",
            )
            if on_progress:
                on_progress(f"  Timeout: {len(pending)} tasks cancelled, using partial results")

            for task in pending:
                task.cancel()
            await asyncio.gather(*pending, return_exceptions=True)

    except Exception as e:
        logger.error(f"spawn_parallel_tracked error: {e}")
        # Cancel all tasks
        for task in spawn_tasks:
            if not task.done():
                task.cancel()
        await asyncio.gather(*spawn_tasks, return_exceptions=True)

    finally:
        # Stop spinner
        spinner_running = False
        if spinner:
            await spinner

    # Build final results list (None for cancelled tasks)
    final_results = []
    for i, result in enumerate(results):
        if result is None:
            final_results.append(
                SpawnResult(
                    success=False,
                    output="",
                    error="Task cancelled (global timeout)",
                    exit_code=-1,
                ),
            )
            metadata["failed_tasks"] += 1
        else:
            final_results.append(result)

    # Finalize metadata
    metadata["total_duration_ms"] = int((time.time() - start_time) * 1000)

    logger.info(
        f"spawn_parallel_tracked complete: {total_tasks} tasks, "
        f"{metadata['failed_tasks']} failed, {metadata['fallback_count']} fallbacks, "
        f"{len(metadata['circuit_blocked'])} circuit blocked, "
        f"duration={metadata['total_duration_ms']}ms",
    )

    return final_results, metadata


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
                        attempt_num,
                        max_total_attempts,
                        f"Waiting {delay:.1f}s before retry",
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

        # Determine error type for retry decision and circuit breaker
        error_type = None
        failure_type = None  # For circuit breaker
        if result.termination_reason:
            reason_lower = result.termination_reason.lower()
            if "timed out" in reason_lower:
                error_type = "timeout"
                failure_type = "timeout"
            elif "error pattern" in reason_lower:
                error_type = "error_pattern"
                failure_type = "error_pattern"
            elif any(
                x in reason_lower
                for x in ["rate limit", "429", "quota exceeded", "too many requests"]
            ):
                error_type = "rate_limit"
                failure_type = "rate_limit"
            elif "inference" in reason_lower or "api" in reason_lower:
                error_type = "inference"
                failure_type = "inference"
            elif "crash" in reason_lower:
                failure_type = "crash"
        elif result.error:
            # Check error message - distinguish permanent vs transient errors
            error_lower = result.error.lower()

            # Rate limits - don't trigger circuit breaker (quota issue, not agent issue)
            if any(
                x in error_lower
                for x in ["rate limit", "429", "quota exceeded", "too many requests"]
            ):
                error_type = "rate_limit"
                failure_type = "rate_limit"

            # Permanent errors - should trigger fast-fail (config/agent broken)
            elif any(
                x in error_lower
                for x in ["unauthorized", "401", "invalid api key", "authentication failed"]
            ):
                error_type = "api_error"
                failure_type = "auth_error"
            elif any(x in error_lower for x in ["forbidden", "403", "insufficient permissions"]):
                error_type = "api_error"
                failure_type = "forbidden"
            elif any(
                x in error_lower
                for x in [
                    "invalid model",
                    "model identifier",
                    "model not found",
                    "model not available",
                ]
            ):
                error_type = "api_error"
                failure_type = "invalid_model"
            elif any(
                x in error_lower for x in ["400", "bad request", "invalid request", "malformed"]
            ):
                error_type = "api_error"
                failure_type = "invalid_request"
            elif any(x in error_lower for x in ["404", "not found", "endpoint not found"]):
                error_type = "api_error"
                failure_type = "not_found"

            # Transient errors - allow retries (temporary issues)
            elif any(
                x in error_lower
                for x in [
                    "500",
                    "502",
                    "503",
                    "504",
                    "internal server error",
                    "bad gateway",
                    "service unavailable",
                ]
            ):
                error_type = "api_error"
                failure_type = "transient_error"
            elif any(x in error_lower for x in ["connection", "econnreset", "network", "timeout"]):
                error_type = "api_error"
                failure_type = "transient_error"
            elif any(x in error_lower for x in ["json", "parse"]):
                error_type = "api_error"
                failure_type = "transient_error"

            # Generic API/inference errors - treat as transient unless proven permanent
            elif any(x in error_lower for x in ["api", "inference"]):
                failure_type = "inference"

        # Check if should retry
        should_retry, retry_reason = policy.retry_policy.should_retry(attempt, error_type)
        if not should_retry:
            logger.debug(f"Not retrying: {retry_reason}")
            # Record failure with circuit breaker including failure type
            if task.agent and policy.retry_policy.circuit_breaker_enabled:
                cb.record_failure(agent_id, failure_type=failure_type)
            break

        # Record failure PER ATTEMPT for faster circuit opening
        if task.agent and policy.retry_policy.circuit_breaker_enabled:
            cb.record_failure(agent_id, failure_type=failure_type)
        logger.debug(f"Spawn attempt {attempt_num} failed: {result.error}")

    # Try fallback if enabled
    if fallback_to_llm:
        if on_progress:
            on_progress(max_agent_attempts + 1, max_total_attempts, "Fallback to LLM")

        logger.debug(
            f"Agent '{agent_id}' failed after {max_agent_attempts} attempts, falling back to LLM",
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
