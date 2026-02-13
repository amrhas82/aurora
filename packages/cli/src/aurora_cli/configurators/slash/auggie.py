"""Auggie (Augment) slash command configurator.

Configures slash commands for Auggie AI in .augment/commands/ directory.
"""

from aurora_cli.configurators.slash.base import SlashCommandConfigurator
from aurora_cli.templates.slash_commands import get_command_body

# Frontmatter for each command
FRONTMATTER: dict[str, str] = {
    "search": """---
name: Aurora: Search
description: Search indexed code ["query" --limit N --type X]
argument-hint: search query
category: Aurora
tags: [aurora, search, memory]
---""",
    "get": """---
name: Aurora: Get
description: Retrieve last search result [N]
argument-hint: chunk index number
category: Aurora
tags: [aurora, search, memory]
---""",
    "plan": """---
name: Aurora: Plan
description: Create implementation plan [goal | goals.json]
argument-hint: request or feature description
category: Aurora
tags: [aurora, planning]
---""",
    "tasks": """---
name: Aurora: Tasks
description: Regenerate tasks from PRD [plan-id]
category: Aurora
tags: [aurora, planning]
---""",
    "implement": """---
name: Aurora: Implement
description: Execute plan tasks [plan-id]
argument-hint: plan ID to implement
category: Aurora
tags: [aurora, planning, implementation]
---""",
    "archive": """---
name: Aurora: Archive
description: Archive completed plan [plan-id]
argument-hint: plan ID to archive
category: Aurora
tags: [aurora, planning, archive]
---""",
}

# File paths for each command
FILE_PATHS: dict[str, str] = {
    "search": ".augment/commands/aurora-search.md",
    "get": ".augment/commands/aurora-get.md",
    "plan": ".augment/commands/aurora-plan.md",
    "tasks": ".augment/commands/aurora-tasks.md",
    "implement": ".augment/commands/aurora-implement.md",
    "archive": ".augment/commands/aurora-archive.md",
}


class AuggieSlashCommandConfigurator(SlashCommandConfigurator):
    """Slash command configurator for Auggie (Augment) AI.

    Creates slash commands in .augment/commands/ directory for
    all Aurora commands.
    """

    @property
    def tool_id(self) -> str:
        """Tool identifier."""
        return "auggie"

    @property
    def is_available(self) -> bool:
        """Auggie is always available (doesn't require detection)."""
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
