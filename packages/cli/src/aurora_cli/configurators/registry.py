"""Tool registry for configurators."""

from .agents import AgentsStandardConfigurator
from .ampcode import AmpCodeConfigurator
from .base import ToolConfigurator
from .claude import ClaudeConfigurator
from .droid import DroidConfigurator
from .opencode import OpenCodeConfigurator


class ToolRegistry:
    """Registry of all available tool configurators.

    This class provides a centralized registry for discovering
    and accessing tool configurators.
    """

    _tools: dict[str, ToolConfigurator] = {}

    @classmethod
    def _initialize(cls) -> None:
        """Initialize the registry with all configurators."""
        if not cls._tools:  # Only initialize once
            configurators = [
                ClaudeConfigurator(),
                OpenCodeConfigurator(),
                AmpCodeConfigurator(),
                DroidConfigurator(),
                AgentsStandardConfigurator(),
            ]

            for configurator in configurators:
                tool_id = configurator.name.lower().replace(" ", "-")
                cls._tools[tool_id] = configurator

    @classmethod
    def register(cls, configurator: ToolConfigurator) -> None:
        """Register a new tool configurator.

        Args:
            configurator: Tool configurator to register

        """
        cls._initialize()
        tool_id = configurator.name.lower().replace(" ", "-")
        cls._tools[tool_id] = configurator

    @classmethod
    def get(cls, tool_id: str) -> ToolConfigurator | None:
        """Get a configurator by tool ID.

        Args:
            tool_id: Tool ID (e.g., "claude-code", "opencode")

        Returns:
            Configurator if found, None otherwise

        """
        cls._initialize()
        return cls._tools.get(tool_id)

    @classmethod
    def get_all(cls) -> list[ToolConfigurator]:
        """Get all registered configurators.

        Returns:
            List of all configurators

        """
        cls._initialize()
        return list(cls._tools.values())

    @classmethod
    def get_available(cls) -> list[ToolConfigurator]:
        """Get all available configurators.

        Returns:
            List of available configurators (is_available=True)

        """
        cls._initialize()
        return [tool for tool in cls._tools.values() if tool.is_available]


# Tool options for CLI display
TOOL_OPTIONS = [
    {"value": "claude-code", "name": "Claude Code", "available": True},
    {"value": "opencode", "name": "OpenCode", "available": True},
    {"value": "ampcode", "name": "AmpCode", "available": True},
    {"value": "droid", "name": "Droid", "available": True},
    {
        "value": "universal-agents.md",
        "name": "Universal AGENTS.md (for other tools)",
        "available": True,
    },
]
