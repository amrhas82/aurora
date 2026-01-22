"""Configuration constants for Aurora planning system.

Defines markers, directory names, and AI tool options.
"""

from dataclasses import dataclass

# Directory name for Aurora planning
AURORA_DIR_NAME = "aurora"

# Markers for managed content in files
AURORA_MARKERS = {
    "start": "<!-- AURORA:START -->",
    "end": "<!-- AURORA:END -->",
}


@dataclass
class AIToolOption:
    """Configuration for an AI coding tool.

    Attributes:
        name: Display name of the tool
        value: ID value for the tool
        available: Whether the tool is available
        success_label: Optional label to show on success

    """

    name: str
    value: str
    available: bool
    success_label: str | None = None


# Available AI coding tools
AI_TOOLS: list[AIToolOption] = [
    AIToolOption("Amazon Q Developer", "amazon-q", True, "Amazon Q Developer"),
    AIToolOption("Antigravity", "antigravity", True, "Antigravity"),
    AIToolOption("Auggie (Augment CLI)", "auggie", True, "Auggie"),
    AIToolOption("Claude Code", "claude", True, "Claude Code"),
    AIToolOption("Cline", "cline", True, "Cline"),
    AIToolOption("Codex", "codex", True, "Codex"),
    AIToolOption("CodeBuddy Code (CLI)", "codebuddy", True, "CodeBuddy Code"),
    AIToolOption("CoStrict", "costrict", True, "CoStrict"),
    AIToolOption("Crush", "crush", True, "Crush"),
    AIToolOption("Cursor", "cursor", True, "Cursor"),
    AIToolOption("Factory Droid", "factory", True, "Factory Droid"),
    AIToolOption("Gemini CLI", "gemini", True, "Gemini CLI"),
    AIToolOption("GitHub Copilot", "github-copilot", True, "GitHub Copilot"),
    AIToolOption("iFlow", "iflow", True, "iFlow"),
    AIToolOption("Kilo Code", "kilocode", True, "Kilo Code"),
    AIToolOption("OpenCode", "opencode", True, "OpenCode"),
    AIToolOption("Qoder (CLI)", "qoder", True, "Qoder"),
    AIToolOption("Qwen Code", "qwen", True, "Qwen Code"),
    AIToolOption("RooCode", "roocode", True, "RooCode"),
    AIToolOption("Windsurf", "windsurf", True, "Windsurf"),
    AIToolOption(
        "AGENTS.md (works with Amp, VS Code, …)",
        "agents",
        False,
        "your AGENTS.md-compatible assistant",
    ),
]


@dataclass
class AuroraConfig:
    """Aurora configuration.

    Attributes:
        ai_tools: List of AI tool IDs to configure

    """

    ai_tools: list[str]
