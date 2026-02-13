"""Comprehensive tests for circuit breaker behavior with adhoc agents.

Tests the specialized handling of adhoc (dynamically generated) agents
including lenient thresholds, inference failure handling, and fast-fail windows.
"""

import time

from aurora_spawner.circuit_breaker import CircuitBreaker


class TestAdhocAgentDetection:
    """Test adhoc agent identification logic."""

    def test_explicit_adhoc_marking(self):
        """Agent explicitly marked as adhoc is detected."""
        cb = CircuitBreaker()
        cb.mark_as_adhoc("my-custom-agent")

        assert cb._is_adhoc_agent("my-custom-agent")

    def test_naming_pattern_adhoc(self):
        """Agents with adhoc naming patterns detected."""
        cb = CircuitBreaker()

        assert cb._is_adhoc_agent("adhoc-specialist")
        assert cb._is_adhoc_agent("ad-hoc-agent")
        assert cb._is_adhoc_agent("generated-agent-1")
        assert cb._is_adhoc_agent("dynamic-solver")
        assert cb._is_adhoc_agent("inferred-agent")

    def test_naming_pattern_case_insensitive(self):
        """Adhoc detection is case-insensitive."""
        cb = CircuitBreaker()

        assert cb._is_adhoc_agent("ADHOC-AGENT")
        assert cb._is_adhoc_agent("Adhoc-Agent")
        assert cb._is_adhoc_agent("AdHoc-Specialist")

    def test_registered_agent_not_adhoc(self):
        """Regular registered agents not detected as adhoc."""
        cb = CircuitBreaker()

        assert not cb._is_adhoc_agent("code-reviewer")
        assert not cb._is_adhoc_agent("test-runner")
        assert not cb._is_adhoc_agent("llm")
        assert not cb._is_adhoc_agent("general-purpose")


class TestAdhocFailureThreshold:
    """Test adhoc agents have higher failure threshold."""

    def test_adhoc_higher_threshold(self):
        """Adhoc agents require 4 failures to open circuit."""
        cb = CircuitBreaker(
            failure_threshold=2,
            adhoc_failure_threshold=4,
            failure_window=60.0,
        )
        cb.mark_as_adhoc("adhoc-agent")

        # Record 3 failures - circuit should stay closed
        for _ in range(3):
            cb.record_failure("adhoc-agent", fast_fail=False)

        assert not cb.is_open("adhoc-agent")

        # 4th failure opens circuit
        cb.record_failure("adhoc-agent", fast_fail=False)
        assert cb.is_open("adhoc-agent")

    def test_regular_agent_lower_threshold(self):
        """Regular agents open circuit at 2 failures."""
        cb = CircuitBreaker(
            failure_threshold=2,
            adhoc_failure_threshold=4,
            failure_window=60.0,
        )

        # Record 2 failures - circuit opens
        for _ in range(2):
            cb.record_failure("regular-agent", fast_fail=False)

        assert cb.is_open("regular-agent")

    def test_threshold_applies_per_agent(self):
        """Thresholds applied independently per agent."""
        cb = CircuitBreaker(
            failure_threshold=2,
            adhoc_failure_threshold=4,
            failure_window=60.0,
        )
        cb.mark_as_adhoc("adhoc-agent")

        # Adhoc needs 4
        for _ in range(3):
            cb.record_failure("adhoc-agent", fast_fail=False)
        assert not cb.is_open("adhoc-agent")

        # Regular needs 2
        for _ in range(2):
            cb.record_failure("regular-agent", fast_fail=False)
        assert cb.is_open("regular-agent")


class TestAdhocFastFailWindow:
    """Test adhoc agents have longer fast-fail window."""

    def test_regular_agent_shorter_fast_fail_window(self):
        """Regular agents fast-fail within 10s window."""
        cb = CircuitBreaker(
            failure_threshold=5,  # High threshold to isolate fast-fail test
            fast_fail_threshold=2,
            failure_window=60.0,
        )

        # Two failures in quick succession (< 10s)
        cb.record_failure("regular-agent", fast_fail=True)
        time.sleep(0.02)
        cb.record_failure("regular-agent", fast_fail=True)

        # Should fast-fail and open circuit
        assert cb.is_open("regular-agent")


class TestAdhocInferenceFailureHandling:
    """Test special handling of inference failures for adhoc agents."""

    def test_adhoc_inference_failure_no_fast_fail(self):
        """Adhoc agent inference failures don't trigger fast-fail."""
        cb = CircuitBreaker(
            failure_threshold=5,
            adhoc_failure_threshold=5,
            fast_fail_threshold=2,
            failure_window=60.0,
        )
        cb.mark_as_adhoc("adhoc-agent")

        # Record two rapid inference failures
        cb.record_failure("adhoc-agent", fast_fail=True, failure_type="inference")
        time.sleep(0.01)
        cb.record_failure("adhoc-agent", fast_fail=True, failure_type="inference")

        # Should NOT fast-fail despite rapid succession
        assert not cb.is_open("adhoc-agent")

    def test_regular_agent_inference_failure_fast_fails(self):
        """Regular agents DO fast-fail on inference failures."""
        cb = CircuitBreaker(
            failure_threshold=5,
            fast_fail_threshold=2,
            failure_window=60.0,
        )

        # Record two rapid inference failures
        cb.record_failure("regular-agent", fast_fail=True, failure_type="inference")
        time.sleep(0.01)
        cb.record_failure("regular-agent", fast_fail=True, failure_type="inference")

        # Regular agents fast-fail on inference failures
        assert cb.is_open("regular-agent")


class TestFailureTypeTracking:
    """Test failure type tracking for health analysis."""

    def test_failure_types_recorded(self):
        """Failure types are recorded for health analysis."""
        cb = CircuitBreaker()

        cb.record_failure("agent-1", failure_type="timeout")
        cb.record_failure("agent-1", failure_type="inference")
        cb.record_failure("agent-1", failure_type="error_pattern")

        # Check internal tracking
        assert "agent-1" in cb._failure_types
        assert len(cb._failure_types["agent-1"]) == 3
        assert "timeout" in cb._failure_types["agent-1"]
        assert "inference" in cb._failure_types["agent-1"]
        assert "error_pattern" in cb._failure_types["agent-1"]

    def test_failure_type_history_limited(self):
        """Failure type history limited to recent 10 entries."""
        cb = CircuitBreaker()

        # Record 15 failures
        for i in range(15):
            cb.record_failure("agent-1", failure_type=f"type-{i}")

        # Should only keep last 10
        assert len(cb._failure_types["agent-1"]) == 10
        # Should have type-5 through type-14
        assert "type-5" in cb._failure_types["agent-1"]
        assert "type-14" in cb._failure_types["agent-1"]
        assert "type-0" not in cb._failure_types["agent-1"]


class TestHealthStatusWithAdhoc:
    """Test health status reporting for adhoc agents."""

    def test_health_status_shows_agent_type(self):
        """Health status accessible for both adhoc and regular agents."""
        cb = CircuitBreaker()
        cb.mark_as_adhoc("adhoc-agent")

        # Record failures for both types
        cb.record_failure("adhoc-agent")
        cb.record_failure("regular-agent")

        adhoc_health = cb.get_health_status("adhoc-agent")
        regular_health = cb.get_health_status("regular-agent")

        # Both should return valid health status
        assert adhoc_health["agent_id"] == "adhoc-agent"
        assert regular_health["agent_id"] == "regular-agent"
        assert adhoc_health["recent_failures"] >= 1
        assert regular_health["recent_failures"] >= 1

    def test_failure_velocity_calculation(self):
        """Failure velocity calculated correctly."""
        cb = CircuitBreaker(failure_window=60.0)

        # Record 3 failures in short time
        for _ in range(3):
            cb.record_failure("agent-1")
            time.sleep(0.01)

        velocity = cb.get_failure_velocity("agent-1")
        # 3 failures in ~0.03s = ~6000 failures/minute
        assert velocity > 100  # At least 100 failures/min

    def test_risk_level_assessment(self):
        """Risk level assessed based on circuit state and failures."""
        cb = CircuitBreaker(failure_threshold=2, failure_window=60.0)

        # Fresh agent - low risk
        health = cb.get_health_status("agent-1")
        assert health["risk_level"] == "low"

        # One failure - medium risk (approaching threshold)
        cb.record_failure("agent-1")
        health = cb.get_health_status("agent-1")
        assert health["risk_level"] == "medium"

        # Two failures - circuit open, critical risk
        cb.record_failure("agent-1")
        health = cb.get_health_status("agent-1")
        assert health["risk_level"] == "critical"


class TestCircuitRecovery:
    """Test circuit recovery behavior for adhoc agents."""

    def test_adhoc_agent_success_closes_circuit(self):
        """Successful execution closes circuit for adhoc agent."""
        cb = CircuitBreaker(failure_threshold=2)
        cb.mark_as_adhoc("adhoc-agent")

        # Open circuit
        cb.record_failure("adhoc-agent")
        cb.record_failure("adhoc-agent")
        assert cb.is_open("adhoc-agent")

        # Record success
        cb.record_success("adhoc-agent")
        assert not cb.is_open("adhoc-agent")

    def test_success_clears_failure_history(self):
        """Success clears failure history."""
        cb = CircuitBreaker(failure_threshold=2, failure_window=60.0)

        # Record failures
        cb.record_failure("agent-1")
        cb.record_failure("agent-1")
        assert len(cb._failure_history["agent-1"]) == 2

        # Success clears history
        cb.record_success("agent-1")
        assert len(cb._failure_history["agent-1"]) == 0


class TestFailureWindowExpiry:
    """Test that failures outside window don't count."""

    def test_old_failures_excluded_from_count(self):
        """Failures outside failure_window don't count toward threshold."""
        cb = CircuitBreaker(
            failure_threshold=2,
            failure_window=1.0,  # 1 second window
        )

        # Record first failure
        cb.record_failure("agent-1")

        # Wait for window to expire
        time.sleep(1.1)

        # Record second failure (first should be expired)
        cb.record_failure("agent-1")

        # Should not open circuit (only 1 failure in window)
        health = cb.get_health_status("agent-1")
        assert health["recent_failures"] == 1
        assert not cb.is_open("agent-1")

    def test_recent_failures_counted_correctly(self):
        """Recent failures within window counted correctly."""
        cb = CircuitBreaker(
            failure_threshold=3,
            failure_window=60.0,  # 60 second window
        )

        # Record 2 failures in quick succession
        cb.record_failure("agent-1")
        time.sleep(0.01)
        cb.record_failure("agent-1")

        health = cb.get_health_status("agent-1")
        assert health["recent_failures"] == 2


class TestConcurrentAdhocAgents:
    """Test behavior with multiple adhoc agents."""

    def test_independent_circuit_state(self):
        """Each adhoc agent has independent circuit state."""
        cb = CircuitBreaker(failure_threshold=2)
        cb.mark_as_adhoc("adhoc-agent-1")
        cb.mark_as_adhoc("adhoc-agent-2")

        # Fail first agent
        cb.record_failure("adhoc-agent-1")
        cb.record_failure("adhoc-agent-1")

        # First agent circuit open, second still closed
        assert cb.is_open("adhoc-agent-1")
        assert not cb.is_open("adhoc-agent-2")

    def test_mixed_adhoc_and_regular_independent(self):
        """Adhoc and regular agents don't interfere."""
        cb = CircuitBreaker(
            failure_threshold=2,
            adhoc_failure_threshold=4,
        )
        cb.mark_as_adhoc("adhoc-agent")

        # Fail regular agent
        cb.record_failure("regular-agent")
        cb.record_failure("regular-agent")

        # Regular circuit open, adhoc still closed
        assert cb.is_open("regular-agent")
        assert not cb.is_open("adhoc-agent")


class TestEdgeCasesAdhoc:
    """Test edge cases specific to adhoc agents."""

    def test_adhoc_with_no_failures(self):
        """Adhoc agent with no failures reports healthy."""
        cb = CircuitBreaker()
        cb.mark_as_adhoc("adhoc-agent")

        health = cb.get_health_status("adhoc-agent")
        assert health["state"] == "closed"
        assert health["failure_count"] == 0
        assert health["recent_failures"] == 0
        assert health["risk_level"] == "low"

    def test_reset_clears_adhoc_marking(self):
        """Circuit reset doesn't clear adhoc marking."""
        cb = CircuitBreaker()
        cb.mark_as_adhoc("adhoc-agent")

        # Reset circuit
        cb.reset("adhoc-agent")

        # Adhoc marking should persist (it's in separate set)
        assert cb._is_adhoc_agent("adhoc-agent")

    def test_reset_all_clears_circuits_not_adhoc_marks(self):
        """reset_all clears circuits but adhoc marks may persist."""
        cb = CircuitBreaker()
        cb.mark_as_adhoc("adhoc-agent")
        cb.record_failure("adhoc-agent")

        # Reset all circuits
        cb.reset_all()

        # Circuit state cleared
        assert not cb.is_open("adhoc-agent")
        # Adhoc marking persists (separate data structure)
        assert cb._is_adhoc_agent("adhoc-agent")


class TestLogging:
    """Test logging behavior for adhoc agents."""

    def test_adhoc_agent_type_in_log_messages(self, caplog):
        """Log messages indicate agent type (adhoc vs regular)."""
        import logging

        caplog.set_level(logging.WARNING)

        cb = CircuitBreaker(
            failure_threshold=2,
            adhoc_failure_threshold=2,
        )
        cb.mark_as_adhoc("adhoc-agent")

        # Open circuit for adhoc agent
        cb.record_failure("adhoc-agent")
        cb.record_failure("adhoc-agent")

        # Check log contains "adhoc agent"
        assert any("adhoc agent" in record.message for record in caplog.records)

    def test_regular_agent_type_in_log_messages(self, caplog):
        """Log messages for regular agents don't say adhoc."""
        import logging

        caplog.set_level(logging.WARNING)

        cb = CircuitBreaker(failure_threshold=2)

        # Open circuit for regular agent
        cb.record_failure("regular-agent")
        cb.record_failure("regular-agent")

        # Check log contains "agent" but not "adhoc agent"
        log_messages = [record.message for record in caplog.records]
        assert any("agent" in msg for msg in log_messages)
        assert not any("adhoc agent" in msg for msg in log_messages)
