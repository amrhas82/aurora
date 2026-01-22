"""Init command for Aurora planning system.

Ported from OpenSpec src/core/init.ts - SIMPLIFIED VERSION
Full AI tool configurator support deferred to Phase 7 (CLI Commands).

This version creates the core OpenSpec directory structure and basic files.
"""

from pathlib import Path

from aurora_planning.templates.agents import AGENTS_TEMPLATE
from aurora_planning.templates.project import PROJECT_TEMPLATE

# Aurora managed block markers
AURORA_START = "<!-- AURORA:START -->"
AURORA_END = "<!-- AURORA:END -->"

# Root stub instructions
ROOT_STUB_TEMPLATE = f"""{AURORA_START}
# Aurora Instructions

These instructions are for AI assistants working in this project.

Always open `@/.aurora/AGENTS.md` when the request:
- Mentions planning or proposals (words like plan, create, implement)
- Introduces new capabilities, breaking changes, or architecture shifts
- Sounds ambiguous and you need authoritative guidance before coding

Use `@/.aurora/AGENTS.md` to learn:
- How to create and work with plans
- Aurora workflow and conventions
- Project structure and guidelines

Keep this managed block so 'aur init --config' can refresh the instructions.

{AURORA_END}
"""


class InitCommand:
    """Command to initialize OpenSpec in a project."""

    def execute(self, target_path: str = ".") -> None:
        """Execute the init command.

        Args:
            target_path: Target directory path (default: current directory)

        """
        target = Path(target_path)
        openspec_dir = target / ".aurora" / "plans"

        # Determine if this is extend mode (openspec dir already exists)
        extend_mode = openspec_dir.exists()

        # Create directory structure
        self._create_directory_structure(openspec_dir)

        # Generate or update template files
        if extend_mode:
            self._ensure_template_files(openspec_dir)
        else:
            self._generate_files(openspec_dir)

        # Create or update root AGENTS.md stub
        self._configure_root_stub(target)

        # Success message
        if extend_mode:
            print("\\nAurora planning updated successfully")
            print("Checked for missing files and refreshed root configuration")
        else:
            print("\\nAurora planning initialized successfully")
            print("Created directory structure and core files")

        print("\\nNext steps:")
        print("  - Review .aurora/plans/AGENTS.md for workflow instructions")
        print("  - Customize .aurora/plans/project.md with your project context")
        print("  - Use your AI assistant with @/.aurora/plans/AGENTS.md reference")

    def _create_directory_structure(self, openspec_dir: Path) -> None:
        """Create OpenSpec directory structure."""
        # Main directories
        openspec_dir.mkdir(parents=True, exist_ok=True)
        (openspec_dir / "specs").mkdir(exist_ok=True)
        (openspec_dir / "changes").mkdir(exist_ok=True)
        (openspec_dir / "changes" / "archive").mkdir(exist_ok=True)

    def _generate_files(self, openspec_dir: Path) -> None:
        """Generate template files (fresh init)."""
        # Create AGENTS.md from template
        agents_path = openspec_dir / "AGENTS.md"
        agents_path.write_text(AGENTS_TEMPLATE)

        # Create project.md from template
        project_path = openspec_dir / "project.md"
        project_path.write_text(PROJECT_TEMPLATE)

    def _ensure_template_files(self, openspec_dir: Path) -> None:
        """Ensure template files exist (extend mode)."""
        # Only recreate files that are missing (don't overwrite existing)
        agents_path = openspec_dir / "AGENTS.md"
        if not agents_path.exists():
            agents_path.write_text(AGENTS_TEMPLATE)

        project_path = openspec_dir / "project.md"
        if not project_path.exists():
            project_path.write_text(PROJECT_TEMPLATE)

    def _configure_root_stub(self, target: Path) -> None:
        """Create or update root AGENTS.md stub."""
        root_stub_path = target / "AGENTS.md"

        if root_stub_path.exists():
            # Update existing file with managed block
            content = root_stub_path.read_text()

            # Check if managed block already exists
            if AURORA_START in content:
                # Replace existing managed block
                start_idx = content.find(AURORA_START)
                end_idx = content.find(AURORA_END)

                if end_idx != -1:
                    # Replace the managed block
                    end_idx += len(AURORA_END)
                    new_content = content[:start_idx] + ROOT_STUB_TEMPLATE + content[end_idx:]
                else:
                    # Malformed - append new block
                    new_content = content + "\\n\\n" + ROOT_STUB_TEMPLATE
            else:
                # Prepend managed block to existing content
                new_content = ROOT_STUB_TEMPLATE + "\\n\\n" + content

            root_stub_path.write_text(new_content)
        else:
            # Create new file with just the managed block
            root_stub_path.write_text(ROOT_STUB_TEMPLATE)
