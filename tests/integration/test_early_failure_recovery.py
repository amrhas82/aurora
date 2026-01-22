"""Integration tests for early failure detection and recovery scenarios.

Tests validate end-to-end behavior of:
1. Error pattern detection triggering circuit breaker
2. Progressive timeout extensions on activity
3. Recovery from transient failures via retry
4. Graceful degradation to LLM fallback
5. Circuit breaker preventing repeated failures
6. Policy presets behaving correctly in scenarios
"""

import asyncio
import time
from unittest.mock import patch

import pytest

from aurora_spawner.circuit_breaker import CircuitBreaker
from aurora_spawner.models import SpawnResult, SpawnTask
from aurora_spawner.spawner import spawn, spawn_with_retry_and_fallback
from aurora_spawner.timeout_policy import (
    RetryPolicy,
    RetryStrategy,
    SpawnPolicy,
    TerminationPolicy,
    TimeoutMode,
    TimeoutPolicy,
)


@pytest.fixture
def fresh_circuit_breaker():
    """Provide fresh circuit breaker for each test."""
    cb = CircuitBreaker(failure_threshold=3, half_open_after=5.0)
    cb.reset_all()
    return cb


@pytest.fixture
def mock_spawner():
    """Mock spawner for controlled testing."""
    with patch("aurora_spawner.spawner.spawn") as mock_spawn:
        yield mock_spawn


class TestErrorPatternDetection:
    """Test early termination on error pattern matches."""

    @pytest.mark.asyncio
    async def test_api_rate_limit_triggers_early_termination(self):
        """API rate limit error should kill process immediately."""
        task = SpawnTask(
            prompt="echo 'Working...'; echo 'rate limit exceeded' >&2; sleep 30",
            agent=None,
            timeout=60,
        )

        policy = SpawnPolicy(
            name="test",
            timeout_policy=TimeoutPolicy(mode=TimeoutMode.FIXED, timeout=60.0),
            termination_policy=TerminationPolicy(
                enabled=True,
                kill_on_error_patterns=True,
                error_patterns=[r"rate.?limit"],
            ),
        )

        start = time.time()
        result = await spawn(task, tool="bash", model="-c", policy=policy)
        elapsed = time.time() - start

        assert not result.success
        assert result.termination_reason is not None
        assert "error pattern" in result.termination_reason.lower()
        assert elapsed < 5  # Should terminate quickly
        assert result.exit_code == -1

    @pytest.mark.asyncio
    async def test_connection_error_triggers_termination(self):
        """Connection errors should trigger immediate termination."""
        task = SpawnTask(
            prompt="echo 'Starting'; echo 'ECONNRESET: connection reset by peer' >&2; sleep 20",
            agent=None,
            timeout=60,
        )

        policy = SpawnPolicy(
            name="test",
            termination_policy=TerminationPolicy(
                enabled=True,
                kill_on_error_patterns=True,
                error_patterns=[r"ECONNRESET", r"connection.?(refused|reset|error)"],
            ),
        )

        start = time.time()
        result = await spawn(task, tool="bash", model="-c", policy=policy)
        elapsed = time.time() - start

        assert not result.success
        assert "error pattern" in result.termination_reason.lower()
        assert elapsed < 5

    @pytest.mark.asyncio
    async def test_multiple_error_patterns_detected(self):
        """Test detection of multiple error patterns."""
        task = SpawnTask(
            prompt="echo 'API error: unauthorized' >&2; sleep 10",
            agent=None,
            timeout=30,
        )

        policy = SpawnPolicy(
            name="test",
            termination_policy=TerminationPolicy(
                enabled=True,
                kill_on_error_patterns=True,
                error_patterns=[r"API.?error", r"unauthorized"],
            ),
        )

        result = await spawn(task, tool="bash", model="-c", policy=policy)

        assert not result.success
        assert result.termination_reason is not None


class TestProgressiveTimeout:
    """Test progressive timeout behavior with activity detection."""

    @pytest.mark.asyncio
    async def test_timeout_extends_on_activity(self):
        """Active processes should get timeout extensions."""
        task = SpawnTask(
            prompt="for i in {1..10}; do echo 'Progress '$i; sleep 1; done; echo 'Done'",
            agent=None,
            timeout=60,
        )

        policy = SpawnPolicy(
            name="test",
            timeout_policy=TimeoutPolicy(
                mode=TimeoutMode.PROGRESSIVE,
                initial_timeout=5.0,
                max_timeout=15.0,
                extension_threshold=2.0,
                activity_check_interval=0.5,
            ),
            termination_policy=TerminationPolicy(kill_on_no_activity=False),
        )

        start = time.time()
        result = await spawn(task, tool="bash", model="-c", policy=policy)
        elapsed = time.time() - start

        assert result.success
        assert result.timeout_extended
        assert elapsed > 5  # Longer than initial timeout
        assert "Done" in result.output

    @pytest.mark.asyncio
    async def test_timeout_does_not_extend_without_activity(self):
        """Inactive processes should timeout at initial threshold."""
        task = SpawnTask(
            prompt="echo 'Start'; sleep 10",
            agent=None,
            timeout=60,
        )

        policy = SpawnPolicy(
            name="test",
            timeout_policy=TimeoutPolicy(
                mode=TimeoutMode.PROGRESSIVE,
                initial_timeout=3.0,
                max_timeout=20.0,
                extension_threshold=1.0,
                no_activity_timeout=5.0,
            ),
            termination_policy=TerminationPolicy(kill_on_no_activity=True),
        )

        start = time.time()
        result = await spawn(task, tool="bash", model="-c", policy=policy)
        elapsed = time.time() - start

        assert not result.success
        assert elapsed < 8  # Should terminate due to inactivity

    @pytest.mark.asyncio
    async def test_fixed_timeout_never_extends(self):
        """Fixed timeout mode should never extend regardless of activity."""
        task = SpawnTask(
            prompt="for i in {1..20}; do echo $i; sleep 0.5; done",
            agent=None,
            timeout=60,
        )

        policy = SpawnPolicy(
            name="test",
            timeout_policy=TimeoutPolicy(
                mode=TimeoutMode.FIXED,
                timeout=5.0,
                activity_check_interval=0.5,
            ),
            termination_policy=TerminationPolicy(kill_on_no_activity=False),
        )

        start = time.time()
        result = await spawn(task, tool="bash", model="-c", policy=policy)
        elapsed = time.time() - start

        assert not result.success
        assert not result.timeout_extended
        assert elapsed >= 5 and elapsed < 8


class TestRetryLogic:
    """Test retry behavior with various strategies."""

    @pytest.mark.asyncio
    async def test_transient_failure_recovers_on_retry(self, mock_spawner):
        """Transient failures should recover on retry."""
        call_count = 0

        async def transient_failure(task, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                return SpawnResult(
                    success=False,
                    output="",
                    error="Transient network error",
                    exit_code=1,
                )
            return SpawnResult(
                success=True,
                output="Success after retry",
                error=None,
                exit_code=0,
            )

        mock_spawner.side_effect = transient_failure

        task = SpawnTask(prompt="test", agent="test-agent", timeout=60)
        policy = SpawnPolicy(
            name="test",
            retry_policy=RetryPolicy(
                max_attempts=5,
                strategy=RetryStrategy.EXPONENTIAL_BACKOFF,
                base_delay=0.1,
                jitter=False,
                circuit_breaker_enabled=False,
            ),
        )

        result = await spawn_with_retry_and_fallback(
            task,
            policy=policy,
            fallback_to_llm=False,
            circuit_breaker=None,
        )

        assert result.success
        assert call_count == 3
        assert result.retry_count == 2

    @pytest.mark.asyncio
    async def test_max_retries_respected(self, mock_spawner):
        """Retry should stop after max attempts."""
        call_count = 0

        async def always_fail(task, **kwargs):
            nonlocal call_count
            call_count += 1
            return SpawnResult(
                success=False,
                output="",
                error=f"Failure {call_count}",
                exit_code=1,
            )

        mock_spawner.side_effect = always_fail

        task = SpawnTask(prompt="test", agent="failing-agent", timeout=60)
        policy = SpawnPolicy(
            name="test",
            retry_policy=RetryPolicy(
                max_attempts=3,
                strategy=RetryStrategy.IMMEDIATE,
                circuit_breaker_enabled=False,
            ),
        )

        result = await spawn_with_retry_and_fallback(task, policy=policy, fallback_to_llm=False)

        assert not result.success
        assert call_count == 3
        assert result.retry_count == 3

    @pytest.mark.asyncio
    async def test_exponential_backoff_delays(self, mock_spawner):
        """Exponential backoff should apply increasing delays."""
        delays = []

        async def track_delays(task, **kwargs):
            delays.append(time.time())
            return SpawnResult(success=False, output="", error="Fail", exit_code=1)

        mock_spawner.side_effect = track_delays

        task = SpawnTask(prompt="test", agent="test-agent", timeout=60)
        policy = SpawnPolicy(
            name="test",
            retry_policy=RetryPolicy(
                max_attempts=4,
                strategy=RetryStrategy.EXPONENTIAL_BACKOFF,
                base_delay=0.1,
                backoff_factor=2.0,
                jitter=False,
                circuit_breaker_enabled=False,
            ),
        )

        await spawn_with_retry_and_fallback(task, policy=policy, fallback_to_llm=False)

        # Check delays increase: ~0.1s, ~0.2s, ~0.4s
        assert len(delays) == 4
        assert delays[1] - delays[0] >= 0.1  # First retry delay
        assert delays[2] - delays[1] >= 0.2  # Second retry delay
        assert delays[3] - delays[2] >= 0.3  # Third retry delay


class TestCircuitBreakerIntegration:
    """Test circuit breaker preventing repeated failures."""

    @pytest.mark.asyncio
    async def test_circuit_opens_after_failures(self, fresh_circuit_breaker, mock_spawner):
        """Circuit should open after threshold failures."""

        async def always_fail(task, **kwargs):
            return SpawnResult(success=False, output="", error="Failure", exit_code=1)

        mock_spawner.side_effect = always_fail

        task = SpawnTask(prompt="test", agent="unstable-agent", timeout=60)
        policy = SpawnPolicy(
            name="test",
            retry_policy=RetryPolicy(
                max_attempts=1,
                strategy=RetryStrategy.IMMEDIATE,
                circuit_breaker_enabled=True,
            ),
        )

        # Execute 3 times to open circuit
        for _ in range(3):
            result = await spawn_with_retry_and_fallback(
                task,
                policy=policy,
                fallback_to_llm=False,
                circuit_breaker=fresh_circuit_breaker,
            )
            assert not result.success

        # Check circuit is open
        should_skip, reason = fresh_circuit_breaker.should_skip("unstable-agent")
        assert should_skip
        assert "Circuit open" in reason

    @pytest.mark.asyncio
    async def test_circuit_open_skips_to_fallback(self, fresh_circuit_breaker, mock_spawner):
        """Open circuit should skip directly to fallback."""

        async def mock_response(task, **kwargs):
            if task.agent is None:
                # Fallback LLM succeeds
                return SpawnResult(
                    success=True,
                    output="Fallback response",
                    error=None,
                    exit_code=0,
                )
            # Agent fails
            return SpawnResult(success=False, output="", error="Fail", exit_code=1)

        mock_spawner.side_effect = mock_response

        task = SpawnTask(prompt="test", agent="broken-agent", timeout=60)
        policy = SpawnPolicy(
            name="test",
            retry_policy=RetryPolicy(max_attempts=1, circuit_breaker_enabled=True),
        )

        # Open the circuit
        for _ in range(3):
            await spawn_with_retry_and_fallback(
                task,
                policy=policy,
                fallback_to_llm=False,
                circuit_breaker=fresh_circuit_breaker,
            )

        # Next call should skip directly to fallback
        result = await spawn_with_retry_and_fallback(
            task,
            policy=policy,
            fallback_to_llm=True,
            circuit_breaker=fresh_circuit_breaker,
        )

        assert result.success
        assert result.fallback
        assert result.original_agent == "broken-agent"
        assert result.retry_count == 0

    @pytest.mark.asyncio
    async def test_circuit_recovery_after_success(self, fresh_circuit_breaker, mock_spawner):
        """Circuit should close after successful executions."""
        attempt_count = 0

        async def flaky_agent(task, **kwargs):
            nonlocal attempt_count
            attempt_count += 1
            # Fail first 3 times, then succeed
            if attempt_count <= 3:
                return SpawnResult(success=False, output="", error="Fail", exit_code=1)
            return SpawnResult(success=True, output="Success", error=None, exit_code=0)

        mock_spawner.side_effect = flaky_agent

        task = SpawnTask(prompt="test", agent="flaky-agent", timeout=60)
        policy = SpawnPolicy(
            name="test",
            retry_policy=RetryPolicy(max_attempts=1, circuit_breaker_enabled=True),
        )

        # Execute 3 failing attempts to open circuit
        for _ in range(3):
            await spawn_with_retry_and_fallback(
                task,
                policy=policy,
                fallback_to_llm=False,
                circuit_breaker=fresh_circuit_breaker,
            )

        # Circuit should be open
        assert fresh_circuit_breaker.should_skip("flaky-agent")[0]

        # Wait for half-open state
        await asyncio.sleep(5.1)

        # Successful attempt should close circuit
        result = await spawn_with_retry_and_fallback(
            task,
            policy=policy,
            fallback_to_llm=False,
            circuit_breaker=fresh_circuit_breaker,
        )

        assert result.success
        # Circuit should now be closed
        assert not fresh_circuit_breaker.should_skip("flaky-agent")[0]


class TestGracefulDegradation:
    """Test fallback to LLM when agents fail."""

    @pytest.mark.asyncio
    async def test_fallback_after_all_retries_exhausted(self, mock_spawner):
        """Should fallback to LLM after retries exhausted."""

        async def mock_response(task, **kwargs):
            if task.agent is None:
                return SpawnResult(success=True, output="LLM response", error=None, exit_code=0)
            return SpawnResult(success=False, output="", error="Agent failed", exit_code=1)

        mock_spawner.side_effect = mock_response

        task = SpawnTask(prompt="test", agent="broken-agent", timeout=60)
        policy = SpawnPolicy(
            name="test",
            retry_policy=RetryPolicy(
                max_attempts=2,
                strategy=RetryStrategy.IMMEDIATE,
                circuit_breaker_enabled=False,
            ),
        )

        result = await spawn_with_retry_and_fallback(task, policy=policy, fallback_to_llm=True)

        assert result.success
        assert result.fallback
        assert result.original_agent == "broken-agent"
        assert "LLM response" in result.output

    @pytest.mark.asyncio
    async def test_no_fallback_when_disabled(self, mock_spawner):
        """Should not fallback if disabled."""

        async def always_fail(task, **kwargs):
            return SpawnResult(success=False, output="", error="Fail", exit_code=1)

        mock_spawner.side_effect = always_fail

        task = SpawnTask(prompt="test", agent="broken-agent", timeout=60)
        policy = SpawnPolicy(
            name="test",
            retry_policy=RetryPolicy(max_attempts=2, circuit_breaker_enabled=False),
        )

        result = await spawn_with_retry_and_fallback(task, policy=policy, fallback_to_llm=False)

        assert not result.success
        assert not result.fallback
        assert result.original_agent is None


class TestPolicyPresets:
    """Test behavior of policy presets in realistic scenarios."""

    @pytest.mark.asyncio
    async def test_production_policy_patient_with_activity(self):
        """Production policy should be patient with active processes."""
        task = SpawnTask(
            prompt="for i in {1..15}; do echo 'Working '$i; sleep 1; done; echo 'Complete'",
            agent=None,
            timeout=600,
        )

        policy = SpawnPolicy.production()

        start = time.time()
        result = await spawn(task, tool="bash", model="-c", policy=policy)
        elapsed = time.time() - start

        assert result.success
        assert "Complete" in result.output
        assert elapsed >= 15  # Should let it run

    @pytest.mark.asyncio
    async def test_fast_fail_policy_terminates_quickly(self):
        """Fast fail policy should terminate quickly."""
        task = SpawnTask(
            prompt="echo 'Start'; sleep 120",
            agent=None,
            timeout=60,
        )

        policy = SpawnPolicy.fast_fail()

        start = time.time()
        result = await spawn(task, tool="bash", model="-c", policy=policy)
        elapsed = time.time() - start

        assert not result.success
        assert elapsed < 25  # Should timeout quickly

    @pytest.mark.asyncio
    async def test_test_policy_detects_errors_fast(self):
        """Test policy should detect errors immediately."""
        task = SpawnTask(
            prompt="echo 'API error: rate limit' >&2; sleep 30",
            agent=None,
            timeout=30,
        )

        policy = SpawnPolicy.test()

        start = time.time()
        result = await spawn(task, tool="bash", model="-c", policy=policy)
        elapsed = time.time() - start

        assert not result.success
        assert elapsed < 5


class TestComplexScenarios:
    """Test complex real-world scenarios."""

    @pytest.mark.asyncio
    async def test_cascade_failure_with_recovery(self, fresh_circuit_breaker, mock_spawner):
        """Test recovery from cascading failures."""
        call_log = []

        async def cascade_scenario(task, **kwargs):
            call_log.append((task.agent, time.time()))
            agent_name = task.agent or "llm"

            # First agent fails twice then succeeds
            if agent_name == "agent-1":
                if len([c for c in call_log if c[0] == "agent-1"]) < 3:
                    return SpawnResult(success=False, output="", error="Transient", exit_code=1)
                return SpawnResult(success=True, output="Agent-1 success", error=None, exit_code=0)

            # LLM fallback always succeeds
            if agent_name == "llm":
                return SpawnResult(success=True, output="LLM success", error=None, exit_code=0)

            return SpawnResult(success=False, output="", error="Unknown agent", exit_code=1)

        mock_spawner.side_effect = cascade_scenario

        task = SpawnTask(prompt="complex task", agent="agent-1", timeout=60)
        policy = SpawnPolicy(
            name="test",
            retry_policy=RetryPolicy(
                max_attempts=5,
                strategy=RetryStrategy.EXPONENTIAL_BACKOFF,
                base_delay=0.1,
                jitter=False,
                circuit_breaker_enabled=False,
            ),
        )

        result = await spawn_with_retry_and_fallback(
            task,
            policy=policy,
            fallback_to_llm=True,
            circuit_breaker=fresh_circuit_breaker,
        )

        assert result.success
        assert len(call_log) == 3  # 3 attempts to agent-1 before success
        assert call_log[-1][0] == "agent-1"

    @pytest.mark.asyncio
    async def test_timeout_with_error_pattern_combination(self):
        """Test behavior when both timeout and error pattern occur."""
        task = SpawnTask(
            prompt="sleep 2; echo 'API error: unauthorized' >&2; sleep 30",
            agent=None,
            timeout=60,
        )

        policy = SpawnPolicy(
            name="test",
            timeout_policy=TimeoutPolicy(mode=TimeoutMode.FIXED, timeout=20.0),
            termination_policy=TerminationPolicy(
                enabled=True,
                kill_on_error_patterns=True,
                error_patterns=[r"API.?error"],
            ),
        )

        start = time.time()
        result = await spawn(task, tool="bash", model="-c", policy=policy)
        elapsed = time.time() - start

        # Should terminate on error pattern, not timeout
        assert not result.success
        assert elapsed < 10  # Much less than 20s timeout
        assert "error pattern" in result.termination_reason.lower()
