"""Amazon Q Developer slash command configurator.

Configures slash commands for Amazon Q in .amazonq/prompts/ directory.
Uses $ARGUMENTS placeholder and <UserRequest> tags for argument handling.
"""

from aurora_cli.configurators.slash.base import SlashCommandConfigurator
from aurora_cli.templates.slash_commands import get_command_body

# Frontmatter for each command - includes $ARGUMENTS and <UserRequest> tags
FRONTMATTER: dict[str, str] = {
    "search": """---
description: Search indexed code ["query" --limit N --type function]
---

The user wants to search indexed memory. Use the aurora instructions to search.

<UserRequest>
  $ARGUMENTS
</UserRequest>""",
    "get": """---
description: Retrieve search result [N] from last search
---

The user wants to retrieve a specific chunk. Use the aurora instructions to get the chunk.

<UserRequest>
  $ARGUMENTS
</UserRequest>""",
    "plan": """---
description: Create implementation plan with agent delegation [goal]
---

The user has requested the following plan. Use the aurora instructions to create their plan.

<UserRequest>
  $ARGUMENTS
</UserRequest>""",
    "proposal": """---
description: Draft spec-delta proposal with requirements [feature]
---

The user has requested a proposal. Use the aurora instructions to create their proposal.

<UserRequest>
  $ARGUMENTS
</UserRequest>""",
    "checkpoint": """---
description: Save session context ["optional-name"]
---

The user wants to save session context. Use the aurora instructions to create a checkpoint.

<UserRequest>
  $ARGUMENTS
</UserRequest>""",
    "implement": """---
description: Execute plan tasks [plan-id]
---

The user wants to implement a plan. Use the aurora instructions for implementation.

<UserRequest>
  $ARGUMENTS
</UserRequest>""",
    "archive": """---
description: Archive completed plan with spec processing [plan-id]
---

The user wants to archive a completed plan. Use the aurora instructions to archive the plan.

<UserRequest>
  $ARGUMENTS
</UserRequest>""",
}

# File paths for each command
FILE_PATHS: dict[str, str] = {
    "search": ".amazonq/prompts/aurora-search.md",
    "get": ".amazonq/prompts/aurora-get.md",
    "plan": ".amazonq/prompts/aurora-plan.md",
    "proposal": ".amazonq/prompts/aurora-proposal.md",
    "checkpoint": ".amazonq/prompts/aurora-checkpoint.md",
    "implement": ".amazonq/prompts/aurora-implement.md",
    "archive": ".amazonq/prompts/aurora-archive.md",
}


class AmazonQSlashCommandConfigurator(SlashCommandConfigurator):
    """Slash command configurator for Amazon Q Developer.

    Creates slash commands in .amazonq/prompts/ directory for
    all Aurora commands. Uses $ARGUMENTS placeholder and <UserRequest>
    tags for argument handling.
    """

    @property
    def tool_id(self) -> str:
        """Tool identifier."""
        return "amazon-q"

    @property
    def is_available(self) -> bool:
        """Amazon Q is always available (doesn't require detection)."""
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
