"""Gemini CLI slash command configurator.

Configures slash commands for Gemini CLI in .gemini/commands/aurora/ directory
using TOML format (extends TomlSlashCommandConfigurator).
"""

from aurora_cli.configurators.slash.toml_base import TomlSlashCommandConfigurator
from aurora_cli.templates.slash_commands import get_command_body


# File paths for each command (TOML format)
FILE_PATHS: dict[str, str] = {
    "plan": ".gemini/commands/aurora/plan.toml",
    "checkpoint": ".gemini/commands/aurora/checkpoint.toml",
    "archive": ".gemini/commands/aurora/archive.toml",
}

# Descriptions for each command
DESCRIPTIONS: dict[str, str] = {
    "plan": "Generate structured plans with agent delegation",
    "checkpoint": "Save session context for continuity",
    "archive": "Archive completed plans with spec processing",
}


class GeminiSlashCommandConfigurator(TomlSlashCommandConfigurator):
    """Slash command configurator for Gemini CLI.

    Creates slash commands in .gemini/commands/aurora/ directory for
    all Aurora commands using TOML format with markers inside the prompt field.
    """

    @property
    def tool_id(self) -> str:
        """Tool identifier."""
        return "gemini"

    @property
    def is_available(self) -> bool:
        """Gemini is always available (doesn't require detection)."""
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
            Description string for the command
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
