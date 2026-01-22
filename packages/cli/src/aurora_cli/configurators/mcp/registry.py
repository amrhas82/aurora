"""Registry for MCP server configurators.

Manages registration and retrieval of tool-specific MCP configurators.
"""

from aurora_cli.configurators.mcp.base import MCPConfigurator


class MCPConfigRegistry:
    """Central registry for MCP server configurators.

    Provides a singleton-like interface for managing MCP configurators.
    Only tools that support MCP are registered here (currently 4 tools).
    """

    _configurators: dict[str, MCPConfigurator] = {}
    _initialized: bool = False

    @classmethod
    def _ensure_initialized(cls) -> None:
        """Ensure all MCP configurators are registered."""
        if cls._initialized:
            return

        # Import configurators here to avoid circular imports
        from aurora_cli.configurators.mcp.claude import ClaudeMCPConfigurator
        from aurora_cli.configurators.mcp.cline import ClineMCPConfigurator
        from aurora_cli.configurators.mcp.continue_ import ContinueMCPConfigurator
        from aurora_cli.configurators.mcp.cursor import CursorMCPConfigurator

        # Register all MCP-capable tool configurators
        configurators = [
            ClaudeMCPConfigurator(),
            CursorMCPConfigurator(),
            ClineMCPConfigurator(),
            ContinueMCPConfigurator(),
        ]

        for configurator in configurators:
            cls.register(configurator)

        cls._initialized = True

    @classmethod
    def register(cls, configurator: MCPConfigurator) -> None:
        """Register an MCP configurator.

        Args:
            configurator: Configurator instance to register

        Note:
            Tool IDs are normalized (lowercase, spaces to dashes).

        """
        tool_id = cls._normalize_tool_id(configurator.tool_id)
        cls._configurators[tool_id] = configurator

    @classmethod
    def get(cls, tool_id: str) -> MCPConfigurator | None:
        """Get a configurator by tool ID.

        Args:
            tool_id: Tool identifier (e.g., 'claude', 'cursor')

        Returns:
            Configurator instance or None if not found

        """
        cls._ensure_initialized()
        normalized_id = cls._normalize_tool_id(tool_id)
        return cls._configurators.get(normalized_id)

    @classmethod
    def get_all(cls) -> list[MCPConfigurator]:
        """Get all registered MCP configurators.

        Returns:
            List of all configurator instances

        """
        cls._ensure_initialized()
        return list(cls._configurators.values())

    @classmethod
    def get_mcp_capable_tools(cls) -> list[str]:
        """Get list of tool IDs that support MCP.

        Returns:
            List of tool IDs (e.g., ['claude', 'cursor', 'cline', 'continue'])

        """
        cls._ensure_initialized()
        return list(cls._configurators.keys())

    @classmethod
    def supports_mcp(cls, tool_id: str) -> bool:
        """Check if a tool supports MCP.

        Args:
            tool_id: Tool identifier to check

        Returns:
            True if tool has an MCP configurator registered

        """
        cls._ensure_initialized()
        normalized_id = cls._normalize_tool_id(tool_id)
        return normalized_id in cls._configurators

    @classmethod
    def clear(cls) -> None:
        """Clear all registered configurators.

        Used primarily for testing.
        """
        cls._configurators.clear()
        cls._initialized = False

    @staticmethod
    def _normalize_tool_id(tool_id: str) -> str:
        """Normalize a tool ID.

        Args:
            tool_id: Tool identifier to normalize

        Returns:
            Normalized tool ID (lowercase, spaces to dashes)

        """
        return tool_id.lower().replace(" ", "-")
