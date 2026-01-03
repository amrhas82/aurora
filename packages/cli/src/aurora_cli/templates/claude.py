"""CLAUDE.md template for Claude Code integration.

Provides the template for CLAUDE.md file that integrates Aurora planning with Claude Code.
This is a stub that references the main AGENTS.md instructions.
"""

CLAUDE_TEMPLATE = """<!-- AURORA:START -->
# Aurora Instructions

These instructions enable Aurora planning system integration with Claude Code.

Always open `@.aurora/AGENTS.md` when working with plans or capabilities.

Use `aur` commands to:
- Create plans: `aur plan create "Goal"`
- List plans: `aur plan list`
- Show plans: `aur plan show <plan-id>`
- Archive plans: `aur plan archive <plan-id>`
- Search code: `aur mem search "<query>"`

Keep this managed block so 'aur init --config' can refresh the instructions.
<!-- AURORA:END -->
"""


def get_claude_template() -> str:
    """Get the CLAUDE.md template.

    Returns:
        CLAUDE.md template string
    """
    return CLAUDE_TEMPLATE
