"""Tests for SOAR route phase (agent assignment)."""

from unittest.mock import MagicMock

import pytest

from aurora_soar.phases.route import route_subgoals

# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def mock_agent_registry():
    """Mock AgentRegistry for testing."""
    registry = MagicMock()

    # Mock an agent
    agent = MagicMock()
    agent.id = "test-agent"
    agent.name = "Test Agent"
    agent.capabilities = ["testing"]

    registry.list_agents.return_value = [agent]
    registry.get_agent.return_value = agent

    return registry


@pytest.fixture
def mock_decomposition():
    """Mock DecompositionResult for testing."""
    decomp = MagicMock()
    decomp.subgoals = [{"subgoal_index": 0, "description": "Test subgoal", "is_critical": True}]
    decomp.execution_strategy = {
        "mode": "parallel",
        "dependency_graph": {"0": []},
    }
    return decomp


# ============================================================================
# Smoke Tests
# ============================================================================


def test_imports():
    """Test that basic imports work."""
    from aurora_soar.phases import route
    from aurora_soar.phases.route import route_subgoals

    assert route is not None
    assert route_subgoals is not None


# ============================================================================
# Agent Discovery Integration Tests (Task 2.4)
# ============================================================================


def test_route_with_manifest_manager():
    """Test that route phase can work with agent_registry=None using discovery.

    Verifies that when agent_registry is None, the route phase uses
    discovery_adapter to lookup agents.
    """
    from unittest.mock import Mock, patch

    from aurora_cli.agent_discovery.models import (
        AgentCategory,
        AgentInfo,
        AgentManifest,
        ManifestStats,
    )

    # Create sample agents for discovery system
    sample_agents = [
        AgentInfo(
            id="test-agent",
            role="Test Agent",
            goal="Execute test tasks",
            category=AgentCategory.ENG,
            skills=["testing", "code-analysis"],
        ),
        AgentInfo(
            id="llm-executor",
            role="Default LLM Executor",
            goal="Fallback agent for general tasks",
            category=AgentCategory.GENERAL,
            skills=["reasoning", "general-purpose"],
        ),
    ]

    sample_manifest = AgentManifest(
        version="1.0.0",
        sources=["/home/user/.aurora/agents"],
        agents=sample_agents,
        stats=ManifestStats(total=2, by_category={"eng": 1, "general": 1}, malformed_files=0),
    )

    # Create decomposition
    decomposition = {
        "goal": "Test goal",
        "subgoals": [
            {
                "subgoal_index": 0,
                "description": "Test subgoal",
                "suggested_agent": "test-agent",
                "is_critical": True,
                "depends_on": [],
            }
        ],
        "execution_order": [
            {
                "phase": 1,
                "subgoals": [0],
                "reasoning": "Execute test subgoal",
            }
        ],
        "expected_tools": ["test-tool"],
    }

    # Mock the discovery adapter
    with patch("aurora_soar.phases.route.discovery_adapter") as mock_adapter:
        # Mock list_agents and get_agent
        from aurora_soar.agent_registry import AgentInfo as RegistryAgentInfo

        registry_agent = RegistryAgentInfo(
            id="test-agent",
            name="Test Agent",
            description="Execute test tasks",
            capabilities=["testing", "code-analysis"],
            agent_type="local",
        )

        mock_adapter.get_agent.return_value = registry_agent
        mock_adapter.list_agents.return_value = [registry_agent]

        # Call route_subgoals with agent_registry=None
        result = route_subgoals(decomposition, agent_registry=None)

        # Verify routing worked
        assert result is not None
        assert len(result.agent_assignments) == 1
        assert result.agent_assignments[0][0] == 0  # subgoal index
        assert result.agent_assignments[0][1].id == "test-agent"

        # Verify discovery adapter was called
        mock_adapter.get_agent.assert_called_with("test-agent")
