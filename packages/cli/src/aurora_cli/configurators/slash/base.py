"""Base protocol for slash command configurators.

Defines the interface that all tool-specific slash command configurators must implement.
Ported from OpenSpec.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path

# Aurora managed block markers
AURORA_MARKERS = {
    "start": "<!-- AURORA:START -->",
    "end": "<!-- AURORA:END -->",
}


@dataclass
class SlashCommandTarget:
    """A slash command target with its path and metadata.

    Attributes:
        command_id: Command identifier (e.g., "plan", "query")
        path: Relative path to the command file
        kind: Always "slash" for slash commands

    """

    command_id: str
    path: str
    kind: str = "slash"


# All Aurora slash commands
ALL_COMMANDS = ["search", "get", "plan", "tasks", "implement", "archive"]


class SlashCommandConfigurator(ABC):
    """Abstract base for tool-specific slash command configurators.

    Each AI coding tool (Claude Code, OpenCode, etc.) has its own
    configurator that knows how to write slash commands for that tool.
    """

    @property
    @abstractmethod
    def tool_id(self) -> str:
        """Tool identifier (e.g., "claude", "opencode")."""
        ...

    @property
    def name(self) -> str:
        """Human-readable tool name.

        Defaults to capitalizing the tool_id. Override in subclasses
        for custom display names.
        """
        # Convert tool_id to title case: "amazon-q" -> "Amazon Q", "github-copilot" -> "GitHub Copilot"
        return self.tool_id.replace("-", " ").title()

    @property
    @abstractmethod
    def is_available(self) -> bool:
        """Whether this tool is available on the system."""
        ...

    def get_targets(self) -> list[SlashCommandTarget]:
        """Get all slash command targets for this tool.

        Returns:
            List of SlashCommandTarget objects

        """
        return [
            SlashCommandTarget(command_id=cmd_id, path=self.get_relative_path(cmd_id), kind="slash")
            for cmd_id in ALL_COMMANDS
        ]

    def generate_all(self, project_path: str, _aurora_dir: str) -> list[str]:
        """Generate or update all slash command files.

        Args:
            project_path: Project root path
            aurora_dir: Aurora directory name (e.g., ".aurora")

        Returns:
            List of created/updated file paths (relative to project_path)

        """
        created_or_updated: list[str] = []

        for target in self.get_targets():
            body = self.get_body(target.command_id)
            file_path = Path(project_path) / target.path

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

                # Add description line before markers (Claude Code may use first line after frontmatter)
                description = self.get_description(target.command_id)
                if description:
                    sections.append(f"\n{description}\n")

                sections.append(f"{AURORA_MARKERS['start']}\n{body}\n{AURORA_MARKERS['end']}")

                content = "\n".join(sections) + "\n"
                file_path.write_text(content, encoding="utf-8")

            created_or_updated.append(target.path)

        return created_or_updated

    def update_existing(self, project_path: str, _aurora_dir: str) -> list[str]:
        """Update existing slash command files only.

        Does not create new files.

        Args:
            project_path: Project root path
            aurora_dir: Aurora directory name

        Returns:
            List of updated file paths (relative to project_path)

        """
        updated: list[str] = []

        for target in self.get_targets():
            file_path = Path(project_path) / target.path

            if file_path.exists():
                body = self.get_body(target.command_id)
                self._update_body(str(file_path), body)
                updated.append(target.path)

        return updated

    @abstractmethod
    def get_relative_path(self, command_id: str) -> str:
        """Get the relative path for a slash command file.

        Args:
            command_id: Command identifier

        Returns:
            Relative path from project root

        """
        ...

    @abstractmethod
    def get_frontmatter(self, command_id: str) -> str | None:
        """Get the frontmatter for a slash command file.

        Args:
            command_id: Command identifier

        Returns:
            YAML frontmatter string or None

        """
        ...

    @abstractmethod
    def get_body(self, command_id: str) -> str:
        """Get the body content for a slash command.

        Args:
            command_id: Command identifier

        Returns:
            Command body content

        """
        ...

    def get_description(self, _command_id: str) -> str | None:
        """Get a brief description for a slash command.

        This is shown as the first line after frontmatter, before Aurora markers.
        Claude Code may use this as the skill description in listings.

        Args:
            command_id: Command identifier

        Returns:
            Brief description string or None

        """
        return None

    def resolve_absolute_path(self, project_path: str, command_id: str) -> str:
        """Resolve absolute path for a slash command file.

        Args:
            project_path: Project root path
            command_id: Command identifier

        Returns:
            Absolute path to the command file

        """
        rel = self.get_relative_path(command_id)
        return str(Path(project_path) / rel)

    def _update_body(self, file_path: str, body: str) -> None:
        """Update the body content between Aurora markers.

        Args:
            file_path: Path to the file to update
            body: New body content

        Raises:
            ValueError: If Aurora markers are missing

        """
        content = Path(file_path).read_text(encoding="utf-8")

        start_marker = AURORA_MARKERS["start"]
        end_marker = AURORA_MARKERS["end"]

        start_index = content.find(start_marker)
        end_index = content.find(end_marker)

        if start_index == -1 or end_index == -1 or end_index <= start_index:
            raise ValueError(f"Missing Aurora markers in {file_path}")

        before = content[: start_index + len(start_marker)]
        after = content[end_index:]
        updated_content = f"{before}\n{body}\n{after}"

        Path(file_path).write_text(updated_content, encoding="utf-8")
