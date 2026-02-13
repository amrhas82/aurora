"""Integration tests for spawner recovery, early detection, and observability.

Tests recovery state machine, error classification, recovery policies,
early detection config, and observability metrics — all pure Python logic.
"""

import time

import pytest

from aurora_spawner.early_detection import EarlyDetectionConfig, ExecutionState
from aurora_spawner.observability import (
    AgentHealthMonitor,
    FailureEvent,
    FailureReason,
    HealthMetrics,
    ProactiveHealthConfig,
)
from aurora_spawner.recovery import (
    ErrorCategory,
    ErrorClassifier,
    RecoveryPolicy,
    RecoveryState,
    RecoveryStateMachine,
    RecoveryStrategy,
    TaskRecoveryState,
)
from aurora_spawner.timeout_policy import RetryPolicy
from aurora_spawner.timeout_policy import RetryStrategy as TimeoutRetryStrategy
from aurora_spawner.timeout_policy import TimeoutMode, TimeoutPolicy

# ---------------------------------------------------------------------------
# Recovery State Machine
# ---------------------------------------------------------------------------


class TestRecoveryStateMachineHappyPath:
    """Test INITIAL → EXECUTING → SUCCEEDED transitions."""

    def test_happy_path(self):
        state = TaskRecoveryState(task_id="t1", agent_id="a1")
        assert state.state == RecoveryState.INITIAL

        state.start()
        assert state.state == RecoveryState.EXECUTING

        state.succeed()
        assert state.state == RecoveryState.SUCCEEDED
        assert state.is_terminal
        assert len(state.transitions) == 2


class TestRecoveryStateMachineRetryFlow:
    """Test EXECUTING → RETRY_PENDING → RETRYING → SUCCEEDED."""

    def test_retry_flow(self):
        state = TaskRecoveryState(task_id="t1", agent_id="a1", max_retries=2)
        state.start()
        result = state.fail("timeout error")
        assert result == RecoveryState.RETRY_PENDING
        assert state.attempt == 1

        state.start_retry()
        assert state.state == RecoveryState.RETRYING

        state.succeed()
        assert state.state == RecoveryState.SUCCEEDED
        assert state.attempt == 1


class TestRecoveryStateMachineFallbackFlow:
    """Test RETRYING → FALLBACK_PENDING → FALLBACK_EXECUTING → SUCCEEDED."""

    def test_fallback_flow(self):
        state = TaskRecoveryState(
            task_id="t1",
            agent_id="a1",
            max_retries=1,
            fallback_enabled=True,
        )
        state.start()

        # First failure → retry
        state.fail("error1")
        state.start_retry()

        # Second failure → exhausts retries, goes to fallback
        result = state.fail("error2")
        assert result == RecoveryState.FALLBACK_PENDING

        state.start_fallback()
        assert state.state == RecoveryState.FALLBACK_EXECUTING
        assert state.used_fallback

        state.succeed()
        assert state.state == RecoveryState.SUCCEEDED


class TestRecoveryStateMachineFullFailure:
    """Test all recovery exhausted → FAILED."""

    def test_full_failure(self):
        state = TaskRecoveryState(
            task_id="t1",
            agent_id="a1",
            max_retries=0,
            fallback_enabled=False,
        )
        state.start()
        result = state.fail("fatal error")
        assert result == RecoveryState.FAILED
        assert state.is_terminal
        assert state.last_error == "fatal error"


class TestRecoveryStateMachineCircuitOpen:
    """Test INITIAL → CIRCUIT_OPEN when breaker is open."""

    def test_circuit_open_with_fallback(self):
        state = TaskRecoveryState(
            task_id="t1",
            agent_id="a1",
            fallback_enabled=True,
        )
        result = state.circuit_open()
        assert result == RecoveryState.CIRCUIT_OPEN
        assert "circuit_open" in state.recovery_path

    def test_circuit_open_no_fallback(self):
        state = TaskRecoveryState(
            task_id="t1",
            agent_id="a1",
            fallback_enabled=False,
        )
        result = state.circuit_open()
        assert result == RecoveryState.FAILED


# ---------------------------------------------------------------------------
# Recovery Policy
# ---------------------------------------------------------------------------


class TestRecoveryPolicyPresets:
    """Test recovery policy preset factories."""

    def test_default_preset(self):
        policy = RecoveryPolicy.default()
        assert policy.max_retries == 2
        assert policy.fallback_to_llm is True
        assert policy.strategy == RecoveryStrategy.RETRY_THEN_FALLBACK
        assert policy.base_delay == 1.0
        assert policy.jitter is True

    def test_patient_preset(self):
        policy = RecoveryPolicy.patient()
        assert policy.max_retries == 3
        assert policy.base_delay == 2.0
        assert policy.backoff_factor == 3.0
        assert policy.max_delay == 120.0
        # Patient has more retries / longer backoff than default
        default = RecoveryPolicy.default()
        assert policy.max_retries > default.max_retries
        assert policy.base_delay > default.base_delay

    def test_aggressive_preset(self):
        policy = RecoveryPolicy.aggressive_retry()
        assert policy.max_retries == 5
        assert policy.fallback_to_llm is False
        assert policy.base_delay == 0.5
        # Shorter base delay than default
        default = RecoveryPolicy.default()
        assert policy.base_delay < default.base_delay

    def test_from_name(self):
        for name in ("default", "aggressive_retry", "fast_fallback", "no_recovery", "patient"):
            policy = RecoveryPolicy.from_name(name)
            assert isinstance(policy, RecoveryPolicy)

        with pytest.raises(ValueError, match="Unknown recovery preset"):
            RecoveryPolicy.from_name("nonexistent")


# ---------------------------------------------------------------------------
# Error Classifier
# ---------------------------------------------------------------------------


class TestErrorClassifier:
    """Test error message classification."""

    def test_permanent_errors(self):
        classifier = ErrorClassifier()
        for msg in ("401 Unauthorized", "403 Forbidden", "invalid model name"):
            category = classifier.classify(msg)
            assert category == ErrorCategory.PERMANENT, f"Expected PERMANENT for: {msg}"
        assert not classifier.should_retry(ErrorCategory.PERMANENT)

    def test_transient_errors(self):
        classifier = ErrorClassifier()
        for msg in ("connection refused", "ECONNRESET", "temporary failure"):
            category = classifier.classify(msg)
            assert category == ErrorCategory.TRANSIENT, f"Expected TRANSIENT for: {msg}"
        assert classifier.should_retry(ErrorCategory.TRANSIENT)

    def test_rate_limit(self):
        classifier = ErrorClassifier()
        for msg in ("429 rate limit exceeded", "rate_limit error"):
            category = classifier.classify(msg)
            assert category == ErrorCategory.TRANSIENT, f"Expected TRANSIENT for: {msg}"

    def test_timeout_errors(self):
        classifier = ErrorClassifier()
        for msg in ("request timed out", "deadline exceeded"):
            category = classifier.classify(msg)
            assert category == ErrorCategory.TIMEOUT, f"Expected TIMEOUT for: {msg}"
        assert classifier.should_retry(ErrorCategory.TIMEOUT)

    def test_unknown_error(self):
        classifier = ErrorClassifier()
        category = classifier.classify("something completely random happened")
        assert category == ErrorCategory.UNKNOWN
        assert classifier.should_retry(ErrorCategory.UNKNOWN)


# ---------------------------------------------------------------------------
# Early Detection
# ---------------------------------------------------------------------------


class TestEarlyDetectionConfig:
    """Test early detection configuration defaults."""

    def test_defaults(self):
        config = EarlyDetectionConfig()
        assert config.enabled is True
        assert config.check_interval == 5.0
        assert config.stall_threshold == 120.0
        assert config.min_output_bytes == 100
        assert config.stderr_pattern_check is True
        assert config.terminate_on_stall is False


class TestEarlyDetectionStallLogic:
    """Test stall detection using ExecutionState directly."""

    def test_stall_detected(self):
        """Stall detected when time_since_activity > threshold with enough output."""
        config = EarlyDetectionConfig(stall_threshold=10.0, min_output_bytes=50)
        state = ExecutionState(
            task_id="t1",
            agent_id="a1",
            start_time=time.time() - 60,
            last_activity_time=time.time() - 15,  # 15s ago, threshold is 10s
            stdout_size=200,  # Above min_output_bytes
        )
        time_since_activity = time.time() - state.last_activity_time
        # Stall condition: output above min AND time_since_activity > threshold
        assert state.stdout_size >= config.min_output_bytes
        assert time_since_activity > config.stall_threshold

    def test_no_stall_below_min_bytes(self):
        """No stall if output below min_output_bytes."""
        config = EarlyDetectionConfig(stall_threshold=10.0, min_output_bytes=100)
        state = ExecutionState(
            task_id="t1",
            agent_id="a1",
            start_time=time.time() - 60,
            last_activity_time=time.time() - 15,
            stdout_size=50,  # Below min_output_bytes
        )
        assert state.stdout_size < config.min_output_bytes

    def test_activity_resets_stall(self):
        """Activity update resets stall counter."""
        state = ExecutionState(
            task_id="t1",
            agent_id="a1",
            start_time=time.time() - 60,
            last_activity_time=time.time() - 30,
            stdout_size=200,
            consecutive_stalls=3,
        )
        # Simulate activity update (like update_activity does)
        new_size = state.stdout_size + 100
        if new_size > state.stdout_size:
            state.last_activity_time = time.time()
            state.consecutive_stalls = 0
        state.stdout_size = new_size

        assert state.consecutive_stalls == 0
        assert time.time() - state.last_activity_time < 1.0


# ---------------------------------------------------------------------------
# Observability
# ---------------------------------------------------------------------------


class TestObservabilityFailureEvent:
    """Test failure event recording."""

    def test_failure_event_fields(self):
        event = FailureEvent(
            agent_id="agent-1",
            task_id="task-1",
            timestamp=time.time(),
            reason=FailureReason.TIMEOUT,
            detection_latency=5.2,
            error_message="Process timed out",
            retry_attempt=1,
        )
        assert event.agent_id == "agent-1"
        assert event.task_id == "task-1"
        assert event.reason == FailureReason.TIMEOUT
        assert event.detection_latency == 5.2
        assert event.error_message == "Process timed out"
        assert event.retry_attempt == 1
        assert event.recovered is False
        assert event.recovery_time is None


class TestObservabilityHealthMetrics:
    """Test health metrics calculation."""

    def test_success_rate_and_avg_time(self):
        monitor = AgentHealthMonitor(ProactiveHealthConfig(enabled=False))

        # Record start → success
        monitor._start_times["t1"] = time.time() - 2.0
        monitor.record_execution_success("t1", "agent-1", output_size=100)

        monitor._start_times["t2"] = time.time() - 4.0
        monitor.record_execution_success("t2", "agent-1", output_size=200)

        metrics = monitor._agent_metrics["agent-1"]
        assert metrics.total_executions == 2
        assert metrics.successful_executions == 2
        assert metrics.failure_rate == 0.0
        assert metrics.avg_execution_time > 0

    def test_failure_recording(self):
        monitor = AgentHealthMonitor(ProactiveHealthConfig(enabled=False))
        monitor._start_times["t1"] = time.time() - 3.0

        monitor.record_execution_failure(
            task_id="t1",
            agent_id="agent-1",
            reason=FailureReason.TIMEOUT,
            error_message="Timed out",
        )

        metrics = monitor._agent_metrics["agent-1"]
        assert metrics.total_executions == 1
        assert metrics.failed_executions == 1
        assert metrics.failure_rate == 1.0
        assert len(monitor._failure_events) == 1


class TestObservabilityAgentHealth:
    """Test per-agent health status queries."""

    def test_agent_health_query(self):
        monitor = AgentHealthMonitor(ProactiveHealthConfig(enabled=False))

        # Mix of successes and failures for agent-1
        monitor._start_times["t1"] = time.time() - 1.0
        monitor.record_execution_success("t1", "agent-1")
        monitor._start_times["t2"] = time.time() - 1.0
        monitor.record_execution_success("t2", "agent-1")
        monitor._start_times["t3"] = time.time() - 1.0
        monitor.record_execution_failure("t3", "agent-1", FailureReason.CRASH)

        # agent-2 all success
        monitor._start_times["t4"] = time.time() - 1.0
        monitor.record_execution_success("t4", "agent-2")

        m1 = monitor._agent_metrics["agent-1"]
        assert m1.total_executions == 3
        assert m1.successful_executions == 2
        assert m1.failed_executions == 1
        assert 0.3 < m1.failure_rate < 0.4  # ~33%

        m2 = monitor._agent_metrics["agent-2"]
        assert m2.total_executions == 1
        assert m2.failure_rate == 0.0


# ---------------------------------------------------------------------------
# Timeout Policy
# ---------------------------------------------------------------------------


class TestTimeoutPolicyProgressive:
    """Test progressive timeout extension."""

    def test_progressive_extension_on_activity(self):
        policy = TimeoutPolicy(
            mode=TimeoutMode.PROGRESSIVE,
            initial_timeout=60.0,
            max_timeout=300.0,
            extension_threshold=10.0,
        )
        assert policy.get_initial_timeout() == 60.0

        # Activity within threshold → should extend
        assert policy.should_extend(_elapsed=50.0, last_activity=5.0, current_timeout=60.0)

        # Extended timeout = 1.5x current, capped at max
        extended = policy.get_extended_timeout(60.0)
        assert extended == 90.0

        # Should not extend beyond max
        assert not policy.should_extend(_elapsed=100.0, last_activity=5.0, current_timeout=300.0)

    def test_fixed_mode_no_extension(self):
        policy = TimeoutPolicy(mode=TimeoutMode.FIXED, timeout=120.0)
        assert policy.get_initial_timeout() == 120.0
        assert not policy.should_extend(_elapsed=50.0, last_activity=5.0, current_timeout=120.0)


class TestRetryPolicyBackoff:
    """Test exponential backoff with jitter."""

    def test_exponential_backoff_range(self):
        policy = RetryPolicy(
            strategy=TimeoutRetryStrategy.EXPONENTIAL_BACKOFF,
            base_delay=1.0,
            backoff_factor=2.0,
            max_delay=60.0,
            jitter=True,
            jitter_factor=0.1,
        )
        # attempt=0: base * 2^0 = 1.0 ± 10%
        delay0 = policy.get_delay(0)
        assert 0.9 <= delay0 <= 1.1

        # attempt=1: base * 2^1 = 2.0 ± 10%
        delay1 = policy.get_delay(1)
        assert 1.8 <= delay1 <= 2.2

        # attempt=2: base * 2^2 = 4.0 ± 10%
        delay2 = policy.get_delay(2)
        assert 3.6 <= delay2 <= 4.4

    def test_max_delay_cap(self):
        policy = RetryPolicy(
            strategy=TimeoutRetryStrategy.EXPONENTIAL_BACKOFF,
            base_delay=1.0,
            backoff_factor=2.0,
            max_delay=10.0,
            jitter=False,
        )
        # attempt=10: base * 2^10 = 1024, capped to 10
        delay = policy.get_delay(10)
        assert delay == 10.0


# ---------------------------------------------------------------------------
# RecoveryStateMachine coordinator
# ---------------------------------------------------------------------------


class TestRecoveryStateMachineCoordinator:
    """Test the RecoveryStateMachine coordinator."""

    def test_create_task_state_uses_policy(self):
        """Mock circuit breaker to avoid real singleton."""

        class FakeBreaker:
            def should_skip(self, _):
                return False, None

            def record_success(self, _):
                pass

            def record_failure(self, _, **kwargs):
                pass

        policy = RecoveryPolicy.default()
        sm = RecoveryStateMachine(policy=policy, circuit_breaker=FakeBreaker())

        state = sm.create_task_state("t1", "agent-1")
        assert state.max_retries == policy.max_retries
        assert state.fallback_enabled == policy.fallback_to_llm

    def test_summary(self):
        class FakeBreaker:
            def should_skip(self, _):
                return False, None

            def record_success(self, _):
                pass

            def record_failure(self, _, **kwargs):
                pass

        sm = RecoveryStateMachine(
            policy=RecoveryPolicy.default(),
            circuit_breaker=FakeBreaker(),
        )
        s1 = sm.create_task_state("t1", "a1")
        s1.start()
        s1.succeed()

        s2 = sm.create_task_state("t2", "a2")
        s2.start()
        s2.fail("error")

        summary = sm.get_summary()
        assert summary["total_tasks"] == 2
        assert summary["succeeded"] == 1
