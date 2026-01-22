"""TaskExecutor for executing tasks with agent dispatch.

Executes tasks sequentially, dispatching to appropriate agents via spawner,
and marking tasks complete in tasks.md file upon successful execution.
"""

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from aurora_spawner import SpawnResult, SpawnTask, spawn
from implement.models import ParsedTask


@dataclass
class ExecutionResult:
    """Result of executing a single task.

    Attributes:
        task_id: Task identifier
        success: Whether execution succeeded
        output: Execution output
        error: Error message if failed
        skipped: Whether task was skipped (already completed)

    """

    task_id: str
    success: bool
    output: str
    error: str | None = None
    skipped: bool = False


class TaskExecutor:
    """Executor for parsed tasks with agent dispatch.

    Executes tasks sequentially:
    - agent="self": Direct execution (placeholder for now)
    - agent!="self": Dispatch via aurora-spawner spawn()
    - Mark tasks complete in tasks.md after successful execution
    """

    def __init__(self, config: dict[str, Any] | None = None):
        """Initialize TaskExecutor.

        Args:
            config: Optional configuration dict (for tool/model settings)

        """
        self.config = config or {}

    async def execute(self, tasks: list[ParsedTask], tasks_file: Path) -> list[ExecutionResult]:
        """Execute tasks sequentially.

        Args:
            tasks: List of parsed tasks to execute
            tasks_file: Path to tasks.md file (for marking complete)

        Returns:
            List of ExecutionResult for each task

        """
        results: list[ExecutionResult] = []

        for task in tasks:
            # Skip already completed tasks
            if task.completed:
                results.append(
                    ExecutionResult(
                        task_id=task.id,
                        success=True,
                        output="Task already completed",
                        skipped=True,
                    ),
                )
                continue

            # Execute task based on agent
            if task.agent == "self":
                result = await self._execute_self_task(task)
            else:
                result = await self._execute_agent_task(task)

            results.append(result)

            # Mark task complete if successful
            if result.success and not result.skipped:
                self._mark_task_complete(tasks_file, task.id)

        return results

    async def _execute_self_task(self, task: ParsedTask) -> ExecutionResult:
        """Execute task directly (self-execution placeholder).

        Args:
            task: Task to execute

        Returns:
            ExecutionResult with success status

        """
        # Placeholder for direct execution
        # In the future, this could execute Python code directly
        return ExecutionResult(
            task_id=task.id,
            success=True,
            output=f"Self-executed task: {task.description}",
        )

    async def _execute_agent_task(self, task: ParsedTask) -> ExecutionResult:
        """Execute task by dispatching to agent via spawner.

        Args:
            task: Task to execute with agent!="self"

        Returns:
            ExecutionResult with agent output

        """
        # Build prompt for agent
        prompt = self._build_agent_prompt(task)

        # Create spawn task
        spawn_task = SpawnTask(
            prompt=prompt,
            agent=task.agent,
            timeout=300,  # 5 minute default timeout
        )

        # Execute via spawner
        try:
            result: SpawnResult = await spawn(
                spawn_task.prompt,
                agent=spawn_task.agent,
                timeout=spawn_task.timeout,
                tool=self.config.get("tool"),
                model=task.model or self.config.get("model"),
            )

            return ExecutionResult(
                task_id=task.id,
                success=result.success,
                output=result.output,
                error=result.error,
            )
        except Exception as e:
            return ExecutionResult(
                task_id=task.id,
                success=False,
                output="",
                error=f"Spawn error: {str(e)}",
            )

    def _build_agent_prompt(self, task: ParsedTask) -> str:
        """Build prompt for agent dispatch.

        Args:
            task: Task with agent and description

        Returns:
            Prompt string for agent

        """
        # Format: task description with agent context
        prompt = f"""As {task.agent}, complete this task:

Task ID: {task.id}
Description: {task.description}

Please execute this task and provide a summary of what was accomplished."""

        return prompt

    def _mark_task_complete(self, tasks_file: Path, task_id: str) -> None:
        """Mark task as complete in tasks.md file.

        Args:
            tasks_file: Path to tasks.md file
            task_id: Task ID to mark complete

        """
        try:
            content = tasks_file.read_text(encoding="utf-8")

            # Pattern to match the specific task line
            # Handles: - [ ] 1. or - [ ] 1.1 with flexible whitespace
            pattern = re.compile(
                rf"^(\s*[-*]\s*\[\s*)([ ])(\s*\]\s*{re.escape(task_id)}\.?\s+.+)$",
                re.MULTILINE,
            )

            # Replace [ ] with [x] for this task ID
            updated_content = pattern.sub(r"\1x\3", content)

            # Write back to file
            tasks_file.write_text(updated_content, encoding="utf-8")

        except Exception as e:
            # Log error but don't fail execution
            print(f"Warning: Could not mark task {task_id} complete: {e}")
