"""PlanParser for parsing plan files with modification specifications.

Extends MarkdownParser to support parsing modification (delta) spec files from
the capability-specs/ directory within a plan folder. This allows plans to
specify detailed requirement-level changes using the modification spec format.
"""

from __future__ import annotations

import re
from pathlib import Path

from aurora_cli.planning.parsers.markdown import (
    MarkdownParser,
    ParsedModification,
    ParsedPlan,
    ParsedPlanMetadata,
    ParsedRequirement,
    Section,
)
from aurora_cli.planning.schemas.plan import ModificationOperation


class PlanParser(MarkdownParser):
    """Parser for plan files with modification specifications.

    Extends MarkdownParser to support parsing modification spec files from the
    capability-specs/ directory within a plan folder. This enables:

    1. Parsing main plan markdown (Why, What Changes sections)
    2. Loading modification spec files from capability-specs/ subdirectory
    3. Combining modifications from both sources

    The capability-specs/ directory structure:
    ```
    .aurora/plans/active/0001-my-plan/
    ├── plan.md (main plan file)
    └── capability-specs/
        ├── http-server/
        │   └── spec.md (modification spec with ADDED/MODIFIED/REMOVED/RENAMED)
        └── auth-system/
            └── spec.md
    ```
    """

    def __init__(self, content: str, plan_dir: str) -> None:
        """Initialize parser with content and plan directory.

        Args:
            content: Raw markdown content from plan.md
            plan_dir: Path to plan directory (for loading modification specs)

        """
        super().__init__(content)
        self._plan_dir = Path(plan_dir)

    def parse_plan_with_modifications(self, name: str) -> ParsedPlan:
        """Parse plan content with modification specifications from spec files.

        This method performs the complete parsing workflow:
        1. Parses the main plan markdown (Why, What Changes)
        2. Checks for modification spec files in capability-specs/ subdirectory
        3. Combines modifications from both sources

        Modification specs take precedence over simple What Changes entries.

        Args:
            name: Name to assign to the plan

        Returns:
            ParsedPlan with modifications from both sources

        Raises:
            ValueError: If required sections (Why, What Changes) are missing

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

        # Parse simple modifications from What Changes section
        simple_modifications = self._parse_modifications(what_changes)

        # Try to parse modification spec files
        specs_dir = self._plan_dir / "capability-specs"
        modification_specs = self._parse_modification_specs(specs_dir)

        # Prefer modification specs if available, otherwise use simple
        modifications = modification_specs if modification_specs else simple_modifications

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

    def _parse_modification_specs(self, specs_dir: Path) -> list[ParsedModification]:
        """Parse modification spec files from capability-specs directory.

        Loads all spec.md files from capability subdirectories and parses their
        ADDED/MODIFIED/REMOVED/RENAMED sections.

        Args:
            specs_dir: Path to capability-specs directory

        Returns:
            List of modifications from modification spec files

        """
        modifications: list[ParsedModification] = []

        if not specs_dir.exists():
            return modifications

        try:
            for spec_path in specs_dir.iterdir():
                if not spec_path.is_dir():
                    continue

                capability_name = spec_path.name
                spec_file = spec_path / "spec.md"

                if not spec_file.exists():
                    continue

                try:
                    content = spec_file.read_text(encoding="utf-8")
                    spec_modifications = self._parse_spec_modifications(capability_name, content)
                    modifications.extend(spec_modifications)
                except OSError:
                    # Spec file couldn't be read, skip it
                    continue

        except OSError:
            # Specs directory couldn't be read
            return []

        return modifications

    def _parse_spec_modifications(
        self,
        capability_name: str,
        content: str,
    ) -> list[ParsedModification]:
        """Parse modification operations from a spec file content.

        Extracts ADDED, MODIFIED, REMOVED, and RENAMED requirements from the
        modification spec file.

        Args:
            capability_name: Name of the capability being modified
            content: Content of the modification spec file

        Returns:
            List of modifications parsed from the spec

        """
        modifications: list[ParsedModification] = []
        sections = self._parse_sections_from_content(content)

        # Parse ADDED requirements
        added_section = self._find_section(sections, "ADDED Requirements")
        if added_section:
            requirements = self._parse_modification_requirements(added_section)
            for req in requirements:
                modifications.append(
                    ParsedModification(
                        capability=capability_name,
                        operation=ModificationOperation.ADDED,
                        description=f"Add requirement: {req.text}",
                        requirement=req,
                        requirements=[req],
                    ),
                )

        # Parse MODIFIED requirements
        modified_section = self._find_section(sections, "MODIFIED Requirements")
        if modified_section:
            requirements = self._parse_modification_requirements(modified_section)
            for req in requirements:
                modifications.append(
                    ParsedModification(
                        capability=capability_name,
                        operation=ModificationOperation.MODIFIED,
                        description=f"Modify requirement: {req.text}",
                        requirement=req,
                        requirements=[req],
                    ),
                )

        # Parse REMOVED requirements
        removed_section = self._find_section(sections, "REMOVED Requirements")
        if removed_section:
            requirements = self._parse_modification_requirements(removed_section)
            for req in requirements:
                modifications.append(
                    ParsedModification(
                        capability=capability_name,
                        operation=ModificationOperation.REMOVED,
                        description=f"Remove requirement: {req.text}",
                        requirement=req,
                        requirements=[req],
                    ),
                )

        # Parse RENAMED requirements
        renamed_section = self._find_section(sections, "RENAMED Requirements")
        if renamed_section:
            renames = self._parse_renames(renamed_section.content)
            for rename in renames:
                modifications.append(
                    ParsedModification(
                        capability=capability_name,
                        operation=ModificationOperation.RENAMED,
                        description=f'Rename requirement from "{rename["from"]}" '
                        f'to "{rename["to"]}"',
                        rename=rename,
                    ),
                )

        return modifications

    def _parse_modification_requirements(self, section: Section) -> list[ParsedRequirement]:
        """Parse requirements from a modification section.

        Modification sections may have metadata fields (ID, Priority) before the
        requirement text. This method extracts the actual requirement text and
        scenarios.

        Args:
            section: Section containing requirements

        Returns:
            List of parsed requirements

        """
        requirements: list[ParsedRequirement] = []

        for child in section.children:
            # Extract requirement text, handling metadata fields
            text = self._extract_requirement_text(child)
            scenarios = self._parse_scenarios(child)

            requirements.append(
                ParsedRequirement(
                    text=text,
                    scenarios=scenarios,
                ),
            )

        return requirements

    def _extract_requirement_text(self, section: Section) -> str:
        """Extract requirement text from section, handling metadata.

        The requirement text may appear after metadata fields like:
        **ID**: REQ-001
        **Priority**: P1

        This method skips metadata fields and extracts the actual requirement text.

        Args:
            section: Section to extract text from

        Returns:
            The requirement text (first non-metadata line with content)

        """
        # Start with section title as fallback
        text = section.title

        if not section.content.strip():
            return text

        lines = section.content.split("\n")
        content_before_children: list[str] = []

        for line in lines:
            # Stop at child headers (scenarios)
            if line.strip().startswith("#"):
                break
            content_before_children.append(line)

        # Find first line that looks like requirement text
        # (not a metadata field like **ID**: ...)
        for line in content_before_children:
            stripped = line.strip()
            if not stripped:
                continue

            # Skip metadata fields
            if stripped.startswith("**") and ":" in stripped:
                continue

            # Found content line
            text = stripped
            break

        return text

    def _parse_renames(self, content: str) -> list[dict[str, str]]:
        """Parse rename pairs from content.

        Format:
        - FROM: `### Requirement: Old Name`
        - TO: `### Requirement: New Name`

        Or without backticks:
        - FROM: ### Requirement: Old Name
        - TO: ### Requirement: New Name

        Args:
            content: Content containing rename pairs

        Returns:
            List of rename dicts with 'from' and 'to' keys

        """
        renames: list[dict[str, str]] = []
        lines = self._normalize_content(content).split("\n")

        current_rename: dict[str, str] = {}

        for line in lines:
            from_match = re.match(r"^\s*-?\s*FROM:\s*`?###\s*Requirement:\s*(.+?)`?\s*$", line)
            to_match = re.match(r"^\s*-?\s*TO:\s*`?###\s*Requirement:\s*(.+?)`?\s*$", line)

            if from_match:
                current_rename["from"] = from_match.group(1).strip()
            elif to_match:
                current_rename["to"] = to_match.group(1).strip()

                if current_rename.get("from") and current_rename.get("to"):
                    renames.append(
                        {
                            "from": current_rename["from"],
                            "to": current_rename["to"],
                        },
                    )
                    current_rename = {}

        return renames

    def _parse_sections_from_content(self, content: str) -> list[Section]:
        """Parse sections from content string (not using instance lines).

        Used for parsing modification spec file content independently from the
        main plan content.

        Args:
            content: Markdown content to parse

        Returns:
            List of sections with proper nesting

        """
        normalized_content = self._normalize_content(content)
        lines = normalized_content.split("\n")
        sections: list[Section] = []
        stack: list[Section] = []

        for i, line in enumerate(lines):
            header_match = re.match(r"^(#{1,6})\s+(.+)$", line)

            if header_match:
                level = len(header_match.group(1))
                title = header_match.group(2).strip()
                content_lines = self._get_content_until_next_header_from_lines(lines, i + 1, level)

                section = Section(
                    level=level,
                    title=title,
                    content="\n".join(content_lines).strip(),
                    children=[],
                )

                while stack and stack[-1].level >= level:
                    stack.pop()

                if not stack:
                    sections.append(section)
                else:
                    stack[-1].children.append(section)

                stack.append(section)

        return sections

    def _get_content_until_next_header_from_lines(
        self,
        lines: list[str],
        start_line: int,
        current_level: int,
    ) -> list[str]:
        """Get content lines until next header of same or higher level.

        Helper method for parsing sections from a separate content string.

        Args:
            lines: All lines from content
            start_line: Line index to start from
            current_level: Current header level

        Returns:
            List of content lines (not joined)

        """
        content_lines: list[str] = []

        for i in range(start_line, len(lines)):
            line = lines[i]
            header_match = re.match(r"^(#{1,6})\s+", line)

            if header_match and len(header_match.group(1)) <= current_level:
                break

            content_lines.append(line)

        return content_lines
