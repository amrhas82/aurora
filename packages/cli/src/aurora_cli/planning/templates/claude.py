"""CLAUDE.md template for Claude Code integration.

Provides the template for CLAUDE.md file that integrates Aurora planning with Claude Code.
"""

CLAUDE_TEMPLATE = """<!-- AURORA:START -->
# Aurora Planning Instructions

These instructions enable Aurora planning system integration with Claude Code.

Always open `@/aurora/AGENTS.md` when working with plans or capabilities.

Use `aurora` commands to:
- Create plans: `aurora plan create`
- List plans: `aurora plan list`
- Validate plans: `aurora validate <plan-id>`
- Show plans: `aurora plan show <plan-id>`

Keep this managed block so 'aurora update' can refresh the instructions.

<!-- AURORA:END -->
"""


def get_claude_template() -> str:
    """Get the CLAUDE.md template.

    Returns:
        CLAUDE.md template string

    """
    return CLAUDE_TEMPLATE
