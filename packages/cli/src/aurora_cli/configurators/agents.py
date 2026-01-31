"""Universal AGENTS.md configurator."""

from aurora_cli.templates import get_agents_template

from .base import BaseConfigurator


class AgentsStandardConfigurator(BaseConfigurator):
    """Configurator for universal AGENTS.md.

    This creates a root-level AGENTS.md file with comprehensive
    Aurora planning instructions for any AI coding tool.
    """

    @property
    def name(self) -> str:
        """Human-readable tool name."""
        return "Universal AGENTS.md"

    @property
    def config_file_name(self) -> str:
        """Name of configuration file."""
        return "AGENTS.md"

    async def get_template_content(self, _aurora_dir: str) -> str:
        """Get universal AGENTS.md template content.

        Args:
            aurora_dir: Name of Aurora directory

        Returns:
            Template content for AGENTS.md (comprehensive instructions)

        """
        return get_agents_template()
