"""Tests for SOAR collect phase (agent execution)."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from aurora_spawner.models import SpawnResult, SpawnTask

from aurora_soar.phases.collect import AgentOutput, CollectResult, execute_agents

# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def mock_agent_info():
    """Mock AgentInfo for testing."""
    agent = MagicMock()
    agent.id = "test-agent"
    agent.name = "Test Agent"
    agent.description = "A test agent"
    agent.capabilities = ["testing"]
    return agent


@pytest.fixture
def mock_routing():
    """Mock RouteResult for testing."""
    routing = MagicMock()
    routing.agent_assignments = [(0, mock_agent_info())]
    routing.execution_plan = [
        {
            "phase": 1,
            "parallelizable": [{"subgoal_index": 0, "description": "Test subgoal"}],
            "sequential": [],
        }
    ]
    return routing


@pytest.fixture
def mock_context():
    """Mock context for testing."""
    return {
        "query": "Test query",
        "retrieved_memories": [],
        "conversation_history": [],
    }


# ============================================================================
# Smoke Tests
# ============================================================================


def test_imports():
    """Test that basic imports work."""
    from aurora_soar.phases import collect
    from aurora_soar.phases.collect import AgentOutput, CollectResult

    assert collect is not None
    assert AgentOutput is not None
    assert CollectResult is not None


def test_agent_output_creation():
    """Test that AgentOutput can be created."""
    output = AgentOutput(
        subgoal_index=0,
        agent_id="test-agent",
        success=True,
        summary="Test summary",
        confidence=0.9,
    )

    assert output.subgoal_index == 0
    assert output.agent_id == "test-agent"
    assert output.success is True
    assert output.confidence == 0.9


def test_collect_result_creation():
    """Test that CollectResult can be created."""
    output = AgentOutput(
        subgoal_index=0,
        agent_id="test-agent",
        success=True,
        summary="Test summary",
    )

    result = CollectResult(
        agent_outputs=[output],
        execution_metadata={"total_duration_ms": 100},
    )

    assert len(result.agent_outputs) == 1
    assert result.execution_metadata["total_duration_ms"] == 100


# ============================================================================
# TDD Tests for Spawner Integration (Task 1.1)
# ============================================================================


@pytest.mark.asyncio
async def test_execute_agent_with_spawner(mock_agent_info, mock_context):
    """Test that _execute_agent() calls spawner.spawn() and converts result correctly.

    This test should FAIL initially (TDD RED phase) because _execute_agent() doesn't exist yet.
    """
    from aurora_soar.phases.collect import _execute_agent

    # Mock subgoal
    subgoal = {
        "subgoal_index": 0,
        "description": "Test task: write hello world",
        "is_critical": False,
    }

    # Mock spawn result
    mock_spawn_result = SpawnResult(
        success=True,
        output="I successfully wrote hello world to hello.py",
        error=None,
        exit_code=0,
    )

    # Mock spawn function
    with patch("aurora_soar.phases.collect.spawn", new_callable=AsyncMock) as mock_spawn:
        mock_spawn.return_value = mock_spawn_result

        # Execute agent
        result = await _execute_agent(mock_agent_info, subgoal, mock_context)

        # Verify spawn was called with correct SpawnTask
        mock_spawn.assert_called_once()
        spawn_task = mock_spawn.call_args[0][0]
        assert isinstance(spawn_task, SpawnTask)
        assert "Test task: write hello world" in spawn_task.prompt
        assert spawn_task.agent == "test-agent"

        # Verify AgentOutput conversion
        assert isinstance(result, AgentOutput)
        assert result.success is True
        assert result.agent_id == "test-agent"
        assert result.subgoal_index == 0
        assert "hello world" in result.summary.lower()


@pytest.mark.asyncio
async def test_execute_agent_spawner_timeout(mock_agent_info, mock_context):
    """Test that _execute_agent() handles spawner timeout gracefully.

    This test should FAIL initially (TDD RED phase).
    """
    from aurora_soar.phases.collect import _execute_agent

    subgoal = {
        "subgoal_index": 1,
        "description": "Long running task",
        "is_critical": False,
    }

    # Mock timeout result
    mock_spawn_result = SpawnResult(
        success=False,
        output="",
        error="Process timed out after 60 seconds",
        exit_code=-1,
    )

    with patch("aurora_soar.phases.collect.spawn", new_callable=AsyncMock) as mock_spawn:
        mock_spawn.return_value = mock_spawn_result

        result = await _execute_agent(mock_agent_info, subgoal, mock_context)

        # Verify graceful degradation
        assert isinstance(result, AgentOutput)
        assert result.success is False
        assert result.agent_id == "test-agent"
        assert result.subgoal_index == 1
        assert result.error is not None
        assert "timeout" in result.error.lower() or "timed out" in result.error.lower()


@pytest.mark.asyncio
async def test_execute_agent_spawner_failure(mock_agent_info, mock_context):
    """Test that _execute_agent() handles spawner failure gracefully.

    This test should FAIL initially (TDD RED phase).
    """
    from aurora_soar.phases.collect import _execute_agent

    subgoal = {
        "subgoal_index": 2,
        "description": "Task that causes error",
        "is_critical": False,
    }

    # Mock failure result
    mock_spawn_result = SpawnResult(
        success=False,
        output="",
        error="Tool 'claude' not found in PATH",
        exit_code=-1,
    )

    with patch("aurora_soar.phases.collect.spawn", new_callable=AsyncMock) as mock_spawn:
        mock_spawn.return_value = mock_spawn_result

        result = await _execute_agent(mock_agent_info, subgoal, mock_context)

        # Verify graceful degradation
        assert isinstance(result, AgentOutput)
        assert result.success is False
        assert result.agent_id == "test-agent"
        assert result.subgoal_index == 2
        assert result.error is not None
        assert "not found" in result.error.lower() or "path" in result.error.lower()


@pytest.mark.asyncio
async def test_convert_spawn_result_to_agent_output():
    """Test conversion from SpawnResult to AgentOutput format.

    This test should FAIL initially (TDD RED phase) because the conversion doesn't exist yet.
    """
    from aurora_soar.phases.collect import _execute_agent

    # Test successful result conversion
    spawn_result = SpawnResult(
        success=True,
        output="Successfully completed task. Modified 3 files: test1.py, test2.py, config.json",
        error=None,
        exit_code=0,
    )

    agent_info = MagicMock()
    agent_info.id = "test-agent"

    subgoal = {
        "subgoal_index": 5,
        "description": "Test conversion",
        "is_critical": False,
    }

    with patch("aurora_soar.phases.collect.spawn", new_callable=AsyncMock) as mock_spawn:
        mock_spawn.return_value = spawn_result

        result = await _execute_agent(agent_info, subgoal, {})

        # Verify conversion preserves key information
        assert result.success is True
        assert result.agent_id == "test-agent"
        assert result.subgoal_index == 5
        assert result.summary == spawn_result.output
        assert result.error is None

        # Verify metadata is captured
        assert "duration_ms" in result.execution_metadata or result.execution_metadata is not None


# ============================================================================
# TDD Tests for Parallel Spawning (Task 1.4)
# ============================================================================


@pytest.mark.asyncio
async def test_collect_parallel_with_spawner():
    """Test that collect phase executes multiple agents in parallel using spawner.

    This test should FAIL initially (TDD RED phase) because spawn_parallel() isn't used yet.
    Tests:
    - Multiple agents spawned in parallel
    - Semaphore limiting (max 5 concurrent)
    - Results maintain input order
    - All AgentOutput objects have correct subgoal_index
    """
    from aurora_soar.phases.collect import execute_agents
    from aurora_soar.phases.route import RouteResult

    # Create mock routing with multiple parallel subgoals
    routing = RouteResult(
        agent_assignments=[
            (0, MagicMock(id="agent-0")),
            (1, MagicMock(id="agent-1")),
            (2, MagicMock(id="agent-2")),
            (3, MagicMock(id="agent-3")),
            (4, MagicMock(id="agent-4")),
            (5, MagicMock(id="agent-5")),
            (6, MagicMock(id="agent-6")),
        ],
        execution_plan=[
            {
                "phase": 1,
                "parallelizable": [
                    {"subgoal_index": 0, "description": "Task 0", "is_critical": False},
                    {"subgoal_index": 1, "description": "Task 1", "is_critical": False},
                    {"subgoal_index": 2, "description": "Task 2", "is_critical": False},
                    {"subgoal_index": 3, "description": "Task 3", "is_critical": False},
                    {"subgoal_index": 4, "description": "Task 4", "is_critical": False},
                    {"subgoal_index": 5, "description": "Task 5", "is_critical": False},
                    {"subgoal_index": 6, "description": "Task 6", "is_critical": False},
                ],
                "sequential": [],
            }
        ],
    )

    context = {"query": "Test parallel execution"}

    # Mock spawn_parallel to return success results
    async def mock_spawn_parallel(
        tasks: list[SpawnTask], max_concurrent: int = 5, **kwargs
    ) -> list[SpawnResult]:
        """Mock spawn_parallel that returns success results in input order."""
        # Verify max_concurrent parameter
        assert max_concurrent == 5, f"Expected max_concurrent=5, got {max_concurrent}"

        # Simulate parallel execution with small delay
        await asyncio.sleep(0.01)

        # Return success results maintaining input order
        return [
            SpawnResult(
                success=True,
                output=f"Completed {task.prompt}",
                error=None,
                exit_code=0,
            )
            for task in tasks
        ]

    with patch(
        "aurora_soar.phases.collect.spawn_parallel", new_callable=AsyncMock
    ) as mock_spawn_parallel_func:
        mock_spawn_parallel_func.side_effect = mock_spawn_parallel

        # Execute agents
        result = await execute_agents(routing, context, agent_timeout=10)

        # Verify spawn_parallel was called once with all tasks
        assert mock_spawn_parallel_func.call_count == 1
        call_args = mock_spawn_parallel_func.call_args
        tasks_arg = call_args[0][0]
        assert len(tasks_arg) == 7, f"Expected 7 tasks, got {len(tasks_arg)}"

        # Verify all subgoals executed
        assert len(result.agent_outputs) == 7

        # Verify results maintain input order (sorted by subgoal_index)
        for i, output in enumerate(result.agent_outputs):
            assert (
                output.subgoal_index == i
            ), f"Expected subgoal_index={i}, got {output.subgoal_index}"
            assert output.agent_id == f"agent-{i}"
            assert output.success is True

        # Verify execution metadata
        assert result.execution_metadata["parallel_subgoals"] == 7
        assert result.execution_metadata["sequential_subgoals"] == 0
        assert result.execution_metadata["failed_subgoals"] == 0
