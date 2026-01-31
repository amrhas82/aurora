"""Claude Code slash commands configurator.

Creates .claude/commands/aur/*.md files for Claude Code slash command integration.
"""

from pathlib import Path

from aurora_cli.templates.commands import get_all_command_templates


class ClaudeCommandsConfigurator:
    """Configurator for Claude Code slash commands.

    Creates slash command files in .claude/commands/aur/ that integrate
    Aurora CLI commands with Claude Code's slash command system.

    Unlike other configurators, this creates multiple files (one per command)
    in a subdirectory, rather than a single configuration file.
    """

    AURORA_MARKERS = {
        "start": "<!-- AURORA:START -->",
        "end": "<!-- AURORA:END -->",
    }

    @property
    def name(self) -> str:
        """Human-readable tool name."""
        return "Claude Commands"

    @property
    def config_file_name(self) -> str:
        """Base directory name for commands."""
        return ".claude/commands/aur"

    @property
    def is_available(self) -> bool:
        """Whether this configurator is available."""
        return True

    async def configure(
        self,
        project_path: Path,
        _aurora_dir: str,
    ) -> list[str]:
        """Configure Claude Code slash commands.

        Creates .claude/commands/aur/*.md files for each Aurora command.

        Args:
            project_path: Root path of the project
            aurora_dir: Name of Aurora directory (unused for commands)

        Returns:
            List of created command file names

        """
        commands_dir = project_path / ".claude" / "commands" / "aur"
        commands_dir.mkdir(parents=True, exist_ok=True)

        created_files: list[str] = []
        templates = get_all_command_templates()

        for command_name, template_content in templates.items():
            file_path = commands_dir / f"{command_name}.md"
            await self._update_file_with_markers(
                file_path,
                template_content,
                self.AURORA_MARKERS["start"],
                self.AURORA_MARKERS["end"],
            )
            created_files.append(f"{command_name}.md")

        return created_files

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
            new_content: New content to insert (already includes markers)
            start_marker: Start marker string
            end_marker: End marker string

        """
        if file_path.exists():
            existing = file_path.read_text(encoding="utf-8")

            # Check if markers exist
            if start_marker in existing and end_marker in existing:
                # Find the end marker position (to preserve content after markers)
                end_idx = existing.index(end_marker) + len(end_marker)

                # Extract frontmatter from new content
                if start_marker in new_content:
                    new_start_idx = new_content.index(start_marker)
                    new_end_idx = new_content.index(end_marker) + len(end_marker)
                    frontmatter = new_content[:new_start_idx]
                    managed_block = new_content[new_start_idx:new_end_idx]
                else:
                    frontmatter = ""
                    managed_block = f"{start_marker}\n{new_content}\n{end_marker}"

                # Preserve content before and after markers
                updated = frontmatter + managed_block + existing[end_idx:]
                file_path.write_text(updated, encoding="utf-8")
                return

        # File doesn't exist or no markers - write entire content
        # The template already includes markers, so write as-is
        file_path.write_text(new_content, encoding="utf-8")

    def get_command_list(self) -> list[str]:
        """Get list of available command names.

        Returns:
            List of command names that will be created

        """
        return list(get_all_command_templates().keys())
