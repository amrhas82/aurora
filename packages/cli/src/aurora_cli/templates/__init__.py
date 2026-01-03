"""Templates for Aurora configuration files.

This module provides template content for AGENTS.md, CLAUDE.md, and project.md files.
Templates are rebranded from OpenSpec to Aurora.
"""

from .agents import AGENTS_TEMPLATE, get_agents_template
from .claude import CLAUDE_TEMPLATE, get_claude_template
from .project import PROJECT_TEMPLATE, get_project_template

__all__ = [
    "AGENTS_TEMPLATE",
    "CLAUDE_TEMPLATE",
    "PROJECT_TEMPLATE",
    "get_agents_template",
    "get_claude_template",
    "get_project_template",
]
