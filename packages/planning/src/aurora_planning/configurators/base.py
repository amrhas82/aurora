"""Base protocol for tool configurators.

Defines the interface that all tool-specific configurators must implement.
"""

from abc import ABC, abstractmethod


class ToolConfigurator(ABC):
    """Abstract base for tool-specific configurators.

    Each AI coding tool (Claude Code, OpenCode, etc.) has its own
    configurator that knows how to configure Aurora for that tool.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable tool name."""
        ...

    @property
    @abstractmethod
    def is_available(self) -> bool:
        """Whether this tool is available on the system."""
        ...

    @property
    def config_file_name(self) -> str:
        """Configuration file name for this tool.

        Defaults to lowercase name with .md extension.
        Override in subclasses for custom file names.
        """
        return f"{self.name.lower().replace(' ', '-')}.md"

    @abstractmethod
    def configure(self, project_path: str, aurora_dir: str) -> None:
        """Configure Aurora for this tool.

        Args:
            project_path: Project root path
            aurora_dir: Aurora directory name (e.g., ".aurora")

        """
        ...
