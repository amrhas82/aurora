"""Registry for tool configurators.

Central registry that manages all available tool configurators.
"""

from aurora_planning.configurators.base import ToolConfigurator


class ToolRegistry:
    """Registry for managing tool configurators.

    This class maintains a central registry of all available tool configurators
    and provides methods to query and retrieve them.
    """

    _tools: dict[str, ToolConfigurator] = {}

    @classmethod
    def register(cls, tool: ToolConfigurator) -> None:
        """Register a tool configurator.

        Args:
            tool: The tool configurator to register

        """
        tool_id = tool.name.lower().replace(" ", "-")
        cls._tools[tool_id] = tool

    @classmethod
    def get(cls, tool_id: str) -> ToolConfigurator | None:
        """Get a tool configurator by ID.

        Args:
            tool_id: The tool ID (lowercase, hyphenated)

        Returns:
            The tool configurator if found, None otherwise

        """
        return cls._tools.get(tool_id)

    @classmethod
    def get_all(cls) -> list[ToolConfigurator]:
        """Get all registered tool configurators.

        Returns:
            List of all registered tool configurators

        """
        return list(cls._tools.values())

    @classmethod
    def get_available(cls) -> list[ToolConfigurator]:
        """Get all available tool configurators.

        Returns:
            List of tool configurators that are currently available

        """
        return [tool for tool in cls._tools.values() if tool.is_available]

    @classmethod
    def clear(cls) -> None:
        """Clear all registered tools.

        Mainly useful for testing.
        """
        cls._tools.clear()
