"""Windsurf slash command configurator.

Configures slash commands for Windsurf in .windsurf/workflows/ directory
with aurora-{command}.md naming and special auto_execution_mode: 3 frontmatter.
"""

from aurora_cli.configurators.slash.base import SlashCommandConfigurator
from aurora_cli.templates.slash_commands import get_command_body

# File paths for each command
FILE_PATHS: dict[str, str] = {
    "search": ".windsurf/workflows/aurora-search.md",
    "get": ".windsurf/workflows/aurora-get.md",
    "plan": ".windsurf/workflows/aurora-plan.md",
    "proposal": ".windsurf/workflows/aurora-proposal.md",
    "checkpoint": ".windsurf/workflows/aurora-checkpoint.md",
    "implement": ".windsurf/workflows/aurora-implement.md",
    "archive": ".windsurf/workflows/aurora-archive.md",
}

# Descriptions for each command (used in frontmatter)
DESCRIPTIONS: dict[str, str] = {
    "search": 'Search indexed code ["query" --limit N --type function]',
    "get": "Retrieve search result [N] from last search",
    "plan": "Create implementation plan with agent delegation [goal]",
    "proposal": "Draft spec-delta proposal with requirements [feature]",
    "checkpoint": 'Save session context ["optional-name"]',
    "implement": "Execute plan tasks [plan-id]",
    "archive": "Archive completed plan with spec processing [plan-id]",
}


class WindsurfSlashCommandConfigurator(SlashCommandConfigurator):
    """Slash command configurator for Windsurf.

    Creates slash commands in .windsurf/workflows/ directory for
    all Aurora commands with aurora-{command}.md naming and
    auto_execution_mode: 3 frontmatter.
    """

    @property
    def tool_id(self) -> str:
        """Tool identifier."""
        return "windsurf"

    @property
    def is_available(self) -> bool:
        """Windsurf is always available (doesn't require detection)."""
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

        Windsurf frontmatter includes description and auto_execution_mode: 3.

        Args:
            command_id: Command identifier

        Returns:
            YAML frontmatter string with description and auto_execution_mode
        """
        description = DESCRIPTIONS[command_id]
        return f"""---
description: {description}
auto_execution_mode: 3
---"""

    def get_body(self, command_id: str) -> str:
        """Get body content for a slash command.

        Args:
            command_id: Command identifier

        Returns:
            Command body content from templates
        """
        return get_command_body(command_id)
