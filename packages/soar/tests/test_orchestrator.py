"""Tests for SOAR orchestrator."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from aurora_soar.orchestrator import SOAROrchestrator

# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def mock_store():
    """Mock Store for testing."""
    store = MagicMock()
    return store


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
def mock_config():
    """Mock Config for testing."""
    config = MagicMock()
    config.budget = MagicMock()
    config.budget.max_cost_usd = 1.0
    return config


@pytest.fixture
def mock_llm():
    """Mock LLMClient for testing."""
    llm = MagicMock()
    llm.generate = AsyncMock(return_value="Mock response")
    return llm


@pytest.fixture
def orchestrator(mock_store, mock_agent_registry, mock_config, mock_llm):
    """Create SOAROrchestrator instance for testing."""
    return SOAROrchestrator(
        store=mock_store,
        config=mock_config,
        reasoning_llm=mock_llm,
        solving_llm=mock_llm,
        agent_registry=mock_agent_registry,
    )


# ============================================================================
# Smoke Tests
# ============================================================================


def test_imports():
    """Test that basic imports work."""
    from aurora_soar import orchestrator
    from aurora_soar.orchestrator import SOAROrchestrator

    assert orchestrator is not None
    assert SOAROrchestrator is not None


def test_orchestrator_creation(orchestrator):
    """Test that SOAROrchestrator can be created."""
    assert orchestrator is not None
    assert hasattr(orchestrator, "store")
    assert hasattr(orchestrator, "agent_registry")


# ============================================================================
# Agent Discovery Integration Tests (Task 2.3)
# ============================================================================


def test_orchestrator_uses_manifest_manager(mock_store, mock_config, mock_llm):
    """Test that orchestrator can use ManifestManager instead of AgentRegistry.

    Verifies that when no agent_registry is provided, the orchestrator
    initializes using the discovery_adapter's ManifestManager.
    """
    from pathlib import Path
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
            skills=["testing"],
        )
    ]

    sample_manifest = AgentManifest(
        version="1.0.0",
        sources=["/home/user/.aurora/agents"],
        agents=sample_agents,
        stats=ManifestStats(total=1, by_category={"eng": 1}, malformed_files=0),
    )

    # Mock the discovery adapter
    with patch("aurora_soar.discovery_adapter.ManifestManager") as MockManager:
        mock_instance = Mock()
        mock_instance.get_or_refresh.return_value = sample_manifest
        MockManager.return_value = mock_instance

        # Create orchestrator with agent_registry=None (will use discovery)
        orchestrator = SOAROrchestrator(
            store=mock_store,
            config=mock_config,
            reasoning_llm=mock_llm,
            solving_llm=mock_llm,
            agent_registry=None,  # Should trigger discovery_adapter usage
        )

        # Verify orchestrator uses discovery adapter
        assert orchestrator._use_discovery is True
        assert hasattr(orchestrator, "_manifest_manager")
        # When agent_registry is None, orchestrator should use discovery_adapter functions


def test_orchestrator_fallback_agent_from_discovery(mock_store, mock_config, mock_llm):
    """Test that orchestrator can create fallback agent using discovery system.

    Verifies that when an agent is not found, the orchestrator can use
    the discovery adapter's fallback agent creation.
    """
    from unittest.mock import Mock, patch

    from aurora_cli.agent_discovery.models import AgentManifest, ManifestStats

    # Create empty manifest (no agents)
    empty_manifest = AgentManifest(
        version="1.0.0",
        sources=[],
        agents=[],
        stats=ManifestStats(total=0, by_category={}, malformed_files=0),
    )

    with patch("aurora_soar.discovery_adapter.ManifestManager") as MockManager:
        mock_instance = Mock()
        mock_instance.get_or_refresh.return_value = empty_manifest
        MockManager.return_value = mock_instance

        # Create orchestrator with agent_registry=None
        orchestrator = SOAROrchestrator(
            store=mock_store,
            config=mock_config,
            reasoning_llm=mock_llm,
            solving_llm=mock_llm,
            agent_registry=None,
        )

        # Test that fallback agent can be created from discovery
        fallback = orchestrator._get_or_create_fallback_agent()
        assert fallback is not None
        assert fallback.id == "llm-executor"
        assert fallback.name == "Default LLM Executor"
