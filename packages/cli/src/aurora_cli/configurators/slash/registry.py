"""Registry for slash command configurators.

Manages registration and retrieval of tool-specific configurators.
"""

from aurora_cli.configurators.slash.base import SlashCommandConfigurator


class SlashCommandRegistry:
    """Central registry for slash command configurators.

    Provides a singleton-like interface for managing tool configurators.
    """

    _configurators: dict[str, SlashCommandConfigurator] = {}
    _initialized: bool = False

    @classmethod
    def _ensure_initialized(cls) -> None:
        """Ensure default configurators are registered."""
        if cls._initialized:
            return

        # Import here to avoid circular imports
        from aurora_cli.configurators.slash.claude import ClaudeSlashCommandConfigurator

        cls.register(ClaudeSlashCommandConfigurator())
        cls._initialized = True

    @classmethod
    def register(cls, configurator: SlashCommandConfigurator) -> None:
        """Register a slash command configurator.

        Args:
            configurator: Configurator instance to register

        Note:
            Tool IDs are normalized (lowercase, spaces to dashes).
        """
        tool_id = cls._normalize_tool_id(configurator.tool_id)
        cls._configurators[tool_id] = configurator

    @classmethod
    def get(cls, tool_id: str) -> SlashCommandConfigurator | None:
        """Get a configurator by tool ID.

        Args:
            tool_id: Tool identifier (e.g., "claude", "opencode")

        Returns:
            Configurator instance or None if not found
        """
        cls._ensure_initialized()
        normalized_id = cls._normalize_tool_id(tool_id)
        return cls._configurators.get(normalized_id)

    @classmethod
    def get_all(cls) -> list[SlashCommandConfigurator]:
        """Get all registered configurators.

        Returns:
            List of all configurator instances
        """
        cls._ensure_initialized()
        return list(cls._configurators.values())

    @classmethod
    def get_available(cls) -> list[SlashCommandConfigurator]:
        """Get only available configurators.

        Returns:
            List of configurators where is_available is True
        """
        cls._ensure_initialized()
        return [c for c in cls._configurators.values() if c.is_available]

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
