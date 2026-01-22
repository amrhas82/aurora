"""Update command for Aurora planning system.

Simplified version ported from OpenSpec src/core/update.ts
Focuses on updating AGENTS.md file with latest instructions.

Full configurator support (Phase 7) to be added later.
"""

from pathlib import Path

from aurora_planning.templates.agents import AGENTS_TEMPLATE


class UpdateCommand:
    """Command to update OpenSpec instruction files."""

    def execute(self, project_path: str = ".", verbose: bool = False) -> None:
        """Execute the update command.

        Updates the .aurora/plans/AGENTS.md file with the latest template content.
        In the full implementation, this would also update AI tool configuration
        files (CLAUDE.md, QWEN.md, etc.) with managed blocks.

        Args:
            project_path: Path to the project root (default: current directory)
            verbose: Enable verbose output (default: False)

        """
        project = Path(project_path).resolve()
        openspec_dir = project / ".aurora/plans"

        # 1. Check openspec directory exists
        if not openspec_dir.is_dir():
            raise RuntimeError("No Aurora plans directory found. Run 'aur init' first.")

        # 2. Update .aurora/plans/AGENTS.md (full replacement)
        agents_path = openspec_dir / "AGENTS.md"

        if verbose:
            status = "Updating" if agents_path.exists() else "Creating"
            print(f"{status} {agents_path}")

        agents_path.write_text(AGENTS_TEMPLATE)

        # Track what was updated
        updated_files = [".aurora/plans/AGENTS.md"]

        if verbose:
            print(f"✓ Updated {agents_path}")

        # 3. In full implementation, would update AI tool config files here
        # This requires configurators from Phase 7
        # For now, we just update AGENTS.md

        # Print summary
        summary_parts = []
        summary_parts.append(f"Updated Aurora instructions ({', '.join(updated_files)})")

        print(" | ".join(summary_parts))
