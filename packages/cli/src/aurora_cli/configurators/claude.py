"""Claude Code configurator."""

from .base import BaseConfigurator


class ClaudeConfigurator(BaseConfigurator):
    """Configurator for Claude Code (Anthropic's official CLI)."""

    @property
    def name(self) -> str:
        """Human-readable tool name."""
        return "Claude Code"

    @property
    def config_file_name(self) -> str:
        """Name of configuration file."""
        return "CLAUDE.md"

    async def get_template_content(self, aurora_dir: str) -> str:
        """Get Claude Code template content.

        Args:
            aurora_dir: Name of Aurora directory

        Returns:
            Template content for CLAUDE.md
        """
        return f"""# Aurora Planning Instructions

These instructions enable Claude Code to work with Aurora's planning system.

## Directory Structure

Aurora stores plans in `{aurora_dir}/plans/`:
- `{aurora_dir}/plans/active/` - Active plans being worked on
- `{aurora_dir}/plans/archive/` - Completed/archived plans

Each plan has:
- `plan.md` - High-level decomposition
- `prd.md` - Detailed requirements
- `tasks.md` - Implementation checklist
- `agents.json` - Machine-readable metadata

## Planning Commands

Use these commands to manage plans:

```bash
# Initialize Aurora directory structure
aur init

# Create a new plan
aur plan create "Goal description"

# List all plans
aur plan list

# View plan details
aur plan view <plan-id>

# Archive a plan
aur plan archive <plan-id>
```

## Workflow

1. **Create Plan**: `aur plan create "Implement OAuth authentication"`
   - Generates 8-file structure in `{aurora_dir}/plans/active/NNNN-slug/`
   - Plan ID format: `0001-oauth-auth`

2. **Review Plan**: `aur plan view 0001`
   - Shows goal, subgoals, tasks, agents

3. **Work on Tasks**: Edit `tasks.md`, mark items complete `[x]`

4. **Archive When Done**: `aur plan archive 0001`
   - Moves to `{aurora_dir}/plans/archive/YYYY-MM-DD-NNNN-slug/`

## Integration with AGENTS.md

When working on Aurora plans, Claude Code should:
- Read the plan files before starting work
- Follow task order in `tasks.md`
- Reference requirements from `prd.md`
- Update agents.json with progress

Always open `@{aurora_dir}/plans/active/<plan-id>/` when the request mentions:
- "work on plan", "implement plan", "continue with plan"
- A plan ID like "0001" or "0001-oauth-auth"
"""
