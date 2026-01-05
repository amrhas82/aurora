"""
Simplified Prompt File Parser and Validator for Headless Mode

This module provides a streamlined implementation for loading and validating
experiment prompt files with only essential sections.

Prompt File Format:
    # Goal
    Clear statement of what needs to be achieved.

    # Success Criteria
    - Measurable criterion 1
    - Measurable criterion 2

    # Constraints (optional)
    - Constraint 1
    - Constraint 2

    # Context (optional)
    Additional background information.

Usage:
    from aurora_soar.headless.prompt_loader_simplified import PromptLoader, PromptData

    loader = PromptLoader("experiment.md")
    prompt = loader.load()

    print(f"Goal: {prompt.goal}")
    print(f"Success Criteria: {prompt.success_criteria}")
"""

import re
from dataclasses import dataclass, field
from pathlib import Path


class PromptValidationError(Exception):
    """Raised when prompt file validation fails."""
    pass


@dataclass
class PromptData:
    """
    Parsed and validated prompt data.

    Attributes:
        goal: The main objective statement
        success_criteria: List of measurable success conditions
        constraints: List of constraints (optional, defaults to empty list)
        context: Additional context (optional, defaults to empty string)
    """
    goal: str
    success_criteria: list[str]
    constraints: list[str] = field(default_factory=list)
    context: str = ""


class PromptLoader:
    """
    Simplified loader for experiment prompt files.

    This loader parses markdown files with structured sections and validates
    that required sections are present and non-empty.

    Required Sections:
        - # Goal: Non-empty objective statement
        - # Success Criteria: At least one criterion

    Optional Sections:
        - # Constraints: List of constraints
        - # Context: Additional background
    """

    # Section header patterns
    GOAL_HEADER = re.compile(r"^#\s+Goal\s*$", re.IGNORECASE | re.MULTILINE)
    SUCCESS_CRITERIA_HEADER = re.compile(r"^#\s+Success\s+Criteria\s*$", re.IGNORECASE | re.MULTILINE)
    CONSTRAINTS_HEADER = re.compile(r"^#\s+Constraints?\s*$", re.IGNORECASE | re.MULTILINE)
    CONTEXT_HEADER = re.compile(r"^#\s+Context\s*$", re.IGNORECASE | re.MULTILINE)

    def __init__(self, prompt_path: str | Path):
        """
        Initialize PromptLoader.

        Args:
            prompt_path: Path to the markdown prompt file
        """
        self.prompt_path = Path(prompt_path)

    def load(self) -> PromptData:
        """
        Load and parse the prompt file.

        Returns:
            Parsed PromptData object

        Raises:
            PromptValidationError: If file not found or validation fails
        """
        # Check file exists
        if not self.prompt_path.exists():
            raise PromptValidationError(
                f"Prompt file not found: {self.prompt_path}"
            )

        if not self.prompt_path.is_file():
            raise PromptValidationError(
                f"Prompt path is a directory, not a file: {self.prompt_path}"
            )

        # Read content
        try:
            content = self.prompt_path.read_text(encoding="utf-8")
        except Exception as e:
            raise PromptValidationError(
                f"Error reading prompt file: {e}"
            ) from e

        # Parse content
        return self._parse(content)

    def _parse(self, content: str) -> PromptData:
        """
        Parse markdown content into PromptData.

        Args:
            content: Markdown file content

        Returns:
            Parsed PromptData

        Raises:
            PromptValidationError: If required sections missing or invalid
        """
        # Extract Goal
        goal = self._extract_section(content, self.GOAL_HEADER)
        if not goal:
            raise PromptValidationError(
                "Goal section is required. Goal cannot be empty"
            )

        # Extract Success Criteria
        success_content = self._extract_section(content, self.SUCCESS_CRITERIA_HEADER)
        if not success_content:
            raise PromptValidationError(
                "Success Criteria section is required. Success Criteria cannot be empty"
            )

        success_criteria = self._parse_list_items(success_content)
        if not success_criteria:
            raise PromptValidationError(
                "Success Criteria must contain at least one item"
            )

        # Extract optional Constraints
        constraints_content = self._extract_section(content, self.CONSTRAINTS_HEADER)
        constraints = self._parse_list_items(constraints_content) if constraints_content else []

        # Extract optional Context
        context = self._extract_section(content, self.CONTEXT_HEADER) or ""

        return PromptData(
            goal=goal,
            success_criteria=success_criteria,
            constraints=constraints,
            context=context
        )

    def _extract_section(self, content: str, header_pattern: re.Pattern) -> str:
        """
        Extract content between a section header and the next header.

        Args:
            content: Full markdown content
            header_pattern: Regex pattern for section header

        Returns:
            Section content (stripped), or empty string if not found
        """
        match = header_pattern.search(content)
        if not match:
            return ""

        # Find start of content (after header line)
        start_pos = match.end()

        # Find next header (or end of file)
        remaining_content = content[start_pos:]
        next_header_match = re.search(r"^#\s+", remaining_content, re.MULTILINE)

        if next_header_match:
            end_pos = start_pos + next_header_match.start()
            section_content = content[start_pos:end_pos]
        else:
            section_content = remaining_content

        return section_content.strip()

    def _parse_list_items(self, content: str) -> list[str]:
        """
        Parse markdown list items (lines starting with - or *).

        Args:
            content: Section content

        Returns:
            List of items (without bullet points)
        """
        items = []
        for line in content.split('\n'):
            line = line.strip()
            # Match lines starting with - or * followed by content
            if line.startswith('- ') or line.startswith('* '):
                item = line[2:].strip()
                if item:
                    items.append(item)
        return items
