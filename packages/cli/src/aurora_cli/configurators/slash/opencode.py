"""OpenCode slash command configurator.

Configures slash commands for OpenCode in .opencode/command/ directory.
Uses $ARGUMENTS placeholder and <UserRequest> tags for argument handling.
"""

from aurora_cli.configurators.slash.base import SlashCommandConfigurator
from aurora_cli.templates.slash_commands import get_command_body

# Frontmatter for each command - includes $ARGUMENTS and <UserRequest> tags
FRONTMATTER: dict[str, str] = {
    "search": """---
description: Search indexed code ["query" --limit N --type X]
---
The user wants to search indexed memory. Use the aurora instructions to search.
<UserRequest>
  $ARGUMENTS
</UserRequest>
""",
    "get": """---
description: Retrieve last search result [N]
---
The user wants to retrieve a specific chunk. Use the aurora instructions to get the chunk.
<UserRequest>
  $ARGUMENTS
</UserRequest>
""",
    "plan": """---
description: Create implementation plan [goal | goals.json]
---
The user has requested the following plan. Use the aurora instructions to create their plan.
<UserRequest>
  $ARGUMENTS
</UserRequest>
""",
    "tasks": """---
description: Regenerate tasks from PRD [plan-id]
---
The user wants to regenerate tasks from the PRD. Use the aurora instructions to regenerate tasks.
<UserRequest>
  $ARGUMENTS
</UserRequest>
""",
    "implement": """---
description: Execute plan tasks [plan-id]
---
The user wants to implement a plan. Use the aurora instructions for implementation.
<UserRequest>
  $ARGUMENTS
</UserRequest>
""",
    "archive": """---
description: Archive completed plan [plan-id]
---
The user wants to archive a completed plan. Use the aurora instructions to archive the plan.
<UserRequest>
  $ARGUMENTS
</UserRequest>
""",
}

# File paths for each command
FILE_PATHS: dict[str, str] = {
    "search": ".opencode/command/aurora-search.md",
    "get": ".opencode/command/aurora-get.md",
    "plan": ".opencode/command/aurora-plan.md",
    "tasks": ".opencode/command/aurora-tasks.md",
    "implement": ".opencode/command/aurora-implement.md",
    "archive": ".opencode/command/aurora-archive.md",
}


class OpenCodeSlashCommandConfigurator(SlashCommandConfigurator):
    """Slash command configurator for OpenCode.

    Creates slash commands in .opencode/command/ directory for
    all Aurora commands. Uses $ARGUMENTS placeholder and <UserRequest>
    tags for argument handling.
    """

    @property
    def tool_id(self) -> str:
        """Tool identifier."""
        return "opencode"

    @property
    def is_available(self) -> bool:
        """OpenCode is always available (doesn't require detection)."""
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
            YAML frontmatter with $ARGUMENTS and <UserRequest> tags

        """
        return FRONTMATTER[command_id]

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
