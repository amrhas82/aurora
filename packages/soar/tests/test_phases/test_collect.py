"""Tests for SOAR collect phase (agent execution)."""

from unittest.mock import patch

import pytest

from aurora_soar.agent_registry import AgentInfo
from aurora_soar.phases.collect import CollectResult, execute_agents, topological_sort
from aurora_spawner.models import SpawnResult


# ============================================================================
# Helpers
# ============================================================================


def _agent(id: str) -> AgentInfo:
    return AgentInfo(id=id, name=id, description="", capabilities=[], agent_type="local")


def _subgoal(index: int, prompt: str, depends_on: list[int] | None = None) -> dict:
    return {
        "subgoal_index": index,
        "description": prompt,
        "prompt": prompt,
        "depends_on": depends_on or [],
    }


async def _mock_spawn_ok(*args, **kwargs):
    """Return success for every task in the wave."""
    tasks = args[0] if args else kwargs.get("tasks", [])
    return (
        [SpawnResult(success=True, output=f"Output {i}", error=None, exit_code=0) for i in range(len(tasks))],
        {},
    )


# ============================================================================
# Topological Sort
# ============================================================================


class TestTopologicalSort:
    def test_no_deps_single_wave(self):
        waves = topological_sort([
            _subgoal(1, "A"),
            _subgoal(2, "B"),
            _subgoal(3, "C"),
        ])
        assert len(waves) == 1
        assert {sg["subgoal_index"] for sg in waves[0]} == {1, 2, 3}

    def test_linear_deps_three_waves(self):
        waves = topological_sort([
            _subgoal(1, "A"),
            _subgoal(2, "B", depends_on=[1]),
            _subgoal(3, "C", depends_on=[2]),
        ])
        assert len(waves) == 3
        assert waves[0][0]["subgoal_index"] == 1
        assert waves[1][0]["subgoal_index"] == 2
        assert waves[2][0]["subgoal_index"] == 3

    def test_diamond_deps(self):
        waves = topological_sort([
            _subgoal(1, "A"),
            _subgoal(2, "B", depends_on=[1]),
            _subgoal(3, "C", depends_on=[1]),
            _subgoal(4, "D", depends_on=[2, 3]),
        ])
        assert len(waves) == 3
        assert waves[0][0]["subgoal_index"] == 1
        assert {sg["subgoal_index"] for sg in waves[1]} == {2, 3}
        assert waves[2][0]["subgoal_index"] == 4

    def test_parallel_chains(self):
        waves = topological_sort([
            _subgoal(1, "A"),
            _subgoal(2, "B", depends_on=[1]),
            _subgoal(3, "C"),
            _subgoal(4, "D", depends_on=[3]),
        ])
        assert len(waves) == 2
        assert {sg["subgoal_index"] for sg in waves[0]} == {1, 3}
        assert {sg["subgoal_index"] for sg in waves[1]} == {2, 4}


# ============================================================================
# Wave Execution
# ============================================================================


class TestWaveExecution:
    @pytest.mark.asyncio
    async def test_wave_execution_order(self):
        """Waves execute sequentially: wave 1 completes before wave 2 starts."""
        agent_assignments = [(1, _agent("a1")), (2, _agent("a2"))]
        subgoals = [_subgoal(1, "Do task 1"), _subgoal(2, "Do task 2", depends_on=[1])]

        call_order = []
        wave1_complete = [False]

        async def mock_spawn(*args, **kwargs):
            if len(call_order) == 0:
                call_order.append("wave1_start")
                import asyncio
                await asyncio.sleep(0.01)
                call_order.append("wave1_end")
                wave1_complete[0] = True
                return ([SpawnResult(success=True, output="Out 1", error=None, exit_code=0)], {})
            call_order.append("wave2_start")
            assert wave1_complete[0], "Wave 2 started before Wave 1 completed!"
            call_order.append("wave2_end")
            return ([SpawnResult(success=True, output="Out 2", error=None, exit_code=0)], {})

        with patch("aurora_soar.phases.collect.spawn_parallel_tracked", side_effect=mock_spawn):
            result = await execute_agents(agent_assignments, subgoals, {"query": "test"})
            assert call_order == ["wave1_start", "wave1_end", "wave2_start", "wave2_end"]
            assert len(result.agent_outputs) == 2

    @pytest.mark.asyncio
    async def test_no_deps_single_spawn_call(self):
        """Independent subgoals execute in a single wave (single spawn call)."""
        agents = [(i, _agent(f"a{i}")) for i in range(1, 4)]
        subgoals = [_subgoal(i, f"Task {i}") for i in range(1, 4)]

        spawn_count = [0]

        async def mock_spawn(*args, **kwargs):
            spawn_count[0] += 1
            tasks = args[0] if args else kwargs.get("tasks", [])
            assert len(tasks) == 3
            return _mock_spawn_ok(*args, **kwargs) if False else (
                [SpawnResult(success=True, output=f"Out {i}", error=None, exit_code=0) for i in range(len(tasks))],
                {},
            )

        with patch("aurora_soar.phases.collect.spawn_parallel_tracked", side_effect=mock_spawn):
            result = await execute_agents(agents, subgoals, {"query": "test"})
            assert spawn_count[0] == 1
            assert len(result.agent_outputs) == 3
            assert all(o.success for o in result.agent_outputs)

    @pytest.mark.asyncio
    async def test_retry_passed_to_spawn(self):
        """max_retries is forwarded to spawn_parallel_tracked."""
        spawn_calls = []

        async def mock_spawn(*args, **kwargs):
            spawn_calls.append(kwargs.copy())
            return ([SpawnResult(success=False, output="", error="Failed", exit_code=-1)], {})

        with patch("aurora_soar.phases.collect.spawn_parallel_tracked", side_effect=mock_spawn):
            result = await execute_agents(
                [(1, _agent("a1"))], [_subgoal(1, "Task 1")], {"query": "test"}, max_retries=2,
            )
            assert spawn_calls[0].get("max_retries") == 2
            assert result.agent_outputs[0].success is False


# ============================================================================
# Context Passing Between Waves
# ============================================================================


class TestContextPassing:
    @pytest.mark.asyncio
    async def test_dependent_receives_predecessor_output(self):
        """sg-2 (depends on sg-1) receives predecessor output in prompt."""
        agent_assignments = [(1, _agent("a1")), (2, _agent("a2"))]
        subgoals = [_subgoal(1, "Do task 1"), _subgoal(2, "Do task 2", depends_on=[1])]

        captured_prompts = []

        async def mock_spawn(*args, **kwargs):
            tasks = args[0] if args else kwargs.get("tasks", [])
            for task in tasks:
                captured_prompts.append(task.prompt)
            return (
                [SpawnResult(success=True, output=f"Output from task {len(captured_prompts)}", error=None, exit_code=0)
                 for _ in tasks],
                {},
            )

        with patch("aurora_soar.phases.collect.spawn_parallel_tracked", side_effect=mock_spawn):
            await execute_agents(agent_assignments, subgoals, {"query": "test"})

            assert len(captured_prompts) == 2
            assert "Previous context" not in captured_prompts[0]
            assert "Previous context" in captured_prompts[1]
            assert "Output from task 1" in captured_prompts[1]

    @pytest.mark.asyncio
    async def test_partial_context_on_failed_dependency(self):
        """sg-3 (depends on sg-1 ok, sg-2 fail) gets both success and failure markers."""
        agent_assignments = [(1, _agent("a1")), (2, _agent("a2")), (3, _agent("a3"))]
        subgoals = [
            _subgoal(1, "Do task 1"),
            _subgoal(2, "Do task 2"),
            _subgoal(3, "Do task 3", depends_on=[1, 2]),
        ]

        captured_prompts = []
        wave_count = [0]

        async def mock_spawn(*args, **kwargs):
            tasks = args[0] if args else kwargs.get("tasks", [])
            wave_count[0] += 1
            for task in tasks:
                captured_prompts.append(task.prompt)
            if wave_count[0] == 1:
                return ([
                    SpawnResult(success=True, output="Output from task 1", error=None, exit_code=0),
                    SpawnResult(success=False, output="", error="Timeout after 180s", exit_code=-1),
                ], {})
            return ([SpawnResult(success=True, output="Output 3", error=None, exit_code=0)], {})

        with patch("aurora_soar.phases.collect.spawn_parallel_tracked", side_effect=mock_spawn):
            await execute_agents(agent_assignments, subgoals, {"query": "test"})

            sg3_prompt = captured_prompts[2]
            assert "Previous context" in sg3_prompt
            assert "Output from task 1" in sg3_prompt
            assert ("✓" in sg3_prompt or "[sg-1]:" in sg3_prompt)
            assert ("✗" in sg3_prompt or "FAILED" in sg3_prompt)
            assert "WARNING" in sg3_prompt

    @pytest.mark.asyncio
    async def test_all_dependencies_failed_still_executes(self):
        """Subgoal executes even when ALL dependencies fail."""
        agent_assignments = [(1, _agent("a1")), (2, _agent("a2")), (3, _agent("a3"))]
        subgoals = [
            _subgoal(1, "Do task 1"),
            _subgoal(2, "Do task 2"),
            _subgoal(3, "Do task 3", depends_on=[1, 2]),
        ]

        captured_prompts = []
        wave_count = [0]

        async def mock_spawn(*args, **kwargs):
            tasks = args[0] if args else kwargs.get("tasks", [])
            wave_count[0] += 1
            for task in tasks:
                captured_prompts.append(task.prompt)
            if wave_count[0] == 1:
                return ([
                    SpawnResult(success=False, output="", error="Failed", exit_code=-1),
                    SpawnResult(success=False, output="", error="Failed", exit_code=-1),
                ], {})
            return ([SpawnResult(success=True, output="Output 3", error=None, exit_code=0)], {})

        with patch("aurora_soar.phases.collect.spawn_parallel_tracked", side_effect=mock_spawn):
            await execute_agents(agent_assignments, subgoals, {"query": "test"})

            assert len(captured_prompts) == 3  # sg-3 NOT skipped
            sg3_prompt = captured_prompts[2]
            assert "Previous context" in sg3_prompt
            assert sg3_prompt.count("✗") >= 2 or sg3_prompt.count("FAILED") >= 2

    @pytest.mark.asyncio
    async def test_independent_chains_isolated(self):
        """Failure in one chain does not affect independent chains."""
        agents = [(i, _agent(f"a{i}")) for i in range(1, 5)]
        subgoals = [
            _subgoal(1, "Do task 1"),
            _subgoal(2, "Do task 2", depends_on=[1]),
            _subgoal(3, "Do task 3"),
            _subgoal(4, "Do task 4", depends_on=[3]),
        ]

        wave_count = [0]

        async def mock_spawn(*args, **kwargs):
            wave_count[0] += 1
            if wave_count[0] == 1:
                return ([
                    SpawnResult(success=True, output="Output 1", error=None, exit_code=0),
                    SpawnResult(success=True, output="Output 3", error=None, exit_code=0),
                ], {})
            return ([
                SpawnResult(success=False, output="", error="Failed", exit_code=-1),
                SpawnResult(success=True, output="Output 4", error=None, exit_code=0),
            ], {})

        with patch("aurora_soar.phases.collect.spawn_parallel_tracked", side_effect=mock_spawn):
            result = await execute_agents(agents, subgoals, {"query": "test"})

            assert len(result.agent_outputs) == 4
            sg2 = [o for o in result.agent_outputs if o.subgoal_index == 2][0]
            sg4 = [o for o in result.agent_outputs if o.subgoal_index == 4][0]
            assert sg2.success is False
            assert sg4.success is True
