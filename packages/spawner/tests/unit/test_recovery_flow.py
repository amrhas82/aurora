"""Unit tests for agent recovery flow.

Tests RecoveryResult, RecoverySummary, RecoveryPolicy presets, and the complete
recovery flow covering success, retry, and permanent failure scenarios.
"""

from unittest.mock import patch

import pytest

from aurora_spawner import SpawnResult, SpawnTask
from aurora_spawner.circuit_breaker import CircuitBreaker
from aurora_spawner.recovery import (
    ErrorCategory,
    RecoveryPolicy,
    RecoveryResult,
    RecoveryStrategy,
    RecoverySummary,
    get_recovery_metrics,
    reset_recovery_metrics,
)
from aurora_spawner.spawner import spawn_parallel_with_recovery, spawn_with_retry_and_fallback


# =============================================================================
# RECOVERY RESULT TESTS
# =============================================================================


class TestRecoveryResult:
    """Test RecoveryResult dataclass."""

    def test_recovery_result_success_first_try(self):
        """Create result for success on first attempt."""
        result = RecoveryResult(
            task_index=0,
            agent_id="test-agent",
            success=True,
            attempts=1,
            used_fallback=False,
        )

        assert result.task_index == 0
        assert result.agent_id == "test-agent"
        assert result.success is True
        assert result.attempts == 1
        assert result.used_fallback is False
        assert result.final_error is None
        assert result.recovery_path == []

    def test_recovery_result_success_after_retries(self):
        """Create result for success after retries."""
        result = RecoveryResult(
            task_index=1,
            agent_id="flaky-agent",
            success=True,
            attempts=3,
            used_fallback=False,
            recovery_path=["retry:1", "retry:2"],
        )

        assert result.attempts == 3
        assert result.recovery_path == ["retry:1", "retry:2"]
        assert result.success is True

    def test_recovery_result_success_via_fallback(self):
        """Create result for success via fallback."""
        result = RecoveryResult(
            task_index=2,
            agent_id="failing-agent",
            success=True,
            attempts=4,
            used_fallback=True,
            recovery_path=["retry:1", "retry:2", "fallback"],
        )

        assert result.used_fallback is True
        assert "fallback" in result.recovery_path

    def test_recovery_result_permanent_failure(self):
        """Create result for permanent failure."""
        result = RecoveryResult(
            task_index=3,
            agent_id="doomed-agent",
            success=False,
            attempts=4,
            used_fallback=True,
            final_error="Both agent and fallback failed",
            recovery_path=["retry:1", "retry:2", "fallback"],
        )

        assert result.success is False
        assert result.final_error == "Both agent and fallback failed"
        assert result.used_fallback is True

    def test_recovery_result_to_dict(self):
        """Test conversion to dictionary."""
        result = RecoveryResult(
            task_index=0,
            agent_id="test-agent",
            success=True,
            attempts=2,
            used_fallback=False,
            recovery_path=["retry:1"],
        )

        data = result.to_dict()

        assert data["task_index"] == 0
        assert data["agent_id"] == "test-agent"
        assert data["success"] is True
        assert data["attempts"] == 2
        assert data["used_fallback"] is False
        assert data["final_error"] is None
        assert data["recovery_path"] == ["retry:1"]


# =============================================================================
# RECOVERY SUMMARY TESTS
# =============================================================================


class TestRecoverySummary:
    """Test RecoverySummary dataclass."""

    def test_summary_all_success_first_try(self):
        """Summary when all tasks succeed on first try."""
        summary = RecoverySummary(
            total_tasks=5,
            succeeded=5,
            failed=0,
            recovered=0,
            used_fallback=0,
            total_retry_attempts=0,
        )

        assert summary.success_rate == 100.0
        assert summary.recovery_rate == 100.0  # All succeeded first try

    def test_summary_partial_success(self):
        """Summary with partial success and recovery."""
        summary = RecoverySummary(
            total_tasks=10,
            succeeded=8,
            failed=2,
            recovered=3,  # 3 tasks recovered after initial failure
            used_fallback=2,
            total_retry_attempts=10,
        )

        assert summary.success_rate == 80.0
        # Recovery rate: 3 recovered / (3 recovered + 2 failed) = 60%
        assert summary.recovery_rate == 60.0

    def test_summary_all_failed(self):
        """Summary when all tasks fail."""
        summary = RecoverySummary(
            total_tasks=5,
            succeeded=0,
            failed=5,
            recovered=0,
            used_fallback=5,
            total_retry_attempts=15,
        )

        assert summary.success_rate == 0.0
        assert summary.recovery_rate == 0.0

    def test_summary_zero_tasks(self):
        """Summary with zero tasks."""
        summary = RecoverySummary(
            total_tasks=0,
            succeeded=0,
            failed=0,
            recovered=0,
            used_fallback=0,
            total_retry_attempts=0,
        )

        assert summary.success_rate == 0.0
        assert summary.recovery_rate == 100.0  # No tasks needing recovery

    def test_summary_with_results(self):
        """Summary with detailed results."""
        results = [
            RecoveryResult(
                task_index=0,
                agent_id="a",
                success=True,
                attempts=1,
                used_fallback=False,
            ),
            RecoveryResult(
                task_index=1,
                agent_id="a",
                success=True,
                attempts=3,
                used_fallback=False,
                recovery_path=["retry:1", "retry:2"],
            ),
            RecoveryResult(
                task_index=2,
                agent_id="a",
                success=False,
                attempts=4,
                used_fallback=True,
                final_error="Failed",
            ),
        ]

        summary = RecoverySummary(
            total_tasks=3,
            succeeded=2,
            failed=1,
            recovered=1,
            used_fallback=1,
            total_retry_attempts=5,
            results=results,
        )

        assert len(summary.results) == 3
        assert summary.success_rate == pytest.approx(66.67, rel=0.01)

    def test_summary_to_dict(self):
        """Test conversion to dictionary."""
        results = [
            RecoveryResult(
                task_index=0,
                agent_id="a",
                success=True,
                attempts=1,
                used_fallback=False,
            ),
        ]

        summary = RecoverySummary(
            total_tasks=1,
            succeeded=1,
            failed=0,
            recovered=0,
            used_fallback=0,
            total_retry_attempts=0,
            results=results,
        )

        data = summary.to_dict()

        assert data["total_tasks"] == 1
        assert data["succeeded"] == 1
        assert data["success_rate"] == 100.0
        assert len(data["results"]) == 1


# =============================================================================
# RECOVERY POLICY PRESET TESTS
# =============================================================================


class TestRecoveryPolicyPresets:
    """Test RecoveryPolicy preset factory methods."""

    def test_default_preset(self):
        """Test default recovery policy."""
        policy = RecoveryPolicy.default()

        assert policy.strategy == RecoveryStrategy.RETRY_THEN_FALLBACK
        assert policy.max_retries == 2
        assert policy.fallback_to_llm is True
        assert policy.base_delay == 1.0
        assert policy.jitter is True

    def test_aggressive_retry_preset(self):
        """Test aggressive retry policy."""
        policy = RecoveryPolicy.aggressive_retry()

        assert policy.strategy == RecoveryStrategy.RETRY_SAME
        assert policy.max_retries == 5
        assert policy.fallback_to_llm is False
        assert policy.base_delay == 0.5

    def test_fast_fallback_preset(self):
        """Test fast fallback policy."""
        policy = RecoveryPolicy.fast_fallback()

        assert policy.strategy == RecoveryStrategy.FALLBACK_ONLY
        assert policy.max_retries == 0
        assert policy.fallback_to_llm is True

    def test_no_recovery_preset(self):
        """Test no recovery policy."""
        policy = RecoveryPolicy.no_recovery()

        assert policy.strategy == RecoveryStrategy.NO_RECOVERY
        assert policy.max_retries == 0
        assert policy.fallback_to_llm is False

    def test_patient_preset(self):
        """Test patient recovery policy."""
        policy = RecoveryPolicy.patient()

        assert policy.strategy == RecoveryStrategy.RETRY_THEN_FALLBACK
        assert policy.max_retries == 3
        assert policy.base_delay == 2.0
        assert policy.max_delay == 120.0
        assert policy.backoff_factor == 3.0

    def test_from_name_all_presets(self):
        """Test from_name for all preset names."""
        presets = ["default", "aggressive_retry", "fast_fallback", "no_recovery", "patient"]

        for name in presets:
            policy = RecoveryPolicy.from_name(name)
            assert policy is not None

    def test_from_name_invalid(self):
        """Test from_name with invalid preset."""
        with pytest.raises(ValueError, match="Unknown recovery preset"):
            RecoveryPolicy.from_name("nonexistent")


# =============================================================================
# RECOVERY POLICY DELAY CALCULATION TESTS
# =============================================================================


class TestRecoveryPolicyDelay:
    """Test delay calculation with backoff."""

    def test_exponential_backoff_no_jitter(self):
        """Test exponential backoff calculation."""
        policy = RecoveryPolicy(
            base_delay=1.0,
            backoff_factor=2.0,
            max_delay=30.0,
            jitter=False,
        )

        assert policy.get_delay(0) == 1.0  # 1 * 2^0
        assert policy.get_delay(1) == 2.0  # 1 * 2^1
        assert policy.get_delay(2) == 4.0  # 1 * 2^2
        assert policy.get_delay(3) == 8.0  # 1 * 2^3

    def test_delay_capped_at_max(self):
        """Test delay doesn't exceed max_delay."""
        policy = RecoveryPolicy(
            base_delay=10.0,
            backoff_factor=2.0,
            max_delay=20.0,
            jitter=False,
        )

        assert policy.get_delay(0) == 10.0
        assert policy.get_delay(1) == 20.0  # Capped
        assert policy.get_delay(5) == 20.0  # Still capped

    def test_jitter_adds_variation(self):
        """Test jitter adds randomness to delay."""
        policy = RecoveryPolicy(
            base_delay=10.0,
            backoff_factor=1.0,
            jitter=True,
        )

        delays = [policy.get_delay(0) for _ in range(20)]

        # All delays should be within +/- 10% of base
        assert all(9.0 <= d <= 11.0 for d in delays)
        # Should have some variation
        assert len(set(delays)) > 1


# =============================================================================
# RECOVERY POLICY AGENT OVERRIDES TESTS
# =============================================================================


class TestRecoveryPolicyOverrides:
    """Test per-agent policy overrides."""

    def test_get_for_agent_default(self):
        """Test get_for_agent returns self when no override."""
        policy = RecoveryPolicy(max_retries=2)

        result = policy.get_for_agent("any-agent")

        assert result is policy

    def test_get_for_agent_with_override(self):
        """Test get_for_agent returns override when present."""
        policy = RecoveryPolicy(max_retries=2)
        policy = policy.with_override("slow-agent", max_retries=5)

        default_policy = policy.get_for_agent("fast-agent")
        override_policy = policy.get_for_agent("slow-agent")

        assert default_policy.max_retries == 2
        assert override_policy.max_retries == 5

    def test_with_override_creates_new_policy(self):
        """Test with_override creates new policy instance."""
        original = RecoveryPolicy(max_retries=2)
        modified = original.with_override("agent", max_retries=5)

        assert original is not modified
        assert original.max_retries == 2
        assert "agent" not in original.agent_overrides


# =============================================================================
# RECOVERY FLOW INTEGRATION TESTS
# =============================================================================


class TestRecoveryFlowSuccess:
    """Test successful recovery flows."""

    @pytest.mark.asyncio
    async def test_success_first_attempt(self):
        """Task succeeds on first attempt - no recovery needed."""

        async def mock_spawn(task, **kwargs):
            return SpawnResult(
                success=True,
                output="Immediate success",
                error=None,
                exit_code=0,
            )

        task = SpawnTask(prompt="Simple task", agent="fast-agent", timeout=10)

        with patch("aurora_spawner.spawner.spawn", side_effect=mock_spawn):
            with patch("aurora_spawner.circuit_breaker.get_circuit_breaker") as mock_cb:
                cb = CircuitBreaker(failure_threshold=5)
                mock_cb.return_value = cb

                result = await spawn_with_retry_and_fallback(
                    task,
                    max_retries=3,
                    fallback_to_llm=True,
                )

                assert result.success
                assert result.retry_count == 0
                assert result.fallback is False

    @pytest.mark.asyncio
    async def test_success_after_single_retry(self):
        """Task succeeds on second attempt."""
        attempt_count = 0

        async def mock_spawn(task, **kwargs):
            nonlocal attempt_count
            attempt_count += 1

            if attempt_count == 1:
                return SpawnResult(
                    success=False,
                    output="",
                    error="Transient error",
                    exit_code=-1,
                )

            return SpawnResult(
                success=True,
                output="Success after retry",
                error=None,
                exit_code=0,
            )

        task = SpawnTask(prompt="Flaky task", agent="flaky-agent", timeout=10)

        with patch("aurora_spawner.spawner.spawn", side_effect=mock_spawn):
            with patch("aurora_spawner.circuit_breaker.get_circuit_breaker") as mock_cb:
                cb = CircuitBreaker(failure_threshold=10, fast_fail_threshold=10)
                mock_cb.return_value = cb

                result = await spawn_with_retry_and_fallback(
                    task,
                    max_retries=3,
                    fallback_to_llm=True,
                )

                assert result.success
                assert result.retry_count == 1
                assert result.fallback is False
                assert attempt_count == 2


class TestRecoveryFlowRetry:
    """Test retry recovery flows."""

    @pytest.mark.asyncio
    async def test_multiple_retries_then_success(self):
        """Task succeeds after multiple retries."""
        attempt_count = 0

        async def mock_spawn(task, **kwargs):
            nonlocal attempt_count
            attempt_count += 1

            if attempt_count < 4:
                return SpawnResult(
                    success=False,
                    output="",
                    error=f"Attempt {attempt_count} failed",
                    exit_code=-1,
                )

            return SpawnResult(
                success=True,
                output="Finally succeeded",
                error=None,
                exit_code=0,
            )

        task = SpawnTask(prompt="Persistent task", agent="unstable-agent", timeout=10)

        with patch("aurora_spawner.spawner.spawn", side_effect=mock_spawn):
            with patch("aurora_spawner.circuit_breaker.get_circuit_breaker") as mock_cb:
                cb = CircuitBreaker(failure_threshold=20, fast_fail_threshold=20)
                mock_cb.return_value = cb

                result = await spawn_with_retry_and_fallback(
                    task,
                    max_retries=5,
                    fallback_to_llm=False,
                )

                assert result.success
                assert result.retry_count == 3
                assert attempt_count == 4

    @pytest.mark.asyncio
    async def test_exhausted_retries_fallback_success(self):
        """Retries exhausted but fallback succeeds."""
        call_sequence = []

        async def mock_spawn(task, **kwargs):
            call_sequence.append(task.agent)

            if task.agent == "failing-agent":
                return SpawnResult(
                    success=False,
                    output="",
                    error="Agent failed",
                    exit_code=-1,
                )

            # Fallback (agent=None) succeeds
            return SpawnResult(
                success=True,
                output="Fallback success",
                error=None,
                exit_code=0,
            )

        task = SpawnTask(prompt="Recovery task", agent="failing-agent", timeout=10)

        with patch("aurora_spawner.spawner.spawn", side_effect=mock_spawn):
            with patch("aurora_spawner.circuit_breaker.get_circuit_breaker") as mock_cb:
                cb = CircuitBreaker(failure_threshold=20, fast_fail_threshold=20)
                mock_cb.return_value = cb

                result = await spawn_with_retry_and_fallback(
                    task,
                    max_retries=2,
                    fallback_to_llm=True,
                )

                assert result.success
                assert result.fallback is True
                assert result.original_agent == "failing-agent"

                # Verify call sequence: 3 agent attempts + 1 fallback
                agent_calls = [c for c in call_sequence if c == "failing-agent"]
                fallback_calls = [c for c in call_sequence if c is None]
                assert len(agent_calls) == 3
                assert len(fallback_calls) == 1


class TestRecoveryFlowPermanentFailure:
    """Test permanent failure scenarios."""

    @pytest.mark.asyncio
    async def test_all_attempts_fail_no_fallback(self):
        """All retry attempts fail, no fallback enabled."""
        attempt_count = 0

        async def mock_spawn(task, **kwargs):
            nonlocal attempt_count
            attempt_count += 1
            return SpawnResult(
                success=False,
                output="",
                error=f"Permanent failure {attempt_count}",
                exit_code=-1,
            )

        task = SpawnTask(prompt="Doomed task", agent="broken-agent", timeout=10)

        with patch("aurora_spawner.spawner.spawn", side_effect=mock_spawn):
            with patch("aurora_spawner.circuit_breaker.get_circuit_breaker") as mock_cb:
                cb = CircuitBreaker(failure_threshold=20, fast_fail_threshold=20)
                mock_cb.return_value = cb

                result = await spawn_with_retry_and_fallback(
                    task,
                    max_retries=3,
                    fallback_to_llm=False,
                )

                assert result.success is False
                assert result.fallback is False
                assert attempt_count == 4  # 1 initial + 3 retries

    @pytest.mark.asyncio
    async def test_agent_and_fallback_both_fail(self):
        """Both agent retries and fallback fail."""

        async def mock_spawn(task, **kwargs):
            return SpawnResult(
                success=False,
                output="",
                error="Everything broken",
                exit_code=-1,
            )

        task = SpawnTask(prompt="Total failure", agent="bad-agent", timeout=10)

        with patch("aurora_spawner.spawner.spawn", side_effect=mock_spawn):
            with patch("aurora_spawner.circuit_breaker.get_circuit_breaker") as mock_cb:
                cb = CircuitBreaker(failure_threshold=20, fast_fail_threshold=20)
                mock_cb.return_value = cb

                result = await spawn_with_retry_and_fallback(
                    task,
                    max_retries=2,
                    fallback_to_llm=True,
                )

                assert result.success is False
                assert result.fallback is True
                assert "broken" in result.error.lower()

    @pytest.mark.asyncio
    async def test_circuit_breaker_blocks_immediately(self):
        """Circuit breaker open prevents any attempts."""
        spawn_called = False

        async def mock_spawn(task, **kwargs):
            nonlocal spawn_called
            spawn_called = True
            return SpawnResult(success=True, output="", error=None, exit_code=0)

        cb = CircuitBreaker(failure_threshold=2)
        # Pre-open circuit
        cb.record_failure("blocked-agent")
        cb.record_failure("blocked-agent")
        assert cb.is_open("blocked-agent")

        task = SpawnTask(prompt="Blocked task", agent="blocked-agent", timeout=10)

        with patch("aurora_spawner.spawner.spawn", side_effect=mock_spawn):
            with patch("aurora_spawner.circuit_breaker.get_circuit_breaker", return_value=cb):
                result = await spawn_with_retry_and_fallback(
                    task,
                    max_retries=5,
                    fallback_to_llm=False,
                )

                assert result.success is False
                assert "Circuit" in result.error or "retry in" in result.error


# =============================================================================
# PARALLEL RECOVERY FLOW TESTS
# =============================================================================


class TestParallelRecoveryFlow:
    """Test recovery across parallel task execution."""

    @pytest.mark.asyncio
    async def test_parallel_mixed_outcomes(self):
        """Parallel tasks with different recovery outcomes."""
        call_counts = {}

        async def mock_spawn(task, **kwargs):
            key = f"{task.agent or 'llm'}:{task.prompt}"
            call_counts[key] = call_counts.get(key, 0) + 1

            idx = int(task.prompt.split()[-1])

            # Task 0: Immediate success
            if idx == 0:
                return SpawnResult(success=True, output="quick", error=None, exit_code=0)

            # Task 1: Retry success
            if idx == 1 and task.agent:
                if call_counts[key] < 2:
                    return SpawnResult(success=False, output="", error="retry", exit_code=-1)
                return SpawnResult(success=True, output="recovered", error=None, exit_code=0)

            # Task 2: Fallback success
            if idx == 2:
                if task.agent:
                    return SpawnResult(
                        success=False,
                        output="",
                        error="need fallback",
                        exit_code=-1,
                    )
                return SpawnResult(success=True, output="fallback worked", error=None, exit_code=0)

            return SpawnResult(success=True, output="default", error=None, exit_code=0)

        tasks = [SpawnTask(prompt=f"Task {i}", agent="test-agent", timeout=10) for i in range(3)]

        with patch("aurora_spawner.spawner.spawn", side_effect=mock_spawn):
            with patch("aurora_spawner.circuit_breaker.get_circuit_breaker") as mock_cb:
                cb = CircuitBreaker(failure_threshold=20, fast_fail_threshold=20)
                mock_cb.return_value = cb

                results = await spawn_parallel_with_recovery(
                    tasks,
                    max_concurrent=3,
                    max_retries=2,
                    fallback_to_llm=True,
                )

                assert all(r.success for r in results)

                # Task 0: No retries
                assert results[0].retry_count == 0
                assert results[0].fallback is False

                # Task 1: Retried
                assert results[1].retry_count > 0
                assert results[1].fallback is False

                # Task 2: Used fallback
                assert results[2].fallback is True

    @pytest.mark.asyncio
    async def test_parallel_recovery_callbacks(self):
        """Recovery callbacks invoked correctly."""
        recovery_events = []
        progress_events = []

        def on_recovery(idx, agent_id, retry_count, used_fallback):
            recovery_events.append(
                {
                    "idx": idx,
                    "agent_id": agent_id,
                    "retries": retry_count,
                    "fallback": used_fallback,
                },
            )

        def on_progress(idx, total, agent_id, status):
            progress_events.append(
                {
                    "idx": idx,
                    "total": total,
                    "agent": agent_id,
                    "status": status,
                },
            )

        attempt_count = 0

        async def mock_spawn(task, **kwargs):
            nonlocal attempt_count
            attempt_count += 1

            if attempt_count == 1:
                return SpawnResult(success=False, output="", error="retry", exit_code=-1)

            return SpawnResult(success=True, output="ok", error=None, exit_code=0)

        tasks = [SpawnTask(prompt="Task 0", agent="flaky", timeout=10)]

        with patch("aurora_spawner.spawner.spawn", side_effect=mock_spawn):
            with patch("aurora_spawner.circuit_breaker.get_circuit_breaker") as mock_cb:
                cb = CircuitBreaker(failure_threshold=10, fast_fail_threshold=10)
                mock_cb.return_value = cb

                await spawn_parallel_with_recovery(
                    tasks,
                    max_retries=2,
                    on_recovery=on_recovery,
                    on_progress=on_progress,
                )

                # Recovery callback should have been called
                assert len(recovery_events) == 1
                assert recovery_events[0]["retries"] > 0

                # Progress callbacks should exist
                assert len(progress_events) >= 2


# =============================================================================
# ERROR CLASSIFICATION IN RECOVERY TESTS
# =============================================================================


class TestRecoveryErrorClassification:
    """Test error classification affects retry decisions."""

    @pytest.mark.asyncio
    async def test_transient_error_triggers_retry(self):
        """Transient errors should trigger retries."""
        attempt_count = 0

        async def mock_spawn(task, **kwargs):
            nonlocal attempt_count
            attempt_count += 1

            if attempt_count == 1:
                return SpawnResult(
                    success=False,
                    output="",
                    error="Rate limit exceeded - 429",
                    exit_code=-1,
                )

            return SpawnResult(success=True, output="ok", error=None, exit_code=0)

        task = SpawnTask(prompt="Test", agent="agent", timeout=10)

        with patch("aurora_spawner.spawner.spawn", side_effect=mock_spawn):
            with patch("aurora_spawner.circuit_breaker.get_circuit_breaker") as mock_cb:
                cb = CircuitBreaker(failure_threshold=10)
                mock_cb.return_value = cb

                result = await spawn_with_retry_and_fallback(
                    task,
                    max_retries=2,
                    fallback_to_llm=False,
                )

                assert result.success
                assert attempt_count == 2

    def test_permanent_error_no_retry_recommendation(self):
        """Permanent errors should not recommend retry."""
        policy = RecoveryPolicy.default()

        # Auth errors are permanent
        assert policy.should_retry_error("Invalid API key") is False
        assert policy.should_retry_error("401 Unauthorized") is False
        assert policy.should_retry_error("Permission denied") is False

    def test_transient_error_retry_recommendation(self):
        """Transient errors should recommend retry."""
        policy = RecoveryPolicy.default()

        assert policy.should_retry_error("Rate limit exceeded") is True
        assert policy.should_retry_error("Connection reset") is True
        assert policy.should_retry_error("503 Service unavailable") is True


# =============================================================================
# RECOVERY METRICS TRACKING TESTS
# =============================================================================


class TestRecoveryMetricsIntegration:
    """Test recovery metrics tracking during flow execution."""

    def setup_method(self):
        """Reset global metrics before each test."""
        reset_recovery_metrics()

    def test_metrics_track_success(self):
        """Metrics track successful attempts."""
        metrics = get_recovery_metrics()

        metrics.record_attempt("agent-1", success=True)
        metrics.record_attempt("agent-1", success=True)
        metrics.record_attempt("agent-1", success=False)

        assert metrics.success_rate("agent-1") == pytest.approx(66.67, rel=0.01)

    def test_metrics_track_recovery_time(self):
        """Metrics track recovery time."""
        metrics = get_recovery_metrics()

        metrics.record_attempt("agent-1", success=True, recovery_time=1.5)
        metrics.record_attempt("agent-1", success=True, recovery_time=2.5)

        assert metrics.avg_recovery_time("agent-1") == 2.0

    def test_metrics_track_fallback(self):
        """Metrics track fallback usage."""
        metrics = get_recovery_metrics()

        metrics.record_attempt("agent-1", success=True, used_fallback=True)
        metrics.record_attempt("agent-1", success=True, used_fallback=False)
        metrics.record_attempt("agent-1", success=True, used_fallback=True)

        assert metrics._fallbacks.get("agent-1") == 2

    def test_metrics_track_error_categories(self):
        """Metrics track error categories."""
        metrics = get_recovery_metrics()

        metrics.record_attempt(
            "agent-1",
            success=False,
            error_category=ErrorCategory.TRANSIENT,
        )
        metrics.record_attempt(
            "agent-1",
            success=False,
            error_category=ErrorCategory.PERMANENT,
        )
        metrics.record_attempt(
            "agent-1",
            success=False,
            error_category=ErrorCategory.TRANSIENT,
        )

        assert metrics._errors_by_category["agent-1"][ErrorCategory.TRANSIENT] == 2
        assert metrics._errors_by_category["agent-1"][ErrorCategory.PERMANENT] == 1

    def test_metrics_overall_stats(self):
        """Metrics calculate overall statistics."""
        metrics = get_recovery_metrics()

        # Multiple agents
        metrics.record_attempt("agent-1", success=True, retries=1)
        metrics.record_attempt("agent-1", success=True, retries=0)
        metrics.record_attempt("agent-2", success=False, retries=2)
        metrics.record_attempt("agent-2", success=True, retries=1, used_fallback=True)

        data = metrics.to_dict()

        assert data["total_attempts"] == 4
        assert data["total_successes"] == 3
        assert data["total_failures"] == 1
        assert data["total_retries"] == 4
        assert data["total_fallbacks"] == 1
        assert data["overall_success_rate"] == 75.0


# =============================================================================
# RECOVERY POLICY FROM CONFIG TESTS
# =============================================================================


class TestRecoveryPolicyFromConfig:
    """Test loading recovery policy from configuration."""

    def test_from_config_empty(self):
        """Empty config returns default policy."""
        config = {}
        policy = RecoveryPolicy.from_config(config)

        assert policy.max_retries == RecoveryPolicy.default().max_retries

    def test_from_config_basic(self):
        """Load basic config values."""
        config = {
            "spawner": {
                "recovery": {
                    "max_retries": 5,
                    "fallback_to_llm": False,
                    "base_delay": 2.0,
                },
            },
        }

        policy = RecoveryPolicy.from_config(config)

        assert policy.max_retries == 5
        assert policy.fallback_to_llm is False
        assert policy.base_delay == 2.0

    def test_from_config_with_preset(self):
        """Load config with preset name."""
        config = {"spawner": {"recovery": {"preset": "patient"}}}

        policy = RecoveryPolicy.from_config(config)

        assert policy.max_retries == 3
        assert policy.base_delay == 2.0

    def test_from_config_preset_with_overrides(self):
        """Preset values can be overridden."""
        config = {
            "spawner": {
                "recovery": {
                    "preset": "patient",
                    "max_retries": 10,
                },
            },
        }

        policy = RecoveryPolicy.from_config(config)

        assert policy.max_retries == 10
        assert policy.base_delay == 2.0  # From patient preset

    def test_from_config_agent_overrides(self):
        """Config can include per-agent overrides."""
        config = {
            "spawner": {
                "recovery": {
                    "max_retries": 2,
                    "agent_overrides": {
                        "slow-agent": {
                            "max_retries": 5,
                            "base_delay": 5.0,
                        },
                    },
                },
            },
        }

        policy = RecoveryPolicy.from_config(config)

        assert policy.max_retries == 2
        assert policy.get_for_agent("slow-agent").max_retries == 5
        assert policy.get_for_agent("fast-agent").max_retries == 2


# =============================================================================
# RECOVERY STATE MACHINE TESTS
# =============================================================================


class TestRecoveryState:
    """Test RecoveryState enum."""

    def test_all_states_defined(self):
        """All expected states are defined."""
        from aurora_spawner.recovery import RecoveryState

        states = [
            RecoveryState.INITIAL,
            RecoveryState.EXECUTING,
            RecoveryState.RETRY_PENDING,
            RecoveryState.RETRYING,
            RecoveryState.FALLBACK_PENDING,
            RecoveryState.FALLBACK_EXECUTING,
            RecoveryState.SUCCEEDED,
            RecoveryState.FAILED,
            RecoveryState.CIRCUIT_OPEN,
        ]

        assert len(states) == 9


class TestTaskRecoveryState:
    """Test TaskRecoveryState state machine."""

    def test_initial_state(self):
        """Task starts in INITIAL state."""
        from aurora_spawner.recovery import RecoveryState, TaskRecoveryState

        state = TaskRecoveryState(
            task_id="task-1",
            agent_id="test-agent",
        )

        assert state.state == RecoveryState.INITIAL
        assert state.attempt == 0
        assert not state.is_terminal
        assert state.transitions == []

    def test_happy_path_flow(self):
        """Test successful execution flow: INITIAL -> EXECUTING -> SUCCEEDED."""
        from aurora_spawner.recovery import RecoveryState, TaskRecoveryState

        state = TaskRecoveryState(
            task_id="task-1",
            agent_id="test-agent",
        )

        state.start()
        assert state.state == RecoveryState.EXECUTING
        assert len(state.transitions) == 1

        state.succeed()
        assert state.state == RecoveryState.SUCCEEDED
        assert state.is_terminal
        assert len(state.transitions) == 2

    def test_retry_flow(self):
        """Test retry flow: INITIAL -> EXECUTING -> RETRY_PENDING -> RETRYING -> SUCCEEDED."""
        from aurora_spawner.recovery import RecoveryState, TaskRecoveryState

        state = TaskRecoveryState(
            task_id="task-1",
            agent_id="test-agent",
            max_retries=2,
        )

        state.start()
        assert state.state == RecoveryState.EXECUTING

        # First failure - should go to RETRY_PENDING
        state.fail("Connection timeout")
        assert state.state == RecoveryState.RETRY_PENDING
        assert state.attempt == 1
        assert state.last_error == "Connection timeout"

        # Start retry
        state.start_retry()
        assert state.state == RecoveryState.RETRYING

        # Retry succeeds
        state.succeed()
        assert state.state == RecoveryState.SUCCEEDED
        assert state.recovery_path == ["retry:1"]

    def test_fallback_flow(self):
        """Test fallback flow: fails retries then falls back."""
        from aurora_spawner.recovery import RecoveryState, TaskRecoveryState

        state = TaskRecoveryState(
            task_id="task-1",
            agent_id="test-agent",
            max_retries=1,
            fallback_enabled=True,
        )

        state.start()

        # First failure
        state.fail("Error 1")
        assert state.state == RecoveryState.RETRY_PENDING

        state.start_retry()
        state.fail("Error 2")
        assert state.state == RecoveryState.FALLBACK_PENDING

        state.start_fallback()
        assert state.state == RecoveryState.FALLBACK_EXECUTING
        assert state.used_fallback is True

        state.succeed()
        assert state.state == RecoveryState.SUCCEEDED
        assert "fallback" in state.recovery_path

    def test_failure_no_recovery(self):
        """Test immediate failure when no recovery options."""
        from aurora_spawner.recovery import RecoveryState, TaskRecoveryState

        state = TaskRecoveryState(
            task_id="task-1",
            agent_id="test-agent",
            max_retries=0,
            fallback_enabled=False,
        )

        state.start()
        state.fail("Fatal error")

        assert state.state == RecoveryState.FAILED
        assert state.is_terminal

    def test_circuit_open_with_fallback(self):
        """Test circuit open with fallback enabled."""
        from aurora_spawner.recovery import RecoveryState, TaskRecoveryState

        state = TaskRecoveryState(
            task_id="task-1",
            agent_id="blocked-agent",
            fallback_enabled=True,
        )

        state.circuit_open()
        assert state.state == RecoveryState.CIRCUIT_OPEN

        state.start_fallback()
        assert state.state == RecoveryState.FALLBACK_EXECUTING

        state.succeed()
        assert state.state == RecoveryState.SUCCEEDED
        assert "circuit_open" in state.recovery_path

    def test_circuit_open_no_fallback(self):
        """Test circuit open without fallback goes to FAILED."""
        from aurora_spawner.recovery import RecoveryState, TaskRecoveryState

        state = TaskRecoveryState(
            task_id="task-1",
            agent_id="blocked-agent",
            fallback_enabled=False,
        )

        state.circuit_open()
        assert state.state == RecoveryState.FAILED
        assert state.is_terminal

    def test_to_dict(self):
        """Test serialization to dictionary."""
        from aurora_spawner.recovery import TaskRecoveryState

        state = TaskRecoveryState(
            task_id="task-1",
            agent_id="test-agent",
            max_retries=2,
        )

        state.start()
        state.fail("Error")
        state.start_retry()
        state.succeed()

        data = state.to_dict()

        assert data["task_id"] == "task-1"
        assert data["agent_id"] == "test-agent"
        assert data["state"] == "succeeded"
        assert data["attempt"] == 1
        assert len(data["transitions"]) == 4
        assert data["recovery_path"] == ["retry:1"]


class TestRecoveryStateMachine:
    """Test RecoveryStateMachine coordinator."""

    def test_create_task_state(self):
        """Test creating task state."""
        from aurora_spawner.recovery import RecoveryPolicy, RecoveryStateMachine

        sm = RecoveryStateMachine(policy=RecoveryPolicy(max_retries=3))
        state = sm.create_task_state("task-1", "agent-1")

        assert state.task_id == "task-1"
        assert state.agent_id == "agent-1"
        assert state.max_retries == 3

    def test_get_task_state(self):
        """Test retrieving task state."""
        from aurora_spawner.recovery import RecoveryStateMachine

        sm = RecoveryStateMachine()
        sm.create_task_state("task-1", "agent-1")

        assert sm.get_task_state("task-1") is not None
        assert sm.get_task_state("task-2") is None

    def test_policy_per_agent_override(self):
        """Test per-agent policy overrides in state machine."""
        from aurora_spawner.recovery import RecoveryPolicy, RecoveryStateMachine

        policy = RecoveryPolicy(max_retries=2).with_override("slow-agent", max_retries=5)
        sm = RecoveryStateMachine(policy=policy)

        fast_state = sm.create_task_state("task-1", "fast-agent")
        slow_state = sm.create_task_state("task-2", "slow-agent")

        assert fast_state.max_retries == 2
        assert slow_state.max_retries == 5

    def test_get_summary(self):
        """Test summary generation."""
        from aurora_spawner.recovery import RecoveryStateMachine

        sm = RecoveryStateMachine()

        # Task 1: Success
        state1 = sm.create_task_state("task-1", "agent-1")
        state1.start()
        state1.succeed()

        # Task 2: Failed
        state2 = sm.create_task_state("task-2", "agent-2")
        state2.start()
        state2.fail("Error")
        state2.transition(
            state2.state,  # Simulate going to FAILED
        )

        summary = sm.get_summary()

        assert summary["total_tasks"] == 2
        assert summary["succeeded"] == 1
        assert "by_state" in summary

    def test_clear(self):
        """Test clearing state machine."""
        from aurora_spawner.recovery import RecoveryStateMachine

        sm = RecoveryStateMachine()
        sm.create_task_state("task-1", "agent-1")
        sm.create_task_state("task-2", "agent-2")

        sm.clear()

        assert sm.get_task_state("task-1") is None
        assert sm.get_task_state("task-2") is None


# =============================================================================
# SPAWN WITH STATE TRACKING TESTS
# =============================================================================


class TestSpawnParallelWithStateTracking:
    """Test spawn_parallel_with_state_tracking function."""

    @pytest.mark.asyncio
    async def test_empty_tasks(self):
        """Empty task list returns empty results."""
        from aurora_spawner.spawner import spawn_parallel_with_state_tracking

        results, summary = await spawn_parallel_with_state_tracking([])

        assert results == []
        assert summary["total_tasks"] == 0

    @pytest.mark.asyncio
    async def test_success_tracking(self):
        """Successful execution tracks state correctly."""
        from aurora_spawner.spawner import spawn_parallel_with_state_tracking

        async def mock_spawn(task, **kwargs):
            return SpawnResult(
                success=True,
                output="Success",
                error=None,
                exit_code=0,
            )

        tasks = [
            SpawnTask(prompt="Task 0", agent="test-agent", timeout=10),
            SpawnTask(prompt="Task 1", agent="test-agent", timeout=10),
        ]

        with patch("aurora_spawner.spawner.spawn", side_effect=mock_spawn):
            with patch("aurora_spawner.circuit_breaker.get_circuit_breaker") as mock_cb:
                cb = CircuitBreaker(failure_threshold=10)
                mock_cb.return_value = cb

                results, summary = await spawn_parallel_with_state_tracking(tasks)

                assert len(results) == 2
                assert all(r.success for r in results)
                assert summary["succeeded"] == 2
                assert summary["failed"] == 0

    @pytest.mark.asyncio
    async def test_state_change_callback(self):
        """State change callback is invoked."""
        from aurora_spawner.spawner import spawn_parallel_with_state_tracking

        state_changes = []

        def on_state_change(task_id, agent_id, from_state, to_state):
            state_changes.append(
                {
                    "task": task_id,
                    "agent": agent_id,
                    "from": from_state,
                    "to": to_state,
                },
            )

        async def mock_spawn(task, **kwargs):
            return SpawnResult(
                success=True,
                output="Success",
                error=None,
                exit_code=0,
            )

        tasks = [SpawnTask(prompt="Task 0", agent="test-agent", timeout=10)]

        with patch("aurora_spawner.spawner.spawn", side_effect=mock_spawn):
            with patch("aurora_spawner.circuit_breaker.get_circuit_breaker") as mock_cb:
                cb = CircuitBreaker(failure_threshold=10)
                mock_cb.return_value = cb

                await spawn_parallel_with_state_tracking(
                    tasks,
                    on_state_change=on_state_change,
                )

                # Should have at least INITIAL->EXECUTING and EXECUTING->SUCCEEDED
                assert len(state_changes) >= 2
                assert state_changes[0]["to"] == "executing"
                assert state_changes[-1]["to"] == "succeeded"

    @pytest.mark.asyncio
    async def test_retry_state_tracking(self):
        """Retry path is tracked in state machine."""
        from aurora_spawner.spawner import spawn_parallel_with_state_tracking

        attempt_count = 0

        async def mock_spawn(task, **kwargs):
            nonlocal attempt_count
            attempt_count += 1

            if attempt_count == 1:
                return SpawnResult(
                    success=False,
                    output="",
                    error="Transient error",
                    exit_code=-1,
                )

            return SpawnResult(
                success=True,
                output="Recovered",
                error=None,
                exit_code=0,
            )

        tasks = [SpawnTask(prompt="Flaky task", agent="flaky-agent", timeout=10)]

        with patch("aurora_spawner.spawner.spawn", side_effect=mock_spawn):
            with patch("aurora_spawner.circuit_breaker.get_circuit_breaker") as mock_cb:
                cb = CircuitBreaker(failure_threshold=20, fast_fail_threshold=20)
                mock_cb.return_value = cb

                results, summary = await spawn_parallel_with_state_tracking(
                    tasks,
                    recovery_policy=RecoveryPolicy(max_retries=2),
                )

                assert results[0].success
                assert results[0].retry_count > 0
                assert summary["recovered"] >= 1
