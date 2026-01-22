"""Base class for tool configurators."""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Protocol


class ToolConfigurator(Protocol):
    """Protocol for tool configurators.

    Tool configurators are responsible for generating configuration
    files for specific AI coding tools (Claude Code, OpenCode, etc.)
    to enable Aurora planning system integration.

    Attributes:
        name: Human-readable tool name (e.g., "Claude Code")
        config_file_name: Name of config file (e.g., "CLAUDE.md")
        is_available: Whether this tool is available/supported

    """

    name: str
    config_file_name: str
    is_available: bool

    async def configure(
        self,
        project_path: Path,
        aurora_dir: str,
    ) -> None:
        """Configure the tool with Aurora integration.

        Args:
            project_path: Root path of the project
            aurora_dir: Name of Aurora directory (e.g., ".aurora")

        """
        ...


class BaseConfigurator(ABC):
    """Base implementation for tool configurators.

    Provides common functionality for writing configuration files
    with managed blocks and markers.
    """

    AURORA_MARKERS = {
        "start": "<!-- AURORA:START -->",
        "end": "<!-- AURORA:END -->",
    }

    def __init__(self) -> None:
        """Initialize the configurator."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable tool name."""
        ...

    @property
    @abstractmethod
    def config_file_name(self) -> str:
        """Name of configuration file."""
        ...

    @property
    def is_available(self) -> bool:
        """Whether this tool is available.

        Can be overridden to check for tool-specific requirements.
        """
        return True

    @abstractmethod
    async def get_template_content(self, aurora_dir: str) -> str:
        """Get the template content for this tool.

        Args:
            aurora_dir: Name of Aurora directory

        Returns:
            Template content to write

        """
        ...

    async def configure(
        self,
        project_path: Path,
        aurora_dir: str,
    ) -> None:
        """Configure the tool with Aurora integration.

        Args:
            project_path: Root path of the project
            aurora_dir: Name of Aurora directory

        """
        file_path = project_path / self.config_file_name
        content = await self.get_template_content(aurora_dir)

        await self._update_file_with_markers(
            file_path,
            content,
            self.AURORA_MARKERS["start"],
            self.AURORA_MARKERS["end"],
        )

    async def _update_file_with_markers(
        self,
        file_path: Path,
        new_content: str,
        start_marker: str,
        end_marker: str,
    ) -> None:
        """Update file with content between markers.

        If the file exists and has markers, only the content between
        markers is replaced. Otherwise, the entire content is written.

        Args:
            file_path: Path to file to update
            new_content: New content to insert
            start_marker: Start marker string
            end_marker: End marker string

        """
        if file_path.exists():
            # Read existing content
            existing = file_path.read_text(encoding="utf-8")

            # Check if markers exist
            if start_marker in existing and end_marker in existing:
                # Replace content between markers
                start_idx = existing.index(start_marker)
                end_idx = existing.index(end_marker) + len(end_marker)

                # Build new content with markers
                managed_block = f"{start_marker}\n{new_content}\n{end_marker}"
                updated = existing[:start_idx] + managed_block + existing[end_idx:]

                file_path.write_text(updated, encoding="utf-8")
                return
            # File exists but no markers - prepend stub to preserve existing content
            managed_block = f"{start_marker}\n{new_content}\n{end_marker}\n\n"
            file_path.write_text(managed_block + existing, encoding="utf-8")
            return

        # File doesn't exist - write entire content with markers
        managed_block = f"{start_marker}\n{new_content}\n{end_marker}\n"
        file_path.write_text(managed_block, encoding="utf-8")
