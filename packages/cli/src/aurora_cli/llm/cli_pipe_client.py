"""CLI Pipe LLM Client - pipes prompts to external CLI tools.

This module implements an LLM client that pipes prompts to external CLI tools
(like claude, cursor, etc.) via subprocess instead of making API calls.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import threading
import time
from pathlib import Path
from typing import Any

from rich.console import Console

from aurora_reasoning.llm_client import LLMClient, LLMResponse, extract_json_from_text

# Console for spinner output
_console = Console()


class CLIPipeLLMClient(LLMClient):
    """LLM client that pipes prompts to external CLI tools.

    This client implements the LLMClient interface but delegates to external
    CLI tools (like claude, cursor, etc.) via subprocess piping.

    Attributes:
        _tool: Name of the CLI tool to pipe to
        _soar_dir: Directory for JSON placeholder files

    """

    def __init__(
        self,
        tool: str = "claude",
        model: str = "sonnet",
        soar_dir: Path | None = None,
    ):
        """Initialize CLI pipe client.

        Args:
            tool: CLI tool name to pipe to (default: "claude")
            model: Model to use - "sonnet" or "opus" (default: "sonnet")
            soar_dir: Directory for JSON placeholder files (default: .aurora/soar/)

        Raises:
            ValueError: If tool is not found in PATH

        """
        # Validate tool exists in PATH
        if not shutil.which(tool):
            raise ValueError(
                f"Tool '{tool}' not found in PATH. "
                f"Please install {tool} or specify a different tool.",
            )

        self._tool = tool
        self._model = model
        self._soar_dir = soar_dir

    def _ensure_soar_dir(self) -> Path:
        """Ensure soar directory exists and return path.

        Returns:
            Path to soar directory

        """
        if self._soar_dir is None:
            from aurora_core.paths import get_aurora_dir

            self._soar_dir = get_aurora_dir() / "soar"

        self._soar_dir.mkdir(parents=True, exist_ok=True)
        return self._soar_dir

    def _write_state(self, phase_name: str, status: str) -> None:
        """Write current state to state.json.

        Args:
            phase_name: Current phase name
            status: Current status (e.g., "running", "complete")

        """
        soar_dir = self._ensure_soar_dir()
        state_file = soar_dir / "state.json"
        state_data = {
            "phase": phase_name,
            "status": status,
            "tool": self._tool,
        }
        state_file.write_text(json.dumps(state_data, indent=2))

    def generate(
        self,
        prompt: str,
        *,
        _model: str | None = None,
        _max_tokens: int = 4096,
        _temperature: float = 0.7,
        system: str | None = None,
        phase_name: str = "unknown",
        **_kwargs: Any,
    ) -> LLMResponse:
        """Generate text completion by piping to CLI tool.

        Args:
            prompt: The user prompt/question
            model: Ignored (tool determines model)
            max_tokens: Ignored (tool determines limits)
            temperature: Ignored (tool determines temperature)
            system: Optional system prompt (prepended to prompt)
            phase_name: Name of current phase for state tracking
            **kwargs: Additional parameters (ignored)

        Returns:
            LLMResponse with generated content and metadata

        Raises:
            ValueError: If prompt is empty
            RuntimeError: If CLI tool fails

        """
        if not prompt or not prompt.strip():
            raise ValueError("Prompt cannot be empty")

        soar_dir = self._ensure_soar_dir()

        # Build full prompt with system message if provided
        full_prompt = prompt
        if system:
            full_prompt = f"{system}\n\n{prompt}"

        # Write input.json (transitory placeholder, overwritten each call)
        input_file = soar_dir / "input.json"
        input_data = {
            "prompt": prompt,
            "system": system,
            "phase": phase_name,
            "tool": self._tool,
        }
        input_file.write_text(json.dumps(input_data, indent=2))

        # Update state
        self._write_state(phase_name, "running")

        # Pipe to tool with spinner
        # Note: Don't pass --model to claude CLI - it generates invalid Bedrock model IDs
        # for aliases like "sonnet". Let the CLI use its default config instead.
        cmd = [self._tool, "-p"]
        result = None
        error = None

        def run_subprocess():
            nonlocal result, error
            try:
                result = subprocess.run(
                    cmd,
                    input=full_prompt,
                    capture_output=True,
                    text=True,
                    timeout=300,  # Increased to 5 minutes
                )
            except subprocess.TimeoutExpired:
                error = RuntimeError(f"Tool {self._tool} timed out after 300 seconds")
            except Exception as e:
                error = e

        # Run subprocess in background thread with spinner
        thread = threading.Thread(target=run_subprocess, daemon=True)
        start_time = time.time()
        thread.start()

        # Show spinner while waiting (only on TTY)
        import sys

        show_spinner = sys.stdout.isatty()
        spinner_chars = "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"
        spinner_idx = 0
        try:
            while thread.is_alive():
                if show_spinner:
                    elapsed = time.time() - start_time
                    spinner = spinner_chars[spinner_idx % len(spinner_chars)]
                    # Use \r to update same line, flush to ensure display
                    sys.stdout.write(f"\r  {spinner} Thinking... ({elapsed:.0f}s)")
                    sys.stdout.flush()
                    spinner_idx += 1
                thread.join(timeout=0.1)
            if show_spinner:
                # Clear spinner line
                sys.stdout.write("\r" + " " * 40 + "\r")
                sys.stdout.flush()
        except KeyboardInterrupt:
            _console.print("\n[yellow]Interrupted - waiting for subprocess...[/]")
            thread.join(timeout=5)
            raise

        if error:
            self._write_state(phase_name, "timeout" if "timed out" in str(error) else "failed")
            raise error

        # Check for errors
        if result.returncode != 0:
            self._write_state(phase_name, "failed")
            # Include both stderr and stdout in error message for debugging
            error_details = result.stderr or result.stdout or "(no output)"

            # Write debug info for troubleshooting intermittent errors
            debug_file = soar_dir / "error_debug.json"
            debug_data = {
                "returncode": result.returncode,
                "stderr": result.stderr,
                "stdout": result.stdout[:1000] if result.stdout else None,
                "phase": phase_name,
            }
            debug_file.write_text(json.dumps(debug_data, indent=2))

            # Try to extract error from JSON response (Claude API returns JSON errors)
            error_msg = None
            try:
                # First try: parse entire output as JSON (may be multi-line)
                # Find the first { and last } to extract JSON object
                first_brace = error_details.find("{")
                last_brace = error_details.rfind("}")
                if first_brace != -1 and last_brace > first_brace:
                    json_str = error_details[first_brace : last_brace + 1]
                    error_json = json.loads(json_str)
                    # Handle different JSON error formats
                    if "error" in error_json:
                        err = error_json["error"]
                        if isinstance(err, dict):
                            error_msg = f"Tool {self._tool} API error: {err.get('message', err.get('type', str(err)))}"
                        else:
                            error_msg = f"Tool {self._tool} API error: {err}"
                    elif "message" in error_json:
                        error_msg = f"Tool {self._tool} error: {error_json['message']}"
            except (json.JSONDecodeError, KeyError, TypeError):
                pass  # Fall back to text extraction

            if error_msg is None:
                # Fall back to text-based extraction
                if "API Error" in error_details:
                    # Shorten API errors - extract just the key info
                    parts = error_details.split(":")
                    if len(parts) >= 2:
                        error_msg = (
                            f"Tool {self._tool} failed: {':'.join(parts[-2:]).strip()[:200]}"
                        )
                    else:
                        error_msg = f"Tool {self._tool} failed: {error_details[:200]}"
                else:
                    error_msg = f"Tool {self._tool} failed (exit {result.returncode}): {error_details[:200]}"
            raise RuntimeError(error_msg)

        content = result.stdout

        # Write output.json (transitory placeholder, overwritten each call)
        output_file = soar_dir / "output.json"
        output_data = {
            "content": content,
            "phase": phase_name,
            "tool": self._tool,
        }
        output_file.write_text(json.dumps(output_data, indent=2))

        # Update state
        self._write_state(phase_name, "complete")

        # Estimate tokens using heuristic
        input_tokens = self.count_tokens(full_prompt)
        output_tokens = self.count_tokens(content)

        return LLMResponse(
            content=content,
            model=self._tool,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            finish_reason="stop",
            metadata={"tool": self._tool, "phase": phase_name},
        )

    def generate_json(
        self,
        prompt: str,
        *,
        model: str | None = None,
        max_tokens: int = 4096,
        temperature: float = 0.7,
        system: str | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Generate JSON-structured output by piping to CLI tool.

        Args:
            prompt: The user prompt/question (should request JSON output)
            model: Ignored (tool determines model)
            max_tokens: Ignored (tool determines limits)
            temperature: Ignored (tool determines temperature)
            system: Optional system prompt
            **kwargs: Additional parameters (passed to generate)

        Returns:
            Parsed JSON object as Python dict

        Raises:
            ValueError: If prompt is empty or output is not valid JSON
            RuntimeError: If CLI tool fails

        """
        # Enhance system prompt to enforce JSON output
        json_system = (
            (system or "")
            + "\n\nYou MUST respond with valid JSON only. Do not include markdown code blocks, explanations, or any text outside the JSON object."
        ).strip()

        response = self.generate(
            prompt=prompt,
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
            system=json_system,
            **kwargs,
        )

        try:
            return extract_json_from_text(response.content)
        except ValueError as e:
            raise ValueError(f"Failed to extract JSON from response: {e}") from e

    def count_tokens(self, text: str) -> int:
        """Estimate token count for text.

        Uses approximate heuristic: 1 token ≈ 4 characters for English text.

        Args:
            text: Text to count tokens for

        Returns:
            Estimated token count

        """
        return len(text) // 4

    @property
    def default_model(self) -> str:
        """Get the default model identifier (tool name)."""
        return self._tool
