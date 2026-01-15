"""Gemini CLI tool provider."""

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


class GeminiToolProvider(ToolProvider):
    """Tool provider for Google Gemini CLI.

    Gemini CLI provides access to Google's Gemini models
    for code generation and assistance.
    """

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        """Initialize Gemini provider with optional config."""
        super().__init__(config)

    @property
    def name(self) -> str:
        return "gemini"

    @property
    def display_name(self) -> str:
        return "Gemini CLI"

    @property
    def input_method(self) -> InputMethod:
        """Gemini uses argument-based input."""
        if "input_method" in self._config:
            return InputMethod(self._config["input_method"])
        return InputMethod.ARGUMENT

    @property
    def capabilities(self) -> ToolCapabilities:
        """Gemini capabilities."""
        return ToolCapabilities(
            supports_streaming=True,
            supports_conversation=True,
            supports_system_prompt=True,
            supports_tools=True,
            supports_vision=True,
            max_context_length=1000000,  # Gemini has large context
            default_timeout=600,
            priority=15,
        )

    @property
    def default_flags(self) -> list[str]:
        """Default flags for Gemini CLI."""
        if "flags" in self._config:
            return list(self._config["flags"])
        return []

    def is_available(self) -> bool:
        """Check if gemini CLI is installed."""
        return shutil.which("gemini") is not None

    def build_command(self, context: str) -> list[str]:
        """Build Gemini CLI command."""
        cmd = ["gemini"] + self.default_flags
        if self.input_method == InputMethod.ARGUMENT:
            cmd.append(context)
        return cmd

    def execute(
        self,
        context: str,
        working_dir: Path | None = None,
        timeout: int = 600,
    ) -> ToolResult:
        """Execute Gemini with the given context."""
        if not self.is_available():
            return ToolResult(
                status=ToolStatus.NOT_FOUND,
                stdout="",
                stderr="gemini CLI not found in PATH",
                return_code=-1,
            )

        cmd = self.build_command(context)
        start_time = time.time()

        try:
            stdin_input = None
            if self.input_method == InputMethod.STDIN:
                stdin_input = context

            result = subprocess.run(
                cmd,
                input=stdin_input,
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
                stderr=f"Gemini timed out after {timeout} seconds",
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
