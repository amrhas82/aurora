"""Claude Code configurator."""

from pathlib import Path

from aurora_cli.templates import get_claude_template

from .base import BaseConfigurator


class ClaudeConfigurator(BaseConfigurator):
    """Configurator for Claude Code (Anthropic's official CLI).

    Creates a CLAUDE.md stub that references AGENTS.md for full instructions.
    Also creates .claude/commands/aur/*.md slash commands for Aurora CLI integration.
    """

    @property
    def name(self) -> str:
        """Human-readable tool name."""
        return "Claude Code"

    @property
    def config_file_name(self) -> str:
        """Name of configuration file."""
        return "CLAUDE.md"

    async def get_template_content(self, _aurora_dir: str) -> str:
        """Get Claude Code template content.

        Args:
            _aurora_dir: Name of Aurora directory (not used by this implementation)

        Returns:
            Template content for CLAUDE.md (stub referencing AGENTS.md)

        """
        return get_claude_template()

    async def configure(
        self,
        project_path: Path,
        aurora_dir: str,
    ) -> None:
        """Configure Claude Code with Aurora integration.

        Creates CLAUDE.md stub that references .aurora/AGENTS.md.

        Note: Slash commands are handled separately by SlashCommandRegistry's
        ClaudeSlashCommandConfigurator to avoid duplication.

        Args:
            project_path: Root path of the project
            aurora_dir: Name of Aurora directory

        """
        # Configure CLAUDE.md using base class method
        await super().configure(project_path, aurora_dir)
