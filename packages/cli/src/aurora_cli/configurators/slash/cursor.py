"""Cursor slash command configurator.

Configures slash commands for Cursor in .cursor/commands/ directory
with aurora-{command}.md naming pattern.
"""

from aurora_cli.configurators.slash.base import SlashCommandConfigurator
from aurora_cli.templates.slash_commands import get_command_body

# File paths for each command
FILE_PATHS: dict[str, str] = {
    "search": ".cursor/commands/aurora-search.md",
    "get": ".cursor/commands/aurora-get.md",
    "plan": ".cursor/commands/aurora-plan.md",
    "proposal": ".cursor/commands/aurora-proposal.md",
    "checkpoint": ".cursor/commands/aurora-checkpoint.md",
    "implement": ".cursor/commands/aurora-implement.md",
    "archive": ".cursor/commands/aurora-archive.md",
}

# Frontmatter for each command (Cursor uses name, id, category, description)
FRONTMATTER: dict[str, str] = {
    "search": """---
name: Aurora: Search
id: /aurora-search
description: Search indexed code ["query" --limit N --type function]
category: Aurora
tags: [aurora, search, memory]
---""",
    "get": """---
name: Aurora: Get
id: /aurora-get
description: Retrieve search result [N] from last search
category: Aurora
tags: [aurora, search, memory]
---""",
    "plan": """---
name: Aurora: Plan
id: /aurora-plan
description: Create implementation plan with agent delegation [goal]
category: Aurora
tags: [aurora, planning]
---""",
    "proposal": """---
name: Aurora: Proposal
id: /aurora-proposal
description: Draft spec-delta proposal with requirements [feature]
category: Aurora
tags: [aurora, planning, specs]
---""",
    "checkpoint": """---
name: Aurora: Checkpoint
id: /aurora-checkpoint
description: Save session context ["optional-name"]
category: Aurora
tags: [aurora, session, checkpoint]
---""",
    "implement": """---
name: Aurora: Implement
id: /aurora-implement
description: Execute plan tasks [plan-id]
category: Aurora
tags: [aurora, planning, implementation]
---""",
    "archive": """---
name: Aurora: Archive
id: /aurora-archive
description: Archive completed plan with spec processing [plan-id]
category: Aurora
tags: [aurora, planning, archive]
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
