"""Droid configurator."""

from .base import BaseConfigurator


class DroidConfigurator(BaseConfigurator):
    """Configurator for Droid."""

    @property
    def name(self) -> str:
        """Human-readable tool name."""
        return "Droid"

    @property
    def config_file_name(self) -> str:
        """Name of configuration file."""
        return "DROID.md"

    async def get_template_content(self, aurora_dir: str) -> str:
        """Get Droid template content.

        Args:
            aurora_dir: Name of Aurora directory

        Returns:
            Template content for DROID.md
        """
        return f"""# Aurora Planning Instructions for Droid

These instructions enable Droid to work with Aurora's planning system.

## Directory Structure

Aurora stores plans in `{aurora_dir}/plans/`:
- `{aurora_dir}/plans/active/` - Active plans
- `{aurora_dir}/plans/archive/` - Archived plans

## Planning Commands

```bash
aur init                        # Initialize Aurora
aur plan create "Goal"          # Create new plan
aur plan list                   # List all plans
aur plan view <plan-id>         # View plan details
aur plan archive <plan-id>      # Archive plan
```

## Workflow Integration

When working with Aurora plans:
1. Read plan files in `{aurora_dir}/plans/active/<plan-id>/`
2. Follow task checklist in `tasks.md`
3. Reference requirements from `prd.md`
4. Update task progress as you work

Always check for Aurora plans when the user mentions:
- Plan IDs (e.g., "0001", "0001-oauth-auth")
- "work on plan", "continue plan", "implement plan"
"""
