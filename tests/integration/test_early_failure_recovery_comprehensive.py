"""Comprehensive integration tests for early failure detection and recovery.

Tests the full lifecycle of failure detection, circuit breaker integration,
recovery procedures, and SOAR orchestrator interaction with spawner resilience features.
"""

import asyncio
import time

import pytest

from aurora_spawner.circuit_breaker import CircuitBreaker, CircuitState
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


class TestTimeoutPolicyIntegration:
    """Integration tests for timeout policy modes across spawn lifecycle."""

    @pytest.mark.asyncio
    async def test_progressive_timeout_extends_on_activity(self):
        """Test that progressive mode extends timeout when process shows activity."""
        task = SpawnTask(
            prompt="for i in {1..5}; do echo 'Progress $i'; sleep 1; done",
            agent=None,
            timeout=60,
        )

        policy = SpawnPolicy(
            name="progressive-test",
            timeout_policy=TimeoutPolicy(
                mode=TimeoutMode.PROGRESSIVE,
                initial_timeout=3.0,
                max_timeout=15.0,
                extension_threshold=2.0,
                activity_check_interval=0.5,
            ),
            termination_policy=TerminationPolicy(enabled=False),
        )

        start = time.time()
        result = await spawn(task, tool="bash", model="-c", policy=policy)
        elapsed = time.time() - start

        assert result.success
        assert result.timeout_extended
        # Should complete (5s) even though initial timeout is 3s
        assert elapsed >= 5.0
        assert elapsed < 10.0

    @pytest.mark.asyncio
    async def test_fixed_timeout_never_extends(self):
        """Test that fixed mode strictly enforces timeout without extension."""
        task = SpawnTask(
            prompt="for i in {1..10}; do echo $i; sleep 1; done",
            agent=None,
            timeout=3,
        )

        policy = SpawnPolicy(
            name="fixed-test",
            timeout_policy=TimeoutPolicy(
                mode=TimeoutMode.FIXED,
                timeout=3.0,
                activity_check_interval=0.5,
            ),
            termination_policy=TerminationPolicy(kill_on_no_activity=False),
        )

        start = time.time()
        result = await spawn(task, tool="bash", model="-c", policy=policy)
        elapsed = time.time() - start

        assert not result.success
        assert result.termination_reason is not None
        assert "timed out" in result.termination_reason.lower()
        assert not result.timeout_extended
        assert elapsed >= 3.0 and elapsed < 6.0

    @pytest.mark.asyncio
    async def test_no_activity_timeout_kills_idle_process(self):
        """Test that no-activity timeout terminates idle processes."""
        task = SpawnTask(
            prompt="echo 'Starting'; sleep 30",
            agent=None,
            timeout=60,
        )

        policy = SpawnPolicy(
            name="no-activity-test",
            timeout_policy=TimeoutPolicy(
                mode=TimeoutMode.PROGRESSIVE,
                initial_timeout=60.0,
                no_activity_timeout=3.0,
                activity_check_interval=0.5,
            ),
            termination_policy=TerminationPolicy(
                enabled=True,
                kill_on_no_activity=True,
            ),
        )

        start = time.time()
        result = await spawn(task, tool="bash", model="-c", policy=policy)
        elapsed = time.time() - start

        assert not result.success
        assert result.termination_reason is not None
        assert "no activity" in result.termination_reason.lower()
        assert elapsed < 10.0  # Much less than the 30s sleep


class TestRetryPolicyIntegration:
    """Integration tests for retry policies across multiple failure scenarios."""

    @pytest.mark.asyncio
    async def test_exponential_backoff_timing(self):
        """Test that exponential backoff delays are correctly calculated."""
        attempt_times = []

        async def track_timing_spawn(task, **kwargs):
            attempt_times.append(time.time())
            return SpawnResult(
                success=False,
                output="",
                error="Transient error",
                exit_code=1,
            )

        import aurora_spawner.spawner

        original_spawn = aurora_spawner.spawner.spawn
        aurora_spawner.spawner.spawn = track_timing_spawn

        try:
            task = SpawnTask(prompt="test", agent=None, timeout=60)
            policy = SpawnPolicy(
                name="backoff-test",
                retry_policy=RetryPolicy(
                    max_attempts=4,
                    strategy=RetryStrategy.EXPONENTIAL_BACKOFF,
                    base_delay=0.5,
                    backoff_factor=2.0,
                    jitter=False,
                ),
            )

            await spawn_with_retry_and_fallback(task, policy=policy, fallback_to_llm=False)

            # Verify attempt spacing: 0.5s, 1.0s, 2.0s
            assert len(attempt_times) == 4
            delay1 = attempt_times[1] - attempt_times[0]
            delay2 = attempt_times[2] - attempt_times[1]
            delay3 = attempt_times[3] - attempt_times[2]

            assert 0.4 < delay1 < 0.6  # ~0.5s
            assert 0.9 < delay2 < 1.1  # ~1.0s
            assert 1.8 < delay3 < 2.2  # ~2.0s

        finally:
            aurora_spawner.spawner.spawn = original_spawn

    @pytest.mark.asyncio
    async def test_retry_skips_on_timeout_when_disabled(self):
        """Test that retry policy respects retry_on_timeout=False."""
        attempt_count = 0

        async def timeout_spawn(task, **kwargs):
            nonlocal attempt_count
            attempt_count += 1
            return SpawnResult(
                success=False,
                output="",
                error="Timeout after 60s",
                exit_code=-1,
                termination_reason="Process timed out after 60 seconds",
            )

        import aurora_spawner.spawner

        original_spawn = aurora_spawner.spawner.spawn
        aurora_spawner.spawner.spawn = timeout_spawn

        try:
            task = SpawnTask(prompt="test", agent=None, timeout=60)
            policy = SpawnPolicy(
                name="no-retry-timeout",
                retry_policy=RetryPolicy(
                    max_attempts=5,
                    retry_on_timeout=False,
                    circuit_breaker_enabled=False,
                ),
            )

            result = await spawn_with_retry_and_fallback(task, policy=policy, fallback_to_llm=False)

            assert not result.success
            assert attempt_count == 1  # Initial attempt only, no retries

        finally:
            aurora_spawner.spawner.spawn = original_spawn

    @pytest.mark.asyncio
    async def test_retry_recovers_from_transient_failures(self):
        """Test that retry successfully recovers from transient failures."""
        attempt_count = 0

        async def flaky_spawn(task, **kwargs):
            nonlocal attempt_count
            attempt_count += 1
            if attempt_count <= 2:
                return SpawnResult(
                    success=False,
                    output="",
                    error=f"Transient error {attempt_count}",
                    exit_code=1,
                )
            return SpawnResult(
                success=True,
                output="Success after retries",
                error=None,
                exit_code=0,
            )

        import aurora_spawner.spawner

        original_spawn = aurora_spawner.spawner.spawn
        aurora_spawner.spawner.spawn = flaky_spawn

        try:
            task = SpawnTask(prompt="test", agent=None, timeout=60)
            policy = SpawnPolicy(
                name="recovery-test",
                retry_policy=RetryPolicy(
                    max_attempts=3,
                    strategy=RetryStrategy.IMMEDIATE,
                ),
            )

            result = await spawn_with_retry_and_fallback(task, policy=policy, fallback_to_llm=False)

            assert result.success
            assert "Success after retries" in result.output
            assert attempt_count == 3
            assert result.retry_count == 2

        finally:
            aurora_spawner.spawner.spawn = original_spawn


class TestTerminationPolicyIntegration:
    """Integration tests for early termination conditions."""

    @pytest.mark.asyncio
    async def test_error_pattern_immediate_termination(self):
        """Test that error patterns trigger immediate termination."""
        task = SpawnTask(
            prompt="echo 'Starting'; echo 'Rate limit exceeded' >&2; sleep 30",
            agent=None,
            timeout=60,
        )

        policy = SpawnPolicy(
            name="error-pattern-test",
            timeout_policy=TimeoutPolicy(
                mode=TimeoutMode.FIXED,
                timeout=60.0,
            ),
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
        assert elapsed < 5.0  # Much less than 30s sleep

    @pytest.mark.asyncio
    async def test_custom_predicate_termination(self):
        """Test that custom termination predicates work correctly."""

        def critical_error_predicate(stdout: str, stderr: str) -> bool:
            return "CRITICAL" in stderr or "FATAL" in stdout

        task = SpawnTask(
            prompt="echo 'Running'; echo 'CRITICAL: Database unavailable' >&2; sleep 30",
            agent=None,
            timeout=60,
        )

        policy = SpawnPolicy(
            name="custom-predicate-test",
            timeout_policy=TimeoutPolicy(
                mode=TimeoutMode.FIXED,
                timeout=60.0,
            ),
            termination_policy=TerminationPolicy(
                enabled=True,
                custom_predicates=[critical_error_predicate],
            ),
        )

        start = time.time()
        result = await spawn(task, tool="bash", model="-c", policy=policy)
        elapsed = time.time() - start

        assert not result.success
        assert result.termination_reason is not None
        assert "custom termination" in result.termination_reason.lower()
        assert elapsed < 5.0

    @pytest.mark.asyncio
    async def test_multiple_termination_conditions_first_wins(self):
        """Test that first matching termination condition triggers kill."""
        task = SpawnTask(
            prompt="echo '429 Too Many Requests' >&2; echo 'CRITICAL ERROR'; sleep 30",
            agent=None,
            timeout=60,
        )

        policy = SpawnPolicy(
            name="multi-condition-test",
            timeout_policy=TimeoutPolicy(timeout=60.0),
            termination_policy=TerminationPolicy(
                enabled=True,
                kill_on_error_patterns=True,
                error_patterns=[r"\b429\b", r"CRITICAL"],
            ),
        )

        start = time.time()
        result = await spawn(task, tool="bash", model="-c", policy=policy)
        elapsed = time.time() - start

        assert not result.success
        assert result.termination_reason is not None
        assert elapsed < 5.0


class TestCircuitBreakerIntegration:
    """Integration tests for circuit breaker behavior."""

    @pytest.mark.asyncio
    async def test_circuit_opens_after_threshold_failures(self):
        """Test that circuit opens after reaching failure threshold."""
        cb = CircuitBreaker(failure_threshold=2, reset_timeout=120)
        agent_id = "test-agent-fail"

        # First failure - circuit remains closed
        cb.record_failure(agent_id)
        skip1, _ = cb.should_skip(agent_id)
        assert not skip1

        # Second failure - circuit opens
        cb.record_failure(agent_id)
        skip2, reason2 = cb.should_skip(agent_id)
        assert skip2
        assert "Circuit open" in reason2
        assert "2 failures" in reason2

    @pytest.mark.asyncio
    async def test_circuit_transitions_to_half_open(self):
        """Test circuit transitions to half-open after timeout."""
        cb = CircuitBreaker(failure_threshold=2, reset_timeout=1.0)
        agent_id = "test-agent-recovery"

        # Open the circuit
        cb.record_failure(agent_id)
        cb.record_failure(agent_id)
        skip1, _ = cb.should_skip(agent_id)
        assert skip1

        # Wait for reset timeout
        await asyncio.sleep(1.1)

        # Should transition to half-open
        skip2, _ = cb.should_skip(agent_id)
        assert not skip2  # Allows test request

        circuit = cb._get_circuit(agent_id)
        assert circuit.state == CircuitState.HALF_OPEN

    @pytest.mark.asyncio
    async def test_circuit_closes_on_successful_recovery(self):
        """Test that circuit closes after successful recovery attempt."""
        cb = CircuitBreaker(failure_threshold=2, reset_timeout=1.0)
        agent_id = "test-agent-success"

        # Open the circuit
        cb.record_failure(agent_id)
        cb.record_failure(agent_id)

        # Wait and allow test request
        await asyncio.sleep(1.1)
        cb.should_skip(agent_id)  # Transition to half-open

        # Record success
        cb.record_success(agent_id)

        # Circuit should be closed
        skip, _ = cb.should_skip(agent_id)
        assert not skip

        circuit = cb._get_circuit(agent_id)
        assert circuit.state == CircuitState.CLOSED
        assert circuit.failure_count == 0

    @pytest.mark.asyncio
    async def test_circuit_reopens_on_failed_recovery(self):
        """Test that circuit reopens if recovery attempt fails."""
        cb = CircuitBreaker(failure_threshold=2, reset_timeout=1.0)
        agent_id = "test-agent-reopen"

        # Open the circuit
        cb.record_failure(agent_id)
        cb.record_failure(agent_id)

        # Wait and allow test request
        await asyncio.sleep(1.1)
        cb.should_skip(agent_id)  # Transition to half-open

        # Record another failure
        cb.record_failure(agent_id)

        # Circuit should be open again
        skip, reason = cb.should_skip(agent_id)
        assert skip
        assert "Circuit open" in reason

        circuit = cb._get_circuit(agent_id)
        assert circuit.state == CircuitState.OPEN


class TestPolicyPresetIntegration:
    """Integration tests for policy preset configurations."""

    @pytest.mark.asyncio
    async def test_production_policy_is_patient(self):
        """Test that production preset uses patient timeout and retry settings."""
        policy = SpawnPolicy.production()

        assert policy.timeout_policy.mode == TimeoutMode.PROGRESSIVE
        assert policy.timeout_policy.initial_timeout == 120.0
        assert policy.timeout_policy.max_timeout == 600.0
        assert policy.retry_policy.max_attempts == 3
        assert policy.retry_policy.strategy == RetryStrategy.EXPONENTIAL_BACKOFF
        assert not policy.termination_policy.kill_on_no_activity  # Patient on idle

    @pytest.mark.asyncio
    async def test_fast_fail_policy_is_aggressive(self):
        """Test that fast_fail preset uses aggressive settings."""
        policy = SpawnPolicy.fast_fail()

        assert policy.timeout_policy.mode == TimeoutMode.FIXED
        assert policy.timeout_policy.timeout == 60.0
        assert policy.retry_policy.max_attempts == 1  # No retries
        assert policy.retry_policy.strategy == RetryStrategy.IMMEDIATE
        assert not policy.retry_policy.retry_on_timeout
        assert policy.termination_policy.kill_on_error_patterns
        assert policy.termination_policy.kill_on_no_activity

    @pytest.mark.asyncio
    async def test_development_policy_is_patient(self):
        """Test that development preset allows long debugging sessions."""
        policy = SpawnPolicy.development()

        assert policy.timeout_policy.mode == TimeoutMode.FIXED
        assert policy.timeout_policy.timeout == 1800.0  # 30 minutes
        assert policy.retry_policy.max_attempts == 1
        assert not policy.retry_policy.circuit_breaker_enabled
        assert not policy.termination_policy.enabled  # Observe failures


class TestSpawnerSOARIntegration:
    """Integration tests for spawner interaction with SOAR orchestrator."""

    @pytest.mark.asyncio
    async def test_circuit_breaker_skips_failing_agent(self):
        """Test that spawner skips agents with open circuits."""
        attempt_count = 0

        async def always_failing_spawn(task, **kwargs):
            nonlocal attempt_count
            attempt_count += 1
            return SpawnResult(
                success=False,
                output="",
                error="Agent consistently failing",
                exit_code=1,
            )

        import aurora_spawner.spawner

        original_spawn = aurora_spawner.spawner.spawn
        aurora_spawner.spawner.spawn = always_failing_spawn

        try:
            task = SpawnTask(prompt="test", agent="failing-agent", timeout=60)
            policy = SpawnPolicy(
                name="circuit-test",
                retry_policy=RetryPolicy(
                    max_attempts=3,
                    strategy=RetryStrategy.IMMEDIATE,
                    circuit_breaker_enabled=True,
                ),
            )

            # First execution - should fail after 3 attempts
            result1 = await spawn_with_retry_and_fallback(
                task,
                policy=policy,
                fallback_to_llm=False,
            )
            assert not result1.success
            assert attempt_count == 3

            # Second execution - should skip immediately
            attempt_count = 0
            result2 = await spawn_with_retry_and_fallback(
                task,
                policy=policy,
                fallback_to_llm=False,
            )
            assert not result2.success
            assert attempt_count == 0  # Skipped due to circuit breaker

        finally:
            aurora_spawner.spawner.spawn = original_spawn

    @pytest.mark.asyncio
    async def test_recovery_metrics_tracked(self):
        """Test that recovery metrics are properly tracked."""
        attempt_count = 0

        async def flaky_spawn(task, **kwargs):
            nonlocal attempt_count
            attempt_count += 1
            if attempt_count == 1:
                return SpawnResult(
                    success=False,
                    output="",
                    error="Timeout",
                    exit_code=-1,
                    termination_reason="Process timed out",
                )
            return SpawnResult(
                success=True,
                output="Success",
                error=None,
                exit_code=0,
            )

        import aurora_spawner.spawner

        original_spawn = aurora_spawner.spawner.spawn
        aurora_spawner.spawner.spawn = flaky_spawn

        try:
            task = SpawnTask(prompt="test", agent="flaky-agent", timeout=60)
            policy = SpawnPolicy.default()

            result = await spawn_with_retry_and_fallback(task, policy=policy, fallback_to_llm=False)

            assert result.success
            assert result.retry_count == 1
            assert attempt_count == 2

        finally:
            aurora_spawner.spawner.spawn = original_spawn


class TestEndToEndFailureRecovery:
    """End-to-end integration tests for complete failure recovery scenarios."""

    @pytest.mark.asyncio
    async def test_early_failure_triggers_fallback(self):
        """Test that early failure detection triggers fallback mechanisms."""

        async def failing_agent_spawn(task, **kwargs):
            return SpawnResult(
                success=False,
                output="",
                error="Rate limit exceeded",
                exit_code=1,
                termination_reason="Error pattern detected: rate.?limit",
            )

        async def llm_fallback_spawn(task, **kwargs):
            # Simulate LLM fallback
            if task.agent is None:
                return SpawnResult(
                    success=True,
                    output="Fallback LLM response",
                    error=None,
                    exit_code=0,
                )
            return await failing_agent_spawn(task, **kwargs)

        import aurora_spawner.spawner

        original_spawn = aurora_spawner.spawner.spawn
        aurora_spawner.spawner.spawn = llm_fallback_spawn

        try:
            task = SpawnTask(prompt="test query", agent="rate-limited-agent", timeout=60)
            policy = SpawnPolicy.production()

            result = await spawn_with_retry_and_fallback(
                task,
                policy=policy,
                fallback_to_llm=True,
                max_retries=1,
            )

            # Should fall back to LLM after agent failure
            assert result.success
            assert "Fallback LLM response" in result.output

        finally:
            aurora_spawner.spawner.spawn = original_spawn

    @pytest.mark.asyncio
    async def test_multiple_agents_with_circuit_breaker_coordination(self):
        """Test coordinated circuit breaker behavior across multiple agents."""
        cb = CircuitBreaker(failure_threshold=2, reset_timeout=1.0)
        execution_log = []

        async def multi_agent_spawn(task, **kwargs):
            execution_log.append((task.agent, time.time()))

            if task.agent == "agent-1":
                return SpawnResult(success=False, output="", error="Failure", exit_code=1)
            if task.agent == "agent-2":
                return SpawnResult(success=True, output="Success", error=None, exit_code=0)
            return SpawnResult(success=False, output="", error="Unknown agent", exit_code=1)

        import aurora_spawner.spawner

        original_spawn = aurora_spawner.spawner.spawn
        aurora_spawner.spawner.spawn = multi_agent_spawn

        try:
            policy = SpawnPolicy(
                name="multi-agent-test",
                retry_policy=RetryPolicy(max_attempts=3, circuit_breaker_enabled=True),
            )

            # Execute agent-1 twice to open circuit
            task1 = SpawnTask(prompt="test", agent="agent-1", timeout=60)
            await spawn_with_retry_and_fallback(task1, policy=policy, fallback_to_llm=False)
            await spawn_with_retry_and_fallback(task1, policy=policy, fallback_to_llm=False)

            # Circuit should be open for agent-1
            assert cb.is_open("agent-1")

            # Execute agent-2 - should work normally
            execution_log.clear()
            task2 = SpawnTask(prompt="test", agent="agent-2", timeout=60)
            result2 = await spawn_with_retry_and_fallback(
                task2,
                policy=policy,
                fallback_to_llm=False,
            )
            assert result2.success
            assert len(execution_log) == 1  # Only one attempt needed

        finally:
            aurora_spawner.spawner.spawn = original_spawn
