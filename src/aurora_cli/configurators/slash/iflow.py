"""iFlow slash command configurator.

Configures slash commands for iFlow AI in .iflow/commands/ directory.
"""

from aurora_cli.configurators.slash.base import SlashCommandConfigurator
from aurora_cli.templates.slash_commands import get_command_body


# Frontmatter for each command
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

# File paths for each command
FILE_PATHS: dict[str, str] = {
    "plan": ".iflow/commands/aurora-plan.md",
    "query": ".iflow/commands/aurora-query.md",
    "index": ".iflow/commands/aurora-index.md",
    "search": ".iflow/commands/aurora-search.md",
    "init": ".iflow/commands/aurora-init.md",
    "doctor": ".iflow/commands/aurora-doctor.md",
    "agents": ".iflow/commands/aurora-agents.md",
}


class IflowSlashCommandConfigurator(SlashCommandConfigurator):
    """Slash command configurator for iFlow AI.

    Creates slash commands in .iflow/commands/ directory for
    all Aurora commands.
    """

    @property
    def tool_id(self) -> str:
        """Tool identifier."""
        return "iflow"

    @property
    def is_available(self) -> bool:
        """iFlow is always available (doesn't require detection)."""
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
