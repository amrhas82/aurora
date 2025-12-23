"""Phase 6: Agent Execution.

This module implements the Collect phase of the SOAR pipeline, which executes
agents in parallel or sequentially based on dependencies.
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from aurora_soar.agent_registry import AgentInfo
    from aurora_soar.phases.route import RouteResult

logger = logging.getLogger(__name__)

__all__ = ["execute_agents", "CollectResult", "AgentOutput"]


# Default timeouts (in seconds)
DEFAULT_AGENT_TIMEOUT = 60
DEFAULT_QUERY_TIMEOUT = 300  # 5 minutes


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
    """

    def __init__(
        self,
        agent_outputs: list[AgentOutput],
        execution_metadata: dict[str, Any],
        user_interactions: list[dict[str, Any]] | None = None,
    ):
        self.agent_outputs = agent_outputs
        self.execution_metadata = execution_metadata
        self.user_interactions = user_interactions or []

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "agent_outputs": [output.to_dict() for output in self.agent_outputs],
            "execution_metadata": self.execution_metadata,
            "user_interactions": self.user_interactions,
        }


async def execute_agents(
    routing: "RouteResult",
    context: dict[str, Any],
    agent_timeout: float = DEFAULT_AGENT_TIMEOUT,
    query_timeout: float = DEFAULT_QUERY_TIMEOUT,
) -> CollectResult:
    """Execute agents based on routing plan with parallel and sequential execution.

    This function:
    1. Executes agents according to execution plan phases
    2. Runs parallelizable subgoals concurrently using asyncio
    3. Executes sequential subgoals in order
    4. Validates agent outputs and retries on failure (max 2 retries)
    5. Handles timeouts at agent and query level
    6. Implements graceful degradation for non-critical failures
    7. Aborts on critical subgoal failure

    Args:
        routing: RouteResult from Phase 5 with agent assignments and execution plan
        context: Retrieved context from Phase 2
        agent_timeout: Timeout per agent execution in seconds (default 60)
        query_timeout: Overall query timeout in seconds (default 300)

    Returns:
        CollectResult with all agent outputs and execution metadata

    Raises:
        TimeoutError: If overall query timeout exceeded
        RuntimeError: If critical subgoal fails after retries
    """
    start_time = time.time()
    agent_outputs: list[AgentOutput] = []
    execution_metadata: dict[str, Any] = {
        "total_duration_ms": 0,
        "phases_executed": 0,
        "parallel_subgoals": 0,
        "sequential_subgoals": 0,
        "failed_subgoals": 0,
        "retries": 0,
    }
    user_interactions: list[dict[str, Any]] = []

    # Convert agent assignments to dict for easy lookup
    agent_map = {idx: agent for idx, agent in routing.agent_assignments}

    try:
        # Execute each phase in the execution plan
        for phase in routing.execution_plan:
            phase_num = phase["phase"]
            logger.info(f"Executing phase {phase_num}")

            # Execute parallelizable subgoals concurrently
            parallelizable = phase.get("parallelizable", [])
            if parallelizable:
                execution_metadata["parallel_subgoals"] += len(parallelizable)
                outputs = await _execute_parallel_subgoals(
                    parallelizable,
                    agent_map,
                    context,
                    agent_timeout,
                    execution_metadata,
                )
                agent_outputs.extend(outputs)

            # Execute sequential subgoals in order
            sequential = phase.get("sequential", [])
            if sequential:
                execution_metadata["sequential_subgoals"] += len(sequential)
                outputs = await _execute_sequential_subgoals(
                    sequential,
                    agent_map,
                    context,
                    agent_timeout,
                    execution_metadata,
                )
                agent_outputs.extend(outputs)

            execution_metadata["phases_executed"] += 1

            # Check overall query timeout
            elapsed = time.time() - start_time
            if elapsed > query_timeout:
                raise TimeoutError(
                    f"Query timeout exceeded: {elapsed:.1f}s > {query_timeout}s"
                )

    except Exception as e:
        logger.error(f"Agent execution failed: {e}")
        raise

    finally:
        # Calculate final metadata
        execution_metadata["total_duration_ms"] = int(
            (time.time() - start_time) * 1000
        )

    logger.info(
        f"Agent execution complete: {len(agent_outputs)} subgoals, "
        f"{execution_metadata['failed_subgoals']} failed"
    )

    return CollectResult(
        agent_outputs=agent_outputs,
        execution_metadata=execution_metadata,
        user_interactions=user_interactions,
    )


async def _execute_parallel_subgoals(
    subgoals: list[dict[str, Any]],
    agent_map: dict[int, "AgentInfo"],
    context: dict[str, Any],
    timeout: float,
    metadata: dict[str, Any],
) -> list[AgentOutput]:
    """Execute subgoals in parallel using asyncio.

    Args:
        subgoals: List of subgoal dictionaries with subgoal_index
        agent_map: Map of subgoal_index -> AgentInfo
        context: Context from Phase 2
        timeout: Timeout per agent in seconds
        metadata: Execution metadata to update

    Returns:
        List of AgentOutput objects
    """
    logger.debug(f"Executing {len(subgoals)} subgoals in parallel")

    # Create tasks for all subgoals
    tasks = []
    for subgoal in subgoals:
        idx = subgoal["subgoal_index"]
        agent = agent_map[idx]
        task = _execute_single_subgoal(
            idx, subgoal, agent, context, timeout, metadata
        )
        tasks.append(task)

    # Execute all tasks concurrently
    outputs = await asyncio.gather(*tasks, return_exceptions=True)

    # Handle any exceptions
    results = []
    for i, output in enumerate(outputs):
        if isinstance(output, BaseException):
            subgoal = subgoals[i]
            idx = subgoal["subgoal_index"]
            logger.error(f"Subgoal {idx} raised exception: {output}")
            results.append(
                AgentOutput(
                    subgoal_index=idx,
                    agent_id=agent_map[idx].id,
                    success=False,
                    error=str(output),
                )
            )
            metadata["failed_subgoals"] += 1
        else:
            results.append(output)

    return results


async def _execute_sequential_subgoals(
    subgoals: list[dict[str, Any]],
    agent_map: dict[int, "AgentInfo"],
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
            output = await _execute_single_subgoal(
                idx, subgoal, agent, context, timeout, metadata
            )
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
                raise RuntimeError(
                    f"Critical subgoal {idx} failed: {e}"
                )

    return outputs


async def _execute_single_subgoal(
    idx: int,
    subgoal: dict[str, Any],
    agent: "AgentInfo",
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
    start_time = time.time()

    try:
        # Execute agent with timeout
        output = await asyncio.wait_for(
            _mock_agent_execution(idx, subgoal, agent, context),
            timeout=timeout,
        )

        # Validate output format
        _validate_agent_output(output)

        # Add execution metadata
        duration_ms = int((time.time() - start_time) * 1000)
        output.execution_metadata["duration_ms"] = duration_ms
        output.execution_metadata["retry_count"] = retry_count

        logger.info(
            f"Subgoal {idx} completed in {duration_ms}ms "
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
            raise RuntimeError(
                f"Critical subgoal {idx} timed out after {max_retries + 1} attempts"
            )

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
    agent: "AgentInfo",
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


def _validate_agent_output(output: AgentOutput) -> None:
    """Validate agent output has required fields.

    Args:
        output: AgentOutput to validate

    Raises:
        ValueError: If required fields are missing or invalid
    """
    if output.confidence < 0 or output.confidence > 1:
        raise ValueError(
            f"Agent confidence must be in [0, 1], got {output.confidence}"
        )

    if output.success and not output.summary:
        raise ValueError("Successful agent output must have a summary")

    if not output.success and not output.error:
        raise ValueError("Failed agent output must have an error message")
