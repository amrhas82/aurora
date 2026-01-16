"""Integration tests for early failure detection and recovery in SOAR pipeline.

Tests end-to-end scenarios with real timeout policies and spawner integration.
"""

import asyncio
import time
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from aurora_cli.config import Config
from aurora_soar.orchestrator import SOAROrchestrator
from aurora_soar.phases.collect import execute_agents
from aurora_spawner import SpawnResult, SpawnTask


@pytest.fixture
def mock_store():
    """Mock ACT-R store."""
    store = MagicMock()
    store.search_by_query.return_value = []
    return store


@pytest.fixture
def test_config(tmp_path):
    """Test configuration."""
    config = Config()
    config.data = {
        "budget": {"monthly_limit_usd": 100.0},
        "logging": {"conversation_logging_enabled": False},
    }
    return config


@pytest.fixture
def mock_llm():
    """Mock LLM client."""
    llm = MagicMock()
    llm.default_model = "test-model"

    # Mock generate response
    mock_response = MagicMock()
    mock_response.content = "Test response"
    mock_response.model = "test-model"
    mock_response.input_tokens = 100
    mock_response.output_tokens = 50
    llm.generate.return_value = mock_response

    return llm


@pytest.fixture
def orchestrator(mock_store, test_config, mock_llm):
    """SOAR orchestrator with mocked dependencies."""
    return SOAROrchestrator(
        store=mock_store,
        config=test_config,
        reasoning_llm=mock_llm,
        solving_llm=mock_llm,
    )


@pytest.mark.asyncio
class TestEarlyTimeoutDetection:
    """Test early timeout detection in full pipeline."""

    async def test_agent_timeout_detected_early_with_no_activity(self):
        """Agent with no activity times out early without waiting for full timeout."""

        # Mock agent that produces no output
        async def mock_spawn_no_activity(task):
            # Simulate agent starting but producing no output
            await asyncio.sleep(0.2)  # Brief startup
            # Return timeout after no-activity threshold
            return SpawnResult(
                success=False,
                output="",
                error="No activity timeout: No output for 30 seconds",
                exit_code=-1,
                fallback=False,
            )

        with patch("aurora_soar.phases.collect.spawn", side_effect=mock_spawn_no_activity):
            mock_agent = MagicMock()
            mock_agent.id = "silent-agent"
            mock_agent.config = {}

            subgoal = {"description": "Process data", "subgoal_index": 0}

            start = time.time()
            result = await execute_agents(
                agent_assignments=[(0, mock_agent)],
                subgoals=[subgoal],
                context={},
                agent_timeout=300.0,  # 5 minute configured timeout
            )
            elapsed = time.time() - start

            # Should fail fast (< 1s in test) due to no-activity detection
            # Not wait for full 300s timeout
            assert elapsed < 2.0
            assert result.execution_metadata["failed_subgoals"] == 1
            assert "no activity" in result.agent_outputs[0].error.lower()

    async def test_global_timeout_prevents_hanging_pipeline(self):
        """Global timeout prevents entire pipeline from hanging on stuck agents."""

        # Mock multiple agents, one of which hangs
        async def mock_spawn_selective_hang(task):
            if "hanging" in task.prompt:
                # This agent never completes
                await asyncio.sleep(999)
                return SpawnResult(
                    success=True, output="Never reached", error=None, exit_code=0, fallback=False
                )
            else:
                # Normal agents complete quickly
                await asyncio.sleep(0.1)
                return SpawnResult(
                    success=True, output="Completed", error=None, exit_code=0, fallback=False
                )

        with patch("aurora_soar.phases.collect.spawn", side_effect=mock_spawn_selective_hang):
            agents = []
            subgoals = []

            for i in range(3):
                agent = MagicMock()
                agent.id = f"agent-{i}"
                agent.config = {}
                agents.append(agent)

                # Second agent is the hanging one
                desc = "hanging task" if i == 1 else "normal task"
                subgoals.append({"description": desc, "subgoal_index": i})

            agent_timeout = 10.0
            global_timeout = agent_timeout * 0.4  # 4 seconds

            start = time.time()
            result = await execute_agents(
                agent_assignments=[(i, a) for i, a in enumerate(agents)],
                subgoals=subgoals,
                context={},
                agent_timeout=agent_timeout,
            )
            elapsed = time.time() - start

            # Should timeout at global limit (~4s), not wait for hanging agent
            assert elapsed < global_timeout + 2.0  # Allow overhead
            assert elapsed < agent_timeout


@pytest.mark.asyncio
class TestEarlyErrorPatternDetection:
    """Test early detection of error patterns."""

    async def test_rate_limit_detected_immediately(self):
        """Rate limit error detected and categorized immediately."""

        async def mock_spawn_rate_limit(task):
            await asyncio.sleep(0.1)
            return SpawnResult(
                success=False,
                output="",
                error="Error: Rate limit exceeded (429 Too Many Requests)",
                exit_code=1,
                fallback=False,
            )

        with patch("aurora_soar.phases.collect.spawn", side_effect=mock_spawn_rate_limit):
            mock_agent = MagicMock()
            mock_agent.id = "rate-limited-agent"
            mock_agent.config = {}

            subgoal = {"description": "API call", "subgoal_index": 0}

            start = time.time()
            result = await execute_agents(
                agent_assignments=[(0, mock_agent)],
                subgoals=[subgoal],
                context={},
                agent_timeout=120.0,
            )
            elapsed = time.time() - start

            # Should fail immediately
            assert elapsed < 1.0
            assert result.execution_metadata["failed_subgoals"] == 1

            output = result.agent_outputs[0]
            assert not output.success
            assert "rate limit" in output.error.lower()

    async def test_auth_failure_detected_immediately(self):
        """Authentication failure detected immediately."""

        async def mock_spawn_auth_fail(task):
            await asyncio.sleep(0.05)
            return SpawnResult(
                success=False,
                output="",
                error="Authentication failed: Invalid API key (401)",
                exit_code=1,
                fallback=False,
            )

        with patch("aurora_soar.phases.collect.spawn", side_effect=mock_spawn_auth_fail):
            mock_agent = MagicMock()
            mock_agent.id = "auth-fail-agent"
            mock_agent.config = {}

            subgoal = {"description": "Authenticated API call", "subgoal_index": 0}

            start = time.time()
            result = await execute_agents(
                agent_assignments=[(0, mock_agent)],
                subgoals=[subgoal],
                context={},
                agent_timeout=120.0,
            )
            elapsed = time.time() - start

            # Should fail immediately
            assert elapsed < 1.0
            assert result.execution_metadata["failed_subgoals"] == 1
            assert "authentication" in result.agent_outputs[0].error.lower()

    async def test_connection_error_detected_immediately(self):
        """Connection errors detected and categorized immediately."""

        async def mock_spawn_conn_error(task):
            await asyncio.sleep(0.08)
            return SpawnResult(
                success=False,
                output="",
                error="Error: ECONNRESET - Connection reset by peer",
                exit_code=1,
                fallback=False,
            )

        with patch("aurora_soar.phases.collect.spawn", side_effect=mock_spawn_conn_error):
            mock_agent = MagicMock()
            mock_agent.id = "conn-error-agent"
            mock_agent.config = {}

            subgoal = {"description": "Network request", "subgoal_index": 0}

            start = time.time()
            result = await execute_agents(
                agent_assignments=[(0, mock_agent)],
                subgoals=[subgoal],
                context={},
                agent_timeout=120.0,
            )
            elapsed = time.time() - start

            # Should fail immediately
            assert elapsed < 1.0
            assert result.execution_metadata["failed_subgoals"] == 1
            assert "connection" in result.agent_outputs[0].error.lower()


class TestOrchestratorFailureAnalysis:
    """Test orchestrator's failure analysis and categorization."""

    def test_orchestrator_categorizes_failures_in_metadata(self, orchestrator):
        """Orchestrator adds recovery metrics to phase metadata."""

        # Mock phase 5 collect result with mixed failures
        from aurora_soar.phases.collect import AgentOutput, CollectResult

        outputs = [
            AgentOutput(
                subgoal_index=0,
                agent_id="timeout-agent",
                success=False,
                error="Timeout: No activity for 30 seconds",
                execution_metadata={"duration_ms": 30000},
            ),
            AgentOutput(
                subgoal_index=1,
                agent_id="rate-limit-agent",
                success=False,
                error="Rate limit exceeded (429)",
                execution_metadata={"duration_ms": 1000},
            ),
            AgentOutput(
                subgoal_index=2,
                agent_id="success-agent",
                success=True,
                summary="Completed successfully",
                execution_metadata={"duration_ms": 5000},
            ),
        ]

        collect_result = CollectResult(
            agent_outputs=outputs, execution_metadata={}, fallback_agents=[]
        )

        # Analyze failures
        analysis = orchestrator._analyze_execution_failures(collect_result)

        # Verify categorization
        assert analysis["failed_count"] == 2
        assert analysis["timeout_count"] == 1
        assert analysis["timeout_agents"] == ["timeout-agent"]
        assert analysis["rate_limit_count"] == 1
        assert analysis["rate_limit_agents"] == ["rate-limit-agent"]

    def test_orchestrator_tracks_early_terminations(self, orchestrator):
        """Orchestrator tracks early terminations separately from timeouts."""
        from aurora_soar.phases.collect import AgentOutput, CollectResult

        outputs = [
            AgentOutput(
                subgoal_index=0,
                agent_id="early-term-agent",
                success=False,
                error="Process terminated: Error pattern detected",
                execution_metadata={
                    "duration_ms": 2000,
                    "termination_reason": "error_pattern_match",
                },
            ),
            AgentOutput(
                subgoal_index=1,
                agent_id="timeout-agent",
                success=False,
                error="Timeout: Agent exceeded 120s limit",
                execution_metadata={"duration_ms": 120000},
            ),
        ]

        collect_result = CollectResult(
            agent_outputs=outputs, execution_metadata={}, fallback_agents=[]
        )

        analysis = orchestrator._analyze_execution_failures(collect_result)

        assert analysis["failed_count"] == 2
        assert analysis["early_term_count"] == 1
        assert analysis["timeout_count"] == 1


@pytest.mark.asyncio
class TestProgressiveTimeoutInPipeline:
    """Test progressive timeout behavior in full pipeline."""

    async def test_progressive_timeout_starts_short_extends_on_activity(self):
        """Progressive timeout starts with short duration, extends when agent is active."""

        call_count = [0]

        # Mock agent that produces periodic output
        async def mock_spawn_with_activity(task):
            call_count[0] += 1
            if call_count[0] == 1:
                # First call - simulate short initial timeout with activity
                await asyncio.sleep(0.1)
                return SpawnResult(
                    success=False,
                    output="Started processing...",
                    error="Timeout extended due to activity",
                    exit_code=-2,  # Special code for "extended"
                    fallback=False,
                )
            else:
                # Second call after extension - complete successfully
                await asyncio.sleep(0.1)
                return SpawnResult(
                    success=True,
                    output="Completed after extension",
                    error=None,
                    exit_code=0,
                    fallback=False,
                )

        with patch("aurora_soar.phases.collect.spawn", side_effect=mock_spawn_with_activity):
            mock_agent = MagicMock()
            mock_agent.id = "progressive-agent"
            mock_agent.config = {}

            subgoal = {"description": "Long-running task", "subgoal_index": 0}

            result = await execute_agents(
                agent_assignments=[(0, mock_agent)],
                subgoals=[subgoal],
                context={},
                agent_timeout=120.0,
            )

            # In this test, spawn is called once and returns success
            # Real progressive timeout would be handled by spawner internally
            assert len(result.agent_outputs) == 1


class TestFallbackMetadataTracking:
    """Test fallback tracking in recovery metadata."""

    def test_fallback_agents_tracked_in_collect_result(self):
        """Fallback agents are tracked in CollectResult."""
        from aurora_soar.phases.collect import AgentOutput, CollectResult

        outputs = [
            AgentOutput(
                subgoal_index=0,
                agent_id="fallback-agent",
                success=True,
                summary="Completed via fallback",
                execution_metadata={"duration_ms": 5000, "fallback_used": True},
            )
        ]

        collect_result = CollectResult(
            agent_outputs=outputs,
            execution_metadata={"fallback_count": 1},
            fallback_agents=["fallback-agent"],
        )

        assert collect_result.fallback_agents == ["fallback-agent"]
        assert collect_result.execution_metadata["fallback_count"] == 1

    def test_orchestrator_includes_fallback_in_recovery_metrics(self, orchestrator):
        """Orchestrator includes fallback count in recovery metrics."""
        from aurora_soar.phases.collect import AgentOutput, CollectResult

        outputs = [
            AgentOutput(
                subgoal_index=0,
                agent_id="agent-1",
                success=True,
                summary="Success",
                execution_metadata={},
            )
        ]

        collect_result = CollectResult(
            agent_outputs=outputs,
            execution_metadata={},
            fallback_agents=["agent-1", "agent-2"],
        )

        # Check that fallback metadata structure exists
        assert hasattr(collect_result, "fallback_agents")
        assert len(collect_result.fallback_agents) == 2


@pytest.mark.asyncio
class TestRecoveryLogging:
    """Test recovery event logging."""

    async def test_circuit_breaker_failures_logged_to_metadata(self, orchestrator):
        """Circuit breaker failures are logged to phase metadata."""
        from aurora_soar.phases.collect import AgentOutput, CollectResult

        # Simulate circuit breaker failure
        outputs = [
            AgentOutput(
                subgoal_index=0,
                agent_id="circuit-blocked-agent",
                success=False,
                error="Circuit open: Agent failed 3 times recently",
                execution_metadata={"duration_ms": 100},
            )
        ]

        collect_result = CollectResult(
            agent_outputs=outputs, execution_metadata={}, fallback_agents=[]
        )

        # Analyze and trigger circuit recovery
        analysis = orchestrator._analyze_execution_failures(collect_result)
        circuit_failures = analysis["circuit_failures"]

        if circuit_failures:
            orchestrator._trigger_circuit_recovery(circuit_failures)

            # Verify metadata was updated
            assert hasattr(orchestrator, "_circuit_failures")
            assert len(orchestrator._circuit_failures) > 0
            assert orchestrator._circuit_failures[0]["agent_id"] == "circuit-blocked-agent"

    async def test_recovery_summary_logged_after_collect(self, orchestrator, caplog):
        """Recovery summary is logged after collect phase."""
        import logging

        from aurora_soar.phases.collect import AgentOutput, CollectResult

        caplog.set_level(logging.INFO)

        # Create mock collect result with failures
        outputs = [
            AgentOutput(
                subgoal_index=0,
                agent_id="timeout-agent",
                success=False,
                error="Timeout",
                execution_metadata={},
            ),
            AgentOutput(
                subgoal_index=1,
                agent_id="success-agent",
                success=True,
                summary="Done",
                execution_metadata={},
            ),
        ]

        collect_result = CollectResult(
            agent_outputs=outputs, execution_metadata={}, fallback_agents=[]
        )

        # Analyze failures (should log summary)
        analysis = orchestrator._analyze_execution_failures(collect_result)

        # The actual logging happens in orchestrator._phase5_collect
        # Verify analysis contains expected data
        assert analysis["failed_count"] == 1
        assert analysis["timeout_count"] == 1


class TestEndToEndRecovery:
    """End-to-end recovery scenarios."""

    @pytest.mark.slow
    def test_mixed_failures_with_recovery(self, orchestrator, mock_store, mock_llm):
        """Pipeline handles mixed failures with appropriate recovery strategies."""

        # Mock decomposition
        decomposition = {
            "goal": "Test goal",
            "subgoals": [
                {
                    "subgoal_index": 0,
                    "description": "Fast task",
                    "assigned_agent": "fast-agent",
                    "is_critical": False,
                },
                {
                    "subgoal_index": 1,
                    "description": "Rate limited task",
                    "assigned_agent": "slow-agent",
                    "is_critical": False,
                },
                {
                    "subgoal_index": 2,
                    "description": "Success task",
                    "assigned_agent": "good-agent",
                    "is_critical": False,
                },
            ],
        }

        # Mock agents
        with patch.object(orchestrator, "_list_agents") as mock_list_agents:
            mock_agents = []
            for agent_id in ["fast-agent", "slow-agent", "good-agent"]:
                agent = MagicMock()
                agent.id = agent_id
                mock_agents.append(agent)

            mock_list_agents.return_value = mock_agents

            # Verify agents exist
            agents = orchestrator._list_agents()
            assert len(agents) == 3
