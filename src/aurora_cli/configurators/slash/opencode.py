"""OpenCode slash command configurator.

Configures slash commands for OpenCode in .opencode/command/ directory.
Uses $ARGUMENTS placeholder and <UserRequest> tags for argument handling.
"""

from aurora_cli.configurators.slash.base import SlashCommandConfigurator
from aurora_cli.templates.slash_commands import get_command_body


# Frontmatter for each command - includes $ARGUMENTS and <UserRequest> tags
FRONTMATTER: dict[str, str] = {
    "plan": """---
description: Generate structured plans with agent delegation
---
The user has requested the following plan. Use the aurora instructions to create their plan.
<UserRequest>
  $ARGUMENTS
</UserRequest>
""",
    "query": """---
description: Search codebase using memory system
---
The user wants to query the codebase. Use the aurora instructions to execute the query.
<UserRequest>
  $ARGUMENTS
</UserRequest>
""",
    "index": """---
description: Index codebase for semantic search
---
The user wants to index the codebase. Use the aurora instructions to index the specified path.
<UserRequest>
  $ARGUMENTS
</UserRequest>
""",
    "search": """---
description: Search indexed code
---
The user wants to search the codebase. Use the aurora instructions to execute the search.
<UserRequest>
  $ARGUMENTS
</UserRequest>
""",
    "init": """---
description: Initialize Aurora for the project
---
The user wants to initialize Aurora for this project. Use the aurora instructions.
<UserRequest>
  $ARGUMENTS
</UserRequest>
""",
    "doctor": """---
description: Run health checks on Aurora installation
---
The user wants to run health checks. Use the aurora instructions to diagnose issues.
<UserRequest>
  $ARGUMENTS
</UserRequest>
""",
    "agents": """---
description: Browse and search available AI agents
---
The user wants to explore available agents. Use the aurora instructions.
<UserRequest>
  $ARGUMENTS
</UserRequest>
""",
}

# File paths for each command
FILE_PATHS: dict[str, str] = {
    "plan": ".opencode/command/aurora-plan.md",
    "query": ".opencode/command/aurora-query.md",
    "index": ".opencode/command/aurora-index.md",
    "search": ".opencode/command/aurora-search.md",
    "init": ".opencode/command/aurora-init.md",
    "doctor": ".opencode/command/aurora-doctor.md",
    "agents": ".opencode/command/aurora-agents.md",
}


class OpenCodeSlashCommandConfigurator(SlashCommandConfigurator):
    """Slash command configurator for OpenCode.

    Creates slash commands in .opencode/command/ directory for
    all Aurora commands. Uses $ARGUMENTS placeholder and <UserRequest>
    tags for argument handling.
    """

    @property
    def tool_id(self) -> str:
        """Tool identifier."""
        return "opencode"

    @property
    def is_available(self) -> bool:
        """OpenCode is always available (doesn't require detection)."""
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
