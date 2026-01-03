"""Universal AGENTS.md configurator."""

from .base import BaseConfigurator


class AgentsStandardConfigurator(BaseConfigurator):
    """Configurator for universal AGENTS.md stub.

    This creates a root-level AGENTS.md file that can be used
    by any AI coding tool that supports the AGENTS.md convention.
    """

    @property
    def name(self) -> str:
        """Human-readable tool name."""
        return "Universal AGENTS.md"

    @property
    def config_file_name(self) -> str:
        """Name of configuration file."""
        return "AGENTS.md"

    async def get_template_content(self, aurora_dir: str) -> str:
        """Get universal AGENTS.md template content.

        Args:
            aurora_dir: Name of Aurora directory

        Returns:
            Template content for AGENTS.md
        """
        return f"""# Aurora Planning System

This project uses Aurora for structured planning and task management.

## Planning Commands

```bash
aur init                        # Initialize Aurora directory structure
aur plan create "Goal"          # Create a new plan
aur plan list                   # List all plans
aur plan view <plan-id>         # View plan details
aur plan archive <plan-id>      # Archive a completed plan
```

## Directory Structure

Plans are stored in `{aurora_dir}/plans/`:
- `{aurora_dir}/plans/active/` - Active plans being worked on
- `{aurora_dir}/plans/archive/` - Completed/archived plans

## Plan Structure

Each plan contains 8 files:
1. `plan.md` - High-level decomposition and subgoals
2. `prd.md` - Detailed requirements and specifications
3. `tasks.md` - Implementation checklist (GitHub Flavored Markdown)
4. `agents.json` - Machine-readable metadata
5-8. Four capability spec files in `specs/` directory

## Workflow

1. **Create**: `aur plan create "Implement feature X"`
   - Generates plan in `{aurora_dir}/plans/active/NNNN-slug/`
   - Plan ID format: `0001-implement-feature-x`

2. **Work**: Open the plan directory and follow `tasks.md`
   - Mark tasks complete with `[x]`
   - Reference requirements in `prd.md`

3. **Archive**: `aur plan archive 0001`
   - Moves to `{aurora_dir}/plans/archive/YYYY-MM-DD-NNNN-slug/`

## AI Assistant Integration

When the user mentions a plan ID or asks to work on a plan:
1. Check for plan in `{aurora_dir}/plans/active/<plan-id>/`
2. Read relevant plan files (plan.md, prd.md, tasks.md)
3. Follow the task checklist systematically
4. Update progress as you work

For more information, see the Aurora documentation.
"""
