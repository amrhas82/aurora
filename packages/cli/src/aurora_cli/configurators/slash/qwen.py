"""Qwen Code slash command configurator.

Configures slash commands for Qwen Code in .qwen/commands/ directory.
Uses TOML format instead of markdown.
"""

from aurora_cli.configurators.slash.toml_base import TomlSlashCommandConfigurator
from aurora_cli.templates.slash_commands import get_command_body


# Descriptions for each command
DESCRIPTIONS: dict[str, str] = {
    "plan": "Generate structured plans with agent delegation",
    "query": "Search codebase using memory system",
    "index": "Index codebase for semantic search",
    "search": "Search indexed code",
    "init": "Initialize Aurora for the project",
    "doctor": "Run health checks on Aurora installation",
    "agents": "Browse and search available AI agents",
}

# File paths for each command (TOML format)
FILE_PATHS: dict[str, str] = {
    "plan": ".qwen/commands/aurora-plan.toml",
    "query": ".qwen/commands/aurora-query.toml",
    "index": ".qwen/commands/aurora-index.toml",
    "search": ".qwen/commands/aurora-search.toml",
    "init": ".qwen/commands/aurora-init.toml",
    "doctor": ".qwen/commands/aurora-doctor.toml",
    "agents": ".qwen/commands/aurora-agents.toml",
}


class QwenSlashCommandConfigurator(TomlSlashCommandConfigurator):
    """Slash command configurator for Qwen Code.

    Creates slash commands in .qwen/commands/ directory for
    all Aurora commands. Uses TOML format.
    """

    @property
    def tool_id(self) -> str:
        """Tool identifier."""
        return "qwen"

    @property
    def is_available(self) -> bool:
        """Qwen Code is always available (doesn't require detection)."""
        return True

    def get_relative_path(self, command_id: str) -> str:
        """Get relative path for a slash command file.

        Args:
            command_id: Command identifier

        Returns:
            Relative path from project root
        """
        return FILE_PATHS[command_id]

    def get_description(self, command_id: str) -> str:
        """Get description for a slash command.

        Args:
            command_id: Command identifier

        Returns:
            Description string
        """
        return DESCRIPTIONS[command_id]

    def get_body(self, command_id: str) -> str:
        """Get body content for a slash command.

        Args:
            command_id: Command identifier

        Returns:
            Command body content from templates
        """
        return get_command_body(command_id)
