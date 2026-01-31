"""RooCode slash command configurator.

Configures slash commands for RooCode in .roo/commands/ directory.
Uses markdown heading format for frontmatter instead of YAML.
"""

from aurora_cli.configurators.slash.base import SlashCommandConfigurator
from aurora_cli.templates.slash_commands import get_command_body

# Descriptions for each command
DESCRIPTIONS: dict[str, str] = {
    "search": 'Search indexed code ["query" --limit N --type X]',
    "get": "Retrieve last search result [N]",
    "plan": "Create implementation plan [goal | goals.json]",
    "tasks": "Regenerate tasks from PRD [plan-id]",
    "implement": "Execute plan tasks [plan-id]",
    "archive": "Archive completed plan [plan-id]",
}

# File paths for each command
FILE_PATHS: dict[str, str] = {
    "search": ".roo/commands/aurora-search.md",
    "get": ".roo/commands/aurora-get.md",
    "plan": ".roo/commands/aurora-plan.md",
    "tasks": ".roo/commands/aurora-tasks.md",
    "implement": ".roo/commands/aurora-implement.md",
    "archive": ".roo/commands/aurora-archive.md",
}


class RooCodeSlashCommandConfigurator(SlashCommandConfigurator):
    """Slash command configurator for RooCode.

    Creates slash commands in .roo/commands/ directory for
    all Aurora commands. Uses markdown heading format for frontmatter.
    """

    @property
    def tool_id(self) -> str:
        """Tool identifier."""
        return "roocode"

    @property
    def is_available(self) -> bool:
        """RooCode is always available (doesn't require detection)."""
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

        Uses markdown heading format instead of YAML:
        # Aurora: {Command}

        {description}

        Args:
            command_id: Command identifier

        Returns:
            Markdown heading format frontmatter

        """
        description = DESCRIPTIONS[command_id]
        command_name = command_id.capitalize()
        return f"# Aurora: {command_name}\n\n{description}"

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
        return DESCRIPTIONS.get(command_id)
