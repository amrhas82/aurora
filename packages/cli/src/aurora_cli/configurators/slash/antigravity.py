"""Antigravity slash command configurator.

Configures slash commands for Antigravity AI in .agent/workflows/ directory.
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
    "plan": ".agent/workflows/aurora-plan.md",
    "query": ".agent/workflows/aurora-query.md",
    "index": ".agent/workflows/aurora-index.md",
    "search": ".agent/workflows/aurora-search.md",
    "init": ".agent/workflows/aurora-init.md",
    "doctor": ".agent/workflows/aurora-doctor.md",
    "agents": ".agent/workflows/aurora-agents.md",
}


class AntigravitySlashCommandConfigurator(SlashCommandConfigurator):
    """Slash command configurator for Antigravity AI.

    Creates slash commands in .agent/workflows/ directory for
    all Aurora commands.
    """

    @property
    def tool_id(self) -> str:
        """Tool identifier."""
        return "antigravity"

    @property
    def is_available(self) -> bool:
        """Antigravity is always available (doesn't require detection)."""
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

        Args:
            command_id: Command identifier

        Returns:
            YAML frontmatter string
        """
        description = DESCRIPTIONS[command_id]
        return f"---\ndescription: {description}\n---"

    def get_body(self, command_id: str) -> str:
        """Get body content for a slash command.

        Args:
            command_id: Command identifier

        Returns:
            Command body content from templates
        """
        return get_command_body(command_id)
