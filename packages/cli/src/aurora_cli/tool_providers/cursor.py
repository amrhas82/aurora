"""Cursor tool provider."""

import shutil
import subprocess
import time
from pathlib import Path
from typing import Any

from aurora_cli.tool_providers.base import (
    InputMethod,
    ToolCapabilities,
    ToolProvider,
    ToolResult,
    ToolStatus,
)


class CursorToolProvider(ToolProvider):
    """Tool provider for Cursor AI editor CLI.

    Cursor is an AI-first code editor with powerful autocomplete
    and chat features.
    """

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        """Initialize Cursor provider with optional config."""
        super().__init__(config)

    @property
    def name(self) -> str:
        return "cursor"

    @property
    def display_name(self) -> str:
        return "Cursor"

    @property
    def input_method(self) -> InputMethod:
        """Cursor uses stdin-based input."""
        if "input_method" in self._config:
            return InputMethod(self._config["input_method"])
        return InputMethod.STDIN

    @property
    def capabilities(self) -> ToolCapabilities:
        """Cursor capabilities."""
        return ToolCapabilities(
            supports_streaming=True,
            supports_conversation=True,
            supports_system_prompt=True,
            supports_tools=True,
            supports_vision=True,
            max_context_length=128000,
            default_timeout=600,
            priority=10,
        )

    @property
    def default_flags(self) -> list[str]:
        """Default flags for Cursor CLI."""
        if "flags" in self._config:
            return list(self._config["flags"])
        return []

    def is_available(self) -> bool:
        """Check if cursor CLI is installed."""
        return shutil.which("cursor") is not None

    def build_command(self, _context: str) -> list[str]:
        """Build Cursor CLI command."""
        return ["cursor"] + self.default_flags

    def execute(
        self,
        context: str,
        working_dir: Path | None = None,
        timeout: int = 600,
    ) -> ToolResult:
        """Execute Cursor with the given context."""
        if not self.is_available():
            return ToolResult(
                status=ToolStatus.NOT_FOUND,
                stdout="",
                stderr="cursor CLI not found in PATH",
                return_code=-1,
            )

        cmd = self.build_command(context)
        start_time = time.time()

        try:
            result = subprocess.run(
                cmd,
                input=context,
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=working_dir,
            )
            duration = time.time() - start_time

            return ToolResult(
                status=ToolStatus.SUCCESS if result.returncode == 0 else ToolStatus.FAILURE,
                stdout=result.stdout,
                stderr=result.stderr,
                return_code=result.returncode,
                duration_seconds=duration,
                metadata={"tool": self.name, "input_method": self.input_method.value},
            )
        except subprocess.TimeoutExpired:
            return ToolResult(
                status=ToolStatus.TIMEOUT,
                stdout="",
                stderr=f"Cursor timed out after {timeout} seconds",
                return_code=-1,
                duration_seconds=timeout,
            )
        except Exception as e:
            return ToolResult(
                status=ToolStatus.FAILURE,
                stdout="",
                stderr=str(e),
                return_code=-1,
                duration_seconds=time.time() - start_time,
            )
