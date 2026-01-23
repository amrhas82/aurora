"""Droid configurator."""

from aurora_cli.templates import get_claude_template

from .base import BaseConfigurator


class DroidConfigurator(BaseConfigurator):
    """Configurator for Droid.

    Creates a DROID.md stub that references AGENTS.md for full instructions.
    """

    @property
    def name(self) -> str:
        """Human-readable tool name."""
        return "Droid"

    @property
    def config_file_name(self) -> str:
        """Name of configuration file."""
        return "DROID.md"

    async def get_template_content(self, _aurora_dir: str) -> str:
        """Get Droid template content.

        Args:
            aurora_dir: Name of Aurora directory

        Returns:
            Template content for DROID.md (stub referencing AGENTS.md)

        """
        # Use same stub template as CLAUDE.md
        return get_claude_template()
