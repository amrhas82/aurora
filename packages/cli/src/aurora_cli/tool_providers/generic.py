"""Generic tool provider for configuration-based tools."""

import shutil
import subprocess
import tempfile
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


class GenericToolProvider(ToolProvider):
    """Generic tool provider that can be configured via config dict.

    This allows adding new AI coding tools without writing custom provider classes.
    All behavior is driven by the configuration dictionary.

    Example config:
        {
            "executable": "cursor",
            "display_name": "Cursor",
            "input_method": "stdin",
            "flags": ["--no-tty"],
            "timeout": 600,
            "priority": 50,
        }
    """

    def __init__(self, name: str, config: dict[str, Any]) -> None:
        """Initialize generic provider.

        Args:
            name: Unique tool identifier
            config: Configuration dictionary

        """
        super().__init__(config)
        self._name = name
        self._executable = config.get("executable", name)
        self._display_name = config.get("display_name", name.capitalize())
        self._input_method_str = config.get("input_method", "stdin")
        self._default_flags = config.get("flags", [])
        self._timeout = config.get("timeout", 600)
        self._priority = config.get("priority", 100)

        # Capabilities from config
        caps = config.get("capabilities", {})
        self._capabilities = ToolCapabilities(
            supports_streaming=caps.get("streaming", False),
            supports_conversation=caps.get("conversation", False),
            supports_system_prompt=caps.get("system_prompt", False),
            supports_tools=caps.get("tools", False),
            supports_vision=caps.get("vision", False),
            max_context_length=caps.get("max_context", None),
            default_timeout=self._timeout,
            priority=self._priority,
        )

    @property
    def name(self) -> str:
        return self._name

    @property
    def display_name(self) -> str:
        return self._display_name

    @property
    def executable(self) -> str:
        return self._executable

    @property
    def input_method(self) -> InputMethod:
        if "input_method" in self._config:
            return InputMethod(self._config["input_method"])
        return InputMethod(self._input_method_str)

    @property
    def capabilities(self) -> ToolCapabilities:
        return self._capabilities

    @property
    def default_flags(self) -> list[str]:
        if "flags" in self._config:
            return list(self._config["flags"])
        return list(self._default_flags)

    @property
    def timeout(self) -> int:
        if "timeout" in self._config:
            return int(self._config["timeout"])
        return self._timeout

    @property
    def priority(self) -> int:
        if "priority" in self._config:
            return int(self._config["priority"])
        return self._priority

    def is_available(self) -> bool:
        """Check if the tool executable is in PATH."""
        return shutil.which(self.executable) is not None

    def build_command(self, context: str) -> list[str]:
        """Build command based on configuration."""
        cmd = [self.executable] + self.default_flags

        if self.input_method == InputMethod.ARGUMENT:
            cmd.append(context)

        return cmd

    def execute(
        self,
        context: str,
        working_dir: Path | None = None,
        timeout: int = 600,
    ) -> ToolResult:
        """Execute the tool with the given context.

        Args:
            context: The prompt/context to pass to the tool
            working_dir: Working directory for execution
            timeout: Maximum execution time in seconds

        Returns:
            ToolResult with execution status and output

        """
        if not self.is_available():
            return ToolResult(
                status=ToolStatus.NOT_FOUND,
                stdout="",
                stderr=f"{self.executable} CLI not found in PATH",
                return_code=-1,
            )

        start_time = time.time()

        try:
            # Build command
            cmd = self.build_command(context)

            # Handle different input methods
            stdin_input = None
            temp_file = None

            if self.input_method == InputMethod.STDIN:
                stdin_input = context
            elif self.input_method == InputMethod.FILE:
                # Write context to temp file
                temp_file = tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False)
                temp_file.write(context)
                temp_file.close()
                cmd.append(temp_file.name)

            result = subprocess.run(
                cmd,
                input=stdin_input,
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=working_dir,
            )

            # Cleanup temp file if used
            if temp_file:
                Path(temp_file.name).unlink(missing_ok=True)

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
                stderr=f"{self.display_name} timed out after {timeout} seconds",
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
