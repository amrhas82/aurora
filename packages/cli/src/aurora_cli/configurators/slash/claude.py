"""Claude Code slash command configurator.

Configures slash commands for Claude Code in .claude/commands/aur/ directory.
"""

from aurora_cli.configurators.slash.base import SlashCommandConfigurator
from aurora_cli.templates.slash_commands import get_command_body

# File paths for each command
FILE_PATHS: dict[str, str] = {
    "search": ".claude/commands/aur/search.md",
    "get": ".claude/commands/aur/get.md",
    "plan": ".claude/commands/aur/plan.md",
    "proposal": ".claude/commands/aur/proposal.md",
    "checkpoint": ".claude/commands/aur/checkpoint.md",
    "implement": ".claude/commands/aur/implement.md",
    "archive": ".claude/commands/aur/archive.md",
}

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
tags: [aurora, planning, specs]
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


class ClaudeSlashCommandConfigurator(SlashCommandConfigurator):
    """Slash command configurator for Claude Code.

    Creates slash commands in .claude/commands/aur/ directory for
    all Aurora commands.
    """

    @property
    def tool_id(self) -> str:
        """Tool identifier."""
        return "claude"

    @property
    def is_available(self) -> bool:
        """Claude Code is always available (doesn't require detection)."""
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
