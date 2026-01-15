"""Templates for Aurora configuration files.

This module provides template content for AGENTS.md, CLAUDE.md, project.md,
and Claude Code slash command files. Templates are rebranded from OpenSpec to Aurora.
"""

from .agents import AGENTS_TEMPLATE, get_agents_template
from .claude import CLAUDE_TEMPLATE, get_claude_template
from .commands import COMMAND_TEMPLATES, get_all_command_templates, get_command_template
from .headless import PROMPT_TEMPLATE, SCRATCHPAD_TEMPLATE
from .project import PROJECT_TEMPLATE, get_project_template


__all__ = [
    "AGENTS_TEMPLATE",
    "CLAUDE_TEMPLATE",
    "COMMAND_TEMPLATES",
    "PROJECT_TEMPLATE",
    "PROMPT_TEMPLATE",
    "SCRATCHPAD_TEMPLATE",
    "get_agents_template",
    "get_all_command_templates",
    "get_claude_template",
    "get_command_template",
    "get_project_template",
]
