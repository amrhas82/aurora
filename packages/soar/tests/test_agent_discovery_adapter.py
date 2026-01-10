"""Tests for agent_discovery adapter in SOAR package.

Tests the adapter layer that bridges ManifestManager (from aurora_cli.agent_discovery)
to SOAR's AgentRegistry interface, enabling SOAR to use the new discovery system.
"""

from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest

from aurora_cli.agent_discovery.manifest import ManifestManager
from aurora_cli.agent_discovery.models import AgentCategory
from aurora_cli.agent_discovery.models import AgentInfo as DiscoveryAgentInfo
from aurora_cli.agent_discovery.models import AgentManifest, ManifestStats
from aurora_soar.agent_registry import AgentInfo as RegistryAgentInfo


class TestManifestManagerAdapter:
    """Test suite for ManifestManager adapter functions."""

    @pytest.fixture
    def sample_discovery_agents(self):
        """Create sample AgentInfo objects from discovery system."""
        return [
            DiscoveryAgentInfo(
                id="qa-test-architect",
                role="Test Architect & Quality Advisor",
                goal="Ensure comprehensive test coverage and quality standards",
                category=AgentCategory.QA,
                skills=["test strategy design", "coverage analysis", "quality gate decisions"],
                when_to_use="Use for test architecture review and quality decisions",
                source_file="/home/user/.claude/agents/qa-test-architect.md",
            ),
            DiscoveryAgentInfo(
                id="full-stack-dev",
                role="Full Stack Developer",
                goal="Implement features and fix bugs across the stack",
                category=AgentCategory.ENG,
                skills=["code implementation", "debugging", "refactoring"],
                when_to_use="Use for code implementation and debugging",
                source_file="/home/user/.claude/agents/full-stack-dev.md",
            ),
            DiscoveryAgentInfo(
                id="orchestrator",
                role="Master Orchestrator",
                goal="Coordinate multi-agent workflows and role switching",
                category=AgentCategory.GENERAL,
                skills=["workflow coordination", "role switching", "multi-agent tasks"],
                when_to_use="Use for workflow coordination and multi-agent tasks",
                source_file="/home/user/.claude/agents/orchestrator.md",
            ),
        ]

    @pytest.fixture
    def sample_manifest(self, sample_discovery_agents):
        """Create a sample AgentManifest for testing."""
        manifest = AgentManifest(
            version="1.0.0",
            sources=["/home/user/.claude/agents"],
            agents=sample_discovery_agents,
            stats=ManifestStats(
                total=len(sample_discovery_agents),
                by_category={"qa": 1, "eng": 1, "general": 1},
                malformed_files=0,
            ),
        )
        return manifest

    @pytest.fixture
    def mock_manifest_manager(self, sample_manifest):
        """Create a mock ManifestManager with sample data."""
        manager = Mock(spec=ManifestManager)
        manager.manifest = sample_manifest
        manager.get_or_refresh.return_value = sample_manifest
        return manager

    def test_load_agents_from_manifest(self, sample_manifest):
        """Test loading agents from a real ManifestManager.

        This test verifies that we can load agents from the discovery system
        and that they can be converted to SOAR's AgentRegistry format.
        """
        # Import the adapter module (this will fail until we create it)
        from aurora_soar.discovery_adapter import convert_agent_info, get_manifest_manager

        # Mock the ManifestManager to return our sample manifest
        with patch("aurora_soar.discovery_adapter.ManifestManager") as MockManager:
            mock_instance = Mock()
            mock_instance.get_or_refresh.return_value = sample_manifest
            MockManager.return_value = mock_instance

            # Get the manifest manager
            manager = get_manifest_manager()
            manifest = manager.get_or_refresh(Path("/tmp/test_manifest.json"))

            # Verify we got agents
            assert manifest is not None
            assert len(manifest.agents) == 3
            assert manifest.stats.total == 3

            # Test converting one agent
            discovery_agent = manifest.agents[0]
            registry_agent = convert_agent_info(discovery_agent)

            # Verify conversion worked
            assert isinstance(registry_agent, RegistryAgentInfo)
            assert registry_agent.id == discovery_agent.id
            assert registry_agent.name == discovery_agent.role
            assert registry_agent.description == discovery_agent.goal

    def test_get_agent_by_id(self, sample_manifest):
        """Test getting an agent by ID using ManifestManager.

        Verifies that we can look up agents by ID and convert them
        to SOAR's AgentRegistry format.
        """
        from aurora_soar.discovery_adapter import get_agent

        # Mock ManifestManager
        with patch("aurora_soar.discovery_adapter.ManifestManager") as MockManager:
            mock_instance = Mock()
            mock_instance.get_or_refresh.return_value = sample_manifest
            MockManager.return_value = mock_instance

            # Test getting agent by ID
            agent = get_agent("qa-test-architect")

            # Verify we got the right agent
            assert agent is not None
            assert isinstance(agent, RegistryAgentInfo)
            assert agent.id == "qa-test-architect"
            assert agent.name == "Test Architect & Quality Advisor"
            assert agent.agent_type == "local"  # All agents from discovery are 'local' type

    def test_get_agent_by_id_not_found(self, sample_manifest):
        """Test getting a non-existent agent returns None."""
        from aurora_soar.discovery_adapter import get_agent

        with patch("aurora_soar.discovery_adapter.ManifestManager") as MockManager:
            mock_instance = Mock()
            mock_instance.get_or_refresh.return_value = sample_manifest
            MockManager.return_value = mock_instance

            # Test getting non-existent agent
            agent = get_agent("non-existent-agent")

            # Verify we got None
            assert agent is None

    def test_list_all_agents(self, sample_manifest):
        """Test listing all agents using ManifestManager.

        Verifies that we can get all agents and convert them to
        SOAR's AgentRegistry format.
        """
        from aurora_soar.discovery_adapter import list_agents

        with patch("aurora_soar.discovery_adapter.ManifestManager") as MockManager:
            mock_instance = Mock()
            mock_instance.get_or_refresh.return_value = sample_manifest
            MockManager.return_value = mock_instance

            # Test listing all agents
            agents = list_agents()

            # Verify we got all agents
            assert len(agents) == 3
            assert all(isinstance(agent, RegistryAgentInfo) for agent in agents)
            assert {agent.id for agent in agents} == {
                "qa-test-architect",
                "full-stack-dev",
                "orchestrator",
            }

    def test_create_fallback_agent(self):
        """Test creating a fallback agent for missing agents.

        Verifies that when an agent is not found, we can create
        a fallback agent similar to AgentRegistry.create_fallback_agent().
        """
        from aurora_soar.discovery_adapter import create_fallback_agent

        # Create fallback agent
        fallback = create_fallback_agent()

        # Verify fallback agent structure
        assert isinstance(fallback, RegistryAgentInfo)
        assert fallback.id == "llm-executor"
        assert fallback.name == "Default LLM Executor"
        assert fallback.agent_type == "local"
        assert "general-purpose" in fallback.capabilities

    def test_convert_agent_info_preserves_fields(self, sample_discovery_agents):
        """Test that convert_agent_info preserves all important fields."""
        from aurora_soar.discovery_adapter import convert_agent_info

        discovery_agent = sample_discovery_agents[0]
        registry_agent = convert_agent_info(discovery_agent)

        # Verify all fields are converted correctly
        assert registry_agent.id == discovery_agent.id
        assert registry_agent.name == discovery_agent.role
        assert registry_agent.description == discovery_agent.goal
        assert registry_agent.agent_type == "local"

        # Capabilities should include skills
        assert len(registry_agent.capabilities) > 0
        for skill in discovery_agent.skills:
            assert skill in registry_agent.capabilities

    def test_convert_agent_info_handles_empty_skills(self):
        """Test that convert_agent_info handles agents with no skills."""
        from aurora_soar.discovery_adapter import convert_agent_info

        # Create agent with no skills
        discovery_agent = DiscoveryAgentInfo(
            id="minimal-agent",
            role="Minimal Agent",
            goal="Basic agent with no skills",
            category=AgentCategory.GENERAL,
        )

        registry_agent = convert_agent_info(discovery_agent)

        # Should still have at least one capability derived from category
        assert isinstance(registry_agent, RegistryAgentInfo)
        assert len(registry_agent.capabilities) > 0

    def test_adapter_caches_manifest_manager(self):
        """Test that the adapter caches the ManifestManager instance.

        Verifies that multiple calls to get_manifest_manager() return
        the same instance to avoid redundant manifest loading.
        """
        from aurora_soar.discovery_adapter import _clear_cache, get_manifest_manager

        # Clear cache before testing to ensure clean state
        _clear_cache()

        with patch("aurora_soar.discovery_adapter.ManifestManager") as MockManager:
            mock_instance = Mock()
            MockManager.return_value = mock_instance

            # Call twice
            manager1 = get_manifest_manager()
            manager2 = get_manifest_manager()

            # Should be the same instance (cached)
            assert manager1 is manager2
            # ManifestManager should only be instantiated once
            assert MockManager.call_count == 1

    def test_get_agent_with_custom_manifest_path(self, sample_manifest):
        """Test getting an agent with a custom manifest path."""
        from aurora_soar.discovery_adapter import _clear_cache, get_agent

        # Clear cache before testing to ensure clean state
        _clear_cache()

        custom_path = Path("/custom/path/manifest.json")

        with patch("aurora_soar.discovery_adapter.ManifestManager") as MockManager:
            mock_instance = Mock()
            mock_instance.get_or_refresh.return_value = sample_manifest
            MockManager.return_value = mock_instance

            # Test with custom path
            agent = get_agent("qa-test-architect", manifest_path=custom_path)

            # Verify the custom path was used
            assert agent is not None
            mock_instance.get_or_refresh.assert_called_with(custom_path)
