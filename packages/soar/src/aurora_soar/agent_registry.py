"""Agent Registry and Discovery System.

Provides agent registration, discovery, validation, and capability-based queries.

DEPRECATION NOTICE:
    AgentRegistry is deprecated and will be removed in a future version.
    Please use aurora_cli.agent_discovery.ManifestManager instead.

    Migration Guide:
        Old: from aurora_soar.agent_registry import AgentRegistry
             registry = AgentRegistry(discovery_paths=[...])
             agent = registry.get(agent_id)

        New: from aurora_cli.agent_discovery.manifest import ManifestManager
             from aurora_soar.discovery_adapter import get_agent
             manager = ManifestManager()  # Auto-discovers from default paths
             agent = get_agent(agent_id)  # Uses discovery_adapter helper
"""

import json
import logging
import warnings
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


logger = logging.getLogger(__name__)


@dataclass
class AgentInfo:
    """Information about a registered agent.

    Attributes:
        id: Unique identifier for the agent
        name: Human-readable agent name
        description: Brief description of agent capabilities
        capabilities: List of capability identifiers this agent provides
        agent_type: Type of agent ('local', 'remote', 'mcp')
        config: Additional configuration as key-value pairs

    """

    id: str
    name: str
    description: str
    capabilities: list[str]
    agent_type: str
    config: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Validate agent info after initialization."""
        if not self.id:
            raise ValueError("Agent ID cannot be empty")
        if not self.name:
            raise ValueError("Agent name cannot be empty")
        # Note: capabilities are optional - agents describe capabilities in their description
        # Suppress warning as it's expected for agents loaded from markdown files
        if self.agent_type not in ["local", "remote", "mcp"]:
            raise ValueError(
                f"Invalid agent type: {self.agent_type}. Must be one of: local, remote, mcp",
            )


class AgentRegistry:
    """Registry for agent discovery and management.

    Manages agent registration, discovery from config files,
    validation, and capability-based queries.

    .. deprecated::
        AgentRegistry is deprecated. Use `aurora_cli.agent_discovery.ManifestManager`
        with `aurora_soar.discovery_adapter` helper functions instead.
    """

    VALID_AGENT_TYPES = {"local", "remote", "mcp"}

    def __init__(self, discovery_paths: list[Path] | None = None):
        """Initialize the agent registry.

        Args:
            discovery_paths: Optional list of directories to scan for agent configs

        .. deprecated::
            AgentRegistry is deprecated. Use ManifestManager with discovery_adapter instead.

        """
        warnings.warn(
            "AgentRegistry is deprecated. Use aurora_cli.agent_discovery.ManifestManager instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        self.agents: dict[str, AgentInfo] = {}
        self.discovery_paths: list[Path] = discovery_paths or []
        self._file_mtimes: dict[Path, float] = {}

    def register(self, agent: AgentInfo) -> None:
        """Register an agent in the registry.

        Args:
            agent: AgentInfo instance to register

        """
        if agent.id in self.agents:
            logger.warning(f"Overwriting existing agent: {agent.id}")

        self.agents[agent.id] = agent
        logger.info(f"Registered agent: {agent.id} ({agent.name})")

    def get(self, agent_id: str) -> AgentInfo | None:
        """Retrieve an agent by ID.

        Args:
            agent_id: Unique identifier of the agent

        Returns:
            AgentInfo if found, None otherwise

        """
        return self.agents.get(agent_id)

    def list_all(self) -> list[AgentInfo]:
        """List all registered agents.

        Returns:
            List of all registered AgentInfo instances

        """
        return list(self.agents.values())

    def find_by_capability(self, capability: str) -> list[AgentInfo]:
        """Find agents that have a specific capability.

        Args:
            capability: Capability identifier to search for

        Returns:
            List of agents that have the specified capability

        """
        return [agent for agent in self.agents.values() if capability in agent.capabilities]

    def find_by_capabilities(self, capabilities: list[str]) -> list[AgentInfo]:
        """Find agents that have ALL specified capabilities.

        Args:
            capabilities: List of capability identifiers

        Returns:
            List of agents that have all specified capabilities

        """
        return [
            agent
            for agent in self.agents.values()
            if all(cap in agent.capabilities for cap in capabilities)
        ]

    def filter_by_type(self, agent_type: str) -> list[AgentInfo]:
        """Filter agents by type.

        Args:
            agent_type: Agent type to filter by ('local', 'remote', 'mcp')

        Returns:
            List of agents matching the specified type

        """
        return [agent for agent in self.agents.values() if agent.agent_type == agent_type]

    def validate_agent_data(self, agent_data: dict[str, Any]) -> tuple[bool, str | None]:
        """Validate agent configuration data.

        Args:
            agent_data: Dictionary containing agent configuration

        Returns:
            Tuple of (is_valid, error_message)

        """
        required_fields = ["id", "name", "description", "capabilities", "type"]

        # Check required fields
        for field_name in required_fields:
            if field_name not in agent_data:
                return False, f"Missing required field: {field_name}"

        # Validate agent type
        agent_type = agent_data.get("type")
        if agent_type not in self.VALID_AGENT_TYPES:
            return False, (
                f"Invalid agent type: {agent_type}. "
                f"Must be one of: {', '.join(self.VALID_AGENT_TYPES)}"
            )

        # Validate capabilities is a list
        capabilities = agent_data.get("capabilities")
        if not isinstance(capabilities, list):
            return False, "capabilities must be a list"

        # Warn about empty capabilities
        if not capabilities:
            logger.warning(f"Agent {agent_data.get('id')} has empty capabilities list")

        return True, None

    def discover(self) -> None:
        """Discover and load agents from all configured discovery paths.

        Scans all discovery paths for agent configuration files
        and registers valid agents.
        """
        for path in self.discovery_paths:
            if not path.exists():
                logger.warning(f"Discovery path does not exist: {path}")
                continue

            self._discover_from_path(path)

    def _discover_from_path(self, path: Path) -> None:
        """Discover agents from a specific path.

        Args:
            path: Path to search for agent configuration files

        """
        # Look for agents.json files
        if path.is_file() and path.name == "agents.json":
            config_files = [path]
        else:
            config_files = list(path.glob("agents.json"))

        for config_file in config_files:
            self._load_config_file(config_file)

    def _load_config_file(self, config_file: Path) -> None:
        """Load agents from a configuration file.

        Args:
            config_file: Path to agent configuration JSON file

        """
        try:
            with open(config_file) as f:
                data = json.load(f)

            # Track file modification time for refresh
            self._file_mtimes[config_file] = config_file.stat().st_mtime

            agents_data = data.get("agents", [])
            for agent_data in agents_data:
                # Validate agent data
                is_valid, error = self.validate_agent_data(agent_data)
                if not is_valid:
                    logger.error(f"Invalid agent config in {config_file}: {error}")
                    continue

                # Create and register agent
                try:
                    agent = AgentInfo(
                        id=agent_data["id"],
                        name=agent_data["name"],
                        description=agent_data["description"],
                        capabilities=agent_data["capabilities"],
                        agent_type=agent_data["type"],
                        config=agent_data.get("config", {}),
                    )
                    self.register(agent)
                except Exception as e:
                    logger.error(f"Failed to create agent from config in {config_file}: {e}")

        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in {config_file}: {e}")
        except Exception as e:
            logger.error(f"Failed to load config file {config_file}: {e}")

    def refresh(self) -> None:
        """Refresh agent registry by re-scanning configuration files.

        Only reloads files that have been modified since last load.
        """
        for config_file, last_mtime in list(self._file_mtimes.items()):
            if not config_file.exists():
                logger.warning(f"Config file no longer exists: {config_file}")
                del self._file_mtimes[config_file]
                continue

            current_mtime = config_file.stat().st_mtime
            if current_mtime > last_mtime:
                logger.info(f"Reloading modified config: {config_file}")
                self._load_config_file(config_file)

    def create_fallback_agent(self) -> AgentInfo:
        """Create a default fallback agent for when no suitable agent is found.

        Returns:
            AgentInfo for the fallback LLM executor agent

        """
        return AgentInfo(
            id="llm-executor",
            name="Default LLM Executor",
            description="Fallback agent that executes tasks using a language model",
            capabilities=["reasoning", "code-generation", "text-generation", "general-purpose"],
            agent_type="local",
            config={},
        )

    def get_or_fallback(self, agent_id: str) -> AgentInfo:
        """Get an agent by ID, or return the fallback agent if not found.

        Args:
            agent_id: ID of the agent to retrieve

        Returns:
            AgentInfo for the requested agent, or fallback agent if not found

        """
        agent = self.get(agent_id)
        if agent is None:
            logger.warning(f"Agent {agent_id} not found, using fallback agent")
            return self.create_fallback_agent()
        return agent
