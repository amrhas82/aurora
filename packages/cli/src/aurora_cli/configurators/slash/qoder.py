"""Qoder slash command configurator.

Configures slash commands for Qoder AI in .qoder/commands/aurora/ directory.
"""

from aurora_cli.configurators.slash.base import SlashCommandConfigurator
from aurora_cli.templates.slash_commands import get_command_body

# Frontmatter for each command
FRONTMATTER: dict[str, str] = {
    "search": """---
name: Aurora: Search
description: Search indexed code ["query" --limit N --type function]
category: Aurora
tags: [aurora, search, memory]
---""",
    "get": """---
name: Aurora: Get
description: Retrieve search result [N] from last search
category: Aurora
tags: [aurora, search, memory]
---""",
    "plan": """---
name: Aurora: Plan
description: Create implementation plan with agent delegation [goal]
category: Aurora
tags: [aurora, planning]
---""",
    "proposal": """---
name: Aurora: Proposal
description: Draft spec-delta proposal with requirements [feature]
category: Aurora
tags: [aurora, proposalning]
---""",
    "checkpoint": """---
name: Aurora: Checkpoint
description: Save session context ["optional-name"]
category: Aurora
tags: [aurora, session, checkpoint]
---""",
    "implement": """---
name: Aurora: Implement
description: Execute plan tasks [plan-id]
category: Aurora
tags: [aurora, planning, implementation]
---""",
    "archive": """---
name: Aurora: Archive
description: Archive completed plan with spec processing [plan-id]
category: Aurora
tags: [aurora, planning, archive]
---""",
}

# File paths for each command
FILE_PATHS: dict[str, str] = {
    "search": ".qoder/commands/aurora/search.md",
    "get": ".qoder/commands/aurora/get.md",
    "plan": ".qoder/commands/aurora/plan.md",
    "proposal": ".qoder/commands/aurora/proposal.md",
    "checkpoint": ".qoder/commands/aurora/checkpoint.md",
    "implement": ".qoder/commands/aurora/implement.md",
    "archive": ".qoder/commands/aurora/archive.md",
}


class QoderSlashCommandConfigurator(SlashCommandConfigurator):
    """Slash command configurator for Qoder AI.

    Creates slash commands in .qoder/commands/aurora/ directory for
    all Aurora commands.
    """

    @property
    def tool_id(self) -> str:
        """Tool identifier."""
        return "qoder"

    @property
    def is_available(self) -> bool:
        """Qoder is always available (doesn't require detection)."""
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
