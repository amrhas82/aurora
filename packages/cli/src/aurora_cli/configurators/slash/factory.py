"""Factory Droid slash command configurator.

Configures slash commands for Factory Droid in .factory/commands/ directory.
Includes argument-hint in frontmatter and $ARGUMENTS in body.
"""

from aurora_cli.configurators.slash.base import SlashCommandConfigurator
from aurora_cli.templates.slash_commands import get_command_body

# Frontmatter for each command
FRONTMATTER: dict[str, str] = {
    "search": """---
name: Aurora: Search
description: Search indexed code ["query" --limit N --type function]
argument-hint: search query
category: Aurora
tags: [aurora, search, memory]
---""",
    "get": """---
name: Aurora: Get
description: Retrieve search result [N] from last search
argument-hint: chunk index number
category: Aurora
tags: [aurora, search, memory]
---""",
    "plan": """---
name: Aurora: Plan
description: Create implementation plan with agent delegation [goal]
argument-hint: request or feature description
category: Aurora
tags: [aurora, planning]
---""",
    "tasks": """---
name: Aurora: Tasks
description: Regenerate tasks from PRD [plan-id]
argument-hint: plan ID to regenerate tasks for
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
description: Archive completed plan with spec processing [plan-id]
argument-hint: plan ID to archive
category: Aurora
tags: [aurora, planning, archive]
---""",
}

# File paths for each command
FILE_PATHS: dict[str, str] = {
    "search": ".factory/commands/aurora-search.md",
    "get": ".factory/commands/aurora-get.md",
    "plan": ".factory/commands/aurora-plan.md",
    "tasks": ".factory/commands/aurora-tasks.md",
    "implement": ".factory/commands/aurora-implement.md",
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
