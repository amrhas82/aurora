"""TOML-format base class for slash command configurators.

Provides a base class for tools like Gemini CLI that use TOML configuration
files instead of markdown with YAML frontmatter.
"""

from abc import abstractmethod
from pathlib import Path

from aurora_cli.configurators.slash.base import AURORA_MARKERS, SlashCommandConfigurator


class TomlSlashCommandConfigurator(SlashCommandConfigurator):
    """Abstract base for TOML-format slash command configurators.

    TOML format tools embed all metadata in the TOML structure itself,
    with Aurora markers inside the prompt field's triple-quoted string.

    Example TOML output:
        description = "Create and manage project plans"

        prompt = \"\"\"
        <!-- AURORA:START -->
        Command body content here...
        <!-- AURORA:END -->
        \"\"\"
    """

    def get_frontmatter(self, _command_id: str) -> str | None:
        """Return None since TOML format doesn't use separate frontmatter.

        TOML embeds all metadata in its structure, so there's no separate
        frontmatter section like in markdown files.

        Args:
            command_id: Command identifier (unused for TOML)

        Returns:
            Always None for TOML format

        """
        return None

    @abstractmethod
    def get_description(self, command_id: str) -> str:
        """Get the description for a command.

        This is used to populate the TOML description field.

        Args:
            command_id: Command identifier (e.g., "plan", "query")

        Returns:
            Description string for the command

        """
        ...

    def generate_all(self, project_path: str, _aurora_dir: str) -> list[str]:
        """Generate or update all slash command files in TOML format.

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
                # Create new file with TOML format
                file_path.parent.mkdir(parents=True, exist_ok=True)
                toml_content = self._generate_toml(target.command_id, body)
                file_path.write_text(toml_content, encoding="utf-8")

            created_or_updated.append(target.path)

        return created_or_updated

    def _generate_toml(self, command_id: str, body: str) -> str:
        """Generate TOML content with markers inside the prompt field.

        Args:
            command_id: Command identifier
            body: Command body content

        Returns:
            Complete TOML file content

        """
        description = self.get_description(command_id)

        # TOML format with triple-quoted string for multi-line prompt
        # Markers are inside the prompt value
        return f'''description = "{description}"

prompt = """
{AURORA_MARKERS["start"]}
{body}
{AURORA_MARKERS["end"]}
"""
'''

    def _update_body(self, file_path: str, body: str) -> None:
        """Update the body content between Aurora markers in TOML format.

        This method handles the TOML-specific format where markers are
        inside the prompt triple-quoted string.

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
