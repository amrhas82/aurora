"""Bareagent bridge — subprocess management for soar-agent.js.

Spawns the Node.js orchestration script and communicates via JSONL over
stdin/stdout. Yields parsed events as they arrive.
"""

from __future__ import annotations

import asyncio
import json
import logging
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any, AsyncIterator

logger = logging.getLogger(__name__)

# Path to soar-agent.js relative to this file
_AGENT_SCRIPT = Path(__file__).parent / "soar_agent.js"

# Default timeout for the entire orchestration (5 minutes)
_DEFAULT_TIMEOUT = 300


@dataclass
class BareagentEvent:
    """A single JSONL event from soar-agent.js."""

    type: str
    data: dict[str, Any]

    @property
    def is_error(self) -> bool:
        return self.type == "error"

    @property
    def is_done(self) -> bool:
        return self.type == "synthesis:done"


class BareagentBridge:
    """Subprocess bridge to soar-agent.js.

    Usage:
        bridge = BareagentBridge(tool="claude", model="sonnet")
        async for event in bridge.run(query, context, complexity):
            handle(event)
    """

    def __init__(
        self,
        tool: str = "claude",
        model: str = "sonnet",
        timeout: int = _DEFAULT_TIMEOUT,
    ):
        self.tool = tool
        self.model = model
        self.timeout = timeout

    async def run(
        self,
        query: str,
        context: list[str],
        complexity: str,
    ) -> AsyncIterator[BareagentEvent]:
        """Run soar-agent.js and yield events.

        Args:
            query: User query
            context: Retrieved memory chunks as strings
            complexity: Complexity level (SIMPLE, MEDIUM, COMPLEX, CRITICAL)

        Yields:
            BareagentEvent for each JSONL line from the agent

        Raises:
            FileNotFoundError: If node or soar-agent.js not found
            RuntimeError: If the agent process fails

        """
        # Validate node is available
        node_path = shutil.which("node")
        if not node_path:
            raise FileNotFoundError("node not found in PATH. Install Node.js >= 18.")

        if not _AGENT_SCRIPT.exists():
            raise FileNotFoundError(f"soar-agent.js not found at {_AGENT_SCRIPT}")

        # Build the JSONL request
        request = json.dumps({
            "method": "soar",
            "params": {
                "query": query,
                "context": context,
                "complexity": complexity,
                "model": self.model,
                "tool": self.tool,
            },
        })

        logger.info(f"Starting soar-agent.js (tool={self.tool}, model={self.model})")

        # Spawn the Node.js process
        proc = await asyncio.create_subprocess_exec(
            node_path,
            str(_AGENT_SCRIPT),
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        try:
            # Send request and close stdin
            proc.stdin.write((request + "\n").encode())
            await proc.stdin.drain()
            proc.stdin.close()

            # Read events line by line with timeout
            async def read_events():
                while True:
                    line = await proc.stdout.readline()
                    if not line:
                        break
                    yield line.decode().strip()

            async for raw_line in read_events():
                if not raw_line:
                    continue

                try:
                    msg = json.loads(raw_line)
                    event = BareagentEvent(
                        type=msg.get("type", "unknown"),
                        data=msg.get("data", {}),
                    )
                    logger.debug(f"Event: {event.type}")
                    yield event

                    # Stop after synthesis or fatal error
                    if event.is_done or (event.is_error and "Fatal" in event.data.get("message", "")):
                        break

                except json.JSONDecodeError as e:
                    logger.warning(f"Invalid JSONL from agent: {e} — line: {raw_line[:200]}")

            # Read any remaining stderr for logging
            stderr_data = await proc.stderr.read()
            if stderr_data:
                for stderr_line in stderr_data.decode().strip().split("\n"):
                    if stderr_line:
                        logger.debug(f"[soar-agent stderr] {stderr_line}")

        except asyncio.TimeoutError:
            logger.error(f"soar-agent.js timed out after {self.timeout}s")
            proc.kill()
            yield BareagentEvent(
                type="error",
                data={"message": f"Agent timed out after {self.timeout}s"},
            )
        finally:
            # Ensure process is cleaned up
            try:
                proc.kill()
            except ProcessLookupError:
                pass
            await proc.wait()
