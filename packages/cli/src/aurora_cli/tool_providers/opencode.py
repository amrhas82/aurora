"""OpenCode tool provider."""

import shutil
import subprocess
import time
from pathlib import Path
from typing import Any

from aurora_cli.tool_providers.base import (
    InputMethod,
    OutputFormat,
    ToolCapabilities,
    ToolProvider,
    ToolResult,
    ToolStatus,
)
from aurora_cli.tool_providers.output_handler import OpenCodeOutputHandler, ParsedOutput


class OpenCodeToolProvider(ToolProvider):
    """Tool provider for OpenCode CLI.

    OpenCode accepts context via stdin.

    Features:
    - Stdin-based input
    - Conversation support
    - System prompt support
    - Tool support
    - Medium context window (128k tokens)
    - Structured output parsing
    """

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        """Initialize OpenCode provider with optional config."""
        super().__init__(config)
        self._output_handler = OpenCodeOutputHandler()

    @property
    def name(self) -> str:
        return "opencode"

    @property
    def display_name(self) -> str:
        return "OpenCode"

    @property
    def input_method(self) -> InputMethod:
        """OpenCode uses stdin-based input."""
        if "input_method" in self._config:
            return InputMethod(self._config["input_method"])
        return InputMethod.STDIN

    @property
    def capabilities(self) -> ToolCapabilities:
        """OpenCode capabilities."""
        return ToolCapabilities(
            supports_streaming=True,
            supports_conversation=True,
            supports_system_prompt=True,
            supports_tools=True,
            supports_vision=False,
            max_context_length=128000,
            default_timeout=600,
            priority=2,
        )

    @property
    def default_flags(self) -> list[str]:
        """Default flags for OpenCode CLI."""
        if "flags" in self._config:
            return list(self._config["flags"])
        return []

    def is_available(self) -> bool:
        """Check if opencode CLI is installed."""
        return shutil.which("opencode") is not None

    def build_command(self, _context: str) -> list[str]:
        """Build OpenCode CLI command.

        OpenCode accepts input via stdin, so command is just the binary plus flags.
        Uses all_flags which includes default_flags + extra_flags from CLI.
        """
        return ["opencode"] + self.all_flags

    def execute(
        self,
        context: str,
        working_dir: Path | None = None,
        timeout: int = 600,
    ) -> ToolResult:
        """Execute OpenCode with the given context.

        Args:
            context: The prompt/context to pass via stdin
            working_dir: Working directory for execution
            timeout: Maximum execution time in seconds

        Returns:
            ToolResult with execution status and output

        """
        import os

        if not self.is_available():
            return ToolResult(
                status=ToolStatus.NOT_FOUND,
                stdout="",
                stderr="opencode CLI not found in PATH",
                return_code=-1,
            )

        cmd = self.build_command(context)
        start_time = time.time()

        # Build environment with overrides
        env = os.environ.copy()
        env.update(self.env_overrides)

        try:
            # OpenCode uses stdin for input
            result = subprocess.run(
                cmd,
                input=context,
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=working_dir,
                env=env,
            )
            duration = time.time() - start_time

            return ToolResult(
                status=ToolStatus.SUCCESS if result.returncode == 0 else ToolStatus.FAILURE,
                stdout=result.stdout,
                stderr=result.stderr,
                return_code=result.returncode,
                duration_seconds=duration,
                metadata={
                    "tool": self.name,
                    "input_method": self.input_method.value,
                    "flags": self.all_flags,
                },
            )
        except subprocess.TimeoutExpired:
            return ToolResult(
                status=ToolStatus.TIMEOUT,
                stdout="",
                stderr=f"OpenCode timed out after {timeout} seconds",
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

    def parse_output(self, output: str) -> ParsedOutput:
        """Parse OpenCode output into structured format.

        Args:
            output: Raw output from OpenCode

        Returns:
            ParsedOutput with extracted status, code blocks, file changes, etc.

        """
        return self._output_handler.parse(output)

    @property
    def output_format(self) -> OutputFormat:
        """OpenCode outputs markdown or JSON."""
        return OutputFormat.MARKDOWN

    def normalize_output(self, output: str) -> str:
        """Normalize OpenCode output.

        Args:
            output: Raw output from OpenCode

        Returns:
            Normalized output string

        """
        parsed = self.parse_output(output)
        return parsed.clean_output

    def get_info(self) -> dict[str, Any]:
        """Get provider information including OpenCode-specific details."""
        info = super().get_info()
        info.update(
            {
                "model_family": "opencode",
                "supports_json_mode": True,
            },
        )
        return info
