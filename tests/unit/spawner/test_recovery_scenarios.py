"""Unit tests for agent recovery scenarios.

Tests partial failures, timeout recovery, retry exhaustion, and fallback mechanisms
in the spawner's recovery pipeline.
"""

import asyncio
import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from aurora_spawner import SpawnResult, SpawnTask, spawn_parallel_with_recovery
from aurora_spawner.circuit_breaker import CircuitBreaker, CircuitState
from aurora_spawner.spawner import spawn_with_retry_and_fallback
from aurora_spawner.timeout_policy import (
    RetryPolicy,
    RetryStrategy,
    SpawnPolicy,
    TerminationPolicy,
    TimeoutMode,
    TimeoutPolicy,
)

# =============================================================================
# PARTIAL FAILURE RECOVERY TESTS
# =============================================================================


class TestPartialFailureRecovery:
    """Test recovery when some tasks in a batch fail."""

    @pytest.mark.asyncio
    async def test_partial_failure_some_succeed(self):
        """Some tasks fail initially but recover on retry."""
        attempt_counts = {}

        async def mock_spawn(task, **kwargs):
            task_id = task.prompt
            attempt_counts[task_id] = attempt_counts.get(task_id, 0) + 1

            # Tasks 0, 2, 4 fail on first attempt
            idx = int(task_id.split()[-1])
            if idx % 2 == 0 and attempt_counts[task_id] == 1:
                return SpawnResult(
                    success=False,
                    output="",
                    error="Transient error",
                    exit_code=-1,
                )

            return SpawnResult(
                success=True,
                output=f"Success {task_id}",
                error=None,
                exit_code=0,
            )

        tasks = [SpawnTask(prompt=f"Task {i}", agent="test-agent", timeout=10) for i in range(5)]

        with patch("aurora_spawner.spawner.spawn", side_effect=mock_spawn):
            with patch("aurora_spawner.circuit_breaker.get_circuit_breaker") as mock_cb:
                # High thresholds to allow multiple retry cascades without circuit opening
                cb = CircuitBreaker(
                    failure_threshold=20, fast_fail_threshold=20, failure_window=600.0
                )
                mock_cb.return_value = cb

                results = await spawn_parallel_with_recovery(
                    tasks,
                    max_concurrent=5,
                    max_retries=2,
                    fallback_to_llm=False,
                )

                # All should eventually succeed
                assert len(results) == 5
                assert all(r.success for r in results)

                # Check that failing tasks were retried
                assert attempt_counts["Task 0"] == 2
                assert attempt_counts["Task 2"] == 2
                assert attempt_counts["Task 4"] == 2
                # Successful tasks only attempted once
                assert attempt_counts["Task 1"] == 1
                assert attempt_counts["Task 3"] == 1

    @pytest.mark.asyncio
    async def test_partial_failure_isolated_failures(self):
        """Failures in one task don't affect others."""
        execution_order = []

        async def mock_spawn(task, **kwargs):
            task_id = task.prompt
            execution_order.append(task_id)

            # Task 2 always fails
            if "Task 2" in task_id:
                return SpawnResult(
                    success=False,
                    output="",
                    error="Persistent failure",
                    exit_code=-1,
                )

            await asyncio.sleep(0.01)
            return SpawnResult(
                success=True,
                output=f"Success {task_id}",
                error=None,
                exit_code=0,
            )

        tasks = [SpawnTask(prompt=f"Task {i}", agent="test-agent", timeout=10) for i in range(5)]

        with patch("aurora_spawner.spawner.spawn", side_effect=mock_spawn):
            with patch("aurora_spawner.circuit_breaker.get_circuit_breaker") as mock_cb:
                # High thresholds to allow retry cascades without circuit opening
                cb = CircuitBreaker(
                    failure_threshold=20, fast_fail_threshold=20, failure_window=600.0
                )
                mock_cb.return_value = cb

                results = await spawn_parallel_with_recovery(
                    tasks,
                    max_concurrent=5,
                    max_retries=1,
                    fallback_to_llm=False,
                )

                # 4 succeed, 1 fails after exhausting retries
                successful = [r for r in results if r.success]
                failed = [r for r in results if not r.success]

                assert len(successful) == 4
                assert len(failed) == 1
                assert results[2].success is False  # Task 2 failed

    @pytest.mark.asyncio
    async def test_partial_failure_with_fallback(self):
        """Failed tasks can fallback to LLM."""
        call_history = []

        async def mock_spawn(task, **kwargs):
            call_history.append({"agent": task.agent, "prompt": task.prompt})

            # Agent fails for Task 1
            if task.agent == "failing-agent" and "Task 1" in task.prompt:
                return SpawnResult(
                    success=False,
                    output="",
                    error="Agent failed",
                    exit_code=-1,
                )

            # LLM fallback succeeds
            return SpawnResult(
                success=True,
                output=f"Success via {task.agent or 'llm'}",
                error=None,
                exit_code=0,
            )

        tasks = [SpawnTask(prompt=f"Task {i}", agent="failing-agent", timeout=10) for i in range(3)]

        with patch("aurora_spawner.spawner.spawn", side_effect=mock_spawn):
            with patch("aurora_spawner.circuit_breaker.get_circuit_breaker") as mock_cb:
                # High thresholds to allow retry cascades without circuit opening
                cb = CircuitBreaker(
                    failure_threshold=20, fast_fail_threshold=20, failure_window=600.0
                )
                mock_cb.return_value = cb

                results = await spawn_parallel_with_recovery(
                    tasks,
                    max_concurrent=5,
                    max_retries=0,  # No agent retries
                    fallback_to_llm=True,
                )

                assert len(results) == 3
                assert all(r.success for r in results)

                # Task 1 should have used fallback
                assert results[1].fallback is True
                assert results[1].original_agent == "failing-agent"

                # Other tasks succeeded with agent
                assert results[0].fallback is False
                assert results[2].fallback is False

    @pytest.mark.asyncio
    async def test_mixed_recovery_outcomes(self):
        """Test mixed outcomes: immediate success, retry success, fallback success, complete failure."""
        call_counts = {}

        async def mock_spawn(task, **kwargs):
            key = f"{task.agent or 'llm'}:{task.prompt}"
            call_counts[key] = call_counts.get(key, 0) + 1

            idx = int(task.prompt.split()[-1])

            # Task 0: Immediate success
            if idx == 0:
                return SpawnResult(success=True, output="immediate", error=None, exit_code=0)

            # Task 1: Success on retry
            if idx == 1:
                if task.agent and call_counts[key] == 1:
                    return SpawnResult(success=False, output="", error="retry me", exit_code=-1)
                return SpawnResult(success=True, output="retry success", error=None, exit_code=0)

            # Task 2: Agent fails, LLM succeeds
            if idx == 2:
                if task.agent:
                    return SpawnResult(
                        success=False, output="", error="fallback needed", exit_code=-1
                    )
                return SpawnResult(success=True, output="fallback success", error=None, exit_code=0)

            # Task 3: Complete failure
            if idx == 3:
                return SpawnResult(
                    success=False, output="", error="permanent failure", exit_code=-1
                )

            return SpawnResult(success=True, output="default", error=None, exit_code=0)

        tasks = [SpawnTask(prompt=f"Task {i}", agent="test-agent", timeout=10) for i in range(4)]

        with patch("aurora_spawner.spawner.spawn", side_effect=mock_spawn):
            with patch("aurora_spawner.circuit_breaker.get_circuit_breaker") as mock_cb:
                # High thresholds to allow retry cascades without circuit opening
                cb = CircuitBreaker(
                    failure_threshold=20, fast_fail_threshold=20, failure_window=600.0
                )
                mock_cb.return_value = cb

                results = await spawn_parallel_with_recovery(
                    tasks,
                    max_concurrent=5,
                    max_retries=1,
                    fallback_to_llm=True,
                )

                # Task 0: Immediate success
                assert results[0].success
                assert results[0].retry_count == 0
                assert not results[0].fallback

                # Task 1: Retry success
                assert results[1].success
                assert results[1].retry_count > 0
                assert not results[1].fallback

                # Task 2: Fallback success
                assert results[2].success
                assert results[2].fallback

                # Task 3: Complete failure (both agent and LLM failed)
                assert not results[3].success


# =============================================================================
# TIMEOUT RECOVERY TESTS
# =============================================================================


class TestTimeoutRecovery:
    """Test recovery from timeout scenarios."""

    @pytest.mark.asyncio
    async def test_timeout_triggers_retry(self):
        """Task that times out gets retried."""
        attempt_count = 0

        async def mock_spawn(task, **kwargs):
            nonlocal attempt_count
            attempt_count += 1

            if attempt_count == 1:
                return SpawnResult(
                    success=False,
                    output="",
                    error="Process timed out",
                    exit_code=-1,
                    termination_reason="Process timed out after 60 seconds",
                )

            return SpawnResult(
                success=True,
                output="Success after timeout",
                error=None,
                exit_code=0,
            )

        task = SpawnTask(prompt="Timeout task", agent="slow-agent", timeout=60)

        with patch("aurora_spawner.spawner.spawn", side_effect=mock_spawn):
            with patch("aurora_spawner.circuit_breaker.get_circuit_breaker") as mock_cb:
                cb = CircuitBreaker(failure_threshold=5)
                mock_cb.return_value = cb

                policy = SpawnPolicy.default()
                result = await spawn_with_retry_and_fallback(
                    task,
                    max_retries=2,
                    fallback_to_llm=False,
                    policy=policy,
                )

                assert result.success
                assert attempt_count == 2
                assert result.retry_count == 1

    @pytest.mark.asyncio
    async def test_timeout_disabled_no_retry(self):
        """Timeout doesn't trigger retry when retry_on_timeout is False."""
        attempt_count = 0

        async def mock_spawn(task, **kwargs):
            nonlocal attempt_count
            attempt_count += 1
            return SpawnResult(
                success=False,
                output="",
                error="Process timed out",
                exit_code=-1,
                termination_reason="Process timed out after 60 seconds",
            )

        task = SpawnTask(prompt="Timeout task", agent="slow-agent", timeout=60)

        with patch("aurora_spawner.spawner.spawn", side_effect=mock_spawn):
            with patch("aurora_spawner.circuit_breaker.get_circuit_breaker") as mock_cb:
                cb = CircuitBreaker(failure_threshold=5)
                mock_cb.return_value = cb

                # Use fast_fail policy which disables timeout retry
                policy = SpawnPolicy.fast_fail()
                result = await spawn_with_retry_and_fallback(
                    task,
                    max_retries=3,
                    fallback_to_llm=False,
                    policy=policy,
                )

                # Should not retry because policy disables timeout retry
                assert not result.success
                assert attempt_count == 1

    @pytest.mark.asyncio
    async def test_progressive_timeout_allows_longer_execution(self):
        """Progressive timeout extends when activity detected."""
        # This tests the policy configuration, not actual timeout behavior
        policy = SpawnPolicy.default()

        assert policy.timeout_policy.mode == TimeoutMode.PROGRESSIVE
        assert policy.timeout_policy.initial_timeout < policy.timeout_policy.max_timeout

        # Verify extension logic
        assert policy.timeout_policy.should_extend(
            elapsed=30.0,
            last_activity=5.0,  # Activity 5s ago (within extension_threshold)
            current_timeout=60.0,
        )

        # Should not extend if already at max
        assert not policy.timeout_policy.should_extend(
            elapsed=200.0,
            last_activity=5.0,
            current_timeout=300.0,  # At max
        )

    @pytest.mark.asyncio
    async def test_no_activity_timeout_triggers_termination(self):
        """No activity for extended period triggers early termination."""

        async def mock_spawn(task, **kwargs):
            return SpawnResult(
                success=False,
                output="",
                error="No activity for 30 seconds",
                exit_code=-1,
                termination_reason="No activity for 30 seconds",
            )

        task = SpawnTask(prompt="Stalled task", agent="stuck-agent", timeout=300)

        with patch("aurora_spawner.spawner.spawn", side_effect=mock_spawn):
            with patch("aurora_spawner.circuit_breaker.get_circuit_breaker") as mock_cb:
                cb = CircuitBreaker(failure_threshold=5)
                mock_cb.return_value = cb

                result = await spawn_with_retry_and_fallback(
                    task,
                    max_retries=1,
                    fallback_to_llm=False,
                )

                assert not result.success
                assert "no activity" in result.error.lower()


# =============================================================================
# RETRY EXHAUSTION TESTS
# =============================================================================


class TestRetryExhaustion:
    """Test behavior when all retries are exhausted."""

    @pytest.mark.asyncio
    async def test_max_retries_exhausted_no_fallback(self):
        """All retries exhausted without fallback returns failure."""
        attempt_count = 0

        async def mock_spawn(task, **kwargs):
            nonlocal attempt_count
            attempt_count += 1
            return SpawnResult(
                success=False,
                output="",
                error=f"Failure attempt {attempt_count}",
                exit_code=-1,
            )

        task = SpawnTask(prompt="Failing task", agent="bad-agent", timeout=10)

        with patch("aurora_spawner.spawner.spawn", side_effect=mock_spawn):
            with patch("aurora_spawner.circuit_breaker.get_circuit_breaker") as mock_cb:
                # High thresholds to allow retry cascades without circuit opening
                cb = CircuitBreaker(
                    failure_threshold=20, fast_fail_threshold=20, failure_window=600.0
                )
                mock_cb.return_value = cb

                result = await spawn_with_retry_and_fallback(
                    task,
                    max_retries=3,
                    fallback_to_llm=False,
                )

                assert not result.success
                assert attempt_count == 4  # 1 initial + 3 retries
                assert result.retry_count == 4
                assert result.fallback is False

    @pytest.mark.asyncio
    async def test_max_retries_exhausted_with_fallback(self):
        """All retries exhausted triggers fallback to LLM."""
        call_history = []

        async def mock_spawn(task, **kwargs):
            call_history.append(task.agent)

            if task.agent == "bad-agent":
                return SpawnResult(
                    success=False,
                    output="",
                    error="Agent failed",
                    exit_code=-1,
                )

            # LLM (agent=None) succeeds
            return SpawnResult(
                success=True,
                output="LLM success",
                error=None,
                exit_code=0,
            )

        task = SpawnTask(prompt="Failing task", agent="bad-agent", timeout=10)

        with patch("aurora_spawner.spawner.spawn", side_effect=mock_spawn):
            with patch("aurora_spawner.circuit_breaker.get_circuit_breaker") as mock_cb:
                # High thresholds to allow retry cascades without circuit opening
                cb = CircuitBreaker(
                    failure_threshold=20, fast_fail_threshold=20, failure_window=600.0
                )
                mock_cb.return_value = cb

                result = await spawn_with_retry_and_fallback(
                    task,
                    max_retries=2,
                    fallback_to_llm=True,
                )

                assert result.success
                assert result.fallback is True
                assert result.original_agent == "bad-agent"

                # Verify call sequence: 3 agent attempts + 1 LLM
                agent_calls = [c for c in call_history if c == "bad-agent"]
                llm_calls = [c for c in call_history if c is None]
                assert len(agent_calls) == 3  # 1 initial + 2 retries
                assert len(llm_calls) == 1

    @pytest.mark.asyncio
    async def test_fallback_also_fails(self):
        """Both agent retries and LLM fallback fail."""

        async def mock_spawn(task, **kwargs):
            return SpawnResult(
                success=False,
                output="",
                error="Everything is broken",
                exit_code=-1,
            )

        task = SpawnTask(prompt="Doomed task", agent="bad-agent", timeout=10)

        with patch("aurora_spawner.spawner.spawn", side_effect=mock_spawn):
            with patch("aurora_spawner.circuit_breaker.get_circuit_breaker") as mock_cb:
                # High thresholds to allow retry cascades without circuit opening
                cb = CircuitBreaker(
                    failure_threshold=20, fast_fail_threshold=20, failure_window=600.0
                )
                mock_cb.return_value = cb

                result = await spawn_with_retry_and_fallback(
                    task,
                    max_retries=2,
                    fallback_to_llm=True,
                )

                assert not result.success
                assert result.fallback is True  # Fallback was attempted
                assert "broken" in result.error.lower()

    @pytest.mark.asyncio
    async def test_retry_count_tracking(self):
        """Retry count is accurately tracked in result."""
        attempt_count = 0

        async def mock_spawn(task, **kwargs):
            nonlocal attempt_count
            attempt_count += 1

            # Succeed on 3rd attempt
            if attempt_count >= 3:
                return SpawnResult(
                    success=True,
                    output="Finally!",
                    error=None,
                    exit_code=0,
                )

            return SpawnResult(
                success=False,
                output="",
                error="Not yet",
                exit_code=-1,
            )

        task = SpawnTask(prompt="Eventual success", agent="flaky-agent", timeout=10)

        with patch("aurora_spawner.spawner.spawn", side_effect=mock_spawn):
            with patch("aurora_spawner.circuit_breaker.get_circuit_breaker") as mock_cb:
                # High thresholds to allow retry cascades without circuit opening
                cb = CircuitBreaker(
                    failure_threshold=20, fast_fail_threshold=20, failure_window=600.0
                )
                mock_cb.return_value = cb

                result = await spawn_with_retry_and_fallback(
                    task,
                    max_retries=5,
                    fallback_to_llm=False,
                )

                assert result.success
                assert result.retry_count == 2  # 0-indexed, 3rd attempt means 2 retries

    @pytest.mark.asyncio
    async def test_zero_retries_single_attempt(self):
        """With max_retries=0, only one attempt is made."""
        attempt_count = 0

        async def mock_spawn(task, **kwargs):
            nonlocal attempt_count
            attempt_count += 1
            return SpawnResult(
                success=False,
                output="",
                error="Failed",
                exit_code=-1,
            )

        task = SpawnTask(prompt="One shot", agent="agent", timeout=10)

        with patch("aurora_spawner.spawner.spawn", side_effect=mock_spawn):
            with patch("aurora_spawner.circuit_breaker.get_circuit_breaker") as mock_cb:
                # High thresholds to allow retry cascades without circuit opening
                cb = CircuitBreaker(
                    failure_threshold=20, fast_fail_threshold=20, failure_window=600.0
                )
                mock_cb.return_value = cb

                result = await spawn_with_retry_and_fallback(
                    task,
                    max_retries=0,
                    fallback_to_llm=False,
                )

                assert not result.success
                assert attempt_count == 1


# =============================================================================
# CIRCUIT BREAKER INTEGRATION TESTS
# =============================================================================


class TestCircuitBreakerRecovery:
    """Test circuit breaker behavior during recovery."""

    @pytest.mark.asyncio
    async def test_circuit_opens_after_threshold_failures(self):
        """Circuit opens after threshold failures across tasks."""
        cb = CircuitBreaker(failure_threshold=2, failure_window=60.0)

        async def mock_spawn(task, **kwargs):
            return SpawnResult(
                success=False,
                output="",
                error="Persistent failure",
                exit_code=-1,
            )

        task = SpawnTask(prompt="Failing task", agent="bad-agent", timeout=10)

        with patch("aurora_spawner.spawner.spawn", side_effect=mock_spawn):
            with patch("aurora_spawner.circuit_breaker.get_circuit_breaker", return_value=cb):
                # First call - should attempt and fail
                result1 = await spawn_with_retry_and_fallback(
                    task,
                    max_retries=0,
                    fallback_to_llm=False,
                )
                assert not result1.success

                # Second call - should attempt and fail, opening circuit
                result2 = await spawn_with_retry_and_fallback(
                    task,
                    max_retries=0,
                    fallback_to_llm=False,
                )
                assert not result2.success

                # Circuit should now be open
                assert cb.is_open("bad-agent")

    @pytest.mark.asyncio
    async def test_circuit_open_skips_agent_uses_fallback(self):
        """Open circuit skips agent and goes directly to fallback."""
        cb = CircuitBreaker(failure_threshold=2)
        # Pre-open the circuit
        cb.record_failure("bad-agent")
        cb.record_failure("bad-agent")
        assert cb.is_open("bad-agent")

        spawn_calls = []

        async def mock_spawn(task, **kwargs):
            spawn_calls.append(task.agent)
            return SpawnResult(
                success=True,
                output="Success",
                error=None,
                exit_code=0,
            )

        task = SpawnTask(prompt="Task", agent="bad-agent", timeout=10)

        with patch("aurora_spawner.spawner.spawn", side_effect=mock_spawn):
            with patch("aurora_spawner.circuit_breaker.get_circuit_breaker", return_value=cb):
                result = await spawn_with_retry_and_fallback(
                    task,
                    max_retries=3,
                    fallback_to_llm=True,
                )

                # Should skip agent and use LLM directly
                assert result.success
                assert result.fallback is True
                assert result.original_agent == "bad-agent"

                # Only LLM was called, not the agent
                assert spawn_calls == [None]

    @pytest.mark.asyncio
    async def test_circuit_open_no_fallback_returns_error(self):
        """Open circuit without fallback returns circuit open error."""
        cb = CircuitBreaker(failure_threshold=2)
        cb.record_failure("bad-agent")
        cb.record_failure("bad-agent")

        task = SpawnTask(prompt="Task", agent="bad-agent", timeout=10)

        with patch("aurora_spawner.circuit_breaker.get_circuit_breaker", return_value=cb):
            result = await spawn_with_retry_and_fallback(
                task,
                max_retries=3,
                fallback_to_llm=False,
            )

            assert not result.success
            assert "Circuit open" in result.error or "retry in" in result.error

    @pytest.mark.asyncio
    async def test_success_after_retry_closes_circuit(self):
        """Successful execution after retry closes the circuit."""
        cb = CircuitBreaker(failure_threshold=3, failure_window=60.0)
        attempt_count = 0

        async def mock_spawn(task, **kwargs):
            nonlocal attempt_count
            attempt_count += 1

            if attempt_count == 1:
                return SpawnResult(
                    success=False,
                    output="",
                    error="First attempt failed",
                    exit_code=-1,
                )

            return SpawnResult(
                success=True,
                output="Recovered",
                error=None,
                exit_code=0,
            )

        task = SpawnTask(prompt="Recovery task", agent="flaky-agent", timeout=10)

        with patch("aurora_spawner.spawner.spawn", side_effect=mock_spawn):
            with patch("aurora_spawner.circuit_breaker.get_circuit_breaker", return_value=cb):
                result = await spawn_with_retry_and_fallback(
                    task,
                    max_retries=2,
                    fallback_to_llm=False,
                )

                assert result.success
                # Circuit should be closed after success
                assert not cb.is_open("flaky-agent")


# =============================================================================
# RETRY POLICY TESTS
# =============================================================================


class TestRetryPolicyBehavior:
    """Test retry policy configuration behavior."""

    def test_exponential_backoff_delays(self):
        """Exponential backoff calculates correct delays."""
        policy = RetryPolicy(
            max_attempts=5,
            strategy=RetryStrategy.EXPONENTIAL_BACKOFF,
            base_delay=1.0,
            backoff_factor=2.0,
            max_delay=60.0,
            jitter=False,
        )

        assert policy.get_delay(0) == 1.0  # 1 * 2^0
        assert policy.get_delay(1) == 2.0  # 1 * 2^1
        assert policy.get_delay(2) == 4.0  # 1 * 2^2
        assert policy.get_delay(3) == 8.0  # 1 * 2^3

    def test_exponential_backoff_capped_at_max(self):
        """Exponential backoff doesn't exceed max_delay."""
        policy = RetryPolicy(
            strategy=RetryStrategy.EXPONENTIAL_BACKOFF,
            base_delay=10.0,
            backoff_factor=2.0,
            max_delay=30.0,
            jitter=False,
        )

        assert policy.get_delay(0) == 10.0
        assert policy.get_delay(1) == 20.0
        assert policy.get_delay(2) == 30.0  # Capped at max_delay
        assert policy.get_delay(10) == 30.0  # Still capped

    def test_linear_backoff_delays(self):
        """Linear backoff calculates correct delays."""
        policy = RetryPolicy(
            strategy=RetryStrategy.LINEAR_BACKOFF,
            base_delay=5.0,
            backoff_factor=2.0,
            max_delay=100.0,
            jitter=False,
        )

        assert policy.get_delay(0) == 5.0  # 5 * (1 + 2*0) = 5
        assert policy.get_delay(1) == 15.0  # 5 * (1 + 2*1) = 15
        assert policy.get_delay(2) == 25.0  # 5 * (1 + 2*2) = 25

    def test_fixed_delay_constant(self):
        """Fixed delay returns constant value."""
        policy = RetryPolicy(
            strategy=RetryStrategy.FIXED_DELAY,
            base_delay=5.0,
            jitter=False,
        )

        assert policy.get_delay(0) == 5.0
        assert policy.get_delay(1) == 5.0
        assert policy.get_delay(5) == 5.0

    def test_immediate_zero_delay(self):
        """Immediate strategy returns zero delay."""
        policy = RetryPolicy(strategy=RetryStrategy.IMMEDIATE)

        assert policy.get_delay(0) == 0.0
        assert policy.get_delay(5) == 0.0

    def test_jitter_adds_variation(self):
        """Jitter adds randomness to delays."""
        policy = RetryPolicy(
            strategy=RetryStrategy.FIXED_DELAY,
            base_delay=10.0,
            jitter=True,
            jitter_factor=0.1,
        )

        # Get multiple delays and check they vary
        delays = [policy.get_delay(0) for _ in range(10)]

        # Should be approximately 10.0 +/- 1.0 (10% jitter)
        assert all(9.0 <= d <= 11.0 for d in delays)
        # Should have some variation
        assert len(set(delays)) > 1

    def test_should_retry_respects_max_attempts(self):
        """should_retry respects max_attempts limit."""
        policy = RetryPolicy(max_attempts=3)

        assert policy.should_retry(0)[0] is True
        assert policy.should_retry(1)[0] is True
        assert policy.should_retry(2)[0] is True
        assert policy.should_retry(3)[0] is False
        assert "Max attempts" in policy.should_retry(3)[1]

    def test_should_retry_timeout_disabled(self):
        """should_retry respects retry_on_timeout setting."""
        policy = RetryPolicy(max_attempts=5, retry_on_timeout=False)

        assert policy.should_retry(0, "timeout")[0] is False
        assert "timeout disabled" in policy.should_retry(0, "timeout")[1].lower()

        # Other errors still retry
        assert policy.should_retry(0, "other_error")[0] is True

    def test_should_retry_error_patterns_disabled(self):
        """should_retry respects retry_on_error_patterns setting."""
        policy = RetryPolicy(max_attempts=5, retry_on_error_patterns=False)

        assert policy.should_retry(0, "error_pattern")[0] is False


# =============================================================================
# SPAWN POLICY PRESET TESTS
# =============================================================================


class TestSpawnPolicyPresets:
    """Test spawn policy preset configurations."""

    def test_default_policy(self):
        """Default policy has balanced settings."""
        policy = SpawnPolicy.default()

        assert policy.name == "default"
        assert policy.timeout_policy.mode == TimeoutMode.PROGRESSIVE
        assert policy.retry_policy.max_attempts == 3
        assert policy.retry_policy.strategy == RetryStrategy.EXPONENTIAL_BACKOFF
        assert policy.termination_policy.enabled is True

    def test_production_policy(self):
        """Production policy is patient with robust retries."""
        policy = SpawnPolicy.production()

        assert policy.name == "production"
        assert policy.timeout_policy.initial_timeout >= 120.0
        assert policy.timeout_policy.max_timeout >= 600.0
        assert policy.retry_policy.max_attempts >= 3

    def test_fast_fail_policy(self):
        """Fast fail policy minimizes waiting."""
        policy = SpawnPolicy.fast_fail()

        assert policy.name == "fast_fail"
        assert policy.timeout_policy.mode == TimeoutMode.FIXED
        assert policy.retry_policy.max_attempts == 1
        assert policy.retry_policy.retry_on_timeout is False

    def test_test_policy(self):
        """Test policy provides fast feedback."""
        policy = SpawnPolicy.test()

        assert policy.name == "test"
        assert policy.timeout_policy.timeout <= 30.0
        assert policy.retry_policy.circuit_breaker_enabled is False

    def test_from_name_valid(self):
        """from_name creates correct preset."""
        for name in ["default", "production", "fast_fail", "patient", "development", "test"]:
            policy = SpawnPolicy.from_name(name)
            assert policy.name == name

    def test_from_name_invalid(self):
        """from_name raises on unknown preset."""
        with pytest.raises(ValueError, match="Unknown policy preset"):
            SpawnPolicy.from_name("nonexistent")


# =============================================================================
# RECOVERY CALLBACK TESTS
# =============================================================================


class TestRecoveryCallbacks:
    """Test recovery notification callbacks."""

    @pytest.mark.asyncio
    async def test_on_recovery_called_on_retry_success(self):
        """on_recovery callback invoked when task recovers via retry."""
        recovery_events = []
        attempt_count = 0

        def on_recovery(idx, agent_id, retry_count, used_fallback):
            recovery_events.append(
                {
                    "idx": idx,
                    "agent_id": agent_id,
                    "retry_count": retry_count,
                    "fallback": used_fallback,
                }
            )

        async def mock_spawn(task, **kwargs):
            nonlocal attempt_count
            attempt_count += 1

            if attempt_count == 1:
                return SpawnResult(
                    success=False,
                    output="",
                    error="First failed",
                    exit_code=-1,
                )

            return SpawnResult(
                success=True,
                output="Recovered",
                error=None,
                exit_code=0,
            )

        tasks = [SpawnTask(prompt="Task 0", agent="flaky", timeout=10)]

        with patch("aurora_spawner.spawner.spawn", side_effect=mock_spawn):
            with patch("aurora_spawner.circuit_breaker.get_circuit_breaker") as mock_cb:
                # High thresholds to allow retry cascades without circuit opening
                cb = CircuitBreaker(
                    failure_threshold=20, fast_fail_threshold=20, failure_window=600.0
                )
                mock_cb.return_value = cb

                await spawn_parallel_with_recovery(
                    tasks,
                    max_retries=2,
                    on_recovery=on_recovery,
                )

                assert len(recovery_events) == 1
                assert recovery_events[0]["retry_count"] > 0
                assert recovery_events[0]["fallback"] is False

    @pytest.mark.asyncio
    async def test_on_recovery_called_on_fallback(self):
        """on_recovery callback invoked when task uses fallback."""
        recovery_events = []

        def on_recovery(idx, agent_id, retry_count, used_fallback):
            recovery_events.append(
                {
                    "idx": idx,
                    "agent_id": agent_id,
                    "retry_count": retry_count,
                    "fallback": used_fallback,
                }
            )

        async def mock_spawn(task, **kwargs):
            if task.agent:
                return SpawnResult(
                    success=False,
                    output="",
                    error="Agent failed",
                    exit_code=-1,
                )
            return SpawnResult(
                success=True,
                output="LLM worked",
                error=None,
                exit_code=0,
            )

        tasks = [SpawnTask(prompt="Task 0", agent="bad-agent", timeout=10)]

        with patch("aurora_spawner.spawner.spawn", side_effect=mock_spawn):
            with patch("aurora_spawner.circuit_breaker.get_circuit_breaker") as mock_cb:
                # High thresholds to allow retry cascades without circuit opening
                cb = CircuitBreaker(
                    failure_threshold=20, fast_fail_threshold=20, failure_window=600.0
                )
                mock_cb.return_value = cb

                await spawn_parallel_with_recovery(
                    tasks,
                    max_retries=0,
                    fallback_to_llm=True,
                    on_recovery=on_recovery,
                )

                assert len(recovery_events) == 1
                assert recovery_events[0]["fallback"] is True

    @pytest.mark.asyncio
    async def test_on_progress_tracks_recovery_status(self):
        """on_progress callback shows recovery status."""
        progress_events = []

        def on_progress(idx, total, agent_id, status):
            progress_events.append(
                {
                    "idx": idx,
                    "total": total,
                    "agent_id": agent_id,
                    "status": status,
                }
            )

        attempt_count = 0

        async def mock_spawn(task, **kwargs):
            nonlocal attempt_count
            attempt_count += 1

            if attempt_count == 1:
                return SpawnResult(
                    success=False,
                    output="",
                    error="Failed",
                    exit_code=-1,
                )

            return SpawnResult(
                success=True,
                output="OK",
                error=None,
                exit_code=0,
            )

        tasks = [SpawnTask(prompt="Task 0", agent="flaky", timeout=10)]

        with patch("aurora_spawner.spawner.spawn", side_effect=mock_spawn):
            with patch("aurora_spawner.circuit_breaker.get_circuit_breaker") as mock_cb:
                # High thresholds to allow retry cascades without circuit opening
                cb = CircuitBreaker(
                    failure_threshold=20, fast_fail_threshold=20, failure_window=600.0
                )
                mock_cb.return_value = cb

                await spawn_parallel_with_recovery(
                    tasks,
                    max_retries=2,
                    on_progress=on_progress,
                )

                # Should have Starting and final status
                assert any("Starting" in e["status"] for e in progress_events)
                # Final status should indicate recovery
                final = progress_events[-1]
                assert "Recovered" in final["status"] or "Completed" in final["status"]


# =============================================================================
# CASCADING RETRY TESTS
# =============================================================================


class TestCascadingRetries:
    """Test cascading retry scenarios where multiple retries are needed."""

    @pytest.mark.asyncio
    async def test_cascading_retry_eventual_success(self):
        """Task fails multiple times then succeeds after cascade of retries."""
        attempt_count = 0
        success_on_attempt = 4  # Succeed on 4th attempt

        async def mock_spawn(task, **kwargs):
            nonlocal attempt_count
            attempt_count += 1

            if attempt_count < success_on_attempt:
                return SpawnResult(
                    success=False,
                    output="",
                    error=f"Transient failure #{attempt_count}",
                    exit_code=-1,
                )

            return SpawnResult(
                success=True,
                output="Cascading success",
                error=None,
                exit_code=0,
            )

        task = SpawnTask(prompt="Cascading task", agent="flaky-agent", timeout=10)

        with patch("aurora_spawner.spawner.spawn", side_effect=mock_spawn):
            with patch("aurora_spawner.circuit_breaker.get_circuit_breaker") as mock_cb:
                # High thresholds to allow multiple retry cascades without circuit opening
                cb = CircuitBreaker(
                    failure_threshold=20, fast_fail_threshold=20, failure_window=600.0
                )
                mock_cb.return_value = cb

                result = await spawn_with_retry_and_fallback(
                    task,
                    max_retries=5,
                    fallback_to_llm=False,
                )

                assert result.success
                assert attempt_count == success_on_attempt
                assert result.retry_count == success_on_attempt - 1

    @pytest.mark.asyncio
    async def test_cascading_retry_different_errors(self):
        """Task encounters different error types across retries."""
        error_sequence = ["timeout", "connection_error", "parse_error", None]
        current_error_idx = 0

        async def mock_spawn(task, **kwargs):
            nonlocal current_error_idx

            if current_error_idx < len(error_sequence) - 1:
                error = error_sequence[current_error_idx]
                current_error_idx += 1
                return SpawnResult(
                    success=False,
                    output="",
                    error=error,
                    exit_code=-1,
                    termination_reason=(
                        f"Process failed: {error}" if "timeout" in str(error) else None
                    ),
                )

            current_error_idx += 1
            return SpawnResult(
                success=True,
                output="Recovered after multiple error types",
                error=None,
                exit_code=0,
            )

        task = SpawnTask(prompt="Multi-error task", agent="unstable-agent", timeout=10)

        with patch("aurora_spawner.spawner.spawn", side_effect=mock_spawn):
            with patch("aurora_spawner.circuit_breaker.get_circuit_breaker") as mock_cb:
                # High thresholds to allow retry cascades without circuit opening
                cb = CircuitBreaker(
                    failure_threshold=20, fast_fail_threshold=20, failure_window=600.0
                )
                mock_cb.return_value = cb

                result = await spawn_with_retry_and_fallback(
                    task,
                    max_retries=5,
                    fallback_to_llm=False,
                )

                assert result.success
                assert current_error_idx == len(error_sequence)

    @pytest.mark.asyncio
    async def test_cascading_retry_with_backoff_timing(self):
        """Verify backoff delays are applied between cascading retries."""
        call_times = []

        async def mock_spawn(task, **kwargs):
            call_times.append(time.time())

            if len(call_times) < 3:
                return SpawnResult(
                    success=False,
                    output="",
                    error="Retry needed",
                    exit_code=-1,
                )

            return SpawnResult(
                success=True,
                output="Success",
                error=None,
                exit_code=0,
            )

        task = SpawnTask(prompt="Backoff task", agent="test-agent", timeout=10)

        with patch("aurora_spawner.spawner.spawn", side_effect=mock_spawn):
            with patch("aurora_spawner.circuit_breaker.get_circuit_breaker") as mock_cb:
                # High thresholds to allow retry cascades without circuit opening
                cb = CircuitBreaker(
                    failure_threshold=20, fast_fail_threshold=20, failure_window=600.0
                )
                mock_cb.return_value = cb

                policy = SpawnPolicy.default()
                # Set known delays for testing
                policy.retry_policy.base_delay = 0.1
                policy.retry_policy.backoff_factor = 2.0
                policy.retry_policy.jitter = False

                result = await spawn_with_retry_and_fallback(
                    task,
                    max_retries=3,
                    fallback_to_llm=False,
                    policy=policy,
                )

                assert result.success
                assert len(call_times) == 3

                # Check delays increase (with some tolerance)
                delay1 = call_times[1] - call_times[0]
                delay2 = call_times[2] - call_times[1]

                # Delay 2 should be greater than delay 1 (exponential backoff)
                assert delay2 > delay1 * 0.9  # 10% tolerance for timing

    @pytest.mark.asyncio
    async def test_cascading_exhaustion_then_fallback(self):
        """Retry cascade exhausted, then fallback succeeds."""
        agent_attempts = 0
        llm_attempts = 0

        async def mock_spawn(task, **kwargs):
            nonlocal agent_attempts, llm_attempts

            if task.agent:
                agent_attempts += 1
                return SpawnResult(
                    success=False,
                    output="",
                    error="Agent keeps failing",
                    exit_code=-1,
                )

            llm_attempts += 1
            return SpawnResult(
                success=True,
                output="LLM saved the day",
                error=None,
                exit_code=0,
            )

        task = SpawnTask(prompt="Fallback task", agent="hopeless-agent", timeout=10)

        with patch("aurora_spawner.spawner.spawn", side_effect=mock_spawn):
            with patch("aurora_spawner.circuit_breaker.get_circuit_breaker") as mock_cb:
                # High thresholds to allow retry cascades without circuit opening
                cb = CircuitBreaker(
                    failure_threshold=20, fast_fail_threshold=20, failure_window=600.0
                )
                mock_cb.return_value = cb

                result = await spawn_with_retry_and_fallback(
                    task,
                    max_retries=3,
                    fallback_to_llm=True,
                )

                assert result.success
                assert result.fallback is True
                assert result.original_agent == "hopeless-agent"
                assert agent_attempts == 4  # 1 initial + 3 retries
                assert llm_attempts == 1


class TestPartialFailureWithRecoveryChain:
    """Test partial failures in batch execution with recovery chains."""

    @pytest.mark.asyncio
    async def test_batch_mixed_recovery_paths(self):
        """Different tasks take different recovery paths in a batch."""
        call_counts = {}

        async def mock_spawn(task, **kwargs):
            key = f"{task.agent or 'llm'}:{task.prompt}"
            call_counts[key] = call_counts.get(key, 0) + 1
            count = call_counts[key]

            task_idx = int(task.prompt.split()[-1])

            # Task 0: Success immediately
            if task_idx == 0:
                return SpawnResult(success=True, output="immediate", error=None, exit_code=0)

            # Task 1: Fails twice, succeeds on third
            if task_idx == 1:
                if task.agent and count < 3:
                    return SpawnResult(success=False, output="", error="retry me", exit_code=-1)
                return SpawnResult(success=True, output="retry success", error=None, exit_code=0)

            # Task 2: Agent always fails, LLM succeeds
            if task_idx == 2:
                if task.agent:
                    return SpawnResult(
                        success=False, output="", error="need fallback", exit_code=-1
                    )
                return SpawnResult(success=True, output="fallback success", error=None, exit_code=0)

            # Task 3: Everything fails
            if task_idx == 3:
                return SpawnResult(success=False, output="", error="total failure", exit_code=-1)

            return SpawnResult(success=True, output="default", error=None, exit_code=0)

        tasks = [SpawnTask(prompt=f"Task {i}", agent="test-agent", timeout=10) for i in range(4)]

        with patch("aurora_spawner.spawner.spawn", side_effect=mock_spawn):
            with patch("aurora_spawner.circuit_breaker.get_circuit_breaker") as mock_cb:
                # High thresholds to allow retry cascades without circuit opening
                cb = CircuitBreaker(
                    failure_threshold=20, fast_fail_threshold=20, failure_window=600.0
                )
                mock_cb.return_value = cb

                results = await spawn_parallel_with_recovery(
                    tasks,
                    max_concurrent=4,
                    max_retries=3,
                    fallback_to_llm=True,
                )

                # Task 0: Immediate success, no retries
                assert results[0].success
                assert results[0].retry_count == 0
                assert not results[0].fallback

                # Task 1: Success after retries
                assert results[1].success
                assert results[1].retry_count >= 2
                assert not results[1].fallback

                # Task 2: Success via fallback
                assert results[2].success
                assert results[2].fallback

                # Task 3: Complete failure
                assert not results[3].success

    @pytest.mark.asyncio
    async def test_batch_recovery_isolation(self):
        """Recovery of one task doesn't affect parallel task execution."""
        execution_log = []

        async def mock_spawn(task, **kwargs):
            task_idx = int(task.prompt.split()[-1])
            execution_log.append({"task": task_idx, "agent": task.agent, "time": time.time()})

            # Task 1 requires multiple retries with delay
            if task_idx == 1 and task.agent:
                if sum(1 for e in execution_log if e["task"] == 1 and e["agent"]) < 3:
                    await asyncio.sleep(0.05)  # Small delay
                    return SpawnResult(success=False, output="", error="retry", exit_code=-1)

            return SpawnResult(success=True, output=f"task {task_idx}", error=None, exit_code=0)

        tasks = [SpawnTask(prompt=f"Task {i}", agent="agent", timeout=10) for i in range(3)]

        with patch("aurora_spawner.spawner.spawn", side_effect=mock_spawn):
            with patch("aurora_spawner.circuit_breaker.get_circuit_breaker") as mock_cb:
                # High thresholds to allow retry cascades without circuit opening
                cb = CircuitBreaker(
                    failure_threshold=20, fast_fail_threshold=20, failure_window=600.0
                )
                mock_cb.return_value = cb

                results = await spawn_parallel_with_recovery(
                    tasks,
                    max_concurrent=3,
                    max_retries=3,
                    fallback_to_llm=False,
                )

                assert all(r.success for r in results)

                # Tasks 0 and 2 should complete faster than task 1
                task0_logs = [e for e in execution_log if e["task"] == 0]
                task2_logs = [e for e in execution_log if e["task"] == 2]

                assert len(task0_logs) == 1  # No retries needed
                assert len(task2_logs) == 1  # No retries needed

    @pytest.mark.asyncio
    async def test_recovery_with_shared_circuit_breaker(self):
        """Multiple tasks share circuit breaker state during recovery."""
        call_counts = {"agent1": 0, "agent2": 0}

        async def mock_spawn(task, **kwargs):
            agent = task.agent or "llm"
            if agent in call_counts:
                call_counts[agent] += 1

            # Agent1 always fails
            if task.agent == "agent1":
                return SpawnResult(success=False, output="", error="agent1 broken", exit_code=-1)

            # Agent2 succeeds
            if task.agent == "agent2":
                return SpawnResult(success=True, output="agent2 works", error=None, exit_code=0)

            # LLM fallback succeeds
            return SpawnResult(success=True, output="llm works", error=None, exit_code=0)

        tasks = [
            SpawnTask(prompt="Task 0", agent="agent1", timeout=10),
            SpawnTask(prompt="Task 1", agent="agent1", timeout=10),
            SpawnTask(prompt="Task 2", agent="agent2", timeout=10),
        ]

        with patch("aurora_spawner.spawner.spawn", side_effect=mock_spawn):
            # Use real circuit breaker to test interaction
            cb = CircuitBreaker(failure_threshold=2, failure_window=60.0)
            with patch("aurora_spawner.circuit_breaker.get_circuit_breaker", return_value=cb):
                results = await spawn_parallel_with_recovery(
                    tasks,
                    max_concurrent=1,  # Sequential to control order
                    max_retries=1,
                    fallback_to_llm=True,
                )

                # All should succeed (via fallback for agent1 tasks)
                assert all(r.success for r in results)

                # Agent1 circuit should be open after threshold
                assert cb.is_open("agent1")
                assert not cb.is_open("agent2")


class TestMultiTaskCascadingFailure:
    """Test cascading failure scenarios across multiple tasks."""

    @pytest.mark.asyncio
    async def test_circuit_opens_affects_later_tasks(self):
        """Circuit opening from early task failures affects later tasks."""
        spawn_order = []

        async def mock_spawn(task, **kwargs):
            spawn_order.append(task.agent)

            if task.agent == "bad-agent":
                return SpawnResult(success=False, output="", error="always fails", exit_code=-1)

            return SpawnResult(success=True, output="works", error=None, exit_code=0)

        tasks = [SpawnTask(prompt=f"Task {i}", agent="bad-agent", timeout=10) for i in range(5)]

        cb = CircuitBreaker(failure_threshold=2, failure_window=60.0)

        with patch("aurora_spawner.spawner.spawn", side_effect=mock_spawn):
            with patch("aurora_spawner.circuit_breaker.get_circuit_breaker", return_value=cb):
                results = await spawn_parallel_with_recovery(
                    tasks,
                    max_concurrent=1,  # Sequential for predictable order
                    max_retries=0,
                    fallback_to_llm=True,
                )

                # All should succeed via fallback
                assert all(r.success for r in results)

                # Circuit should be open
                assert cb.is_open("bad-agent")

                # Later tasks should have used fallback directly
                # (after circuit opened)
                fallback_results = [r for r in results if r.fallback]
                assert len(fallback_results) >= 3  # Most should be fallbacks

    @pytest.mark.asyncio
    async def test_cascading_failure_with_dependency_chain(self):
        """Simulate failure cascade in sequential task chain."""
        context_chain = []

        async def mock_spawn(task, **kwargs):
            # Extract context from prompt if present
            if "Previous context:" in task.prompt:
                context_chain.append("has_context")
            else:
                context_chain.append("no_context")

            # First task fails once then succeeds
            if "Task 0" in task.prompt:
                if context_chain.count("no_context") == 1:
                    return SpawnResult(success=False, output="", error="first fail", exit_code=-1)
                return SpawnResult(success=True, output="task0_output", error=None, exit_code=0)

            return SpawnResult(success=True, output="subsequent_output", error=None, exit_code=0)

        tasks = [SpawnTask(prompt=f"Task {i}", agent="seq-agent", timeout=10) for i in range(3)]

        with patch("aurora_spawner.spawner.spawn", side_effect=mock_spawn):
            from aurora_spawner.spawner import spawn_sequential

            results = await spawn_sequential(
                tasks,
                pass_context=True,
                stop_on_failure=True,
            )

            # First task failed, chain stopped
            assert len(results) == 1
            assert not results[0].success

    @pytest.mark.asyncio
    async def test_recovery_metrics_from_results(self):
        """Calculate recovery metrics from SpawnResult data."""
        # Simulate results from spawn_parallel_with_recovery
        results = [
            SpawnResult(
                success=True, output="ok", error=None, exit_code=0, retry_count=0, fallback=False
            ),
            SpawnResult(
                success=True, output="ok", error=None, exit_code=0, retry_count=2, fallback=False
            ),
            SpawnResult(
                success=True, output="ok", error=None, exit_code=0, retry_count=3, fallback=True
            ),
            SpawnResult(
                success=False, output="", error="failed", exit_code=-1, retry_count=3, fallback=True
            ),
        ]

        # Calculate metrics from results
        total = len(results)
        succeeded = sum(1 for r in results if r.success)
        failed = sum(1 for r in results if not r.success)
        recovered = sum(1 for r in results if r.success and r.retry_count > 0)
        used_fallback = sum(1 for r in results if r.fallback)
        total_retries = sum(r.retry_count for r in results)

        assert total == 4
        assert succeeded == 3
        assert failed == 1
        assert recovered == 2  # Tasks 1 and 2 recovered (retry_count > 0 and success)
        assert used_fallback == 2  # Tasks 2 and 3 used fallback
        assert total_retries == 8  # 0 + 2 + 3 + 3

        success_rate = (succeeded / total) * 100
        assert success_rate == 75.0


# =============================================================================
# ERROR CLASSIFICATION TESTS
# =============================================================================


class TestErrorClassifier:
    """Test error classification for smart recovery decisions."""

    def test_classify_transient_errors(self):
        """Classify transient errors correctly."""
        from aurora_spawner.recovery import ErrorCategory, ErrorClassifier

        classifier = ErrorClassifier()

        # Rate limit errors
        assert classifier.classify("Rate limit exceeded") == ErrorCategory.TRANSIENT
        assert classifier.classify("Error 429 too many requests") == ErrorCategory.TRANSIENT
        assert classifier.classify("Connection reset by peer") == ErrorCategory.TRANSIENT
        assert classifier.classify("ECONNRESET error") == ErrorCategory.TRANSIENT
        assert classifier.classify("Service unavailable, try again") == ErrorCategory.TRANSIENT
        assert classifier.classify("503 Service Unavailable") == ErrorCategory.TRANSIENT

    def test_classify_permanent_errors(self):
        """Classify permanent errors correctly."""
        from aurora_spawner.recovery import ErrorCategory, ErrorClassifier

        classifier = ErrorClassifier()

        # Auth errors
        assert classifier.classify("Authentication failed") == ErrorCategory.PERMANENT
        assert classifier.classify("Invalid API key provided") == ErrorCategory.PERMANENT
        assert classifier.classify("401 Unauthorized") == ErrorCategory.PERMANENT
        assert classifier.classify("403 Forbidden") == ErrorCategory.PERMANENT
        assert classifier.classify("Model not found: gpt-5") == ErrorCategory.PERMANENT
        assert classifier.classify("Permission denied") == ErrorCategory.PERMANENT

    def test_classify_timeout_errors(self):
        """Classify timeout errors correctly."""
        from aurora_spawner.recovery import ErrorCategory, ErrorClassifier

        classifier = ErrorClassifier()

        assert classifier.classify("Request timed out") == ErrorCategory.TIMEOUT
        assert classifier.classify("Deadline exceeded") == ErrorCategory.TIMEOUT
        assert classifier.classify("No activity for 30 seconds") == ErrorCategory.TIMEOUT

    def test_classify_resource_errors(self):
        """Classify resource errors correctly."""
        from aurora_spawner.recovery import ErrorCategory, ErrorClassifier

        classifier = ErrorClassifier()

        assert classifier.classify("Quota exceeded") == ErrorCategory.RESOURCE
        assert classifier.classify("Out of memory") == ErrorCategory.RESOURCE
        assert classifier.classify("Resource exhausted") == ErrorCategory.RESOURCE

    def test_classify_unknown_errors(self):
        """Unknown errors return UNKNOWN category."""
        from aurora_spawner.recovery import ErrorCategory, ErrorClassifier

        classifier = ErrorClassifier()

        assert classifier.classify("Some random error") == ErrorCategory.UNKNOWN
        assert classifier.classify("") == ErrorCategory.UNKNOWN
        assert classifier.classify("Unexpected issue occurred") == ErrorCategory.UNKNOWN

    def test_should_retry_categories(self):
        """Check which categories should be retried."""
        from aurora_spawner.recovery import ErrorCategory, ErrorClassifier

        classifier = ErrorClassifier()

        # Transient, timeout, resource, and unknown should retry
        assert classifier.should_retry(ErrorCategory.TRANSIENT) is True
        assert classifier.should_retry(ErrorCategory.TIMEOUT) is True
        assert classifier.should_retry(ErrorCategory.RESOURCE) is True
        assert classifier.should_retry(ErrorCategory.UNKNOWN) is True

        # Permanent should not retry
        assert classifier.should_retry(ErrorCategory.PERMANENT) is False

    def test_add_custom_pattern(self):
        """Add custom patterns to classifier."""
        from aurora_spawner.recovery import ErrorCategory, ErrorClassifier

        classifier = ErrorClassifier()

        # Add custom pattern
        classifier.add_pattern(ErrorCategory.TRANSIENT, r"my_custom_error")

        # Should now classify as transient
        assert classifier.classify("my_custom_error occurred") == ErrorCategory.TRANSIENT


# =============================================================================
# RECOVERY METRICS TESTS
# =============================================================================


class TestRecoveryMetrics:
    """Test recovery metrics tracking."""

    def test_record_and_calculate_success_rate(self):
        """Record attempts and calculate success rate."""
        from aurora_spawner.recovery import RecoveryMetrics

        metrics = RecoveryMetrics()

        # Record some attempts
        metrics.record_attempt("agent-1", success=True)
        metrics.record_attempt("agent-1", success=True)
        metrics.record_attempt("agent-1", success=False)

        # 2/3 = 66.67%
        assert metrics.success_rate("agent-1") == pytest.approx(66.67, rel=0.01)

    def test_record_with_retries(self):
        """Track retry counts."""
        from aurora_spawner.recovery import RecoveryMetrics

        metrics = RecoveryMetrics()

        metrics.record_attempt("agent-1", success=True, retries=2)
        metrics.record_attempt("agent-1", success=True, retries=0)

        # Total retries should be 2
        assert metrics._retries.get("agent-1", 0) == 2

    def test_record_with_fallback(self):
        """Track fallback usage."""
        from aurora_spawner.recovery import RecoveryMetrics

        metrics = RecoveryMetrics()

        metrics.record_attempt("agent-1", success=True, used_fallback=True)
        metrics.record_attempt("agent-1", success=True, used_fallback=False)

        assert metrics._fallbacks.get("agent-1", 0) == 1

    def test_overall_success_rate(self):
        """Calculate overall success rate across agents."""
        from aurora_spawner.recovery import RecoveryMetrics

        metrics = RecoveryMetrics()

        metrics.record_attempt("agent-1", success=True)
        metrics.record_attempt("agent-1", success=True)
        metrics.record_attempt("agent-2", success=False)
        metrics.record_attempt("agent-2", success=False)

        # Overall: 2 success / 4 attempts = 50%
        assert metrics.success_rate() == 50.0

    def test_avg_recovery_time(self):
        """Calculate average recovery time."""
        from aurora_spawner.recovery import RecoveryMetrics

        metrics = RecoveryMetrics()

        metrics.record_attempt("agent-1", success=True, recovery_time=1.0)
        metrics.record_attempt("agent-1", success=True, recovery_time=3.0)

        # Average: (1.0 + 3.0) / 2 = 2.0
        assert metrics.avg_recovery_time("agent-1") == 2.0

    def test_to_dict(self):
        """Convert metrics to dictionary."""
        from aurora_spawner.recovery import RecoveryMetrics

        metrics = RecoveryMetrics()

        metrics.record_attempt("agent-1", success=True, retries=1)
        metrics.record_attempt("agent-1", success=False)

        result = metrics.to_dict()

        assert result["total_attempts"] == 2
        assert result["total_successes"] == 1
        assert result["total_failures"] == 1
        assert "by_agent" in result
        assert "agent-1" in result["by_agent"]

    def test_reset_clears_metrics(self):
        """Reset clears all metrics."""
        from aurora_spawner.recovery import RecoveryMetrics

        metrics = RecoveryMetrics()

        metrics.record_attempt("agent-1", success=True)
        metrics.record_attempt("agent-2", success=False)

        metrics.reset()

        assert metrics.success_rate() == 0.0
        assert len(metrics._attempts) == 0

    def test_global_metrics_singleton(self):
        """Global metrics functions work correctly."""
        from aurora_spawner.recovery import get_recovery_metrics, reset_recovery_metrics

        reset_recovery_metrics()  # Start clean
        metrics = get_recovery_metrics()
        metrics.record_attempt("test-agent", success=True)

        # Same instance returned
        metrics2 = get_recovery_metrics()
        assert metrics is metrics2

        # Reset clears it
        reset_recovery_metrics()
        assert get_recovery_metrics().success_rate() == 0.0


# =============================================================================
# RECOVERY POLICY CONFIG TESTS
# =============================================================================


class TestRecoveryPolicyConfig:
    """Test recovery policy configuration from dict/config."""

    def test_from_dict_basic(self):
        """Create policy from basic dictionary."""
        from aurora_spawner.recovery import RecoveryPolicy, RecoveryStrategy

        policy = RecoveryPolicy.from_dict(
            {
                "strategy": "retry_then_fallback",
                "max_retries": 5,
                "fallback_to_llm": True,
                "base_delay": 2.0,
            }
        )

        assert policy.strategy == RecoveryStrategy.RETRY_THEN_FALLBACK
        assert policy.max_retries == 5
        assert policy.fallback_to_llm is True
        assert policy.base_delay == 2.0

    def test_from_dict_with_agent_overrides(self):
        """Create policy with agent-specific overrides."""
        from aurora_spawner.recovery import RecoveryPolicy

        policy = RecoveryPolicy.from_dict(
            {
                "max_retries": 2,
                "agent_overrides": {
                    "slow-agent": {
                        "max_retries": 5,
                        "base_delay": 5.0,
                    }
                },
            }
        )

        assert policy.max_retries == 2
        assert policy.get_for_agent("slow-agent").max_retries == 5
        assert policy.get_for_agent("slow-agent").base_delay == 5.0

    def test_from_config_with_preset(self):
        """Create policy from config with preset name."""
        from aurora_spawner.recovery import RecoveryPolicy

        config = {"spawner": {"recovery": {"preset": "patient"}}}

        policy = RecoveryPolicy.from_config(config)

        # Should have patient preset values
        assert policy.max_retries == 3
        assert policy.base_delay == 2.0

    def test_from_config_with_preset_and_overrides(self):
        """Preset with field overrides applied on top."""
        from aurora_spawner.recovery import RecoveryPolicy

        config = {
            "spawner": {
                "recovery": {
                    "preset": "patient",
                    "max_retries": 10,  # Override
                }
            }
        }

        policy = RecoveryPolicy.from_config(config)

        # Max retries overridden
        assert policy.max_retries == 10
        # Other patient values preserved
        assert policy.base_delay == 2.0

    def test_from_config_empty_returns_default(self):
        """Empty config returns default policy."""
        from aurora_spawner.recovery import RecoveryPolicy

        config = {}
        policy = RecoveryPolicy.from_config(config)

        default = RecoveryPolicy.default()
        assert policy.max_retries == default.max_retries
        assert policy.fallback_to_llm == default.fallback_to_llm

    def test_to_dict_roundtrip(self):
        """Policy survives roundtrip to/from dict."""
        from aurora_spawner.recovery import RecoveryPolicy, RecoveryStrategy

        original = RecoveryPolicy(
            strategy=RecoveryStrategy.RETRY_SAME,
            max_retries=4,
            fallback_to_llm=False,
            base_delay=1.5,
            backoff_factor=3.0,
            jitter=False,
        )

        data = original.to_dict()
        restored = RecoveryPolicy.from_dict(data)

        assert restored.strategy == original.strategy
        assert restored.max_retries == original.max_retries
        assert restored.fallback_to_llm == original.fallback_to_llm
        assert restored.base_delay == original.base_delay
        assert restored.backoff_factor == original.backoff_factor

    def test_should_retry_error_integration(self):
        """RecoveryPolicy.should_retry_error uses classifier."""
        from aurora_spawner.recovery import RecoveryPolicy

        policy = RecoveryPolicy.default()

        # Transient error - should retry
        assert policy.should_retry_error("Rate limit exceeded") is True

        # Permanent error - should not retry
        assert policy.should_retry_error("Invalid API key") is False

    def test_classify_error_method(self):
        """RecoveryPolicy.classify_error exposes classifier."""
        from aurora_spawner.recovery import ErrorCategory, RecoveryPolicy

        policy = RecoveryPolicy.default()

        assert policy.classify_error("Connection reset") == ErrorCategory.TRANSIENT
        assert policy.classify_error("401 Unauthorized") == ErrorCategory.PERMANENT
