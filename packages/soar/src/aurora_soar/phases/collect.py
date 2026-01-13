"""Phase 6: Agent Execution.

This module implements the Collect phase of the SOAR pipeline, which executes
agents in parallel or sequentially based on dependencies.

Supports ad-hoc agent spawning when no suitable agent exists in the registry.
When an agent has config["is_spawn"]=True, the collect phase generates a spawn prompt
using AgentMatcher and executes it via LLM instead of invoking a registered agent.
"""

from __future__ import annotations

import asyncio
import logging
import sys
import time
from typing import TYPE_CHECKING, Any, Callable

from aurora_spawner import (
    SpawnResult,
    SpawnTask,
    spawn,
    spawn_parallel,
    spawn_with_retry_and_fallback,
)

if TYPE_CHECKING:
    from aurora_soar.agent_registry import AgentInfo

logger = logging.getLogger(__name__)


def _get_agent_matcher():
    """Lazy import of AgentMatcher to avoid circular imports."""
    try:
        from aurora_cli.planning.agents import AgentMatcher

        return AgentMatcher()
    except ImportError:
        logger.warning("AgentMatcher not available, ad-hoc spawning disabled")
        return None


__all__ = ["execute_agents", "CollectResult", "AgentOutput"]


# Default timeouts (in seconds)
DEFAULT_AGENT_TIMEOUT = 300  # 5 minutes per agent
DEFAULT_QUERY_TIMEOUT = 300  # 5 minutes overall

# Spinner characters
SPINNER_CHARS = "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"


async def _spawn_with_spinner(
    task: SpawnTask,
    progress_cb: Callable,
    agent_idx: int,
    total_agents: int,
    agent_id: str,
    on_progress: Callable | None,
) -> SpawnResult:
    """Run spawn_with_retry_and_fallback with a spinner on TTY."""
    show_spinner = sys.stdout.isatty()
    start_time = time.time()

    # Create the spawn task
    spawn_coro = spawn_with_retry_and_fallback(task, on_progress=progress_cb)

    if not show_spinner:
        # No spinner, just await
        return await spawn_coro

    # Run spawn in background, show spinner in foreground
    spawn_task = asyncio.create_task(spawn_coro)
    spinner_idx = 0

    while not spawn_task.done():
        elapsed = time.time() - start_time
        spinner = SPINNER_CHARS[spinner_idx % len(SPINNER_CHARS)]
        sys.stdout.write(
            f"\r[Agent {agent_idx}/{total_agents}] {agent_id}: {spinner} Working... ({elapsed:.0f}s)"
        )
        sys.stdout.flush()
        spinner_idx += 1
        await asyncio.sleep(0.1)

    # Clear spinner line
    sys.stdout.write("\r" + " " * 60 + "\r")
    sys.stdout.flush()

    return await spawn_task


class AgentOutput:
    """Output from a single agent execution.

    Attributes:
        subgoal_index: Index of the subgoal this output is for
        agent_id: ID of the agent that executed
        success: Whether execution succeeded
        summary: Natural language summary of what was done
        data: Structured data output (files modified, results, etc.)
        confidence: Agent's confidence in the output (0-1)
        execution_metadata: Metadata about execution (duration, tools used, etc.)
        error: Error message if execution failed
    """

    def __init__(
        self,
        subgoal_index: int,
        agent_id: str,
        success: bool,
        summary: str = "",
        data: dict[str, Any] | None = None,
        confidence: float = 0.0,
        execution_metadata: dict[str, Any] | None = None,
        error: str | None = None,
    ):
        self.subgoal_index = subgoal_index
        self.agent_id = agent_id
        self.success = success
        self.summary = summary
        self.data = data or {}
        self.confidence = confidence
        self.execution_metadata = execution_metadata or {}
        self.error = error

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "subgoal_index": self.subgoal_index,
            "agent_id": self.agent_id,
            "success": self.success,
            "summary": self.summary,
            "data": self.data,
            "confidence": self.confidence,
            "execution_metadata": self.execution_metadata,
            "error": self.error,
        }


class CollectResult:
    """Result of agent execution phase.

    Attributes:
        agent_outputs: List of AgentOutput objects for each executed subgoal
        execution_metadata: Overall execution metadata (total time, parallel speedup, etc.)
        user_interactions: List of user interactions during execution
        fallback_agents: List of agent IDs that used fallback to LLM
    """

    def __init__(
        self,
        agent_outputs: list[AgentOutput],
        execution_metadata: dict[str, Any],
        user_interactions: list[dict[str, Any]] | None = None,
        fallback_agents: list[str] | None = None,
    ):
        self.agent_outputs = agent_outputs
        self.execution_metadata = execution_metadata
        self.user_interactions = user_interactions or []
        self.fallback_agents = fallback_agents or []

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "agent_outputs": [output.to_dict() for output in self.agent_outputs],
            "execution_metadata": self.execution_metadata,
            "user_interactions": self.user_interactions,
            "fallback_agents": self.fallback_agents,
        }


async def execute_agents(
    agent_assignments: list[tuple[int, "AgentInfo"]],
    subgoals: list[dict[str, Any]],
    context: dict[str, Any],
    on_progress: Any = None,
    agent_timeout: float = DEFAULT_AGENT_TIMEOUT,
) -> CollectResult:
    """Execute agents with automatic retry and fallback to LLM.

    Simplified agent execution that:
    1. Takes agent assignments directly (no RouteResult)
    2. Uses spawn_with_retry_and_fallback for reliability
    3. Provides streaming progress updates via callback
    4. Tracks fallback metadata for monitoring
    5. Executes all subgoals in parallel (no complex phasing)

    Args:
        agent_assignments: List of (subgoal_index, AgentInfo) tuples
        subgoals: List of subgoal dictionaries from decomposition
        context: Retrieved context from earlier phases
        on_progress: Optional callback for progress updates: "[Agent X/Y] agent-id: Status"
        agent_timeout: Timeout per agent execution in seconds (default 300)

    Returns:
        CollectResult with all agent outputs and fallback metadata

    Raises:
        RuntimeError: If critical subgoal fails after all retries
    """
    start_time = time.time()
    agent_outputs: list[AgentOutput] = []
    fallback_agents: list[str] = []
    execution_metadata: dict[str, Any] = {
        "total_duration_ms": 0,
        "total_subgoals": len(agent_assignments),
        "failed_subgoals": 0,
        "fallback_count": 0,
    }

    # Build subgoal map for lookup
    # If subgoals don't have subgoal_index, use array index
    subgoal_map = {}
    for i, sg in enumerate(subgoals):
        idx = sg.get("subgoal_index", i)
        subgoal_map[idx] = sg

    # Build spawn tasks with progress wrapper
    total_agents = len(agent_assignments)
    agent_idx = 0

    # Get AgentMatcher for ad-hoc spawning (lazy load)
    agent_matcher = None

    for subgoal_idx, agent in agent_assignments:
        agent_idx += 1
        subgoal = subgoal_map.get(subgoal_idx, {})

        # Check if this is an ad-hoc spawn (marked in config)
        is_spawn = agent.config.get("is_spawn", False)

        if is_spawn:
            # Ad-hoc spawn: use spawn prompt from AgentMatcher
            if agent_matcher is None:
                agent_matcher = _get_agent_matcher()

            if agent_matcher:
                prompt = agent_matcher._create_spawn_prompt(
                    agent_name=agent.id,
                    agent_desc=getattr(agent, "description", ""),
                    task_description=subgoal.get("description", ""),
                )
            else:
                # Fallback: build a simple spawn prompt without AgentMatcher
                prompt = f"""For this specific request, act as a {agent.id} specialist - {getattr(agent, "description", "specialist agent")}.

Task: {subgoal.get("description", "")}

Please complete this task directly without additional questions or preamble. Provide the complete deliverable.

---

After your deliverable, suggest a formal agent specification for this capability."""

            logger.info(f"Ad-hoc spawning agent '{agent.id}' for subgoal {subgoal_idx}")
            logger.debug(f"Spawn prompt for {agent.id}:\n{prompt[:500]}...")
        else:
            # Regular agent: use standard prompt
            prompt = _build_agent_prompt(subgoal, context)

        # Create spawn task
        # For ad-hoc spawns, use None as agent (direct LLM call without agent persona)
        # For registered agents, use their agent.id
        spawn_agent = None if is_spawn else agent.id

        spawn_task = SpawnTask(
            prompt=prompt,
            agent=spawn_agent,
            timeout=int(agent_timeout),
        )

        # Progress callback wrapper
        def make_progress_callback(idx, total, agent_id):
            def progress_callback(attempt, max_attempts, status):
                if on_progress:
                    on_progress(f"[Agent {idx}/{total}] {agent_id}: {status}")

            return progress_callback

        progress_cb = make_progress_callback(agent_idx, total_agents, agent.id)

        # Call spawn_with_retry_and_fallback with spinner
        if on_progress:
            on_progress(f"[Agent {agent_idx}/{total_agents}] {agent.id}: Starting...")

        # Run spawn with concurrent spinner
        spawn_result = await _spawn_with_spinner(
            spawn_task,
            progress_cb,
            agent_idx,
            total_agents,
            agent.id,
            on_progress,
        )

        # Track fallback and spawn usage
        if spawn_result.fallback:
            fallback_agents.append(agent.id)
            execution_metadata["fallback_count"] += 1

        # Track ad-hoc spawned agents
        if is_spawn:
            if "spawned_agents" not in execution_metadata:
                execution_metadata["spawned_agents"] = []
            execution_metadata["spawned_agents"].append(agent.id)
            execution_metadata["spawn_count"] = execution_metadata.get("spawn_count", 0) + 1

        # Convert to AgentOutput
        duration_ms = int((time.time() - start_time) * 1000)

        if spawn_result.success:
            output = AgentOutput(
                subgoal_index=subgoal_idx,
                agent_id=agent.id,
                success=True,
                summary=spawn_result.output,
                confidence=0.85,
                execution_metadata={
                    "duration_ms": duration_ms,
                    "exit_code": spawn_result.exit_code,
                    "fallback": spawn_result.fallback,
                    "retry_count": spawn_result.retry_count,
                    "original_agent": spawn_result.original_agent,
                    "spawned": is_spawn,  # Track if this was an ad-hoc spawn
                },
            )
            if on_progress:
                elapsed = duration_ms / 1000
                on_progress(
                    f"[Agent {agent_idx}/{total_agents}] {agent.id}: Completed ({elapsed:.1f}s)"
                )
        else:
            # Handle failure
            output = AgentOutput(
                subgoal_index=subgoal_idx,
                agent_id=agent.id,
                success=False,
                summary="",
                confidence=0.0,
                error=spawn_result.error or "Agent execution failed",
                execution_metadata={
                    "duration_ms": duration_ms,
                    "exit_code": spawn_result.exit_code,
                    "fallback": spawn_result.fallback,
                    "retry_count": spawn_result.retry_count,
                    "spawned": is_spawn,  # Track if this was an ad-hoc spawn
                },
            )
            execution_metadata["failed_subgoals"] += 1

            if on_progress:
                on_progress(f"[Agent {agent_idx}/{total_agents}] {agent.id}: Failed")

            # Check if critical subgoal
            if subgoal.get("is_critical", False):
                raise RuntimeError(f"Critical subgoal {subgoal_idx} failed: {spawn_result.error}")

        agent_outputs.append(output)

    # Calculate final metadata
    execution_metadata["total_duration_ms"] = int((time.time() - start_time) * 1000)

    logger.info(
        f"Agent execution complete: {len(agent_outputs)} subgoals, "
        f"{execution_metadata['failed_subgoals']} failed, "
        f"{execution_metadata['fallback_count']} used fallback"
    )

    return CollectResult(
        agent_outputs=agent_outputs,
        execution_metadata=execution_metadata,
        user_interactions=[],
        fallback_agents=fallback_agents,
    )


async def _execute_parallel_subgoals(
    subgoals: list[dict[str, Any]],
    agent_map: dict[int, AgentInfo],
    context: dict[str, Any],
    timeout: float,
    metadata: dict[str, Any],
) -> list[AgentOutput]:
    """Execute subgoals in parallel using spawn_parallel().

    Args:
        subgoals: List of subgoal dictionaries with subgoal_index
        agent_map: Map of subgoal_index -> AgentInfo
        context: Context from Phase 2
        timeout: Timeout per agent in seconds
        metadata: Execution metadata to update

    Returns:
        List of AgentOutput objects in input order
    """
    logger.debug(f"Executing {len(subgoals)} subgoals in parallel with spawn_parallel()")

    start_time = time.time()

    # Build SpawnTask list for all subgoals
    spawn_tasks = []
    for subgoal in subgoals:
        idx = subgoal["subgoal_index"]
        agent = agent_map[idx]

        # Build agent prompt
        prompt = _build_agent_prompt(subgoal, context)

        # Create SpawnTask
        spawn_task = SpawnTask(
            prompt=prompt,
            agent=agent.id,
            timeout=int(timeout),
        )
        spawn_tasks.append(spawn_task)

    # Call spawn_parallel() with max_concurrent=5
    logger.info(f"Spawning {len(spawn_tasks)} agents in parallel (max_concurrent=5)")
    spawn_results = await spawn_parallel(spawn_tasks, max_concurrent=5)

    # Convert all SpawnResults to AgentOutputs
    agent_outputs = []
    for i, spawn_result in enumerate(spawn_results):
        subgoal = subgoals[i]
        idx = subgoal["subgoal_index"]
        agent = agent_map[idx]

        duration_ms = int((time.time() - start_time) * 1000)

        if spawn_result.success:
            output = AgentOutput(
                subgoal_index=idx,
                agent_id=agent.id,
                success=True,
                summary=spawn_result.output,
                confidence=0.85,  # Default confidence for successful spawner execution
                execution_metadata={
                    "duration_ms": duration_ms,
                    "exit_code": spawn_result.exit_code,
                    "spawner": True,
                    "parallel": True,
                },
            )
        else:
            # Handle partial failures gracefully
            output = AgentOutput(
                subgoal_index=idx,
                agent_id=agent.id,
                success=False,
                summary="",
                confidence=0.0,
                error=spawn_result.error or "Spawner execution failed",
                execution_metadata={
                    "duration_ms": duration_ms,
                    "exit_code": spawn_result.exit_code,
                    "spawner": True,
                    "parallel": True,
                },
            )
            metadata["failed_subgoals"] += 1
            logger.warning(f"Subgoal {idx} failed: {spawn_result.error}")

        agent_outputs.append(output)

    # Update execution metadata with parallel timing
    total_duration = int((time.time() - start_time) * 1000)
    logger.info(
        f"Parallel execution complete: {len(agent_outputs)} subgoals "
        f"in {total_duration}ms ({metadata['failed_subgoals']} failed)"
    )

    return agent_outputs


async def _execute_sequential_subgoals(
    subgoals: list[dict[str, Any]],
    agent_map: dict[int, AgentInfo],
    context: dict[str, Any],
    timeout: float,
    metadata: dict[str, Any],
) -> list[AgentOutput]:
    """Execute subgoals sequentially.

    Args:
        subgoals: List of subgoal dictionaries with subgoal_index
        agent_map: Map of subgoal_index -> AgentInfo
        context: Context from Phase 2
        timeout: Timeout per agent in seconds
        metadata: Execution metadata to update

    Returns:
        List of AgentOutput objects
    """
    logger.debug(f"Executing {len(subgoals)} subgoals sequentially")

    outputs = []
    for subgoal in subgoals:
        idx = subgoal["subgoal_index"]
        agent = agent_map[idx]

        try:
            output = await _execute_single_subgoal(idx, subgoal, agent, context, timeout, metadata)
            outputs.append(output)
        except Exception as e:
            logger.error(f"Subgoal {idx} failed: {e}")
            outputs.append(
                AgentOutput(
                    subgoal_index=idx,
                    agent_id=agent.id,
                    success=False,
                    error=str(e),
                )
            )
            metadata["failed_subgoals"] += 1

            # Check if this is a critical subgoal - abort if so
            if subgoal.get("is_critical", False):
                logger.error(f"Critical subgoal {idx} failed, aborting execution")
                raise RuntimeError(f"Critical subgoal {idx} failed: {e}")

    return outputs


async def _execute_single_subgoal(
    idx: int,
    subgoal: dict[str, Any],
    agent: AgentInfo,
    context: dict[str, Any],
    timeout: float,
    metadata: dict[str, Any],
    retry_count: int = 0,
    max_retries: int = 2,
) -> AgentOutput:
    """Execute a single subgoal with an agent, with retry logic.

    Args:
        idx: Subgoal index
        subgoal: Subgoal dictionary
        agent: AgentInfo for the assigned agent
        context: Context from Phase 2
        timeout: Timeout in seconds
        metadata: Execution metadata to update
        retry_count: Current retry attempt (0 = first attempt)
        max_retries: Maximum number of retries

    Returns:
        AgentOutput with execution results

    Raises:
        RuntimeError: If critical subgoal fails after all retries
    """
    logger.info(f"Executing subgoal {idx} with agent '{agent.id}' (attempt {retry_count + 1})")

    try:
        # Execute agent with timeout using spawner
        output = await asyncio.wait_for(
            _execute_agent(agent, subgoal, context, timeout),
            timeout=timeout,
        )

        # Validate output format
        _validate_agent_output(output)

        # Add retry count to metadata (duration_ms already set by _execute_agent)
        output.execution_metadata["retry_count"] = retry_count

        logger.info(
            f"Subgoal {idx} completed in {output.execution_metadata.get('duration_ms', 0)}ms "
            f"(confidence: {output.confidence:.2f})"
        )

        return output

    except asyncio.TimeoutError:
        logger.warning(f"Subgoal {idx} timed out after {timeout}s")

        # Retry if not at max retries
        if retry_count < max_retries:
            metadata["retries"] += 1
            logger.info(f"Retrying subgoal {idx} (attempt {retry_count + 2})")
            return await _execute_single_subgoal(
                idx, subgoal, agent, context, timeout, metadata, retry_count + 1, max_retries
            )

        # Max retries exceeded - check criticality
        is_critical = subgoal.get("is_critical", False)
        if is_critical:
            raise RuntimeError(f"Critical subgoal {idx} timed out after {max_retries + 1} attempts")

        # Non-critical: graceful degradation
        metadata["failed_subgoals"] += 1
        return AgentOutput(
            subgoal_index=idx,
            agent_id=agent.id,
            success=False,
            error=f"Timeout after {max_retries + 1} attempts",
        )

    except Exception as e:
        logger.error(f"Subgoal {idx} execution error: {e}")

        # Retry if not at max retries
        if retry_count < max_retries:
            metadata["retries"] += 1
            logger.info(f"Retrying subgoal {idx} after error (attempt {retry_count + 2})")
            return await _execute_single_subgoal(
                idx, subgoal, agent, context, timeout, metadata, retry_count + 1, max_retries
            )

        # Max retries exceeded - check criticality
        is_critical = subgoal.get("is_critical", False)
        if is_critical:
            raise RuntimeError(
                f"Critical subgoal {idx} failed after {max_retries + 1} attempts: {e}"
            )

        # Non-critical: graceful degradation
        metadata["failed_subgoals"] += 1
        return AgentOutput(
            subgoal_index=idx,
            agent_id=agent.id,
            success=False,
            error=str(e),
        )


async def _mock_agent_execution(
    idx: int,
    subgoal: dict[str, Any],
    agent: AgentInfo,
    context: dict[str, Any],
) -> AgentOutput:
    """Mock agent execution (placeholder for actual agent integration).

    This will be replaced with actual agent execution logic that:
    - Invokes the agent via MCP, API, or local execution
    - Passes context and subgoal description
    - Collects agent output and metadata

    Args:
        idx: Subgoal index
        subgoal: Subgoal dictionary
        agent: AgentInfo for the agent to execute
        context: Context from Phase 2

    Returns:
        AgentOutput with mock results
    """
    # TODO: Replace with actual agent execution
    # For now, simulate execution with a small delay
    await asyncio.sleep(0.1)

    return AgentOutput(
        subgoal_index=idx,
        agent_id=agent.id,
        success=True,
        summary=f"Mock execution of: {subgoal['description']}",
        data={
            "files_modified": [],
            "results": {},
        },
        confidence=0.85,
        execution_metadata={
            "tools_used": ["mock_tool"],
            "model_used": "mock-model",
        },
    )


async def _execute_agent(
    agent: AgentInfo,
    subgoal: dict[str, Any],
    context: dict[str, Any],
    timeout: float = DEFAULT_AGENT_TIMEOUT,
) -> AgentOutput:
    """Execute a single agent using the spawner.

    This function replaces _mock_agent_execution() with real spawner integration.

    Args:
        agent: AgentInfo for the agent to execute
        subgoal: Subgoal dictionary with description and metadata
        context: Context from Phase 2 (retrieved memories, conversation history)
        timeout: Timeout in seconds (default: DEFAULT_AGENT_TIMEOUT)

    Returns:
        AgentOutput with execution results

    Raises:
        Never - errors are captured in AgentOutput.error
    """
    start_time = time.time()
    subgoal_index = subgoal.get("subgoal_index", 0)

    try:
        # Build agent prompt from subgoal and context
        prompt = _build_agent_prompt(subgoal, context)

        # Create SpawnTask
        spawn_task = SpawnTask(
            prompt=prompt,
            agent=agent.id,
            timeout=int(timeout),
        )

        # Call spawn() function
        logger.debug(f"Spawning agent '{agent.id}' for subgoal {subgoal_index}")
        spawn_result: SpawnResult = await spawn(spawn_task)

        # Convert SpawnResult to AgentOutput
        duration_ms = int((time.time() - start_time) * 1000)

        if spawn_result.success:
            output = AgentOutput(
                subgoal_index=subgoal_index,
                agent_id=agent.id,
                success=True,
                summary=spawn_result.output,
                confidence=0.85,  # Default confidence for successful spawner execution
                execution_metadata={
                    "duration_ms": duration_ms,
                    "exit_code": spawn_result.exit_code,
                    "spawner": True,
                },
            )
        else:
            # Graceful degradation on failure
            output = AgentOutput(
                subgoal_index=subgoal_index,
                agent_id=agent.id,
                success=False,
                summary="",
                confidence=0.0,
                error=spawn_result.error or "Spawner execution failed",
                execution_metadata={
                    "duration_ms": duration_ms,
                    "exit_code": spawn_result.exit_code,
                    "spawner": True,
                },
            )

        logger.info(
            f"Agent '{agent.id}' completed subgoal {subgoal_index} "
            f"(success={output.success}, duration={duration_ms}ms)"
        )

        return output

    except Exception as e:
        # Handle unexpected errors gracefully
        duration_ms = int((time.time() - start_time) * 1000)
        logger.error(f"Unexpected error executing agent '{agent.id}': {e}")

        return AgentOutput(
            subgoal_index=subgoal_index,
            agent_id=agent.id,
            success=False,
            summary="",
            confidence=0.0,
            error=f"Unexpected error: {str(e)}",
            execution_metadata={
                "duration_ms": duration_ms,
                "spawner": True,
            },
        )


def _build_agent_prompt(subgoal: dict[str, Any], context: dict[str, Any]) -> str:
    """Build agent prompt from subgoal description and context.

    Args:
        subgoal: Subgoal dictionary with description
        context: Context from Phase 2

    Returns:
        Formatted prompt string for the agent
    """
    description = subgoal.get("description", "")

    # Build directive prompt that forces execution (not conversation)
    prompt_parts = [
        "EXECUTE THIS TASK IMMEDIATELY. Do NOT introduce yourself or ask clarifying questions.",
        "Return ONLY your findings and analysis.",
        "",
    ]

    # Add original query for context if available
    original_query = context.get("query", context.get("original_query", ""))
    if original_query:
        prompt_parts.append(f"ORIGINAL QUESTION: {original_query}")
        prompt_parts.append("")

    # Add the actual task
    prompt_parts.append(f"YOUR TASK: {description}")

    # Add retrieved context if available (keep brief)
    if context.get("retrieved_memories"):
        prompt_parts.append("")
        prompt_parts.append("RELEVANT CONTEXT:")
        for i, memory in enumerate(context["retrieved_memories"][:2], 1):
            content = memory.get("content", str(memory))[:200]
            prompt_parts.append(f"{i}. {content}")

    prompt_parts.append("")
    prompt_parts.append("BEGIN EXECUTION NOW:")

    return "\n".join(prompt_parts)


def _validate_agent_output(output: AgentOutput) -> None:
    """Validate agent output has required fields.

    Args:
        output: AgentOutput to validate

    Raises:
        ValueError: If required fields are missing or invalid
    """
    if output.confidence < 0 or output.confidence > 1:
        raise ValueError(f"Agent confidence must be in [0, 1], got {output.confidence}")

    if output.success and not output.summary:
        raise ValueError("Successful agent output must have a summary")

    if not output.success and not output.error:
        raise ValueError("Failed agent output must have an error message")
