"""Tests for early failure detection and recovery in SOAR orchestrator."""

from unittest.mock import Mock, patch

import pytest

from aurora_soar.orchestrator import SOAROrchestrator
from aurora_soar.phases.collect import AgentOutput, CollectResult


@pytest.fixture
def mock_store():
    """Create mock store."""
    store = Mock()
    store.search = Mock(return_value=[])
    return store


@pytest.fixture
def mock_config():
    """Create mock config."""
    return {
        "budget": {"monthly_limit_usd": 100.0},
        "logging": {"conversation_logging_enabled": False},
    }


@pytest.fixture
def mock_llm():
    """Create mock LLM client."""
    llm = Mock()
    llm.default_model = "mock-model"
    llm.generate = Mock()
    return llm


@pytest.fixture
def orchestrator(mock_store, mock_config, mock_llm):
    """Create orchestrator for testing."""
    return SOAROrchestrator(
        store=mock_store,
        config=mock_config,
        reasoning_llm=mock_llm,
        solving_llm=mock_llm,
        agent_registry=None,
    )


def test_circuit_breaker_recovery_triggered(orchestrator):
    """Test that circuit breaker failures trigger recovery procedures."""
    # Create mock agent outputs with circuit breaker failure
    outputs = [
        AgentOutput(
            subgoal_index=0,
            agent_id="test-agent",
            success=False,
            error="Circuit open: 2 failures, retry in 120s",
            execution_metadata={},
        ),
    ]

    result = CollectResult(
        agent_outputs=outputs,
        execution_metadata={},
        fallback_agents=[],
    )

    # Simulate phase 5 processing
    with patch.object(orchestrator, "_trigger_circuit_recovery") as mock_recovery:
        # Mock the _phase5_collect to return our result
        with patch.object(orchestrator, "_phase5_collect", return_value=result):
            # Mock other phases
            with patch.object(
                orchestrator,
                "_phase1_assess",
                return_value={"complexity": "MEDIUM"},
            ):
                with patch.object(
                    orchestrator,
                    "_phase2_retrieve",
                    return_value={"code_chunks": [], "reasoning_chunks": []},
                ):
                    with patch.object(
                        orchestrator,
                        "_phase3_decompose",
                        return_value={
                            "decomposition": {"subgoals": [{"description": "test"}]},
                            "subgoals_total": 1,
                        },
                    ):
                        with patch(
                            "aurora_soar.phases.verify.verify_lite",
                            return_value=(True, [(0, Mock(id="test-agent"))], []),
                        ):
                            with patch.object(orchestrator, "_phase6_synthesize"):
                                with patch.object(orchestrator, "_phase7_record"):
                                    with patch.object(
                                        orchestrator,
                                        "_phase8_respond",
                                        return_value={},
                                    ):
                                        try:
                                            orchestrator.execute("test query")
                                        except Exception:
                                            pass

        # Verify recovery was triggered
        mock_recovery.assert_called_once_with(["test-agent"])


def test_early_termination_tracking(orchestrator):
    """Test that early terminations are tracked in metadata."""
    # Create mock agent outputs with early termination
    outputs = [
        AgentOutput(
            subgoal_index=0,
            agent_id="test-agent",
            success=False,
            error="Killed: rate limit detected",
            execution_metadata={"termination_reason": "rate_limit_pattern"},
        ),
    ]

    result = CollectResult(
        agent_outputs=outputs,
        execution_metadata={},
        fallback_agents=[],
    )

    # Simulate phase 5 processing
    with patch.object(orchestrator, "_phase5_collect", return_value=result):
        with patch.object(orchestrator, "_phase1_assess", return_value={"complexity": "MEDIUM"}):
            with patch.object(
                orchestrator,
                "_phase2_retrieve",
                return_value={"code_chunks": [], "reasoning_chunks": []},
            ):
                with patch.object(
                    orchestrator,
                    "_phase3_decompose",
                    return_value={
                        "decomposition": {"subgoals": [{"description": "test"}]},
                        "subgoals_total": 1,
                    },
                ):
                    with patch(
                        "aurora_soar.phases.verify.verify_lite",
                        return_value=(True, [(0, Mock(id="test-agent"))], []),
                    ):
                        with patch.object(orchestrator, "_phase6_synthesize"):
                            with patch.object(orchestrator, "_phase7_record"):
                                with patch.object(orchestrator, "_phase8_respond", return_value={}):
                                    try:
                                        orchestrator.execute("test query")
                                    except Exception:
                                        pass

    # Verify metadata includes early termination tracking
    metadata = orchestrator._phase_metadata.get("phase5_collect", {})
    assert "recovery_metrics" in metadata
    assert metadata["recovery_metrics"]["early_terminations"] == 1


def test_timeout_failure_tracking(orchestrator):
    """Test that timeout failures are tracked separately."""
    # Create mock agent outputs with timeout
    outputs = [
        AgentOutput(
            subgoal_index=0,
            agent_id="test-agent",
            success=False,
            error="Timeout after 300s",
            execution_metadata={},
        ),
    ]

    result = CollectResult(
        agent_outputs=outputs,
        execution_metadata={},
        fallback_agents=[],
    )

    # Simulate phase 5 processing
    with patch.object(orchestrator, "_phase5_collect", return_value=result):
        with patch.object(orchestrator, "_phase1_assess", return_value={"complexity": "MEDIUM"}):
            with patch.object(
                orchestrator,
                "_phase2_retrieve",
                return_value={"code_chunks": [], "reasoning_chunks": []},
            ):
                with patch.object(
                    orchestrator,
                    "_phase3_decompose",
                    return_value={
                        "decomposition": {"subgoals": [{"description": "test"}]},
                        "subgoals_total": 1,
                    },
                ):
                    with patch(
                        "aurora_soar.phases.verify.verify_lite",
                        return_value=(True, [(0, Mock(id="test-agent"))], []),
                    ):
                        with patch.object(orchestrator, "_phase6_synthesize"):
                            with patch.object(orchestrator, "_phase7_record"):
                                with patch.object(orchestrator, "_phase8_respond", return_value={}):
                                    try:
                                        orchestrator.execute("test query")
                                    except Exception:
                                        pass

    # Verify metadata includes timeout tracking
    metadata = orchestrator._phase_metadata.get("phase5_collect", {})
    assert "recovery_metrics" in metadata
    assert metadata["recovery_metrics"]["timeout_failures"] == ["test-agent"]


def test_recovery_metadata_in_final_output(orchestrator):
    """Test that recovery metrics appear in final metadata."""
    # Trigger circuit breaker recovery
    orchestrator._query_id = "test-query"
    orchestrator._trigger_circuit_recovery(["agent-1", "agent-2"])

    # Build metadata
    orchestrator._start_time = 0
    orchestrator._total_cost = 0.0
    orchestrator._token_usage = {"input": 0, "output": 0}
    orchestrator._query = "test"

    metadata = orchestrator._build_metadata()

    # Verify recovery section exists
    assert "recovery" in metadata
    assert metadata["recovery"]["circuit_breaker_triggered"] is True
    assert metadata["recovery"]["total_circuit_failures"] == 2
    assert len(metadata["recovery"]["circuit_failures"]) == 2
