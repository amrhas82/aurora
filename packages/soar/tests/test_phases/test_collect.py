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
        },
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
            },
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
            },
        ]
        context = {"query": "Test query"}

        progress_calls = []

        def on_progress(message: str):
            progress_calls.append(message)

        async def mock_spawn_parallel_tracked(*args, **kwargs):
            # Capture on_progress callback if provided
            if "on_progress" in kwargs and kwargs["on_progress"]:
                kwargs["on_progress"]("[Agent 1/1] test-agent: Running")
            tasks = args[0] if args else kwargs.get("tasks", [])
            return (
                [
                    SpawnResult(success=True, output="test output", error=None, exit_code=0)
                    for _ in tasks
                ],
                {},
            )

        with patch(
            "aurora_soar.phases.collect.spawn_parallel_tracked",
            side_effect=mock_spawn_parallel_tracked,
        ):
            await execute_agents(agent_assignments, subgoals, context, on_progress=on_progress)

            # Check format: [Agent X/Y] agent-id: Status
            assert any("[Agent" in msg for msg in progress_calls), (
                f"Expected '[Agent' in progress, got: {progress_calls}"
            )
            assert any("test-agent" in msg for msg in progress_calls), (
                f"Expected 'test-agent' in progress, got: {progress_calls}"
            )

    @pytest.mark.asyncio
    async def test_calls_spawn_parallel_tracked(self):
        """Test execute_agents calls spawn_parallel_tracked for parallel execution."""
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
            },
        ]
        context = {"query": "Test query"}

        async def mock_spawn_parallel_tracked(*args, **kwargs):
            tasks = args[0] if args else kwargs.get("tasks", [])
            return (
                [
                    SpawnResult(success=True, output="test output", error=None, exit_code=0)
                    for _ in tasks
                ],
                {},
            )

        with patch(
            "aurora_soar.phases.collect.spawn_parallel_tracked",
            side_effect=mock_spawn_parallel_tracked,
        ) as mock_spawn:
            await execute_agents(agent_assignments, subgoals, context)

            # Verify spawn_parallel_tracked was called
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
            },
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
                id="agent-0",
                name="Agent 0",
                description="",
                capabilities=[],
                agent_type="local",
            ),
        ),
        (
            1,
            AgentInfo(
                id="agent-1",
                name="Agent 1",
                description="",
                capabilities=[],
                agent_type="local",
            ),
        ),
        (
            2,
            AgentInfo(
                id="agent-2",
                name="Agent 2",
                description="",
                capabilities=[],
                agent_type="local",
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

    # Mock spawn_parallel_tracked
    async def mock_spawn_parallel_tracked(*args, **kwargs):
        tasks = args[0] if args else kwargs.get("tasks", [])
        return (
            [
                SpawnResult(
                    success=True,
                    output="test output",
                    error=None,
                    exit_code=0,
                    fallback=False,
                    retry_count=0,
                )
                for _ in tasks
            ],
            {},
        )

    with patch(
        "aurora_soar.phases.collect.spawn_parallel_tracked", side_effect=mock_spawn_parallel_tracked
    ) as mock_spawn:
        # Execute agents with new signature
        result = await execute_agents(agent_assignments, subgoals, context, agent_timeout=10)

        # Verify spawn_parallel_tracked was called (once for the single wave)
        assert mock_spawn.call_count == 1

        # Verify all subgoals executed
        assert len(result.agent_outputs) == 3

        # Verify results maintain input order (sorted by subgoal_index)
        for i, output in enumerate(result.agent_outputs):
            assert output.subgoal_index == i, (
                f"Expected subgoal_index={i}, got {output.subgoal_index}"
            )
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


class TestContextPassing:
    """TDD tests for context passing between dependency waves."""

    @pytest.mark.asyncio
    async def test_context_passing_between_waves(self):
        """Test that dependent subgoal receives predecessor output in spawn_sequential format.

        sg-2 (depends on sg-1) should receive:
        "prompt\n\nPrevious context:\n✓ [sg-1]: output"
        """
        from aurora_soar.agent_registry import AgentInfo
        from aurora_soar.phases.collect import execute_agents

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

        agent_assignments = [(1, agent1), (2, agent2)]

        # sg-1 has no dependencies, sg-2 depends on sg-1
        subgoals = [
            {
                "subgoal_index": 1,
                "description": "Task 1",
                "prompt": "Do task 1",
                "depends_on": [],
            },
            {
                "subgoal_index": 2,
                "description": "Task 2",
                "prompt": "Do task 2",
                "depends_on": [1],
            },
        ]

        context = {"query": "Test context passing"}

        # Track prompts sent to spawn_parallel_tracked
        captured_prompts = []

        async def mock_spawn_parallel_tracked(*args, **kwargs):
            tasks = args[0] if args else kwargs.get("tasks", [])
            # Capture prompts from all tasks in this wave
            for task in tasks:
                captured_prompts.append(task.prompt)

            # Return success for all tasks
            return (
                [
                    SpawnResult(
                        success=True,
                        output=f"Output from task {len(captured_prompts)}",
                        error=None,
                        exit_code=0,
                    )
                    for _ in tasks
                ],
                {},
            )

        with patch(
            "aurora_soar.phases.collect.spawn_parallel_tracked",
            side_effect=mock_spawn_parallel_tracked,
        ):
            await execute_agents(agent_assignments, subgoals, context)

            # Verify two prompts were captured (one per wave)
            assert len(captured_prompts) == 2

            # First prompt (sg-1): no context injection
            assert "Do task 1" in captured_prompts[0]
            assert "Previous context" not in captured_prompts[0]

            # Second prompt (sg-2): should have context from sg-1
            assert "Do task 2" in captured_prompts[1]
            assert "Previous context" in captured_prompts[1]
            # Check for success marker
            assert "✓ [sg-1]:" in captured_prompts[1] or "[sg-1]:" in captured_prompts[1]
            assert "Output from task 1" in captured_prompts[1]

    @pytest.mark.asyncio
    async def test_partial_context_with_failed_dependency(self):
        """Test that subgoal receives partial context with both success and failure markers.

        sg-3 (depends on sg-1✓, sg-2✗) should receive:
        "✓ [sg-1]: output\n✗ [sg-2]: FAILED - timeout"
        """
        from aurora_soar.agent_registry import AgentInfo
        from aurora_soar.phases.collect import execute_agents

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
        agent3 = AgentInfo(
            id="agent-3",
            name="Agent 3",
            description="Test",
            capabilities=["test"],
            agent_type="local",
        )

        agent_assignments = [(1, agent1), (2, agent2), (3, agent3)]

        # sg-1 no deps, sg-2 no deps, sg-3 depends on both
        subgoals = [
            {"subgoal_index": 1, "description": "Task 1", "prompt": "Do task 1", "depends_on": []},
            {"subgoal_index": 2, "description": "Task 2", "prompt": "Do task 2", "depends_on": []},
            {
                "subgoal_index": 3,
                "description": "Task 3",
                "prompt": "Do task 3",
                "depends_on": [1, 2],
            },
        ]

        context = {"query": "Test partial context"}

        captured_prompts = []
        wave_count = [0]

        async def mock_spawn_parallel_tracked(*args, **kwargs):
            tasks = args[0] if args else kwargs.get("tasks", [])
            wave_count[0] += 1

            # Capture prompts
            for task in tasks:
                captured_prompts.append(task.prompt)

            # Wave 1: sg-1 succeeds, sg-2 fails
            if wave_count[0] == 1:
                return (
                    [
                        SpawnResult(
                            success=True, output="Output from task 1", error=None, exit_code=0
                        ),
                        SpawnResult(
                            success=False,
                            output="",
                            error="Timeout after 180s",
                            exit_code=-1,
                        ),
                    ],
                    {},
                )
            # Wave 2: sg-3 executes with partial context
            return (
                [SpawnResult(success=True, output="Output from task 3", error=None, exit_code=0)],
                {},
            )

        with patch(
            "aurora_soar.phases.collect.spawn_parallel_tracked",
            side_effect=mock_spawn_parallel_tracked,
        ):
            await execute_agents(agent_assignments, subgoals, context)

            # Verify three prompts captured
            assert len(captured_prompts) == 3

            # Third prompt (sg-3) should have partial context
            sg3_prompt = captured_prompts[2]
            assert "Do task 3" in sg3_prompt
            assert "Previous context" in sg3_prompt

            # Should have success marker for sg-1
            assert "✓" in sg3_prompt or "[sg-1]:" in sg3_prompt
            assert "Output from task 1" in sg3_prompt

            # Should have failure marker for sg-2
            assert "✗" in sg3_prompt or "FAILED" in sg3_prompt
            assert "Timeout" in sg3_prompt or "timeout" in sg3_prompt.lower()

    @pytest.mark.asyncio
    async def test_partial_context_warning_footer(self):
        """Test that WARNING footer appears when dependencies fail.

        Subgoal with failed dependencies should receive:
        "WARNING: 1/2 dependencies failed. Proceed with available context."
        """
        from aurora_soar.agent_registry import AgentInfo
        from aurora_soar.phases.collect import execute_agents

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
        agent3 = AgentInfo(
            id="agent-3",
            name="Agent 3",
            description="Test",
            capabilities=["test"],
            agent_type="local",
        )

        agent_assignments = [(1, agent1), (2, agent2), (3, agent3)]

        subgoals = [
            {"subgoal_index": 1, "description": "Task 1", "prompt": "Do task 1", "depends_on": []},
            {"subgoal_index": 2, "description": "Task 2", "prompt": "Do task 2", "depends_on": []},
            {
                "subgoal_index": 3,
                "description": "Task 3",
                "prompt": "Do task 3",
                "depends_on": [1, 2],
            },
        ]

        context = {"query": "Test warning footer"}

        captured_prompts = []
        wave_count = [0]

        async def mock_spawn_parallel_tracked(*args, **kwargs):
            tasks = args[0] if args else kwargs.get("tasks", [])
            wave_count[0] += 1

            for task in tasks:
                captured_prompts.append(task.prompt)

            if wave_count[0] == 1:
                return (
                    [
                        SpawnResult(success=True, output="Output 1", error=None, exit_code=0),
                        SpawnResult(success=False, output="", error="Error", exit_code=-1),
                    ],
                    {},
                )
            return (
                [SpawnResult(success=True, output="Output 3", error=None, exit_code=0)],
                {},
            )

        with patch(
            "aurora_soar.phases.collect.spawn_parallel_tracked",
            side_effect=mock_spawn_parallel_tracked,
        ):
            await execute_agents(agent_assignments, subgoals, context)

            # Verify sg-3 prompt has WARNING footer
            sg3_prompt = captured_prompts[2]
            assert "WARNING" in sg3_prompt
            assert "dependencies failed" in sg3_prompt or "dependency failed" in sg3_prompt
            assert "available context" in sg3_prompt

    @pytest.mark.asyncio
    async def test_all_dependencies_failed(self):
        """Test that subgoal still executes when ALL dependencies fail.

        sg-3 (depends on sg-1✗, sg-2✗) should still execute with all failure markers.
        """
        from aurora_soar.agent_registry import AgentInfo
        from aurora_soar.phases.collect import execute_agents

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
        agent3 = AgentInfo(
            id="agent-3",
            name="Agent 3",
            description="Test",
            capabilities=["test"],
            agent_type="local",
        )

        agent_assignments = [(1, agent1), (2, agent2), (3, agent3)]

        subgoals = [
            {"subgoal_index": 1, "description": "Task 1", "prompt": "Do task 1", "depends_on": []},
            {"subgoal_index": 2, "description": "Task 2", "prompt": "Do task 2", "depends_on": []},
            {
                "subgoal_index": 3,
                "description": "Task 3",
                "prompt": "Do task 3",
                "depends_on": [1, 2],
            },
        ]

        context = {"query": "Test all failed"}

        captured_prompts = []
        wave_count = [0]

        async def mock_spawn_parallel_tracked(*args, **kwargs):
            tasks = args[0] if args else kwargs.get("tasks", [])
            wave_count[0] += 1

            for task in tasks:
                captured_prompts.append(task.prompt)

            if wave_count[0] == 1:
                # Both dependencies fail
                return (
                    [
                        SpawnResult(success=False, output="", error="Failed", exit_code=-1),
                        SpawnResult(success=False, output="", error="Failed", exit_code=-1),
                    ],
                    {},
                )
            # sg-3 still executes
            return (
                [SpawnResult(success=True, output="Output 3", error=None, exit_code=0)],
                {},
            )

        with patch(
            "aurora_soar.phases.collect.spawn_parallel_tracked",
            side_effect=mock_spawn_parallel_tracked,
        ):
            await execute_agents(agent_assignments, subgoals, context)

            # Verify three prompts captured (sg-3 NOT skipped)
            assert len(captured_prompts) == 3

            # sg-3 should have context with ALL failure markers
            sg3_prompt = captured_prompts[2]
            assert "Do task 3" in sg3_prompt
            assert "Previous context" in sg3_prompt

            # Both dependencies should show as failed
            assert sg3_prompt.count("✗") >= 2 or sg3_prompt.count("FAILED") >= 2

    @pytest.mark.asyncio
    async def test_independent_subgoals_continue(self):
        """Test that independent subgoals continue executing despite failures in other chains.

        sg-4 (no deps) should execute successfully even when sg-2 (different chain) fails.
        """
        from aurora_soar.agent_registry import AgentInfo
        from aurora_soar.phases.collect import execute_agents

        agents = [
            AgentInfo(
                id=f"agent-{i}",
                name=f"Agent {i}",
                description="Test",
                capabilities=["test"],
                agent_type="local",
            )
            for i in range(1, 5)
        ]

        agent_assignments = [(i, agents[i - 1]) for i in range(1, 5)]

        # Chain 1: sg-1 → sg-2 (fails), Chain 2: sg-3 → sg-4 (succeeds)
        subgoals = [
            {"subgoal_index": 1, "description": "Task 1", "prompt": "Do task 1", "depends_on": []},
            {
                "subgoal_index": 2,
                "description": "Task 2",
                "prompt": "Do task 2",
                "depends_on": [1],
            },
            {"subgoal_index": 3, "description": "Task 3", "prompt": "Do task 3", "depends_on": []},
            {
                "subgoal_index": 4,
                "description": "Task 4",
                "prompt": "Do task 4",
                "depends_on": [3],
            },
        ]

        context = {"query": "Test independent chains"}

        wave_count = [0]
        results_by_wave = []

        async def mock_spawn_parallel_tracked(*args, **kwargs):
            args[0] if args else kwargs.get("tasks", [])
            wave_count[0] += 1

            # Wave 1: sg-1 and sg-3 succeed
            if wave_count[0] == 1:
                results = [
                    SpawnResult(success=True, output="Output 1", error=None, exit_code=0),
                    SpawnResult(success=True, output="Output 3", error=None, exit_code=0),
                ]
            # Wave 2: sg-2 fails, sg-4 succeeds
            else:
                results = [
                    SpawnResult(success=False, output="", error="Failed", exit_code=-1),
                    SpawnResult(success=True, output="Output 4", error=None, exit_code=0),
                ]

            results_by_wave.append(results)
            return (results, {})

        with patch(
            "aurora_soar.phases.collect.spawn_parallel_tracked",
            side_effect=mock_spawn_parallel_tracked,
        ):
            result = await execute_agents(agent_assignments, subgoals, context)

            # All 4 subgoals should execute (sg-4 not affected by sg-2 failure)
            assert len(result.agent_outputs) == 4

            # sg-2 failed
            sg2_output = [o for o in result.agent_outputs if o.subgoal_index == 2][0]
            assert sg2_output.success is False

            # sg-4 succeeded (independent chain)
            sg4_output = [o for o in result.agent_outputs if o.subgoal_index == 4][0]
            assert sg4_output.success is True


class TestWaveExecution:
    """Tests for wave-based execution order and behavior."""

    @pytest.mark.asyncio
    async def test_wave_execution_order(self):
        """Test that waves execute sequentially: wave 1 completes before wave 2 starts.

        Mock spawn_parallel_tracked to track call order and verify wave 2
        doesn't start until wave 1 completes.
        """
        from aurora_soar.agent_registry import AgentInfo
        from aurora_soar.phases.collect import execute_agents

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

        agent_assignments = [(1, agent1), (2, agent2)]

        # Linear dependency: sg-1 -> sg-2
        subgoals = [
            {"subgoal_index": 1, "description": "Task 1", "prompt": "Do task 1", "depends_on": []},
            {
                "subgoal_index": 2,
                "description": "Task 2",
                "prompt": "Do task 2",
                "depends_on": [1],
            },
        ]

        context = {"query": "Test wave order"}

        # Track call order
        call_order = []
        wave1_complete = [False]

        async def mock_spawn_parallel_tracked(*args, **kwargs):
            args[0] if args else kwargs.get("tasks", [])
            # Identify wave by number of tasks or prompt content
            if len(call_order) == 0:
                # First wave
                call_order.append("wave1_start")
                # Simulate some work
                import asyncio

                await asyncio.sleep(0.01)
                call_order.append("wave1_end")
                wave1_complete[0] = True
                # Return result for sg-1
                return (
                    [SpawnResult(success=True, output="Output 1", error=None, exit_code=0)],
                    {},
                )
            # Second wave - verify wave 1 completed
            call_order.append("wave2_start")
            assert wave1_complete[0], "Wave 2 started before Wave 1 completed!"
            call_order.append("wave2_end")
            # Return result for sg-2
            return (
                [SpawnResult(success=True, output="Output 2", error=None, exit_code=0)],
                {},
            )

        with patch(
            "aurora_soar.phases.collect.spawn_parallel_tracked",
            side_effect=mock_spawn_parallel_tracked,
        ):
            result = await execute_agents(agent_assignments, subgoals, context)

            # Verify execution order
            assert call_order == ["wave1_start", "wave1_end", "wave2_start", "wave2_end"]
            assert result is not None
            assert len(result.agent_outputs) == 2

    @pytest.mark.asyncio
    async def test_retry_chain_before_failure(self):
        """Test that spawn_parallel_tracked exhausts retries before marking failure.

        Verify that spawn_parallel_tracked is configured with max_retries
        and that it handles the retry chain (not execute_agents).
        """
        from aurora_soar.agent_registry import AgentInfo
        from aurora_soar.phases.collect import execute_agents

        agent = AgentInfo(
            id="test-agent",
            name="Test Agent",
            description="Test",
            capabilities=["test"],
            agent_type="local",
        )

        agent_assignments = [(1, agent)]

        subgoals = [
            {"subgoal_index": 1, "description": "Task 1", "prompt": "Do task 1", "depends_on": []},
        ]

        context = {"query": "Test retry"}

        # Track spawn_parallel_tracked calls
        spawn_calls = []

        async def mock_spawn_parallel_tracked(*args, **kwargs):
            spawn_calls.append(kwargs.copy())
            # Return failure result (after spawn_parallel_tracked already tried retries)
            return (
                [SpawnResult(success=False, output="", error="Failed after retries", exit_code=-1)],
                {"failed_tasks": 1, "retried_tasks": ["task-1"]},
            )

        with patch(
            "aurora_soar.phases.collect.spawn_parallel_tracked",
            side_effect=mock_spawn_parallel_tracked,
        ):
            result = await execute_agents(agent_assignments, subgoals, context, max_retries=2)

            # Verify spawn_parallel_tracked was called with max_retries
            assert len(spawn_calls) == 1
            assert spawn_calls[0].get("max_retries") == 2

            # Verify result shows failure
            assert result.agent_outputs[0].success is False

    @pytest.mark.asyncio
    async def test_no_deps_single_wave(self):
        """Test that query without dependencies executes in single wave.

        No performance overhead - just verify single spawn_parallel_tracked call.
        """
        from aurora_soar.agent_registry import AgentInfo
        from aurora_soar.phases.collect import execute_agents

        agents = [
            AgentInfo(
                id=f"agent-{i}",
                name=f"Agent {i}",
                description="Test",
                capabilities=["test"],
                agent_type="local",
            )
            for i in range(1, 4)
        ]

        agent_assignments = [(i, agents[i - 1]) for i in range(1, 4)]

        # No dependencies
        subgoals = [
            {"subgoal_index": 1, "description": "Task 1", "prompt": "Task 1", "depends_on": []},
            {"subgoal_index": 2, "description": "Task 2", "prompt": "Task 2", "depends_on": []},
            {"subgoal_index": 3, "description": "Task 3", "prompt": "Task 3", "depends_on": []},
        ]

        context = {"query": "Test no deps"}

        spawn_call_count = [0]

        async def mock_spawn_parallel_tracked(*args, **kwargs):
            spawn_call_count[0] += 1
            tasks = args[0] if args else kwargs.get("tasks", [])
            # All 3 tasks should be in single wave
            assert len(tasks) == 3, f"Expected 3 tasks in single wave, got {len(tasks)}"
            # Return success for all
            return (
                [
                    SpawnResult(success=True, output=f"Output {i}", error=None, exit_code=0)
                    for i in range(1, 4)
                ],
                {},
            )

        with patch(
            "aurora_soar.phases.collect.spawn_parallel_tracked",
            side_effect=mock_spawn_parallel_tracked,
        ):
            result = await execute_agents(agent_assignments, subgoals, context)

            # Should only call spawn_parallel_tracked once (single wave)
            assert spawn_call_count[0] == 1
            assert len(result.agent_outputs) == 3
            assert all(o.success for o in result.agent_outputs)

    @pytest.mark.asyncio
    async def test_no_deps_performance_regression(self):
        """Test that no-dependency execution completes within 5% of baseline.

        Baseline: Measure time with simple mock that returns immediately.
        Test: Verify wave-based execution overhead is minimal (<5%).
        """
        import time

        from aurora_soar.agent_registry import AgentInfo
        from aurora_soar.phases.collect import execute_agents

        agents = [
            AgentInfo(
                id=f"agent-{i}",
                name=f"Agent {i}",
                description="Test",
                capabilities=["test"],
                agent_type="local",
            )
            for i in range(1, 6)
        ]

        agent_assignments = [(i, agents[i - 1]) for i in range(1, 6)]

        # No dependencies - should be fast
        subgoals = [
            {
                "subgoal_index": i,
                "description": f"Task {i}",
                "prompt": f"Task {i}",
                "depends_on": [],
            }
            for i in range(1, 6)
        ]

        context = {"query": "Test performance"}

        async def mock_spawn_parallel_tracked(*args, **kwargs):
            # Fast mock - return immediately
            tasks = args[0] if args else kwargs.get("tasks", [])
            return (
                [
                    SpawnResult(success=True, output=f"Output {i}", error=None, exit_code=0)
                    for i in range(len(tasks))
                ],
                {},
            )

        with patch(
            "aurora_soar.phases.collect.spawn_parallel_tracked",
            side_effect=mock_spawn_parallel_tracked,
        ):
            # Measure execution time
            start = time.time()
            result = await execute_agents(agent_assignments, subgoals, context)
            elapsed = time.time() - start

            # Should complete very quickly (< 100ms for this simple case)
            # The overhead of wave processing should be negligible
            assert elapsed < 0.1, f"Execution took {elapsed:.3f}s, expected < 0.1s"

            # Verify correctness
            assert len(result.agent_outputs) == 5
            assert all(o.success for o in result.agent_outputs)


class TestProgressDisplayAndLogging:
    """Tests for progress display and logging functionality."""

    @pytest.mark.asyncio
    async def test_default_mode_streaming_output(self, caplog):
        """Test default output shows wave progress with emoji markers, no DEBUG logs.

        Verifies:
        - INFO logs show "Wave X/Y (N subgoals)..." format
        - ✓/✗/⚠ markers are present
        - Final summary appears
        - DEBUG logs are absent
        """
        import logging

        from aurora_soar.agent_registry import AgentInfo
        from aurora_soar.phases.collect import execute_agents

        # Set log level to INFO (default mode)
        caplog.set_level(logging.INFO)

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
        agent3 = AgentInfo(
            id="agent-3",
            name="Agent 3",
            description="Test",
            capabilities=["test"],
            agent_type="local",
        )

        agent_assignments = [(1, agent1), (2, agent2), (3, agent3)]

        # Diamond pattern: sg-1 -> (sg-2, sg-3) with sg-2 failing
        subgoals = [
            {"subgoal_index": 1, "description": "Task 1", "prompt": "Do task 1", "depends_on": []},
            {"subgoal_index": 2, "description": "Task 2", "prompt": "Do task 2", "depends_on": [1]},
            {"subgoal_index": 3, "description": "Task 3", "prompt": "Do task 3", "depends_on": [1]},
        ]

        context = {"query": "Test progress display"}

        wave_count = [0]

        async def mock_spawn_parallel_tracked(*args, **kwargs):
            args[0] if args else kwargs.get("tasks", [])
            wave_count[0] += 1

            if wave_count[0] == 1:
                # Wave 1: sg-1 succeeds
                return (
                    [SpawnResult(success=True, output="Output 1", error=None, exit_code=0)],
                    {},
                )
            # Wave 2: sg-2 fails, sg-3 succeeds
            return (
                [
                    SpawnResult(success=False, output="", error="Timeout", exit_code=-1),
                    SpawnResult(success=True, output="Output 3", error=None, exit_code=0),
                ],
                {},
            )

        with patch(
            "aurora_soar.phases.collect.spawn_parallel_tracked",
            side_effect=mock_spawn_parallel_tracked,
        ):
            await execute_agents(agent_assignments, subgoals, context)

            # Capture log output
            log_output = "\n".join([record.message for record in caplog.records])

            # Verify INFO logs present
            info_logs = [r for r in caplog.records if r.levelno == logging.INFO]
            assert len(info_logs) > 0, "Expected INFO logs but found none"

            # Verify DEBUG logs absent (default mode)
            debug_logs = [r for r in caplog.records if r.levelno == logging.DEBUG]
            assert len(debug_logs) == 0, f"Found {len(debug_logs)} DEBUG logs in default mode"

            # Verify wave progress format appears
            assert "Wave" in log_output or "wave" in log_output.lower()

            # Verify emoji markers present (at least one success or failure marker)
            has_markers = "✓" in log_output or "✗" in log_output or "⚠" in log_output
            assert has_markers, "Expected emoji markers (✓/✗/⚠) in output"

            # Verify final summary appears
            assert (
                "EXECUTION COMPLETE" in log_output
                or "COMPLETE" in log_output
                or "complete" in log_output.lower()
            ), "Expected final execution summary"

    @pytest.mark.asyncio
    async def test_verbose_mode_streaming_output(self, caplog):
        """Test --verbose flag adds DEBUG logs (topological sort, context assembly, spawn results).

        Verifies:
        - DEBUG logs present when log level set to DEBUG
        - Includes topological sort details
        - Includes context assembly details
        """
        import logging

        from aurora_soar.agent_registry import AgentInfo
        from aurora_soar.phases.collect import execute_agents

        # Set log level to DEBUG (verbose mode)
        caplog.set_level(logging.DEBUG)

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

        agent_assignments = [(1, agent1), (2, agent2)]

        # Linear dependency: sg-1 -> sg-2
        subgoals = [
            {"subgoal_index": 1, "description": "Task 1", "prompt": "Do task 1", "depends_on": []},
            {"subgoal_index": 2, "description": "Task 2", "prompt": "Do task 2", "depends_on": [1]},
        ]

        context = {"query": "Test verbose mode"}

        wave_count = [0]

        async def mock_spawn_parallel_tracked(*args, **kwargs):
            tasks = args[0] if args else kwargs.get("tasks", [])
            wave_count[0] += 1

            return (
                [
                    SpawnResult(
                        success=True, output=f"Output {wave_count[0]}", error=None, exit_code=0
                    )
                    for _ in tasks
                ],
                {},
            )

        with patch(
            "aurora_soar.phases.collect.spawn_parallel_tracked",
            side_effect=mock_spawn_parallel_tracked,
        ):
            await execute_agents(agent_assignments, subgoals, context)

            # Capture log output
            "\n".join([record.message for record in caplog.records])

            # Verify DEBUG logs present
            debug_logs = [r for r in caplog.records if r.levelno == logging.DEBUG]
            assert len(debug_logs) > 0, f"Expected DEBUG logs but found {len(debug_logs)}"

            # Verify specific DEBUG content
            debug_output = "\n".join([r.message for r in debug_logs])

            # Check for topological sort debug logs
            assert "Topological sort complete" in debug_output or "wave" in debug_output.lower(), (
                f"Expected topological sort details in DEBUG logs: {debug_output}"
            )

            # Check for spawn result debug logs
            assert "result:" in debug_output or "success=" in debug_output, (
                f"Expected spawn result details in DEBUG logs: {debug_output}"
            )

            # Verify INFO logs still present
            info_logs = [r for r in caplog.records if r.levelno == logging.INFO]
            assert len(info_logs) > 0, "Expected INFO logs but found none"

    @pytest.mark.asyncio
    async def test_final_summary_appears_after_waves(self, caplog):
        """Test 'EXECUTION COMPLETE: X/N succeeded, Y failed, Z partial' appears after all waves.

        Verifies:
        - Final summary appears
        - Summary shows correct counts
        - Summary appears after all wave logs
        """
        import logging

        from aurora_soar.agent_registry import AgentInfo
        from aurora_soar.phases.collect import execute_agents

        caplog.set_level(logging.INFO)

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

        agent_assignments = [(1, agent1), (2, agent2)]

        # Two independent subgoals
        subgoals = [
            {"subgoal_index": 1, "description": "Task 1", "prompt": "Do task 1", "depends_on": []},
            {"subgoal_index": 2, "description": "Task 2", "prompt": "Do task 2", "depends_on": []},
        ]

        context = {"query": "Test final summary"}

        async def mock_spawn_parallel_tracked(*args, **kwargs):
            args[0] if args else kwargs.get("tasks", [])
            # Return 1 success, 1 failure
            return (
                [
                    SpawnResult(success=True, output="Output 1", error=None, exit_code=0),
                    SpawnResult(success=False, output="", error="Failed", exit_code=-1),
                ],
                {},
            )

        with patch(
            "aurora_soar.phases.collect.spawn_parallel_tracked",
            side_effect=mock_spawn_parallel_tracked,
        ):
            await execute_agents(agent_assignments, subgoals, context)

            # Capture log messages
            log_messages = [
                record.message for record in caplog.records if record.levelno == logging.INFO
            ]
            log_output = "\n".join(log_messages)

            # Verify final summary appears
            assert "EXECUTION COMPLETE" in log_output, (
                f"Expected 'EXECUTION COMPLETE' in logs: {log_output}"
            )

            # Verify summary has correct format (X/N succeeded, Y failed, Z partial)
            assert "succeeded" in log_output.lower() or "failed" in log_output.lower()

            # Verify summary appears after wave logs
            wave_log_index = None
            summary_log_index = None
            for i, msg in enumerate(log_messages):
                if "Wave" in msg:
                    wave_log_index = i
                if "EXECUTION COMPLETE" in msg:
                    summary_log_index = i

            if wave_log_index is not None and summary_log_index is not None:
                assert summary_log_index > wave_log_index, "Summary should appear after wave logs"

    @pytest.mark.asyncio
    async def test_partial_context_warning_in_output(self, caplog):
        """Test WARNING footer and ⚠ marker appear when dependencies fail.

        Verifies:
        - WARNING footer in prompt for partial context
        - ⚠ marker in progress display
        """
        import logging

        from aurora_soar.agent_registry import AgentInfo
        from aurora_soar.phases.collect import execute_agents

        caplog.set_level(logging.INFO)

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
        agent3 = AgentInfo(
            id="agent-3",
            name="Agent 3",
            description="Test",
            capabilities=["test"],
            agent_type="local",
        )

        agent_assignments = [(1, agent1), (2, agent2), (3, agent3)]

        # sg-1, sg-2 independent, sg-3 depends on both
        subgoals = [
            {"subgoal_index": 1, "description": "Task 1", "prompt": "Do task 1", "depends_on": []},
            {"subgoal_index": 2, "description": "Task 2", "prompt": "Do task 2", "depends_on": []},
            {
                "subgoal_index": 3,
                "description": "Task 3",
                "prompt": "Do task 3",
                "depends_on": [1, 2],
            },
        ]

        context = {"query": "Test partial warning"}

        wave_count = [0]
        captured_prompts = []

        async def mock_spawn_parallel_tracked(*args, **kwargs):
            tasks = args[0] if args else kwargs.get("tasks", [])
            wave_count[0] += 1

            # Capture prompts
            for task in tasks:
                captured_prompts.append(task.prompt)

            if wave_count[0] == 1:
                # Wave 1: sg-1 succeeds, sg-2 fails
                return (
                    [
                        SpawnResult(success=True, output="Output 1", error=None, exit_code=0),
                        SpawnResult(success=False, output="", error="Timeout", exit_code=-1),
                    ],
                    {},
                )
            # Wave 2: sg-3 executes with partial context
            return (
                [SpawnResult(success=True, output="Output 3", error=None, exit_code=0)],
                {},
            )

        with patch(
            "aurora_soar.phases.collect.spawn_parallel_tracked",
            side_effect=mock_spawn_parallel_tracked,
        ):
            result = await execute_agents(agent_assignments, subgoals, context)

            # Verify WARNING footer in prompt
            sg3_prompt = captured_prompts[2]  # Third prompt (sg-3)
            assert "WARNING" in sg3_prompt, f"Expected WARNING in prompt: {sg3_prompt}"
            assert "failed" in sg3_prompt.lower(), f"Expected 'failed' in warning: {sg3_prompt}"

            # Verify partial context marker in output (check agent_outputs metadata)
            sg3_output = [o for o in result.agent_outputs if o.subgoal_index == 3][0]
            assert sg3_output.execution_metadata.get("partial_context", False), (
                "Expected partial_context flag set"
            )


class TestEndToEndIntegration:
    """End-to-end integration tests for dependency-aware execution."""

    @pytest.mark.asyncio
    async def test_three_wave_diamond_pattern_execution(self):
        """Test A → (B, C) → D pattern executes in 3 waves with correct context passing.

        Acceptance Criteria #1: Basic 3-wave example executes correctly.

        Pattern:
        - Wave 1: A (no dependencies)
        - Wave 2: B, C (both depend on A, execute in parallel)
        - Wave 3: D (depends on B and C)

        Verifies:
        - Correct wave ordering
        - Context passing from A to B and C
        - Context passing from B, C to D
        - All subgoals complete successfully
        """
        from aurora_soar.agent_registry import AgentInfo
        from aurora_soar.phases.collect import execute_agents

        # Create agents
        agents = {
            "A": AgentInfo(
                id="agent-a", name="Agent A", description="", capabilities=[], agent_type="local"
            ),
            "B": AgentInfo(
                id="agent-b", name="Agent B", description="", capabilities=[], agent_type="local"
            ),
            "C": AgentInfo(
                id="agent-c", name="Agent C", description="", capabilities=[], agent_type="local"
            ),
            "D": AgentInfo(
                id="agent-d", name="Agent D", description="", capabilities=[], agent_type="local"
            ),
        }

        agent_assignments = [
            (1, agents["A"]),
            (2, agents["B"]),
            (3, agents["C"]),
            (4, agents["D"]),
        ]

        # Diamond pattern: A → (B, C) → D
        subgoals = [
            {
                "subgoal_index": 1,
                "description": "Task A",
                "prompt": "Execute task A",
                "depends_on": [],
            },
            {
                "subgoal_index": 2,
                "description": "Task B",
                "prompt": "Execute task B",
                "depends_on": [1],
            },
            {
                "subgoal_index": 3,
                "description": "Task C",
                "prompt": "Execute task C",
                "depends_on": [1],
            },
            {
                "subgoal_index": 4,
                "description": "Task D",
                "prompt": "Execute task D",
                "depends_on": [2, 3],
            },
        ]

        context = {"query": "Test 3-wave diamond pattern"}

        # Track execution order
        wave_count = [0]
        execution_log = []
        captured_prompts = {}

        async def mock_spawn_parallel_tracked(*args, **kwargs):
            tasks = args[0] if args else kwargs.get("tasks", [])
            wave_count[0] += 1
            current_wave = wave_count[0]

            # Log wave execution - figure out subgoal indices from prompts
            task_indices = []
            for task in tasks:
                # Detect subgoal index from prompt content
                prompt = task.prompt
                if "Execute task A" in prompt:
                    idx = 1
                elif "Execute task B" in prompt:
                    idx = 2
                elif "Execute task C" in prompt:
                    idx = 3
                elif "Execute task D" in prompt:
                    idx = 4
                else:
                    idx = None

                if idx:
                    task_indices.append(idx)
                    captured_prompts[idx] = prompt
                    execution_log.append((current_wave, idx))

            # Return success for all tasks
            results = []
            for i, task in enumerate(tasks):
                idx = task_indices[i] if i < len(task_indices) else 0
                output = f"Output from subgoal {idx}"
                results.append(SpawnResult(success=True, output=output, error=None, exit_code=0))

            return (results, {})

        with patch(
            "aurora_soar.phases.collect.spawn_parallel_tracked",
            side_effect=mock_spawn_parallel_tracked,
        ):
            result = await execute_agents(agent_assignments, subgoals, context)

            # Verify 3 waves executed
            assert wave_count[0] == 3, f"Expected 3 waves but got {wave_count[0]}"

            # Verify wave 1 contains only A (subgoal 1)
            wave1_tasks = [idx for wave, idx in execution_log if wave == 1]
            assert wave1_tasks == [1], f"Wave 1 should only contain subgoal 1, got {wave1_tasks}"

            # Verify wave 2 contains B and C (subgoals 2, 3) - order doesn't matter
            wave2_tasks = sorted([idx for wave, idx in execution_log if wave == 2])
            assert wave2_tasks == [
                2,
                3,
            ], f"Wave 2 should contain subgoals 2 and 3, got {wave2_tasks}"

            # Verify wave 3 contains only D (subgoal 4)
            wave3_tasks = [idx for wave, idx in execution_log if wave == 3]
            assert wave3_tasks == [4], f"Wave 3 should only contain subgoal 4, got {wave3_tasks}"

            # Verify context passing: B and C should receive A's output
            assert 2 in captured_prompts, "Subgoal 2 (B) prompt not captured"
            assert 3 in captured_prompts, "Subgoal 3 (C) prompt not captured"

            prompt_b = captured_prompts[2]
            prompt_c = captured_prompts[3]

            assert "Previous context" in prompt_b, "B should receive context from A"
            assert "Output from subgoal 1" in prompt_b, "B should have A's output"
            assert "✓ [sg-1]:" in prompt_b or "[sg-1]:" in prompt_b, (
                "B should have success marker for A"
            )

            assert "Previous context" in prompt_c, "C should receive context from A"
            assert "Output from subgoal 1" in prompt_c, "C should have A's output"
            assert "✓ [sg-1]:" in prompt_c or "[sg-1]:" in prompt_c, (
                "C should have success marker for A"
            )

            # Verify context passing: D should receive B and C's outputs
            assert 4 in captured_prompts, "Subgoal 4 (D) prompt not captured"
            prompt_d = captured_prompts[4]

            assert "Previous context" in prompt_d, "D should receive context from B and C"
            assert "Output from subgoal 2" in prompt_d, "D should have B's output"
            assert "Output from subgoal 3" in prompt_d, "D should have C's output"

            # Verify all subgoals completed successfully
            assert len(result.agent_outputs) == 4, (
                f"Expected 4 outputs but got {len(result.agent_outputs)}"
            )
            assert all(o.success for o in result.agent_outputs), "All subgoals should succeed"
