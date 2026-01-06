"""CodeBuddy slash command configurator.

Configures slash commands for CodeBuddy AI in .codebuddy/commands/aurora/ directory.
"""

from aurora_cli.configurators.slash.base import SlashCommandConfigurator
from aurora_cli.templates.slash_commands import get_command_body


# Frontmatter for each command
FRONTMATTER: dict[str, str] = {
    "plan": """---
name: Aurora: Plan
description: Generate structured plans with agent delegation
category: Aurora
tags: [aurora, planning]
---""",
    "checkpoint": """---
name: Aurora: Checkpoint
description: Save session context for continuity
category: Aurora
tags: [aurora, session, checkpoint]
---""",
    "archive": """---
name: Aurora: Archive
description: Archive completed plans with spec processing
category: Aurora
tags: [aurora, planning, archive]
---""",
}

# File paths for each command
FILE_PATHS: dict[str, str] = {
    "plan": ".codebuddy/commands/aurora/plan.md",
    "checkpoint": ".codebuddy/commands/aurora/checkpoint.md",
    "archive": ".codebuddy/commands/aurora/archive.md",
}


class CodeBuddySlashCommandConfigurator(SlashCommandConfigurator):
    """Slash command configurator for CodeBuddy AI.

    Creates slash commands in .codebuddy/commands/aurora/ directory for
    all Aurora commands.
    """

    @property
    def tool_id(self) -> str:
        """Tool identifier."""
        return "codebuddy"

    @property
    def is_available(self) -> bool:
        """CodeBuddy is always available (doesn't require detection)."""
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
        return FRONTMATTER[command_id]

    def get_body(self, command_id: str) -> str:
        """Get body content for a slash command.

        Args:
            command_id: Command identifier

        Returns:
            Command body content from templates
        """
        return get_command_body(command_id)
