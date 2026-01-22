"""Output handling for tool providers.

Provides consistent output parsing and normalization for different AI tool outputs.
Extracts structured information like status, code blocks, file changes, and errors.
"""

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class ParsedStatus(Enum):
    """Status extracted from tool output."""

    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    DONE = "done"
    BLOCKED = "blocked"
    ERROR = "error"
    UNKNOWN = "unknown"


@dataclass
class CodeBlock:
    """Extracted code block from output."""

    language: str
    content: str
    file_path: str | None = None  # If the block specifies a file


@dataclass
class FileChange:
    """Extracted file change from output."""

    path: str
    action: str  # create, edit, delete, read
    content: str | None = None


@dataclass
class ToolCommand:
    """Extracted tool/command execution from output."""

    tool_name: str
    arguments: dict[str, Any] = field(default_factory=dict)
    result: str | None = None


@dataclass
class ParsedOutput:
    """Structured output from a tool execution."""

    raw_output: str
    clean_output: str
    status: ParsedStatus = ParsedStatus.UNKNOWN
    status_message: str | None = None
    code_blocks: list[CodeBlock] = field(default_factory=list)
    file_changes: list[FileChange] = field(default_factory=list)
    tool_commands: list[ToolCommand] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    next_steps: list[str] = field(default_factory=list)
    scratchpad_updates: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def has_errors(self) -> bool:
        """Check if there are any errors."""
        return len(self.errors) > 0

    @property
    def is_complete(self) -> bool:
        """Check if the task is marked as complete."""
        return self.status == ParsedStatus.DONE

    @property
    def summary(self) -> str:
        """Generate a brief summary of the output."""
        parts = []
        if self.status != ParsedStatus.UNKNOWN:
            parts.append(f"Status: {self.status.value}")
        if self.code_blocks:
            parts.append(f"{len(self.code_blocks)} code blocks")
        if self.file_changes:
            parts.append(f"{len(self.file_changes)} file changes")
        if self.errors:
            parts.append(f"{len(self.errors)} errors")
        return ", ".join(parts) if parts else "No structured content"


class OutputHandler:
    """Base output handler with common parsing logic.

    Subclasses can override methods for tool-specific parsing.
    """

    # ANSI escape code pattern
    ANSI_PATTERN = re.compile(r"\x1b\[[0-9;]*[a-zA-Z]")

    # Status patterns (case-insensitive)
    STATUS_PATTERNS = {
        ParsedStatus.DONE: [
            r"STATUS:\s*DONE",
            r"COMPLETED",
            r"Task completed",
            r"Successfully completed",
        ],
        ParsedStatus.IN_PROGRESS: [
            r"STATUS:\s*IN_PROGRESS",
            r"Working on",
            r"In progress",
        ],
        ParsedStatus.BLOCKED: [
            r"STATUS:\s*BLOCKED",
            r"BLOCKED",
            r"Cannot proceed",
            r"Waiting for",
        ],
        ParsedStatus.ERROR: [
            r"ERROR:",
            r"FAILED",
            r"Exception:",
        ],
    }

    # Code block pattern
    CODE_BLOCK_PATTERN = re.compile(
        r"```(\w*)\n(.*?)```",
        re.DOTALL,
    )

    # File path pattern in code blocks (common format: ```python path/to/file.py)
    FILE_CODE_BLOCK_PATTERN = re.compile(
        r"```(\w+)\s+([\w./\-_]+\.\w+)\n(.*?)```",
        re.DOTALL,
    )

    def __init__(self, tool_name: str):
        """Initialize handler for a specific tool.

        Args:
            tool_name: Name of the tool this handler is for

        """
        self.tool_name = tool_name

    def parse(self, output: str) -> ParsedOutput:
        """Parse tool output into structured format.

        Args:
            output: Raw output from the tool

        Returns:
            ParsedOutput with extracted information

        """
        clean = self._clean_output(output)
        result = ParsedOutput(
            raw_output=output,
            clean_output=clean,
        )

        # Extract components
        result.status, result.status_message = self._extract_status(clean)
        result.code_blocks = self._extract_code_blocks(clean)
        result.file_changes = self._extract_file_changes(clean)
        result.errors = self._extract_errors(clean)
        result.warnings = self._extract_warnings(clean)
        result.next_steps = self._extract_next_steps(clean)
        result.scratchpad_updates = self._extract_scratchpad_updates(clean)

        return result

    def _clean_output(self, output: str) -> str:
        """Clean output by removing ANSI codes and normalizing whitespace.

        Args:
            output: Raw output

        Returns:
            Cleaned output

        """
        if not output:
            return ""

        # Remove ANSI codes
        clean = self.ANSI_PATTERN.sub("", output)

        # Normalize multiple blank lines
        clean = re.sub(r"\n{3,}", "\n\n", clean)

        # Strip trailing whitespace on each line
        lines = [line.rstrip() for line in clean.split("\n")]
        return "\n".join(lines).strip()

    def _extract_status(self, output: str) -> tuple[ParsedStatus, str | None]:
        """Extract status from output.

        Args:
            output: Clean output text

        Returns:
            Tuple of (status, optional status message)

        """
        for status, patterns in self.STATUS_PATTERNS.items():
            for pattern in patterns:
                match = re.search(pattern, output, re.IGNORECASE)
                if match:
                    # Try to extract message after status
                    line_match = re.search(
                        rf"{pattern}[:\s]*(.+?)(?:\n|$)",
                        output,
                        re.IGNORECASE,
                    )
                    message = line_match.group(1).strip() if line_match else None
                    return status, message

        return ParsedStatus.UNKNOWN, None

    def _extract_code_blocks(self, output: str) -> list[CodeBlock]:
        """Extract code blocks from output.

        Args:
            output: Clean output text

        Returns:
            List of CodeBlock objects

        """
        blocks = []

        # First, try to find file-annotated code blocks
        for match in self.FILE_CODE_BLOCK_PATTERN.finditer(output):
            blocks.append(
                CodeBlock(
                    language=match.group(1) or "",
                    file_path=match.group(2),
                    content=match.group(3).strip(),
                ),
            )

        # Then find regular code blocks (avoid duplicates)
        for match in self.CODE_BLOCK_PATTERN.finditer(output):
            content = match.group(2).strip()
            # Skip if we already captured this block with a file path
            if not any(b.content == content for b in blocks):
                blocks.append(
                    CodeBlock(
                        language=match.group(1) or "",
                        content=content,
                    ),
                )

        return blocks

    def _extract_file_changes(self, output: str) -> list[FileChange]:
        """Extract file change operations from output.

        Override in subclasses for tool-specific formats.

        Args:
            output: Clean output text

        Returns:
            List of FileChange objects

        """
        changes = []

        # Common patterns for file operations
        create_patterns = [
            r"(?:Created?|Creating|Wrote?|Writing)\s+(?:file\s+)?['\"]?([\w./\-_]+\.\w+)['\"]?",
            r"(?:Write|Edit)\s+tool.*?['\"]?([\w./\-_]+\.\w+)['\"]?",
        ]
        edit_patterns = [
            r"(?:Modified|Modifying|Updated|Updating|Edited|Editing)\s+['\"]?([\w./\-_]+\.\w+)['\"]?",
        ]
        delete_patterns = [
            r"(?:Deleted?|Deleting|Removed?|Removing)\s+['\"]?([\w./\-_]+\.\w+)['\"]?",
        ]

        for pattern in create_patterns:
            for match in re.finditer(pattern, output, re.IGNORECASE):
                changes.append(FileChange(path=match.group(1), action="create"))

        for pattern in edit_patterns:
            for match in re.finditer(pattern, output, re.IGNORECASE):
                changes.append(FileChange(path=match.group(1), action="edit"))

        for pattern in delete_patterns:
            for match in re.finditer(pattern, output, re.IGNORECASE):
                changes.append(FileChange(path=match.group(1), action="delete"))

        return changes

    def _extract_errors(self, output: str) -> list[str]:
        """Extract error messages from output.

        Args:
            output: Clean output text

        Returns:
            List of error messages

        """
        errors = []

        error_patterns = [
            r"(?:Error|ERROR):\s*(.+?)(?:\n|$)",
            r"(?:Failed|FAILED):\s*(.+?)(?:\n|$)",
            r"Exception:\s*(.+?)(?:\n|$)",
            r"Traceback \(most recent call last\):(.*?)(?=\n\n|\Z)",
        ]

        for pattern in error_patterns:
            for match in re.finditer(pattern, output, re.IGNORECASE | re.DOTALL):
                msg = match.group(1).strip()
                if msg and msg not in errors:
                    errors.append(msg)

        return errors

    def _extract_warnings(self, output: str) -> list[str]:
        """Extract warning messages from output.

        Args:
            output: Clean output text

        Returns:
            List of warning messages

        """
        warnings = []

        warning_patterns = [
            r"(?:Warning|WARN|WARNING):\s*(.+?)(?:\n|$)",
            r"(?:Note|NOTE):\s*(.+?)(?:\n|$)",
            r"(?:Caution|CAUTION):\s*(.+?)(?:\n|$)",
        ]

        for pattern in warning_patterns:
            for match in re.finditer(pattern, output, re.IGNORECASE):
                msg = match.group(1).strip()
                if msg and msg not in warnings:
                    warnings.append(msg)

        return warnings

    def _extract_next_steps(self, output: str) -> list[str]:
        """Extract next steps or action items from output.

        Args:
            output: Clean output text

        Returns:
            List of next step descriptions

        """
        steps = []

        # Look for numbered lists after "Next steps" header
        next_steps_pattern = (
            r"(?:Next steps?|TODO|Action items?):\s*((?:\n\s*(?:\d+\.|[-*])\s*.+)+)"
        )
        match = re.search(next_steps_pattern, output, re.IGNORECASE)
        if match:
            items = re.findall(r"(?:\d+\.|[-*])\s*(.+)", match.group(1))
            steps.extend(item.strip() for item in items)

        return steps

    def _extract_scratchpad_updates(self, output: str) -> dict[str, Any]:
        """Extract scratchpad update suggestions from output.

        Override in subclasses for tool-specific formats.

        Args:
            output: Clean output text

        Returns:
            Dictionary of scratchpad field updates

        """
        updates: dict[str, Any] = {}

        # Look for explicit scratchpad section markers
        scratchpad_pattern = r"##\s*(?:Updated\s+)?Scratchpad(?:\s+State)?:(.*?)(?=##|\Z)"
        match = re.search(scratchpad_pattern, output, re.IGNORECASE | re.DOTALL)
        if match:
            content = match.group(1).strip()
            # Try to extract status
            status_match = re.search(r"STATUS:\s*(\w+)", content)
            if status_match:
                updates["status"] = status_match.group(1)

            # Try to extract completed items
            completed_match = re.search(
                r"##\s*Completed\s*(.*?)(?=##|\Z)",
                content,
                re.IGNORECASE | re.DOTALL,
            )
            if completed_match:
                items = re.findall(r"[-*]\s*(.+)", completed_match.group(1))
                updates["completed"] = items

        return updates


class ClaudeOutputHandler(OutputHandler):
    """Output handler specialized for Claude Code CLI.

    Handles Claude-specific output formats including:
    - Tool use blocks (function calls in XML format)
    - Permission requests
    - Streaming markers
    """

    def __init__(self):
        """Initialize Claude output handler."""
        super().__init__("claude")

    def _extract_file_changes(self, output: str) -> list[FileChange]:
        """Extract file changes from Claude's tool invocations.

        Claude uses XML-style function calls for file operations.
        """
        changes = super()._extract_file_changes(output)

        # Claude-specific: Extract from Write/Edit tool invocations
        # Pattern for Write tool
        write_pattern = r'<invoke name="Write">\s*<parameter name="file_path">([^<]+)</parameter>'
        for match in re.finditer(write_pattern, output, re.DOTALL):
            path = match.group(1).strip()
            if not any(c.path == path for c in changes):
                changes.append(FileChange(path=path, action="create"))

        # Pattern for Edit tool
        edit_pattern = r'<invoke name="Edit">\s*<parameter name="file_path">([^<]+)</parameter>'
        for match in re.finditer(edit_pattern, output, re.DOTALL):
            path = match.group(1).strip()
            if not any(c.path == path for c in changes):
                changes.append(FileChange(path=path, action="edit"))

        return changes

    def _extract_tool_commands(self, output: str) -> list[ToolCommand]:
        """Extract Claude's tool invocations.

        Args:
            output: Clean output text

        Returns:
            List of ToolCommand objects

        """
        commands = []

        # Pattern for function call blocks
        invoke_pattern = r'<invoke name="(\w+)">(.*?)</invoke>'
        for match in re.finditer(invoke_pattern, output, re.DOTALL):
            tool_name = match.group(1)
            params_text = match.group(2)

            # Extract parameters
            args = {}
            param_pattern = r'<parameter name="(\w+)">([^<]*)</parameter>'
            for param_match in re.finditer(param_pattern, params_text):
                args[param_match.group(1)] = param_match.group(2)

            commands.append(ToolCommand(tool_name=tool_name, arguments=args))

        return commands

    def parse(self, output: str) -> ParsedOutput:
        """Parse Claude output with tool command extraction.

        Args:
            output: Raw output from Claude

        Returns:
            ParsedOutput with extracted information

        """
        result = super().parse(output)
        result.tool_commands = self._extract_tool_commands(result.clean_output)
        result.metadata["tool"] = "claude"
        return result


class OpenCodeOutputHandler(OutputHandler):
    """Output handler specialized for OpenCode CLI.

    Handles OpenCode-specific output formats including:
    - JSON-structured responses
    - Markdown with file annotations
    - Tool call syntax
    """

    def __init__(self):
        """Initialize OpenCode output handler."""
        super().__init__("opencode")

    def _extract_file_changes(self, output: str) -> list[FileChange]:
        """Extract file changes from OpenCode output.

        OpenCode may use different annotation styles.
        """
        changes = super()._extract_file_changes(output)

        # OpenCode-specific: Look for file operation markers
        # Pattern: [FILE: path/to/file.py] or File: path/to/file.py
        file_marker_pattern = r"\[?FILE:\s*([\w./\-_]+\.\w+)\]?"
        for match in re.finditer(file_marker_pattern, output, re.IGNORECASE):
            path = match.group(1).strip()
            if not any(c.path == path for c in changes):
                changes.append(FileChange(path=path, action="edit"))

        return changes

    def parse(self, output: str) -> ParsedOutput:
        """Parse OpenCode output.

        Args:
            output: Raw output from OpenCode

        Returns:
            ParsedOutput with extracted information

        """
        result = super().parse(output)
        result.metadata["tool"] = "opencode"

        # Try to detect if output is JSON-structured
        if output.strip().startswith("{"):
            try:
                import json

                data = json.loads(output)
                if "status" in data:
                    status_val = data["status"].lower()
                    for status in ParsedStatus:
                        if status.value == status_val:
                            result.status = status
                            break
                result.metadata["json_response"] = True
            except json.JSONDecodeError:
                pass

        return result


def get_handler(tool_name: str) -> OutputHandler:
    """Get the appropriate output handler for a tool.

    Args:
        tool_name: Name of the tool

    Returns:
        OutputHandler instance for the tool

    """
    handlers = {
        "claude": ClaudeOutputHandler,
        "opencode": OpenCodeOutputHandler,
    }

    handler_class = handlers.get(tool_name, OutputHandler)
    if handler_class == OutputHandler:
        return OutputHandler(tool_name)
    return handler_class()
