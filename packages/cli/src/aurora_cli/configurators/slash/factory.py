"""Factory Droid slash command configurator.

Configures slash commands for Factory Droid in .factory/commands/ directory.
Includes argument-hint in frontmatter and $ARGUMENTS in body.
"""

from aurora_cli.configurators.slash.base import SlashCommandConfigurator
from aurora_cli.templates.slash_commands import get_command_body


# Frontmatter for each command
FRONTMATTER: dict[str, str] = {
    "plan": """---
name: Aurora: Plan
description: Generate structured plans with agent delegation
argument-hint: request or feature description
category: Aurora
tags: [aurora, planning]
---""",
    "checkpoint": """---
name: Aurora: Checkpoint
description: Save session context for continuity
argument-hint: optional checkpoint name
category: Aurora
tags: [aurora, session, checkpoint]
---""",
    "archive": """---
name: Aurora: Archive
description: Archive completed plans with spec processing
argument-hint: plan ID to archive
category: Aurora
tags: [aurora, planning, archive]
---""",
}

# File paths for each command
FILE_PATHS: dict[str, str] = {
    "plan": ".factory/commands/aurora-plan.md",
    "checkpoint": ".factory/commands/aurora-checkpoint.md",
    "archive": ".factory/commands/aurora-archive.md",
}


class FactorySlashCommandConfigurator(SlashCommandConfigurator):
    """Slash command configurator for Factory Droid.

    Creates slash commands in .factory/commands/ directory for
    all Aurora commands. Includes $ARGUMENTS placeholder in body.
    """

    @property
    def tool_id(self) -> str:
        """Tool identifier."""
        return "factory"

    @property
    def is_available(self) -> bool:
        """Factory is always available (doesn't require detection)."""
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
            YAML frontmatter with argument-hint
        """
        return FRONTMATTER[command_id]

    def get_body(self, command_id: str) -> str:
        """Get body content for a slash command.

        Appends $ARGUMENTS placeholder to the template body.

        Args:
            command_id: Command identifier

        Returns:
            Command body content with $ARGUMENTS placeholder
        """
        base_body = get_command_body(command_id)
        return f"{base_body}\n\n$ARGUMENTS"
