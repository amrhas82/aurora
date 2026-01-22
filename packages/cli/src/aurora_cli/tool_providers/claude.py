"""Claude Code tool provider."""

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
from aurora_cli.tool_providers.output_handler import ClaudeOutputHandler, ParsedOutput


class ClaudeToolProvider(ToolProvider):
    """Tool provider for Claude Code CLI.

    Claude uses --print flag with the prompt as an argument.
    Supports --dangerously-skip-permissions for headless execution.

    Features:
    - Argument-based input (--print flag)
    - Full tool support (Read, Write, Edit, Bash, etc.)
    - Vision capabilities
    - Large context window (200k tokens)
    - Structured output parsing
    """

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        """Initialize Claude provider with optional config."""
        super().__init__(config)
        self._output_handler = ClaudeOutputHandler()

    @property
    def name(self) -> str:
        return "claude"

    @property
    def display_name(self) -> str:
        return "Claude Code"

    @property
    def input_method(self) -> InputMethod:
        """Claude uses argument-based input."""
        if "input_method" in self._config:
            return InputMethod(self._config["input_method"])
        return InputMethod.ARGUMENT

    @property
    def capabilities(self) -> ToolCapabilities:
        """Claude Code capabilities."""
        return ToolCapabilities(
            supports_streaming=True,
            supports_conversation=True,
            supports_system_prompt=True,
            supports_tools=True,
            supports_vision=True,
            max_context_length=200000,
            default_timeout=600,
            priority=1,  # Highest priority
        )

    @property
    def default_flags(self) -> list[str]:
        """Default flags for Claude CLI."""
        if "flags" in self._config:
            return list(self._config["flags"])
        return ["--print", "--dangerously-skip-permissions"]

    def is_available(self) -> bool:
        """Check if claude CLI is installed."""
        return shutil.which("claude") is not None

    def build_command(self, context: str) -> list[str]:
        """Build Claude CLI command.

        Claude uses: claude --print --dangerously-skip-permissions <prompt>
        Uses all_flags which includes default_flags + extra_flags from CLI.
        """
        cmd = ["claude"] + self.all_flags
        if self.input_method == InputMethod.ARGUMENT:
            cmd.append(context)
        return cmd

    def execute(
        self,
        context: str,
        working_dir: Path | None = None,
        timeout: int = 600,
    ) -> ToolResult:
        """Execute Claude with the given context.

        Args:
            context: The prompt/context to pass to Claude
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
                stderr="claude CLI not found in PATH",
                return_code=-1,
            )

        cmd = self.build_command(context)
        start_time = time.time()

        # Build environment with overrides
        env = os.environ.copy()
        env.update(self.env_overrides)

        try:
            # Handle different input methods
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
                stderr=f"Claude timed out after {timeout} seconds",
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
        """Parse Claude output into structured format.

        Args:
            output: Raw output from Claude

        Returns:
            ParsedOutput with extracted status, code blocks, file changes, etc.

        """
        return self._output_handler.parse(output)

    @property
    def output_format(self) -> OutputFormat:
        """Claude outputs markdown with XML tool invocations."""
        return OutputFormat.MARKDOWN

    def normalize_output(self, output: str) -> str:
        """Normalize Claude output, preserving code blocks.

        Args:
            output: Raw output from Claude

        Returns:
            Normalized output string

        """
        parsed = self.parse_output(output)
        return parsed.clean_output

    def get_info(self) -> dict[str, Any]:
        """Get provider information including Claude-specific details."""
        info = super().get_info()
        info.update(
            {
                "model_family": "claude",
                "supports_mcp": True,
                "supports_system_prompt_file": True,
                "permission_modes": ["interactive", "dangerously-skip-permissions"],
            },
        )
        return info
