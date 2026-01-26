"""Codex slash command configurator.

Configures slash commands for Codex in a GLOBAL directory (~/.codex/prompts/
or $CODEX_HOME/prompts/) rather than project-relative paths like other tools.
"""

import os
from pathlib import Path

from aurora_cli.configurators.slash.base import AURORA_MARKERS, SlashCommandConfigurator
from aurora_cli.templates.slash_commands import get_command_body

# Relative paths (used for get_relative_path, but actual files go to global dir)
FILE_PATHS: dict[str, str] = {
    "search": ".codex/prompts/aurora-search.md",
    "get": ".codex/prompts/aurora-get.md",
    "plan": ".codex/prompts/aurora-plan.md",
    "tasks": ".codex/prompts/aurora-tasks.md",
    "implement": ".codex/prompts/aurora-implement.md",
    "archive": ".codex/prompts/aurora-archive.md",
}

# Frontmatter with $ARGUMENTS placeholder and argument-hint
FRONTMATTER: dict[str, str] = {
    "search": """---
description: Search indexed code ["query" --limit N --type X]
argument-hint: search query
---

$ARGUMENTS""",
    "get": """---
description: Retrieve last search result [N]
argument-hint: chunk index number
---

$ARGUMENTS""",
    "plan": """---
description: Create implementation plan [goal | goals.json]
argument-hint: request or feature description
---

$ARGUMENTS""",
    "tasks": """---
description: Regenerate tasks from PRD [plan-id]
argument-hint: plan ID to regenerate tasks for
---

$ARGUMENTS""",
    "implement": """---
description: Execute plan tasks [plan-id]
argument-hint: plan ID to implement
---

$ARGUMENTS""",
    "archive": """---
description: Archive completed plan [plan-id]
argument-hint: plan ID to archive
---

$ARGUMENTS""",
}


class CodexSlashCommandConfigurator(SlashCommandConfigurator):
    """Slash command configurator for Codex.

    Creates slash commands in a GLOBAL directory (~/.codex/prompts/ or
    $CODEX_HOME/prompts/) for all Aurora commands.

    Unlike other configurators that write to project-relative paths,
    Codex discovers prompts globally.
    """

    @property
    def tool_id(self) -> str:
        """Tool identifier."""
        return "codex"

    @property
    def is_available(self) -> bool:
        """Codex is always available (doesn't require detection)."""
        return True

    def _get_global_prompts_dir(self) -> str:
        """Get the global prompts directory path.

        Returns ~/.codex/prompts/ by default, or $CODEX_HOME/prompts/
        if CODEX_HOME environment variable is set.

        Returns:
            Path to the global prompts directory

        """
        codex_home_env = os.environ.get("CODEX_HOME", "").strip()

        if codex_home_env:
            codex_home = codex_home_env
        else:
            codex_home = os.path.join(os.path.expanduser("~"), ".codex")

        return os.path.join(codex_home, "prompts")

    def get_relative_path(self, command_id: str) -> str:
        """Get relative path for a slash command file.

        Note: This returns the relative path format, but actual files
        are written to the global prompts directory.

        Args:
            command_id: Command identifier

        Returns:
            Relative path from project root (used for display/tracking)

        """
        return FILE_PATHS[command_id]

    def get_frontmatter(self, command_id: str) -> str | None:
        """Get frontmatter for a slash command file.

        Codex frontmatter includes description, argument-hint, and
        $ARGUMENTS placeholder to capture all arguments as a single string.

        Args:
            command_id: Command identifier

        Returns:
            YAML frontmatter string with $ARGUMENTS placeholder

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

    def get_description(self, command_id: str) -> str | None:
        """Get brief description for skill listings.

        Args:
            command_id: Command identifier

        Returns:
            One-line description for skill listings

        """
        descriptions = {
            "search": 'Search indexed code ["query" --limit N --type X]',
            "get": "Retrieve last search result [N]",
            "plan": "Create implementation plan [goal | goals.json]",
            "tasks": "Regenerate tasks from PRD [plan-id]",
            "implement": "Execute plan tasks [plan-id]",
            "archive": "Archive completed plan [plan-id]",
        }
        return descriptions.get(command_id)

    def resolve_absolute_path(self, project_path: str, command_id: str) -> str:
        """Resolve absolute path for a slash command file.

        For Codex, this returns the global path instead of project path.

        Args:
            project_path: Project root path (ignored for Codex)
            command_id: Command identifier

        Returns:
            Absolute path to the command file in global prompts directory

        """
        prompts_dir = self._get_global_prompts_dir()
        filename = Path(FILE_PATHS[command_id]).name
        return str(Path(prompts_dir) / filename)

    def generate_all(self, project_path: str, aurora_dir: str) -> list[str]:
        """Generate or update all slash command files in global directory.

        Codex discovers prompts globally, so files are written to
        ~/.codex/prompts/ or $CODEX_HOME/prompts/ instead of project path.

        Args:
            project_path: Project root path (ignored for Codex)
            aurora_dir: Aurora directory name (ignored for Codex)

        Returns:
            List of created/updated file paths (relative paths for tracking)

        """
        created_or_updated: list[str] = []
        prompts_dir = Path(self._get_global_prompts_dir())

        for target in self.get_targets():
            body = self.get_body(target.command_id)
            filename = Path(target.path).name
            file_path = prompts_dir / filename

            if file_path.exists():
                # Update existing file
                self._update_body(str(file_path), body)
            else:
                # Create new file
                file_path.parent.mkdir(parents=True, exist_ok=True)

                frontmatter = self.get_frontmatter(target.command_id)
                sections: list[str] = []

                if frontmatter:
                    sections.append(frontmatter.strip())

                sections.append(f"{AURORA_MARKERS['start']}\n{body}\n{AURORA_MARKERS['end']}")

                content = "\n".join(sections) + "\n"
                file_path.write_text(content, encoding="utf-8")

            created_or_updated.append(target.path)

        return created_or_updated

    def update_existing(self, project_path: str, aurora_dir: str) -> list[str]:
        """Update existing slash command files in global directory.

        Does not create new files.

        Args:
            project_path: Project root path (ignored for Codex)
            aurora_dir: Aurora directory name (ignored for Codex)

        Returns:
            List of updated file paths (relative paths for tracking)

        """
        updated: list[str] = []
        prompts_dir = Path(self._get_global_prompts_dir())

        for target in self.get_targets():
            filename = Path(target.path).name
            file_path = prompts_dir / filename

            if file_path.exists():
                body = self.get_body(target.command_id)
                self._update_body(str(file_path), body)
                updated.append(target.path)

        return updated
