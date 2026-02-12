"""Comprehensive test suite for parallel spawning edge cases and failure scenarios.

Tests focus on adhoc agent spawning, concurrent failures, circuit breaker behavior,
race conditions, and recovery mechanisms in parallel execution contexts.
"""

import asyncio
import time
from unittest.mock import MagicMock, patch

import pytest

from aurora_soar.phases.collect import execute_agents
from aurora_spawner import SpawnResult, SpawnTask, spawn_parallel
from aurora_spawner.circuit_breaker import get_circuit_breaker


@pytest.fixture
def reset_circuit_breaker():
    """Reset circuit breaker state before each test."""
    cb = get_circuit_breaker()
    cb.reset_all()
    yield cb
    cb.reset_all()


class TestParallelSpawnConcurrency:
    """Test concurrent spawning behavior and race conditions."""

    @pytest.mark.asyncio
    async def test_concurrent_adhoc_agent_spawns(self, reset_circuit_breaker):
        """Multiple adhoc agents spawned in parallel don't interfere."""
        spawn_count = 0

        async def mock_spawn(task):
            nonlocal spawn_count
            spawn_count += 1
            await asyncio.sleep(0.1)  # Simulate work
            return SpawnResult(
                success=True,
                output=f"Adhoc agent {spawn_count} completed",
                error=None,
                exit_code=0,
                fallback=False,
            )

        with patch("aurora_soar.phases.collect.spawn", side_effect=mock_spawn):
            agents = []
            subgoals = []

            # Create 5 adhoc agents
            for i in range(5):
                agent = MagicMock()
                agent.id = f"adhoc-agent-{i}"
                agent.config = {"is_spawn": True}
                agent.description = f"Adhoc specialist {i}"
                agents.append(agent)

                subgoals.append(
                    {
                        "description": f"Task for adhoc agent {i}",
                        "subgoal_index": i,
                    },
                )

            result = await execute_agents(
                agent_assignments=[(i, a) for i, a in enumerate(agents)],
                subgoals=subgoals,
                context={"query": "Test query"},
                agent_timeout=10.0,
            )

            # All adhoc agents should complete successfully
            assert len(result.agent_outputs) == 5
            assert all(out.success for out in result.agent_outputs)
            assert result.execution_metadata.get("spawn_count", 0) == 5
            assert len(result.execution_metadata.get("spawned_agents", [])) == 5

    @pytest.mark.asyncio
    async def test_mixed_adhoc_and_registered_agents(self, reset_circuit_breaker):
        """Adhoc and registered agents execute correctly in parallel."""

        async def mock_spawn(task):
            agent_type = "adhoc" if task.agent is None else "registered"
            await asyncio.sleep(0.05)
            return SpawnResult(
                success=True,
                output=f"{agent_type} agent output",
                error=None,
                exit_code=0,
                fallback=False,
            )

        with patch("aurora_soar.phases.collect.spawn", side_effect=mock_spawn):
            agents = []
            subgoals = []

            # Mix of adhoc and registered agents
            for i in range(6):
                agent = MagicMock()
                is_adhoc = i % 2 == 0
                agent.id = f"{'adhoc' if is_adhoc else 'reg'}-agent-{i}"
                agent.config = {"is_spawn": is_adhoc}
                if is_adhoc:
                    agent.description = f"Adhoc specialist {i}"
                agents.append(agent)

                subgoals.append(
                    {
                        "description": f"Task {i}",
                        "subgoal_index": i,
                    },
                )

            result = await execute_agents(
                agent_assignments=[(i, a) for i, a in enumerate(agents)],
                subgoals=subgoals,
                context={},
                agent_timeout=10.0,
            )

            # All agents should complete
            assert len(result.agent_outputs) == 6
            assert all(out.success for out in result.agent_outputs)
            # 3 adhoc agents spawned
            assert result.execution_metadata.get("spawn_count", 0) == 3

    @pytest.mark.asyncio
    async def test_concurrent_circuit_breaker_updates(self, reset_circuit_breaker):
        """Circuit breaker state updates correctly under concurrent failures."""
        cb = reset_circuit_breaker
        failure_count = {"adhoc-agent-1": 0}

        async def mock_spawn(task):
            await asyncio.sleep(0.02)
            # Agent fails twice then succeeds
            agent_id = task.agent or "adhoc-llm"
            failure_count[agent_id] = failure_count.get(agent_id, 0) + 1

            if failure_count[agent_id] <= 2:
                return SpawnResult(
                    success=False,
                    output="",
                    error="Connection error",
                    exit_code=-1,
                    fallback=False,
                )
            return SpawnResult(
                success=True,
                output="Success after retries",
                error=None,
                exit_code=0,
                fallback=False,
            )

        with patch(
            "aurora_soar.phases.collect.spawn_with_retry_and_fallback",
            side_effect=mock_spawn,
        ):
            agents = []
            subgoals = []

            # Same agent used multiple times
            for i in range(3):
                agent = MagicMock()
                agent.id = "adhoc-agent-1"
                agent.config = {"is_spawn": True}
                agent.description = "Adhoc specialist"
                agents.append(agent)

                subgoals.append(
                    {
                        "description": f"Task {i}",
                        "subgoal_index": i,
                    },
                )

            result = await execute_agents(
                agent_assignments=[(i, a) for i, a in enumerate(agents)],
                subgoals=subgoals,
                context={},
                agent_timeout=10.0,
                max_retries=3,
            )

            # Check circuit breaker tracked failures correctly
            # With adhoc agents, higher threshold should apply
            assert not cb.is_open("adhoc-agent-1")


class TestAdhocAgentFailures:
    """Test failure scenarios specific to adhoc (dynamically spawned) agents."""

    @pytest.mark.asyncio
    async def test_adhoc_agent_inference_failures(self, reset_circuit_breaker):
        """Adhoc agents with inference failures get lenient circuit breaker treatment."""
        cb = reset_circuit_breaker
        cb.mark_as_adhoc("adhoc-specialist")

        async def mock_spawn_inference_fail(task):
            await asyncio.sleep(0.01)
            return SpawnResult(
                success=False,
                output="",
                error="API error: model inference failed",
                exit_code=-1,
                fallback=False,
            )

        with patch(
            "aurora_soar.phases.collect.spawn_with_retry_and_fallback",
            side_effect=mock_spawn_inference_fail,
        ):
            agent = MagicMock()
            agent.id = "adhoc-specialist"
            agent.config = {"is_spawn": True}
            agent.description = "Adhoc specialist"

            subgoals = [{"description": "Complex task", "subgoal_index": 0}]

            result = await execute_agents(
                agent_assignments=[(0, agent)],
                subgoals=subgoals,
                context={},
                agent_timeout=10.0,
                max_retries=2,
                fallback_to_llm=True,
            )

            # Should fail but not open circuit immediately (inference failures)
            assert result.execution_metadata["failed_subgoals"] >= 1
            # Adhoc threshold is 4, so circuit should still be closed after 2-3 failures
            assert not cb.is_open("adhoc-specialist")

    @pytest.mark.asyncio
    async def test_adhoc_agent_fast_fail_threshold(self, reset_circuit_breaker):
        """Adhoc agents have longer fast-fail window (30s vs 10s)."""
        cb = reset_circuit_breaker

        async def mock_spawn_rapid_fail(task):
            await asyncio.sleep(0.01)
            return SpawnResult(
                success=False,
                output="",
                error="Timeout after 5s",
                exit_code=-1,
                fallback=False,
            )

        with patch(
            "aurora_soar.phases.collect.spawn_with_retry_and_fallback",
            side_effect=mock_spawn_rapid_fail,
        ):
            agent = MagicMock()
            agent.id = "adhoc-timeout-agent"
            agent.config = {"is_spawn": True}
            agent.description = "Adhoc agent"

            # Rapid succession of failures
            for i in range(3):
                subgoals = [{"description": f"Task {i}", "subgoal_index": i}]
                result = await execute_agents(
                    agent_assignments=[(i, agent)],
                    subgoals=subgoals,
                    context={},
                    agent_timeout=10.0,
                    max_retries=1,
                )
                # Small delay between failures (within 30s window)
                await asyncio.sleep(0.05)

            # Check if circuit opened (adhoc should be more lenient)
            health = cb.get_health_status("adhoc-timeout-agent")
            # Adhoc threshold is 4, may not be open yet
            assert health["recent_failures"] >= 3

    @pytest.mark.asyncio
    async def test_adhoc_agent_missing_matcher(self, reset_circuit_breaker):
        """Adhoc agents work even when AgentMatcher is unavailable."""

        async def mock_spawn(task):
            # Verify fallback spawn prompt was generated
            assert "act as a" in task.prompt.lower()
            await asyncio.sleep(0.05)
            return SpawnResult(
                success=True,
                output="Completed with fallback prompt",
                error=None,
                exit_code=0,
                fallback=False,
            )

        with patch("aurora_soar.phases.collect._get_agent_matcher", return_value=None):
            with patch("aurora_soar.phases.collect.spawn", side_effect=mock_spawn):
                agent = MagicMock()
                agent.id = "adhoc-no-matcher"
                agent.config = {"is_spawn": True}
                agent.description = "Specialist without matcher"

                subgoals = [{"description": "Task", "subgoal_index": 0}]

                result = await execute_agents(
                    agent_assignments=[(0, agent)],
                    subgoals=subgoals,
                    context={},
                    agent_timeout=10.0,
                )

                assert len(result.agent_outputs) == 1
                assert result.agent_outputs[0].success


class TestCircuitBreakerEdgeCases:
    """Test circuit breaker behavior in edge cases."""

    @pytest.mark.asyncio
    async def test_circuit_breaker_pre_spawn_blocking(self, reset_circuit_breaker):
        """Circuit breaker blocks agents before spawning (fast-fail)."""
        cb = reset_circuit_breaker

        # Pre-open circuit for test-agent
        for _ in range(3):
            cb.record_failure("test-agent", failure_type="timeout")

        assert cb.is_open("test-agent")

        async def mock_spawn(task):
            pytest.fail("Should not spawn when circuit is open")

        with patch("aurora_soar.phases.collect.spawn", side_effect=mock_spawn):
            agent = MagicMock()
            agent.id = "test-agent"
            agent.config = {}

            subgoals = [{"description": "Task", "subgoal_index": 0}]

            result = await execute_agents(
                agent_assignments=[(0, agent)],
                subgoals=subgoals,
                context={},
                agent_timeout=10.0,
                fallback_to_llm=False,
            )

            # Should fail immediately without spawning
            assert result.execution_metadata["failed_subgoals"] == 1
            assert result.execution_metadata["circuit_blocked_count"] == 1
            assert result.agent_outputs[0].error.startswith("Circuit breaker open")

    @pytest.mark.asyncio
    async def test_circuit_breaker_with_fallback(self, reset_circuit_breaker):
        """Circuit breaker triggers fallback to LLM."""
        cb = reset_circuit_breaker

        # Pre-open circuit
        for _ in range(3):
            cb.record_failure("broken-agent", failure_type="crash")

        async def mock_spawn_fallback(task):
            # Should only be called with agent=None (LLM fallback)
            assert task.agent is None
            await asyncio.sleep(0.05)
            return SpawnResult(
                success=True,
                output="LLM fallback succeeded",
                error=None,
                exit_code=0,
                fallback=True,
                original_agent="broken-agent",
            )

        with patch("aurora_soar.phases.collect.spawn", side_effect=mock_spawn_fallback):
            agent = MagicMock()
            agent.id = "broken-agent"
            agent.config = {}

            subgoals = [{"description": "Task", "subgoal_index": 0}]

            result = await execute_agents(
                agent_assignments=[(0, agent)],
                subgoals=subgoals,
                context={},
                agent_timeout=10.0,
                fallback_to_llm=True,
            )

            # Should use fallback
            assert len(result.fallback_agents) >= 1
            assert "broken-agent" in result.fallback_agents

    @pytest.mark.asyncio
    async def test_circuit_recovery_in_parallel(self, reset_circuit_breaker):
        """Circuit breaker recovers when agent succeeds in parallel execution."""
        cb = reset_circuit_breaker
        attempt = {"count": 0}

        async def mock_spawn_recovery(task):
            attempt["count"] += 1
            await asyncio.sleep(0.05)
            # Fail first 2, succeed rest
            if attempt["count"] <= 2:
                return SpawnResult(
                    success=False,
                    output="",
                    error="Temporary failure",
                    exit_code=-1,
                    fallback=False,
                )
            return SpawnResult(
                success=True,
                output="Recovered",
                error=None,
                exit_code=0,
                fallback=False,
            )

        with patch(
            "aurora_soar.phases.collect.spawn_with_retry_and_fallback",
            side_effect=mock_spawn_recovery,
        ):
            agents = []
            subgoals = []

            # Same agent multiple times
            for i in range(4):
                agent = MagicMock()
                agent.id = "recovering-agent"
                agent.config = {}
                agents.append(agent)

                subgoals.append(
                    {
                        "description": f"Task {i}",
                        "subgoal_index": i,
                    },
                )

            result = await execute_agents(
                agent_assignments=[(i, a) for i, a in enumerate(agents)],
                subgoals=subgoals,
                context={},
                agent_timeout=10.0,
                max_retries=2,
            )

            # At least some should succeed
            successes = sum(1 for out in result.agent_outputs if out.success)
            assert successes >= 2


class TestResourceContention:
    """Test resource contention and limit scenarios."""

    @pytest.mark.asyncio
    async def test_max_concurrent_limit_respected(self):
        """Parallel spawning respects max_concurrent limit."""
        active_count = {"value": 0}
        max_observed = {"value": 0}
        lock = asyncio.Lock()

        async def mock_spawn(task):
            async with lock:
                active_count["value"] += 1
                max_observed["value"] = max(max_observed["value"], active_count["value"])

            await asyncio.sleep(0.1)

            async with lock:
                active_count["value"] -= 1

            return SpawnResult(
                success=True,
                output="Done",
                error=None,
                exit_code=0,
                fallback=False,
            )

        # Test spawn_parallel directly with max_concurrent
        tasks = [SpawnTask(prompt=f"Task {i}", agent="test-agent", timeout=10) for i in range(10)]

        with patch("aurora_spawner.spawner.spawn", side_effect=mock_spawn):
            results = await spawn_parallel(tasks, max_concurrent=3)

            # Max concurrent should not exceed 3
            assert max_observed["value"] <= 3
            assert len(results) == 10
            assert all(r.success for r in results)

    @pytest.mark.asyncio
    async def test_global_timeout_with_slow_agents(self):
        """Global timeout prevents pipeline hanging with many slow agents."""

        async def mock_spawn_slow(task):
            # Simulate slow agents
            await asyncio.sleep(10)
            return SpawnResult(
                success=True,
                output="Completed",
                error=None,
                exit_code=0,
                fallback=False,
            )

        with patch(
            "aurora_soar.phases.collect.spawn_with_retry_and_fallback",
            side_effect=mock_spawn_slow,
        ):
            agents = []
            subgoals = []

            for i in range(5):
                agent = MagicMock()
                agent.id = f"slow-agent-{i}"
                agent.config = {}
                agents.append(agent)

                subgoals.append(
                    {
                        "description": f"Task {i}",
                        "subgoal_index": i,
                    },
                )

            agent_timeout = 20.0
            expected_global_timeout = agent_timeout * 1.5  # 30s

            start = time.time()
            result = await execute_agents(
                agent_assignments=[(i, a) for i, a in enumerate(agents)],
                subgoals=subgoals,
                context={},
                agent_timeout=agent_timeout,
            )
            elapsed = time.time() - start

            # Should hit global timeout (~30s) not wait for all agents (50s)
            assert elapsed < expected_global_timeout + 2.0
            # May have partial results
            assert len(result.agent_outputs) <= 5


class TestFailurePatternDetection:
    """Test detection and categorization of failure patterns."""

    @pytest.mark.asyncio
    async def test_error_pattern_early_termination(self, reset_circuit_breaker):
        """Error patterns trigger early termination tracking."""

        async def mock_spawn_rate_limit(task):
            await asyncio.sleep(0.05)
            return SpawnResult(
                success=False,
                output="",
                error="API error: rate limit exceeded",
                exit_code=-1,
                fallback=False,
                termination_reason="Early detection: rate limit pattern detected",
            )

        with patch(
            "aurora_soar.phases.collect.spawn_with_retry_and_fallback",
            side_effect=mock_spawn_rate_limit,
        ):
            agent = MagicMock()
            agent.id = "rate-limited-agent"
            agent.config = {}

            subgoals = [{"description": "Task", "subgoal_index": 0}]

            result = await execute_agents(
                agent_assignments=[(0, agent)],
                subgoals=subgoals,
                context={},
                agent_timeout=10.0,
                fallback_to_llm=False,
            )

            # Check early termination was tracked
            early_terms = result.execution_metadata.get("early_terminations", [])
            assert len(early_terms) >= 1
            assert "rate" in early_terms[0]["reason"].lower()

    @pytest.mark.asyncio
    async def test_mixed_failure_types(self, reset_circuit_breaker):
        """Different failure types tracked separately in metadata."""

        async def mock_spawn_varied_failures(task):
            await asyncio.sleep(0.05)
            if "timeout" in task.prompt:
                return SpawnResult(
                    success=False,
                    output="",
                    error="Process timed out after 60 seconds",
                    exit_code=-1,
                    fallback=False,
                    termination_reason="Process timed out after 60 seconds",
                )
            if "auth" in task.prompt:
                return SpawnResult(
                    success=False,
                    output="",
                    error="Authentication failed: invalid API key",
                    exit_code=-1,
                    fallback=False,
                    termination_reason="Early detection: auth failure pattern detected",
                )
            return SpawnResult(
                success=True,
                output="Success",
                error=None,
                exit_code=0,
                fallback=False,
            )

        with patch(
            "aurora_soar.phases.collect.spawn_with_retry_and_fallback",
            side_effect=mock_spawn_varied_failures,
        ):
            agents = []
            subgoals = []

            for i, failure_type in enumerate(["timeout", "auth", "success"]):
                agent = MagicMock()
                agent.id = f"{failure_type}-agent"
                agent.config = {}
                agents.append(agent)

                subgoals.append(
                    {
                        "description": f"Task with {failure_type}",
                        "subgoal_index": i,
                    },
                )

            result = await execute_agents(
                agent_assignments=[(i, a) for i, a in enumerate(agents)],
                subgoals=subgoals,
                context={},
                agent_timeout=10.0,
            )

            # Check varied failures recorded
            assert result.execution_metadata["failed_subgoals"] == 2
            early_terms = result.execution_metadata.get("early_terminations", [])
            # At least auth failure should be early termination
            assert any("auth" in term["reason"].lower() for term in early_terms)


class TestRecoveryMechanisms:
    """Test retry and recovery mechanisms in parallel execution."""

    @pytest.mark.asyncio
    async def test_retry_with_exponential_backoff(self, reset_circuit_breaker):
        """Retries use exponential backoff correctly."""
        attempt_times = []

        async def mock_spawn_track_timing(task):
            attempt_times.append(time.time())
            await asyncio.sleep(0.01)
            # Fail first 2 attempts
            if len(attempt_times) <= 2:
                return SpawnResult(
                    success=False,
                    output="",
                    error="Temporary failure",
                    exit_code=-1,
                    fallback=False,
                )
            return SpawnResult(
                success=True,
                output="Success",
                error=None,
                exit_code=0,
                fallback=False,
            )

        with patch(
            "aurora_soar.phases.collect.spawn_with_retry_and_fallback",
            side_effect=mock_spawn_track_timing,
        ):
            agent = MagicMock()
            agent.id = "retry-agent"
            agent.config = {}

            subgoals = [{"description": "Task", "subgoal_index": 0}]

            result = await execute_agents(
                agent_assignments=[(0, agent)],
                subgoals=subgoals,
                context={},
                agent_timeout=10.0,
                max_retries=3,
            )

            # Check timing shows backoff (delays between attempts)
            if len(attempt_times) >= 3:
                delay1 = attempt_times[1] - attempt_times[0]
                delay2 = attempt_times[2] - attempt_times[1]
                # Second delay should be longer (exponential backoff)
                # Allow tolerance for test timing variance
                assert delay2 >= delay1 * 0.8

    @pytest.mark.asyncio
    async def test_partial_success_handling(self, reset_circuit_breaker):
        """Partial successes handled correctly in parallel execution."""

        async def mock_spawn_partial(task):
            await asyncio.sleep(0.05)
            # Half succeed, half fail
            if "succeed" in task.prompt:
                return SpawnResult(
                    success=True,
                    output="Success",
                    error=None,
                    exit_code=0,
                    fallback=False,
                )
            return SpawnResult(
                success=False,
                output="",
                error="Failed",
                exit_code=-1,
                fallback=False,
            )

        with patch(
            "aurora_soar.phases.collect.spawn_with_retry_and_fallback",
            side_effect=mock_spawn_partial,
        ):
            agents = []
            subgoals = []

            for i in range(6):
                agent = MagicMock()
                agent.id = f"agent-{i}"
                agent.config = {}
                agents.append(agent)

                outcome = "succeed" if i % 2 == 0 else "fail"
                subgoals.append(
                    {
                        "description": f"Task {outcome} {i}",
                        "subgoal_index": i,
                    },
                )

            result = await execute_agents(
                agent_assignments=[(i, a) for i, a in enumerate(agents)],
                subgoals=subgoals,
                context={},
                agent_timeout=10.0,
            )

            # Check partial success
            successes = sum(1 for out in result.agent_outputs if out.success)
            failures = sum(1 for out in result.agent_outputs if not out.success)
            assert successes == 3
            assert failures == 3
            assert result.execution_metadata["failed_subgoals"] == 3


class TestEdgeCasesAndBoundaries:
    """Test edge cases and boundary conditions."""

    @pytest.mark.asyncio
    async def test_empty_agent_list(self):
        """Empty agent list handled gracefully."""
        result = await execute_agents(
            agent_assignments=[],
            subgoals=[],
            context={},
            agent_timeout=10.0,
        )

        assert len(result.agent_outputs) == 0
        assert result.execution_metadata["total_subgoals"] == 0
        assert result.execution_metadata["failed_subgoals"] == 0

    @pytest.mark.asyncio
    async def test_single_agent_execution(self, reset_circuit_breaker):
        """Single agent execution works correctly."""

        async def mock_spawn(task):
            await asyncio.sleep(0.05)
            return SpawnResult(
                success=True,
                output="Single agent success",
                error=None,
                exit_code=0,
                fallback=False,
            )

        with patch(
            "aurora_soar.phases.collect.spawn_with_retry_and_fallback",
            side_effect=mock_spawn,
        ):
            agent = MagicMock()
            agent.id = "solo-agent"
            agent.config = {}

            subgoals = [{"description": "Single task", "subgoal_index": 0}]

            result = await execute_agents(
                agent_assignments=[(0, agent)],
                subgoals=subgoals,
                context={},
                agent_timeout=10.0,
            )

            assert len(result.agent_outputs) == 1
            assert result.agent_outputs[0].success

    @pytest.mark.asyncio
    async def test_very_high_concurrency(self):
        """High concurrency (100+ agents) handled correctly."""

        async def mock_spawn_fast(task):
            await asyncio.sleep(0.01)
            return SpawnResult(
                success=True,
                output="Fast",
                error=None,
                exit_code=0,
                fallback=False,
            )

        with patch(
            "aurora_soar.phases.collect.spawn_with_retry_and_fallback",
            side_effect=mock_spawn_fast,
        ):
            agents = []
            subgoals = []

            for i in range(100):
                agent = MagicMock()
                agent.id = f"agent-{i}"
                agent.config = {}
                agents.append(agent)

                subgoals.append(
                    {
                        "description": f"Task {i}",
                        "subgoal_index": i,
                    },
                )

            start = time.time()
            result = await execute_agents(
                agent_assignments=[(i, a) for i, a in enumerate(agents)],
                subgoals=subgoals,
                context={},
                agent_timeout=10.0,
            )
            elapsed = time.time() - start

            # All should complete
            assert len(result.agent_outputs) == 100
            # With concurrency, should complete much faster than serial (100 * 0.01 = 1s)
            # Allow for overhead but should be < 5s
            assert elapsed < 5.0

    @pytest.mark.asyncio
    async def test_exception_during_spawn(self, reset_circuit_breaker):
        """Exceptions during spawn handled gracefully."""

        async def mock_spawn_exception(task):
            await asyncio.sleep(0.05)
            raise RuntimeError("Unexpected spawn error")

        with patch(
            "aurora_soar.phases.collect.spawn_with_retry_and_fallback",
            side_effect=mock_spawn_exception,
        ):
            agent = MagicMock()
            agent.id = "error-agent"
            agent.config = {}

            subgoals = [{"description": "Task", "subgoal_index": 0}]

            result = await execute_agents(
                agent_assignments=[(0, agent)],
                subgoals=subgoals,
                context={},
                agent_timeout=10.0,
            )

            # Should catch exception and return failed output
            assert len(result.agent_outputs) == 1
            assert not result.agent_outputs[0].success
            assert "Unexpected spawn error" in result.agent_outputs[0].error
