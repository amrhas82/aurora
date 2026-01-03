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
        return f"""<!-- AURORA:START -->
# Aurora Planning Instructions

These instructions are for AI assistants working in this project.

Always open `@{aurora_dir}/plans/active/` when the request:
- Mentions planning or proposals (words like proposal, spec, change, plan)
- Introduces new capabilities, breaking changes, architecture shifts
- Sounds ambiguous and you need project context before coding

Use `@{aurora_dir}/project.md` to learn:
- Project overview and tech stack
- Coding conventions and standards
- Architecture decisions

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

```bash
# Initialize Aurora (first time setup)
aur init

# Create a new plan
aur plan create "Goal description"

# List all plans
aur plan list

# View plan details
aur plan view <plan-id>

# Archive a plan
aur plan archive <plan-id>

# Search indexed code
aur mem search "query"
```

## Workflow

1. **Create Plan**: `aur plan create "Implement OAuth authentication"`
   - Generates plan structure in `{aurora_dir}/plans/active/NNNN-slug/`
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

Keep this managed block so 'aur init --config' can refresh instructions.
<!-- AURORA:END -->
"""
