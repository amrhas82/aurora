"""Agent recovery module for handling agent execution failures."""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Callable


if TYPE_CHECKING:
    from aurora_cli.policies.models import RecoveryConfig

logger = logging.getLogger(__name__)


@dataclass
class RecoveryResult:
    """Result of agent execution with recovery."""

    success: bool
    output: str
    error: str | None = None
    retry_count: int = 0
    fallback_used: bool = False
    original_agent: str | None = None
    metadata: dict[str, Any] | None = None


class AgentRecovery:
    """Handle agent execution with retry and fallback logic."""

    def __init__(self, config: RecoveryConfig):
        """Initialize agent recovery handler.

        Args:
            config: Recovery configuration

        """
        self.timeout = config.timeout_seconds
        self.max_retries = config.max_retries
        self.fallback_enabled = config.fallback_to_llm

    async def execute_with_recovery(
        self,
        agent_id: str,
        task: str,
        execute_fn: Callable,
        on_progress: Callable[[int, int, str], None] | None = None,
    ) -> RecoveryResult:
        """Execute agent with retry and fallback logic.

        Args:
            agent_id: Agent identifier
            task: Task description/prompt
            execute_fn: Async function to execute the agent. Should accept (agent_id, task, timeout)
            on_progress: Optional progress callback (attempt, max_attempts, status)

        Returns:
            RecoveryResult with execution details

        """
        max_attempts = self.max_retries + 1  # Initial attempt + retries
        original_agent = agent_id

        # Attempt initial execution + retries
        for attempt in range(max_attempts):
            attempt_num = attempt + 1
            logger.debug(f"Agent execution attempt {attempt_num}/{max_attempts} for {agent_id}")

            if on_progress:
                status = "Retrying" if attempt > 0 else "Starting"
                on_progress(attempt_num, max_attempts, status)

            try:
                result = await asyncio.wait_for(
                    execute_fn(agent_id, task, self.timeout),
                    timeout=self.timeout,
                )

                if result.get("success", False):
                    logger.debug(f"Agent {agent_id} succeeded on attempt {attempt_num}")
                    return RecoveryResult(
                        success=True,
                        output=result.get("output", ""),
                        retry_count=attempt,
                        fallback_used=False,
                        original_agent=original_agent,
                        metadata=result.get("metadata", {}),
                    )

                logger.debug(
                    f"Agent {agent_id} failed on attempt {attempt_num}: {result.get('error')}",
                )

            except asyncio.TimeoutError:
                logger.debug(
                    f"Agent {agent_id} timed out on attempt {attempt_num} ({self.timeout}s)",
                )
            except Exception as e:
                logger.warning(f"Agent {agent_id} exception on attempt {attempt_num}: {e}")

        # All attempts failed, try fallback if enabled
        if self.fallback_enabled:
            logger.info(
                f"Agent {agent_id} failed after {max_attempts} attempts, using LLM fallback",
            )

            if on_progress:
                on_progress(max_attempts + 1, max_attempts + 1, "Fallback to LLM")

            try:
                result = await self.execute_fallback(task, execute_fn)
                return RecoveryResult(
                    success=result.get("success", False),
                    output=result.get("output", ""),
                    error=result.get("error"),
                    retry_count=max_attempts,
                    fallback_used=True,
                    original_agent=original_agent,
                    metadata=result.get("metadata", {}),
                )
            except Exception as e:
                logger.error(f"Fallback to LLM also failed: {e}")
                return RecoveryResult(
                    success=False,
                    output="",
                    error=f"All recovery attempts failed: {str(e)}",
                    retry_count=max_attempts,
                    fallback_used=True,
                    original_agent=original_agent,
                )

        # No fallback, return failure
        return RecoveryResult(
            success=False,
            output="",
            error=f"Agent {agent_id} failed after {max_attempts} attempts",
            retry_count=max_attempts,
            fallback_used=False,
            original_agent=original_agent,
        )

    async def execute_fallback(self, task: str, execute_fn: Callable) -> dict[str, Any]:
        """Execute task with direct LLM call as last resort.

        Args:
            task: Task description/prompt
            execute_fn: Async function to execute. Should accept (None, task, timeout) for LLM

        Returns:
            Dict with success, output, error keys

        """
        try:
            # Execute with agent_id=None to indicate direct LLM call
            result = await asyncio.wait_for(
                execute_fn(None, task, self.timeout),
                timeout=self.timeout,
            )
            return result
        except asyncio.TimeoutError:
            return {"success": False, "output": "", "error": "LLM fallback timed out"}
        except Exception as e:
            return {"success": False, "output": "", "error": f"LLM fallback failed: {str(e)}"}
