"""Antigravity slash command configurator.

Configures slash commands for Antigravity AI in .agent/workflows/ directory.
"""

from aurora_cli.configurators.slash.base import SlashCommandConfigurator
from aurora_cli.templates.slash_commands import get_command_body

# Descriptions for each command
DESCRIPTIONS: dict[str, str] = {
    "search": 'Search indexed code ["query" --limit N --type function]',
    "get": "Retrieve search result [N] from last search",
    "plan": "Create implementation plan with agent delegation [goal]",
    "proposal": "Generate spec-delta proposals with requirements",
    "checkpoint": 'Save session context ["optional-name"]',
    "implement": "Execute plan tasks [plan-id]",
    "archive": "Archive completed plan with spec processing [plan-id]",
}

# File paths for each command
FILE_PATHS: dict[str, str] = {
    "search": ".agent/workflows/aurora-search.md",
    "get": ".agent/workflows/aurora-get.md",
    "plan": ".agent/workflows/aurora-plan.md",
    "proposal": ".agent/workflows/aurora-proposal.md",
    "checkpoint": ".agent/workflows/aurora-checkpoint.md",
    "implement": ".agent/workflows/aurora-implement.md",
    "archive": ".agent/workflows/aurora-archive.md",
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
