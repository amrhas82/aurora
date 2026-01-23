"""OpenCode configurator."""

from aurora_cli.templates import get_claude_template

from .base import BaseConfigurator


class OpenCodeConfigurator(BaseConfigurator):
    """Configurator for OpenCode.

    Creates an OPENCODE.md stub that references AGENTS.md for full instructions.
    """

    @property
    def name(self) -> str:
        """Human-readable tool name."""
        return "OpenCode"

    @property
    def config_file_name(self) -> str:
        """Name of configuration file."""
        return "OPENCODE.md"

    async def get_template_content(self, _aurora_dir: str) -> str:
        """Get OpenCode template content.

        Args:
            aurora_dir: Name of Aurora directory

        Returns:
            Template content for OPENCODE.md (stub referencing AGENTS.md)

        """
        # Use same stub template as CLAUDE.md
        return get_claude_template()
