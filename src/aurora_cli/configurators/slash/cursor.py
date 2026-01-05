"""Cursor slash command configurator.

Configures slash commands for Cursor in .cursor/commands/ directory
with aurora-{command}.md naming pattern.
"""

from aurora_cli.configurators.slash.base import SlashCommandConfigurator
from aurora_cli.templates.slash_commands import get_command_body


# File paths for each command
FILE_PATHS: dict[str, str] = {
    "plan": ".cursor/commands/aurora-plan.md",
    "query": ".cursor/commands/aurora-query.md",
    "index": ".cursor/commands/aurora-index.md",
    "search": ".cursor/commands/aurora-search.md",
    "init": ".cursor/commands/aurora-init.md",
    "doctor": ".cursor/commands/aurora-doctor.md",
    "agents": ".cursor/commands/aurora-agents.md",
}

# Frontmatter for each command (Cursor uses name, id, category, description)
FRONTMATTER: dict[str, str] = {
    "plan": """---
name: /aurora-plan
id: aurora-plan
category: Aurora
description: Generate structured plans with agent delegation
---""",
    "query": """---
name: /aurora-query
id: aurora-query
category: Aurora
description: Search codebase using memory system
---""",
    "index": """---
name: /aurora-index
id: aurora-index
category: Aurora
description: Index codebase for semantic search
---""",
    "search": """---
name: /aurora-search
id: aurora-search
category: Aurora
description: Search indexed code
---""",
    "init": """---
name: /aurora-init
id: aurora-init
category: Aurora
description: Initialize Aurora for the project
---""",
    "doctor": """---
name: /aurora-doctor
id: aurora-doctor
category: Aurora
description: Run health checks on Aurora installation
---""",
    "agents": """---
name: /aurora-agents
id: aurora-agents
category: Aurora
description: Browse and search available AI agents
---""",
}


class CursorSlashCommandConfigurator(SlashCommandConfigurator):
    """Slash command configurator for Cursor.

    Creates slash commands in .cursor/commands/ directory for
    all Aurora commands with aurora-{command}.md naming.
    """

    @property
    def tool_id(self) -> str:
        """Tool identifier."""
        return "cursor"

    @property
    def is_available(self) -> bool:
        """Cursor is always available (doesn't require detection)."""
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
            YAML frontmatter string with name, id, category, description
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
