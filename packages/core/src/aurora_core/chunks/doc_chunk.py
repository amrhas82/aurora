"""Document chunk model for PDF, DOCX, and Markdown files.

This module provides the DocChunk dataclass for representing hierarchical
document sections with parent-child relationships and pre-computed breadcrumbs.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from aurora_core.chunks.base import Chunk


@dataclass
class DocChunk(Chunk):
    """Document section chunk (PDF, DOCX, Markdown).

    Represents a hierarchical section of a document with support for:
    - Page-based navigation (PDF)
    - Parent-child relationships
    - Pre-computed section paths (breadcrumbs)
    - Multiple element types (TOC entries, sections, paragraphs, tables)

    Attributes:
        chunk_id: Unique identifier for this chunk
        type: Always "doc" for document chunks
        file_path: Absolute path to the source document
        page_start: First page number (1-indexed, 0 for non-paginated)
        page_end: Last page number
        element_type: Type of document element ("toc_entry", "section", "paragraph", "table")
        name: Section title or heading text (e.g., "2.1 Installation")
        content: Full text content of this section
        parent_chunk_id: ID of parent chunk (None for top-level sections)
        section_path: Pre-computed breadcrumb list (e.g., ["Ch 2", "2.1 Install"])
        section_level: Heading depth (1-5, with 1 being top-level)
        document_type: Document format ("pdf", "docx", "markdown")
        embeddings: Optional semantic embeddings (binary format)
        metadata: Additional metadata dictionary

    Element Types:
        - toc_entry: Header-only chunk (high signal, structural anchor)
        - section: Full section with content
        - paragraph: Standalone paragraph (Tier 3 fallback)
        - table: Extracted table content

    Examples:
        >>> from datetime import datetime, timezone
        >>> chunk = DocChunk(
        ...     chunk_id="doc-1",
        ...     file_path="/path/to/manual.pdf",
        ...     page_start=5,
        ...     page_end=7,
        ...     element_type="section",
        ...     name="2.1 Installation",
        ...     content="To install the software...",
        ...     parent_chunk_id="doc-0",
        ...     section_path=["Chapter 2", "2.1 Installation"],
        ...     section_level=2,
        ...     document_type="pdf",
        ...     created_at=datetime.now(timezone.utc),
        ...     updated_at=datetime.now(timezone.utc)
        ... )

    """

    # Location
    file_path: str
    page_start: int = 0  # 1-indexed, 0 for non-paginated
    page_end: int = 0

    # Identity
    element_type: str = "section"  # "toc_entry" | "section" | "paragraph" | "table"
    name: str = ""  # Section title
    content: str = ""  # Section body text

    # Hierarchy (dual storage for efficiency)
    parent_chunk_id: str | None = None  # FK to parent chunk
    section_path: list[str] = field(default_factory=list)  # Pre-computed breadcrumb
    section_level: int = 0  # Heading depth (1-5)

    # Document metadata
    document_type: str = "pdf"  # "pdf" | "docx" | "markdown"
    embeddings: bytes | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: datetime | None = None
    updated_at: datetime | None = None

    def __init__(
        self,
        chunk_id: str,
        file_path: str,
        page_start: int = 0,
        page_end: int = 0,
        element_type: str = "section",
        name: str = "",
        content: str = "",
        parent_chunk_id: str | None = None,
        section_path: list[str] | None = None,
        section_level: int = 0,
        document_type: str = "pdf",
        embeddings: bytes | None = None,
        metadata: dict[str, Any] | None = None,
        created_at: datetime | None = None,
        updated_at: datetime | None = None,
    ):
        """Initialize a DocChunk.

        Args:
            chunk_id: Unique identifier for this chunk
            file_path: Absolute path to document file
            page_start: First page number (1-indexed, 0 for non-paginated)
            page_end: Last page number
            element_type: Type of element ("toc_entry", "section", "paragraph", "table")
            name: Section title
            content: Section body text
            parent_chunk_id: ID of parent chunk (None for root)
            section_path: Pre-computed breadcrumb list
            section_level: Heading depth (1-5)
            document_type: Document format ("pdf", "docx", "markdown")
            embeddings: Optional semantic embeddings
            metadata: Additional metadata
            created_at: Creation timestamp
            updated_at: Last update timestamp

        Raises:
            ValueError: If validation fails

        """
        # Initialize base class
        super().__init__(chunk_id=chunk_id, chunk_type="doc")

        # Set fields
        self.file_path = file_path
        self.page_start = page_start
        self.page_end = page_end
        self.element_type = element_type
        self.name = name
        self.content = content
        self.parent_chunk_id = parent_chunk_id
        self.section_path = section_path if section_path is not None else []
        self.section_level = section_level
        self.document_type = document_type
        self.embeddings = embeddings
        self.metadata = metadata if metadata is not None else {}

        # Override timestamps if provided
        if created_at is not None:
            self.created_at = created_at
        if updated_at is not None:
            self.updated_at = updated_at

        # Validate on construction
        self.validate()

    def validate(self) -> bool:
        """Validate DocChunk structure and data.

        Validation rules:
        - element_type must be one of: toc_entry, section, paragraph, table
        - document_type must be one of: pdf, docx, markdown
        - page_start must be >= 0
        - page_end must be >= 0
        - page_start must be <= page_end (if page_end > 0)
        - section_level must be >= 0

        Returns:
            True if valid

        Raises:
            ValueError: If validation fails with descriptive message

        """
        # Validate element_type
        valid_types = {"toc_entry", "section", "paragraph", "table"}
        if self.element_type not in valid_types:
            raise ValueError(
                f"Invalid element_type '{self.element_type}'. Must be one of {valid_types}"
            )

        # Validate document_type
        valid_doc_types = {"pdf", "docx", "markdown"}
        if self.document_type not in valid_doc_types:
            raise ValueError(
                f"Invalid document_type '{self.document_type}'. Must be one of {valid_doc_types}"
            )

        # Validate page numbers
        if self.page_start < 0:
            raise ValueError(f"page_start must be >= 0, got {self.page_start}")
        if self.page_end < 0:
            raise ValueError(f"page_end must be >= 0, got {self.page_end}")
        if self.page_end > 0 and self.page_start > self.page_end:
            raise ValueError(
                f"page_start ({self.page_start}) must be <= page_end ({self.page_end})"
            )

        # Validate section_level
        if self.section_level < 0:
            raise ValueError(f"section_level must be >= 0, got {self.section_level}")

        return True

    def to_json(self) -> dict[str, Any]:
        """Convert DocChunk to JSON-serializable dictionary.

        Returns:
            Dictionary with all chunk fields, structured for SQLiteStore.
            The "content" key contains a nested dict (like CodeChunk).

        """
        # Build metadata dict
        metadata_dict = {
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
        # Merge custom metadata
        if self.metadata:
            metadata_dict.update(self.metadata)

        return {
            "id": self.id,
            "type": self.type,
            "content": {
                "file_path": self.file_path,
                "page_start": self.page_start,
                "page_end": self.page_end,
                "element_type": self.element_type,
                "name": self.name,
                "text": self.content,  # Renamed to avoid confusion with outer structure
                "parent_chunk_id": self.parent_chunk_id,
                "section_path": self.section_path,
                "section_level": self.section_level,
                "document_type": self.document_type,
            },
            "metadata": metadata_dict,
        }

    @classmethod
    def from_json(cls, data: dict[str, Any]) -> "DocChunk":
        """Create DocChunk from JSON dictionary.

        Args:
            data: Dictionary with chunk fields (supports both nested and flat formats)

        Returns:
            DocChunk instance

        """
        from datetime import datetime

        # Handle nested format (from to_json) or flat format (legacy)
        content = data.get("content", {})
        metadata = data.get("metadata", {})

        # If content is a dict, extract from nested structure
        if isinstance(content, dict):
            file_path = content.get("file_path", data.get("file_path", ""))
            page_start = content.get("page_start", data.get("page_start", 0))
            page_end = content.get("page_end", data.get("page_end", 0))
            element_type = content.get("element_type", data.get("element_type", "section"))
            name = content.get("name", data.get("name", ""))
            text = content.get("text", data.get("content", ""))  # "text" in new format
            parent_chunk_id = content.get("parent_chunk_id", data.get("parent_chunk_id"))
            section_path = content.get("section_path", data.get("section_path", []))
            section_level = content.get("section_level", data.get("section_level", 0))
            document_type = content.get("document_type", data.get("document_type", "pdf"))
        else:
            # Flat format (legacy)
            file_path = data.get("file_path", "")
            page_start = data.get("page_start", 0)
            page_end = data.get("page_end", 0)
            element_type = data.get("element_type", "section")
            name = data.get("name", "")
            text = content if isinstance(content, str) else ""
            parent_chunk_id = data.get("parent_chunk_id")
            section_path = data.get("section_path", [])
            section_level = data.get("section_level", 0)
            document_type = data.get("document_type", "pdf")

        # Convert timestamps from metadata or top-level
        created_at = None
        created_at_str = metadata.get("created_at") or data.get("created_at")
        if created_at_str:
            created_at = datetime.fromisoformat(created_at_str)

        updated_at = None
        updated_at_str = metadata.get("updated_at") or data.get("updated_at")
        if updated_at_str:
            updated_at = datetime.fromisoformat(updated_at_str)

        # Get chunk_id from either "id" (new format) or "chunk_id" (legacy)
        chunk_id = data.get("id") or data.get("chunk_id", "")

        return cls(
            chunk_id=chunk_id,
            file_path=file_path,
            page_start=page_start,
            page_end=page_end,
            element_type=element_type,
            name=name,
            content=text,
            parent_chunk_id=parent_chunk_id,
            section_path=section_path,
            section_level=section_level,
            document_type=document_type,
            embeddings=None,  # Embeddings stored separately in DB
            metadata=metadata,
            created_at=created_at,
            updated_at=updated_at,
        )

    def get_breadcrumb(self) -> str:
        """Get formatted breadcrumb path.

        Returns:
            Breadcrumb string (e.g., "Ch 2 > 2.1 Install > 2.1.3 Requirements")

        """
        if not self.section_path:
            return self.name
        return " > ".join(self.section_path)

    def __repr__(self) -> str:
        """Return string representation of DocChunk."""
        breadcrumb = self.get_breadcrumb()
        return (
            f"DocChunk(id={self.id!r}, "
            f"type={self.element_type!r}, "
            f"path={breadcrumb!r}, "
            f"pages={self.page_start}-{self.page_end})"
        )


__all__ = ["DocChunk"]
