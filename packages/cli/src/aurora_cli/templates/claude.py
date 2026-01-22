"""CLAUDE.md template for Claude Code integration.

Provides the template for CLAUDE.md file that integrates Aurora planning with Claude Code.
This is a stub that references the main AGENTS.md instructions.
"""

CLAUDE_TEMPLATE = """# Aurora Instructions

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
"""


def get_claude_template() -> str:
    """Get the CLAUDE.md template.

    Returns:
        CLAUDE.md template string

    """
    return CLAUDE_TEMPLATE
