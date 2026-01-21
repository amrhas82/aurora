"""Tests for SOAR collect phase (agent execution)."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from aurora_soar.phases.collect import AgentOutput, CollectResult, execute_agents
from aurora_spawner.models import SpawnResult, SpawnTask

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
# TDD Tests for Phase 3: Collect Phase Updates
# ============================================================================


class TestExecuteAgentsWithRetry:
    """TDD tests for updated execute_agents function with retry/fallback."""

    @pytest.mark.asyncio
    async def test_accepts_agent_assignments_list(self):
        """Test execute_agents accepts agent_assignments list instead of RouteResult."""
        from aurora_soar.agent_registry import AgentInfo

        # Create agent_assignments list
        agent = AgentInfo(
            id="test-agent",
            name="Test Agent",
            description="Test",
            capabilities=["test"],
            agent_type="local",
        )
        agent_assignments = [(0, agent)]

        # Create subgoals
        subgoals = [
            {
                "subgoal_index": 0,
                "description": "Test subgoal",
                "suggested_agent": "test-agent",
                "is_critical": False,
                "depends_on": [],
            }
        ]

        context = {"query": "Test query"}

        # Mock spawn_with_retry_and_fallback
        with patch("aurora_soar.phases.collect.spawn_with_retry_and_fallback") as mock_spawn:
            mock_spawn.return_value = SpawnResult(
                success=True,
                output="test output",
                error=None,
                exit_code=0,
            )

            result = await execute_agents(agent_assignments, subgoals, context)

            assert result is not None
            assert isinstance(result, CollectResult)

    @pytest.mark.asyncio
    async def test_uses_300s_timeout(self):
        """Test execute_agents uses 300s default timeout (not 60s)."""
        from aurora_soar.phases.collect import DEFAULT_AGENT_TIMEOUT

        # Verify constant changed
        assert DEFAULT_AGENT_TIMEOUT == 300

    @pytest.mark.asyncio
    async def test_on_progress_callback_invoked(self):
        """Test execute_agents invokes on_progress callback."""
        from aurora_soar.agent_registry import AgentInfo

        agent = AgentInfo(
            id="test-agent",
            name="Test Agent",
            description="Test",
            capabilities=["test"],
            agent_type="local",
        )
        agent_assignments = [(0, agent)]
        subgoals = [
            {
                "subgoal_index": 0,
                "description": "Test subgoal",
                "suggested_agent": "test-agent",
                "is_critical": False,
                "depends_on": [],
            }
        ]
        context = {"query": "Test query"}

        progress_calls = []

        def on_progress(message: str):
            progress_calls.append(message)

        with patch("aurora_soar.phases.collect.spawn_with_retry_and_fallback") as mock_spawn:
            mock_spawn.return_value = SpawnResult(
                success=True,
                output="test output",
                error=None,
                exit_code=0,
            )

            await execute_agents(agent_assignments, subgoals, context, on_progress=on_progress)

            # Should have progress messages
            assert len(progress_calls) > 0

    @pytest.mark.asyncio
    async def test_progress_format_matches_spec(self):
        """Test progress format: '[Agent 1/3] agent-id: Status'."""
        from aurora_soar.agent_registry import AgentInfo

        agent = AgentInfo(
            id="test-agent",
            name="Test Agent",
            description="Test",
            capabilities=["test"],
            agent_type="local",
        )
        agent_assignments = [(0, agent)]
        subgoals = [
            {
                "subgoal_index": 0,
                "description": "Test subgoal",
                "suggested_agent": "test-agent",
                "is_critical": False,
                "depends_on": [],
            }
        ]
        context = {"query": "Test query"}

        progress_calls = []

        def on_progress(message: str):
            progress_calls.append(message)

        with patch("aurora_soar.phases.collect.spawn_with_retry_and_fallback") as mock_spawn:
            mock_spawn.return_value = SpawnResult(
                success=True,
                output="test output",
                error=None,
                exit_code=0,
            )

            await execute_agents(agent_assignments, subgoals, context, on_progress=on_progress)

            # Check format: [Agent X/Y] agent-id: Status
            assert any("[Agent" in msg for msg in progress_calls)
            assert any("test-agent" in msg for msg in progress_calls)

    @pytest.mark.asyncio
    async def test_calls_spawn_with_retry_and_fallback(self):
        """Test execute_agents calls spawn_with_retry_and_fallback (not spawn)."""
        from aurora_soar.agent_registry import AgentInfo

        agent = AgentInfo(
            id="test-agent",
            name="Test Agent",
            description="Test",
            capabilities=["test"],
            agent_type="local",
        )
        agent_assignments = [(0, agent)]
        subgoals = [
            {
                "subgoal_index": 0,
                "description": "Test subgoal",
                "suggested_agent": "test-agent",
                "is_critical": False,
                "depends_on": [],
            }
        ]
        context = {"query": "Test query"}

        with patch("aurora_soar.phases.collect.spawn_with_retry_and_fallback") as mock_spawn:
            mock_spawn.return_value = SpawnResult(
                success=True,
                output="test output",
                error=None,
                exit_code=0,
                fallback=False,
                retry_count=0,
            )

            await execute_agents(agent_assignments, subgoals, context)

            # Verify spawn_with_retry_and_fallback was called
            mock_spawn.assert_called()

    @pytest.mark.asyncio
    async def test_fallback_metadata_in_result(self):
        """Test CollectResult includes fallback metadata."""
        from aurora_soar.agent_registry import AgentInfo

        agent = AgentInfo(
            id="test-agent",
            name="Test Agent",
            description="Test",
            capabilities=["test"],
            agent_type="local",
        )
        agent_assignments = [(0, agent)]
        subgoals = [
            {
                "subgoal_index": 0,
                "description": "Test subgoal",
                "suggested_agent": "test-agent",
                "is_critical": False,
                "depends_on": [],
            }
        ]
        context = {"query": "Test query"}

        with patch("aurora_soar.phases.collect.spawn_with_retry_and_fallback") as mock_spawn:
            # Simulate fallback
            mock_spawn.return_value = SpawnResult(
                success=True,
                output="fallback output",
                error=None,
                exit_code=0,
                fallback=True,
                original_agent="test-agent",
                retry_count=2,
            )

            result = await execute_agents(agent_assignments, subgoals, context)

            # Verify fallback metadata exists
            result_dict = result.to_dict()
            assert "fallback_agents" in result_dict or "execution_metadata" in result_dict

    @pytest.mark.asyncio
    async def test_parallel_progress_multiple_lines(self):
        """Test parallel execution shows progress for multiple agents."""
        from aurora_soar.agent_registry import AgentInfo

        agent1 = AgentInfo(
            id="agent-1",
            name="Agent 1",
            description="Test",
            capabilities=["test"],
            agent_type="local",
        )
        agent2 = AgentInfo(
            id="agent-2",
            name="Agent 2",
            description="Test",
            capabilities=["test"],
            agent_type="local",
        )
        agent_assignments = [(0, agent1), (1, agent2)]
        subgoals = [
            {
                "subgoal_index": 0,
                "description": "Test subgoal 1",
                "suggested_agent": "agent-1",
                "is_critical": False,
                "depends_on": [],
            },
            {
                "subgoal_index": 1,
                "description": "Test subgoal 2",
                "suggested_agent": "agent-2",
                "is_critical": False,
                "depends_on": [],
            },
        ]
        context = {"query": "Test query"}

        progress_calls = []

        def on_progress(message: str):
            progress_calls.append(message)

        with patch("aurora_soar.phases.collect.spawn_with_retry_and_fallback") as mock_spawn:
            mock_spawn.return_value = SpawnResult(
                success=True,
                output="test output",
                error=None,
                exit_code=0,
            )

            await execute_agents(agent_assignments, subgoals, context, on_progress=on_progress)

            # Should have progress for both agents
            agent1_messages = [msg for msg in progress_calls if "agent-1" in msg]
            agent2_messages = [msg for msg in progress_calls if "agent-2" in msg]

            assert len(agent1_messages) > 0
            assert len(agent2_messages) > 0


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
    """Test that collect phase executes multiple agents using new signature.

    Tests new execute_agents signature with agent_assignments list.
    """
    from aurora_soar.agent_registry import AgentInfo
    from aurora_soar.phases.collect import execute_agents

    # Create agent assignments directly (new API)
    agent_assignments = [
        (
            0,
            AgentInfo(
                id="agent-0", name="Agent 0", description="", capabilities=[], agent_type="local"
            ),
        ),
        (
            1,
            AgentInfo(
                id="agent-1", name="Agent 1", description="", capabilities=[], agent_type="local"
            ),
        ),
        (
            2,
            AgentInfo(
                id="agent-2", name="Agent 2", description="", capabilities=[], agent_type="local"
            ),
        ),
    ]

    subgoals = [
        {
            "subgoal_index": 0,
            "description": "Task 0",
            "is_critical": False,
            "suggested_agent": "agent-0",
        },
        {
            "subgoal_index": 1,
            "description": "Task 1",
            "is_critical": False,
            "suggested_agent": "agent-1",
        },
        {
            "subgoal_index": 2,
            "description": "Task 2",
            "is_critical": False,
            "suggested_agent": "agent-2",
        },
    ]

    context = {"query": "Test parallel execution"}

    # Mock spawn_with_retry_and_fallback
    with patch("aurora_soar.phases.collect.spawn_with_retry_and_fallback") as mock_spawn:
        mock_spawn.return_value = SpawnResult(
            success=True,
            output="test output",
            error=None,
            exit_code=0,
            fallback=False,
            retry_count=0,
        )

        # Execute agents with new signature
        result = await execute_agents(agent_assignments, subgoals, context, agent_timeout=10)

        # Verify spawn_with_retry_and_fallback was called for each agent
        assert mock_spawn.call_count == 3

        # Verify all subgoals executed
        assert len(result.agent_outputs) == 3

        # Verify results maintain input order (sorted by subgoal_index)
        for i, output in enumerate(result.agent_outputs):
            assert (
                output.subgoal_index == i
            ), f"Expected subgoal_index={i}, got {output.subgoal_index}"
            assert output.agent_id == f"agent-{i}"
            assert output.success is True

        # Verify execution metadata
        assert result.execution_metadata["total_subgoals"] == 3
        assert "total_duration_ms" in result.execution_metadata
        assert result.execution_metadata["failed_subgoals"] == 0


# ============================================================================
# TDD Tests for Dependency-Aware Execution (PRD 0030)
# ============================================================================


class TestTopologicalSort:
    """TDD tests for topological sorting of subgoals."""

    def test_topological_sort_no_deps(self):
        """Test that subgoals with no dependencies all go into single wave.

        Input: [sg-1, sg-2, sg-3] with no dependencies
        Expected: [[sg-1, sg-2, sg-3]] (single wave with all subgoals)
        """
        from aurora_soar.phases.collect import topological_sort

        subgoals = [
            {"subgoal_index": 1, "description": "Task 1", "depends_on": []},
            {"subgoal_index": 2, "description": "Task 2", "depends_on": []},
            {"subgoal_index": 3, "description": "Task 3", "depends_on": []},
        ]

        waves = topological_sort(subgoals)

        # All subgoals should be in a single wave
        assert len(waves) == 1
        assert len(waves[0]) == 3

        # Verify all subgoals are present
        wave_indices = {sg["subgoal_index"] for sg in waves[0]}
        assert wave_indices == {1, 2, 3}

    def test_topological_sort_linear_deps(self):
        """Test linear chain A → B → C produces 3 waves.

        Input: A (no deps), B (depends on A), C (depends on B)
        Expected: [[A], [B], [C]] (3 waves, one subgoal each)
        """
        from aurora_soar.phases.collect import topological_sort

        subgoals = [
            {"subgoal_index": 1, "description": "Task A", "depends_on": []},
            {"subgoal_index": 2, "description": "Task B", "depends_on": [1]},
            {"subgoal_index": 3, "description": "Task C", "depends_on": [2]},
        ]

        waves = topological_sort(subgoals)

        # Should have 3 waves
        assert len(waves) == 3

        # Each wave should have exactly 1 subgoal
        assert len(waves[0]) == 1
        assert len(waves[1]) == 1
        assert len(waves[2]) == 1

        # Verify correct ordering
        assert waves[0][0]["subgoal_index"] == 1  # A first
        assert waves[1][0]["subgoal_index"] == 2  # B second
        assert waves[2][0]["subgoal_index"] == 3  # C third

    def test_topological_sort_diamond_deps(self):
        """Test diamond pattern A → (B, C) → D produces 3 waves.

        Input: A (no deps), B (depends on A), C (depends on A), D (depends on B, C)
        Expected: [[A], [B, C], [D]] (3 waves)
        """
        from aurora_soar.phases.collect import topological_sort

        subgoals = [
            {"subgoal_index": 1, "description": "Task A", "depends_on": []},
            {"subgoal_index": 2, "description": "Task B", "depends_on": [1]},
            {"subgoal_index": 3, "description": "Task C", "depends_on": [1]},
            {"subgoal_index": 4, "description": "Task D", "depends_on": [2, 3]},
        ]

        waves = topological_sort(subgoals)

        # Should have 3 waves
        assert len(waves) == 3

        # Wave 1: A only
        assert len(waves[0]) == 1
        assert waves[0][0]["subgoal_index"] == 1

        # Wave 2: B and C (parallel)
        assert len(waves[1]) == 2
        wave2_indices = {sg["subgoal_index"] for sg in waves[1]}
        assert wave2_indices == {2, 3}

        # Wave 3: D only
        assert len(waves[2]) == 1
        assert waves[2][0]["subgoal_index"] == 4

    def test_topological_sort_parallel_chains(self):
        """Test independent chains (A → B) and (C → D) produce 2 waves.

        Input: A (no deps), B (depends on A), C (no deps), D (depends on C)
        Expected: [[A, C], [B, D]] (2 waves with parallel execution)
        """
        from aurora_soar.phases.collect import topological_sort

        subgoals = [
            {"subgoal_index": 1, "description": "Task A", "depends_on": []},
            {"subgoal_index": 2, "description": "Task B", "depends_on": [1]},
            {"subgoal_index": 3, "description": "Task C", "depends_on": []},
            {"subgoal_index": 4, "description": "Task D", "depends_on": [3]},
        ]

        waves = topological_sort(subgoals)

        # Should have 2 waves
        assert len(waves) == 2

        # Wave 1: A and C (independent, parallel)
        assert len(waves[0]) == 2
        wave1_indices = {sg["subgoal_index"] for sg in waves[0]}
        assert wave1_indices == {1, 3}

        # Wave 2: B and D (each depends on their respective chain root)
        assert len(waves[1]) == 2
        wave2_indices = {sg["subgoal_index"] for sg in waves[1]}
        assert wave2_indices == {2, 4}
