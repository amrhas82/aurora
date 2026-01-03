"""Claude Code configurator."""

from .base import BaseConfigurator
from aurora_cli.templates import get_claude_template


class ClaudeConfigurator(BaseConfigurator):
    """Configurator for Claude Code (Anthropic's official CLI).

    Creates a CLAUDE.md stub that references AGENTS.md for full instructions.
    """

    @property
    def name(self) -> str:
        """Human-readable tool name."""
        return "Claude Code"

    @property
    def config_file_name(self) -> str:
        """Name of configuration file."""
        return "CLAUDE.md"

    async def get_template_content(self, aurora_dir: str) -> str:
        """Get Claude Code template content.

        Args:
            aurora_dir: Name of Aurora directory

        Returns:
            Template content for CLAUDE.md (stub referencing AGENTS.md)
        """
        return get_claude_template()
