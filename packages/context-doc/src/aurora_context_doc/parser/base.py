"""Base document parser interface."""

from abc import ABC, abstractmethod
from pathlib import Path

from aurora_core.chunks import DocChunk


class DocumentParser(ABC):
    """Abstract base class for document parsers.

    All document parsers (PDF, DOCX, Markdown) must implement this interface
    to provide consistent extraction of hierarchical sections from documents.
    """

    @abstractmethod
    def parse(self, file_path: Path) -> list[DocChunk]:
        """Extract sections with hierarchy from a document.

        Args:
            file_path: Path to the document file

        Returns:
            List of DocChunk objects representing the document structure.
            Each chunk should have:
            - chunk_id: Unique identifier
            - element_type: "toc_entry" | "section" | "paragraph" | "table"
            - name: Section title
            - content: Section body text
            - parent_chunk_id: ID of parent chunk (None for root)
            - section_path: Pre-computed breadcrumb list
            - section_level: Heading depth (1-5)
            - page_start, page_end: Page numbers (if applicable)

        Raises:
            FileNotFoundError: If file does not exist
            ValueError: If file format is invalid
            RuntimeError: If parsing fails

        """

    @abstractmethod
    def supported_extensions(self) -> list[str]:
        """Return list of supported file extensions.

        Returns:
            List of extensions without dots (e.g., ["pdf", "PDF"])

        """

    def can_parse(self, file_path: Path) -> bool:
        """Check if this parser can handle the given file.

        Args:
            file_path: Path to check

        Returns:
            True if this parser supports the file extension

        """
        extension = file_path.suffix.lstrip(".").lower()
        return extension in [ext.lower() for ext in self.supported_extensions()]


__all__ = ["DocumentParser"]
