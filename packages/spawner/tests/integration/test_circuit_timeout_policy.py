"""Integration tests for circuit breaker state machine, retry/termination policies, heartbeat.

Tests pure logic — no LLM calls, no network, no subprocesses.
"""

import time
from unittest.mock import patch

import pytest

from aurora_spawner.circuit_breaker import CircuitBreaker, CircuitState
from aurora_spawner.heartbeat import HeartbeatEmitter, HeartbeatEventType, HeartbeatMonitor
from aurora_spawner.timeout_policy import (
    RetryPolicy,
    RetryStrategy,
    SpawnPolicy,
    TerminationPolicy,
    TimeoutMode,
    TimeoutPolicy,
)

# ---------------------------------------------------------------------------
# Circuit breaker state machine
# ---------------------------------------------------------------------------


class TestCircuitBreakerStateMachine:
    """Tests for CLOSED → OPEN → HALF_OPEN → CLOSED transitions."""

    def test_circuit_closed_to_open(self):
        """Failures exceeding threshold transition CLOSED → OPEN."""
        cb = CircuitBreaker(failure_threshold=2, failure_window=300)
        cb.record_failure("a1", fast_fail=False)
        assert cb._get_circuit("a1").state == CircuitState.CLOSED
        cb.record_failure("a1", fast_fail=False)
        assert cb._get_circuit("a1").state == CircuitState.OPEN

    def test_circuit_open_to_half_open(self):
        """After reset_timeout elapses, OPEN → HALF_OPEN and should_skip returns False."""
        cb = CircuitBreaker(failure_threshold=1, reset_timeout=0.05, failure_window=300)
        cb.record_failure("a1", fast_fail=False)
        assert cb.is_open("a1")

        time.sleep(0.06)
        skip, reason = cb.should_skip("a1")
        assert not skip
        assert cb._get_circuit("a1").state == CircuitState.HALF_OPEN

    def test_circuit_half_open_success(self):
        """Success in HALF_OPEN transitions back to CLOSED."""
        cb = CircuitBreaker(failure_threshold=1, reset_timeout=0.01, failure_window=300)
        cb.record_failure("a1", fast_fail=False)
        time.sleep(0.02)
        cb.should_skip("a1")  # triggers HALF_OPEN
        assert cb._get_circuit("a1").state == CircuitState.HALF_OPEN

        cb.record_success("a1")
        assert cb._get_circuit("a1").state == CircuitState.CLOSED
        assert cb._get_circuit("a1").failure_count == 0

    def test_circuit_open_skip_reason(self):
        """should_skip returns True with descriptive reason when OPEN."""
        cb = CircuitBreaker(failure_threshold=1, reset_timeout=600, failure_window=300)
        cb.record_failure("a1", fast_fail=False)
        skip, reason = cb.should_skip("a1")
        assert skip
        assert "Circuit open" in reason
        assert "retry in" in reason


class TestCircuitBreakerAdhoc:
    """Tests for adhoc agent detection and higher thresholds."""

    @pytest.mark.parametrize("agent_id", ["task-adhoc-1", "my-AD-HOC-agent", "ad-hoc-worker"])
    def test_circuit_adhoc_detection(self, agent_id):
        """Adhoc patterns detected case-insensitively."""
        cb = CircuitBreaker()
        assert cb._is_adhoc_agent(agent_id)

    def test_circuit_adhoc_mark_explicit(self):
        """Explicitly marked agents detected as adhoc."""
        cb = CircuitBreaker()
        assert not cb._is_adhoc_agent("plain-agent")
        cb.mark_as_adhoc("plain-agent")
        assert cb._is_adhoc_agent("plain-agent")

    def test_circuit_adhoc_higher_threshold(self):
        """Adhoc agents need more failures (adhoc_failure_threshold) to open."""
        cb = CircuitBreaker(
            failure_threshold=2,
            adhoc_failure_threshold=4,
            failure_window=300,
        )
        for _ in range(3):
            cb.record_failure("adhoc-agent-1", fast_fail=False)
        # 3 < adhoc threshold of 4 → still CLOSED
        assert cb._get_circuit("adhoc-agent-1").state == CircuitState.CLOSED

        cb.record_failure("adhoc-agent-1", fast_fail=False)
        assert cb._get_circuit("adhoc-agent-1").state == CircuitState.OPEN

    def test_circuit_non_adhoc_normal_threshold(self):
        """Non-adhoc agents use standard failure_threshold."""
        cb = CircuitBreaker(
            failure_threshold=2,
            adhoc_failure_threshold=4,
            failure_window=300,
        )
        cb.record_failure("regular-agent", fast_fail=False)
        cb.record_failure("regular-agent", fast_fail=False)
        assert cb._get_circuit("regular-agent").state == CircuitState.OPEN


class TestCircuitBreakerAdvanced:
    """Tests for velocity, health status, permanent errors, reset."""

    def test_circuit_failure_velocity_no_history(self):
        """No failures → velocity 0."""
        cb = CircuitBreaker()
        assert cb.get_failure_velocity("unknown") == 0.0

    def test_circuit_failure_velocity_single(self):
        """Single failure → velocity 0 (need ≥2 for rate calc)."""
        cb = CircuitBreaker()
        cb.record_failure("a1", fast_fail=False)
        assert cb.get_failure_velocity("a1") == 0.0

    def test_circuit_failure_velocity_multiple(self):
        """Multiple failures produce positive velocity."""
        cb = CircuitBreaker(failure_window=300)
        cb.record_failure("a1", fast_fail=False)
        cb.record_failure("a1", fast_fail=False)
        vel = cb.get_failure_velocity("a1")
        assert vel > 0.0

    def test_circuit_health_status_risk_levels(self):
        """Risk levels: low (closed) → medium (near threshold) → critical (open)."""
        cb = CircuitBreaker(failure_threshold=3, failure_window=300)

        # Fresh agent → low risk
        status = cb.get_health_status("a1")
        assert status["risk_level"] == "low"
        assert status["can_execute"]

        # Near threshold → medium
        cb.record_failure("a1", fast_fail=False)
        cb.record_failure("a1", fast_fail=False)
        status = cb.get_health_status("a1")
        assert status["risk_level"] == "medium"

        # Open circuit → critical
        cb.record_failure("a1", fast_fail=False)
        status = cb.get_health_status("a1")
        assert status["risk_level"] == "critical"
        assert not status["can_execute"]

    def test_circuit_permanent_error_fast_fail(self):
        """Permanent errors (auth, invalid_model) open circuit via fast-fail."""
        cb = CircuitBreaker(failure_threshold=10, fast_fail_threshold=2, failure_window=300)
        cb.record_failure("a1", failure_type="auth_error", fast_fail=True)
        cb.record_failure("a1", failure_type="auth_error", fast_fail=True)
        assert cb._get_circuit("a1").state == CircuitState.OPEN

    def test_circuit_rate_limit_ignored(self):
        """Rate limit failures do NOT trigger circuit breaker."""
        cb = CircuitBreaker(failure_threshold=1, failure_window=300)
        cb.record_failure("a1", failure_type="rate_limit")
        assert cb._get_circuit("a1").state == CircuitState.CLOSED
        assert cb._get_circuit("a1").failure_count == 0

    def test_circuit_reset_single(self):
        """Manual reset clears circuit for one agent."""
        cb = CircuitBreaker(failure_threshold=1, failure_window=300)
        cb.record_failure("a1", fast_fail=False)
        assert cb.is_open("a1")
        cb.reset("a1")
        assert not cb.is_open("a1")

    def test_circuit_reset_all(self):
        """reset_all clears all circuits."""
        cb = CircuitBreaker(failure_threshold=1, failure_window=300)
        cb.record_failure("a1", fast_fail=False)
        cb.record_failure("a2", fast_fail=False)
        cb.reset_all()
        assert not cb.is_open("a1")
        assert not cb.is_open("a2")


# ---------------------------------------------------------------------------
# Retry policy
# ---------------------------------------------------------------------------


class TestRetryPolicy:
    """Tests for RetryPolicy delay calculation and should_retry logic."""

    def test_retry_should_retry_max_attempts(self):
        """Exceeding max_attempts → should_retry returns False."""
        rp = RetryPolicy(max_attempts=3)
        ok, _ = rp.should_retry(3)
        assert not ok
        assert "Max attempts" in _

    def test_retry_should_retry_rate_limit(self):
        """Rate limit → never retry regardless of attempt number."""
        rp = RetryPolicy(max_attempts=10)
        ok, reason = rp.should_retry(0, error_type="rate_limit")
        assert not ok
        assert "rate_limit" in reason.lower() or "Rate limit" in reason

    def test_retry_should_retry_timeout_disabled(self):
        """retry_on_timeout=False → timeout errors not retried."""
        rp = RetryPolicy(retry_on_timeout=False)
        ok, _ = rp.should_retry(0, error_type="timeout")
        assert not ok

    def test_retry_should_retry_allowed(self):
        """Normal attempt within limits → should_retry returns True."""
        rp = RetryPolicy(max_attempts=3)
        ok, _ = rp.should_retry(0)
        assert ok

    def test_retry_all_strategies(self):
        """All strategies produce correct delay values."""
        # IMMEDIATE → 0
        rp = RetryPolicy(strategy=RetryStrategy.IMMEDIATE, jitter=False)
        assert rp.get_delay(0) == 0.0
        assert rp.get_delay(5) == 0.0

        # FIXED_DELAY → base_delay
        rp = RetryPolicy(strategy=RetryStrategy.FIXED_DELAY, base_delay=5.0, jitter=False)
        assert rp.get_delay(0) == 5.0
        assert rp.get_delay(3) == 5.0

        # EXPONENTIAL_BACKOFF → base * factor^attempt
        rp = RetryPolicy(
            strategy=RetryStrategy.EXPONENTIAL_BACKOFF,
            base_delay=1.0,
            backoff_factor=2.0,
            max_delay=100.0,
            jitter=False,
        )
        assert rp.get_delay(0) == 1.0  # 1 * 2^0
        assert rp.get_delay(1) == 2.0  # 1 * 2^1
        assert rp.get_delay(2) == 4.0  # 1 * 2^2

        # LINEAR_BACKOFF → base * (1 + factor * attempt)
        rp = RetryPolicy(
            strategy=RetryStrategy.LINEAR_BACKOFF,
            base_delay=2.0,
            backoff_factor=3.0,
            max_delay=100.0,
            jitter=False,
        )
        assert rp.get_delay(0) == 2.0  # 2*(1+3*0)
        assert rp.get_delay(1) == 8.0  # 2*(1+3*1)
        assert rp.get_delay(2) == 14.0  # 2*(1+3*2)

    def test_retry_max_delay_cap(self):
        """Delay never exceeds max_delay."""
        rp = RetryPolicy(
            strategy=RetryStrategy.EXPONENTIAL_BACKOFF,
            base_delay=10.0,
            backoff_factor=10.0,
            max_delay=50.0,
            jitter=False,
        )
        assert rp.get_delay(5) == 50.0


# ---------------------------------------------------------------------------
# Termination policy
# ---------------------------------------------------------------------------


class TestTerminationPolicy:
    """Tests for TerminationPolicy error pattern matching and custom predicates."""

    def test_termination_error_patterns(self):
        """Default error patterns trigger termination on stderr match."""
        tp = TerminationPolicy()
        # rate limit pattern
        should, reason = tp.should_terminate("", "Error: rate limit exceeded", 10, 5)
        assert should
        assert "rate" in reason.lower()

        # 429 pattern
        should, reason = tp.should_terminate("", "HTTP 429 Too Many Requests", 10, 5)
        assert should

        # connection error
        should, reason = tp.should_terminate("", "connection refused by host", 10, 5)
        assert should

    def test_termination_no_match(self):
        """Normal output does not trigger termination."""
        tp = TerminationPolicy()
        should, _ = tp.should_terminate("output", "some warning", 10, 5)
        assert not should

    def test_termination_custom_predicates(self):
        """Custom callable triggers termination."""
        pred = lambda stdout, stderr: "FATAL" in stderr
        tp = TerminationPolicy(custom_predicates=[pred])
        should, reason = tp.should_terminate("", "FATAL crash", 10, 5)
        assert should
        assert "Custom" in reason

    def test_termination_disabled(self):
        """enabled=False → never terminate."""
        tp = TerminationPolicy(enabled=False)
        should, _ = tp.should_terminate("", "rate limit hit 429", 10, 5)
        assert not should

    def test_termination_empty_stderr(self):
        """Empty stderr → no termination even with patterns enabled."""
        tp = TerminationPolicy()
        should, _ = tp.should_terminate("output", "", 10, 5)
        assert not should


# ---------------------------------------------------------------------------
# Spawn policy presets
# ---------------------------------------------------------------------------


class TestSpawnPolicy:
    """Tests for SpawnPolicy presets and from_name factory."""

    @pytest.mark.parametrize(
        "name", ["default", "production", "fast_fail", "patient", "development", "test"]
    )
    def test_spawn_policy_all_presets_valid(self, name):
        """All 6 presets return valid SpawnPolicy instances."""
        policy = SpawnPolicy.from_name(name)
        assert policy.name == name
        assert isinstance(policy.timeout_policy, TimeoutPolicy)
        assert isinstance(policy.retry_policy, RetryPolicy)
        assert isinstance(policy.termination_policy, TerminationPolicy)

    def test_spawn_policy_from_name_invalid(self):
        """Unknown preset name raises ValueError."""
        with pytest.raises(ValueError, match="Unknown policy preset"):
            SpawnPolicy.from_name("nonexistent")

    def test_spawn_policy_fast_fail_values(self):
        """fast_fail preset has short timeouts and minimal retries."""
        p = SpawnPolicy.fast_fail()
        assert p.timeout_policy.timeout == 60.0
        assert p.timeout_policy.mode == TimeoutMode.FIXED
        assert p.retry_policy.max_attempts == 1
        assert not p.retry_policy.retry_on_timeout

    def test_spawn_policy_patient_values(self):
        """patient preset has longer timeouts."""
        p = SpawnPolicy.patient()
        assert p.timeout_policy.initial_timeout >= 120.0
        assert p.timeout_policy.max_timeout >= 600.0
        assert p.timeout_policy.no_activity_timeout >= 120.0

    def test_spawn_policy_development_no_termination(self):
        """development preset disables termination."""
        p = SpawnPolicy.development()
        assert not p.termination_policy.enabled
        assert p.timeout_policy.timeout >= 1800.0


# ---------------------------------------------------------------------------
# Heartbeat
# ---------------------------------------------------------------------------


class TestHeartbeat:
    """Tests for HeartbeatEmitter and HeartbeatMonitor."""

    def test_heartbeat_subscriber_error(self):
        """Bad subscriber doesn't crash emitter."""
        emitter = HeartbeatEmitter(task_id="t1")
        errors = []

        def bad_subscriber(event):
            raise RuntimeError("subscriber crash")

        def good_subscriber(event):
            errors.append(event.event_type)

        emitter.subscribe(bad_subscriber)
        emitter.subscribe(good_subscriber)

        # Should not raise
        emitter.emit(HeartbeatEventType.STARTED)
        assert HeartbeatEventType.STARTED in errors

    def test_heartbeat_monitor_threshold_warning(self):
        """Monitor emits TIMEOUT_WARNING at warning_threshold fraction of timeout."""
        emitter = HeartbeatEmitter(task_id="t1")
        monitor = HeartbeatMonitor(
            emitter=emitter,
            total_timeout=100,
            activity_timeout=200,
            warning_threshold=0.8,
        )

        # Simulate start
        emitter.emit(HeartbeatEventType.STARTED)

        # Mock time so elapsed > 80% of 100s
        with patch.object(emitter, "seconds_since_start", return_value=85.0):
            with patch.object(emitter, "seconds_since_activity", return_value=1.0):
                healthy, _ = monitor.check_health()

        assert healthy
        # Warning event should have been emitted
        events = emitter.get_all_events()
        warning_events = [e for e in events if e.event_type == HeartbeatEventType.TIMEOUT_WARNING]
        assert len(warning_events) == 1

    def test_heartbeat_monitor_timeout(self):
        """Monitor returns unhealthy when total timeout exceeded."""
        emitter = HeartbeatEmitter(task_id="t1")
        monitor = HeartbeatMonitor(emitter=emitter, total_timeout=10, activity_timeout=200)
        emitter.emit(HeartbeatEventType.STARTED)

        with patch.object(emitter, "seconds_since_start", return_value=15.0):
            with patch.object(emitter, "seconds_since_activity", return_value=1.0):
                healthy, reason = monitor.check_health()

        assert not healthy
        assert "timeout" in reason.lower()

    def test_heartbeat_activity_tracking(self):
        """STDOUT events update last_activity timestamp."""
        emitter = HeartbeatEmitter(task_id="t1")
        emitter.emit(HeartbeatEventType.STARTED)
        assert emitter._last_activity is None  # STARTED doesn't count as activity

        emitter.emit(HeartbeatEventType.STDOUT, message="output")
        assert emitter._last_activity is not None
