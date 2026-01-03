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
        return f"""<!-- AURORA:START -->
# Aurora Instructions

These instructions are for AI assistants working in this project.

Always open `@{aurora_dir}/plans/active/` when the request:
- Mentions planning or proposals (words like proposal, spec, change, plan)
- Introduces new capabilities, breaking changes, architecture shifts
- Sounds ambiguous and you need project context before coding

Use `@{aurora_dir}/project.md` to learn:
- Project overview and tech stack
- Coding conventions and standards
- Architecture decisions

## Planning Commands

```bash
aur init                        # Initialize Aurora
aur plan create "Goal"          # Create new plan
aur plan list                   # List all plans
aur plan view <plan-id>         # View plan details
aur plan archive <plan-id>      # Archive plan
aur mem search "query"          # Search indexed code
```

## Workflow

When working with Aurora plans:
1. Read plan files in `{aurora_dir}/plans/active/<plan-id>/`
2. Follow task checklist in `tasks.md`
3. Reference requirements from `prd.md`
4. Update task progress as you work

Keep this managed block so 'aur init --config' can refresh instructions.
<!-- AURORA:END -->
"""
