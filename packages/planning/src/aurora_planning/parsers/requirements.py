"""Requirements block parsing utilities.

Ported from: src/core/parsers/requirement-blocks.ts
Terminology: delta→modification, spec→capability

Provides utilities for extracting and parsing requirement blocks
from markdown files, including delta (modification) spec parsing.
"""

import re
from dataclasses import dataclass, field


@dataclass
class RequirementBlock:
    """A parsed requirement block.

    Represents a single requirement with its header and raw content.
    """

    header_line: str  # e.g., '### Requirement: Something'
    name: str  # e.g., 'Something'
    raw: str  # full block including header_line and following content


@dataclass
class RequirementsSectionParts:
    """Parts of a requirements section from a spec file.

    Used for extracting and manipulating requirements sections.
    """

    before: str  # Content before the Requirements section
    header_line: str  # The '## Requirements' line
    preamble: str  # Content between header and first requirement
    body_blocks: list[RequirementBlock]  # Parsed requirement blocks
    after: str  # Content after the Requirements section


@dataclass
class ModificationPlan:
    """A parsed modification (delta) plan from a spec file.

    Contains categorized requirement blocks by operation type.
    """

    added: list[RequirementBlock] = field(default_factory=list)
    modified: list[RequirementBlock] = field(default_factory=list)
    removed: list[str] = field(default_factory=list)  # requirement names
    renamed: list[dict[str, str]] = field(default_factory=list)  # {from, to}
    section_presence: dict[str, bool] = field(
        default_factory=lambda: {
            "added": False,
            "modified": False,
            "removed": False,
            "renamed": False,
        },
    )


# Regex pattern for requirement headers
REQUIREMENT_HEADER_REGEX = re.compile(r"^###\s*Requirement:\s*(.+)\s*$")


def normalize_requirement_name(name: str) -> str:
    """Normalize a requirement name by trimming whitespace.

    Args:
        name: Raw requirement name

    Returns:
        Normalized requirement name

    """
    return name.strip()


def _normalize_line_endings(content: str) -> str:
    """Normalize line endings to Unix style.

    Args:
        content: Content with potentially mixed line endings

    Returns:
        Content with Unix line endings only

    """
    return re.sub(r"\r\n?", "\n", content)


def extract_requirements_section(content: str) -> RequirementsSectionParts:
    """Extract the Requirements section from a spec file.

    Parses the content to find the ## Requirements section and
    extracts all requirement blocks within it.

    Args:
        content: Full spec file content

    Returns:
        RequirementsSectionParts with parsed sections and blocks

    """
    normalized = _normalize_line_endings(content)
    lines = normalized.split("\n")

    # Find the Requirements header
    req_header_index = -1
    for i, line in enumerate(lines):
        if re.match(r"^##\s+Requirements\s*$", line, re.IGNORECASE):
            req_header_index = i
            break

    if req_header_index == -1:
        # No requirements section; create an empty one at the end
        before = content.rstrip()
        header_line = "## Requirements"
        return RequirementsSectionParts(
            before=before + "\n\n" if before else "",
            header_line=header_line,
            preamble="",
            body_blocks=[],
            after="\n",
        )

    # Find end of this section: next line that starts with '## '
    end_index = len(lines)
    for i in range(req_header_index + 1, len(lines)):
        if re.match(r"^##\s+", lines[i]):
            end_index = i
            break

    before = "\n".join(lines[:req_header_index])
    header_line = lines[req_header_index]
    section_body_lines = lines[req_header_index + 1 : end_index]

    # Parse requirement blocks within section body
    blocks: list[RequirementBlock] = []
    cursor = 0
    preamble_lines: list[str] = []

    # Collect preamble lines until first requirement header
    while cursor < len(section_body_lines):
        if re.match(r"^###\s+Requirement:", section_body_lines[cursor]):
            break
        preamble_lines.append(section_body_lines[cursor])
        cursor += 1

    # Parse requirement blocks
    while cursor < len(section_body_lines):
        header_line_candidate = section_body_lines[cursor]
        header_match = REQUIREMENT_HEADER_REGEX.match(header_line_candidate)

        if not header_match:
            cursor += 1
            continue

        name = normalize_requirement_name(header_match.group(1))
        cursor += 1

        # Gather lines until next requirement header or end of section
        body_lines: list[str] = [header_line_candidate]
        while cursor < len(section_body_lines):
            line = section_body_lines[cursor]
            if re.match(r"^###\s+Requirement:", line):
                break
            if re.match(r"^##\s+", line):
                break
            body_lines.append(line)
            cursor += 1

        raw = "\n".join(body_lines).rstrip()
        blocks.append(
            RequirementBlock(
                header_line=header_line_candidate,
                name=name,
                raw=raw,
            ),
        )

    after = "\n".join(lines[end_index:])
    preamble = "\n".join(preamble_lines).rstrip()

    return RequirementsSectionParts(
        before=before.rstrip() + "\n" if before.rstrip() else before,
        header_line=header_line,
        preamble=preamble,
        body_blocks=blocks,
        after="\n" + after if after and not after.startswith("\n") else after,
    )


def _split_top_level_sections(content: str) -> dict[str, str]:
    """Split content into top-level sections (## headers).

    Args:
        content: Normalized content to split

    Returns:
        Dict mapping section titles to their body content

    """
    lines = content.split("\n")
    result: dict[str, str] = {}
    indices: list[tuple[str, int]] = []

    for i, line in enumerate(lines):
        match = re.match(r"^##\s+(.+)$", line)
        if match:
            title = match.group(1).strip()
            indices.append((title, i))

    for i, (title, start_idx) in enumerate(indices):
        if i + 1 < len(indices):
            end_idx = indices[i + 1][1]
        else:
            end_idx = len(lines)

        body = "\n".join(lines[start_idx + 1 : end_idx])
        result[title] = body

    return result


def _get_section_case_insensitive(sections: dict[str, str], desired: str) -> tuple[str, bool]:
    """Get a section by title (case-insensitive).

    Args:
        sections: Dict of section titles to bodies
        desired: Desired section title

    Returns:
        Tuple of (section body, found flag)

    """
    target = desired.lower()
    for title, body in sections.items():
        if title.lower() == target:
            return body, True
    return "", False


def _parse_requirement_blocks_from_section(section_body: str) -> list[RequirementBlock]:
    """Parse requirement blocks from a section body.

    Args:
        section_body: Body content of a section

    Returns:
        List of RequirementBlock objects

    """
    if not section_body:
        return []

    lines = _normalize_line_endings(section_body).split("\n")
    blocks: list[RequirementBlock] = []
    i = 0

    while i < len(lines):
        # Seek next requirement header
        while i < len(lines) and not re.match(r"^###\s+Requirement:", lines[i]):
            i += 1

        if i >= len(lines):
            break

        header_line = lines[i]
        match = REQUIREMENT_HEADER_REGEX.match(header_line)
        if not match:
            i += 1
            continue

        name = normalize_requirement_name(match.group(1))
        buf: list[str] = [header_line]
        i += 1

        # Gather content until next requirement or section
        while i < len(lines):
            line = lines[i]
            if re.match(r"^###\s+Requirement:", line):
                break
            if re.match(r"^##\s+", line):
                break
            buf.append(line)
            i += 1

        blocks.append(
            RequirementBlock(
                header_line=header_line,
                name=name,
                raw="\n".join(buf).rstrip(),
            ),
        )

    return blocks


def _parse_removed_names(section_body: str) -> list[str]:
    """Parse requirement names from a REMOVED section.

    Supports both full requirement headers and bullet list format.

    Args:
        section_body: Body of the REMOVED Requirements section

    Returns:
        List of requirement names marked for removal

    """
    if not section_body:
        return []

    names: list[str] = []
    lines = _normalize_line_endings(section_body).split("\n")

    for line in lines:
        # Match full requirement header
        match = REQUIREMENT_HEADER_REGEX.match(line)
        if match:
            names.append(normalize_requirement_name(match.group(1)))
            continue

        # Match bullet list format
        bullet_match = re.match(r"^\s*-\s*`?###\s*Requirement:\s*(.+?)`?\s*$", line)
        if bullet_match:
            names.append(normalize_requirement_name(bullet_match.group(1)))

    return names


def _parse_renamed_pairs(section_body: str) -> list[dict[str, str]]:
    """Parse rename pairs from a RENAMED section.

    Format:
    - FROM: `### Requirement: Old Name`
    - TO: `### Requirement: New Name`

    Args:
        section_body: Body of the RENAMED Requirements section

    Returns:
        List of rename dicts with 'from' and 'to' keys

    """
    if not section_body:
        return []

    pairs: list[dict[str, str]] = []
    lines = _normalize_line_endings(section_body).split("\n")
    current: dict[str, str] = {}

    for line in lines:
        from_match = re.match(r"^\s*-?\s*FROM:\s*`?###\s*Requirement:\s*(.+?)`?\s*$", line)
        to_match = re.match(r"^\s*-?\s*TO:\s*`?###\s*Requirement:\s*(.+?)`?\s*$", line)

        if from_match:
            current["from"] = normalize_requirement_name(from_match.group(1))
        elif to_match:
            current["to"] = normalize_requirement_name(to_match.group(1))

            if current.get("from") and current.get("to"):
                pairs.append(
                    {
                        "from": current["from"],
                        "to": current["to"],
                    },
                )
                current = {}

    return pairs


def parse_modification_spec(content: str) -> ModificationPlan:
    """Parse a modification (delta) formatted spec file.

    Extracts ADDED, MODIFIED, REMOVED, and RENAMED requirements
    from a delta spec file format.

    Args:
        content: Delta spec file content

    Returns:
        ModificationPlan with categorized requirements

    """
    normalized = _normalize_line_endings(content)
    sections = _split_top_level_sections(normalized)

    added_body, added_found = _get_section_case_insensitive(sections, "ADDED Requirements")
    modified_body, modified_found = _get_section_case_insensitive(sections, "MODIFIED Requirements")
    removed_body, removed_found = _get_section_case_insensitive(sections, "REMOVED Requirements")
    renamed_body, renamed_found = _get_section_case_insensitive(sections, "RENAMED Requirements")

    return ModificationPlan(
        added=_parse_requirement_blocks_from_section(added_body),
        modified=_parse_requirement_blocks_from_section(modified_body),
        removed=_parse_removed_names(removed_body),
        renamed=_parse_renamed_pairs(renamed_body),
        section_presence={
            "added": added_found,
            "modified": modified_found,
            "removed": removed_found,
            "renamed": renamed_found,
        },
    )
