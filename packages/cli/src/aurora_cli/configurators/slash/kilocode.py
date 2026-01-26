"""Kilo Code slash command configurator.

Configures slash commands for Kilo Code in .kilocode/workflows/ directory.
This configurator returns None for frontmatter (no frontmatter needed).
"""

from aurora_cli.configurators.slash.base import SlashCommandConfigurator
from aurora_cli.templates.slash_commands import get_command_body

# File paths for each command
FILE_PATHS: dict[str, str] = {
    "search": ".kilocode/workflows/aurora-search.md",
    "get": ".kilocode/workflows/aurora-get.md",
    "plan": ".kilocode/workflows/aurora-plan.md",
    "tasks": ".kilocode/workflows/aurora-tasks.md",
    "implement": ".kilocode/workflows/aurora-implement.md",
    "archive": ".kilocode/workflows/aurora-archive.md",
}


class KiloCodeSlashCommandConfigurator(SlashCommandConfigurator):
    """Slash command configurator for Kilo Code.

    Creates slash commands in .kilocode/workflows/ directory for
    all Aurora commands. Does not include frontmatter.
    """

    @property
    def tool_id(self) -> str:
        """Tool identifier."""
        return "kilocode"

    @property
    def is_available(self) -> bool:
        """Kilo Code is always available (doesn't require detection)."""
        return True

    def get_relative_path(self, command_id: str) -> str:
        """Get relative path for a slash command file.

        Args:
            command_id: Command identifier

        Returns:
            Relative path from project root

        """
        return FILE_PATHS[command_id]

    def get_frontmatter(self, command_id: str) -> str | None:
        """Get frontmatter for a slash command file.

        Kilo Code does not use frontmatter.

        Args:
            command_id: Command identifier

        Returns:
            None (no frontmatter)

        """
        return None

    def get_body(self, command_id: str) -> str:
        """Get body content for a slash command.

        Args:
            command_id: Command identifier

        Returns:
            Command body content from templates

        """
        return get_command_body(command_id)

    def get_description(self, command_id: str) -> str | None:
        """Get brief description for skill listings.

        Args:
            command_id: Command identifier

        Returns:
            One-line description for skill listings

        """
        descriptions = {
            "search": 'Search indexed code ["query" --limit N --type X]',
            "get": "Retrieve last search result [N]",
            "plan": "Create implementation plan [goal | goals.json]",
            "tasks": "Regenerate tasks from PRD [plan-id]",
            "implement": "Execute plan tasks [plan-id]",
            "archive": "Archive completed plan [plan-id]",
        }
        return descriptions.get(command_id)
