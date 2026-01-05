"""Qoder slash command configurator.

Configures slash commands for Qoder AI in .qoder/commands/aurora/ directory.
"""

from aurora_cli.configurators.slash.base import SlashCommandConfigurator
from aurora_cli.templates.slash_commands import get_command_body


# Frontmatter for each command
FRONTMATTER: dict[str, str] = {
    "plan": """---
name: Aurora: Plan
description: Generate structured plans with agent delegation
category: Aurora
tags: [aurora, planning]
---""",
    "query": """---
name: Aurora: Query
description: Search codebase using memory system
category: Aurora
tags: [aurora, search, memory]
---""",
    "index": """---
name: Aurora: Index
description: Index codebase for semantic search
category: Aurora
tags: [aurora, memory]
---""",
    "search": """---
name: Aurora: Search
description: Search indexed code
category: Aurora
tags: [aurora, search, memory]
---""",
    "init": """---
name: Aurora: Init
description: Initialize Aurora for the project
category: Aurora
tags: [aurora, setup]
---""",
    "doctor": """---
name: Aurora: Doctor
description: Run health checks on Aurora installation
category: Aurora
tags: [aurora, diagnostics]
---""",
    "agents": """---
name: Aurora: Agents
description: Browse and search available AI agents
category: Aurora
tags: [aurora, agents]
---""",
}

# File paths for each command
FILE_PATHS: dict[str, str] = {
    "plan": ".qoder/commands/aurora/plan.md",
    "query": ".qoder/commands/aurora/query.md",
    "index": ".qoder/commands/aurora/index.md",
    "search": ".qoder/commands/aurora/search.md",
    "init": ".qoder/commands/aurora/init.md",
    "doctor": ".qoder/commands/aurora/doctor.md",
    "agents": ".qoder/commands/aurora/agents.md",
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
