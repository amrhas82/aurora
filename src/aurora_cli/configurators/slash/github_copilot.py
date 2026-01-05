"""GitHub Copilot slash command configurator.

Configures slash commands for GitHub Copilot in .github/prompts/ directory.
Files use .prompt.md extension and include $ARGUMENTS placeholder.
"""

from aurora_cli.configurators.slash.base import SlashCommandConfigurator
from aurora_cli.templates.slash_commands import get_command_body


# Frontmatter for each command - includes $ARGUMENTS placeholder
FRONTMATTER: dict[str, str] = {
    "plan": """---
description: Generate structured plans with agent delegation
---

$ARGUMENTS""",
    "query": """---
description: Search codebase using memory system
---

$ARGUMENTS""",
    "index": """---
description: Index codebase for semantic search
---

$ARGUMENTS""",
    "search": """---
description: Search indexed code
---

$ARGUMENTS""",
    "init": """---
description: Initialize Aurora for the project
---

$ARGUMENTS""",
    "doctor": """---
description: Run health checks on Aurora installation
---

$ARGUMENTS""",
    "agents": """---
description: Browse and search available AI agents
---

$ARGUMENTS""",
}

# File paths for each command - uses .prompt.md extension
FILE_PATHS: dict[str, str] = {
    "plan": ".github/prompts/aurora-plan.prompt.md",
    "query": ".github/prompts/aurora-query.prompt.md",
    "index": ".github/prompts/aurora-index.prompt.md",
    "search": ".github/prompts/aurora-search.prompt.md",
    "init": ".github/prompts/aurora-init.prompt.md",
    "doctor": ".github/prompts/aurora-doctor.prompt.md",
    "agents": ".github/prompts/aurora-agents.prompt.md",
}


class GitHubCopilotSlashCommandConfigurator(SlashCommandConfigurator):
    """Slash command configurator for GitHub Copilot.

    Creates slash commands in .github/prompts/ directory for
    all Aurora commands. Uses .prompt.md extension.
    """

    @property
    def tool_id(self) -> str:
        """Tool identifier."""
        return "github-copilot"

    @property
    def is_available(self) -> bool:
        """GitHub Copilot is always available (doesn't require detection)."""
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
            YAML frontmatter with $ARGUMENTS placeholder
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
