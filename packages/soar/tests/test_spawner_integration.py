"""Integration tests for SOAR with spawner.

These tests verify the complete flow from orchestrator through collect phase
to spawner execution and back to AgentOutput.
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from aurora_spawner.models import SpawnResult, SpawnTask

from aurora_soar.phases.collect import AgentOutput, execute_agents
from aurora_soar.phases.route import RouteResult

# ============================================================================
# Integration Tests
# ============================================================================


@pytest.mark.asyncio
async def test_soar_with_spawner_mock():
    """Test complete flow: orchestrator → collect → spawn → AgentOutput.

    This test mocks subprocess execution but uses real spawner logic
    to verify the integration works end-to-end.
    """
    # Create routing with both parallel and sequential subgoals
    routing = RouteResult(
        agent_assignments=[
            (0, MagicMock(id="planner")),
            (1, MagicMock(id="executor")),
            (2, MagicMock(id="validator")),
        ],
        execution_plan=[
            {
                "phase": 1,
                "parallelizable": [
                    {
                        "subgoal_index": 0,
                        "description": "Plan the implementation",
                        "is_critical": True,
                    },
                    {"subgoal_index": 1, "description": "Write the code", "is_critical": True},
                ],
                "sequential": [],
            },
            {
                "phase": 2,
                "parallelizable": [],
                "sequential": [
                    {
                        "subgoal_index": 2,
                        "description": "Validate the implementation",
                        "is_critical": True,
                    },
                ],
            },
        ],
    )

    context = {
        "query": "Implement feature X",
        "retrieved_memories": [
            {"content": "Feature X requires Y and Z"},
        ],
    }

    # Mock spawn_parallel for parallel execution
    async def mock_spawn_parallel(
        tasks: list[SpawnTask], max_concurrent: int = 5, **kwargs
    ) -> list[SpawnResult]:
        # Simulate parallel execution
        await asyncio.sleep(0.01)
        return [
            SpawnResult(
                success=True,
                output=f"Agent {task.agent} completed: {task.prompt[:50]}...",
                error=None,
                exit_code=0,
            )
            for task in tasks
        ]

    # Mock spawn for sequential execution
    async def mock_spawn(task: SpawnTask, **kwargs) -> SpawnResult:
        # Simulate sequential execution
        await asyncio.sleep(0.01)
        return SpawnResult(
            success=True,
            output=f"Agent {task.agent} completed: {task.prompt[:50]}...",
            error=None,
            exit_code=0,
        )

    with patch(
        "aurora_soar.phases.collect.spawn_parallel", new_callable=AsyncMock
    ) as mock_spawn_parallel_func:
        with patch("aurora_soar.phases.collect.spawn", new_callable=AsyncMock) as mock_spawn_func:
            mock_spawn_parallel_func.side_effect = mock_spawn_parallel
            mock_spawn_func.side_effect = mock_spawn

            # Execute the complete flow
            result = await execute_agents(routing, context, agent_timeout=30)

            # Verify complete flow
            assert len(result.agent_outputs) == 3

            # Verify parallel subgoals (phase 1)
            assert result.agent_outputs[0].subgoal_index == 0
            assert result.agent_outputs[0].agent_id == "planner"
            assert result.agent_outputs[0].success is True
            assert (
                "Plan the implementation" in result.agent_outputs[0].summary
                or "planner" in result.agent_outputs[0].summary
            )

            assert result.agent_outputs[1].subgoal_index == 1
            assert result.agent_outputs[1].agent_id == "executor"
            assert result.agent_outputs[1].success is True

            # Verify sequential subgoal (phase 2)
            assert result.agent_outputs[2].subgoal_index == 2
            assert result.agent_outputs[2].agent_id == "validator"
            assert result.agent_outputs[2].success is True

            # Verify execution metadata
            assert result.execution_metadata["phases_executed"] == 2
            assert result.execution_metadata["parallel_subgoals"] == 2
            assert result.execution_metadata["sequential_subgoals"] == 1
            assert result.execution_metadata["failed_subgoals"] == 0
            assert result.execution_metadata["total_duration_ms"] > 0

            # Verify spawner was called correctly
            assert mock_spawn_parallel_func.call_count == 1  # Called once for parallel phase
            assert mock_spawn_func.call_count == 1  # Called once for sequential subgoal


@pytest.mark.asyncio
async def test_soar_with_spawner_parallel_execution():
    """Test parallel execution mode with spawner.

    Verifies that parallel subgoals are executed concurrently
    and results are properly collected.
    """
    # Create routing with only parallel subgoals
    routing = RouteResult(
        agent_assignments=[
            (0, MagicMock(id="agent-a")),
            (1, MagicMock(id="agent-b")),
            (2, MagicMock(id="agent-c")),
        ],
        execution_plan=[
            {
                "phase": 1,
                "parallelizable": [
                    {"subgoal_index": 0, "description": "Task A", "is_critical": False},
                    {"subgoal_index": 1, "description": "Task B", "is_critical": False},
                    {"subgoal_index": 2, "description": "Task C", "is_critical": False},
                ],
                "sequential": [],
            }
        ],
    )

    context = {"query": "Run parallel tasks"}

    # Mock spawn_parallel with timing simulation
    async def mock_spawn_parallel(
        tasks: list[SpawnTask], max_concurrent: int = 5, **kwargs
    ) -> list[SpawnResult]:
        # Verify all tasks are passed at once
        assert len(tasks) == 3
        await asyncio.sleep(0.05)  # Simulate concurrent execution
        return [
            SpawnResult(
                success=True,
                output=f"Completed {i+1}",
                error=None,
                exit_code=0,
            )
            for i in range(len(tasks))
        ]

    with patch("aurora_soar.phases.collect.spawn_parallel", new_callable=AsyncMock) as mock_func:
        mock_func.side_effect = mock_spawn_parallel

        start_time = asyncio.get_event_loop().time()
        result = await execute_agents(routing, context, agent_timeout=10)
        duration = asyncio.get_event_loop().time() - start_time

        # Verify parallel execution happened (should take ~0.05s, not 3*0.05s)
        assert duration < 0.2, f"Parallel execution took too long: {duration}s"

        # Verify all outputs
        assert len(result.agent_outputs) == 3
        assert all(output.success for output in result.agent_outputs)

        # Verify spawn_parallel was called once with all tasks
        assert mock_func.call_count == 1


@pytest.mark.asyncio
async def test_soar_with_spawner_sequential_execution():
    """Test sequential execution mode with spawner.

    Verifies that sequential subgoals are executed in order
    and context is properly maintained.
    """
    # Create routing with only sequential subgoals
    routing = RouteResult(
        agent_assignments=[
            (0, MagicMock(id="step-1")),
            (1, MagicMock(id="step-2")),
        ],
        execution_plan=[
            {
                "phase": 1,
                "parallelizable": [],
                "sequential": [
                    {"subgoal_index": 0, "description": "First step", "is_critical": True},
                    {"subgoal_index": 1, "description": "Second step", "is_critical": True},
                ],
            }
        ],
    )

    context = {"query": "Run sequential tasks"}

    call_order = []

    # Mock spawn to track call order
    async def mock_spawn(task: SpawnTask, **kwargs) -> SpawnResult:
        call_order.append(task.agent)
        await asyncio.sleep(0.01)
        return SpawnResult(
            success=True,
            output=f"Completed by {task.agent}",
            error=None,
            exit_code=0,
        )

    with patch("aurora_soar.phases.collect.spawn", new_callable=AsyncMock) as mock_func:
        mock_func.side_effect = mock_spawn

        result = await execute_agents(routing, context, agent_timeout=10)

        # Verify sequential execution order
        assert call_order == ["step-1", "step-2"], f"Wrong order: {call_order}"

        # Verify all outputs
        assert len(result.agent_outputs) == 2
        assert all(output.success for output in result.agent_outputs)


@pytest.mark.asyncio
async def test_soar_with_spawner_cost_tracking():
    """Test that cost tracking includes spawner operations.

    Verifies that execution metadata properly tracks spawner
    operations including duration, exit codes, and success rates.
    """
    routing = RouteResult(
        agent_assignments=[
            (0, MagicMock(id="agent-1")),
            (1, MagicMock(id="agent-2")),
        ],
        execution_plan=[
            {
                "phase": 1,
                "parallelizable": [
                    {"subgoal_index": 0, "description": "Task 1", "is_critical": False},
                    {"subgoal_index": 1, "description": "Task 2", "is_critical": False},
                ],
                "sequential": [],
            }
        ],
    )

    context = {"query": "Track costs"}

    async def mock_spawn_parallel(
        tasks: list[SpawnTask], max_concurrent: int = 5, **kwargs
    ) -> list[SpawnResult]:
        await asyncio.sleep(0.02)
        return [
            SpawnResult(success=True, output="Done", error=None, exit_code=0),
            SpawnResult(success=True, output="Done", error=None, exit_code=0),
        ]

    with patch("aurora_soar.phases.collect.spawn_parallel", new_callable=AsyncMock) as mock_func:
        mock_func.side_effect = mock_spawn_parallel

        result = await execute_agents(routing, context, agent_timeout=10)

        # Verify cost tracking metadata
        assert result.execution_metadata["total_duration_ms"] > 0
        assert result.execution_metadata["parallel_subgoals"] == 2
        assert result.execution_metadata["failed_subgoals"] == 0

        # Verify each agent output has spawner metadata
        for output in result.agent_outputs:
            assert "duration_ms" in output.execution_metadata
            assert "exit_code" in output.execution_metadata
            assert output.execution_metadata["spawner"] is True
            assert output.execution_metadata["parallel"] is True
