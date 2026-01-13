"""Auggie (Augment) slash command configurator.

Configures slash commands for Auggie AI in .augment/commands/ directory.
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
    "proposal": """---
name: Aurora: Proposal
description: Draft spec-delta proposal with requirements [feature]
argument-hint: request or feature description
category: Aurora
tags: [aurora, planning, specs]
---""",
    "checkpoint": """---
name: Aurora: Checkpoint
description: Save session context ["optional-name"]
argument-hint: optional checkpoint name
category: Aurora
tags: [aurora, session, checkpoint]
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
    "search": ".augment/commands/aurora-search.md",
    "get": ".augment/commands/aurora-get.md",
    "plan": ".augment/commands/aurora-plan.md",
    "proposal": ".augment/commands/aurora-proposal.md",
    "checkpoint": ".augment/commands/aurora-checkpoint.md",
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
