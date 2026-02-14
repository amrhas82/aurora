"""Prompt-to-tasks.md decomposition via LLM.

Standalone function that converts a natural language prompt into a tasks.md
markdown string with Agent and Depends sub-bullets. No SOAR dependency.
"""

import logging
from typing import Any

from aurora_reasoning.llm_client import LLMClient


logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = """\
You are a task decomposition assistant. Given a user prompt, break it into \
concrete, actionable tasks for parallel execution.

Output JSON with this schema:
{
  "tasks": [
    {
      "id": "1.0",
      "description": "Clear, actionable description",
      "agent": "agent-name or null",
      "depends_on": ["1.0"]  // task IDs this depends on, or empty list
    }
  ]
}

Rules:
- Use sequential IDs: 1.0, 2.0, 3.0, etc.
- Only add depends_on when a task genuinely needs output from another task
- Keep descriptions specific and self-contained
- Assign agents from the available list when a clear match exists
- Use null for agent when no specific agent is needed
"""


def decompose_prompt_to_tasks_md(
    llm_client: LLMClient,
    prompt: str,
    available_agents: list[str] | None = None,
) -> str:
    """Decompose a natural language prompt into tasks.md content.

    Args:
        llm_client: LLM client for generation
        prompt: User's natural language prompt
        available_agents: List of available agent names (optional)

    Returns:
        Markdown string in tasks.md format

    """
    system = _SYSTEM_PROMPT
    if available_agents:
        system += f"\nAvailable agents: {', '.join(available_agents)}"

    result = llm_client.generate_json(
        prompt=prompt,
        system=system,
        temperature=0.3,
    )

    return _json_to_tasks_md(result, prompt)


def _json_to_tasks_md(data: dict[str, Any], prompt: str) -> str:
    """Convert JSON task list to tasks.md markdown format.

    Args:
        data: JSON dict with "tasks" key containing task objects
        prompt: Original prompt (used as goal header)

    Returns:
        Markdown formatted tasks.md string

    """
    lines = ["# Tasks: decomposed from prompt", "", f"Goal: {prompt}", "", "## Implementation Tasks", ""]

    tasks = data.get("tasks", [])
    for task in tasks:
        tid = task.get("id", "0")
        desc = task.get("description", "")
        agent = task.get("agent")
        depends = task.get("depends_on", [])

        lines.append(f"- [ ] {tid} {desc}")

        if agent:
            lines.append(f"  - Agent: @{agent}")
        if depends:
            lines.append(f"  - Depends: {', '.join(str(d) for d in depends)}")

        lines.append("")

    return "\n".join(lines)
