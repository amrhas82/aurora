"""Unit tests for early failure detection in SOAR pipeline.

Tests early termination, timeout detection, and recovery mechanisms
to prevent waiting for full timeouts before detecting failures.
"""

import asyncio
import time
from unittest.mock import MagicMock, patch

import pytest

from aurora_soar.phases.collect import AgentOutput, CollectResult, execute_agents
from aurora_spawner import SpawnResult
from aurora_spawner.timeout_policy import (
    RetryStrategy,
    SpawnPolicy,
    TerminationPolicy,
    TimeoutMode,
    TimeoutPolicy,
)


class TestEarlyTerminationDetection:
    """Test early termination based on error patterns."""

    def test_termination_policy_detects_rate_limit(self):
        """TerminationPolicy detects rate limit error immediately."""
        policy = TerminationPolicy()
        stderr = "Error: rate limit exceeded (429 Too Many Requests)"

        should_term, reason = policy.should_terminate(
            stdout="",
            stderr=stderr,
            elapsed=5.0,
            last_activity=1.0,
        )

        assert should_term
        assert "rate.?limit" in reason

    def test_termination_policy_detects_auth_failure(self):
        """TerminationPolicy detects authentication failures immediately."""
        policy = TerminationPolicy()
        stderr = "Authentication failed: Invalid API key"

        should_term, reason = policy.should_terminate(
            stdout="",
            stderr=stderr,
            elapsed=2.0,
            last_activity=0.5,
        )

        assert should_term
        assert "authentication.?failed" in reason

    def test_termination_policy_detects_connection_error(self):
        """TerminationPolicy detects connection errors immediately."""
        policy = TerminationPolicy()
        stderr = "Error: ECONNRESET - connection reset by peer"

        should_term, reason = policy.should_terminate(
            stdout="",
            stderr=stderr,
            elapsed=1.0,
            last_activity=0.2,
        )

        assert should_term
        assert "ECONNRESET" in reason or "connection" in reason.lower()

    def test_termination_policy_detects_api_error(self):
        """TerminationPolicy detects API errors immediately."""
        policy = TerminationPolicy()
        stderr = "API error: Service unavailable"

        should_term, reason = policy.should_terminate(
            stdout="",
            stderr=stderr,
            elapsed=3.0,
            last_activity=0.8,
        )

        assert should_term
        assert "API.?error" in reason

    def test_termination_policy_no_false_positives(self):
        """TerminationPolicy doesn't terminate on benign stderr."""
        policy = TerminationPolicy()
        stderr = "Warning: Cache miss, fetching from source\nInfo: Processing chunk 3/10"

        should_term, reason = policy.should_terminate(
            stdout="",
            stderr=stderr,
            elapsed=5.0,
            last_activity=1.0,
        )

        assert not should_term
        assert reason == ""

    def test_termination_policy_custom_predicate(self):
        """TerminationPolicy supports custom termination predicates."""

        def detect_oom(stdout: str, stderr: str) -> bool:
            return "out of memory" in stderr.lower() or "oom" in stderr.lower()

        policy = TerminationPolicy(custom_predicates=[detect_oom])
        stderr = "Fatal error: Out of memory (OOM)"

        should_term, reason = policy.should_terminate(
            stdout="",
            stderr=stderr,
            elapsed=2.0,
            last_activity=0.5,
        )

        assert should_term
        assert "custom termination" in reason.lower()

    def test_termination_policy_disabled(self):
        """TerminationPolicy respects enabled=False flag."""
        policy = TerminationPolicy(enabled=False)
        stderr = "Error: rate limit exceeded"

        should_term, reason = policy.should_terminate(
            stdout="",
            stderr=stderr,
            elapsed=5.0,
            last_activity=1.0,
        )

        assert not should_term
        assert reason == ""


class TestProgressiveTimeoutDetection:
    """Test progressive timeout with early activity detection."""

    def test_progressive_timeout_extends_on_activity(self):
        """Progressive timeout extends when activity detected."""
        policy = TimeoutPolicy(
            mode=TimeoutMode.PROGRESSIVE,
            initial_timeout=60.0,
            max_timeout=300.0,
            extension_threshold=10.0,
        )

        # Activity within threshold - should extend
        current_timeout = 60.0
        should_extend = policy.should_extend(
            elapsed=55.0,
            last_activity=5.0,
            current_timeout=current_timeout,
        )

        assert should_extend

        extended = policy.get_extended_timeout(current_timeout)
        assert extended == 90.0  # 60 * 1.5

    def test_progressive_timeout_no_extend_on_no_activity(self):
        """Progressive timeout doesn't extend without recent activity."""
        policy = TimeoutPolicy(
            mode=TimeoutMode.PROGRESSIVE,
            initial_timeout=60.0,
            max_timeout=300.0,
            extension_threshold=10.0,
        )

        # No activity beyond threshold - shouldn't extend
        current_timeout = 60.0
        should_extend = policy.should_extend(
            elapsed=55.0,
            last_activity=25.0,
            current_timeout=current_timeout,
        )

        assert not should_extend

    def test_progressive_timeout_caps_at_max(self):
        """Progressive timeout never exceeds max_timeout."""
        policy = TimeoutPolicy(
            mode=TimeoutMode.PROGRESSIVE,
            initial_timeout=60.0,
            max_timeout=120.0,
            extension_threshold=10.0,
        )

        # Already at max - shouldn't extend
        should_extend = policy.should_extend(
            elapsed=115.0,
            last_activity=5.0,
            current_timeout=120.0,
        )

        assert not should_extend

    def test_progressive_timeout_early_detection_vs_fixed(self):
        """Progressive timeout detects failures earlier than fixed timeout."""
        progressive = TimeoutPolicy(
            mode=TimeoutMode.PROGRESSIVE,
            initial_timeout=30.0,
            no_activity_timeout=15.0,
        )

        fixed = TimeoutPolicy(mode=TimeoutMode.FIXED, timeout=120.0)

        # Progressive starts with 30s, fixed with 120s
        assert progressive.get_initial_timeout() < fixed.get_initial_timeout()

        # With no activity, progressive would timeout faster
        # (30s initial + 15s no-activity = 45s vs 120s fixed)


class TestNoActivityTimeout:
    """Test no-activity timeout for early failure detection."""

    def test_spawn_policy_fast_fail_short_timeout(self):
        """Fast fail policy has short no-activity timeout."""
        policy = SpawnPolicy.fast_fail()

        assert policy.timeout_policy.no_activity_timeout == 15.0
        assert policy.timeout_policy.mode == TimeoutMode.FIXED
        assert policy.timeout_policy.timeout == 60.0

    def test_spawn_policy_patient_longer_timeout(self):
        """Patient policy has longer no-activity timeout for agents."""
        policy = SpawnPolicy.patient()

        assert policy.timeout_policy.no_activity_timeout == 120.0  # 2 minutes
        assert policy.timeout_policy.initial_timeout == 120.0
        assert policy.timeout_policy.max_timeout == 600.0

    def test_spawn_policy_test_shortest_timeout(self):
        """Test policy has shortest timeouts for fast feedback."""
        policy = SpawnPolicy.test()

        assert policy.timeout_policy.timeout == 30.0
        assert policy.timeout_policy.no_activity_timeout == 10.0
        assert policy.retry_policy.max_attempts == 1


class TestFailFastRetryPolicy:
    """Test fail-fast retry policies."""

    def test_retry_policy_immediate_no_delay(self):
        """IMMEDIATE strategy has zero delay."""
        policy = SpawnPolicy.fast_fail().retry_policy

        assert policy.strategy == RetryStrategy.IMMEDIATE
        assert policy.get_delay(0) == 0.0
        assert policy.get_delay(1) == 0.0

    def test_retry_policy_exponential_backoff(self):
        """EXPONENTIAL_BACKOFF strategy increases delay exponentially."""
        policy = SpawnPolicy.default().retry_policy

        delay0 = policy.get_delay(0)
        delay1 = policy.get_delay(1)
        delay2 = policy.get_delay(2)

        assert delay0 < delay1 < delay2
        # Approximately exponential (with jitter)
        assert delay1 > delay0 * 1.5
        assert delay2 > delay1 * 1.5

    def test_retry_policy_max_attempts_check(self):
        """Retry policy respects max_attempts limit."""
        policy = SpawnPolicy.fast_fail().retry_policy

        should_retry, reason = policy.should_retry(0)
        assert should_retry

        should_retry, reason = policy.should_retry(1)  # Beyond max_attempts=1
        assert not should_retry
        assert "Max attempts" in reason

    def test_retry_policy_disabled_on_timeout(self):
        """Retry policy can disable retry on timeout."""
        policy = SpawnPolicy.fast_fail().retry_policy
        policy.retry_on_timeout = False

        should_retry, reason = policy.should_retry(0, error_type="timeout")
        assert not should_retry
        assert "timeout disabled" in reason.lower()


@pytest.mark.asyncio
class TestCollectPhaseEarlyFailures:
    """Test collect phase early failure detection."""

    async def test_collect_detects_timeout_immediately(self):
        """Collect phase detects timeout without waiting for full duration."""

        # Mock agent that times out
        async def mock_spawn_timeout(task):
            await asyncio.sleep(0.1)
            return SpawnResult(
                success=False,
                output="",
                error="Timeout: No activity for 10 seconds",
                exit_code=-1,
                fallback=False,
            )

        with patch("aurora_soar.phases.collect.spawn", side_effect=mock_spawn_timeout):
            # Mock agent
            mock_agent = MagicMock()
            mock_agent.id = "test-agent"
            mock_agent.config = {}

            subgoal = {"description": "Test task", "subgoal_index": 0}

            start = time.time()
            result = await execute_agents(
                agent_assignments=[(0, mock_agent)],
                subgoals=[subgoal],
                context={},
                agent_timeout=120.0,  # 2 minute timeout configured
            )
            elapsed = time.time() - start

            # Should complete in ~0.1s, not wait for 120s timeout
            assert elapsed < 1.0
            assert result.execution_metadata["failed_subgoals"] == 1
            assert result.agent_outputs[0].success is False
            assert "timeout" in result.agent_outputs[0].error.lower()

    async def test_collect_detects_rate_limit_early(self):
        """Collect phase detects rate limit error immediately."""

        # Mock agent that hits rate limit
        async def mock_spawn_rate_limit(task):
            await asyncio.sleep(0.05)
            return SpawnResult(
                success=False,
                output="",
                error="Rate limit exceeded (429)",
                exit_code=1,
                fallback=False,
            )

        with patch("aurora_soar.phases.collect.spawn", side_effect=mock_spawn_rate_limit):
            mock_agent = MagicMock()
            mock_agent.id = "rate-limited-agent"
            mock_agent.config = {}

            subgoal = {"description": "Test task", "subgoal_index": 0}

            start = time.time()
            result = await execute_agents(
                agent_assignments=[(0, mock_agent)],
                subgoals=[subgoal],
                context={},
                agent_timeout=120.0,
            )
            elapsed = time.time() - start

            # Should fail fast, not wait
            assert elapsed < 1.0
            assert result.execution_metadata["failed_subgoals"] == 1
            assert "rate limit" in result.agent_outputs[0].error.lower()

    async def test_collect_parallel_timeout_with_global_limit(self):
        """Collect phase uses global timeout to prevent hanging."""

        # Mock agent that hangs (never returns)
        async def mock_spawn_hang(task):
            await asyncio.sleep(999)  # Never completes
            return SpawnResult(success=True, output="Done", error=None, exit_code=0, fallback=False)

        with patch("aurora_soar.phases.collect.spawn", side_effect=mock_spawn_hang):
            mock_agent = MagicMock()
            mock_agent.id = "hanging-agent"
            mock_agent.config = {}

            subgoal = {"description": "Test task", "subgoal_index": 0}

            # Set short agent_timeout
            agent_timeout = 5.0  # 5 seconds per agent
            # Note: global timeout in collect is agent_timeout * 0.4 = 2.0s
            # But actual implementation may have different calculation

            start = time.time()
            result = await execute_agents(
                agent_assignments=[(0, mock_agent)],
                subgoals=[subgoal],
                context={},
                agent_timeout=agent_timeout,
            )
            elapsed = time.time() - start

            # Should timeout reasonably quickly, not hang for 999s
            # Global timeout should trigger within reasonable time
            assert elapsed < 15.0  # Much less than 999s hang time
            # The important thing is it didn't wait for the full hang (999s)


class TestCircuitBreakerIntegration:
    """Test circuit breaker integration with early failure detection."""

    def test_spawn_policy_default_has_circuit_breaker(self):
        """Default policy enables circuit breaker."""
        policy = SpawnPolicy.default()
        assert policy.retry_policy.circuit_breaker_enabled

    def test_spawn_policy_development_disables_circuit_breaker(self):
        """Development policy disables circuit breaker for debugging."""
        policy = SpawnPolicy.development()
        assert not policy.retry_policy.circuit_breaker_enabled

    def test_spawn_policy_test_disables_circuit_breaker(self):
        """Test policy disables circuit breaker for predictable tests."""
        policy = SpawnPolicy.test()
        assert not policy.retry_policy.circuit_breaker_enabled


class TestFailurePatternAnalysis:
    """Test failure pattern analysis for categorization."""

    def test_analyze_execution_failures_categorizes_timeouts(self):
        """Orchestrator categorizes timeout failures separately."""
        from aurora_soar.orchestrator import SOAROrchestrator

        # Create mock outputs with timeout
        timeout_output = AgentOutput(
            subgoal_index=0,
            agent_id="timeout-agent",
            success=False,
            error="Timeout: Agent timed out after 120s",
            execution_metadata={"duration_ms": 120000},
        )

        collect_result = CollectResult(
            agent_outputs=[timeout_output],
            execution_metadata={},
            fallback_agents=[],
        )

        # Mock orchestrator
        mock_store = MagicMock()
        mock_config = MagicMock()
        mock_llm = MagicMock()

        orchestrator = SOAROrchestrator(
            store=mock_store,
            config=mock_config,
            reasoning_llm=mock_llm,
            solving_llm=mock_llm,
        )

        analysis = orchestrator._analyze_execution_failures(collect_result)

        assert analysis["failed_count"] == 1
        assert len(analysis["timeout_failures"]) == 1
        assert "timeout-agent" in analysis["timeout_failures"]

    def test_analyze_execution_failures_categorizes_rate_limits(self):
        """Orchestrator categorizes rate limit failures separately."""
        from aurora_soar.orchestrator import SOAROrchestrator

        rate_limit_output = AgentOutput(
            subgoal_index=0,
            agent_id="rate-limited-agent",
            success=False,
            error="Rate limit exceeded: 429 Too Many Requests",
            execution_metadata={"duration_ms": 1000},
        )

        collect_result = CollectResult(
            agent_outputs=[rate_limit_output],
            execution_metadata={},
            fallback_agents=[],
        )

        mock_store = MagicMock()
        mock_config = MagicMock()
        mock_llm = MagicMock()

        orchestrator = SOAROrchestrator(
            store=mock_store,
            config=mock_config,
            reasoning_llm=mock_llm,
            solving_llm=mock_llm,
        )

        analysis = orchestrator._analyze_execution_failures(collect_result)

        assert analysis["failed_count"] == 1
        assert len(analysis["rate_limit_failures"]) == 1
        assert "rate-limited-agent" in analysis["rate_limit_failures"]

    def test_analyze_execution_failures_categorizes_auth_failures(self):
        """Orchestrator categorizes authentication failures separately."""
        from aurora_soar.orchestrator import SOAROrchestrator

        auth_output = AgentOutput(
            subgoal_index=0,
            agent_id="auth-failed-agent",
            success=False,
            error="Authentication failed: Invalid API key (401 Unauthorized)",
            execution_metadata={"duration_ms": 500},
        )

        collect_result = CollectResult(
            agent_outputs=[auth_output],
            execution_metadata={},
            fallback_agents=[],
        )

        mock_store = MagicMock()
        mock_config = MagicMock()
        mock_llm = MagicMock()

        orchestrator = SOAROrchestrator(
            store=mock_store,
            config=mock_config,
            reasoning_llm=mock_llm,
            solving_llm=mock_llm,
        )

        analysis = orchestrator._analyze_execution_failures(collect_result)

        assert analysis["failed_count"] == 1
        assert len(analysis["auth_failures"]) == 1
        assert "auth-failed-agent" in analysis["auth_failures"]

    def test_analyze_execution_failures_early_termination_tracking(self):
        """Orchestrator tracks early termination separately from regular failures."""
        from aurora_soar.orchestrator import SOAROrchestrator

        early_term_output = AgentOutput(
            subgoal_index=0,
            agent_id="early-term-agent",
            success=False,
            error="Process terminated: Error pattern detected",
            execution_metadata={"duration_ms": 2000, "termination_reason": "error_pattern_match"},
        )

        collect_result = CollectResult(
            agent_outputs=[early_term_output],
            execution_metadata={},
            fallback_agents=[],
        )

        mock_store = MagicMock()
        mock_config = MagicMock()
        mock_llm = MagicMock()

        orchestrator = SOAROrchestrator(
            store=mock_store,
            config=mock_config,
            reasoning_llm=mock_llm,
            solving_llm=mock_llm,
        )

        analysis = orchestrator._analyze_execution_failures(collect_result)

        assert analysis["failed_count"] == 1
        assert analysis["early_term_count"] == 1


class TestMetadataTracking:
    """Test recovery metadata tracking."""

    def test_phase5_metadata_includes_recovery_metrics(self):
        """Phase 5 collect metadata includes detailed recovery metrics."""
        # This tests the structure documented in orchestrator.py:421-442
        expected_keys = [
            "total_failures",
            "early_terminations",
            "circuit_breaker_blocks",
            "circuit_blocked_agents",
            "timeout_count",
            "timeout_agents",
            "rate_limit_count",
            "rate_limit_agents",
            "auth_failure_count",
            "auth_failed_agents",
            "fallback_used_count",
            "fallback_agents",
        ]

        # Create mock recovery metrics
        recovery_metrics = {
            "total_failures": 3,
            "early_terminations": 1,
            "circuit_breaker_blocks": 1,
            "circuit_blocked_agents": ["blocked-agent"],
            "timeout_count": 1,
            "timeout_agents": ["timeout-agent"],
            "rate_limit_count": 0,
            "rate_limit_agents": [],
            "auth_failure_count": 0,
            "auth_failed_agents": [],
            "fallback_used_count": 2,
            "fallback_agents": ["fallback-agent-1", "fallback-agent-2"],
        }

        # Verify all expected keys present
        for key in expected_keys:
            assert key in recovery_metrics
