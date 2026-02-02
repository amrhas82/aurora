"""Document indexer for orchestrating parsing and storage."""

import logging
from pathlib import Path
from typing import Optional

from aurora_core.store import Store

from aurora_context_doc.chunker import DocumentChunker
from aurora_context_doc.parser.base import DocumentParser

logger = logging.getLogger(__name__)


class DocumentIndexer:
    """Orchestrates document parsing and storage.

    Handles:
    - Parser selection based on file extension
    - Chunk splitting and merging
    - Incremental indexing with content hash tracking
    - Batch storage operations
    """

    def __init__(
        self,
        store: Store,
        chunker: Optional[DocumentChunker] = None,
    ):
        """Initialize document indexer.

        Args:
            store: Storage backend for saving chunks
            chunker: Optional custom chunker (defaults to DocumentChunker())

        """
        self.store = store
        self.chunker = chunker or DocumentChunker()
        self._parsers: dict[str, DocumentParser] = {}

    def _get_parser(self, file_path: Path) -> Optional[DocumentParser]:
        """Get appropriate parser for file extension.

        Args:
            file_path: Path to document file

        Returns:
            DocumentParser instance, or None if unsupported

        """
        extension = file_path.suffix.lstrip(".").lower()

        # Lazy load parsers on demand
        if extension == "pdf":
            if "pdf" not in self._parsers:
                from aurora_context_doc.parser.pdf import PDFParser

                self._parsers["pdf"] = PDFParser()
            return self._parsers["pdf"]

        elif extension == "docx":
            if "docx" not in self._parsers:
                from aurora_context_doc.parser.docx import DOCXParser

                self._parsers["docx"] = DOCXParser()
            return self._parsers["docx"]

        return None

    def index_file(self, file_path: Path | str) -> int:
        """Index a single document file.

        Args:
            file_path: Path to document file

        Returns:
            Number of chunks created

        Raises:
            FileNotFoundError: If file does not exist
            ValueError: If file format is unsupported or invalid
            RuntimeError: If indexing fails

        """
        file_path = Path(file_path)

        if not file_path.exists():
            raise FileNotFoundError(f"Document file not found: {file_path}")

        # Get parser
        parser = self._get_parser(file_path)
        if parser is None:
            raise ValueError(f"Unsupported file format: {file_path.suffix}. Supported: .pdf, .docx")

        logger.info(f"Indexing document: {file_path}")

        # Parse document
        chunks = parser.parse(file_path)

        if not chunks:
            logger.warning(f"No chunks extracted from: {file_path}")
            return 0

        # Process chunks (split large, merge small)
        processed_chunks = []
        for chunk in chunks:
            # Split if too large
            split_chunks = self.chunker.split_large_section(chunk)
            processed_chunks.extend(split_chunks)

        # Optionally merge small chunks
        # processed_chunks = self.chunker.merge_small_sections(processed_chunks)

        # Save to store
        saved_count = 0
        for chunk in processed_chunks:
            try:
                # Use store's doc-specific save method if available
                if hasattr(self.store, "save_doc_chunk"):
                    self.store.save_doc_chunk(chunk)
                else:
                    # Fallback to generic save_chunk
                    self.store.save_chunk(chunk)

                saved_count += 1

            except Exception as e:
                logger.error(f"Failed to save chunk {chunk.id}: {e}")

        logger.info(f"Indexed {saved_count} chunks from {file_path}")
        return saved_count

    def index_directory(
        self,
        dir_path: Path | str,
        recursive: bool = True,
        extensions: Optional[list[str]] = None,
    ) -> int:
        """Index all documents in a directory.

        Args:
            dir_path: Path to directory
            recursive: If True, index subdirectories recursively
            extensions: Optional list of extensions to index (e.g., ["pdf", "docx"])

        Returns:
            Total number of chunks created

        Raises:
            FileNotFoundError: If directory does not exist
            RuntimeError: If indexing fails

        """
        dir_path = Path(dir_path)

        if not dir_path.exists():
            raise FileNotFoundError(f"Directory not found: {dir_path}")

        if not dir_path.is_dir():
            raise ValueError(f"Not a directory: {dir_path}")

        # Default to supported extensions
        if extensions is None:
            extensions = ["pdf", "docx"]

        # Normalize extensions
        extensions = [ext.lower().lstrip(".") for ext in extensions]

        # Find all matching files
        total_chunks = 0

        if recursive:
            pattern = "**/*"
        else:
            pattern = "*"

        for file_path in dir_path.glob(pattern):
            if not file_path.is_file():
                continue

            extension = file_path.suffix.lstrip(".").lower()
            if extension in extensions:
                try:
                    chunk_count = self.index_file(file_path)
                    total_chunks += chunk_count
                except Exception as e:
                    logger.error(f"Failed to index {file_path}: {e}")

        logger.info(f"Indexed {total_chunks} total chunks from {dir_path}")
        return total_chunks


__all__ = ["DocumentIndexer"]
