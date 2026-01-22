"""Tests for aur soar command parallel research spawning.

These tests verify that the soar command uses spawn_parallel() for complex
queries that require research across multiple subgoals.
"""

from unittest.mock import patch

import pytest


class TestSoarParallelResearch:
    """Test parallel research spawning in soar command."""

    def test_complex_query_uses_spawn_parallel_for_research(self):
        """Test that complex query uses spawn_parallel() for research."""
        # This test verifies the integration exists
        # The actual parallel spawning is in collect.py which we verified in task 2.3

        from aurora_soar.phases.collect import _execute_parallel_subgoals

        # Verify the function exists and is importable
        assert callable(_execute_parallel_subgoals)

        # The function signature should accept subgoals, agent_map, context, timeout, metadata
        import inspect

        sig = inspect.signature(_execute_parallel_subgoals)
        params = list(sig.parameters.keys())

        assert "subgoals" in params
        assert "agent_map" in params
        assert "context" in params
        assert "timeout" in params
        assert "metadata" in params

    @pytest.mark.asyncio
    async def test_parallel_subgoals_calls_spawn_parallel(self):
        """Test that _execute_parallel_subgoals calls spawn_parallel()."""
        from aurora_soar.agent_registry import AgentInfo
        from aurora_soar.phases.collect import _execute_parallel_subgoals
        from aurora_spawner.models import SpawnResult

        # Setup test data
        subgoals = [
            {"subgoal_index": 0, "description": "Research React"},
            {"subgoal_index": 1, "description": "Research Vue"},
            {"subgoal_index": 2, "description": "Research Angular"},
        ]

        agent_map = {
            0: AgentInfo(
                id="researcher",
                name="Researcher",
                description="Research agent",
                capabilities=[],
                agent_type="local",
            ),
            1: AgentInfo(
                id="researcher",
                name="Researcher",
                description="Research agent",
                capabilities=[],
                agent_type="local",
            ),
            2: AgentInfo(
                id="researcher",
                name="Researcher",
                description="Research agent",
                capabilities=[],
                agent_type="local",
            ),
        }

        context = {"query": "Compare React, Vue, and Angular"}
        timeout = 60.0
        metadata = {"failed_subgoals": 0}

        # Mock spawn_parallel to avoid actual execution
        with patch("aurora_soar.phases.collect.spawn_parallel") as mock_spawn_parallel:
            # Return successful results for all subgoals
            mock_spawn_parallel.return_value = [
                SpawnResult(success=True, output="React findings", error=None, exit_code=0),
                SpawnResult(success=True, output="Vue findings", error=None, exit_code=0),
                SpawnResult(success=True, output="Angular findings", error=None, exit_code=0),
            ]

            # Execute parallel subgoals
            outputs = await _execute_parallel_subgoals(
                subgoals,
                agent_map,
                context,
                timeout,
                metadata,
            )

            # Verify spawn_parallel was called
            assert mock_spawn_parallel.called
            assert mock_spawn_parallel.call_count == 1

            # Verify it was called with correct number of tasks
            call_args = mock_spawn_parallel.call_args
            spawn_tasks = call_args[0][0]  # First positional argument
            assert len(spawn_tasks) == 3

            # Verify max_concurrent parameter
            assert call_args.kwargs.get("max_concurrent") == 5

            # Verify outputs
            assert len(outputs) == 3
            assert all(output.success for output in outputs)

    @pytest.mark.asyncio
    async def test_parallel_execution_handles_failures_gracefully(self):
        """Test that parallel results properly handle failures."""
        from aurora_soar.agent_registry import AgentInfo
        from aurora_soar.phases.collect import _execute_parallel_subgoals
        from aurora_spawner.models import SpawnResult

        # Setup test data with one failing subgoal
        subgoals = [
            {"subgoal_index": 0, "description": "Successful task"},
            {"subgoal_index": 1, "description": "Failing task"},
        ]

        agent_map = {
            0: AgentInfo(
                id="agent1",
                name="Agent 1",
                description="Agent",
                capabilities=[],
                agent_type="local",
            ),
            1: AgentInfo(
                id="agent2",
                name="Agent 2",
                description="Agent",
                capabilities=[],
                agent_type="local",
            ),
        }

        context = {"query": "Test query"}
        timeout = 60.0
        metadata = {"failed_subgoals": 0}

        # Mock spawn_parallel with mixed results
        with patch("aurora_soar.phases.collect.spawn_parallel") as mock_spawn_parallel:
            mock_spawn_parallel.return_value = [
                SpawnResult(success=True, output="Success", error=None, exit_code=0),
                SpawnResult(success=False, output="", error="Failed", exit_code=1),
            ]

            # Execute parallel subgoals
            outputs = await _execute_parallel_subgoals(
                subgoals,
                agent_map,
                context,
                timeout,
                metadata,
            )

            # Verify outputs
            assert len(outputs) == 2
            assert outputs[0].success is True
            assert outputs[1].success is False

            # Verify failure was counted in metadata
            assert metadata["failed_subgoals"] == 1

    def test_trivial_query_still_works(self):
        """Test that trivial queries don't require parallel execution."""
        # Trivial queries may not go through collect phase at all
        # They might be handled directly in assess -> respond flow

        from aurora_soar.phases.assess import assess_complexity

        # Test a trivial query
        trivial_query = "What is 2 + 2?"

        # This should assess as low complexity
        assessment = assess_complexity(trivial_query, llm_client=None)

        # Verify it's assessed as simple/trivial (score should be low)
        assert "complexity" in assessment
        assert "score" in assessment

        # Low score indicates simple query
        score = assessment.get("score", 100)
        assert score < 20, f"Trivial query should have low complexity score, got {score}"

    @pytest.mark.asyncio
    async def test_parallel_results_maintain_order(self):
        """Test that parallel execution returns results in input order."""
        from aurora_soar.agent_registry import AgentInfo
        from aurora_soar.phases.collect import _execute_parallel_subgoals
        from aurora_spawner.models import SpawnResult

        # Setup test data
        subgoals = [
            {"subgoal_index": 0, "description": "First"},
            {"subgoal_index": 1, "description": "Second"},
            {"subgoal_index": 2, "description": "Third"},
        ]

        agent_map = {
            i: AgentInfo(
                id=f"agent{i}",
                name=f"Agent {i}",
                description="Agent",
                capabilities=[],
                agent_type="local",
            )
            for i in range(3)
        }

        context = {"query": "Test"}
        timeout = 60.0
        metadata = {"failed_subgoals": 0}

        with patch("aurora_soar.phases.collect.spawn_parallel") as mock_spawn_parallel:
            # Return results with identifiable outputs
            mock_spawn_parallel.return_value = [
                SpawnResult(success=True, output="First result", error=None, exit_code=0),
                SpawnResult(success=True, output="Second result", error=None, exit_code=0),
                SpawnResult(success=True, output="Third result", error=None, exit_code=0),
            ]

            outputs = await _execute_parallel_subgoals(
                subgoals,
                agent_map,
                context,
                timeout,
                metadata,
            )

            # Verify order is preserved
            assert len(outputs) == 3
            assert outputs[0].subgoal_index == 0
            assert outputs[1].subgoal_index == 1
            assert outputs[2].subgoal_index == 2
            assert "First" in outputs[0].summary
            assert "Second" in outputs[1].summary
            assert "Third" in outputs[2].summary
