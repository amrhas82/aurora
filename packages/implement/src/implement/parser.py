"""TaskParser for parsing tasks.md files with agent metadata.

Ports and extends regex patterns from openspec-source task_progress.py
to support agent and model metadata extraction from HTML comments.
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

# Regex for metadata extraction from HTML comments
AGENT_METADATA_PATTERN = re.compile(r"<!--\s*agent:\s*([\w-]+)\s*-->", re.IGNORECASE)
MODEL_METADATA_PATTERN = re.compile(r"<!--\s*model:\s*([\w-]+)\s*-->", re.IGNORECASE)


class TaskParser:
    """Parser for tasks.md files with agent and model metadata.

    Parses markdown task lists with:
    - Checkbox syntax: - [ ] or - [x]
    - Task IDs: 1, 1.1, 2.3, etc.
    - Agent metadata: <!-- agent: agent-name -->
    - Model metadata: <!-- model: model-name -->

    Metadata comments apply to the task immediately preceding them.
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

            # Try to extract agent metadata
            agent_match = AGENT_METADATA_PATTERN.search(line)
            if agent_match and current_task_idx >= 0:
                tasks[current_task_idx].agent = agent_match.group(1)

            # Try to extract model metadata
            model_match = MODEL_METADATA_PATTERN.search(line)
            if model_match and current_task_idx >= 0:
                tasks[current_task_idx].model = model_match.group(1)

        return tasks
