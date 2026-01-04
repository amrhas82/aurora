"""RooCode slash command configurator.

Configures slash commands for RooCode in .roo/commands/ directory.
Uses markdown heading format for frontmatter instead of YAML.
"""

from aurora_cli.configurators.slash.base import SlashCommandConfigurator
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

# File paths for each command
FILE_PATHS: dict[str, str] = {
    "plan": ".roo/commands/aurora-plan.md",
    "query": ".roo/commands/aurora-query.md",
    "index": ".roo/commands/aurora-index.md",
    "search": ".roo/commands/aurora-search.md",
    "init": ".roo/commands/aurora-init.md",
    "doctor": ".roo/commands/aurora-doctor.md",
    "agents": ".roo/commands/aurora-agents.md",
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
