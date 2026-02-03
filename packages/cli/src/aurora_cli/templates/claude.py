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

## MCP Tools Available

Aurora provides MCP tools for code intelligence (automatically available in Claude):

**`lsp`** - LSP code intelligence with 3 actions:
- `deadcode` - Find unused symbols, generates CODE_QUALITY_REPORT.md
- `impact` - Analyze symbol usage, show callers and risk level
- `check` - Quick usage check before editing

**`mem_search`** - Search indexed code with LSP enrichment:
- Returns code snippets with metadata (type, symbol, lines)
- Enriched with LSP context (used_by, called_by, calling)
- Includes git info (last_modified, last_author)

**When to use:**
- Before edits: Use `lsp check` to see usage impact
- Before refactoring: Use `lsp deadcode` or `lsp impact` to find all references
- Code search: Use `mem_search` instead of grep for semantic results
- After large changes: Use `lsp deadcode` to find orphaned code

Keep this managed block so 'aur init --config' can refresh the instructions.
"""


def get_claude_template() -> str:
    """Get the CLAUDE.md template.

    Returns:
        CLAUDE.md template string

    """
    return CLAUDE_TEMPLATE
