"""Knowledge Chunk Parser for AURORA.

Parses conversation logs and documentation into searchable knowledge chunks.
Extracts metadata from filenames and splits by markdown sections.
"""

import logging
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class KnowledgeChunk:
    """Represents a knowledge chunk with content and metadata."""

    content: str
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Validate chunk after initialization."""
        if not isinstance(self.content, str):
            raise TypeError("content must be a string")
        if not isinstance(self.metadata, dict):
            raise TypeError("metadata must be a dictionary")


class KnowledgeParser:
    """Parser for conversation logs and knowledge documents."""

    def __init__(self) -> None:
        """Initialize the knowledge parser."""
        self.logger = logging.getLogger(__name__)

    def parse_conversation_log(self, file_path: Path) -> list[KnowledgeChunk]:
        """Parse a conversation log file into knowledge chunks.

        Args:
            file_path: Path to the markdown file

        Returns:
            List of KnowledgeChunk objects, one per markdown section

        Strategy:
            1. Extract metadata from filename (keywords, date if present)
            2. Read file content
            3. Split by ## headers (markdown sections)
            4. Create a chunk for each section with shared metadata

        """
        if not file_path.exists():
            self.logger.warning(f"File not found: {file_path}")
            return []

        # Extract metadata from filename
        metadata = self._extract_metadata_from_filename(file_path)

        # Read file content
        try:
            content = file_path.read_text(encoding="utf-8")
        except Exception as e:
            self.logger.error(f"Failed to read {file_path}: {e}")
            return []

        # Handle empty files
        if not content.strip():
            self.logger.debug(f"Empty file: {file_path}")
            return []

        # Split by markdown sections
        chunks = self._split_by_sections(content, metadata, file_path)

        return chunks

    def _extract_metadata_from_filename(self, file_path: Path) -> dict[str, Any]:
        """Extract metadata from filename.

        Filename patterns:
            - 2024-01-15_semantic_search.md → date + keywords
            - semantic_search_discussion.md → keywords only

        Args:
            file_path: Path to the file

        Returns:
            Dictionary with metadata (keywords, date, source_file)

        """
        filename = file_path.stem  # Without extension

        metadata: dict[str, Any] = {"source_file": str(file_path), "keywords": []}

        # Try to extract date (YYYY-MM-DD pattern at start)
        date_match = re.match(r"^(\d{4}-\d{2}-\d{2})_(.+)$", filename)
        if date_match:
            metadata["date"] = date_match.group(1)
            keywords_part = date_match.group(2)
        else:
            keywords_part = filename

        # Extract keywords from filename (split by underscore, filter short words)
        keywords = [
            word.lower()
            for word in re.split(r"[_\-\s]+", keywords_part)
            if len(word) > 2  # Skip very short words
        ]

        metadata["keywords"] = keywords

        return metadata

    def _split_by_sections(
        self,
        content: str,
        base_metadata: dict[str, Any],
        file_path: Path,
    ) -> list[KnowledgeChunk]:
        """Split content by markdown ## headers.

        Args:
            content: Full file content
            base_metadata: Metadata extracted from filename
            file_path: Source file path

        Returns:
            List of KnowledgeChunk objects, one per section

        """
        chunks = []

        # Split by level-2 headers (##), excluding single # headers
        section_pattern = r"^## (.+)$"
        sections = re.split(section_pattern, content, flags=re.MULTILINE)

        # Handle content before first section
        if sections[0].strip():
            # Content before first ## header (intro/preamble)
            chunk_metadata = base_metadata.copy()
            chunk_metadata["section"] = "Introduction"

            chunks.append(KnowledgeChunk(content=sections[0].strip(), metadata=chunk_metadata))

        # Process pairs of (section_title, section_content)
        for i in range(1, len(sections), 2):
            if i + 1 < len(sections):
                section_title = sections[i].strip()
                section_content = sections[i + 1].strip()

                if section_content:
                    chunk_metadata = base_metadata.copy()
                    chunk_metadata["section"] = section_title

                    # Include section title in content for better searchability
                    full_content = f"## {section_title}\n\n{section_content}"

                    chunks.append(KnowledgeChunk(content=full_content, metadata=chunk_metadata))

        # If no sections found, treat entire content as one chunk
        if not chunks and content.strip():
            chunks.append(KnowledgeChunk(content=content.strip(), metadata=base_metadata))

        self.logger.debug(f"Parsed {len(chunks)} sections from {file_path.name}")

        return chunks


def parse_knowledge_file(file_path: Path) -> list[KnowledgeChunk]:
    """Convenience function to parse a knowledge file.

    Args:
        file_path: Path to the markdown file

    Returns:
        List of KnowledgeChunk objects

    """
    parser = KnowledgeParser()
    return parser.parse_conversation_log(file_path)
