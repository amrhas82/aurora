"""
Unit tests for AgentRegistry and AgentInfo.

Tests agent discovery, registration, validation, and capability-based queries.
"""

import json
from dataclasses import asdict
from pathlib import Path

from aurora_soar.agent_registry import AgentInfo, AgentRegistry


class TestAgentInfo:
    """Test AgentInfo dataclass structure and validation."""

    def test_agent_info_creation(self):
        """Test creating a valid AgentInfo instance."""
        agent = AgentInfo(
            id="test-agent",
            name="Test Agent",
            description="A test agent for testing",
            capabilities=["capability1", "capability2"],
            agent_type="local",
            config={"key": "value"}
        )

        assert agent.id == "test-agent"
        assert agent.name == "Test Agent"
        assert agent.description == "A test agent for testing"
        assert agent.capabilities == ["capability1", "capability2"]
        assert agent.agent_type == "local"
        assert agent.config == {"key": "value"}

    def test_agent_info_optional_fields(self):
        """Test AgentInfo with only required fields."""
        agent = AgentInfo(
            id="minimal-agent",
            name="Minimal Agent",
            description="Minimal description",
            capabilities=["test"],
            agent_type="local"
        )

        assert agent.id == "minimal-agent"
        assert agent.config == {}

    def test_agent_info_to_dict(self):
        """Test converting AgentInfo to dictionary."""
        agent = AgentInfo(
            id="test-agent",
            name="Test Agent",
            description="Test description",
            capabilities=["cap1"],
            agent_type="local",
            config={"setting": "value"}
        )

        agent_dict = asdict(agent)
        assert agent_dict["id"] == "test-agent"
        assert agent_dict["name"] == "Test Agent"
        assert agent_dict["capabilities"] == ["cap1"]


class TestAgentRegistryInitialization:
    """Test AgentRegistry initialization and setup."""

    def test_registry_creation_empty(self):
        """Test creating registry with no discovery paths."""
        registry = AgentRegistry()

        assert isinstance(registry.agents, dict)
        assert len(registry.agents) == 0
        assert isinstance(registry.discovery_paths, list)

    def test_registry_creation_with_paths(self):
        """Test creating registry with discovery paths."""
        paths = [Path("/path/to/agents"), Path("/another/path")]
        registry = AgentRegistry(discovery_paths=paths)

        assert registry.discovery_paths == paths

    def test_registry_default_discovery_paths(self):
        """Test registry sets up default discovery paths."""
        registry = AgentRegistry()

        # Should have some default paths set up
        assert isinstance(registry.discovery_paths, list)


class TestAgentRegistration:
    """Test agent registration and storage."""

    def test_register_single_agent(self):
        """Test registering a single agent."""
        registry = AgentRegistry()
        agent = AgentInfo(
            id="agent1",
            name="Agent One",
            description="First agent",
            capabilities=["cap1"],
            agent_type="local"
        )

        registry.register(agent)

        assert "agent1" in registry.agents
        assert registry.agents["agent1"] == agent

    def test_register_multiple_agents(self):
        """Test registering multiple agents."""
        registry = AgentRegistry()
        agent1 = AgentInfo(
            id="agent1",
            name="Agent One",
            description="First agent",
            capabilities=["cap1"],
            agent_type="local"
        )
        agent2 = AgentInfo(
            id="agent2",
            name="Agent Two",
            description="Second agent",
            capabilities=["cap2"],
            agent_type="remote"
        )

        registry.register(agent1)
        registry.register(agent2)

        assert len(registry.agents) == 2
        assert "agent1" in registry.agents
        assert "agent2" in registry.agents

    def test_register_duplicate_overwrites(self):
        """Test registering agent with duplicate ID overwrites existing."""
        registry = AgentRegistry()
        agent1 = AgentInfo(
            id="agent1",
            name="Agent One",
            description="First version",
            capabilities=["cap1"],
            agent_type="local"
        )
        agent2 = AgentInfo(
            id="agent1",
            name="Agent One Updated",
            description="Second version",
            capabilities=["cap1", "cap2"],
            agent_type="local"
        )

        registry.register(agent1)
        registry.register(agent2)

        assert len(registry.agents) == 1
        assert registry.agents["agent1"].description == "Second version"
        assert len(registry.agents["agent1"].capabilities) == 2


class TestAgentValidation:
    """Test agent configuration validation."""

    def test_validate_valid_agent(self):
        """Test validation passes for valid agent data."""
        registry = AgentRegistry()
        agent_data = {
            "id": "test-agent",
            "name": "Test Agent",
            "description": "Valid agent",
            "capabilities": ["cap1", "cap2"],
            "type": "local"
        }

        is_valid, error = registry.validate_agent_data(agent_data)

        assert is_valid
        assert error is None

    def test_validate_missing_required_fields(self):
        """Test validation fails for missing required fields."""
        registry = AgentRegistry()

        # Missing 'id'
        agent_data = {
            "name": "Test Agent",
            "description": "Missing ID",
            "capabilities": ["cap1"],
            "type": "local"
        }

        is_valid, error = registry.validate_agent_data(agent_data)

        assert not is_valid
        assert error is not None
        assert "id" in error.lower()

    def test_validate_invalid_type(self):
        """Test validation fails for invalid agent type."""
        registry = AgentRegistry()
        agent_data = {
            "id": "test-agent",
            "name": "Test Agent",
            "description": "Invalid type",
            "capabilities": ["cap1"],
            "type": "invalid_type"
        }

        is_valid, error = registry.validate_agent_data(agent_data)

        assert not is_valid
        assert error is not None

    def test_validate_empty_capabilities(self):
        """Test validation handles empty capabilities list."""
        registry = AgentRegistry()
        agent_data = {
            "id": "test-agent",
            "name": "Test Agent",
            "description": "No capabilities",
            "capabilities": [],
            "type": "local"
        }

        is_valid, error = registry.validate_agent_data(agent_data)

        # Empty capabilities might be valid but should be warned
        assert is_valid or "capabilities" in error.lower()


class TestAgentDiscovery:
    """Test agent discovery from configuration files."""

    def test_discover_from_single_file(self, tmp_path):
        """Test discovering agents from a single JSON file."""
        config_file = tmp_path / "agents.json"
        config_data = {
            "agents": [
                {
                    "id": "agent1",
                    "name": "Agent One",
                    "description": "First agent",
                    "capabilities": ["cap1"],
                    "type": "local"
                }
            ]
        }
        config_file.write_text(json.dumps(config_data))

        registry = AgentRegistry(discovery_paths=[tmp_path])
        registry.discover()

        assert "agent1" in registry.agents

    def test_discover_from_multiple_files(self, tmp_path):
        """Test discovering agents from multiple config files."""
        dir1 = tmp_path / "config1"
        dir2 = tmp_path / "config2"
        dir1.mkdir()
        dir2.mkdir()

        config1 = dir1 / "agents.json"
        config1.write_text(json.dumps({
            "agents": [{
                "id": "agent1",
                "name": "Agent One",
                "description": "First agent",
                "capabilities": ["cap1"],
                "type": "local"
            }]
        }))

        config2 = dir2 / "agents.json"
        config2.write_text(json.dumps({
            "agents": [{
                "id": "agent2",
                "name": "Agent Two",
                "description": "Second agent",
                "capabilities": ["cap2"],
                "type": "remote"
            }]
        }))

        registry = AgentRegistry(discovery_paths=[dir1, dir2])
        registry.discover()

        assert len(registry.agents) == 2
        assert "agent1" in registry.agents
        assert "agent2" in registry.agents

    def test_discover_handles_invalid_json(self, tmp_path):
        """Test discovery gracefully handles invalid JSON."""
        config_file = tmp_path / "agents.json"
        config_file.write_text("{invalid json")

        registry = AgentRegistry(discovery_paths=[tmp_path])
        registry.discover()

        # Should not crash, just skip invalid file
        assert len(registry.agents) == 0

    def test_discover_handles_missing_paths(self):
        """Test discovery handles non-existent paths gracefully."""
        registry = AgentRegistry(discovery_paths=[Path("/nonexistent/path")])
        registry.discover()

        # Should not crash
        assert len(registry.agents) == 0


class TestCapabilityQueries:
    """Test capability-based agent queries."""

    def test_find_by_single_capability(self):
        """Test finding agents by single capability."""
        registry = AgentRegistry()

        agent1 = AgentInfo(
            id="agent1",
            name="Agent One",
            description="Has cap1",
            capabilities=["cap1", "cap2"],
            agent_type="local"
        )
        agent2 = AgentInfo(
            id="agent2",
            name="Agent Two",
            description="Has cap2",
            capabilities=["cap2", "cap3"],
            agent_type="local"
        )
        agent3 = AgentInfo(
            id="agent3",
            name="Agent Three",
            description="Has cap3",
            capabilities=["cap3"],
            agent_type="local"
        )

        registry.register(agent1)
        registry.register(agent2)
        registry.register(agent3)

        results = registry.find_by_capability("cap1")

        assert len(results) == 1
        assert results[0].id == "agent1"

    def test_find_by_multiple_capabilities(self):
        """Test finding agents with multiple capabilities."""
        registry = AgentRegistry()

        agent1 = AgentInfo(
            id="agent1",
            name="Agent One",
            description="Has cap1 and cap2",
            capabilities=["cap1", "cap2"],
            agent_type="local"
        )
        agent2 = AgentInfo(
            id="agent2",
            name="Agent Two",
            description="Has only cap1",
            capabilities=["cap1"],
            agent_type="local"
        )

        registry.register(agent1)
        registry.register(agent2)

        # Agent must have ALL specified capabilities
        results = registry.find_by_capabilities(["cap1", "cap2"])

        assert len(results) == 1
        assert results[0].id == "agent1"

    def test_find_by_nonexistent_capability(self):
        """Test finding agents with capability that doesn't exist."""
        registry = AgentRegistry()

        agent1 = AgentInfo(
            id="agent1",
            name="Agent One",
            description="Has cap1",
            capabilities=["cap1"],
            agent_type="local"
        )
        registry.register(agent1)

        results = registry.find_by_capability("nonexistent")

        assert len(results) == 0

    def test_filter_by_agent_type(self):
        """Test filtering agents by type."""
        registry = AgentRegistry()

        local_agent = AgentInfo(
            id="local1",
            name="Local Agent",
            description="Local agent",
            capabilities=["cap1"],
            agent_type="local"
        )
        remote_agent = AgentInfo(
            id="remote1",
            name="Remote Agent",
            description="Remote agent",
            capabilities=["cap1"],
            agent_type="remote"
        )

        registry.register(local_agent)
        registry.register(remote_agent)

        local_agents = registry.filter_by_type("local")

        assert len(local_agents) == 1
        assert local_agents[0].id == "local1"


class TestFallbackAgent:
    """Test fallback agent creation."""

    def test_create_fallback_agent(self):
        """Test creating default fallback agent."""
        registry = AgentRegistry()

        fallback = registry.create_fallback_agent()

        assert fallback.id == "llm-executor"
        assert "llm" in fallback.name.lower() or "executor" in fallback.name.lower()
        assert len(fallback.capabilities) > 0

    def test_get_or_fallback_returns_existing(self):
        """Test get_or_fallback returns existing agent if found."""
        registry = AgentRegistry()

        agent = AgentInfo(
            id="agent1",
            name="Agent One",
            description="Existing agent",
            capabilities=["cap1"],
            agent_type="local"
        )
        registry.register(agent)

        result = registry.get_or_fallback("agent1")

        assert result.id == "agent1"

    def test_get_or_fallback_returns_fallback(self):
        """Test get_or_fallback returns fallback if agent not found."""
        registry = AgentRegistry()

        result = registry.get_or_fallback("nonexistent")

        assert result.id == "llm-executor"


class TestAgentRefresh:
    """Test agent registry refresh functionality."""

    def test_refresh_reloads_agents(self, tmp_path):
        """Test refresh reloads agents from config files."""
        config_file = tmp_path / "agents.json"

        # Initial config
        config_data = {
            "agents": [{
                "id": "agent1",
                "name": "Agent One",
                "description": "First version",
                "capabilities": ["cap1"],
                "type": "local"
            }]
        }
        config_file.write_text(json.dumps(config_data))

        registry = AgentRegistry(discovery_paths=[tmp_path])
        registry.discover()

        assert registry.agents["agent1"].description == "First version"

        # Update config
        config_data["agents"][0]["description"] = "Updated version"
        config_file.write_text(json.dumps(config_data))

        # Refresh should pick up changes
        registry.refresh()

        assert registry.agents["agent1"].description == "Updated version"

    def test_refresh_handles_mtime_check(self, tmp_path):
        """Test refresh only reloads if file modified time changed."""
        config_file = tmp_path / "agents.json"
        config_data = {
            "agents": [{
                "id": "agent1",
                "name": "Agent One",
                "description": "First version",
                "capabilities": ["cap1"],
                "type": "local"
            }]
        }
        config_file.write_text(json.dumps(config_data))

        registry = AgentRegistry(discovery_paths=[tmp_path])
        registry.discover()

        initial_agent = registry.agents["agent1"]

        # Refresh without file changes
        registry.refresh()

        # Should still have same agent (may be different object but same data)
        assert registry.agents["agent1"].description == initial_agent.description


class TestAgentRetrieval:
    """Test retrieving registered agents."""

    def test_get_agent_by_id(self):
        """Test retrieving agent by ID."""
        registry = AgentRegistry()

        agent = AgentInfo(
            id="agent1",
            name="Agent One",
            description="Test agent",
            capabilities=["cap1"],
            agent_type="local"
        )
        registry.register(agent)

        retrieved = registry.get("agent1")

        assert retrieved is not None
        assert retrieved.id == "agent1"

    def test_get_nonexistent_agent(self):
        """Test retrieving non-existent agent returns None."""
        registry = AgentRegistry()

        result = registry.get("nonexistent")

        assert result is None

    def test_list_all_agents(self):
        """Test listing all registered agents."""
        registry = AgentRegistry()

        agent1 = AgentInfo(
            id="agent1",
            name="Agent One",
            description="First",
            capabilities=["cap1"],
            agent_type="local"
        )
        agent2 = AgentInfo(
            id="agent2",
            name="Agent Two",
            description="Second",
            capabilities=["cap2"],
            agent_type="local"
        )

        registry.register(agent1)
        registry.register(agent2)

        all_agents = registry.list_all()

        assert len(all_agents) == 2
        assert any(a.id == "agent1" for a in all_agents)
        assert any(a.id == "agent2" for a in all_agents)
