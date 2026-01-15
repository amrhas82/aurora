"""Tests for AgentRegistry deprecation and migration to ManifestManager.

This test module verifies that:
1. AgentRegistry raises DeprecationWarning when instantiated
2. ManifestManager (via discovery_adapter) works without warnings
3. Both systems provide equivalent results (for migration validation)

Migration Path:
    Old approach (deprecated):
        from aurora_soar.agent_registry import AgentRegistry
        registry = AgentRegistry()
        agent = registry.get(agent_id)

    New approach:
        from aurora_soar.discovery_adapter import get_agent, list_agents
        agent = get_agent(agent_id)  # Uses ManifestManager internally
        all_agents = list_agents()
"""

import warnings
from unittest.mock import Mock, patch

from aurora_cli.agent_discovery.models import AgentCategory, AgentInfo, AgentManifest, ManifestStats
from aurora_soar.agent_registry import AgentInfo as RegistryAgentInfo
from aurora_soar.agent_registry import AgentRegistry


class TestAgentRegistryDeprecation:
    """Test suite for AgentRegistry deprecation warnings."""

    def test_agent_registry_shows_deprecation_warning(self):
        """Test that AgentRegistry.__init__() raises DeprecationWarning.

        This verifies that users are warned when using the deprecated API.
        """
        with warnings.catch_warnings(record=True) as w:
            # Enable all warnings
            warnings.simplefilter("always")

            # Create AgentRegistry (should trigger warning)
            AgentRegistry()

            # Verify warning was raised
            assert len(w) == 1
            assert issubclass(w[0].category, DeprecationWarning)
            assert "AgentRegistry is deprecated" in str(w[0].message)
            assert "ManifestManager" in str(w[0].message)

    def test_discovery_adapter_no_warning(self):
        """Test that discovery_adapter functions don't raise warnings.

        This verifies that the new API works without deprecation warnings.
        """
        from aurora_soar.discovery_adapter import _clear_cache, get_agent, list_agents

        # Clear cache to ensure clean state
        _clear_cache()

        # Create mock manifest
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
            sources=["/test/agents"],
            agents=sample_agents,
            stats=ManifestStats(total=1, by_category={"eng": 1}, malformed_files=0),
        )

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")

            # Mock ManifestManager
            with patch("aurora_soar.discovery_adapter.ManifestManager") as MockManager:
                mock_instance = Mock()
                mock_instance.get_or_refresh.return_value = sample_manifest
                MockManager.return_value = mock_instance

                # Use discovery adapter (should NOT trigger warning)
                list_agents()
                get_agent("test-agent")

                # Verify no warnings were raised
                deprecation_warnings = [x for x in w if issubclass(x.category, DeprecationWarning)]
                assert len(deprecation_warnings) == 0, (
                    f"Expected no DeprecationWarnings, but got: "
                    f"{[str(x.message) for x in deprecation_warnings]}"
                )

    def test_registry_and_discovery_equivalent_results(self):
        """Test that AgentRegistry and discovery_adapter provide equivalent results.

        This validates that migrating from AgentRegistry to ManifestManager
        produces the same agent data, ensuring backward compatibility.
        """
        from aurora_soar.discovery_adapter import convert_agent_info

        # Create a discovery system AgentInfo
        discovery_agent = AgentInfo(
            id="test-agent",
            role="Test Agent",
            goal="Execute test tasks",
            category=AgentCategory.ENG,
            skills=["testing", "code-analysis"],
        )

        # Convert to registry format
        registry_agent = convert_agent_info(discovery_agent)

        # Verify fields match
        assert registry_agent.id == discovery_agent.id
        assert registry_agent.name == discovery_agent.role
        assert registry_agent.description == discovery_agent.goal
        assert registry_agent.agent_type == "local"

        # Verify capabilities include all skills
        for skill in discovery_agent.skills:
            assert skill in registry_agent.capabilities

    def test_migration_guide_in_docstring(self):
        """Test that AgentRegistry has migration guide in module docstring."""
        import aurora_soar.agent_registry as registry_module

        module_doc = registry_module.__doc__
        assert module_doc is not None
        assert "DEPRECATION NOTICE" in module_doc
        assert "Migration Guide" in module_doc
        assert "ManifestManager" in module_doc
        assert "discovery_adapter" in module_doc

    def test_registry_list_all_vs_discovery_list_agents(self):
        """Compare AgentRegistry.list_all() with discovery_adapter.list_agents().

        Verifies that both methods return equivalent agent lists when
        given the same data source.
        """
        from aurora_soar.discovery_adapter import _clear_cache, list_agents

        # Clear cache
        _clear_cache()

        # Create sample discovery agents
        discovery_agents = [
            AgentInfo(
                id="agent-1",
                role="Agent One",
                goal="First agent",
                category=AgentCategory.ENG,
                skills=["skill-1"],
            ),
            AgentInfo(
                id="agent-2",
                role="Agent Two",
                goal="Second agent",
                category=AgentCategory.QA,
                skills=["skill-2"],
            ),
        ]

        sample_manifest = AgentManifest(
            version="1.0.0",
            sources=["/test"],
            agents=discovery_agents,
            stats=ManifestStats(total=2, by_category={"eng": 1, "qa": 1}, malformed_files=0),
        )

        # Suppress deprecation warning for AgentRegistry
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)

            # Create AgentRegistry with same agents
            registry = AgentRegistry()
            for da in discovery_agents:
                registry_agent = RegistryAgentInfo(
                    id=da.id,
                    name=da.role,
                    description=da.goal,
                    capabilities=da.skills,
                    agent_type="local",
                )
                registry.register(registry_agent)

            # Mock discovery adapter
            with patch("aurora_soar.discovery_adapter.ManifestManager") as MockManager:
                mock_instance = Mock()
                mock_instance.get_or_refresh.return_value = sample_manifest
                MockManager.return_value = mock_instance

                # Get agents from both systems
                registry_agents = registry.list_all()
                discovery_list = list_agents()

                # Verify same number of agents
                assert len(registry_agents) == len(discovery_list)

                # Verify IDs match
                registry_ids = {a.id for a in registry_agents}
                discovery_ids = {a.id for a in discovery_list}
                assert registry_ids == discovery_ids
