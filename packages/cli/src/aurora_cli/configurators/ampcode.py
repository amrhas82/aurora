"""AmpCode configurator."""

from aurora_cli.templates import get_claude_template

from .base import BaseConfigurator


class AmpCodeConfigurator(BaseConfigurator):
    """Configurator for AmpCode.

    Creates an AMPCODE.md stub that references AGENTS.md for full instructions.
    """

    @property
    def name(self) -> str:
        """Human-readable tool name."""
        return "AmpCode"

    @property
    def config_file_name(self) -> str:
        """Name of configuration file."""
        return "AMPCODE.md"

    async def get_template_content(self, _aurora_dir: str) -> str:
        """Get AmpCode template content.

        Args:
            aurora_dir: Name of Aurora directory

        Returns:
            Template content for AMPCODE.md (stub referencing AGENTS.md)

        """
        # Use same stub template as CLAUDE.md
        return get_claude_template()
