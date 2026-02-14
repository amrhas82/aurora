"""TaskParser for parsing tasks.md files with agent metadata.

Ports and extends regex patterns from openspec-source task_progress.py
to support agent and model metadata extraction from visible markdown sub-bullets.

Supported formats:
  - Agent: @code-developer       (with @ prefix)
  - Agent: code-developer        (without @ prefix)
  - Model: opus
"""

import re

from implement.models import ParsedTask


# Regex patterns for task checkboxes (ported from task_progress.py)
TASK_PATTERN = re.compile(r"^[-*]\s+\[[\sx]\]", re.IGNORECASE)
COMPLETED_TASK_PATTERN = re.compile(r"^[-*]\s+\[x\]", re.IGNORECASE)

# Regex for parsing task line components
# Handles: - [ ] 1. Description or - [ ] 1.1 Description (period after ID is optional)
# Very flexible whitespace handling: -[ ]3.Task and - [ ] 1. Task both work
TASK_LINE_PATTERN = re.compile(
    r"^\s*[-*]\s*\[\s*([ x])\s*\]\s*(\d+(?:\.\d+)?)\.?\s*(.+)$",
    re.IGNORECASE,
)

# Visible markdown metadata sub-bullets
# "- Agent: @code-developer" or "- Agent: code-developer"
AGENT_PATTERN = re.compile(r"^\s*[-*]\s+Agent:\s*@?([\w-]+)", re.IGNORECASE)
MODEL_PATTERN = re.compile(r"^\s*[-*]\s+Model:\s*([\w-]+)", re.IGNORECASE)
DEPENDS_PATTERN = re.compile(r"^\s*[-*]\s+Depends:\s*([\d.,\s]+)", re.IGNORECASE)


class TaskParser:
    """Parser for tasks.md files with agent and model metadata.

    Parses markdown task lists with:
    - Checkbox syntax: - [ ] or - [x]
    - Task IDs: 1, 1.1, 2.3, etc.
    - Agent metadata: - Agent: @agent-name (sub-bullet)
    - Model metadata: - Model: model-name (sub-bullet)

    Metadata sub-bullets apply to the task immediately preceding them.
    """

    def parse(self, content: str) -> list[ParsedTask]:
        """Parse tasks from markdown content.

        Args:
            content: Markdown content with task list

        Returns:
            List of ParsedTask objects in order of appearance

        """
        if not content or not content.strip():
            return []

        lines = content.split("\n")
        tasks: list[ParsedTask] = []
        current_task_idx = -1

        for line in lines:
            # Try to parse as task line
            task_match = TASK_LINE_PATTERN.match(line)
            if task_match:
                checkbox = task_match.group(1).strip().lower()
                task_id = task_match.group(2)
                description = task_match.group(3).strip()

                completed = checkbox == "x"

                task = ParsedTask(
                    id=task_id,
                    description=description,
                    agent="self",
                    model=None,
                    completed=completed,
                )

                tasks.append(task)
                current_task_idx = len(tasks) - 1
                continue

            # Try to extract agent metadata from sub-bullet
            agent_match = AGENT_PATTERN.match(line)
            if agent_match and current_task_idx >= 0:
                tasks[current_task_idx].agent = agent_match.group(1)

            # Try to extract model metadata from sub-bullet
            model_match = MODEL_PATTERN.match(line)
            if model_match and current_task_idx >= 0:
                tasks[current_task_idx].model = model_match.group(1)

            # Try to extract depends metadata from sub-bullet
            depends_match = DEPENDS_PATTERN.match(line)
            if depends_match and current_task_idx >= 0:
                dep_ids = [d.strip() for d in depends_match.group(1).split(",") if d.strip()]
                tasks[current_task_idx].depends_on = dep_ids

        return tasks
