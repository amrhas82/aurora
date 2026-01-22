"""Conventional directory paths for all 20 AI coding tools.

Each tool has standard locations for:
- agents: Where agent persona markdown files are stored (global, e.g., ~/.claude/agents)
- commands: Where user slash/custom commands are stored (global, e.g., ~/.claude/commands)
- slash_commands: Where project-local slash commands are written (e.g., .claude/commands/aur/)
- mcp: Where MCP server configurations are stored

These paths are used by:
- Agent discovery (scanning for available agents)
- Slash command generation (knowing where to write)
- MCP configuration (future)
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ToolPaths:
    """Conventional paths for an AI coding tool.

    Attributes:
        tool_id: Tool identifier (kebab-case)
        agents: Global path to agents directory (e.g., "~/.claude/agents")
        commands: Global path to user commands directory (e.g., "~/.claude/commands")
        slash_commands: Project-local path for Aurora slash commands (e.g., ".claude/commands/aur")
        mcp: Path to MCP configuration (e.g., "~/.claude/mcp_servers.json")

    """

    tool_id: str
    agents: str | None = None
    commands: str | None = None
    slash_commands: str | None = None
    mcp: str | None = None


# Registry of all 20 tools with their conventional paths
# Sources:
# - OpenCode: https://opencode.ai/docs/config/ - ~/.config/opencode/agent/
# - Factory Droid: https://docs.factory.ai/cli/configuration/custom-droids - ~/.factory/droids/
# - Cline: https://docs.cline.bot/cline-cli/cli-reference - ~/.cline/
# - Cursor: https://cursor.com/docs/cli/reference/configuration - ~/.cursor/
# - Codex: https://developers.openai.com/codex/config-advanced/ - .codex/ (project-local)
# - Amazon Q: https://builder.aws.com/... - ~/.aws/amazonq/cli-agents/
#
# slash_commands paths are from the configurator FILE_PATHS definitions
TOOL_PATHS: dict[str, ToolPaths] = {
    "amazon-q": ToolPaths(
        tool_id="amazon-q",
        agents="~/.aws/amazonq/cli-agents",
        commands="~/.amazonq/commands",
        slash_commands=".amazonq/prompts",
        mcp="~/.aws/amazonq/mcp.json",
    ),
    "antigravity": ToolPaths(
        tool_id="antigravity",
        agents="~/.config/antigravity/agents",
        commands="~/.config/antigravity/commands",
        slash_commands=".agent/workflows",
    ),
    "auggie": ToolPaths(
        tool_id="auggie",
        agents="~/.config/auggie/agents",
        commands="~/.config/auggie/commands",
        slash_commands=".augment/commands",
    ),
    "claude": ToolPaths(
        tool_id="claude",
        agents="~/.claude/agents",
        commands="~/.claude/commands",
        slash_commands=".claude/commands/aur",
        mcp="~/.claude/mcp_servers.json",
    ),
    "cline": ToolPaths(
        tool_id="cline",
        agents="~/.cline/agents",
        commands="~/.cline/commands",
        slash_commands=".clinerules/workflows",
        mcp="~/.cline/mcp_settings.json",
    ),
    "codebuddy": ToolPaths(
        tool_id="codebuddy",
        agents="~/.config/codebuddy/agents",
        commands="~/.config/codebuddy/commands",
        slash_commands=".codebuddy/commands/aurora",
    ),
    "codex": ToolPaths(
        tool_id="codex",
        # Codex uses project-local .codex/ and AGENTS.md, not global agents
        agents="~/.codex/agents",
        commands="~/.codex/commands",
        slash_commands=".codex/prompts",
    ),
    "costrict": ToolPaths(
        tool_id="costrict",
        agents="~/.config/costrict/agents",
        commands="~/.config/costrict/commands",
        slash_commands=".cospec/aurora/commands",
    ),
    "crush": ToolPaths(
        tool_id="crush",
        agents="~/.config/crush/agents",
        commands="~/.config/crush/commands",
        slash_commands=".crush/commands/aurora",
    ),
    "cursor": ToolPaths(
        tool_id="cursor",
        agents="~/.cursor/agents",
        commands="~/.cursor/commands",
        slash_commands=".cursor/commands",
    ),
    "factory": ToolPaths(
        tool_id="factory",
        # Factory Droid uses "droids" not "agents"
        agents="~/.factory/droids",
        commands="~/.factory/commands",
        slash_commands=".factory/commands",
    ),
    "gemini": ToolPaths(
        tool_id="gemini",
        agents="~/.config/gemini-cli/agents",
        commands="~/.config/gemini-cli/commands",
        slash_commands=".gemini/commands/aurora",
    ),
    "github-copilot": ToolPaths(
        tool_id="github-copilot",
        agents="~/.config/github-copilot/agents",
        commands="~/.config/github-copilot/commands",
        slash_commands=".github/prompts",
    ),
    "iflow": ToolPaths(
        tool_id="iflow",
        agents="~/.config/iflow/agents",
        commands="~/.config/iflow/commands",
        slash_commands=".iflow/commands",
    ),
    "kilocode": ToolPaths(
        tool_id="kilocode",
        agents="~/.config/kilocode/agents",
        commands="~/.config/kilocode/commands",
        slash_commands=".kilocode/workflows",
    ),
    "opencode": ToolPaths(
        tool_id="opencode",
        # OpenCode uses "agent" (singular) per docs
        agents="~/.config/opencode/agent",
        commands="~/.config/opencode/commands",
        slash_commands=".opencode/command",
    ),
    "qoder": ToolPaths(
        tool_id="qoder",
        agents="~/.config/qoder/agents",
        commands="~/.config/qoder/commands",
        slash_commands=".qoder/commands/aurora",
    ),
    "qwen": ToolPaths(
        tool_id="qwen",
        agents="~/.config/qwen-coder/agents",
        commands="~/.config/qwen-coder/commands",
        slash_commands=".qwen/commands",
    ),
    "roocode": ToolPaths(
        tool_id="roocode",
        agents="~/.config/roocode/agents",
        commands="~/.config/roocode/commands",
        slash_commands=".roo/commands",
    ),
    "windsurf": ToolPaths(
        tool_id="windsurf",
        agents="~/.windsurf/agents",
        commands="~/.windsurf/commands",
        slash_commands=".windsurf/workflows",
    ),
}


def get_all_agent_paths() -> list[str]:
    """Get all agent discovery paths from the registry.

    Returns:
        List of agent directory paths (unexpanded, with ~)

    """
    return [tp.agents for tp in TOOL_PATHS.values() if tp.agents]


def get_tool_paths(tool_id: str) -> ToolPaths | None:
    """Get paths for a specific tool.

    Args:
        tool_id: Tool identifier (case-insensitive, spaces converted to dashes)

    Returns:
        ToolPaths for the tool, or None if not found

    """
    normalized = tool_id.lower().replace(" ", "-")
    return TOOL_PATHS.get(normalized)


def get_all_tools() -> list[str]:
    """Get list of all tool IDs.

    Returns:
        List of tool identifiers

    """
    return list(TOOL_PATHS.keys())
