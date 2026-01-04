"""Amazon Q Developer slash command configurator.

Configures slash commands for Amazon Q in .amazonq/prompts/ directory.
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
</UserRequest>""",
    "query": """---
description: Search codebase using memory system
---

The user wants to query the codebase. Use the aurora instructions to execute the query.

<UserRequest>
  $ARGUMENTS
</UserRequest>""",
    "index": """---
description: Index codebase for semantic search
---

The user wants to index the codebase. Use the aurora instructions to index the specified path.

<IndexPath>
  $ARGUMENTS
</IndexPath>""",
    "search": """---
description: Search indexed code
---

The user wants to search the codebase. Use the aurora instructions to execute the search.

<SearchQuery>
  $ARGUMENTS
</SearchQuery>""",
    "init": """---
description: Initialize Aurora for the project
---

The user wants to initialize Aurora for this project. Use the aurora instructions to set up the project.

<InitOptions>
  $ARGUMENTS
</InitOptions>""",
    "doctor": """---
description: Run health checks on Aurora installation
---

The user wants to run health checks. Use the aurora instructions to diagnose issues.

<DoctorOptions>
  $ARGUMENTS
</DoctorOptions>""",
    "agents": """---
description: Browse and search available AI agents
---

The user wants to explore available agents. Use the aurora instructions to list or search agents.

<AgentQuery>
  $ARGUMENTS
</AgentQuery>""",
}

# File paths for each command
FILE_PATHS: dict[str, str] = {
    "plan": ".amazonq/prompts/aurora-plan.md",
    "query": ".amazonq/prompts/aurora-query.md",
    "index": ".amazonq/prompts/aurora-index.md",
    "search": ".amazonq/prompts/aurora-search.md",
    "init": ".amazonq/prompts/aurora-init.md",
    "doctor": ".amazonq/prompts/aurora-doctor.md",
    "agents": ".amazonq/prompts/aurora-agents.md",
}


class AmazonQSlashCommandConfigurator(SlashCommandConfigurator):
    """Slash command configurator for Amazon Q Developer.

    Creates slash commands in .amazonq/prompts/ directory for
    all Aurora commands. Uses $ARGUMENTS placeholder and <UserRequest>
    tags for argument handling.
    """

    @property
    def tool_id(self) -> str:
        """Tool identifier."""
        return "amazon-q"

    @property
    def is_available(self) -> bool:
        """Amazon Q is always available (doesn't require detection)."""
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
