"""Markdown parser for knowledge documents and conversation logs.

This module provides the MarkdownParser class for extracting knowledge chunks
from markdown files (conversation logs, documentation, notes).
"""

import hashlib
import logging
from pathlib import Path

from aurora_context_code.knowledge_parser import KnowledgeParser
from aurora_context_code.parser import CodeParser
from aurora_core.chunks.code_chunk import CodeChunk


logger = logging.getLogger(__name__)


class MarkdownParser(CodeParser):
    """Markdown parser for knowledge documents.

    Extracts knowledge chunks from markdown files by:
    - Splitting content by ## headers (sections)
    - Extracting metadata from filenames (keywords, dates)
    - Creating searchable chunks for each section

    Knowledge chunks are stored as CodeChunk instances with chunk_type="knowledge"
    for compatibility with the existing retrieval infrastructure.
    """

    # Supported file extensions
    EXTENSIONS = {".md", ".markdown"}

    def __init__(self) -> None:
        """Initialize Markdown parser with knowledge parser."""
        super().__init__(language="markdown")
        self.knowledge_parser = KnowledgeParser()
        logger.debug("MarkdownParser initialized")

    def can_parse(self, file_path: Path) -> bool:
        """Check if this parser can handle the given file.

        Args:
            file_path: Path to check

        Returns:
            True if file has .md or .markdown extension, False otherwise

        """
        return file_path.suffix.lower() in self.EXTENSIONS

    def parse(self, file_path: Path) -> list[CodeChunk]:
        """Parse a markdown file and extract knowledge chunks.

        This method:
        1. Uses KnowledgeParser to split markdown by sections
        2. Converts KnowledgeChunk to CodeChunk for storage compatibility
        3. Adds metadata for searchability

        Args:
            file_path: Absolute path to markdown file to parse

        Returns:
            List of CodeChunk instances, one per markdown section.
            Returns empty list if parsing fails or file is empty.

        Raises:
            Does NOT raise exceptions - logs errors and returns empty list.

        """
        try:
            # Parse markdown into knowledge chunks
            knowledge_chunks = self.knowledge_parser.parse_conversation_log(file_path)

            if not knowledge_chunks:
                logger.debug(f"No content extracted from {file_path}")
                return []

            # Convert to CodeChunk format for storage
            code_chunks = []
            for i, kchunk in enumerate(knowledge_chunks):
                try:
                    # Generate chunk ID from content hash
                    content_hash = hashlib.sha256(kchunk.content.encode("utf-8")).hexdigest()[:16]

                    chunk_id = f"{file_path.stem}_section_{i}_{content_hash}"

                    # Create CodeChunk with knowledge-specific metadata
                    # CodeChunk is reused for storage compatibility (code, knowledge, reasoning)
                    code_chunk = CodeChunk(
                        chunk_id=chunk_id,
                        file_path=str(file_path),
                        element_type="knowledge",  # Use element_type to mark as knowledge
                        name=kchunk.metadata.get("section", file_path.stem),
                        line_start=1,  # Markdown doesn't have meaningful line numbers
                        line_end=len(kchunk.content.split("\n")),
                        signature="",  # No signature for markdown
                        docstring=kchunk.content,  # Store content in docstring field
                        dependencies=[],
                        complexity_score=0,
                        language="markdown",
                        metadata={
                            **kchunk.metadata,
                            "chunk_index": i,
                            "total_chunks": len(knowledge_chunks),
                            "is_knowledge": True,  # Flag for filtering
                        },
                    )

                    # Override chunk type to "kb" (CodeChunk defaults to "code")
                    code_chunk.type = "kb"

                    code_chunks.append(code_chunk)

                except Exception as e:
                    logger.error(f"Failed to convert knowledge chunk {i} from {file_path}: {e}")
                    continue

            logger.debug(f"Extracted {len(code_chunks)} knowledge chunks from {file_path}")
            return code_chunks

        except Exception as e:
            logger.error(f"Failed to parse {file_path}: {e}")
            return []


__all__ = ["MarkdownParser"]
