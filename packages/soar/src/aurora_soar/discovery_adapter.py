"""Adapter layer for agent discovery integration with SOAR.

This module bridges the new ManifestManager (from aurora_cli.agent_discovery)
with SOAR's AgentRegistry interface, enabling SOAR to use the agent discovery system
while maintaining backward compatibility.

Functions:
    - get_manifest_manager(): Get or create cached ManifestManager instance
    - convert_agent_info(): Convert discovery AgentInfo to registry AgentInfo
    - get_agent(): Get agent by ID using ManifestManager
    - list_agents(): List all agents using ManifestManager
    - create_fallback_agent(): Create fallback agent for missing agents
"""

import logging
from pathlib import Path

from aurora_cli.agent_discovery.manifest import ManifestManager
from aurora_cli.agent_discovery.models import AgentInfo as DiscoveryAgentInfo
from aurora_soar.agent_registry import AgentInfo as RegistryAgentInfo


logger = logging.getLogger(__name__)


# Module-level cache for ManifestManager instance
_manifest_manager_cache: ManifestManager | None = None


def _clear_cache() -> None:
    """Clear the cached ManifestManager instance.

    This function is primarily for testing purposes, allowing tests
    to reset the cache between test runs.
    """
    global _manifest_manager_cache
    _manifest_manager_cache = None


def get_manifest_manager() -> ManifestManager:
    """Get or create a cached ManifestManager instance.

    This function caches the ManifestManager instance to avoid redundant
    manifest loading across multiple calls. The cache is module-level and
    persists for the lifetime of the process.

    Returns:
        ManifestManager instance (cached on first call)

    """
    global _manifest_manager_cache

    if _manifest_manager_cache is None:
        _manifest_manager_cache = ManifestManager()
        logger.debug("Created new ManifestManager instance")

    return _manifest_manager_cache


def convert_agent_info(discovery_agent: DiscoveryAgentInfo) -> RegistryAgentInfo:
    """Convert discovery AgentInfo to registry AgentInfo.

    Maps fields from the discovery system's AgentInfo model to SOAR's
    AgentRegistry.AgentInfo model. Handles field name differences and
    provides sensible defaults for missing data.

    Field mapping:
        - id -> id (direct copy)
        - role -> name (role becomes the agent name)
        - goal -> description (goal becomes the description)
        - skills -> capabilities (skills list becomes capabilities)
        - agent_type -> "local" (all discovery agents are local)

    Args:
        discovery_agent: AgentInfo from discovery system

    Returns:
        RegistryAgentInfo compatible with SOAR's AgentRegistry

    """
    # Start with skills as base capabilities
    capabilities = list(discovery_agent.skills) if discovery_agent.skills else []

    # If no skills provided, add category-based default capability
    if not capabilities:
        capabilities.append(f"{discovery_agent.category.value}-general")

    return RegistryAgentInfo(
        id=discovery_agent.id,
        name=discovery_agent.role,
        description=discovery_agent.goal,
        capabilities=capabilities,
        agent_type="local",  # All discovery agents are local agents
        config={
            "category": discovery_agent.category.value,
            "source_file": discovery_agent.source_file,
            "when_to_use": discovery_agent.when_to_use,
        },
    )


def get_agent(
    agent_id: str,
    manifest_path: Path | None = None,
) -> RegistryAgentInfo | None:
    """Get an agent by ID using ManifestManager.

    Looks up an agent in the discovery system's manifest and converts it
    to SOAR's AgentRegistry format. Returns None if the agent is not found.

    Args:
        agent_id: Unique identifier of the agent to retrieve
        manifest_path: Optional custom path to manifest file.
                      If not provided, uses default manifest path.

    Returns:
        RegistryAgentInfo if agent found, None otherwise

    """
    manager = get_manifest_manager()

    # Load or refresh the manifest
    if manifest_path is None:
        # Use default manifest path (ManifestManager handles this)
        manifest_path = Path.home() / ".aurora" / "cache" / "agent_manifest.json"

    manifest = manager.get_or_refresh(manifest_path)

    # Look up the agent
    discovery_agent = manifest.get_agent(agent_id)
    if discovery_agent is None:
        logger.debug(f"Agent '{agent_id}' not found in manifest")
        return None

    # Convert and return
    return convert_agent_info(discovery_agent)


def list_agents(
    manifest_path: Path | None = None,
) -> list[RegistryAgentInfo]:
    """List all agents using ManifestManager.

    Retrieves all agents from the discovery system's manifest and converts
    them to SOAR's AgentRegistry format.

    Args:
        manifest_path: Optional custom path to manifest file.
                      If not provided, uses default manifest path.

    Returns:
        List of all agents as RegistryAgentInfo objects

    """
    manager = get_manifest_manager()

    # Load or refresh the manifest
    if manifest_path is None:
        manifest_path = Path.home() / ".aurora" / "cache" / "agent_manifest.json"

    manifest = manager.get_or_refresh(manifest_path)

    # Convert all agents to registry format
    return [convert_agent_info(agent) for agent in manifest.agents]


def create_fallback_agent() -> RegistryAgentInfo:
    """Create a fallback agent for when no suitable agent is found.

    This function mirrors AgentRegistry.create_fallback_agent() to provide
    backward compatibility. The fallback agent is a general-purpose LLM executor
    that can handle tasks when no specialized agent is available.

    Returns:
        RegistryAgentInfo for the fallback LLM executor agent

    """
    return RegistryAgentInfo(
        id="llm-executor",
        name="Default LLM Executor",
        description="Fallback agent that executes tasks using a language model",
        capabilities=["reasoning", "code-generation", "text-generation", "general-purpose"],
        agent_type="local",
        config={},
    )
