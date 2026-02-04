"""PDF document parser using PyMuPDF."""

import hashlib
from datetime import datetime, timezone
from pathlib import Path

from aurora_context_doc.parser.base import DocumentParser
from aurora_core.chunks import DocChunk


class PDFParser(DocumentParser):
    """Parse PDF documents with TOC extraction and section hierarchy.

    Extraction strategy (tiered):
    1. Tier 1: Use doc.get_toc() for explicit TOC structure
    2. Tier 2: Font size detection for inferred headings
    3. Tier 3: Paragraph clustering with 10-20% overlap
    """

    def __init__(self):
        """Initialize PDF parser (lazy import PyMuPDF)."""
        self._fitz = None

    def _get_fitz(self):
        """Lazy import of PyMuPDF (fitz).

        Returns:
            fitz module

        Raises:
            ImportError: If pymupdf is not installed

        """
        if self._fitz is None:
            try:
                import fitz

                self._fitz = fitz
            except ImportError as e:
                raise ImportError(
                    "PyMuPDF (fitz) is required for PDF parsing. "
                    "Install with: pip install aurora-context-doc[pdf]"
                ) from e
        return self._fitz

    def supported_extensions(self) -> list[str]:
        """Return supported extensions.

        Returns:
            List of extensions: ["pdf", "PDF"]

        """
        return ["pdf", "PDF"]

    def parse(self, file_path: Path) -> list[DocChunk]:
        """Extract sections from PDF with TOC hierarchy.

        Args:
            file_path: Path to PDF file

        Returns:
            List of DocChunk objects with hierarchy

        Raises:
            FileNotFoundError: If PDF file not found
            ValueError: If PDF is invalid or corrupted
            RuntimeError: If parsing fails

        """
        if not file_path.exists():
            raise FileNotFoundError(f"PDF file not found: {file_path}")

        fitz = self._get_fitz()

        try:
            doc = fitz.open(str(file_path))
        except Exception as e:
            raise ValueError(f"Failed to open PDF: {file_path}") from e

        chunks = []
        timestamp = datetime.now(timezone.utc)

        try:
            # Tier 1: Extract TOC structure
            toc = doc.get_toc()

            if toc:
                chunks.extend(self._parse_with_toc(doc, toc, file_path, timestamp))
            else:
                # Tier 2: Font size detection for inferred headings
                chunks.extend(self._parse_with_font_detection(doc, file_path, timestamp))

        finally:
            doc.close()

        return chunks

    def _parse_with_toc(
        self, doc, toc: list, file_path: Path, timestamp: datetime
    ) -> list[DocChunk]:
        """Parse PDF using explicit TOC structure.

        Args:
            doc: PyMuPDF document object
            toc: Table of contents from doc.get_toc()
            file_path: Path to PDF file
            timestamp: Creation timestamp

        Returns:
            List of DocChunk objects

        """
        chunks = []
        chunk_map = {}  # Map (level, index) -> chunk_id for parent lookup

        for i, entry in enumerate(toc):
            level, title, page_num = entry

            # Generate unique chunk ID
            chunk_id = self._generate_chunk_id(file_path, f"toc-{i}")

            # Find parent chunk
            parent_id = None
            section_path = []

            if level > 1:
                # Look for parent at level-1
                for j in range(i - 1, -1, -1):
                    if toc[j][0] == level - 1:
                        parent_key = (level - 1, j)
                        parent_id = chunk_map.get(parent_key)
                        if parent_id:
                            # Build section path from parent
                            parent_chunk = next(
                                (c for c in chunks if c.chunk_id == parent_id), None
                            )
                            if parent_chunk:
                                section_path = parent_chunk.section_path + [parent_chunk.name]
                        break

            # Add current title to path
            section_path.append(title)

            # Extract page content (simple extraction for now)
            page_start = max(1, page_num)
            page_end = page_start  # For TOC entries, single page reference

            # Get text from page (basic extraction)
            try:
                page = doc.load_page(page_start - 1)  # 0-indexed
                content = page.get_text()
            except Exception:
                content = ""

            # Create TOC entry chunk
            chunk = DocChunk(
                chunk_id=chunk_id,
                file_path=str(file_path.absolute()),
                page_start=page_start,
                page_end=page_end,
                element_type="toc_entry",
                name=title,
                content=content[:1000] if content else "",  # Limit content length
                parent_chunk_id=parent_id,
                section_path=section_path,
                section_level=level,
                document_type="pdf",
                created_at=timestamp,
                updated_at=timestamp,
            )

            chunks.append(chunk)
            chunk_map[(level, i)] = chunk_id

        return chunks

    def _parse_with_font_detection(
        self, doc, file_path: Path, timestamp: datetime
    ) -> list[DocChunk]:
        """Parse PDF using font size detection (Tier 2 fallback).

        Args:
            doc: PyMuPDF document object
            file_path: Path to PDF file
            timestamp: Creation timestamp

        Returns:
            List of DocChunk objects

        """
        chunks = []

        # Simple fallback: Create one chunk per page
        for page_num in range(len(doc)):
            page = doc.load_page(page_num)
            text = page.get_text()

            if not text.strip():
                continue

            chunk_id = self._generate_chunk_id(file_path, f"page-{page_num + 1}")

            chunk = DocChunk(
                chunk_id=chunk_id,
                file_path=str(file_path.absolute()),
                page_start=page_num + 1,
                page_end=page_num + 1,
                element_type="paragraph",
                name=f"Page {page_num + 1}",
                content=text,
                parent_chunk_id=None,
                section_path=[f"Page {page_num + 1}"],
                section_level=1,
                document_type="pdf",
                created_at=timestamp,
                updated_at=timestamp,
            )

            chunks.append(chunk)

        return chunks

    def _generate_chunk_id(self, file_path: Path, suffix: str) -> str:
        """Generate unique chunk ID for a document section.

        Args:
            file_path: Path to document
            suffix: Unique suffix (e.g., "toc-1", "page-5")

        Returns:
            Unique chunk ID string

        """
        # Use file path + suffix for uniqueness
        content = f"{file_path.absolute()}:{suffix}"
        hash_digest = hashlib.sha256(content.encode()).hexdigest()[:16]
        return f"doc:pdf:{hash_digest}"


__all__ = ["PDFParser"]
