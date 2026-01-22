"""MarkdownParser for parsing capability and plan markdown files.

Ported from: src/core/parsers/markdown-parser.ts
Terminology: spec→capability, change→plan, delta→modification

Note: This parser returns "parsed" dataclasses without validation.
Validation is done separately by the Validator class.
This matches TypeScript behavior where MarkdownParser returns plain objects.
"""

import re
from dataclasses import dataclass, field

from aurora_planning.schemas.plan import ModificationOperation


@dataclass
class Section:
    """A parsed markdown section."""

    level: int
    title: str
    content: str
    children: list["Section"] = field(default_factory=list)


@dataclass
class ParsedScenario:
    """A parsed scenario (unvalidated).

    Matches TypeScript Scenario interface behavior.
    """

    raw_text: str


@dataclass
class ParsedRequirement:
    """A parsed requirement (unvalidated).

    Matches TypeScript Requirement interface behavior.
    """

    text: str
    scenarios: list[ParsedScenario] = field(default_factory=list)


@dataclass
class ParsedCapabilityMetadata:
    """Metadata for a parsed capability."""

    version: str = "1.0.0"
    format: str = "aurora-capability"


@dataclass
class ParsedCapability:
    """A parsed capability (unvalidated, was Spec).

    Matches TypeScript Spec interface behavior.
    """

    name: str
    overview: str
    requirements: list[ParsedRequirement] = field(default_factory=list)
    metadata: ParsedCapabilityMetadata | None = None


@dataclass
class ParsedModification:
    """A parsed modification (unvalidated, was Delta).

    Matches TypeScript Delta interface behavior.
    """

    capability: str
    operation: ModificationOperation
    description: str
    requirement: ParsedRequirement | None = None
    requirements: list[ParsedRequirement] | None = None
    rename: dict[str, str] | None = None  # {from: str, to: str}


@dataclass
class ParsedPlanMetadata:
    """Metadata for a parsed plan."""

    version: str = "1.0.0"
    format: str = "aurora-plan"


@dataclass
class ParsedPlan:
    """A parsed plan (unvalidated, was Change).

    Matches TypeScript Change interface behavior.
    """

    name: str
    why: str
    what_changes: str
    modifications: list[ParsedModification] = field(default_factory=list)
    metadata: ParsedPlanMetadata | None = None


class MarkdownParser:
    """Parser for markdown files containing capabilities or plans.

    Ported from: MarkdownParser class in TypeScript
    """

    def __init__(self, content: str) -> None:
        """Initialize parser with markdown content.

        Args:
            content: Raw markdown content to parse

        """
        normalized = self._normalize_content(content)
        self._lines = normalized.split("\n")
        self._current_line = 0

    @staticmethod
    def _normalize_content(content: str) -> str:
        """Normalize line endings to Unix style.

        Args:
            content: Content with potentially mixed line endings

        Returns:
            Content with Unix line endings only

        """
        return re.sub(r"\r\n?", "\n", content)

    def parse_capability(self, name: str) -> ParsedCapability:
        """Parse content as a capability (was parseSpec).

        Args:
            name: Name to assign to the capability

        Returns:
            ParsedCapability object (unvalidated)

        Raises:
            ValueError: If required sections are missing

        """
        sections = self._parse_sections()
        purpose_section = self._find_section(sections, "Purpose")
        requirements_section = self._find_section(sections, "Requirements")

        purpose = purpose_section.content if purpose_section else ""

        if not purpose:
            raise ValueError("Capability must have a Purpose section")

        if not requirements_section:
            raise ValueError("Capability must have a Requirements section")

        requirements = self._parse_requirements(requirements_section)

        return ParsedCapability(
            name=name,
            overview=purpose.strip(),
            requirements=requirements,
            metadata=ParsedCapabilityMetadata(
                version="1.0.0",
                format="aurora-capability",
            ),
        )

    def parse_plan(self, name: str) -> ParsedPlan:
        """Parse content as a plan (was parseChange).

        Args:
            name: Name to assign to the plan

        Returns:
            ParsedPlan object (unvalidated)

        Raises:
            ValueError: If required sections are missing

        """
        sections = self._parse_sections()
        why_section = self._find_section(sections, "Why")
        what_changes_section = self._find_section(sections, "What Changes")

        why = why_section.content if why_section else ""
        what_changes = what_changes_section.content if what_changes_section else ""

        if not why:
            raise ValueError("Plan must have a Why section")

        if not what_changes:
            raise ValueError("Plan must have a What Changes section")

        modifications = self._parse_modifications(what_changes)

        return ParsedPlan(
            name=name,
            why=why.strip(),
            what_changes=what_changes.strip(),
            modifications=modifications,
            metadata=ParsedPlanMetadata(
                version="1.0.0",
                format="aurora-plan",
            ),
        )

    def _parse_sections(self) -> list[Section]:
        """Parse all sections from the markdown content.

        Returns:
            List of top-level sections with nested children

        """
        sections: list[Section] = []
        stack: list[Section] = []

        for i, line in enumerate(self._lines):
            header_match = re.match(r"^(#{1,6})\s+(.+)$", line)

            if header_match:
                level = len(header_match.group(1))
                title = header_match.group(2).strip()
                content = self._get_content_until_next_header(i + 1, level)

                section = Section(
                    level=level,
                    title=title,
                    content=content,
                    children=[],
                )

                # Pop sections at same or deeper level
                while stack and stack[-1].level >= level:
                    stack.pop()

                # Add to parent or root
                if not stack:
                    sections.append(section)
                else:
                    stack[-1].children.append(section)

                stack.append(section)

        return sections

    def _get_content_until_next_header(self, start_line: int, current_level: int) -> str:
        """Get content from start_line until next header of same or higher level.

        Args:
            start_line: Line index to start from
            current_level: Current header level (1-6)

        Returns:
            Content as string

        """
        content_lines: list[str] = []

        for i in range(start_line, len(self._lines)):
            line = self._lines[i]
            header_match = re.match(r"^(#{1,6})\s+", line)

            if header_match and len(header_match.group(1)) <= current_level:
                break

            content_lines.append(line)

        return "\n".join(content_lines).strip()

    def _find_section(self, sections: list[Section], title: str) -> Section | None:
        """Find a section by title (case-insensitive).

        Args:
            sections: List of sections to search
            title: Title to find

        Returns:
            Found section or None

        """
        for section in sections:
            if section.title.lower() == title.lower():
                return section
            child = self._find_section(section.children, title)
            if child:
                return child
        return None

    def _parse_requirements(self, section: Section) -> list[ParsedRequirement]:
        """Parse requirements from a section.

        Args:
            section: Requirements section to parse

        Returns:
            List of ParsedRequirement objects (unvalidated)

        """
        requirements: list[ParsedRequirement] = []

        for child in section.children:
            # Extract requirement text from first non-empty content line,
            # fall back to heading
            text = child.title

            # Get content before any child sections (scenarios)
            if child.content.strip():
                lines = child.content.split("\n")
                content_before_children: list[str] = []

                for line in lines:
                    # Stop at child headers (scenarios start with ####)
                    if line.strip().startswith("#"):
                        break
                    content_before_children.append(line)

                # Find first non-empty line
                direct_content = "\n".join(content_before_children).strip()
                if direct_content:
                    first_line = next(
                        (ln for ln in direct_content.split("\n") if ln.strip()),
                        None,
                    )
                    if first_line:
                        text = first_line.strip()

            scenarios = self._parse_scenarios(child)

            requirements.append(
                ParsedRequirement(
                    text=text,
                    scenarios=scenarios,
                ),
            )

        return requirements

    def _parse_scenarios(self, requirement_section: Section) -> list[ParsedScenario]:
        """Parse scenarios from a requirement section.

        Args:
            requirement_section: Section containing scenarios as children

        Returns:
            List of ParsedScenario objects (unvalidated)

        """
        scenarios: list[ParsedScenario] = []

        for scenario_section in requirement_section.children:
            # Store the raw text content of the scenario section
            if scenario_section.content.strip():
                scenarios.append(ParsedScenario(raw_text=scenario_section.content))

        return scenarios

    def _parse_modifications(self, content: str) -> list[ParsedModification]:
        """Parse modifications (was deltas) from content.

        Args:
            content: What Changes section content

        Returns:
            List of ParsedModification objects (unvalidated)

        """
        modifications: list[ParsedModification] = []
        lines = content.split("\n")

        for line in lines:
            # Match both formats: **spec:** and **spec**:
            modification_match = re.match(r"^\s*-\s*\*\*([^*:]+)(?::\*\*|\*\*:)\s*(.+)$", line)
            if modification_match:
                capability_name = modification_match.group(1).strip()
                description = modification_match.group(2).strip()

                operation = ModificationOperation.MODIFIED
                lower_desc = description.lower()

                # Use word boundaries to avoid false matches
                # Check RENAMED first since it's more specific
                if re.search(r"\brename[sd]?\b", lower_desc) or re.search(
                    r"\brenamed\s+(to|from)\b",
                    lower_desc,
                ):
                    operation = ModificationOperation.RENAMED
                elif (
                    re.search(r"\badd[sed]?\b", lower_desc)
                    or re.search(r"\bcreate[sd]?\b", lower_desc)
                    or re.search(r"\bnew\b", lower_desc)
                ):
                    operation = ModificationOperation.ADDED
                elif re.search(r"\bremove[sd]?\b", lower_desc) or re.search(
                    r"\bdelete[sd]?\b",
                    lower_desc,
                ):
                    operation = ModificationOperation.REMOVED

                modifications.append(
                    ParsedModification(
                        capability=capability_name,
                        operation=operation,
                        description=description,
                    ),
                )

        return modifications
