"""
Prompt File Parser and Validator for Headless Mode

This module handles loading and validation of experiment prompt files that define
the goals, success criteria, and constraints for autonomous headless execution.

Prompt File Format:
    Prompts are markdown files with specific required sections:

    # Goal
    Clear statement of what the experiment aims to achieve.

    # Success Criteria
    - Measurable criterion 1
    - Measurable criterion 2
    - Measurable criterion 3

    # Constraints
    - Constraint 1 (e.g., budget limits, time limits)
    - Constraint 2 (e.g., file restrictions, API limits)

    # Context (optional)
    Additional background information that helps AURORA understand
    the problem space and make better decisions.

Usage:
    from aurora_soar.headless import PromptLoader, PromptData

    loader = PromptLoader("experiment.md")
    prompt = loader.load()

    print(f"Goal: {prompt.goal}")
    print(f"Success Criteria: {prompt.success_criteria}")
    print(f"Constraints: {prompt.constraints}")

Validation Rules:
    - File must exist and be readable
    - Must contain "# Goal" section with non-empty content
    - Must contain "# Success Criteria" section with at least one item
    - Must contain "# Constraints" section (can be empty)
    - Markdown parsing must succeed without errors
"""

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional


class PromptValidationError(Exception):
    """
    Raised when prompt file validation fails.

    This exception indicates the prompt file is missing required sections,
    has invalid format, or contains empty required fields.
    """

    pass


@dataclass
class PromptData:
    """
    Parsed and validated prompt data.

    Attributes:
        goal: The main objective of the experiment
        success_criteria: List of measurable success conditions
        constraints: List of constraints/limitations for the experiment
        context: Optional additional context/background information
        raw_content: Original markdown content
    """

    goal: str
    success_criteria: List[str]
    constraints: List[str]
    context: Optional[str] = None
    raw_content: str = ""


class PromptLoader:
    """
    Loads and validates experiment prompt files for headless mode.

    The PromptLoader reads markdown files with structured sections defining
    the experiment goal, success criteria, and constraints. It validates the
    format and extracts the data into a structured PromptData object.

    Required Sections:
        - # Goal: Clear objective statement
        - # Success Criteria: List of measurable criteria (at least 1)
        - # Constraints: List of constraints (can be empty)

    Optional Sections:
        - # Context: Additional background information

    Examples:
        # Basic usage
        >>> loader = PromptLoader("experiment.md")
        >>> prompt = loader.load()
        >>> print(prompt.goal)
        'Implement feature X with tests'

        # With validation only (no loading)
        >>> loader = PromptLoader("experiment.md")
        >>> is_valid, errors = loader.validate_format()
        >>> if not is_valid:
        ...     print(f"Validation errors: {errors}")

        # Check if file exists before loading
        >>> loader = PromptLoader("experiment.md")
        >>> if loader.file_exists():
        ...     prompt = loader.load()
        ... else:
        ...     print("File not found")
    """

    # Regex patterns for section headers
    GOAL_HEADER = re.compile(r"^#\s+Goal\s*$", re.IGNORECASE | re.MULTILINE)
    SUCCESS_CRITERIA_HEADER = re.compile(
        r"^#\s+Success\s+Criteria\s*$", re.IGNORECASE | re.MULTILINE
    )
    CONSTRAINTS_HEADER = re.compile(
        r"^#\s+Constraints?\s*$", re.IGNORECASE | re.MULTILINE
    )
    CONTEXT_HEADER = re.compile(r"^#\s+Context\s*$", re.IGNORECASE | re.MULTILINE)

    # Any level-1 header pattern for section splitting
    ANY_HEADER = re.compile(r"^#\s+.+$", re.MULTILINE)

    def __init__(self, prompt_path: str | Path):
        """
        Initialize PromptLoader with path to prompt file.

        Args:
            prompt_path: Path to the markdown prompt file
        """
        self.prompt_path = Path(prompt_path)

    def file_exists(self) -> bool:
        """
        Check if prompt file exists.

        Returns:
            True if file exists and is a file, False otherwise

        Examples:
            >>> loader = PromptLoader("experiment.md")
            >>> if loader.file_exists():
            ...     print("File exists")
        """
        return self.prompt_path.exists() and self.prompt_path.is_file()

    def _read_file(self) -> str:
        """
        Read the prompt file content.

        Returns:
            File content as string

        Raises:
            PromptValidationError: If file cannot be read
        """
        if not self.file_exists():
            raise PromptValidationError(
                f"Prompt file not found: {self.prompt_path}\n"
                f"Please create a prompt file with Goal, Success Criteria, and Constraints sections."
            )

        try:
            return self.prompt_path.read_text(encoding="utf-8")
        except UnicodeDecodeError as e:
            raise PromptValidationError(
                f"Prompt file is not valid UTF-8: {self.prompt_path}"
            ) from e
        except PermissionError as e:
            raise PromptValidationError(
                f"Permission denied reading prompt file: {self.prompt_path}"
            ) from e
        except Exception as e:
            raise PromptValidationError(
                f"Error reading prompt file: {self.prompt_path}: {e}"
            ) from e

    def _extract_section_content(
        self, content: str, header_pattern: re.Pattern[str], next_section_start: int = -1
    ) -> str:
        """
        Extract content between a section header and the next header.

        Args:
            content: Full markdown content
            header_pattern: Regex pattern for the section header
            next_section_start: Position of next section (or -1 for end of file)

        Returns:
            Section content (trimmed)
        """
        match = header_pattern.search(content)
        if not match:
            return ""

        # Start after the header line
        start = match.end()

        # Find the next header after this section
        if next_section_start == -1:
            # Look for any level-1 header after current position
            next_match = self.ANY_HEADER.search(content, start)
            if next_match:
                end = next_match.start()
            else:
                end = len(content)
        else:
            end = next_section_start

        return content[start:end].strip()

    def _parse_list_items(self, content: str) -> List[str]:
        """
        Parse markdown list items from content.

        Supports both "- item" and "* item" formats.

        Args:
            content: Section content with list items

        Returns:
            List of parsed items (without bullets, trimmed)
        """
        items = []
        for line in content.split("\n"):
            line = line.strip()
            # Match "- item" or "* item"
            if line.startswith("- ") or line.startswith("* "):
                item = line[2:].strip()
                if item:  # Skip empty items
                    items.append(item)
        return items

    def _find_all_sections(self, content: str) -> Dict[str, int]:
        """
        Find all level-1 sections and their positions.

        Returns:
            Dictionary mapping section names to their start positions
        """
        sections = {}
        for match in self.ANY_HEADER.finditer(content):
            header_text = match.group().strip("# \t").lower()
            sections[header_text] = match.start()
        return sections

    def parse(self, content: str) -> PromptData:
        """
        Parse markdown content into PromptData.

        Args:
            content: Markdown prompt file content

        Returns:
            Parsed PromptData object

        Raises:
            PromptValidationError: If required sections are missing or invalid
        """
        # Find all sections for proper boundary detection
        sections = self._find_all_sections(content)

        # Extract Goal
        goal_content = self._extract_section_content(content, self.GOAL_HEADER)
        if not goal_content:
            raise PromptValidationError(
                "Prompt file is missing required '# Goal' section.\n"
                "Example format:\n"
                "# Goal\n"
                "Implement feature X with comprehensive tests and documentation."
            )

        # Extract Success Criteria
        success_content = self._extract_section_content(
            content, self.SUCCESS_CRITERIA_HEADER
        )
        if not success_content:
            raise PromptValidationError(
                "Prompt file is missing required '# Success Criteria' section.\n"
                "Example format:\n"
                "# Success Criteria\n"
                "- All tests pass\n"
                "- Code coverage > 80%\n"
                "- Documentation updated"
            )

        success_criteria = self._parse_list_items(success_content)
        if not success_criteria:
            raise PromptValidationError(
                "Success Criteria section must contain at least one item.\n"
                "Use markdown list format:\n"
                "- Criterion 1\n"
                "- Criterion 2"
            )

        # Extract Constraints
        constraints_content = self._extract_section_content(
            content, self.CONSTRAINTS_HEADER
        )
        if not self.CONSTRAINTS_HEADER.search(content):
            raise PromptValidationError(
                "Prompt file is missing required '# Constraints' section.\n"
                "Example format:\n"
                "# Constraints\n"
                "- Budget limit: $5.00\n"
                "- Max iterations: 10\n"
                "- No modifications to core API"
            )

        constraints = self._parse_list_items(constraints_content)
        # Constraints can be empty list (section exists but no items)

        # Extract optional Context
        context_content = self._extract_section_content(content, self.CONTEXT_HEADER)
        context = context_content if context_content else None

        return PromptData(
            goal=goal_content,
            success_criteria=success_criteria,
            constraints=constraints,
            context=context,
            raw_content=content,
        )

    def load(self) -> PromptData:
        """
        Load and parse the prompt file.

        This is the main entry point for loading prompts. It reads the file,
        validates the format, and returns structured data.

        Returns:
            Parsed PromptData object

        Raises:
            PromptValidationError: If file doesn't exist, can't be read,
                                  or validation fails

        Examples:
            >>> loader = PromptLoader("experiment.md")
            >>> prompt = loader.load()
            >>> print(f"Goal: {prompt.goal}")
            >>> for criterion in prompt.success_criteria:
            ...     print(f"- {criterion}")
        """
        content = self._read_file()
        return self.parse(content)

    def validate_format(self) -> tuple[bool, List[str]]:
        """
        Validate prompt file format without raising exceptions.

        Useful for checking validity before attempting to load, or for
        providing detailed error feedback to users.

        Returns:
            Tuple of (is_valid, error_messages)
            - is_valid: True if format is valid
            - error_messages: List of validation errors (empty if valid)

        Examples:
            >>> loader = PromptLoader("experiment.md")
            >>> is_valid, errors = loader.validate_format()
            >>> if not is_valid:
            ...     for error in errors:
            ...         print(f"Error: {error}")
        """
        errors = []

        # Check file existence
        if not self.file_exists():
            errors.append(f"File not found: {self.prompt_path}")
            return False, errors

        # Try to read and parse
        try:
            content = self._read_file()
        except PromptValidationError as e:
            errors.append(str(e))
            return False, errors

        # Check for required sections
        if not self.GOAL_HEADER.search(content):
            errors.append("Missing required section: # Goal")

        if not self.SUCCESS_CRITERIA_HEADER.search(content):
            errors.append("Missing required section: # Success Criteria")

        if not self.CONSTRAINTS_HEADER.search(content):
            errors.append("Missing required section: # Constraints")

        # If headers missing, don't continue with content validation
        if errors:
            return False, errors

        # Try full parse to check content validity
        try:
            self.parse(content)
        except PromptValidationError as e:
            errors.append(str(e))

        is_valid = len(errors) == 0
        return is_valid, errors

    def get_summary(self) -> Dict[str, Any]:
        """
        Get a summary of the prompt without full parsing.

        Useful for displaying prompt information before execution.

        Returns:
            Dictionary with summary information:
                - file_path: Path to prompt file
                - exists: Whether file exists
                - has_goal: Whether Goal section exists
                - has_success_criteria: Whether Success Criteria section exists
                - has_constraints: Whether Constraints section exists
                - has_context: Whether Context section exists
                - is_valid: Overall validity

        Examples:
            >>> loader = PromptLoader("experiment.md")
            >>> summary = loader.get_summary()
            >>> print(f"Valid: {summary['is_valid']}")
            >>> print(f"Has context: {summary['has_context']}")
        """
        summary = {
            "file_path": str(self.prompt_path),
            "exists": self.file_exists(),
            "has_goal": False,
            "has_success_criteria": False,
            "has_constraints": False,
            "has_context": False,
            "is_valid": False,
        }

        if not summary["exists"]:
            return summary

        try:
            content = self._read_file()
            summary["has_goal"] = bool(self.GOAL_HEADER.search(content))
            summary["has_success_criteria"] = bool(
                self.SUCCESS_CRITERIA_HEADER.search(content)
            )
            summary["has_constraints"] = bool(self.CONSTRAINTS_HEADER.search(content))
            summary["has_context"] = bool(self.CONTEXT_HEADER.search(content))

            # Check overall validity
            is_valid, _ = self.validate_format()
            summary["is_valid"] = is_valid

        except PromptValidationError:
            pass

        return summary
